#!/usr/bin/env python3
"""The warning a hand-picked ⚡ Generate source owes the user.

Run:  py -m unittest tests.planner.test_source_gap_hint -v

Drawing from the wishlists or one .m3u is strict: a dance that pool cannot
cover stays blank instead of being topped up from the whole library. That is
the point of the setting — but a silently blank slot reads as a bug, so
`source_gap_hint` has to name the dances and the count.
"""

import unittest

from planner.suggester import source_gap_hint


def _entry(title):
    return type("E", (), {"title": title})()


def _playlist(rows):
    """{'Round 1': [heat, …]} from plain lists of 'x' (filled) / None."""
    return {"Round 1": [[_entry("t") if c else None for c in row] for row in rows]}


class SourceGapHintTest(unittest.TestCase):

    def test_the_favorites_library_says_nothing_here(self):
        """An empty label = the default source; generate_hints covers that one."""
        pl = _playlist([[None, None]])
        self.assertEqual(source_gap_hint(pl, ["SA", "CC"], ""), "")

    def test_a_pool_that_covers_everything_stays_quiet(self):
        pl = _playlist([["x", "x"], ["x", "x"]])
        self.assertEqual(source_gap_hint(pl, ["SA", "CC"], "⭐ the open wishlists"), "")

    def test_no_playlist_at_all_stays_quiet(self):
        self.assertEqual(source_gap_hint(None, ["SA"], "⭐ the open wishlists"), "")

    def test_the_blank_slots_are_counted_and_named_per_dance(self):
        pl = _playlist([["x", None], ["x", None], [None, None]])
        got = source_gap_hint(pl, ["SA", "CC"], "📂 party.m3u")
        self.assertIn("📂 party.m3u", got)
        self.assertIn("could not fill 4 of 6 slots", got)
        self.assertIn("Cha-Cha 3", got)
        self.assertIn("Samba 1", got)

    def test_the_worst_dance_is_named_first(self):
        pl = _playlist([[None, None], ["x", None]])
        got = source_gap_hint(pl, ["SA", "CC"], "📂 party.m3u")
        self.assertLess(got.index("Cha-Cha 2"), got.index("Samba 1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
