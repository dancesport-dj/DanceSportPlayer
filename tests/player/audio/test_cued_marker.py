#!/usr/bin/env python3
"""⏯ on a cued title that carries a ↩ time marker asks where it starts.

Run:  py -m unittest tests.player.audio.test_cued_marker -v

"currently only in auto mode i get asked if i want to start from time marker,
but not if i load a title in main player and press play. since i can overlook
that it starts not from beginning i want the hint dialog there too" (Marcel,
2026-11-15).

A title loaded onto the card (double-click cue, a drop, the first title of a
list) is the row the deck already holds, so the ▶ route never asks about it;
⏯ then started it at its marker without a word. Now ⏯ asks first: from the
beginning (the marker goes), at the marker (default), or Cancel, which leaves
it cued. A playhead moved by hand keeps its own question and wins.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cuedmark_"))

from PySide6.QtWidgets import QApplication

from tests.player.audio.test_cued_start import _Desk as _CuedDesk


class _Desk(_CuedDesk):

    def __init__(self, mark=65_000, answer="mark", spot=None, **kw):
        super().__init__(**kw)
        self._big_player = SimpleNamespace(hand_spot=lambda: spot)
        self.mark = mark
        self.answer = answer
        self.asked = []
        self.cleared = []

    def _resume_mark_for(self, path):
        return self.mark

    def _ask_cued_marker(self, ms):
        self.asked.append(ms)
        return self.answer

    def _ask_cued_spot(self, ms):
        self.asked.append(("spot", ms))
        return "spot"

    def _clear_resume(self, path):
        self.cleared.append(path)


class CuedMarkerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_play_asks_where_a_marked_title_starts(self):
        desk = _Desk()
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.asked, [65_000])

    def test_at_the_marker_starts_and_keeps_the_marker(self):
        desk = _Desk(answer="mark")
        desk._resume_tap()
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])
        self.assertEqual(desk.cleared, [])

    def test_from_the_beginning_starts_and_drops_the_marker(self):
        desk = _Desk(answer="top")
        desk._resume_tap()
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])
        self.assertEqual(desk.cleared, [_Desk.PATH])

    def test_cancel_starts_nothing_and_leaves_it_cued(self):
        desk = _Desk(answer=None)
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.loads, [])
        self.assertTrue(desk._cued)
        self.assertEqual(desk.cleared, [])

    def test_a_title_without_a_marker_asks_nothing(self):
        desk = _Desk(mark=None)
        desk._resume_tap()
        self.assertEqual(desk.asked, [])
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])

    def test_a_playhead_moved_by_hand_keeps_its_own_question_only(self):
        desk = _Desk(spot=70_000)
        desk._resume_tap()
        self.assertEqual(desk.asked, [("spot", 70_000)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
