"""Not a test of its own: test_suite_temp_cleanup runs it under pytest --cov.

It leaves a database to the garbage collector unclosed, as a thread's
connection in planner.music.db is when the thread ends.
"""
import gc
import sqlite3
import tempfile
import unittest
from pathlib import Path


class UnclosedDatabaseCase(unittest.TestCase):

    def test_a_connection_is_left_to_the_collector(self):
        conn = sqlite3.connect(Path(tempfile.mkdtemp(prefix="dp_unclosed_")) / "x.db")
        conn.execute("CREATE TABLE t (x)")
        conn.execute("SELECT x FROM t").fetchall()
        del conn
        gc.collect()
