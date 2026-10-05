"""🕒 Where the evening's running order is typed.

One row per entry — when, what, and an optional line under it — plus the two
things the presenter needs to know: whether to rotate between the music page
and this one, and how often. Everything here is free text on purpose; see
`player.timetable.Entry` for why "ca. 23 Uhr" has to be allowed through.
"""
import logging
from datetime import datetime, time, timedelta

from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
)

from shared.widgets import _app_icon, _hsep
from player.timetable import (
    DEFAULT_ROTATE_SECS,
    DEFAULT_TITLE,
    MAX_ROTATE_SECS,
    MIN_ROTATE_SECS,
    Entry,
    Timetable,
    offset_for,
)

log = logging.getLogger("dancesport.gui.timetable")

_COL_TIME = 0
_COL_UNTIL = 1
_COL_WHAT = 2
_COL_NOTE = 3

# What a first-time timetable is pre-filled with. Not empty: an empty grid
# hides what the four columns are for, and a wedding evening really does look
# roughly like this. The ends are part of the lesson: "Tanz frei" runs to 01:00
# and the snack happens inside it, which is the shape the Until column is for.
# Field order, not column order — Entry is (time, what, note, until).
_EXAMPLE = [
    ("18:00", "Sektempfang", "", "19:00"),
    ("19:00", "Dinner", "Buffet im Saal", "20:30"),
    ("20:30", "Eröffnungstanz", "", "20:45"),
    ("20:45", "Tanz frei", "", "01:00"),
    ("23:00", "Mitternachtssnack", "", "23:30"),
]


