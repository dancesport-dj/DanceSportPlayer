#!/usr/bin/env python3
"""Tests that a title with a loudness but no true peak gets its peak measured.

Run:  py -m unittest tests.player.window.test_peak_backfill -v

Review #15: 2198 paths held a LUFS without a peak, written before the peak was
measured. 📊 walks the library folder only and `_await_loudness` left alone
whatever had a LUFS, so nothing ever reached the titles outside it, and the
gain could not be capped by a peak it never heard of. Playing or preloading
such a title now measures it, without a wait, for the next time it plays.

A real MainWindow is built offscreen with no library scan; ffmpeg and the worker
are stood in for, so no decode runs.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_peak_backfill_"))

from tests.qt_test_support import reap_widget, stub_window_startup


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in self.slots:
            slot(*args)


class _Worker:
    """A measurement that lands when the test says so."""

    started = []

    def __init__(self, path, _ffmpeg, parent=None):
        self.path = Path(path)
        self.done = _Signal()
        self.error = _Signal()
        self.cancelled = False
        self.running = True

    def start(self):
        self.started.append(self)

    def isRunning(self):
        return self.running

    def cancel(self):
        self.cancelled = True


class _Cache:
    def __init__(self, lufs=-14.0, tp=None):
        self.lufs = lufs
        self.tp = tp
        self.put = []

    def get_lufs(self, _path):
        return self.lufs

    def get_tp(self, _path):
        return self.tp

    def put_lufs(self, path, lufs, tp=None):
        self.put.append((path, lufs, tp))

    def save(self):
        pass

    def get_silences(self, _path):
        return None

    def lufs_count(self):
        return 1


class PeakBackfillTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_peak_backfill_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.cache = _Cache()
        self.win._library.cache = self.cache
        self.win._pv = lambda key: True if key == "loudness" else 0
        _Worker.started = []
        patches = [
            mock.patch("player.window.main_audio.find_ffmpeg", return_value="ffmpeg"),
            mock.patch("player.window.main_audio.LoudnessWorker", _Worker),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.path = Path(r"C:\music\SB\Old (SB 50).mp3")

    def test_no_peak_is_measured_and_nobody_waits(self):
        self.assertFalse(self.win._await_loudness(self.path, True))
        self.assertEqual([w.path for w in _Worker.started], [self.path])
        self.assertIsNone(self.win._lufs_pending)

    def test_a_title_with_its_peak_is_left_alone(self):
        self.cache.tp = -1.0
        self.assertFalse(self.win._await_loudness(self.path, True))
        self.assertEqual(_Worker.started, [])

    def test_the_number_is_kept_for_the_next_play(self):
        self.win._await_loudness(self.path, True)
        _Worker.started[0].done.emit(str(self.path), -13.9, -0.5)
        self.assertEqual(self.cache.put, [(self.path, -13.9, -0.5)])

    def test_a_title_on_the_speakers_keeps_its_level(self):
        """The peak can cut the gain by several dB: mid-song the floor would
        hear the drop. The next play starts at the right level instead."""
        self.win._await_loudness(self.path, True)
        self.win._playback.path = self.path
        with mock.patch.object(self.win._mix, "ramp_gain_to") as ramp:
            _Worker.started[0].done.emit(str(self.path), -13.9, -0.5)
        ramp.assert_not_called()

    def test_a_file_without_a_peak_is_measured_once(self):
        self.win._await_loudness(self.path, True)
        _Worker.started[0].running = False
        _Worker.started[0].done.emit(str(self.path), -13.9, None)
        self.win._await_loudness(self.path, True)
        self.assertEqual(len(_Worker.started), 1)
        self.assertEqual(self.cache.put, [])   # the LUFS on record stays

    def test_a_failed_measurement_is_not_tried_again(self):
        self.win._await_loudness(self.path, True)
        _Worker.started[0].running = False
        _Worker.started[0].error.emit(str(self.path), "Invalid data found")
        self.win._await_loudness(self.path, True)
        self.assertEqual(len(_Worker.started), 1)

    def test_a_measurement_of_another_title_is_not_cancelled(self):
        """That one fills a title nobody measured, which matters more."""
        other = _Worker(r"C:\music\SB\New (SB 50).mp3", "ffmpeg")
        self.win._lufs_worker = other
        self.win._await_loudness(self.path, True)
        self.assertFalse(other.cancelled)
        self.assertEqual(_Worker.started, [])

    def test_a_peak_skipped_for_a_busy_slot_runs_when_it_frees(self):
        """#12: the title was dropped for good if another measurement ran."""
        other = _Worker(r"C:\music\SB\New (SB 50).mp3", "ffmpeg")
        self.win._lufs_worker = other
        self.win._await_loudness(self.path, True)
        self.assertEqual(_Worker.started, [])
        self.win._on_track_lufs(str(other.path), -14.0, -1.0)
        self.assertEqual([w.path for w in _Worker.started], [self.path])

    def test_a_new_title_outranks_a_running_peak(self):
        self.win._await_loudness(self.path, True)
        peak = _Worker.started[0]
        self.cache.lufs = None
        fresh = Path(r"C:\music\SB\New (SB 50).mp3")
        self.assertTrue(self.win._await_loudness(fresh, True))
        self.win._lufs_pending = None   # or its timer fires into a torn-down window
        self.assertTrue(peak.cancelled)
        self.assertEqual(self.win._lufs_worker.path, fresh)

    def test_a_single_measurement_says_so_in_the_status_bar_and_clears_it(self):
        self.win.statusBar().clearMessage()
        self.win._await_loudness(self.path, True)
        self.assertIn("Measuring loudness", self.win.statusBar().currentMessage())
        _Worker.started[0].done.emit(str(self.path), -13.9, -0.5)
        self.assertEqual(self.win.statusBar().currentMessage(), "")

    def test_a_failed_measurement_clears_it_too(self):
        self.win.statusBar().clearMessage()
        self.win._await_loudness(self.path, True)
        _Worker.started[0].error.emit(str(self.path), "Invalid data found")
        self.assertEqual(self.win.statusBar().currentMessage(), "")

    def test_somebody_elses_message_is_not_wiped(self):
        self.win.statusBar().clearMessage()
        self.win._await_loudness(self.path, True)
        self.win.statusBar().showMessage("🔇 Skipped 3s of leading silence.")
        _Worker.started[0].done.emit(str(self.path), -13.9, -0.5)
        self.assertEqual(self.win.statusBar().currentMessage(),
                         "🔇 Skipped 3s of leading silence.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
