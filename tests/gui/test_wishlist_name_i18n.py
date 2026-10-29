#!/usr/bin/env python3
"""⭐ The wishlist titles read "Wunschliste" in a German app.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_wishlist_name_i18n -v

Marcel: "Wishlist" was not translated to "Wunschliste". The catalog had the
word all along, but the titles are built as "⭐  Wishlist 2" — a deck name,
not a catalog key — so the text hook never saw a match. A session saved
before the fix (or under another language) still holds the English default;
restored, it reads in the app's language too. A title the user typed stays.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wish_name_"))

from PySide6.QtWidgets import QApplication

from planner import i18n
from tests.qt_test_support import reap_widget, stub_window_startup


class GermanWishlistNameTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_wish_name_qs_")
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
        return [self.win.deck(t).name for t in self.win._deckset.wishlists]

    def restore(self, **names):
        env = self.win._build_env()
        env["names"].update(names)
        self.win._apply_env(env)

    def test_a_new_window_names_them_in_german(self):
        self.assertEqual(self.names(), ["⭐  Wunschliste", "⭐  Wunschliste 2",
                                        "⭐  Wunschliste 3", "⭐  Wunschliste 4"])

    def test_a_clear_goes_back_to_the_german_name(self):
        wl = self.win._deckset.wishlist2
        self.win._set_deck_name(wl, "Finale")
        self.win._reset_wishlist_name(wl)
        self.assertEqual(self.win.deck(wl).name, "⭐  Wunschliste 2")

    def test_an_english_default_from_an_old_session(self):
        self.restore(wishlist="⭐  Wishlist", wishlist2="⭐  Wishlist 2")
        self.assertEqual(self.names()[:2], ["⭐  Wunschliste", "⭐  Wunschliste 2"])

    def test_a_title_after_a_loaded_playlist(self):
        self.restore(wishlist3="⭐  Wishlist 3: Finale")
        self.assertEqual(self.names()[2], "⭐  Wunschliste 3: Finale")

    def test_a_typed_title_stays(self):
        self.restore(wishlist="Wishlist", wishlist4="My Wishlist 4")
        self.assertEqual(self.names()[0], "Wishlist")
        self.assertEqual(self.names()[3], "My Wishlist 4")


if __name__ == "__main__":
    unittest.main()
