"""An Album column in the decks and the library pane, hidden until asked for.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_album_column -v

The ID3 album tag was already read and cached (`tag_album`) but only shown in
the hover info. It gets its own column: in the decks at 12 in front of ↺ (which
moves to 13), in the library at 13. Like ★, Custom and File name it starts
hidden and is ticked on in the header menu.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_albumcol_"))

from PySide6.QtWidgets import QApplication

from dancesport_planner import RoundConfig
from gui.common import DEFAULT_HIDDEN_COLUMNS
from gui.library_browser import _LIB_COL_ALBUM, LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import TableActionsMixin
from planner.models import MusicEntry
from shared.columns import _COL_ALBUM, _COL_FILE, _COL_REGEN
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_PATH = Path(r"C:\music\tanzcds\standardcd\07 Moon River (LW 29).mp3")


def _entry(album="Strictly Ballroom 3", **kw):
    return MusicEntry(path=_PATH, title="Moon River", dance="LW", bpm=29,
                      tag_album=album, **kw)


class DeckAlbumTest(unittest.TestCase):

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

    def test_album_sits_behind_file_name(self):
        self.assertEqual((_COL_FILE, _COL_ALBUM), (11, 12))
        self.assertEqual(self.table.horizontalHeaderItem(_COL_ALBUM).text(), "Album")
        self.assertEqual(self.table.horizontalHeaderItem(_COL_REGEN).text(), "↺")

    def test_the_cell_shows_the_album_tag(self):
        self.assertEqual(self.table.item(self.row, _COL_ALBUM).text(),
                         "Strictly Ballroom 3")

    def test_every_kind_starts_with_it_hidden(self):
        for kind, cols in DEFAULT_HIDDEN_COLUMNS.items():
            self.assertIn(_COL_ALBUM, cols, kind)

    def test_the_header_menu_offers_it(self):
        menu = self.table.build_column_menu()
        self.assertIn(_COL_ALBUM, [a.data() for a in menu.actions() if a.isCheckable()])

    def test_it_sorts_by_album_then_title(self):
        key = TableActionsMixin._FLAT_SORT_KEYS[_COL_ALBUM]
        self.assertLess(key(_entry("abba gold")), key(_entry("Zumba Hits")))
        self.assertEqual(key(_entry(None)), ("", "moon river"))


class LibraryAlbumTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.pane.set_entries([_entry()])

    def test_the_cell(self):
        t = self.pane._table
        self.assertEqual(_LIB_COL_ALBUM, 13)
        self.assertGreaterEqual(t.columnCount(), 14)
        self.assertEqual(t.horizontalHeaderItem(_LIB_COL_ALBUM).text(), "Album")
        self.assertEqual(t.item(0, _LIB_COL_ALBUM).text(), "Strictly Ballroom 3")

    def test_it_starts_hidden_and_can_be_ticked_on(self):
        self.assertIn(_LIB_COL_ALBUM, self.pane.hidden_columns())
        menu = self.pane.build_column_menu()
        self.assertIn(_LIB_COL_ALBUM,
                      [a.data() for a in menu.actions() if a.isCheckable()])


if __name__ == "__main__":
    unittest.main()
