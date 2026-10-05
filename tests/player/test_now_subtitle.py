#!/usr/bin/env python3
"""Tests for the player card's subtitle (dance · takt · 🥁 bpm).

Run:  py -m unittest tests.player.test_now_subtitle -v

The dance on it is written the way the desk knows it — the Σ line's short
form, Samba SB and Jive JV — not as the internal code SA / JI. The real
`_load_track` runs, on the reduced desk of test_pitch_gap.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_subtitle_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from tests.player.test_pitch_gap import _Desk, _entry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class NowSubtitleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _subtitle(self, dance: str, bpm: int) -> str:
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        table.load_warmup([_entry(dance, 1, bpm), _entry(dance, 2, bpm)],
                          "🤸 Eintanzen", "both", "S", False,
                          lambda *a: None, None)
        row = next(r for r, m in enumerate(table._row_meta)
                   if m and m.entry is not None)
        desk = _Desk(table, tso=False)
        self.addCleanup(reap_widget, desk)
        seen = []
        desk._big_player.set_now = lambda title, sub="", **kw: seen.append(sub)
        table._current_play_row = row
        desk._load_track(table._row_meta[row].entry.path)
        return seen[-1]

    def test_samba_is_written_sb(self):
        self.assertEqual(self._subtitle("SA", 50), "SB  ·  T50")

    def test_jive_is_written_jv(self):
        self.assertEqual(self._subtitle("JI", 43), "JV  ·  T43")

    def test_a_dance_without_another_abbreviation_keeps_its_code(self):
        self.assertEqual(self._subtitle("QS", 51), "QS  ·  T51")


if __name__ == "__main__":
    unittest.main()
