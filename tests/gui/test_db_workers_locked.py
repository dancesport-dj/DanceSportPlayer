"""🧹 A database cleanup that meets a running scan says what to do about it.

Run:  py -m unittest tests.gui.test_db_workers_locked -v

Maintenance takes the write lock with BEGIN IMMEDIATE. While a library scan
or an analysis is writing, that waits out the busy timeout and then fails
with "database is locked", and the user was shown just that. The workers now
add what the lock means and that a second try after the scan will work.
"""
import sqlite3
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication

from gui import workers

_app = QApplication.instance() or QApplication([])


class LockedDatabaseTest(unittest.TestCase):

    def errors_of(self, worker, target, exc):
        got = []
        worker.error.connect(got.append)
        with mock.patch.object(workers, target, side_effect=exc):
            worker.run()
        return got

    def test_maintenance_names_the_scan_that_holds_the_lock(self):
        got = self.errors_of(workers.DbMaintenanceWorker(), "db_maintenance",
                             sqlite3.OperationalError("database is locked"))
        self.assertEqual(len(got), 1)
        self.assertIn("database is locked", got[0])
        self.assertIn("Let it finish, then try again", got[0])

    def test_reset_names_it_too(self):
        got = self.errors_of(workers.DbResetWorker({"features"}), "reset_database",
                             sqlite3.OperationalError("database is locked"))
        self.assertIn("Let it finish, then try again", got[0])

    def test_any_other_error_is_passed_on_as_it_is(self):
        got = self.errors_of(workers.DbMaintenanceWorker(), "db_maintenance",
                             OSError("disk full"))
        self.assertEqual(got, ["disk full"])


if __name__ == "__main__":
    unittest.main()
