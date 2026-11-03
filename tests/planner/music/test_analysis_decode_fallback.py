"""A title libsndfile cannot open (.m4a, .wma, ...) is still analysed, by ffmpeg.

librosa 1.0 reads through soundfile only; its audioread fallback is gone. So an
.m4a failed the analysis with "Format not recognised" and the title never got a
vector. `load_audio` falls back to the ffmpeg decode the app already ships.
"""
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from planner.music import analysis

SR = 11025


def _ramp(seconds):
    """One sample value per sample, so a slice shows where it was cut."""
    return np.arange(int(seconds * SR), dtype=np.float32)


class DecodeFallbackTests(unittest.TestCase):
    def _load(self, ffmpeg_samples, **kw):
        path = Path("x.m4a")
        with mock.patch.object(analysis.librosa, "load",
                               side_effect=RuntimeError("Format not recognised")), \
             mock.patch.object(analysis, "fallback_decoder",
                               return_value=ffmpeg_samples):
            return analysis.load_audio(path, SR, offset=10.0, duration=5.0, **kw)

    def test_falls_back_to_ffmpeg_and_cuts_the_window(self):
        y, sr = self._load(_ramp(100))
        self.assertEqual(sr, SR)
        self.assertEqual(len(y), 5 * SR)
        self.assertEqual(y[0], 10 * SR)

    def test_centered_takes_the_middle_when_the_length_is_unknown(self):
        y, _sr = self._load(_ramp(100), centered=True)
        self.assertEqual(len(y), 5 * SR)
        self.assertEqual(y[0], (100 * SR - 5 * SR) // 2)

    def test_the_original_error_stands_when_ffmpeg_gets_nothing(self):
        with self.assertRaisesRegex(RuntimeError, "Format not recognised"):
            self._load(np.empty(0, dtype=np.float32))

    def test_a_readable_file_never_touches_ffmpeg(self):
        with mock.patch.object(analysis.librosa, "load",
                               return_value=(np.zeros(3), SR)), \
             mock.patch.object(analysis, "fallback_decoder") as dec:
            analysis.load_audio(Path("x.mp3"), SR, offset=0.0, duration=2.0)
        dec.assert_not_called()


class RegistrationTest(unittest.TestCase):
    def test_the_gui_registers_the_ffmpeg_decode(self):
        from gui import workers
        self.assertIs(analysis.fallback_decoder, workers.decode_pcm_mono)


if __name__ == "__main__":
    unittest.main()
