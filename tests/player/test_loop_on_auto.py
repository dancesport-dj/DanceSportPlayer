#!/usr/bin/env python3
"""🔁 Switching to Auto while the title repeats endlessly asks about the repeat.

Run:  py -m unittest tests.player.test_loop_on_auto -v

Marcel's list, 5.6: "If Reloop is enabled and the user switches from manual to
auto, show a warning asking whether Reloop should be disabled." With 🔁 on the
running title never ends, so Auto would never move on, and the desk would stand
there believing the round runs by itself.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_loop_auto_"))

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from player.widgets.play_mode_panel import PlayModePanel
from player.widgets.player import BigPlayerWidget
from player.window.main_play_values import PlayValuesMixin
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget


class _Desk(QWidget):
    """The real switches and the real question, on a window of one list."""

    _wire_advance_switch = PlayValuesMixin._wire_advance_switch
    _set_deck_advance = PlayValuesMixin._set_deck_advance
    _offer_loop_off = PlayValuesMixin._offer_loop_off
    _engine_list = PlayValuesMixin._engine_list
    _looping = PlayerControlMixin._looping

    def __init__(self):
        super().__init__()
        self._big_player = BigPlayerWidget(QMediaPlayer())
        self._play_panel = PlayModePanel({"auto_advance": False})
        self.table = self.list_of()
        self.other = self.list_of()
        self.vals = {id(self.table): {"advance": False},
                     id(self.other): {"advance": False}}
        self.playing = self.table
        self._wire_advance_switch()

    @staticmethod
    def list_of():
        return SimpleNamespace(refresh_advance_toggle=lambda: None)

    def _list_vals(self, table):
        return self.vals[id(table)]

    def _panel_list(self):
        return self.table

    def _playing_row(self):
        return self.playing, 0

    def _refresh_advance_toggles(self):
        """The corner switches: none here."""

    def _autosave_playlist(self):
        """Nothing to save to."""


class ReloopWarningTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk._big_player)
        self.addCleanup(reap_widget, self.desk._play_panel)
        self.addCleanup(reap_widget, self.desk)
        self.switch = self.desk._play_panel.advance_check
        self.shown = []

    def answer(self, button):
        """Press `button` in the box once it stands."""
        def press():
            box = QApplication.activeModalWidget()
            self.assertIsInstance(box, QMessageBox)
            self.shown.append(box.text())
            box.button(button).click()
        QTimer.singleShot(0, press)

    def looping(self, on=True):
        self.desk._big_player.set_loop_mode(on)

    def test_auto_with_the_repeat_on_asks(self):
        self.looping()
        self.answer(QMessageBox.StandardButton.Yes)
        self.switch.click()
        self.assertEqual(len(self.shown), 1)
        self.assertIn("🔁", self.shown[0])

    def test_yes_switches_the_repeat_off(self):
        self.looping()
        self.answer(QMessageBox.StandardButton.Yes)
        self.switch.click()
        self.assertFalse(self.desk._big_player.loop_mode())
        self.assertTrue(self.switch.isChecked())

    def test_no_keeps_the_repeat_and_auto(self):
        self.looping()
        self.answer(QMessageBox.StandardButton.No)
        self.switch.click()
        self.assertTrue(self.desk._big_player.loop_mode())
        self.assertTrue(self.switch.isChecked())

    def test_the_corner_switch_of_the_playing_list_asks_too(self):
        self.looping()
        self.answer(QMessageBox.StandardButton.Yes)
        self.desk._set_deck_advance(self.desk.table, True)
        self.assertEqual(len(self.shown), 1)
        self.assertFalse(self.desk._big_player.loop_mode())

    def test_the_corner_switch_asks_only_once(self):
        """It moves the panel's switch along, which must not ask again."""
        self.looping()
        self.answer(QMessageBox.StandardButton.No)
        self.desk._set_deck_advance(self.desk.table, True)
        self.assertIsNone(QApplication.activeModalWidget())
        self.assertEqual(len(self.shown), 1)

    def test_another_list_going_to_auto_is_left_alone(self):
        """The repeat holds the list that plays, not this one."""
        self.looping()
        self.desk._set_deck_advance(self.desk.other, True)
        self.assertEqual(self.shown, [])
        self.assertTrue(self.desk._big_player.loop_mode())

    def test_without_the_repeat_nothing_is_asked(self):
        self.switch.click()
        self.assertTrue(self.switch.isChecked())
        self.assertEqual(self.shown, [])

    def test_going_to_manual_asks_nothing(self):
        self.desk._play_panel.advance_check.setChecked(True)
        self.looping()
        self.switch.click()
        self.assertFalse(self.switch.isChecked())
        self.assertEqual(self.shown, [])

    def test_a_play_set_switching_to_auto_asks_nothing(self):
        """Only a person says "manual to auto"; a set just arrives."""
        self.looping()
        self.switch.setChecked(True)
        self.assertEqual(self.shown, [])
        self.assertTrue(self.desk._big_player.loop_mode())


if __name__ == "__main__":
    unittest.main()
