#!/usr/bin/env python3
"""A generation is reproducible from its seed.

Run:  py -m unittest tests.planner.test_suggester_seed -v

The suggester drew from the interpreter's global `random`, so a surprising pick
could never be replayed, and a test's `random.seed()` reached into every other
test in the process. Each `PlaylistSuggester` now owns a `random.Random`, seeded
from `seed` or a fresh one it records, and the deck keeps that seed.
"""

import random
import unittest
from pathlib import Path

from planner.library import MusicLibrary
from planner.models import MusicEntry, rounds_from_pattern
from planner.suggester import PlaylistSuggester


def _library() -> MusicLibrary:
    lib = MusicLibrary()
    lib.entries.extend(
        MusicEntry(path=Path(rf"C:\music\CC\Cha {i}.mp3"), title=f"Cha {i}",
                   dance="CC", bpm=31, popularity=i % 7)
        for i in range(40))
    return lib


def _titles(sugg: PlaylistSuggester) -> list[str]:
    playlist = sugg.suggest("S", rounds_from_pattern("1-1-1"), ["CC"],
                            use_timbre=False, style="Latin")
    return [e.title for heats in playlist.values()
            for heat in heats for e in heat if e is not None]


class SuggesterSeedTest(unittest.TestCase):

    def test_the_same_seed_gives_the_same_playlist(self):
        lib = _library()
        self.assertEqual(_titles(PlaylistSuggester(lib, seed=81723)),
                         _titles(PlaylistSuggester(lib, seed=81723)))

    def test_a_suggester_without_a_seed_records_the_one_it_drew(self):
        lib = _library()
        first = PlaylistSuggester(lib)
        self.assertIsInstance(first.seed, int)
        self.assertEqual(_titles(first), _titles(PlaylistSuggester(lib, seed=first.seed)))

    def test_the_global_random_state_is_left_alone(self):
        lib = _library()
        random.seed(1)
        expected = random.random()
        random.seed(1)
        _titles(PlaylistSuggester(lib, seed=5))
        self.assertEqual(random.random(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
