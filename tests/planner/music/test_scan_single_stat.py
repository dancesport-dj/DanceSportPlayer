"""The library scan takes each file's date from the folder listing.

Run:  py -m unittest tests.planner.music.test_scan_single_stat -v

The fingerprint cache is keyed by path + modification time, and the scan
asked the disk for that time twice per file (scan metadata, then the audio
features): 7.3k stat calls, 0.74 s for the 3.6k-title library. The folder
walk already holds the time, so a scan over known files stats no MP3 at all.
(A file seen for the first time is still stat'ed once while it is hashed: it
is read then anyway.)
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class ScanSingleStatTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_single_stat_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music"
        for name in ("Waltz LW 29.mp3", "Tango TG 32.mp3", "Rumba RB 25.mp3"):
            (self.root / "standardcd").mkdir(parents=True, exist_ok=True)
            (self.root / "standardcd" / name).write_bytes(b"\x00" * 64)

    def scan(self, cache):
        lib = MusicLibrary()
        lib.scan(cache, music_dir=self.root, learn=False, interactive=False)
        return lib

    def test_no_mp3_is_stated_after_the_listing(self):
        self.scan(pdb.AudioCache())   # first run: the files get hashed
        cache = pdb.AudioCache()      # the next start
        orig = Path.stat
        stated = []

        def stat(path, *a, **kw):
            if path.suffix.lower() == ".mp3":
                stated.append(path.name)
            return orig(path, *a, **kw)

        with mock.patch.object(Path, "stat", stat):
            lib = self.scan(cache)
        self.assertEqual(len(lib.entries), 3)
        self.assertEqual(stated, [])

    def test_the_cache_key_is_the_one_a_stat_would_give(self):
        cache = pdb.AudioCache()
        self.scan(cache)
        for mp3 in self.root.rglob("*.mp3"):
            self.assertIsNotNone(cache._fp.get(f"{mp3}::{int(mp3.stat().st_mtime)}"), mp3)

    def test_after_the_scan_a_file_is_stated_again(self):
        """The listed times serve the scan only: a file the app re-tags later
        in the session must be seen with its new time."""
        cache = pdb.AudioCache()
        self.scan(cache)
        mp3 = next(self.root.rglob("*.mp3"))
        with mock.patch.object(Path, "stat", wraps=mp3.stat) as stat:
            cache.fingerprint(mp3)
        self.assertTrue(stat.called)


if __name__ == "__main__":
    unittest.main()
