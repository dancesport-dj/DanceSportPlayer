#!/usr/bin/env python3
"""🔝 The true peak is stored beside the loudness, and a library measured
before it is measured once more.

Run:  py -m unittest tests.planner.music.test_loudness_tp -v

The gain cap needs each track's true peak, which the 📊 loudness pass now
reads in the same ffmpeg run. It lives in the `loudness` table's own `tp`
column: content-addressed like the LUFS, carried along by a re-tag, and NULL
on every row measured before — which is what puts those tracks back on the
loudness pass's list.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_lufs_tp_"))

from planner.music.db import AudioCache, _db
from tests.db_support import use_scratch_db


def _track(folder: Path, name: str, payload: bytes) -> Path:
    p = folder / name
    p.write_bytes(payload * 4096)
    return p


class TruePeakStoreTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_lufs_tp_f_"))
        use_scratch_db(self, self.dir / "audio.db")
        self.cache = AudioCache()
        self.track = _track(self.dir, "a.mp3", self.id().encode())

    def test_a_measurement_keeps_its_true_peak(self):
        self.cache.put_lufs(self.track, -9.5, -0.3)
        self.assertEqual(self.cache.get_lufs(self.track), -9.5)
        self.assertEqual(self.cache.get_tp(self.track), -0.3)

    def test_it_is_read_back_from_the_database(self):
        self.cache.put_lufs(self.track, -9.5, -0.3)
        self.assertEqual(AudioCache().get_tp(self.track), -0.3)

    def test_a_measurement_without_one_has_none(self):
        self.cache.put_lufs(self.track, -9.5)
        self.assertIsNone(self.cache.get_tp(self.track))
        self.assertIsNone(AudioCache().get_tp(self.track))

    def test_a_new_measurement_without_one_drops_the_old(self):
        self.cache.put_lufs(self.track, -9.5, -0.3)
        self.cache.put_lufs(self.track, -9.0)
        self.assertIsNone(self.cache.get_tp(self.track))


class OldDatabaseTest(unittest.TestCase):
    """A `loudness` table from before the column: added, rows kept, tp NULL."""

    def test_the_column_is_added_and_the_lufs_kept(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_lufs_tp_old_"))
        path = folder / "audio.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE loudness (fp TEXT PRIMARY KEY, lufs REAL)")
        conn.execute("INSERT INTO loudness VALUES ('abc', -11.0)")
        conn.commit()
        conn.close()
        use_scratch_db(self, path)
        cols = [r[1] for r in _db().execute("PRAGMA table_info(loudness)")]
        self.assertIn("tp", cols)
        self.assertEqual(_db().execute(
            "SELECT lufs, tp FROM loudness WHERE fp = 'abc'").fetchone(),
            (-11.0, None))


class LoudnessPassTest(unittest.TestCase):
    """📊 The library pass measures a track again until its peak is known."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_lufs_tp_p_"))
        use_scratch_db(self, self.dir / "audio.db")
        self.cache = AudioCache()

    def test_a_track_without_a_true_peak_is_still_to_do(self):
        from gui.workers import LoudnessAnalyzer
        old = _track(self.dir, "old.mp3", b"old")
        done = _track(self.dir, "done.mp3", b"done")
        new = _track(self.dir, "new.mp3", b"new")
        self.cache.put_lufs(old, -10.0)
        self.cache.put_lufs(done, -10.0, -1.5)
        todo = LoudnessAnalyzer(self.cache, [old, done, new], "ffmpeg").todo()
        self.assertEqual(todo, [old, new])

    def test_the_pass_stores_both_numbers(self):
        from gui.workers import LoudnessAnalyzer
        track = _track(self.dir, "t.mp3", b"t")
        LoudnessAnalyzer(self.cache, [track], "ffmpeg").store(track, (-8.0, 0.4))
        self.assertEqual(self.cache.get_lufs(track), -8.0)
        self.assertEqual(self.cache.get_tp(track), 0.4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
