#!/usr/bin/env python3
"""Tests for the toast message (`widgets._show_toast`).

Run:  py -m unittest tests.gui.test_toast -v

One at a time per window. Mark a track and unmark it again and the second
message arrives well inside the 1.5 s the first one lives; drawn as two labels
at the same spot they overlapped into a smudge of both texts.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_toast_"))

from PySide6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from shared import widgets  # noqa: E402


class ToastTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = QWidget()
        self.win.resize(400, 300)
        self.addCleanup(reap_widget, self.win)

    def _labels(self):
        # isHidden, not isVisible: the window itself is never shown in a
        # headless run, which would make every child report invisible.
        return [w for w in self.win.findChildren(QLabel) if not w.isHidden()]

    def test_one_message_shows(self):
        widgets._show_toast(self.win, "🔁  Marked for replace")
        self.assertEqual([lbl.text() for lbl in self._labels()],
                         ["🔁  Marked for replace"])

    def test_a_second_message_replaces_the_first(self):
        """Mark, then unmark: one label, showing the newer text."""
        widgets._show_toast(self.win, "🔁  Marked for replace")
        widgets._show_toast(self.win, "🔁  Unmarked")
        labels = self._labels()
        self.assertEqual(len(labels), 1, "the two messages overlap")
        self.assertEqual(labels[0].text(), "🔁  Unmarked")

    def test_a_long_message_after_a_short_one_is_not_clipped(self):
        """The reused label has to re-measure, or the old width would cut it."""
        widgets._show_toast(self.win, "🔁  Unmarked")
        short = self._labels()[0].width()
        widgets._show_toast(self.win, "🔁  Cleared all replacement marks")
        self.assertGreater(self._labels()[0].width(), short)

    def test_it_stays_centred_on_the_window(self):
        widgets._show_toast(self.win, "🔁  Marked for replace")
        lbl = self._labels()[0]
        self.assertAlmostEqual(lbl.x() + lbl.width() / 2,
                               self.win.width() / 2, delta=1)

    def test_the_clock_restarts_for_the_new_message(self):
        """Otherwise the replacement would inherit what was left of the old
        1.5 s and could vanish almost at once."""
        widgets._show_toast(self.win, "🔁  Marked for replace", msec=50)
        widgets._show_toast(self.win, "🔁  Unmarked", msec=5000)
        self.assertGreater(self.win._toast_timer.remainingTime(), 50)

    def test_it_hides_itself_when_the_time_is_up(self):
        widgets._show_toast(self.win, "🔁  Marked for replace", msec=1)
        self.win._toast_timer.timeout.emit()
        self.assertEqual(self._labels(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
