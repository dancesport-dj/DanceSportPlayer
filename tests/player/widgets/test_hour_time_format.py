#!/usr/bin/env python3
"""⏱ A title over an hour reads 1:04:00 on the player and the mini player.

Run:  py -m unittest tests.player.widgets.test_hour_time_format -v

The times were minutes and seconds only, so a 64-minute mix read "64:00".
⚙ Settings → 🔊 Sound & player now picks how such a title reads: hours,
minutes and seconds (the default) or minutes past 59 as before.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_hourfmt_"))

from PySide6.QtWidgets import QApplication

from player.widgets import player_parts
from player.widgets.player_parts import fmt_ms, set_time_format
from tests.qt_test_support import reap_widget, stub_window_startup

_HOUR_4 = 64 * 60 * 1000


class FormatTest(unittest.TestCase):

    def tearDown(self):
        set_time_format(None)

    def test_hours_by_default(self):
        self.assertEqual(fmt_ms(_HOUR_4), "1:04:00")
        self.assertEqual(fmt_ms(_HOUR_4 + 7_500), "1:04:07")

    def test_under_an_hour_stays_as_it_was(self):
        self.assertEqual(fmt_ms(59 * 60_000 + 59_000), "59:59")
        self.assertEqual(fmt_ms(65_000), "01:05")

    def test_minutes_past_59_when_picked(self):
        set_time_format("minutes")
        self.assertEqual(fmt_ms(_HOUR_4), "64:00")

    def test_an_unknown_value_falls_back_to_hours(self):
        set_time_format("weird")
        self.assertEqual(fmt_ms(_HOUR_4), "1:04:00")


class SettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_hours_is_the_default(self):
        self.assertEqual(self._dlg({}).values()["time_format"], "hours")

    def test_a_stored_choice_is_shown_and_saved(self):
        dlg = self._dlg({"time_format": "minutes"})
        self.assertEqual(dlg._time_format_combo.currentData(), "minutes")
        dlg._time_format_combo.setCurrentIndex(
            dlg._time_format_combo.findData("hours"))
        self.assertEqual(dlg.values()["time_format"], "hours")


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_hourfmt_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(
            cls, {"app_mode": "both", "time_format": "minutes"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.addCleanup(set_time_format, None)

    def test_the_window_starts_as_the_setting_says(self):
        self.assertEqual(player_parts._time_format, "minutes")

    def test_a_saved_change_applies_at_once(self):
        from PySide6.QtWidgets import QDialog
        given = dict(self.win._settings)

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return {**given, "time_format": "hours"}

            def running_look_touched(self):
                return False

            def deleteLater(self):
                pass

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()
        self.assertEqual(player_parts._time_format, "hours")


if __name__ == "__main__":
    unittest.main()
