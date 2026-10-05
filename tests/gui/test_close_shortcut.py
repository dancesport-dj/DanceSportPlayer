#!/usr/bin/env python3
"""Tests for closing a dialog from the keyboard.

Run:  py -m unittest tests.gui.test_close_shortcut -v

The desk opens a lot of windows — 🔧 Fix paths, 🔥 Eintanzen, ⚙ Settings — and
the hand that opened one wants it gone again without hunting for a button.
Ctrl+W is what every other window on the machine answers to, Ctrl+X is what
this one has always answered to; both close the dialog in front, and neither
ever closes the app itself.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_close_"))

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QLineEdit,
    QVBoxLayout,
)

from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


def _ctrl(key):
    return QKeyEvent(QEvent.Type.KeyPress, key,
                     Qt.KeyboardModifier.ControlModifier)


class CloseShortcutTest(unittest.TestCase):
    """A real MainWindow with a dialog open in front of it."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_close_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win.show()
        self.app.processEvents()

    def _dialog(self):
        dlg = QDialog(self.win)
        self.addCleanup(reap_widget, dlg)
        lyt = QVBoxLayout(dlg)
        edit = QLineEdit(dlg)
        lyt.addWidget(edit)
        dlg.show()
        dlg.activateWindow()
        self.app.processEvents()
        return dlg, edit

    def test_ctrl_w_closes_the_dialog_in_front(self):
        dlg, _edit = self._dialog()
        self.assertTrue(self.win.eventFilter(dlg, _ctrl(Qt.Key.Key_W)))
        self.app.processEvents()
        self.assertFalse(dlg.isVisible())

    def test_ctrl_x_still_does_too(self):
        dlg, edit = self._dialog()
        edit.clearFocus()       # in a text field Ctrl+X is the cut, below
        self.app.processEvents()
        self.assertTrue(self.win.eventFilter(dlg, _ctrl(Qt.Key.Key_X)))
        self.app.processEvents()
        self.assertFalse(dlg.isVisible())

    def test_ctrl_w_closes_it_from_inside_a_text_field(self):
        """Nothing in a line edit answers to Ctrl+W, so there is nothing to
        protect there — unlike Ctrl+X, which is the cut."""
        dlg, edit = self._dialog()
        edit.setFocus()
        self.app.processEvents()
        self.assertTrue(self.win.eventFilter(edit, _ctrl(Qt.Key.Key_W)))
        self.app.processEvents()
        self.assertFalse(dlg.isVisible())

    def test_ctrl_x_in_a_text_field_is_still_the_cut(self):
        dlg, edit = self._dialog()
        edit.setFocus()
        self.app.processEvents()
        self.assertFalse(self.win.eventFilter(edit, _ctrl(Qt.Key.Key_X)))
        self.assertTrue(dlg.isVisible())

    def test_neither_key_ever_closes_the_desk(self):
        """On the main window the shortcut is swallowed — a stray Ctrl+W in
        the middle of a tournament must not take the desk down with it."""
        self.win.activateWindow()
        self.app.processEvents()
        for key in (Qt.Key.Key_W, Qt.Key.Key_X):
            self.assertTrue(self.win.eventFilter(self.win, _ctrl(key)))
            self.app.processEvents()
            self.assertTrue(self.win.isVisible())

    def test_the_filter_passes_on_what_is_not_a_qobject(self):
        """The filter sits on the whole application, so it sees every event
        of every object — and PySide can hand it a stale wrapper for an address
        Qt has reused, typed as whatever lived there before. A QWidgetItem once
        reached `super().eventFilter`, which only takes a QObject: the
        TypeError stayed pending and was re-raised by the next `event.type()`
        of every filter in the chain, 1140 frames deep, until a later test's
        `MainWindow()` died in `_loading_dlg.show()`."""
        from PySide6.QtWidgets import QWidget, QWidgetItem

        host = QWidget()
        self.addCleanup(reap_widget, host)
        item = QWidgetItem(host)
        for kind in (QEvent.Type.Show, QEvent.Type.Paint):
            self.assertFalse(self.win.eventFilter(item, QEvent(kind)))


if __name__ == "__main__":
    unittest.main()
