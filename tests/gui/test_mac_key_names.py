#!/usr/bin/env python3
"""A Mac names the key it has: Qt's Control is ⌘ there, and every text said Ctrl.

Run:  py -m unittest tests.gui.test_mac_key_names -v

`sys.platform` is patched: this checks the texts, it has not run on macOS. The
key itself needs nothing, Ctrl+F in `table_actions.py` already answers to ⌘ F.
"""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gui.dialogs.shortcuts import shortcut_sheet_html
from planner import i18n
from tests.gui.table.test_context_menu_dispatch import ContextMenuDispatchTest


def on_a_mac():
    return mock.patch.object(sys, "platform", "darwin")


class CheatSheetKeyNamesTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_a_mac_reads_cmd_on_every_row(self):
        with on_a_mac():
            html = shortcut_sheet_html()
        self.assertIn("Cmd + F", html)
        self.assertNotIn("Ctrl", html)

    def test_a_german_mac_too(self):
        i18n.set_active("de")
        with on_a_mac():
            html = shortcut_sheet_html()
        self.assertIn("Cmd + F", html)
        self.assertNotIn("Strg", html)

    def test_windows_keeps_ctrl(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertIn("Ctrl + F", shortcut_sheet_html())


class FindMenuKeyNameTest(ContextMenuDispatchTest):

    def find_entry(self):
        t = self._warmup()
        entries, _ = self._open(t, t._row_meta.song_rows()[0])
        return next(text for text, _on in entries if text.startswith("🔍"))

    def test_the_menu_names_cmd_on_a_mac(self):
        with on_a_mac():
            self.assertTrue(self.find_entry().endswith("\tCmd+F"))

    def test_the_menu_names_ctrl_elsewhere(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertTrue(self.find_entry().endswith("\tCtrl+F"))


def load_tests(loader, _tests, _pattern):
    """Not the inherited tests: `FindMenuKeyNameTest` only borrows their window."""
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(CheatSheetKeyNamesTest))
    suite.addTests(FindMenuKeyNameTest(name) for name in
                   ("test_the_menu_names_cmd_on_a_mac", "test_the_menu_names_ctrl_elsewhere"))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
