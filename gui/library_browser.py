"""The library browser pane (searchable table of the whole music library).

Extracted from dancesport_gui.py (view split): LibraryBrowser plus its small
table/item subclasses (_LibTable, _LibSortItem, _LibPlayItem).
"""
import gc
import logging
import time
from datetime import date

from PySide6.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QMimeData,
    QSize,
    QTimer,
    QUrl,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QDrag,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QStyle,
    QStyleOptionComboBox,
    QStylePainter,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from collections.abc import Callable
from typing import Any, cast
from planner.models import DANCE_NAMES, TEMPO_RANGES, MusicEntry
from planner.terms import dance_name, genre_name
from planner import i18n
from planner.models import (  # auto-resolved
    DEFAULT_DANCES,
    LIBRARY_CATEGORIES,
    is_non_turnier,
    library_category,
)
from planner.music.vocals import entry_is_instrumental
from planner.generate.warmup import warmup_code
from gui.common import (
    CUSTOM_HEADER_TIP,
    DANCE_SHORT,
    _C_NEW_FG,
    _PROVEN_MIN_PLAYS,
    _C_POP_FG,
    _entry_tooltip,
    _fmt_track_secs,
    _open_in_default_player,
    add_custom_mapping_action,
    bpm_tooltip,
    display_title,
    reveal_in_explorer,
    set_header_tip,
    stopwatch_header,
)
from gui.table.star_rating import RATING_ROLE, StarDelegate
from shared.widgets import (
    FlowLayout,
    _show_toast,
)

log = logging.getLogger("dancesport.gui.library_browser")

# The pane's own columns. Only the ones the header menu has to reason about are
# named; the row filler below writes the first ten by number as it always has.
_LIB_COL_PLAY = 0
_LIB_COL_DANCE = 1
_LIB_COL_TITLE = 3
_LIB_COL_LEN = 5
_LIB_COL_RATING = 10   # ★ came last: the sections are movable, a saved order is by index
_LIB_COL_CUSTOM = 11   # …and Custom after it
_LIB_COL_FILE = 12     # …and the cleaned-up file name after that
_LIB_COL_ALBUM = 13    # …and the ID3 album tag last

# 📚 A fill writes this many rows at once (a filtered list is all there before
# the call returns), then the rest in chunks between turns of the event loop,
# as many per turn as fit in the budget (seconds).
_FILL_FIRST = 500
_FILL_CHUNK = 250
_FILL_BUDGET = 0.025
# A fill still running after this long shows its count at the table's foot;
# a short one (the favorites) never flashes it.
_PROGRESS_AFTER = 0.3


def _classes_label(e: MusicEntry) -> str:
    classes = getattr(e, "classes_ok", None) or []
    return f"[{','.join(classes)}]" if classes else ""


class _LibSortItem(QTableWidgetItem):
    """Sorts by the numeric UserRole payload (text comparison as fallback)."""

    def __lt__(self, other):
        a = self.data(Qt.ItemDataRole.UserRole)
        b = other.data(Qt.ItemDataRole.UserRole)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(other)


class _LibPlayItem(QTableWidgetItem):
    """▶/■ cell: sorts by its track path, NOT the marker text — so flipping
    the marker while the table is sorted by this column never reorders rows."""

    def __lt__(self, other):
        a = self.data(Qt.ItemDataRole.UserRole)
        b = other.data(Qt.ItemDataRole.UserRole)
        return str(a or "") < str(b or "")


class _LoadOverlay(QFrame):
    """What the browser is loading, on top of its table.

    While the whole library loads it covers the table: the favorites under it
    are not what was asked for. While the rows are written it is a strip at
    the table's foot, and clicks go through to the rows above. Either way the
    rest of the window keeps working."""

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._view = table
        self.setObjectName("LibLoadOverlay")
        self.setAutoFillBackground(True)
        self.setStyleSheet("QFrame#LibLoadOverlay { background: palette(base);"
                           " border-top: 1px solid palette(mid); }")
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bar = QProgressBar(self)
        self.bar.setTextVisible(False)
        self.bar.setMaximumHeight(12)
        # The stretches centre the two in the cover and take no room in the strip.
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 4, 12, 6)
        lay.addStretch(1)
        lay.addWidget(self.label)
        lay.addWidget(self.bar, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        self.covering = False
        self.hide()

    def show_loading(self, text: str):
        """Cover the table, with a busy bar: the loader tells no count."""
        self.covering = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.label.setText(text)
        self.bar.setRange(0, 0)
        self.bar.setFixedWidth(260)
        self.place()
        self.show()
        self.raise_()

    def show_progress(self, text: str, done: int, total: int):
        """The strip at the foot, unless the table is covered."""
        if self.covering:
            return
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label.setText(text)
        self.bar.setRange(0, total)
        self.bar.setValue(done)
        self.place()
        self.show()
        self.raise_()

    def finish(self, covering: bool):
        """Hide the cover (`covering`) or the strip, whichever is up."""
        if covering == self.covering:
            self.covering = False
            self.hide()

    def place(self):
        vp = self._view.viewport().geometry()
        if self.covering:
            self.setGeometry(vp)
            return
        self.bar.setFixedWidth(max(60, vp.width() - 24))
        h = self.sizeHint().height()
        self.setGeometry(vp.x(), vp.y() + vp.height() - h, vp.width(), h)


class _HdrButton(QToolButton):
    """A header button as wide as its text plus the QSS padding: QToolButton's
    own size hint adds ~12 px of air on top, too wide next to the title."""

    def sizeHint(self):
        # 4 px padding + 1 px border per side, +1 so a glyph's overhang isn't clipped
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + 11,
                     super().sizeHint().height())

    def minimumSizeHint(self):
        return self.sizeHint()


