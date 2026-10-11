#!/usr/bin/env python3
"""Tests for a deck row's ▶ and ↺: painted by a delegate, not cell widgets.

Run:  py -m unittest tests.gui.test_row_buttons -v

Every song row used to carry two QPushButton cell widgets. A start restores
~460 rows, and those ~930 widgets were ~0.85 s of the ~1.2 s fill (measured
2026-10-09). The cell now holds an item and `gui.row_buttons` paints the
button; a click is resolved to the row it lands on at click time, so a row
inserted or removed above never makes it play the wrong title.
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
                      tempfile.mkdtemp(prefix="dp_rowbtn_"))

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from gui.playlist_table import PlaylistTable
from gui.row_buttons import BUTTON_ROLE, BUTTON_SIZE, LOOK_ROLE, button_rect
from gui.running_order import Row, RunningOrder
from planner.models import MusicEntry
from shared.columns import _COL_PLAY, _COL_REGEN, _COL_TITLE
from tests.qt_test_support import reap_widget


_MUSIC = Path(tempfile.mkdtemp(prefix="dp_rowbtn_m_"))


def _meta(name: str, h_idx: int, exists: bool = True) -> Row:
    path = _MUSIC / f"{name}.mp3"
    if exists:
        path.write_bytes(b"x")
    entry = MusicEntry(path=path, title=name, dance="WW", bpm=29)
    return Row(entry=entry, dance="WW", h_idx=h_idx)


class _Win(QWidget):
    def _is_player_running(self) -> bool:
        return True

    def _is_player_stopped(self) -> bool:
        return False


class RowButtonsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self, *, play=True):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 300)
        t.setRowCount(3)
        t._row_meta = RunningOrder([_meta("first", 0), _meta("second", 1), _meta("third", 2)])
        self.played = []
        t._play_cb = self.played.append if play else None
        for row in range(3):
            t._refill_row(row, t._row_meta[row])
        win.show()
        self.addCleanup(reap_widget, win)
        return t

    def button_center(self, t, row, col) -> QPoint:
        return button_rect(t.visualRect(t.model().index(row, col))).center()

    def click(self, t, row, col, at=None):
        QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         at if at is not None else self.button_center(t, row, col))

    def test_the_button_sits_in_the_middle_of_its_cell(self):
        t = self.deck()
        for col in (_COL_PLAY, _COL_REGEN):
            cell = t.visualRect(t.model().index(1, col))
            btn = button_rect(cell)
            self.assertEqual(btn.size(), BUTTON_SIZE)
            self.assertLessEqual(abs(btn.center().x() - cell.center().x()), 1, col)
            self.assertLessEqual(abs(btn.center().y() - cell.center().y()), 1, col)

    def test_a_header_regen_button_lines_up_with_the_song_rows(self):
        t = self.deck()
        row = t._add_span_row("Waltz", QColor("white"), QColor("black"), True,
                              regen_cb=lambda: None)
        self.app.processEvents()
        holder = t.cellWidget(row, _COL_REGEN)
        btn = holder.findChild(QPushButton)
        song = button_rect(t.visualRect(t.model().index(1, _COL_REGEN)))
        head = QRect(btn.mapTo(t.viewport(), QPoint(0, 0)), btn.size())
        self.assertLessEqual(abs(head.center().x() - song.center().x()), 1)

    def test_a_song_row_builds_no_cell_widget(self):
        t = self.deck()
        for row in range(3):
            self.assertIsNone(t.cellWidget(row, _COL_PLAY))
            self.assertIsNone(t.cellWidget(row, _COL_REGEN))
            self.assertEqual(t.play_glyph(row), "▶")

    def test_clicking_play_starts_that_row(self):
        t = self.deck()
        self.click(t, 1, _COL_PLAY)
        self.assertEqual(self.played, [_MUSIC / "second.mp3"])
        self.assertEqual(t.play_glyph(1), "■")
        self.click(t, 1, _COL_PLAY)                    # same row again: stop
        self.assertEqual(self.played[-1], None)
        self.assertEqual(t.play_glyph(1), "▶")

    def test_the_row_is_read_at_click_time(self):
        t = self.deck()
        t.insertRow(0)                                 # everything moves one down
        with mock.patch.object(t, "_on_play_click") as play:
            self.click(t, 2, _COL_PLAY)
        play.assert_called_once_with(2, _MUSIC / "second.mp3")

    def test_a_file_not_on_disk_shows_its_mark_on_the_play_button(self):
        # Playing mode hides the ↺ column, and with it the red ❗ a missing
        # file used to get only there — the ▶ is what stays on screen.
        t = self.deck()
        t._row_meta[1] = _meta("gone", 1, exists=False)
        t._refill_row(1, t._row_meta[1])
        self.assertEqual(t.play_glyph(1), "❗")
        it = t.item(1, _COL_PLAY)
        self.assertEqual(it.data(LOOK_ROLE), "missing")
        self.assertIn(str(_MUSIC / "gone.mp3"), it.toolTip())
        self.assertEqual(t.play_glyph(0), "▶")
        # one ❗ per row: planning shows the ↺ column too, and it stays a ↺
        self.assertEqual(t.item(1, _COL_REGEN).data(BUTTON_ROLE), "↺")

    def test_a_marked_row_is_orange_without_a_mark_glyph(self):
        # The orange row says "marked"; a ❗ on its ↺ read like a missing file.
        t = self.deck()
        t._marked_paths.add(str(_MUSIC / "second.mp3"))
        t._refill_row(1, t._row_meta[1])
        regen = t.item(1, _COL_REGEN)
        self.assertEqual(regen.data(BUTTON_ROLE), "↺")
        self.assertEqual(regen.data(LOOK_ROLE), "plain")
        self.assertIn("Marked for potential replace", regen.toolTip())
        self.assertEqual(t.play_glyph(1), "▶")

    def test_a_missing_file_tints_its_whole_row_light_red(self):
        from gui.playlist_table import _C_MISSING_BG
        t = self.deck()
        t._row_meta[1] = _meta("gone", 1, exists=False)
        t._refill_row(1, t._row_meta[1])
        t._restripe_song_rows(0)                # a row inserted above re-shades the rest
        for col in (_COL_PLAY, _COL_TITLE, _COL_REGEN):
            self.assertEqual(t.item(1, col).background().color(), _C_MISSING_BG, col)
        self.assertNotEqual(t.item(0, _COL_TITLE).background().color(), _C_MISSING_BG)

    def test_a_file_back_on_disk_loses_its_mark_once_it_plays(self):
        # Renamed back while the app ran: the click plays it, but only swapped
        # the glyph — the row kept its missing look until it was refilled.
        t = self.deck()
        t._row_meta[1] = _meta("gone", 1, exists=False)
        t._refill_row(1, t._row_meta[1])
        (_MUSIC / "gone.mp3").write_bytes(b"x")
        self.addCleanup((_MUSIC / "gone.mp3").unlink)
        self.click(t, 1, _COL_PLAY)
        self.assertEqual(t.refresh_found(_MUSIC / "gone.mp3"), 1)
        self.assertEqual(t.play_glyph(1), "■")
        self.assertEqual(t.item(1, _COL_PLAY).data(LOOK_ROLE), "plain")
        self.assertEqual(t.refresh_found(_MUSIC / "gone.mp3"), 0, "nothing left to clear")

    def test_clicking_regen_rerolls_that_row(self):
        t = self.deck()
        with mock.patch.object(t, "_regen") as regen:
            self.click(t, 2, _COL_REGEN)
        regen.assert_called_once_with(2)

    def test_a_click_beside_the_button_is_no_press(self):
        t = self.deck()
        rect = t.visualRect(t.model().index(1, _COL_PLAY))
        with mock.patch.object(t, "_on_play_click") as play:
            self.click(t, 1, _COL_PLAY, at=rect.bottomRight() - QPoint(1, 1))
        play.assert_not_called()

    def test_without_a_player_the_button_is_off(self):
        t = self.deck(play=False)
        with mock.patch.object(t, "_on_play_click") as play:
            self.click(t, 0, _COL_PLAY)
        play.assert_not_called()

    def test_a_press_on_a_button_does_not_select_the_row(self):
        t = self.deck()
        t.setCurrentCell(0, _COL_TITLE)
        with mock.patch.object(t, "_regen"):
            self.click(t, 2, _COL_REGEN)
        self.assertEqual(t.currentRow(), 0)


if __name__ == "__main__":
    unittest.main()
