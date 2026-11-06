"""The Chromaprint store: one fingerprint per content fingerprint, kept in the DB.

Run:  py -m unittest tests.planner.music.test_chroma_store -v
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

import planner.music.db as pdb
from planner.music import chroma_match
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

    def test_the_count_is_the_number_of_keys_without_reading_them(self):
        cache = pdb.AudioCache()
        self.assertEqual(cache.chroma_count(), 0)
        cache.put_chroma(self.song, self.words, 215.0)
        other = self.dir / "b.mp3"
        other.write_bytes(b"y" * 5000)
        cache.put_chroma(other, self.words, 100.0)
        self.assertEqual(cache.chroma_count(), len(cache.chroma_keys()))
        self.assertEqual(cache.chroma_count(), 2)

    def test_the_row_follows_a_retag_and_a_reset(self):
        self.assertIn("chroma_fps", pdb._FP_TABLES)
        self.assertIn(("chroma_fps", ""), upkeep.RESET_GROUPS["analysis"])

    def damage(self, cache, blob=b"123456"):
        """The stored words cut off mid-word, as a half-written row leaves them."""
        cache.put_chroma(self.song, self.words, 215.0)
        pdb._db().execute("UPDATE chroma_fps SET words = ?", (blob,))

    def test_a_damaged_blob_reads_as_no_fingerprint(self):
        cache = pdb.AudioCache()
        self.damage(cache)
        self.assertIsNone(cache.get_chroma(self.song))

    def test_a_damaged_blob_does_not_hide_the_good_rows(self):
        cache = pdb.AudioCache()
        other = self.dir / "b.mp3"
        other.write_bytes(b"y" * 5000)
        cache.put_chroma(other, self.words, 100.0)
        self.damage(cache)
        pdb._db().execute("UPDATE chroma_fps SET words = ? WHERE fp = ?",
                          (chroma_match.pack(self.words), cache.fingerprint(other)))
        everything = cache.all_chromas()
        self.assertEqual(list(everything), [cache.fingerprint(other)])


if __name__ == "__main__":
    unittest.main()
