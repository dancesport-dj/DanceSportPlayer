"""A cancelled analysis ends between the stages of the title in work, not after it.

The decode and each feature stage of one title take a fraction of a second; the
whole title several seconds. A show must not wait for the whole of it.
"""
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from planner.models import MusicEntry
from planner.music import analysis
from planner.music.analysis import AnalysisCancelled, analyze_file
from planner.music.db import AudioCache

_AUDIO = (np.ones(11025 * 5, dtype=np.float32), 11025)


def _run(cancel_after: int | None):
    """analyze_file with the librosa stages mocked; the cancel answers True from its
    `cancel_after`-th question on (None: never). Returns the stage mocks."""
    asked = []

    def should_cancel():
        asked.append(1)
        return cancel_after is not None and len(asked) >= cancel_after

    names = ("mfcc", "delta", "spectral_centroid", "rms", "spectral_contrast", "tempogram")
    stages = {n: mock.MagicMock(return_value=np.ones((20, 9), dtype=np.float32))
              for n in names}
    onset = mock.MagicMock(return_value=np.ones(9, dtype=np.float32))
    with mock.patch.object(analysis, "load_audio", return_value=_AUDIO), \
            mock.patch.object(analysis.librosa, "get_duration", return_value=5.0), \
            mock.patch.object(analysis.librosa.feature, "mfcc", stages["mfcc"]), \
            mock.patch.object(analysis.librosa.feature, "delta", stages["delta"]), \
            mock.patch.object(analysis.librosa.feature, "spectral_centroid",
                              stages["spectral_centroid"]), \
            mock.patch.object(analysis.librosa.feature, "rms", stages["rms"]), \
            mock.patch.object(analysis.librosa.feature, "spectral_contrast",
                              stages["spectral_contrast"]), \
            mock.patch.object(analysis.librosa.feature, "tempogram", stages["tempogram"]), \
            mock.patch.object(analysis.librosa.onset, "onset_strength", onset), \
            mock.patch.object(analysis, "_gaussian_timbre", return_value=(None, None)):
        try:
            analyze_file(Path("x.mp3"), None, should_cancel=should_cancel)
            error = None
        except AnalysisCancelled as exc:
            error = exc
        except Exception as exc:   # the mocks are no real spectrogram: only the order matters
            error = exc
    return stages, error


class CheckpointTest(unittest.TestCase):

    def test_a_cancel_before_the_decode_returns_stops_before_any_feature(self):
        stages, error = _run(cancel_after=1)
        self.assertIsInstance(error, AnalysisCancelled)
        self.assertFalse(stages["mfcc"].called)

    def test_a_cancel_after_the_timbre_stops_before_the_rhythm(self):
        stages, error = _run(cancel_after=3)
        self.assertIsInstance(error, AnalysisCancelled)
        self.assertTrue(stages["mfcc"].called)
        self.assertFalse(stages["tempogram"].called)

    def test_without_a_cancel_it_is_not_asked_for_one(self):
        _stages, error = _run(cancel_after=None)
        self.assertNotIsInstance(error, AnalysisCancelled)


class _Cache:
    BATCH_FILES = 50
    BIG_LIBRARY = 1000
    analyze_entries = AudioCache.analyze_entries
    _finish_batch = AudioCache._finish_batch

    def __init__(self):
        self.saved = 0
        self.store = {}

    def fingerprint(self, path):
        return path.name

    def _analyze_file(self, path, expected_bpm=None, should_cancel=None):
        if path.name.startswith("b"):
            raise AnalysisCancelled()
        return "feat-" + path.name

    def put(self, path, feat):
        self.store[path.name] = feat

    def get(self, path):
        return self.store.get(path.name)

    def save(self):
        self.saved += 1


class LoopTest(unittest.TestCase):

    def test_a_title_cancelled_halfway_ends_the_run_as_cancelled_not_as_an_error(self):
        entries = [MusicEntry(path=Path(f"X:/{n}.mp3"), title=n, dance="LW")
                   for n in ("a", "b", "c")]
        cache, errors = _Cache(), []
        ok, failed, cancelled = cache.analyze_entries(
            entries, should_cancel=lambda: False, on_error=lambda p, e: errors.append(p))
        self.assertEqual((ok, failed, cancelled), (1, 0, True))
        self.assertEqual(errors, [])
        self.assertEqual(sorted(cache.store), ["a.mp3"])
        self.assertGreaterEqual(cache.saved, 1)
        self.assertIsNone(entries[1].features)


if __name__ == "__main__":
    unittest.main()
