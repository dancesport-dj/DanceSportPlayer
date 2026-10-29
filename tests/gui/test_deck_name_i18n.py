#!/usr/bin/env python3
"""🅰 The decks' default titles read "Wiedergabeliste 3" in a German app.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_deck_name_i18n -v

Marcel: in German the decks on places 3 and 4 still said "Playlist 3" and
"Playlist 4". The titles were built as "Playlist 3" — a deck name, not a
catalog key — so the text hook never saw a match (the wishlists had the same
fault, see test_wishlist_name_i18n). A session saved under another language
still holds that language's default; restored, it reads in the app's
language too. A title the user typed stays.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_deck_name_"))

from PySide6.QtWidgets import QApplication

from planner import i18n
from tests.qt_test_support import reap_widget, stub_window_startup


class GermanDeckNameTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_deck_name_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def names(self):
        return [self.win.deck(t).name for t in self.win._deckset.decks]

    def restore(self, **names):
        env = self.win._build_env()
        env["names"].update(names)
        self.win._apply_env(env)

    def test_a_new_window_names_them_in_german(self):
        self.assertEqual(self.names(),
                         [f"Wiedergabeliste {n}" for n in range(1, 9)])

    def test_the_header_shows_the_german_name(self):
        hdr = self.win.deck(self.win._deckset.tableC).header
        self.assertIn("Wiedergabeliste 3", hdr.text())

    def test_an_english_default_from_an_old_session(self):
        self.restore(deck_c="Playlist 3", deck_d="Playlist 4")
        self.assertEqual(self.names()[2:4],
                         ["Wiedergabeliste 3", "Wiedergabeliste 4"])

    def test_a_typed_title_stays(self):
        self.restore(deck_c="Finale", deck_d="Playlist 3")
        self.assertEqual(self.names()[2:4], ["Finale", "Playlist 3"])


if __name__ == "__main__":
    unittest.main()
