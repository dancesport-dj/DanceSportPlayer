#!/usr/bin/env python3
"""📚 A filter that narrows the whole library is instant; a header click sorts.

Run:  py -m unittest tests.gui.test_library_sort_refill -v

Typing a filter over the whole repository (54 368 titles) froze the window
for ~1.2 s: emptying the table deleted 700 000 Python item wrappers, one per
cell, which PySide keeps for every item handed to setItem (the same wrappers
the 0.5 s gen-2 GC passes scan). The cells are now written through the model,
as plain C++ items: emptying the full table takes ~0.2 s. Qt's own sort can't
read those (it compares the shown text, "9" after "30"), so a header click
sorts the list in Python by each column's value and fills it again; a filter
keeps the chosen order, and the selection and the ■ marker stay put.
"""
import gc
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libsort_"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import gui.library_browser as library_browser
from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_PLAY, _TITLE, _BPM, _RATING = 0, 3, 4, library_browser.LIB_COL_RATING
ASC, DESC = Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder


def _entries(bpms):
    return [MusicEntry(path=Path(rf"C:\music\{i:05d}.mp3"), title=f"Title {i}",
                       dance="LW", bpm=b) for i, b in enumerate(bpms)]


class SortRefillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.t = self.b._table
        self.hh = self.t.horizontalHeader()

    def pump(self, turns=100):
        for _ in range(turns):
            QApplication.processEvents()

    def column(self, col, role=Qt.ItemDataRole.DisplayRole):
        return [self.t.item(r, col).data(role) for r in range(self.t.rowCount())]

    def test_a_full_table_leaves_no_python_wrapper_per_cell(self):
        entries = _entries([29] * 2000)
        # A first fill builds what the entries cache themselves (a Path's
        # parts list on its first str()), as the app's loaded library has.
        self.b._populate(entries)
        self.pump()
        self.b._populate([])
        gc.collect()
        before = len(gc.get_objects())
        self.b._populate(entries)
        self.pump()
        gc.collect()
        self.assertEqual(self.t.rowCount(), 2000)
        self.assertLess(len(gc.get_objects()) - before, 1000,
                        "13 cells per row once lived on as Python objects")

    def test_a_header_click_sorts_by_value_not_by_text(self):
        self.b._populate(_entries([30, 9, 29]))
        self.b.show()
        x = self.hh.sectionViewportPosition(_BPM) + 5
        QTest.mouseClick(self.hh.viewport(), Qt.MouseButton.LeftButton,
                         pos=QPoint(x, self.hh.height() // 2))
        self.assertEqual(self.column(_BPM), ["9", "29", "30"])
        QTest.mouseClick(self.hh.viewport(), Qt.MouseButton.LeftButton,
                         pos=QPoint(x, self.hh.height() // 2))
        self.assertEqual(self.column(_BPM), ["30", "29", "9"])

    def test_the_play_column_sorts_by_path_not_by_marker(self):
        self.b._populate(_entries([29, 30, 31]))
        self.b._start_row(1)
        self.hh.setSortIndicator(_PLAY, DESC)
        self.assertEqual([p.name for p in self.column(_PLAY, Qt.ItemDataRole.UserRole)],
                         ["00002.mp3", "00001.mp3", "00000.mp3"])

    def test_a_sort_mid_fill_sorts_the_whole_list(self):
        n = library_browser._FILL_FIRST + 3 * library_browser._FILL_CHUNK
        self.b._populate(_entries(range(1, n + 1)))
        self.hh.setSortIndicator(_BPM, DESC)
        self.pump()
        self.assertEqual(self.column(_BPM, Qt.ItemDataRole.UserRole),
                         list(range(n, 0, -1)))

    def test_a_filter_keeps_the_chosen_order(self):
        self.b._populate(_entries([29, 31, 30]))
        self.hh.setSortIndicator(_BPM, DESC)
        self.b._populate(_entries([28, 32]))
        self.assertEqual(self.column(_BPM), ["32", "28"])

    def test_equal_values_keep_their_order(self):
        self.b._populate(_entries([29, 30, 29, 30]))
        self.hh.setSortIndicator(_BPM, DESC)
        self.assertEqual(self.column(_TITLE),
                         ["Title 1", "Title 3", "Title 0", "Title 2"])

    def test_the_selection_and_the_playing_marker_survive_a_sort(self):
        self.b._populate(_entries([29, 31, 30]))
        self.t.selectRow(0)
        self.b._start_row(2)
        self.hh.setSortIndicator(_BPM, DESC)
        self.assertEqual(self.column(_BPM), ["31", "30", "29"])
        self.assertEqual([i.row() for i in self.t.selectionModel().selectedRows()], [2])
        self.assertEqual(self.b.current_play_row(), 1)

    def test_a_rating_change_shows_in_its_cell(self):
        entries = _entries([29, 30])
        self.b.set_entries(entries)
        entries[1].rating = 4
        self.b.show_tag_cells([entries[1].path])
        self.assertEqual(self.column(_RATING, library_browser.RATING_ROLE), [0, 4])

    def test_an_unsorted_table_keeps_the_library_order(self):
        with mock.patch.object(library_browser, "_FILL_BUDGET", 0.0):
            self.b._populate(_entries([31, 29, 30]))
        self.assertEqual(self.hh.sortIndicatorSection(), -1)
        self.assertEqual(self.column(_BPM), ["31", "29", "30"])


if __name__ == "__main__":
    unittest.main()
