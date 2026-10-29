#!/usr/bin/env python3
"""🎶 A starting title waits until a background pad has faded out.

Run:  py -m unittest tests.player.test_cartwall_bed_first -v

Marcel: "Background fading: make it configurable whether it overlaps or not.
Default: complete fade-out, then the main music starts." The dip itself keeps
its own time (🌙 cart_bg_fade_out_ms); ⚙ Settings ▸ 🎛 Cartwall can let the
title start over it again (cart_bg_overlap).
"""

import unittest
from typing import Any, cast

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from planner.playing import cartwall as pc
from player.audio.playback_state import PlaybackState
from player.window.main_cartwall import CartwallMixin
from tests.player.audio.test_pitch_gap import _Desk as _LoadDesk
from tests.player.audio.test_pitch_gap import _entry
from tests.player.test_cartwall_voices import _pad, _VoiceCase
from tests.qt_test_support import reap_widget

_STOPPED = QMediaPlayer.PlaybackState.StoppedState


class SettingTest(unittest.TestCase):

    def test_the_title_waits_unless_told_otherwise(self):
        self.assertFalse(pc.background_overlaps({}))
        self.assertFalse(pc.background_overlaps({"cart_bg_overlap": False}))
        self.assertTrue(pc.background_overlaps({"cart_bg_overlap": True}))


class DownInTest(_VoiceCase):
    """How long the bed still needs to be silent."""

    def _bed(self):
        self.v.fire((0, 0, 0), _pad("bed.mp3", background=True))

    def test_nothing_on_the_wall_nothing_to_wait_for(self):
        self.assertEqual(self.v.background_down_in_ms(), 0)

    def test_an_ordinary_pad_is_no_bed(self):
        self.v.fire((0, 0, 0), _pad("tusch.mp3"))
        self.assertEqual(self.v.background_down_in_ms(), 0)

    def test_a_bed_at_full_volume_takes_the_whole_fade_out(self):
        self._bed()
        self.assertEqual(self.v.background_down_in_ms(), pc.DEFAULT_BG_FADE_OUT_MS)
        self.v.set_background_fade_out(1500)
        self.assertEqual(self.v.background_down_in_ms(), 1500)

    def test_a_bed_halfway_down_takes_the_rest(self):
        self._bed()
        self.v.set_background_fade_out(1000)
        self.v._bg = 0.5
        self.assertEqual(self.v.background_down_in_ms(), 500)

    def test_a_bed_already_down_is_no_wait(self):
        self._bed()
        self.v.set_music_playing(True)
        while self.v._bg_ramp.isActive():
            self.v._step_background()
        self.assertEqual(self.v.background_down_in_ms(), 0)

    def test_a_muted_wall_is_no_wait(self):
        self._bed()
        self.v.set_muted(True)
        self.assertEqual(self.v.background_down_in_ms(), 0)

    def test_no_fade_out_is_no_wait(self):
        self._bed()
        self.v.set_background_fade_out(0)
        self.assertEqual(self.v.background_down_in_ms(), 0)


class _Voices:
    def __init__(self, ms=0):
        self.ms = ms
        self.told = []

    def background_down_in_ms(self):
        return self.ms

    def set_music_playing(self, playing):
        self.told.append(playing)


class FollowTest(unittest.TestCase):

    def test_the_wait_counts_as_music(self):
        """A stray Stopped while the bed dips must not bring it back up."""
        d: Any = CartwallMixin.__new__(CartwallMixin)
        d._cart_voices = _Voices()
        d._player = None
        d._settings = {}
        d._pd_hold = None
        d._playback = PlaybackState(bed_wait=4)
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])
        d._playback.bed_wait = None
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True, False])


class _BedDesk(_LoadDesk):
    """The real load path, with a wall whose bed is up."""

    def __init__(self, table, ms, settings=None):
        super().__init__(table, settings=settings)
        self.wall = _Voices(ms)
        self._cart_voices = cast(Any, self.wall)
        self.followed = []
        self.called = []

    def _cart_follow_deck(self, state):
        self.followed.append(self._playback.bed_wait)

    def _maybe_announce_start(self, ent):
        self.called.append(ent)

    def _is_player_running(self):
        return "play" in self.log

    def _set_countdown(self, text):
        pass


class LoadWaitsForTheBedTest(unittest.TestCase):
    """The real `_load_track` (see tests.player.audio.test_pitch_gap)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _bed_desk(self, ms, settings=None):
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load_warmup(
            [_entry("QS", 1, 50), _entry("QS", 2, 52)],
            "🤸 Eintanzen", "both", "S", False, lambda *a: None, None)
        self.rows = [r for r, m in enumerate(self.table._row_meta)
                     if m and m.entry is not None]
        desk = _BedDesk(self.table, ms, settings)
        self.addCleanup(reap_widget, desk)
        return desk

    def _start(self, desk, i=0):
        self.table._current_play_row = self.rows[i]
        path = self.table._row_meta[self.rows[i]].entry.path
        desk._load_track(path)
        return path

    def test_the_title_waits_for_the_bed_to_go_down(self):
        desk = self._bed_desk(200)
        path = self._start(desk)
        self.assertNotIn("play", desk.log, "the bed is still up")
        self.assertEqual(desk.wall.told, [True], "…and on its way down")
        self.assertEqual(desk.called, [], "no call over the tail of the bed")
        token = desk._playback.token
        self.assertEqual(desk._playback.bed_wait, token)
        desk._release_after_bed(token, path, "ent")
        self.assertIn("play", desk.log)
        self.assertEqual(desk.called, ["ent"], "named over the first bars as ever")
        self.assertIsNone(desk._playback.bed_wait)

    def test_switched_to_overlap_it_starts_at_once(self):
        desk = self._bed_desk(200, settings={"cart_bg_overlap": True})
        self._start(desk)
        self.assertIn("play", desk.log)
        self.assertEqual(desk.wall.told, [])
        self.assertIsNone(desk._playback.bed_wait)

    def test_no_bed_up_no_wait(self):
        desk = self._bed_desk(0)
        self._start(desk)
        self.assertIn("play", desk.log)
        self.assertIsNone(desk._playback.bed_wait)

    def test_a_stop_in_the_wait_keeps_the_music_off_and_lets_the_bed_back(self):
        desk = self._bed_desk(200)
        path = self._start(desk)
        token = desk._playback.token
        desk._playback.token += 1           # ⏹, or the next title
        desk._release_after_bed(token, path, "ent")
        self.assertNotIn("play", desk.log)
        self.assertEqual(desk.called, [])
        self.assertIsNone(desk._playback.bed_wait)
        self.assertEqual(desk.followed[-1], None, "the wall decides again")

    def test_a_later_wait_is_not_cleared_by_an_earlier_one(self):
        desk = self._bed_desk(200)
        path = self._start(desk)
        first = desk._playback.token
        self._start(desk, 1)                # the next title, bed still dipping
        desk._release_after_bed(first, path, "ent")
        self.assertEqual(desk._playback.bed_wait, desk._playback.token)
        self.assertNotIn("play", desk.log)


if __name__ == "__main__":
    unittest.main()
