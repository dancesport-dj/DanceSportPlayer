#!/usr/bin/env python3
"""A title whose file vanished after its row was drawn.

Run:  py -m unittest tests.player.window.test_vanished_file -v

A row checks for its file when it is filled, so a file deleted or renamed
while the app runs kept a normal row: no red ❗, and ▶ only left a status-bar
line nobody saw (seen 2026-10-09 with a title on the desktop). The failed
play now repaints the rows that show the file, so they get the ❗, and says
in a toast which file is gone.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_vanished_"))

from PySide6.QtCore import QUrl

from gui.decks.deck_set import DeckSet
from player.audio.playback_state import PlaybackState
from shared.widgets import WARN_TOAST_MS


class _Table:
    def __init__(self):
        self.asked = []

    def refresh_paths(self, paths):
        self.asked.append([str(p) for p in paths])
        return len(paths)

    def refresh_found(self, path):
        self.asked.append(["found", str(path)])
        return 1

    def refresh_issue_marks(self):
        pass


class _Player:
    def __init__(self, path: Path):
        self._url = QUrl.fromLocalFile(str(path))

    def source(self):
        return self._url


class VanishedFileTest(unittest.TestCase):

    def _win(self, path: Path):
        from player.window.main_player import PlayerControlMixin

        class Win(PlayerControlMixin):
            pass

        w = Win()
        w._is_playing_mode = lambda: False
        w._playback = PlaybackState()
        w._player = _Player(path)
        w.table = _Table()
        w._deckset = DeckSet()
        w._deckset.all_tables = [w.table]
        w.reset = []
        w._reset_playback_ui = w.reset.append
        return w

    def test_a_vanished_file_gets_its_rows_repainted_and_a_toast(self):
        gone = Path(tempfile.mkdtemp(prefix="dp_vanished_m_")) / "070 - Treat You Better (JV 43).mp3"
        w = self._win(gone)
        with mock.patch("player.window.main_load.show_toast") as toast:
            w._on_player_error(None, "Could not open file")
        self.assertEqual(w.table.asked, [[str(gone)]])
        self.assertEqual(len(w.reset), 1)
        toast.assert_called_once()
        self.assertIn(str(gone), toast.call_args.args[1])
        # Marcel: as long as the drive-unplugged one, long enough to read it.
        self.assertEqual(toast.call_args.args[2], WARN_TOAST_MS)

    def test_a_file_that_is_there_is_no_missing_file(self):
        fd, name = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self.addCleanup(os.remove, name)
        w = self._win(Path(name))
        with mock.patch("player.window.main_load.show_toast") as toast:
            w._on_player_error(None, "Could not decode")
        self.assertEqual(w.table.asked, [])
        toast.assert_not_called()
        self.assertEqual(len(w.reset), 1)

    def test_a_file_that_loads_clears_its_missing_mark(self):
        """Renamed back on disk: once it opens, its rows drop the red ❗."""
        from PySide6.QtMultimedia import QMediaPlayer
        back = Path(r"C:\m\back.mp3")
        w = self._win(back)
        w._playback = mock.Mock(path=back, pre_roll_ms=0, ready_logged=True)
        w._resume_seek_ms = None
        w._on_media_status(QMediaPlayer.MediaStatus.BufferedMedia)
        self.assertEqual(w.table.asked, [])
        w._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(w.table.asked, [["found", str(back)]])


if __name__ == "__main__":
    unittest.main()
