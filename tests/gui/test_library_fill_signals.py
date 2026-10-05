#!/usr/bin/env python3
"""🐌 Filling the library pane must not notify the platform 36 000 times.

Run:  py -m unittest tests.gui.test_library_fill_signals -v

`_populate` writes ten cells per track, and every `setItem` on a QTableWidget
emits `dataChanged`. With ~3 600 tracks in the library that is 36 380
notifications in one synchronous burst on the GUI thread. On Windows that is
merely wasteful; on macOS each one goes through the Cocoa accessibility
bridge, which allocates an Objective-C element per cell — and the app shows
the spinning ball while it does.

The rows are all written in one go, so the table is told once, at the end.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libfill_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner.models import MusicEntry  # noqa: E402
from gui.library_browser import LibraryBrowser  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

DANCES = ["LW", "TG", "WW", "SF", "QS", "CC", "SA", "RB", "PD", "JI"]


class LibraryFillSignalsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.lb = LibraryBrowser()
        self.addCleanup(reap_widget, self.lb)
        self.seen = []
        self.lb._table.model().dataChanged.connect(
            lambda tl, br, *_a: self.seen.append((tl.row(), br.row())))

    def entries(self, n: int) -> list:
        now = time.time()
        return [MusicEntry(
            path=Path(f"F:/my music/tanzcds/{DANCES[i % 10]}/T{i}.mp3"),
            title=f"Track {i}", dance=DANCES[i % 10], bpm=50, duration=195,
            popularity=i % 7, tag_artist=f"Artist {i}", added=now,
            classes_ok=["D"] if i % 2 else None) for i in range(n)]

    def test_the_whole_fill_is_one_notification(self):
        self.lb._populate(self.entries(120))
        self.assertEqual(len(self.seen), 1,
                         f"{len(self.seen)} dataChanged for 120 tracks")

    def test_it_covers_every_row_that_was_written(self):
        self.lb._populate(self.entries(120))
        self.assertEqual(self.seen[0], (0, 119))

    def test_an_empty_library_says_nothing_at_all(self):
        self.lb._populate([])
        self.assertEqual(self.seen, [])

    def test_the_rows_are_all_there_afterwards(self):
        """Quiet is worthless if the pane comes out blank."""
        self.lb._populate(self.entries(40))
        t = self.lb._table
        self.assertEqual(t.rowCount(), 40)
        self.assertEqual(t.item(0, 3).text(), "Track 0")
        self.assertEqual(t.item(39, 3).text(), "Track 39")
        self.assertEqual(t.item(7, 2).text(), "Artist 7")
        self.assertEqual(t.rowHeight(3), 22)

    def test_sorting_still_reads_the_rows_it_was_not_told_about(self):
        """The sort keys live in UserRole and are set while the model is quiet."""
        self.lb._populate(self.entries(30))
        t = self.lb._table
        t.sortItems(3)
        self.assertEqual(t.item(0, 3).text(), "Track 0")
        self.assertEqual(t.item(1, 3).text(), "Track 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
