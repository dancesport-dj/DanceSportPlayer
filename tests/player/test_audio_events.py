#!/usr/bin/env python3
"""🔊 The sound card is watched by events, not by a 2 s poll.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_audio_events -v

Windows reports a card plugged in or pulled out AND a switch of the default
output through QMediaDevices.audioOutputsChanged (measured 2026-10-27: every
switch in the sound flyout fired it, the new default already readable). What
else the poll did — the idle countdown, the system-sound mute, the 🔊 badge —
looks again whenever something starts or stops being audible, a setting is
saved, or the outputs change.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_audio_events_"))

from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from gui.window import main_global
from tests.qt_test_support import reap_widget, stub_window_startup

_MAYA = "MAYA44USB Ch12 (3- ESI Audio Device (WDM) - MAYA44USB)"


class _Dialog:
    """⚙ Settings, answered with OK and the settings it was opened with."""

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return dict(self._given)

    def running_look_touched(self):
        return False

    def deleteLater(self):
        pass


class AudioEventsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both",
                                            "release_audio_idle": True})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.device = self.win._audio_device
        if self.win._player is None:
            self.skipTest("no Qt Multimedia")

    def _clock_reset(self):
        self.device.idle_since = None
        self.device._idle_timer.stop()

    @unittest.skipUnless(sys.platform == "win32", "the signal was measured on Windows")
    def test_no_two_second_poll_on_windows(self):
        self.assertIsNone(getattr(self.win, "_device_watch", None))

    def test_the_first_silence_after_the_start_counts(self):
        self.app.processEvents()
        self.assertIsNotNone(self.device.idle_since)
        self.assertTrue(self.device._idle_timer.isActive())

    def test_a_pad_falling_silent_starts_the_clock(self):
        if self.win._cart_voices is None:
            self.skipTest("no cartwall pool")
        self._clock_reset()
        self.win._cart_voices.activeChanged.emit(0)
        self.assertTrue(self.device._idle_timer.isActive())

    def test_an_announcement_ending_starts_the_clock(self):
        self._clock_reset()
        self.win._on_announcer_speaking(False)
        self.assertTrue(self.device._idle_timer.isActive())

    def test_a_card_plugged_in_while_muted_is_muted_too(self):
        with (mock.patch.object(self.device._system_sounds, "active", True),
              mock.patch.object(self.device, "hold_system_sounds") as hold):
            self.device.on_outputs_changed()
        hold.assert_called_once_with(True)

    def test_unmuted_a_changed_output_mutes_nothing(self):
        with mock.patch.object(self.device, "hold_system_sounds") as hold:
            self.device.on_outputs_changed()
        hold.assert_not_called()

    def test_saving_settings_looks_again(self):
        """A switch flipped in ⚙ Settings, and a card chosen there, are
        applied on OK instead of on the next tick."""
        self._clock_reset()
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        with mock.patch.object(self.device, "music_card", return_value=_MAYA):
            self.win._open_settings()
        badge = self.win.statusBar().findChild(QPushButton, "soundBadge")
        self.assertFalse(badge.isHidden())
        self.assertTrue(self.device._idle_timer.isActive())


if __name__ == "__main__":
    unittest.main()
