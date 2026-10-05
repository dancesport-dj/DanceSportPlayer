#!/usr/bin/env python3
"""Each 🔁 Check duplicates frees the dialog it opened.

Run:  py -m unittest tests.gui.test_duplicate_dialog_freed -v

The dialog is parented to the main window. It used to be a local, exec()'d:
the local went, the window's child did not, and every check left one more
hidden dialog — its three tabs, its report widgets — alive until the app quit.
It is modeless now, so it is freed when it is closed.
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.duplicate_dialog import DuplicateResolveDialog  # noqa: E402
from gui.main_dupes import DuplicateCheckMixin  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Win(QWidget, DuplicateCheckMixin):
    _lib = object()

    def _deck_dup_report(self):
        return {"within": [], "cross": []}

    def _pick_replacement(self, entry):
        return None

    def _check_dropped_duplicates(self, paths, progress_cb=None):
        return {"within": [], "cross": []}

    def _play_or_stop(self, path):
        pass

    def _seek(self, ms):
        pass


class DuplicateDialogFreedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_no_dialog_outlives_its_check(self):
        win = _Win()
        self.addCleanup(reap_widget, win)

        for _ in range(2):
            win._check_duplicates()
            win.findChildren(DuplicateResolveDialog)[-1].reject()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual(win.findChildren(DuplicateResolveDialog), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
