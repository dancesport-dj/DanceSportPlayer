#!/usr/bin/env python3
"""❔ F1 — a search field over the cheat sheet.

Run:  py -m unittest tests.gui.test_shortcuts_search -v

Marcel: "the key shortcut dialog make searchable to easily find the searched
mapping". Fifty-odd rows in three sections; typing a word keeps the rows
whose key or description holds it — in the language the sheet is shown in —
and the heading of every section that still has a row. The field has the
focus when the sheet opens, so F1 and typing is all it takes.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_keys_search_"))

from PySide6.QtWidgets import QApplication, QLineEdit, QTextBrowser

from gui.dialogs.shortcuts import shortcut_sheet_html, shortcuts_dialog
from planner import i18n
from tests.qt_test_support import reap_widget


class SheetFilterTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_no_query_is_the_whole_sheet(self):
        self.assertEqual(shortcut_sheet_html(), shortcut_sheet_html(query=""))

    def test_a_word_keeps_its_rows_and_their_heading(self):
        html = shortcut_sheet_html(query="tempo")
        self.assertIn("Tempo up", html)
        self.assertIn("Keyboard", html)
        self.assertNotIn("Save the focused playlist", html)
        self.assertNotIn("Mouse", html, "a section without a match keeps no heading")

    def test_the_key_half_is_searched_too_and_case_does_not_matter(self):
        html = shortcut_sheet_html(query="f11")
        self.assertIn("Fullscreen on / off", html)
        self.assertNotIn("This cheat sheet", html)

    def test_it_searches_the_language_on_screen(self):
        i18n.set_active("de")
        html = shortcut_sheet_html(query="speichern")
        self.assertIn(i18n.t("Save the focused playlist / wishlist as M3U"), html)

    def test_nothing_found_says_so(self):
        html = shortcut_sheet_html(query="zzzz")
        self.assertIn("Nothing found", html)


class SearchFieldTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_typing_filters_the_sheet(self):
        dlg = shortcuts_dialog(None)
        self.addCleanup(reap_widget, dlg)
        field = dlg.findChild(QLineEdit)
        browser = dlg.findChild(QTextBrowser)
        self.assertIn("Save the focused playlist", browser.toPlainText())
        field.setText("tempo")
        self.assertIn("Tempo up", browser.toPlainText())
        self.assertNotIn("Save the focused playlist", browser.toPlainText())
        field.clear()
        self.assertIn("Save the focused playlist", browser.toPlainText())

    def test_the_field_takes_the_typing_first(self):
        dlg = shortcuts_dialog(None)
        self.addCleanup(reap_widget, dlg)
        dlg.show()
        self.app.processEvents()
        self.assertIs(dlg.focusWidget(), dlg.findChild(QLineEdit))


if __name__ == "__main__":
    unittest.main()
