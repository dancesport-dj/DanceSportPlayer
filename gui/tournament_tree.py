"""🏆 The tournament pane: a folder tree of .m3u files, tabbed beside the library.

A competition weekend is not one playlist, it is dozens — DanceComp 2026 →
Freitag → Turnier 1, 2, 3 — and on the desk they have to be reachable in the
order the day runs, not in the order Explorer sorts them. So the operator
builds that tree here once and it is theirs: the folders are labels this app
keeps in a JSON file of its own, the leaves POINT at .m3u files wherever they
live. Nothing is copied, nothing is moved, nothing is renamed on disk — delete
a tournament here and the playlist file is still there.

Two grips on the same thing: drag a tournament out to load the whole round onto
a deck, or pick it and drag single tracks out of the list below it.
"""
import logging
import re
import threading

from pathlib import Path

from PySide6.QtCore import (
    QEventLoop,
    QMimeData,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QDrag,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from planner.m3u import (m3u_marker_rounds_in_order, read_m3u_tracks,
                         running_order_rounds)
from planner import i18n
from planner.models import DEFAULT_DANCES, MusicEntry
from planner.warmup import warmup_code
from planner import terms
from planner.terms import dance_name
from planner.planned import path_key
from planner.parsing import _detect_dance
from gui.common import (
    BusyDialog,
    _C_NEW_FG,
    _C_POP_FG,
    _entry_tooltip,
    _fmt_track_secs,
    _open_in_default_player,
    stopwatch_header,
)
from shared.widgets import (
    FlowLayout,
)

from gui.library_browser import (
    _LibPlayItem,
    _LibSortItem,
    _LibTable,
    fill_track_columns,
)

log = logging.getLogger("dancesport.gui.tournament_tree")

# Where a tree item sits in the node list, as "0/2/1". NOT the node dict
# itself: PySide6 marshals a dict through QVariant as a C++ QVariantMap and
# hands back a COPY, so edits would never reach the model and `is` comparisons
# would all miss. An index path is a string, which survives the round trip.
_ROLE_KEY = Qt.ItemDataRole.UserRole
# Track path on a row of the list below (what _LibTable.startDrag exports).
_ROLE_PATH = Qt.ItemDataRole.UserRole
# Fixed widths of the narrow columns; Artist (3) and Title (4) share the rest.
_TRACK_COL_W = {0: 30, 1: 46, 2: 90, 5: 52, 6: 52, 7: 52, 8: 70}
# A track the playlist points at but the disk no longer has.
_C_MISS_BG = QColor(255, 224, 178)   # orange

# The two ways to look at a filed weekend. Slots is what the pane opens in: on
# the desk a tournament is something you grab, not something you read.
VIEW_SLOTS = "slots"   # ▦ folders left, their playlists as draggable tiles
VIEW_LIST = "list"     # ▤ the whole tree left, the picked playlist's tracks right

# One slot. Wide enough for "Turnier 3 Sen I S" and two rows of them fit the
# strip the pane gets at the bottom of the window.
_SLOT_W, _SLOT_H = 200, 62
# Section tints, by which dances a playlist turns out to hold.
_STD = frozenset(DEFAULT_DANCES["Standard"]["S"])
_LAT = frozenset(DEFAULT_DANCES["Latin"]["S"])
_SLOT_TINTS = {"Standard": "#3b6ea5", "Latin": "#b5533c", "": "#9aa3ad"}

_ROUND_SHORT = {"vorrunde": "VR", "zwischenrunde": "ZR", "semifinale": "SF",
                "halbfinale": "SF", "finale": "ER", "endrunde": "ER"}
# The other direction: what a FILE NAME calls a round, in this app's words.
_NAME_ROUNDS = {"VR": "Vorrunde", "VORRUNDE": "Vorrunde", "VOR": "Vorrunde",
                "ZR": "Zwischenrunde", "ZWISCHENRUNDE": "Zwischenrunde",
                "ZWISCHEN": "Zwischenrunde",
                "HF": "Semifinale", "HALBFINALE": "Semifinale",
                "SEMIFINALE": "Semifinale", "SEMI": "Semifinale",
                "ER": "Finale", "ENDRUNDE": "Finale", "FINALE": "Finale",
                "END": "Finale"}


def _rounds_in_name(stem: str) -> list[str]:
    """The rounds a playlist's FILE NAME names, in the order it names them.

    One file per round is how a weekend is usually filed — '01_VR_JUGD_KINC',
    '07 ZR_WDSF', '09 ER_WDSF' — and a single round is a single pass through
    the dances, which is exactly what the running order cannot cut into
    anything. So the name is the only thing that knows which round the file is,
    and it is the operator's own word for it.

    Whole tokens only: ERSATZ is not an Endrunde. Bare 'SF' is not read as the
    semifinal either — in this collection that is Slowfox."""
    out: list[str] = []
    for token in re.split(r"[^A-Za-z0-9]+", stem.upper()):
        nth = re.fullmatch(r"(\d)\.?ZR|ZR(\d)", token)
        name = (f"{nth.group(1) or nth.group(2)}. Zwischenrunde" if nth
                else _NAME_ROUNDS.get(token))
        if name and name not in out:
            out.append(name)
    return out


def _round_short(name: str) -> str:
    """'Vorrunde' → VR, '2. Zwischenrunde' → 2ZR, 'Finale' → ER.

    Short enough that a whole tournament's shape fits on one slot, so the
    operator can tell a two-round warm-up class from a five-round A-final
    without opening either."""
    text = re.sub(r"\s*\(\d+\)$", "", (name or "").strip())
    m = re.match(r"(\d+)\.\s*(.+)", text)
    lead, rest = (m.group(1), m.group(2)) if m else ("", text)
    short = _ROUND_SHORT.get(rest.lower())
    if short is None:
        # Whatever the file called it: "Runde 3" → R3, anything else its initials.
        numbered = re.match(r"runde\s*(\d+)$", rest.lower())
        short = f"R{numbered.group(1)}" if numbered else rest[:2].upper()
    return lead + short


def normalize_nodes(data) -> list[dict]:
    """Whatever is in the JSON → the node list this pane works on.

    Hand-editing the file is expected (it is a plain list of names and paths),
    so anything unreadable is dropped rather than raised: a typo in one branch
    must not cost the operator the whole weekend's tree.
    """
    out: list[dict] = []
    for raw in data if isinstance(data, list) else []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        if raw.get("m3u"):
            out.append({"name": name, "m3u": str(raw["m3u"])})
        else:
            out.append({"name": name,
                        "children": normalize_nodes(raw.get("children"))})
    return out


def load_tree(store) -> list[dict]:
    """The saved tree, or [] when there is none yet (the normal first start)."""
    data = store.read()
    return normalize_nodes(data.get("tournaments")
                           if isinstance(data, dict) else data)


def load_view(store) -> str:
    """Which of the two views the pane was left in — the slot board unless the
    file says otherwise, which is also what a tree filed before either of them
    existed gets."""
    data = store.read()
    view = data.get("view") if isinstance(data, dict) else None
    return VIEW_LIST if view == VIEW_LIST else VIEW_SLOTS


def save_tree(store, nodes: list[dict], view: str = VIEW_SLOTS):
    store.write({"version": 1, "tournaments": nodes,
                 "view": VIEW_LIST if view == VIEW_LIST else VIEW_SLOTS})


class _TourneyTree(QTreeWidget):
    """The tree itself: .m3u files dropped in from Explorer become leaves,
    and a leaf dragged out is that .m3u file — so it lands on a deck exactly
    as it would coming from Explorer."""

    filesDropped = Signal(object, object)   # (target item | None, [Path, …])

    node_of = None      # set by TournamentTree: item key → node dict
    # set by TournamentTree: Ctrl+A → True when it marked something else instead
    select_all_cb = None

    def keyPressEvent(self, event):
        if (event.matches(QKeySequence.StandardKey.SelectAll)
                and self.select_all_cb is not None and self.select_all_cb()):
            return
        super().keyPressEvent(event)

    @staticmethod
    def _m3u_urls(mime) -> list[Path]:
        """The dropped .m3u files AND folders — a whole competition folder
        dropped in is the fastest way to get a weekend into the tree, and the
        folder itself says how it is organised."""
        out = []
        for u in mime.urls():
            if not u.isLocalFile():
                continue
            p = Path(u.toLocalFile())
            if p.is_dir() or p.name.lower().endswith(".m3u"):
                out.append(p)
        return out

    def dragEnterEvent(self, event):
        if self._m3u_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if self._m3u_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        paths = self._m3u_urls(event.mimeData())
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        # Handled on the next tick: reading a dropped folder walks everything
        # under it and puts a progress dialog up, and neither belongs inside the
        # drag gesture — Explorer stays frozen until this handler returns.
        item = self.itemAt(event.position().toPoint())
        QTimer.singleShot(0, lambda: self.filesDropped.emit(item, paths))

    def startDrag(self, _actions):
        paths = []
        for item in self.selectedItems():
            node = self.node_of(item.data(0, _ROLE_KEY)) or {}
            if node.get("m3u"):
                paths.append(str(node["m3u"]))
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime.setText("\n".join(paths))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.LinkAction,
                  Qt.DropAction.CopyAction)


