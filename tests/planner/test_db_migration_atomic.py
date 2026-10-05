#!/usr/bin/env python3
"""A database migration that dies half-way leaves the old tables as they were.

Run:  py -m unittest tests.planner.test_db_migration_atomic -v

The connection is in autocommit mode, so every step of the startup migration
committed on its own: the legacy tables were DROPPED first and their rows held
only in memory until the next step put them back, and scan_meta was dropped
before it was re-filled. A crash, a kill or a full disk in between left the
rows gone for good. The whole migration now runs as one transaction.
"""

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_db_migrate_"))

import planner.db as pdb  # noqa: E402


class MigrationAtomicTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_db_migrate_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        self.addCleanup(self._restore)
        self._fresh()

    def _fresh(self):
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

    def _close(self):
        conn = getattr(pdb._DB_LOCAL, "conn", None)
        if conn is not None:
            conn.close()

    def _restore(self):
        self._close()
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _raw(self):
        conn = sqlite3.connect(str(pdb.AUDIO_DB_FILE))
        self.addCleanup(conn.close)
        return conn

    def _cols(self, table):
        return [r[1] for r in self._raw().execute(f"PRAGMA table_info({table})")]

    def test_legacy_fingerprints_survive_a_crash_before_they_are_reinserted(self):
        raw = self._raw()
        raw.execute("CREATE TABLE fingerprints (key TEXT PRIMARY KEY, fp TEXT)")
        raw.execute("INSERT INTO fingerprints VALUES (?, ?)",
                    (r"F:\music\Grünwald.mp3::1700000000", "abc123"))
        raw.commit()
        raw.close()

        with mock.patch.object(pdb, "_insert_legacy",
                               side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                pdb._db()
        self._close()

        self.assertIn("key", self._cols("fingerprints"))
        rows = self._raw().execute("SELECT key, fp FROM fingerprints").fetchall()
        self.assertEqual(rows, [(r"F:\music\Grünwald.mp3::1700000000", "abc123")])

        # and the next start migrates them for real
        self._fresh()
        conn = pdb._db()
        self.assertEqual(conn.execute("SELECT fp FROM fingerprints").fetchall(),
                         [("abc123",)])

    def test_scan_meta_survives_a_crash_after_it_was_rebuilt(self):
        raw = self._raw()
        raw.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT UNIQUE)")
        raw.execute("CREATE TABLE fingerprints (file_id INTEGER PRIMARY KEY, "
                    "mtime INTEGER, fp TEXT)")
        raw.execute(f"CREATE TABLE scan_meta (file_id INTEGER PRIMARY KEY, "
                    f"size INTEGER, {pdb._META_COLS_SQL})")
        raw.execute("INSERT INTO files VALUES (1, ?)", (r"F:\music\a.mp3",))
        raw.execute("INSERT INTO fingerprints VALUES (1, 0, 'abc123')")
        raw.execute("INSERT INTO scan_meta (file_id, size) VALUES (1, 4096)")
        raw.execute("PRAGMA user_version = 2")
        raw.commit()
        raw.close()

        with mock.patch.object(pdb, "_migrate_features_gauss",
                               side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                pdb._db()
        self._close()

        self.assertIn("file_id", self._cols("scan_meta"))
        self.assertEqual(
            self._raw().execute("SELECT file_id, size FROM scan_meta").fetchall(),
            [(1, 4096)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
