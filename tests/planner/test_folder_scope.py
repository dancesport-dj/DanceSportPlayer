#!/usr/bin/env python3
"""Which library folders ⚡ Generate may draw from.

Run:  py -m unittest tests.planner.test_folder_scope -v

Tier 4 #15: the Favorites library is one folder with sub-folders, and the
sub-folders do not all hold what a competition is drawn from. A folder is
chosen for the titles directly in it, so "the main folder, not vlt" and
"only vlt/vlt" are both a pick.
"""

import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.music.folder_scope import entries_in_folders, library_folders

ROOT = "C:/fav"


def _entry(rel):
    return MusicEntry(path=Path(f"{ROOT}/{rel}"), title=rel, dance="SA", bpm=51)


ENTRIES = [_entry("a.mp3"), _entry("b.mp3"),
           _entry("vlt/c.mp3"),
           _entry("vlt/vlt/d.mp3"), _entry("vlt/vlt/e.mp3")]


class LibraryFoldersTest(unittest.TestCase):

    def test_every_folder_with_titles_and_how_many(self):
        self.assertEqual(library_folders(ENTRIES, ROOT),
                         [("", 2), ("vlt", 1), ("vlt/vlt", 2)])

    def test_a_folder_with_no_titles_of_its_own_is_not_listed(self):
        entries = [_entry("x/y/z.mp3")]
        self.assertEqual(library_folders(entries, ROOT), [("x/y", 1)])

    def test_a_file_outside_the_library_is_not_counted(self):
        entries = [_entry("a.mp3"),
                   MusicEntry(path=Path("D:/elsewhere/z.mp3"), title="z", dance="SA", bpm=51)]
        self.assertEqual(library_folders(entries, ROOT), [("", 1)])
        self.assertEqual(entries_in_folders(entries, ROOT, [""]), [entries[0]])


class EntriesInFoldersTest(unittest.TestCase):

    @staticmethod
    def _titles(folders):
        return [e.title for e in entries_in_folders(ENTRIES, ROOT, folders)]

    def test_the_main_folder_alone_leaves_the_sub_folders_out(self):
        self.assertEqual(self._titles([""]), ["a.mp3", "b.mp3"])

    def test_a_sub_sub_folder_alone(self):
        self.assertEqual(self._titles(["vlt/vlt"]),
                         ["vlt/vlt/d.mp3", "vlt/vlt/e.mp3"])

    def test_several_folders_add_up(self):
        self.assertEqual(self._titles(["", "vlt"]),
                         ["a.mp3", "b.mp3", "vlt/c.mp3"])

    def test_letter_case_and_separators_do_not_matter(self):
        entries = [MusicEntry(path=Path(r"C:\FAV\Vlt\c.mp3"), title="c",
                              dance="SA", bpm=51)]
        got = entries_in_folders(entries, ROOT, ["vlt"])
        self.assertEqual([e.title for e in got], ["c"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
