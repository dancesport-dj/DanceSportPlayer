"""The Title column shows the ID3 title tag, and a File name column beside it.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_title_file_columns -v

A tester wanted "only the title" in the Title column: until now it showed the
cleaned-up file name, so a name like "07 Moon River (LW 29) remaster" came out
as whatever the cleaner left of it. Title now shows the title tag and falls
back to the cleaned name when the tag is empty. The cleaned-up file name moves
to its own column at the end ("cleaned-up filename as column and title as
column"), hidden until ticked on in the header menu; its tooltip is the path.

Display only: `entry.title` still feeds matching and the duplicate keys.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_titlecol_"))

from PySide6.QtWidgets import QApplication

from dancesport_planner import RoundConfig
from gui.common import DEFAULT_HIDDEN_COLUMNS, display_title
from gui.dialogs import COLUMNS_VERSION, migrate_column_settings
from gui.library_browser import _LIB_COL_FILE, _LIB_COL_TITLE, LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import TableActionsMixin
from planner.models import MusicEntry
from shared.columns import (_COL_ALBUM, _COL_COMMENT, _COL_CUSTOM, _COL_FILE, _COL_PLAYS, _COL_REGEN,
                            _COL_TITLE)
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_PATH = Path(r"C:\music\tanzcds\standardcd\07 Moon River (LW 29) remaster.mp3")


def _entry(tag_title="Moon River", **kw):
    return MusicEntry(path=_PATH, title="Moon River remaster", dance="LW",
                      bpm=29, tag_title=tag_title, **kw)


class DisplayTitleTest(unittest.TestCase):

    def test_the_title_tag_wins(self):
        self.assertEqual(display_title(_entry()), "Moon River")

    def test_an_empty_tag_falls_back_to_the_cleaned_name(self):
        self.assertEqual(display_title(_entry(None)), "Moon River remaster")
        self.assertEqual(display_title(_entry("  ")), "Moon River remaster")

    def test_the_title_sort_follows_what_is_shown(self):
        key = TableActionsMixin._FLAT_SORT_KEYS[_COL_TITLE]
        self.assertEqual(key(_entry("Zebra")), "zebra")


class DeckColumnsTest(unittest.TestCase):

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

    def test_file_name_sits_behind_custom(self):
        self.assertEqual((_COL_CUSTOM, _COL_FILE, _COL_ALBUM), (10, 11, 12))
        self.assertEqual(self.table.horizontalHeaderItem(_COL_FILE).text(),
                         "Filename")

    def test_the_cells(self):
        self.assertEqual(self.table.item(self.row, _COL_TITLE).text(), "Moon River")
        cell = self.table.item(self.row, _COL_FILE)
        self.assertEqual(cell.text(), "Moon River remaster")
        self.assertEqual(cell.toolTip(), str(_PATH))

    def test_every_kind_starts_with_it_hidden(self):
        for kind, cols in DEFAULT_HIDDEN_COLUMNS.items():
            self.assertIn(_COL_FILE, cols, kind)

    def test_the_header_menu_offers_it(self):
        menu = self.table.build_column_menu()
        self.assertIn(_COL_FILE, [a.data() for a in menu.actions() if a.isCheckable()])


class LibraryColumnsTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.pane.set_entries([_entry()])

    def test_the_cells(self):
        t = self.pane._table
        self.assertEqual(t.item(0, _LIB_COL_TITLE).text(), "Moon River")
        self.assertEqual(_LIB_COL_FILE, 12)
        self.assertEqual(t.horizontalHeaderItem(_LIB_COL_FILE).text(), "Filename")
        self.assertEqual(t.item(0, _LIB_COL_FILE).text(), "Moon River remaster")
        self.assertEqual(self.pane.cell_tooltip(0, _LIB_COL_FILE), str(_PATH))

    def test_it_starts_hidden_and_can_be_ticked_on(self):
        self.assertIn(_LIB_COL_FILE, self.pane.hidden_columns())
        menu = self.pane.build_column_menu()
        self.assertIn(_LIB_COL_FILE,
                      [a.data() for a in menu.actions() if a.isCheckable()])


class MigrationTest(unittest.TestCase):
    """Settings saved with Custom already in (columns_version 3)."""

    def test_regen_moves_behind_file_name(self):
        s = {"columns_version": 3,
             "hidden_columns": {"playlist": [9, 10], "wishlist": [1, 11]},
             "column_widths": {"playlist": {"10": 90, "11": 30}}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [9, 10, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS],
                          "wishlist": [1, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {"10": 90, str(_COL_REGEN): 30})
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)

    def test_the_library_gets_it_at_the_end(self):
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9, 10, 11]
        s = {"columns_version": 3, "library_columns": list(order),
             "library_hidden_columns": [10, 11]}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], order + [12, 13, 14, 15])
        self.assertEqual(s["library_hidden_columns"], [10, 11, 12, 13, 14, 15])


if __name__ == "__main__":
    unittest.main()
