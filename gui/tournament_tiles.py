"""🏆 The tournament pane's parts: the folder tree, a playlist's slot tile and
the board the tiles sit on.

Split off gui/tournament_tree.py, which keeps the pane (TournamentTree) and
the tree's model.
"""
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDrag, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QScrollArea,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from shared.widgets import FlowLayout

# Where a tree item sits in the node list, as "0/2/1". NOT the node dict
# itself: PySide6 marshals a dict through QVariant as a C++ QVariantMap and
# hands back a COPY, so edits would never reach the model and `is` comparisons
# would all miss. An index path is a string, which survives the round trip.
ROLE_KEY = Qt.ItemDataRole.UserRole
# One slot. Wide enough for "Turnier 3 Sen I S" and two rows of them fit the
# strip the pane gets at the bottom of the window.
_SLOT_W, _SLOT_H = 200, 62
# Section tints, by which dances a playlist turns out to hold.
_SLOT_TINTS = {"Standard": "#3b6ea5", "Latin": "#b5533c", "": "#9aa3ad"}


class TourneyTree(QTreeWidget):
    """The tree itself: .m3u files dropped in from Explorer become leaves,
    and a leaf dragged out is that .m3u file — so it lands on a deck exactly
    as it would coming from Explorer."""

    filesDropped = Signal(object, object)   # (target item | None, [Path, …])

    node_of: Callable[[object], dict | None] | None = None  # set by TournamentTree: item key → node dict
    # set by TournamentTree: Ctrl+A → True when it marked something else instead
    select_all_cb: Callable[[], bool] | None = None

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
            node = (self.node_of(item.data(0, ROLE_KEY)) if self.node_of else None) or {}
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


class SlotBoard(QScrollArea):
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
            w = item.widget() if item is not None else None
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
