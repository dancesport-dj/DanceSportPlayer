#!/usr/bin/env python3
"""🎛 What a right-click on a pad offers, with ✏ off and with ✏ on.

Run:  py -m unittest tests.player.test_cartwall_pad_menu -v

Marcel: "the context item with setting and shortcuts if i right click in non
edit mode" — and "in edit mode remove shortcuts, show only settings only for
this pad". Playing the wall, the right-click is the way to the wall's own
settings and keys; building it, the menu is about the pad under the mouse,
and ⌨ already sits in the toolbar next to ✏.
"""

import unittest

from PySide6.QtCore import QPoint

from planner.playing import cartwall as pc
from player.widgets import cartwall as gc
from tests.player.test_cartwall_i18n import _OpenedMenu, _PadMenu
from tests.qt_test_support import reap_widget


class PadMenuModeTest(_PadMenu):

    def pad(self, *, editable, filled=True):
        pad = gc.CartPadButton((0, 0, 0))
        self.addCleanup(reap_widget, pad)
        pad._editable = editable
        if filled:
            pad.set_pad(pc.CartPad(path="fanfare.mp3"))
        return pad

    def open(self, pad):
        _OpenedMenu.built = []
        pad._context_menu(QPoint(0, 0))
        self.assertTrue(_OpenedMenu.built, "the pad opened no menu")
        return _OpenedMenu.built[0]

    def test_playing_the_wall_offers_its_settings_and_the_keys(self):
        for filled in (True, False):
            with self.subTest(filled=filled):
                menu = self.open(self.pad(editable=False, filled=filled))
                self.assertEqual(self.captions(menu),
                                 ["⚙  Cartwall settings…", "⌨  Shortcuts…"])

    def test_the_wall_settings_item_asks_for_them(self):
        pad = self.pad(editable=False)
        seen = []
        pad.wall_settings_requested.connect(lambda: seen.append(True))
        self.open(pad).actions()[0].trigger()
        self.assertEqual(seen, [True])

    def test_the_shortcuts_item_asks_for_the_keys_window(self):
        pad = self.pad(editable=False)
        seen = []
        pad.shortcuts_requested.connect(lambda: seen.append(True))
        self.open(pad).actions()[1].trigger()
        self.assertEqual(seen, [True])

    def test_building_the_wall_the_menu_is_only_about_this_pad(self):
        captions = self.captions(self.open(self.pad(editable=True)))
        self.assertEqual(captions, ["⚙  Settings…", "🎨  Colour",
                                    "📄  Move to page", "🗑  Clear pad"])

    def test_an_empty_pad_while_building_only_takes_files(self):
        captions = self.captions(self.open(self.pad(editable=True,
                                                    filled=False)))
        self.assertEqual(captions, ["📂  Assign files…"])


class MoveToPageMenuTest(_PadMenu):
    """📄 Move to page lists the wall's OTHER pages, by their names."""

    def move_menu(self, names, page=0):
        pad = gc.CartPadButton((page, 0, 0))
        self.addCleanup(reap_widget, pad)
        pad._editable = True
        pad.set_pad(pc.CartPad(path="fanfare.mp3"))
        pad.set_page_names(names)
        _OpenedMenu.built = []
        pad._context_menu(QPoint(0, 0))
        item = next(a for a in _OpenedMenu.built[0].actions()
                    if a.text() == "📄  Move to page")
        return pad, item.menu()

    def test_every_page_but_its_own(self):
        _pad, sub = self.move_menu(["Page 1", "Intro", "Page 3"], page=1)
        self.assertEqual([a.text() for a in sub.actions()], ["Page 1", "Page 3"])

    def test_one_page_wall_has_nowhere_to_go(self):
        _pad, sub = self.move_menu(["Page 1"])
        self.assertFalse(sub.isEnabled())

    def test_picking_a_page_asks_for_the_move(self):
        pad, sub = self.move_menu(["Page 1", "Page 2"])
        seen = []
        pad.move_requested.connect(lambda key, dst: seen.append((key, dst)))
        sub.actions()[0].trigger()
        self.assertEqual(seen, [((0, 0, 0), 1)])


class MoveToPageWallTest(unittest.TestCase):
    """The wall moves the pad, or the whole selection, and the sounding
    voices follow it."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def wall(self, first, second):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        page = lambda cells: pc.Page(pads={c: pc.CartPad(path=f"{c}.mp3")
                                           for c in cells})
        w.set_wall((2, 2), [page(first), page(second)])
        return w

    def test_one_pad_goes_into_the_same_cell(self):
        w = self.wall([(1, 0)], [])
        moved, changed = [], []
        w.padsMoved.connect(moved.append)
        w.changed.connect(lambda: changed.append(True))
        w._on_move_to_page((0, 1, 0), 1)
        self.assertIsNone(w.pad_at((0, 1, 0)))
        self.assertEqual(w.pad_at((1, 1, 0)).path, "(1, 0).mp3")
        self.assertEqual(moved, [{(0, 1, 0): (1, 1, 0)}])
        self.assertTrue(changed)

    def test_the_selection_moves_together_and_is_dropped(self):
        w = self.wall([(0, 0), (0, 1)], [])
        w._selected = {(0, 0, 0), (0, 0, 1)}
        w._on_move_to_page((0, 0, 0), 1)
        self.assertEqual(pc.pad_count(w.pages()[:1]), 0)
        self.assertEqual(pc.pad_count(w.pages()[1:]), 2)
        self.assertEqual(w._selected, set())

    def test_a_full_page_says_how_many_made_it(self):
        w = self.wall([(0, 0), (0, 1)], [(0, 0), (0, 1), (1, 0)])
        w._selected = {(0, 0, 0), (0, 0, 1)}
        said = []
        real = gc.QMessageBox.information
        gc.QMessageBox.information = lambda *a: said.append(a[2])
        self.addCleanup(setattr, gc.QMessageBox, "information", real)
        w._on_move_to_page((0, 0, 0), 1)
        self.assertEqual(pc.pad_count(w.pages()), 5)
        self.assertEqual(len(said), 1)
        self.assertIn("1 of 2", said[0])


class WallSettingsSignalTest(unittest.TestCase):
    """The wall passes the pad's request on: the window owns ⚙ Settings."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_a_pad_asking_for_the_wall_settings_reaches_the_window(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        seen = []
        w.settingsRequested.connect(lambda: seen.append(True))
        w._buttons[(0, 0, 0)].wall_settings_requested.emit()
        self.assertEqual(seen, [True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
