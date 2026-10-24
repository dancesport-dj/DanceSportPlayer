#!/usr/bin/env python3
"""A file the scan cannot stat is never served from the whole-repo cache.

Run:  py -m unittest tests.planner.music.test_global_cache_unstatable -v

GlobalScanCache._mtime answers 0 when stat fails (a network drive that
dropped, a file locked mid-scan), and a row can be stored with mtime 0 too:
a put() whose stat failed, or a legacy JSON record without one. get()
compared 0 == 0 and handed that row back as unchanged.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gunstat_state_"))

from planner.music.scan_caches import GlobalScanCache
from tests.db_support import use_scratch_db


class UnstatableFileTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_gunstat_"))
        use_scratch_db(self, self.root / "scratch.db")
        self.cache = GlobalScanCache()

    def test_a_row_stored_without_an_mtime_is_not_fresh(self):
        gone = self.root / "offline" / "Atemlos (DF 30).mp3"
        self.cache.put(gone, {"title": "Atemlos"})
        self.assertIsNone(self.cache.get(gone))

    def test_a_readable_unchanged_file_is_still_served(self):
        song = self.root / "Atemlos (DF 30).mp3"
        song.write_bytes(b"x")
        self.cache.put(song, {"title": "Atemlos"})
        self.assertEqual(self.cache.get(song), {"title": "Atemlos"})


if __name__ == "__main__":
    unittest.main()
