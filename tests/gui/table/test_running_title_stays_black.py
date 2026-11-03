#!/usr/bin/env python3
"""The running title stays black until it has really been left.

Run:  py -m unittest tests.gui.table.test_running_title_stays_black -v

A title counts as played after 10 s, so it is already marked while it runs.
Only the running row was exempt from the grey, and that row is found by its
id: while a drag re-filled the rows the id had not been handed back yet, so
the moved title greyed there and nothing took the grey off again. Grey is for
a title the player has left: the next one loaded, or the end reached.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_running_black_"))

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_TITLE
from tests.qt_test_support import reap_widget

# Real files: a row whose file is not on disk is painted light red.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_running_black_music_"))
_GREY = QColor("#a8aeb8")


def _e(n):
    path = _MUSIC / f"CC{n}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=f"CC {n}", dance="CC", duration=150)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class RunningTitleStaysBlackTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.entries = [_e(1), _e(2), _e(3), _e(4)]
        win = _Win()
        self.table = PlaylistTable()
        self.table.setParent(win)
        self.addCleanup(reap_widget, win)
        self.table.load_wishlist(list(self.entries), play_cb=lambda *a: None,
                                 suggester=None)
        self.table.set_play_highlight_enabled(True)
        self.running = self.entries[1]
        self.table._current_play_row = 1
        self.table.mark_path_played(str(self.running.path))   # 10 s in

    def greyed(self):
        return {m.entry.title for r, m in self.table._row_meta.numbered()
                if self.table.item(r, _COL_TITLE).foreground().color() == _GREY}

    def test_it_stays_black_once_marked_played(self):
        self.assertEqual(self.greyed(), set())

    def test_dragging_the_running_title_leaves_it_black(self):
        t = self.table
        t._drag_src_rows = [1]
        self.assertTrue(t._reorder_flat(4))
        self.assertEqual(t._row_meta[t._current_play_row].entry, self.running)
        self.assertEqual(self.greyed(), set())

    def test_dragging_another_title_over_it_leaves_it_black(self):
        t = self.table
        t._drag_src_rows = [3]
        self.assertTrue(t._reorder_flat(0))
        self.assertEqual(t._current_play_row, 2)
        self.assertEqual(self.greyed(), set())

    def test_a_new_title_dropped_in_leaves_it_black(self):
        t = self.table
        t._render_flat_entries([_e(9)] + list(self.entries))
        self.assertEqual(t._current_play_row, 2)
        self.assertEqual(self.greyed(), set())

    def test_a_title_played_before_goes_black_while_it_runs_again(self):
        t = self.table
        t.mark_path_played(str(self.entries[2].path))
        self.assertEqual(self.greyed(), {"CC 3"})
        t._current_play_row = 2
        t._update_play_row_hl()
        self.assertEqual(self.greyed(), {"CC 2"})

    def test_the_end_of_the_title_greys_it(self):
        self.table.on_playback_stopped()
        self.assertEqual(self.greyed(), {"CC 2"})

    def test_the_next_title_loaded_greys_it(self):
        self.table.cue_row(2)
        self.assertEqual(self.greyed(), {"CC 2"})


if __name__ == "__main__":
    unittest.main()
