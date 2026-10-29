#!/usr/bin/env python3
"""The pick score weighs popularity against sound and tempo as the W_* say.

Run:  py -m unittest tests.planner.test_pick_score_balance -v

Popularity used to enter `_pick` as a raw play count while timbre and tempo fit
are 0..1: one extra play (×3) outweighed a much closer sound (×W_TIMBRE 5 over
a 0.4 gap = 2). Popularity is now on the pool's own 0..1 log scale, so a much
closer sound beats a single play, while a staple still beats a title nobody
has played.

`_pick` draws among the top ten by score; with a two-title pool the better one
wins with weight (gap + 0.1) against 0.1, so a clear gap shows as a clear share.
"""

import unittest
from pathlib import Path
from unittest import mock

from planner.generate.suggester import PlaylistSuggester
from planner.models import MusicEntry

TRIALS = 300


def _song(name: str, plays: int) -> MusicEntry:
    e = MusicEntry(path=Path(rf"C:\music\{name} (TG 32).mp3"), title=name,
                   dance="TG", bpm=32)
    e.popularity = plays
    e.class_plays = {"D": plays} if plays else {}
    e.features = object()             # anything truthy: the sims are mocked
    return e


def _share_of(winner: MusicEntry, sims: list[tuple[MusicEntry, float]]) -> float:
    pool = [e for e, _ in sims]
    sugg = PlaylistSuggester(None, seed=1)   # the pool is mocked, the library unused
    with mock.patch.object(PlaylistSuggester, "_get_pool", return_value=pool), \
            mock.patch("planner.generate.suggester.timbre_similarity",
                       return_value={str(e.path): s for e, s in sims}):
        wins = sum(sugg._pick("TG", "D", "Final", set(), anchor=object(),
                              strategy="mixed")[0] is winner
                   for _ in range(TRIALS))
    return wins / TRIALS


class PickScoreBalanceTest(unittest.TestCase):

    def test_a_much_closer_sound_beats_one_more_play(self):
        played_4 = _song("Four", 4)
        played_3 = _song("Three", 3)
        share = _share_of(played_3, [(played_4, 0.5), (played_3, 0.9)])
        self.assertGreater(share, 0.75)

    def test_a_staple_still_beats_an_unplayed_title(self):
        staple = _song("Staple", 20)
        unknown = _song("Unknown", 0)
        share = _share_of(staple, [(staple, 0.6), (unknown, 0.8)])
        self.assertGreater(share, 0.75)


if __name__ == "__main__":
    unittest.main(verbosity=2)
