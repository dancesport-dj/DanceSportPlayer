"""A Comment column in the decks and the library pane, hidden until asked for.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_comment_column -v

A Mac tester wanted the comment as UltraMixer shows it ('vocal AS'): the text
as the file has it (`tag_comment`), not the classes and markers the app reads
out of it. It sits in the decks at 13 in front of ↺ (which moves to 14), in the
library at 14. Like Album it starts hidden and is ticked on in the header menu.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_commentcol_"))

from PySide6.QtWidgets import QApplication

from dancesport_planner import RoundConfig
from gui.common import DEFAULT_HIDDEN_COLUMNS
from gui.dialogs import migrate_column_settings
from gui.library_browser import _LIB_COL_COMMENT, LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import TableActionsMixin
from planner.models import MusicEntry
from shared.columns import _COL_ALBUM, _COL_COMMENT, _COL_REGEN, _N_COLS
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_PATH = Path(r"C:\music\tanzcds\standardcd\SW29_Lady Hear Me Tonight_DJ Maksy.mp3")


def _entry(comment="vocal AS", **kw):
    return MusicEntry(path=_PATH, title="Lady Hear Me Tonight", dance="LW", bpm=29,
                      tag_comment=comment, **kw)


class DeckCommentTest(unittest.TestCase):

    def setUp(self):
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.entry = _entry()
        self.table.load({"Final": [[self.entry]]}, ["LW"],
                        [RoundConfig(name="Final", heats=1, tier="final")], "S",
                        play_cb=lambda *_: None, suggester=None,
                        use_timbre=False, style="Standard")
        self.row = next(r for r, m in enumerate(self.table._row_meta)
                        if m and m.entry is self.entry)

    def test_comment_sits_between_album_and_regen(self):
        self.assertEqual((_COL_ALBUM, _COL_COMMENT, _COL_REGEN, _N_COLS),
                         (12, 13, 14, 15))
        self.assertEqual(self.table.horizontalHeaderItem(_COL_COMMENT).text(), "Comment")
        self.assertEqual(self.table.horizontalHeaderItem(_COL_REGEN).text(), "↺")

    def test_the_cell_shows_the_comment_as_written(self):
        it = self.table.item(self.row, _COL_COMMENT)
        self.assertEqual(it.text(), "vocal AS")
        self.assertEqual(it.toolTip(), "vocal AS")

    def test_every_kind_starts_with_it_hidden(self):
        for kind, cols in DEFAULT_HIDDEN_COLUMNS.items():
            self.assertIn(_COL_COMMENT, cols, kind)

    def test_the_header_menu_offers_it(self):
        menu = self.table.build_column_menu()
        self.assertIn(_COL_COMMENT, [a.data() for a in menu.actions() if a.isCheckable()])

    def test_it_sorts_by_comment_then_title(self):
        key = TableActionsMixin._FLAT_SORT_KEYS[_COL_COMMENT]
        self.assertLess(key(_entry("instr")), key(_entry("Vocal AS")))
        self.assertEqual(key(_entry(None)), ("", "lady hear me tonight"))


class LibraryCommentTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.pane.set_entries([_entry()])

    def test_the_cell(self):
        t = self.pane._table
        self.assertEqual(_LIB_COL_COMMENT, 14)
        self.assertEqual(t.columnCount(), 15)
        self.assertEqual(t.horizontalHeaderItem(_LIB_COL_COMMENT).text(), "Comment")
        self.assertEqual(t.item(0, _LIB_COL_COMMENT).text(), "vocal AS")
        self.assertEqual(self.pane.cell_tooltip(0, _LIB_COL_COMMENT), "vocal AS")

    def test_it_starts_hidden_and_can_be_ticked_on(self):
        self.assertIn(_LIB_COL_COMMENT, self.pane.hidden_columns())
        menu = self.pane.build_column_menu()
        self.assertIn(_LIB_COL_COMMENT,
                      [a.data() for a in menu.actions() if a.isCheckable()])


class SavedLayoutTest(unittest.TestCase):
    """Settings saved with Album already in (columns_version 5)."""

    def test_comment_comes_in_hidden_in_front_of_regen(self):
        s = {"columns_version": 5,
             "hidden_columns": {"playlist": [1, 12], "wishlist": [13]},
             "column_widths": {"playlist": {"12": 180, "13": 30}},
             "library_columns": list(range(14)), "library_hidden_columns": [13]}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [1, _COL_ALBUM, _COL_COMMENT],
                          "wishlist": [_COL_COMMENT, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {str(_COL_ALBUM): 180, str(_COL_REGEN): 30})
        self.assertEqual(s["library_columns"], list(range(15)))
        self.assertEqual(s["library_hidden_columns"], [13, 14])

    def test_a_dragged_deck_order_is_kept(self):
        """A deck order names every column, so one saved before Comment would
        be thrown away whole; it gets Comment in front of ↺ instead."""
        order = [0, 3, 4, 12, 2, 1, 5, 6, 7, 8, 9, 10, 11, 13]
        s = {"columns_version": 5, "column_order": {"playlist": order}}
        migrate_column_settings(s)
        self.assertEqual(s["column_order"]["playlist"],
                         [0, 3, 4, 12, 2, 1, 5, 6, 7, 8, 9, 10, 11, 13, 14])


if __name__ == "__main__":
    unittest.main()
