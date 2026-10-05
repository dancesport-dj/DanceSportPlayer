#!/usr/bin/env python3
"""Tests for window titles that would show the icon twice.

Run:  py -m unittest tests.gui.test_window_title_icon -v

Windows paints the app icon at the left of every title bar. A title that also
starts with an emoji ("⚙  Settings", "🎵 Music speed") put two pictures side
by side there. The emoji stays on the buttons that open those windows; only
the title loses it.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_title_"))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

from gui.common import install_plain_title_hook, plain_title  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class PlainTitleTest(unittest.TestCase):
    def test_leading_emoji_goes(self):
        self.assertEqual(plain_title("⚙  Settings"), "Settings")
        self.assertEqual(plain_title("🎵 Music speed"), "Music speed")
        self.assertEqual(plain_title("🖥️  Presenter — DancePlaylist"),
                         "Presenter — DancePlaylist")

    def test_plain_titles_stay(self):
        for title in ("Settings", "Similar to: 🎵 Samba", "3 files", ""):
            self.assertEqual(plain_title(title), title)

    def test_an_emoji_alone_stays(self):
        self.assertEqual(plain_title("🎉"), "🎉")


class TitleHookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.hook = install_plain_title_hook()

    @classmethod
    def tearDownClass(cls):
        cls.app.removeEventFilter(cls.hook)

    def test_dialog_title_loses_the_emoji(self):
        dlg = QDialog()
        self.addCleanup(reap_widget, dlg)
        dlg.setWindowTitle("⚙  Settings")
        self.assertEqual(dlg.windowTitle(), "Settings")

    def test_message_box_title_loses_the_emoji(self):
        box = QMessageBox()
        self.addCleanup(reap_widget, box)
        box.setWindowTitle("📂  Import — track paths")
        self.assertEqual(box.windowTitle(), "Import — track paths")

    def test_owned_dialog_title_loses_the_emoji(self):
        dlg = QDialog()
        self.addCleanup(reap_widget, dlg)
        child = QDialog(dlg)                 # a dialog is a window even with a parent
        child.setWindowTitle("🎵 Music speed")
        self.assertEqual(child.windowTitle(), "Music speed")


if __name__ == "__main__":
    unittest.main()
