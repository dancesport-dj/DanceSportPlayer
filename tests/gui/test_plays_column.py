"""🔁 A Plays column in the decks: how often the title played in the last 24 h.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_plays_column -v

A tester wanted to see how often a title has played today, in any list, as a
column to tick on, with a reset. It sits in the decks at 14 in front of ↺
(which moves to 15) and starts hidden like Album and Comment. Marcel: "Plays
Counter should aslo be available in library column and in tournament column",
so the library pane has it too, last at 15 (the 🏆 track list's is tested in
test_tournament_tree). The counts come from planner.playing.play_counts.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_playscol_"))

from PySide6.QtWidgets import QApplication

from dancesport_planner import RoundConfig
from gui.common import DEFAULT_HIDDEN_COLUMNS
from gui.dialogs import migrate_column_settings
from gui.library_browser import LIB_COL_COMMENT, LIB_COL_PLAYS, LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import TableActionsMixin
from planner.models import MusicEntry
from planner.playing import play_counts
from shared.columns import _COL_COMMENT, _COL_PLAYS, _N_COLS, COL_REGEN
from tests.db_support import use_scratch_db
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_PATH = Path(r"C:\music\tanzcds\standardcd\SW29_Lady Hear Me Tonight_DJ Maksy.mp3")
_OTHER = Path(r"C:\music\tanzcds\standardcd\SW29_Moon River.mp3")


def _entry(path=_PATH, title="Lady Hear Me Tonight"):
    return MusicEntry(path=path, title=title, dance="LW", bpm=29)


class DeckPlaysTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_playscol_db_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.addCleanup(play_counts.clear)
        play_counts.bump(_PATH)
        play_counts.bump(_PATH)
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.entry = _entry()
        self.table.load({"Final": [[self.entry]]}, ["LW"],
                        [RoundConfig(name="Final", heats=1, tier="final")], "S",
                        play_cb=lambda *_: None, suggester=None,
                        use_timbre=False, style="Standard")
        self.row = next(r for r, m in enumerate(self.table._row_meta)
                        if m and m.entry is self.entry)

    def cell(self):
        return self.table.item(self.row, _COL_PLAYS).text()

    def test_it_sits_between_comment_and_regen(self):
        self.assertEqual((_COL_COMMENT, _COL_PLAYS, COL_REGEN, _N_COLS), (13, 14, 15, 16))
        self.assertEqual(self.table.horizontalHeaderItem(_COL_PLAYS).text(), "Plays")
        self.assertEqual(self.table.horizontalHeaderItem(COL_REGEN).text(), "↺")

    def test_the_cell_shows_the_count(self):
        # A bare number, Marcel: "for play counter remove the x"
        self.assertEqual(self.cell(), "2")

    def test_a_title_not_played_shows_nothing(self):
        play_counts.clear()
        self.table.refresh_play_counts()
        self.assertEqual(self.cell(), "")

    def test_a_new_play_shows_after_a_refresh(self):
        play_counts.bump(_PATH)
        self.table.refresh_play_counts()
        self.assertEqual(self.cell(), "3")

    def test_every_kind_starts_with_it_hidden(self):
        for kind, cols in DEFAULT_HIDDEN_COLUMNS.items():
            self.assertIn(_COL_PLAYS, cols, kind)

    def test_the_header_menu_offers_it(self):
        menu = self.table.build_column_menu()
        self.assertIn(_COL_PLAYS, [a.data() for a in menu.actions() if a.isCheckable()])

    def test_the_header_menu_resets_through_the_window(self):
        calls = []
        self.table.set_play_counts_callback(lambda: calls.append("reset"))
        reset = self._reset_action()
        self.assertTrue(reset.isEnabled())
        reset.trigger()
        self.assertEqual(calls, ["reset"])

    def test_the_reset_is_greyed_while_nothing_counts(self):
        self.table.set_play_counts_callback(lambda: None)
        play_counts.clear()
        self.assertFalse(self._reset_action().isEnabled())

    def test_a_table_without_a_window_offers_no_reset(self):
        texts = [a.text() for a in self.table.build_column_menu().actions()]
        self.assertNotIn("Reset the play counters", texts)

    def test_it_sorts_by_count_then_title(self):
        key = TableActionsMixin._FLAT_SORT_KEYS[_COL_PLAYS]
        self.assertLess(key(_entry(_OTHER, "Moon River")), key(self.entry))

    def _reset_action(self):
        return next(a for a in self.table.build_column_menu().actions()
                    if a.text() == "Reset the play counters")


class SavedLayoutTest(unittest.TestCase):
    """Settings saved with Comment already in (columns_version 6)."""

    def test_plays_comes_in_hidden_in_front_of_regen(self):
        s = {"columns_version": 6,
             "hidden_columns": {"playlist": [1, 13], "wishlist": [14]},
             "column_widths": {"playlist": {"13": 180, "14": 30}},
             "column_order": {"playlist": list(range(15))},
             "library_columns": list(range(15)), "library_hidden_columns": [14]}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [1, _COL_COMMENT, _COL_PLAYS],
                          "wishlist": [_COL_PLAYS, COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {str(_COL_COMMENT): 180, str(COL_REGEN): 30})
        self.assertEqual(s["column_order"]["playlist"], list(range(16)))

    def test_the_library_gets_it_hidden_at_the_end(self):
        s = {"columns_version": 6,
             "library_columns": list(range(15)), "library_hidden_columns": [14]}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], list(range(16)))
        self.assertEqual(s["library_hidden_columns"], [LIB_COL_COMMENT, LIB_COL_PLAYS])

    def test_a_layout_with_the_deck_column_only_gets_the_library_one(self):
        # columns_version 7 gave the decks Plays and the library nothing.
        s = {"columns_version": 7,
             "hidden_columns": {"playlist": [1, _COL_PLAYS]},
             "column_order": {"playlist": list(range(16))},
             "library_columns": list(range(15)), "library_hidden_columns": []}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"], {"playlist": [1, _COL_PLAYS]})
        self.assertEqual(s["column_order"]["playlist"], list(range(16)))
        self.assertEqual(s["library_columns"], list(range(16)))
        self.assertEqual(s["library_hidden_columns"], [LIB_COL_PLAYS])


class LibraryPlaysTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(play_counts.clear)
        play_counts.bump(_PATH)
        play_counts.bump(_PATH)
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.pane.set_entries([_entry(), _entry(_OTHER, "Moon River")])

    def cell(self, path=_PATH):
        t = self.pane._table
        row = next(r for r in range(t.rowCount())
                   if str(self.pane._row_path(r)) == str(path))
        return t.item(row, LIB_COL_PLAYS).text()

    def test_it_is_the_last_column(self):
        t = self.pane._table
        self.assertEqual((LIB_COL_PLAYS, t.columnCount()), (15, 16))
        self.assertEqual(t.horizontalHeaderItem(LIB_COL_PLAYS).text(), "Plays")

    def test_the_cell_shows_the_count(self):
        self.assertEqual(self.cell(), "2")
        self.assertEqual(self.cell(_OTHER), "")

    def test_a_new_play_shows_after_a_refresh(self):
        play_counts.bump(_OTHER)
        self.pane.refresh_play_counts()
        self.assertEqual(self.cell(_OTHER), "1")

    def test_it_starts_hidden_and_can_be_ticked_on(self):
        self.assertIn(LIB_COL_PLAYS, self.pane.hidden_columns())
        menu = self.pane.build_column_menu()
        self.assertIn(LIB_COL_PLAYS,
                      [a.data() for a in menu.actions() if a.isCheckable()])

    def test_it_sorts_by_count(self):
        key = self.pane._sort_key(LIB_COL_PLAYS)
        self.assertLess(key(_entry(_OTHER, "Moon River")), key(_entry()))

    def test_the_header_menu_resets_through_the_window(self):
        calls = []
        self.pane.playCountsResetWanted.connect(lambda: calls.append("reset"))
        reset = self._reset_action()
        self.assertTrue(reset.isEnabled())
        reset.trigger()
        self.assertEqual(calls, ["reset"])

    def test_the_reset_is_greyed_while_nothing_counts(self):
        play_counts.clear()
        self.assertFalse(self._reset_action().isEnabled())

    def _reset_action(self):
        return next(a for a in self.pane.build_column_menu().actions()
                    if a.text() == "Reset the play counters")


if __name__ == "__main__":
    unittest.main()
