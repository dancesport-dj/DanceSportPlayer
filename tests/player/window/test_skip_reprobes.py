#!/usr/bin/env python3
"""Tests that a fast skip does not leave the next title unprobed.

Run:  py -m unittest tests.player.window.test_skip_reprobes -v

L13: one 🔇 silence probe and one 📊 loudness measurement run at a time. A
title skipped a few seconds in still held that slot, so the title the hall
heard next got neither: no stillness skip, and it played at its own level
in an equalized round. The skipped title's probe now gives way.

A real MainWindow is built offscreen with no library scan; ffmpeg and both
workers are stood in for, so no decode runs.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_skip_reprobe_"))

from tests.qt_test_support import (
    reap_widget, stub_window_startup)


class _Worker:
    """A probe that never lands on its own."""

    started = []

    class _Sig:
        def connect(self, *_a, **_kw):
            pass

    def __init__(self, path, _ffmpeg, parent=None):
        self.path = Path(path)
        self.done = self._Sig()
        self.error = self._Sig()
        self.cancelled = False

    def start(self):
        self.started.append(self)

    def isRunning(self):
        return True

    def cancel(self):
        self.cancelled = True


class _Cache:
    def get_lufs(self, _path):
        return None

    def get_silences(self, _path):
        return None

    def lufs_count(self):
        return 0


class SkipReprobesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_skip_reprobe_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win._library.cache = _Cache()
        self.win._pv = lambda key: True if key == "loudness" else 0
        _Worker.started = []
        patches = [
            mock.patch("player.window.main_audio.find_ffmpeg", return_value="ffmpeg"),
            mock.patch("player.window.main_audio.LoudnessWorker", _Worker),
            mock.patch("player.window.main_audio.SilenceWorker", _Worker),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.skipped = Path(r"C:\music\LW\Skipped (LW 29).mp3")
        self.next = Path(r"C:\music\LW\Next (LW 29).mp3")

    def test_the_next_title_gets_its_own_silence_probe(self):
        self.win._ensure_silences(self.skipped)
        first = self.win._silence_worker
        self.win._ensure_silences(self.next)
        self.assertTrue(first.cancelled)
        self.assertEqual(self.win._silence_worker.path, self.next)
        self.assertEqual(len(_Worker.started), 2)

    def test_the_same_title_again_is_not_probed_twice(self):
        self.win._ensure_silences(self.skipped)
        self.win._ensure_silences(self.skipped)
        self.assertFalse(_Worker.started[0].cancelled)
        self.assertEqual(len(_Worker.started), 1)

    def test_one_failed_probe_is_tried_again_on_the_next_load(self):
        """PL11: a file locked for a moment (a virus scan) lost its stillness
        skip until the app restarted."""
        key = str(self.skipped)
        self.win._on_silence_error(key, "Permission denied")
        self.assertIsNone(self.win._silences.get(key))
        self.win._ensure_silences(self.skipped)
        self.assertEqual(len(_Worker.started), 1)

    def test_a_second_failure_is_remembered(self):
        key = str(self.skipped)
        self.win._on_silence_error(key, "Invalid data found")
        self.win._on_silence_error(key, "Invalid data found")
        self.assertEqual(self.win._silences[key], [])
        self.win._ensure_silences(self.skipped)
        self.assertEqual(_Worker.started, [])

    def test_the_next_title_gets_its_own_level(self):
        self.win._await_loudness(self.skipped, False)
        first = self.win._lufs_worker
        self.assertTrue(self.win._await_loudness(self.next, True))
        self.assertTrue(first.cancelled)
        self.assertEqual(self.win._lufs_worker.path, self.next)
        self.assertEqual(self.win._lufs_pending, self.next)
        # Drop the wait, or its timer fires into a torn-down window later.
        self.win._lufs_pending = None

    def test_a_measurement_already_running_for_it_is_kept(self):
        self.win._await_loudness(self.next, False)     # the pause's preload
        self.assertFalse(self.win._await_loudness(self.next, True))
        self.assertFalse(_Worker.started[0].cancelled)
        self.assertEqual(len(_Worker.started), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
