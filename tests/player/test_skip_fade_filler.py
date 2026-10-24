#!/usr/bin/env python3
"""⏭ during an announcement: the filler fades, it does not swell first.

Run:  py -m unittest tests.player.test_skip_fade_filler -v

⏭ in a pause stops the announcer and starts the skip-fade of the filler.
Stopping the announcer lets the "announce" duck ramp back up over 600 ms,
and every 25 ms step of that ramp wrote the filler's full level, while the
200 ms fade tick wrote the fade's level in between: the PA heard a pump for
the better part of a second. While the skip-fade runs, it alone sets the
filler's level.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_skipfade_"))

from player.audio.between_dances import BetweenDances
from player.audio.mix import OutputMix
from player.window.main_audio import AudioLevelMixin
from player.window.main_pause import PauseMusicMixin


class _Win:
    _step_volume_ramp = AudioLevelMixin._step_volume_ramp
    _update_pause_music_volume = PauseMusicMixin._update_pause_music_volume

    def __init__(self):
        self._mix = OutputMix()
        self._big_player = None
        self._ramp_timer = mock.Mock()
        self._apply_volume = lambda: None
        self._filler = mock.Mock(active=True)
        self._between = BetweenDances()
        self._pause_out = mock.Mock()
        self._play_panel = mock.Mock(pause_music_vol=lambda: 100)


class SkipFadeOwnsTheFillerTest(unittest.TestCase):

    def test_the_duck_ramp_leaves_a_skip_fade_alone(self):
        w = _Win()
        w._mix.duck_reason("announce", True)
        w._mix.duck = w._mix.duck_target
        w._between.fade_end = time.monotonic() + 3.0   # ⏭ started the fade
        w._mix.duck_reason("announce", False)          # …and stopped the call
        w._step_volume_ramp()
        w._pause_out.setVolume.assert_not_called()

    def test_without_a_skip_fade_the_duck_still_reaches_the_filler(self):
        w = _Win()
        w._mix.duck_reason("announce", True)
        w._step_volume_ramp()
        w._pause_out.setVolume.assert_called_once()


if __name__ == "__main__":
    unittest.main()
