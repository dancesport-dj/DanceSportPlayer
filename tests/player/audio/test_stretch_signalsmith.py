#!/usr/bin/env python3
"""⏩ Signalsmith Stretch through sstretch.dll (player.audio.stretch_signalsmith).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_stretch_signalsmith -v

No Qt. The pieces are the size Qt really hands over (~26 ms). Skipped where
the library is not built (macOS / Linux before build_sstretch.sh).
"""
import unittest
from unittest import mock

import numpy as np

from player.audio import stretch_signalsmith as ss

_RATE = 48000
_PIECE = 1250


def _sine(freq: float, seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(_RATE * seconds)) / _RATE
    mono = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.column_stack([mono, mono])


def _run(stretch, frames: np.ndarray, piece: int = _PIECE) -> np.ndarray:
    return np.vstack([stretch.process(frames[i:i + piece])
                      for i in range(0, len(frames), piece)] + [stretch.flush()])


def _off_440(mono: np.ndarray) -> float:
    """Share of the energy away from 440 Hz."""
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1 / _RATE)
    return 1 - spectrum[(freqs > 430) & (freqs < 450)].sum() / spectrum.sum()


@unittest.skipUnless(ss.available(), "sstretch.dll not built")
class SignalsmithStretchTest(unittest.TestCase):

    def setUp(self):
        self.stretch = ss.SignalsmithStretch(_RATE)

    # ===== Acceptance criteria =====

    def test_the_pitch_stays_in_small_pieces(self):
        """What broke the python-stretch wrapper: in ~26 ms pieces its pitch
        fell to ~422 Hz. Streamed properly it stays at 440."""
        for rate in (0.95, 1.05):
            self.stretch.reset()
            self.stretch.set_rate(rate)
            out = _run(self.stretch, _sine(440, 4.0))
            self.assertLess(_off_440(out[_RATE // 2:-_RATE // 2, 0]), 0.01, msg=rate)

    def test_a_whole_title_comes_out_at_its_tempo_without_drift(self):
        title = _sine(440, 20.0)
        for rate in (0.96, 1.04):
            self.stretch.reset()
            self.stretch.set_rate(rate)
            out = _run(self.stretch, title)
            self.assertAlmostEqual(len(out), len(title) / rate, delta=2, msg=rate)

    def test_nothing_is_put_in_front_of_the_title(self):
        """A burst at 2 s is heard at 2 s ÷ tempo, not a latency later."""
        for rate in (1.0, 1.05):
            title = np.zeros((4 * _RATE, 2), dtype=np.float32)
            title[2 * _RATE:2 * _RATE + 200] = 0.8
            self.stretch.reset()
            self.stretch.set_rate(rate)
            out = _run(self.stretch, title)
            onset = int(np.argmax(np.abs(out[:, 0]) > 0.1))
            self.assertAlmostEqual(onset, 2 * _RATE / rate, delta=_RATE * 0.01, msg=rate)

    # ===== Core behavior =====

    def test_the_size_of_the_pieces_changes_nothing_audible(self):
        """Its blocks fall where the calls do, so the samples differ a little;
        the length and the pitch do not."""
        title = _sine(440, 3.0)
        self.stretch.set_rate(1.05)
        small = _run(self.stretch, title, 1250)
        self.stretch.reset()
        big = _run(self.stretch, title, 48000)
        self.assertEqual(len(small), len(big))
        for out in (small, big):
            self.assertLess(_off_440(out[_RATE // 2:-_RATE // 2, 0]), 0.01)

    def test_a_tempo_change_mid_title_carries_on(self):
        title = _sine(440, 6.0)
        half = len(title) // 2
        self.stretch.set_rate(1.0)
        first = np.vstack([self.stretch.process(title[i:min(i + _PIECE, half)])
                           for i in range(0, half, _PIECE)])
        self.stretch.set_rate(1.05)
        second = _run(self.stretch, title[half:])
        out = np.vstack([first, second])
        # The change lands where it is processing, the lookahead behind the feed.
        lag = self.stretch._in_latency * (1 - 1 / 1.05)
        self.assertAlmostEqual(len(out), half + (len(title) - half) / 1.05 - lag, delta=2)
        self.assertLess(_off_440(out[_RATE // 2:-_RATE // 2, 0]), 0.01)

    def test_reset_forgets_what_came_before(self):
        self.stretch.process(_sine(440, 1.0))
        self.stretch.reset()
        self.assertFalse(self.stretch.holding)
        out = _run(self.stretch, np.zeros((_RATE, 2), dtype=np.float32))
        self.assertLess(np.abs(out).max(), 1e-6)

    # ===== Coverage and null checks =====

    def test_the_first_frames_are_held_for_the_lookahead(self):
        out = self.stretch.process(_sine(440, 0.01))
        self.assertEqual(len(out), 0)
        self.assertTrue(self.stretch.holding)

    def test_a_title_shorter_than_the_lookahead_comes_out_as_it_is(self):
        short = _sine(440, 0.01)
        self.stretch.process(short)
        np.testing.assert_array_equal(self.stretch.flush(), short)
        self.assertFalse(self.stretch.holding)

    def test_an_empty_piece_gives_nothing(self):
        self.assertEqual(self.stretch.process(np.zeros((0, 2), np.float32)).shape, (0, 2))

    def test_a_tempo_of_zero_counts_as_1(self):
        self.stretch.set_rate(0)
        self.assertEqual(self.stretch.rate, 1.0)


class AvailabilityTest(unittest.TestCase):

    # ===== Coverage and null checks =====

    def test_a_missing_dll_is_not_available(self):
        with mock.patch.object(ss, "_dll", None), mock.patch.object(ss, "_tried", False), \
                mock.patch.object(ss.os.path, "isfile", return_value=False):
            self.assertFalse(ss.available())
            with self.assertRaises(RuntimeError):
                ss.SignalsmithStretch(_RATE)


if __name__ == "__main__":
    unittest.main()
