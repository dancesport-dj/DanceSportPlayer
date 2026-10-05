#!/usr/bin/env python3
"""Tests for ↶ the undo timeline on its own, without a window.

Run:  py -m unittest tests.gui.test_undo_timeline -v

A step is a whole autosave environment. The timeline only decides which one is
current; applying it, flashing rows and tinting buttons stay with the window.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir
# (the gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_undo_"))

from gui.undo_timeline import UndoTimeline  # noqa: E402


def env(n):
    return {"deck_a": {"paths": [f"t{n}.mp3"]}}


class PushTest(unittest.TestCase):

    def test_the_first_push_only_sets_the_current_state(self):
        t = UndoTimeline()
        self.assertTrue(t.push(env(1)))
        self.assertEqual(t.current, env(1))
        self.assertEqual(t.undo_count, 0)

    def test_a_push_puts_the_old_state_on_the_undo_side(self):
        t = UndoTimeline()
        t.push(env(1))
        t.push(env(2))
        self.assertEqual(t.undo_count, 1)
        self.assertEqual(t.next_undo(), env(1))

    def test_an_unchanged_state_is_not_a_step(self):
        t = UndoTimeline()
        t.push(env(1))
        self.assertFalse(t.push(env(1)))
        self.assertEqual(t.undo_count, 0)

    def test_a_push_drops_the_redo_branch(self):
        t = UndoTimeline()
        t.push(env(1))
        t.push(env(2))
        t.undo()
        self.assertEqual(t.redo_count, 1)
        t.push(env(3))
        self.assertEqual(t.redo_count, 0)

    def test_the_oldest_step_falls_off_at_the_limit(self):
        t = UndoTimeline(limit=3)
        for n in range(6):
            t.push(env(n))
        self.assertEqual(t.undo_count, 3)
        steps = [t.undo()[1] for _ in range(3)]
        self.assertEqual(steps, [env(4), env(3), env(2)])


class UndoRedoTest(unittest.TestCase):

    def setUp(self):
        self.t = UndoTimeline()
        for n in range(3):
            self.t.push(env(n))

    def test_undo_returns_the_state_left_and_the_state_now_current(self):
        self.assertEqual(self.t.undo(), (env(2), env(1)))
        self.assertEqual(self.t.current, env(1))

    def test_redo_goes_forward_again(self):
        self.t.undo()
        self.assertEqual(self.t.redo(), (env(1), env(2)))
        self.assertEqual(self.t.current, env(2))
        self.assertEqual(self.t.redo_count, 0)

    def test_nothing_to_undo_is_None_and_changes_nothing(self):
        t = UndoTimeline()
        t.push(env(1))
        self.assertIsNone(t.undo())
        self.assertEqual(t.current, env(1))

    def test_nothing_to_redo_is_None(self):
        self.assertIsNone(self.t.redo())

    def test_the_peeks_name_the_next_step_either_way(self):
        self.t.undo()
        self.assertEqual(self.t.next_undo(), env(0))
        self.assertEqual(self.t.next_redo(), env(2))


class SeedTest(unittest.TestCase):

    def test_seeding_starts_a_fresh_timeline_at_that_state(self):
        t = UndoTimeline()
        t.push(env(1))
        t.push(env(2))
        t.undo()
        t.seed(env(9))
        self.assertEqual(t.current, env(9))
        self.assertEqual((t.undo_count, t.redo_count), (0, 0))

    def test_the_seed_is_a_copy(self):
        """The restored session's env may still be edited by the caller; the
        baseline an undo returns to must not move with it."""
        t = UndoTimeline()
        e = env(1)
        t.seed(e)
        e["deck_a"]["paths"].append("x.mp3")
        self.assertEqual(t.current, env(1))

    def test_seeding_nothing_keeps_the_state_but_clears_the_steps(self):
        t = UndoTimeline()
        t.push(env(1))
        t.push(env(2))
        t.seed(None)
        self.assertEqual(t.current, env(2))
        self.assertEqual(t.undo_count, 0)


class WindowTest(unittest.TestCase):
    """The window's side: the step it lands on is applied, and the ↶/↷
    buttons count what is left."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from tests.qt_test_support import stub_window_startup

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_undo_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def window(self):
        from tests.qt_test_support import reap_widget
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        win._seed_undo_baseline()
        self.applied = []
        win._apply_env = self.applied.append
        return win

    def test_undo_applies_the_step_before_and_redo_the_one_after(self):
        win = self.window()
        base = win._undo_timeline.current
        edited = dict(base or {}, marker="edited")
        win._push_undo(edited)
        self.assertEqual(win._undo_btn.text(), "↶ 1")

        win._undo()
        self.assertEqual(self.applied, [base])
        self.assertEqual(win._undo_btn.text(), "↶")
        self.assertEqual(win._redo_btn.text(), "↷ 1")

        win._redo()
        self.assertEqual(self.applied, [base, edited])
        self.assertEqual(win._redo_btn.text(), "↷")

    def test_nothing_to_undo_applies_nothing(self):
        win = self.window()
        win._undo()
        win._redo()
        self.assertEqual(self.applied, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
