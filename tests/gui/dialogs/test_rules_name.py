#!/usr/bin/env python3
"""🎚 TSO is the German rule book: other screens name the WDSF CR instead.

Run:  py -m unittest tests.gui.dialogs.test_rules_name -v

'in german language keep term TSO, for english and other languages when not
the keep german checkbox selected (under language) rename to WDSF CR (WDSF
Competition Rules) and in Player to CR.' The switch is the same one the dance
and round names follow (planner.terms.english), and the word is swapped after
the catalog has spoken, so the catalog keys keep their TSO.

'in settings move under play sets the tso part up directly below tournament
section' — the 🎚 pitch-target block sits between 🏆 and 🎉.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rules_name_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel

from gui.dialogs.settings_dialog import SettingsDialog
from planner import i18n, terms
from player.widgets.player import BigPlayerWidget
from tests.qt_test_support import reap_widget


class _Screen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.addCleanup(i18n.set_active, i18n.active_language())
        self.addCleanup(i18n._restore_text_hook)
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)

    def screen(self, language, german_terms=False):
        i18n.set_active(language)
        i18n.install_text_hook()
        terms.apply_settings({"german_dance_terms": german_terms})

    def settings(self):
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        return dlg

    def card(self):
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        return card

    @staticmethod
    def tso_check(dlg):
        return next(c for c in dlg.findChildren(QCheckBox)
                    if c.text().startswith("🎚"))

    @staticmethod
    def band_label(dlg):
        return next(lbl for lbl in dlg.findChildren(QLabel)
                    if lbl.text().startswith("<b>🎚"))


class RulesNameTest(_Screen):

    def test_english_names_the_wdsf_rules(self):
        self.screen("en")
        self.assertEqual(terms.rules_name("the TSO range"), "the WDSF CR range")
        self.assertEqual(terms.rules_name("TSO", short=True), "CR")

    def test_the_german_terms_keep_tso(self):
        self.screen("en", german_terms=True)
        self.assertEqual(terms.rules_name("the TSO range"), "the TSO range")
        self.assertEqual(terms.rules_name("TSO", short=True), "TSO")

    def test_a_german_screen_keeps_tso(self):
        self.screen("de")
        self.assertEqual(terms.rules_name("TSO-Bereich"), "TSO-Bereich")

    def test_another_language_names_the_wdsf_rules_too(self):
        self.screen("es")
        self.assertEqual(terms.rules_name("rango TSO"), "rango WDSF CR")


class SettingsTest(_Screen):

    def test_english_settings_say_wdsf_cr(self):
        self.screen("en")
        dlg = self.settings()
        self.assertEqual(self.tso_check(dlg).text(),
                         "🎚  WDSF CR pitch to the heat tempo")
        self.assertIn("WDSF CR range", self.tso_check(dlg).toolTip())
        self.assertTrue(self.band_label(dlg).text().startswith(
            "<b>🎚 WDSF CR pitch target</b>"))
        self.assertNotIn("TSO", self.band_label(dlg).text())

    def test_german_settings_keep_tso(self):
        self.screen("de")
        dlg = self.settings()
        self.assertIn("TSO", self.tso_check(dlg).text())
        self.assertIn("TSO", self.band_label(dlg).text())
        self.assertNotIn("WDSF", self.band_label(dlg).text())

    def test_spanish_settings_say_wdsf_cr(self):
        self.screen("es")
        dlg = self.settings()
        self.assertIn("WDSF CR", self.tso_check(dlg).text())
        self.assertNotIn("TSO", self.band_label(dlg).text())

    def test_the_pitch_target_sits_right_under_the_tournament_set(self):
        self.screen("en")
        dlg = self.settings()
        label = self.band_label(dlg)
        lyt = label.parentWidget().layout()
        order = [lyt.itemAt(i).widget() for i in range(lyt.count())]
        boxes = [w for w in order if isinstance(w, QGroupBox)]
        tournament, party = boxes[0], boxes[1]
        self.assertIn("Tournament", tournament.title())
        self.assertIn("Party", party.title())
        self.assertLess(order.index(tournament), order.index(label))
        self.assertLess(order.index(label), order.index(party))


class PlayerCardTest(_Screen):

    def test_english_card_says_cr(self):
        self.screen("en")
        card = self.card()
        self.assertEqual(card._tso_btn.text(), "CR")
        self.assertIn("CR range", card._tso_btn.toolTip())
        self.assertNotIn("TSO", card._tso_btn.toolTip())
        self.assertNotIn("TSO", card._tempo_pin.toolTip())

    def test_the_german_terms_keep_tso_on_the_card(self):
        self.screen("en", german_terms=True)
        self.assertEqual(self.card()._tso_btn.text(), "TSO")

    def test_a_german_card_keeps_tso(self):
        self.screen("de")
        self.assertEqual(self.card()._tso_btn.text(), "TSO")


if __name__ == "__main__":
    unittest.main()
