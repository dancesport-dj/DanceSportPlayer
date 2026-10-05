"""Finding music you have NOT used yet: the 📚 library's freshness filters,
the 🌱 freshness pick in the Similar-Tracks window, the 📊 gap dashboard's
jump into the library, and the same jump from an empty grid slot.

They are one workflow — "what is new here, and what have I never played?"
— so they are tested together: what each filter keeps, and that a jump really
carries the dance × class it was asked for.
"""
import os
import sys
import tempfile
import time
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fresh_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

from dancesport_planner import DANCE_NAMES, MusicLibrary  # noqa: E402
from gui.common import _PROVEN_MIN_PLAYS  # noqa: E402
from gui.dialogs import LibraryGapsDialog  # noqa: E402
from gui.library_browser import LibraryBrowser  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.running_order import Row, RunningOrder  # noqa: E402
from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

_DAY = 86400
_NOW = time.time()
_YEAR = date.today().year

_COL_TITLE = 3
_COL_ADDED = 8
_COL_LAST = 9


def _entry(title, dance="LW", popularity=0, last_played=None, age_days=900,
           **kw) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\standardcd\{title}.mp3"),
        title=title, dance=dance, bpm=29, popularity=popularity,
        last_played=last_played, added=_NOW - age_days * _DAY, **kw)


# The four cases every freshness filter has to tell apart.
_NEW_UNUSED = _entry("brand new", age_days=10)
_NEW_PLAYED = _entry("new but used", popularity=5, last_played=_YEAR, age_days=10)  # tried out, not proven
_OLD_RARE = _entry("played twice", popularity=2, last_played=_YEAR - 4)
_OLD_PROVEN = _entry("workhorse", popularity=40, last_played=_YEAR)
_ALL = [_NEW_UNUSED, _NEW_PLAYED, _OLD_RARE, _OLD_PROVEN]


class LibraryFilterTest(unittest.TestCase):
    """The 📚 pane's Plays / Added combos."""

    def setUp(self):
        self.pane = LibraryBrowser()
        self.pane.set_entries(_ALL)

    def tearDown(self):
        reap_widget(self.pane)

    def _shown(self) -> set:
        t = self.pane._table
        return {t.item(r, _COL_TITLE).text() for r in range(t.rowCount())}

    def _pick(self, combo, value):
        combo.setCurrentIndex(combo.findData(value))

    def test_everything_shows_without_a_filter(self):
        self.assertEqual(self._shown(), {e.title for e in _ALL})

    def test_never_played_keeps_only_the_unused(self):
        self._pick(self.pane._plays_combo, "never")
        self.assertEqual(self._shown(), {"brand new"})

    def test_rarely_played_is_anything_under_the_proven_mark(self):
        self._pick(self.pane._plays_combo, "rare")
        self.assertEqual(self._shown(), {"played twice", "new but used"})

    def test_proven_takes_ten_playlists(self):
        self._pick(self.pane._plays_combo, "proven")
        self.assertEqual(self._shown(), {"workhorse"})

    def test_the_proven_mark_itself_counts_as_proven(self):
        """One play either side of the line — the boundary is where the
        wording promises it is."""
        self.pane.set_entries([_entry("nine", popularity=_PROVEN_MIN_PLAYS - 1),
                               _entry("ten", popularity=_PROVEN_MIN_PLAYS)])
        self._pick(self.pane._plays_combo, "proven")
        self.assertEqual(self._shown(), {"ten"})
        self._pick(self.pane._plays_combo, "rare")
        self.assertEqual(self._shown(), {"nine"})

    def test_not_since_a_year_skips_the_never_played(self):
        """'Not played since' is about forgotten music, not unused music —
        a track with no play at all is the OTHER filter's job."""
        self._pick(self.pane._plays_combo, "stale1")
        self.assertEqual(self._shown(), {"played twice"})

    def test_an_undated_play_history_is_not_stale(self):
        self.pane.set_entries([_entry("undated", popularity=3)])
        self._pick(self.pane._plays_combo, "stale1")
        self.assertEqual(self._shown(), set())

    def test_added_filters_by_the_files_own_age(self):
        self._pick(self.pane._added_combo, "30")
        self.assertEqual(self._shown(), {"brand new", "new but used"})

    def test_last_18_months_sits_beside_last_12_months(self):
        """Marcel: add a Last 18 months filter beside Last 12 months."""
        combo = self.pane._added_combo
        self.assertEqual(combo.findData("548"), combo.findData("365") + 1)
        self.assertEqual(combo.itemText(combo.findData("548")), "🆕 Last 18 months")
        self.pane.set_entries([_entry("a year and a bit", age_days=400),
                               _entry("two years", age_days=730)])
        self._pick(combo, "548")
        self.assertEqual(self._shown(), {"a year and a bit"})
        self._pick(combo, "365")
        self.assertEqual(self._shown(), set())

    def test_new_and_never_played_is_the_two_filters_together(self):
        self._pick(self.pane._added_combo, "30")
        self._pick(self.pane._plays_combo, "never")
        self.assertEqual(self._shown(), {"brand new"})

    def test_a_track_without_a_timestamp_is_not_called_new(self):
        self.pane.set_entries([_entry("no stat", age_days=0)] )
        self.pane._entries[0].added = None
        self._pick(self.pane._added_combo, "30")
        self.assertEqual(self._shown(), set())


