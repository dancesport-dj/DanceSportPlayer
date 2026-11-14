#!/usr/bin/env python3
"""🎧 The audio profile in the status bar: shown while any profile exists, and a
click lists them to switch with — no trip through ⚙ Settings between the
evening's preparation and the tournament. The list always opens, since the red
⏹ Stop all music sits at its foot (tests/player/test_stop_all_sound.py); with
two profiles the other one is the default under the pointer, so a second click
on the same spot switches.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_profile_badge -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_profile_badge_"))

from PySide6.QtWidgets import QApplication, QMenu, QPushButton

from shared.audio import profiles
from tests.qt_test_support import reap_widget, stub_window_startup

HALL = {"music": {"id": "aa", "name": "PA"}}
HOME = {"music": {"id": "bb", "name": "Phones"}}


class ProfileBadgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def _badge(self):
        self.win._sync_sound_badge()
        return self.win.statusBar().findChild(QPushButton, "profileBadge")

    def _picks(self):
        """The chooser's profile entries, without the line and the ⏹ below."""
        menu = self.win._audio_profile_menu()
        self.addCleanup(menu.deleteLater)
        return menu, [a for a in menu.actions() if a.data() is not None]

    def _two_profiles(self):
        profiles.save_profile(self.win._settings, "Tournament", HALL)
        profiles.save_profile(self.win._settings, "Rehearsal", HOME, private=True)
        profiles.switch_profile(self.win._settings, "Tournament")

    def test_a_fresh_start_shows_main(self):
        """Main and Rehearsal always exist, so there is always a badge."""
        badge = self._badge()
        self.assertFalse(badge.isHidden())
        self.assertIn("Main", badge.text())

    def test_a_hall_profile_shows_its_name(self):
        self._two_profiles()
        badge = self._badge()
        self.assertFalse(badge.isHidden())
        self.assertIn("Tournament", badge.text())
        self.assertIn("🔊", badge.text())
        self.assertNotIn("🏆", badge.text())

    def test_a_rehearsal_profile_looks_different(self):
        self._two_profiles()
        profiles.switch_profile(self.win._settings, "Rehearsal")
        badge = self._badge()
        self.assertIn("Rehearsal", badge.text())
        self.assertIn("🎧", badge.text())
        self.assertNotIn("🔊", badge.text())

    def test_the_menu_uses_the_same_icons(self):
        self._two_profiles()
        texts = [a.text() for a in self._picks()[1]]
        self.assertEqual(texts, ["🔊 Main", "🎧 Rehearsal", "🔊 Tournament"])

    def test_one_badge_however_often_it_syncs(self):
        self._two_profiles()
        self._badge()
        self._badge()
        self.assertEqual(len(self.win.statusBar().findChildren(
            QPushButton, "profileBadge")), 1)

    def test_the_menu_lists_every_profile_and_ticks_the_active_one(self):
        self._two_profiles()
        actions = self._picks()[1]
        self.assertEqual([a.data() for a in actions], ["Main", "Rehearsal", "Tournament"])
        self.assertEqual([a.isChecked() for a in actions], [False, False, True])

    def test_picking_from_the_menu_switches_the_profile_and_the_badge(self):
        self._two_profiles()
        badge = self._badge()
        actions = self._picks()[1]
        with mock.patch("player.audio.audio_device.save_settings", return_value=True):
            actions[1].trigger()
        self.assertEqual(profiles.active_profile(self.win._settings), "Rehearsal")
        self.assertEqual(self.win._settings["audio_outputs"], HOME)
        self.assertIn("Rehearsal", badge.text())

    def test_a_click_opens_the_menu(self):
        self._two_profiles()
        badge = self._badge()
        with mock.patch.object(self.win, "_audio_profile_menu") as menu:
            badge.click()
        menu.return_value.exec.assert_called_once()

    def test_with_two_profiles_a_click_opens_the_chooser_on_the_other_one(self):
        """Main and Rehearsal only: the chooser still opens, for the ⏹ below
        the profiles, but with the other profile under the pointer, so a
        second click on the same spot switches as one click used to."""
        badge = self._badge()
        self.assertEqual(profiles.profile_names(self.win._settings), ["Main", "Rehearsal"])
        real, picks = self._picks()
        self.assertIs(real.defaultAction(), picks[1])
        menu = mock.Mock(spec=QMenu)
        menu.defaultAction.return_value = real.defaultAction()
        menu.exec.side_effect = lambda pos, at: at.trigger()   # the pick under the pointer
        with mock.patch.object(self.win, "_audio_profile_menu", return_value=menu),                 mock.patch("player.audio.audio_device.save_settings", return_value=True):
            badge.click()
        menu.exec.assert_called_once()
        self.assertEqual(profiles.active_profile(self.win._settings), "Rehearsal")
        self.assertIn("Rehearsal", badge.text())

    def test_with_three_profiles_no_pick_waits_under_the_pointer(self):
        self._two_profiles()
        self.assertIsNone(self._picks()[0].defaultAction())

    def test_the_tip_tells_of_the_switch_and_the_stop(self):
        badge = self._badge()
        self.assertIn("stop all music", badge.toolTip())
        self._two_profiles()
        profiles.switch_profile(self.win._settings, "Rehearsal")
        self.assertIn("stop all music", self._badge().toolTip())

    def test_the_badges_add_no_margin_on_their_right(self):
        """The status bar already keeps its own gap before the size grip; a
        margin on top of it pushed the badge visibly away from the edge."""
        self._badge()
        for name in ("profileBadge", "soundBadge"):
            sheet = self.win.statusBar().findChild(QPushButton, name).styleSheet()
            self.assertIn("margin:2px 0 2px 4px", sheet, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
