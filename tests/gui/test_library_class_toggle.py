"""The 📚 library pane's "only titles with a class" toggle.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_library_class_toggle -v

A title without a class tag is shown for every class by the class filter, so
a tester could not tell the tagged music apart. The toggle hides the untagged
competition titles; social dances, which have no classes, stay.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_classchk_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from planner.models import LIBRARY_CATEGORIES, MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_COL_TITLE = 3


def _entry(title, dance="LW", classes_ok=None):
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{title}.mp3"), title=title,
                      dance=dance, bpm=29, classes_ok=classes_ok)


_TAGGED = _entry("tagged", classes_ok=["B", "A", "S"])
_UNTAGGED = _entry("untagged")
_SOCIAL = _entry("salsa", dance=None)


class ClassOnlyToggleTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.pane.set_entries([_TAGGED, _UNTAGGED, _SOCIAL])

    def tearDown(self):
        reap_widget(self.pane)

    def _shown(self) -> set:
        t = self.pane._table
        return {t.item(r, _COL_TITLE).text() for r in range(t.rowCount())}

    def test_off_shows_everything(self):
        self.assertEqual(self._shown(), {"tagged", "untagged", "salsa"})

    def test_on_hides_the_untagged_competition_title(self):
        self.pane._class_only_chk.setChecked(True)
        self.assertEqual(self._shown(), {"tagged", "salsa"})

    def test_a_filter_jump_resets_it(self):
        self.pane._class_only_chk.setChecked(True)
        self.pane.focus_filter(dance="LW")
        self.assertFalse(self.pane._class_only_chk.isChecked())
        self.assertIn("untagged", self._shown())

    def test_the_category_picker_offers_no_class(self):
        combo = self.pane._cat_combo
        self.assertGreaterEqual(combo.findData("no_class"), 0)
        self.assertEqual(LIBRARY_CATEGORIES["no_class"][1], ())


if __name__ == "__main__":
    unittest.main()
