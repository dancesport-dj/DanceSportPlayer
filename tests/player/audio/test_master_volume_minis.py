"""🔊 The main slider is the master for the mini players too.

Run:  py -m unittest tests.player.audio.test_master_volume_minis -v

The library's pre-listen mini player has an output of its own; it follows the
music fader (and the 🔉 desk duck) like the deck. The cartwall keeps its fader.
"""
import unittest

from player.audio.mix import OutputMix
from player.window.main_audio import AudioLevelMixin


class _Out:
    def __init__(self):
        self.vol = 1.0

    def setVolume(self, v):
        self.vol = v


class _Cue:
    def __init__(self):
        self.audio_output = _Out()


class _Desk(AudioLevelMixin):
    def __init__(self):
        self._mix = OutputMix(base=0.8)
        self._player = None
        self._audio_out = None
        self._cart_voices = None
        self._cue = _Cue()

    def _cue_player(self):
        return self._cue


class MiniFollowsMasterTest(unittest.TestCase):

    def test_the_cue_output_follows_the_main_slider(self):
        desk = _Desk()
        desk._apply_volume()
        self.assertAlmostEqual(desk._cue.audio_output.vol, 0.8)
        desk._mix.set_base(0.3)
        desk._apply_volume()
        self.assertAlmostEqual(desk._cue.audio_output.vol, 0.3)

    def test_the_desk_duck_lowers_it_too(self):
        desk = _Desk()
        desk._mix.set_desk_duck(True, 0.5)
        desk._apply_volume()
        self.assertAlmostEqual(desk._cue.audio_output.vol, 0.4)

    def test_no_cue_player_is_fine(self):
        desk = _Desk()
        desk._cue = None
        desk._apply_volume()

    def test_the_cartwall_fader_does_not_move_it(self):
        desk = _Desk()
        desk._mix.set_cart(0.1)
        desk._apply_volume()
        self.assertAlmostEqual(desk._cue.audio_output.vol, 0.8)


if __name__ == "__main__":
    unittest.main()
