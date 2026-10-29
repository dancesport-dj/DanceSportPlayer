#!/usr/bin/env python3
"""A pick's timbre similarity belongs to the deck and round it was measured for.

Run:  py -m unittest tests.planner.test_pick_similarity -v

`_pick` wrote the score onto the library's MusicEntry, which every deck shares:
the same track in two decks showed whichever deck picked it last. Each
suggester now keeps it per round, next to the anchors it was measured against.

A track without audio features has no similarity. The ↺ branch used to call
that 0.5, an average match, so unanalysed tracks pushed real matches out of
the closest-sounding shortlist.
"""

import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from dancesport_planner import MusicEntry, MusicLibrary, PlaylistSuggester
from planner.generate import suggester as suggester_mod
from planner.music.analysis import AudioFeatures

ANCHOR_A = object()
ANCHOR_B = object()
# Analysed: a timbre Gaussian the metric can place (the scores are mocked).
FEATURES = AudioFeatures(bpm=32.0, mfcc=np.zeros(84), centroid=0.0, rms=0.0,
                         mfcc_mean=np.zeros(20), mfcc_cov=np.eye(20).ravel())


def _entry(name: str, features=True) -> MusicEntry:
    e = MusicEntry(path=Path(rf"C:\music\tanzcds\standardcd\TG\{name}.mp3"),
                   title=name, dance="TG", bpm=None, popularity=3)
    e.features = FEATURES if features else None
    return e


def _fake_similarity(score_of):
    """`_timbre_similarity` stand-in for the analysed tracks; the real one
    also scores the rest, with a neutral 0.5."""
    def similarity(anchor, entries):
        return {str(e.path): score_of(anchor, e) for e in entries if e.features}
    return similarity


class PickSimilarityTest(unittest.TestCase):

    def _suggester(self, entries) -> PlaylistSuggester:
        lib = MusicLibrary()
        lib.entries.extend(entries)
        return PlaylistSuggester(lib)

    def test_two_decks_keep_their_own_score_for_the_same_track(self):
        track = _entry("Tanguera (TG 32)")
        deck_a, deck_b = self._suggester([track]), self._suggester([track])
        score = {ANCHOR_A: 0.9, ANCHOR_B: 0.2}
        with mock.patch.object(suggester_mod, "timbre_similarity",
                               _fake_similarity(lambda a, e: score[a])):
            deck_a.regenerate("TG", "S", "early", set(), round_name="Final",
                              anchor=ANCHOR_A, style="Standard")
            deck_b.regenerate("TG", "S", "early", set(), round_name="Final",
                              anchor=ANCHOR_B, style="Standard")
        self.assertEqual(deck_a.similarity(track, "Final"), 0.9)
        self.assertEqual(deck_b.similarity(track, "Final"), 0.2)

    def test_a_re_roll_scores_an_unanalysed_track_as_none(self):
        track = _entry("Sway (TG 33)", features=False)
        sugg = self._suggester([track])
        with mock.patch.object(suggester_mod, "timbre_similarity",
                               _fake_similarity(lambda a, e: 0.3)):
            picked = sugg.regenerate("TG", "S", "early", set(), round_name="Final",
                                     anchor=ANCHOR_A, style="Standard")
        self.assertIs(picked, track)
        self.assertIsNone(sugg.similarity(track, "Final"))

    def test_unanalysed_tracks_stay_out_of_the_closest_sounding_shortlist(self):
        analysed = [_entry(f"Analysed {i} (TG 32)") for i in range(10)]
        unanalysed = _entry("Unanalysed (TG 32)", features=False)
        sugg = self._suggester(analysed + [unanalysed])
        offered = []

        def choices(population, weights, k):
            offered.extend(population)
            return [population[0]]

        with mock.patch.object(suggester_mod, "timbre_similarity",
                               _fake_similarity(lambda a, e: 0.3)), \
             mock.patch.object(suggester_mod.random, "choices", choices):
            sugg.regenerate("TG", "S", "early", set(), round_name="Final",
                            anchor=ANCHOR_A, style="Standard")
        self.assertNotIn(unanalysed, offered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
