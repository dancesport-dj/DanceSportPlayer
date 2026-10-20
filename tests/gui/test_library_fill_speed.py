"""⏱ Filling the library browser builds no hover texts and sets no row heights.

Run:  py -m unittest tests.gui.test_library_fill_speed -v

Marcel: "can we make it faster?" — the fill of the whole repository (54 414
titles) blocked the window ~20 s. Profiled: ~9 s went into hover texts built
for every cell up front (the rich title/artist text twice per row, the BPM
source, 490 000 setToolTip calls) and 2.4 s into one setRowHeight per row. A
hover text is now built for the one cell the mouse rests on, and the rows take
the table's default height. The cyclic GC rests while the rows fill: it kept
sweeping the 700 000 fresh item wrappers, ~1 s of the rest.
"""
import gc
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QEvent
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication

import gui.library_browser as library_browser
from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_TITLE = 3


def _entries(n=3):
    return [MusicEntry(path=Path(rf"C:\music\{i}.mp3"), title=f"Title {i}", dance="LW",
                       bpm=29) for i in range(n)]


class FillSpeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.b = LibraryBrowser()
        self.b.resize(900, 400)
        self.addCleanup(reap_widget, self.b)

    def test_filling_builds_no_hover_text(self):
        with mock.patch.object(library_browser, "_entry_tooltip", return_value="") as rich, \
                mock.patch.object(library_browser, "bpm_tooltip", return_value="") as bpm:
            self.b.set_entries(_entries(3))
            self.assertEqual((rich.call_count, bpm.call_count), (0, 0))
            self.b.cell_tooltip(1, _TITLE)
            self.assertEqual(rich.call_args.args[0].title, "Title 1",
                             "built on demand, for the row asked about")

    def test_every_row_is_22_px_high(self):
        self.b.set_entries(_entries(5))
        t = self.b._table
        self.assertEqual([t.rowHeight(r) for r in range(5)], [22] * 5)

    def test_hovering_a_cell_shows_its_text(self):
        self.b.set_entries(_entries(3))
        self.b.show()
        t = self.b._table
        pos = t.visualRect(t.model().index(2, _TITLE)).center()
        ev = QHelpEvent(QEvent.Type.ToolTip, pos, t.viewport().mapToGlobal(pos))
        with mock.patch.object(library_browser.QToolTip, "showText") as show:
            QApplication.sendEvent(t.viewport(), ev)
        self.assertTrue(show.called, "no tooltip shown")
        self.assertIn("Title 2", show.call_args.args[1])

    def test_a_sorted_table_still_names_the_row_under_the_mouse(self):
        self.b.set_entries(_entries(3))
        t = self.b._table
        t.horizontalHeader().setSortIndicator(_TITLE, library_browser.Qt.SortOrder.DescendingOrder)
        self.assertIn("Title 2", self.b.cell_tooltip(0, _TITLE))

    def test_a_cell_without_text_leaves_the_table_help(self):
        self.b.set_entries(_entries(1))
        self.b.show()
        t = self.b._table
        pos = t.visualRect(t.model().index(0, 5)).center()   # ⏱ length: no hover text
        ev = QHelpEvent(QEvent.Type.ToolTip, pos, t.viewport().mapToGlobal(pos))
        with mock.patch.object(library_browser.QToolTip, "showText") as show:
            QApplication.sendEvent(t.viewport(), ev)
        texts = [c.args[1] for c in show.call_args_list]
        self.assertNotIn("Title 0", " ".join(texts))
        self.assertEqual(self.b.cell_tooltip(0, 5), "")

    def test_the_cyclic_gc_rests_only_while_the_rows_fill(self):
        seen = []
        real = LibraryBrowser._fill_rows

        def spy(pane, *a):
            seen.append(gc.isenabled())
            real(pane, *a)

        with mock.patch.object(LibraryBrowser, "_fill_rows", spy):
            self.b.set_entries(_entries(3))
        self.assertEqual(seen, [False])
        self.assertTrue(gc.isenabled())

    def test_a_failing_fill_turns_the_gc_back_on(self):
        with mock.patch.object(LibraryBrowser, "_fill_rows", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.b.set_entries(_entries(3))
        self.assertTrue(gc.isenabled())

    def test_outside_the_rows_there_is_no_text(self):
        self.b.set_entries(_entries(1))
        self.assertEqual(self.b.cell_tooltip(7, _TITLE), "")
        self.assertEqual(self.b.cell_tooltip(-1, _TITLE), "")


if __name__ == "__main__":
    unittest.main()
