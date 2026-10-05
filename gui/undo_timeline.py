"""↶ The undo/redo timeline: which whole autosave environment is current.

Split off gui/main_undo.py as an object of its own rather than state spread over
MainWindow: it owns the two stacks and the current state and knows nothing of
widgets, so it is built and tested without a window. Applying a state, flashing
the rows it changed and tinting the ↶/↷ buttons stay with the window.
"""
import copy


class UndoTimeline:
    """Past states, the current one, and the redo branch after an undo."""

    def __init__(self, limit: int = 50):
        self._limit = limit
        self._undo: list[dict] = []
        self._redo: list[dict] = []
        self.current: dict | None = None

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)

    def next_undo(self) -> dict | None:
        return self._undo[-1] if self._undo else None

    def next_redo(self) -> dict | None:
        return self._redo[-1] if self._redo else None

    def push(self, env: dict) -> bool:
        """Record a fresh state, discarding any redo branch. False when it
        equals the current one — no real change, no step on the timeline.

        Stored as-is: _build_env() returns a freshly-built, never-mutated dict,
        so no deepcopy is needed (that copy was a measurable drop-lag cost)."""
        if self.current is not None and env == self.current:
            return False
        if self.current is not None:
            self._undo.append(self.current)
            if len(self._undo) > self._limit:
                self._undo.pop(0)
        self.current = env
        self._redo.clear()
        return True

    def seed(self, env: dict | None):
        """Start over at `env` — the session just restored — so the very first
        edit is undoable back to it. None keeps the current state."""
        if env is not None:
            self.current = copy.deepcopy(env)
        self._undo.clear()
        self._redo.clear()

    def undo(self) -> tuple[dict | None, dict] | None:
        """Step back: (the state left, the state now current), or None."""
        if not self._undo:
            return None
        before = self.current
        self._redo.append(self.current)
        self.current = self._undo.pop()
        return before, self.current

    def redo(self) -> tuple[dict | None, dict] | None:
        """Step forward again: (the state left, the state now current), or None."""
        if not self._redo:
            return None
        before = self.current
        self._undo.append(self.current)
        self.current = self._redo.pop()
        return before, self.current