class _SlotTile(QFrame):
    """One playlist as a thing to grab.

    It is a drag source first and a label second: what the operator does with a
    tournament at the desk is pull it onto a deck, and that gesture has to work
    from anywhere on the tile. So the press is remembered and the drag starts
    only past the system's drag distance — otherwise a click that wandered two
    pixels would be a drag and the tile could never simply be selected.
    """

    picked = Signal(str)        # key — this tile is now the selected one
    released = Signal(str)      # key — a click that did not become a drag
    activated = Signal(str)     # key — load it (double-click)
    menuRequested = Signal(str, object)   # key, global pos

    def __init__(self, key: str, meta: dict, parent=None):
        super().__init__(parent)
        self._key = key
        self._m3u = meta["m3u"]
        self._missing = meta["missing"]
        self._style = meta["style"]
        self._press = None
        self._selected = False
        # What a drag from here carries — set by the board, so a tile among
        # several marked ones takes them all along.
        self.drag_paths = lambda: [self._m3u]
        self.setObjectName("slot")
        self.setFixedSize(_SLOT_W, _SLOT_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.menuRequested.emit(self._key,
                                                self.mapToGlobal(pos)))

        box = QVBoxLayout(self)
        box.setContentsMargins(7, 4, 7, 4)
        box.setSpacing(0)
        self._name_lbl = QLabel()
        self._name_lbl.setStyleSheet("font-weight:600; font-size:11px;")
        self._sub_lbl = QLabel(meta["subtitle"])
        self._sub_lbl.setStyleSheet("color:#6b7480; font-size:10px;")
        # How far the tournament runs. Its own line and a shade darker than the
        # song count: which rounds are in the file is what says whether this is
        # the whole event or one round of it.
        self._round_lbl = QLabel()
        self._round_lbl.setStyleSheet("color:#4c5563; font-size:10px;")
        box.addWidget(self._name_lbl)
        box.addWidget(self._sub_lbl)
        box.addWidget(self._round_lbl)
        # Elided by hand: a QLabel would just clip, and the tail of "Turnier 3
        # Sen I S" is the half that says which tournament it is.
        self._name_lbl.setText(self._name_lbl.fontMetrics().elidedText(
            meta["name"], Qt.TextElideMode.ElideRight, _SLOT_W - 20))
        self._round_lbl.setText(self._round_lbl.fontMetrics().elidedText(
            meta.get("rounds", ""), Qt.TextElideMode.ElideRight, _SLOT_W - 20))
        self.setToolTip(meta["tip"])
        self._paint()

    def _paint(self):
        """The tile's own look. Written as a stylesheet rather than painted so
        the hover state comes for free — a slot has to answer the mouse, or
        nobody believes it can be picked up."""
        tint = "#e08a2e" if self._missing else _SLOT_TINTS[self._style]
        bg = "#fff5e6" if self._missing else ("#eaf1fb" if self._selected
                                              else "#ffffff")
        self.setStyleSheet(
            f"QFrame#slot {{ background:{bg}; border:1px solid "
            f"{'#7aa0d0' if self._selected else '#d3dae3'}; "
            f"border-left:4px solid {tint}; border-radius:6px; }}"
            f"QFrame#slot:hover {{ background:#f2f7ff; border-color:#7aa0d0; "
            f"border-left:4px solid {tint}; }}")

    def set_selected(self, on: bool):
        if on != self._selected:
            self._selected = on
            self._paint()

    # ── the grab ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
            self.picked.emit(self._key)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        if ((event.position().toPoint() - self._press).manhattanLength()
                < QApplication.startDragDistance()):
            return
        self._press = None
        paths = self.drag_paths()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime.setText("\n".join(paths))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())   # the tile itself rides the cursor
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.LinkAction,
                  Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event):
        if self._press is not None:
            self.released.emit(self._key)
        self._press = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.activated.emit(self._key)


