"""🔊 The card's dB readout says the gain the hall hears, not the one asked for.

Run:  py -m unittest tests.player.audio.test_heard_gain -v

The deck's level is base × gain × …, clamped at 1.0 (the most a QAudioOutput
takes). With the music fader at 80 % a +6 dB boost (×2.0) runs into that
ceiling at ×1.25: the hall hears +1.9 dB, while the card said +6.0 dB.
"""
import math
import unittest
from pathlib import Path

from player.audio.mix import OutputMix
from player.window.main_audio import AudioLevelMixin


def _db(factor: float) -> float:
    return round(20 * math.log10(factor), 1)


class HeardGainTest(unittest.TestCase):

    def mix(self, base: float, gain: float) -> OutputMix:
        mix = OutputMix(base=base)
        mix.load_gain(gain)
        return mix

    def test_a_boost_stops_where_the_fader_meets_full_scale(self):
        self.assertEqual(_db(self.mix(0.8, 2.0).heard_gain()), 1.9)

    def test_a_boost_with_room_under_the_fader_is_heard_whole(self):
        self.assertEqual(_db(self.mix(0.5, 2.0).heard_gain()), 6.0)

    def test_a_cut_is_never_clamped(self):
        self.assertEqual(self.mix(1.0, 0.5).heard_gain(), 0.5)

    def test_a_silent_fader_shows_the_gain_asked_for(self):
        """Nothing is heard at all; the track's own figure is the useful one."""
        self.assertEqual(self.mix(0.0, 2.0).heard_gain(), 2.0)


class _Card:
    def __init__(self):
        self.gains = []

    def set_volume_value(self, _v):
        pass

    def set_gain(self, factor):
        self.gains.append(round(factor, 3))


class _Desk(AudioLevelMixin):

    def __init__(self):
        self._mix = OutputMix(base=0.5)
        self._mix.load_gain(2.0)
        self._big_player = _Card()
        self._playback = type("P", (), {"path": Path("x.mp3")})()
        self._vol_save_timer = type("T", (), {"start": lambda _s: None})()

    def _apply_volume(self):
        pass


class FaderMovesTheReadoutTest(unittest.TestCase):

    def test_raising_the_music_fader_updates_the_db(self):
        desk = _Desk()
        desk._set_base_volume(0.8)
        self.assertEqual(desk._big_player.gains, [1.25])

    def test_a_cut_track_keeps_its_readout_steady(self):
        desk = _Desk()
        desk._mix.load_gain(0.5)
        desk._set_base_volume(0.8)
        self.assertEqual(desk._big_player.gains, [0.5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
