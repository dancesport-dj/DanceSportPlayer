#!/usr/bin/env python3
"""🐂 A 🎶 background pad stays down while a Paso Doble waits to start.

Run:  py -m unittest tests.player.test_cartwall_pd_wait -v

Marcel: no background music while waiting for Paso Doble — the couples walk
on to the call, and the bed swelling up in the 'Start after' seconds plays
over the hall's announcer and the first bar. The deck is stopped through the
wait, so for the wall it reads as the music being over. ⚙ Settings ▸
🎛 Cartwall can let the bed come back in the wait (cart_bg_pd_quiet off).

Between the rumba and the Paso Doble the bed comes back up when the PD has
a 'Start after': its silent wait is the couples' sign, and the bed dips out
for it. Only with 0 s, no wait to dip out for, does it stay down.
"""

import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from planner.playing import cartwall as pc
from player.audio.playback_state import PlaybackState
from player.window.main_cartwall import CartwallMixin
from tests.player.audio.test_pitch_gap import _Desk as _LoadDesk
from tests.player.audio.test_pitch_gap import _entry
from tests.player.audio.test_repeat_list import _Desk as _AdvanceDesk
from tests.player.audio.test_repeat_list import _Fixture
from tests.player.window.test_pd_start_hold import _Desk
from tests.qt_test_support import reap_widget

_STOPPED = QMediaPlayer.PlaybackState.StoppedState
_PLAYING = QMediaPlayer.PlaybackState.PlayingState


class SettingTest(unittest.TestCase):

    def test_the_bed_stays_down_unless_told_otherwise(self):
        self.assertTrue(pc.background_quiet_in_pd_wait({}))
        self.assertTrue(pc.background_quiet_in_pd_wait({"cart_bg_pd_quiet": True}))
        self.assertFalse(pc.background_quiet_in_pd_wait({"cart_bg_pd_quiet": False}))

    def test_before_a_paso_it_stays_down_only_without_a_wait(self):
        self.assertTrue(pc.background_quiet_before_pd({}))
        self.assertTrue(pc.background_quiet_before_pd({"pd_start_delay": 0}))
        self.assertFalse(pc.background_quiet_before_pd({"pd_start_delay": 5}))
        self.assertFalse(pc.background_quiet_before_pd(
            {"pd_start_delay": 0, "cart_bg_pd_quiet": False}))


class _Voices:
    def __init__(self):
        self.told = []

    def set_music_playing(self, playing):
        self.told.append(playing)


class FollowTest(unittest.TestCase):

    def desk(self, holding, settings=None):
        d: Any = CartwallMixin.__new__(CartwallMixin)
        d._cart_voices = _Voices()
        d._player = None
        d._settings = settings or {}
        d._pd_hold = (7, "espana.mp3", 0.0) if holding else None
        return d

    def test_the_wait_counts_as_music(self):
        d = self.desk(holding=True)
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])

    def test_switched_off_the_bed_comes_back_in_the_wait(self):
        d = self.desk(holding=True, settings={"cart_bg_pd_quiet": False})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_without_a_wait_a_stopped_deck_lifts_the_bed(self):
        d = self.desk(holding=False)
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_the_music_itself_still_counts(self):
        d = self.desk(holding=False, settings={"cart_bg_pd_quiet": False})
        d._cart_follow_deck(_PLAYING)
        self.assertEqual(d._cart_voices.told, [True])

    def pause_before(self, dance, settings=None):
        """The rumba is over and the auto-advance pause runs into `dance`."""
        d = self.desk(holding=False, settings=settings)
        path = Path("C:/music/next.mp3")
        meta = SimpleNamespace(dance=dance, path_str=str(path))
        table = SimpleNamespace(_row_meta=SimpleNamespace(at=lambda _r: meta))
        d._between = SimpleNamespace(pending=(table, 4, path))
        return d

    def test_the_pause_before_a_paso_doble_keeps_it_down(self):
        """F17: after a rumba the bed came up in the pause and the Paso Doble
        started over it — with no 'Start after' wait at all just as much."""
        d = self.pause_before("PD")
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])

    def test_the_pause_before_a_paso_with_a_wait_lifts_it(self):
        """Marcel: with a 'Start after' the bed comes back after the rumba —
        the wait dips it out again before the Paso Doble."""
        d = self.pause_before("PD", settings={"pd_start_delay": 5})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_the_pause_before_another_dance_lifts_it(self):
        d = self.pause_before("JI")
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_switched_off_the_pause_before_a_paso_lifts_it(self):
        d = self.pause_before("PD", settings={"cart_bg_pd_quiet": False})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def cued(self, dance, settings=None):
        """The rumba is over, ⏭ Auto is off: `dance` waits cued for ⏯."""
        d = self.desk(holding=False, settings=settings)
        d._cued = True
        d._playback = PlaybackState()
        d._playback.dance = dance
        return d

    def test_a_paso_doble_cued_next_keeps_it_down(self):
        """F17 again: with the queue's bed running, the rumba ended, the
        Paso Doble sat cued for ⏯, and the bed came up in that second."""
        d = self.cued("PD")
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])

    def test_a_paso_doble_with_a_wait_cued_next_lifts_it(self):
        d = self.cued("PD", settings={"pd_start_delay": 5})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_its_wait_itself_still_keeps_it_down(self):
        d = self.desk(holding=True, settings={"pd_start_delay": 5})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])

    def test_another_dance_cued_lifts_it(self):
        d = self.cued("RU")
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_switched_off_a_cued_paso_lifts_it(self):
        d = self.cued("PD", settings={"cart_bg_pd_quiet": False})
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [False])


