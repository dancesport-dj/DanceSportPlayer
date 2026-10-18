"""⛶ Fullscreen (F11) for the planner and the player, with a clock.

On the dance floor the desk is often the only screen in sight, so while the
window fills it the status bar shows the date and time at its right end.
A MainWindow mixin.
"""
from PySide6.QtCore import QDateTime, QLocale, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel

from planner import i18n
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object


def clock_text(when: QDateTime, time_only: bool = False) -> str:
    """"Sat, 10.10.2026 20:45:12" — the short weekday in the desk's language —
    or just "20:45:12"."""
    if time_only:
        return when.time().toString("HH:mm:ss")
    loc = QLocale(i18n.active_language())
    day = loc.dayName(when.date().dayOfWeek(), QLocale.FormatType.ShortFormat)
    day = day.rstrip(".")
    return (f"{day[:1].upper()}{day[1:]}, {when.date().toString('dd.MM.yyyy')} "
            f"{when.time().toString('HH:mm:ss')}")


class FullscreenMixin(MainWindowHost):

    def _setup_fullscreen(self):
        self._fullscreen_sc = QShortcut(QKeySequence("F11"), self)
        self._fullscreen_sc.setAutoRepeat(False)
        self._fullscreen_sc.activated.connect(
            lambda: self.set_fullscreen(not self.isFullScreen()))
        # Always the last permanent widget, so it is the rightmost one.
        self._clock = QLabel()
        self._clock.setStyleSheet("padding:0 8px;")
        self._clock.hide()
        self.statusBar().addPermanentWidget(self._clock)
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)

    def set_fullscreen(self, on: bool):
        # Toggling only the fullscreen bit brings a maximized window back
        # maximized, not shrunk to its normal size.
        state = self.windowState() & ~Qt.WindowState.WindowFullScreen
        if on:
            state |= Qt.WindowState.WindowFullScreen
        self.setWindowState(state)
        self._clock.setVisible(on)
        if on:
            self._tick_clock()
            self._clock_timer.start()
        else:
            self._clock_timer.stop()

    def _tick_clock(self):
        # Read every tick: a change in ⚙ Settings shows within a second.
        self._clock.setText(clock_text(
            QDateTime.currentDateTime(),
            time_only=bool(self._settings.get("clock_time_only", False))))
