"""The playlist grid widget (drag & drop, play toggle, per-row regen).

Extracted from dancesport_gui.py (view split): PlaylistTable is the editable
song grid used by every deck and the wishlist. Shared GUI primitives come from
gui.dialogs / gui.workers; planner data types from dancesport_planner.
"""
import html
import logging

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
    QUrl,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPalette,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
)
from pathlib import Path
from collections.abc import Callable
from planner.db import AudioCache
from planner.m3u import running_order_rounds
from planner.models import ALLOW_REPEAT, MusicEntry, RoundConfig
from planner import terms
from planner.terms import dance_name
from planner.suggester import PlaylistSuggester
from planner.warmup import warmup_code, warmup_rounds
from planner.checks import FLAG_EDGE_SILENCE, is_final_round
from planner.warmup import warmup_swap_partner
from planner.parsing import _fmt_bpm
from planner import i18n
from gui.common import (
    CUSTOM_HEADER_TIP,
    DANCE_SHORT,
    _C_DANCE_BG,
    _C_DANCE_FG,
    _C_DEFAULT,
    _C_NEW_FG,
    _C_POP_FG,
    _C_ROUND_BG,
    _C_ROUND_FG,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _C_SIM_FG,
    _C_LEN_WARN_FG,
    _C_WARN_FG,
    _entry_tooltip,
    _fmt_track_secs,
    _open_in_default_player,
    add_custom_mapping_action,
    stopwatch_header,
)
from shared.columns import (
    _COL_ARTIST,
    _COL_BPM,
    _COL_CLASS,
    _COL_CUSTOM,
    _COL_DANCE,
    _COL_HEAT,
    _COL_LEN,
    _COL_PLAY,
    _COL_POP,
    _COL_RATING,
    _COL_REGEN,
    _COL_TITLE,
    _N_COLS,
)
from shared.widgets import (
    _show_toast,
    set_play_glyph,
)
from gui.running_order import Row, RunningOrder
from gui.star_rating import RATING_ROLE, StarDelegate
from gui.table_dnd import TableDragDropMixin
from gui.table_dynamic import DynamicModeMixin
from gui.table_actions import TableActionsMixin
from gui.table_host import TableHost
from gui import table_dnd
from gui import table_dynamic
from gui import table_actions

log = logging.getLogger("dancesport.gui.playlist_table")


# "Marked for potential replace" (dynamic decks): a light-orange row underlay plus
# an orange ❗ in the last column — the same style as a missing file's red ❗, but
# orange so a deliberately-marked song stays distinct from a genuinely missing one.
_C_MARK_BG = QColor(255, 224, 178)
_C_MARK_FG = QColor(216, 96, 24)

# Live Check-Music mark: a row whose track (play length / takt) or round
# (heat-tempo spread) has an issue stays RED until the issue is resolved.
_C_ISSUE_BG = QColor(255, 183, 183)

# How long the auto-play scroll takes to glide to the new row: long enough to
# read as a movement, short enough that the list is settled before the operator
# looks back at it.
_SCROLL_MS = 260


class _MarkSelectionDelegate(QStyledItemDelegate):
    """Selecting a marked song highlights the row in ORANGE — the same full-row,
    opaque selection the rest of the grid draws in blue, just recoloured. We swap the
    palette's Highlight brush to orange for marked + selected cells and let the normal
    style paint it, so every column of the row is covered (not a single cell)."""

    _SEL = QColor(232, 126, 14)   # orange counterpart of the default blue selection

    def __init__(self, table: PlaylistTable):
        super().__init__(table)
        self._table = table

    def paint(self, painter, option, index):
        if (option.state & QStyle.StateFlag.State_Selected
                and self._table._is_row_marked(index.row())):
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            opt.palette.setColor(QPalette.ColorRole.Highlight, self._SEL)
            super().paint(painter, opt, index)
        else:
            super().paint(painter, option, index)


