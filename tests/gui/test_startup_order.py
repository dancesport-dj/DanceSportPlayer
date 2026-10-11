#!/usr/bin/env python3
"""The library scan starts before the window is built, not after.

Run:  py -m unittest tests.gui.test_startup_order -v

Building MainWindow takes about 2 s and the background scan about 4 s. Run one
after the other, the screen stayed empty for over 3 s and the scan waited for
the build. Now the splash is up and the loader running before the first panel
is built, and the build pumps no events after that: the loader's result is a
queued signal, and it must not reach a half-built window.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_startup_order_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import StubLoader, reap_widget, stub_window_startup


class StartupOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.dg = stub_window_startup(cls)

    def test_the_scan_runs_while_the_window_is_built(self):
        dg = self.dg
        order = []

        class Loader(StubLoader):
            def start(self):
                order.append("loader started")
                super().start()

        orig_left = dg.MainWindow._setup_left_panel

        def left_panel(win):
            order.append(f"left panel, splash visible={win._loading_dlg.isVisible()}")
            return orig_left(win)

        orig_pump = QApplication.processEvents

        def pump(*a):
            order.append("events pumped")
            return orig_pump(*a)

        with mock.patch.object(dg, "LibraryLoader", Loader), \
                mock.patch.object(dg.MainWindow, "_setup_left_panel", left_panel), \
                mock.patch.object(QApplication, "processEvents", pump):
            win = dg.MainWindow()
        self.addCleanup(reap_widget, win)
        self.assertEqual(order[:3], ["events pumped", "loader started",
                                     "left panel, splash visible=True"])
        self.assertNotIn("events pumped", order[1:])


if __name__ == "__main__":
    unittest.main()
