#!/usr/bin/env python3
"""↔ A social track keeps its dance when the ETDS party list is re-ordered.

Run:  py -m unittest tests.gui.test_party_social_dance -v

Discofox, Salsa and the rest have no `.dance` at all — the genre names the
dance, and `planner.warmup.warmup_code` is what turns "Discofox" into the
DISCOFOX the Dance column then writes out. Both render paths of the party list
(`load_warmup` and the in-place edit) ask it.

The re-order did not: dragging a title to another place rebuilt every moved
row's dance from `entry.dance` alone, so every social row the drag touched came
back with an EMPTY Dance cell — which is exactly what the operator sees after
pushing a wish around in the party list.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_psocial_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from shared.columns import _COL_DANCE  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _e(dance, n, other_genre=None):
    tag = dance or (other_genre or "X").replace(" ", "")
    return MusicEntry(path=Path(rf"C:\music\{tag}{n}.mp3"), title=f"{tag} {n}",
                      dance=dance, other_genre=other_genre, duration=150)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class PartySocialDanceTest(unittest.TestCase):
    """A party list whose third round is a social one: Discofox, then Salsa."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.entries = [_e("LW", 1), _e("TG", 1),
                        _e("CC", 1), _e("RB", 1),
                        _e(None, 1, other_genre="Discofox"),
                        _e(None, 1, other_genre="Salsa"),
                        _e("SF", 1), _e("QS", 1)]
        win = _Win()
        self.table = PlaylistTable()
        self.table.list_kind = "party"
        self.table.setParent(win)
        self.table.resize(700, 400)
        self.addCleanup(reap_widget, win)
        self.table.load_warmup(list(self.entries), "ETDS Party", "", "S", True,
                               lambda _p: None, None)
        self.app.processEvents()

    def dances(self) -> dict:
        """{title -> what the Dance column says}."""
        return {m.entry.title: self.table.item(r, _COL_DANCE).text()
                for r, m in self.table._row_meta.numbered()}

    def row_of(self, title: str) -> int:
        return next(r for r, m in self.table._row_meta.numbered()
                    if m.entry.title == title)

    def test_the_fixture_names_the_social_dances(self):
        self.assertEqual(self.dances()["Discofox 1"], "Discofox")
        self.assertEqual(self.dances()["Salsa 1"], "Salsa")

    def test_a_social_track_dragged_up_keeps_its_dance(self):
        self.table._drag_src_rows = [self.row_of("Salsa 1")]
        self.assertTrue(self.table._reorder_warmup(0))
        self.app.processEvents()
        self.assertEqual(self.dances()["Salsa 1"], "Salsa")

    def test_the_social_rows_a_drag_shifts_past_keep_theirs(self):
        """Every row from the drop point down takes a new track — so the two
        social rows are re-filled even though neither was the one dragged."""
        self.table._drag_src_rows = [self.row_of("LW 1")]
        self.assertTrue(self.table._reorder_warmup(self.table.rowCount()))
        self.app.processEvents()
        self.assertEqual(self.dances()["Discofox 1"], "Discofox")
        self.assertEqual(self.dances()["Salsa 1"], "Salsa")

    def test_a_ctrl_swap_keeps_it_too(self):
        self.table._drag_src_rows = [self.row_of("Discofox 1")]
        self.assertTrue(self.table._swap_reorder(self.row_of("LW 1")))
        self.app.processEvents()
        self.assertEqual(self.dances()["Discofox 1"], "Discofox")
        self.assertEqual(self.dances()["LW 1"], "Langsamer Walzer")

    def test_short_dance_names_still_read_short_after_a_drag(self):
        self.table.set_short_dances(True)
        self.table._drag_src_rows = [self.row_of("Salsa 1")]
        self.assertTrue(self.table._reorder_warmup(0))
        self.app.processEvents()
        self.assertEqual(self.dances()["Salsa 1"], "SL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
