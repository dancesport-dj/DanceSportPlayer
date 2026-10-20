"""The playlist grid widget (drag & drop, play toggle, per-row regen).

Extracted from dancesport_gui.py (view split): PlaylistTable is the editable
song grid used by every deck and the wishlist. Shared GUI primitives come from
gui.dialogs / gui.workers; planner data types from dancesport_planner. Filling
the grid (playlist, theme, warm-up, player list, wishlist) is in
gui.table.table_load, the ↺ re-rolls in gui.table.table_regen, the columns and
the Nb. gutter in gui.table.table_columns.
"""
import html
import logging

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
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
from planner.music.db import AudioCache
from planner.models import MusicEntry, RoundConfig
from planner.terms import dance_name
from planner.generate.suggester import PlaylistSuggester
from planner.generate.warmup import warmup_code
from planner.playlist.checks import FLAG_EDGE_SILENCE, is_final_round
from planner.playing.play_sets import dblclick_ask_of
from planner.music.parsing import _fmt_bpm
from planner import i18n
from gui.common import (
    CUSTOM_HEADER_TIP,
    _C_DEFAULT,
    _C_NEW_FG,
    _C_POP_FG,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _C_SIM_FG,
    _C_LEN_WARN_FG,
    _C_WARN_FG,
    bpm_tooltip,
    display_title,
    _entry_tooltip,
    _fmt_track_secs,
    _open_in_default_player,
    set_header_tip,
    stopwatch_header,
)
from shared.columns import (
    _COL_ARTIST,
    _COL_BPM,
    _COL_CLASS,
    _COL_CUSTOM,
    _COL_DANCE,
    _COL_FILE,
    _COL_HEAT,
    _COL_LEN,
    _COL_PLAY,
    _COL_POP,
    _COL_RATING,
    _COL_REGEN,
    _COL_TITLE,
    _N_COLS,
)
from gui.table.row_buttons import BUTTON_ROLE, LOOK_ROLE, PATH_ROLE, RowButtonDelegate
from gui.decks.running_order import Row, RunningOrder
from gui.table.star_rating import RATING_ROLE, StarDelegate
from gui.table.table_dnd import TableDragDropMixin
from gui.table.table_dynamic import DynamicModeMixin
from gui.table.table_load import TableLoadMixin, _C_MISSING_BG
from gui.table.table_regen import TableRegenMixin
from gui.table.table_columns import TableColumnsMixin
from gui.table.table_actions import TableActionsMixin
from gui.table.table_host import TableHost
from gui.table import table_dnd
from gui.table import table_dynamic
from gui.table import table_actions

log = logging.getLogger("dancesport.gui.playlist_table")


# "Marked for potential replace" (dynamic decks): a light-orange row underlay and
# an orange title — no ❗, which belongs to a missing file alone.
_C_MARK_BG = QColor(255, 224, 178)
_C_MARK_FG = QColor(216, 96, 24)

