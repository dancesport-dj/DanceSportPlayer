#!/usr/bin/env python3
"""The Group A–D / E–H tabs take a name of their own, like the 📅 tab.

Run:  py -m unittest tests.gui.window.test_group_tab_rename -v

Marcel: "when i use 8 playliste, i want to be able to rename the tab buttons
names Grouo A-D and Grouo E-H". Picked: the same as the 📅 tab, a double-click
on the tab or ✏️ Rename tab… in its right-click menu asks for a name, an empty
one gives the default back, and the names come back at the next start.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_group_tab_rename_"))

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from dancesport_planner import MusicLibrary
from tests.gui.test_header_save_m3u import _menu_class
from tests.qt_test_support import reap_widget, stub_window_startup


class GroupTabRenameTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_group_tab_rename_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.win._deckset.deck_count = 8
        self.win._apply_deck_view()
        self.tabs = self.win._grid.deck_tabs
        save = mock.patch.object(self.win, "_autosave_playlist")
        self.saved = save.start()
        self.addCleanup(save.stop)

    def page(self, second=False) -> int:
        return self.win._grid.group_page(second)

    def double_click(self, page: int, typed=("", False)) -> bool:
        from gui.window import main_decks
        tb = self.tabs.tabBar()
        pos = QPointF(tb.tabRect(page).center())
        ev = QMouseEvent(QEvent.Type.MouseButtonDblClick, pos, tb.mapToGlobal(pos),
                         Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(main_decks.QInputDialog, "getText",
                               return_value=typed):
            return self.win.eventFilter(tb, ev)

    def test_a_double_click_on_a_group_tab_renames_it(self):
        self.assertTrue(self.double_click(self.page(True), ("Standard Senioren", True)))
        self.assertEqual(self.tabs.tabText(self.page(True)), "Standard Senioren")
        self.assertEqual(self.tabs.tabText(self.page()), "Group A–D")
        self.saved.assert_called()

    def test_an_empty_name_gives_the_default_back(self):
        self.double_click(self.page(), ("Latin", True))
        self.double_click(self.page(), ("   ", True))
        self.assertEqual(self.tabs.tabText(self.page()), "Group A–D")

    def test_cancel_keeps_the_name(self):
        self.double_click(self.page(), ("Latin", True))
        self.double_click(self.page(), ("", False))
        self.assertEqual(self.tabs.tabText(self.page()), "Latin")

    def test_the_right_click_menu_renames_too(self):
        from gui.window import main_decks
        seen = {}
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, "✏️")), \
                mock.patch.object(main_decks.QInputDialog, "getText",
                                  return_value=("Latin", True)):
            self.win._group_tab_menu(self.page(), QPoint(10, 10))
        self.assertIn("✏️  Rename tab…", seen)
        self.assertEqual(self.tabs.tabText(self.page()), "Latin")

    def test_the_names_are_saved_and_come_back(self):
        self.double_click(self.page(True), ("Standard", True))
        env = self.win._build_env()
        self.assertEqual(env["group_tabs"], ["", "Standard"])

        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        win._restore_env(env, deck_modes=True)
        tabs = win._grid.deck_tabs
        self.assertEqual(tabs.tabText(win._grid.group_page(True)), "Standard")
        self.assertEqual(tabs.tabText(win._grid.group_page()), "Group A–D")

    def test_an_old_save_without_names_keeps_the_defaults(self):
        self.double_click(self.page(), ("Latin", True))
        env = self.win._build_env()
        del env["group_tabs"]
        self.win._restore_env(env, deck_modes=True)
        self.assertEqual(self.tabs.tabText(self.page()), "Group A–D")


if __name__ == "__main__":
    unittest.main()
