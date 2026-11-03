"""☀ Holding the machine's idle timers off while the desk works.

The window says what the desk wants, this says what reaches the OS. Music
ending does not reach it yet: a track switch passes through Stopped and a floor
waits between titles, and macOS counts idle time since the last touch. Letting
go there blanks a screen nobody touched for an hour, and the next title's hold
does not switch it back on.
"""
from PySide6.QtCore import QTimer

from shared.audio.playback import keep_display_awake

# How long the hold outlasts the music and the presenter.
AFTER_MUSIC_MS = 10 * 60_000


class WakeHold:
    """Whether the OS holds the screen, and the timer that hands it back."""

    def __init__(self, parent=None):
        self.held = False
        self.release = QTimer(parent)
        self.release.setSingleShot(True)
        self.release.setInterval(AFTER_MUSIC_MS)
        self.release.timeout.connect(self._let_go)

    def follow(self, want: bool, switched_on: bool):
        """Take the desk's current wish. Only the changes reach the OS, the end
        of the music only once the release runs out; switching ☀ off lets go
        at once."""
        if self.held:
            if not want and switched_on:
                if not self.release.isActive():
                    self.release.start()
                return
            self.release.stop()
        if want == self.held:
            return
        if keep_display_awake(want) or not want:
            self.held = want

    def _let_go(self):
        keep_display_awake(False)
        self.held = False
