#!/usr/bin/env python3
"""Tests that ⏹ abandons everything the player was still about to do.

Run:  py -m unittest tests.player.test_stop_abandons_pending -v

A title that is about to be PLAYED waits up to a second for its loudness
measurement (`_await_loudness`). The wait re-enters `_load_track` from a timer
or from the measurement landing. A ⏹ pressed inside that second used to leave
the wait armed, so the title started after the operator had stopped the music.

A real MainWindow is built offscreen with no library scan; only the ffmpeg
lookup and the loudness worker are stood in for, so no decode runs.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_stop_pending_"))

from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _StubLoudnessWorker:
    """A measurement that never lands on its own — the test decides when."""

    class _Sig:
        def connect(self, *_a, **_kw):
            pass

    def __init__(self, *_a, **_kw):
        self.done = self._Sig()
        self.error = self._Sig()

    def start(self):
        pass

    def isRunning(self):
        return True


class _NoLufsCache:
    def get_lufs(self, _path):
        return None

    def put_lufs(self, *_a):
        pass

    def lufs_count(self):
        return 0

    def save(self):
        pass


class StopAbandonsLoudnessWaitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_stop_pending_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win._cache = _NoLufsCache()
        self.win._pv = lambda key: True if key == "loudness" else 0
        patches = [
            mock.patch("player.main_audio.find_ffmpeg", return_value="ffmpeg"),
            mock.patch("player.main_audio.LoudnessWorker", _StubLoudnessWorker),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.path = Path(r"C:\music\tanzcds\standardcd\LW\Unmeasured (LW 29).mp3")

    def _arm_wait(self):
        """Ask for the title to PLAY — it has no level yet, so it waits."""
        self.assertTrue(self.win._await_loudness(self.path, True))
        self.assertEqual(self.win._lufs_pending, self.path)

    def test_stop_during_the_wait_keeps_the_title_silent(self):
        self._arm_wait()
        self.win._on_stop_btn()
        with mock.patch.object(self.win, "_load_track") as load:
            self.win._resume_after_loudness(self.path)   # the wait's timer fires
        load.assert_not_called()

    def test_a_measurement_landing_after_stop_does_not_start_it(self):
        self._arm_wait()
        self.win._on_stop_btn()
        with mock.patch.object(self.win, "_load_track") as load:
            self.win._on_track_lufs(str(self.path), -10.0)
        load.assert_not_called()

    def test_loading_nothing_also_cancels_the_wait(self):
        """`_play_or_stop(None)` is the other way the player is told to stop."""
        self._arm_wait()
        self.win._load_track(None)
        with mock.patch.object(self.win, "_load_track") as load:
            self.win._resume_after_loudness(self.path)
        load.assert_not_called()

    def test_without_a_stop_the_waiting_title_still_starts(self):
        """The fix must not break the wait itself."""
        self._arm_wait()
        with mock.patch.object(self.win, "_load_track") as load:
            self.win._resume_after_loudness(self.path)
        load.assert_called_once_with(self.path, True)

    def test_stop_drops_a_load_held_back_by_the_rate_limit(self):
        """⏭⏭⏭ then ⏹: the burst's last title must not start 250 ms later."""
        self.win._pending_load = (self.path, True)
        self.win._load_timer.start(250)
        self.win._on_stop_btn()
        self.assertIsNone(self.win._pending_load)
        self.assertFalse(self.win._load_timer.isActive())
        with mock.patch.object(self.win, "_load_track") as load:
            self.win._flush_pending_load()
        load.assert_not_called()

    def test_stop_silences_a_running_announcement(self):
        with mock.patch.object(self.win._announcer, "stop") as stop:
            self.win._on_stop_btn()
        stop.assert_called()

    def test_a_waiting_title_already_counts_as_on_the_deck(self):
        """The Similar-Tracks window asks `deck_path()` whether the player is
        still on its preview before it stops it; a title held back by the
        loudness wait or the load rate limit is the one on the deck."""
        self.assertIsNone(self.win.deck_path())
        self._arm_wait()
        self.assertEqual(self.win.deck_path(), self.path)
        other = self.path.with_name("Rate limited (LW 29).mp3")
        self.win._pending_load = (other, True)
        self.assertEqual(self.win.deck_path(), other)
        # Drop the wait, or its timer fires into a torn-down window later.
        self.win._pending_load = None
        self.win._lufs_pending = None


if __name__ == "__main__":
    unittest.main(verbosity=2)
