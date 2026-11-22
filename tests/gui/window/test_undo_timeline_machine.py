"""Model-based test of ↶ the undo timeline: random push/undo/redo/seed runs
against a plain list of states and a cursor into it.

The example tests in test_undo_timeline.py walk a few chosen paths; this lets
Hypothesis string the steps together in any order, shrinks a failing run to
the shortest one, and checks after every step that the timeline and the model
agree on the current state, what ↶ and ↷ would bring back, and the counts the
buttons are tinted from.

Run:  .venv/Scripts/python.exe -m pytest tests/gui/window/test_undo_timeline_machine.py -n0
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_undo_"))

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from gui.window.undo_timeline import UndoTimeline

LIMIT = 4   # small, so that runs reach the cap
states = st.integers(0, 5).map(lambda n: {"deck_a": {"paths": [f"t{n}.mp3"]}})


class UndoTimelineMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.timeline = UndoTimeline(limit=LIMIT)
        # The model: every state still reachable, oldest first, and which one is current.
        self.history: list[dict] = []
        self.at = -1

    @rule(env=states)
    def push(self, env):
        changed = self.timeline.push(env)
        current = self.history[self.at] if self.history else None
        self.assertEqual(changed, env != current)
        if changed:
            self.history = self.history[: self.at + 1] + [env]
            if len(self.history) > LIMIT + 1:   # LIMIT undo steps + the current state
                self.history.pop(0)
            self.at = len(self.history) - 1

    @rule()
    def undo(self):
        step = self.timeline.undo()
        if self.at <= 0:
            self.assertIsNone(step)
            return
        self.assertEqual(step, (self.history[self.at], self.history[self.at - 1]))
        self.at -= 1

    @rule()
    def redo(self):
        step = self.timeline.redo()
        if self.at < 0 or self.at == len(self.history) - 1:
            self.assertIsNone(step)
            return
        self.assertEqual(step, (self.history[self.at], self.history[self.at + 1]))
        self.at += 1

    @rule(env=st.none() | states)
    def seed(self, env):
        self.timeline.seed(env)
        if env is not None:
            self.history, self.at = [env], 0
        elif self.history:
            self.history, self.at = [self.history[self.at]], 0

    @invariant()
    def the_timeline_matches_the_model(self):
        t = self.timeline
        self.assertEqual(t.current, self.history[self.at] if self.history else None)
        self.assertEqual(t.undo_count, max(self.at, 0))
        self.assertEqual(t.redo_count, len(self.history) - 1 - self.at if self.history else 0)
        self.assertEqual(t.next_undo(), self.history[self.at - 1] if self.at > 0 else None)
        self.assertEqual(t.next_redo(), self.history[self.at + 1] if t.redo_count else None)

    def assertEqual(self, a, b):   # noqa: N802 - unittest's name, used as in the other tests
        assert a == b, (a, b)

    def assertIsNone(self, a):   # noqa: N802
        assert a is None, a


UndoTimelineMachine.TestCase.settings = settings(max_examples=200, stateful_step_count=30, deadline=None)


class UndoTimelineMachineTest(UndoTimelineMachine.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
