#!/usr/bin/env python3
"""🔇 Starting Playing mode on a rehearsal audio profile says so: the hall
would hear nothing. A red toast, not a dialog — preparing at home is no reason
to be nagged, and the 🚦 Ready? line already stands guard before the evening.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_rehearsal_play_warning -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rehearsal_warn_"))

from PySide6.QtWidgets import QApplication

from player.window import main_player
from shared.audio import profiles
from tests.qt_test_support import reap_widget, stub_window_startup

HALL = {"music": {"id": "aa", "name": "PA"}}
HOME = {"music": {"id": "bb", "name": "Phones"}}


class RehearsalPlayWarningTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        profiles.save_profile(self.win._settings, "Tournament", HALL)
        profiles.save_profile(self.win._settings, "Rehearsal", HOME, private=True)

    def _enter(self, playing=True):
        with mock.patch.object(main_player, "show_toast") as toast, \
                mock.patch.object(main_player, "save_settings"):
            self.win._set_play_mode(playing)
        return toast

    def test_playing_on_a_rehearsal_profile_toasts_a_red_warning(self):
        profiles.switch_profile(self.win._settings, "Rehearsal")
        toast = self._enter()
        toast.assert_called_once()
        args, kwargs = toast.call_args
        self.assertIn("Rehearsal", args[1])
        self.assertTrue(kwargs.get("error"))

    def test_playing_on_a_hall_profile_says_nothing(self):
        profiles.switch_profile(self.win._settings, "Tournament")
        self._enter().assert_not_called()

    def test_playing_on_main_says_nothing(self):
        profiles.switch_profile(self.win._settings, "Main")
        self._enter().assert_not_called()

    def test_playing_with_no_profile_active_says_nothing(self):
        profiles.clear_active(self.win._settings)
        self._enter().assert_not_called()

    def test_going_back_to_planning_says_nothing(self):
        profiles.switch_profile(self.win._settings, "Rehearsal")
        self._enter(playing=False).assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
