"""🔉↓ / 🛑 The fade an operator starts by hand on the big player.

Split off MainWindow (H1, the PlaybackController steps after ResumeMarks),
where it was three loose fields — the ramp's end, its length and the 🛑 hold
flag — written by two buttons and read by the play tick and the stop path.
Held here, the ramp's arithmetic is tested without a window, and the window
keeps the wiring: the buttons, the tick, the indicator and what happens at
the bottom of the ramp.
"""
import time


class FadeNow:
    """One running fade-out, or none.

    `end` is the monotonic time the ramp reaches silence (None = not fading),
    `total` its length in seconds, the divisor of the ramp ratio. `hold` is
    True for the 🛑 panic fade: at the bottom the title is paused in place
    instead of ended, so nothing auto-advances.
    """

    # Shorter than this, a fade is a click, not a ramp.
    MIN_SECS = 0.5

    def __init__(self) -> None:
        self.end: float | None = None
        self.total = 0.0
        self.hold = False
        # Seconds left when the title was paused; None = the clock runs.
        self.left: float | None = None
        # ✕ was pressed with music on: the window closes once the fade-out is
        # done, and that close (or a second ✕) does not fade again.
        self.quitting = False

    @property
    def running(self) -> bool:
        return self.end is not None

    def start(self, secs: float, hold: bool = False) -> None:
        """Ramp to silence over `secs` (at least MIN_SECS) from now."""
        self.hold = hold
        self.total = max(self.MIN_SECS, float(secs))
        self.end = time.monotonic() + self.total
        self.left = None

    def remaining(self) -> float:
        """Seconds left on the ramp; 0 or less once it reached the bottom."""
        if self.end is None:
            return 0.0      # no ramp running
        if self.left is not None:
            return self.left    # paused: the ramp waits where it was
        return self.end - time.monotonic()

    def freeze(self) -> None:
        """The title was paused: stop the ramp's clock where it stands."""
        if self.end is not None and self.left is None:
            self.left = self.remaining()

    def thaw(self) -> None:
        """The title runs again: the ramp goes on from where it stopped."""
        if self.left is not None:
            self.end = time.monotonic() + self.left
            self.left = None

    def level(self, remaining: float) -> float:
        """The volume factor for `remaining` seconds left: 1 → 0 along the ramp."""
        return max(0.0, remaining / self.total) if self.total > 0 else 0.0

    def cancel(self) -> None:
        self.end = None
        self.left = None
