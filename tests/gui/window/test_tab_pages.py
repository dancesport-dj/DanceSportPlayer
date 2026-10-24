#!/usr/bin/env python3
"""The deck tabs and the left panel find their pages by widget, not by number.

Run:  py -m unittest tests.gui.window.test_tab_pages -v

Group A–D, Group E–H and 📅 Tournament day were 0, 1 and 2 all over the
window code, and Planning / Playing were 0 and 1 of the left stack, so a page
added in front, or a reorder, would have pointed every one of them at the
wrong page. Each test here slips an extra page in front first.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tab_pages_"))

from PySide6.QtWidgets import QWidget

from dancesport_planner import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup


class TabPagesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_tab_pages_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.win._deckset.deck_count = 8
        self.win._apply_deck_view()
        grid = self.win._grid
        self.tabs, self.day = grid.deck_tabs, grid.day_tabs
        self.tabs.insertTab(0, QWidget(), "extra")
        self.day.insertTab(0, QWidget(), "extra")
        self.win._left_stack.insertWidget(0, QWidget())

    def test_each_deck_names_the_page_it_sits_on(self):
        ds, grid = self.win._deckset, self.win._grid
        self.assertEqual(self.win._deck_tab_index(ds.tableA),
                         self.tabs.indexOf(grid.decks_split))
        self.assertEqual(self.win._deck_tab_index(ds.tableE),
                         self.tabs.indexOf(grid.decks_split2))
        self.assertEqual(self.win._deck_tab_index(ds.day_decks[0]),
                         self.tabs.indexOf(self.day))
        self.assertEqual(self.win._day_tab_index(ds.day_decks[5]),
                         self.day.indexOf(grid.day_split2))

    def test_the_day_title_lands_on_the_day_tab(self):
        self.win._set_day_tab_title("DanceComp 2026")
        self.assertEqual(self.tabs.tabText(self.tabs.indexOf(self.day)),
                         "📅 DanceComp 2026")
        self.assertEqual(self.tabs.tabText(0), "extra")

    def test_a_new_day_opens_and_fronts_the_day_tab(self):
        from gui.window import main_decks
        with mock.patch.object(main_decks.QInputDialog, "getText",
                               return_value=("Cup", True)), \
                mock.patch.object(self.win, "_autosave_playlist"):
            self.win._new_day_tab()
        self.assertIs(self.tabs.currentWidget(), self.day)
        self.assertTrue(self.tabs.isTabVisible(self.tabs.indexOf(self.day)))

    def test_the_deck_view_shows_and_hides_the_right_pages(self):
        self.win._deckset.deck_count = 4
        self.win._apply_deck_view()
        self.assertTrue(self.tabs.isTabVisible(
            self.tabs.indexOf(self.win._grid.decks_split)))
        self.assertFalse(self.tabs.isTabVisible(
            self.tabs.indexOf(self.win._grid.decks_split2)))
        self.assertFalse(self.tabs.isTabVisible(self.tabs.indexOf(self.day)))

    def test_playing_mode_is_the_playing_page(self):
        self.win._set_play_mode(True)
        self.assertIs(self.win._left_stack.currentWidget(), self.win._play_scroll)
        self.assertTrue(self.win._is_playing_mode())
        self.win._set_play_mode(False)
        self.assertIs(self.win._left_stack.currentWidget(), self.win._cfg_scroll)
        self.assertFalse(self.win._is_playing_mode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
