#!/usr/bin/env python3
"""Tests for planner.planned — the one rule for "already in an open deck".

Run:  py -m unittest tests.planner.test_planned -v

It was written out four times (🧹 deck clean, 🧹 wishlist clean, the 🆕
library browser, the 🤸 "unused only" source), and two of the copies looked a
path up without lower-casing it first — so a planned track with a capital in
its path was never found by its path.
"""
import unittest
from pathlib import Path

from planner.planned import is_planned, path_key

_PLANNED = Path(r"F:\My Music\Tanzcds\LW\Moon River (LW 29).mp3")


def _index(*paths, fps=()):
    return {path_key(p) for p in paths}, set(fps)


class IsPlannedTest(unittest.TestCase):

    def test_a_planned_path_matches_whatever_its_case(self):
        paths, fps = _index(_PLANNED)
        self.assertTrue(is_planned(Path(str(_PLANNED).upper()), paths, fps))
        self.assertTrue(is_planned(str(_PLANNED), paths, fps))

    def test_a_renamed_copy_matches_by_its_fingerprint(self):
        paths, fps = _index(_PLANNED, fps={"FP1"})
        copy = Path(r"F:\Other\Moon River copy.mp3")
        self.assertTrue(is_planned(copy, paths, fps, lambda p: "FP1"))
        self.assertFalse(is_planned(copy, paths, fps, lambda p: "FP2"))

    def test_the_file_is_not_fingerprinted_without_fingerprints_to_match(self):
        asked = []
        paths, fps = _index(_PLANNED)
        is_planned(Path(r"F:\x.mp3"), paths, fps, asked.append)
        self.assertEqual(asked, [])

    def test_a_failing_fingerprint_is_no_match(self):
        def broken(_p):
            raise OSError("locked")
        paths, fps = _index(fps={"FP1"})
        self.assertFalse(is_planned(Path(r"F:\x.mp3"), paths, fps, broken))

    def test_a_track_without_a_path_is_never_planned(self):
        paths, fps = _index(_PLANNED, fps={"FP1"})
        self.assertFalse(is_planned(None, paths, fps, lambda p: "FP1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
