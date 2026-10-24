#!/usr/bin/env python3
"""The Planner and the Player starting together both open the database.

Run:  py -m unittest tests.planner.test_db_init_two_processes -v

L24: each process runs the startup migration in one transaction, and every
run ends in a write (PRAGMA user_version), even on a database that needs
nothing new. A deferred BEGIN reads first and asks for the write lock only
then; under WAL, once the other process has committed in between, SQLite
answers 'database is locked' at once, without the busy wait. The second
window to start died on opening its own cache.
"""

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_db_two_procs_"))

import planner.music.db as pdb
from tests.db_support import use_scratch_db


class TwoProcessesStartTest(unittest.TestCase):

    def setUp(self):
        db_file = Path(tempfile.mkdtemp(prefix="dp_db_two_procs_")) / "scratch.db"
        use_scratch_db(self, db_file)
        pdb._db()                       # the first process migrated it long ago
        pdb._DB_LOCAL.conn.close()
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False     # this process starts now
        self.db_file = db_file

    def test_a_write_from_the_other_process_mid_migration_is_waited_for(self):
        errors = []

        def other_process_writes():
            conn = sqlite3.connect(str(self.db_file), timeout=5)
            try:
                conn.execute("INSERT INTO files (path) VALUES ('F:/music/a.mp3')")
                conn.commit()
            except sqlite3.Error as exc:
                errors.append(exc)
            finally:
                conn.close()

        real_read = pdb._read_and_drop_legacy

        def read_then_the_other_one_writes(conn):
            out = real_read(conn)
            writer = threading.Thread(target=other_process_writes)
            writer.start()
            writer.join(0.5)            # it commits now, or waits for our commit
            self.writer = writer
            return out

        with mock.patch.object(pdb, "_read_and_drop_legacy",
                               read_then_the_other_one_writes):
            conn = pdb._db()
        self.writer.join(5)
        self.assertEqual(errors, [])
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0],
                         pdb._SCHEMA_VERSION)
        self.assertEqual(conn.execute("SELECT count(*) FROM files").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
