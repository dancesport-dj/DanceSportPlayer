#!/usr/bin/env python3
"""🎧 The active audio profile is kept across a restart, a rehearsal one too.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_rehearsal_kept -v

Marcel: "the profile changes are not saved and persisted between sessions. i
want them to be saved." The app used to leave a rehearsal profile at start
(back on Main, a red toast); it now opens on whatever was active when it was
closed. Entering Playing mode on a rehearsal profile still warns (see
test_rehearsal_play_warning). Main and Rehearsal themselves are added to a
settings file that has none, and that is saved.
"""
import copy
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rehearsal_start_"))

from PySide6.QtWidgets import QApplication

from shared.audio import profiles
from tests.qt_test_support import reap_widget, stub_window_startup

HALL = {"music": {"id": "aa", "name": "PA"}}
HOME = {"music": {"id": "bb", "name": "Phones"}}


def _settings(active, seeded=False):
    """`seeded`: a file that already holds Main and Rehearsal, as a saved one does."""
    s = {"app_mode": "both"}
    profiles.save_profile(s, "Rehearsal", HOME, private=True)
    profiles.save_profile(s, "Tournament", HALL)
    if seeded:
        profiles.save_profile(s, "Main", HALL)
    profiles.switch_profile(s, active)
    return copy.deepcopy(s)


class _Start(unittest.TestCase):
    active = "Rehearsal"
    seeded = False

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, _settings(cls.active, cls.seeded))

    def build(self):
        """The window, what it saved, and the delayed callbacks it scheduled."""
        with mock.patch.object(self.gui, "save_settings") as save, \
                mock.patch.object(self.gui.QTimer, "singleShot") as later:
            win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win, save, later

    @staticmethod
    def announcement(later):
        """The callback scheduled for 2 s after the start, None if there is none."""
        for call in later.call_args_list:
            if call.args[0] == 2000:
                return call.args[-1]
        return None


class RehearsalLeftOnTest(_Start):
    seeded = True

    def test_the_app_starts_on_the_rehearsal_profile(self):
        win, _save, _later = self.build()
        self.assertEqual(profiles.active_profile(win._settings), "Rehearsal")
        self.assertEqual(win._settings["audio_outputs"], HOME)

    def test_nothing_is_rewritten_and_nothing_announced(self):
        win, save, later = self.build()
        self.assertIsNone(self.announcement(later))
        save.assert_not_called()


class HallProfileTest(_Start):
    active = "Tournament"
    seeded = True

    def test_a_hall_profile_is_kept_and_nothing_is_announced(self):
        win, save, later = self.build()
        self.assertEqual(profiles.active_profile(win._settings), "Tournament")
        self.assertIsNone(self.announcement(later))
        save.assert_not_called()


class BuiltinAddedTest(_Start):
    """A file from before Main and Rehearsal gets both, and is saved."""
    active = "Tournament"

    def test_main_and_rehearsal_are_added_and_saved_but_nothing_is_announced(self):
        win, save, later = self.build()
        self.assertEqual(profiles.profile_names(win._settings),
                         ["Main", "Rehearsal", "Tournament"])
        self.assertEqual(profiles.active_profile(win._settings), "Tournament")
        self.assertIsNone(self.announcement(later))
        save.assert_called_once_with(win._settings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
