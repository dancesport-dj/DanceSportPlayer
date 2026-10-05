#!/usr/bin/env python3
"""Tests for emptying the focused playlist from the keyboard.

Run:  py -m unittest tests.gui.test_clear_shortcut -v

Marcel: "we need a shortcut to empty current selected playlist". Del with
nothing selected already clears a list, but only while the list itself has
the focus and nothing in it is selected. Ctrl+Shift+Del empties the focused
playlist or wishlist from anywhere in the window, after the same question.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_clear_sc_"))

from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class ClearShortcutTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_clear_sc_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_the_key_is_ctrl_shift_del(self):
        self.assertEqual(self.win._clear_sc.key(), QKeySequence("Ctrl+Shift+Del"))

    def test_it_empties_the_focused_deck(self):
        deck = self.win._tableA
        self.win._on_table_focused(deck)
        with mock.patch.object(deck, "_clear_entire") as clear:
            self.win._clear_sc.activated.emit()
        clear.assert_called_once_with()

    def test_it_empties_the_focused_wishlist(self):
        wish = self.win._wishlist
        self.win._on_table_focused(wish)
        with mock.patch.object(wish, "_clear_entire") as clear, \
                mock.patch.object(self.win._tableA, "_clear_entire") as deck:
            self.win._clear_sc.activated.emit()
        clear.assert_called_once_with()
        deck.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
