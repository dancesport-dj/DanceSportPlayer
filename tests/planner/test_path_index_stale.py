#!/usr/bin/env python3
"""The path → entry index follows a new entry list, whatever its length.

Run:  py -m unittest tests.planner.test_path_index_stale -v

`_path_index` rebuilt only when `len(entries)` changed, so a list replaced by
one of the same length (`load_from_global_cache` starts from a fresh list) kept
answering with the old entries: a renamed track was not found under its new
path and still found under the old one.
"""

import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary

ROOT = Path(r"C:\music\tanzcds\standardcd\TG")


def _entry(name: str) -> MusicEntry:
    return MusicEntry(path=ROOT / f"{name}.mp3", title=name, dance="TG")


class PathIndexStaleTest(unittest.TestCase):

    def test_a_replaced_list_of_the_same_length_is_indexed_anew(self):
        lib = MusicLibrary()
        old, new = _entry("Tanguera (TG 32)"), _entry("Tanguera - Remaster (TG 32)")
        lib.entries = [old]
        self.assertIs(lib.entry_for(old.path), old)

        lib.entries = [new]

        self.assertIs(lib.entry_for(new.path), new)
        self.assertIsNone(lib.entry_for(old.path))

    def test_a_restricted_view_indexes_only_its_subset(self):
        lib = MusicLibrary()
        a, b = _entry("Sway (TG 33)"), _entry("Tanguera (TG 32)")
        lib.entries = [a, b]
        self.assertIs(lib.entry_for(b.path), b)

        view = lib.restricted_to([a])

        self.assertIs(view.entry_for(a.path), a)
        self.assertIsNone(view.entry_for(b.path))
        self.assertIs(lib.entry_for(b.path), b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
