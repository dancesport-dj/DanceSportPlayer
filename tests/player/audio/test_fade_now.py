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


if __name__ == "__main__":
    unittest.main()
