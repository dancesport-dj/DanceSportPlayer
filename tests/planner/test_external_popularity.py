"""A track from outside the library still counts its past playlists.

Run:  py -m unittest tests.planner.test_external_popularity -v

Marcel, after a restart: every row of the saved decks read ✦new in Pop, though
those titles had been planned before. The decks came from .m3u lists naming the
old library copy (C:\\…\\datein\\my music), which still exists on this PC, so each
line became an EXTERNAL entry — and only library entries were ever given a
popularity. The playlist index is keyed by filename and title, not by path, so
an outside copy of a well-used track matches it just as well.
"""
import unittest
from pathlib import Path
from unittest import mock

from planner.library import MusicLibrary
from planner.models import MusicEntry

_OUTSIDE = Path(r"C:\old copy\tanzcds\standardcd\007 LW Stuck On You (LW 29).mp3")


class _Cache:
    """Only what make_external_entry asks of the AudioCache."""

    def recorded_fingerprint(self, path):
        return None

    def get(self, path, hash_if_missing=False):
        return None


class ExternalPopularityTest(unittest.TestCase):

    def setUp(self):
        self.lib = MusicLibrary()
        self.fresh = MusicEntry(path=_OUTSIDE, title="Stuck On You", dance="LW", bpm=29)

    def _external(self) -> MusicEntry:
        with mock.patch.object(self.lib, "_make_entry", return_value=self.fresh):
            return self.lib.make_external_entry(_OUTSIDE, _Cache())

    def _learn(self, *playlists: str):
        """The index as `_learn_playlists` leaves it, for this track's keys."""
        for key in self.lib._match_keys(self.fresh):
            self.lib._track_playlists[key] = set(playlists)

    def test_a_planned_track_is_not_new(self):
        self._learn(r"D:\Turniere\a\CSTD.m3u", r"D:\Turniere\b\HGR_II_D_STD.m3u")
        e = self._external()
        self.assertEqual(e.popularity, 2)
        self.assertIn("CSTD", e.source_info)

    def test_a_never_planned_track_stays_new(self):
        self.assertEqual(self._external().popularity, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
