#!/usr/bin/env python3
"""The whole library loads from the cache without a stat per file.

Run:  py -m unittest tests.planner.music.test_global_load_listing -v

Marcel: "loading from repositoy cache is still really slow". Timed on a copy
of his database (54 368 titles): 4.6 s of the 14.5 s were one stat per file
on F:, only for its mtime, the key to the recorded fingerprint. The 🔄 walk
takes the same mtime from the folder listing (a Windows directory entry
carries it); the cache load now lists each folder once and does the same.
A file changed since its fingerprint was recorded must still come without
features, exactly as with the stat.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
from planner.music.analysis import AUDIO_FEAT_DIM
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class _GlobalCache:
    def __init__(self, paths):
        self._paths = paths

    def all_entries(self):
        return [(str(p), {"title": p.stem, "dance": "LW"}) for p in self._paths]

    def put(self, path, data):
        pass


class ListingTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_global_listing_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        pack = pdb.AudioCache._pack_mfcc
        conn = pdb._db()
        self.songs = []
        for i, folder in enumerate(("Album A", "Album B")):
            song = self.dir / "repo" / folder / f"Moon River {i} (LW 29).mp3"
            song.parent.mkdir(parents=True)
            song.write_bytes(b"x")
            self.songs.append(song)
            conn.execute(
                "INSERT INTO features (fp, bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"fp{i}", 29.0 + i, 1500.0, 0.1, pack([0.5] * AUDIO_FEAT_DIM),
                 pack([0.1] * 20), pack([0.2] * 400)))
        conn.commit()
        self.cache = pdb.AudioCache()
        for i, song in enumerate(self.songs):
            self.cache._fp[self.cache._key(song)] = f"fp{i}"
            self.cache._feat_fps.add(f"fp{i}")

    def load(self, paths=None):
        lib = MusicLibrary()
        lib.load_from_global_cache(self.cache, _GlobalCache(paths or self.songs))
        return {e.path: e.features for e in lib.entries}

    def test_features_come_without_a_stat_per_file(self):
        real = Path.stat
        stats = []

        def counted(p, *a, **kw):
            stats.append(p)
            return real(p, *a, **kw)

        with mock.patch.object(Path, "stat", counted):
            got = self.load()
        self.assertEqual([got[s].bpm for s in self.songs], [29.0, 30.0])
        self.assertEqual(stats, [])

    def test_the_features_come_in_one_read(self):
        """One SELECT per title was 1.2 s of the 54 368-title load; one pass
        over the table 0.5 s."""
        reads = []
        pdb._db().set_trace_callback(
            lambda sql: reads.append(sql) if "FROM features" in sql else None)
        self.addCleanup(pdb._db().set_trace_callback, None)
        got = self.load()
        self.assertEqual([got[s].bpm for s in self.songs], [29.0, 30.0])
        self.assertEqual(len(reads), 1, reads)

    def test_a_short_stale_vector_still_comes_as_none(self):
        pdb._db().execute("UPDATE features SET mfcc = ? WHERE fp = 'fp1'",
                          (pdb.AudioCache._pack_mfcc([0.5] * 60),))
        got = self.load()
        self.assertEqual(got[self.songs[0]].bpm, 29.0)
        self.assertIsNone(got[self.songs[1]])

    def test_a_file_changed_since_its_fingerprint_comes_without_features(self):
        st = self.songs[1].stat()
        os.utime(self.songs[1], (st.st_atime, st.st_mtime + 60))
        got = self.load()
        self.assertEqual(got[self.songs[0]].bpm, 29.0)
        self.assertIsNone(got[self.songs[1]])

    def test_a_folder_gone_from_disk_is_no_error(self):
        gone = self.dir / "repo" / "Unplugged" / "Tango (TG 32).mp3"
        got = self.load(self.songs + [gone])
        self.assertIsNone(got[gone])
        self.assertEqual(got[self.songs[0]].bpm, 29.0)


if __name__ == "__main__":
    unittest.main()