class TimetableDialog(QDialog):
    """Edit the running order the presenter screen can show. `timetable()`
    hands back what was typed; the caller saves it."""

    # Something in here was edited. Whoever has the presenter screen open can
    # follow along on it while the typing happens instead of waiting for Save.
    changed = Signal()

    def __init__(self, table: Timetable | None = None, parent=None,
                 now_offset=None):
        super().__init__(parent)
        self.setWindowTitle("🕒 Timetable — presenter screen")
        self.setWindowIcon(_app_icon())
        self.setModal(True)
        self.resize(620, 480)
        table = table if table is not None else Timetable()

        lay = QVBoxLayout(self)
        hint = QLabel(
            "What the presenter screen shows on its second page — the evening's\n"
            "running order. The line the clock has reached is highlighted, the\n"
            "ones before it are greyed out.\n\n"
            "A time may be anything you would write on a programme; only real\n"
            "clock times (20:30, 20.30) take part in the highlighting.\n\n"
            "\"Until\" is optional and is what lets one point hold another: give\n"
            "the party 19:00–01:00 and the opening dance 19:30–19:50, and when\n"
            "the dance is over the highlight goes back to the party. Either an\n"
            "end time (01:00) or a length in minutes (20).")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(_hsep())

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Heading"))
        self.title_ed = QLineEdit(table.title or DEFAULT_TITLE)
        self.title_ed.setPlaceholderText(DEFAULT_TITLE)
        title_row.addWidget(self.title_ed, 1)
        lay.addLayout(title_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Until", "What", "Note"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(_COL_TIME, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(_COL_TIME, 90)
        head.setSectionResizeMode(_COL_UNTIL, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(_COL_UNTIL, 90)
        head.setSectionResizeMode(_COL_WHAT, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(_COL_NOTE, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)

        for entry in (table.entries or [Entry(*e) for e in _EXAMPLE]):
            self._add_row(entry)

        btn_row = QHBoxLayout()
        for text, tip, slot in (
                ("➕  Add", "A new line at the end", self._add_row),
                ("✖  Remove", "Take the selected line out", self._remove_row),
                ("▲", "Move the selected line up", lambda: self._move(-1)),
                ("▼", "Move the selected line down", lambda: self._move(1))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        lay.addWidget(_hsep())

        # ── How the presenter divides its screen time between the two pages ──
        rot_row = QHBoxLayout()
        self.rotate_check = QCheckBox("Fade between music and timetable every")
        self.rotate_check.setToolTip(
            "Off, the screen stays on whichever page you picked (T on the\n"
            "presenter screen, or its 🕒 button, switches by hand).\n\n"
            "On, it fades from one to the other by itself — so the hall sees\n"
            "both without anybody at the desk touching anything.")
        self.rotate_check.setChecked(bool(table.rotate))
        self.rotate_secs = QSpinBox()
        self.rotate_secs.setRange(MIN_ROTATE_SECS, MAX_ROTATE_SECS)
        self.rotate_secs.setSuffix(" s")
        self.rotate_secs.setValue(int(table.rotate_secs or DEFAULT_ROTATE_SECS))
        self.rotate_secs.setEnabled(self.rotate_check.isChecked())
        self.rotate_check.toggled.connect(self.rotate_secs.setEnabled)
        rot_row.addWidget(self.rotate_check)
        rot_row.addWidget(self.rotate_secs)
        rot_row.addStretch(1)
        lay.addLayout(rot_row)

        # ── What the screen is to take for "now" ────────────────────────────
        now_row = QHBoxLayout()
        self.now_check = QCheckBox("Set clock to")
        self.now_check.setToolTip(
            "Off, the running order goes by this machine's clock.\n\n"
            "On, it goes by the time you set here — from the moment you save,\n"
            "and running on from there. An evening half an hour behind stays\n"
            "half an hour behind; the screen does not stand still.\n\n"
            "This is not saved with the programme: the next start of the app\n"
            "is back on the machine's clock.")
        self.now_check.setChecked(now_offset is not None)
        self.now_time = QTimeEdit()
        self.now_time.setDisplayFormat("HH:mm")
        shown = datetime.now() + (now_offset or timedelta())
        self.now_time.setTime(QTime(shown.hour, shown.minute))
        self.now_time.setEnabled(self.now_check.isChecked())
        self.now_check.toggled.connect(self.now_time.setEnabled)
        # The field shows whole minutes of the moment the dialog opened, so a
        # shift is recomputed from it only once somebody touches the clock.
        self._now_given = now_offset
        self._now_touched = False
        self.now_check.toggled.connect(self._touch_clock)
        self.now_time.timeChanged.connect(self._touch_clock)
        now_row.addWidget(self.now_check)
        now_row.addWidget(self.now_time)
        now_row.addStretch(1)
        lay.addLayout(now_row)

        # ── Anything below this line is a live change ───────────────────────
        # Connected last on purpose: filling the grid above would otherwise
        # announce every pre-existing row as an edit. itemChanged covers typing
        # as well as Add and ▲▼, which both write cells; Remove does not, so it
        # says so itself.
        self.title_ed.textChanged.connect(self.changed)
        self.table.itemChanged.connect(self.changed)
        self.rotate_check.toggled.connect(self.changed)
        self.rotate_secs.valueChanged.connect(self.changed)
        self.now_check.toggled.connect(self.changed)
        self.now_time.timeChanged.connect(self.changed)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add_row(self, entry: Entry | None = None):
        entry = entry if isinstance(entry, Entry) else Entry()
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, text in ((_COL_TIME, entry.time), (_COL_UNTIL, entry.until),
                          (_COL_WHAT, entry.what), (_COL_NOTE, entry.note)):
            self.table.setItem(row, col, QTableWidgetItem(text))
        self.table.setCurrentCell(row, _COL_TIME)

    def _remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def _move(self, step: int):
        """Swap the selected line with its neighbour — the order on the screen
        is the order typed here, and a programme is rarely typed in order."""
        row = self.table.currentRow()
        other = row + step
        if row < 0 or not 0 <= other < self.table.rowCount():
            return
        for col in range(self.table.columnCount()):
            a = self.table.takeItem(row, col)
            b = self.table.takeItem(other, col)
            self.table.setItem(row, col, b or QTableWidgetItem(""))
            self.table.setItem(other, col, a or QTableWidgetItem(""))
        self.table.setCurrentCell(other, self.table.currentColumn())

    def _cell(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item is not None else ""

    def timetable(self) -> Timetable:
        """What was typed. Blank lines are dropped: a row somebody cleared out
        instead of removing is not an entry, and it would print as a gap."""
        entries = []
        for row in range(self.table.rowCount()):
            entry = Entry(time=self._cell(row, _COL_TIME),
                          what=self._cell(row, _COL_WHAT),
                          note=self._cell(row, _COL_NOTE),
                          until=self._cell(row, _COL_UNTIL))
            if entry.time or entry.what:
                entries.append(entry)
        return Timetable(title=self.title_ed.text().strip() or DEFAULT_TITLE,
                         entries=entries,
                         rotate=self.rotate_check.isChecked(),
                         rotate_secs=self.rotate_secs.value())

    def now_offset(self):
        """How far the screen's clock is to be moved, or None for the
        machine's own. Deliberately not part of `timetable()`: the programme
        is typed once and kept, while this belongs to one evening — and a
        forgotten test time must not be waiting in the file on the night."""
        if not self.now_check.isChecked():
            return None
        if not self._now_touched:
            return self._now_given
        t = self.now_time.time()
        return offset_for(time(t.hour(), t.minute()))

    def _touch_clock(self, *_args):
        self._now_touched = True
