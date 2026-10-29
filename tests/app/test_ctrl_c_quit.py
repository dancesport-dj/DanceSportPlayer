#!/usr/bin/env python3
"""Ctrl+C in the console the app was started from closes it like ✕.

Run:  py -m unittest tests.app.test_ctrl_c_quit -v

Python's own SIGINT handler raises KeyboardInterrupt in whatever Python
code runs next — under Qt that is a native event filter or a slot, where
PySide only prints it: the window stayed open, and the traceback in
crash.log made the next start report a crash.
"""

import os
import signal
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ctrlc_"))

from PySide6.QtWidgets import QApplication

import dancesport_gui as dg


class CtrlCTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        before = signal.getsignal(signal.SIGINT)
        self.addCleanup(signal.signal, signal.SIGINT, before)

    def test_ctrl_c_closes_the_window_from_the_event_loop(self):
        window = mock.Mock()
        dg._quit_on_ctrl_c(window)
        handler = signal.getsignal(signal.SIGINT)
        self.assertTrue(callable(handler))
        handler(signal.SIGINT, None)   # raises nothing
        window.close.assert_not_called()   # not from inside a native filter
        self.app.processEvents()
        window.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
