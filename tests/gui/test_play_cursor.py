#!/usr/bin/env python3
"""Tests for the play cursor: the ■ marker follows the placed TRACK, by id.

Run:  py -m unittest tests.gui.test_play_cursor -v

`_current_play_row` used to be a bare row number. Every edit that moved rows —
a swap, a drag, a removal above it, a sort, a re-render — had to work out where
the playing title went and write the new number back, and each of the twenty
places that did so did it its own way: by row arithmetic, by entry identity,
or by searching the path. The path search picked the FIRST row with that file,
so a Paso Doble danced in the Vorrunde and again in the Finale sent the marker
back to the Vorrunde whenever the deck was re-rendered.

Now every Row carries an id, minted when the row is made. A swap takes it along
with the track, a re-render hands it back to the row the same track landed on,
and the table only remembers which id is playing: the row number is looked up.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cursor_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.running_order import Row, RunningOrder  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _e(dance: str, n: int) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class RowIdTest(unittest.TestCase):
    """Every row is a placement of its own, and says so by its id."""

    def test_every_row_gets_its_own_id(self):
        self.assertNotEqual(Row(entry=_e("LW", 1)).uid, Row(entry=_e("LW", 1)).uid)

    def test_a_stacked_spare_is_a_placement_of_its_own(self):
        slot = Row(entry=_e("LW", 1), round_name="Finale")
        self.assertNotEqual(slot.spare(_e("LW", 2), 1).uid, slot.uid)

    def test_the_id_does_not_make_two_rows_unequal(self):
        """Rows are compared as data (an undo compares them); the id is not
        part of what a row says."""
        e = _e("LW", 1)
        self.assertEqual(Row(entry=e, dance="LW"), Row(entry=e, dance="LW"))


class RunningOrderIdsTest(unittest.TestCase):

    def setUp(self):
        self.a, self.b, self.c = _e("LW", 1), _e("LW", 2), _e("LW", 3)
        self.order = RunningOrder([None, Row(entry=self.a, h_idx=0),
                                   Row(entry=self.b, h_idx=1),
                                   Row(entry=self.c, h_idx=2)])

    def _uid(self, entry):
        return next(r.uid for r in self.order.songs() if r.entry is entry)

    def test_row_of_finds_the_row_by_its_id(self):
        self.assertEqual(self.order.row_of(self._uid(self.b)), 2)

    def test_row_of_a_row_that_is_gone_is_minus_one(self):
        uid = self._uid(self.b)
        del self.order[2]
        self.assertEqual(self.order.row_of(uid), -1)
        self.assertEqual(self.order.row_of(None), -1)

    def test_a_row_removed_above_moves_the_id_up_with_its_row(self):
        uid = self._uid(self.c)
        del self.order[1]
        self.assertEqual(self.order.row_of(uid), 2)

    def test_a_swap_takes_the_id_along_with_the_track(self):
        uid = self._uid(self.a)
        self.order.swap(1, 3)
        self.assertIs(self.order[3].entry, self.a)
        self.assertEqual(self.order.row_of(uid), 3)

    def test_a_rebuild_hands_each_track_its_id_back(self):
        before = self.order.placements()
        uid_c = self._uid(self.c)
        self.order = RunningOrder([Row(entry=self.c), None, Row(entry=self.a),
                                   Row(entry=self.b)])
        self.order.adopt(before)
        self.assertEqual(self.order.row_of(uid_c), 0)

    def test_the_same_track_twice_keeps_each_placement_apart(self):
        """A Paso Doble danced in the Vorrunde and again in the Finale: the
        Finale placement stays the Finale placement."""
        pd = _e("PD", 1)
        order = RunningOrder([Row(entry=pd, round_name="Vorrunde"),
                              Row(entry=pd, round_name="Finale")])
        final = order[1].uid
        rebuilt = RunningOrder([Row(entry=pd, round_name="Vorrunde"),
                                Row(entry=pd, round_name="Finale")])
        rebuilt.adopt(order.placements())
        self.assertEqual(rebuilt.row_of(final), 1)

    def test_a_track_loaded_again_from_its_file_is_found_by_path(self):
        """An undo or a restore builds the entries anew from the paths."""
        uid = self._uid(self.b)
        again = _e("LW", 2)
        rebuilt = RunningOrder([Row(entry=again, h_idx=1)])
        rebuilt.adopt(self.order.placements())
        self.assertEqual(rebuilt.row_of(uid), 0)

    def test_a_row_that_got_a_new_track_gets_a_new_id(self):
        """Reshuffled in place: no two rows may end up with one id."""
        before = self.order.placements()
        self.order[1].entry = _e("LW", 9)
        self.order[2].entry = self.a
        self.order.adopt(before)
        uids = [r.uid for r in self.order.songs()]
        self.assertEqual(len(set(uids)), len(uids))
        self.assertEqual(self.order.row_of(before[0][0]), 2)


class MarkerFollowsThePlacementTest(unittest.TestCase):
    """On a real table: the marker stays on the placement that plays."""

    def setUp(self):
        self.t = PlaylistTable()
        self.addCleanup(reap_widget, self.t)

    def _load(self, playlist, dances):
        rounds = [RoundConfig(name=n, heats=1, tier="final") for n in playlist]
        self.t.load(playlist, list(dances), rounds, "S",
                    play_cb=lambda *a: None, suggester=None, use_timbre=False)

    def test_the_final_keeps_the_marker_when_the_track_was_danced_before(self):
        pd = _e("PD", 1)
        self._load({"Vorrunde": [[pd, _e("JI", 1)]],
                    "Finale": [[pd, _e("JI", 2)]]}, ("PD", "JI"))
        final_row = next(r for r, m in self.t._row_meta.numbered()
                         if m.round_name == "Finale" and m.entry is pd)
        self.t._current_play_row = final_row
        self.t.set_grouping(2)          # re-render without the headers
        m = self.t._row_meta.at(self.t._current_play_row)
        self.assertEqual((m.round_name, m.entry), ("Finale", pd))

    def test_the_row_number_is_looked_up_not_kept(self):
        self._load({"Finale": [[_e("PD", 1), _e("JI", 1)]]}, ("PD", "JI"))
        rows = self.t._row_meta.song_rows()
        self.t._current_play_row = rows[1]
        uid = self.t._row_meta[rows[1]].uid
        self.t.removeRow(rows[0])
        del self.t._row_meta[rows[0]]
        self.assertEqual(self.t._current_play_row,
                         self.t._row_meta.row_of(uid))
        self.assertEqual(self.t._current_play_row, rows[1] - 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
