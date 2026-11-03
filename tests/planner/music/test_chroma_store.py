"""The Chromaprint store: one fingerprint per content fingerprint, kept in the DB.

Run:  py -m unittest tests.planner.music.test_chroma_store -v
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

import planner.music.db as pdb
from planner.music import db_upkeep as upkeep
from tests.db_support import use_scratch_db


class ChromaStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_chroma_store_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.song = self.dir / "a.mp3"
        self.song.write_bytes(b"x" * 5000)
        self.words = np.array([1, 2, 0xFFFFFFFF, 7], dtype=np.uint32)

    def test_a_track_without_fingerprint_has_none(self):
        self.assertIsNone(pdb.AudioCache().get_chroma(self.song))

    def test_put_then_get_roundtrips_words_and_duration(self):
        cache = pdb.AudioCache()
        cache.put_chroma(self.song, self.words, 215.0)
        got = cache.get_chroma(self.song)
        self.assertEqual(got.duration, 215.0)
        self.assertTrue(np.array_equal(got.words, self.words))

    def test_it_survives_a_new_cache(self):
        pdb.AudioCache().put_chroma(self.song, self.words, 215.0)
        self.assertIsNotNone(pdb.AudioCache().get_chroma(self.song))

    def test_keys_and_all(self):
        cache = pdb.AudioCache()
        cache.put_chroma(self.song, self.words, 215.0)
        fp = cache.fingerprint(self.song)
        self.assertEqual(cache.chroma_keys(), {fp})
        self.assertTrue(np.array_equal(cache.all_chromas()[fp], self.words))

    def test_the_row_follows_a_retag_and_a_reset(self):
        self.assertIn("chroma_fps", pdb._FP_TABLES)
        self.assertIn(("chroma_fps", ""), upkeep.RESET_GROUPS["analysis"])


if __name__ == "__main__":
    unittest.main()