# 📌 Pinned: the orange mark's look in lila. The title sits out the round's ↻
# and the dance's ↺ re-rolls.
_C_PIN_BG = QColor(231, 214, 247)
_C_PIN_FG = QColor(122, 63, 176)

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
    _PIN_SEL = QColor(140, 82, 196)   # …and the lila one of a 📌 pinned row

    def __init__(self, table: PlaylistTable):
        super().__init__(table)
        self._table = table

    def paint(self, painter, option, index):
        sel = None
        if option.state & QStyle.StateFlag.State_Selected:
            row = index.row()
            sel = (self._SEL if self._table._is_row_marked(row)
                   else self._PIN_SEL if self._table._is_row_pinned(row) else None)
        if sel is not None:
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            opt.palette.setColor(QPalette.ColorRole.Highlight, sel)
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
class PlaylistTable(TableColumnsMixin, TableRegenMixin, TableLoadMixin,
                    TableDragDropMixin, DynamicModeMixin, TableActionsMixin,
                    QTableWidget):
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
        self._init_state()
        self._build_drag_overlays()
        self._build_advance_button()
        # Tracks already played this session (playing mode greys them out).
        self._played_paths: set = set()
        self._played_saved: dict[tuple[int, int], QBrush] = {}
        # Songs the user flagged "for potential replace" (dynamic decks), keyed by file
        # path so the orange mark survives structural re-renders. Persisted per deck
        # in the autosave/undo snapshot ("marked" key of _serialize_playlist_state).
        self._marked_paths: set = set()
        # 📌 Pinned titles, keyed by path like the marks: the ↻ / ↺ re-rolls of
        # their round or dance leave them where they are. Persisted per deck
        # ("pinned" key of the snapshot).
        self._pinned_paths: set = set()
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

        self._build_columns()
        self._build_headers()
        self._configure_view()

    def _init_state(self):
        """The list's own state: its modes, the window's callbacks, the play cursor."""
        # The glide of the auto-play scroll, built on first use and reused after.
        self._scroll_anim = None
        # The .m3u this list was loaded from or last saved to (📂 Show in Explorer
        # on the header, 🖼 the playlist's own cover); None = never a file.
        self._m3u_path: Path | None = None
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
        # Row → "Heat 2" in such a list, derived from its order (_paint_player_heats).
        self._player_heat_text: dict[int, str] = {}
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
        self._short_secs_cb: Callable[[str], int] | None = None   # dance → length
        # Set by MainWindow: fn(entry) → seconds the track will really PLAY once
        # the 🔇 stillness skip has cut the dead air off its edges, or None when
        # the track was never probed. Reported in the cell's tooltip whenever it
        # differs from the file's length, flagged or not.
        self._play_secs_cb: Callable[[MusicEntry], int | None] | None = None
        # Longest single edge of stillness, in seconds — what decides the amber ⏱
        # (see planner.playlist.checks.FLAG_EDGE_SILENCE).
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

    def _build_drag_overlays(self):
        """Drag auto-scroll, the drop line / row highlight and the playing-row marker."""
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

    def _build_advance_button(self):
        """The ⏭/✋ auto-advance switch the deck box lays out next to Σ."""
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
        # What this list stood on before 🎉/🏆 was pressed on it: the way back
        # when the lit set is clicked off (`_leave_set`). Never saved.
        self._before_set: dict | None = None
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

    def _build_columns(self):
        """Column captions, header tooltips, cell delegates and the column-tick state."""
        self.setHorizontalHeaderLabels(
            ["Dance", "Heat", "▶", "Artist", "Title", "BPM", "⏱", "Pop", "Class", "★",
             "Custom", "File name", "↺"]
        )
        stopwatch_header(self, _COL_LEN)
        set_header_tip(self, _COL_LEN,
            "Track length (m:ss)\n"
            "orange = shorter than the configured play length, or 5 s or more\n"
            "of stillness at an edge that the player skips (the cell's own\n"
            "tooltip says which, and how long it really plays)"
        )
        set_header_tip(self, _COL_CLASS,
            "≈  timbral similarity to round anchor\n"
            "    (only shown after running Audio Analysis)\n"
            "[D,C,…]  class tags from MP3 COMM field"
        )
        set_header_tip(self, _COL_RATING,
            "Rating — click a star to set it, the last lit one again to clear it.\n"
            "Kept in the app's database; the MP3 itself is not changed."
        )
        self.setItemDelegateForColumn(_COL_RATING, StarDelegate(self._on_star_clicked, self))
        buttons = RowButtonDelegate(self, self._on_row_button, self._is_row_marked)
        self.setItemDelegateForColumn(_COL_PLAY, buttons)
        self.setItemDelegateForColumn(_COL_REGEN, buttons)
        set_header_tip(self, _COL_CUSTOM, CUSTOM_HEADER_TIP)
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

    def _build_headers(self):
        """Column widths and resizing, the column menu and the Nb. number column."""
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
                     (_COL_CUSTOM, 90), (_COL_FILE, 220), (_COL_REGEN, 30)):
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

    def _configure_view(self):
        """Selection, drag-and-drop, scrolling and the click / double-click wiring."""
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
        if row < 0 or not self.play_glyph(row):
            return
        if not self.pauses_on_stop():
            self._set_play_glyph(row, playing is not None or not self._player_stopped())
            return
        if playing is None:
            playing = self.host.is_player_running()
        self._set_play_glyph(row, playing)

    def play_glyph(self, row: int) -> str:
        """The ▶ / ■ on `row`'s play button, "" where the row has none."""
        it = self.item(row, _COL_PLAY)
        return (it.data(BUTTON_ROLE) or "") if it is not None else ""

    def _set_play_glyph(self, row: int, playing: bool):
        it = self.item(row, _COL_PLAY)
        if it is not None and it.data(BUTTON_ROLE):
            it.setData(BUTTON_ROLE, "■" if playing else "▶")

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
        # A warm-up / running-order row takes its dance from the title, and so
        # do the ─── strips and "Heat n" around it: a re-tag to another dance
        # re-cuts the whole list.
        moved = [m for _r, m in self._row_meta.numbered()
                 if m.warmup and m.path_str in wanted
                 and m.dance != (warmup_code(m.entry) or m.entry.dance or "")]
        if moved:
            self._reload_warmup(rebuild=True)
            return len(moved)
        done = flat = 0
        for r, m in self._row_meta.numbered():
            p = m.path_str
            if m.theme:
                flat += 1
            if not p or p not in wanted:
                continue
            if m.theme:
                # A wishlist / theme row: its dance is the title's own, not a
                # heat's, so a re-tag to another dance shows there.
                m.dance = m.entry.dance or ""
                bg = _C_ROW_EVEN if (flat - 1) % 2 == 0 else _C_ROW_ODD
            else:
                bg = _C_ROW_EVEN if (m.h_idx or 0) % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(r, m, bg)
            if r == self._current_play_row:
                self.sync_play_glyph()   # a fresh fill says ▶
            done += 1
        return done

    def refresh_found(self, path) -> int:
        """Repaint the rows that still show `path` as missing, now it plays
        again (renamed back, drive plugged in) — a play only swaps the glyph."""
        p = str(path)
        if not any(m.path_str == p and (it := self.item(r, _COL_PLAY)) is not None
                   and it.data(LOOK_ROLE) == "missing"
                   for r, m in self._row_meta.numbered()):
            return 0
        return self.refresh_paths([path])

    def flash_rows(self, rows: list[int],
                   color: QColor | None = None, msec: int = 2400):
        """Briefly tint the given rows (then restore their exact backgrounds) so the
        user can SEE which songs an undo/redo just changed. Captures each cell's
        current brush and restores it, so it works for any row type."""
        if color is None:
            color = QColor(255, 236, 160)
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

    def dblclick_asks(self) -> bool:
        """❓ True where a double-click on another title asks before it stops
        the one on the speakers — part of both play sets (⚙ Settings → 🎛
        Play sets) and on in both. A list saved before it existed asks; a
        window that keeps no list values asks as the 🏆 set does."""
        vals = self.host.list_vals()
        if vals is not None:
            return bool(vals.get("dblclick_ask", True))
        return dblclick_ask_of(self.host.settings(), "tournament")

    def _ask_stop_playing(self, title: str) -> bool:
        """Yes/No: stop the playing title for `title`. Defaults to No, so a
        stray Enter keeps the music on the floor."""
        text = (i18n.t("A title is playing. Stop it and start “%s”?")
                if self.dblclick_plays()
                else i18n.t("A title is playing. Stop it and cue “%s”?"))
        ans = QMessageBox.question(
            self, i18n.t("Stop the playing title?"), text % title,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return ans == QMessageBox.StandardButton.Yes

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

        A double-click on ANOTHER row stops the playing title just the same,
        whether it plays or cues the new one — so while music is on it asks
        first, unless the list's ❓ play value says not to (`dblclick_asks`).
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
        if (self.host.is_player_running() and self.dblclick_asks()
                and not self._ask_stop_playing(entry.title)):
            return
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

    def _fill_song_row(self, row: int, meta: Row, bg: QColor):
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
            return it

        ctr = Qt.AlignmentFlag.AlignCenter
        is_backup = meta.backup
        sim = (self._suggester.similarity(entry, meta.round_name)
               if entry and self._suggester else None)
        missing, marked, pinned, issue_text = self._row_flags(entry)
        if missing:
            bg = _C_MISSING_BG
        elif issue_text:
            bg = _C_ISSUE_BG
        elif marked and not missing:
            bg = _C_MARK_BG
        elif pinned:
            bg = _C_PIN_BG

        # Dance column (also holds path for drag)
        cell(_COL_DANCE, "" if is_backup else self._dance_label(dance))

        # Heat column
        if is_backup:
            cell(_COL_HEAT, f"↳ backup {meta.backup_n or ''}".rstrip(), align=ctr)
        elif meta.warmup:
            cell(_COL_HEAT, self._player_heat_text.get(row, ""), align=ctr)
        else:
            cell(_COL_HEAT, f"Heat {h_idx + 1}" if multi else "", align=ctr)

        if entry:
            pin = "📌 " if pinned else ""
            shown = display_title(entry)
            title_txt = ("    " + pin + shown[:61]) if is_backup else pin + shown[:65]
            resume_ms = self._resume_marks.get(str(entry.path))
            if resume_ms:
                title_txt += f"   ↩ {_fmt_track_secs(resume_ms // 1000)}"
            cell(_COL_TITLE, title_txt,
                 fg=(_C_WARN_FG if missing else _C_MARK_FG if marked
                     else _C_PIN_FG if pinned
                     else _C_NEW_FG if is_backup else _C_DEFAULT))
            # Hover the title → same rich track description as the Similar-Tracks window.
            title_it = self.item(row, _COL_TITLE)
            if title_it is not None:
                if missing:
                    title_it.setToolTip(i18n.t("⚠ File not found on disk:\n%s") % entry.path)
                else:
                    tip = self._title_tooltip(entry, sim, resume_ms, marked, issue_text)
                    title_it.setToolTip(tip)

            cell(_COL_ARTIST, getattr(entry, "tag_artist", None) or "")
            artist_it = self.item(row, _COL_ARTIST)
            if artist_it is not None:
                artist_it.setToolTip(_entry_tooltip(entry))

            bpm_s = _fmt_bpm(entry.bpm, dance, dance_class).strip()
            bpm_fg = QColor(200, 130, 80) if bpm_s.endswith("*") else _C_DEFAULT
            cell(_COL_BPM, bpm_s, fg=bpm_fg, align=ctr).setToolTip(bpm_tooltip(entry))

            self._fill_length_cell(row, cell, entry, ctr)

            if entry.popularity:
                cell(_COL_POP, f"★{entry.popularity}", fg=_C_POP_FG, align=ctr)
            else:
                cell(_COL_POP, i18n.t("✦new"), fg=_C_NEW_FG, align=ctr)

            self._fill_class_cell(cell, entry, sim, ctr)
            cell(_COL_RATING, "").setData(RATING_ROLE, entry.rating or 0)
            custom_it = cell(_COL_CUSTOM, entry.custom or "")
            if entry.custom:
                custom_it.setToolTip(entry.custom)
            cell(_COL_FILE, entry.title or "").setToolTip(str(entry.path))
        else:
            cell(_COL_TITLE, "⚠  No song found", fg=_C_WARN_FG)
            for c in (_COL_ARTIST, _COL_BPM, _COL_LEN, _COL_POP, _COL_CLASS, _COL_RATING,
                      _COL_CUSTOM, _COL_FILE):
                cell(c, "")

        self._fill_row_buttons(row, meta, bg, missing, marked)

        self.setRowHeight(row, 24)

    def _fill_class_cell(self, cell, entry, sim, ctr):
        """Class column: ≈ for a sound-alike, then the classes it suits."""
        cls_parts = []
        if sim is not None and sim >= 0.7:
            cls_parts.append("≈")
        if entry.classes_ok:
            cls_parts.append(f"[{','.join(entry.classes_ok)}]")
        cls_fg = _C_SIM_FG if cls_parts and cls_parts[0] == "≈" else _C_DEFAULT
        cell(_COL_CLASS, " ".join(cls_parts), fg=cls_fg, align=ctr)

    def _row_flags(self, entry):
        """What colours this title's row: missing file, replace mark, 📌 pin, open issue."""
        # Flag tracks whose file has vanished from disk since the playlist was made
        # (moved / deleted / drive offline) — red title + a red ❗ in the last column.
        missing = bool(entry) and not Path(entry.path).exists()
        # "Marked for potential replace": orange row underlay + an orange title.
        # A genuinely missing file wins the styling (its red ❗ is the more urgent flag).
        marked = bool(entry is not None and getattr(entry, "path", None)
                      and str(entry.path) in self._marked_paths)
        # 📌 Pinned: the same look in lila, below the orange mark.
        pinned = bool(entry is not None and getattr(entry, "path", None)
                      and str(entry.path) in self._pinned_paths)
        # Live Check-Music issue (play length / takt / round tempo spread): the
        # row stays RED until the issue is resolved. Red outranks the orange
        # replace-mark; a genuinely missing file keeps its own styling.
        issue_text = (self._issue_paths.get(str(entry.path))
                      if entry is not None and getattr(entry, "path", None) else None)
        return missing, marked, pinned, issue_text

    def _title_tooltip(self, entry, sim, resume_ms, marked, issue_text):
        """The title's hover text, with the resume / mark / issue notes on top."""
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
        return tip

    def _fill_length_cell(self, row: int, cell, entry, ctr):
        """The ⏱ cell: the length, amber when it plays short or trims long silence."""
        secs = int(getattr(entry, "duration", 0) or 0)
        if secs:
            play = self._play_secs_cb(entry) if self._play_secs_cb else None
            play_secs = int(play) if play is not None else secs
            trimmed = play_secs != secs
            # Red is for an edge long enough to notice on the floor, not for
            # every file with a couple of seconds of room tone (which is
            # most of them). The tooltip still reports any trim.
            edge = self._edge_silence_cb(entry) if self._edge_silence_cb else 0.0
            flagged = trimmed and edge >= FLAG_EDGE_SILENCE
            meta = self._row_meta.at(row)
            limit = (self._short_secs_cb(meta.dance if meta is not None else "")
                     if self._short_secs_cb else 0)
            too_short = bool(limit) and play_secs < limit
            # Orange, not red: red in this table is a file that is MISSING,
            # and a track that merely ends early is not that. Both length
            # warnings share the amber; the tooltip says which one fired.
            fg = _C_LEN_WARN_FG if (flagged or too_short) else _C_DEFAULT
            len_it = cell(_COL_LEN, _fmt_track_secs(secs), fg=fg, align=ctr)
            tips = []
            if trimmed:
                tips.append(
                    i18n.t("Plays %s — the stillness at the edges of the file is skipped")
                    % _fmt_track_secs(play_secs))
            if too_short:
                tips.append(i18n.t("Shorter than the configured play length (%s)")
                            % _fmt_track_secs(limit))
            if tips:
                len_it.setToolTip("\n".join(tips))
        else:
            cell(_COL_LEN, "", align=ctr)

    def _fill_row_buttons(self, row: int, meta, bg: QColor, missing: bool, marked: bool):
        """The ▶ and ↺ cells, or ❗ where the file is gone."""
        entry = meta.entry
        ctr = Qt.AlignmentFlag.AlignCenter
        # ── Play button ── (painted by RowButtonDelegate; a click reads its row
        # off the index then, so a row removed above never plays the wrong track)
        def cell_button(col, glyph, look, tip=""):
            it = QTableWidgetItem()
            it.setData(BUTTON_ROLE, glyph)
            it.setData(LOOK_ROLE, look)
            it.setBackground(bg)                # the row's tint runs under the button
            if tip:
                it.setToolTip(tip)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.setItem(row, col, it)
            return it

        if self.cellWidget(row, _COL_REGEN) is not None:   # a header's ↺ held the cell
            self.removeCellWidget(row, _COL_REGEN)
        # Playing mode hides the ↺ column — the ▶ is what stays on screen, and
        # it could not play the file anyway. One ❗ per row, so ↺ then stays ↺.
        missing_on_play = missing and bool(self._play_cb)
        if missing_on_play:
            cell_button(_COL_PLAY, "❗", "missing",
                   i18n.t("⚠ File not found on disk:\n%s") % entry.path
                   ).setData(PATH_ROLE, entry.path)
        elif entry and self._play_cb:
            cell_button(_COL_PLAY, "▶", "plain").setData(PATH_ROLE, entry.path)
        else:
            cell_button(_COL_PLAY, "▶", "off")

        # ── Regenerate button ── (a flat Wishlist has no rounds to re-roll from)
        if not self._flat_mode:
            if self._party_swap():
                dname = dance_name(meta.dance, meta.dance) or "title"
                regen_hint = (i18n.t("↺ click to swap it with a %s from the end "
                                     "of the list") % dname)
            else:
                regen_hint = i18n.t("↺ click to re-roll a replacement")
            if missing and not missing_on_play:
                cell_button(_COL_REGEN, "❗", "missing",
                       i18n.t("⚠ File not found on disk:\n%s") % entry.path
                       + "\n\n" + regen_hint)
            elif marked:
                # The orange row is the mark — a ❗ here read like a missing file.
                cell_button(_COL_REGEN, "↺", "plain",
                       i18n.t("🔁 Marked for potential replace  "
                              "(Ctrl+M to toggle)") + "\n" + regen_hint)
            elif self._party_swap():
                cell_button(_COL_REGEN, "↺", "plain",
                       i18n.t("Swap with a %s from the end of the list — a "
                              "leftover that fits no round first, else one from "
                              "the last third  (Ctrl+R / Ctrl+N)")
                       % dname)
            else:
                cell_button(_COL_REGEN, "↺", "plain",
                       "Re-roll this song — best timbre match first  (Ctrl+R / Ctrl+N)")
        elif missing and not missing_on_play:
            # Flat list (wishlist / Eintanzen) has no ↺ button — mark the dead file
            # with a red ❗ in the last column instead.
            warn = QTableWidgetItem("❗")
            warn.setBackground(bg)
            warn.setForeground(_C_WARN_FG)
            warn.setTextAlignment(ctr)
            warn.setToolTip(i18n.t("⚠ File not found on disk:\n%s") % entry.path)
            warn.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.setItem(row, _COL_REGEN, warn)

    # ── Play / stop toggle ────────────────────────────────────────────────────

    def _on_row_button(self, row: int, col: int):
        """A row's ▶ or ↺ was clicked (RowButtonDelegate)."""
        if col == _COL_PLAY:
            it = self.item(row, _COL_PLAY)
            path = it.data(PATH_ROLE) if it is not None else None
            if path is not None:
                self._on_play_click(row, path)
        elif col == _COL_REGEN:
            self._regen(row)

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
            self._set_play_glyph(row, False)
            self._current_play_row = -1
            if self._play_cb:
                self._play_cb(None)
        else:
            # Different row (or nothing playing) → switch
            if self._current_play_row >= 0:
                self._set_play_glyph(self._current_play_row, False)
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
            self._set_play_glyph(self._current_play_row, False)
        self._current_play_row = row
        self.sync_play_glyph()   # cued, not started → ▶ at the desk
        if scroll:
            self.scroll_row_into_play_view(row)
        self._update_play_row_hl()

    def on_playback_stopped(self):
        """Call this when the media player stops naturally (end of song)."""
        if self._current_play_row >= 0:
            row = self._current_play_row
            self._set_play_glyph(row, False)
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


# Late-bind the concrete class into the mixin modules: their methods
# isinstance-check drag sources against PlaylistTable, but a top-level import
# there would be circular. Module globals resolve at call time, so this is
# all they need.
table_dnd.PlaylistTable = PlaylistTable
table_dynamic.PlaylistTable = PlaylistTable
table_actions.PlaylistTable = PlaylistTable
