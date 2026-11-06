#!/usr/bin/env python3
"""One title is danced once in a round, whoever recorded it.

Run:  py -m unittest tests.planner.test_suggester_same_title -v

Tier 2 #6/#7: "Bamboleo" by Jao and by DJ Ice are two files, so the
no-repeat set (which held file paths) let both into one competition.
"""

import unittest
from pathlib import Path

from planner.generate.suggester import PlaylistSuggester, mark_used
from planner.models import MusicEntry, rounds_from_pattern
from planner.music.library import MusicLibrary


def _library() -> MusicLibrary:
    lib = MusicLibrary()
    names = ["Bamboleo (SA51)", "Bamboleo DJ Ice"]
    lib.entries.extend(
        MusicEntry(path=Path(rf"C:\music\LateinCD\{n}.mp3"), title=n, dance="SA", bpm=51)
        for n in names)
    return lib


class SameTitleTest(unittest.TestCase):

    def test_two_recordings_of_one_title_do_not_share_a_round(self):
        playlist = PlaylistSuggester(_library(), seed=1).suggest(
            "S", rounds_from_pattern("2"), ["SA"], use_timbre=False, style="Latin")
        picked = [e for heats in playlist.values() for heat in heats
                  for e in heat if e is not None]
        self.assertEqual(len(picked), 1, [e.title for e in picked])

    def test_a_rerolled_round_skips_a_title_another_round_has(self):
        lib = _library()
        sugg = PlaylistSuggester(lib, seed=1)
        rc = rounds_from_pattern("1")[0]
        used: set = set()
        mark_used(used, lib.entries[0])
        heats = sugg.regenerate_round(rc, ["SA"], "S", used, set(),
                                      use_timbre=False, style="Latin")
        self.assertEqual([e for heat in heats for e in heat], [None])


if __name__ == "__main__":
    unittest.main(verbosity=2)
