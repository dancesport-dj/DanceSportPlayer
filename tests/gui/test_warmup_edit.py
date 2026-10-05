#!/usr/bin/env python3
"""Tests for editing a running order without re-rendering it.

Run:  py -m unittest tests.gui.test_warmup_edit -v

Dragging one title from a 250-row running order into another used to rebuild
both lists row by row — a second of frozen window per drag, spent almost
entirely on rows that had not changed. An added or dropped track now moves the
rows under it and re-shades them, and nothing else is touched.

"Nothing else is touched" is the whole point, so that is what these check: the
row widgets of the unchanged rows must be the very same objects afterwards. A
rebuild makes new ones, which is how a silent fall back to it gets caught.

The fall backs are here too. Only a clean insertion or removal can be shown in
place; a re-order, a drop that cuts a strip in two, a folded strip — those go
through load_warmup as before, and must still come out right.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wedit_"))

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.common import _C_ROW_EVEN, _C_ROW_ODD  # noqa: E402
from shared.columns import _COL_PLAY, _COL_TITLE
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _e(dance, n, secs=150):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, duration=secs)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _EditTest(unittest.TestCase):
    """A running order cut into two ─── strips: two Walzer, then two Tango."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.played = []
        self.entries = [_e("LW", 1), _e("LW", 2), _e("TG", 1), _e("TG", 2)]
        win = _Win()
        self.table = PlaylistTable()
        self.table.setParent(win)
        self.table.resize(700, 400)
        self.addCleanup(reap_widget, win)
        self.table.load_warmup(list(self.entries), "Running order", "both", "S",
                               False, self.played.append, None, running_order=True)

    # ── what the table says about itself ────────────────────────────────────
    def titles(self):
        return [m.entry.title for _r, m in self.table._row_meta.numbered()]

    def headers(self):
        return [self.table.item(r, 0).text()
                for r in sorted(self.table._round_hdr_rows)]

    def buttons(self):
        """The play button of every song row, by title — the objects a rebuild
        would throw away and make again."""
        return {m.entry.title: self.table.cellWidget(r, _COL_PLAY)
                for r, m in self.table._row_meta.numbered()}

    def stripes(self):
        return [self.table.item(r, _COL_TITLE).background().color()
                for r, _m in self.table._row_meta.numbered()]

    def assert_consistent(self):
        """The table renders exactly the rows its own list asks for."""
        t = self.table
        plan = t._warmup_plan(t._row_meta.entries())
        self.assertEqual(len(plan), t.rowCount(), "row count drifted from the list")
        self.assertEqual(len(plan), len(t._row_meta), "row meta drifted from the list")
        self.assertEqual([i for i, (kind, _v) in enumerate(plan) if kind == "H"],
                         sorted(t._round_hdr_rows), "strips sit on the wrong rows")
        for r, m in t._row_meta.numbered():
            self.assertEqual(t.item(r, _COL_TITLE).text(), m.entry.title,
                             f"row {r} shows a different track than it holds")


class FixtureTest(_EditTest):

    def test_the_list_is_cut_into_strips(self):
        """Guards the fixture: with a single strip the header tests below would
        pass for the wrong reason."""
        self.assertEqual(len(self.table._round_hdr_rows), 2)
        self.assertEqual(self.titles(), ["LW 1", "LW 2", "TG 1", "TG 2"])
        self.assert_consistent()


