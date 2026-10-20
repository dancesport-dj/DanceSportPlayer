#!/usr/bin/env python3
"""🙈 Hidden folders: titles below a folder named in ⚙ Settings → 📁 Paths stay
out of the library.

Run:  py -m unittest tests.planner.music.test_hidden_folders -v

Marcel: "Wie können einzelne Ordner ausgeblendet werden?" The setting
`hidden_folders` (one folder per line) leaves them out of the favorites scan,
the 🔄 whole-repo scan and the whole library's load from the cache. A hidden
file is not a file gone: its cached row stays, so showing it again needs no scan.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_hidden_state_"))

import planner.models as models
import planner.music.library as plib
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary
from planner.music.scan_caches import GlobalScanCache
from tests.db_support import use_scratch_db


class HiddenPathTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(models.set_hidden_folders, [])

    def test_below_a_hidden_folder_is_hidden(self):
        models.set_hidden_folders([r"F:\my music\Party\\"])
        self.assertTrue(models.is_hidden_path(r"F:\my music\Party\a.mp3"))
        self.assertTrue(models.is_hidden_path(r"F:\my music\Party\x\b.mp3"))
        self.assertFalse(models.is_hidden_path(r"F:\my music\Party 2\a.mp3"))
        self.assertFalse(models.is_hidden_path(r"F:\my music\a.mp3"))

    @unittest.skipUnless(os.name == "nt", "Windows paths ignore case")
    def test_case_and_slashes_do_not_matter_on_windows(self):
        models.set_hidden_folders(["f:/My Music/party"])
        self.assertTrue(models.is_hidden_path(r"F:\my music\Party\a.mp3"))

    def test_nothing_hidden_hides_nothing(self):
        models.set_hidden_folders(["", "  "])
        self.assertFalse(models.is_hidden_path(r"F:\my music\a.mp3"))


class HiddenScanTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_hidden_"))
        use_scratch_db(self, self.root / "scratch.db")
        self.addCleanup(models.set_hidden_folders, [])
        self.shown = self.root / "Standard" / "Moon River (LW 29).mp3"
        self.hidden = self.root / "Party" / "Atemlos (DF 30).mp3"
        for song in (self.shown, self.hidden):
            song.parent.mkdir(parents=True)
            song.write_bytes(b"not really an mp3")

    def scan(self, whole_repo=False):
        lib = MusicLibrary()
        with mock.patch.object(plib, "_read_duration", lambda _p: 180), \
                mock.patch.object(plib, "_read_tags_once", lambda _p: (None, 180)):
            lib.scan(AudioCache(), music_dir=self.root, skip_special=False, learn=False,
                     analyze=False, interactive=False,
                     global_cache=GlobalScanCache() if whole_repo else None)
        return {e.path for e in lib.entries}

    def test_the_favorites_scan_leaves_it_out(self):
        models.set_hidden_folders([str(self.hidden.parent)])
        self.assertEqual(self.scan(), {self.shown})

    def test_the_whole_repo_scan_leaves_it_out_but_keeps_its_row(self):
        self.assertEqual(self.scan(whole_repo=True), {self.shown, self.hidden})
        models.set_hidden_folders([str(self.hidden.parent)])
        self.assertEqual(self.scan(whole_repo=True), {self.shown})
        self.assertIsNotNone(GlobalScanCache().get(self.hidden))

    def test_the_cache_load_leaves_it_out(self):
        self.scan(whole_repo=True)
        models.set_hidden_folders([str(self.hidden.parent)])
        lib = MusicLibrary()
        lib.load_from_global_cache(AudioCache(), GlobalScanCache())
        self.assertEqual({e.path for e in lib.entries}, {self.shown})


if __name__ == "__main__":
    unittest.main()
