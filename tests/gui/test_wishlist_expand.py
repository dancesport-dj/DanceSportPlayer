#!/usr/bin/env python3
"""↔ One wishlist gets the whole area, the others go down to tabs.

Run:  py -m unittest tests.gui.test_wishlist_expand -v

Marcel's list, 7.1: "Add a right-click "expand" on a wishlist that expands it and
minimizes the other wishlists (e.g. with 3 wishlists). Also add a keyboard shortcut."
The way back is the same entry: with the others already down it opens them again.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wish_expand_"))

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import QApplication, QMenu

from gui.dialogs.shortcuts import shortcut_rows
from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from gui.window import main_decks
from planner.models import MusicEntry
from planner.playing import controller as pctl
from tests.qt_test_support import reap_widget, stub_window_startup

EXPAND = "↔  Expand this wishlist\tCtrl+Shift+E"
SHOW_ALL = "↔  Show all wishlists again\tCtrl+Shift+E"
KEY = "Ctrl+Shift+E"


def _e(title):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance="LW",
                      duration=150)


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_wish_expand_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def window(self, count=3, grid=False):
        # A closing window writes its folds to layout.ini in the state dir, and the
        # next window, also in another module of the batch, would start from them.
        env = mock.patch.dict(os.environ, {
            "DANCEPLAYLIST_STATE_DIR": tempfile.mkdtemp(prefix="dp_wish_expand_")})
        env.start()
        self.addCleanup(env.stop)
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win.resize(1400, 1000)
        win.show()
        win._set_wish_state(count, grid=grid)
        self.app.processEvents()
        return win

    @staticmethod
    def wishes(win, count=3):
        return win._deckset.wishlists[:count]

    @staticmethod
    def folded(win, *tables):
        return [bool(win.deck(t).folded) for t in tables]

    def caption(self, win, wl):
        return win._wish_expand_caption(wl)


class ExpandTest(_Base):

    def test_the_others_go_down_to_tabs(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._expand_wishlist(b)
        self.assertEqual(self.folded(win, a, b, c), [True, False, True])

    def test_a_folded_one_comes_up(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._toggle_deck_fold(c, folded=True)
        win._expand_wishlist(c)
        self.assertEqual(self.folded(win, a, b, c), [True, True, False])

    def test_doing_it_again_opens_them_all(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._expand_wishlist(a)
        win._expand_wishlist(a)
        self.assertEqual(self.folded(win, a, b, c), [False, False, False])

    def test_another_one_takes_over(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._expand_wishlist(a)
        win._expand_wishlist(c)
        self.assertEqual(self.folded(win, a, b, c), [True, True, False])

    def test_hidden_wishlists_stay_out_of_it(self):
        win = self.window(2)
        a, b, c, d = win._deckset.wishlists
        win._expand_wishlist(a)
        self.assertEqual(self.folded(win, a, b, c, d), [False, True, False, False])

    def test_the_grid_folds_the_other_three(self):
        win = self.window(4, grid=True)
        a, b, c, d = win._deckset.wishlists
        win._expand_wishlist(d)
        self.app.processEvents()
        self.assertEqual(self.folded(win, a, b, c, d), [True, True, True, False])
        self.assertTrue(d.isVisibleTo(win))

    def test_it_really_gets_the_room(self):
        win = self.window()
        a, b, _c = self.wishes(win)
        before = b.width()
        win._expand_wishlist(b)
        self.app.processEvents()
        self.assertTrue(b.isVisibleTo(win))
        self.assertFalse(a.isVisibleTo(win))
        self.assertGreater(b.width(), before)


class CaptionTest(_Base):

    def test_it_says_what_a_click_will_do(self):
        win = self.window()
        a, b, _c = self.wishes(win)
        self.assertEqual(self.caption(win, a), EXPAND)
        win._expand_wishlist(a)
        self.assertEqual(self.caption(win, a), SHOW_ALL)
        self.assertEqual(self.caption(win, b), EXPAND)

    def test_a_lone_wishlist_has_nothing_to_expand_over(self):
        win = self.window(1)
        self.assertIsNone(self.caption(win, win._deckset.wishlist))


class MenuTest(_Base):

    @staticmethod
    def list_menu(t, pick=None):
        """The list menu's captions; `pick` is the caption to click."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        pos = QPoint(5, t.rowViewportPosition(t._row_meta.song_rows()[0]) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen

    @staticmethod
    def header_menu(win, wl, pick=None):
        """The header menu's captions; `pick` is the caption to click."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5),
                            Qt.MouseButton.RightButton, Qt.MouseButton.RightButton,
                            Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(main_decks, "QMenu", _Menu):
            win._on_header_press(press, wl)
        return seen

    def test_the_list_offers_it(self):
        win = self.window()
        wl = win._deckset.wishlist
        wl.load_wishlist([_e("A")], mock.Mock(), None)
        self.assertIn(EXPAND, self.list_menu(wl, pick=EXPAND))
        self.assertEqual(self.folded(win, *self.wishes(win)), [False, True, True])

    def test_the_header_offers_it(self):
        win = self.window()
        wl = win._deckset.wishlist
        self.assertIn(EXPAND, self.header_menu(win, wl, pick=EXPAND))
        self.assertEqual(self.folded(win, *self.wishes(win)), [False, True, True])

    def test_the_way_back_stands_in_the_same_place(self):
        win = self.window()
        wl = win._deckset.wishlist
        win._expand_wishlist(wl)
        self.assertIn(SHOW_ALL, self.header_menu(win, wl, pick=SHOW_ALL))
        self.assertEqual(self.folded(win, *self.wishes(win)), [False, False, False])

    def test_a_lone_wishlist_offers_neither(self):
        win = self.window(1)
        wl = win._deckset.wishlist
        wl.load_wishlist([_e("A")], mock.Mock(), None)
        self.assertNotIn(EXPAND, self.list_menu(wl))
        self.assertNotIn(EXPAND, self.header_menu(win, wl))

    def test_a_table_outside_the_window_shows_nothing(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t.load_wishlist([_e("A")], mock.Mock(), None)
        self.assertNotIn(EXPAND, self.list_menu(t))


class ShortcutTest(_Base):

    @staticmethod
    def shortcut(win):
        return next(s for s in win.findChildren(QShortcut)
                    if s.key() == QKeySequence(KEY))

    def test_it_works_on_the_focused_wishlist(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._focused_table = b
        self.shortcut(win).activated.emit()
        self.assertEqual(self.folded(win, a, b, c), [True, False, True])

    def test_a_deck_in_focus_leaves_the_wishlists_alone(self):
        win = self.window()
        a, b, c = self.wishes(win)
        win._focused_table = win._deckset.table
        self.shortcut(win).activated.emit()
        self.assertEqual(self.folded(win, a, b, c), [False, False, False])

    def test_no_desk_key_can_take_it(self):
        self.assertIn(KEY, pctl.RESERVED_KEYS)
        self.assertNotIn(KEY, {k for keys in pctl.desk_keys(None).values() for k in keys})

    def test_the_cheat_sheet_lists_it(self):
        keys = {row[0]: row[1] for row in shortcut_rows()}
        self.assertEqual(keys["Ctrl + Shift + E"], pctl.RESERVED_KEYS[KEY])


if __name__ == "__main__":
    unittest.main()
