#!/usr/bin/env python3
"""Tests for 🔊 where loudness equalization lands the evening.

Run:  py -m unittest tests.player.test_loudness_target -v

Equalizing tracks against each other works at any target — the whole set moves
together, and the hall level is set at the amplifier afterwards. What the target
DOES decide is how far below full scale the music leaves the sound card, and a
card's noise floor does not come down with it: every dB of attenuation here is a
dB of hiss the amplifier makes up for on the way to the PA.

So the target is a trade, not a taste. Too low and a hissy onboard output puts
that hiss on the PA; too high and the boost side clips, blind, because only the
integrated loudness is stored and never a true peak.
"""
import unittest
from types import SimpleNamespace

from shared.playback import _TARGET_LUFS
from player.main_audio import AudioLevelMixin


def _db(gain: float) -> float:
    """A linear factor back in dB, which is how the trade is reasoned about."""
    import math
    return 20 * math.log10(gain)


class _Desk(AudioLevelMixin):
    """The audio half of the window, reduced to what the gain is worked out from."""

    def __init__(self, lufs, active: bool = True):
        self._loudness = active
        self._cache = SimpleNamespace(get_lufs=lambda _p: lufs)

    def _pv(self, key):
        # The playing list's own values — only the 📊 switch is asked here.
        return {"loudness": self._loudness}[key]


def _gain(lufs, **kw) -> float:
    return _Desk(lufs, **kw)._loudness_gain("x.mp3")


class LoudnessTargetTest(unittest.TestCase):

    def test_the_target_sits_near_the_music_not_far_under_it(self):
        """−18 threw away 8 dB of the card's range for headroom nothing used;
        −12 would boost a quarter of this library with no peak to clamp to."""
        self.assertGreaterEqual(_TARGET_LUFS, -16.0)
        self.assertLessEqual(_TARGET_LUFS, -12.0)

    def test_a_typical_dance_track_keeps_most_of_its_level(self):
        """The library's median is −9.9 LUFS: 4748 measured tracks, p75 −8.8.
        Cutting the middle of that by more than 6 dB is 6 dB of hiss."""
        self.assertGreater(_db(_gain(-9.9)), -6.0)

    def test_a_quiet_track_is_still_brought_up(self):
        self.assertGreater(_gain(-20.0), 1.0)

    def test_the_boost_cannot_run_away(self):
        """A broken measurement must never blast the hall."""
        self.assertAlmostEqual(_db(_gain(-40.0)), 9.0, places=6)

    def test_the_cut_cannot_mute_a_song(self):
        self.assertAlmostEqual(_db(_gain(0.0)), -12.0, places=6)

    def test_an_unmeasured_track_plays_as_it_is(self):
        self.assertEqual(_gain(None), 1.0)

    def test_switched_off_nothing_is_touched(self):
        self.assertEqual(_gain(-9.9, active=False), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
