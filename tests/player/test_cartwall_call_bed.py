#!/usr/bin/env python3
"""🎶 The bed while a title is called first (⏳), on the REAL wall.

Run:  py -m unittest tests.player.test_cartwall_call_bed -v

Marcel: a title started by hand with the dance called first played the
background music "for a brief moment". `test_cartwall_bed_first` stubs
`_cart_follow_deck`, so it cannot see what the wall really does; here the deck
is wired to the real `CartwallMixin._cart_follow_deck` and a real `CartVoices`
(stub players), and the bed's level is read while the voice runs.
"""

import unittest
from typing import Any

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from player.audio.cart_voices import CartVoices
from player.window.main_cartwall import CartwallMixin
from tests.player.audio.test_pitch_gap import _Desk as _LoadDesk
from tests.player.audio.test_pitch_gap import _entry
from tests.player.test_cartwall_voices import _factory, _pad
from tests.qt_test_support import reap_widget

_STOPPED = QMediaPlayer.PlaybackState.StoppedState


class _Backend:
    """The deck's player: stopped, as it is in a pause."""

    def __init__(self, log):
        self.log = log
        self._src = None

    def stop(self):
        pass

    def setSource(self, url):
        self._src = url

    def source(self):
        return self._src

    def play(self):
        self.log.append("play")

    def playbackState(self):
        return _STOPPED


class _WallDesk(_LoadDesk):
    """The real load path over the real wall; only the voice is a stand-in."""

    def __init__(self, table, settings=None):
        super().__init__(table, settings=settings)
        self._player = _Backend(self.log)
        self.wall = CartVoices(voices=4, factory=_factory)
        self.wall.set_level(1.0)
        self.wall.set_background_fade_out(1000)
        self._cart_voices = self.wall
        self._pd_hold = None
        self.bed_when_called = []
        self.waited_for = []

    # The real follow logic, not the stub the other bed tests use.
    _cart_follow_deck = CartwallMixin._cart_follow_deck

    def _announce_start_first(self, ent):
        self.bed_when_called.append(self.wall._bg)
        return True

    def _wait_for_announcement(self, path):
        self.waited_for.append(path)

    def _maybe_announce_start(self, ent):
        pass

    def _set_countdown(self, text):
        pass


class CallFirstOnTheRealWallTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load_warmup(
            [_entry("QS", 1, 50), _entry("QS", 2, 52)],
            "🤸 Eintanzen", "both", "S", False, lambda *a: None, None)
        self.rows = [r for r, m in enumerate(self.table._row_meta)
                     if m and m.entry is not None]
        self.desk: Any = _WallDesk(self.table)
        self.addCleanup(reap_widget, self.desk)
        self.addCleanup(self.desk.wall.shutdown)

    def _start(self):
        self.table._current_play_row = self.rows[0]
        path = self.table._row_meta[self.rows[0]].entry.path
        self.desk._load_track(path)
        return path

    def _bed_up(self):
        """The pause's own bed: a background pad at full volume."""
        self.desk.wall.fire((0, 0, 0), _pad("bed.mp3", loop=True, background=True))
        self.assertEqual(self.desk.wall._bg, 1.0)

    def test_the_bed_is_aimed_down_for_the_whole_call(self):
        self._bed_up()
        self._start()
        wall = self.desk.wall
        self.assertEqual(wall._bg_target, 0.0, "the bed goes down for the call")
        self.assertFalse(wall._bg_hold.isActive(), "and nothing waits to lift it")

    def test_the_call_is_not_spoken_over_a_bed_that_is_still_up(self):
        self._bed_up()
        path = self._start()
        desk = self.desk
        self.assertEqual(desk.bed_when_called, [], "no voice while the bed dips")
        self.assertNotIn("play", desk.log)
        while desk.wall._bg_ramp.isActive():       # the dip runs its course
            desk.wall._step_background()
        desk._release_after_bed(desk._playback.token, path, "ent")
        self.assertEqual(desk.bed_when_called, [0.0],
                         "the voice comes in once the bed is down")
        self.assertEqual(desk.waited_for, [path], "and the music waits for it")
        self.assertNotIn("play", desk.log)
        self.assertEqual(desk._playback.bed_wait, desk._playback.token,
                         "the bed stays down for the call")

    def test_a_stray_stopped_in_the_call_does_not_lift_the_bed(self):
        self._bed_up()
        self._start()
        self.desk._cart_follow_deck(_STOPPED)
        self.assertEqual(self.desk.wall._bg_target, 0.0)
        self.assertFalse(self.desk.wall._bg_hold.isActive())


if __name__ == "__main__":
    unittest.main()
