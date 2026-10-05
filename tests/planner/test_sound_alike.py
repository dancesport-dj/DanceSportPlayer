#!/usr/bin/env python3
"""How much one title sounds like another, three ways at once.

Run:  py -m unittest tests.planner.test_sound_alike -v

Marcel: analyse similarity with the timbre Gaussian/KL, the librosa timbre +
rhythm vector and the chroma cover match — "the best are where all 3 have
high sim", a score of all three, "mehr ein Mittelwert". Each view ranks a
title among its dance, and the agreement is their mean.
"""

import unittest
from pathlib import Path

import numpy as np

from planner.db import AudioFeatures
from planner.library import MusicLibrary
from planner.models import MusicEntry
from planner.similarity import SoundAlike


def _entry(title, mean, vec, dance="WW"):
    e = MusicEntry(path=Path(rf"C:\music\standardcd\{title} ({dance} 59).mp3"),
                   title=title, dance=dance, bpm=59)
    e.features = AudioFeatures(
        bpm=59.0, mfcc=np.asarray(vec, dtype=float), centroid=float(vec[0]),
        rms=float(vec[1]), mfcc_mean=np.asarray(mean, dtype=float),
        mfcc_cov=np.eye(20).ravel())
    return e


class SoundAlikeTest(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(7)
        mean, vec, chroma = rng.normal(size=20), rng.normal(size=84), rng.normal(size=64)
        self.anchor = _entry("Anchor", mean, vec)
        # Close in all three views.
        self.alike = _entry("Alike", mean + 0.3, vec + 0.1 * rng.normal(size=84))
        # The timbre twin: nearly the same Gaussian, but another groove and melody.
        self.twin = _entry("Twin", mean + 0.05, -vec)
        self.others = [_entry(f"Other {k}", rng.normal(size=20) * 2, rng.normal(size=84))
                       for k in range(12)]
        self.chroma = {self.anchor.path: chroma,
                       self.alike.path: chroma + 0.1 * rng.normal(size=64),
                       self.twin.path: -chroma}
        for e in self.others:
            self.chroma[e.path] = rng.normal(size=64)
        self.lib = MusicLibrary()
        self.lib.entries = [self.anchor, self.twin, self.alike, *self.others,
                            _entry("Tango", mean, vec, dance="TG")]
        self.sound = SoundAlike(self.lib, chroma=lambda e: self.chroma.get(e.path))

    def test_the_title_alike_in_all_three_views_comes_first(self):
        (sim, first), *_rest = self.sound(self.anchor, n=3)
        self.assertIs(first, self.alike)
        self.assertGreater(sim, self.sound.agreement(self.anchor, self.twin))

    def test_the_agreement_is_the_mean_of_the_three_views(self):
        views = self.sound.views(self.anchor, self.twin)
        self.assertEqual(set(views), {"timbre", "groove", "melody"})
        self.assertGreaterEqual(views["timbre"], self.sound.views(self.anchor, self.alike)["timbre"])
        self.assertAlmostEqual(self.sound.agreement(self.anchor, self.twin),
                               sum(views.values()) / 3)
        self.assertLess(views["melody"], 0.5)

    def test_it_ranks_within_the_dance_and_leaves_out_the_anchor(self):
        found = [e for _sim, e in self.sound(self.anchor, n=50)]
        self.assertEqual(len(found), 14)
        self.assertNotIn(self.anchor, found)
        self.assertTrue(all(e.dance == "WW" for e in found))

    def test_a_title_missing_a_view_sits_in_its_middle(self):
        del self.chroma[self.alike.path]
        self.assertEqual(self.sound.views(self.anchor, self.alike)["melody"], 0.5)

    def test_without_chroma_two_views_decide(self):
        sound = SoundAlike(self.lib)
        self.assertEqual(set(sound.views(self.anchor, self.alike)), {"timbre", "groove"})
        self.assertIs(sound(self.anchor, n=1)[0][1], self.alike)


if __name__ == "__main__":
    unittest.main()
