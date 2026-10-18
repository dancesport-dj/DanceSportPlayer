#!/usr/bin/env python3
"""The migrations of one database file never count for another.

Run:  py -m unittest tests.planner.test_db_init_per_file -v

`_DB_INITIALIZED` was one flag for the process. A thread still migrating the
database a test had just moved away from set it after the next test had reset
it for its own scratch file, and that test's `_db()` then skipped the
migrations: "no such table: tag_edits" on its first insert.
"""

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import planner.music.db as pdb
from tests.db_support import use_scratch_db


class InitPerFileTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_db_init_"))

    def _point_at(self, name: str) -> Path:
        return use_scratch_db(self, self.dir / name)

    def test_a_late_migration_of_the_old_file_does_not_cover_the_new_one(self):
        old = self._point_at("old.db")
        opened, go, done = threading.Event(), threading.Event(), threading.Event()

        def straggler():
            # A worker of the earlier test inside _db(): connected to the old
            # file, it reaches the rest of _db() only after the swap.
            conn = sqlite3.connect(str(old), isolation_level=None)
            opened.set()
            go.wait(5)
            try:
                pdb._DB_LOCAL.conn = conn
                pdb._init_db(conn)
            finally:
                conn.close()
                done.set()

        t = threading.Thread(target=straggler)
        t.start()
        self.assertTrue(opened.wait(5))
        self._point_at("new.db")      # the next test's setUp
        go.set()
        self.assertTrue(done.wait(10))
        t.join()

        conn = pdb._db()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("tag_edits", tables)


if __name__ == "__main__":
    unittest.main(verbosity=2)
