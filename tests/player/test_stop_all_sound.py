#!/usr/bin/env python3
"""⏹ Stop all: a click on the audio profile, one pick, and the app is silent.

Review 2026-11-12, suggestion 1, first as a red status-bar button, then for a
moment in a chooser on the output's name. Marcel then: "instead the stop all
should be reachable in audio profile ... make sure it is still shown in red".
So the profile badge always opens its chooser, and a red ⏹ Stop all music
sits at its foot. Unlike the player card's 🛑 (a fade that holds the title in
place) Stop all cuts at once: the music as ⏹ does, then every cartwall voice
with its tails, and the pre-listen.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_stop_all_sound -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_stop_all_"))

from PySide6.QtWidgets import QApplication, QPushButton, QWidgetAction

from gui.dialogs.settings_dialog import SettingsDialog
from tests.qt_test_support import reap_widget, stub_window_startup


class ProfileChooserStopAllTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        if self.win._player is None:
            self.skipTest("no QtMultimedia")

    def _stop(self):
        """The chooser's Stop all entry: the last one, a red button."""
        menu = self.win._audio_profile_menu()
        self.addCleanup(menu.deleteLater)
        last = menu.actions()[-1]
        self.assertIsInstance(last, QWidgetAction)
        return last, last.defaultWidget()

    def test_the_chooser_ends_on_stop_all_after_a_line(self):
        menu = self.win._audio_profile_menu()
        self.addCleanup(menu.deleteLater)
        actions = menu.actions()
        self.assertTrue(actions[-2].isSeparator())
        self.assertIn("Stop all music", actions[-1].defaultWidget().text())

    def test_stop_all_is_shown_in_red(self):
        _action, button = self._stop()
        self.assertIsInstance(button, QPushButton)
        self.assertIn("background:#c62828", button.styleSheet().replace(" ", ""))
        self.assertIn("color:white", button.styleSheet().replace(" ", ""))

    def test_stop_all_stops_the_music_first_then_cuts_the_wall_and_the_cue(self):
        calls = mock.Mock()
        cue = mock.Mock()
        real = self.win._cart_voices
        self.addCleanup(setattr, self.win, "_cart_voices", real)   # the close stops them
        self.win._cart_voices = calls.voices
        _action, button = self._stop()
        with mock.patch.object(self.win, "_on_stop_btn", calls.stop_btn), \
                mock.patch.object(self.win, "_cue_player", return_value=cue), \
                mock.patch.object(self.win._cartwall, "end_queue_run", calls.end_queue):
            button.click()
        names = [c[0] for c in calls.mock_calls]
        self.assertEqual(names[0], "stop_btn", "the deck first: no pause music lifts a bed after the cut")
        self.assertIn("end_queue", names)
        self.assertIn("voices.cut_all", names)
        self.assertLess(names.index("end_queue"), names.index("voices.cut_all"))
        cue.stop.assert_called_once()

    def test_the_red_button_closes_the_chooser(self):
        from PySide6.QtCore import QPoint
        action, button = self._stop()
        menu = action.parent()
        menu.popup(QPoint(0, 0))
        self.assertTrue(menu.isVisible())
        with mock.patch.object(self.win, "_stop_all_sound"):
            button.click()
        self.assertFalse(menu.isVisible())

    def test_stop_all_takes_no_focus_from_the_desk(self):
        from PySide6.QtCore import Qt
        _action, button = self._stop()
        self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.NoFocus)

    def test_without_a_player_there_is_nothing_to_stop(self):
        with mock.patch.object(self.win, "_player", None):
            menu = self.win._audio_profile_menu()
        self.addCleanup(menu.deleteLater)
        self.assertFalse(any(isinstance(a, QWidgetAction) for a in menu.actions()))

    def test_the_red_status_bar_button_is_gone(self):
        self.win._sync_sound_badge()
        self.assertIsNone(self.win.statusBar().findChild(QPushButton, "stopAllButton"))


class StopAllKeyTest(unittest.TestCase):
    """Marcel: "for stop all music we need also an emergency key shortcut".
    A desk key, so it can be bound anew in ⌨ Keys and on the 🎛 controller;
    Shift+Esc by default, the stronger brother of Esc, which fades the pads."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        if self.win._player is None:
            self.skipTest("no QtMultimedia")

    def test_it_is_a_desk_key_on_shift_esc_that_nothing_else_has(self):
        from planner.playing import controller as pctl
        self.assertIn("stop_all", pctl.KEY_ACTIONS)
        self.assertEqual(pctl.KEY_DEFAULTS["stop_all"], "Shift+Esc")
        self.assertNotIn("Shift+Esc", pctl.RESERVED_KEYS)
        others = [k for a, k in pctl.KEY_DEFAULTS.items() if a != "stop_all"]
        self.assertNotIn("Shift+Esc", others)

    def test_the_key_stops_all_sound(self):
        from PySide6.QtGui import QKeySequence
        sc = self.win._desk_keys["stop_all"]
        self.assertEqual(sc.keys(), [QKeySequence("Shift+Esc")])
        with mock.patch.object(self.win, "_stop_all_sound") as stop:
            sc.activated.emit()
        stop.assert_called_once()

    def test_the_key_works_from_the_floating_wall_too(self):
        from PySide6.QtCore import Qt
        self.assertEqual(self.win._desk_keys["stop_all"].context(),
                         Qt.ShortcutContext.ApplicationShortcut)

    def test_the_red_button_names_the_key(self):
        from planner.playing import controller as pctl
        menu = self.win._audio_profile_menu()
        self.addCleanup(menu.deleteLater)
        button = menu.actions()[-1].defaultWidget()
        self.assertIn(pctl.key_text("Shift+Esc"), button.toolTip())


class NoStopAllSwitchTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_sound_page_has_no_show_button_switch_any_more(self):
        dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertFalse(hasattr(dlg, "_stop_all_chk"))
        self.assertNotIn("stop_all_button", dlg.values())


if __name__ == "__main__":
    unittest.main(verbosity=2)
