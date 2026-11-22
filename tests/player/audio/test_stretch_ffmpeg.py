#!/usr/bin/env python3
"""⏩ Rubber Band through an ffmpeg pipe (player.audio.stretch_ffmpeg).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_stretch_ffmpeg -v

Runs the real ffmpeg; skipped where the ffmpeg in use has no rubberband
filter. Output comes back asynchronously, so the checks look at a whole
stream after flush(), not at single pieces.
"""
import time
import unittest
from unittest import mock

import numpy as np

from player.audio import stretch_ffmpeg as sf
from shared.audio import audio_probes

_RATE = 48000
_PIECE = 1250
_READY_S = 5.0


def _sine(seconds: float, freq: float = 440.0) -> np.ndarray:
    t = np.arange(int(_RATE * seconds)) / _RATE
    mono = (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.column_stack([mono, mono])


def _run(stretch, frames: np.ndarray) -> np.ndarray:
    out = [stretch.process(frames[i:i + _PIECE]) for i in range(0, len(frames), _PIECE)]
    return np.vstack(out + [stretch.flush()])


def _peak_hz(mono: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    return float(np.fft.rfftfreq(len(mono), 1 / _RATE)[np.argmax(spectrum)])


class _Standin:
    """Counts the titles the stand-in took; stretches like numpy's."""

    def __init__(self):
        self.made = 0

    def __call__(self):
        from player.audio.stretch import TimeStretch
        self.made += 1
        return TimeStretch(_RATE)


@unittest.skipUnless(sf.available(), "no ffmpeg with the rubberband filter")
class FfmpegStretchTest(unittest.TestCase):

    def setUp(self):
        self.standin = _Standin()
        self.stretch = sf.FfmpegStretch(_RATE, standin=self.standin)

    def tearDown(self):
        self.stretch.close()

    def _ready_at(self, rate: float):
        self.stretch.set_rate(rate)
        self.assertTrue(self.stretch.ready(_READY_S))

    # ===== Acceptance criteria =====

    def test_a_title_comes_out_at_its_tempo_with_its_pitch(self):
        """Rubber Band spreads a pure tone a little (445 Hz measured at 1.10
        offline too), hence the band around 440."""
        self._ready_at(1.05)
        title = _sine(4.0)
        out = _run(self.stretch, title)
        self.assertAlmostEqual(len(out), len(title) / 1.05, delta=_RATE * 0.005)
        self.assertAlmostEqual(_peak_hz(out[_RATE // 2:-_RATE // 2, 0]), 440, delta=6)
        self.assertEqual(self.standin.made, 0)

    def test_nothing_is_put_in_front_of_the_title(self):
        title = np.zeros((3 * _RATE, 2), dtype=np.float32)
        title[_RATE:_RATE + 200] = 0.9
        self._ready_at(1.05)
        out = _run(self.stretch, title)
        onset = int(np.argmax(np.abs(out[:, 0]) > 0.5))
        self.assertAlmostEqual(onset, _RATE / 1.05, delta=_RATE * 0.01)

    # ===== Core behavior =====

    def test_a_tempo_change_between_titles_starts_a_spare_at_it(self):
        self._ready_at(1.0)
        self.stretch.set_rate(0.95)
        self.assertTrue(self.stretch.ready(_READY_S))
        self.assertEqual(self.stretch._spare.rate, 0.95)

    def test_a_title_ffmpeg_is_not_ready_for_goes_through_the_standin(self):
        self._ready_at(1.0)
        self.stretch.set_rate(1.05)   # the spare at 1.05 is not there yet
        title = _sine(2.0)
        out = _run(self.stretch, title)
        self.assertEqual(self.standin.made, 1)
        self.assertAlmostEqual(len(out), len(title) / 1.05, delta=_RATE * 0.01)
        self.assertFalse(self.stretch.failed)

    def test_a_tempo_change_mid_title_reaches_the_running_process(self):
        self._ready_at(1.0)
        title = _sine(4.0)
        half = len(title) // 2
        out = [self.stretch.process(title[i:min(i + _PIECE, half)])
               for i in range(0, half, _PIECE)]
        # The change goes out once ffmpeg has answered: wait for that here.
        deadline = time.monotonic() + _READY_S
        while not self.stretch._proc.output_started and time.monotonic() < deadline:
            time.sleep(0.01)
        self.stretch.set_rate(1.25)
        out.append(self.stretch.process(title[half:half + _PIECE]))
        # ffmpeg reads the command within a -stats_period (50 ms); played in
        # real time, the rest of the title comes in after that.
        time.sleep(0.2)
        out += [self.stretch.process(title[i:i + _PIECE])
                for i in range(half + _PIECE, len(title), _PIECE)]
        out.append(self.stretch.flush())
        total = sum(len(o) for o in out)
        # Where the change lands depends on how far ffmpeg has got; it lands.
        self.assertLess(total, half + (len(title) - half) / 1.1)
        self.assertGreater(total, half / 1.25 + (len(title) - half) / 1.25)
        self.assertEqual(self.standin.made, 0)

    def test_the_next_title_gets_a_fresh_process(self):
        self._ready_at(1.0)
        _run(self.stretch, _sine(1.0))
        self.assertTrue(self.stretch.ready(_READY_S))
        out = _run(self.stretch, _sine(1.0))
        self.assertAlmostEqual(len(out), _RATE, delta=_RATE * 0.005)
        self.assertEqual(self.standin.made, 0)

    def test_a_dead_ffmpeg_hands_the_title_to_the_standin(self):
        """Unstretched, the title would pile up `rate` × real time on the card."""
        self._ready_at(1.05)
        self.stretch.process(_sine(0.1))
        self.stretch._proc.proc.kill()
        self.stretch._proc.proc.wait(5)
        piece = _sine(0.5)
        with self.assertLogs("dancesport.gui.audio", "WARNING"):
            out = np.vstack([self.stretch.process(piece) for _ in range(3)] + [self.stretch.flush()])
        self.assertTrue(self.stretch.failed)
        self.assertEqual(self.standin.made, 1)
        self.assertLess(len(out), 3 * len(piece))

    # ===== Coverage and null checks =====

    def test_reset_drops_the_stream(self):
        self._ready_at(1.0)
        self.stretch.process(_sine(0.1))
        self.assertTrue(self.stretch.holding)
        self.stretch.reset()
        self.assertFalse(self.stretch.holding)

    def test_a_tempo_of_zero_counts_as_1(self):
        self.stretch.set_rate(0)
        self.assertEqual(self.stretch.rate, 1.0)


class AvailabilityTest(unittest.TestCase):

    # ===== Coverage and null checks =====

    def test_no_ffmpeg_means_not_available(self):
        with mock.patch.object(sf, "_ffmpeg", return_value=None), \
                mock.patch.object(audio_probes, "find_ffmpeg", return_value=None), \
                mock.patch.dict(audio_probes._filters, {}, clear=True):
            self.assertFalse(sf.available())
            with self.assertRaises(RuntimeError):
                sf.FfmpegStretch(_RATE)


if __name__ == "__main__":
    unittest.main()
