"""Send a title to the end of its list from the context menu.

Run:  py -m unittest tests.gui.table.test_move_to_end -v

Marcel's list, 6.5: "Add a context menu entry to put a title at the end of the
list." A list with an order of its own has an end. A grid has heats and dances,
and a title there has no way out of its slot but a swap.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_to_end_"))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

ONE = "⬇  Move to the end of the list"
TWO = "⬇  Move 2 selected titles to the end"


def _e(title, dance="LW"):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance=dance,
                      duration=150)


class _Base(unittest.TestCase):

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def party(self, *titles, running_order=False):
        t = self.table()
        t.load_warmup([_e(x) for x in titles], "Party", "Standard", "S", False,
                      mock.Mock(), None, running_order=running_order)
        return t

    def wishlist(self, *titles):
        t = self.table()
        t.load_wishlist([_e(x) for x in titles], mock.Mock(), None)
        return t

    @staticmethod
    def titles(t):
        return [e.title for e in t._row_meta.entries()]

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in t._row_meta.numbered() if m.entry.title == title)

    def menu(self, t, row, pick=None):
        """The menu's texts on `row`; `pick` is chosen from it."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen


class ListsWithAnOrderTest(_Base):

    def test_a_party_title_goes_last(self):
        t = self.party("A", "B", "C")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertEqual(self.titles(t), ["B", "C", "A"])

    def test_a_free_order_title_goes_last(self):
        t = self.party("A", "B", "C", running_order=True)
        self.menu(t, self.row_of(t, "B"), pick=ONE)
        self.assertEqual(self.titles(t), ["A", "C", "B"])

    def test_a_wishlist_title_goes_last(self):
        t = self.wishlist("A", "B", "C")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertEqual(self.titles(t), ["B", "C", "A"])

    def test_a_selection_goes_last_in_the_order_it_stood(self):
        t = self.party("A", "B", "C", "D")
        t.selectRow(self.row_of(t, "A"))
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(self.row_of(t, "C"))
        self.menu(t, self.row_of(t, "C"), pick=TWO)
        self.assertEqual(self.titles(t), ["B", "D", "A", "C"])

    def test_the_moved_title_stays_selected(self):
        t = self.party("A", "B", "C")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertEqual({ix.row() for ix in t.selectedIndexes()},
                         {self.row_of(t, "A")})

    def test_the_play_marker_goes_along(self):
        t = self.party("A", "B", "C")
        t._current_play_row = self.row_of(t, "A")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertEqual(self.titles(t), ["B", "C", "A"])
        self.assertEqual(t._current_play_row, self.row_of(t, "A"))

    def test_the_title_already_last_has_no_entry(self):
        t = self.party("A", "B")
        self.assertNotIn(ONE, self.menu(t, self.row_of(t, "B")))

    def test_a_selection_already_last_has_no_entry(self):
        t = self.party("A", "B", "C")
        t.selectRow(self.row_of(t, "B"))
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(self.row_of(t, "C"))
        self.assertNotIn(TWO, self.menu(t, self.row_of(t, "C")))


class GridTest(_Base):

    def test_a_grid_has_no_end_to_go_to(self):
        t = self.table()
        playlist = {"Final": [[_e("A"), _e("B", "TG")]]}
        rounds = [RoundConfig(name="Final", heats=1, tier="final")]
        t.load(playlist, ["LW", "TG"], rounds, "S", mock.Mock(), suggester=None,
               use_timbre=False, style="Standard", dynamic=True, capacity=[1, 1])
        self.assertNotIn(ONE, self.menu(t, self.row_of(t, "A")))


if __name__ == "__main__":
    unittest.main()
