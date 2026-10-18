#!/usr/bin/env python3
"""⚙ Settings from the ❔ menu and from a key of its own.

Run:  py -m unittest tests.gui.test_settings_access -v

Marcel: "add under the question mark button also a shortcut to the
settings" and "settings button should have a keymapping". Ctrl + , is the
key other desktop apps use for their settings, and nothing in this app had
it yet. The ❔ entry names the key, like F1 and F11 beside it, and the F1
cheat sheet lists it. Marcel later: "use f12 and crtl+alt+s" as well — one key
to hit without looking, and the JetBrains one. Then: "remove crtl + , from
shortcut for setting" — F12 and Ctrl+Alt+S are the two left.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_access_"))

from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication

from gui.dialogs.shortcuts import shortcut_rows
from planner.playing import controller as pctl
from tests.qt_test_support import reap_widget, stub_window_startup


class SettingsAccessTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def test_the_help_menu_opens_the_settings(self):
        entry = next((a for a in self.win._help_menu().actions()
                      if a.text().startswith("⚙")), None)
        self.assertIsNotNone(entry, "no ⚙ entry under ❔")
        self.assertIn("F12 / Ctrl+Alt+S", entry.text())
        with mock.patch.object(self.win, "_open_settings") as opened:
            entry.trigger()
        opened.assert_called_once_with()

    def test_each_settings_key_opens_the_settings(self):
        for key in ("F12", "Ctrl+Alt+S"):
            with self.subTest(key=key):
                keys = [sc for sc in self.win.findChildren(QShortcut)
                        if sc.key().toString() == key]
                self.assertEqual(len(keys), 1)
                with mock.patch.object(self.win, "_open_settings") as opened:
                    keys[0].activated.emit()
                opened.assert_called_once_with()

    def test_ctrl_comma_is_no_settings_key_any_more(self):
        self.assertEqual([sc for sc in self.win.findChildren(QShortcut)
                          if sc.key().toString() == "Ctrl+,"], [])
        self.assertEqual(pctl.key_clashes({"toggle": ["Ctrl+,"]}), {})

    def test_the_cheat_sheet_lists_them(self):
        self.assertIn("F12  /  Ctrl + Alt + S",
                      [left for left, _r in shortcut_rows()])

    def test_a_desk_key_is_warned_off_them(self):
        for key in ("F12", "Ctrl+Alt+S"):
            with self.subTest(key=key):
                self.assertEqual(pctl.key_clashes({"toggle": [key]}),
                                 {("toggle", 0): "Open ⚙ Settings"})


if __name__ == "__main__":
    unittest.main()
