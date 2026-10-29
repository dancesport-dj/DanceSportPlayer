#!/usr/bin/env python3
"""A file dated before 1970 keeps its fingerprint from one start to the next.

Run:  py -m unittest tests.planner.music.test_fingerprint_negative_mtime -v

NTFS allows dates before 1970, so st_mtime can be negative. The cache key is
"path::mtime"; loading it back read the mtime with lstrip('-').isdigit(),
but every write used mt.isdigit() and stored a negative one as 0. The next
start rebuilt the key as "path::0", the live key said "path::-5", and the
file was hashed again on every launch.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_negmt_state_"))

import planner.music.db as pdb
from planner.music.db import AudioCache
from tests.db_support import use_scratch_db


class NegativeMtimeTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_negmt_"))
        use_scratch_db(self, self.dir / "scratch.db")
        self.song = self.dir / "Old Waltz.mp3"
        self.song.write_bytes(b"not really an mp3")

    def test_the_next_start_finds_the_fingerprint_again(self):
        cache = AudioCache()
        cache.listed_mtimes[str(self.song)] = -5
        fp = cache.fingerprint(self.song)
        self.assertIsNotNone(fp)
        cache.save()

        again = AudioCache()
        again.listed_mtimes[str(self.song)] = -5
        with mock.patch.object(pdb, "fingerprints",
                               side_effect=AssertionError("hashed again")):
            self.assertEqual(again.fingerprint(self.song), fp)


if __name__ == "__main__":
    unittest.main()