class LibraryColumnTest(unittest.TestCase):
    """The two new columns: what they say, and that they sort by value."""

    def setUp(self):
        self.pane = LibraryBrowser()
        self.pane.set_entries(_ALL)

    def tearDown(self):
        reap_widget(self.pane)

    def _cell(self, title, col):
        t = self.pane._table
        for r in range(t.rowCount()):
            if t.item(r, _COL_TITLE).text() == title:
                return t.item(r, col)
        raise AssertionError(f"{title} is not in the table")

    def test_added_shows_the_date_the_file_appeared(self):
        expected = date.fromtimestamp(_NEW_UNUSED.added).isoformat()
        self.assertEqual(self._cell("brand new", _COL_ADDED).text(), expected)

    def test_last_played_shows_the_year(self):
        self.assertEqual(self._cell("workhorse", _COL_LAST).text(), str(_YEAR))

    def test_a_never_played_track_says_so(self):
        it = self._cell("brand new", _COL_LAST)
        self.assertEqual(it.text(), "—")
        self.assertEqual(it.toolTip(), "Never played")

    def test_a_played_but_undated_track_is_a_question_mark(self):
        self.pane.set_entries([_entry("undated", popularity=3)])
        self.assertEqual(self._cell("undated", _COL_LAST).text(), "?")

    def test_the_columns_sort_by_value_not_by_text(self):
        t = self.pane._table
        t.sortItems(_COL_LAST, Qt.SortOrder.DescendingOrder)
        years = [t.item(r, _COL_LAST).data(Qt.ItemDataRole.UserRole)
                 for r in range(t.rowCount())]
        self.assertEqual(years, sorted(years, reverse=True))


class FocusFilterTest(unittest.TestCase):
    """`focus_filter` is what the 📊 gap dashboard drives the pane with."""

    def setUp(self):
        self.pane = LibraryBrowser()
        self.pane.set_entries(_ALL + [_entry("rumba unused", dance="RB",
                                             age_days=5)])

    def tearDown(self):
        reap_widget(self.pane)

    def _shown(self) -> set:
        t = self.pane._table
        return {t.item(r, _COL_TITLE).text() for r in range(t.rowCount())}

    def test_it_applies_dance_and_play_history(self):
        self.pane.focus_filter(dance="RB", plays="never")
        self.assertEqual(self._shown(), {"rumba unused"})

    def test_it_clears_the_filters_it_was_not_asked_for(self):
        """A leftover filter would silently eat the answer."""
        self.pane._filter_edit.setText("workhorse")
        self.pane._vocal_combo.setCurrentIndex(
            self.pane._vocal_combo.findData("instr"))
        self.pane.focus_filter(dance="LW", plays="never")
        self.assertEqual(self.pane._filter_edit.text(), "")
        self.assertEqual(self.pane._vocal_combo.currentData(), "")
        self.assertEqual(self._shown(), {"brand new"})

    def test_it_unfolds_the_pane(self):
        self.pane.set_folded(True)
        self.pane.focus_filter(dance="LW")
        self.assertFalse(self.pane.is_folded())


class SimilarFreshnessTest(unittest.TestCase):
    """🌱 in the Similar-Tracks window — same question, from a track's side."""

    def _dialog(self, **kw):
        results = [(0.9, e) for e in _ALL]
        dlg = SimilarTracksDialog(_entry("anchor"), results, **kw)  # never lists itself
        self.addCleanup(reap_widget, dlg)
        return dlg

    def _shown(self, dlg) -> set:
        return {e.title for e in dlg._row_entries}

    def test_all_tracks_by_default(self):
        dlg = self._dialog()
        self.assertEqual(self._shown(dlg), {e.title for e in _ALL})

    def test_the_context_entry_opens_it_on_never_played(self):
        dlg = self._dialog(fresh_only=True)
        self.assertEqual(dlg._fresh_combo.currentData(), "never")
        self.assertEqual(self._shown(dlg), {"brand new"})

    def test_not_played_since_last_year_keeps_the_forgotten_ones(self):
        dlg = self._dialog()
        dlg._fresh_combo.setCurrentIndex(dlg._fresh_combo.findData("stale1"))
        self.assertEqual(self._shown(dlg), {"played twice"})

    def test_the_header_says_the_filter_is_on(self):
        dlg = self._dialog(fresh_only=True)
        self.assertIn("hidden", dlg._head.text())


