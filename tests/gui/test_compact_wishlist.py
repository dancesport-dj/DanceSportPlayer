#!/usr/bin/env python3
"""📐 Compact: an empty wishlist starts folded to its header tab.

Run:  py -m unittest tests.gui.test_compact_wishlist -v

An empty wishlist took a fifth of a 13″ laptop's height to say "0 titles".
Under Compact it starts folded once the last session is back; one with
titles in it stays open, and Normal leaves them all as they were.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_compactwish_"))

from PySide6.QtWidgets import QApplication

import dancesport_gui as gui
from gui import screen_mode
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget, stub_window_startup


class CompactWishlistTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()      # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.addCleanup(setattr, screen_mode, "_compact", screen_mode._compact)
        self.wish = self.win._deckset.wishlist
        # The layout an earlier window saved on its way out folds it again.
        self.win._toggle_deck_fold(self.wish, False)

    def _folded(self):
        return bool(self.win.deck(self.wish).folded)

    # ===== Acceptance criteria =====
    def test_compact_folds_an_empty_wishlist(self):
        screen_mode._compact = True
        self.win._fold_empty_wishlists()
        self.assertTrue(self._folded())

    def test_a_wishlist_with_titles_stays_open(self):
        screen_mode._compact = True
        song = MusicEntry(path=Path("C:/m/song.mp3"), title="song", dance="WW", bpm=None)
        self.wish.load_wishlist([song], play_cb=lambda *a: None, suggester=None)
        self.win._fold_empty_wishlists()
        self.assertFalse(self._folded())

    def test_normal_leaves_it_open(self):
        screen_mode._compact = False
        self.win._fold_empty_wishlists()
        self.assertFalse(self._folded())


class CompactLibraryTest(unittest.TestCase):
    """📐 Compact: the library pane keeps six rows in sight — it was left
    with two under the decks, too few to pick a title from."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        stub_window_startup(cls, {"app_mode": "both"})

    def _table(self, compact):
        self.addCleanup(setattr, screen_mode, "_compact", screen_mode._compact)
        # The window decides it itself, from the settings and the screen.
        with mock.patch.object(screen_mode, "is_compact", return_value=compact):
            win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win._lib_browser._table

    def _six_rows(self, table):
        return 6 * table.verticalHeader().defaultSectionSize()

    # ===== Acceptance criteria =====
    def test_compact_keeps_six_library_rows(self):
        table = self._table(compact=True)
        self.assertGreaterEqual(table.minimumHeight(), self._six_rows(table))

    def test_normal_lets_the_divider_decide(self):
        table = self._table(compact=False)
        self.assertLess(table.minimumHeight(), self._six_rows(table))


if __name__ == "__main__":
    unittest.main(verbosity=2)
