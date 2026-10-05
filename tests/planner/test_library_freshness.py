"""How fresh a track is: when its file arrived, and when it was last played.

Both answers come from data the app already had lying around — the directory
entry carries the creation time, the playlist paths carry a year — so what is
tested here is that the walk really reports every file with its own timestamp,
and that a scanned entry knows the newest playlist it sits in.

Run:  py -m unittest tests.planner.test_library_freshness -v
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from dancesport_planner import MusicEntry, MusicLibrary
from planner.library import _library_mp3s, playlist_year


def _tmp(prefix="dp_fresh_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _mp3(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_bytes(b"\x00")
    return p


class FakePlaylistLib(MusicLibrary):
    """_playlists_for keyed by entry title — no real playlist index needed."""

    def __init__(self, playlists_by_title=None):
        super().__init__()
        self._by_title = playlists_by_title or {}

    def _playlists_for(self, entry, keys=None):
        return self._by_title.get(entry.title, set())


class LibraryWalkTest(unittest.TestCase):
    """The scandir walk that replaced rglob — same files, plus their age."""

    def test_finds_every_mp3_below_the_root(self):
        root = _tmp()
        _mp3(root, "top.mp3")
        _mp3(root / "standardcd" / "lw", "waltz.mp3")
        _mp3(root / "lateincd", "rumba.MP3")      # upper case counts too
        _mp3(root / "lateincd", "cover.jpg")      # …but only mp3s
        found = {p.name for p, _ in _library_mp3s(root)}
        self.assertEqual(found, {"top.mp3", "waltz.mp3", "rumba.MP3"})

    def test_reports_the_creation_time_of_each_file(self):
        root = _tmp()
        _mp3(root, "now.mp3")
        (path, ts), = _library_mp3s(root)
        self.assertEqual(path.name, "now.mp3")
        self.assertLess(abs(ts - time.time()), 300)

    def test_a_missing_root_is_no_error(self):
        self.assertEqual(_library_mp3s(_tmp() / "nope"), [])

    def test_an_unreadable_folder_does_not_lose_the_rest(self):
        root = _tmp()
        _mp3(root, "kept.mp3")
        deep = root / "gone"
        _mp3(deep, "lost.mp3")
        real_scandir = os.scandir

        def scandir(path):
            if str(path) == str(deep):
                raise PermissionError("no")
            return real_scandir(path)

        with mock.patch("planner.library.os.scandir", scandir):
            found = [p.name for p, _ in _library_mp3s(root)]
        self.assertEqual(found, ["kept.mp3"])


class PlaylistYearTest(unittest.TestCase):
    """The only date an M3U carries is the one in its path."""

    def test_the_newest_year_in_the_path_wins(self):
        self.assertEqual(
            playlist_year(r"D:\Turniere\Turnier 2019\2021 Finale.m3u"), 2021)

    def test_a_path_without_a_year_says_nothing(self):
        self.assertIsNone(playlist_year(r"D:\Turniere\Hochzeit\finale.m3u"))

    def test_a_longer_number_is_not_a_year(self):
        self.assertIsNone(playlist_year(r"D:\Turniere\12019er Liste.m3u"))


class LastPlayedTest(unittest.TestCase):
    """`_apply_popularity` dates every entry it counts."""

    def _entry(self, title):
        return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title)

    def test_the_newest_playlist_dates_the_track(self):
        lib = FakePlaylistLib({"waltz": {r"D:\T\Turnier 2017\a.m3u",
                                         r"D:\T\Turnier 2023\b.m3u"}})
        e = self._entry("waltz")
        lib._apply_popularity(e)
        self.assertEqual(e.popularity, 2)
        self.assertEqual(e.last_played, 2023)

    def test_a_never_played_track_has_no_date(self):
        e = self._entry("unused")
        FakePlaylistLib()._apply_popularity(e)
        self.assertEqual(e.popularity, 0)
        self.assertIsNone(e.last_played)

    def test_undated_playlists_leave_the_date_open(self):
        """Played, but no list says when — that is not the same as 'old'."""
        lib = FakePlaylistLib({"waltz": {r"D:\T\Hochzeit\a.m3u"}})
        e = self._entry("waltz")
        lib._apply_popularity(e)
        self.assertEqual(e.popularity, 1)
        self.assertIsNone(e.last_played)


if __name__ == "__main__":
    unittest.main()
