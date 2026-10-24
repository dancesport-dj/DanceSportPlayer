#!/usr/bin/env python3
"""↺ on a warm-up row keeps that row's stripe colour.

Run:  py -m unittest tests.gui.table.test_warmup_regen_stripe -v

load_warmup stripes by the song's index in the list, but a section header
(Standardrunde 1, …) sits on its own table row. _regen_warmup picked the
stripe from the raw row number, so under one header every re-rolled track
flipped to the other shade.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wstripe_"))

from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_TITLE
from tests.qt_test_support import reap_widget

_DIR = Path(tempfile.mkdtemp(prefix="dp_wstripe_m_"))


def _e(dance, n):
    path = _DIR / f"{dance}{n}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=f"{dance} {n}", dance=dance, duration=150)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _Suggester:
    """Only the re-roll: the next track it hands back is set by the test."""
    next_entry = None

    def regenerate_warmup(self, *a, **kw):
        return self.next_entry

    def similarity(self, *a):
        return None


class WarmupRegenStripeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        win = _Win()
        self.table = PlaylistTable()
        self.table.setParent(win)
        self.addCleanup(reap_widget, win)
        entries = [_e("LW", 1), _e("TG", 1), _e("QS", 1),
                   _e("CC", 1), _e("RB", 1), _e("JI", 1)]
        self.table.load_warmup(entries, "Eintanzen", "", "S", True,
                               lambda _p: None, _Suggester())

    def bg(self, row):
        return self.table.item(row, _COL_TITLE).background().color().name()

    def test_every_song_row_keeps_its_shade_after_a_reroll(self):
        t = self.table
        song_rows = t._row_meta.song_rows()
        self.assertNotEqual(song_rows[0], 0, "expected a section header on row 0")
        for k, row in enumerate(song_rows):
            with self.subTest(row=row):
                before = self.bg(row)
                t._suggester.next_entry = _e("XX", k)
                t._regen_warmup(row)
                self.app.processEvents()
                self.assertEqual(t._row_meta[row].entry.title, f"XX {k}")
                self.assertEqual(self.bg(row), before)


if __name__ == "__main__":
    unittest.main()
