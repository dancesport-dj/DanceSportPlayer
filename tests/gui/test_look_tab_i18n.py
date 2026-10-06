#!/usr/bin/env python3
"""The 🎨 Erscheinungsbild tab: the theme entries and the colour picker.

Run:  py -m unittest tests.gui.test_look_tab_i18n -v

Three separate reasons the tab was half English, and each needs its own kind
of fix:

* The theme list is a QListWidget, and QListWidgetItem is not among the
  hooked setters — every caption, section header and blurb asks `i18n.t`
  itself, the classic pair (THEME_CHOICES) and the 🎨 looks alike.
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
from shared import looks  # noqa: E402
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


class ThemeListI18nTest(_Look):

    def rows(self, language):
        """(key or None for a section header, shown text) per list row."""
        lst = self.dlg(language)._theme_list
        return [(lst.item(i).data(Qt.ItemDataRole.UserRole), lst.item(i).text().strip())
                for i in range(lst.count())]

    def test_the_key_behind_every_entry_stays_english(self):
        """theme.theme_of and the saved settings compare against these."""
        keys = [k for k, _text in self.rows("de") if k is not None]
        self.assertEqual(keys, [k for k, _c, _b in THEME_CHOICES] + list(looks.LOOKS))

    def test_english_is_unchanged(self):
        shown = dict((k, text) for k, text in self.rows("en") if k is not None)
        for key, caption, _b in THEME_CHOICES:
            self.assertEqual(shown[key], caption.strip())
        for look in looks.LOOKS.values():
            self.assertEqual(shown[look.key], look.caption)

    def test_german_captions_and_sections(self):
        rows = self.rows("de")
        shown = dict((k, text) for k, text in rows if k is not None)
        self.assertIn("Hell", shown["light"])
        self.assertIn("Dunkel", shown["dark"])
        self.assertEqual(shown["contrast_dark"], "Hoher Kontrast · Dunkel")
        lst = self.dlg("de")._theme_list
        heads = [lst.item(i).text() for i in range(lst.count())
                 if lst.item(i).font().bold()]
        self.assertEqual(heads, ["Standard", "Plattform-Looks", "Pult-Looks",
                                 "Modern Looks", "Eigene Looks"])

    def test_with_no_own_look_yet_the_section_says_how_to_make_one(self):
        last = self.rows("de")[-1]
        self.assertEqual(last, (None, "noch keine — ＋ Neuer Look…"))

    def test_german_blurbs(self):
        dlg = self.dlg("de")
        for key, _c, english in THEME_CHOICES:
            self.assertNotEqual(dlg._theme_blurbs[key], english, key)
        for look in looks.LOOKS.values():
            self.assertNotEqual(dlg._theme_blurbs[look.key], look.blurb, look.key)

    def test_the_accent_note_speaks_german(self):
        self.assertIn("eigene Akzentfarbe", self.dlg("de")._accent_note.text())


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
