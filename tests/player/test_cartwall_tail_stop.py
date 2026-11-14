"""A loop's old round, still fading under the next one, obeys every stop.

Review 2026-11-12, F1: during a loop crossover the finished round (the
"tail") has no key, so stop(key), stop_all() and a ■ pad's _stop_others()
all passed it by. After a hard cut it kept sounding for the rest of the
crossover, up to 15 s. A stop now takes the pad's tail too: a hard cut
silences it at once, a fade makes it go no later than the fade asks.

Runs on the stub players of test_cartwall_voices.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tailstop_"))

from PySide6.QtWidgets import QApplication

from player.audio import cart_voices
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)
OTHER = (0, 0, 1)


class TailStopTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)
        self.v.set_wall_fade(1000)
        self.v.set_wall_cross(3000)

    def tearDown(self):
        self.v.shutdown()

    def _crossing(self, **kw):
        """A looping pad in the middle of its crossover: (tail, new round)."""
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, **kw))
        first = self.v._voice_for(KEY)
        first.player.setPosition(first.player.duration() - 2900)
        self.v._emit_tick()
        self.v._step_fades()
        self.assertTrue(first.tail, "the crossover has started")
        self.assertGreater(first.out.volume(), 0.0)
        return first, self.v._voice_for(KEY)

    def _steps(self, n):
        for _ in range(n):
            self.v._step_fades()

    def test_a_hard_stop_of_the_pad_silences_its_tail_at_once(self):
        tail, _round = self._crossing(fade_ms=0)
        self.v.stop(KEY)
        self.assertEqual(tail.out.volume(), 0.0)
        self.assertIsNone(tail.pad, "the tail's voice is free again")

    def test_a_hard_stop_all_silences_the_tail_at_once(self):
        tail, _round = self._crossing()
        self.v.set_wall_fade(0)
        self.v.stop_all()
        self.assertEqual(tail.out.volume(), 0.0)
        self.assertIsNone(tail.pad)

    def test_stop_all_with_a_short_fade_ends_the_tail_with_it(self):
        tail, _round = self._crossing()
        self.v.set_wall_fade(250)        # ten ramp steps; the crossover has ~115 left
        longest = self.v.stop_all()
        self.assertGreaterEqual(longest, 250)
        self._steps(11)
        self.assertIsNone(tail.pad, "the tail went with the stop, not with the crossover")

    def test_a_long_stop_fade_does_not_stretch_the_tail(self):
        tail, _round = self._crossing()
        self.v.set_wall_fade(10_000)
        self.v.stop_all()
        self._steps(120)                  # the crossover's own 3 s
        self.assertIsNone(tail.pad)

    def test_stopping_another_pad_leaves_this_tail_alone(self):
        tail, _round = self._crossing()
        self.v.fire(OTHER, _pad("tusch.mp3", fade_ms=0))
        self.v.stop(OTHER)
        self.assertIs(tail.pad.loop, True, "the crossover carries on")
        self.assertGreater(tail.out.volume(), 0.0)

    def test_a_stops_others_pad_takes_the_tail_too(self):
        tail, _round = self._crossing(fade_ms=0)
        self.v.fire(OTHER, _pad("tusch.mp3", stops_others=True))
        self.assertIsNone(tail.pad)
        self.assertEqual(tail.out.volume(), 0.0)

    def test_the_tail_follows_its_pad_when_the_wall_is_reshaped(self):
        tail, _round = self._crossing(fade_ms=0)
        moved = (1, 0, 0)
        self.v.rekey({KEY: moved})
        self.v.stop(moved)
        self.assertIsNone(tail.pad)


if __name__ == "__main__":
    unittest.main()
