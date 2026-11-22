#!/usr/bin/env python3
"""⚙ A settings file written by main loads and saves unchanged.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_main_era_settings -v

`tests/gui/golden/main_era_settings.json` is main's own load_settings()
(669ebbe2, the per-machine paths blanked): every key main knew, at main's
defaults. Read by this branch it must keep each of them, come up with all
three equalizer tabs off and the tempo on Qt's own, and survive a round
through ⚙ Settings without losing a key main knew.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_main_era_settings_"))

from PySide6.QtWidgets import QApplication

from gui.dialogs import load_settings, tempo_engine_of
from gui.dialogs.settings_dialog import SettingsDialog
from planner.playing import equalizer as eqs
from shared.stores import SETTINGS, save_settings

MAIN_SETTINGS = json.loads(
    (Path(__file__).parent / "golden" / "main_era_settings.json").read_text("utf-8"))
# The per-machine paths: blanked in the golden file, so the path fallback
# (main's too) puts this machine's in, and lists them as offline.
_PATHS = {k for k, v in MAIN_SETTINGS.items()
          if isinstance(v, str) and v.endswith("music") and ":" in v} | {"paths_offline"}


class MainEraSettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.assertTrue(save_settings(dict(MAIN_SETTINGS), report=False))
        self.addCleanup(SETTINGS.write, {})
        self.loaded = load_settings()

    # ===== Acceptance criteria =====

    def test_every_key_main_knew_comes_back_as_main_wrote_it(self):
        for key, value in MAIN_SETTINGS.items():
            if key in _PATHS:
                continue
            with self.subTest(key=key):
                self.assertEqual(self.loaded.get(key), value)

    def test_every_equalizer_tab_is_off(self):
        for source in eqs.SOURCES:
            with self.subTest(source=source):
                self.assertFalse(eqs.eq_of(self.loaded, source)["on"])

    def test_the_tempo_is_qts_own(self):
        self.assertEqual(tempo_engine_of(self.loaded), "qt")

    def test_a_round_through_settings_keeps_every_key_main_knew(self):
        dlg = SettingsDialog(dict(self.loaded), None)
        self.addCleanup(dlg.deleteLater)
        saved = dlg.values()
        for key in MAIN_SETTINGS:
            with self.subTest(key=key):
                self.assertIn(key, saved)

    # ===== Core behavior =====

    def test_a_round_through_settings_leaves_every_eq_off(self):
        """Saving with OK must not switch an EQ on that main never had."""
        dlg = SettingsDialog(dict(self.loaded), None)
        self.addCleanup(dlg.deleteLater)
        saved = dlg.values()
        for source in eqs.SOURCES:
            with self.subTest(source=source):
                self.assertFalse(eqs.eq_of(saved, source)["on"])
        self.assertEqual(tempo_engine_of(saved), "qt")

    def test_the_round_changes_no_value_main_knew(self):
        dlg = SettingsDialog(dict(self.loaded), None)
        self.addCleanup(dlg.deleteLater)
        saved = dlg.values()
        for key in MAIN_SETTINGS:
            with self.subTest(key=key):
                self.assertEqual(saved[key], self.loaded[key])


if __name__ == "__main__":
    unittest.main()
