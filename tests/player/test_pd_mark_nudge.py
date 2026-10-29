#!/usr/bin/env python3
"""🎯 A hand-set Paso Doble mark sits on a 0.1 s raster and −/+ nudges it.

A 🎯 tap lands a little early or late. The chips showed whole seconds only,
so a mark could be neither read nor corrected finer than a second; the only
fix was a new tap within 3 s. Now a chip reads "0:44.3" and its −/+ move that
one mark by 0.1 s.

Run:  py -m unittest tests.player.test_pd_mark_nudge -v
"""

import os
import tempfile
import unittest
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_nudge_"))

from PySide6.QtWidgets import QApplication, QToolButton

from player.widgets.play_mode_panel import PlayModePanel
from tests.player.test_pd_manual_kept import PATH, _Desk

_app = QApplication.instance() or QApplication([])


class _Player:
    def __init__(self, ms):
        self.ms = ms

    def duration(self):
        return 0

    def position(self):
        return self.ms


class ChipNudgeTest(unittest.TestCase):

    def setUp(self):
        self.panel = PlayModePanel({"pd_highlight_stop": True})
        self.addCleanup(self.panel.deleteLater)
        self.nudges = []
        self.panel.pdMarkNudgeRequested.connect(
            lambda secs, delta: self.nudges.append((secs, delta)))
        self.panel.set_pd_marks([44.3])

    def _button(self, text):
        hits = [b for b in self.panel.pd_marks_box.findChildren(QToolButton)
                if b.text() == text]
        self.assertEqual(len(hits), 1, text)
        return hits[0]

    def test_the_chip_shows_tenths(self):
        self._button("0:44.3  ✕")

    def test_minus_and_plus_ask_for_a_tenth(self):
        self._button("−").click()
        self._button("+").click()
        self.assertEqual(self.nudges, [(44.3, -0.1), (44.3, 0.1)])


class DeskNudgeTest(unittest.TestCase):

    def setUp(self):
        self.desk = _Desk()
        self.stub: Any = self.desk   # the test doubles behind its typed attributes

    def _marks(self):
        return self.desk._pd_highlights[str(PATH)]

    def test_a_tap_lands_on_the_tenth(self):
        self.stub._player = _Player(6043)
        self.desk._learn_pd_highlight()
        self.assertEqual(self._marks(), [6.0])

    def test_a_nudge_moves_that_mark_and_rearms_the_stop(self):
        self.desk._store_pd_marks(PATH, [6.0, 44.3])
        self.desk._nudge_pd_mark(44.3, 0.1)
        self.assertEqual(self._marks(), [6.0, 44.4])
        self.desk._nudge_pd_mark(6.0, -0.1)
        self.assertEqual(self._marks(), [5.9, 44.4])
        self.assertEqual(self.stub._library.cache.times[str(PATH)], [5.9, 44.4])
        self.assertTrue(self.stub._library.cache.is_pd_manual(PATH))
        self.assertEqual(self.desk._pd_stop_at, 5.9)

    def test_a_nudge_never_goes_below_a_tenth(self):
        self.desk._store_pd_marks(PATH, [0.1])
        self.desk._nudge_pd_mark(0.1, -0.1)
        self.assertEqual(self._marks(), [0.1])


if __name__ == "__main__":
    unittest.main()
