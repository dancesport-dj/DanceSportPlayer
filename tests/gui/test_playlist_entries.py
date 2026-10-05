#!/usr/bin/env python3
"""Tests for turning a playlist's lines into library entries, without a window.

Run:  py -m unittest tests.gui.test_playlist_entries -v

The parse is shared by a dropped .m3u and a party list; the resolve is what a
party list's titles become — the library's own entry where it has one, else a
re-rooted path, else an entry read off the disk.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

from gui.playlist_entries import playlist_paths, resolve_playlist_entries


def entry(path):
    return SimpleNamespace(path=Path(path))


class _Lib:
    def __init__(self, *paths, external=()):
        self.entries = [entry(p) for p in paths]
        self.external = {str(Path(p)) for p in external}
        self.caches = []

    def make_external_entry(self, path, cache):
        self.caches.append(cache)
        if str(path) in self.external:
            return entry(path)
        raise OSError("not there")


class PlaylistPathsTest(unittest.TestCase):

    def test_comments_and_blank_lines_are_not_tracks(self):
        lines = ["#EXTM3U", "#EXTINF:180,A", r"C:\m\a.mp3", "  ", r"C:\m\b.mp3"]
        self.assertEqual(playlist_paths(lines), [Path(r"C:\m\a.mp3"), Path(r"C:\m\b.mp3")])

    def test_a_file_url_and_a_quoted_path_read_as_paths(self):
        lines = ["file:///C:/m/a%20b.mp3", '"C:\\m\\c.mp3"']
        self.assertEqual(playlist_paths(lines), [Path("C:/m/a b.mp3"), Path(r"C:\m\c.mp3")])


class ResolveTest(unittest.TestCase):

    def test_the_library_entry_is_taken_whatever_the_case(self):
        lib = _Lib(r"C:\m\Tango.mp3")
        got = resolve_playlist_entries([Path(r"c:\M\tango.mp3")], lib, None)
        self.assertIs(got[0], lib.entries[0])

    def test_a_path_from_another_machine_is_re_rooted(self):
        lib = _Lib(r"F:\m\Tango.mp3")
        remapper = SimpleNamespace(remap=lambda p: Path(r"F:\m") / p.name)
        got = resolve_playlist_entries([Path(r"E:\m\Tango.mp3")], lib, None, remapper)
        self.assertEqual(got, [lib.entries[0]])

    def test_a_title_outside_the_library_is_read_off_the_disk(self):
        lib = _Lib(external=[r"C:\x\new.mp3"])
        got = resolve_playlist_entries([Path(r"C:\x\new.mp3"), Path(r"C:\x\gone.mp3")],
                                       lib, "cache")
        self.assertEqual([e.path for e in got], [Path(r"C:\x\new.mp3")])
        self.assertEqual(lib.caches, ["cache", "cache"])

    def test_a_title_listed_twice_is_taken_once_in_its_first_place(self):
        lib = _Lib(r"C:\m\a.mp3", r"C:\m\b.mp3")
        paths = [Path(r"C:\m\b.mp3"), Path(r"C:\m\a.mp3"), Path(r"C:\m\b.mp3")]
        got = resolve_playlist_entries(paths, lib, None)
        self.assertEqual([e.path.name for e in got], ["b.mp3", "a.mp3"])

    def test_progress_counts_the_tracks_every_25(self):
        lib = _Lib(*[rf"C:\m\{n}.mp3" for n in range(60)])
        seen = []
        resolve_playlist_entries([e.path for e in lib.entries], lib, None,
                                 progress_cb=lambda d, t, detail: seen.append((d, t, detail)))
        self.assertEqual(seen, [(0, 60, "0 tracks"), (25, 60, "25 tracks"),
                                (50, 60, "50 tracks")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