class GapJumpTest(unittest.TestCase):
    """📊 Library gaps → 📚 library: the jump carries its dance × class."""

    def setUp(self):
        lib = MusicLibrary()
        lib.entries = list(_ALL)
        self.dlg = LibraryGapsDialog(lib)
        self.addCleanup(reap_widget, self.dlg)

    def test_nothing_is_asked_for_until_a_row_is_picked(self):
        self.assertIsNone(self.dlg.jump_to)

    def test_a_picked_row_names_its_dance_and_class(self):
        """Sorted first, because the row a click lands on is a VISUAL row —
        the stats it belongs to are found through the cell, not the index."""
        self.dlg._table.sortItems(4, Qt.SortOrder.DescendingOrder)
        self.dlg._jump(0)
        dance, cls = self.dlg.jump_to
        self.assertEqual(self.dlg._table.item(0, 1).text(), cls)
        self.assertEqual(self.dlg._table.item(0, 2).text(),
                         f"{DANCE_NAMES[dance]} ({dance})")

    def test_picking_no_row_at_all_is_ignored(self):
        self.dlg._jump(-1)
        self.assertIsNone(self.dlg.jump_to)


class _JumpWindow(QWidget):
    """A top-level that records the jump, standing in for the MainWindow."""

    def __init__(self):
        super().__init__()
        self.asked = None

    def show_library_filtered(self, dance="", cls="", plays="", added=""):
        self.asked = (dance, cls, plays, added)


class EmptySlotJumpTest(unittest.TestCase):
    """Double-clicking a hole in the grid asks the library what fits in it."""

    def setUp(self):
        self.win = _JumpWindow()
        self.addCleanup(reap_widget, self.win)
        self.table = PlaylistTable(self.win)
        self.table._dance_class = "B"
        self.table._row_meta = RunningOrder([
            Row(entry=_OLD_PROVEN, dance="LW"),     # a filled row
            Row(entry=None, dance="SF"),            # the hole
        ])

    def test_an_empty_slot_opens_the_library_on_its_dance_and_class(self):
        self.table._on_row_double_clicked(1, 0)
        self.assertEqual(self.win.asked, ("SF", "B", "", ""))

    def test_playing_mode_keeps_the_double_click_to_itself(self):
        """Mid-tournament there is nothing to fill and the desk is busy."""
        self.table._play_hl_enabled = True
        self.table._on_row_double_clicked(1, 0)
        self.assertIsNone(self.win.asked)

    def test_a_filled_row_does_not_jump(self):
        """It opens the file externally — the audition path, left untouched."""
        self.table._browse_for_empty_slot = lambda meta: self.fail("jumped")
        with unittest.mock.patch("gui.playlist_table._open_in_default_player"):
            self.table._on_row_double_clicked(0, 0)
        self.assertIsNone(self.win.asked)

    def test_a_header_row_is_ignored(self):
        self.table._row_meta = RunningOrder([None])
        self.table._on_row_double_clicked(0, 0)
        self.assertIsNone(self.win.asked)


class MainWindowJumpTest(unittest.TestCase):
    """The window end of the jump — the pane is revealed and filtered."""

    @classmethod
    def setUpClass(cls):
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib_browser.set_entries(_ALL)

    def test_it_reveals_the_pane_and_applies_the_filter(self):
        self.win._lib_btn.setChecked(False)
        self.win.show_library_filtered(dance="LW", cls="B", plays="never")
        pane = self.win._lib_browser
        self.assertTrue(self.win._lib_btn.isChecked())
        self.assertIs(self.win._lib_tabs.currentWidget(), pane)
        self.assertEqual(pane._dance_combo.currentData(), "LW")
        self.assertEqual(pane._class_combo.currentData(), "B")
        self.assertEqual(pane._plays_combo.currentData(), "never")
        self.assertEqual(
            {pane._table.item(r, _COL_TITLE).text()
             for r in range(pane._table.rowCount())}, {"brand new"})


if __name__ == "__main__":
    unittest.main()
