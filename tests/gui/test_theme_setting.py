#!/usr/bin/env python3
"""The 🎨 Look tab: theme and accent, from the Settings dialog to the settings.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_theme_setting -v

Both settings are read once while the app starts, so the only thing the dialog
has to get right is the round trip — what was stored comes back into the
controls, and what the controls say goes back out of `values()` unharmed. The
rest of the settings have to ride along untouched: `_open_settings` saves the
dict as a whole.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_themeset_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared import theme  # noqa: E402
from gui.dialogs import SettingsDialog  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class LookTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_defaults_to_light_and_the_app_blue(self):
        dlg = self._dlg({})
        self.assertEqual(dlg._theme_combo.currentData(), "light")
        self.assertEqual(dlg._accent, theme.ACCENT_DEFAULT)
        vals = dlg.values()
        self.assertEqual(vals["theme"], "light")
        self.assertEqual(vals["accent_color"], theme.ACCENT_DEFAULT)

    def test_the_stored_theme_comes_back_into_the_combo(self):
        dlg = self._dlg({"theme": "dark"})
        self.assertEqual(dlg._theme_combo.currentData(), "dark")
        self.assertEqual(dlg.values()["theme"], "dark")

    def test_the_stored_accent_comes_back_and_is_normalised(self):
        dlg = self._dlg({"accent_color": "#B8006E"})
        self.assertEqual(dlg._accent, "#b8006e")
        self.assertEqual(dlg.values()["accent_color"], "#b8006e")

    def test_an_unreadable_accent_falls_back_to_the_app_blue(self):
        dlg = self._dlg({"accent_color": "rebeccapurple"})
        self.assertEqual(dlg._accent, theme.ACCENT_DEFAULT)

    def test_the_reset_button_puts_the_blue_back(self):
        dlg = self._dlg({"accent_color": "#b8006e"})
        dlg._accent_reset.click()
        self.assertEqual(dlg.values()["accent_color"], theme.ACCENT_DEFAULT)

    def test_the_swatch_shows_the_colour_that_was_picked(self):
        """Not the colour shaded for the active theme — the picked one.

        Installed hook and dark theme on purpose: without them both paths look
        alike and the test would prove nothing. The hook cannot be taken off
        again, which is harmless — light mode with the default accent, restored
        below, makes it the identity for every later test in this process."""
        from PySide6.QtWidgets import QLabel

        theme.install_stylesheet_hook()
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        self.addCleanup(theme.set_active, "light", theme.ACCENT_DEFAULT)

        ordinary = QLabel()
        self.addCleanup(reap_widget, ordinary)
        ordinary.setStyleSheet("background:#ffffff;")
        self.assertNotIn("#ffffff", ordinary.styleSheet(),
                         "the hook must shade an ordinary widget")

        dlg = self._dlg({})
        dlg._set_accent("#b8006e")
        self.assertIn("#b8006e", dlg._accent_btn.styleSheet(),
                      "the swatch must survive the hook unshaded")
        self.assertIn("#b8006e", dlg._accent_btn.text())

    def test_other_settings_ride_along(self):
        dlg = self._dlg({"theme": "dark", "wish_state": 2, "compact": 3})
        vals = dlg.values()
        self.assertEqual(vals["wish_state"], 2)
        self.assertEqual(vals["compact"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
