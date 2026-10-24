#!/usr/bin/env python3
"""↺ Replace: a title never analysed is no 50 % match.

Run:  py -m unittest tests.planner.test_replace_unanalysed -v

The ↺ branch of `_pick` means to rank a title without audio features below
every measured one, and to report no similarity for it. But the timbre metric
hands such a title its neutral 0.5, so right after an import a never-measured
title outranked a real but weaker sound-alike and showed as a 50 % match.
"""

import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from planner.generate.suggester import PlaylistSuggester
from planner.models import MusicEntry
from planner.music.analysis import AudioFeatures

TRIALS = 50


def _features(offset: float) -> AudioFeatures:
    mean = np.zeros(20)
    mean[0] = offset
    return AudioFeatures(bpm=30.0, mfcc=np.zeros(84), centroid=0.0, rms=0.0,
                         mfcc_mean=mean, mfcc_cov=np.eye(20).ravel())


def _song(name: str, features: AudioFeatures | None) -> MusicEntry:
    e = MusicEntry(path=Path(rf"C:\music\{name} (TG 32).mp3"), title=name,
                   dance="TG", bpm=32)
    e.features = features
    return e


class ReplaceUnanalysedTest(unittest.TestCase):

    def setUp(self):
        self.anchor = _features(0.0)
        self.measured = _song("Measured", _features(4.3))   # a weak match, ≈ 31 %
        self.unanalysed = _song("Unanalysed", None)
        sugg = PlaylistSuggester(None, seed=1)
        patch = mock.patch.object(PlaylistSuggester, "_get_pool",
                                  return_value=[self.measured, self.unanalysed])
        patch.start()
        self.addCleanup(patch.stop)
        self.picks = [sugg._pick("TG", "D", "Final", set(), anchor=self.anchor,
                                 strategy="all", timbre_first=True)
                      for _ in range(TRIALS)]

    def test_the_measured_title_is_picked(self):
        self.assertEqual({e.title for e, _sim in self.picks}, {"Measured"})

    def test_its_own_similarity_is_reported(self):
        sim = self.picks[0][1]
        self.assertLess(sim, 0.5)
        self.assertGreater(sim, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
