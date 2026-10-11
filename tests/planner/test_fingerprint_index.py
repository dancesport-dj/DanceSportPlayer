#!/usr/bin/env python3
"""Looking a content fingerprint up in `fingerprints` uses an index.

Run:  py -m unittest tests.planner.test_fingerprint_index -v

`fingerprints` is keyed by file_id, but the joins and dedup lookups ask it by
`fp` (every file a byte-identical copy shares, every orphan check), and without
an index each of those is a full scan of ~54k rows. A database built before the
index gets it on the next start.
"""

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fp_index_"))

import planner.db as pdb


class FingerprintIndexTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_fp_index_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)

    def _restore(self):
        conn = getattr(pdb._DB_LOCAL, "conn", None)
        if conn is not None:
            conn.close()
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _plan(self, conn):
        rows = conn.execute("EXPLAIN QUERY PLAN "
                            "SELECT file_id FROM fingerprints WHERE fp = ?", ("abc",))
        return " ".join(r[-1] for r in rows)

    def test_a_new_database_looks_fingerprints_up_by_index(self):
        self.assertIn("idx_fingerprints_fp", self._plan(pdb._db()))

    def test_a_database_from_before_gets_the_index(self):
        raw = sqlite3.connect(str(pdb.AUDIO_DB_FILE))
        raw.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL)")
        raw.execute("CREATE TABLE fingerprints ("
                    "file_id INTEGER PRIMARY KEY REFERENCES files(id), mtime INTEGER, fp TEXT)")
        raw.execute(f"PRAGMA user_version = {pdb._SCHEMA_VERSION}")
        raw.commit()
        raw.close()

        self.assertIn("idx_fingerprints_fp", self._plan(pdb._db()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
