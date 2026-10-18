#!/usr/bin/env python3
"""🔊 A small indicator in the status bar while the sound card chosen for
the music is plugged in, so the desk sees at a glance that the MAYA44USB is
there to play on. Plain, not a green pill like the 🎛 nanoKONTROL2 one.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_sound_badge -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sound_badge_"))

from PySide6.QtWidgets import QApplication, QPushButton

from tests.qt_test_support import reap_widget, stub_window_startup

_MAYA = "MAYA44USB Ch12 (3- ESI Audio Device (WDM) - MAYA44USB)"


class SoundBadgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def _show(self, card):
        with mock.patch.object(self.win._audio_device, "music_card",
                               return_value=card):
            self.win._sync_sound_badge()
        return self.win.statusBar().findChild(QPushButton, "soundBadge")

    def test_a_plugged_in_card_shows_its_badge(self):
        badge = self._show(_MAYA)
        self.assertFalse(badge.isHidden())
        self.assertIn("🔊", badge.text())
        self.assertIn("MAYA44USB", badge.text())
        self.assertTrue(self.win.statusBar().isAncestorOf(badge))

    def test_it_is_a_small_indicator_not_a_green_pill(self):
        """Marcel: "for the soundcard maybe no green badge but a grey or no
        background color so it is only a small indicator"."""
        style = self._show(_MAYA).styleSheet().replace(" ", "")
        self.assertIn("background:transparent", style)
        self.assertNotIn("#2e7d32", style)
        self.assertNotIn("color:", style.replace("background-color", ""))   # the look's text colour
        self.assertNotIn("bold", style)

    def test_it_leaves_the_windows_instance_number_out(self):
        self.assertNotIn("3-", self._show(_MAYA).text())

    def test_it_goes_when_the_card_does(self):
        self._show(_MAYA)
        self.assertTrue(self._show(None).isHidden())

    def test_one_badge_however_often_it_syncs(self):
        self._show(_MAYA)
        self._show(_MAYA)
        self.assertEqual(len(self.win.statusBar().findChildren(
            QPushButton, "soundBadge")), 1)

    def test_a_click_opens_the_sound_settings(self):
        badge = self._show(_MAYA)
        with mock.patch.object(self.win, "_open_settings") as opened:
            badge.click()
        opened.assert_called_once_with(open_sound=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
