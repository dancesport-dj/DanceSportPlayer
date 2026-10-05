"""⏱ How many songs per dance a party list of N hours needs — the Eintanzen dialog's
estimate box.

The count runs the real ETDS builder many times (`estimate_warmup_counts`), which
takes up to a few seconds for a long party, so it runs on its own thread and
starts over whenever the hours or the dialog's options change.
"""
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from planner.terms import dance_name
from planner.warmup import (
    _WARMUP_BALLROOM, _WARMUP_LATIN, _WARMUP_MODE, estimate_warmup_counts,
)

_SECTIONS = (("Standard", _WARMUP_BALLROOM), ("Latin", _WARMUP_LATIN),
             ("Social", _WARMUP_MODE))


def estimate_text(counts, total, hours) -> str:
    """One line for the whole list, then per section each dance with the number
    of songs to have ready (the stock, enough for 9 of 10 lists)."""
    lines = [f"⏱ {hours:g} h: about {round(total[0])} songs "
             f"(have {total[1]} ready)"]
    for name, codes in _SECTIONS:
        cells = [f"{dance_name(c, c) if c in _WARMUP_MODE else c} {counts[c][1]}"
                 for c in codes if c in counts]
        if cells:
            lines.append(f"{name}: " + " · ".join(cells))
    return "\n".join(lines)


class WarmupEstimator(QThread):
    """Runs one `estimate_warmup_counts` off the UI thread."""
    done = Signal(object, object)      # (counts, total)

    def __init__(self, lengths, hours, options, parent=None):
        super().__init__(parent)
        self._lengths = lengths
        self._hours = hours
        self._options = options
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        res = estimate_warmup_counts(self._lengths, self._hours,
                                     should_stop=lambda: self._cancelled,
                                     **self._options)
        if res is not None:
            self.done.emit(*res)


class WarmupEstimateBox(QWidget):
    """Hours spin box plus the estimate. `lengths`: known track lengths per dance
    (`warmup_lengths`); `options_cb()`: the dialog's current builder options.
    Call `refresh()` when an option changes, `stop()` before the dialog goes.

    `songsNeeded(n)` hands the list length on to the dialog's Max tracks — only
    once the hours were changed, never for the default nobody picked."""
    songsNeeded = Signal(int)

    def __init__(self, lengths, options_cb, parent=None):
        super().__init__(parent)
        self._lengths = lengths
        self._options_cb = options_cb
        self._worker = None
        self._stale = False
        self._hours_picked = False

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel("Songs needed for:"))
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.5, 24)
        self.hours_spin.setSingleStep(0.5)
        self.hours_spin.setDecimals(1)
        self.hours_spin.setSuffix(" h")
        self.hours_spin.setValue(6)
        self.hours_spin.setToolTip(
            "Party play time, songs at full length with no pause.\n"
            "The count simulates the party generator with your library's\n"
            "track lengths per dance (3.5 min where none are known).")
        row.addWidget(self.hours_spin)
        row.addStretch(1)
        lyt.addLayout(row)
        self.label = QLabel("⏱ calculating…")
        self.label.setWordWrap(True)
        # The dialog's page sizes itself before the first result is in: keep room
        # for the total, three sections and a wrapped social line.
        self.label.setMinimumHeight(self.label.fontMetrics().lineSpacing() * 5 + 4)
        self.label.setToolTip(
            "Per dance: songs to have ready — enough for 9 of 10 generated lists.")
        lyt.addWidget(self.label)

        # Spinning through the hours shouldn't start a run per step.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._start)
        self.hours_spin.valueChanged.connect(lambda *_: self._on_hours())
        self.refresh()

    def _on_hours(self):
        self._hours_picked = True
        self.refresh()

    def refresh(self):
        self._debounce.start()

    def _start(self):
        if self._worker is not None and self._worker.isRunning():
            # One run at a time: stop it and start over once it has let go.
            self._stale = True
            self._worker.cancel()
            return
        self._stale = False
        self.label.setText("⏱ calculating…")
        self._worker = WarmupEstimator(self._lengths, self.hours_spin.value(),
                                       self._options_cb(), self)
        self._worker.done.connect(self._show)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _show(self, counts, total):
        if not self._stale:
            self.label.setText(estimate_text(counts, total, self.hours_spin.value()))
            if self._hours_picked:
                self.songsNeeded.emit(round(total[0]))

    def _on_finished(self):
        if self._stale:
            self._start()

    def stop(self):
        self._debounce.stop()
        self._stale = False
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
