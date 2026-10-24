#!/usr/bin/env python3
"""Re-loading a theme deck in Playing mode: the played tracks stay grey.

Run:  py -m unittest tests.gui.table.test_theme_reload_greys -v

load() forgets the saved (row, column) colours and greys the played rows
again after the rebuild. load_theme did neither: a re-rolled theme showed
its played tracks as unplayed. The 🤸 warm-up panel (and a player-only
running order, which loads through it) and the ⭐ wishlist had the same gap.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_theme_greys_"))

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_TITLE
from tests.qt_test_support import reap_widget

# Real files: a row whose file is not on disk is painted light red.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_theme_greys_music_"))
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


class ThemeReloadGreysTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.entries = [_e(1), _e(2), _e(3)]
        win = _Win()
        self.table = PlaylistTable()
        self.table.setParent(win)
        self.addCleanup(reap_widget, win)
        self.table.load_theme(list(self.entries), "Party", play_cb=lambda *a: None,
                              suggester=None)
        self.table.set_play_highlight_enabled(True)

    def greyed(self):
        return {m.entry.title for r, m in self.table._row_meta.numbered()
                if self.table.item(r, _COL_TITLE).foreground().color() == _GREY}

    def test_a_played_track_is_grey_again_after_the_reload(self):
        t = self.table
        t.mark_path_played(str(self.entries[1].path))
        self.assertEqual(self.greyed(), {"CC 2"})
        t.load_theme([self.entries[1], self.entries[0], self.entries[2]], "Party",
                     play_cb=lambda *a: None, suggester=None)
        self.assertEqual(self.greyed(), {"CC 2"})

    def test_a_reloaded_warmup_keeps_its_played_track_grey(self):
        t = self.table
        load = lambda entries: t.load_warmup(
            entries, "Party", style="", dance_class="S", relax=True,
            play_cb=lambda *a: None, suggester=None)
        load(list(self.entries))
        t.mark_path_played(str(self.entries[1].path))
        self.assertEqual(self.greyed(), {"CC 2"})
        load([self.entries[2], self.entries[1], self.entries[0]])
        self.assertEqual(self.greyed(), {"CC 2"})

    def test_a_reloaded_wishlist_keeps_its_played_track_grey(self):
        t = self.table
        t.load_wishlist(list(self.entries), play_cb=lambda *a: None, suggester=None)
        t.mark_path_played(str(self.entries[1].path))
        self.assertEqual(self.greyed(), {"CC 2"})
        t.load_wishlist([self.entries[2], self.entries[1]],
                        play_cb=lambda *a: None, suggester=None)
        self.assertEqual(self.greyed(), {"CC 2"})


if __name__ == "__main__":
    unittest.main()
