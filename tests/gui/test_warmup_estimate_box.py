#!/usr/bin/env python3
"""⏱ The Eintanzen dialog's "songs needed for N hours" box.

Run:  py -m unittest tests.gui.test_warmup_estimate_box -v

The numbers come from `planner.warmup.estimate_warmup_counts` (tested in
tests/planner/test_warmup_estimate.py); here: the text, and that the box
recomputes on its own thread whenever the hours or the options change.
"""

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.warmup_estimate import WarmupEstimateBox, estimate_text  # noqa: E402
from planner.warmup import _WARMUP_BALLROOM, _WARMUP_LATIN, _WARMUP_MODE  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_ALL = _WARMUP_BALLROOM + _WARMUP_LATIN + _WARMUP_MODE


class EstimateTextTest(unittest.TestCase):

    def test_stock_numbers_per_section(self):
        text = estimate_text({"LW": (14.1, 15), "TG": (10.5, 12), "RB": (14.2, 15),
                              "DISCOFOX": (10.4, 13)}, (119.4, 123), 6)
        self.assertIn("6 h", text)
        self.assertIn("119", text)
        self.assertIn("Standard: LW 15 · TG 12", text)
        self.assertIn("Latin: RB 15", text)
        self.assertIn("Social: Discofox 13", text)

    def test_a_section_without_dances_is_left_out(self):
        text = estimate_text({"LW": (3.0, 3)}, (20.0, 20), 1.5)
        self.assertIn("1.5 h", text)
        self.assertNotIn("Latin", text)
        self.assertNotIn("Social", text)


class EstimateBoxTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.options = {"include_latin": False}
        self.box = WarmupEstimateBox({c: [180] for c in _ALL}, lambda: dict(self.options))
        self.addCleanup(reap_widget, self.box)

    def _wait_for(self, needle):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.app.processEvents()
            if needle in self.box.label.text():
                return self.box.label.text()
            time.sleep(0.01)
        self.fail(f"{needle!r} never showed, last text: {self.box.label.text()!r}")

    def test_it_fills_in_on_its_own(self):
        self.box.hours_spin.setValue(1)
        text = self._wait_for("about 20 songs")
        self.assertIn("Standard:", text)
        self.assertNotIn("Latin:", text)

    def test_hours_and_options_recompute(self):
        self.box.hours_spin.setValue(1)
        self._wait_for("about 20 songs")
        self.box.hours_spin.setValue(2)
        self._wait_for("about 40 songs")
        self.options = {"include_standard": False}
        self.box.refresh()
        text = self._wait_for("Latin:")
        self.assertNotIn("Standard:", text)

    def test_changing_the_hours_hands_on_the_song_count(self):
        """Max tracks follows: the box announces how many songs the hours need."""
        seen = []
        self.box.songsNeeded.connect(seen.append)
        self.box.hours_spin.setValue(2)
        self._wait_for("about 40 songs")
        self.app.processEvents()
        self.assertEqual(seen[-1], 40)

    def test_opening_the_dialog_announces_nothing(self):
        """The first estimate is for the default hours nobody picked — Max
        tracks keeps its own default until the hours are changed."""
        seen = []
        self.box.songsNeeded.connect(seen.append)
        self._wait_for("about ")
        self.app.processEvents()
        self.assertEqual(seen, [])

    def test_a_change_during_a_run_is_not_lost(self):
        self.box.hours_spin.setValue(3)
        self.box.hours_spin.setValue(1)
        self.box.hours_spin.setValue(2)
        self._wait_for("about 40 songs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
