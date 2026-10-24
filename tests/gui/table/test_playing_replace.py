#!/usr/bin/env python3
"""A replace on the playing row never cuts the floor.

Run:  py -m unittest tests.gui.table.test_playing_replace -v

↺, a drop onto the row and a 🔁 replace used to do three different things to
the title that was playing: the re-rolls switched playback to the new pick,
the drop and the 🔁 stopped the music, the 🧭 reference swap kept it going.
Now every one of them keeps the sounding title playing. The row shows the new
title and keeps its ■: auto-advance, next-up and the 🏁 round end all count on
from the play cursor, so clearing it would end the evening after this title.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_playing_replace_"))

from PySide6.QtWidgets import QApplication, QMessageBox

from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)
_DIR = Path(tempfile.mkdtemp(prefix="dp_playing_replace_m_"))


def _e(dance, n):
    path = _DIR / f"{dance}{n}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=f"{dance} {n}", dance=dance, duration=150)


class _Lib:
    def __init__(self):
        self.next_entry = None
        self.entries = []

    def entry_for(self, *_a, **_kw):
        return self.next_entry


class _Suggester:
    """Hands back a fresh title of the asked dance on every re-roll."""

    def __init__(self):
        self.lib = _Lib()
        self.n = 100

    def _fresh(self, dance):
        self.n += 1
        return _e(dance or "LW", self.n)

    def regenerate(self, dance, *_a, **_kw):
        return self._fresh(dance)

    def regenerate_warmup(self, dance, *_a, **_kw):
        return self._fresh(dance)

    def similarity(self, *_a):
        return None

    def anchor_similarity(self, *_a, **_kw):
        return None

    def set_similarity(self, *_a):
        pass


class PlayingReplaceTest(unittest.TestCase):

    def setUp(self):
        for name in ("information", "critical", "question"):
            p = mock.patch.object(QMessageBox, name)
            p.start()
            self.addCleanup(p.stop)

    def table(self):
        from gui.table.playlist_table import PlaylistTable
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def deck(self):
        t = self.table()
        playlist = {"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                    "Finale": [[_e("LW", 3), _e("TG", 4)]]}
        rounds = [RoundConfig(name=n, heats=1, tier="final") for n in playlist]
        t.load(playlist, ["LW", "TG"], rounds, "S", play_cb=None,
               suggester=_Suggester(), use_timbre=False)
        return t

    def warmup(self):
        t = self.table()
        t.load_warmup([_e("LW", 1), _e("TG", 2)], "Eintanzen", style="Standard",
                      dance_class="S", relax=True, play_cb=None,
                      suggester=_Suggester())
        return t

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in enumerate(t._row_meta)
                    if m and m.entry is not None and m.entry.title == title)

    def start(self, t, title):
        """`title` is on the floor: cursor and ■ on its row, the player wired."""
        row = self.row_of(t, title)
        self.calls = []
        t._play_cb = self.calls.append
        t._current_play_row = row
        t.sync_play_glyph(True)
        self.assertEqual(t.play_glyph(row), "■")
        self.clicks = mock.patch.object(t, "_on_play_click").start()
        self.addCleanup(mock.patch.stopall)
        return row

    def assert_kept_playing(self, t, row, old_title):
        _app.processEvents()
        self.assertNotEqual(t._row_meta[row].entry.title, old_title)
        self.assertEqual(self.calls, [], "the player was told to stop or switch")
        self.clicks.assert_not_called()
        self.assertEqual(t._current_play_row, row)
        self.assertEqual(t.play_glyph(row), "■")

    def test_the_song_reroll_keeps_playing(self):
        t = self.deck()
        row = self.start(t, "LW 1")
        t._regen(row)
        self.assert_kept_playing(t, row, "LW 1")

    def test_the_warmup_reroll_keeps_playing(self):
        t = self.warmup()
        row = self.start(t, "TG 2")
        t._regen(row)
        self.assert_kept_playing(t, row, "TG 2")

    def test_the_dance_reroll_keeps_playing(self):
        t = self.deck()
        row = self.start(t, "TG 2")
        meta = t._row_meta[row]
        t._regen_dance(meta.round_name, meta.d_idx, meta.dance)
        self.assert_kept_playing(t, row, "TG 2")

    def test_the_round_reroll_keeps_playing(self):
        t = self.deck()
        row = self.start(t, "LW 3")
        t._regen_round(t._row_meta[row].round_name)
        self.assert_kept_playing(t, row, "LW 3")

    def test_a_drop_onto_the_playing_row_keeps_playing(self):
        t = self.deck()
        row = self.start(t, "LW 1")
        t._suggester.lib.next_entry = _e("LW", 9)
        self.assertTrue(t._replace_row_with_path(row, _DIR / "LW9.mp3"))
        self.assert_kept_playing(t, row, "LW 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