class _ClassFilterCombo(QComboBox):
    """The class filter, several classes at once: a click on a class ticks
    it and leaves the list open for the next, "All classes" clears the ticks.

    The current index stays on "All classes"; the box paints `summary()`
    instead. Wheel and arrow keys still step through the classes one by
    one, each step picking just that class, as the plain combo did."""

    classesChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItem("All classes", "")
        for cls in ("D", "C", "B", "A", "S"):
            self.addItem(i18n.t("Class %s") % cls, cls)
            self._item(self.count() - 1).setCheckState(Qt.CheckState.Unchecked)
        # The combo's menu delegate draws a tick as a ~20 px menu check box;
        # an item-view one draws the style's own, as tall as the text. The rows
        # keep the menu's height, or they shrink to the text and are fiddly.
        self.setItemDelegate(QStyledItemDelegate(self))
        row_h = self.fontMetrics().height() + 8
        for i in range(self.count()):
            self._item(i).setSizeHint(QSize(0, row_h))
        self._pressed_in_list = False
        self.view().viewport().installEventFilter(self)
        self.currentIndexChanged.connect(self._on_index_changed)

    def _item(self, i: int):
        """Row i of the combo's own model, a QStandardItemModel: its items
        carry the ticks."""
        return cast(QStandardItemModel, self.model()).item(i)

    def classes(self) -> list[str]:
        """The ticked classes, D to S."""
        return [self.itemData(i) for i in range(1, self.count())
                if self._item(i).checkState() == Qt.CheckState.Checked]

    def set_classes(self, classes):
        if all(self.itemData(i) in classes for i in range(1, self.count())):
            classes = ()    # every class ticked is "All classes"
        for i in range(1, self.count()):
            self._item(i).setCheckState(
                Qt.CheckState.Checked if self.itemData(i) in classes
                else Qt.CheckState.Unchecked)
        self.update()
        self.classesChanged.emit()

    def summary(self) -> str:
        picked = self.classes()
        return i18n.t("Class %s") % " + ".join(picked) if picked else self.itemText(0)

    def showPopup(self):
        self._pressed_in_list = False
        super().showPopup()

    def eventFilter(self, obj, ev):
        # Runs before the popup's own filter, which would close the list.
        if ev.type() == QEvent.Type.MouseButtonPress:
            self._pressed_in_list = True
        elif ev.type() == QEvent.Type.MouseButtonRelease:
            row = self.view().indexAt(ev.position().toPoint()).row()
            # Fusion lays the list over the box, "All classes" under the
            # mouse: the release of the click that opened it lands there.
            if row == 0 and not self._pressed_in_list:
                return True
            if row > 0:
                cls = self.itemData(row)
                picked = self.classes()
                if cls in picked:
                    self.set_classes([c for c in picked if c != cls])
                    return True
                self.set_classes(picked + [cls])
                if not self.classes():
                    # The last class ticked them all, which is All classes: the
                    # list shuts rather than flicker its ticks away under the mouse.
                    self.hidePopup()
                return True
            if row == 0:
                self.hidePopup()
                self.set_classes(())
                return True
        return super().eventFilter(obj, ev)

    def _on_index_changed(self, index):
        if index > 0:
            cls = self.itemData(index)
            self.blockSignals(True)
            self.setCurrentIndex(0)
            self.blockSignals(False)
            self.set_classes([cls])

    def paintEvent(self, _ev):
        p = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = self.fontMetrics().elidedText(
            self.summary(), Qt.TextElideMode.ElideRight,
            self.style().subControlRect(QStyle.ComplexControl.CC_ComboBox, opt,
                                        QStyle.SubControl.SC_ComboBoxEditField,
                                        self).width())
        p.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        p.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, opt)


class _LibTable(QTableWidget):
    """Read-only library list whose rows drag out as file URLs — dropping one
    on a deck/wishlist behaves exactly like a file dragged in from Explorer."""

    space_cb: Callable[[int], None] | None = None   # set by LibraryBrowser
    seek_cb: Callable[[int], None] | None = None    # set by MainWindow
    context_menu_cb: Callable | None = None         # set by LibraryBrowser
    resize_cb: Callable | None = None               # set by LibraryBrowser
    tooltip_cb: Callable[[int, int], str] | None = None   # set by LibraryBrowser

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.resize_cb is not None:
            self.resize_cb()

    def viewportEvent(self, event):
        # A cell's hover text is built when the mouse rests on it, not stored on
        # every item at fill time: that was ~9 s of a 54 000-title fill. A cell
        # without one falls through to Qt, which shows the table's own help.
        if event.type() == QEvent.Type.ToolTip and self.tooltip_cb is not None:
            index = self.indexAt(event.pos())
            text = self.tooltip_cb(index.row(), index.column()) if index.isValid() else ""
            if text:
                QToolTip.showText(event.globalPos(), text, self.viewport(),
                                  self.visualRect(index))
                return True
        return super().viewportEvent(event)

    def contextMenuEvent(self, event):
        # Override the widget event directly — a viewport
        # customContextMenuRequested connection never fired here, so the
        # right-click menu silently did nothing.
        if self.context_menu_cb is not None:
            self.context_menu_cb(event)
        else:
            super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        """Space / Enter: play/stop the selected library row; Ctrl+←/→: seek
        ∓30 s — same shortcuts as in the decks."""
        key = event.key()
        if (key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() in (Qt.KeyboardModifier.NoModifier,
                                          Qt.KeyboardModifier.KeypadModifier)
                and self.space_cb is not None):
            row = self.currentRow()
            if row >= 0:
                self.space_cb(row)
                event.accept()
                return
        if (key in (Qt.Key.Key_Left, Qt.Key.Key_Right)
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and self.seek_cb is not None):
            self.seek_cb(-30000 if key == Qt.Key.Key_Left else 30000)
            event.accept()
            return
        super().keyPressEvent(event)

    def startDrag(self, _actions):
        rows = sorted({i.row() for i in self.selectedIndexes()})
        paths = [it.data(Qt.ItemDataRole.UserRole)
                 for r in rows if (it := self.item(r, 0))]
        paths = [p for p in paths if p]
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        mime.setText("\n".join(str(p) for p in paths))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
                  | Qt.DropAction.LinkAction, Qt.DropAction.CopyAction)


def fill_track_columns(table, fixed=None, artist_col=2, title_col=3):
    """Stretch a ▶/Dance/Artist/Title/BPM/⏱/Pop/Class list so it exactly fills
    its viewport — the narrow columns keep a fixed size, Artist and Title share
    the rest. Shared with the 🏆 tournament pane so the same track reads the
    same width in both lists; that pane carries an extra Round column and hands
    in its own `fixed` widths and Artist/Title positions."""
    vp_w = table.viewport().width()
    if vp_w < 80:
        return
    fixed = fixed if fixed is not None else {0: 30, 1: 90, 4: 52, 5: 52, 6: 52, 7: 70}
    # A column ticked away in the header menu claims no width, and the room it
    # used to take belongs to Artist and Title like the rest of the leftover.
    shown = {c: w for c, w in fixed.items() if not table.isColumnHidden(c)}
    rest = vp_w - sum(shown.values())
    hh = table.horizontalHeader()
    hh.blockSignals(True)
    for col, w in shown.items():
        table.setColumnWidth(col, w)
    if table.isColumnHidden(artist_col):
        table.setColumnWidth(title_col, max(120, rest))
    else:
        title_w = max(120, int(rest * 0.6))
        table.setColumnWidth(artist_col, max(80, rest - title_w))   # Artist sits LEFT
        table.setColumnWidth(title_col, title_w)
    hh.blockSignals(False)


# Roughly the resting label of every filter combo ("All categories" is the
# longest of them). Anything a user PICKS may be longer and is elided.
_FILTER_CHARS = 14


def cap_filter_combo(combo: QComboBox, chars: int = _FILTER_CHARS) -> QComboBox:
    """Let the resting label decide a filter's width, not its longest entry.

    A QComboBox asks for the width of its widest entry and refuses to shrink
    below it, so one wordy category label made the library pane that wide —
    and squeezed the 🔍 search box beside it down to a sliver. Capped, a long
    pick elides in the box while the list still opens at its full width.
    """
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(chars)
    combo.setMaximumWidth(combo.sizeHint().width())
    combo.view().setMinimumWidth(combo.view().sizeHintForColumn(0) + 24)
    return combo


