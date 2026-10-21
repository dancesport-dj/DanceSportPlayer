"""📂 A double-click hands the file to the system's music player — only when
⚙ Settings → 🔊 Sound & player says so.

Run:  py -m unittest tests.gui.test_dblclick_external_setting -v

A tester on a Mac double-clicked a title and found it opened in Apple's Music
app, with nothing in ⚙ Settings to stop it. The switch now lives there and
starts OFF: a double-click while planning, in the 📚 library, the 🏆 tree or
the Similar dialog leaves the file alone. The right-click "open" entries are
an explicit request and keep working either way.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dblclick_ext_"))

from PySide6.QtWidgets import QApplication

from gui import common
from tests.qt_test_support import reap_widget, stub_window_startup


def _switch(test, on):
    """Set the module switch for one test and put the old value back after."""
    test.addCleanup(common.set_dblclick_opens_external,
                    common.dblclick_opens_external())
    common.set_dblclick_opens_external(on)


class SoundTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_starts_off(self):
        self.assertIs(self._dlg({}).values()["dblclick_external"], False)

    def test_a_stored_choice_is_shown_and_saved(self):
        dlg = self._dlg({"dblclick_external": True})
        self.assertTrue(dlg._dblclick_external_chk.isChecked())
        dlg._dblclick_external_chk.setChecked(False)
        self.assertIs(dlg.values()["dblclick_external"], False)

    def test_the_default_settings_have_it_off(self):
        from gui.dialogs import load_settings
        with mock.patch("gui.dialogs.SETTINGS.read", return_value=None):
            self.assertIs(load_settings()["dblclick_external"], False)


class LibraryBrowserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui.library_browser import LibraryBrowser
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.opened = []
        self.browser._open_external = self.opened.append
        self.browser._row_path = lambda _row: Path(r"C:\music\a.mp3")

    def test_off_leaves_the_file_alone(self):
        _switch(self, False)
        self.browser._on_double_click(0, 1)
        self.assertEqual(self.opened, [])

    def test_on_opens_it(self):
        _switch(self, True)
        self.browser._on_double_click(0, 1)
        self.assertEqual(self.opened, [Path(r"C:\music\a.mp3")])


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_dblclick_ext_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(
            cls, {"app_mode": "both", "dblclick_external": True})

    def setUp(self):
        _switch(self, False)
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_the_window_starts_as_the_setting_says(self):
        self.assertTrue(common.dblclick_opens_external())

    def test_a_saved_change_applies_at_once(self):
        from PySide6.QtWidgets import QDialog
        given = {**self.win._settings, "dblclick_external": False}

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return given

            def running_look_touched(self):
                return False

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()
        self.assertFalse(common.dblclick_opens_external())


if __name__ == "__main__":
    unittest.main()
