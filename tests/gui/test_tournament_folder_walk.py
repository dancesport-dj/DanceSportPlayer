"""🏆 A folder added to the tree is read without freezing the window.

Run:  py -m unittest tests.gui.test_tournament_folder_walk -v

Marcel: "when i import playlist from a folder the dialog that appears is
strange like more overlaying over each other and no progress bar". The walk
ran on the UI thread with the wait dialog raised at once: a folder of eight
playlists flashed a half-built dialog for a quarter second, and a slow one sat
on a bar that could not move. The walk now runs beside the event loop, and the
dialog only comes when it is worth one.
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_walk_"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import tournament_tree as gt  # noqa: E402
from planner.store import JsonStore  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


class _Busy(gt.BusyDialog):
    """The real dialog, remembering whether it ever came on screen."""
    shown = []

    def showEvent(self, event):
        _Busy.shown.append(self)
        super().showEvent(event)


class FolderWalkTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_walk_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane.show()
        self.day = self.dir / "23.11.2013 Moers SenII STD"
        self.day.mkdir()
        for i in range(8):
            (self.day / f"T{i}.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        _Busy.shown = []
        patch = mock.patch.object(gt, "BusyDialog", _Busy)
        patch.start()
        self.addCleanup(patch.stop)

    def add(self):
        self.pane._add_m3u_files(self.pane._target_children(), [self.day])

    def test_a_quick_folder_raises_no_dialog(self):
        self.add()
        self.assertEqual(_Busy.shown, [])
        self.assertEqual(len(self.pane._nodes[0]["children"]), 8)

    def test_the_window_keeps_running_while_a_slow_folder_is_listed(self):
        real = Path.iterdir
        day = self.day

        def slow(path):
            if path == day:
                time.sleep(1.0)       # a network or Dropbox listing
            return real(path)

        fired = []
        start = time.monotonic()
        QTimer.singleShot(100, lambda: fired.append(time.monotonic() - start))
        with mock.patch.object(Path, "iterdir", slow):
            self.add()
        self.assertTrue(fired, "no timer ran during the walk")
        self.assertLess(fired[0], 0.6, "the event loop stood still during the listing")
        self.assertEqual(len(_Busy.shown), 1, "a slow walk gets its dialog")
        self.assertFalse(_Busy.shown[0].isVisible(), "and it is closed afterwards")
        self.assertEqual(len(self.pane._nodes[0]["children"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
