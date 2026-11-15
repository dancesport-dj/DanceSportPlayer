#!/usr/bin/env python3
"""A fade-in is a slope, not a stair.

Run:  py -m unittest tests.player.audio.test_fade_in_steps -v

The 🌅 fade-in level moved only on the 200 ms play tick: on a 3 s fade-in the
music came up in fifteen steps, the first one from silence straight to about
-23 dB. The fade-out got its fine steps in 2.0.1 (test_fade_out_steps); the
fade-in now rides the same 25 ms ramp timer. Qt's player updates position()
only about every 100 ms (measured on 6.11: 16 distinct values in 1.5 s), so
the heard time is carried on by the clock in between.

Driven through the real `_on_play_tick` and `_step_volume_ramp` on a virtual
clock, at every tick phase.
"""
import unittest
from unittest import mock

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.audio.playback_state import PlaybackState
from player.window.main_player import PlayerControlMixin
from tests.player.audio.test_fade_out_steps import _Clock, _Desk, _Media, _run, _Timer
from tests.qt_test_support import reap_widget

FADE_IN = 3.0
# One 25 ms step of a 3 s fade-in is 0.008; one 200 ms tick was 0.067.
FINE = 0.02
QUIET = 0.013


class _GrainyMedia(_Media):
    """A position that moves in 100 ms jumps, as Qt's does."""

    def position(self):
        return super().position() // 100 * 100


class _FadeInDesk(_Desk):

    def __init__(self, clock, **kw):
        super().__init__(clock, **kw)
        self._player = _GrainyMedia(clock, kw.get("start_secs", 0.0))
        self._playback.fade_in_from = 0.0
        self._playback.fade_in_secs = FADE_IN
        self._mix.fade_in = 0.0
        self.ins = []

    def _apply_volume(self):
        self.ins.append(self._mix.fade_in)


def _biggest_rise(levels):
    return max(b - a for a, b in zip(levels, levels[1:], strict=False))


class FadeInStepTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def phases(self):
        return range(5, 205, 10)

    def desk(self, clock, **kw):
        d = _FadeInDesk(clock, **kw)
        self.addCleanup(reap_widget, d)
        return d

    def test_the_fade_in_rises_in_fine_steps_at_every_tick_phase(self):
        worst = 0.0
        for phase in self.phases():
            clock = _Clock()
            with mock.patch("time.monotonic", clock):
                desk = self.desk(clock, start_secs=0.0)
                _run(desk, clock, phase, 1.0)   # the first tick sets it going
                desk.ins.clear()
                _run(desk, clock, phase, 3.5)
            self.assertEqual(desk._mix.fade_in, 1.0, phase)
            worst = max(worst, _biggest_rise(desk.ins))
        self.assertLessEqual(worst, FINE)

    def test_the_first_sound_is_quiet_once_the_steps_run_from_the_start(self):
        """The play start sets the steps going (see the playback-state test):
        the music comes out of silence, not with a 200 ms jump."""
        worst = 0.0
        for phase in self.phases():
            clock = _Clock()
            with mock.patch("time.monotonic", clock):
                desk = self.desk(clock, start_secs=0.0)
                desk._ramp_timer.start()
                _run(desk, clock, phase, 0.5)
            loud = [lv for lv in desk.ins if lv > 0.0001]
            self.assertTrue(loud, phase)
            worst = max(worst, loud[0])
        self.assertLessEqual(worst, QUIET)

    def test_the_steps_stop_when_the_fade_in_is_through(self):
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=0.0)
            _run(desk, clock, 5, 4.0)
        self.assertIsNone(desk._playback.fade_in_from)
        self.assertEqual(desk._mix.fade_in, 1.0)
        self.assertFalse(desk._ramp_timer.running)

    def test_a_pause_holds_the_level_between_ticks(self):
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=1.0)
            desk._on_play_tick()
            held = desk._mix.fade_in
            desk._player.playbackState = lambda: QMediaPlayer.PlaybackState.PausedState
            clock.now += 0.15
            desk._step_volume_ramp()
        self.assertEqual(desk._mix.fade_in, held)
        self.assertFalse(desk._ramp_timer.running)

    def test_a_crossfade_owns_the_level(self):
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=1.0)
            desk._mix.fade_in = 0.4
            desk._between.xfade.state = "fading"
            clock.now += 0.15
            desk._step_volume_ramp()
        self.assertEqual(desk._mix.fade_in, 0.4)

    def test_the_heard_time_is_carried_no_further_than_a_position_update(self):
        """A stalled player (buffering) must not have the level run ahead."""
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=1.0)
            desk._player.position = lambda: 1000
            desk._on_play_tick()
            for _ in range(40):          # one second, the position standing still
                clock.now += 0.025
                desk._step_volume_ramp()
        self.assertLessEqual(desk._mix.fade_in, (1.0 + 0.2) / FADE_IN + 1e-9)


class PlayStartTest(unittest.TestCase):
    """▶ with a fade-in armed sets the fine steps going at once."""

    def _win(self, fade_in_from):
        class Win:
            _on_playback_state = PlayerControlMixin._on_playback_state

            def __init__(self):
                self._fade_now = mock.Mock(total=0.0, remaining=lambda: 0.0)
                self._xfade_follow = self._refresh_wake_lock = lambda *a: None
                self._stop_background_analysis = lambda: None
                self._deckset = mock.Mock(all_tables=())
                self._playback = PlaybackState()
                self._playback.fade_in_from = fade_in_from
                self._level_owed = False
                self._refresh_loudness_gain = lambda: None
                self._fade_timer = mock.Mock(isActive=lambda: True)
                self._ramp_timer = _Timer()
                self._cued = False

            def _is_playing_mode(self):
                return False

        return Win()

    def test_a_fade_in_starts_the_steps(self):
        win = self._win(0.0)
        with mock.patch("player.window.main_player.log_song_action"):
            win._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertTrue(win._ramp_timer.running)

    def test_no_fade_in_no_steps(self):
        win = self._win(None)
        with mock.patch("player.window.main_player.log_song_action"):
            win._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertFalse(win._ramp_timer.running)


if __name__ == "__main__":
    unittest.main(verbosity=2)
