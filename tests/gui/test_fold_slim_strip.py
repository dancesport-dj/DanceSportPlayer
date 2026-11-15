#!/usr/bin/env python3
"""📐 A playlist folded sideways keeps no gaps around its letter.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_fold_slim_strip -v

Marcel: "make the folded icon smaller, currently we have gaps not needed",
then "same goes for whitelist" (the wishlists). A deck whose whole column is
folded, or a wishlist folded beside an open one, shrinks to a slim strip that
shows its letter and the ▸/◂ arrow. The letter sat in the header's full 8 px
padding a side, and the arrow in a 22 px button around an 8 px glyph. Folded
sideways, the strip is now padded 3 px a side and the arrow button is as wide
as its glyph. Open, and in the full-width tab rows of a fully folded section,
the header keeps its padding.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fold_slim_"))

from PySide6.QtWidgets import QApplication

from gui.window.main_fold import SLIM_HDR
from tests.qt_test_support import reap_widget, stub_window_startup


class FoldSlimStripTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_fold_slim_qs_"))
        patcher = mock.patch.dict(os.environ, {
            "DANCEPLAYLIST_STATE_DIR": tempfile.mkdtemp(prefix="dp_fold_slim_state_")})
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        win = self.win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win.resize(1400, 1000)
        win.show()
        win._deckset.deck_count = 4
        win._apply_deck_view()
        win._set_wish_state(2)
        self.app.processEvents()

    # The offscreen font measures an emoji narrower than it draws, and by a
    # different amount for each header text, so pixel widths of the header are
    # no evidence here. Checked instead: what the header is given. With real
    # fonts the left column's strip went from 67 to 43 px.
    def slim_style(self, table) -> bool:
        return SLIM_HDR in self.win.deck(table).header.styleSheet()

    def arrow_spare(self, table) -> int:
        """How much wider the ▸/◂ button is laid out than its glyph."""
        btn = self.win.deck(table).fold_btn
        width = min(btn.sizeHint().width(), btn.maximumWidth())
        return width - btn.fontMetrics().horizontalAdvance(btn.text())

    def fold(self, *tables):
        for t in tables:
            self.win._toggle_deck_fold(t, True)
        self.app.processEvents()

    def check_slim(self, table):
        self.assertTrue(self.win._folded_tab_is_sideways(table))
        self.assertTrue(self.slim_style(table))
        self.assertLessEqual(self.arrow_spare(table), 6)

    def check_full(self, table):
        self.assertFalse(self.slim_style(table))
        self.assertEqual(self.win.deck(table).fold_btn.maximumWidth(), 16777215)
        self.assertGreater(self.arrow_spare(table), 6)

    def test_a_deck_folded_sideways_is_slim(self):
        ds = self.win._deckset
        self.fold(ds.tableA, ds.tableC)
        self.check_slim(ds.tableA)
        self.check_slim(ds.tableC)
        box = self.win.deck(ds.tableA).box
        self.assertLessEqual(box.maximumWidth(), box.sizeHint().width() + 2)

    def test_a_wishlist_folded_sideways_is_slim(self):
        ds = self.win._deckset
        self.fold(ds.wishlist)
        self.check_slim(ds.wishlist)
        box = self.win.deck(ds.wishlist).box
        self.assertLessEqual(box.maximumWidth(), box.sizeHint().width() + 2)

    def test_unfolding_gives_the_padding_back(self):
        ds = self.win._deckset
        self.fold(ds.tableA, ds.tableC, ds.wishlist)
        self.win._toggle_deck_fold(ds.tableA, False)
        self.win._toggle_deck_fold(ds.wishlist, False)
        self.app.processEvents()
        self.check_full(ds.tableA)
        self.check_full(ds.wishlist)

    def test_focus_keeps_a_sideways_strip_slim(self):
        ds = self.win._deckset
        self.fold(ds.tableA, ds.tableC)
        self.win._set_active_table(ds.tableB)
        self.check_slim(ds.tableA)

    def test_full_width_tab_rows_keep_their_padding(self):
        ds = self.win._deckset
        self.fold(ds.tableA, ds.tableB, ds.tableC, ds.tableD)
        self.assertFalse(self.win._folded_tab_is_sideways(ds.tableA))
        self.check_full(ds.tableA)


if __name__ == "__main__":
    unittest.main()
