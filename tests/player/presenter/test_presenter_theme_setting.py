"""🎨 The presenter screen's palette is picked in ⚙ Settings → 🎨 Look.

Run:  py -m unittest tests.player.presenter.test_presenter_theme_setting -v

It sat as a combo on the ▶ Playing panel, but it is set once per venue, not
switched on the night. Marcel: "move presenter theme in theme settings tab and
the timetable button a row up where presenter and monitor button is".
"""
import os
import tempfile
import unittest
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_presthemeset_"))

from PySide6.QtWidgets import QApplication

from shared.appearance.presenter_theme import theme_choices, theme_for
from tests.qt_test_support import reap_widget, stub_window_startup


class LookTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_every_theme_is_offered_and_the_stored_one_picked(self):
        combo = self._dlg({"presenter_theme": "light"})._presenter_theme_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         [key for key, _label in theme_choices()])
        self.assertEqual(combo.currentData(), "light")

    def test_nothing_stored_is_the_default(self):
        self.assertEqual(self._dlg({}).values()["presenter_theme"], "default")

    def test_the_pick_is_saved(self):
        dlg = self._dlg({})
        combo = dlg._presenter_theme_combo
        combo.setCurrentIndex(combo.findData("light"))
        self.assertEqual(dlg.values()["presenter_theme"], "light")


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_presthemeset_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.panel = self.win._play_panel

    def test_the_panel_has_no_theme_combo_any_more(self):
        self.assertFalse(hasattr(self.panel, "presenter_theme_combo"))

    def test_the_timetable_sits_beside_presenter_and_monitor(self):
        row = self.panel.presenter_btn.parentWidget()
        self.assertIs(self.panel.presenter_screen_combo.parentWidget(), row)
        self.assertIs(self.panel.timetable_btn.parentWidget(), row)

    def test_the_presenter_opens_in_the_stored_theme(self):
        self.win._settings["presenter_theme"] = "light"
        with mock.patch("player.presenter.presenter.PresenterWindow.show_on_screen"):
            self.win._toggle_presenter(True)
        self.addCleanup(self.win._toggle_presenter, False)
        self.assertIs(self.win._presenter._theme, theme_for("light"))

    def test_a_settings_pick_repaints_an_open_presenter(self):
        with mock.patch("player.presenter.presenter.PresenterWindow.show_on_screen"):
            self.win._toggle_presenter(True)
        self.addCleanup(self.win._toggle_presenter, False)
        self._save_settings({"presenter_theme": "light"})
        self.assertIs(self.win._presenter._theme, theme_for("light"))
        self.assertEqual(self.win._settings["presenter_theme"], "light")

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
