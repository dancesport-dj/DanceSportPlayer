#!/usr/bin/env python3
"""🐂 The Paso Doble values of the 🏆 tournament and 🎉 party sets,
configurable.

Run:  py -m unittest tests.gui.test_tournament_pd -v

Marcel: "i miss the setting for play set for the user to change the option
for paso doble stop at highlight and start after make them configurable" —
for a tournament the stop is off, "because it can be buggy", after the 2nd
highlight once switched on, "but start at 0sec is fine". ⚙ Settings → 🎛 Play
sets carries the three, and 🏆 applies them.

The 🎉 party set got the same row: "there we normally only want playing paso
till second highlight and wait 3 seconds before starting".
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tournament_pd_"))

from PySide6.QtWidgets import QApplication

from planner.playing.play_sets import pd_of
from player.widgets.play_mode_panel import PlayModePanel
from tests.player.audio.test_party_set import _Desk
from tests.qt_test_support import reap_widget


class PdOfTest(unittest.TestCase):

    def test_nothing_stored_is_no_stop_after_the_2nd_and_no_wait(self):
        self.assertEqual(pd_of({}), {"pd_stop": False, "pd_n": 2, "pd_delay": 0})

    def test_the_stored_values_are_read(self):
        got = pd_of({"tournament_set": {"pd_stop": True, "pd_n": 3, "pd_delay": 5}})
        self.assertEqual(got, {"pd_stop": True, "pd_n": 3, "pd_delay": 5})

    def test_values_out_of_range_are_pulled_in(self):
        got = pd_of({"tournament_set": {"pd_n": 9, "pd_delay": -4}})
        self.assertEqual((got["pd_n"], got["pd_delay"]), (3, 0))

    def test_a_hand_edited_value_that_is_no_number_falls_back(self):
        got = pd_of({"tournament_set": {"pd_n": "two", "pd_delay": None}})
        self.assertEqual((got["pd_n"], got["pd_delay"]), (2, 0))

    def test_a_party_stops_after_the_2nd_and_waits_3_s(self):
        self.assertEqual(pd_of({}, "party"),
                         {"pd_stop": True, "pd_n": 2, "pd_delay": 3})

    def test_each_set_reads_its_own(self):
        settings = {"tournament_set": {"pd_delay": 7},
                    "party_set": {"pd_stop": False, "pd_delay": 5}}
        self.assertEqual(pd_of(settings, "party"),
                         {"pd_stop": False, "pd_n": 2, "pd_delay": 5})
        self.assertEqual(pd_of(settings)["pd_delay"], 7)


class TournamentButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)
        self.panel = PlayModePanel({"pd_highlight_stop": False, "pd_highlight_n": 2,
                                    "pd_start_delay": 3})
        self.addCleanup(reap_widget, self.panel)
        self.desk._play_panel = self.panel

    def test_it_applies_the_configured_paso_doble_values(self):
        self.desk._settings["tournament_set"] = {"pd_stop": True, "pd_n": 3,
                                                 "pd_delay": 6}
        self.desk._apply_tournament_set()
        self.assertTrue(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_highlight_n(), 3)
        self.assertEqual(self.panel.pd_start_delay(), 6)

    def test_by_default_it_stops_nothing_and_waits_for_nothing(self):
        self.panel.set_pd_highlight_stop(True)
        self.panel.pd_spin.setValue(3)
        self.desk._apply_tournament_set()
        self.assertFalse(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_highlight_n(), 2)
        self.assertEqual(self.panel.pd_start_delay(), 0)

    def test_the_party_button_applies_the_party_values(self):
        self.desk._set_party_mode(True)
        self.assertTrue(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_highlight_n(), 2)
        self.assertEqual(self.panel.pd_start_delay(), 3)

    def test_the_party_button_applies_the_configured_party_values(self):
        self.desk._settings["party_set"] = {"pd_stop": False, "pd_n": 3,
                                            "pd_delay": 9}
        self.desk._set_party_mode(True)
        self.assertFalse(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_highlight_n(), 3)
        self.assertEqual(self.panel.pd_start_delay(), 9)

    def test_switching_the_party_off_brings_the_earlier_values_back(self):
        self.panel.pd_delay_spin.setValue(5)
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertFalse(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_start_delay(), 5)

    def test_it_says_which_highlight_it_set(self):
        self.assertTrue([s for s in self.panel.set_pd_highlight_n(3)
                         if "Paso Doble" in s])
        self.assertEqual(self.panel.set_pd_highlight_n(3), [],
                         "already the 3rd — nothing to report")


class SettingsTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_tournament_box_shows_the_paso_doble_values(self):
        dlg = self._dlg({"tournament_set": {"pd_stop": True, "pd_n": 3,
                                            "pd_delay": 4}})
        stop, n, delay = dlg._set_widgets["tournament"]["pd"]
        self.assertTrue(stop.isChecked())
        self.assertEqual((n.value(), delay.value()), (3, 4))

    def test_a_fresh_install_shows_the_defaults(self):
        stop, n, delay = self._dlg({})._set_widgets["tournament"]["pd"]
        self.assertFalse(stop.isChecked())
        self.assertEqual((n.value(), delay.value()), (2, 0))

    def test_they_are_saved_with_the_set(self):
        dlg = self._dlg({})
        stop, n, delay = dlg._set_widgets["tournament"]["pd"]
        stop.setChecked(True)
        n.setValue(1)
        delay.setValue(8)
        saved = dlg.values()["tournament_set"]
        self.assertEqual((saved["pd_stop"], saved["pd_n"], saved["pd_delay"]),
                         (True, 1, 8))

    def test_the_party_box_shows_its_own_defaults(self):
        stop, n, delay = self._dlg({})._set_widgets["party"]["pd"]
        self.assertTrue(stop.isChecked())
        self.assertEqual((n.value(), delay.value()), (2, 3))

    def test_the_party_values_are_saved_with_the_party_set(self):
        dlg = self._dlg({})
        stop, n, delay = dlg._set_widgets["party"]["pd"]
        stop.setChecked(False)
        delay.setValue(5)
        saved = dlg.values()["party_set"]
        self.assertEqual((saved["pd_stop"], saved["pd_n"], saved["pd_delay"]),
                         (False, 2, 5))
        self.assertEqual(dlg.values()["tournament_set"]["pd_delay"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
