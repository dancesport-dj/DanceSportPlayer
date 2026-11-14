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

from PySide6.QtCore import QEvent, QItemSelectionModel, QPoint, Qt
from PySide6.QtGui import QContextMenuEvent, QKeyEvent
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

    def test_the_selection_stays_where_the_next_title_slid_up(self):
        # Sending titles to the end one after another: the focus must not follow
        # the moved title to the end, it stays on the row the next one now holds.
        t = self.party("A", "B", "C", "D")
        place = self.row_of(t, "A")
        self.menu(t, place, pick=ONE)
        self.assertEqual(self.titles(t), ["B", "C", "D", "A"])
        self.assertEqual({ix.row() for ix in t.selectedIndexes()}, {place})
        self.assertEqual(t.currentRow(), place)

    def test_a_selection_moved_leaves_the_focus_at_the_first_place(self):
        t = self.party("A", "B", "C", "D")
        first = self.row_of(t, "A")
        t.selectRow(first)
        t.selectionModel().select(
            t.model().index(self.row_of(t, "C"), 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        self.menu(t, self.row_of(t, "C"), pick=TWO)
        self.assertEqual({ix.row() for ix in t.selectedIndexes()}, {first})
        self.assertEqual(t._row_meta[first].entry.title, "B")

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


class ShortcutTest(_Base):
    """Alt+End sends the selected title(s) last, like the menu entry."""

    @staticmethod
    def press(t, key=Qt.Key.Key_End, mods=Qt.KeyboardModifier.AltModifier):
        t.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, mods))

    def test_alt_end_sends_the_selected_title_last(self):
        t = self.party("A", "B", "C")
        t.selectRow(self.row_of(t, "A"))
        self.press(t)
        self.assertEqual(self.titles(t), ["B", "C", "A"])
        self.assertEqual(t.currentRow(), self.row_of(t, "B"))

    def test_alt_end_works_in_a_wishlist(self):
        t = self.wishlist("A", "B", "C")
        t.selectRow(self.row_of(t, "B"))
        self.press(t)
        self.assertEqual(self.titles(t), ["A", "C", "B"])

    def test_alt_end_on_the_last_title_does_nothing(self):
        t = self.party("A", "B")
        t.selectRow(self.row_of(t, "B"))
        self.press(t)
        self.assertEqual(self.titles(t), ["A", "B"])

    def test_end_alone_is_not_the_shortcut(self):
        t = self.party("A", "B", "C")
        t.selectRow(self.row_of(t, "A"))
        self.press(t, mods=Qt.KeyboardModifier.NoModifier)
        self.assertEqual(self.titles(t), ["A", "B", "C"])

    def test_the_menu_entry_shows_the_key(self):
        t = self.party("A", "B", "C")
        shown = {}

        class _Menu(QMenu):
            def exec(self, *_a):
                shown.update({a.text(): a.shortcut().toString() for a in self.actions()})
                return None

        pos = QPoint(5, t.rowViewportPosition(self.row_of(t, "A")) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertEqual(shown[ONE], "Alt+End")

    def test_the_desk_cannot_take_the_key(self):
        from planner.playing import controller as pctl
        self.assertIn("Alt+End", pctl.RESERVED_KEYS)


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
