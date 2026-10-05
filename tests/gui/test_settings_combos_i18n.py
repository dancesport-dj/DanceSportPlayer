#!/usr/bin/env python3
"""⚙ App mode, ▶ Player position and 🔊 Audio backend — entries, not just headings.

Run:  py -m unittest tests.gui.test_settings_combos_i18n -v

All three headings above these combos were translated long ago; the entries
inside them were not, so the ⚙ tab read as a German sentence followed by an
English list. Three tuples hold those entries — APP_MODE_CHOICES,
PLAYER_LAYOUT_CHOICES and MEDIA_BACKEND_CHOICES — and each is (key, caption)
or (key, caption, blurb).

The caption half needs nothing but catalog entries: every combo already uses
`addItem(caption, key)`, which the hook patches, and every reader goes through
`currentData()`. The blurb half does not, and it is the same asymmetry
5413e9e found in the strategy combo:

    combo.setItemData(i, blurb, Qt.ItemDataRole.ToolTipRole)   ← not patched

so those two call sites have to ask for the translation themselves.

APP_MODE_CHOICES is read twice — the first-start AppModeDialog builds a radio
button and a QLabel from the same tuple. Both of those constructors ARE
patched, so that dialog comes along with the catalog entries and is pinned
here so it cannot drift away from the ⚙ combo it shares its wording with.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_combos_i18n_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.dialogs import (  # noqa: E402
    APP_MODE_CHOICES, MEDIA_BACKEND_CHOICES, PLAYER_LAYOUT_CHOICES,
    AppModeDialog, SettingsDialog,
)
from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Combos(unittest.TestCase):
    """A real ⚙ Settings dialog, built offscreen under one language."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def dlg(self, language):
        i18n.set_active(language)
        i18n.install_text_hook()
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def captions(combo):
        return [combo.itemText(i) for i in range(combo.count())]

    @staticmethod
    def keys(combo):
        return [combo.itemData(i) for i in range(combo.count())]

    @staticmethod
    def tips(combo):
        return [combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
                for i in range(combo.count())]


class AppModeComboI18nTest(_Combos):

    def combo(self, language):
        return self.dlg(language)._app_mode_combo

    def test_the_key_behind_every_entry_stays_english(self):
        """What app_mode_of and the saved settings compare against."""
        self.assertEqual(self.keys(self.combo("de")),
                         [k for k, _c, _b in APP_MODE_CHOICES])

    def test_english_is_unchanged(self):
        combo = self.combo("en")
        self.assertEqual(self.captions(combo),
                         [c for _k, c, _b in APP_MODE_CHOICES])
        self.assertEqual(self.tips(combo),
                         [b for _k, _c, b in APP_MODE_CHOICES])

    def test_german_captions(self):
        shown = self.captions(self.combo("de"))
        for caption, (_k, english, _b) in zip(shown, APP_MODE_CHOICES):
            self.assertNotEqual(caption, english,
                                f"{english!r} stayed English")
        self.assertIn("Beides", shown[0])
        self.assertIn("Nur Planer", shown[1])
        self.assertIn("Nur Player", shown[2])

    def test_german_per_item_tooltips(self):
        """setItemData is not patched — this is the half that goes silently."""
        for (key, _c, english), tip in zip(APP_MODE_CHOICES,
                                           self.tips(self.combo("de"))):
            self.assertTrue(tip, f"{key} has no tooltip at all")
            self.assertNotEqual(tip, english, f"{key} kept its English tooltip")

    def test_the_combos_own_tooltip_was_already_german(self):
        """setToolTip is patched, so this half was never broken — which is
        exactly why the entries could sit English unnoticed."""
        self.assertIn("Planer blendet nur den Abspielbereich",
                      self.combo("de").toolTip())


class PlayerLayoutComboI18nTest(_Combos):

    def combo(self, language):
        return self.dlg(language)._player_layout_combo

    def test_the_key_behind_every_entry_stays_english(self):
        self.assertEqual(self.keys(self.combo("de")),
                         [k for k, _c, _b in PLAYER_LAYOUT_CHOICES])

    def test_english_is_unchanged(self):
        combo = self.combo("en")
        self.assertEqual(self.captions(combo),
                         [c for _k, c, _b in PLAYER_LAYOUT_CHOICES])
        self.assertEqual(self.tips(combo),
                         [b for _k, _c, b in PLAYER_LAYOUT_CHOICES])

    def test_german_captions(self):
        shown = self.captions(self.combo("de"))
        for caption, (_k, english, _b) in zip(shown, PLAYER_LAYOUT_CHOICES):
            self.assertNotEqual(caption, english,
                                f"{english!r} stayed English")
        self.assertIn("Neben den Playlists", shown[0])
        self.assertIn("Über den Playlists", shown[1])

    def test_german_per_item_tooltips(self):
        for (key, _c, english), tip in zip(PLAYER_LAYOUT_CHOICES,
                                           self.tips(self.combo("de"))):
            self.assertTrue(tip, f"{key} has no tooltip at all")
            self.assertNotEqual(tip, english, f"{key} kept its English tooltip")


