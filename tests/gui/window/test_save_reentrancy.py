#!/usr/bin/env python3
"""A save in progress takes no second click before its dialog is up.

Run:  py -m unittest tests.gui.window.test_save_reentrancy -v

L23: the save loops repaint their progress bar with processEvents(), and the
bar's dialog only appears (and only blocks the window) after 250 ms. Until
then every queued click and key reached the window: a second 💾 Save-all
started a whole save inside the first, with its own summary box on top.
The loops have no Cancel button, so they need no input while they run.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_save_reentry_"))

from PySide6.QtCore import QEventLoop

from dancesport_planner import MusicEntry
from tests.qt_test_support import reap_widget, stub_window_startup

_TMP = Path(tempfile.mkdtemp(prefix="dp_save_reentry_files_"))


class _QueuedClick:
    """processEvents as Qt runs it: a click waiting in the queue is delivered
    unless the call excludes user input."""

    def __init__(self, click):
        self._click = click
        self.delivered = 0

    def __call__(self, flags=QEventLoop.ProcessEventsFlag.AllEvents, *_a):
        if flags & QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents:
            return
        if self.delivered == 0:
            self.delivered += 1
            self._click()


class SaveReentrancyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        track = _TMP / "c1.mp3"
        track.touch()
        self.win._deckset.tableB.load_player_list(
            [MusicEntry(path=track, title="c1", dance="CC", duration=180)],
            "Party", play_cb=None)

    def test_a_second_save_all_click_waits_for_the_first(self):
        from gui.window import main_export
        out_dir = _TMP / "all"
        box = mock.MagicMock()
        box.clickedButton.return_value = None
        pump = _QueuedClick(self.win._save_all_playlists)
        with mock.patch.object(main_export, "OUTPUT_DIR", out_dir), \
                mock.patch("planner.playlist.m3u.OUTPUT_DIR", out_dir), \
                mock.patch.object(main_export, "QMessageBox", return_value=box), \
                mock.patch.object(main_export.QApplication, "processEvents", pump):
            self.win._save_all_playlists()
        self.assertEqual(pump.delivered, 0, "the click ran a save inside the save")
        self.assertEqual(box.exec.call_count, 1)

    def test_a_single_save_takes_no_input_while_it_writes(self):
        from gui.window import main_export
        clicks = []
        pump = _QueuedClick(lambda: clicks.append(1))

        def fn(cb):
            cb(1, 2, "a")
            cb(2, 2, "b")
            return "done"

        with mock.patch.object(main_export.QApplication, "processEvents", pump):
            self.assertEqual(self.win._run_export("💾 Saving…", fn), "done")
        self.assertEqual(clicks, [])


if __name__ == "__main__":
    unittest.main()
