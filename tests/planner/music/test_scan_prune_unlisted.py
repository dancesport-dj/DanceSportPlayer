#!/usr/bin/env python3
"""A folder the scan could not list is not a folder gone.

Run:  py -m unittest tests.planner.music.test_scan_prune_unlisted -v

The walk swallows an OSError from a folder (a share that dropped, a permission
change) and carries on, so none of that folder's files reached `seen`, and the
whole-repo cache then deleted every row below it: a full re-read of the
subtree on the next scan. A walk that lost a folder prunes nothing.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_unlisted_state_"))

import planner.music.library as plib
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary, library_mp3s
from planner.music.scan_caches import GlobalScanCache
from tests.db_support import use_scratch_db


class UnlistedFolderTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_unlisted_"))
        use_scratch_db(self, self.root / "scratch.db")
        self.kept = self.root / "Latin" / "Rumba (RU 25).mp3"
        self.lost = self.root / "Standard" / "Moon River (LW 29).mp3"
        for song in (self.kept, self.lost):
            song.parent.mkdir(parents=True)
            song.write_bytes(b"not really an mp3")
        self.real_scandir = os.scandir

    def scan(self):
        lib = MusicLibrary()
        with mock.patch.object(plib, "read_duration", lambda _p: 180), \
                mock.patch.object(plib, "read_tags_once", lambda _p: (None, 180)):
            lib.scan(AudioCache(), music_dir=self.root, skip_special=False, learn=False,
                     analyze=False, interactive=False, global_cache=GlobalScanCache())
        return {e.path for e in lib.entries}

    def cached(self, song):
        return str(song) in GlobalScanCache()._data

    def refuse(self, folder):
        def scandir(path):
            if str(path) == str(folder):
                raise PermissionError("share went away")
            return self.real_scandir(path)
        return mock.patch("planner.music.library.os.scandir", scandir)

    def test_the_walk_names_the_folder_it_could_not_list(self):
        unlisted = []
        with self.refuse(self.lost.parent):
            found = library_mp3s(self.root, unlisted=unlisted)
        self.assertEqual([p for p, _ in found], [self.kept])
        self.assertEqual(unlisted, [str(self.lost.parent)])

    def test_a_clean_walk_names_nothing(self):
        unlisted = []
        library_mp3s(self.root, unlisted=unlisted)
        self.assertEqual(unlisted, [])

    def test_a_folder_that_could_not_be_listed_keeps_its_cached_rows(self):
        self.assertEqual(self.scan(), {self.kept, self.lost})
        self.assertTrue(self.cached(self.lost))
        with self.refuse(self.lost.parent):
            self.assertEqual(self.scan(), {self.kept})
        self.assertTrue(self.cached(self.lost))

    def test_a_file_really_gone_is_still_pruned(self):
        """The control: a clean walk that does not see a file drops its row."""
        self.scan()
        self.lost.unlink()
        self.scan()
        self.assertFalse(self.cached(self.lost))
        self.assertTrue(self.cached(self.kept))


if __name__ == "__main__":
    unittest.main()
