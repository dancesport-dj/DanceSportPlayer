#!/usr/bin/env python3
"""⏯ on a cued title whose playhead was moved by hand asks where it starts.

Run:  py -m unittest tests.player.audio.test_cued_spot -v

"when i have the next titel loaded in main player then click somewhere in
middle of waveform and then play it starts at beginning? in this case i also
want a ask dialog if play at marker or beginning" (Marcel, 2026-11-14).

A click on the 〰 strip of a cued title moved the playhead, but ⏯ starts a
cued title through the full start (call, pitch, hold), which loads it afresh
from the top. Now ⏯ asks first: at the spot the playhead was put (the
default), from the beginning (a ↩ time marker goes too, as in the marker
question), or Cancel, which leaves it cued.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cuedspot_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.widgets.player import BigPlayerWidget
from tests.player.audio.test_cued_start import _Desk as _CuedDesk
from tests.qt_test_support import reap_widget


class CardSpotTest(unittest.TestCase):
    """The card keeps where a hand put the playhead, until the next title."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)

    def test_a_click_on_the_waveform_is_the_spot(self):
        self.card._on_wave_released(70_000)
        self.assertEqual(self.card.hand_spot(), 70_000)

    def test_a_new_title_has_no_spot(self):
        self.card._on_wave_released(70_000)
        self.card.set_waveform_track(None)
        self.assertIsNone(self.card.hand_spot())

    def test_nothing_moved_is_no_spot(self):
        self.assertIsNone(self.card.hand_spot())

    def test_back_at_the_top_is_no_spot(self):
        self.card._on_wave_released(70_000)
        self.card._seek_by_hand(0)
        self.assertIsNone(self.card.hand_spot())


class _Desk(_CuedDesk):

    def __init__(self, spot=70_000, answer="spot", **kw):
        super().__init__(**kw)
        self._big_player = SimpleNamespace(hand_spot=lambda: spot)
        self.answer = answer
        self.asked = []
        self.cleared = []
        self.spot_at_load = []

    def _ask_cued_spot(self, ms):
        self.asked.append(ms)
        return self.answer

    def _clear_resume(self, path):
        self.cleared.append(path)

    def _play_or_stop(self, path, start=True):
        super()._play_or_stop(path, start)
        self.spot_at_load.append(self._playback.spot_ms)

    def _resume_mark_for(self, path):
        return 5_000


class CuedSpotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_play_asks_where_it_starts(self):
        desk = _Desk()
        desk._resume_tap()
        self.assertEqual(desk.asked, [70_000])

    def test_at_the_spot_starts_there(self):
        desk = _Desk(answer="spot")
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])
        self.assertEqual(desk.spot_at_load, [70_000])
        self.assertEqual(desk.cleared, [])

    def test_from_the_beginning_starts_at_the_top_and_drops_the_marker(self):
        desk = _Desk(answer="top")
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])
        self.assertEqual(desk.spot_at_load, [None])
        self.assertEqual(desk.cleared, [_Desk.PATH])

    def test_cancel_starts_nothing_and_leaves_it_cued(self):
        desk = _Desk(answer=None)
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.loads, [])
        self.assertTrue(desk._cued)

    def test_an_untouched_playhead_asks_nothing(self):
        desk = _Desk(spot=None)
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.asked, [])
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])

    def test_the_load_spends_the_spot_once_instead_of_the_marker(self):
        desk = _Desk()
        desk._playback.spot_ms = 70_000
        self.assertEqual(desk._start_seek_for(_Desk.PATH), 70_000)
        self.assertIsNone(desk._playback.spot_ms)
        self.assertEqual(desk._start_seek_for(_Desk.PATH), 5_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