class _SlotBoard(QScrollArea):
    """The tiles of one folder, wrapped across whatever width there is."""

    picked = Signal(str)
    activated = Signal(str)
    menuRequested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._flow = FlowLayout(self._inner, spacing=6)
        self.setWidget(self._inner)
        self._tiles: dict[str, _SlotTile] = {}
        self.selected_keys: list[str] = []   # the marked tiles, in filed order
        self._empty = QLabel("", self._inner)
        self._empty.setStyleSheet("color:#8a929c; font-size:11px;")

    def set_slots(self, slots: list[dict], hint: str):
        """slots: one meta dict per playlist, in the order they are filed."""
        while self._flow.count():
            item = self._flow.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._tiles.clear()
        self.selected_keys = []
        for meta in slots:
            tile = _SlotTile(meta["key"], meta)
            tile.drag_paths = lambda k=meta["key"]: self.drag_paths_of(k)
            tile.picked.connect(self.picked)
            tile.released.connect(self.select)
            tile.activated.connect(self.activated)
            tile.menuRequested.connect(self.menuRequested)
            self._tiles[meta["key"]] = tile
            self._flow.addWidget(tile)
        self._empty.setVisible(not slots)
        self._empty.setText(hint)
        if not slots:
            self._empty.adjustSize()
            self._empty.move(4, 4)

    def select(self, key: str):
        self._mark([key] if key in self._tiles else [])

    def select_all(self):
        self._mark(list(self._tiles))

    def _mark(self, keys: list[str]):
        self.selected_keys = keys
        for k, tile in self._tiles.items():
            tile.set_selected(k in keys)

    def drag_paths_of(self, key: str) -> list[str]:
        """The playlists a drag from tile `key` carries: every marked one when
        it is among them, else just its own."""
        keys = self.selected_keys if key in self.selected_keys else [key]
        return [self._tiles[k]._m3u for k in keys]


