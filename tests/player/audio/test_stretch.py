#!/usr/bin/env python3
"""⏩ The pitch-kept tempo change (player.audio.stretch).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_stretch -v

Pure numpy, no Qt. The pieces are the size Qt really hands over (~26 ms).
"""
import unittest

import numpy as np

from player.audio.stretch import TimeStretch

_RATE = 48000
_PIECE = 1250


def _sine(freq: float, seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(_RATE * seconds)) / _RATE
    mono = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.column_stack([mono, mono])


def _noise(seconds: float, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (0.3 * rng.standard_normal((int(_RATE * seconds), 2))).astype(np.float32)


def _run(stretch: TimeStretch, frames: np.ndarray, piece: int = _PIECE) -> np.ndarray:
    return np.vstack([stretch.process(frames[i:i + piece])
                      for i in range(0, len(frames), piece)])


def _peak_hz(mono: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    return float(np.fft.rfftfreq(len(mono), 1 / _RATE)[np.argmax(spectrum)])


class TimeStretchTest(unittest.TestCase):

    def setUp(self):
        self.stretch = TimeStretch(_RATE)
        # What it holds back at most: a window, the search either side, a hop.
        self.slack = self.stretch._size + 2 * self.stretch._search + self.stretch._hop

    # ===== Acceptance criteria =====

    def test_the_pitch_stays_where_it_was(self):
        for rate in (0.95, 1.05):
            self.stretch.reset()
            self.stretch.set_rate(rate)
            out = _run(self.stretch, _sine(440, 2.0))
            self.assertAlmostEqual(_peak_hz(out[_RATE // 4:, 0]), 440, delta=3, msg=rate)

    def test_a_whole_title_comes_out_at_its_tempo_without_drift(self):
        """90 s in ~26 ms pieces: out = in ÷ rate, to within what it holds back."""
        title = _noise(90.0)
        for rate in (0.96, 1.04):
            self.stretch.reset()
            self.stretch.set_rate(rate)
            out = _run(self.stretch, title)
            self.assertLess(abs(len(out) - len(title) / rate), self.slack, rate)

    def test_tempo_1_leaves_the_sound_as_it_is(self):
        title = _noise(2.0)
        out = _run(self.stretch, title)
        self.assertGreater(len(out), len(title) - self.slack)
        np.testing.assert_allclose(out, title[:len(out)], atol=1e-6)

    # ===== Core behavior =====

    def test_the_size_of_the_pieces_changes_nothing(self):
        """No seam where one piece ends: any cut gives the same sound."""
        title = _noise(3.0)
        other = TimeStretch(_RATE)
        for s in (self.stretch, other):
            s.set_rate(1.04)
        a, b = _run(self.stretch, title, 1250), _run(other, title, 4458)
        n = min(len(a), len(b))
        np.testing.assert_allclose(a[:n], b[:n], atol=1e-6)

    def test_a_steady_tone_keeps_its_level(self):
        """The overlapped windows neither dip nor bulge between segments."""
        self.stretch.set_rate(1.04)
        out = _run(self.stretch, _sine(200, 2.0))[_RATE // 4:, 0]
        frame = _RATE // 50
        rms = [float(np.sqrt(np.mean(out[i:i + frame] ** 2)))
               for i in range(0, len(out) - frame, frame)]
        self.assertLess(max(rms) - min(rms), 0.05 * np.mean(rms))

    def test_a_tempo_change_mid_title_has_no_jump(self):
        tone = _sine(80, 2.0)
        out = [_run(self.stretch, tone[:_RATE])]
        self.stretch.set_rate(1.05)
        out.append(_run(self.stretch, tone[_RATE:]))
        joined = np.vstack(out)[:, 0]
        # An 80 Hz sine at 0.5 moves at most ~0.005 per frame: a step would be far more.
        self.assertLess(float(np.max(np.abs(np.diff(joined)))), 0.01)

    def test_the_end_of_a_title_lets_out_the_lookahead_without_a_jump(self):
        tone = _sine(80, 1.0)
        self.stretch.set_rate(1.04)
        out = np.vstack([_run(self.stretch, tone), self.stretch.flush()])
        np.testing.assert_allclose(out[-1], tone[-1], atol=1e-6)
        self.assertLess(float(np.max(np.abs(np.diff(out[:, 0])))), 0.01)
        self.assertFalse(self.stretch.holding)

    def test_reset_forgets_what_came_before(self):
        fresh = TimeStretch(_RATE)
        for s in (self.stretch, fresh):
            s.set_rate(0.97)
        _run(self.stretch, _noise(1.0, seed=2))
        self.stretch.reset()
        title = _noise(1.0, seed=3)
        np.testing.assert_allclose(_run(self.stretch, title), _run(fresh, title), atol=1e-6)

    # ===== Coverage and null checks =====

    def test_the_first_frames_are_held_for_the_lookahead(self):
        self.stretch.set_rate(1.04)
        self.assertEqual(self.stretch.process(_noise(0.01)).shape, (0, 2))

    def test_an_empty_piece_gives_nothing(self):
        self.assertEqual(self.stretch.process(np.zeros((0, 2), np.float32)).shape, (0, 2))

    def test_a_tempo_of_zero_counts_as_1(self):
        self.stretch.set_rate(0)
        self.assertEqual(self.stretch.rate, 1.0)


if __name__ == "__main__":
    unittest.main()
