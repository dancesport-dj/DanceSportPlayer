#!/usr/bin/env python3
"""A toast that reports an error or a refusal is red (F13).

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_error_toast -v

Marcel: "tooltips that report an error / something we could not do are red."
The window keeps one toast label for every message, so an ordinary toast
after a red one has to turn grey again.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_error_toast_"))

from PySide6.QtWidgets import QApplication, QWidget

from shared.widgets import ERROR_TOAST_BG, show_toast
from tests.qt_test_support import reap_widget


class ErrorToastTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = QWidget()
        self.addCleanup(reap_widget, self.win)

    def css(self) -> str:
        return getattr(self.win, "_toast_lbl").styleSheet()

    def test_an_error_is_red(self):
        show_toast(self.win, "Couldn't", error=True)
        self.assertIn(ERROR_TOAST_BG, self.css())

    def test_an_ordinary_one_after_it_is_not(self):
        show_toast(self.win, "Couldn't", error=True)
        show_toast(self.win, "Saved")
        self.assertNotIn(ERROR_TOAST_BG, self.css())


if __name__ == "__main__":
    unittest.main(verbosity=2)
