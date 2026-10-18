"""The scans cut a file's folders out of its path string.

Run:  py -m unittest tests.planner.test_scan_folder_parts -v

The library scan asked pathlib for each file's folders below the library
twice (excluded folders, then the special skip): 7.7k `relative_to` calls,
0.5 s for the 3.6k-title library; the playlist learning another 4.2k, 0.2 s.
Every path comes from a walk of its root, so it starts with the root's string
and the folders are a slice of it.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
from planner.config import folders_below
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class FoldersBelowTest(unittest.TestCase):
    def check(self, root: str, path: str):
        self.assertEqual(folders_below(path, root),
                         list(Path(path).relative_to(Path(root)).parts[:-1]), (root, path))

    def test_it_matches_relative_to(self):
        sep = os.sep
        self.check(f"C:{sep}music", f"C:{sep}music{sep}a.mp3")
        self.check(f"C:{sep}music", f"C:{sep}music{sep}standardcd{sep}a.mp3")
        self.check(f"C:{sep}music", f"C:{sep}music{sep}special{sep}Hymnen{sep}a.mp3")

    def test_a_root_with_a_trailing_separator(self):
        sep = os.sep
        self.check(f"F:{sep}", f"F:{sep}a.mp3")
        self.check(f"F:{sep}", f"F:{sep}sox{sep}a.mp3")
        self.check(f"C:{sep}music{sep}", f"C:{sep}music{sep}lateincd{sep}a.mp3")

    def test_a_path_outside_the_root_is_none(self):
        sep = os.sep
        self.assertIsNone(folders_below(f"D:{sep}lists{sep}a.m3u", f"C:{sep}music"))
        # a sibling whose name only starts like the root
        self.assertIsNone(folders_below(f"C:{sep}music2{sep}a.mp3", f"C:{sep}music"))


class ScanFolderPartsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_folder_parts_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music"
        for rel in ("standardcd/Waltz LW 29.mp3", "special/Hymnen/Anthem.mp3",
                    "endrunden/Final LW 29.mp3", "sox/raw LW 29.mp3"):
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"\x00" * 64)

    def test_the_scan_asks_pathlib_for_no_folders(self):
        orig = Path.relative_to
        calls = []

        def relative_to(path, *a, **kw):
            if path.suffix.lower() == ".mp3":
                calls.append(path.name)
            return orig(path, *a, **kw)

        lib = MusicLibrary()
        with mock.patch.object(Path, "relative_to", relative_to):
            lib.scan(pdb.AudioCache(), music_dir=self.root, learn=False, interactive=False)
        self.assertEqual(calls, [])
        # sox is hard-excluded, endrunden skipped, special/Hymnen loads as a category
        self.assertEqual(sorted(e.path.name for e in lib.entries),
                         ["Anthem.mp3", "Waltz LW 29.mp3"])


if __name__ == "__main__":
    unittest.main()