class InsertTest(_EditTest):

    def test_a_track_added_to_a_strip_leaves_every_other_row_alone(self):
        before = self.buttons()
        self.table._reload_warmup(self.entries[:2] + [_e("LW", 3)] + self.entries[2:])
        after = self.buttons()
        self.assertEqual(self.titles(), ["LW 1", "LW 2", "LW 3", "TG 1", "TG 2"])
        for title, widget in before.items():
            self.assertIs(after[title], widget,
                          f"{title} was rebuilt though it did not change")
        self.assert_consistent()

    def test_the_strip_counts_what_it_now_holds(self):
        self.table._reload_warmup(self.entries[:2] + [_e("LW", 3)] + self.entries[2:])
        self.assertIn("(3 songs", self.headers()[0])
        self.assertIn("(2 songs", self.headers()[1])

    def test_the_rows_under_it_take_the_other_shade(self):
        """The stripes count songs, so everything below an added row flips."""
        self.table._reload_warmup(self.entries[:2] + [_e("LW", 3)] + self.entries[2:])
        self.assertEqual(self.stripes(),
                         [_C_ROW_EVEN, _C_ROW_ODD, _C_ROW_EVEN, _C_ROW_ODD, _C_ROW_EVEN])

    def test_a_track_appended_at_the_end_is_added_in_place(self):
        before = self.buttons()
        self.table._reload_warmup(self.entries + [_e("TG", 3)])
        self.assertEqual(self.titles()[-1], "TG 3")
        self.assertIs(self.buttons()["LW 1"], before["LW 1"])
        self.assert_consistent()

    def test_a_new_dance_brings_its_own_strip_with_it(self):
        before = self.buttons()
        self.table._reload_warmup(self.entries + [_e("QS", 9)])
        self.assertEqual(len(self.table._round_hdr_rows), 3)
        self.assertIn("Quickstep", self.headers()[2])
        self.assertIs(self.buttons()["LW 1"], before["LW 1"])
        self.assert_consistent()

    def test_a_dance_dropped_mid_strip_cuts_it_in_two(self):
        """Three strips where there were two: not an insertion any more, so the
        list is rebuilt — and has to come out right."""
        self.table._reload_warmup(self.entries[:1] + [_e("QS", 9)] + self.entries[1:])
        self.assertEqual(self.titles(), ["LW 1", "QS 9", "LW 2", "TG 1", "TG 2"])
        self.assertEqual(len(self.table._round_hdr_rows), 4)
        self.assert_consistent()


class RemoveTest(_EditTest):

    def test_dropping_a_track_leaves_every_other_row_alone(self):
        before = self.buttons()
        self.table._reload_warmup([e for e in self.entries if e.title != "LW 2"])
        after = self.buttons()
        self.assertEqual(self.titles(), ["LW 1", "TG 1", "TG 2"])
        for title, widget in after.items():
            self.assertIs(widget, before[title],
                          f"{title} was rebuilt though it did not change")
        self.assert_consistent()

    def test_a_strip_left_empty_goes_with_its_last_track(self):
        self.table._reload_warmup([e for e in self.entries
                                   if not e.title.startswith("LW")])
        self.assertEqual(self.titles(), ["TG 1", "TG 2"])
        self.assertEqual(len(self.table._round_hdr_rows), 1)
        self.assert_consistent()

    def test_the_strip_counts_what_is_left(self):
        self.table._reload_warmup([e for e in self.entries if e.title != "TG 1"])
        self.assertIn("(2 songs", self.headers()[0])
        self.assertIn("(1 song", self.headers()[1])

    def test_the_rows_under_it_take_the_other_shade(self):
        self.table._reload_warmup([e for e in self.entries if e.title != "LW 1"])
        self.assertEqual(self.stripes(), [_C_ROW_EVEN, _C_ROW_ODD, _C_ROW_EVEN])

    def test_emptying_the_list_empties_the_table(self):
        self.table._reload_warmup([])
        self.assertEqual(self.table.rowCount(), 0)
        self.assert_consistent()


class RebuildTest(_EditTest):
    """Edits that are not a clean insertion or removal still go the long way."""

    def test_a_reorder_is_rebuilt(self):
        self.assertFalse(self.table._warmup_edit_in_place(
            [self.entries[1], self.entries[0]] + self.entries[2:]))

    def test_a_swap_is_rebuilt(self):
        """One track out and another in at the same spot: changed on both sides,
        which moving rows cannot express."""
        self.assertFalse(self.table._warmup_edit_in_place(
            self.entries[:1] + [_e("LW", 7)] + self.entries[2:]))

    def test_a_folded_strip_is_rebuilt(self):
        """Which strip is folded is remembered by row number, and an in-place
        edit moves the rows out from under it."""
        self.table._on_header_click(sorted(self.table._round_hdr_rows)[0], 0)
        self.assertTrue(self.table._collapsed)
        self.assertFalse(self.table._warmup_edit_in_place(self.entries + [_e("TG", 3)]))

    def test_a_table_the_plan_does_not_describe_is_rebuilt(self):
        """Belt and braces: if the rendered rows and the list have drifted apart,
        the rows must not be edited on the strength of the list."""
        self.table.insertRow(0)
        self.assertFalse(self.table._warmup_edit_in_place(self.entries + [_e("TG", 3)]))

    def test_the_same_list_again_changes_nothing(self):
        before = self.buttons()
        self.table._reload_warmup(list(self.entries))
        self.assertEqual(self.titles(), ["LW 1", "LW 2", "TG 1", "TG 2"])
        self.assertIs(self.buttons()["TG 2"], before["TG 2"])
        self.assert_consistent()