class _WallDesk(_Desk):
    """The PD wait's desk, with the wall's view of it."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.seen = []

    def _cart_follow_deck(self, state):
        self.seen.append(self._pd_hold is not None)


class HoldTellsTheWallTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_wall_hears_the_wait_start_and_end(self):
        d = _WallDesk()
        d._hold_pd_start(5.0, d.PATH)
        self.assertEqual(d.seen, [True])
        d._end_pd_hold()
        self.assertEqual(d.seen, [True, False])

    def test_a_cut_short_wait_lets_go_of_the_wall_too(self):
        d = _WallDesk()
        d._hold_pd_start(5.0, d.PATH)
        d._skip_pd_hold()
        self.assertEqual(d.seen[-1], False)


class _BedVoices(_Voices):
    """A wall whose 🎶 bed is still heard: it needs `down_ms` to dip out."""

    def __init__(self, down_ms):
        super().__init__()
        self.down_ms = down_ms

    def background_down_in_ms(self):
        return self.down_ms


class StillnessTest(unittest.TestCase):
    """F17: ✋ Manual, the rumba faded out, the bed came up under it, and the
    Paso Doble is started by hand. 'Start after' is the couples' sign that
    the music comes in a few seconds, so those seconds are silent: the bed
    dips out first, and only then does the wait run."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_left(self, down_ms, settings=None):
        d = _WallDesk()
        d._cart_voices = _BedVoices(down_ms)
        d._settings = settings or {}
        d._hold_pd_start(5.0, d.PATH)
        self.addCleanup(d._end_pd_hold)
        return d._pd_hold[2] - time.monotonic()

    def test_the_wait_starts_once_the_bed_is_down(self):
        self.assertAlmostEqual(self.wait_left(2500), 7.5, delta=0.2)

    def test_no_bed_heard_waits_just_the_seconds(self):
        self.assertAlmostEqual(self.wait_left(0), 5.0, delta=0.2)

    def test_switched_off_the_bed_plays_on_through_the_wait(self):
        left = self.wait_left(2500, settings={"cart_bg_pd_quiet": False})
        self.assertAlmostEqual(left, 5.0, delta=0.2)


class _PauseWallDesk(_AdvanceDesk):
    """The advance engine, with the wall's view of the pause."""

    def __init__(self, table, **settings):
        super().__init__(table, **settings)
        self._cart_voices = _Voices()
        self._mix = SimpleNamespace(fade=1.0)
        self.seen = []

    def _start_pause_pads(self):
        pass

    def _cart_follow_deck(self, state):
        self.seen.append(self._between.pending is not None)


class PauseTellsTheWallTest(_Fixture):
    """The wall must hear the pause arm and end, or it never learns that a
    Paso Doble is next."""

    def desk(self):
        self.deck()
        desk = _PauseWallDesk(self.table)
        self.addCleanup(desk.deleteLater)
        return desk

    def test_arming_the_advance_asks_the_wall(self):
        desk = self.desk()
        self.table._current_play_row = self.song_rows()[0]
        desk._queue_auto_advance()
        self.assertEqual(desk.seen, [True])

    def test_the_pause_ending_asks_it_again(self):
        desk = self.desk()
        self.table._current_play_row = self.song_rows()[0]
        desk._queue_auto_advance()
        desk._stop_play_timer()
        self.assertEqual(desk.seen, [True, False])

    def test_a_stop_without_a_pause_leaves_the_wall_alone(self):
        desk = self.desk()
        desk._stop_play_timer()
        self.assertEqual(desk.seen, [])


class _CueWallDesk(_LoadDesk):
    """The real load path, with the wall's view of what it cued."""

    def __init__(self, table):
        super().__init__(table)
        self._cart_voices = _Voices()
        self.seen = []

    def _cart_follow_deck(self, state):
        self.seen.append((self._cued, self._playback.dance))

    def _pd_highlight(self):
        return (False, 2)   # the 🐂 stop is not what this is about


class CueTellsTheWallTest(unittest.TestCase):
    """A cue starts nothing, so the deck's state never changes: the wall has
    to be told, or a Paso Doble cued after the rumba never keeps it down."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cueing_asks_the_wall(self):
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        table.load_warmup([_entry("PD", 1, 60)], "🤸 Eintanzen", "both", "S",
                          False, lambda *a: None, None)
        row = next(r for r, m in enumerate(table._row_meta)
                   if m and m.entry is not None)
        desk = _CueWallDesk(table)
        self.addCleanup(reap_widget, desk)
        table._current_play_row = row
        desk._load_track(table._row_meta[row].entry.path, start=False)
        self.assertEqual(desk.seen[-1:], [(True, "PD")])
        desk._load_track(None)
        self.assertEqual(desk.seen[-1:], [(False, "")], "unloaded: let it up")


if __name__ == "__main__":
    unittest.main()
