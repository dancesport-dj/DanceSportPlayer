#!/usr/bin/env python3
"""Tests for the ⚙ Mode combo — caption translated, value not.

Run:  py -m unittest tests.gui.test_mode_combo -v

"Favorites", "Theme" and "Past Competitions" are not captions that happen to
be English. They are the value: fourteen sites across main_decks, main_export
and main_generate compare against those exact strings, and an autosaved deck
carries one in data["mode"]. Translating what the combo SHOWS therefore has
to leave what the combo MEANS alone, which is what the data role is for.

Get that wrong and German mode does not mislabel a deck, it loses it: a deck
saved as "Theme" no longer matches anything on the way back in.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_mode_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner import i18n  # noqa: E402

MODES = ("Favorites", "Theme", "Past Competitions")


class ModeComboTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def panel(self, language="en"):
        i18n.set_active(language)
        i18n.install_text_hook()
        from gui.config_panel import ConfigPanel
        panel = ConfigPanel()
        self.addCleanup(panel.deleteLater)
        return panel

    def test_the_value_behind_every_entry_is_the_english_one(self):
        """What every comparison in the app is written against."""
        combo = self.panel("de").mode_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         list(MODES))

    def test_german_shows_german(self):
        combo = self.panel("de").mode_combo
        shown = [combo.itemText(i) for i in range(combo.count())]
        self.assertNotEqual(shown, list(MODES), "the captions stayed English")
        for caption in shown:
            self.assertTrue(caption.strip())

    def test_english_is_untouched(self):
        combo = self.panel("en").mode_combo
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         list(MODES))
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         list(MODES))

    def test_get_mode_answers_in_english_in_german_mode(self):
        """The one that matters: every reader compares this against a literal."""
        panel = self.panel("de")
        for i, mode in enumerate(MODES):
            panel.mode_combo.setCurrentIndex(i)
            self.assertEqual(panel.get_mode(), mode)

    def test_a_deck_saved_in_english_still_finds_its_mode(self):
        """apply_config gets what an autosave stored — always English, both
        from older files and from this run."""
        panel = self.panel("de")
        for mode in reversed(MODES):
            panel.apply_config(mode=mode)
            self.assertEqual(panel.get_mode(), mode)

    def test_the_panel_still_rearranges_itself_per_mode(self):
        """_on_mode_changed moved off currentTextChanged; if it stopped firing
        the Theme/Favorites panels would simply never toggle again."""
        panel = self.panel("de")
        panel.apply_config(mode="Favorites")
        self.assertTrue(panel._comp.isVisibleTo(panel))
        panel.apply_config(mode="Theme")
        self.assertFalse(panel._comp.isVisibleTo(panel))


if __name__ == "__main__":
    unittest.main()
