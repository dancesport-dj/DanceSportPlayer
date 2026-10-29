"""AudioCache reads a title's analysis when it is first asked for, not at start.

Run:  py -m unittest tests.planner.music.test_audio_cache_lazy -v

The DB holds the analysis of the whole repository (~53k titles, ~100 MB of
vectors) and the start used to unpack all of it, 1.1 s of the start-up on
the loader thread, while the dance library asks for ~3.6k of them.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import planner.music.db as pdb
from planner.music.analysis import AUDIO_FEAT_DIM
from tests.db_support import use_scratch_db


class LazyFeaturesTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_lazy_feat_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        pack = pdb.AudioCache._pack_mfcc
        conn = pdb._db()
        for fp, bpm in (("fp1", 120.0), ("fp2", 96.0)):
            conn.execute(
                "INSERT INTO features (fp, bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov) "
                "VALUES (?,?,?,?,?,?,?)",
                (fp, bpm, 1500.0, 0.1, pack([0.5] * AUDIO_FEAT_DIM),
                 pack([0.1] * 20), pack([0.2] * 400)))
        conn.commit()
        self.song = self.dir / "a.mp3"
        self.song.write_bytes(b"x")

    def test_nothing_is_unpacked_at_start(self):
        self.assertEqual(pdb.AudioCache()._data, {})

    def test_a_title_is_read_on_first_use(self):
        cache = pdb.AudioCache()
        cache._fp[cache._key(self.song)] = "fp1"
        feat = cache.get(self.song, hash_if_missing=False)
        self.assertEqual(feat.bpm, 120.0)
        self.assertEqual(len(feat.mfcc), AUDIO_FEAT_DIM)
        self.assertEqual(set(cache._data), {"fp1"})

    def test_a_title_without_analysis_has_none(self):
        cache = pdb.AudioCache()
        cache._fp[cache._key(self.song)] = "fp9"
        self.assertIsNone(cache.get(self.song, hash_if_missing=False))
        self.assertEqual(cache._data, {})


if __name__ == "__main__":
    unittest.main()
