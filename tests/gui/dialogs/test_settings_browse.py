#!/usr/bin/env python3
"""📁 Settings "Browse…" writes the folder the way the setting already holds it.

Run:  py -m unittest tests.gui.dialogs.test_settings_browse -v

Qt's folder picker answers with forward slashes on Windows, and the window
compares the folder settings as strings: re-picking the music folder that is
already set counted as a change — a restart prompt and a global-library reset,
for the playlist folder a full relearn (BUG_REVIEW B4.5).
"""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit

from gui.dialogs import settings_dialog


class BrowseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_picked_folder_is_stored_in_the_platform_s_form(self):
        edit = QLineEdit(os.path.normpath("D:/Music/Latin"))
        with mock.patch.object(settings_dialog.QFileDialog, "getExistingDirectory",
                               return_value="D:/Music/Latin"):
            settings_dialog.SettingsDialog._browse(None, edit)
        self.assertEqual(edit.text(), os.path.normpath("D:/Music/Latin"))

    def test_an_added_folder_already_listed_is_not_added_again(self):
        """The folder lists' "Add…" goes through the same picker: a folder
        listed already came in a second time, slashes the other way round,
        and the list compared as changed."""
        for method, field in (("_add_remap_folder", "_remap_edit"),
                              ("_add_hidden_folder", "_hidden_edit"),
                              ("_add_ceremony_folder", "_ceremony_edit")):
            listed = os.path.normpath("D:/Music/Latin")
            dlg = SimpleNamespace(**{field: QPlainTextEdit(listed)})
            with mock.patch.object(settings_dialog.QFileDialog, "getExistingDirectory",
                                   return_value="D:/Music/Latin"):
                getattr(settings_dialog.SettingsDialog, method)(dlg)
            self.assertEqual(getattr(dlg, field).toPlainText(), listed, method)


if __name__ == "__main__":
    unittest.main()
