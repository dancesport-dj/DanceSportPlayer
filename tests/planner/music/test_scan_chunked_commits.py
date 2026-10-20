"""The library scan commits its cache rows in chunks, not one per row.

Run:  py -m unittest tests.planner.music.test_scan_chunked_commits -v

The audio DB connection is autocommit, so a cold scan paid a commit for every
INSERT: fingerprint, audio fingerprint, file id and scan row, about eight per
file (19k statements for 2.4k files). One transaction around the whole scan
would hold the write lock for minutes, longer than the 10 s the audio worker
waits for it. So the scan commits every few hundred files, and whatever it
wrote is committed when it is cancelled or fails.
"""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
from planner.music.library import MusicLibrary, ScanCancelled
from tests.db_support import use_scratch_db

_FILES = 29


class ScanChunkedCommitsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_chunked_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.db_path = use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music" / "standardcd"
        self.root.mkdir(parents=True)
        for i in range(_FILES):
            (self.root / f"Waltz {i} LW 29.mp3").write_bytes(bytes([i]) * 64)
        self.statements = []
        pdb._db().set_trace_callback(self.statements.append)
        patcher = mock.patch.object(pdb, "_COMMIT_EVERY", 10)
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, **kw):
        MusicLibrary().scan(pdb.AudioCache(), music_dir=self.root.parent,
                            learn=False, interactive=False, **kw)

    def rows_seen_by_another_connection(self):
        other = sqlite3.connect(str(self.db_path))
        try:
            return other.execute("SELECT COUNT(*) FROM scan_meta").fetchone()[0]
        finally:
            other.close()

    def test_writes_run_in_a_few_transactions(self):
        self.scan()
        in_txn = False
        commits = 0
        for sql in self.statements:
            word = sql.split(None, 1)[0].upper()
            if word == "BEGIN":
                in_txn = True
            elif word == "COMMIT":
                in_txn = False
                commits += 1
            elif word in ("INSERT", "UPDATE", "DELETE"):
                self.assertTrue(in_txn, f"written outside a transaction: {sql}")
        # 29 files in chunks of 10: after file 10, after file 20, and at the end.
        self.assertEqual(commits, 3)
        self.assertEqual(self.rows_seen_by_another_connection(), _FILES)

    def test_a_cancelled_scan_keeps_its_rows(self):
        # Polled every 25 files: it stops before the 25th.
        with self.assertRaises(ScanCancelled):
            self.scan(should_cancel=lambda: True)
        self.assertFalse(pdb._db().in_transaction)
        self.assertEqual(self.rows_seen_by_another_connection(), 24)

    def test_a_failed_scan_keeps_its_rows(self):
        orig = MusicLibrary._make_entry
        made = []

        def make_entry(lib, path, scan_cache, *rest):
            if len(made) == 5:
                raise RuntimeError("disk gone")
            made.append(path)
            return orig(lib, path, scan_cache, *rest)

        with mock.patch.object(MusicLibrary, "_make_entry", make_entry):
            with self.assertRaises(RuntimeError):
                self.scan()
        self.assertFalse(pdb._db().in_transaction)
        self.assertEqual(self.rows_seen_by_another_connection(), 5)


if __name__ == "__main__":
    unittest.main()
