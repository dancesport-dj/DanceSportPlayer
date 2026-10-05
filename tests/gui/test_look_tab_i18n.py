#!/usr/bin/env python3
"""The 🎨 Erscheinungsbild tab: the theme entries and the colour picker.

Run:  py -m unittest tests.gui.test_look_tab_i18n -v

Three separate reasons the tab was half English, and each needs its own kind
of fix:

* THEME_CHOICES is the same shape as the three combos of 5d3221d — captions
  through the hooked `addItem`, blurbs through the unpatched `setItemData`.
* The accent button's caption is assembled: `setText(f"  {hex}  —  pick a
  colour…")`, so it matches no catalog key and never will. It takes the
  project's `i18n.t("… %s …") % value` shape.
* `QColorDialog.getColor(colour, self, "Accent colour")` is a static the hook
  does not patch — only the QMessageBox / QInputDialog statics are — so the
  picker's own window title asks for its translation at the call site.

The button's ctor caption ("  Pick a colour…") is NOT what the user sees: the
tab calls `_set_accent` immediately afterwards, which replaces it with the
assembled one. Its catalog entry has therefore never been reached. Left alone
— it is a pre-existing oddity, not something this change made.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_look_i18n_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import dialogs  # noqa: E402
from gui.dialogs import THEME_CHOICES, SettingsDialog  # noqa: E402
from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Look(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def dlg(self, language, settings=None):
        i18n.set_active(language)
        i18n.install_text_hook()
        dlg = SettingsDialog(settings or {})
        self.addCleanup(reap_widget, dlg)
        return dlg


class ThemeComboI18nTest(_Look):

    def combo(self, language):
        return self.dlg(language)._theme_combo

    def test_the_key_behind_every_entry_stays_english(self):
        """theme.theme_of and the saved settings compare against these."""
        combo = self.combo("de")
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         [k for k, _c, _b in THEME_CHOICES])

    def test_english_is_unchanged(self):
        combo = self.combo("en")
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         [c for _k, c, _b in THEME_CHOICES])
        self.assertEqual(
            [combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
             for i in range(combo.count())],
            [b for _k, _c, b in THEME_CHOICES])

    def test_german_captions(self):
        combo = self.combo("de")
        shown = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn("Hell", shown[0])
        self.assertIn("Dunkel", shown[1])

    def test_german_per_item_tooltips(self):
        """setItemData again — the half the hook cannot reach."""
        combo = self.combo("de")
        for (key, _c, english), i in zip(THEME_CHOICES, range(combo.count())):
            tip = combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
            self.assertTrue(tip, f"{key} has no tooltip at all")
            self.assertNotEqual(tip, english, f"{key} kept its English tooltip")


class AccentPickerI18nTest(_Look):

    def button(self, language, accent="#3a7bd5"):
        return self.dlg(language, {"accent_color": accent})._accent_btn

    def test_english_is_unchanged(self):
        self.assertEqual(self.button("en").text(),
                         "  #3a7bd5  —  pick a colour…")

    def test_the_button_speaks_german_and_keeps_the_colour(self):
        """The hex is data: it must survive the translation untouched."""
        self.assertEqual(self.button("de").text(),
                         "  #3a7bd5  —  Farbe wählen…")

    def test_a_different_colour_still_comes_through(self):
        self.assertIn("#ff0000", self.button("de", "#ff0000").text())

    def test_the_buttons_tooltip_was_already_german(self):
        self.assertIn("Nur die Tönungen der Akzentfarbe",
                      self.button("de").toolTip())

    def test_the_reset_button_speaks_german(self):
        self.assertEqual(self.dlg("de")._accent_reset.text(), "↺  Standardblau")


class ColourDialogTitleI18nTest(_Look):
    """QColorDialog.getColor is not a patched static — the title is passed in."""

    def title(self, language):
        seen = []

        class _Colour:
            @staticmethod
            def getColor(initial, parent, title):
                seen.append(title)
                return initial

        real = dialogs.QColorDialog
        dialogs.QColorDialog = _Colour
        self.addCleanup(setattr, dialogs, "QColorDialog", real)
        self.dlg(language)._pick_accent()
        return seen[0]

    def test_english_is_unchanged(self):
        self.assertEqual(self.title("en"), "Accent colour")

    def test_german(self):
        self.assertEqual(self.title("de"), "Akzentfarbe")


if __name__ == "__main__":
    unittest.main()
