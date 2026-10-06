#!/usr/bin/env python3
"""The ● focus dot on a deck header survives a rename and a fold refresh.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_deck_focus_mark -v

The header used to tell whether its deck was focused by comparing its own
stylesheet with _DECK_HDR_ACTIVE. With a picked accent colour the stylesheet
hook stores the recoloured sheet, so that comparison was always false and a
rename or fold refresh dropped the dot from the focused deck.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_focus_mark_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared import theme  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class DeckFocusMarkTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_focus_mark_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    # A picked accent recolours the active strip's blue; the default does not.
    PICKED = "#b8006e"

    def window(self, key, accent=PICKED):
        theme.install_stylesheet_hook()
        theme.set_active(key, accent)
        self.addCleanup(theme.set_active, "light", theme.ACCENT_DEFAULT)
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win._on_table_focused(win._tableA)
        return win

    def test_a_rename_keeps_the_dot(self):
        for key in ("light", "dark", "midnight"):
            with self.subTest(theme=key):
                win = self.window(key)
                win._set_deck_name(win._tableA, "Finale")
                self.assertIn("●", win.deck(win._tableA).header.text())

    def test_a_header_refresh_keeps_the_dot(self):
        for key in ("light", "dark"):
            with self.subTest(theme=key):
                win = self.window(key)
                win._refresh_deck_header(win._tableA)
                self.assertIn("●", win.deck(win._tableA).header.text())
                win._refresh_deck_header(win._tableB)
                self.assertNotIn("●", win.deck(win._tableB).header.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
