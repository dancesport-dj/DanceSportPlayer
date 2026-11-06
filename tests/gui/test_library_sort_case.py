"""The library's text columns sort without regard to case (review section 4).

`sorted()` on plain strings puts every capital before every small letter, so
"abba" landed behind "Zorba" in the Artist, Title, Album, Custom and File
columns (only Comment lowercased).
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sortcase_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import (
    LIB_COL_ALBUM,
    LIB_COL_CUSTOM,
    LIB_COL_FILE,
    LibraryBrowser,
)
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


def _entry(text: str) -> MusicEntry:
    e = MusicEntry(path=Path(rf"C:\music\{text}.mp3"), title=text, dance="LW")
    e.tag_artist = text
    e.tag_title = text
    e.tag_album = text
    e.custom = text
    return e


class SortCaseTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.small = _entry("abba")
        self.capital = _entry("Zorba")

    def check(self, col):
        key = self.pane._sort_key(col)
        self.assertLess(key(self.small), key(self.capital))

    def test_artist(self):
        self.check(2)

    def test_title(self):
        self.check(3)

    def test_album(self):
        self.check(LIB_COL_ALBUM)

    def test_custom(self):
        self.check(LIB_COL_CUSTOM)

    def test_file(self):
        self.check(LIB_COL_FILE)


if __name__ == "__main__":
    unittest.main()
