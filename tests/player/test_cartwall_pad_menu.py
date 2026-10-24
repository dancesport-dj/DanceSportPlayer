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
        pad = gc._CartPadButton((0, 0, 0))
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
        self.assertEqual(captions,
                         ["⚙  Settings…", "🎨  Colour", "🗑  Clear pad"])

    def test_an_empty_pad_while_building_only_takes_files(self):
        captions = self.captions(self.open(self.pad(editable=True,
                                                    filled=False)))
        self.assertEqual(captions, ["📂  Assign files…"])


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
