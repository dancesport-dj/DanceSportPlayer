"""🔬 The background analysis in the status bar: a count, the time left, a bar.

The run starts by itself, under nobody's eyes and never in a show's way, so it
gets no dialog. This is the quiet version of the busy dialog the 🔬 button
opens; it only says how far the run is and goes away when it ends.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from gui.common import fmt_duration
from planner import i18n


class BackgroundAnalysisBar(QWidget):
    """A label, a bar and a stop button for QStatusBar.addPermanentWidget.
    Hidden when idle. The button only says what was asked; the window cancels."""

    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(self)
        self.progress = QProgressBar(self)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(160)
        self.progress.setMaximumHeight(14)
        self.stop_btn = QToolButton(self)
        self.stop_btn.setText("⏹")
        self.stop_btn.setAutoRaise(True)
        self.stop_btn.setToolTip(i18n.t("Stop the analysis of the new titles; "
                                        "the title in work still ends"))
        self.stop_btn.clicked.connect(self._on_stop)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 6, 0)
        row.addWidget(self.label)
        row.addWidget(self.progress)
        row.addWidget(self.stop_btn)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.hide()

    def _on_stop(self) -> None:
        self.stop_btn.setEnabled(False)
        self.stop_requested.emit()

    def start(self, total: int) -> None:
        self.stop_btn.setEnabled(True)
        self.progress.setRange(0, total)
        self.progress.setValue(0)
        self.label.setText(i18n.t("🔬 Analyzing new titles…") + f" {total}")
        self.show()

    def set_progress(self, done: int, total: int, errors: int, _name: str, eta: float) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        text = i18n.t("🔬 Analyzing new titles…") + f" {done}/{total}"
        if eta >= 0:
            text += i18n.t("  ~%s left") % fmt_duration(eta)
        if errors:
            text += "  " + i18n.t("(%s errors)") % errors
        self.label.setText(text)

    def finish(self, *_args) -> None:
        self.hide()
