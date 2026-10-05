#!/usr/bin/env python3
"""Tests for 🔀 Shuffle on the ETDS party list.

Run:  py -m unittest tests.planner.test_warmup_reshuffle -v

Shuffle puts the titles of the list in a fresh order, the way building the list
again from scratch would, out of exactly the titles it already holds: none is
lost, none is added.
"""

import random
import unittest
from collections import Counter
from pathlib import Path

from planner.models import MusicEntry
from planner.warmup import reshuffle_warmup, warmup_code, warmup_rounds


def _e(code: str, n: int) -> MusicEntry:
    social = {"DISCOFOX": "Discofox", "SALSA": "Salsa"}
    return MusicEntry(path=Path(rf"C:\music\{code}{n}.mp3"), title=f"{code} {n}",
                      dance=None if code in social else code,
                      other_genre=social.get(code), duration=180)


def _party(per_dance=4, codes=("LW", "TG", "WW", "SF", "QS",
                               "SA", "CC", "RB", "PD", "JI", "DISCOFOX")):
    return [_e(c, n) for c in codes for n in range(1, per_dance + 1)]


class ReshuffleTest(unittest.TestCase):

    def setUp(self):
        random.seed(7)

    def test_keeps_every_title(self):
        entries = _party()
        out = reshuffle_warmup(entries)
        self.assertEqual(len(out), len(entries))
        self.assertEqual({id(e) for e in out}, {id(e) for e in entries})

    def test_comes_out_in_a_fresh_order(self):
        entries = _party()
        orders = {tuple(id(e) for e in reshuffle_warmup(entries)) for _ in range(5)}
        self.assertGreater(len(orders), 1)
        self.assertNotIn(tuple(id(e) for e in entries), orders)

    def test_alternates_standard_and_latin_like_a_fresh_build(self):
        out = reshuffle_warmup(_party())
        sections = [s for s, _songs in warmup_rounds(out)]
        self.assertTrue(sections[0].startswith("Standardrunde"))
        self.assertTrue(sections[1].startswith("Lateinrunde"))

    def test_a_list_that_started_latin_starts_latin_again(self):
        entries = _party()
        first = reshuffle_warmup(entries, start_with_latin=True)
        again = reshuffle_warmup(first)
        self.assertTrue(warmup_rounds(again)[0][0].startswith("Lateinrunde"))

    def test_social_titles_stay_even_when_not_ticked_before(self):
        out = reshuffle_warmup(_party())
        self.assertEqual(Counter(warmup_code(e) for e in out)["DISCOFOX"], 4)

    def test_a_title_without_a_warmup_dance_goes_to_the_end(self):
        odd = MusicEntry(path=Path(r"C:\music\odd.mp3"), title="odd", dance=None)
        entries = _party() + [odd]
        out = reshuffle_warmup(entries)
        self.assertIs(out[-1], odd)
        self.assertEqual(len(out), len(entries))

    def test_standard_only_list(self):
        entries = _party(codes=("LW", "TG", "QS"))
        out = reshuffle_warmup(entries)
        self.assertEqual({id(e) for e in out}, {id(e) for e in entries})


if __name__ == "__main__":
    unittest.main()
