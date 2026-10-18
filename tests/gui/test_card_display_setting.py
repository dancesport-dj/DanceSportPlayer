"""🖼 〰 Cover art and waveform on the player card, set in ⚙ Settings.

Run:  py -m unittest tests.gui.test_card_display_setting -v

Both were switches on the ▶ Playing panel, but they are set once and left
alone, not switched on the night — so they moved to ⚙ Settings →
🔊 Sound & player, beside the other player rows.
"""
import os
import tempfile
import unittest
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_carddisplay_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import reap_widget, stub_window_startup


class SoundTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_both_start_on(self):
        vals = self._dlg({}).values()
        self.assertIs(vals["show_artwork"], True)
        self.assertIs(vals["show_waveform"], True)

    def test_a_stored_choice_is_shown_and_saved(self):
        dlg = self._dlg({"show_artwork": False, "show_waveform": True})
        self.assertFalse(dlg._artwork_chk.isChecked())
        dlg._waveform_chk.setChecked(False)
        self.assertIs(dlg.values()["show_waveform"], False)


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_carddisplay_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(
            cls, {"app_mode": "both", "show_artwork": False})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_the_panel_has_neither_switch_any_more(self):
        panel = self.win._play_panel
        self.assertFalse(hasattr(panel, "artwork_check"))
        self.assertFalse(hasattr(panel, "waveform_check"))

    def test_the_card_starts_as_the_setting_says(self):
        card = self.win._big_player
        self.assertFalse(card._art_on)
        self.assertTrue(card._wave_on)

    def test_a_saved_change_reaches_the_card_at_once(self):
        self._save_settings({"show_artwork": True, "show_waveform": False})
        self.assertTrue(self.win._big_player._art_on)
        self.assertFalse(self.win._big_player._wave_on)

    def test_a_panel_save_does_not_overwrite_it(self):
        self.win._settings["show_waveform"] = False
        self.win._save_play_settings()
        self.assertIs(self.win._settings["show_waveform"], False)

    def _save_settings(self, change):
        """⚙ Settings opened, `change` made, Save pressed."""
        from PySide6.QtWidgets import QDialog
        given = dict(self.win._settings)

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return {**given, **change}

            def running_look_touched(self):
                return False

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()


if __name__ == "__main__":
    unittest.main()
