#!/usr/bin/env python3
"""Quitting tells every worker to stop before it waits for any of them.

Run:  py -m unittest tests.app.test_quit_cancel_all -v

`_stop_workers` cancelled one worker and waited up to 5 s for it before it
even told the next one, so several busy workers made the quit wait their
stops one after the other instead of side by side.
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QWidget

import dancesport_gui as dg


class _Busy(QThread):
    """A worker that reports running and logs what quit asks of it."""

    def __init__(self, parent, name, calls):
        super().__init__(parent)
        self._name, self._calls = name, calls

    def isRunning(self):
        return True

    def cancel(self):
        self._calls.append(("cancel", self._name))

    def wait(self, ms=0):
        self._calls.append(("wait", self._name))
        return True


class QuitCancelAllTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_worker_is_cancelled_before_the_first_wait(self):
        win = QWidget()
        self.addCleanup(win.deleteLater)
        calls = []
        _Busy(win, "a", calls)
        _Busy(win, "b", calls)

        dg.MainWindow._stop_workers(win)

        self.assertEqual([kind for kind, _ in calls],
                         ["cancel", "cancel", "wait", "wait"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
