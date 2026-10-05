#!/usr/bin/env python3
"""Tests for ↺ on the ETDS party list: a swap within the list, not a re-roll.

Run:  py -m unittest tests.gui.test_party_swap -v

On the party list ↺ swaps the row with a title of the same dance from the end of
the list (planner.warmup.warmup_swap_partner picks which). A per-class Eintanzen
list keeps the library re-roll.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pswap_"))

from PySide6.QtCore import QEvent, QItemSelectionModel, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from shared.columns import _COL_REGEN  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


_DIR = Path(tempfile.mkdtemp(prefix="dp_pswap_m_"))


def _e(dance, n):
    # A real file: a missing one gets the ❗ tooltip instead of the ↺ one.
    path = _DIR / f"{dance}{n}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=f"{dance} {n}", dance=dance, duration=150)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _PartyBase(unittest.TestCase):
    """S L S L S | S: LW 4 at the very end is the leftover."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, style=""):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        entries = [_e("LW", 1), _e("TG", 1), _e("QS", 1),
                   _e("CC", 1), _e("RB", 1), _e("JI", 1),
                   _e("LW", 2), _e("SF", 1), _e("QS", 2),
                   _e("SA", 1), _e("CC", 2), _e("RB", 2),
                   _e("LW", 3), _e("TG", 2), _e("SF", 2),
                   _e("LW", 4), _e("QS", 3)]
        t.load_warmup(entries, "ETDS Party", style, "S", True, lambda _p: None, None)
        return t

    def titles(self, t):
        return [m.entry.title for _r, m in t._row_meta.numbered()]

    def row_of(self, t, title):
        return next(r for r, m in t._row_meta.numbered() if m.entry.title == title)


class PartySwapTest(_PartyBase):
    """↺ on the party list."""

    def test_regen_swaps_with_the_leftover(self):
        t = self.table()
        before = self.titles(t)
        t._regen(self.row_of(t, "LW 1"))
        self.app.processEvents()
        after = self.titles(t)
        self.assertEqual(after[0], "LW 4")
        self.assertEqual(after[15], "LW 1")
        self.assertEqual(after[1:15] + after[16:], before[1:15] + before[16:])
        # The rows are drawn with what they now hold.
        self.assertEqual(t.item(self.row_of(t, "LW 4"), 4).text(), "LW 4")

    def test_playing_row_follows_its_song(self):
        t = self.table()
        first = self.row_of(t, "LW 1")
        t._current_play_row = first
        t._regen(first)
        self.app.processEvents()
        self.assertEqual(t._current_play_row, self.row_of(t, "LW 1"))

    def test_regen_button_says_it_swaps(self):
        t = self.table()
        tip = t.cellWidget(self.row_of(t, "LW 1"), _COL_REGEN).toolTip()
        self.assertIn("Swap", tip)

    def test_class_warmup_keeps_the_library_reroll(self):
        t = self.table(style="Latin")
        self.assertNotIn("Swap", t.cellWidget(self.row_of(t, "LW 1"), _COL_REGEN).toolTip())
        with mock.patch.object(t, "_regen_warmup") as reroll:
            t._regen(self.row_of(t, "LW 1"))
        reroll.assert_called_once()


class SwapSelectedTest(_PartyBase):
    """⇅ in the context menu: two selected titles of one dance change places."""

    def select(self, t, *titles):
        t.clearSelection()
        flags = (QItemSelectionModel.SelectionFlag.Select
                 | QItemSelectionModel.SelectionFlag.Rows)
        for title in titles:
            t.selectionModel().select(t.model().index(self.row_of(t, title), 0), flags)

    def test_two_of_the_same_dance_are_a_pair(self):
        t = self.table()
        self.select(t, "LW 1", "LW 3")
        self.assertEqual(t._swappable_pair(),
                         (self.row_of(t, "LW 1"), self.row_of(t, "LW 3")))

    def test_swapping_the_pair_changes_their_places(self):
        t = self.table()
        before = self.titles(t)
        self.select(t, "LW 1", "LW 3")
        t._swap_song_rows(*t._swappable_pair())
        after = self.titles(t)
        self.assertEqual((after[0], after[12]), ("LW 3", "LW 1"))
        self.assertEqual(after[1:12] + after[13:], before[1:12] + before[13:])

    def test_different_dances_are_no_pair(self):
        t = self.table()
        self.select(t, "LW 1", "TG 1")
        self.assertIsNone(t._swappable_pair())
        self.assertTrue(t._two_songs_selected())

    def test_alt_s_swaps_the_selected_pair(self):
        t = self.table()
        self.select(t, "LW 1", "LW 3")
        t.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S,
                                  Qt.KeyboardModifier.AltModifier))
        after = self.titles(t)
        self.assertEqual((after[0], after[12]), ("LW 3", "LW 1"))

    def test_different_dances_get_a_warning_and_stay_put(self):
        t = self.table()
        before = self.titles(t)
        self.select(t, "LW 1", "TG 1")
        with mock.patch("gui.table_actions.QMessageBox.warning") as warn:
            t._swap_selected()
        warn.assert_called_once()
        self.assertIn("Tango", warn.call_args.args[2])
        self.assertEqual(self.titles(t), before)

    def test_not_two_titles_get_a_hint_and_stay_put(self):
        t = self.table()
        before = self.titles(t)
        self.select(t, "LW 1")
        with mock.patch("gui.table_actions.QMessageBox.information") as info:
            t._swap_selected()
        info.assert_called_once()
        self.assertEqual(self.titles(t), before)

    def test_one_or_three_titles_are_no_pair(self):
        t = self.table()
        self.select(t, "LW 1")
        self.assertIsNone(t._swappable_pair())
        self.select(t, "LW 1", "LW 2", "LW 3")
        self.assertIsNone(t._swappable_pair())
        self.assertFalse(t._two_songs_selected())

    def test_class_warmup_swaps_too(self):
        t = self.table(style="Latin")
        self.select(t, "LW 1", "LW 3")
        self.assertIsNotNone(t._swappable_pair())


if __name__ == "__main__":
    unittest.main()