class MediaBackendComboI18nTest(_Combos):
    """Two entries on Windows, two others everywhere else — the whole table is
    translated, so the test does not need to know which platform it is on."""

    def combo(self, language):
        return self.dlg(language)._backend_combo

    def test_the_key_behind_every_entry_stays_english(self):
        """media_backend_of and the Qt env var both read these."""
        self.assertEqual(self.keys(self.combo("de")),
                         [k for k, _c in MEDIA_BACKEND_CHOICES])

    def test_english_is_unchanged(self):
        self.assertEqual(self.captions(self.combo("en")),
                         [c for _k, c in MEDIA_BACKEND_CHOICES])

    def test_german_captions(self):
        for caption, (_k, english) in zip(self.captions(self.combo("de")),
                                          MEDIA_BACKEND_CHOICES):
            self.assertNotEqual(caption, english,
                                f"{english!r} stayed English")

    def test_the_engine_names_themselves_are_kept(self):
        """FFmpeg and Windows Media Foundation are what the machine calls
        them; only the explanation after the dash is German."""
        joined = " ".join(self.captions(self.combo("de")))
        self.assertIn("FFmpeg", joined)
        if any(k == "windows" for k, _c in MEDIA_BACKEND_CHOICES):
            self.assertIn("Windows Media Foundation", joined)

    def test_the_combos_own_tooltip_was_already_german(self):
        """The same asymmetry as the ⚙ mode combo: hovering the widget looked
        right, opening the list did not."""
        self.assertIn("Ändere das nur, wenn der Ton Ärger macht",
                      self.combo("de").toolTip())


class TsoBandComboI18nTest(_Combos):
    """🎚 TSO pitch target — one combo per dance, four entries each.

    Only the first entry was ever a plain literal; the three fixed points are
    f-strings carrying the dance's own band edges ("Lower — T28"), and an
    f-string can never be a catalog key, so they stayed English next to a
    German first line.

    The first line was worse than English: "Middle of the round" is the
    round's own MEAN tempo pulled into the band (`tso_band_target`'s
    `min(max(mean, lo), hi)`), not the middle of anything. "Mitte der Runde"
    said the opposite, and said it again inside the blurb above — where it
    sits two lines from "auf die Mitte ihrer Takte", which really is a middle.
    """

    def combo(self, language, dance="RB"):
        return self.dlg(language)._band_combos[dance]

    def test_the_key_behind_every_entry_stays_english(self):
        """tso_band_of and tso_band_target both compare against these."""
        self.assertEqual(self.keys(self.combo("de")),
                         ["mean", "lower", "middle", "upper"])

    def test_english_is_unchanged(self):
        self.assertEqual(self.captions(self.combo("en")),
                         ["Middle of the round", "Lower — T24",
                          "Middle — T25", "Upper — T26"])

    def test_the_band_edges_speak_german(self):
        for caption in self.captions(self.combo("de"))[1:]:
            self.assertFalse(
                caption.split("—")[0].strip() in ("Lower", "Middle", "Upper"),
                f"{caption!r} stayed English")

    def test_the_takt_itself_is_kept(self):
        """The edge is the point of the entry — T24, T25, T26 for a Rumba."""
        shown = self.captions(self.combo("de"))
        self.assertIn("T24", shown[1])
        self.assertIn("T25", shown[2])
        self.assertIn("T26", shown[3])

    def test_the_round_keeps_its_mean_not_its_middle(self):
        first = self.captions(self.combo("de"))[0]
        self.assertIn("Mittelwert", first)
        self.assertNotEqual(first, "Mitte der Runde")

    def test_the_blurb_above_says_the_same_thing(self):
        """It quotes the entry in italics — the two have to agree or the
        explanation points at a line that is not there."""
        i18n.set_active("de")
        english = (
            "<b>🎚 TSO pitch target</b> — which takt the 🎚 button pitches a "
            "heat to. <i>Middle of the round</i> puts the round on one takt: "
            "the takt most of its titles are on where a step of one gets the "
            "rest there cheaply (T30+T31+T31 Cha-Chas → 31), the middle of "
            "its takte where it does not (T24+T25+T25 Rumbas → 24.5, "
            "T50+T52+T52 Quicksteps → 51). Nothing moves more than a takt. A "
            "fixed takt puts every title of that dance on the same tempo "
            "instead — worth setting on the slow dances, where one takt out "
            "of 24 is twice the pitch shift one takt out of 50 is.")
        german = i18n.t(english)
        self.assertNotEqual(german, english, "the blurb is not in the catalog")
        self.assertIn("<i>Mittelwert der Runde</i>", german)


class FirstStartDialogI18nTest(unittest.TestCase):
    """The same three modes, as the very first start asks them."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def dlg(self, language):
        i18n.set_active(language)
        i18n.install_text_hook()
        dlg = AppModeDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_radio_buttons_speak_german(self):
        dlg = self.dlg("de")
        for key, english, _blurb in APP_MODE_CHOICES:
            self.assertNotEqual(dlg._radios[key].text(), english,
                                f"{key} stayed English")

    def test_the_mode_it_returns_is_still_a_key(self):
        self.assertIn(self.dlg("de").mode(), [k for k, _c, _b in APP_MODE_CHOICES])


if __name__ == "__main__":
    unittest.main()
