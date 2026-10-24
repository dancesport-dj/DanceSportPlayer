#!/usr/bin/env python3
"""🔉↓ / 🛑 The hand-started fade's own rules, without a window.

Run:  py -m unittest tests.player.audio.test_fade_now -v

The window drives FadeNow from the play tick; these tests pin the ramp
arithmetic it relies on: the minimum length, the 1 → 0 level and the hold
flag the 🛑 fade sets.
"""

import unittest
from unittest import mock

from player.audio.fade_now import FadeNow


class FadeNowTest(unittest.TestCase):

    def test_a_new_fade_is_not_running(self):
        fade = FadeNow()
        self.assertFalse(fade.running)
        self.assertFalse(fade.hold)

    def test_start_runs_the_ramp_from_now(self):
        fade = FadeNow()
        with mock.patch("player.audio.fade_now.time.monotonic", return_value=100.0):
            fade.start(4)
            self.assertTrue(fade.running)
            self.assertEqual(fade.total, 4.0)
            self.assertEqual(fade.end, 104.0)
            self.assertEqual(fade.remaining(), 4.0)

    def test_a_fade_shorter_than_half_a_second_is_stretched(self):
        fade = FadeNow()
        fade.start(0)
        self.assertEqual(fade.total, FadeNow.MIN_SECS)

    def test_the_level_falls_from_one_to_zero(self):
        fade = FadeNow()
        fade.start(4)
        self.assertEqual(fade.level(4.0), 1.0)
        self.assertEqual(fade.level(1.0), 0.25)
        self.assertEqual(fade.level(-0.3), 0.0)

    def test_without_a_length_the_level_is_silence(self):
        self.assertEqual(FadeNow().level(1.0), 0.0)

    def test_the_panic_fade_holds_and_a_plain_one_does_not(self):
        fade = FadeNow()
        fade.start(2, hold=True)
        self.assertTrue(fade.hold)
        fade.start(2)
        self.assertFalse(fade.hold)

    def test_cancel_stops_the_ramp(self):
        fade = FadeNow()
        fade.start(2)
        fade.cancel()
        self.assertFalse(fade.running)


class PausedFadeTest(unittest.TestCase):
    """A 3 s 🔉↓ fade paused after 1 s: its clock ran on through the pause,
    and the first tick after ⏯ found it at the bottom and cut the title."""

    def _at(self, t):
        return mock.patch("player.audio.fade_now.time.monotonic", return_value=t)

    def test_a_pause_stops_the_clock(self):
        fade = FadeNow()
        with self._at(100.0):
            fade.start(3)
        with self._at(101.0):
            fade.freeze()
        with self._at(160.0):
            self.assertEqual(fade.remaining(), 2.0)
            fade.thaw()
        with self._at(161.0):
            self.assertEqual(fade.remaining(), 1.0)

    def test_without_a_fade_a_pause_changes_nothing(self):
        fade = FadeNow()
        fade.freeze()
        fade.thaw()
        self.assertFalse(fade.running)

    def test_a_second_pause_keeps_the_first_reading(self):
        fade = FadeNow()
        with self._at(100.0):
            fade.start(3)
        with self._at(101.0):
            fade.freeze()
        with self._at(102.0):
            fade.freeze()
            self.assertEqual(fade.remaining(), 2.0)

    def test_a_new_fade_or_a_cancel_drops_the_frozen_one(self):
        fade = FadeNow()
        with self._at(100.0):
            fade.start(3)
            fade.freeze()
            fade.start(5)
            self.assertEqual(fade.remaining(), 5.0)
            fade.freeze()
            fade.cancel()
            fade.thaw()
        self.assertFalse(fade.running)


class WindowPausesTheFadeTest(unittest.TestCase):
    """The window stops and restarts that clock with the player."""

    def _win(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.window.main_player import PlayerControlMixin

        class Win:
            _on_playback_state = PlayerControlMixin._on_playback_state

            def __init__(self):
                self._fade_now = mock.Mock()
                self._xfade_follow = self._refresh_wake_lock = lambda *a: None
                self._deckset = mock.Mock(all_tables=())
                self._playback = mock.Mock(path=None, dance="")
                self._level_owed = False
                self._refresh_loudness_gain = lambda: None
                self._fade_timer = mock.Mock(isActive=lambda: True)
        return Win(), QMediaPlayer.PlaybackState

    def test_pause_freezes_and_play_thaws(self):
        win, state = self._win()
        win._on_playback_state(state.PausedState)
        win._fade_now.freeze.assert_called_once_with()
        win._fade_now.thaw.assert_not_called()
        win._on_playback_state(state.PlayingState)
        win._fade_now.thaw.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