class TournamentTree(QWidget):
    """The 🏆 tab: the filing on the left, what a pick of it holds on the right.

    Two views of the same tree, on the ▦/▤ button. ▦ is what it opens in —
    folders on the left, and the playlists of the picked folder laid out as
    slots to grab. ▤ is the reading view: the whole tree, and the titles of the
    picked playlist."""

    playRequested = Signal(object, int)   # (Path | None, table row) — None stops
    loadRequested = Signal(str)           # .m3u to load onto the focused deck

    # Path → MusicEntry for tracks that are NOT in the library, set by MainWindow.
    resolve_entry = None

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self._store = store
        self._entries_by_path: dict = {}
        self._external: dict = {}   # path → entry built off the library, memoised
        self._rows_cache: dict = {}   # m3u → (stamp, finished rows)
        self._meta_cache: dict = {}   # m3u → (stamp, slot meta)
        self._collapsed = False       # ⊟: every folder folded away
        self._view = load_view(self._store)   # ▦ slots / ▤ tree + track list
        self._nodes: list[dict] = load_tree(self._store)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        bar = QHBoxLayout()
        bar.setSpacing(4)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#666;")
        bar.addWidget(self._count_lbl)
        bar.addStretch(1)
        for text, tip, slot in (
                ("▤", "Show the tracks of one playlist instead of the slots —\n"
                      "the whole tree on the left, the titles of whatever is\n"
                      "picked on the right (click again for the slots)",
                 self._toggle_view),
                ("⊟", "Collapse every folder — click again to open them all\n"
                      "(a whole season of weekends is a long tree)",
                 self._toggle_collapse_all),
                ("📁", "New folder — a day, a venue, a competition", self._add_folder),
                ("＋", "Add playlist files (.m3u) to the selected folder",
                 self._add_playlists),
                ("✎", "Rename the selected entry (F2)", self._rename),
                ("🗑", "Remove the selected entry from the tree —\n"
                       "the playlist file on disk is left alone (Del)", self._remove)):
            btn = QToolButton()
            btn.setText(text)
            btn.setToolTip(tip)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(slot)
            if text == "⊟":
                self._collapse_btn = btn   # its face says what the next click does
            elif text == "▤":
                self._view_btn = btn
            bar.addWidget(btn)
        v.addLayout(bar)

        # Always side by side: this pane is the wide, short strip at the bottom
        # of the window, and both views put a list of names next to what that
        # name holds — stacking them halves the one dimension there is least of.
        split = self._split = QSplitter(Qt.Orientation.Horizontal)
        self._tree = _TourneyTree()
        self._tree.node_of = self.node_at
        self._tree.select_all_cb = self._select_all_slots
        self._tree.setHeaderHidden(True)
        # Extended, so Ctrl+A marks the whole tree for Del or one drag.
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setToolTip(
            "Your competitions, days and tournaments — folders are labels,\n"
            "the 🎵 entries point at .m3u files wherever they lie.\n\n"
            "Drop .m3u files or a whole folder in from Explorer · pick a folder\n"
            "to lay its playlists out as slots on the right · drag a slot onto\n"
            "a deck to load the round · double-click it to load it onto the\n"
            "focused deck.")
        self._tree.currentItemChanged.connect(lambda *_: self._show_current())
        # Clicking the folder again makes IT the picked thing once more — what
        # Del, 🗑 and F2 act on has to be what is highlighted.
        self._tree.itemPressed.connect(lambda *_: self._board.select(""))
        self._tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self._tree.filesDropped.connect(self._on_files_dropped)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        split.addWidget(self._tree)

        # The library pane's columns plus the round each track is played in —
        # the same grouping the deck will head its ─── strips with once the
        # playlist is loaded, so the list can be read against the running order.
        self._table = _LibTable(0, 9)
        self._table.setHorizontalHeaderLabels(
            ["▶", "Round", "Dance", "Artist", "Title", "BPM", "⏱", "Pop", "Class"])
        hh = stopwatch_header(self._table, 6)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(False)
        hh.setMinimumSectionSize(24)
        for c, w in enumerate((30, 46, 90, 160, 240, 52, 52, 52, 70)):
            self._table.setColumnWidth(c, w)
        # …and they stretch to the pane on every resize, exactly as the library's
        # do — the same track has to read the same in both lists.
        self._table.resize_cb = lambda: fill_track_columns(
            self._table, _TRACK_COL_W, artist_col=3, title_col=4)
        self._table.verticalHeader().setVisible(False)
        # Plain rows without cell borders, as a deck draws a playlist.
        self._table.setShowGrid(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setDragEnabled(True)
        self._table.space_cb = self._start_row   # Space plays the selected row
        self._table.setToolTip(
            "The tracks of the selected playlist, in playing order.\n"
            "▶ or Space previews · drag them onto a deck or the player list ·\n"
            "double-click to open in your external player.")
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellDoubleClicked.connect(self._on_track_double_click)

        self._board = _SlotBoard()
        self._board.picked.connect(self._on_slot_picked)
        self._board.activated.connect(self._load_key)
        self._board.menuRequested.connect(self._on_slot_menu)
        self._board.setToolTip(
            "The playlists filed in the selected folder, one slot each.\n"
            "Drag a slot onto a deck to load that round · double-click it to\n"
            "load it onto the focused deck · right-click to rename, remove or\n"
            "read its tracks.")

        # One or the other, never both: the slots and the track list are two
        # answers to "which playlist" and there is room for one of them.
        self._right = QStackedWidget()
        self._right.addWidget(self._board)
        self._right.addWidget(self._table)
        split.addWidget(self._right)
        split.setChildrenCollapsible(False)
        # The tree names folders, the right half carries the weekend — so the
        # tree keeps its 300 px and everything else goes to what is beside it.
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 700])
        v.addWidget(split, stretch=1)
        # Σ badge under the list, the same one every deck and the party panel
        # carry: how long the tournament is, before it is loaded onto a deck.
        self._total_lbl = QLabel("")
        self._total_lbl.setStyleSheet(
            "color:#2c4a73; background:#eef3fb; border:1px solid #c9d6ea; "
            "border-radius:4px; padding:2px 6px; font-size:11px;")
        self._total_lbl.setToolTip(
            "Songs and total play time of the selected playlist\n"
            "(tracks this library doesn't know count, but add no time)")
        self._total_lbl.setVisible(False)
        v.addWidget(self._total_lbl)

        self._apply_view()
        self._rebuild()

    # ── Data ──

    def set_entries(self, entries: list[MusicEntry]):
        """The library, for showing dance / BPM of the tracks a playlist holds."""
        self._entries_by_path = {path_key(e.path): e for e in entries}
        self._external.clear()
        self._rows_cache.clear()   # every row was read against the old library
        self._meta_cache.clear()   # …and every slot was named against it too
        self._show_current()

    def _leaf_count(self, nodes: list[dict]) -> int:
        return sum(1 if n.get("m3u") else self._leaf_count(n.get("children") or [])
                   for n in nodes)

    def node_at(self, key) -> dict | None:
        """The node an item's index path points at, or None if the tree has
        moved on since (a stale key from before a removal)."""
        nodes, node = self._nodes, None
        for part in str(key or "").split("/"):
            if not part.isdigit() or int(part) >= len(nodes):
                return None
            node = nodes[int(part)]
            nodes = node.get("children") or []
        return node

    def _rebuild(self):
        """Tree widget ← node list. The node dicts are the model; the items only
        show them, so every edit works on the dict and calls back in here."""
        current = self._tree.currentItem()
        keep = current.data(0, _ROLE_KEY) if current else None
        self._tree.clear()
        # A playlist filed at the root has no folder to be picked under, so the
        # board would never show it. It gets one — but only while there is one,
        # or every tree grows a row that does nothing.
        if self._view == VIEW_SLOTS and any(n.get("m3u") for n in self._nodes):
            loose = QTreeWidgetItem(self._tree.invisibleRootItem())
            loose.setText(0, "📂  (not in a folder)")
            loose.setData(0, _ROLE_KEY, "")
        self._fill(self._tree.invisibleRootItem(), self._nodes, "", keep)
        n = self._leaf_count(self._nodes)
        self._count_lbl.setText((i18n.t("(%d playlist)") if n == 1
                                 else i18n.t("(%d playlists)")) % n if n else "")
        self._show_current()

    def _toggle_collapse_all(self):
        """⊟ / ⊞ — fold the whole tree away, or open it again. Kept as a flag,
        not just applied once: every edit rebuilds the tree from the node list,
        and a tree that springs open again on the next rename is no help."""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._tree.collapseAll()
        else:
            self._tree.expandAll()
        self._collapse_btn.setText("⊞" if self._collapsed else "⊟")

    def _apply_view(self):
        """Which half of the stack is showing, and what the button then offers.

        The two views also mean different things by "selected": on the board it
        is a FOLDER that is picked and its playlists are the tiles, in the list
        it is a playlist that is picked and its tracks are the rows. So the
        tree itself is not the same tree — the leaves are only in one of
        them — and switching has to rebuild it."""
        slots = self._view == VIEW_SLOTS
        self._right.setCurrentWidget(self._board if slots else self._table)
        self._view_btn.setText("▤" if slots else "▦")

    def _toggle_view(self):
        self._view = VIEW_LIST if self._view == VIEW_SLOTS else VIEW_SLOTS
        self._apply_view()
        self._rebuild()
        self._save()

    def _fill(self, parent, nodes: list[dict], prefix: str, keep):
        slots = self._view == VIEW_SLOTS
        for i, node in enumerate(nodes):
            key = f"{prefix}{i}"
            leaf = bool(node.get("m3u"))
            if leaf and slots:
                continue   # the playlists are the tiles on the board, not rows
            item = QTreeWidgetItem(parent)
            item.setText(0, ("🎵  " if leaf else "📁  ") + node["name"])
            item.setData(0, _ROLE_KEY, key)
            if slots:
                # What picking this folder will lay out. Silent when it holds no
                # playlists of its own — a "(0)" reads like something is broken.
                held = sum(1 for n in node.get("children") or [] if n.get("m3u"))
                if held:
                    item.setText(0, f"{item.text(0)}  ({held})")
            if leaf:
                missing = not Path(node["m3u"]).is_file()
                item.setToolTip(0, ("⚠ missing: " if missing else "") + node["m3u"])
                if missing:
                    item.setText(0, "⚠  " + node["name"])
            else:
                item.setExpanded(not self._collapsed)
                self._fill(item, node.get("children") or [], key + "/", keep)
            if key == keep:
                self._tree.setCurrentItem(item)

    def _save(self):
        save_tree(self._store, self._nodes, self._view)

    # ── The tracks of the selected playlist ──

    def _current_key(self) -> str:
        item = self._tree.currentItem()
        return (item.data(0, _ROLE_KEY) or "") if item else ""

    def _current_node(self) -> dict | None:
        return self.node_at(self._current_key())

    def _picked_nodes(self) -> list[dict]:
        """What ✎ / 🗑 / F2 / Del act on: on the ▦ board the marked tiles,
        since the tree row there is their folder — otherwise the marked tree
        rows. An entry under a marked folder goes with the folder already."""
        if self._view == VIEW_SLOTS and self._board.selected_keys:
            keys = list(self._board.selected_keys)
        else:
            keys = ([it.data(0, _ROLE_KEY) or "" for it in self._tree.selectedItems()]
                    or [self._current_key()])
        keys = [k for k in keys
                if not any(o and k.startswith(o + "/") for o in keys)]
        return [n for n in (self.node_at(k) for k in keys) if n is not None]

    def _select_all_slots(self) -> bool:
        """Ctrl+A on the ▦ board marks the folder's playlists, not the folders
        beside it — those are what the tab is about there."""
        if self._view != VIEW_SLOTS:
            return False
        self._board.select_all()
        return True

    def _entry_for(self, path: Path) -> MusicEntry | None:
        """The MusicEntry behind a track of the playlist. A tournament list can
        point at files outside the library (an older copy of the collection, a
        USB stick), and those would otherwise show up as bare file names — so
        what the library doesn't know is read off the file itself, once."""
        key = path_key(path)
        entry = self._entries_by_path.get(key)
        if entry is not None:
            return entry
        if key in self._external:
            return self._external[key]
        entry = None
        if self.resolve_entry is not None and path.is_file():
            try:
                entry = self.resolve_entry(path)
            except Exception as exc:
                log.debug("🏆 Could not read %s: %s", path.name, exc)
        self._external[key] = entry
        return entry

    def _round_names(self, m3u_path, tracks, entries) -> list[str]:
        """The round each track is played in, one name per row ("" when the file
        yields none). Read from the '# ══ Round ══' markers this app writes into
        its own exports, otherwise derived from the running order — the very same
        two sources the deck uses, so the list here and the ─── strips there tell
        the same story about the same file."""
        marked = m3u_marker_rounds_in_order(m3u_path)
        if len({name for _p, name in marked}) > 1:
            # Walked rather than looked up: a track played in two rounds is two
            # lines in the file, and each row wants the round of ITS line.
            names, i = [], 0
            for p, _x in tracks:
                key = path_key(p)
                j = next((k for k in range(i, len(marked)) if marked[k][0] == key),
                         None)
                names.append("" if j is None else marked[j][1])
                i = i if j is None else j + 1
            return names
        # The name, when it names ONE round: then the whole file is that round,
        # and it says so more surely than any reading of the running order —
        # which sees a lone round as a single pass and calls it nothing.
        named = _rounds_in_name(Path(m3u_path).stem)
        if len(named) == 1:
            return [named[0]] * len(tracks)
        # A track the library doesn't know still has its dance in the file name,
        # which is all the round derivation reads.
        stand_ins = [e if e is not None else MusicEntry(path=p, title=x or p.stem)
                     for (p, x), e in zip(tracks, entries)]
        # The order is only cut, never regrouped, so the segment lengths lay the
        # names back onto the rows — and a file listed twice keeps both rounds.
        names: list[str] = []
        for name, seg in running_order_rounds(stand_ins):
            names.extend([name] * len(seg))
        return names if len(names) == len(tracks) else [""] * len(tracks)

    @staticmethod
    def _stamp(path: Path):
        """(mtime, size) of a file, or None when it isn't there — what says
        whether a cached reading of it is still the file's own."""
        try:
            st = path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _rows_for(self, m3u_path) -> list[dict]:
        """The finished rows of a playlist: everything read off disk and looked
        up in the library, ready to be poured into the table.

        Cached per file, because clicking through a weekend means coming back:
        the reading is a file read, a library lookup and a tag read per unknown
        track, and doing that again on every click makes the tree stutter. The
        file's own (mtime, size) says when the reading is stale — an .m3u
        re-exported under the same name reads fresh."""
        p = Path(m3u_path)
        key = path_key(p)
        stamp = self._stamp(p)
        hit = self._rows_cache.get(key)
        if hit is not None and hit[0] == stamp:
            return hit[1]
        tracks = read_m3u_tracks(p)
        entries = [self._entry_for(tp) for tp, _x in tracks]
        rounds = self._round_names(p, tracks, entries) if tracks else []
        rows = []
        for (path, extinf), entry, round_name in zip(tracks, entries, rounds):
            missing = not path.is_file()
            secs = int(getattr(entry, "duration", 0) or 0) if entry is not None else 0
            rows.append({
                "path": path,
                "round": round_name,
                "dance": dance_name(warmup_code(entry), entry.dance
                                         or entry.other_genre or "")
                         if entry is not None else "",
                "artist": getattr(entry, "tag_artist", None) or "",
                "title": (entry.title if entry is not None else "")
                         or extinf or path.stem,
                "tip": (f"⚠ Not where the playlist says it is:\n{path}" if missing
                        else _entry_tooltip(entry) if entry is not None
                        else str(path)),
                "bpm": entry.bpm if entry is not None else None,
                "secs": secs,
                "length": _fmt_track_secs(secs) if secs else "",
                # None where the library has never heard of the track at all:
                # ✦ says "never played", and that is a thing only a track we
                # know can be.
                "pop": (entry.popularity or 0) if entry is not None else None,
                "classes": getattr(entry, "classes_ok", None) or [],
                "missing": missing,
            })
        self._rows_cache[key] = (stamp, rows)
        return rows

    # ── The slots of the selected folder ──

    def _slot_meta(self, node: dict, key: str) -> dict:
        """The name-plate of one slot: how many songs, which dances, and the
        first titles for the tooltip.

        Read off the .m3u and the library ONLY — never off the tracks
        themselves. A board shows a whole folder at once, and the track list's
        habit of opening every file the library doesn't know to read its tags
        would turn picking a folder of foreign playlists into a wait. A dance
        the library can't name is taken from the file name, which is where the
        code sits in this collection anyway."""
        m3u = str(node["m3u"])
        cache_key = m3u.lower()
        stamp = self._stamp(Path(m3u))
        hit = self._meta_cache.get(cache_key)
        if hit is not None and hit[0] == stamp:
            meta = dict(hit[1])
            meta["key"] = key       # the same file can be filed twice
            meta["name"] = node["name"]
            return meta
        tracks = read_m3u_tracks(Path(m3u))
        codes, titles, entries = [], [], []
        for path, extinf in tracks:
            entry = self._entries_by_path.get(path_key(path))
            entries.append(entry)
            code = entry.dance if entry is not None else _detect_dance(path.name)
            if code and code not in codes:
                codes.append(code)
            if len(titles) < 15:
                titles.append((entry.title if entry is not None else "")
                              or extinf or path.stem)
        full, short = self._slot_rounds(Path(m3u), tracks, entries)
        held = set(codes)
        style = ("Standard" if held and held <= _STD else
                 "Latin" if held and held <= _LAT else "")
        missing = stamp is None
        shown = codes[:5] + (["…"] if len(codes) > 5 else [])
        meta = {
            "m3u": m3u,
            "missing": missing,
            "style": style,
            "songs": len(tracks),
            "rounds": "" if missing else " - ".join(short),
            "subtitle": ("⚠  the file is gone" if missing else
                         f"{len(tracks)} ♪" + ("  ·  " + " ".join(shown)
                                               if shown else "")),
            "tip": (f"⚠ Not where the tree says it is:\n{m3u}" if missing else
                    m3u + ("\n" + "  →  ".join(full) if full else "")
                    + "\n\n" + "\n".join(titles)
                    + ("\n…" if len(tracks) > len(titles) else "")),
        }
        self._meta_cache[cache_key] = (stamp, meta)
        meta = dict(meta)
        meta["key"] = key
        meta["name"] = node["name"]
        return meta

    def _slot_rounds(self, m3u_path, tracks, entries) -> tuple[list, list]:
        """The rounds a playlist plays out, as (full names, short codes).

        Both are empty when the file names no rounds — a warm-up or a party set
        runs through the dances all evening and has no shape to show. Same two
        sources as the Runde column, so a slot and the list behind it cannot
        disagree about the same file."""
        if not tracks:
            return [], []
        rounds = self._round_names(m3u_path, tracks, entries)
        if not any(rounds):
            # A file holding rounds of SEVERAL classes — "08 ZR_WDSF_ER_JUGC" —
            # runs through the dances in a shape no reading can cut, but its
            # name still lists what is in it. A row can't be told which of them
            # it belongs to; a slot only has to say that both are there.
            rounds = _rounds_in_name(Path(m3u_path).stem)
        seen, full, short = set(), [], []
        for name in rounds:
            code = _round_short(name) if name else ""
            if code and code not in seen:
                seen.add(code)
                full.append(name)
                short.append(code)
        return full, short

    def _folder_children(self) -> list[dict]:
        """The nodes the board lays out: what is filed DIRECTLY in the picked
        folder. Its sub-folders stay on the left, where they can be picked in
        turn — a whole weekend's rounds at once would need a board taller than
        this pane has ever been."""
        key = self._current_key()
        if not key:                     # 📂 the root's own loose playlists
            return self._nodes
        node = self.node_at(key)
        if node is None or node.get("m3u"):
            return []
        return node.get("children") or []

    def _show_slots(self):
        slots = [self._slot_meta(n, f"{self._current_key()}/{i}".lstrip("/"))
                 for i, n in enumerate(self._folder_children()) if n.get("m3u")]
        self._board.set_slots(
            slots, "Pick a folder on the left to see the playlists in it."
            if not self._nodes or self._tree.currentItem() is None
            else "No playlists filed directly in this folder.")
        songs = sum(m["songs"] for m in slots)
        self._total_lbl.setText(
            "Σ  " + (i18n.t("%d playlist") if len(slots) == 1 else i18n.t("%d playlists")) % len(slots)
            + "  ·  " + (i18n.t("%d song") if songs == 1 else i18n.t("%d songs")) % songs)
        self._total_lbl.setVisible(bool(slots))

    def _show_current(self):
        """Whichever of the two views is up gets refilled — both hang off the
        same selection change in the tree."""
        if self._view == VIEW_SLOTS:
            self._show_slots()
        else:
            self._show_tracks()

    def _on_slot_picked(self, key: str):
        # A press on one of several marked tiles keeps them marked — it may be
        # the start of dragging them all. A plain click narrows on release.
        if key not in self._board.selected_keys:
            self._board.select(key)

    def _load_key(self, key: str):
        node = self.node_at(key) or {}
        if not node.get("m3u"):
            return
        if not Path(node["m3u"]).is_file():
            QMessageBox.warning(self, "Load playlist",
                                i18n.t("The playlist file is gone:\n\n%s") % node['m3u'])
            return
        self.loadRequested.emit(str(node["m3u"]))

    def _on_slot_menu(self, key: str, pos):
        node = self.node_at(key)
        if node is None:
            return
        if key not in self._board.selected_keys:
            self._board.select(key)
        menu = QMenu(self)
        load_act = menu.addAction("▶  Load onto the focused deck")
        tracks_act = menu.addAction("🎵  Show its tracks")
        menu.addSeparator()
        rename_act = menu.addAction("✎  Rename…")
        remove_act = menu.addAction("🗑  Remove from tree")
        chosen = menu.exec(pos)
        if chosen is load_act:
            self._load_key(key)
        elif chosen is tracks_act:
            self._show_tracks_of(key)
        elif chosen is rename_act:
            self._rename_node(node)
        elif chosen is remove_act:
            self._remove()

    def _show_tracks_of(self, key: str):
        """The way back to the titles: switch to the ▤ view with this playlist
        already picked, so 'what is actually in it' is one click from a slot."""
        self._view = VIEW_LIST
        self._apply_view()
        self._save()
        self._rebuild()
        self._select_key(key)

    def _select_key(self, key: str):
        it = QTreeWidgetItemIterator(self._tree)
        while it.value():
            item = it.value()
            if item.data(0, _ROLE_KEY) == key:
                self._tree.setCurrentItem(item)
                return
            it += 1

    def _update_total(self, rows: list[dict]):
        """The Σ badge under the list — songs and play time, worded like the
        deck badges so the same playlist reads the same on either side."""
        n = len(rows)
        secs = sum(r["secs"] for r in rows)
        self._total_lbl.setText(
            "Σ  " + (i18n.t("%d song") if n == 1 else i18n.t("%d songs")) % n
            + (f"  ·  ~{_fmt_track_secs(secs)}" if secs else ""))
        self._total_lbl.setVisible(bool(n))

    def _show_tracks(self):
        node = self._current_node() or {}
        rows = self._rows_for(node["m3u"]) if node.get("m3u") else []
        self._update_total(rows)
        t = self._table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            missing = row["missing"]
            play_it = _LibPlayItem("▶")
            play_it.setData(_ROLE_PATH, row["path"])   # what startDrag exports
            play_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            play_it.setToolTip("Play / stop this track")
            t.setItem(r, 0, play_it)
            # Short, as the slots write it: "1. Zwischenrunde" is wider than
            # the column, and VR / 1ZR / ER is how the desk says it anyway.
            round_it = QTableWidgetItem(
                _round_short(row["round"]) if row["round"] else "")
            round_it.setToolTip(terms.round_name(row["round"]))
            round_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 1, round_it)
            t.setItem(r, 2, QTableWidgetItem(row["dance"]))
            artist_it = QTableWidgetItem(row["artist"])
            t.setItem(r, 3, artist_it)   # Artist sits LEFT of Title
            title = row["title"]
            title_it = QTableWidgetItem("⚠  " + title if missing else title)
            title_it.setToolTip(row["tip"])
            artist_it.setToolTip(row["tip"])
            t.setItem(r, 4, title_it)
            bpm_it = _LibSortItem(str(row["bpm"]) if row["bpm"] else "")
            bpm_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 5, bpm_it)
            len_it = _LibSortItem(row["length"])
            len_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 6, len_it)
            pop = row["pop"]
            pop_it = _LibSortItem("" if pop is None else f"★{pop}" if pop else "✦")
            pop_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pop_it.setForeground(_C_POP_FG if pop else _C_NEW_FG)
            t.setItem(r, 7, pop_it)
            classes = row["classes"]
            cls_it = QTableWidgetItem(f"[{','.join(classes)}]" if classes else "")
            cls_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 8, cls_it)
            if missing:
                # The ⚠ alone is easy to scroll past — a whole orange row is not,
                # and on the desk this is the one thing worth noticing early.
                for c in range(t.columnCount()):
                    t.item(r, c).setBackground(_C_MISS_BG)
            t.setRowHeight(r, 22)

    # ── Previewing a track ──

    def _row_path(self, row: int) -> Path | None:
        it = self._table.item(row, 0)
        return it.data(_ROLE_PATH) if it else None

    def _on_cell_clicked(self, row: int, col: int):
        """A click on the ▶ column toggles preview playback of that row."""
        if col != 0:
            return
        it = self._table.item(row, 0)
        if it is None:
            return
        if it.text() == "■":
            it.setText("▶")
            self.playRequested.emit(None, -1)
            return
        self._start_row(row)

    def _start_row(self, row: int):
        path = self._row_path(row)
        if path:
            self.on_playback_stopped()
            self._table.item(row, 0).setText("■")
            self.playRequested.emit(path, row)

    def on_playback_stopped(self):
        """Reset the ▶/■ marker — playback ended or started somewhere else."""
        t = self._table
        for r in range(t.rowCount()):
            it = t.item(r, 0)
            if it is not None and it.text() == "■":
                it.setText("▶")

    def _on_track_double_click(self, row: int, col: int):
        if col == 0:   # the click handler above already toggled this row
            return
        path = self._row_path(row)
        if path and Path(path).is_file():
            _open_in_default_player(Path(path), self)

    # ── Editing the tree ──

    def _target_children(self) -> list[dict]:
        """Where a new entry goes: into the selected folder, beside a selected
        playlist, at the root when nothing is selected."""
        key = self._current_key()
        while key:
            node = self.node_at(key)
            if node is not None and not node.get("m3u"):
                return node.setdefault("children", [])
            key = key.rpartition("/")[0]
        return self._nodes

    def _add_folder(self):
        name, ok = QInputDialog.getText(self, "New folder",
                                        "Name (competition, day, tournament):")
        name = (name or "").strip()
        if not ok or not name:
            return
        self._target_children().append({"name": name, "children": []})
        self._save()
        self._rebuild()

    def _add_playlists(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add playlists to the tournament tree", "",
            "Playlists (*.m3u);;All files (*)")
        if files:
            self._add_m3u_files(self._target_children(),
                                [Path(f) for f in files])

    def _add_playlist_folder(self):
        """A whole folder off the disk, filed as a dropped one would be: a
        branch mirroring it, with every .m3u under it."""
        folder = QFileDialog.getExistingDirectory(
            self, "Add a folder of playlists to the tournament tree")
        if folder:
            self._add_m3u_files(self._target_children(), [Path(folder)])

    def _on_files_dropped(self, item, paths):
        """.m3u files and folders dragged in from Explorer — they land in the
        folder they were dropped on (or beside the playlist they were dropped
        on). A folder arrives as a branch mirroring what is inside it."""
        self._tree.setCurrentItem(item)
        self._add_m3u_files(self._target_children(), paths)

    def _folder_node(self, folder: Path, tick=None) -> dict | None:
        """A dropped folder as a branch: sub-folders become folders, .m3u files
        become playlists — folders first, then files, as Explorer shows them.
        None when there is no playlist under it at all — a music folder would
        otherwise arrive as an empty skeleton.

        `tick(folder)` is called for every folder read, so the walk can say
        where it is instead of looking hung."""
        if tick is not None:
            tick(folder)
        children: list[dict] = []
        try:
            items = sorted(folder.iterdir(),
                           key=lambda p: (p.is_file(), p.name.lower()))
        except OSError as exc:
            log.warning("🏆 Could not read the dropped folder\n"
                        "folder: %s\n"
                        "error: %s", folder, exc)
            return None
        for p in items:
            if p.is_dir():
                sub = self._folder_node(p, tick)
                if sub is not None:
                    children.append(sub)
            elif p.name.lower().endswith(".m3u"):
                children.append({"name": p.stem, "m3u": str(p)})
        return {"name": folder.name, "children": children} if children else None

    def _read_folders(self, folders: list[Path]) -> dict[Path, dict | None]:
        """Each folder's branch (`_folder_node`), read on a worker thread.

        A weekend on a network or Dropbox drive is thousands of directories, and
        a single listing there can take seconds. Walked on the UI thread, the
        wait dialog could not paint or pulse, and Windows drew its frozen
        copy over the window. With the event loop running, the dialog can wait
        the usual grace period: a folder of a few playlists shows none."""
        branches: dict[Path, dict | None] = {}
        seen = [0, ""]

        def tick(folder: Path):
            seen[0] += 1
            seen[1] = folder.name

        def walk():
            for folder in folders:
                branches[folder] = self._folder_node(folder, tick)

        worker = threading.Thread(target=walk, name="tree-folder-walk", daemon=True)
        dlg = BusyDialog(self, message="📁 Reading the dropped folder…")
        dlg.set_progress(0, 0)   # its final shape before it is ever shown
        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(50)

        def check():
            if seen[0]:
                dlg.set_progress(0, 0, f"{seen[0]} folder(s) read  ·  {seen[1]}")
            if not worker.is_alive():
                loop.quit()

        poll.timeout.connect(check)
        worker.start()
        dlg.show_after()
        poll.start()
        loop.exec()
        poll.stop()
        dlg.finish()   # before any message box, or it sits behind it
        return branches

    def _add_m3u_files(self, children: list[dict], paths: list[Path]):
        folders = [p for p in paths if p.is_dir()]
        branches = self._read_folders(folders) if folders else {}
        added = 0
        empty: list[str] = []
        for p in paths:
            if p in folders:
                node = branches.get(p)
                if node is None:
                    empty.append(p.name)
                    continue
                children.append(node)
                added += self._leaf_count([node])
            else:
                children.append({"name": p.stem, "m3u": str(p)})
                added += 1
        for name in empty:
            QMessageBox.information(
                self, "Add folder", i18n.t("No .m3u playlists found under “%s”.") % name)
        if not added:
            return
        self._save()
        self._rebuild()
        log.info("🏆 Added %s playlist(s) to the tournament tree", added)

    def file_saved(self, paths: list[Path], folder: str | None = None) -> int:
        """Just-saved .m3u files, filed where "Add playlists…" would put them —
        a tournament day in a folder `folder` there, the one of that name
        when it already exists. A file filed there already is not filed
        again, so saving a day twice leaves one entry each. The day's folder,
        or the first playlist, is then picked. Returns how many were filed."""
        children = self._target_children()
        day = None
        if folder:
            # Picked (after the last save of it) is the day's folder itself.
            key = self._current_key()
            while key and day is None:
                node = self.node_at(key)
                if node is not None and not node.get("m3u") and node.get("name") == folder:
                    day = node
                key = key.rpartition("/")[0]
            day = day or next((n for n in children
                               if not n.get("m3u") and n.get("name") == folder), None)
            if day is None:
                day = {"name": folder, "children": []}
                children.append(day)
            children = day.setdefault("children", [])
        there = {path_key(n["m3u"]) for n in children if n.get("m3u")}
        added = 0
        for p in paths:
            if path_key(p) not in there:
                there.add(path_key(p))
                children.append({"name": Path(p).stem, "m3u": str(p)})
                added += 1
        if added:
            self._save()
            self._rebuild()
        first = next((n for n in children if n.get("m3u")
                      and paths and path_key(n["m3u"]) == path_key(paths[0])), None)
        shown = day if day is not None else first
        if shown is not None:
            self._pick_node(shown)
        return added

    def _key_of(self, target: dict, nodes=None, prefix: str = "") -> str | None:
        """The index path of node `target` (by identity), None when not filed."""
        for i, node in enumerate(self._nodes if nodes is None else nodes):
            key = f"{prefix}{i}"
            if node is target:
                return key
            found = self._key_of(target, node.get("children") or [], key + "/")
            if found is not None:
                return found
        return None

    def _pick_node(self, node: dict):
        """Pick `node` in the tree — a playlist in the ▦ view on its folder's
        board, since it is no tree row there — and scroll it into view."""
        key = self._key_of(node)
        if key is None:
            return
        if node.get("m3u") and self._view == VIEW_SLOTS:
            self._select_key(key.rpartition("/")[0])
            self._board.select(key)
        else:
            self._select_key(key)
        item = self._tree.currentItem()
        if item is not None:
            self._tree.scrollToItem(item)

    def _on_tree_double_click(self, item, _col: int):
        """Double-click on a playlist loads it — MainWindow asks first when the
        deck it would land on is not empty. A folder just folds open/shut."""
        node = self.node_at(item.data(0, _ROLE_KEY)) if item else None
        if not (node or {}).get("m3u"):
            return
        if not Path(node["m3u"]).is_file():
            QMessageBox.warning(self, "Load playlist",
                                i18n.t("The playlist file is gone:\n\n%s") % node['m3u'])
            return
        self.loadRequested.emit(str(node["m3u"]))

    def _rename(self):
        # No argument of its own: this is a button slot, and Qt hands a slot
        # that accepts one the `checked` flag — which would arrive as the node.
        nodes = self._picked_nodes()
        if len(nodes) == 1:
            self._rename_node(nodes[0])

    def _rename_node(self, node: dict | None):
        if node is None:
            return
        name, ok = QInputDialog.getText(self, "Rename", "Name:",
                                        text=node["name"])
        name = (name or "").strip()
        if ok and name:
            node["name"] = name
            self._save()
            self._rebuild()

    def _remove_from(self, nodes: list[dict], node: dict) -> bool:
        for i, n in enumerate(nodes):
            if n is node:
                del nodes[i]
                return True
            if n.get("children") and self._remove_from(n["children"], node):
                return True
        return False

    def _remove(self):
        nodes = self._picked_nodes()
        if len(nodes) == 1:
            self._remove_node(nodes[0])
            return
        if not nodes or QMessageBox.question(
                self, "Remove",
                i18n.t("Remove %d entries from the tree?\n\n%d playlist file(s) are listed "
                       "under them — they stay on disk, only these entries go.")
                % (len(nodes), self._leaf_count(nodes)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        for node in nodes:
            self._remove_from(self._nodes, node)
        self._save()
        self._rebuild()

    def _remove_node(self, node: dict | None):
        if node is None:
            return
        held = self._leaf_count([node])
        if held and QMessageBox.question(
                self, "Remove",
                i18n.t("Remove “%s” from the tree?\n\n%d playlist file(s) are listed under "
                       "it — they stay on disk, only this entry goes.") % (node['name'], held),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        if self._remove_from(self._nodes, node):
            self._save()
            self._rebuild()

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if item is not None:
            # The row right-clicked is what it acts on — all the marked ones
            # when it is among them.
            if not item.isSelected():
                self._tree.setCurrentItem(item)
            self._board.select("")
        menu = QMenu(self._tree)
        folder_act = menu.addAction("📁  New folder…")
        add_act = menu.addAction("＋  Add playlists…")
        add_dir_act = menu.addAction("📂  Add a folder of playlists…")
        menu.addSeparator()
        rename_act = menu.addAction("✎  Rename…")
        remove_act = menu.addAction("🗑  Remove from tree")
        rename_act.setEnabled(item is not None)
        remove_act.setEnabled(item is not None)
        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen is folder_act:
            self._add_folder()
        elif chosen is add_act:
            self._add_playlists()
        elif chosen is add_dir_act:
            self._add_playlist_folder()
        elif chosen is rename_act:
            self._rename()
        elif chosen is remove_act:
            self._remove()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.SelectAll):
            if not self._select_all_slots():
                self._tree.selectAll()
            return
        if event.key() == Qt.Key.Key_F2:
            self._rename()
            return
        if event.key() == Qt.Key.Key_Delete:
            self._remove()
            return
        super().keyPressEvent(event)
