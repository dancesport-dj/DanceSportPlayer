"""🔉 The small window that says the app is closing while ✕ fades the music.

Marcel: "so the user not think that it stucks". It does not block the desk:
a second ✕ on the main window still quits at once, and it goes with it.
"""
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from planner import i18n

_TICK_MS = 50


class QuitFadeDialog(QDialog):
    """Shows itself at once; its bar fills up over `ms`."""

    def __init__(self, parent, ms: int):
        super().__init__(parent)
        self.setWindowTitle(i18n.t("Closing"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(i18n.t(
            "🔉 Fading out the music…\nThe app closes in a moment.")))
        self._bar = QProgressBar()
        self._bar.setRange(0, max(1, ms))
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        lay.addWidget(self._bar)
        self._start = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(
            lambda: self.tick(round((time.monotonic() - self._start) * 1000)))
        self._timer.start()
        self.show()

    def tick(self, elapsed_ms: int):
        self._bar.setValue(min(self._bar.maximum(), elapsed_ms))
