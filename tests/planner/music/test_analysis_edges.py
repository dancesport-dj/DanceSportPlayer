"""The corners of the audio analysis that real music never reaches.

A flat tempogram, a silent file, a length that cannot be read, a platform with
no malloc to trim: each one is built by hand, because none of them turns up
in a folder of real tracks until the day one does.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from planner.dances import BEATS_PER_BAR
from planner.music import analysis

SR = 11025
HOP = 512


def _lag_bpm(lag):
    return 60.0 * SR / (HOP * lag)


def _tempogram(peaks, lags=384, frames=20):
    """A tempogram whose mean lag profile is `peaks`: {lag: strength}."""
    tg = np.zeros((lags, frames), dtype=np.float32)
    for lag, value in peaks.items():
        tg[lag, :] = value
    return tg


class TempoPriorTests(unittest.TestCase):
    def test_an_unknown_dance_has_no_prior(self):
        self.assertIsNone(analysis.tempo_prior("zzz", 30))
        self.assertIsNone(analysis.tempo_prior(None, 30))

    def test_the_prior_is_the_takt_times_the_beats_per_bar(self):
        dance = next(iter(BEATS_PER_BAR))
        self.assertEqual(analysis.tempo_prior(dance, 30.0), 30.0 * BEATS_PER_BAR[dance])

    def test_a_file_without_a_takt_uses_the_dance_norm(self):
        dance = next(iter(BEATS_PER_BAR))
        with mock.patch.object(analysis, "default_takt", return_value=25.0):
            self.assertEqual(analysis.tempo_prior(dance, None),
                             25.0 * BEATS_PER_BAR[dance])
        with mock.patch.object(analysis, "default_takt", return_value=0):
            self.assertIsNone(analysis.tempo_prior(dance, None))


@unittest.skipUnless(analysis.HAS_LIBROSA, "needs librosa")
class TempoFromTempogramTests(unittest.TestCase):
    def tempo(self, tg, expected, **kw):
        return analysis._tempo_from_tempogram(tg, SR, expected, hop_length=HOP, **kw)

    def test_no_tempogram_or_no_prior_means_no_answer(self):
        self.assertIsNone(self.tempo(None, 120))
        self.assertIsNone(self.tempo(_tempogram({10: 1.0}), None))
        self.assertIsNone(self.tempo(_tempogram({10: 1.0}), 0))

    def test_a_band_with_no_lag_in_it_means_no_answer(self):
        self.assertIsNone(self.tempo(_tempogram({10: 1.0}), 20000))

    def test_the_strongest_lag_in_the_band_is_read_off(self):
        got = self.tempo(_tempogram({10: 1.0, 9: 0.0, 11: 0.0}), _lag_bpm(10))
        self.assertAlmostEqual(got, _lag_bpm(10), places=3)

    def test_a_strong_neighbour_pulls_the_peak_between_the_lags(self):
        """The sub-lag refinement: lag 10 with a strong lag 9 sits at ~9.8."""
        got = self.tempo(_tempogram({10: 1.0, 9: 0.6, 11: 0.0}), _lag_bpm(10))
        self.assertGreater(got, _lag_bpm(10))
        self.assertLess(got, _lag_bpm(9))

    def test_a_flat_profile_falls_back_to_the_whole_lag(self):
        """Three equal neighbours leave the parabola with nothing to fit; lag 9
        is outside the band, so the first lag inside it (10) is the answer."""
        got = self.tempo(_tempogram({9: 1.0, 10: 1.0, 11: 1.0}), _lag_bpm(10))
        self.assertAlmostEqual(got, _lag_bpm(10), places=3)

    def test_the_last_lag_has_no_neighbour_to_refine_with(self):
        last = 383
        got = self.tempo(_tempogram({last: 1.0}), _lag_bpm(last), band=0.2)
        self.assertAlmostEqual(got, _lag_bpm(last), places=3)


class StderrTests(unittest.TestCase):
    def test_no_stderr_to_redirect_means_nothing_to_restore(self):
        with mock.patch.object(analysis.os, "dup", side_effect=OSError("no fd 2")):
            self.assertIsNone(analysis._mute_stderr())

    def test_the_win32_handle_is_left_alone_elsewhere(self):
        with mock.patch.object(analysis.sys, "platform", "linux"), \
                mock.patch.dict(sys.modules, {"msvcrt": None}):
            self.assertIsNone(analysis._sync_win32_stderr())

    @unittest.skipUnless(sys.platform == "win32", "Win32 handles")
    def test_a_handle_that_cannot_be_set_is_only_logged(self):
        import msvcrt
        with mock.patch.object(msvcrt, "get_osfhandle", side_effect=OSError("bad fd")):
            self.assertIsNone(analysis._sync_win32_stderr())


class ReleaseFreeHeapTests(unittest.TestCase):
    def release(self, platform, **cdll):
        with mock.patch.object(analysis.sys, "platform", platform), \
                mock.patch("ctypes.CDLL", **cdll) as lib:
            analysis.release_free_heap()
        return lib

    def test_macos_asks_the_malloc_zone_to_give_pages_back(self):
        lib = self.release("darwin")
        lib.assert_called_once_with(None)
        lib.return_value.malloc_zone_pressure_relief.assert_called_once_with(None, 0)

    def test_linux_trims_the_glibc_heap(self):
        lib = self.release("linux")
        lib.assert_called_once_with("libc.so.6")
        lib.return_value.malloc_trim.assert_called_once_with(0)

    def test_windows_has_nothing_to_release(self):
        self.assertFalse(self.release("win32").called)

    def test_a_missing_libc_costs_nothing(self):
        self.release("linux", side_effect=OSError("no libc"))


@unittest.skipUnless(analysis.HAS_LIBROSA, "needs librosa")
class FeatureEdgeTests(unittest.TestCase):
    def test_too_few_frames_leave_the_timbre_model_out(self):
        y = np.zeros(2000, dtype=np.float32)
        self.assertEqual(analysis._gaussian_timbre(y, SR), (None, None))

    def test_enough_audio_gives_a_mean_and_a_flattened_covariance(self):
        rng = np.random.default_rng(1)
        y = rng.standard_normal(SR * 3).astype(np.float32) * 0.1
        mean, cov = analysis._gaussian_timbre(y, SR)
        self.assertEqual(mean.shape, (analysis.GAUSS_MFCC,))
        self.assertEqual(cov.shape, (analysis.GAUSS_MFCC ** 2,))

    def test_a_silent_file_with_an_unreadable_length_still_gets_features(self):
        silence = np.zeros(SR * 3, dtype=np.float32)
        with mock.patch.object(analysis.librosa, "get_duration",
                               side_effect=RuntimeError("no header")), \
                mock.patch.object(analysis, "load_audio",
                                  return_value=(silence, SR)) as load:
            got = analysis.analyze_file(Path("silence.wav"))
        self.assertTrue(load.call_args.kwargs["centered"])     # length unknown
        self.assertEqual(load.call_args.args[2], 0.0)          # read from the start
        self.assertIsInstance(got, analysis.AudioFeatures)


if __name__ == "__main__":
    unittest.main()
