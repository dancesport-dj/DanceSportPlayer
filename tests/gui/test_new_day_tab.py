#!/usr/bin/env python3
"""Right-click on a Group tab opens a 📅 tab under a competition name.

Run:  py -m unittest tests.gui.test_new_day_tab -v

Marcel: "allow to add a new tab with right click like the day plan do, so we
can make a new tab with the name of a competition manually". The 📅 tab only
ever opened for a day the day planner made; now it can be opened empty, named
by hand, and filled from there.

Then: "would be nice to have also when i click next to the tab and if i only
have 1-4 playlist on context menu of one of the playlist above". With 1–4
playlists there is no tab bar to right-click, so a playlist's header offers it.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_new_day_tab_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QContextMenuEvent  # noqa: E402

from dancesport_planner import MusicLibrary  # noqa: E402
from tests.gui.test_deck_file_reveal import _RightClick, _entry  # noqa: E402
from tests.gui.test_header_save_m3u import _menu_class  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402

_NEW = "📅  New tournament day…"


class NewDayTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_new_day_tab_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        # A view with decks: the settings the suite shares may carry the
        # no-playlist view, which shows no tabs at all.
        self.win._deck_count = 4
        self.win._apply_deck_view()

    def tab_menu(self, pick=None, typed=("", False)) -> dict:
        from gui import main_decks
        seen = {}
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, pick)), \
                mock.patch.object(main_decks.QInputDialog, "getText",
                                  return_value=typed):
            self.win._group_tab_menu(0, QPoint(10, 10))
        return seen

    def header_menu(self, table, pick=None, typed=("", False)) -> dict:
        from gui import main_decks
        seen = {}
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, pick)),                 mock.patch.object(main_decks.QInputDialog, "getText",
                                  return_value=typed):
            self.win._on_header_press(_RightClick(), table)
        return seen

    def right_click(self, obj, pos: QPoint, pick=None,
                    typed=("", False)) -> tuple[bool, dict]:
        from gui import main_decks
        seen = {}
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, obj.mapToGlobal(pos))
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, pick)),                 mock.patch.object(main_decks.QInputDialog, "getText",
                                  return_value=typed):
            handled = self.win.eventFilter(obj, ev)
        return handled, seen

    def eight_decks_on_screen(self):
        self.win._deck_count = 8
        self.win._apply_deck_view()
        self.win.show()
        self.app.processEvents()

    def day_tab_shown(self) -> bool:
        return self.win._deck_tabs.isTabVisible(2)

    def test_a_group_tab_offers_it(self):
        self.assertTrue(self.tab_menu()[_NEW])

    def test_it_opens_the_day_tab_under_that_name(self):
        self.tab_menu(pick="📅", typed=("DanceComp 2026", True))
        self.assertTrue(self.day_tab_shown())
        self.assertEqual(self.win._deck_tabs.tabText(2), "📅 DanceComp 2026")
        self.assertEqual(self.win._deck_tabs.currentIndex(), 2)
        self.assertTrue(all(t.rowCount() == 0 for t in self.win._day_decks))

    def test_cancelling_opens_nothing(self):
        self.tab_menu(pick="📅", typed=("DanceComp 2026", False))
        self.assertFalse(self.day_tab_shown())

    def test_a_tab_needs_a_name(self):
        self.tab_menu(pick="📅", typed=("   ", True))
        self.assertFalse(self.day_tab_shown())

    def test_while_a_day_is_open_it_is_greyed_out(self):
        # There is one 📅 tab; renaming it is on its own menu.
        self.win._day_decks[0].load_player_list([_entry("c1")], "HGR D",
                                                play_cb=None)
        self.win._apply_deck_view()
        self.assertFalse(self.tab_menu()[_NEW])

    # ── a playlist's header ────────────────────────────────────────────────
    def test_with_four_playlists_a_header_opens_it(self):
        tb = self.win._deck_tabs.tabBar()
        self.assertTrue(tb.isHidden(), "1–4 playlists: no tab bar to click")
        self.header_menu(self.win._tableA, pick="📅",
                         typed=("DanceComp 2026", True))
        self.assertTrue(self.day_tab_shown())
        self.assertFalse(tb.isHidden())
        self.assertEqual(self.win._deck_tabs.tabText(2), "📅 DanceComp 2026")

    def test_the_header_greys_it_out_while_a_day_is_open(self):
        self.header_menu(self.win._tableA, pick="📅",
                         typed=("DanceComp 2026", True))
        self.assertFalse(self.header_menu(self.win._tableB)[_NEW])

    # ── beside the tabs ────────────────────────────────────────────────────
    def test_right_of_the_last_tab_on_the_bar_opens_it(self):
        # The bar spans the tab widget's whole width, so every click beside
        # the tabs lands on it.
        self.eight_decks_on_screen()
        tb = self.win._deck_tabs.tabBar()
        pos = QPoint(tb.tabRect(1).right() + 20, tb.height() // 2)
        self.assertEqual(tb.tabAt(pos), -1)
        handled, menu = self.right_click(tb, pos, pick="📅",
                                         typed=("DanceComp 2026", True))
        self.assertTrue(handled)
        self.assertTrue(menu[_NEW])
        self.assertTrue(self.day_tab_shown())


if __name__ == "__main__":
    unittest.main()