class LibraryBrowser(QWidget):
    """Dockable library pane under the wishlists: filter by text / dance,
    sort by any column, drag tracks into the decks, double-click to preview.

    Folds to its header strip via the ▾ arrow (like the playlist decks) and
    can be hidden entirely with the 📚 toolbar toggle."""

    playRequested = Signal(object, int)   # (Path | None, table row) — None stops
    foldToggled = Signal(bool)            # folded? — MainWindow persists it
    columnOrderChanged = Signal(list)     # logical indices in visual order — persisted
    # Signal(object), NOT Signal(dict): PySide6 marshals a `dict`-typed signal arg to a
    # C++ QVariantMap, which only allows STRING keys — emitting our {int col -> width px}
    # map aborts the app ("Cannot copy-convert (dict) to C++"). `object` passes the Python
    # dict through untouched (int keys preserved).
    columnWidthsChanged = Signal(object)  # {logical col -> width px} — persisted
    columnsChanged = Signal(list)         # columns ticked away — persisted
    danceNamesChanged = Signal(bool)      # Dance column written short? — persisted
    unplannedToggled = Signal(bool)       # 🆕 filter on? — MainWindow feeds it the planned set
    wholeLibraryWanted = Signal()         # 🌐 clicked — MainWindow loads the global index
    wholeLibraryDropped = Signal()        # ⭐ clicked while 🌐 still loads — stop waiting
    wholeRescanWanted = Signal()          # 🔄 clicked — MainWindow walks the repository again

    # Dance codes per style (S-class = the full dance set), for the combo's group filters.
    _STYLE_DANCES = {style: set(DEFAULT_DANCES[style]["S"])
                     for style in ("Standard", "Latin")}
    # Narrow columns keep their width while Artist/Title share the rest — the
    # 🏆 pane's default has no Added/Last, so this list carries them.
    _FIXED_COL_W = {0: 30, 1: 90, 4: 52, 5: 52, 6: 52, 7: 70, 8: 82, 9: 52, 10: 72,
                    11: 90, 12: 220, 13: 180}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[MusicEntry] = []
        # ⭐ The favorites library; _entries is whichever list is shown, which
        # is the global index instead while 🌐 is on.
        self._favorites: list[MusicEntry] = []
        self._by_path: dict[str, MusicEntry] = {}   # the rows on screen, by path
        self._shown: list[MusicEntry] = []          # …and in their order
        self._fill_gen = 0   # bumped per fill: a step of an older fill stops
        self._whole_shown = False
        self._whole_loading = False   # ⏳ on the button: 🌐 asked for, not there yet
        self._folded = False
        # Paths of tracks already used in the open playlist decks; fed by
        # MainWindow so the 🆕 "Unplanned" filter can hide them.
        self._planned_paths: set = set()

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        # ── Header strip (stays visible when folded) ──
        self._build_header()
        v.addWidget(self._hdr)

        # ── Content (filter row + table) — hidden while folded ──
        self._content = QWidget()
        cv = QVBoxLayout(self._content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(2)

        # A flow layout, not a row: six combos plus the search box do not fit
        # across a pane docked at half the window, and a clipped filter strip
        # would keep the whole pane wider than the screen. They wrap instead.
        flt = FlowLayout(spacing=4)
        self._add_filters(flt)
        self._add_fresh_filters(flt)
        cv.addLayout(flt)

        self._build_table()
        cv.addWidget(self._table, stretch=1)
        v.addWidget(self._content, stretch=1)

        # Debounced re-filter so typing doesn't rebuild 3k rows per keystroke.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(180)
        self._filter_timer.timeout.connect(self._refilter)
        self._filter_edit.textChanged.connect(
            lambda _: self._filter_timer.start())
        self._dance_combo.currentIndexChanged.connect(lambda _: self._refilter())
        self._class_combo.classesChanged.connect(self._refilter)
        self._vocal_combo.currentIndexChanged.connect(lambda _: self._refilter())
        self._cat_combo.currentIndexChanged.connect(lambda _: self._refilter())
        self._plays_combo.currentIndexChanged.connect(lambda _: self._refilter())
        self._added_combo.currentIndexChanged.connect(lambda _: self._refilter())
        self._unplanned_chk.toggled.connect(self._on_unplanned_toggled)
        self._class_only_chk.toggled.connect(lambda _: self._refilter())

    def _build_header(self):
        """The header strip: ▾ fold, the title, the ⭐/🌐 switch and the count."""
        self._hdr = QWidget()
        self._hdr.setStyleSheet("background:#e8edf6; border-radius:3px;")
        hh = QHBoxLayout(self._hdr)
        hh.setContentsMargins(4, 1, 6, 1)
        hh.setSpacing(6)
        self._fold_btn = QToolButton()
        self._fold_btn.setText("▾")
        self._fold_btn.setToolTip("Fold the library pane to its header")
        self._fold_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._fold_btn.clicked.connect(lambda: self.set_folded(not self._folded))
        hh.addWidget(self._fold_btn)
        title = QLabel("📚  Library")
        title.setStyleSheet("font-weight:bold; color:#2c3e60;")
        hh.addWidget(title)
        # The header's flat background cascades onto its children, so without a
        # frame of their own the ⭐/🌐 switch and 🔄 read like the title. A thin
        # outline in the header's blues, no white fill: a white one broke the strip.
        hdr_btn_qss = (
            "QToolButton { background:transparent; color:#2c3e60; border:1px solid #b9c5dd;"
            " border-radius:4px; padding:0px 4px; }"
            "QToolButton:hover { background:#f4f7fc; border-color:#4a6fa5; }"
            "QToolButton:pressed { background:#c3d4f0; }"
            "QToolButton:checked { background:#d3e1f7; border-color:#8ea6cf; }")
        self._source_btn = _HdrButton()
        self._source_btn.setCheckable(True)
        self._source_btn.setStyleSheet(hdr_btn_qss)
        self._source_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._source_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._source_btn.clicked.connect(self._on_source_clicked)
        # 🔄 Under 🌐 only: the global index comes from the database, and a
        # title added to the repository since its last walk is not in it.
        self._rescan_btn = _HdrButton()
        self._rescan_btn.setText("🔄")
        self._rescan_btn.setToolTip(
            "Scan the whole music repository again for new and changed titles.\n"
            "Reads the tags only, no audio analysis; the progress shows in the\n"
            "status bar.")
        self._rescan_btn.setStyleSheet(hdr_btn_qss)
        self._rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rescan_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._rescan_btn.clicked.connect(self.wholeRescanWanted)
        self._sync_source_btn()
        hh.addWidget(self._source_btn)
        hh.addWidget(self._rescan_btn)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#666;")
        hh.addWidget(self._count_lbl)
        hh.addStretch(1)

    def _add_filters(self, flt):
        """🔍 The search box and the dance, class, vocal and category combos."""
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText(
            "🔍  Filter title / artist / comment tag…")
        self._filter_edit.setToolTip(
            "Substring of the title, the artist, or a comment marker\n"
            "(vocal_f, classic, eintanzen, …)")
        self._filter_edit.setClearButtonEnabled(True)
        flt.addWidget(self._filter_edit)
        self._dance_combo = QComboBox()
        self._dance_combo.addItem("All dances", "")
        # Style groups first (Standard / Latin), then the individual dances. A group
        # entry filters to every dance of that style; carries a "grp:" data prefix so
        # _refilter can tell it apart from a single-dance code.
        self._dance_combo.addItem("— Standard —", "grp:Standard")
        self._dance_combo.addItem("— Latin —", "grp:Latin")
        for code in DANCE_NAMES:
            self._dance_combo.addItem(dance_name(code, code), code)
        flt.addWidget(cap_filter_combo(self._dance_combo))
        self._class_combo = _ClassFilterCombo()
        self._class_combo.setToolTip(
            "Only tracks suited for one of the ticked starting classes\n"
            "(tick several; tracks without a class tag show only with all classes)")
        flt.addWidget(cap_filter_combo(self._class_combo))
        self._vocal_combo = QComboBox()
        self._vocal_combo.addItem("Vocal + instr.", "")
        self._vocal_combo.addItem("🎤 Vocal", "vocal")
        self._vocal_combo.addItem("🎻 Instrumental", "instr")
        self._vocal_combo.setToolTip("Filter by the instrumental tag")
        flt.addWidget(cap_filter_combo(self._vocal_combo))
        # Library category: tournament tracks vs the non-tournament folders
        # (anthems, background, wrong-tempo, duplicates, seasonal) that are kept
        # out of generation but stay here to browse — e.g. party music.
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("All categories", "")
        self._cat_combo.addItem("🏆 Tournament only", "turnier")
        for cid, (label, _folders) in LIBRARY_CATEGORIES.items():
            self._cat_combo.addItem(label, cid)
        self._cat_combo.setToolTip(
            "Browse by library category — 🏆 Tournament hides the non-tournament\n"
            "folders (anthems, background, wrong-tempo, duplicates, seasonal);\n"
            "pick a category to look only at those (handy for parties).")
        flt.addWidget(cap_filter_combo(self._cat_combo))

    def _add_fresh_filters(self, flt):
        """✦ Plays, 🆕 added, unplanned and class-only: is this fresh?"""
        # ── The two "is this fresh?" filters ──
        # Play history: how often (and how recently) the track was used in a real
        # tournament, read off the playlist index (popularity / last_played).
        self._plays_combo = QComboBox()
        self._plays_combo.addItem("Plays: all", "")
        self._plays_combo.addItem("✦ Never played", "never")
        self._plays_combo.addItem(
            i18n.t("★ Rarely (1–%d)") % (_PROVEN_MIN_PLAYS - 1), "rare")
        self._plays_combo.addItem(
            i18n.t("★ Proven (≥%d)") % _PROVEN_MIN_PLAYS, "proven")
        self._plays_combo.addItem("📅 Not since 1 y", "stale1")
        self._plays_combo.setToolTip(
            i18n.t("Filter by how the track was used so far:\n"
                   "✦ never — in none of your playlists\n"
                   "★ rarely / proven — in 1–%d vs. %d+ of them\n"
                   "📅 not since — played, but the newest playlist\n"
                   "carrying it is that old (the year comes from the\n"
                   "playlist's path; undated lists don't count as old).")
            % (_PROVEN_MIN_PLAYS - 1, _PROVEN_MIN_PLAYS))
        flt.addWidget(cap_filter_combo(self._plays_combo))
        # When the file arrived in the library — a copied file gets a fresh
        # creation time, so this really is "new music I put in".
        self._added_combo = QComboBox()
        self._added_combo.addItem("Added: all", "")
        self._added_combo.addItem("🆕 Last 30 days", "30")
        self._added_combo.addItem("🆕 Last 90 days", "90")
        self._added_combo.addItem("🆕 Last 12 months", "365")
        self._added_combo.addItem("🆕 Last 18 months", "548")
        self._added_combo.setToolTip(
            "Only tracks whose file was created in the library that\n"
            "recently. Combine with ✦ Never played to see what you\n"
            "copied in but have never actually used.")
        flt.addWidget(cap_filter_combo(self._added_combo))
        self._unplanned_chk = QCheckBox("🆕 Unplanned")
        self._unplanned_chk.setToolTip(
            "Show only tracks not already used in any open playlist deck —\n"
            "handy for finding fresh music while building rounds.")
        flt.addWidget(self._unplanned_chk)
        self._class_only_chk = QCheckBox("🏷 Only with a class")
        self._class_only_chk.setToolTip(
            "Hide competition titles without a class tag — the class filter\n"
            "shows those for every class.")
        flt.addWidget(self._class_only_chk)

    def _build_table(self):
        """The track table: its columns, header menu, widths and clicks."""
        self._table = _LibTable(0, 14)
        self._table.setHorizontalHeaderLabels(
            ["▶", "Dance", "Artist", "Title", "BPM", "⏱", "Pop", "Class",
             "Added", "Last", "★", "Custom", "File name", "Album"])
        set_header_tip(self._table, _LIB_COL_CUSTOM, CUSTOM_HEADER_TIP)
        set_header_tip(
            self._table, _LIB_COL_RATING,
            "Rating — click a star to set it, the last lit one again to clear it.\n"
            "Kept in the app's database; the MP3 itself is not changed."
        )
        self._table.setItemDelegateForColumn(
            _LIB_COL_RATING, StarDelegate(self._on_star_clicked, self._table))
        hh2 = stopwatch_header(self._table, 5)
        # Every column is user-resizable; the widths are persisted by MainWindow.
        # (Stretch / ResizeToContents modes would lock the handles, so we use
        # Interactive throughout and seed sensible defaults instead.)
        hh2.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh2.setStretchLastSection(False)
        hh2.setMinimumSectionSize(24)
        for c, w in enumerate((30, 90, 200, 280, 52, 52, 52, 70, 82, 52, 72, 90, 220, 180)):
            self._table.setColumnWidth(c, w)
        # Until the user drags a handle (or saved widths are restored), the
        # columns stretch to fill the whole pane on every resize.
        self._auto_fill = True
        self._filling = False
        self._col_width: dict[int, int] = {}   # width a column had when it was hidden
        self._short_dances = False             # Dance column: "LW", not "Langsamer Walzer"
        self.set_hidden_columns([_LIB_COL_RATING, _LIB_COL_CUSTOM, _LIB_COL_FILE,
                                _LIB_COL_ALBUM])   # wait until asked for
        self._table.resize_cb = self._on_table_resized
        # Right-click the header to tick columns away or shorten the dance names.
        hh2.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hh2.customContextMenuRequested.connect(self._show_column_menu)
        # Drag headers to reorder columns; the order is persisted by MainWindow.
        hh2.setSectionsMovable(True)
        hh2.sectionMoved.connect(
            lambda *_: self.columnOrderChanged.emit(self.column_order()))
        # Debounce width changes so a single drag saves once, not per pixel.
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.setInterval(400)
        self._width_timer.timeout.connect(
            lambda: self.columnWidthsChanged.emit(self.column_widths()))
        hh2.sectionResized.connect(self._on_section_resized)
        self._table.verticalHeader().setVisible(False)
        # One height for every row, instead of a setRowHeight per row (2.4 s
        # of a 54 000-title fill).
        self._table.verticalHeader().setMinimumSectionSize(22)
        self._table.verticalHeader().setDefaultSectionSize(22)
        self._table.tooltip_cb = self.cell_tooltip
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setDragEnabled(True)
        # A header click sorts the list in Python and fills it again (see
        # _populate): Qt's own sort compares the shown text of the plain items
        # the fill writes, "9" after "30". No initial sort indicator.
        hh2.setSectionsClickable(True)
        hh2.setSortIndicatorShown(True)
        hh2.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        hh2.sortIndicatorChanged.connect(self._on_sort_changed)
        self._table.setToolTip(
            "Drag a track onto a deck or wishlist to use it.\n"
            "▶ to preview · double-click to open in your external player\n"
            "· right-click for more.")
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        self._table.space_cb = lambda row: self._on_cell_clicked(row, 0)
        self._table.context_menu_cb = self._on_context_menu
        self._overlay = _LoadOverlay(self._table)
        self._fill_started = 0.0

    # ── Fold to header strip ──

    def set_folded(self, folded: bool):
        self._folded = folded
        self._content.setVisible(not folded)
        self._fold_btn.setText("▸" if folded else "▾")
        self._fold_btn.setToolTip(
            "Unfold the library pane" if folded
            else "Fold the library pane to its header")
        self.setMaximumHeight(
            self._hdr.sizeHint().height() + 4 if folded else 16777215)
        self.foldToggled.emit(folded)

    def is_folded(self) -> bool:
        return self._folded

    # ── Column order (drag to reorder, persisted by MainWindow) ──

    def column_order(self) -> list[int]:
        """Logical column indices in their current visual (left→right) order."""
        hh = self._table.horizontalHeader()
        return [hh.logicalIndex(v) for v in range(hh.count())]

    def apply_column_order(self, order: list[int]):
        """Restore a saved visual order. Ignored if it doesn't list exactly the
        current columns (e.g. a stale order from before a column was added)."""
        hh = self._table.horizontalHeader()
        if sorted(order) != list(range(hh.count())):
            return
        hh.blockSignals(True)   # don't re-emit columnOrderChanged while restoring
        for visual_pos, logical in enumerate(order):
            cur = hh.visualIndex(logical)
            if cur != -1 and cur != visual_pos:
                hh.moveSection(cur, visual_pos)
        hh.blockSignals(False)

    # ── Column widths (drag the handles, persisted by MainWindow) ──

    def column_widths(self) -> dict:
        """{logical column index -> current width in px}. A hidden column reports
        the width it HAD, not the 0 Qt gives a hidden section — otherwise ticking
        it back on would bring it back as an invisible sliver."""
        return {c: (self._col_width.get(c, 0) if self._table.isColumnHidden(c)
                    else self._table.columnWidth(c))
                for c in range(self._table.columnCount())}

    def apply_column_widths(self, widths: dict):
        """Restore saved widths. Keys may be ints or strings (JSON round-trip)."""
        hh = self._table.horizontalHeader()
        hh.blockSignals(True)   # don't re-emit columnWidthsChanged while restoring
        applied = False
        for key, w in widths.items():
            try:
                col, px = int(key), int(w)
            except (TypeError, ValueError):
                continue
            if 0 <= col < self._table.columnCount() and px >= 24:
                self._table.setColumnWidth(col, px)
                applied = True
        hh.blockSignals(False)
        if applied:   # saved layout wins — stop auto-stretching to the pane
            self._auto_fill = False

    def _on_table_resized(self):
        if self._auto_fill:
            self._fill_columns()
        if self._overlay.isVisible():
            self._overlay.place()

    def _on_section_resized(self, *_):
        # User dragged a handle: freeze the layout and persist it. (Programmatic
        # width changes block the header's signals, so they never land here.)
        if self._filling:
            return
        self._auto_fill = False
        self._width_timer.start()

    def _fill_columns(self):
        self._filling = True
        fill_track_columns(self._table, fixed=self._FIXED_COL_W)
        self._filling = False

    # ── Columns the pane shows, and how it writes a dance (header right-click) ──
    # Readable names for the two columns whose caption is a glyph — a tick list
    # reading "▶ / ⏱" says nothing about what would disappear.
    _COL_MENU_NAMES = {_LIB_COL_PLAY: "▶  Play", _LIB_COL_LEN: "⏱  Length",
                       _LIB_COL_RATING: "★  Rating"}

    def hidden_columns(self) -> list:
        return [c for c in range(self._table.columnCount())
                if self._table.isColumnHidden(c)]

    def set_hidden_columns(self, cols):
        """Show exactly the columns not in `cols`. Title is never put away — a
        row without it cannot be told from any other."""
        want = {int(c) for c in cols if int(c) != _LIB_COL_TITLE}
        t = self._table
        freed = 0
        self._filling = True      # hiding a section resizes it; that is not a drag
        try:
            for c in range(t.columnCount()):
                hidden = t.isColumnHidden(c)
                if c in want and not hidden:
                    self._col_width[c] = t.columnWidth(c)
                    freed += t.columnWidth(c)
                    t.setColumnHidden(c, True)
                elif hidden and c not in want:
                    t.setColumnHidden(c, False)
                    w = self._col_width.pop(c, 0)
                    if w:
                        t.setColumnWidth(c, w)
                    freed -= t.columnWidth(c)
        finally:
            self._filling = False
        if self._auto_fill:
            self._fill_columns()
        elif freed:
            # The user has dragged their own widths and those stand; only the
            # room the column leaves behind changes hands, and Title takes it.
            self._filling = True
            t.setColumnWidth(_LIB_COL_TITLE,
                             max(120, t.columnWidth(_LIB_COL_TITLE) + freed))
            self._filling = False

    def short_dances(self) -> bool:
        return self._short_dances

    def set_short_dances(self, on: bool):
        """Write the Dance column short ("LW", "SB") or in full."""
        on = bool(on)
        if on == self._short_dances:
            return
        self._short_dances = on
        t = self._table
        by_path = {str(e.path): e for e in self._entries}
        model = t.model()
        model.blockSignals(True)   # one dataChanged for the column, not one per row
        try:
            for r in range(t.rowCount()):
                play_it = t.item(r, _LIB_COL_PLAY)
                cell = t.item(r, _LIB_COL_DANCE)
                if play_it is None or cell is None:
                    continue
                e = by_path.get(str(play_it.data(Qt.ItemDataRole.UserRole)))
                if e is not None:
                    cell.setText(self._dance_label(e))
        finally:
            model.blockSignals(False)
        if t.rowCount():
            model.dataChanged.emit(model.index(0, _LIB_COL_DANCE),
                                   model.index(t.rowCount() - 1, _LIB_COL_DANCE))

    def _dance_label(self, e) -> str:
        """What the Dance column says for a track: the full name, or the Σ
        line's short code when the user has asked for it. A social track has no
        .dance at all — its genre names the dance."""
        if not self._short_dances:
            return dance_name(warmup_code(e), e.dance or e.other_genre or "")
        code = warmup_code(e)
        if not code:
            return genre_name(e.other_genre or "")
        return DANCE_SHORT.get(code, code)

    def build_column_menu(self) -> QMenu:
        """The right-click tick list of the header."""
        menu = QMenu(self._table)
        head = menu.addAction("Columns in the library")
        head.setEnabled(False)
        menu.addSeparator()
        for c in range(self._table.columnCount()):
            if c == _LIB_COL_TITLE:
                continue
            item = self._table.horizontalHeaderItem(c)
            act = menu.addAction(self._COL_MENU_NAMES.get(
                c, item.text() if item else str(c)))
            act.setCheckable(True)
            act.setChecked(not self._table.isColumnHidden(c))
            act.setData(c)
            act.triggered.connect(lambda on, col=c: self._toggle_column(col, on))
        menu.addSeparator()
        # Not a column but the same kind of choice: how much room the Dance
        # column needs. Carries no data(), which tells it from a column tick.
        short = menu.addAction("Short dance names  (LW, SB)")
        short.setCheckable(True)
        short.setChecked(self._short_dances)
        short.triggered.connect(self._toggle_short_dances)
        add_custom_mapping_action(menu, self)
        return menu

    def _toggle_column(self, col: int, on: bool):
        hidden = set(self.hidden_columns())
        if on:
            hidden.discard(col)
        else:
            hidden.add(col)
        self.set_hidden_columns(sorted(hidden))
        self.columnsChanged.emit(self.hidden_columns())

    def _toggle_short_dances(self, on: bool):
        self.set_short_dances(on)
        self.danceNamesChanged.emit(self._short_dances)

    def _show_column_menu(self, pos):
        hh = self._table.horizontalHeader()
        self.build_column_menu().exec(hh.mapToGlobal(pos))

    # ── Data ──

    def set_entries(self, entries: list[MusicEntry]):
        """The ⭐ favorites library. Under 🌐 it is kept for the way back."""
        self._favorites = list(entries)
        if not self._whole_shown:
            self._entries = self._favorites
            self._refilter()

    def set_whole_entries(self, entries: list[MusicEntry]):
        """🌐 The global index, once MainWindow has it loaded."""
        self._whole_shown = True
        self._entries = list(entries)
        self._sync_source_btn()
        self._refilter()

    def show_whole_loading(self, on: bool):
        """🌐 clicked while the whole library still loads in the background:
        the button and a cover over the table say so until it is there (or
        the load failed)."""
        self._whole_loading = on
        if not on:
            self._sync_source_btn()
            self._overlay.finish(covering=True)
            return
        btn = self._source_btn
        btn.setChecked(True)
        btn.setText("⏳ Whole library…")
        btn.setToolTip("The whole library is still loading in the background.\n"
                       "It is listed here when it is there; keep working meanwhile.")
        self._overlay.show_loading(i18n.t("🌐 Loading the whole library…"))

    def _on_source_clicked(self):
        if self._whole_loading:
            # Back to the favorites while 🌐 still loads: asking again was
            # the only thing a click did, and the cover never went.
            self.show_whole_loading(False)
            self.wholeLibraryDropped.emit()
        elif self._whole_shown:
            self._whole_shown = False
            self._entries = self._favorites
            self._sync_source_btn()
            self._refilter()
        else:
            # The click already ticked it; it switches once the index is here.
            self._sync_source_btn()
            self.wholeLibraryWanted.emit()

    @property
    def whole_shown(self) -> bool:
        """🌐 Is the global index on screen, rather than the favorites?"""
        return self._whole_shown

    def _sync_source_btn(self):
        btn = self._source_btn
        btn.setChecked(self._whole_shown)
        self._rescan_btn.setVisible(self._whole_shown)
        if self._whole_shown:
            btn.setText("🌐 Whole library")
            btn.setToolTip("Listing the whole music repository.\n"
                           "Click to go back to the favorites library.")
        else:
            btn.setText("⭐ Favorites")
            btn.setToolTip("Listing the favorites library.\n"
                           "Click to list the whole music repository instead.")

    def _on_unplanned_toggled(self, on: bool):
        # Ask MainWindow to (re)build the planned-path set, then refilter.
        self.unplannedToggled.emit(bool(on))
        self._refilter()

    def set_planned_paths(self, paths):
        """MainWindow feeds the set of file paths already used in the open decks
        so the 🆕 Unplanned filter can hide them."""
        self._planned_paths = set(paths or ())
        if self._unplanned_chk.isChecked():
            self._refilter()

    def unplanned_active(self) -> bool:
        return self._unplanned_chk.isChecked()

    def focus_filter(self, dance: str = "", cls: str = "", plays: str = "",
                     added: str = ""):
        """Apply one filter set from outside (📊 the gap dashboard jumps here).

        Every other filter is reset, so what lands on screen is exactly what was
        asked for — a leftover category or 🎙️ vocal filter silently eating half
        the result would be read as 'the library has nothing'."""
        self._class_combo.blockSignals(True)
        self._class_combo.set_classes([cls] if cls else [])
        self._class_combo.blockSignals(False)
        combos = ((self._dance_combo, dance),
                  (self._plays_combo, plays), (self._added_combo, added),
                  (self._vocal_combo, ""), (self._cat_combo, ""))
        for combo, value in combos:
            combo.blockSignals(True)
            idx = combo.findData(value)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        self._filter_edit.blockSignals(True)
        self._filter_edit.clear()
        self._filter_edit.blockSignals(False)
        for chk in (self._unplanned_chk, self._class_only_chk):
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        if self._folded:
            self.set_folded(False)
        self._refilter()

    def _refilter(self):
        text = self._filter_edit.text().strip().lower()
        dance = self._dance_combo.currentData() or ""
        classes = set(self._class_combo.classes())
        some_classes = 0 < len(classes) < self._class_combo.count() - 1
        vocal =self._vocal_combo.currentData() or ""
        cat = self._cat_combo.currentData() or ""
        plays = self._plays_combo.currentData() or ""
        added = self._added_combo.currentData() or ""
        added_after = time.time() - int(added) * 86400 if added else None
        stale_before = (date.today().year - int(plays[-1])) if plays.startswith("stale") else None
        unplanned_only = self._unplanned_chk.isChecked()
        class_only = self._class_only_chk.isChecked()
        rows = []
        for e in self._entries:
            if unplanned_only and str(e.path) in self._planned_paths:
                continue
            if plays:
                pop = e.popularity or 0
                if stale_before is not None:
                    # Played, but the newest playlist carrying it is that old.
                    # An undated play history says nothing — don't call it stale.
                    if not pop or not e.last_played or e.last_played > stale_before:
                        continue
                elif plays == "never" and pop:
                    continue
                elif plays == "rare" and not (1 <= pop < _PROVEN_MIN_PLAYS):
                    continue
                elif plays == "proven" and pop < _PROVEN_MIN_PLAYS:
                    continue
            if added_after is not None and (e.added or 0) < added_after:
                continue
            if cat == "turnier":
                if is_non_turnier(e):
                    continue       # 🏆 only what generation draws from
            elif cat and library_category(e) != cat:
                continue           # a specific non-tournament category
            if dance.startswith("grp:"):
                # Style group (Standard / Latin): keep any dance of that style.
                if (e.dance or "") not in self._STYLE_DANCES.get(dance[4:], ()):
                    continue
            elif dance and e.dance != dance:
                # Social dances (Forró, Salsa, …) carry no dance code — they
                # are labelled via other_genre; match that against the combo.
                if (e.other_genre or "") != DANCE_NAMES.get(dance, dance):
                    continue
            classes_ok = getattr(e, "classes_ok", None)
            if classes and classes_ok and classes.isdisjoint(classes_ok):
                continue
            # Untagged competition titles show only under all classes.
            if ((class_only or some_classes) and not classes_ok
                    and e.dance in TEMPO_RANGES):
                continue   # social dances have no classes — they stay
            if vocal:
                # Tag/filename marker first, then the learned audio probability
                # (planner.music.vocals) for the untagged rest.
                if entry_is_instrumental(e) != (vocal == "instr"):
                    continue
            if text:
                hay = " ".join(filter(None, (
                    e.title, getattr(e, "tag_artist", None),
                    getattr(e, "tag_title", None),
                    *(getattr(e, "comment_tags", None) or ())))).lower()
                if text not in hay:
                    continue
            rows.append(e)
        self._populate(rows)
        self._count_lbl.setText(
            i18n.t("(%d/%d tracks)") % (len(rows), len(self._entries))
            if self._entries else "")

    def _populate(self, entries: list[MusicEntry], keep=(frozenset(), None)):
        """Show `entries`: the first _FILL_FIRST rows at once, the rest in steps.

        The whole repository (54 000 titles) takes ~5 s to write, so it is
        written between turns of the event loop: the rows appear as they come,
        the window keeps working, and a newer fill (the next filter) drops this
        one. Only written rows exist, so whatever reads the table never meets
        an empty one. A sorted header orders the list before it is written;
        `keep` = (selected paths, playing path) to select and mark ■ again."""
        t = self._table
        self._fill_gen += 1
        hh = t.horizontalHeader()
        col = hh.sortIndicatorSection()
        if 0 <= col < t.columnCount():
            entries = sorted(entries, key=self._sort_key(col),
                             reverse=hh.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder)
        # Emptying the table deletes plain C++ items, no Python wrappers
        # (those made a 54 000-row table take 1.2 s to clear).
        t.setRowCount(0)
        self._shown = entries
        self._by_path = {str(e.path): e for e in entries}   # for cell_tooltip
        self._fill_started = time.perf_counter()
        self._fill_step(self._fill_gen, entries, 0, time.time(), keep)

    def _on_sort_changed(self, *_):
        """A header click: the same rows again, in the new order, keeping the
        selection and the ■ marker that Qt's own sort used to carry along."""
        selected = {str(self._row_path(i.row()))
                    for i in self._table.selectionModel().selectedRows()}
        row = self.current_play_row()
        self._populate(self._shown, (selected, str(self._row_path(row)) if row >= 0 else None))

    def _sort_key(self, col: int) -> Callable[[MusicEntry], Any]:
        """What column `col` sorts by: the text it shows, or for the number
        columns the number behind the text (▶ by path, not by its marker)."""
        return {
            0: lambda e: str(e.path),
            1: self._dance_label,
            2: lambda e: getattr(e, "tag_artist", None) or "",
            3: display_title,
            4: lambda e: e.bpm or -1,
            5: lambda e: int(getattr(e, "duration", 0) or 0),
            6: lambda e: e.popularity or 0,
            7: _classes_label,
            8: lambda e: getattr(e, "added", None) or 0,
            9: lambda e: getattr(e, "last_played", None) or 0,
            _LIB_COL_RATING: lambda e: int(getattr(e, "rating", 0) or 0),
            _LIB_COL_CUSTOM: lambda e: e.custom or "",
            _LIB_COL_FILE: lambda e: e.title or "",
            _LIB_COL_ALBUM: lambda e: getattr(e, "tag_album", None) or "",
        }[col]

    def _fill_step(self, gen: int, entries: list[MusicEntry], start: int, now: float, keep):
        if gen != self._fill_gen:
            return   # a newer fill took over
        t = self._table
        model = t.model()
        end = start
        began = time.perf_counter()
        kept, playing = keep
        selected: list[int] = []
        # No cyclic GC pass inside a step: a gen-2 one is a 0.5 s stall.
        gc.disable()
        try:
            while end < len(entries):
                stop = min(len(entries), end + (_FILL_FIRST if end == 0 else _FILL_CHUNK))
                # setRowCount stays outside the quiet model: rowsInserted must
                # reach the view or its own row bookkeeping goes stale.
                t.setRowCount(stop)
                # Every setData emits dataChanged, ~30 per track; on macOS
                # each one walks the Cocoa accessibility bridge and the app
                # beachballs. The step's rows are told once, below.
                model.blockSignals(True)
                try:
                    self._fill_rows(entries[end:stop], end, now)
                    if kept or playing:
                        for r, e in enumerate(entries[end:stop], end):
                            path = str(e.path)
                            if path in kept:
                                selected.append(r)
                            if path == playing:
                                model.setData(model.index(r, 0), "■")
                finally:
                    model.blockSignals(False)
                end = stop
                if time.perf_counter() - began >= _FILL_BUDGET:
                    break
        finally:
            gc.enable()
        if end > start:
            model.dataChanged.emit(model.index(start, 0),
                                   model.index(end - 1, _LIB_COL_ALBUM))
        if selected:
            sel = QItemSelection()
            for r in selected:
                sel.select(model.index(r, 0), model.index(r, _LIB_COL_ALBUM))
            t.selectionModel().select(sel, QItemSelectionModel.SelectionFlag.Select)
        if end < len(entries):
            if time.perf_counter() - self._fill_started >= _PROGRESS_AFTER:
                self._overlay.show_progress(
                    (i18n.t("🌐 Listing the whole library: %s / %s titles")
                     if self._whole_shown else
                     i18n.t("📚 Listing the library: %s / %s titles"))
                    % (f"{end:,}", f"{len(entries):,}"), end, len(entries))
            QTimer.singleShot(0, self, lambda: self._fill_step(gen, entries, end, now, keep))
        else:
            self._overlay.finish(covering=False)

    def _fill_rows(self, entries: list[MusicEntry], first_row: int, now: float):
        """Write the rows through the model, as plain C++ items: an item handed
        to setItem keeps a Python wrapper alive per cell."""
        model = self._table.model()
        idx, put = model.index, model.setData
        display, user = Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole
        align, fg = Qt.ItemDataRole.TextAlignmentRole, Qt.ItemDataRole.ForegroundRole
        center = int(Qt.AlignmentFlag.AlignCenter)

        def cell(r, c, text, value=None, color=None):
            i = idx(r, c)
            put(i, text, display)
            if value is not None:
                put(i, value, user)
                put(i, center, align)
            if color is not None:
                put(i, color, fg)

        for r, e in enumerate(entries, first_row):
            i = idx(r, 0)
            put(i, "▶", display)
            put(i, e.path, user)
            put(i, center, align)
            cell(r, 1, self._dance_label(e))
            cell(r, 2, getattr(e, "tag_artist", None) or "")   # Artist sits LEFT of Title
            cell(r, 3, display_title(e))
            cell(r, 4, str(e.bpm) if e.bpm else "", e.bpm or -1)
            secs = int(getattr(e, "duration", 0) or 0)
            cell(r, 5, _fmt_track_secs(secs) if secs else "", secs)
            pop = e.popularity or 0
            cell(r, 6, f"★{pop}" if pop else "✦", pop, _C_POP_FG if pop else _C_NEW_FG)
            cell(r, 7, _classes_label(e))
            put(idx(r, 7), center, align)
            ts = getattr(e, "added", None) or 0
            cell(r, 8, date.fromtimestamp(ts).isoformat() if ts else "", ts,
                 _C_NEW_FG if ts and ts >= now - 90 * 86400 else None)   # new: last 3 months
            last = getattr(e, "last_played", None)
            cell(r, 9, str(last) if last else ("—" if not pop else "?"), last or 0,
                 None if last else _C_NEW_FG)
            self._put_tag_cells(r, e)
            cell(r, _LIB_COL_FILE, e.title or "")
            cell(r, _LIB_COL_ALBUM, getattr(e, "tag_album", None) or "")

    def cell_tooltip(self, row: int, col: int) -> str:
        """The hover text of one cell, built when the mouse rests on it ('' =
        none, Qt then shows the table's own help)."""
        e = self._by_path.get(str(self._row_path(row))) if 0 <= row < self._table.rowCount() else None
        if e is None:
            return ""
        if col == 0:
            return i18n.t("Play / stop this track")
        if col in (2, 3):
            return _entry_tooltip(e)
        if col == 4:
            return bpm_tooltip(e)
        if col == 7:
            return (i18n.t("Class tags from the MP3 comment field")
                    if getattr(e, "classes_ok", None) else "")
        if col == 8:
            return i18n.t("When this file was created in the library")
        if col == 9:
            return i18n.t(
                "Newest playlist carrying this track" if getattr(e, "last_played", None)
                else "Never played" if not (e.popularity or 0)
                else "Played, but none of those playlists is dated")
        if col == _LIB_COL_CUSTOM:
            return e.custom or ""
        if col == _LIB_COL_FILE:
            return str(e.path)
        return ""

    def _put_tag_cells(self, row: int, e: MusicEntry):
        """The ★ and Custom cells of one row (the ★ delegate paints RATING_ROLE)."""
        model = self._table.model()
        stars = int(getattr(e, "rating", 0) or 0)
        i = model.index(row, _LIB_COL_RATING)
        model.setData(i, stars, Qt.ItemDataRole.UserRole)
        model.setData(i, stars, RATING_ROLE)
        model.setData(model.index(row, _LIB_COL_CUSTOM), e.custom or "")

    def _on_star_clicked(self, index, stars: int):
        """★ clicked: MainWindow owns the library and the cache and stores the
        rating, then hands the changed paths back through `show_tag_cells`."""
        set_rating = getattr(self.window(), "_set_entry_rating", None)
        path = self._row_path(index.row())
        if path is None or set_rating is None:
            return
        entry = next((e for e in self._entries if str(e.path) == str(path)), None)
        if entry is not None:
            set_rating(entry, stars)

    def show_tag_cells(self, paths):
        """Repaint the ★ and Custom cells of the rows showing `paths` — two
        cells each, not a rebuild of the whole pane on every click."""
        wanted = {str(p) for p in paths}
        by_path = {str(e.path): e for e in self._entries if str(e.path) in wanted}
        if not by_path:
            return
        for r in range(self._table.rowCount()):
            e = by_path.get(str(self._row_path(r)))
            if e is not None:
                self._put_tag_cells(r, e)

    def _on_cell_clicked(self, row: int, col: int):
        """Single click on the ▶ column toggles preview playback of that row."""
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

    def _on_double_click(self, row: int, col: int):
        if col == 0:   # the click handler above already toggled this row
            return
        if col == _LIB_COL_RATING:   # two quick star clicks, not "open the file"
            return
        path = self._row_path(row)
        if path:
            self._open_external(path)

    def _row_path(self, row: int) -> Path | None:
        it = self._table.item(row, 0)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _open_external(self, path: Path):
        """Hand the file to the system's default audio player.

        Through the shared helper, not os.startfile: that one does not exist off
        Windows, and it raises AttributeError rather than the OSError this used
        to catch — an uncaught crash instead of a shrug.
        """
        _open_in_default_player(path, self)

    def _on_context_menu(self, event):
        row = self._table.rowAt(event.pos().y())
        path = self._row_path(row) if row >= 0 else None
        if not path:
            return
        menu = QMenu(self._table)
        copy_act = menu.addAction("📋  Copy file path")
        reveal_act = menu.addAction("📂  Show in Explorer")
        open_act = menu.addAction("🎧  Open in external player")
        retag_act = menu.addAction("🏷  Re-read MP3 tags")
        # Inside a selection the editor takes the whole selection, outside it
        # only the row under the mouse — the decks' rule.
        sel = {ix.row() for ix in self._table.selectedIndexes()}
        rows = sorted(sel) if row in sel else [row]
        edit_paths = {str(p) for p in map(self._row_path, rows) if p}
        edit_act = menu.addAction(
            i18n.t("🏷  Edit tags of %d tracks…") % len(edit_paths)
            if len(edit_paths) > 1 else i18n.t("🏷  Edit tags…"))
        chosen = menu.exec(event.globalPos())
        if chosen is copy_act:
            QApplication.clipboard().setText(str(path))
            _show_toast(self, "📋  Path copied to clipboard")
        elif chosen is reveal_act:
            reveal_in_explorer(path, self)
        elif chosen is open_act:
            self._open_external(path)
        elif chosen is retag_act:
            self._rescan_tags(path)
        elif chosen is edit_act:
            self._edit_tags(edit_paths)

    def _rescan_tags(self, path: Path):
        """🏷 Re-read one file's ID3 tags. MainWindow owns the library and the
        cache, and its re-read feeds every pane back through `set_entries` — so
        a row whose new dance or takt drops it out of the active filter goes
        away here, which is the correct answer."""
        rescan = getattr(self.window(), "_rescan_entry_tags", None)
        if rescan is None:
            return
        entry = next((e for e in self._entries if str(e.path) == str(path)), None)
        if entry is not None:
            rescan(entry)

    def _edit_tags(self, paths: set):
        """🏷 Open the window's tag editor on these rows. The window stores the
        edit and feeds every pane back through `set_entries`."""
        edit_tags = getattr(self.window(), "_edit_entry_tags", None)
        if edit_tags is None:
            return
        entries = [e for e in self._entries if str(e.path) in paths]
        if entries:
            edit_tags(entries)

    def _start_row(self, row: int):
        it = self._table.item(row, 0)
        path = it.data(Qt.ItemDataRole.UserRole) if it else None
        if it is not None and path:
            self.on_playback_stopped()
            it.setText("■")
            self.playRequested.emit(path, row)

    def on_playback_stopped(self):
        """Reset the ▶/■ marker — playback ended or started somewhere else."""
        t = self._table
        for r in range(t.rowCount()):
            it = t.item(r, 0)
            if it is not None and it.text() == "■":
                it.setText("▶")

    def current_play_row(self) -> int:
        """Visual row currently marked ■ (playing), -1 when none."""
        model = self._table.model()
        # Qt's own search: a Python item() per row is 0.14 s over 54 000 rows.
        hit = model.match(model.index(0, 0), Qt.ItemDataRole.DisplayRole, "■", 1,
                          Qt.MatchFlag.MatchExactly)
        return hit[0].row() if hit else -1

    def skip(self, step: int) -> bool:
        """⏮/⏭ while previewing from the library: play the previous / next
        visible (filtered + sorted) row. Returns False when nothing is
        playing here or the edge of the list is reached."""
        row = self.current_play_row()
        if row < 0:
            return False
        nrow = row + step
        if not (0 <= nrow < self._table.rowCount()):
            return False
        self._start_row(nrow)
        item = self._table.item(nrow, 2)
        if item:
            self._table.scrollToItem(item)
        return True
