#!/usr/bin/env python3
"""An error the backend raised for the previous title does not skip the next.

Run:  py -m unittest tests.player.window.test_stale_player_error -v

The media backend reports errors from its own thread, so they reach the window
as queued events. One raised for the title that was just replaced can still be
waiting when ⏭ loads the next title; `_on_player_error` then read the NEW
source, marked that good title as failed and skipped it. Errors already queued
before the new source was set belong to the old title and are only logged.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_stale_error_"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from tests.player.audio.test_pitch_gap import _Desk, _entry
from tests.qt_test_support import reap_widget


class StalePlayerErrorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        table.load_warmup([_entry("SW", 1, 29), _entry("SW", 2, 29)],
                          "🤸 Eintanzen", "both", "S", False,
                          lambda *a: None, None)
        row = next(r for r, m in enumerate(table._row_meta)
                   if m and m.entry is not None)
        self.desk = _Desk(table, tso=False)
        self.addCleanup(reap_widget, self.desk)
        self.failed = []
        self.desk._playback_failed = lambda path, *a: self.failed.append(path)
        table._current_play_row = row
        self.path = table._row_meta[row].entry.path

    def backend_error(self, text: str):
        """As the backend thread delivers it: queued, not called directly."""
        QTimer.singleShot(0, lambda: self.desk._on_player_error(None, text))

    def test_an_error_queued_before_the_load_is_ignored(self):
        self.backend_error("the previous title broke")
        self.desk._load_track(self.path)
        QApplication.processEvents()
        self.assertEqual(self.failed, [])

    def test_an_error_after_the_load_still_fails_the_title(self):
        self.desk._load_track(self.path)
        QApplication.processEvents()
        self.backend_error("this title broke")
        QApplication.processEvents()
        self.assertEqual([str(p) for p in self.failed], [str(self.path)])


if __name__ == "__main__":
    unittest.main()
