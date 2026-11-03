"""#127: the cartwall looks for a pad's file off the GUI thread.

A pad on a dead network share used to stall the whole window on every page
turn, because the check ran where the buttons are painted. Now an answer that
is not known yet reads as "there" and the real one arrives a moment later.
"""
import os
import sys
import tempfile
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartchk_"))

from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.widgets import cartwall as gc
from tests.qt_test_support import reap_widget, settle_wall_checks

_app = QApplication.instance() or QApplication(sys.argv)


def _wall(exists):
    w = gc.CartwallWidget()
    w.resize(600, 400)
    w.set_file_check(exists)
    w.set_wall(pc.DEFAULT_GRID,
               [pc.Page(pads={(0, 0): pc.CartPad(path="gone.mp3")})])
    return w


class OffThreadFileCheckTest(unittest.TestCase):

    def test_the_check_never_runs_on_the_gui_thread(self):
        threads = []
        w = _wall(lambda p: threads.append(threading.current_thread()) or True)
        self.addCleanup(reap_widget, w)
        settle_wall_checks(w)
        self.assertTrue(threads)
        self.assertNotIn(threading.main_thread(), threads)

    def test_a_slow_share_does_not_hold_the_wall(self):
        release = threading.Event()
        w = _wall(lambda p: release.wait(5) and False)
        self.addCleanup(reap_widget, w)
        self.addCleanup(release.set)
        start = time.monotonic()
        w._rebuild()
        self.assertLess(time.monotonic() - start, 1.0)
        self.assertFalse(w._buttons[(0, 0, 0)]._missing)   # not known yet

    def test_the_answer_marks_the_pad_when_it_arrives(self):
        w = _wall(lambda p: False)
        self.addCleanup(reap_widget, w)
        settle_wall_checks(w)
        button = w._buttons[(0, 0, 0)]
        self.assertTrue(button._missing)
        self.assertTrue(button._title.text().startswith("⚠"))
        self.assertIsNotNone(w.pad_at((0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
