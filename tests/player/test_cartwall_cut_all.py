"""⏹ cut_all: every pad voice silent at once, whatever it was doing.

Review 2026-11-12, suggestion 1: the status bar's red stop wants the wall
silent now. stop_all() is not that: a pad with a fade of its own still
fades, and a voice already on a ramp (a ⏹ all a moment ago, a steal, a
loop's tail) is passed by. cut_all() ends each of them on the spot, and a
pad waiting for a voice does not start any more.

Runs on the stub players of test_cartwall_voices.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cutall_"))

from PySide6.QtWidgets import QApplication

from player.audio import cart_voices
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

A, B, C = (0, 0, 0), (0, 0, 1), (0, 0, 2)


class CutAllTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=2, factory=_factory)
        self.v.set_level(1.0)
        self.v.set_wall_fade(2000)
        self.v.set_wall_cross(3000)
        self.stopped = []
        self.v.padStopped.connect(self.stopped.append)

    def tearDown(self):
        self.v.shutdown()

    def _silent(self):
        for voice in self.v._pool:
            self.assertIsNone(voice.pad)
            self.assertEqual(voice.out.volume(), 0.0)
            self.assertEqual(voice.fade_step, 0.0)
            self.assertEqual(voice.rise_step, 0.0)
            self.assertEqual(voice.dip_step, 0.0)
            self.assertFalse(voice.tail)
            self.assertIsNone(voice.then)

    def test_a_pad_with_its_own_fade_is_cut_not_faded(self):
        self.v.fire(A, _pad("tusch.mp3", fade_ms=5000))
        self.v.cut_all()
        self._silent()
        self.assertEqual(self.stopped, [A], "the wall's button goes idle")

    def test_a_voice_already_fading_is_cut_too(self):
        self.v.fire(A, _pad("tusch.mp3"))
        self.v.stop_all()                # a 2 s fade under way
        self.v._step_fades()
        self.v.cut_all()
        self._silent()

    def test_a_pad_waiting_for_a_stolen_voice_does_not_start(self):
        self.v.fire(A, _pad("one.mp3"))
        self.v.fire(B, _pad("two.mp3"))
        self.v.fire(C, _pad("three.mp3"))   # takes over the oldest: a steal ramp
        self.assertTrue(any(v.then is not None for v in self.v._pool))
        self.v.cut_all()
        self._silent()
        self.assertNotIn(C, self.v.playing_keys())

    def test_a_loop_and_its_crossover_tail_are_both_cut(self):
        self.v.fire(A, _pad("bed.mp3", loop=True, duck=False))
        first = self.v._voice_for(A)
        first.player.setPosition(first.player.duration() - 2900)
        self.v._emit_tick()
        self.v._step_fades()
        self.assertTrue(first.tail)
        self.v.cut_all()
        self._silent()

    def test_a_loop_dipping_before_its_restart_is_cut(self):
        self.v.set_loop_mode("fade")
        self.v.fire(A, _pad("bed.mp3", loop=True, duck=False))
        voice = self.v._voice_for(A)
        voice.player.setPosition(voice.player.duration() - 2900)
        self.v._emit_tick()
        self.assertGreater(voice.dip_step, 0.0)
        self.v.cut_all()
        self._silent()

    def test_a_bed_held_under_a_title_is_let_go(self):
        self.v.fire(A, _pad("bed.mp3", background=True, loop=True))
        voice = self.v._voice_for(A)
        self.v._set_held(voice, True)
        self.v.cut_all()
        self._silent()
        self.assertFalse(voice.held)

    def test_a_bed_still_rising_is_cut(self):
        self.v.set_background_fire_fade(3000)
        self.v.fire(A, _pad("bed.mp3", background=True, loop=True))
        self.assertGreater(self.v._voice_for(A).rise_step, 0.0)
        self.v.cut_all()
        self._silent()

    def test_nothing_playing_is_fine(self):
        self.v.cut_all()
        self._silent()
        self.assertEqual(self.stopped, [])


if __name__ == "__main__":
    unittest.main()
