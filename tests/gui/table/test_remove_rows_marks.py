#!/usr/bin/env python3
"""Removing wishlist rows in Playing mode: the frame and the grey follow.

Run:  py -m unittest tests.gui.table.test_remove_rows_marks -v

The played colours are saved by (row, column) and the blue playing-row frame
is placed at a row's position. A swap and a re-order took care of both, a
removal did neither: the frame stayed where the playing row had been and so
framed the song below it, and a greyed row that moved up kept its grey for good
once Playing mode ended, while another row got its saved colours.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_remove_marks_"))

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_TITLE
from tests.qt_test_support import reap_widget

# Real files: a row whose file is not on disk is painted light red.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_remove_marks_music_"))
_GREY = QColor("#a8aeb8")


def _e(n):
    path = _MUSIC / f"SW{n}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=f"SW {n}", dance="SW", duration=150)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class RemoveRowsMarksTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.entries = [_e(1), _e(2), _e(3), _e(4)]
        win = _Win()
        self.table = PlaylistTable()
        self.table.setParent(win)
        self.table.resize(700, 400)
        self.addCleanup(reap_widget, win)
        self.table.load_wishlist(list(self.entries), play_cb=lambda *a: None,
                                 suggester=None)
        self.table.set_play_highlight_enabled(True)

    def row_of(self, title):
        return next(r for r, m in self.table._row_meta.numbered()
                    if m.entry.title == title)

    def greyed(self):
        return {m.entry.title for r, m in self.table._row_meta.numbered()
                if self.table.item(r, _COL_TITLE).foreground().color() == _GREY}

    def test_the_frame_stays_on_the_playing_title(self):
        t = self.table
        t._current_play_row = self.row_of("SW 3")
        t._update_play_row_hl()
        t._remove_rows([self.row_of("SW 1")])
        row = t._current_play_row
        self.assertEqual(t._row_meta.at(row).entry.title, "SW 3")
        self.assertEqual(t._play_row_hl.geometry().y(), t.rowViewportPosition(row))

    def test_a_played_title_that_moved_up_is_not_grey_in_planning_mode(self):
        t = self.table
        t.mark_path_played(str(self.entries[2].path))     # "SW 3" was heard
        t._remove_rows([self.row_of("SW 1")])
        self.assertEqual(self.greyed(), {"SW 3"})
        t.set_play_highlight_enabled(False)
        self.assertEqual(self.greyed(), set())


if __name__ == "__main__":
    unittest.main()
