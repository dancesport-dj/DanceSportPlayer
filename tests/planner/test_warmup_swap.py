#!/usr/bin/env python3
"""Tests for the ↺ swap partner on the ETDS party list.

Run:  py -m unittest tests.planner.test_warmup_swap -v

↺ on a party list does not fetch a new title from the library: it swaps the row
with a title of the same dance from the bottom of the list. The leftovers come
first, the rounds at the very end that no longer fit the Standard / Latin order
because the other section ran dry. Without leftovers it's any title of that
dance from the last third.
"""

import random
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.warmup import warmup_leftover_start, warmup_swap_partner


def _e(code: str, n: int) -> MusicEntry:
    social = {"DISCOFOX": "Discofox", "SALSA": "Salsa"}
    return MusicEntry(path=Path(rf"C:\music\{code}{n}.mp3"), title=f"{code} {n}",
                      dance=None if code in social else code,
                      other_genre=social.get(code), duration=180)


def _list(*rounds) -> list:
    """Rounds of dance codes, flattened into entries numbered per dance."""
    seen: dict[str, int] = {}
    out = []
    for codes in rounds:
        for c in codes:
            seen[c] = seen.get(c, 0) + 1
            out.append(_e(c, seen[c]))
    return out


class LeftoverStartTest(unittest.TestCase):

    def test_standard_rounds_back_to_back_after_latin_ran_dry(self):
        # S L S L S | S — the Standard round right after the last Latin one is
        # still in order; the one after it is a leftover.
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"], ["SA", "CC", "RB"],
                        ["LW", "TG", "SF"], ["LW", "QS"])
        self.assertEqual(warmup_leftover_start(entries), 15)

    def test_alternating_to_the_end_has_no_leftovers(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"], ["SA", "CC", "RB"])
        self.assertEqual(warmup_leftover_start(entries), len(entries))

    def test_a_list_cut_after_a_standard_round_has_no_leftovers(self):
        # max_tracks cut the list in the middle of a pass.
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"])
        self.assertEqual(warmup_leftover_start(entries), len(entries))

    def test_social_rounds_between_do_not_hide_the_leftovers(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"], ["DISCOFOX"],
                        ["LW", "SF", "QS"], ["SALSA"], ["LW", "TG", "SF"])
        # S L D | S Sal S  → leftovers start at the second Standard round.
        self.assertEqual(warmup_leftover_start(entries), 11)

    def test_a_single_section_list_has_no_leftovers(self):
        entries = _list(["LW", "TG", "QS"], ["LW", "SF", "QS"], ["LW", "TG"])
        self.assertEqual(warmup_leftover_start(entries), len(entries))


class SwapPartnerTest(unittest.TestCase):

    def test_prefers_a_leftover_of_the_same_dance(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"], ["SA", "CC", "RB"],
                        ["LW", "TG", "SF"], ["LW", "QS"])
        # The LW at 12 is in the last third too, but 15 is the leftover.
        for seed in range(20):
            self.assertEqual(warmup_swap_partner(entries, 0, random.Random(seed)), 15)

    def test_falls_back_to_the_last_third(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"], ["SA", "CC", "RB"],
                        ["LW", "TG", "SF"], ["CC", "RB", "JI"])
        # 18 titles → the last third starts at 12; LW sits at 0, 6, 12.
        for seed in range(20):
            self.assertEqual(warmup_swap_partner(entries, 0, random.Random(seed)), 12)

    def test_picks_at_random_among_the_last_third(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["LW", "SF", "QS"], ["SA", "CC", "RB"],
                        ["TG", "SF", "QS"], ["CC", "RB", "JI"])
        # CC at 3, 10, 15: only 15 is in the last third (from 12 on).
        picks = {warmup_swap_partner(entries, 3, random.Random(s)) for s in range(20)}
        self.assertEqual(picks, {15})
        picks = {warmup_swap_partner(entries, 1, random.Random(s)) for s in range(40)}
        self.assertEqual(picks, {12})    # TG at 1 and 12
        entries.append(_e("TG", 9))        # a second TG in the last third
        picks = {warmup_swap_partner(entries, 1, random.Random(s)) for s in range(40)}
        self.assertEqual(picks, {12, 18})

    def test_never_the_row_itself(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"], ["LW", "SF", "QS"])
        self.assertIsNone(warmup_swap_partner(entries, 6))

    def test_none_when_the_dance_is_not_near_the_end(self):
        entries = _list(["LW", "TG", "QS"], ["CC", "RB", "JI"],
                        ["TG", "SF", "QS"], ["SA", "CC", "RB"])
        self.assertIsNone(warmup_swap_partner(entries, 0))


if __name__ == "__main__":
    unittest.main()