class PlayingTest(_EditTest):
    """The marker follows the track, not the row number it happened to be on."""

    def test_it_stays_on_the_track_when_one_above_is_dropped(self):
        self.table._current_play_row = self.table._row_meta.song_rows()[3]
        self.table._reload_warmup([e for e in self.entries if e.title != "LW 1"])
        playing = self.table._row_meta.at(self.table._current_play_row)
        self.assertIsNotNone(playing, "the marker landed on a header row")
        self.assertEqual(playing.entry.title, "TG 2")

    def test_it_stays_on_the_track_when_one_above_is_added(self):
        self.table._current_play_row = self.table._row_meta.song_rows()[3]
        self.table._reload_warmup(self.entries[:1] + [_e("LW", 3)] + self.entries[1:])
        playing = self.table._row_meta.at(self.table._current_play_row)
        self.assertIsNotNone(playing, "the marker landed on a header row")
        self.assertEqual(playing.entry.title, "TG 2")


class GreyedTest(_EditTest):
    """Played rows are greyed out in playing mode — and remembered by ROW, so
    an edit that moves rows has to hand the colours back before it moves them
    and grey the played tracks again afterwards."""

    GREY = QColor("#a8aeb8")

    def setUp(self):
        super().setUp()
        self.table.set_play_highlight_enabled(True)
        self.table.mark_path_played(str(self.entries[3].path))   # "TG 2" was heard

    def greyed(self):
        return {m.entry.title for r, m in self.table._row_meta.numbered()
                if self.table.item(r, _COL_TITLE).foreground().color() == self.GREY}

    def test_the_fixture_greys_the_played_track(self):
        self.assertEqual(self.greyed(), {"TG 2"})

    def test_the_played_track_stays_grey_when_a_row_above_it_is_added(self):
        self.table._reload_warmup(self.entries[:1] + [_e("LW", 3)] + self.entries[1:])
        self.assertEqual(self.greyed(), {"TG 2"})

    def test_the_played_track_stays_grey_when_a_row_above_it_is_dropped(self):
        self.table._reload_warmup([e for e in self.entries if e.title != "LW 1"])
        self.assertEqual(self.greyed(), {"TG 2"})

    def test_a_track_played_after_the_edit_greys_where_it_now_sits(self):
        """The added row pushes "TG 1" onto the row "TG 2" was greyed on. A
        stale row key there means the next track played never greys."""
        self.table._reload_warmup(self.entries[:2] + [_e("LW", 3)] + self.entries[2:])
        self.table.mark_path_played(str(self.entries[2].path))   # "TG 1" was heard
        self.assertEqual(self.greyed(), {"TG 1", "TG 2"})

    def test_a_reorder_takes_the_grey_with_the_track(self):
        """A drag inside the list moves the tracks between rows that stay put,
        and re-fills the rows it changed with fresh colours — the played track
        has to come out of it grey on its new row."""
        e = self.entries
        self.table._apply_song_reorder([e[0], e[1], e[3], e[2]])   # TG 2 up
        self.assertEqual(self.titles(), ["LW 1", "LW 2", "TG 2", "TG 1"])
        self.assertEqual(self.greyed(), {"TG 2"})

    def test_planning_mode_after_a_reorder_leaves_no_grey_behind(self):
        e = self.entries
        self.table._apply_song_reorder([e[0], e[1], e[3], e[2]])
        self.table.set_play_highlight_enabled(False)
        self.assertEqual(self.greyed(), set())

    def test_planning_mode_gives_every_row_its_own_colour_back(self):
        """The saved colours must not be restored onto whatever row happens to
        sit at those numbers after the edit."""
        self.table._reload_warmup(self.entries[:1] + [_e("LW", 3)] + self.entries[1:])
        self.table.set_play_highlight_enabled(False)
        self.assertEqual(self.greyed(), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
