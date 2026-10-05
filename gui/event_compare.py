"""🏆 The event plan side by side: the last word before the day decks.

One tab per competition, the variants as columns and the slots as rows. A
badge says where a title comes from (🟦 this event, 🟩 the class lists,
🟨 new, 🟧 rarely played, ⬜ library); the tooltip adds its source and the AI's why. A click on
a slot offers the replacement "like last year" suggests, the swaps the AI
wanted and did not get, and the free titles of each tier; one that breaks the
day goes in only after a warning. The window edits the plan the main window
keeps, so asking the AI again starts from what is shown here. A cell's ▶,
Space and a Ctrl+click in the menu prehear a title on the main window's
player, a cell with the mini player below its row; a double
click opens `SlotPicker`, where every choice has its own ▶; a title
dragged onto the same dance of another variant goes in there, within its
variant the two swap."""
import html
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor, QDrag, QFont, QKeySequence, QPainter, QPen, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QMenu, QMessageBox, QPushButton, QStyle,
    QTabBar, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from gui.common import _entry_tooltip
from planner import event_plan, i18n

TIER_BADGES = {"event": "🟦", "class": "🟩", "new": "🟨", "rare": "🟧",
               "library": "⬜"}
SLOT_MIME = "application/x-dancesport-event-slot"   # "competition,row,col"

NO_HISTORY = ("The earlier editions had no list of this competition — "
              "'like similar competitions' fills it from the class lists 🟩")
# What "Like last year" is called there — Marcel: label it like similar comps.
LIKE_SIMILAR = "Like similar competitions"

# "Last year, renewed" next to its reference: what it changed is coloured,
# and where it changed nothing it is not shown twice.
REFERENCE, RENEWED = "like_last_year", "last_year_renewed"
CHANGED = QColor(255, 226, 150)
SAME_AS_REFERENCE = ("'Last year, renewed' found no sound-alike to swap here — "
                     "the same as 'Like last year'")

TIER_NAMES = {"event": "🟦 This event's lists", "class": "🟩 The class lists",
              "new": "🟨 New titles", "rare": "🟧 Rarely played",
              "library": "⬜ Library"}


def _data_action(menu: QMenu, text: str):
    """A menu entry whose text is a title — data, not a catalog key."""
    with i18n.verbatim():
        return menu.addAction(text)


class _MarkedTabBar(QTabBar):
    """Tabs, the ones in `marked` orange — Marcel: the ∅ of a competition the
    event never had is too inconspicuous on its own."""
    FILL = QColor(255, 152, 0, 150)
    EDGE = QColor(245, 124, 0)

    def __init__(self):
        super().__init__()
        self.marked: set[int] = set()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        for k in self.marked:
            if k < self.count():
                rect = self.tabRect(k).adjusted(1, 1, -1, 0)
                painter.fillRect(rect, self.FILL)
                painter.fillRect(rect.adjusted(0, rect.height() - 3, 0, 0), self.EDGE)
        painter.end()


