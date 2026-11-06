#!/usr/bin/env python3
"""🥇 The celebration switch on the main GUI: a value of the list on the panel,
like the others — on, every title of the list plays on after the play length.
Greyed out while the length is "full".

Run:  py -m unittest tests.gui.test_celebrate_switch -v
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_celebrate_sw_"))

from PySide6.QtWidgets import QApplication

from gui import dialogs
from gui.window.main_persist import layout_settings
from tests.qt_test_support import reap_widget, stub_window_startup


class CelebrateSwitchTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        layout_settings().clear()
        dialogs.AUTOSAVE.remove()
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.panel = self.win._play_panel

    def test_it_starts_off(self):
        self.assertFalse(self.panel.celebrate_btn.isChecked())

    def test_showing_the_state_does_not_emit(self):
        got = []
        self.panel.celebrateToggled.connect(got.append)
        self.panel.set_celebrate(True)
        self.assertTrue(self.panel.celebrate_btn.isChecked())
        self.assertEqual(got, [])

    def test_a_click_is_stored_in_the_list_on_the_panel(self):
        t = self.win._panel_list()
        self.panel.celebrate_btn.click()
        self.assertTrue(self.win._list_vals(t)["celebrate"])
        self.panel.celebrate_btn.click()
        self.assertFalse(self.win._list_vals(t)["celebrate"])

    def test_a_list_saved_without_it_is_untouched(self):
        t = self.win._panel_list()
        t._play_vals = {"secs": 90}
        self.assertIsNone(self.win._list_vals(t)["celebrate"])

    def test_it_is_hidden_with_a_full_length(self):
        self.panel._secs = 0
        self.panel._refresh_len_lbl()
        self.assertTrue(self.panel.celebrate_btn.isHidden())
        self.panel._secs = 90
        self.panel._refresh_len_lbl()
        self.assertFalse(self.panel.celebrate_btn.isHidden())

    def test_the_tooltip_says_it_needs_a_length(self):
        tip = self.panel.celebrate_btn.toolTip()
        self.assertIn("Works only with a play length set", tip)
        self.assertNotIn("finals only", tip)

    def test_it_is_a_slider_switch_like_equalize_volume(self):
        from player.widgets.panel_parts import Toggle
        self.assertIsInstance(self.panel.celebrate_btn, Toggle)
        self.assertIsInstance(self.panel.loudness_check, Toggle)

    def test_it_carries_a_visible_caption(self):
        self.assertIn("Celebration", self.panel.celebrate_btn.text())

    def test_the_single_set_button_names_all_three_sets_when_none_is_on(self):
        self.assertIn("🏃", self.panel.set_toggle_btn.text())
        self.assertIn("🏆", self.panel.set_toggle_btn.text())
        self.assertIn("🎉", self.panel.set_toggle_btn.text())

    def test_its_text_is_translated(self):
        from planner.i18n import lang_de, lang_es, lang_nl, lang_ru
        self.panel._secs = 0
        self.panel._refresh_len_lbl()
        for cat in (lang_de, lang_es, lang_nl, lang_ru):
            for key in (
                    self.panel.celebrate_btn.text(),
                    "Every title of this list plays on after the play length: the\n"
                    "music comes back up while the couples celebrate.\n"
                    "Works only with a play length set, not with 'full'.",):
                with self.subTest(lang=cat.__name__):
                    self.assertIn(key, cat.CATALOG)


if __name__ == "__main__":
    unittest.main()
