#!/usr/bin/env python3
"""The undo/redo flash tints rows and puts their backgrounds back.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_flash_rows -v

The restore runs on a timer. A deck closed before it fired left the timer
calling into the deleted table: "Internal C++ object (PlaylistTable) already
deleted", printed out of whatever happened to be running at the time.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_flashrows_"))

import shiboken6  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableWidgetItem  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402

_FLASH = QColor(255, 236, 160)


class FlashRowsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _table(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t.setRowCount(1)
        item = QTableWidgetItem("Slot")
        item.setBackground(QColor("white"))
        t.setItem(0, 0, item)
        return t

    def test_the_row_is_tinted_and_then_restored(self):
        t = self._table()
        t.flash_rows([0], _FLASH, msec=50)
        self.assertEqual(t.item(0, 0).background().color(), _FLASH)
        QTest.qWait(150)
        self.assertEqual(t.item(0, 0).background().color(), QColor("white"))

    def test_a_table_deleted_before_the_restore_raises_nothing(self):
        t = self._table()
        t.flash_rows([0], _FLASH, msec=50)
        shiboken6.delete(t)
        errors = []
        with mock.patch.object(sys, "excepthook",
                               lambda *exc: errors.append(exc[1])):
            QTest.qWait(150)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