class _SlotTable(QTableWidget):
    """A competition's slots; Space and a click on a cell's icon prehear it
    (`icon_cb(row, col)`), and a title dragged onto a slot goes in when
    `can_drop(src, dst)` lets it — src and dst as (row, col). The slot it
    would go into is coloured while the drag is over it. A drag also carries
    the title's file (`path_of(row, col)`), which the decks and wishlists
    take like one from Explorer."""

    DROP_FILL = QColor(33, 150, 243, 110)
    DROP_EDGE = QColor(33, 150, 243)

    def __init__(self, rows: int, cols: int, comp: int, space_cb=None,
                 can_drop=None, drop=None, icon_cb=None, path_of=None):
        super().__init__(rows, cols)
        self._comp = comp
        self._path_of = path_of
        self._space_cb = space_cb
        self._icon_cb = icon_cb
        self._can_drop = can_drop
        self._drop = drop
        self._over = None                # (row, col) a drag would drop into
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def slot_mime(self, row: int, col: int) -> QMimeData:
        mime = QMimeData()
        mime.setData(SLOT_MIME, f"{self._comp},{row},{col}".encode())
        path = self._path_of(row, col) if self._path_of else None
        if path is not None:
            mime.setUrls([QUrl.fromLocalFile(str(path))])
            mime.setText(str(path))
        return mime

    def startDrag(self, actions):
        row, col = self.currentRow(), self.currentColumn()
        if row < 0 or col < 0:
            return
        drag = QDrag(self)
        drag.setMimeData(self.slot_mime(row, col))
        drag.exec(Qt.DropAction.CopyAction)

    def _target(self, e):
        """(src, dst) of a drag over this table, None when it cannot go there."""
        if not self._can_drop or not e.mimeData().hasFormat(SLOT_MIME):
            return None
        comp, row, col = map(int, bytes(e.mimeData().data(SLOT_MIME)).decode().split(","))
        index = self.indexAt(e.position().toPoint())
        if comp != self._comp or not index.isValid():
            return None
        src, dst = (row, col), (index.row(), index.column())
        return (src, dst) if self._can_drop(src, dst) else None

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(SLOT_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        super().dragMoveEvent(e)                    # scrolls at the edges
        target = self._target(e)
        self._set_over(target[1] if target else None)
        if target:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._set_over(None)
        super().dragLeaveEvent(e)

    def drop_cell(self):
        """The (row, col) the drag over the table would drop into, else None."""
        return self._over

    def _set_over(self, cell):
        # Painted over the cell, not into it: the renewed column's own
        # background stays as it was.
        if cell != self._over:
            self._over = cell
            self.viewport().update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._over is None:
            return
        rect = self.visualRect(self.model().index(*self._over))
        painter = QPainter(self.viewport())
        painter.fillRect(rect, self.DROP_FILL)
        painter.setPen(QPen(self.DROP_EDGE, 2))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        painter.end()

    def dropEvent(self, e):
        self._set_over(None)
        target = self._target(e)
        if not target:
            e.ignore()
            return
        e.acceptProposedAction()
        # After the drag has ended: a warning must not open inside it.
        QTimer.singleShot(0, self, lambda: self._drop(*target))

    def keyPressEvent(self, e):
        if (self._space_cb and e.key() == Qt.Key.Key_Space
                and e.modifiers() == Qt.KeyboardModifier.NoModifier):
            self._space_cb()
            return
        super().keyPressEvent(e)

    def _on_icon(self, e):
        """The index whose ▶/■ a plain left click hit, else None."""
        if (not self._icon_cb or e.button() != Qt.MouseButton.LeftButton
                or e.modifiers() != Qt.KeyboardModifier.NoModifier):
            return None
        pos = e.position().toPoint()
        index = self.indexAt(pos)
        item = self.itemFromIndex(index) if index.isValid() else None
        if item is None or item.icon().isNull():
            return None
        size = self.style().pixelMetric(QStyle.PixelMetric.PM_SmallIconSize)
        return index if pos.x() - self.visualRect(index).left() <= size + 10 else None

    def mousePressEvent(self, e):
        index = self._on_icon(e)
        if index is None:
            super().mousePressEvent(e)
            return
        self.setCurrentCell(index.row(), index.column())
        self._icon_cb(index.row(), index.column())
        e.accept()

    def mouseDoubleClickEvent(self, e):
        # The second click on the icon is not a double click on the slot:
        # the first one already played it, the picker stays shut.
        if self._on_icon(e) is not None:
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class _PrehearMenu(QMenu):
    """A slot's menu: a Ctrl+click prehears a title and leaves the menu open,
    a plain click chooses it."""

    def __init__(self, parent, picks: dict, prehear=None):
        super().__init__(parent)
        self._picks = picks          # shared with the submenus: action → pick
        self._prehear = prehear

    def mouseReleaseEvent(self, e):
        action = self.actionAt(e.position().toPoint())
        if (self._prehear and action in self._picks
                and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._prehear(self._picks[action].entry.path)
            e.accept()
            return
        super().mouseReleaseEvent(e)


class _PickerTable(QTableWidget):
    """The picker's list, with the keys of the decks: Space plays the selected
    title, Ctrl+←/→ seeks ∓30 s in it (`seek_cb(ms)`), Ctrl+Shift+←/→ skips
    to the title before or after it (`skip_cb(step)`). A row drags its file
    (`path_of(row)`) into the decks and wishlists, as from Explorer."""

    def __init__(self, space_cb, skip_cb, seek_cb=None, path_of=None):
        super().__init__(0, 3)
        self._space_cb = space_cb
        self._skip_cb = skip_cb
        self._seek_cb = seek_cb
        self._path_of = path_of
        self.setDragEnabled(path_of is not None)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def row_mime(self, row: int):
        """The file of the title in `row`; None on a heading."""
        path = self._path_of(row) if self._path_of else None
        if path is None:
            return None
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        mime.setText(str(path))
        return mime

    def startDrag(self, actions):
        mime = self.row_mime(self.currentRow())
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    def keyPressEvent(self, e):
        ctrl = Qt.KeyboardModifier.ControlModifier
        if (e.key() == Qt.Key.Key_Space
                and e.modifiers() == Qt.KeyboardModifier.NoModifier):
            self._space_cb()
            return
        if e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            back = e.key() == Qt.Key.Key_Left
            if e.modifiers() == ctrl | Qt.KeyboardModifier.ShiftModifier:
                # Held, the key would throw away a title per repeat — as the
                # player's ⏭ does not repeat either.
                if not e.isAutoRepeat():
                    self._skip_cb(-1 if back else 1)
                return
            if e.modifiers() == ctrl:
                if self._seek_cb:
                    self._seek_cb(-30000 if back else 30000)
                return
        super().keyPressEvent(e)


class SlotPicker(QDialog):
    """A slot's choices on top of the compare window, each with a ▶ to hear
    it first — Marcel: only names are not good enough. Grouped like the menu:
    the suggestion and the AI's lost swaps, then tier by tier. A double click
    or "Take" chooses; `chosen` is then the pick.

    `prehear(path)` plays or stops a title, `playing()` names the one this
    window's owner has on the player, `seek(ms)` moves the player — all None
    without a player."""

    def __init__(self, parent, title: str, now, choices, prehear=None, playing=None,
                 seek=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("🎧 Hear and choose — %s") % title)
        self.resize(760, 560)
        self._prehear = prehear
        self._playing = playing or (lambda: None)
        self._picks = []                 # in the order shown
        self._rows = []                  # table row of each pick
        self._buttons = []               # ▶ of each pick
        self._headings = []
        self.chosen = None

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self._now_btn = self._play_button(now.entry.path if now else None)
        self._now_btn.setVisible(bool(prehear and now))
        row.addWidget(self._now_btn)
        now_text = (i18n.t("Now: %s") % now.entry.title if now
                    else i18n.t("Now: —"))
        with i18n.verbatim():
            self._now = QLabel(now_text)
        self._now.setWordWrap(True)
        row.addWidget(self._now, 1)
        lay.addLayout(row)

        self._table = _PickerTable(self._space, self.skip, seek, self._path_of_row)
        table = self._table
        table.setHorizontalHeaderLabels(["", i18n.t("Title"), i18n.t("Where from")])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        head = table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        head.setStretchLastSection(True)
        table.setColumnWidth(1, 300)
        bold = QFont()
        bold.setBold(True)
        group_of = None
        for group, text, pick in choices:
            if group != group_of or not self._rows:
                group_of = group
                heading = i18n.t(TIER_NAMES[group]) if group else i18n.t(
                    "Offered for this slot")
                r = table.rowCount()
                table.insertRow(r)
                item = QTableWidgetItem(heading)
                item.setFont(bold)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                table.setItem(r, 0, item)
                table.setSpan(r, 0, 1, 3)
                self._headings.append(heading)
            r = table.rowCount()
            table.insertRow(r)
            btn = self._play_button(pick.entry.path)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # the keys stay with the list
            table.setCellWidget(r, 0, btn)
            btn.setVisible(bool(prehear))           # after: setCellWidget shows it
            name = text if not group else f"{TIER_BADGES[pick.tier]} {text}"
            source = " · ".join(s for s in (pick.source, pick.like_heat) if s)
            tip = pick_tooltip(pick, [])
            for col, cell in ((1, name), (2, source)):
                with i18n.verbatim():
                    item = QTableWidgetItem(cell)
                item.setToolTip(tip)
                table.setItem(r, col, item)
            self._picks.append(pick)
            self._rows.append(r)
            self._buttons.append(btn)
        table.cellDoubleClicked.connect(lambda r, _c: self._take_row(r))
        lay.addWidget(table, 1)

        hint = QLabel(i18n.t("▶ or Space plays a title, again stops it, Ctrl+←/→ "
                             "seeks 30 s, Ctrl+Shift+←/→ plays the title before "
                             "or after it; a double click or \"Take\" puts it "
                             "into the slot."))
        hint.setWordWrap(True)
        lay.addWidget(hint)
        box = QDialogButtonBox()
        self._take_btn = box.addButton(i18n.t("Take"), QDialogButtonBox.ButtonRole.AcceptRole)
        box.addButton(QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.take)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        if self._rows:
            table.selectRow(self._rows[0])
        self._refresh()

    def _play_button(self, path) -> QPushButton:
        btn = QPushButton("▶")
        btn.setFixedSize(26, 20)
        btn.setStyleSheet("padding: 0;")
        btn.setToolTip(i18n.t("Play / stop this title"))
        btn.clicked.connect(lambda: self._play(path))
        btn.setProperty("path", str(path) if path else "")
        return btn

    def _play(self, path):
        if self._prehear and path is not None:
            self._prehear(path)
        self._refresh()

    def _refresh(self):
        """■ on the title that plays, ▶ on all others."""
        now = self._playing()
        now = str(now) if now else None
        for btn in (self._now_btn, *self._buttons):
            btn.setText("■" if now and btn.property("path") == now else "▶")

    def _space(self):
        k = self._selected()
        if k is not None:
            self._play(self._picks[k].entry.path)

    def skip(self, step: int):
        """Select the title `step` places down (up) the list and play it —
        headings skipped. Nothing at the list's end."""
        k = self._selected()
        k = (0 if step > 0 else len(self._picks) - 1) if k is None else k + step
        if 0 <= k < len(self._picks):
            self.select(k)
            self._play(self._picks[k].entry.path)

    def _path_of_row(self, row: int):
        if row not in self._rows:
            return None
        return self._picks[self._rows.index(row)].entry.path

    def _selected(self):
        row = self._table.currentRow()
        return self._rows.index(row) if row in self._rows else None

    def _take_row(self, row: int):
        if row in self._rows:
            self.select(self._rows.index(row))
            self.take()

    # ── for the compare window and the tests ─────────────────────────────

    def picks(self) -> list:
        return list(self._picks)

    def headings(self) -> list[str]:
        return list(self._headings)

    def now_text(self) -> str:
        return self._now.text()

    def now_button(self) -> QPushButton:
        return self._now_btn

    def play_button(self, k: int) -> QPushButton:
        return self._buttons[k]

    def table(self) -> QTableWidget:
        return self._table

    def select(self, k: int):
        self._table.setCurrentCell(self._rows[k], 1)

    def take(self):
        """Choose the selected title, when there is one."""
        k = self._selected()
        if k is None:
            return
        self.chosen = self._picks[k]
        self.accept()


def pick_tooltip(pick, refused) -> str:
    """Where a title comes from, why the AI chose it, what is offered instead
    — above what a playlist row's tooltip tells about it (rich text)."""
    lines = ["%s — %s" % (i18n.t(TIER_NAMES[pick.tier]), pick.source)]
    if pick.like_heat:
        lines.append("≈ " + pick.like_heat)
    if pick.why:
        lines.append(i18n.t("AI: %s") % pick.why)
    if pick.replaces is not None:
        lines.append(i18n.t("↺ Replaces '%s' of last year — %s")
                     % (pick.replaces.entry.title, pick.replaces.source))
    if pick.suggestion is not None:
        lines.append(i18n.t("↻ Suggested instead: %s — %s")
                     % (pick.suggestion.entry.title, pick.suggestion.source))
    for x in refused:
        lines.append(i18n.t("✋ The AI wanted '%s': %s")
                     % (x.pick.entry.title, i18n.t(x.reason)))
    plan = "<br>".join(html.escape(line, quote=False) for line in lines)
    return f"<div>{plan}</div><hr>" + _entry_tooltip(pick.entry)


class EventCompareDialog(QDialog):
    continueRequested = Signal(object)    # list[int]: the competitions to ask again
    applyRequested = Signal(object)       # list[str]: each competition's variant for the day decks
    prehearing = Signal(object, int, str)  # a cell plays: its table, row, title
    tablesReplaced = Signal()             # the tables are about to be deleted

    def __init__(self, result, cands_list, parent=None, play_cb=None, seek_cb=None):
        super().__init__(parent)
        self.setWindowTitle("🏆 Event plan")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self._busy = False
        self._play_cb = play_cb
        self._seek_cb = seek_cb
        self._started = None      # the title this window put on the player
        self._tables = []
        self._playing = None      # (competition, row, col) of the cell that plays
        self._icons = {playing: self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaStop if playing
            else QStyle.StandardPixmap.SP_MediaPlay) for playing in (False, True)}

        lay = QVBoxLayout(self)
        self._tabs = QTabWidget()
        self._tabs.setTabBar(_MarkedTabBar())
        lay.addWidget(self._tabs, 1)
        self._status = QLabel()
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        row = QHBoxLayout()
        self._later_btn = QPushButton("⏳ Ask about the held back now")
        self._later_btn.clicked.connect(
            lambda: self._ask_again(self._result.pending))
        self._second_btn = QPushButton("🔁 Second round")
        self._second_btn.setToolTip(
            "Ask the AI again where a swap was lost, to fill or improve those slots.")
        self._second_btn.clicked.connect(
            lambda: self._ask_again(self._result.second_round))
        row.addWidget(self._later_btn)
        row.addWidget(self._second_btn)
        row.addStretch(1)
        # Marcel: choose the variant per tab, then copy everything into the
        # decks — the combo shows and sets the variant of the tab in front.
        self._choice: dict[int, str] = {}
        row.addWidget(QLabel("Variant:"))
        self._variant = QComboBox()
        self._variant.setToolTip("The variant of the competition in front — "
                                 "each tab keeps its own, ✔ in its header; a "
                                 "click on a column header chooses it too")
        self._variant.currentIndexChanged.connect(self._variant_chosen)
        self._tabs.currentChanged.connect(self._show_choice)
        row.addWidget(self._variant)
        self._apply_btn = QPushButton("📅 Into the tournament-day decks")
        self._apply_btn.clicked.connect(
            lambda: self.applyRequested.emit([self.chosen(i)
                                              for i in range(len(self._cands))]))
        row.addWidget(self._apply_btn)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        row.addWidget(close)
        lay.addLayout(row)

        # Ctrl+Z takes the last choice, swap or drop back; Ctrl+Y and
        # Ctrl+Shift+Z put it in again — the main window's keys.
        self._undo, self._redo = [], []
        self._undo_sc = QShortcut(QKeySequence.StandardKey.Undo, self)
        self._undo_sc.activated.connect(self.undo)
        self._redo_sc = QShortcut(QKeySequence.StandardKey.Redo, self)
        self._redo_sc.activated.connect(self.redo)
        self._redo_sc2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_sc2.activated.connect(self.redo)

        self.set_result(result, cands_list)
        # Marcel: every variant's column side by side from the start.
        self.resize(min(max(self.fit_width(), 1100),
                        self.screen().availableGeometry().width()), 720)

    def fit_width(self) -> int:
        """The window width that shows every variant's column in full."""
        if not self._tables:
            return 0
        table = self._tables[0]
        page = table.parentWidget().layout().contentsMargins()
        outer = self.layout().contentsMargins()
        return (max(sum(t.columnWidth(c) for c in range(t.columnCount())
                        if not t.isColumnHidden(c)) for t in self._tables)
                + table.verticalHeader().sizeHint().width()
                + table.verticalScrollBar().sizeHint().width()
                + 2 * table.frameWidth() + page.left() + page.right()
                + outer.left() + outer.right() + 8)    # the tab pane's frame

    # ── showing a result ──────────────────────────────────────────────────

    def set_result(self, result, cands_list):
        """Show `result` — also the answer to asking again, in place."""
        if result is not getattr(self, "_result", None):
            self._undo, self._redo = [], []   # its steps were taken in the plan before
        self._result = result
        self._cands = cands_list
        self._profiles = list(result.variants)
        keep = self._tabs.currentIndex()
        if self._tables:
            self.tablesReplaced.emit()
        self._close_picker()
        self._playing = None
        for k in range(self._tabs.count()):
            self._tabs.widget(k).deleteLater()
        self._tabs.clear()
        self._tables = []
        self._slots = []
        self._tabs.tabBar().marked = {i for i in range(len(cands_list))
                                      if not self._has_history(i)}
        for i, c in enumerate(cands_list):
            page = QWidget()
            v = QVBoxLayout(page)
            table = self._table(i)
            v.addWidget(table, 1)
            notes = QLabel(self._notes(i))
            notes.setWordWrap(True)
            v.addWidget(notes)
            mark = ("⏳ " if i in result.pending
                    else "⚠ " if i in result.failed else "")
            if not self._has_history(i):
                mark += "∅ "
            with i18n.verbatim():
                self._tabs.addTab(page, mark + c.spec.label.replace("&", "&&"))
            if not self._has_history(i):
                self._tabs.setTabToolTip(i, i18n.t(NO_HISTORY))
            self._tables.append(table)
        if 0 <= keep < self._tabs.count():
            self._tabs.setCurrentIndex(keep)

        self._variant.blockSignals(True)
        self._variant.clear()
        for p in self._profiles:
            self._variant.addItem(event_plan.PROFILE_NAMES.get(p, p), p)
        self._variant.blockSignals(False)
        self._show_choice(self._tabs.currentIndex())
        self._status.setText(self._status_text())
        self.set_busy(self._busy)

    def chosen(self, i: int) -> str:
        """The variant competition `i` goes into the day decks with."""
        p = self._choice.get(i)
        return p if p in self._profiles else self._profiles[0]

    def _show_choice(self, i: int):
        """The combo follows the tab in front."""
        k = self._variant.findData(self.chosen(i)) if i >= 0 else -1
        if k >= 0:
            self._variant.blockSignals(True)
            self._variant.setCurrentIndex(k)
            self._variant.blockSignals(False)

    def _variant_chosen(self):
        i = self._tabs.currentIndex()
        if i < 0 or self._variant.currentData() is None:
            return
        self._choice[i] = self._variant.currentData()
        self._head(i, self._tables[i])

    def choose_variant(self, i: int, col: int):
        """A click on a column header chooses that variant for the tab."""
        self._choice[i] = self._profiles[col]
        self._head(i, self._tables[i])
        if i == self._tabs.currentIndex():
            self._show_choice(i)

    def _head(self, i: int, table: QTableWidget):
        """The variants' names over the columns, the tab's chosen one ticked."""
        names = [("✔ " if p == self.chosen(i) else "") + i18n.t(self._name(i, p))
                 for p in self._profiles]
        with i18n.verbatim():
            table.setHorizontalHeaderLabels(names)

    def _table(self, i: int) -> QTableWidget:
        comp0 = self._result.variants[self._profiles[0]][i]
        # Dance by dance, its heats together — the order the playlist runs in.
        slots = [(r, h, j) for r, rc in enumerate(comp0.rounds)
                 for j in range(len(comp0.spec.dances)) for h in range(rc.heats)]
        self._slots.append(slots)
        table = _SlotTable(len(slots), len(self._profiles), i,
                           (lambda: self.prehear_slot(i)) if self._play_cb else None,
                           lambda src, dst: self.can_drop(i, src, dst),
                           lambda src, dst: self.drop_slot(i, src, dst),
                           (lambda row, col: self.prehear_cell(i, row, col))
                           if self._play_cb else None,
                           lambda row, col: self._path_at(i, row, col))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._head(i, table)
        table.horizontalHeader().sectionClicked.connect(
            lambda col, i=i: self.choose_variant(i, col))
        heads = []
        for r, h, j in slots:
            rc = comp0.rounds[r]
            heat = f" {h + 1}" if rc.heats > 1 else ""
            heads.append(f"{rc.name}{heat} · {comp0.spec.dances[j]}")
        table.setVerticalHeaderLabels(heads)
        table.horizontalHeader().setStretchLastSection(True)
        for col in range(len(self._profiles)):
            table.setColumnWidth(col, 300)
            for row in range(len(slots)):
                self._fill(i, row, col, table)
        if self._renews_nothing(i):
            table.setColumnHidden(self._profiles.index(RENEWED), True)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, i=i, t=table: self._menu_at(i, t.indexAt(pos),
                                                    t.viewport().mapToGlobal(pos)))
        table.cellDoubleClicked.connect(
            lambda row, col, i=i: self.open_picker(i, row, col))
        return table

    def _fill(self, i: int, row: int, col: int, table: QTableWidget | None = None):
        table = table or self._tables[i]
        comps = self._result.variants[self._profiles[col]]
        key = (i, *self._slots[i][row])
        pick = event_plan.slot_pick(comps, key)
        refused = event_plan.slot_refused(comps[i], key)
        if pick is None:
            item = QTableWidgetItem("—")
        else:
            text = f"{TIER_BADGES[pick.tier]} {pick.entry.title}"
            if pick.replaces is not None:
                text += "   ↺"
            if pick.suggestion is not None:
                text += "   ↻"
            if refused:
                text += f"   ✋{len(refused)}"
            item = QTableWidgetItem(text)
            item.setToolTip(pick_tooltip(pick, refused))
            if col == self._renewed_col() and self._changed(i, row):
                item.setBackground(CHANGED)
            if self._play_cb:
                item.setIcon(self._icons[self._playing == (i, row, col)])
        table.setItem(row, col, item)

    def _renewed_col(self) -> int | None:
        """The column of "Last year, renewed" when its reference is shown too."""
        if REFERENCE in self._profiles and RENEWED in self._profiles:
            return self._profiles.index(RENEWED)
        return None

    def _changed(self, i: int, row: int) -> bool:
        """Whether "Last year, renewed" plays another title there than its reference."""
        key = (i, *self._slots[i][row])
        path = lambda p: str(p.entry.path) if p else None  # noqa: E731
        return (path(event_plan.slot_pick(self._result.variants[RENEWED], key))
                != path(event_plan.slot_pick(self._result.variants[REFERENCE], key)))

    def _renews_nothing(self, i: int) -> bool:
        return (self._renewed_col() is not None
                and not any(self._changed(i, row) for row in range(len(self._slots[i]))))

    def _refill(self, i: int, row: int, col: int):
        """Show the slot anew — and its renewed title, whose colour follows the reference."""
        self._fill(i, row, col)
        renewed = self._renewed_col()
        if renewed is not None and col == self._profiles.index(REFERENCE):
            self._fill(i, row, renewed)

    def _has_history(self, i: int) -> bool:
        """Whether the event's earlier editions had a list of competition `i`."""
        return any(picks for rnd in self._cands[i].event for picks in rnd.values())

    def _name(self, i: int, p: str) -> str:
        """The variant's name in competition `i`'s tab."""
        if p == REFERENCE and not self._has_history(i):
            return LIKE_SIMILAR
        return event_plan.PROFILE_NAMES.get(p, p)

    def _notes(self, i: int) -> str:
        lines = [] if self._has_history(i) else [f"∅ {i18n.t(NO_HISTORY)}"]
        if self._renews_nothing(i):
            lines.append(i18n.t(SAME_AS_REFERENCE))
        for p in self._profiles:
            note = self._result.variants[p][i].notes
            if note:
                lines.append(f"<b>{i18n.t(self._name(i, p))}:</b> {note}")
        return "<br>".join(lines)

    def _status_text(self) -> str:
        r = self._result
        names = lambda idx: ", ".join(self._cands[i].spec.label for i in idx)  # noqa: E731
        lines = []
        if r.pending:
            lines.append(i18n.t("⏳ Held back by the AI's limit: %s") % names(r.pending)
                         + (f" — {r.limit}" if r.limit else ""))
        if r.failed:
            lines.append(i18n.t("⚠ The AI could not check: %s — the plan stands")
                         % names(r.failed))
        if r.second_round:
            lines.append(i18n.t("🔁 A swap was lost at: %s — a second round can "
                                "fill or improve those slots") % names(r.second_round))
        lines.append(i18n.t("Double-click or right-click a title for what else fits "
                            "there.  🟦 event  🟩 class lists  🟨 new  "
                            "🟧 rarely played  ⬜ library  "
                            "↺ replaces last year's title  ↻ a replacement is offered  "
                            "✋ the AI wanted another"))
        lines.append(i18n.t("Drag a title onto the same dance in another "
                            "variant to take it over there, within its variant "
                            "to swap the two"))
        if self._play_cb:
            lines.append(i18n.t("▶ A title's ▶ or Space plays it, again stops it; "
                                "Ctrl+click in the menu one to choose from"))
        return "\n".join(lines)

    def set_busy(self, busy: bool):
        """While the AI is asked again the plan is not edited here."""
        self._busy = busy
        self._later_btn.setVisible(bool(self._result.pending))
        self._second_btn.setVisible(bool(self._result.second_round))
        for w in (self._later_btn, self._second_btn, self._apply_btn):
            w.setEnabled(not busy)

    def _ask_again(self, only):
        if only and not self._busy:
            self.continueRequested.emit(list(only))

    # ── the last word on a slot ───────────────────────────────────────────

    def slot_choices(self, i: int, row: int, col: int) -> list[tuple[str, str, object]]:
        """What the slot's menu offers, as (group, text, pick): group '' for
        the suggestion and the AI's lost swaps, else the tier."""
        comps = self._result.variants[self._profiles[col]]
        key = (i, *self._slots[i][row])
        pick = event_plan.slot_pick(comps, key)
        out = []
        if pick is not None and pick.replaces is not None:
            out.append(("", i18n.t("↺ Back to last year: %s")
                        % pick.replaces.entry.title, pick.replaces))
        if pick is not None and pick.suggestion is not None:
            out.append(("", i18n.t("↻ Take the suggestion: %s")
                        % pick.suggestion.entry.title, pick.suggestion))
        for x in event_plan.slot_refused(comps[i], key):
            out.append(("", i18n.t("✋ The AI wanted: %s (%s)")
                        % (x.pick.entry.title, i18n.t(x.reason)), x.pick))
        for tier, picks in event_plan.slot_alternatives(self._cands[i], comps, key).items():
            out += [(tier, p.entry.title, p) for p in picks]
        return out

    def _slot_menu(self, i: int, row: int, col: int):
        """The slot's menu and its actions → the pick each one puts in."""
        actions = {}
        prehear = self.prehear if self._play_cb else None
        menu = _PrehearMenu(self, actions, prehear)
        self._picker_action = menu.addAction(i18n.t("🎧 Hear and choose…"))
        menu.addSeparator()
        subs = {}
        for group, text, pick in self.slot_choices(i, row, col):
            if group and group not in subs:
                if not subs and actions:
                    menu.addSeparator()
                sub = _PrehearMenu(menu, actions, prehear)
                sub.setTitle(i18n.t(TIER_NAMES[group]))
                sub.setToolTipsVisible(True)
                menu.addMenu(sub)
                subs[group] = sub
            action = _data_action(subs[group] if group else menu, text)
            if group:
                action.setToolTip(pick.source)
            actions[action] = pick
        menu.setToolTipsVisible(True)
        return menu, actions

    def _menu_at(self, i: int, index, global_pos):
        if self._busy or not index.isValid():
            return
        row, col = index.row(), index.column()
        menu, actions = self._slot_menu(i, row, col)
        chosen = menu.exec(global_pos)
        menu.deleteLater()
        if chosen is not None and chosen is self._picker_action:
            self.open_picker(i, row, col)
        elif chosen in actions:
            self.choose(i, row, col, actions[chosen])

    def slot_picker(self, i: int, row: int, col: int) -> SlotPicker:
        """The picker of a slot: its choices, each to be heard first."""
        table = self._tables[i]
        title = "%s · %s" % (self._tabs.tabText(i).replace("&&", "&"),
                             table.verticalHeaderItem(row).text())
        variant = table.horizontalHeaderItem(col).text()
        return SlotPicker(
            self, f"{title} · {variant}", self._pick(i, row, col),
            self.slot_choices(i, row, col),
            self.prehear if self._play_cb else None,
            lambda: self._started if self._started and self._playing_ours() else None,
            self._seek_cb)

    def open_picker(self, i: int, row: int, col: int):
        """Let the slot's title be chosen in `SlotPicker`, heard first. Not
        modal: Qt refuses a drop onto a window a modal one blocks, and a title
        of the picker is to be dragged into the playlists too. One at a time,
        gone when the tables are."""
        if self._busy or row < 0 or col < 0:
            return
        self._close_picker()
        picker = self._picker = self.slot_picker(i, row, col)
        picker.finished.connect(lambda code: self._picker_done(picker, i, row, col, code))
        picker.show()

    def _picker_done(self, picker, i, row, col, code):
        if self._picker is picker:
            self._picker = None
        picker.deleteLater()
        if code == QDialog.DialogCode.Accepted and picker.chosen is not None:
            self.choose(i, row, col, picker.chosen)

    def _close_picker(self):
        picker, self._picker = getattr(self, "_picker", None), None
        if picker is not None:
            picker.reject()

    def shown_picker(self):
        """The open `SlotPicker`, None without one."""
        return self._picker

    def choose(self, i: int, row: int, col: int, pick) -> bool:
        """Put `pick` into the slot, after a warning if it breaks the day."""
        comps = self._result.variants[self._profiles[col]]
        key = (i, *self._slots[i][row])
        conflict = event_plan.slot_conflict(comps, key, pick)
        if conflict:
            ret = QMessageBox.question(
                self, "Event plan",
                i18n.t("'%s' %s.\n\nPut it in anyway?")
                % (pick.entry.title, i18n.t(conflict)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return False
        self._remember(i, col, (row,))
        event_plan.put_slot(comps, key, pick)
        self._refill(i, row, col)
        return True

    def _pick(self, i: int, row: int, col: int):
        return event_plan.slot_pick(self._result.variants[self._profiles[col]],
                                    (i, *self._slots[i][row]))

    def _path_at(self, i: int, row: int, col: int):
        pick = self._pick(i, row, col)
        return pick.entry.path if pick is not None else None

    def can_drop(self, i: int, src: tuple, dst: tuple) -> bool:
        """A title may be dragged onto the same dance in another variant, or
        in its own onto another slot with a title to swap with."""
        (src_row, src_col), (dst_row, dst_col) = src, dst
        slots = self._slots[i]
        return (not self._busy and src != dst
                and slots[src_row][2] == slots[dst_row][2]
                and self._pick(i, src_row, src_col) is not None
                and (src_col != dst_col or self._pick(i, dst_row, dst_col) is not None))

    def drop_slot(self, i: int, src: tuple, dst: tuple) -> bool:
        """Put the title of slot `src` into slot `dst`, like a menu choice —
        within one variant the two titles swap."""
        if not self.can_drop(i, src, dst):
            return False
        if src[1] == dst[1]:
            return self.swap(i, src[0], dst[0], src[1])
        return self.choose(i, *dst, self._pick(i, *src))

    def swap(self, i: int, row_a: int, row_b: int, col: int) -> bool:
        """Swap two slots' titles, after a warning if that breaks the day."""
        comps = self._result.variants[self._profiles[col]]
        a, b = (i, *self._slots[i][row_a]), (i, *self._slots[i][row_b])
        conflict = event_plan.swap_conflict(comps, a, b)
        if conflict:
            ret = QMessageBox.question(
                self, "Event plan",
                i18n.t("'%s' ⇄ '%s': %s.\n\nSwap anyway?")
                % (self._pick(i, row_a, col).entry.title,
                   self._pick(i, row_b, col).entry.title, i18n.t(conflict)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return False
        self._remember(i, col, (row_a, row_b))
        event_plan.swap_slots(comps, a, b)
        self._refill(i, row_a, col)
        self._refill(i, row_b, col)
        return True

    def _kept(self, i: int, col: int, rows) -> tuple:
        """The slots' titles and the competition's refused swaps — a choice
        settles those — as Ctrl+Z and Ctrl+Y put them back."""
        comp = self._result.variants[self._profiles[col]][i]
        return (i, col, [(row, self._pick(i, row, col)) for row in rows],
                list(comp.refused))

    def _remember(self, i: int, col: int, rows: tuple):
        self._undo.append(self._kept(i, col, rows))
        self._redo = []

    def undo(self):
        """Take the last choice, swap or drop back, and show where it was."""
        self._step(self._undo, self._redo)

    def redo(self):
        """Put in again what Ctrl+Z took back."""
        self._step(self._redo, self._undo)

    def _step(self, source: list, target: list):
        """Put the slots back as the last step of `source` kept them; how
        they are now goes to `target`."""
        if self._busy or not source:
            return
        i, col, picks, refused = source.pop()
        target.append(self._kept(i, col, [row for row, _pick in picks]))
        comp = self._result.variants[self._profiles[col]][i]
        for row, pick in picks:
            r, h, j = self._slots[i][row]
            comp.grid[comp.rounds[r].name][h][j] = pick
        comp.refused = refused
        for row, _pick in picks:
            self._refill(i, row, col)
        self._tabs.setCurrentIndex(i)
        self._tables[i].setCurrentCell(picks[0][0], col)

    # ── prehearing ────────────────────────────────────────────────────────

    def prehear_slot(self, i: int):
        """Prehear the selected title of competition `i`, or stop it."""
        if not 0 <= i < len(self._tables):
            return
        table = self._tables[i]
        row, col = table.currentRow(), table.currentColumn()
        if row >= 0 and col >= 0:
            self.prehear_cell(i, row, col)

    def prehear_cell(self, i: int, row: int, col: int):
        """Prehear the title of a slot, or stop it; ■ marks the cell."""
        pick = self._pick(i, row, col)
        if pick is not None:
            self.prehear(pick.entry.path, (i, row, col))

    def prehear(self, path, cell=None):
        """Play `path` on the main window's player — or stop it, when this
        window already put it there and it still plays. A `cell` (competition,
        row, col) it came from gets the ■ and asks for the mini player."""
        if not self._play_cb:
            return
        if path == self._started and self._playing_ours():
            self._stop_own_preview()
            return
        self._started = path
        self._play_cb(path)
        self._mark(cell)
        if cell is not None:
            self.prehearing.emit(self._tables[cell[0]], cell[1], Path(path).stem)

    def _mark(self, cell):
        """■ on `cell` (None: on no cell), ▶ back on the one before."""
        old, self._playing = self._playing, cell
        for c in {old, cell} - {None}:
            i, row, col = c
            item = self._tables[i].item(row, col) if i < len(self._tables) else None
            if item is not None and not item.icon().isNull():
                item.setIcon(self._icons[c == cell])

    def on_playback_stopped(self):
        """The shared player stopped, or someone else took it over."""
        self._mark(None)

    def skip_prehear(self, step: int) -> bool:
        """⏮/⏭ of the mini player: the next titled slot up or down the
        column that plays. False when no cell plays or the column ends."""
        if self._playing is None:
            return False
        i, row, col = self._playing
        table = self._tables[i]
        row += step
        while 0 <= row < table.rowCount():
            if self._pick(i, row, col) is not None:
                table.setCurrentCell(row, col)
                table.scrollToItem(table.item(row, col))
                self.prehear_cell(i, row, col)
                return True
            row += step
        return False

    def _playing_ours(self) -> bool:
        host = self.parentWidget()
        deck_path = getattr(host.window(), "deck_path", None) if host else None
        return deck_path is None or deck_path() == self._started

    def _stop_own_preview(self):
        """Stop the player, but only while it is still on the title this window
        started: the decks share the player, and a title the operator started
        since is the live music."""
        if self._started is not None and self._play_cb and self._playing_ours():
            self._play_cb(None)
        self._started = None
        self._mark(None)

    def closeEvent(self, e):
        self._stop_own_preview()
        super().closeEvent(e)
