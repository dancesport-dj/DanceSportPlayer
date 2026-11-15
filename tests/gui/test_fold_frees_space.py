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
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fold_space_"))

from PySide6.QtCore import QPoint
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
        # A window of an earlier test module leaves its layout.ini (and the lists
        # it autosaved) in the shared state dir; this window would restore them.
        patcher = mock.patch.dict(os.environ, {
            "DANCEPLAYLIST_STATE_DIR": tempfile.mkdtemp(prefix="dp_fold_space_state_")})
        patcher.start()
        cls.addClassCleanup(patcher.stop)
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

    def test_folding_the_wishlist(self):  # overconfidence:short-test-ok - asserts in the helper
        self.check_wishlist_fold(warmup=False)

    def test_folding_the_wishlist_beside_the_warmup_panel(self):  # overconfidence:short-test-ok - asserts in the helper
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

    def test_folding_every_deck(self):  # overconfidence:short-test-ok - asserts in the helper
        self.check_deck_fold(warmup=False)

    def test_folding_every_deck_beside_the_warmup_panel(self):  # overconfidence:short-test-ok - asserts in the helper
        self.check_deck_fold(warmup=True)

    # Marcel: "if i fold playist 1 and 2 i have a gap to wishlists?" The strip
    # height came from the group tab widget's sizeHint, which counts the Group
    # tab bar even while it is hidden (two or four playlists) and the open decks
    # of the pages not shown (eight playlists).
    def gap_under_folded_decks(self, deck_count):
        win = self.win_of_last_gap_test = self.window(warmup=False)
        win._deckset.deck_count = deck_count
        win._apply_deck_view()
        self.app.processEvents()
        folded = [t for t in win._deckset.decks if win._box_shown(t)]
        # The window saves its folds into the shared state dir on close; the
        # next test's window would start with them already folded.
        self.addCleanup(lambda: [win._toggle_deck_fold(t, False) for t in folded])
        for t in folded:
            win._toggle_deck_fold(t, True)
        self.app.processEvents()
        tabs = win._grid.deck_tabs
        boxes = [b for t in folded if (b := win.deck(t).box) is not None]
        bottom = max(b.mapTo(tabs, QPoint(0, b.height())).y() for b in boxes)
        return self.size_of(win, tabs) - bottom

    def test_two_folded_playlists_leave_no_gap(self):
        self.assertLessEqual(self.gap_under_folded_decks(2), 4)

    def test_four_folded_playlists_leave_no_gap(self):
        self.assertLessEqual(self.gap_under_folded_decks(4), 4)

    def test_eight_playlists_a_folded_group_leaves_no_gap(self):
        self.assertLessEqual(self.gap_under_folded_decks(8), 4)

    # Marcel: "when i collapse whole windows i also get a gap, but not every
    # time depends on the order". The section folded second handed its freed
    # height to the other section, which was already folded to its tabs.
    def fold_both_sections(self, decks_first):
        win = self.window(warmup=False)
        win._set_wish_state(2)
        self.app.processEvents()
        ds = win._deckset
        decks = [t for t in ds.decks if win._box_shown(t)]
        wishes = [t for t in ds.wishlists if win._box_shown(t)]
        order = decks + wishes if decks_first else wishes + decks
        self.addCleanup(lambda: [win._toggle_deck_fold(t, False) for t in order])
        lib_before = self.size_of(win, win._lib_tabs)
        for t in order:
            win._toggle_deck_fold(t, True)
        self.app.processEvents()
        sizes = win._grid.right_split.sizes()
        deck_strip = win._folded_decks_height()
        wish_strip = win._grid.wish_split.sizeHint().height()
        self.assertLessEqual(self.size_of(win, win._grid.deck_tabs), deck_strip + 4, sizes)
        self.assertLessEqual(self.size_of(win, win._grid.wish_split), wish_strip + 4, sizes)
        self.assertGreater(self.size_of(win, win._lib_tabs), lib_before + 200, sizes)
        return win, decks, wishes

    def test_decks_then_wishlists_folded_leave_no_gap(self):  # overconfidence:short-test-ok - asserts in the helper
        self.fold_both_sections(decks_first=True)

    def test_wishlists_then_decks_folded_leave_no_gap(self):  # overconfidence:short-test-ok - asserts in the helper
        self.fold_both_sections(decks_first=False)

    def test_unfolding_one_section_takes_the_room_back(self):
        for decks_first in (True, False):
            with self.subTest(decks_first=decks_first):
                win, decks, wishes = self.fold_both_sections(decks_first)
                win._toggle_deck_fold(decks[0], False)
                self.app.processEvents()
                self.assertGreater(self.size_of(win, win._grid.deck_tabs), 300,
                                   win._grid.right_split.sizes())
                win._toggle_deck_fold(decks[0], True)
                win._toggle_deck_fold(wishes[0], False)
                self.app.processEvents()
                self.assertGreater(self.size_of(win, win._grid.wish_split), 300,
                                   win._grid.right_split.sizes())

    def test_switching_from_a_folded_group_to_an_open_one(self):
        """The strip fits the page on show, so a switch to Group E–H with
        open decks must give the section its room back, and back again."""
        self.gap_under_folded_decks(8)
        win = self.win_of_last_gap_test
        tabs = win._grid.deck_tabs
        tabs.setCurrentIndex(win._grid.group_page(True))
        self.app.processEvents()
        box_e = win.deck(win._deckset.decks[4]).box
        assert box_e is not None
        self.assertGreater(box_e.height(), 150)
        tabs.setCurrentIndex(win._grid.group_page())
        self.app.processEvents()
        self.assertLessEqual(self.size_of(win, tabs), win._folded_decks_height() + 4)


if __name__ == "__main__":
    unittest.main()
