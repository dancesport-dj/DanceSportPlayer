#!/usr/bin/env python3
"""💥 The box about last session's crash.log says what the log holds.

Run:  py -m unittest tests.app.test_previous_crash_box -v

crash.log gets two kinds of text: faulthandler's dump when the process was
killed by a native fault, and an uncaught Python exception, after which the app
may well have carried on. The box said "did not shut down cleanly" for both.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_crash_box_"))

from PySide6.QtWidgets import QApplication, QMessageBox

import dancesport_gui

FAULT = ("Windows fatal exception: access violation\n\n"
         "Current thread 0x00004a1c (most recent call first):\n"
         "  File \"dancesport_gui.py\", line 2003 in main\n")
ERROR = ("=== Uncaught Python exception ===\n"
         "Traceback (most recent call last):\n"
         "  File \"gui/foo.py\", line 1, in bar\n"
         "ZeroDivisionError: division by zero\n")


class PreviousCrashBoxTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def shown(self, prev_crash):
        boxes = []
        with mock.patch.object(QMessageBox, "exec", lambda box: boxes.append(box)):
            dancesport_gui._show_previous_crash(None, prev_crash, "")
        self.addCleanup(boxes[0].deleteLater)
        return boxes[0]

    def test_a_native_fault_says_the_app_crashed(self):
        box = self.shown(FAULT)
        self.assertEqual(box.windowTitle(), "Previous session crashed")
        self.assertIn("did not shut down cleanly", box.text())

    def test_a_python_fatal_error_says_the_app_crashed(self):
        box = self.shown("Fatal Python error: Segmentation fault\n\n" + ERROR)
        self.assertEqual(box.windowTitle(), "Previous session crashed")

    def test_an_uncaught_exception_alone_says_an_error_was_logged(self):
        box = self.shown(ERROR)
        self.assertEqual(box.windowTitle(), "Previous session logged an error")
        self.assertIn("may have kept running", box.text())
        self.assertNotIn("did not shut down cleanly", box.text())

    def test_every_language_has_the_error_wording(self):
        import importlib
        box = self.shown(ERROR)
        for code in ("de", "es", "nl", "ru"):
            catalog = importlib.import_module(f"planner.i18n.lang_{code}").CATALOG
            with self.subTest(lang=code):
                self.assertIn(box.windowTitle(), catalog)
                self.assertIn(box.text(), catalog)

    def test_the_log_is_under_the_details_either_way(self):
        for text in (FAULT, ERROR):
            with self.subTest(text=text[:20]):
                self.assertIn(text.strip(), self.shown(text).detailedText())


if __name__ == "__main__":
    unittest.main(verbosity=2)
