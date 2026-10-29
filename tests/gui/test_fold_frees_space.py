#!/usr/bin/env python3
"""📐 Folding every wishlist (or every deck) hands the freed height over.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_fold_frees_space -v

Marcel: collapsing the wishlist (and similar panels) did not give the space
back — the collapse arrow should release the gap. The right-hand splitter
holds decks, the 🤸 warm-up panel, the wishlists and the library, in that
order; the fold code took pane 1 for the wishlists, which is the warm-up
panel. So the wishlist area kept its height, and with the warm-up panel open
that panel was squeezed to a strip instead.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fold_space_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import reap_widget, stub_window_startup

SLACK = 12   # px a strip may carry beyond its header


class FoldFreesSpaceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_fold_space_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def window(self, warmup):
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win.resize(1400, 1000)
        win.show()
        win._deckset.deck_count = 2
        win._apply_deck_view()
        win._set_wish_state(1)
        win._on_warmup_toggle(warmup)
        split = win._grid.right_split
        sizes = split.sizes()
        sizes[split.indexOf(win._grid.warmup_box)] = 150 if warmup else 0
        sizes[split.indexOf(win._grid.wish_split)] = 300
        split.setSizes(sizes)
        self.app.processEvents()
        return win

    def size_of(self, win, pane):
        split = win._grid.right_split
        return split.sizes()[split.indexOf(pane)]

    def check_wishlist_fold(self, warmup):
        win = self.window(warmup)
        decks = self.size_of(win, win._grid.deck_tabs)
        warm = self.size_of(win, win._grid.warmup_box)
        win._toggle_deck_fold(win._deckset.wishlist, True)
        self.app.processEvents()
        strip = win._grid.wish_split.sizeHint().height()
        self.assertLessEqual(self.size_of(win, win._grid.wish_split), strip + SLACK)
        self.assertEqual(self.size_of(win, win._grid.warmup_box), warm)
        self.assertGreater(self.size_of(win, win._grid.deck_tabs), decks + 200)
        win._toggle_deck_fold(win._deckset.wishlist, False)
        self.app.processEvents()
        self.assertGreater(self.size_of(win, win._grid.wish_split), 4 * strip)
        self.assertEqual(self.size_of(win, win._grid.warmup_box), warm)

    def test_folding_the_wishlist(self):
        self.check_wishlist_fold(warmup=False)

    def test_folding_the_wishlist_beside_the_warmup_panel(self):
        self.check_wishlist_fold(warmup=True)

    def check_deck_fold(self, warmup):
        win = self.window(warmup)
        wish = self.size_of(win, win._grid.wish_split)
        warm = self.size_of(win, win._grid.warmup_box)
        for t in (win._deckset.tableA, win._deckset.tableB):
            win._toggle_deck_fold(t, True)
        self.app.processEvents()
        strip = win._grid.deck_tabs.sizeHint().height()
        self.assertLessEqual(self.size_of(win, win._grid.deck_tabs), strip + SLACK)
        self.assertEqual(self.size_of(win, win._grid.warmup_box), warm)
        self.assertGreater(self.size_of(win, win._grid.wish_split), wish + 150)
        win._toggle_deck_fold(win._deckset.tableA, False)
        self.app.processEvents()
        self.assertGreater(self.size_of(win, win._grid.deck_tabs), 4 * strip)
        self.assertEqual(win._grid.deck_tabs.minimumHeight(), 0)

    def test_folding_every_deck(self):
        self.check_deck_fold(warmup=False)

    def test_folding_every_deck_beside_the_warmup_panel(self):
        self.check_deck_fold(warmup=True)


if __name__ == "__main__":
    unittest.main()
