"""🎵 The filler music of the between-dances pause — which title, how loud.

Split off the pause mixin as an object of its own: it owns the rotation through
the filler titles and the fade ramp, knows nothing of players or widgets, and so
is built and tested without a window. Loading the title into the pause player,
playing it and routing it to the sound card stay with the window.
"""
from pathlib import Path


class PauseFiller:
    """The filler titles, the one playing now, and the pause they fill."""

    def __init__(self):
        self.titles: list[str] = []   # resolved filler titles (rotation)
        self.index = 0   # which title plays in the current pause
        self.total = 0.0   # configured pause length when the filler started
        self.active = False   # filler audible right now?

    @property
    def current(self) -> str | None:
        return self.titles[self.index] if self.titles else None

    def load(self, paths: list[str]) -> str | None:
        """Keep the titles that exist on disk and return the one to play: the
        rotation resumes where the last pause left off. None = none exists."""
        self.titles = [p for p in paths if Path(p).is_file()]
        if not self.titles:
            return None
        self.index %= len(self.titles)
        return self.titles[self.index]

    def rotate(self) -> str | None:
        """A title ran out mid-pause: the next one (a single title restarts)."""
        if not self.titles:
            return None
        self.index = (self.index + 1) % len(self.titles)
        return self.titles[self.index]

    def fade(self, remaining: float) -> float:
        """Level of the fade ramp, 0…1: in over the first seconds of the pause,
        out over the last ones (at most 2 s, a third of a short pause)."""
        total = self.total or 1.0
        fade = min(2.0, total / 3.0)
        elapsed = total - remaining
        return min(1.0, elapsed / fade, remaining / fade) if fade > 0 else 1.0
