#!/usr/bin/env python3
"""Tests for 🎵 the pause filler on its own, without a window or a player.

Run:  py -m unittest tests.player.test_pause_filler -v

The filler decides WHICH title plays in the between-dances pause and how loud
its fade ramp lets it be; loading, playing and routing stay with the window.
"""

import tempfile
import unittest
from pathlib import Path

from player.pause_filler import PauseFiller


class _Titles(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def titles(self, *names):
        paths = []
        for n in names:
            p = self.dir / f"{n}.mp3"
            p.write_bytes(b"")
            paths.append(str(p))
        return paths


class LoadTest(_Titles):

    def test_nothing_loaded_means_nothing_current(self):
        self.assertIsNone(PauseFiller().current)

    def test_load_returns_the_first_title(self):
        f = PauseFiller()
        a, b = self.titles("a", "b")
        self.assertEqual(f.load([a, b]), a)
        self.assertEqual(f.current, a)

    def test_missing_files_are_left_out(self):
        f = PauseFiller()
        (a,) = self.titles("a")
        self.assertEqual(f.load([str(self.dir / "gone.mp3"), a]), a)
        self.assertEqual(f.titles, [a])

    def test_no_existing_file_loads_nothing(self):
        f = PauseFiller()
        self.assertIsNone(f.load([str(self.dir / "gone.mp3")]))
        self.assertIsNone(f.current)

    def test_the_next_pause_resumes_the_rotation(self):
        """The title after the one the last pause rotated to — the hall does
        not hear the same opening every pause."""
        f = PauseFiller()
        paths = self.titles("a", "b", "c")
        f.load(paths)
        f.rotate()
        self.assertEqual(f.load(paths), paths[1])

    def test_a_shorter_list_wraps_the_position(self):
        f = PauseFiller()
        paths = self.titles("a", "b", "c")
        f.load(paths)
        f.rotate()
        f.rotate()
        self.assertEqual(f.load(paths[:2]), paths[0])


class RotateTest(_Titles):

    def test_rotate_moves_to_the_next_title_and_wraps(self):
        f = PauseFiller()
        a, b = self.titles("a", "b")
        f.load([a, b])
        self.assertEqual(f.rotate(), b)
        self.assertEqual(f.rotate(), a)

    def test_a_single_title_rotates_onto_itself(self):
        f = PauseFiller()
        (a,) = self.titles("a")
        f.load([a])
        self.assertEqual(f.rotate(), a)

    def test_rotating_nothing_is_None(self):
        self.assertIsNone(PauseFiller().rotate())


class FadeTest(unittest.TestCase):

    def filler(self, total):
        f = PauseFiller()
        f.total = total
        return f

    def test_the_fade_in_rises_over_the_first_two_seconds(self):
        f = self.filler(12.0)
        self.assertAlmostEqual(f.fade(12.0), 0.0)
        self.assertAlmostEqual(f.fade(11.0), 0.5)
        self.assertAlmostEqual(f.fade(10.0), 1.0)

    def test_full_level_in_between(self):
        self.assertAlmostEqual(self.filler(12.0).fade(6.0), 1.0)

    def test_the_fade_out_falls_over_the_last_two_seconds(self):
        f = self.filler(12.0)
        self.assertAlmostEqual(f.fade(1.0), 0.5)
        self.assertAlmostEqual(f.fade(0.0), 0.0)

    def test_a_short_pause_fades_over_a_third_of_it(self):
        f = self.filler(4.5)
        self.assertAlmostEqual(f.fade(4.5 - 0.75), 0.5)

    def test_an_extended_pause_keeps_the_ramp_proportional(self):
        f = self.filler(12.0)
        f.total += 12.0
        self.assertAlmostEqual(f.fade(12.0), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
