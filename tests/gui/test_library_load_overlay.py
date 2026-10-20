#!/usr/bin/env python3
"""🌐 What the library browser is loading shows on its table, not in a dialog.

Run:  py -m unittest tests.gui.test_library_load_overlay -v

Marcel: "a progess bar overlay over the table object / instead of table so it
is clear what loades at not blocking other things". While the whole library
loads in the background a cover with a busy bar hides the favorites under it;
while its rows are written a strip at the table's foot counts them, and
clicks go through it to the rows already there.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_liboverlay_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import gui.library_browser as library_browser
from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_TRANSPARENT = Qt.WidgetAttribute.WA_TransparentForMouseEvents


def _entries(n, prefix="repo"):
    return [MusicEntry(path=Path(rf"C:\{prefix}\{i:05d}.mp3"), title=f"T {i}",
                       dance="LW", bpm=29) for i in range(n)]


class LoadOverlayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.b.resize(700, 500)
        self.b.show()
        self.b.set_entries(_entries(3, "favs"))
        self.o = self.b._overlay
        self.vp = self.b._table.viewport()

    def pump(self, turns=50):
        for _ in range(turns):
            QApplication.processEvents()

    def big_fill(self):
        """A fill that takes several steps and is "long" from the start."""
        n = library_browser._FILL_FIRST + 3 * library_browser._FILL_CHUNK
        patches = (mock.patch.object(library_browser, "_FILL_BUDGET", 0.0),
                   mock.patch.object(library_browser, "_PROGRESS_AFTER", 0.0))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return n

    def test_waiting_for_the_whole_library_covers_the_table(self):
        self.b.show_whole_loading(True)
        self.assertTrue(self.o.isVisible())
        self.assertEqual(self.o.geometry(), self.vp.geometry())
        self.assertIn("Loading the whole library", self.o.label.text())
        self.assertEqual(self.o.bar.maximum(), 0, "a busy bar: the loader tells no count")
        self.assertFalse(self.o.testAttribute(_TRANSPARENT),
                         "the favorites under it are not what was asked for")

    def test_the_cover_goes_when_the_wait_ends(self):
        self.b.show_whole_loading(True)
        self.b.show_whole_loading(False)
        self.assertFalse(self.o.isVisible())

    def test_the_cover_follows_the_table_when_it_is_resized(self):
        self.b.show_whole_loading(True)
        self.b.resize(900, 650)
        self.pump()
        self.assertEqual(self.o.geometry(), self.vp.geometry())

    def test_a_long_fill_counts_its_rows_at_the_foot_of_the_table(self):
        n = self.big_fill()
        self.b.set_whole_entries(_entries(n))
        self.assertTrue(self.o.isVisible())
        self.assertIn(f"{library_browser._FILL_FIRST:,} / {n:,}", self.o.label.text())
        self.assertIn("whole library", self.o.label.text())
        self.assertEqual((self.o.bar.value(), self.o.bar.maximum()),
                         (library_browser._FILL_FIRST, n))
        vp = self.vp.geometry()
        self.assertEqual(self.o.geometry().bottom(), vp.bottom())
        self.assertLess(self.o.height(), vp.height() // 3)
        self.assertTrue(self.o.testAttribute(_TRANSPARENT),
                        "clicks go through to the rows already written")

    def test_the_strip_goes_when_the_last_row_is_in(self):
        n = self.big_fill()
        self.b.set_whole_entries(_entries(n))
        self.pump()
        self.assertEqual(self.b._table.rowCount(), n)
        self.assertFalse(self.o.isVisible())

    def test_a_short_fill_never_shows_it(self):
        self.b.set_entries(_entries(library_browser._FILL_FIRST + 10, "favs"))
        self.assertFalse(self.o.isVisible())
        self.pump()
        self.assertFalse(self.o.isVisible())

    def test_a_fill_under_the_cover_leaves_the_cover(self):
        # A favorites rescan finishing while 🌐 waits must not swap the cover
        # for its strip, nor take it away when it is done.
        n = self.big_fill()
        self.b.show_whole_loading(True)
        self.b.set_entries(_entries(n, "favs"))
        self.pump()
        self.assertTrue(self.o.isVisible())
        self.assertEqual(self.o.geometry(), self.vp.geometry())
        self.assertIn("Loading the whole library", self.o.label.text())

    def test_the_whole_library_arriving_turns_the_cover_into_the_strip(self):
        n = self.big_fill()
        self.b.show_whole_loading(True)
        self.b.show_whole_loading(False)
        self.b.set_whole_entries(_entries(n))
        self.assertTrue(self.o.isVisible())
        self.assertLess(self.o.height(), self.vp.height() // 3)


if __name__ == "__main__":
    unittest.main()
