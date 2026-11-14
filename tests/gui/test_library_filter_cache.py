"""📚 Filtering the library hides rows; it does not write the whole list again.

Run:  py -m unittest tests.gui.test_library_filter_cache -v

Marcel's list, 6.18: "The global library view reloads with a progress bar every
time, also after clearing a filter. Cache it." Every filter change emptied the
table and wrote the rows again; for the whole repository (54 000 titles) that is
~5 s and the "Listing the whole library" bar, on every keystroke that cleared the
box. The rows of one fill now stay, and a filter hides the ones it drops. A new
list, a sort, or a different ♊ marking still writes the rows again.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_filter_cache_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import gui.library_browser as library_browser
from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_TITLE = 3


def _entries(n=60, prefix="Title"):
    return [MusicEntry(path=Path(rf"C:\music\{prefix}{i:02d}.mp3"), title=f"{prefix} {i:02d}",
                       dance="LW", bpm=29) for i in range(n)]


class FilterCacheTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Every table counts, however small: the hide path is the only path.
        patch = mock.patch.object(library_browser, "_HIDE_MIN_ROWS", 0, create=True)
        patch.start()
        self.addCleanup(patch.stop)
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.b.resize(1000, 500)
        self.b.show()
        self.entries = _entries()
        self.b.set_entries(self.entries)
        self.app.processEvents()
        self.fill = mock.patch.object(self.b, "_fill_rows", wraps=self.b._fill_rows)
        self.fill_mock = self.fill.start()
        self.addCleanup(self.fill.stop)

    def type_filter(self, text):
        self.b._filter_edit.setText(text)
        self.b._filter_timer.stop()
        self.b._refilter()

    def visible(self):
        t = self.b._table
        return [str(self.b._row_path(r)) for r in range(t.rowCount()) if not t.isRowHidden(r)]

    def test_clearing_a_filter_writes_no_row_again(self):
        self.type_filter("Title 1")
        self.type_filter("")
        self.assertEqual(self.fill_mock.call_count, 0)
        self.assertEqual(len(self.visible()), 60)

    def test_the_same_filter_again_writes_no_row_again(self):
        self.type_filter("Title 1")
        self.type_filter("Title 1")
        self.assertEqual(self.fill_mock.call_count, 0)

    def test_a_filter_leaves_only_what_matches(self):
        self.type_filter("Title 1")
        want = [str(e.path) for e in self.entries if "Title 1" in e.title]
        self.assertEqual(self.visible(), want)
        self.assertEqual([str(e.path) for e in self.b._shown], want)
        self.assertIn(f"({len(want)}/60", self.b._count_lbl.text())

    def test_a_filter_with_no_match_shows_nothing(self):
        self.type_filter("zzz")
        self.assertEqual(self.visible(), [])
        self.type_filter("")
        self.assertEqual(len(self.visible()), 60)

    def test_a_hidden_row_is_not_selected_any_more(self):
        t = self.b._table
        t.selectRow(2)                     # Title 02, which the filter drops
        t.selectRow(11)                    # Title 11, which it keeps
        self.type_filter("Title 1")
        picked = {str(self.b._row_path(i.row())) for i in t.selectionModel().selectedRows()}
        self.assertEqual(picked, {str(self.entries[11].path)})

    def test_a_selection_comes_back_when_the_filter_still_holds_it(self):
        t = self.b._table
        t.selectRow(11)
        self.type_filter("Title 1")
        self.type_filter("")
        picked = {str(self.b._row_path(i.row())) for i in t.selectionModel().selectedRows()}
        self.assertEqual(picked, {str(self.entries[11].path)})

    def test_next_and_previous_step_over_hidden_rows(self):
        self.type_filter("Title 1")                       # 10..19
        t = self.b._table
        row = next(r for r in range(t.rowCount())
                   if str(self.b._row_path(r)) == str(self.entries[19].path))
        t.item(row, 0).setText("■")
        with mock.patch.object(self.b, "_start_row") as start:
            self.assertFalse(self.b.skip(1), "Title 19 is the last one shown")
            self.assertTrue(self.b.skip(-1))
        self.assertEqual(str(self.b._row_path(start.call_args.args[0])),
                         str(self.entries[18].path))
        t.item(row, 0).setText("▶")

    def test_a_new_list_writes_its_rows(self):
        self.b.set_entries(_entries(5, "Other"))
        self.assertGreater(self.fill_mock.call_count, 0)
        self.assertEqual(len(self.visible()), 5)
        self.assertTrue(all("Other" in p for p in self.visible()))

    def test_sorting_a_filtered_list_shows_the_filtered_rows_in_the_new_order(self):
        self.type_filter("Title 1")
        t = self.b._table
        t.horizontalHeader().setSortIndicator(_TITLE, Qt.SortOrder.DescendingOrder)
        self.app.processEvents()
        want = sorted((str(e.path) for e in self.entries if "Title 1" in e.title),
                      reverse=True)
        self.assertEqual(self.visible(), want)
        self.type_filter("")
        self.app.processEvents()
        self.assertEqual(self.visible(),
                         sorted((str(e.path) for e in self.entries), reverse=True))

    def test_a_sort_asked_for_writes_the_rows_in_that_order(self):
        t = self.b._table
        t.horizontalHeader().setSortIndicator(_TITLE, Qt.SortOrder.DescendingOrder)
        self.app.processEvents()
        self.assertGreater(self.fill_mock.call_count, 0)
        self.fill_mock.reset_mock()
        self.type_filter("Title 3")
        self.type_filter("")
        self.assertEqual(self.fill_mock.call_count, 0, "in the new order, the cache is good again")

    def test_a_tiny_list_keeps_writing_rows(self):
        with mock.patch.object(library_browser, "_HIDE_MIN_ROWS", 1000, create=True):
            self.b.set_entries(_entries(10, "Small"))
            self.fill_mock.reset_mock()
            self.type_filter("Small 0")
            self.assertGreater(self.fill_mock.call_count, 0)
            self.assertEqual(self.b._table.rowCount(), 10)


if __name__ == "__main__":
    unittest.main()
