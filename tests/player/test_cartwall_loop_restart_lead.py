"""🔁 A loop's next round skips the dead air in the fade and hard modes too.

Review 2026-11-12, F4 (first nit): the crossover starts the next round at
the first audible point (`_audible`), but the "fade" and "hard" loop modes
restarted at 0 and so replayed the silence at the top of the file every
round. Every restart now starts where a crossover would, and a pad that
skips its lead-in (🔇) starts past that one as well.

Runs on the stub players of test_cartwall_voices (files of 10 s).
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_looplead_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.audio import cart_voices
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)
PATH = "C:\\samples\\bed.mp3"
LONG_LEAD = [[0.0, 3.0]]     # 3 s of dead air at the top
MUSIC_AT = 3000 - cart_voices._SILENCE_LEAD_MS


def _last_position(voice):
    return [c[1] for c in voice.player.calls if c[0] == "setPosition"][-1]


class LoopRestartLeadTest(unittest.TestCase):

    def _voices(self, mode):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        v.set_loop_mode(mode)
        return v

    def _end_of_file(self, v, voice):
        cart_voices.CartVoices._on_status(v, voice, QMediaPlayer.MediaStatus.EndOfMedia)

    def test_the_hard_mode_restarts_at_the_music(self):
        v = self._voices("hard")
        v.set_silences(PATH, LONG_LEAD)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        voice = v._voice_for(KEY)
        self._end_of_file(v, voice)
        self.assertIs(v._voice_for(KEY), voice, "the same voice goes round again")
        self.assertEqual(_last_position(voice), MUSIC_AT)

    def test_the_fade_mode_restarts_at_the_music(self):
        v = self._voices("fade")
        v.set_silences(PATH, LONG_LEAD)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        voice = v._voice_for(KEY)
        voice.player.setPosition(9000)
        v._emit_tick()
        self.assertGreater(voice.dip_step, 0, "dipping towards the restart")
        for _ in range(400):
            if voice.dip_step <= 0:
                break
            v._step_fades()
        self.assertEqual(_last_position(voice), MUSIC_AT)

    def test_without_dead_air_it_still_restarts_at_the_top(self):
        v = self._voices("hard")
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        voice = v._voice_for(KEY)
        self._end_of_file(v, voice)
        self.assertEqual(_last_position(voice), 0)

    def test_a_pad_that_skips_its_lead_in_restarts_past_it(self):
        v = self._voices("hard")
        v.set_edges(PATH, [[0.0, 0.4]])
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, skip_silence=True))
        voice = v._voice_for(KEY)
        self._end_of_file(v, voice)
        self.assertEqual(_last_position(voice), 400 - cart_voices._LEAD_PREROLL_MS)

    def test_the_crossover_round_starts_past_a_skipped_lead_in_too(self):
        v = self._voices("crossover")
        v.set_wall_cross(2000)
        v.set_edges(PATH, [[0.0, 0.4]])
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, skip_silence=True))
        first = v._voice_for(KEY)
        first.player.setPosition(8100)
        v._emit_tick()
        nxt = v._voice_for(KEY)
        self.assertIsNot(nxt, first, "the crossover started")
        self.assertEqual(_last_position(nxt), 400 - cart_voices._LEAD_PREROLL_MS)


if __name__ == "__main__":
    unittest.main()