class _NumberHeader(QHeaderView):
    """The Nb. column of the 🔢 Numbers view, drawn as the table's vertical
    header: every title carries its place in the list, header and empty rows
    stay blank. The text is asked for at paint time, so a swap, drop or removal
    renumbers without anyone having to tell the header.

    Painted flat, like an editor's line-number gutter: Fusion would draw every
    row as a raised grey button and bold the current one."""

    _BG = QColor(243, 245, 249)
    _FG = QColor(120, 128, 140)
    _LINE = QColor(214, 219, 228)

    def __init__(self, table: PlaylistTable):
        super().__init__(Qt.Orientation.Vertical, table)
        self._table = table

    def paintSection(self, painter, rect, logical_index):
        if not rect.isValid():
            return
        painter.save()
        painter.fillRect(rect, self._BG)
        painter.setPen(self._LINE)
        painter.drawLine(rect.topRight(), rect.bottomRight())
        text = self._table.song_number_label(logical_index)
        if text:
            painter.setPen(self._FG)
            painter.drawText(rect.adjusted(0, 0, -7, 0),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             text)
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# Playlist Table
# ─────────────────────────────────────────────────────────────────────────────
class PlaylistTable(TableDragDropMixin, DynamicModeMixin,
                    TableActionsMixin, QTableWidget):
    """Shows the suggested playlist; supports drag-and-drop (file URIs)."""

    focused      = Signal(object)   # emitted (self) when this table gains focus
    playRequested = Signal(object)  # emitted (self) right before this deck starts playing
    saveRequested = Signal(object)  # emitted (self) when "Save as M3U…" is chosen
    saveToTournamentsRequested = Signal(object)  # … "Save and add to Tournaments…"
    cleared       = Signal(object)  # emitted (self) when DEL on the header wipes the deck
    loaded        = Signal(object)  # emitted (self) when a whole playlist lands in this table
    dynamicChanged = Signal(object) # emitted (self) when the deck flips static⇄dynamic

    def __init__(self, parent=None):
        super().__init__(0, _N_COLS, parent)
        # The glide of the auto-play scroll, built on first use and reused after.
        self._scroll_anim = None
        # The .m3u this list was loaded from or last saved to (📂 Show in Explorer
        # on the header, 🖼 the playlist's own cover); None = never a file.
        self._m3u_path = None
        # Flat scratch list (the Wishlist) instead of a rounds/heats grid: drops
        # append a row instead of replacing a slot.
        self._flat_mode = False
        # Dynamic mode: drops BUILD the rounds/heats grid (vs static decks generated
        # from the combos, where a drop just replaces one slot). Per-deck — deck 1 can
        # stay static while deck 2 is dynamic.
        self._dynamic = False
        self._dynamic_capacity: list[int] = []   # heats/round pattern, e.g. [6,3,2,1]
        self._dynamic_dances: list[str] = []     # column order (first-placed first)
        # Final-round backups stacked under a slot: (round_name, h_idx, d_idx) → entries.
        self._dynamic_backups: dict[tuple[str, int, int], list[MusicEntry]] = {}
        # Dances explicitly removed from a single round (round_name → {dance codes}); that
        # round skips rendering them even though the deck still has the column elsewhere.
        self._round_skip_dances: dict[str, set] = {}
        # Stacked 📅 day-plan deck: round_name → {"comp", "cls", "style"} so each
        # round keeps its own competition's class/style for ↺ and export split.
        self._round_ctx: dict[str, dict] = {}
        # Compact view: skip the per-dance header rows (the Dance column already names
        # each row's dance), so a round lists its songs straight under its header.
        self._compact = False
        # No grouping at all: on top of the dance headers, drop the round / ─── section
        # headers too, so the list is one flat run of songs (party playlists mostly).
        self._nogroup = False
        # 🔢 Numbers view: the Nb. column (vertical header) counts the titles.
        self._numbered = False
        # Warm-up ("Eintanzen") list: a flat, own-category list whose rows carry a
        # 'warmup' tag so ↺ re-rolls a timbre-matched, TSO-conform track of the same
        # dance and a drop can replace a slot (set by load_warmup).
        self._warmup       = False
        self._warmup_style = ""
        self._warmup_class = ""
        self._warmup_relax = True
        self._warmup_label = ""
        # Player-only install: this deck holds the flat running order of the
        # evening (set by load_player_list). It rides on the warm-up list's
        # machinery — free reorder, a drop lands where it was dropped — and its
        # ─── strips head the rounds it plays out (path → round name below), or
        # each run of a dance when no round could be derived.
        self._player_list = False
        self._player_sections: dict[str, str] = {}
        # Set by MainWindow on decks: returns the current "6-3-2-1" Rounds-field pattern,
        # used as the capacity when an empty deck turns dynamic on its first drop.
        self._capacity_provider: Callable[[], list[int]] | None = None
        self._row_meta = RunningOrder()
        self._playlist: dict | None       = None
        self._suggester: PlaylistSuggester | None = None
        self._cache: AudioCache | None = None   # set by MainWindow for chained drops
        self._dance_class    = "C"
        self._style          = "Latin"
        self._play_cb        = None
        self._seek_cb        = None   # set by MainWindow: fn(delta_ms) seeks the player
        # Set by MainWindow: fn() → configured play length in s; tracks shorter than
        # this get an orange ⏱ cell. None/0 → no flagging.
        self._short_secs_cb: Callable[[], int] | None = None
        # Set by MainWindow: fn(entry) → seconds the track will really PLAY once
        # the 🔇 stillness skip has cut the dead air off its edges, or None when
        # the track was never probed. Reported in the cell's tooltip whenever it
        # differs from the file's length, flagged or not.
        self._play_secs_cb: Callable[[MusicEntry], int | None] | None = None
        # Longest single edge of stillness, in seconds — what decides the amber ⏱
        # (see planner.checks.FLAG_EDGE_SILENCE).
        self._edge_silence_cb: Callable[[MusicEntry], float] | None = None
        # The play cursor: the id of the placement that plays (Row.uid), and
        # the row it was last found on. See _current_play_row.
        self._play_uid: int | None = None
        self._play_hint = -1
        # True only while `loaded` fires after a load() that took the playing
        # title out of this deck: the desk still has to know the music came
        # from here, though the marker is gone (see _stop_if_playing_from).
        self._play_dropped = False
        self._use_timbre: bool = True
        self._round_pools_by_name: dict[str, list[MusicEntry]] = {}
        # Last load() arguments, kept so the table can re-render itself (e.g. after
        # a dance-header drag reorders the dance columns of a STATIC deck).
        self._loaded_dances: list[str] = []
        self._loaded_rounds: list[RoundConfig] = []
        self._drag_src_rows: list[int] = []   # song rows of an in-flight internal drag
        self._dance_drag: str | None = None   # dance code of an in-flight header drag
        self._hdr_press: tuple[int, QPoint] | None = None   # pressed dance header (row, pos)
        # Notified (by MainWindow) after every grid edit so the working playlist can
        # be autosaved. Set via set_change_callback(); fired through _notify_changed().
        self._change_cb: Callable[[], None] | None = None

        # Edge auto-scroll while a drag is held near the top/bottom of the viewport.
        self._autoscroll_dir = 0
        self._autoscroll_speed = self._AUTOSCROLL_MIN_PX
        self._autoscroll_timer = QTimer(self)
        self._autoscroll_timer.setInterval(40)
        self._autoscroll_timer.timeout.connect(self._drag_autoscroll)

        # Red drop-indicator line (UltraMixer-style) painted between rows while a
        # Wishlist drag hovers, marking the exact insert position. It's a child of
        # the viewport so it draws over the rows; hidden whenever no drag is active.
        self._drop_line = QFrame(self.viewport())
        self._drop_line.setFrameShape(QFrame.Shape.HLine)
        self._drop_line.setStyleSheet("background:#e53935; border:none;")
        self._drop_line.setFixedHeight(1)
        self._drop_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._drop_line.hide()
        # Deck (rounds/heats grid) drops REPLACE one slot, so instead of a gap line
        # we highlight the whole target row the track would land on.
        self._drop_row_hl = QFrame(self.viewport())
        self._drop_row_hl.setStyleSheet(
            "background:rgba(229,57,53,45); border:2px solid #e53935;")
        self._drop_row_hl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._drop_row_hl.hide()
        # Playing-mode marker: a blue twin of the red replace-highlight that
        # sits on the row currently playing (enabled by MainWindow per mode).
        self._play_row_hl = QFrame(self.viewport())
        self._play_row_hl.setStyleSheet(
            "background:rgba(21,101,192,40); border:2px solid #1565c0;")
        self._play_row_hl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._play_row_hl.hide()
        self._play_hl_enabled = False
        # ⏭/✋ auto-advance switch: the difference between a round running by
        # itself and every title started by hand, and it gets flipped between
        # heats — so it sits on every deck instead of only on the play panel.
        # The SETTING is MainWindow's; this button only reads and flips it,
        # which is why all decks show the same state.
        #
        # It is built here but laid out by the deck box, which puts it in the
        # same bar as the Σ song counter (`advance_toggle()`). It floated in the
        # viewport's corner before, and there it lay ON the playlist: covering
        # the bottom rows, and parked across the middle of the list as soon as
        # the rows scrolled under it.
        self._advance_get: Callable[[], bool] | None = None
        self._advance_set: Callable[[bool], None] | None = None
        # This list's OWN play values (`play_set()`'s keys plus `tso`), None
        # until the window first gives it some — see `_list_vals` there. One
        # player, several lists: the party list runs full length and
        # hands-free while the round beside it cuts at 1:30.
        self._play_vals: dict | None = None
        # Whether the switch is wanted — asked instead of the button's own
        # isVisible(), which is False for as long as the WINDOW is unmapped and
        # would leave a deck wired during start-up with no caption at all.
        self._advance_on = False
        # Whether this is the list a title was last started from — the one
        # whose switch decides what follows. Every deck has a switch, and
        # flipping the one beside it changed nothing on the floor.
        self._advance_live = False
        # Parented to the table until a bar adopts it: a parentless QPushButton
        # is a top-level window and would flash up as one.
        self._advance_btn = QPushButton("", self)
        self._advance_btn.setObjectName("AdvanceCorner")
        self._advance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # The decks keep the keyboard: Space plays, Ctrl+←/→ seeks.
        self._advance_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Sized and coloured like the Σ badge it stands next to, so the two
        # read as one bar rather than a badge with a button dropped beside it.
        self._advance_btn.setStyleSheet(
            "#AdvanceCorner { background:#eef3fb; color:#2c4a73;"
            " border:1px solid #c9d6ea; border-radius:4px;"
            " padding:2px 8px; font-size:11px; font-weight:bold; }"
            "#AdvanceCorner:hover { background:#d6e6fa; }"
            "#AdvanceCorner[live=\"true\"] { background:#c6daf5; color:#1f3a5f;"
            " border-color:#7a9ccc; }"
            "#AdvanceCorner[live=\"true\"]:hover { background:#b5cef0; }")
        self._advance_btn.clicked.connect(self._on_advance_clicked)
        self._advance_btn.hide()
        self.verticalScrollBar().valueChanged.connect(
            lambda _: self._update_play_row_hl())
        # Tracks already played this session (playing mode greys them out).
        self._played_paths: set = set()
        self._played_saved: dict[tuple[int, int], QBrush] = {}
        # Songs the user flagged "for potential replace" (dynamic decks), keyed by file
        # path so the orange mark survives structural re-renders. Persisted per deck
        # in the autosave/undo snapshot ("marked" key of _serialize_playlist_state).
        self._marked_paths: set = set()
        # Live Check-Music marks: path → issue text, recomputed after every grid
        # edit (refresh_issue_marks); keyed by path so red survives re-renders.
        self._issue_paths: dict[str, str] = {}
        # ↩ Resume marks: path → position in ms where the title was left. Session
        # only (the player owns the dict), keyed by path so the badge survives
        # re-renders. Only marked titles get one.
        self._resume_marks: dict[str, int] = {}
        # Custom delegate so a marked row's orange shows through the selection colour.
        self.setItemDelegate(_MarkSelectionDelegate(self))

        # Collapsible headers: maps a managed row → its round / dance header row, so a
        # collapsed header hides all rows beneath it. Rebuilt on every load().
        self._row_round_hdr: dict[int, int] = {}
        self._row_dance_hdr: dict[int, int] = {}
        self._round_hdr_rows: set = set()
        self._dance_hdr_rows: set = set()
        self._dance_hdr_dance: dict[int, str] = {}   # dance header row → dance code
        self._row_round_name: dict[int, str] = {}    # header row → its round name
        self._collapsed: set = set()
        self._hdr_base_text: dict[int, str] = {}

        self.setHorizontalHeaderLabels(
            ["Dance", "Heat", "▶", "Artist", "Title", "BPM", "⏱", "Pop", "Class", "★",
             "Custom", "↺"]
        )
        stopwatch_header(self, _COL_LEN)
        self.horizontalHeaderItem(_COL_LEN).setToolTip(
            "Track length (m:ss)\n"
            "orange = shorter than the configured play length, or 5 s or more\n"
            "of stillness at an edge that the player skips (the cell's own\n"
            "tooltip says which, and how long it really plays)"
        )
        self.horizontalHeaderItem(_COL_CLASS).setToolTip(
            "≈  timbral similarity to round anchor\n"
            "    (only shown after running Audio Analysis)\n"
            "[D,C,…]  class tags from MP3 COMM field"
        )
        self.horizontalHeaderItem(_COL_RATING).setToolTip(
            "Rating — click a star to set it, the last lit one again to clear it.\n"
            "Kept in the app's database; the MP3 itself is not changed."
        )
        self.setItemDelegateForColumn(_COL_RATING, StarDelegate(self._on_star_clicked, self))
        self.horizontalHeaderItem(_COL_CUSTOM).setToolTip(CUSTOM_HEADER_TIP)
        # `cb(entry, stars)` — the window stores the rating (see set_rating_callback).
        self._rating_cb: Callable | None = None
        # Which kind of list this table is — "playlist" (a deck), "wishlist" or
        # "party" (the Eintanzen panel). Set by the window that builds them; the
        # column ticks are remembered per kind, not per table.
        self.list_kind = "playlist"
        self._columns_cb: Callable[[str, list], None] | None = None
        self._widths_cb: Callable[[str, dict], None] | None = None
        self._dance_cb: Callable[[str, bool], None] | None = None
        self._short_dances = False             # Dance column: "LW", not "Langsamer Walzer"
        self._col_width: dict[int, int] = {}   # width a column had when it was hidden
        self._filling = False                  # guard: our own resizes are not the user's
        # A drag arrives a pixel at a time — save it once, when it comes to rest.
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.setInterval(400)
        self._width_timer.timeout.connect(self._notify_widths)

        hh = self.horizontalHeader()
        # Every column is user-resizable (drag the handles) — Interactive throughout
        # with seeded default widths, exactly like the library browser. Title was the
        # one exception, on Stretch so it soaked up the leftover width; Qt does not
        # let a stretched section be dragged, so its handle was the one that did
        # nothing. It is Interactive like the rest now and `_fill_title_column` does
        # the soaking up — on a table resize, and when a neighbour is dragged.
        hh.setMinimumSectionSize(24)
        for c in range(_N_COLS):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        for c, w in ((_COL_DANCE, 80), (_COL_HEAT, 56), (_COL_PLAY, 30),
                     (_COL_ARTIST, 150), (_COL_BPM, 52), (_COL_LEN, 48),
                     (_COL_POP, 50), (_COL_CLASS, 60), (_COL_RATING, 72),
                     (_COL_CUSTOM, 90), (_COL_REGEN, 30)):
            self.setColumnWidth(c, w)
        hh.sectionResized.connect(self._on_section_resized)
        # Right-click the header → tick the columns this KIND of list shows.
        hh.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hh.customContextMenuRequested.connect(self._show_column_menu)

        self.setVerticalHeader(_NumberHeader(self))
        self.verticalHeader().setVisible(False)
        # The Nb. column's caption, laid over the corner button above it.
        self._nb_label = QLabel("Nb.", self)
        self._nb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Same face as the column captions beside it.
        self._nb_label.setFont(self.horizontalHeader().font())
        self._nb_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._nb_label.hide()
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setDragEnabled(True)
        # DragDrop (not DragOnly): rows still drag OUT to VLC/Explorer, and tracks
        # dragged from the Similar-Tracks window can be dropped ONTO a row to replace it.
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        # Pixel (not per-item) scrolling so the edge auto-scroll during a drag can
        # move in small, fine-grained steps near the boundary instead of jumping a
        # whole row per tick — lets the user ease onto the exact drop point.
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        # Disable Qt's built-in drag auto-scroll: it ran ALONGSIDE our own
        # proportional one (below), doubling the speed near the edge and making the
        # drop point hard to hit. Our _drag_autoscroll is now the only one, so the
        # behaviour is identical and controllable across every deck / wishlist /
        # warm-up list (all PlaylistTable).
        self.setAutoScroll(False)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # Double-click a row → play it (Playing mode) or open the file in the
        # system's default music player. Handled in mouseDoubleClickEvent, NOT
        # via cellDoubleClicked — see there.
        # Single-click a round / dance header → collapse or expand it.
        self.cellClicked.connect(self._on_header_click)
        # Double-click a column header → sort by that column: the Wishlist and a
        # deck in ✋ free order, which are lists. A rounds/heats grid ignores it —
        # its rows ARE the running order. Doing it again flips the direction.
        # Double, not single: a header takes single clicks for resizing and for
        # dragging a column, and a list that reorders itself under a stray click
        # is a list you have to undo.
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().sectionDoubleClicked.connect(
            self._on_header_section_double_clicked)
        self._flat_sort_col = -1
        self._flat_sort_desc = False

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused.emit(self)

    @property
    def host(self) -> TableHost:
        """The window around this table: everything the table asks of it."""
        return TableHost(self)

    def player_only(self) -> bool:
        """True where this install runs the music but never plans it (⚙ app mode
        'player'). A deck there has no static/dynamic choice to make — the toggle
        is hidden and every drop ADDS the title to the list, the way any media
        player behaves."""
        return self.host.player_only()

    def pauses_on_stop(self) -> bool:
        """True at the desk: there the row's button PAUSES the running title
        instead of unloading it. Playing mode has the big player's ⏯ right next
        to the grid, the track keeps its position, and a resume is instant — the
        two buttons must mean the same thing. A planning-mode preview is
        throw-away, so it keeps the plain stop that frees the file."""
        return bool(self._play_hl_enabled and self.host.has_big_player())

    @property
    def _current_play_row(self) -> int:
        """The row the playing title sits on, or -1.

        Looked up from the play cursor — the id of the playing placement — so
        an edit that moves rows moves the marker with them: a swap carries the
        id along with its track, a re-render hands it back (RunningOrder.adopt),
        and a removal above just renumbers. Nothing writes a new row number back."""
        if self._play_uid is None:
            return -1
        m = self._row_meta.at(self._play_hint)
        if m is None or m.uid != self._play_uid:
            self._play_hint = self._row_meta.row_of(self._play_uid)
        return self._play_hint

    @_current_play_row.setter
    def _current_play_row(self, row: int):
        m = self._row_meta.at(row)
        self._play_uid = m.uid if m is not None else None
        self._play_hint = row if m is not None else -1

    def _follow_play_row(self):
        """After the rows were rebuilt and their ids handed back: the ■ goes on
        the row the playing title landed on, or the cursor lets go of a title
        that is no longer in the list."""
        if self._current_play_row >= 0:
            self.sync_play_glyph()
        else:
            self._play_uid = None

    def sync_play_glyph(self, playing: bool | None = None):
        """Keep the running row's ■/▶ in step with the player: ■ while the music
        runs, ▶ once it is paused — the grid keeps the two characters it always
        had. `playing=None` asks the window for the live state, which is the path
        every re-render takes. A planning preview has no pause, so its running
        row stays ■ — unless the title is only cued (loaded, never started),
        which shows ▶ like any title that is not playing."""
        row = self._current_play_row
        if row < 0:
            return
        w = self.cellWidget(row, _COL_PLAY)
        if not isinstance(w, QPushButton):
            return
        if not self.pauses_on_stop():
            set_play_glyph(w, playing is not None or not self._player_stopped())
            return
        if playing is None:
            playing = self.host.is_player_running()
        set_play_glyph(w, playing)

    def _player_stopped(self) -> bool:
        """The window's player stands fully stopped — a cued title, not a
        paused one."""
        return self.host.is_player_stopped()

    def mouseDoubleClickEvent(self, event):
        """Route a double-click by the row under the CURSOR, not by Qt's
        cellDoubleClicked signal.

        Qt emits that signal only when the second press lands on the very index
        the first press stored — anything that moves the rows in between (the
        grid scrolling itself, a deck header re-laying out on focus, an internal
        drag starting) makes the whole double-click vanish without a trace. At
        the desk that reads as "double-click is broken", and a title that will
        not start is the one thing playing mode may not do."""
        super().mouseDoubleClickEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if col == _COL_RATING:
            return          # two quick ★ clicks, not "play this title"
        if row >= 0:
            self._on_row_double_clicked(row, col)

    def set_change_callback(self, cb: Callable[[], None] | None):
        """Register a callback fired after every grid edit (for autosave)."""
        self._change_cb = cb

    def _notify_changed(self):
        if self._change_cb is not None:
            try:
                self._change_cb()
            except Exception as exc:
                log.warning("💾 Change callback failed — autosave may be stale: %s", exc)
        # Live Check-Music marks follow every grid edit: a red row clears the
        # moment its issue is resolved (track replaced, spread evened out, …).
        try:
            self.refresh_issue_marks()
        except Exception:
            logging.exception("⚠ issue-mark refresh failed")

    def _compute_issue_marks(self, probe_rows=()) -> dict[int, list[str]]:
        """Instant Check-Music over the whole grid: per-track problems (⚡ tempo,
        🐢/🐇 TSO takt, ⏱ play length — via the window's _track_issues) plus the
        heat-tempo evenness of every (round, dance) column. Returns {row: [msg]};
        ffmpeg silence probing only for `probe_rows` (freshly dropped files)."""
        host = self.host
        if self._playlist is None or not host.can_check_tracks():
            return {}
        out: dict[int, list[str]] = {}
        cols: dict[tuple, list] = {}   # (round_name, d_idx) → [(row, takt)]
        for r, m in self._row_meta.numbered():
            e = m.entry
            if m.theme or m.backup or not m.round_name:
                continue
            try:
                trk = host.track_issues(
                    e, probe_silence=(r in probe_rows),
                    in_final=is_final_round(m.round_name, m.tier))
            except Exception:
                trk = []
            if trk:
                out[r] = [i18n.t("“%s” — %s") % (e.title, '; '.join(trk))]
            takt = host.entry_takt(e)
            if takt:
                cols.setdefault((m.round_name, m.d_idx), []).append((r, takt))
        for (rname, _d), pairs in cols.items():
            vals = [t for _, t in pairs]
            if len(vals) >= 2 and max(vals) - min(vals) > 1:
                dance = self._row_meta[pairs[0][0]].dance
                msg = (i18n.t("🧩 “%s” %s heats differ by %d takte (allowed: 1)")
                       % (rname, dance_name(dance, dance), max(vals) - min(vals)))
                for r, _ in pairs:
                    out.setdefault(r, []).append(msg)
        return out

    def refresh_issue_marks(self, probe_rows=()) -> dict[int, list[str]]:
        """Re-evaluate the live Check-Music marks and repaint the rows whose
        state changed: offenders turn RED (kept until resolved), resolved rows
        get their normal striping back. Returns {row: [messages]} for toasts."""
        issues = self._compute_issue_marks(probe_rows)
        new: dict[str, str] = {}
        for r, msgs in issues.items():
            p = self._row_meta[r].path_str
            if p:
                new[p] = "\n".join(msgs)
        old = self._issue_paths
        if new != old:
            self._issue_paths = new
            for r, m in self._row_meta.numbered():
                p = m.path_str
                if not p or m.theme:
                    continue
                if old.get(p) != new.get(p):
                    bg = _C_ROW_EVEN if (m.h_idx or 0) % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, m, bg)
                    if r == self._current_play_row:
                        self.sync_play_glyph()   # a fresh fill says ▶
        return issues

    def set_resume_marks(self, marks: dict[str, int]) -> None:
        """Show “↩ m:ss” on every row whose title carries a resume mark, and drop
        the badge from the rows that lost theirs. `marks` is the player's whole
        session dict (path → ms), so this is safe to call on every deck."""
        marks = {str(k): int(v) for k, v in (marks or {}).items()}
        old = self._resume_marks
        if marks == old:
            return
        self._resume_marks = marks
        for r, m in self._row_meta.numbered():
            p = m.path_str
            if not p or m.theme:
                continue
            if old.get(p) != marks.get(p):
                bg = _C_ROW_EVEN if (m.h_idx or 0) % 2 == 0 else _C_ROW_ODD
                self._fill_song_row(r, m, bg)
                if r == self._current_play_row:
                    self.sync_play_glyph()   # a fresh fill says ▶

    def refresh_paths(self, paths) -> int:
        """Repaint every row showing one of `paths`, and say how many that was.

        For the case the table can't see coming: the MusicEntry behind a row
        changed underneath it (a 🏷 tag re-read), while the row itself did not.
        Cheap enough to call on every deck."""
        wanted = {str(p) for p in paths}
        if not wanted:
            return 0
        done = 0
        for r, m in self._row_meta.numbered():
            p = m.path_str
            if not p or m.theme or p not in wanted:
                continue
            bg = _C_ROW_EVEN if (m.h_idx or 0) % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(r, m, bg)
            if r == self._current_play_row:
                self.sync_play_glyph()   # a fresh fill says ▶
            done += 1
        return done

    def flash_rows(self, rows: list[int],
                   color: QColor = QColor(255, 236, 160), msec: int = 2400):
        """Briefly tint the given rows (then restore their exact backgrounds) so the
        user can SEE which songs an undo/redo just changed. Captures each cell's
        current brush and restores it, so it works for any row type."""
        rows = [r for r in rows if 0 <= r < self.rowCount()]
        if not rows:
            return
        saved = {}
        for r in rows:
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it is not None:
                    saved[(r, c)] = it.background()
                    it.setBackground(color)
        first = self.item(rows[0], 0)
        if first is not None:
            self.scrollToItem(first, QAbstractItemView.ScrollHint.PositionAtCenter)

        def _restore():
            for (r, c), brush in saved.items():
                it = self.item(r, c)
                if it is not None:
                    it.setBackground(brush)
        # The table as context: a deck closed before the restore takes the timer with it.
        QTimer.singleShot(msec, self, _restore)

    # ── Double-click → play (playing mode) / open the file (planning mode) ─────
    def dblclick_plays(self) -> bool:
        """True where a double-click STARTS the title, False where it only cues
        it on the player — the ▶️ box on the Playing panel, part of the play
        sets: 🏆 tournament cues (the heat starts on ⏯, when the couples
        stand), 🎉 party plays. Default: it cues. It is this list's own."""
        vals = self.host.list_vals()
        if vals is not None:
            return bool(vals["dblclick"])
        return bool(self.host.settings().get("dblclick_plays", False))

    def _on_row_double_clicked(self, row: int, _col: int):
        """Playing mode PLAYS the row (or cues it — see `dblclick_plays`);
        planning mode opens the file externally, and an EMPTY slot opens 📚 the
        library on the dance that belongs in it.

        At the desk a double-click on a title has to put it on the speakers —
        handing the file to whatever the OS calls a music player, mid-tournament,
        is the one thing it must not do. While planning, opening the file is the
        point: that is how you audition a track you are unsure about.

        A row that is already playing is left alone rather than toggled off. The
        ■ button is right there, and silence in the middle of a heat is not
        something a stray double-click should be able to cause.
        """
        if not (0 <= row < len(self._row_meta) and self._row_meta[row]):
            return
        meta = self._row_meta[row]
        entry = meta.entry
        if not (entry and entry.path):
            self._browse_for_empty_slot(meta)
            return
        if not self._play_hl_enabled:
            _open_in_default_player(Path(entry.path), self)
            return
        if row == self._current_play_row:
            return          # never touch the title that is on the speakers
        if self.dblclick_plays():
            self._on_play_click(row, entry.path)
            return
        # Cue only: the same route a drop onto the player card takes — load it,
        # show it, leave it silent, and point the playing-row marker here so ⏭
        # walks on from this title.
        self.host.cue(str(entry.path))

    def _browse_for_empty_slot(self, meta):
        """Double-click on an unfilled grid slot → 📚 the library, filtered to the
        dance and class that slot is waiting for.

        The same jump 📊 the gap dashboard makes, taken from the deck side: the
        hole is right there on the screen, so the shortest way to fill it by hand
        is to be shown what could go in it. Playing mode has no holes to fill and
        keeps the double-click to itself.
        """
        if self._play_hl_enabled or not meta.dance:
            return
        self.host.show_library_filtered(dance=meta.dance, cls=self._dance_class)

    # ── Load playlist data ────────────────────────────────────────────────────

    def load(
        self,
        playlist: dict,
        dances: list[str],
        rounds: list[RoundConfig],
        dance_class: str,
        play_cb,
        suggester: PlaylistSuggester,
        use_timbre: bool = True,
        style: str = "Latin",
        round_pools: list[list[MusicEntry]] | None = None,
        dynamic: bool = False,
        capacity: list[int] | None = None,
        backups: dict | None = None,
        round_skip_dances: dict | None = None,
        round_ctx: dict | None = None,
        marked: set | None = None,
    ):
        self._playlist    = playlist
        self._warmup      = False
        self._player_list = False
        # 🖼 A fresh load is not the imported .m3u any more — the importer sets
        # this again right after, so the deck's cover follows what it holds.
        self._m3u_path    = None
        self._dance_class = dance_class
        self._play_cb     = play_cb
        self._suggester   = suggester
        self._use_timbre  = use_timbre
        self._style       = style
        self._loaded_dances = list(dances)
        self._loaded_rounds = list(rounds)
        # The rows are rebuilt below — keep the placements, to hand the ids back.
        placed = self._row_meta.placements()
        playing = self._current_play_row >= 0
        self._row_meta    = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        # Dynamic-mode state: a static (combo-generated) load resets it; a dynamic
        # load / rebuild carries the pattern, column order and stacked backups.
        self._dynamic          = dynamic
        self._dynamic_capacity = list(capacity) if capacity else ([] if not dynamic else self._dynamic_capacity)
        self._dynamic_dances   = list(dances) if dynamic else []
        self._dynamic_backups  = backups or {}
        self._round_skip_dances = ({k: set(v) for k, v in round_skip_dances.items()}
                                   if round_skip_dances else {})
        self._round_ctx = ({k: dict(v) for k, v in round_ctx.items()}
                           if round_ctx else {})
        # 🔁 "potential replace" marks: a fresh (generated / imported) load starts
        # clean — otherwise a re-picked song would come back already orange. Only a
        # restore hands its saved set in, so the rows below are painted marked.
        self._marked_paths = set(marked) if marked else set()
        # 'Past competitions': per-round history pool keyed by round name, so a row
        # ↺ re-rolls from the same round's history first (library as fallback).
        self._round_pools_by_name = {}
        if round_pools:
            for rc, pool in zip(rounds, round_pools):
                self._round_pools_by_name[rc.name] = pool
        self._reset_collapse_state()
        self.setRowCount(0)

        rc_map = {rc.name: rc for rc in rounds}

        for round_name, heats in playlist.items():
            rc    = rc_map.get(round_name)
            tier  = rc.tier if rc else "early"
            total = sum(1 for h in heats for e in h if e is not None)
            multi = len(heats) > 1

            # ── Round header (spans all columns) ──
            # Total play time of the round; "~" because tracks without a probed
            # duration count as 0 (and timed fade-out may cut songs early anyway).
            round_secs = sum(getattr(e, "duration", 0) or 0
                             for h in heats for e in h if e is not None)
            time_s = f",  ~{_fmt_track_secs(round_secs)}" if round_secs else ""
            heat_s = "heat" if len(heats) == 1 else "heats"
            if self._nogroup:
                round_hdr = -1   # no grouping: the songs stand on their own
            else:
                round_hdr = self._add_span_row(
                    f"  ═══  {terms.round_name(round_name).upper()}   "
                    f"({len(heats)} {heat_s},  {total} songs{time_s})  ═══",
                    _C_ROUND_BG, _C_ROUND_FG, bold=True, collapsible=True,
                    regen_cb=(lambda rn=round_name: self._regen_round(rn)),
                    regen_tip="Regenerate every dance in this round",
                )
                self._round_hdr_rows.add(round_hdr)
                self._row_round_name[round_hdr] = round_name

            for d_idx, dance in enumerate(dances):
                # A dance explicitly removed from THIS round is not rendered (its slots
                # stay None in the data, d_idx stays aligned for the other rounds).
                if dance in self._round_skip_dances.get(round_name, ()):
                    continue
                dn = dance_name(dance, dance)

                # ── Dance header (with a per-dance ↺ that re-rolls every heat
                #    of THIS dance in THIS round, respecting the round strategy) ──
                # Compact view drops the dance header entirely; song rows fall under the
                # round header (which still collapses them) and keep their Dance column.
                if self._compact or self._nogroup:
                    dance_hdr = round_hdr
                else:
                    dance_hdr = self._add_span_row(
                        f"    {dn}", _C_DANCE_BG, _C_DANCE_FG, bold=False,
                        regen_cb=(lambda rn=round_name, di=d_idx, dc=dance:
                                  self._regen_dance(rn, di, dc)),
                        collapsible=True,
                    )
                    self._dance_hdr_rows.add(dance_hdr)
                    self._dance_hdr_dance[dance_hdr] = dance
                    self._row_round_hdr[dance_hdr] = round_hdr   # collapsing round hides it
                    self._row_round_name[dance_hdr] = round_name

                for h_idx, heat in enumerate(heats):
                    entry = heat[d_idx]
                    meta  = Row(
                        round_name=round_name,
                        dance=dance,
                        h_idx=h_idx,
                        d_idx=d_idx,
                        tier=tier,
                        prefer_fresh=rc.prefer_fresh if rc else False,
                        strategy=(rc.strategy if rc else "") or "",
                        entry=entry,
                        multi=multi,
                    )
                    row = self.rowCount()
                    self.insertRow(row)
                    self._row_meta.append(meta)
                    self._row_round_hdr[row] = round_hdr
                    self._row_dance_hdr[row] = dance_hdr
                    bg = _C_ROW_EVEN if h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(row, meta, bg)

                    # Final-round backups: stacked, indented under their slot.
                    for bn, bentry in enumerate(
                            self._dynamic_backups.get((round_name, h_idx, d_idx), []), 1):
                        bmeta = meta.spare(bentry, bn)
                        brow = self.rowCount()
                        self.insertRow(brow)
                        self._row_meta.append(bmeta)
                        self._row_round_hdr[brow] = round_hdr
                        self._row_dance_hdr[brow] = dance_hdr
                        self._fill_song_row(brow, bmeta, bg)

        # …and put the ■ marker back on the playing one, wherever it sits now.
        self._row_meta.adopt(placed)
        self._follow_play_row()
        self._update_play_row_hl()
        self._grey_played_rows()   # re-apply played greys after the rebuild
        self._notify_changed()
        self._play_dropped = playing and self._current_play_row < 0
        try:
            self.loaded.emit(self)
        finally:
            self._play_dropped = False

    def load_theme(
        self,
        entries: list[MusicEntry],
        theme_label: str,
        play_cb,
        suggester: PlaylistSuggester,
    ):
        """Load a flat themed playlist (no rounds / heats)."""
        self._playlist    = None
        self._warmup      = False
        self._player_list = False
        self._dance_class = "S"
        self._play_cb     = play_cb
        self._suggester   = suggester
        self._use_timbre  = False
        placed = self._row_meta.placements()   # to hand the ids back below
        self._row_meta    = RunningOrder()
        self._reset_collapse_state()
        self.setRowCount(0)

        theme_secs = sum(getattr(e, "duration", 0) or 0 for e in entries)
        time_s = f",  ~{_fmt_track_secs(theme_secs)}" if theme_secs else ""
        self._add_span_row(
            f"  ═══  {theme_label}   ({len(entries)} tracks{time_s})  ═══",
            _C_ROUND_BG, _C_ROUND_FG, bold=True,
        )
        for i, e in enumerate(entries):
            meta = Row(dance=e.dance or "", entry=e, theme=True)
            row = self.rowCount()
            self.insertRow(row)
            self._row_meta.append(meta)
            bg = _C_ROW_EVEN if i % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(row, meta, bg)

        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._notify_changed()
        self.loaded.emit(self)

    def _warmup_sections(self, entries: list[MusicEntry]) -> list:
        """The ─── strips a warm-up / running-order list is cut into, as
        [(section, [entries])] — a pure function of the ORDER, which is why a
        drop re-cuts them.

        A running order is grouped by what is actually being played: the round
        each track belongs to where that could be derived, otherwise one strip
        per run of the same dance. A warm-up list follows the ETDS rule instead
        and starts a fresh round wherever a dance REPEATS — which would cut a
        dance-major order (all Walzer, then all Tango, …) into one strip per
        song, so a running order never uses it."""
        if not self._player_list:
            return warmup_rounds(entries)
        rounds: list[tuple[str, list[MusicEntry]]] = []
        for section, e in zip(self._player_section_labels(entries), entries):
            if not rounds or rounds[-1][0] != section:
                rounds.append((section, []))
            rounds[-1][1].append(e)
        return rounds

    def _section_title(self, section: str, songs: list[MusicEntry]) -> str:
        """The ─── strip over a section: what it is, and what is in it."""
        r_secs = sum(getattr(s, "duration", 0) or 0 for s in songs)
        r_time = f",  ~{_fmt_track_secs(r_secs)}" if r_secs else ""
        song_s = "song" if len(songs) == 1 else "songs"
        if self._player_list:
            # The strip names the round — or the dance, when the rounds couldn't
            # be derived — never a heat count: a running order is played straight
            # through.
            title = (f"{terms.round_name(section)}   "
                     f"({len(songs)} {song_s}{r_time})")
        else:
            title = f"{terms.round_name(section)}   (1 heat,  {len(songs)} {song_s}{r_time})"
        return f"    ───  {title}  ───"

    def load_warmup(self, entries: list[MusicEntry], label: str,
                    style: str, dance_class: str, relax: bool,
                    play_cb, suggester: PlaylistSuggester,
                    running_order: bool = False):
        """Load a flat warm-up ("Eintanzen") list as its OWN category. Like a theme,
        but each row keeps a 'warmup' tag so the ↺ button re-rolls a timbre-matched,
        TSO-conform track of the same dance and a drag-drop can replace a slot.

        `running_order` says the list is a competition order rather than a warm-up
        (see `load_player_list`) — the panel then heads its strips with the rounds
        instead of cutting a fresh one wherever a dance repeats. A plain warm-up
        list clears that again, so a panel that held an order once doesn't keep
        grouping the next Eintanzen list by rounds it no longer has."""
        self._player_list = bool(running_order)
        if not running_order:
            self._player_sections = {}
        self._flat_mode    = False
        self._playlist     = None
        self._dynamic      = False
        self._warmup       = True
        self._warmup_style = style
        self._warmup_class = dance_class
        self._warmup_relax = bool(relax)
        self._warmup_label = label
        self._dance_class  = dance_class
        self._style        = style
        self._play_cb      = play_cb
        self._suggester    = suggester
        self._use_timbre   = True
        placed = self._row_meta.placements()   # to hand the ids back below
        self._row_meta     = RunningOrder()
        self._played_saved.clear()   # rows are rebuilt with fresh colors
        self._reset_collapse_state()
        self.setRowCount(0)
        # Separate the flat list into the rounds it was built from, numbered per
        # section — Standardrunde 1, Lateinrunde 1, Socialrunde 1, … `warmup_rounds`
        # is where that cut lives, so a deck reading the same list back off disk
        # heads its strips with the very same rounds. Each header carries the
        # competition-style "(1 heat, N songs, ~t)" summary (a warm-up round is
        # always a single heat).
        rounds = self._warmup_sections(entries)

        i = 0
        for section, songs in rounds:
            # A section header counts as this list's round header, so ⊟ / ⊞ and a
            # click on the ─── strip fold it exactly like a competition round.
            round_hdr = -1
            if section and not self._nogroup:
                round_hdr = self._add_span_row(
                    self._section_title(section, songs),
                    _C_ROUND_BG, _C_ROUND_FG, bold=True, collapsible=True,
                )
                self._round_hdr_rows.add(round_hdr)
            for e in songs:
                # Social tracks have no .dance; warmup_code resolves their
                # genre (Discofox, Salsa, …) so the Dance column isn't blank.
                meta = Row(dance=warmup_code(e) or e.dance or "", d_idx=i,
                           entry=e, warmup=True)
                row = self.rowCount()
                self.insertRow(row)
                self._row_meta.append(meta)
                self._row_round_hdr[row] = round_hdr
                bg = _C_ROW_EVEN if i % 2 == 0 else _C_ROW_ODD
                self._fill_song_row(row, meta, bg)
                i += 1
        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._notify_changed()
        self.loaded.emit(self)

    def _warmup_plan(self, entries: list[MusicEntry]) -> list:
        """The rows load_warmup would render for `entries`: ("H", section) for a
        ─── strip header, ("S", entry) for a song. What the in-place edit below
        compares, so it can only ever skip a rebuild that would have come out
        the same way."""
        plan = []
        for section, songs in self._warmup_sections(entries):
            if section and not self._nogroup:
                plan.append(("H", section))
            plan.extend(("S", e) for e in songs)
        return plan

    def _warmup_edit_in_place(self, entries: list[MusicEntry]) -> bool:
        """Show an edit to a warm-up / running-order list by touching only the
        rows that actually changed. True when that was possible.

        Dragging one title between two 250-row running orders used to re-render
        both lists from scratch — a second of frozen window per drag, nearly all
        of it spent rebuilding rows that did not change. Adding or dropping a
        track moves the rows under it and re-shades them, and that is all this
        does.

        Only a clean insertion or removal is taken: the row plans before and
        after must agree apart from ONE run of songs, with no ─── strip
        appearing or vanishing. A re-order, a sort, a dropped dance that splits
        a strip in three — those say False and are rendered by load_warmup, as
        is a list with a folded strip (whose collapse state is keyed by row
        number and would be left pointing at the wrong rows)."""
        if not self._warmup or self._collapsed:
            return False
        old = self._warmup_plan(self._row_meta.entries())
        if len(old) != self.rowCount():
            return False              # the table is not what this plan describes
        new = self._warmup_plan(entries)

        def same(a, b) -> bool:
            # Songs by identity: two different tracks can share a title, and the
            # edited list is built from the very objects the old one held.
            return a[0] == b[0] and (a[1] is b[1] if a[0] == "S" else a[1] == b[1])

        head = 0
        while head < len(old) and head < len(new) and same(old[head], new[head]):
            head += 1
        tail = 0
        while (tail < len(old) - head and tail < len(new) - head
               and same(old[-1 - tail], new[-1 - tail])):
            tail += 1
        gone = old[head:len(old) - tail]
        added = new[head:len(new) - tail]
        if gone and added:
            return False              # changed on both sides: not an insert or a drop

        for _ in gone:
            self.removeRow(head)
        for i in range(len(added)):
            self.insertRow(head + i)
        # Every row number below the edit moved, so the row-keyed bookkeeping is
        # re-derived wholesale — it is a few dicts, not a few hundred widgets.
        self._row_meta = RunningOrder()
        self._row_round_hdr = {}
        self._round_hdr_rows = set()
        self._hdr_base_text = {}
        def fresh(row: int) -> bool:
            """Is this one of the blank rows just inserted? Every other row is
            already drawn, and re-drawing it is the cost this exists to avoid."""
            return head <= row < head + len(added)

        row = 0
        i = 0
        round_hdr = -1
        for section, songs in self._warmup_sections(entries):
            if section and not self._nogroup:
                round_hdr = row
                self._round_hdr_rows.add(row)
                title = self._section_title(section, songs)
                if fresh(row):
                    self._paint_span_row(row, title, _C_ROUND_BG, _C_ROUND_FG,
                                         bold=True, collapsible=True)
                else:
                    # The strip was already there; only what it counts changed.
                    self._hdr_base_text[row] = title
                    self._set_header_text(row)
                self._row_meta.append(None)
                row += 1
            for e in songs:
                meta = Row(dance=warmup_code(e) or e.dance or "", d_idx=i,
                           entry=e, warmup=True)
                self._row_meta.append(meta)
                self._row_round_hdr[row] = round_hdr
                if fresh(row):
                    bg = _C_ROW_EVEN if i % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(row, meta, bg)
                i += 1
                row += 1
        self._restripe_song_rows(head)
        self._notify_changed()
        self.loaded.emit(self)
        return True

    def _restripe_song_rows(self, from_row: int) -> None:
        """Re-shade the song rows from `from_row` down. The stripes count songs,
        so inserting or dropping one flips the colour of everything under it —
        but only the colour, which is 500 brushes rather than 500 rebuilt rows.
        A row painted red by a live 🎵 issue or orange by a replace mark keeps
        what _fill_song_row gave it."""
        for i, (row, meta) in enumerate(self._row_meta.numbered()):
            if row < from_row:
                continue
            path = meta.path_str
            if path and (path in self._issue_paths or path in self._marked_paths):
                continue
            bg = _C_ROW_EVEN if i % 2 == 0 else _C_ROW_ODD
            for col in range(self.columnCount()):
                it = self.item(row, col)
                if it is not None:
                    it.setBackground(bg)

    def _player_section_labels(self, entries: list[MusicEntry]) -> list[str]:
        """One ─── strip label per entry of a running order.

        The round it is played in when the caller could work that out, the dance
        otherwise. A track dropped in later belongs to no round of its own — it
        takes the one it landed in, so the strips stay whole instead of tearing
        open around every wish."""
        if not self._player_sections:
            return [warmup_code(e) or e.dance or "" for e in entries]
        out: list[str] = []
        last = ""
        for e in entries:
            last = self._player_sections.get(str(e.path)) or last
            out.append(last)
        # Anything dropped ahead of the first known track joins that first round.
        first = next((lbl for lbl in out if lbl), "")
        return [lbl or first for lbl in out]

    def load_player_list(self, entries: list[MusicEntry], label: str,
                         play_cb, suggester: PlaylistSuggester | None = None,
                         sections: dict[str, str] | None = None):
        """Load a deck as the flat running order of a player-only install.

        There is no draw to plan in such an install: the deck IS the list the
        evening is played from, so it behaves like the ETDS party list — one
        running order, a dropped title lands where it was dropped, any row can be
        dragged anywhere. It keeps the ─── strips, because seeing where one round
        ends and the next begins is worth having; `sections` (track path → round
        name) is what heads them with 'Vorrunde' / 'Finale', and without it they
        fall back to naming the dance being played. Either way they are derived
        from the order and simply re-cut themselves around whatever was just
        dragged in. What they never do is refuse a drop.

        Handed no `sections`, the list works the rounds out of its own order —
        a grid that carried no round names into the conversion, a running order
        restored from a file saved before the strips knew about rounds, a list
        assembled by hand: all of them would otherwise be stuck naming dances
        for good, because nothing ever derives the rounds a second time."""
        self._player_sections = dict(sections or {})
        if not self._player_sections:
            self._player_sections = {str(e.path): name
                                     for name, seg in running_order_rounds(entries)
                                     for e in seg}
            if self._player_sections:
                log.info("🏁 Rounds derived from the running order\n"
                         "tracks: %s\n"
                         "rounds: %s", len(entries),
                         ", ".join(dict.fromkeys(self._player_sections.values())))
        self.load_warmup(entries, label, style="", dance_class="S", relax=True,
                         play_cb=play_cb, suggester=suggester, running_order=True)

    def load_wishlist(self, entries: list[MusicEntry], play_cb,
                      suggester: PlaylistSuggester | None):
        """Load the flat scratch Wishlist. Like a theme list but drops append to it."""
        self._flat_mode   = True
        self._warmup      = False
        self._playlist    = None
        self._dance_class = "S"
        self._play_cb     = play_cb
        self._suggester   = suggester
        self._use_timbre  = False
        placed = self._row_meta.placements()   # to hand the ids back below
        self._row_meta    = RunningOrder()
        self._reset_collapse_state()
        self.setRowCount(0)
        for e in entries:
            self._append_entry(e, notify=False)
        self._row_meta.adopt(placed)   # the ■ marker follows a title still here
        self._follow_play_row()
        self._notify_changed()
        self.loaded.emit(self)

    def _append_entry(self, entry: MusicEntry, notify: bool = True):
        """Append one track as a flat row (Wishlist)."""
        if entry is None:
            return
        # Skip exact duplicates already parked in the wishlist.
        for m in self._row_meta:
            if m and m.entry is not None and str(m.entry.path) == str(entry.path):
                return
        meta = Row(dance=entry.dance or "", entry=entry, theme=True)
        row = self.rowCount()
        self.insertRow(row)
        self._row_meta.append(meta)
        bg = _C_ROW_EVEN if row % 2 == 0 else _C_ROW_ODD
        self._fill_song_row(row, meta, bg)
        if notify:
            self._notify_changed()

    def _append_path(self, path: Path) -> bool:
        """Resolve a dropped file path to an entry and append it to the wishlist.
        Returns True when a track was added."""
        entry = self._entry_for(path)
        if entry is None:
            QMessageBox.information(
                self, "Wishlist",
                i18n.t("Couldn't read “%s” as an audio track.") % Path(path).name
            )
            return False
        before = len(self._row_meta)
        self._append_entry(entry)
        return len(self._row_meta) > before

    def _append_m3u(self, path: Path) -> int:
        """Expand a dropped .m3u/.m3u8 into the wishlist. Returns how many tracks
        were added (deduped against what's already parked there)."""
        try:
            lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return 0
        added = 0
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.lower().startswith("file:"):
                u = QUrl(s)
                if u.isLocalFile():
                    s = u.toLocalFile()
            tp = Path(s.strip('"'))
            entry = self._entry_for(tp)
            if entry is not None:
                before = len(self._row_meta)
                self._append_entry(entry, notify=False)
                added += 1 if len(self._row_meta) > before else 0
        if added:
            self._notify_changed()
        return added

    # A dropped folder is read whole, subfolders included — a tournament's music
    # sits in one folder per dance. Past this many tracks it is more likely a slip
    # of the hand than an intention (a library root holds thousands, and every one
    # of them has its tags read on the way in), so ask before doing it.
    _DIR_DROP_ASK = 100

    def _files_from_dir(self, folder: Path) -> list[Path]:
        """Every audio file in a dropped FOLDER, subfolders included, in path order.
        Playlists inside it are skipped: what was dropped is the folder's own music,
        and an .m3u lying next to it would add every track a second time."""
        try:
            found = [p for p in sorted(folder.rglob("*"), key=lambda q: str(q).lower())
                     if p.suffix.lower() in self._AUDIO_DROP_EXTS and p.is_file()]
        except OSError as exc:
            log.warning("📂 Dropped folder could not be read\n"
                        "folder: %s\n"
                        "error: %s", folder, exc)
            return []
        if len(found) > self._DIR_DROP_ASK and not self._confirm_big_dir_drop(folder, len(found)):
            return []
        return found

    def _confirm_big_dir_drop(self, folder: Path, n: int) -> bool:
        ans = QMessageBox.question(
            self, "Add folder",
            i18n.t("“%s” holds %d tracks (subfolders included).\n\nReading them all takes a "
                   "moment — every file's tags are read on the way in.\n\nAdd them?")
            % (folder.name, n),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _wishlist_droppables(self, e, expand_dirs: bool = True) -> list[Path]:
        """All local audio files and .m3u playlists carried by a drop (for the
        Wishlist's append-anything behaviour). A dropped FOLDER stands for the audio
        files inside it. Falls back to the text payload and finally the raw-mime path
        dig used for DJ apps.

        `expand_dirs=False` leaves a folder in the list as itself. That's for the
        drag accept-checks, which only ask whether there is anything to drop at all
        and must not walk a music tree on every mouse move of the drag."""
        md = e.mimeData()
        out: list[Path] = []
        ok = self._AUDIO_DROP_EXTS + (".m3u", ".m3u8")
        seen: set = set()

        def _add(s: str):
            s = (s or "").strip().strip('"').strip("'")
            if not s:
                return
            if s.lower().startswith("file:"):
                u = QUrl(s)
                if u.isLocalFile():
                    s = u.toLocalFile()
            p = Path(s)
            key = str(p).lower()
            if key in seen:
                return
            if p.suffix.lower() in ok and p.is_file():
                seen.add(key)
                out.append(p)
            elif p.is_dir():
                seen.add(key)
                out.extend(self._files_from_dir(p) if expand_dirs else [p])

        if md and md.hasUrls():
            for url in md.urls():
                _add(url.toLocalFile() if url.isLocalFile() else url.toString())
        if not out and md and md.hasText():
            for line in md.text().splitlines():
                _add(line)
        if not out:
            p = self._path_from_raw_mime(md)
            if p is not None:
                out.append(p)
        return out

    def wishlist_entries(self) -> list[MusicEntry]:
        return self._row_meta.entries()

    def _add_span_row(self, text: str, bg: QColor, fg: QColor, bold: bool,
                      regen_cb=None, collapsible: bool = False,
                      regen_tip: str = "Regenerate every heat of this dance (this round only)") -> int:
        row = self.rowCount()
        self.insertRow(row)
        self._row_meta.append(None)
        self._paint_span_row(row, text, bg, fg, bold, regen_cb, collapsible, regen_tip)
        return row

    def _paint_span_row(self, row: int, text: str, bg: QColor, fg: QColor, bold: bool,
                        regen_cb=None, collapsible: bool = False,
                        regen_tip: str = "") -> None:
        """Dress an EXISTING row as a header. Split out of `_add_span_row` so a
        row inserted in the middle of a list can be given the same look without
        being appended to the order."""
        if collapsible:
            # Store the bare label; the ▼/▶ arrow is rendered by _set_header_text.
            self._hdr_base_text[row] = text
            text = f"▼ {text}"
        item = QTableWidgetItem(text)
        item.setBackground(bg)
        item.setForeground(fg)
        if bold:
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)   # not selectable / draggable
        if collapsible:
            item.setToolTip("Click to collapse / expand")
        self.setItem(row, 0, item)
        if regen_cb is not None:
            # Leave the last (↺) column free for a per-dance regenerate button.
            self.setSpan(row, 0, 1, _N_COLS - 1)
            btn = QPushButton("↺")
            btn.setFixedSize(26, 20)
            btn.setStyleSheet("padding: 0;")
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # keep keyboard focus on the table
            btn.setToolTip(regen_tip)
            btn.clicked.connect(lambda _: regen_cb())
            self.setCellWidget(row, _COL_REGEN, btn)
        else:
            self.setSpan(row, 0, 1, _N_COLS)
        self.setRowHeight(row, 22)

    # ── Collapse / expand rounds and dance sections ────────────────────────────

    def _reset_collapse_state(self):
        self._row_round_hdr = {}
        self._row_dance_hdr = {}
        self._round_hdr_rows = set()
        self._dance_hdr_rows = set()
        self._dance_hdr_dance = {}
        self._row_round_name = {}
        self._collapsed = set()
        self._hdr_base_text = {}

    def _set_header_text(self, row: int):
        """Render a collapsible header's label with the current ▼/▶ arrow."""
        base = self._hdr_base_text.get(row)
        if base is None:
            return
        arrow = "▶" if row in self._collapsed else "▼"
        it = self.item(row, 0)
        if it is not None:
            it.setText(f"{arrow} {base}")

    def _on_header_click(self, row: int, _col: int):
        if row in self._round_hdr_rows or row in self._dance_hdr_rows:
            if row in self._collapsed:
                self._collapsed.discard(row)
            else:
                self._collapsed.add(row)
            self._set_header_text(row)
            self._apply_collapse_visibility()

    def _apply_collapse_visibility(self):
        """Hide every row whose round OR dance header is collapsed; show the rest.
        A dance header itself is hidden only when its round is collapsed."""
        for r in range(self.rowCount()):
            rh = self._row_round_hdr.get(r)
            dh = self._row_dance_hdr.get(r)
            hidden = (rh in self._collapsed) or (dh in self._collapsed)
            self.setRowHidden(r, hidden)
        # Columns are user-resizable (Interactive), so there's nothing to re-fit on
        # collapse — their widths are whatever the user dragged them to.

    def collapse_all(self):
        """Collapse every round (one row per round visible)."""
        self._collapsed = set(self._round_hdr_rows)
        for r in self._round_hdr_rows:
            self._set_header_text(r)
        self._apply_collapse_visibility()

    def expand_all(self):
        """Expand every round and dance section."""
        self._collapsed = set()
        for r in (*self._round_hdr_rows, *self._dance_hdr_rows):
            self._set_header_text(r)
        self._apply_collapse_visibility()

    def _fill_song_row(self, row: int, meta: dict, bg: QColor):
        dance       = meta.dance
        h_idx       = meta.h_idx
        multi       = meta.multi
        entry       = meta.entry
        dance_class = self._dance_class

        def cell(col, text, fg=_C_DEFAULT,
                 align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
            it = QTableWidgetItem(str(text))
            it.setBackground(bg)
            it.setForeground(fg)
            it.setTextAlignment(align)
            it.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            self.setItem(row, col, it)

        ctr = Qt.AlignmentFlag.AlignCenter
        is_backup = meta.backup
        # Flag tracks whose file has vanished from disk since the playlist was made
        # (moved / deleted / drive offline) — red title + a red ❗ in the last column.
        missing = bool(entry) and not Path(entry.path).exists()
        # "Marked for potential replace": orange row underlay + an orange ❗ (below).
        # A genuinely missing file wins the styling (its red ❗ is the more urgent flag).
        marked = bool(entry is not None and getattr(entry, "path", None)
                      and str(entry.path) in self._marked_paths)
        # Live Check-Music issue (play length / takt / round tempo spread): the
        # row stays RED until the issue is resolved. Red outranks the orange
        # replace-mark; a genuinely missing file keeps its own styling.
        issue_text = (self._issue_paths.get(str(entry.path))
                      if entry is not None and getattr(entry, "path", None) else None)
        if issue_text and not missing:
            bg = _C_ISSUE_BG
        elif marked and not missing:
            bg = _C_MARK_BG

        # Dance column (also holds path for drag)
        cell(_COL_DANCE, "" if is_backup else self._dance_label(dance))

        # Heat column
        if is_backup:
            cell(_COL_HEAT, f"↳ backup {meta.backup_n or ''}".rstrip(), align=ctr)
        else:
            cell(_COL_HEAT, f"Heat {h_idx + 1}" if multi else "", align=ctr)

        if entry:
            title_txt = ("    " + entry.title[:61]) if is_backup else entry.title[:65]
            resume_ms = self._resume_marks.get(str(entry.path))
            if resume_ms:
                title_txt += f"   ↩ {_fmt_track_secs(resume_ms // 1000)}"
            cell(_COL_TITLE, title_txt,
                 fg=(_C_WARN_FG if missing else _C_MARK_FG if marked
                     else _C_NEW_FG if is_backup else _C_DEFAULT))
            # Hover the title → same rich track description as the Similar-Tracks window.
            title_it = self.item(row, _COL_TITLE)
            if title_it is not None:
                if missing:
                    title_it.setToolTip(i18n.t("⚠ File not found on disk:\n%s") % entry.path)
                else:
                    sim = entry.sim_score if entry.sim_score is not None else None
                    tip = _entry_tooltip(entry, sim, "Similarity")
                    if resume_ms:
                        tip = ("<div style='color:#2e9e5b'><b>"
                               + i18n.t("↩ Left at %s — starts there again")
                               % _fmt_track_secs(resume_ms // 1000)
                               + "</b></div><hr>" + tip)
                    if marked:
                        # Same HTML treatment as the ⚠ issue block below — the
                        # base tooltip is rich text, plain \n prefixes mangle it.
                        tip = ("<div style='color:#d86018'><b>"
                               + i18n.t("🔁 Marked for potential replace  (Ctrl+M to toggle)")
                               + "</b></div><hr>" + tip)
                    if issue_text:
                        # The base tooltip is rich text (<div>…</div>) — the
                        # issue lines must be an HTML block too, or Qt mangles
                        # the layout (plain \n text glued above the div).
                        issue_html = "<br>".join(
                            "⚠ " + html.escape(line)
                            for line in issue_text.split("\n"))
                        tip = (f"<div style='color:#c62828'><b>{issue_html}"
                               "</b></div><hr>" + tip)
                    title_it.setToolTip(tip)

            cell(_COL_ARTIST, getattr(entry, "tag_artist", None) or "")
            artist_it = self.item(row, _COL_ARTIST)
            if artist_it is not None:
                artist_it.setToolTip(_entry_tooltip(entry))

            bpm_s = _fmt_bpm(entry.bpm, dance, dance_class).strip()
            bpm_fg = QColor(200, 130, 80) if bpm_s.endswith("*") else _C_DEFAULT
            cell(_COL_BPM, bpm_s, fg=bpm_fg, align=ctr)

            secs = int(getattr(entry, "duration", 0) or 0)
            if secs:
                play = self._play_secs_cb(entry) if self._play_secs_cb else None
                trimmed = play is not None and int(play) != secs
                # Red is for an edge long enough to notice on the floor, not for
                # every file with a couple of seconds of room tone (which is
                # most of them). The tooltip still reports any trim.
                edge = self._edge_silence_cb(entry) if self._edge_silence_cb else 0.0
                flagged = trimmed and edge >= FLAG_EDGE_SILENCE
                limit = self._short_secs_cb() if self._short_secs_cb else 0
                too_short = bool(limit) and (int(play) if trimmed else secs) < limit
                # Orange, not red: red in this table is a file that is MISSING,
                # and a track that merely ends early is not that. Both length
                # warnings share the amber; the tooltip says which one fired.
                fg = _C_LEN_WARN_FG if (flagged or too_short) else _C_DEFAULT
                cell(_COL_LEN, _fmt_track_secs(secs), fg=fg, align=ctr)
                tips = []
                if trimmed:
                    tips.append(
                        i18n.t("Plays %s — the stillness at the edges of the file is skipped")
                        % _fmt_track_secs(int(play)))
                if too_short:
                    tips.append(i18n.t("Shorter than the configured play length (%s)")
                                % _fmt_track_secs(limit))
                if tips:
                    self.item(row, _COL_LEN).setToolTip("\n".join(tips))
            else:
                cell(_COL_LEN, "", align=ctr)

            if entry.popularity:
                cell(_COL_POP, f"★{entry.popularity}", fg=_C_POP_FG, align=ctr)
            else:
                cell(_COL_POP, i18n.t("✦new"), fg=_C_NEW_FG, align=ctr)

            cls_parts = []
            if entry.sim_score is not None and entry.sim_score >= 0.7:
                cls_parts.append("≈")
            if entry.classes_ok:
                cls_parts.append(f"[{','.join(entry.classes_ok)}]")
            cls_fg = _C_SIM_FG if cls_parts and cls_parts[0] == "≈" else _C_DEFAULT
            cell(_COL_CLASS, " ".join(cls_parts), fg=cls_fg, align=ctr)
            cell(_COL_RATING, "")
            self.item(row, _COL_RATING).setData(RATING_ROLE, entry.rating or 0)
            cell(_COL_CUSTOM, entry.custom or "")
            if entry.custom:
                self.item(row, _COL_CUSTOM).setToolTip(entry.custom)
        else:
            cell(_COL_TITLE, "⚠  No song found", fg=_C_WARN_FG)
            for c in (_COL_ARTIST, _COL_BPM, _COL_LEN, _COL_POP, _COL_CLASS, _COL_RATING,
                      _COL_CUSTOM):
                cell(c, "")

        # ── Play button ──
        play_btn = QPushButton()
        set_play_glyph(play_btn, False)
        play_btn.setFixedSize(26, 20)
        play_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # keep keyboard focus on the table
        if entry and self._play_cb:
            p = entry.path
            # Resolve the button's row LIVE on click: a captured row index goes stale
            # once a row above is removed (drag a track out to another list, context
            # remove, auto-clean), which otherwise plays the wrong / next track.
            play_btn.clicked.connect(
                lambda _, b=play_btn, path=p:
                    self._on_play_click(self._row_of_widget(b, _COL_PLAY), path))
        else:
            play_btn.setEnabled(False)
        self.setCellWidget(row, _COL_PLAY, play_btn)

        # ── Regenerate button ── (a flat Wishlist has no rounds to re-roll from)
        if not self._flat_mode:
            regen_btn = QPushButton("❗" if (missing or marked) else "↺")
            regen_btn.setFixedSize(26, 20)
            regen_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # keep keyboard focus on the table
            if self._party_swap():
                dname = dance_name(meta.dance, meta.dance) or "title"
                regen_hint = (i18n.t("↺ click to swap it with a %s from the end "
                                     "of the list") % dname)
            else:
                regen_hint = i18n.t("↺ click to re-roll a replacement")
            if missing:
                regen_btn.setStyleSheet("padding: 0; color: #c81e1e; font-weight: bold;")
                regen_btn.setToolTip(
                    i18n.t("⚠ File not found on disk:\n%s") % entry.path
                    + "\n\n" + regen_hint)
            elif marked:
                regen_btn.setStyleSheet("padding: 0; color: #d86018; font-weight: bold;")
                regen_btn.setToolTip(
                    i18n.t("🔁 Marked for potential replace  "
                           "(Ctrl+M to toggle)") + "\n" + regen_hint)
            elif self._party_swap():
                regen_btn.setStyleSheet("padding: 0;")
                regen_btn.setToolTip(
                    i18n.t("Swap with a %s from the end of the list — a "
                           "leftover that fits no round first, else one from "
                           "the last third  (Ctrl+R / Ctrl+N)")
                    % dname)
            else:
                regen_btn.setStyleSheet("padding: 0;")
                regen_btn.setToolTip("Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)")
            regen_btn.clicked.connect(
                lambda _, b=regen_btn: self._regen(self._row_of_widget(b, _COL_REGEN)))
            self.setCellWidget(row, _COL_REGEN, regen_btn)
        elif missing:
            # Flat list (wishlist / Eintanzen) has no ↺ button — mark the dead file
            # with a red ❗ in the last column instead.
            warn = QTableWidgetItem("❗")
            warn.setBackground(bg)
            warn.setForeground(_C_WARN_FG)
            warn.setTextAlignment(ctr)
            warn.setToolTip(i18n.t("⚠ File not found on disk:\n%s") % entry.path)
            warn.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.setItem(row, _COL_REGEN, warn)

        self.setRowHeight(row, 24)

    # ── Play / stop toggle ────────────────────────────────────────────────────

    def _row_of_widget(self, widget, col: int) -> int:
        """Current row of a cell widget, looked up live. Per-row buttons capture
        their row at build time, but a removal above them (drag-out, context remove,
        auto-clean) shifts rows up without re-filling — so resolve the row on click."""
        for r in range(self.rowCount()):
            if self.cellWidget(r, col) is widget:
                return r
        return -1

    def scroll_row_into_play_view(self, row: int):
        """Bring a starting title into view — and when it wasn't fully on
        screen, put it at the TOP instead of just barely inside.

        What the operator needs to see once a title starts is what comes after
        it, so the free room belongs below the running row, not above it.
        A row that is already fully visible is left where it is: no jump on
        every auto-advance.

        The move itself is animated. A list that snaps to a new position leaves
        the operator hunting for the row that just started; a short glide keeps
        the eye on it."""
        item = self.item(row, _COL_TITLE)
        if item is None:
            return
        rect = self.visualItemRect(item)
        whole = rect.height() > 0 and self.viewport().rect().contains(rect)
        bar = self.verticalScrollBar()
        start = bar.value()
        # Let Qt work out where that hint lands, then put the bar back and
        # travel there ourselves. Both setValue calls happen before the next
        # repaint, so nothing of the jump is ever on screen.
        self.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible
                          if whole else QAbstractItemView.ScrollHint.PositionAtTop)
        target = bar.value()
        if target == start:
            return
        bar.setValue(start)
        if self._scroll_anim is None:
            self._scroll_anim = QPropertyAnimation(bar, b"value", self)
            self._scroll_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._scroll_anim.setDuration(_SCROLL_MS)
        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(start)
        self._scroll_anim.setEndValue(target)
        self._scroll_anim.start()

    def _on_play_click(self, row: int, path):
        """Toggle play/stop when a row's ▶/■ button is clicked."""
        # A cued row in planning shows ▶, so its click starts it (switch branch)
        # — the plain stop below would unload a title that never played.
        cued = not self.pauses_on_stop() and self._player_stopped()
        if row == self._current_play_row and not cued:
            if self.pauses_on_stop():
                # Desk: pause instead of unloading — position and source stay,
                # exactly like Space and the player card's ⏯ (whose state pushes
                # the glyph back here via sync_play_glyph).
                self.host.toggle_play()
                return
            # Same row → stop
            w = self.cellWidget(row, _COL_PLAY)
            if isinstance(w, QPushButton):
                set_play_glyph(w, False)
            self._current_play_row = -1
            if self._play_cb:
                self._play_cb(None)
        else:
            # Different row (or nothing playing) → switch
            if self._current_play_row >= 0:
                old = self.cellWidget(self._current_play_row, _COL_PLAY)
                if isinstance(old, QPushButton):
                    set_play_glyph(old, False)
            self._current_play_row = row
            self.sync_play_glyph(True)
            # Keep the running title in sight and focused — matters most when
            # auto-advance / ⏭ picked the row, not a click.
            if self.item(row, _COL_TITLE) is not None:
                self.scroll_row_into_play_view(row)
                self.setCurrentCell(row, _COL_TITLE)
            self.playRequested.emit(self)   # let MainWindow stop the other decks
            if self._play_cb:
                self._play_cb(path)
        self._update_play_row_hl()

    def first_track_path(self) -> Path | None:
        """Path of the first row that holds a real song, or None for an empty
        deck. Round and dance headers carry no meta, so they are skipped."""
        for entry in self._row_meta.entries():
            if getattr(entry, "path", None):
                return Path(entry.path)
        return None

    def cue_row(self, row: int, scroll: bool = True):
        """Make `row` the running row for a title that is cued, not started, so
        ⏭ / ⏮ continue from it. scroll=False marks it without bringing it into
        view — for a cue the operator did not ask for."""
        if self._current_play_row == row:
            return
        if self._current_play_row >= 0:
            old = self.cellWidget(self._current_play_row, _COL_PLAY)
            if isinstance(old, QPushButton):
                set_play_glyph(old, False)
        self._current_play_row = row
        self.sync_play_glyph()   # cued, not started → ▶ at the desk
        if scroll:
            self.scroll_row_into_play_view(row)
        self._update_play_row_hl()

    def on_playback_stopped(self):
        """Call this when the media player stops naturally (end of song)."""
        if self._current_play_row >= 0:
            row = self._current_play_row
            w = self.cellWidget(row, _COL_PLAY)
            if isinstance(w, QPushButton):
                set_play_glyph(w, False)
            self._current_play_row = -1
            self._update_play_row_hl()

    def advance_toggle(self) -> QPushButton:
        """The ⏭/✋ switch itself, for the deck box to put in its badge bar.

        Adding it to a layout reparents it out of the table, which is the
        point: it is a control ABOUT this deck, not something drawn over it."""
        return self._advance_btn

    def set_advance_toggle(self, get_cb, set_cb):
        """Hand the ⏭/✋ switch the setting it stands for: `get_cb()` reads
        auto-advance for THIS list, `set_cb(on)` flips it. MainWindow owns the
        value (per deck, falling back to the play panel) — the deck only shows
        it."""
        self._advance_get = get_cb
        self._advance_set = set_cb
        self._apply_advance_visible()

    def set_advance_toggle_visible(self, on: bool):
        """Only playing mode has anything to advance (MainWindow flips this on
        the mode switch, like the play highlight)."""
        self._advance_on = bool(on)
        self._apply_advance_visible()

    def _apply_advance_visible(self):
        self._advance_btn.setVisible(self._advance_on
                                     and self._advance_get is not None)
        self.refresh_advance_toggle()

    def set_advance_live(self, on: bool):
        """Mark this list's switch as the one that counts: a title was last
        started from this list (MainWindow clears it on the others)."""
        if self._advance_live == bool(on):
            return
        self._advance_live = bool(on)
        self._advance_btn.setProperty("live", self._advance_live)
        # A property selector is only re-read on a fresh polish.
        self._advance_btn.style().unpolish(self._advance_btn)
        self._advance_btn.style().polish(self._advance_btn)
        self.refresh_advance_toggle()

    def refresh_advance_toggle(self):
        """Caption follows the setting, whichever deck or the panel changed it."""
        if self._advance_get is None or not self._advance_on:
            return
        auto = bool(self._advance_get())
        self._advance_btn.setText("⏭  Auto" if auto else "✋  Manual")
        tip = i18n.t(
            "Auto: a finished song is followed by the next row of the deck, so\n"
            "a whole round runs hands-free.\n"
            "Manual: every song is started by the operator, and 🔈 Announce\n"
            "next dance stops with it — back on Auto it returns.\n\n"
            "This playlist's own answer, remembered for it: the party list can\n"
            "run hands-free while the round next to it is started by hand.\n"
            "⏭ Auto-advance on the play panel is the same answer while this\n"
            "list is the one last clicked.") if auto else i18n.t(
            "Manual: every song is started by the operator, and 🔈 Announce\n"
            "next dance is off with it.\n"
            "Auto: a finished song is followed by the next row of the deck, so\n"
            "a whole round runs hands-free — and the announcement returns.\n\n"
            "This playlist's own answer, remembered for it: the party list can\n"
            "run hands-free while the round next to it is started by hand.\n"
            "⏭ Auto-advance on the play panel is the same answer while this\n"
            "list is the one last clicked.")
        if self._advance_live:
            tip = i18n.t("▶ This list is playing: this switch decides what "
                         "follows the title.") + "\n\n" + tip
        self._advance_btn.setToolTip(tip)

    def _on_advance_clicked(self):
        if self._advance_get is None or self._advance_set is None:
            return
        self._advance_set(not bool(self._advance_get()))

    def set_play_highlight_enabled(self, on: bool):
        """Playing mode shows a blue marker on the playing row and greys out
        already-played tracks (MainWindow flips this on the mode switch)."""
        self._play_hl_enabled = bool(on)
        self._update_play_row_hl()
        if on:
            self._grey_played_rows()
        else:
            self._ungrey_played_rows()

    def mark_path_played(self, path_str: str):
        """Playing mode: mark a track (by path) as played — greys every copy of
        it in this deck. Driven by MainWindow once a song has actually been
        heard for >10 s, so it never depends on which row came before/after."""
        if not self._play_hl_enabled or not path_str:
            return
        self._played_paths.add(path_str)
        self._grey_played_rows()

    def _grey_played_rows(self):
        """Grey out every row holding an already-played track (any copy)."""
        if not self._play_hl_enabled or not self._played_paths:
            return
        grey = QColor("#a8aeb8")
        for r, m in self._row_meta.numbered():
            if m.path_str not in self._played_paths:
                continue
            if r == self._current_play_row:
                continue   # the running row keeps its colors (blue marker)
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it is not None and (r, c) not in self._played_saved:
                    self._played_saved[(r, c)] = it.foreground()
                    it.setForeground(grey)

    def _ungrey_played_rows(self):
        """Back to planning mode: restore the original row colors."""
        for (r, c), brush in self._played_saved.items():
            it = self.item(r, c)
            if it is not None:
                it.setForeground(brush)
        self._played_saved.clear()

    def reset_played_marks(self):
        """Forget every played mark (fresh session / new tournament)."""
        self._played_paths.clear()
        self._ungrey_played_rows()

    def _update_play_row_hl(self):
        # Whenever the playing row changes, re-grey played rows so the one we
        # just left greys at once (it's no longer skipped as the current row).
        self._grey_played_rows()
        row = self._current_play_row
        if (not self._play_hl_enabled or not (0 <= row < self.rowCount())):
            self._play_row_hl.hide()
            return
        y = self.rowViewportPosition(row)
        self._play_row_hl.setGeometry(
            0, y, self.viewport().width(), self.rowHeight(row))
        self._play_row_hl.raise_()
        self._play_row_hl.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fill_title_column()
        self._update_play_row_hl()

    # ── Columns: what is shown, and who takes the width nobody claimed ─────────
    # Readable names for the three columns whose caption is a glyph — a tick list
    # reading "▶ / ⏱ / ↺" says nothing about what would disappear.
    _COL_MENU_NAMES = {_COL_PLAY: "▶  Play", _COL_LEN: "⏱  Length",
                       _COL_RATING: "★  Rating", _COL_REGEN: "↺  Regenerate"}
    # Whole captions, not the bare noun: the noun on its own cannot be a
    # catalog key, and glueing one into a sentence is how the German would go
    # wrong the first time a kind is added whose article is not "jeder".
    _KIND_HEADS = {"wishlist": "Columns in every wishlist",
                   "party": "Columns in every party list"}

    def _fill_title_column(self):
        """Give Title whatever width the other columns leave over.

        What `Stretch` used to do, minus the part that made Title the one column
        the user could not drag. Runs on a table resize and after a neighbour is
        dragged, so there is never an empty gap on the right."""
        if self._filling or self.isColumnHidden(_COL_TITLE):
            return
        others = sum(self.columnWidth(c) for c in range(_N_COLS)
                     if c != _COL_TITLE and not self.isColumnHidden(c))
        want = self.viewport().width() - others
        self._filling = True
        try:
            self.setColumnWidth(
                _COL_TITLE, max(self.horizontalHeader().minimumSectionSize(), want))
        finally:
            self._filling = False

    def _on_section_resized(self, idx: int, _old: int, _new: int):
        """A dragged column takes its width from Title, not from the window."""
        if idx == _COL_TITLE or self._filling:
            return
        self._fill_title_column()
        # A drag arrives a pixel at a time; save once when it comes to rest.
        self._width_timer.start()

    def _notify_widths(self):
        if self._widths_cb:
            self._widths_cb(self.list_kind, self.column_widths())

    def _notify_dance_names(self):
        if self._dance_cb:
            self._dance_cb(self.list_kind, self._short_dances)

    def set_dance_names_callback(self, cb):
        """`cb(kind, short)` when the Dance column is switched between the full
        name and the short code."""
        self._dance_cb = cb

    def _dance_label(self, dance: str) -> str:
        """What the Dance column says for a dance code: the full name, or the
        Σ line's short one when the user has asked for it."""
        if self._short_dances:
            return DANCE_SHORT.get(dance, dance)
        return dance_name(dance, dance)

    def short_dances(self) -> bool:
        return self._short_dances

    def set_short_dances(self, on: bool):
        """Write the Dance column short ("LW", "SB") or in full. Rewrites the
        rows that are already there; the dance HEADER rows keep the full name,
        they span the table and have the room."""
        on = bool(on)
        if on == self._short_dances:
            return
        self._short_dances = on
        for row, meta in enumerate(self._row_meta):
            # A header row carries no dance of its own, and a stacked backup's
            # Dance cell is deliberately blank.
            if meta is None or meta.backup:
                continue
            item = self.item(row, _COL_DANCE)
            if item is not None:
                item.setText(self._dance_label(meta.dance))

    def set_columns_callback(self, cb):
        """`cb(kind, hidden_columns)` whenever a tick changes — the window saves it
        and applies it to every other list of the same kind."""
        self._columns_cb = cb

    def set_rating_callback(self, cb):
        """`cb(entry, stars)` when a ★ is clicked — 0 stars = take the rating back."""
        self._rating_cb = cb

    def _on_star_clicked(self, index, stars: int):
        entry = self._row_meta.entry_at(index.row())
        if entry is not None and self._rating_cb is not None:
            self._rating_cb(entry, stars)

    def set_widths_callback(self, cb):
        """`cb(kind, widths)` when the user has finished dragging a handle."""
        self._widths_cb = cb

    def column_widths(self) -> dict[int, int]:
        """Every column's width except Title's, which is the leftover and is
        recomputed on each resize. A hidden column reports the width it had, not
        the 0 Qt gives a hidden section."""
        return {c: (self._col_width.get(c, 0) if self.isColumnHidden(c)
                    else self.columnWidth(c))
                for c in range(_N_COLS) if c != _COL_TITLE}

    def set_column_widths(self, widths):
        """Apply saved widths. JSON has no integer keys, so string ones count."""
        self._filling = True          # our own doing, not a drag: don't re-save
        try:
            for key, w in (widths or {}).items():
                c, w = int(key), int(w)
                if c == _COL_TITLE or not 0 <= c < _N_COLS or w <= 0:
                    continue
                if self.isColumnHidden(c):
                    self._col_width[c] = w
                else:
                    self.setColumnWidth(c, w)
        finally:
            self._filling = False
        self._fill_title_column()

    def hidden_columns(self) -> list[int]:
        return [c for c in range(_N_COLS) if self.isColumnHidden(c)]

    def set_hidden_columns(self, cols):
        """Show exactly the columns not in `cols`. Title is never put away — a row
        without it cannot be told from any other."""
        want = {int(c) for c in cols if int(c) != _COL_TITLE}
        for c in range(_N_COLS):
            hidden = self.isColumnHidden(c)
            if c in want and not hidden:
                self._col_width[c] = self.columnWidth(c)
                self.setColumnHidden(c, True)
            elif hidden and c not in want:
                self.setColumnHidden(c, False)
                w = self._col_width.pop(c, 0)
                if w:
                    self.setColumnWidth(c, w)
        self._fill_title_column()

    def build_column_menu(self) -> QMenu:
        """The right-click tick list of the header."""
        menu = QMenu(self)
        head = menu.addAction(self._KIND_HEADS.get(
            self.list_kind, "Columns in every playlist"))
        head.setEnabled(False)
        menu.addSeparator()
        for c in range(_N_COLS):
            if c == _COL_TITLE:
                continue
            item = self.horizontalHeaderItem(c)
            act = menu.addAction(self._COL_MENU_NAMES.get(
                c, item.text() if item else str(c)))
            act.setCheckable(True)
            act.setChecked(not self.isColumnHidden(c))
            act.setData(c)
            act.triggered.connect(lambda on, col=c: self._toggle_column(col, on))
        menu.addSeparator()
        # Not a column but the same kind of choice: how much room the Dance
        # column needs. Carries no data(), which is how a column tick is told
        # apart from it.
        short = menu.addAction("Short dance names  (LW, SB)")
        short.setCheckable(True)
        short.setChecked(self._short_dances)
        short.triggered.connect(self._toggle_short_dances)
        add_custom_mapping_action(menu, self)
        return menu

    def _toggle_short_dances(self, on: bool):
        self.set_short_dances(on)
        self._notify_dance_names()

    def _toggle_column(self, col: int, on: bool):
        hidden = set(self.hidden_columns())
        if on:
            hidden.discard(col)
        else:
            hidden.add(col)
        self.set_hidden_columns(sorted(hidden))
        if self._columns_cb:
            self._columns_cb(self.list_kind, self.hidden_columns())

    def _show_column_menu(self, pos: QPoint):
        self.build_column_menu().exec(self.horizontalHeader().mapToGlobal(pos))

    def set_numbered(self, on: bool):
        """Show or hide the Nb. column of the 🔢 Numbers view."""
        self._numbered = on
        vh = self.verticalHeader()
        fm = self._nb_label.fontMetrics()
        vh.setFixedWidth(max(fm.horizontalAdvance("Nb."), fm.horizontalAdvance("999")) + 14)
        vh.setVisible(on)
        self._nb_label.setVisible(on)
        self.updateGeometries()

    def updateGeometries(self):
        super().updateGeometries()
        if getattr(self, "_nb_label", None) is not None:
            f = self.frameWidth()
            self._nb_label.setGeometry(f, f, self.verticalHeader().width(),
                                       self.horizontalHeader().height())

    def song_number_label(self, row: int) -> str:
        """The Nb. text of a table row: the title's place in the list, counted
        from 1, or blank for a header / empty slot."""
        songs = self._row_meta.song_rows()
        try:
            return str(songs.index(row) + 1)
        except ValueError:
            return ""

    def next_song_row(self, row: int, step: int) -> tuple[int, Path | None]:
        """First row holding a real song before/after `row` (step = -1 / +1),
        skipping round/dance headers. Returns (-1, None) at either end."""
        r = row + step
        while 0 <= r < len(self._row_meta):
            meta = self._row_meta[r]
            if meta:
                entry = meta.entry
                if entry is not None:
                    return r, entry.path
            r += step
        return -1, None

    # ── Regenerate a song ─────────────────────────────────────────────────────

    def _effective_anchor(self, round_name: str | None, exclude_rows: set):
        """Audio features to use as the round's timbral anchor for a regen/replace.

        The anchor is normally the round's FIRST song. But when that song is the one
        being re-rolled/replaced (its row is in `exclude_rows`), anchoring on it would
        just match the song we're removing — so fall back to the next song in the round
        (in display order) that still has features. Returns None when timbre is off or
        no surviving song in the round has features."""
        if not round_name or not self._use_timbre:
            return None
        for r, m in self._row_meta.numbered():
            if m.theme or m.round_name != round_name or r in exclude_rows:
                continue
            if m.entry.features is not None:
                return m.entry.features
        return None

    def _round_cls_style(self, round_name: str | None) -> tuple[str, str]:
        """Class + style a ↺ re-roll must respect — the round's own competition
        on a stacked 📅 day-plan deck, the deck's otherwise."""
        ctx = self._round_ctx.get(round_name or "") or {}
        return (ctx.get("cls") or self._dance_class,
                ctx.get("style") or self._style)

    def _regen(self, row: int):
        try:
            if row >= len(self._row_meta) or not self._row_meta[row]:
                return
            meta = self._row_meta[row]
            if meta.warmup and self._party_swap():
                self._swap_from_list_end(row)
                return
            if meta.warmup:
                self._regen_warmup(row)
                return
            if meta.theme:
                return   # theme rows have no round/tier context to regenerate from
            if not self._suggester or not self._playlist:
                return

            dance = meta.dance
            tier  = meta.tier

            # Build exclusion set: every current entry AND any library copy of it
            # (same filename / fingerprint), so a re-roll can't return a duplicate of
            # a song already planned here. Drop this slot's own song so it stays an
            # available fallback when no alternative exists.
            planned = self._row_meta.entries()
            exclude = self._exclude_with_dupes(planned)
            current = meta.entry
            if current and dance not in ALLOW_REPEAT:
                exclude.discard(str(current.path))

            r_cls, r_style = self._round_cls_style(meta.round_name)
            new_entry = self._suggester.regenerate(
                dance, r_cls, tier, exclude,
                prefer_fresh=meta.prefer_fresh,
                round_name=meta.round_name,
                use_timbre=self._use_timbre,
                strategy=meta.strategy or None,
                style=r_style,
                candidates=self._round_pools_by_name.get(meta.round_name),
                anchor=self._effective_anchor(meta.round_name, {row}),
            )
            if not new_entry:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            # If this row was playing, remember it so we can auto-play the new pick
            # in its place once the row is redrawn. Drop the play-row marker now (the
            # widget it points at is about to be replaced); playback switches in _after.
            was_playing = (row == self._current_play_row)
            if was_playing:
                self._current_play_row = -1

            # Update metadata + live playlist
            meta.entry = new_entry
            self._playlist[meta.round_name][meta.h_idx][meta.d_idx] = new_entry

            # Defer row redraw so it happens after the clicked signal returns.
            # Replacing a cell widget while inside its signal handler can crash.
            bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD

            def _after():
                self._fill_song_row(row, meta, bg)
                # If the replaced song was playing, immediately play the new one in
                # its place instead of leaving playback stopped.
                if was_playing and self._play_cb:
                    self._on_play_click(row, new_entry.path)
                # Keep the row selected AND the keyboard focus on the table so the
                # Space / Ctrl+R / Ctrl+N shortcuts keep firing after a re-roll.
                self.setCurrentCell(row, _COL_TITLE)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _after)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def _party_swap(self) -> bool:
        """Does ↺ swap within this list instead of re-rolling from the library?
        True on the ETDS party list: an Eintanzen list without a style (a
        per-class warm-up always has one) that is not a running order."""
        return self._warmup and not self._player_list and not self._warmup_style

    def _swap_from_list_end(self, row: int):
        """↺ on the party list: swap the title on `row` with one of the same
        dance from the end of the list (see warmup_swap_partner)."""
        song_rows = self._row_meta.song_rows()
        if row not in song_rows:
            return
        k = warmup_swap_partner(self._row_meta.entries(), song_rows.index(row))
        if k is None:
            dance = self._row_meta[row].dance
            _show_toast(self, i18n.t("↺  No other %s near the end of the list")
                        % dance_name(dance, dance))
            return
        partner = song_rows[k]
        # Deferred: the ↺ button that fired this is one of the widgets redrawn.
        QTimer.singleShot(0, lambda: self._swap_song_rows(row, partner))

    def _swap_song_rows(self, a: int, b: int):
        """Swap the titles on two song rows in place and redraw just those two.
        The playing title keeps playing; its marker moves with it."""
        ma, mb = self._row_meta.at(a), self._row_meta.at(b)
        if ma is None or mb is None or not ma.filled or not mb.filled:
            return
        self._row_meta.swap(a, b)
        song_rows = self._row_meta.song_rows()
        for r, m in ((a, ma), (b, mb)):
            for c in range(self.columnCount()):
                self._played_saved.pop((r, c), None)
            bg = _C_ROW_EVEN if song_rows.index(r) % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(r, m, bg)
            if r == self._current_play_row:
                self.sync_play_glyph()
        self._update_play_row_hl()
        self.setCurrentCell(a, _COL_TITLE)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        log.info("⇅ Titles swapped\n"
                 "row %d: %s\n"
                 "row %d: %s", a, ma.entry.title, b, mb.entry.title)
        self._notify_changed()

    def _regen_warmup(self, row: int):
        """Re-roll one warm-up row: pick a fresh timbre-matched, TSO-conform track
        of the same dance for this class (excluding tracks already in the list)."""
        meta = self._row_meta[row]
        if not self._suggester:
            return
        dance = meta.dance or ""
        # Exclude tracks already in THIS list AND any track planned in the open
        # playlist decks, so a re-roll never picks music used elsewhere.
        exclude = self._row_meta.paths()
        try:
            exclude |= self.host.planned_paths()
        except Exception as exc:
            log.debug("♻️ Deck dedup index unavailable — re-roll may reuse a planned track: %s", exc)
        current = meta.entry
        new_entry = self._suggester.regenerate_warmup(
            dance, self._warmup_style, self._warmup_class, exclude,
            anchor_entry=current, relax=self._warmup_relax,
        )
        if not new_entry:
            QMessageBox.information(self, "Regenerate",
                                    "No alternative Eintanzen track found.")
            return
        was_playing = (row == self._current_play_row)
        if was_playing:
            self._current_play_row = -1
        meta.entry = new_entry
        bg = _C_ROW_EVEN if row % 2 == 0 else _C_ROW_ODD

        def _after():
            self._fill_song_row(row, meta, bg)
            if was_playing and self._play_cb:
                self._on_play_click(row, new_entry.path)
            self.setCurrentCell(row, _COL_TITLE)
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self._notify_changed()
        QTimer.singleShot(0, _after)

    def _regen_dance(self, round_name: str, d_idx: int, dance: str):
        """Re-roll EVERY heat of one dance within one round.

        Same behaviour as the per-song ↺ (honours the round's strategy, BPM,
        class and timbre), but applied to the whole dance segment at once. Other
        dances and other rounds stay untouched; picks stay unique across the
        whole playlist (except ALLOW_REPEAT dances, e.g. PD)."""
        try:
            if not self._suggester or not self._playlist:
                return

            # Rows that hold this dance in this round.
            target_rows = [
                r for r, m in enumerate(self._row_meta)
                if m and not m.theme
                and m.round_name == round_name and m.d_idx == d_idx
            ]
            if not target_rows:
                return

            # Exclude every other current entry across the whole playlist (and any
            # library copy of it), but NOT the ones we're replacing, so other slots
            # stay unique and no duplicate of a planned song can be re-picked.
            replacing = set(target_rows)
            keep = [m.entry for r, m in self._row_meta.numbered()
                    if r not in replacing]
            exclude = self._exclude_with_dupes(keep)

            # Anchor on the first surviving song NOT in this dance segment, so re-rolling
            # the anchor dance (e.g. the first one) matches the rest of the round.
            seg_anchor = self._effective_anchor(round_name, replacing)

            # Remember which row (if any) in this segment was playing so we can
            # auto-play its replacement once the rows are redrawn.
            playing_row = -1
            picked_any = False
            r_cls, r_style = self._round_cls_style(round_name)
            for r in target_rows:
                meta = self._row_meta[r]
                new_entry = self._suggester.regenerate(
                    dance, r_cls, meta.tier, exclude,
                    prefer_fresh=meta.prefer_fresh,
                    round_name=meta.round_name,
                    use_timbre=self._use_timbre,
                    strategy=meta.strategy or None,
                    style=r_style,
                    candidates=self._round_pools_by_name.get(meta.round_name),
                    anchor=seg_anchor,
                )
                if not new_entry:
                    continue
                picked_any = True
                # Keep heats within this dance unique (PD may repeat) — exclude the
                # pick AND its library copies so a later heat can't grab a duplicate.
                if dance not in ALLOW_REPEAT:
                    exclude |= self._exclude_with_dupes([new_entry])

                # Drop the play-row marker if this row was playing — its widget is
                # about to be replaced; playback switches to the new pick in _redraw.
                if r == self._current_play_row:
                    playing_row = r
                    self._current_play_row = -1

                meta.entry = new_entry
                self._playlist[meta.round_name][meta.h_idx][meta.d_idx] = new_entry

            if not picked_any:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            # Defer redraw so widgets aren't replaced inside the clicked handler.
            def _redraw():
                for r in target_rows:
                    meta = self._row_meta[r]
                    bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, meta, bg)
                # If a song in this segment was playing, play its replacement now.
                if playing_row >= 0 and self._play_cb:
                    new_entry = self._row_meta[playing_row].entry
                    if new_entry is not None:
                        self._on_play_click(playing_row, new_entry.path)
                # Keep keyboard focus on the table so shortcuts keep working.
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _redraw)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def _regen_round(self, round_name: str):
        """Re-roll EVERY dance / heat of one whole round at once.

        Like the per-dance ↺ but applied to the entire round: each dance is
        re-rolled from its own pool (honouring the round's strategy, BPM, class
        and timbre), picks stay unique across the whole playlist (except
        ALLOW_REPEAT dances, e.g. PD). Other rounds stay untouched."""
        try:
            if not self._suggester or not self._playlist:
                return

            # Group this round's song rows by dance, preserving display order.
            rows_by_dance: dict[int, list[int]] = {}
            for r, m in enumerate(self._row_meta):
                if (m and not m.theme
                        and m.round_name == round_name):
                    rows_by_dance.setdefault(m.d_idx, []).append(r)
            if not rows_by_dance:
                return

            all_rows = [r for rows in rows_by_dance.values() for r in rows]
            playing_row = -1
            picked_any  = False

            # Re-roll dance by dance. `exclude` is rebuilt per dance so that
            # already-replaced dances (with their new picks) and untouched
            # rounds keep every slot unique.
            for d_idx in sorted(rows_by_dance):
                seg_rows = rows_by_dance[d_idx]
                dance    = self._row_meta[seg_rows[0]].dance

                replacing = set(seg_rows)
                keep = [m.entry for r, m in self._row_meta.numbered()
                        if r not in replacing]
                exclude = self._exclude_with_dupes(keep)

                seg_anchor = self._effective_anchor(round_name, replacing)

                r_cls, r_style = self._round_cls_style(round_name)
                for r in seg_rows:
                    meta = self._row_meta[r]
                    new_entry = self._suggester.regenerate(
                        dance, r_cls, meta.tier, exclude,
                        prefer_fresh=meta.prefer_fresh,
                        round_name=round_name,
                        use_timbre=self._use_timbre,
                        strategy=meta.strategy or None,
                        style=r_style,
                        candidates=self._round_pools_by_name.get(round_name),
                        anchor=seg_anchor,
                    )
                    if not new_entry:
                        continue
                    picked_any = True
                    if dance not in ALLOW_REPEAT:
                        exclude |= self._exclude_with_dupes([new_entry])

                    if r == self._current_play_row:
                        playing_row = r
                        self._current_play_row = -1

                    meta.entry = new_entry
                    self._playlist[round_name][meta.h_idx][meta.d_idx] = new_entry

            if not picked_any:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            def _redraw():
                for r in all_rows:
                    meta = self._row_meta[r]
                    bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, meta, bg)
                if playing_row >= 0 and self._play_cb:
                    new_entry = self._row_meta[playing_row].entry
                    if new_entry is not None:
                        self._on_play_click(playing_row, new_entry.path)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _redraw)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def update_strategy(self, round_name: str, strategy: str, prefer_fresh: bool):
        """Update the stored strategy for every row of a round WITHOUT re-rolling.

        Lets the ↺ buttons (per-song / per-dance) draw from the newly selected
        strategy's pool while the already-generated grid stays untouched."""
        for m in self._row_meta:
            if m and m.round_name == round_name:
                m.strategy     = strategy or ""
                m.prefer_fresh = prefer_fresh

    def set_round_pool(self, round_name: str, pool):
        """Update the candidate pool a round's ↺ buttons draw from (Past
        Competitions 🎯 scope), without re-rolling the grid. `pool=None` means
        the full library (🎯 unticked)."""
        self._round_pools_by_name[round_name] = pool

    def set_use_timbre(self, on: bool):
        """Toggle timbre-similarity scoring for the ↺ buttons live, without
        re-rolling the grid (anchors stay cached on the suggester)."""
        self._use_timbre = on


# Late-bind the concrete class into the mixin modules: their methods
# isinstance-check drag sources against PlaylistTable, but a top-level import
# there would be circular. Module globals resolve at call time, so this is
# all they need.
table_dnd.PlaylistTable = PlaylistTable
table_dynamic.PlaylistTable = PlaylistTable
table_actions.PlaylistTable = PlaylistTable
