#!/usr/bin/env python3
"""🏃 The training set on the real window: pause 25 s, Paso Doble starts after 2 s.

Run:  py -m unittest tests.gui.test_training_set_window -v
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_training_"))

from PySide6.QtWidgets import QApplication

from gui import dialogs
from gui.window.main_persist import layout_settings
from tests.qt_test_support import reap_widget, stub_window_startup


class TrainingSetWindowTest(unittest.TestCase):

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

    def lights(self):
        p = self.panel
        return (p.party_btn.isChecked(), p.tournament_btn.isChecked(),
                p.training_btn.isChecked())

    def test_it_puts_the_pause_on_for_25_seconds(self):
        self.panel.pause_check.setChecked(False)
        self.win._set_training_mode(True)
        self.assertTrue(self.panel.pause_check.isChecked())
        self.assertEqual(self.panel.pause_setting_secs(), 25)
        self.assertEqual(self.lights(), (False, False, True))

    def test_the_paso_doble_waits_2_seconds(self):
        self.win._set_training_mode(True)
        self.assertEqual(self.panel.pd_start_delay(), 2)

    def test_switching_it_off_brings_the_earlier_values_back(self):
        self.panel.pause_check.setChecked(False)
        self.panel.pause_spin.setValue(10)
        self.win._set_training_mode(True)
        self.win._set_training_mode(False)
        self.assertFalse(self.panel.pause_check.isChecked())
        self.assertEqual(self.panel.pause_setting_secs(), 10)

    def test_a_hand_on_the_pause_puts_the_light_out(self):
        self.win._set_training_mode(True)
        self.panel.pause_spin.setValue(20)
        self.app.processEvents()
        self.assertEqual(self.lights(), (False, False, False))

    def test_party_is_not_lit_by_it(self):
        self.win._set_training_mode(True)
        self.assertFalse(self.win._on_play_set("party"))
        self.win._set_party_mode(True)
        self.assertEqual(self.lights(), (True, False, False))

    def test_a_party_panel_with_the_pause_ticked_by_hand_is_not_training(self):
        self.win._set_party_mode(True)
        self.panel.pause_check.setChecked(True)
        self.panel.pause_spin.setValue(25)
        self.app.processEvents()
        self.assertFalse(self.win._on_play_set("training"))
        self.assertEqual(self.lights(), (False, False, False))

    def edited(self, **training):
        old = self.win._settings
        new = dict(old, training_set=dict(old.get("training_set", {}), **training))
        self.win._settings = new
        self.win._follow_play_sets(old, new)

    def test_an_edit_of_the_training_set_moves_the_lit_panel_along(self):
        self.win._set_training_mode(True)
        self.edited(pause_secs=40, pd_delay=5)
        self.assertEqual(self.panel.pause_setting_secs(), 40)
        self.assertEqual(self.panel.pd_start_delay(), 5)
        self.app.processEvents()
        self.assertEqual(self.lights(), (False, False, True))

    def test_an_edit_leaves_a_pause_changed_by_hand_alone(self):
        self.win._set_training_mode(True)
        self.panel.pause_spin.setValue(20)
        self.edited(pause_secs=40)
        self.assertEqual(self.panel.pause_setting_secs(), 20)

    def test_an_edit_moves_a_list_lit_training_along(self):
        self.win._set_training_mode(True)
        table = self.win._panel_list()
        self.edited(secs=70)
        self.assertEqual(table._play_vals["secs"], 70)

    def test_an_edit_keeps_the_lists_own_round_paso_doble_picks(self):
        from player.window.main_play_values import ROUND_PD_OWN_KEY
        self.win._set_training_mode(True)
        table = self.win._panel_list()
        self.win._list_vals(table)[ROUND_PD_OWN_KEY] = {"Endrunde": 2}
        self.edited(pause_secs=40)
        self.assertEqual(self.win._list_vals(table).get(ROUND_PD_OWN_KEY),
                         {"Endrunde": 2})

    def test_an_edit_of_the_training_set_leaves_a_party_list_alone(self):
        self.win._set_party_mode(True)
        table = self.win._panel_list()
        self.panel.pause_check.setChecked(True)
        self.panel.pause_spin.setValue(25)
        before = table._play_vals["secs"]
        self.edited(secs=before + 30)
        self.assertEqual(table._play_vals["secs"], before)

    def test_the_single_button_cycles_the_three(self):
        p = self.panel
        seen = []
        for _ in range(4):
            p.set_toggle_btn.click()
            self.app.processEvents()
            seen.append(self.lights())
        self.assertEqual(seen, [(False, True, False), (True, False, False),
                                (False, False, True), (False, True, False)])


class TrainingSettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_dialog_holds_and_saves_the_training_set(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog({"training_set": {"pause_secs": 40}})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._set_widgets["training"]["pause"].value(), 40)
        dlg._set_widgets["training"]["pause"].setValue(30)
        vals = dlg.values()["training_set"]
        self.assertEqual(vals["pause_secs"], 30)
        self.assertEqual(vals["pd_delay"], 2)
        self.assertNotIn("pause_secs", dlg.values()["party_set"])


if __name__ == "__main__":
    unittest.main()
