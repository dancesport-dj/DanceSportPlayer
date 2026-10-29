#!/usr/bin/env python3
"""🔍 The library search finds a title by its file name too.

Run:  py -m unittest tests.gui.test_library_search_filename -v

The card, the log and the deck all name a title by its file, so that is what
gets typed. `17 Espana Cani (PD 60)gep.mp3` reads "Espana Cani gep" as its
title and "Espana Cani (PD 60) gepitch" as its tag — neither holds the file's
own name, and the search found nothing.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libsearch_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


class FileNameSearchTest(unittest.TestCase):
    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        e = MusicEntry(path=Path(r"F:\m\lateincd\17 Espana Cani (PD 60)gep.mp3"),
                       title="Espana Cani gep", dance="PD", bpm=60)
        e.tag_title = "Espana Cani (PD 60) gepitch"
        e.tag_artist = "André Rieu"
        other = MusicEntry(path=Path(r"F:\m\lateincd\13 Spanish Gipsy Dance (PD 60).mp3"),
                           title="Spanish Gipsy Dance", dance="PD", bpm=60)
        self.b.set_entries([e, other])
        _app.processEvents()

    def _shown(self, text: str) -> int:
        self.b._filter_edit.setText(text)
        self.b._refilter()
        return self.b._table.rowCount()

    def test_the_file_name_finds_the_title(self):
        self.assertEqual(self._shown("17 Espana Cani (PD 60)gep"), 1)

    def test_any_case_of_it_does(self):
        self.assertEqual(self._shown("17 espana cani (pd 60)GEP"), 1)

    def test_the_title_still_does(self):
        self.assertEqual(self._shown("Spanish Gipsy"), 1)


if __name__ == "__main__":
    unittest.main()
