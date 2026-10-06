#!/usr/bin/env python3
"""A playlist is read with its umlauts, or not at all.

Run:  py -m unittest tests.planner.test_playlist_umlauts -v

Every playlist was read as UTF-8 with the errors thrown away. About 500 of the
tournament lists are cp1252 (the old Java app, Windows tools), and in those
every ä/ö/ü/ß was dropped: 'Küss mich' became 'Kss mich', no longer matched
the library, and the song counted as never played — or came back from an
import as missing. They are now decoded strictly (BOM, UTF-8, cp1252). A file
that is none of them is skipped with a warning where a whole folder is walked,
and refused where it is the one file being imported.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from dancesport_planner import MusicEntry, MusicLibrary
from planner import config as planner_config
from planner.competition import parse_competition_schedule
from planner.m3u import import_playlist_m3u, read_m3u_tracks
from planner.playlist_text import PlaylistEncodingError

_TRACK = r"C:\music\standardcd\Küss mich (TG 32).mp3"
_UNDECODABLE = b"\x81\x8d not text \x8f\x90\r\n"   # neither UTF-8 nor cp1252


class _Base(unittest.TestCase):

    def setUp(self):
        self._orig_dir = planner_config.PLAYLIST_DIR
        self.dir = Path(tempfile.mkdtemp(prefix="dp_umlaut_"))
        planner_config.set_playlist_dir(self.dir)
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(planner_config.set_playlist_dir, self._orig_dir)
        self.entry = MusicEntry(path=Path(_TRACK), title="Küss mich",
                                dance="TG", bpm=32)

    def _lib(self):
        lib = MusicLibrary()
        lib.entries.append(self.entry)
        return lib

    def _write(self, name, data: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(data)
        return p

    def _cp1252_list(self, name):
        return self._write(name, ("#EXTM3U\r\n" + _TRACK + "\r\n").encode("cp1252"))


class PopularityTest(_Base):

    def test_a_cp1252_list_counts_its_umlaut_title(self):
        self._cp1252_list("Turnier 2026 Hgr B TG.m3u")
        lib = self._lib()
        self.assertEqual(lib.relearn_playlists(), 1)
        self.assertEqual(self.entry.popularity, 1)

    def test_an_undecodable_list_is_skipped_out_loud(self):
        self._write("Turnier 2026 Hgr B TG.m3u", _UNDECODABLE)
        with self.assertLogs("dancesport.library", "WARNING") as cm:
            self._lib().relearn_playlists()
        self.assertEqual(self.entry.popularity, 0)
        self.assertIn("Turnier 2026 Hgr B TG.m3u", "\n".join(cm.output))


class PastCompetitionTest(_Base):

    def setUp(self):
        super().setUp()
        self.spec = parse_competition_schedule("HGR B STD 1-1")[0]

    def test_a_cp1252_list_is_found_as_planned_before(self):
        self._cp1252_list("Turnier Hgr B STD.m3u")
        entries, n_files = self._lib().past_competition_entries(self.spec)
        self.assertEqual(n_files, 1)
        self.assertEqual(entries, [self.entry])

    def test_the_round_pools_read_it_too(self):
        self._cp1252_list("Turnier Hgr B STD.m3u")
        found, _rounds, n_files, _sources = self._lib().past_competition_round_pools(
            self.spec, [1, 1], 5)
        self.assertEqual(n_files, 1)
        self.assertEqual(found, [self.entry])

    def test_an_undecodable_list_is_skipped_out_loud(self):
        self._write("Turnier Hgr B STD.m3u", _UNDECODABLE)
        with self.assertLogs("dancesport.library", "WARNING"):
            entries, _n = self._lib().past_competition_entries(self.spec)
        self.assertEqual(entries, [])
        with self.assertLogs("dancesport.library", "WARNING"):
            self._lib().past_competition_round_pools(self.spec, [1, 1], 5)


class ReadAndImportTest(_Base):

    def test_the_browsing_view_shows_the_umlaut_path(self):
        p = self._cp1252_list("list.m3u")
        self.assertEqual([t for t, _x in read_m3u_tracks(p)], [Path(_TRACK)])

    def test_the_browsing_view_shows_an_undecodable_file_as_empty_and_says_why(self):
        p = self._write("list.m3u", _UNDECODABLE)
        with self.assertLogs("dancesport.m3u", "WARNING"):
            self.assertEqual(read_m3u_tracks(p), [])

    def test_an_import_resolves_the_umlaut_title_to_the_library(self):
        p = self._cp1252_list("list.m3u")
        res = import_playlist_m3u(p, SimpleNamespace(entries=[self.entry]), None)
        self.assertEqual(res["missing"], 0)
        self.assertIs(next(iter(res["playlist"].values()))[0][0], self.entry)

    def test_an_import_of_an_undecodable_file_fails(self):
        p = self._write("list.m3u", _UNDECODABLE)
        with self.assertRaises(PlaylistEncodingError):
            import_playlist_m3u(p, SimpleNamespace(entries=[]), None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
