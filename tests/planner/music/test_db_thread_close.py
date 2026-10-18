#!/usr/bin/env python3
"""A worker thread's database connection is closed when the thread ends.

Run:  py -m unittest tests.planner.music.test_db_thread_close -v

Every thread gets its own connection (planner.music.db._db). Left to the garbage
collector, a connection is closed late, with an "unclosed database"
ResourceWarning, and under pytest --cov the recorded warning kept the file
open until the end of the run.
"""
import sqlite3
import threading
import unittest

from tests.qt_test_support import qapp

from PySide6.QtCore import QThread

from planner.music import db as pdb


def _is_closed(conn: sqlite3.Connection) -> bool:
    try:
        conn.total_changes
    except sqlite3.ProgrammingError as exc:
        return "closed" in str(exc)
    return False


class ThreadConnectionCloseTest(unittest.TestCase):

    def test_a_python_thread_closes_its_connection_at_the_end(self):
        conns = []

        def work():
            conns.append(pdb._db())
            conns[0].execute("SELECT 1").fetchall()
        t = threading.Thread(target=work)
        t.start()
        t.join()
        self.assertTrue(_is_closed(conns[0]))

    def test_a_qthread_closes_its_connection_at_the_end(self):
        qapp()
        conns = []

        class Worker(QThread):
            def run(self):
                conns.append(pdb._db())
                conns[0].execute("SELECT 1").fetchall()
        w = Worker()
        w.start()
        self.assertTrue(w.wait(10000))
        self.assertTrue(_is_closed(conns[0]))

    def test_the_main_threads_connection_stays_open(self):
        conn = pdb._db()
        threading.Thread(target=lambda: pdb._db()).start()
        self.assertIs(pdb._db(), conn)
        self.assertFalse(_is_closed(conn))


if __name__ == "__main__":
    unittest.main()
