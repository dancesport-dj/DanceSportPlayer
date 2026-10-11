"""↩ Where each title was left — the marks the Remember switch keeps.

Split off MainWindow, where they were a loose dict and two class constants
next to the player code that fills them. Held here, the rules for what is
worth a mark are tested without a window, and a playback part that is later
cut out of the window takes this one object along.
"""
from pathlib import Path


class ResumeMarks:
    """Positions in ms, keyed by path — one player serves every deck, so
    leaving a title to hear another one is the normal way to lose your place
    in it. Session-scoped on purpose (the ▶️ Remember switch on the Playing
    panel): a mark is about the evening being planned, not something to find
    again next week."""

    # Both windows are the 10 s the rest of the player already counts in
    # (`_PLAYED_AFTER_MS`, the point a title counts as heard).
    MIN_MS = 10_000    # the first seconds are not a place to come back to
    TAIL_MS = 10_000   # stopped this near the end, a title is finished

    def __init__(self) -> None:
        self.at: dict[str, int] = {}

    def get(self, path: Path) -> int | None:
        return self.at.get(str(path))

    def note(self, path: Path, pos_ms: int, dur_ms: int) -> None:
        """Keep (or drop) the mark for `path` at `pos_ms`.

        Two guards decide whether there is anything worth coming back to: the
        opening seconds are not a place anyone wants back, and a title stopped
        on its last note is one that finished — resuming there would play the
        run-out and call it a title.
        """
        key = str(path)
        done = dur_ms > 0 and pos_ms >= dur_ms - self.TAIL_MS
        if pos_ms < self.MIN_MS or done:
            self.at.pop(key, None)
        else:
            self.at[key] = int(pos_ms)

    def clear(self, path: Path) -> bool:
        """Forget where `path` stood. True when it had a mark."""
        return self.at.pop(str(path), None) is not None

    def clear_all(self) -> bool:
        """Forget every mark. True when there was one."""
        had = bool(self.at)
        self.at.clear()
        return had
