#!/usr/bin/env python3
"""🔉↓ 🛑 ⏹ ✕ The fades started by hand get a time of their own.

Run:  py -m unittest tests.player.test_hand_fade -v

Item 23: the playlist's one fade-out also drove 🔉↓, the 🛑 panic fade, the
⏹ "At …" stop and the fade before quitting. ⚙ Settings ▸ Sound & player can
now give those their own seconds; 0 keeps the playlist's, as before.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_hand_fade_"))

from PySide6.QtWidgets import QApplication

from player.audio.mix import hand_fade_secs
from tests.player.audio.test_fade_indicator import _Desk
from tests.qt_test_support import reap_widget


class SettingTest(unittest.TestCase):

    def test_the_playlist_fade_unless_set(self):
        self.assertEqual(hand_fade_secs({}, 3.0), 3.0)
        self.assertEqual(hand_fade_secs({"hand_fade_secs": 0}, 3.0), 3.0)

    def test_its_own_seconds_once_set(self):
        self.assertEqual(hand_fade_secs({"hand_fade_secs": 1.5}, 3.0), 1.5)

    def test_a_broken_value_is_the_playlist_fade(self):
        self.assertEqual(hand_fade_secs({"hand_fade_secs": "soon"}, 3.0), 3.0)
        self.assertEqual(hand_fade_secs({"hand_fade_secs": None}, 3.0), 3.0)

    def test_bounded(self):
        self.assertEqual(hand_fade_secs({"hand_fade_secs": 99}, 3.0), 10.0)
        self.assertEqual(hand_fade_secs({"hand_fade_secs": -2}, 3.0), 3.0)


class DeskTest(unittest.TestCase):
    """The desk's playlist fade is 2 s (see test_fade_indicator._Panel)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desk(self, settings):
        d = _Desk()
        d._settings = dict(settings)
        self.addCleanup(reap_widget, d)
        return d

    def test_the_fade_button_takes_its_own_time(self):
        d = self.desk({"hand_fade_secs": 5.0})
        d._fade_out_now()
        self.assertEqual(d._fade_now.total, 5.0)

    def test_the_panic_fade_too(self):
        d = self.desk({"hand_fade_secs": 1.0})
        d._fade_and_hold()
        self.assertEqual(d._fade_now.total, 1.0)

    def test_unset_they_keep_the_playlist_fade(self):
        d = self.desk({})
        d._fade_out_now()
        self.assertEqual(d._fade_now.total, 2.0)

    def test_the_fade_before_quitting_too(self):
        d = self.desk({"hand_fade_secs": 4.0})
        d._cart_voices = None
        d._fade_out_to_quit()
        self.assertEqual(d._fade_now.total, 4.0)


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_playlist_fade_by_default(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._hand_fade_spin.value(), 0.0)
        self.assertEqual(dlg.values()["hand_fade_secs"], 0.0)

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"hand_fade_secs": 1.5})
        self.assertEqual(dlg._hand_fade_spin.value(), 1.5)
        dlg._hand_fade_spin.setValue(4.0)
        self.assertEqual(dlg.values()["hand_fade_secs"], 4.0)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._hand_fade_spin.toolTip(),
                     dlg._hand_fade_spin.specialValueText(),
                     dlg._hand_fade_lbl.text()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
