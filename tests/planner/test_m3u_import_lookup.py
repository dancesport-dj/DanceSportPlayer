#!/usr/bin/env python3
"""An imported .m3u line finds its library entry through the path index.

Run:  py -m unittest tests.planner.test_m3u_import_lookup -v

`_resolve_import_path` walked the whole entry list for every line, twice when
the case differed: a 60-line list against a 54k-track library is millions of
string compares. It now asks `MusicLibrary.entry_for`, with the same answer:
an exact path first, then a case-folded one.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dancesport_planner import MusicEntry, MusicLibrary
from planner.playlist.m3u import _resolve_import_path

TANGO = r"C:\music\tanzcds\standardcd\TG\Tanguera (TG 32).mp3"


class _Loud(list):
    def __iter__(self):
        raise AssertionError("the import walked the whole entry list")


def _library(*paths) -> MusicLibrary:
    lib = MusicLibrary()
    lib.entries = [MusicEntry(path=Path(p), title=Path(p).stem, dance="TG")
                   for p in paths]
    return lib


class M3uImportLookupTest(unittest.TestCase):

    def test_a_line_resolves_without_walking_the_list(self):
        lib = _library(TANGO)
        tango = lib.entries[0]
        lib.entry_for(TANGO)                      # builds the index
        lib._entries = _Loud(lib.entries)         # under the setter, as in test_entry_for

        entry, found, _ = _resolve_import_path(TANGO, lib, None, "Tanguera")

        self.assertIs(entry, tango)
        self.assertTrue(found)

    def test_an_exact_path_wins_over_a_case_folded_one(self):
        lower = TANGO.lower()
        lib = _library(lower, TANGO)
        entry, _, _ = _resolve_import_path(TANGO, lib, None, "Tanguera")
        self.assertEqual(str(entry.path), TANGO)

    def test_a_line_in_another_case_still_finds_the_track(self):
        lib = _library(TANGO)
        entry, found, _ = _resolve_import_path(TANGO.upper(), lib, None, "Tanguera")
        self.assertIs(entry, lib.entries[0])
        self.assertTrue(found)

    def test_a_file_whose_tags_fail_is_logged_and_kept_as_a_ghost(self):
        """A file that is there but can't be read still fills the slot, and the
        reason it came in as a ghost is in the debug log, not swallowed."""
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "Tanguera (TG 32).mp3"
            song.write_bytes(b"")
            lib = _library()
            with mock.patch.object(MusicLibrary, "make_external_entry",
                                   side_effect=RuntimeError("bad tags")), \
                    self.assertLogs("dancesport.m3u", "DEBUG") as logs:
                # Any cache: without one an outside file is never read at all.
                entry, found, _ = _resolve_import_path(str(song), lib, mock.Mock(),
                                                       "Tanguera")
        self.assertFalse(found)
        self.assertEqual(entry.title, "Tanguera")
        text = "\n".join(logs.output)
        self.assertIn(str(song), text)
        self.assertIn("bad tags", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
