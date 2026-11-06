#!/usr/bin/env python3
"""One button for the 🏆 tournament / 🎉 party set, named for the one that is on.

Run:  py -m unittest tests.gui.test_single_set_button -v

The two buttons stay the model (every light and signal keeps working); the
single button is the face. It is the default, ⚙ Settings can bring the pair back.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_singleset_"))

from PySide6.QtWidgets import QApplication

from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget


class SingleSetButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, settings=None):
        p = PlayModePanel(settings or {})
        self.addCleanup(reap_widget, p)
        return p

    def test_single_is_the_default(self):
        p = self.panel()
        self.assertFalse(p.set_toggle_btn.isHidden())
        self.assertTrue(p.tournament_btn.isHidden())
        self.assertTrue(p.party_btn.isHidden())

    def test_the_setting_brings_the_pair_back(self):
        p = self.panel({"single_set_button": False})
        self.assertTrue(p.set_toggle_btn.isHidden())
        self.assertFalse(p.tournament_btn.isHidden())
        self.assertFalse(p.party_btn.isHidden())
        p.set_single_set_button(True)
        self.assertFalse(p.set_toggle_btn.isHidden())
        self.assertTrue(p.party_btn.isHidden())

    def test_it_names_the_set_that_is_on(self):
        p = self.panel()
        p.set_tournament_on(True)
        self.assertIn("Tournament", p.set_toggle_btn.text())
        p.set_party_on(True)
        self.assertIn("Party", p.set_toggle_btn.text())
        self.assertNotIn("Tournament", p.set_toggle_btn.text())

    def test_each_set_has_its_own_colour(self):
        p = self.panel()
        p.set_tournament_on(True)
        gold = p.set_toggle_btn.styleSheet()
        p.set_party_on(True)
        self.assertNotEqual(gold, p.set_toggle_btn.styleSheet())

    def test_clicked_with_none_on_it_asks_for_the_tournament_set(self):
        p = self.panel()
        got = []
        p.tournamentSetRequested.connect(lambda *_: got.append("t"))
        p.partySetToggled.connect(lambda on: got.append(("p", on)))
        p.set_toggle_btn.click()
        self.assertEqual(got, ["t"])

    def test_clicked_on_the_tournament_set_it_goes_to_party(self):
        p = self.panel()
        p.set_tournament_on(True)
        got = []
        p.partySetToggled.connect(lambda on: got.append(on))
        p.set_toggle_btn.click()
        self.assertEqual(got, [True])

    def test_clicked_on_the_party_set_it_goes_to_training(self):
        p = self.panel()
        p.set_party_on(True)
        got = []
        p.trainingSetToggled.connect(lambda on: got.append(on))
        p.set_toggle_btn.click()
        self.assertEqual(got, [True])

    def test_clicked_on_the_training_set_it_goes_to_tournament(self):
        p = self.panel()
        p.set_training_on(True)
        got = []
        p.tournamentSetRequested.connect(lambda *_: got.append("t"))
        p.set_toggle_btn.click()
        self.assertEqual(got, ["t"])


if __name__ == "__main__":
    unittest.main()
