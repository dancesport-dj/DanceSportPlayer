#!/usr/bin/env python3
"""An English screen names the dances and rounds in English.

Run:  py -m unittest tests.gui.test_english_dance_terms -v

The strips over a party list read "Standardrunde 1", a running order read
"Vorrunde … Finale" and every Dance column "Langsamer Walzer", whatever the
language: they are the data's own German words. In English they are now
translated on screen; ⚙ Settings ▸ 🎨 Look keeps the German words on request.
The list itself, and every file written from it, stays German.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_terms_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared.columns import _COL_DANCE  # noqa: E402
from planner import i18n, terms  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_STD = ("LW", "TG", "WW", "SF", "QS")


class EnglishDanceTermsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_terms_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_terms_m3u_"))

    def setUp(self):
        self.addCleanup(i18n.set_active, i18n.active_language())
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)
        i18n.set_active("en")
        terms.apply_settings({})
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._lib = self.lib
        self.table = self.win._warmup_table

    def _m3u(self, name, dances):
        paths = []
        for i, d in enumerate(dances):
            p = self.dir / f"{name}_{i:03d}_{d}.mp3"
            self.lib.entries.append(
                MusicEntry(path=p, title=f"{d} {i}", dance=d, duration=180))
            paths.append(str(p))
        f = self.dir / f"{name}.m3u"
        f.write_text("#EXTM3U\n" + "\n".join(paths), encoding="utf-8")
        return str(f)

    def strips(self):
        out = []
        for r in range(self.table.rowCount()):
            if self.table._row_meta[r] is None:
                it = self.table.item(r, 0) or self.table.item(r, 3)
                text = (it.text() if it else "").strip(" ▼▶─")
                out.append(text.split("   (")[0].strip())
        return out

    def dance_cells(self):
        return [self.table.item(r, _COL_DANCE).text()
                for r in range(self.table.rowCount())
                if self.table._row_meta[r] is not None]

    def test_a_party_list_has_english_rounds_and_dances(self):
        self.win._load_warmup_from_m3u(self.table, self._m3u("eintanzen", _STD * 8))
        self.assertEqual(self.strips(),
                         [f"Standard round {n}" for n in range(1, 9)])
        self.assertEqual(self.dance_cells()[:5],
                         ["Slow Waltz", "Tango", "Viennese Waltz",
                          "Slowfox", "Quickstep"])

    def test_a_running_order_has_english_rounds(self):
        self.win._load_warmup_from_m3u(self.table, self._m3u("HGR_D", _STD * 3))
        self.assertEqual(self.strips(),
                         ["Round 1", "Round 2", "Final"])

    def test_the_list_itself_keeps_its_german_sections(self):
        """Only the screen is translated: the rounds the panel stores and
        writes back are the data's own words."""
        self.win._load_warmup_from_m3u(self.table, self._m3u("eintanzen2", _STD * 8))
        sections = [s for s, _songs in self.table._warmup_sections(
            [m.entry for m in self.table._row_meta if m])]
        self.assertEqual(sections, [f"Standardrunde {n}" for n in range(1, 9)])

    def test_argentine_tango_by_its_genre_reads_english(self):
        """A social track carries no dance code: its "Tango Argentino" is the
        genre label, and that came through German."""
        p = self.dir / "ta_genre.mp3"
        self.lib.entries.append(MusicEntry(path=p, title="Por una cabeza",
                                           other_genre="Tango Argentino",
                                           duration=180))
        f = self.dir / "party_ta.m3u"
        f.write_text(f"#EXTM3U\n{p}", encoding="utf-8")
        self.win._load_warmup_from_m3u(self.table, str(f))
        self.assertEqual(self.dance_cells(), ["Argentine Tango"])

    def test_the_setting_keeps_the_german_words(self):
        terms.apply_settings({"german_dance_terms": True})
        self.win._load_warmup_from_m3u(self.table, self._m3u("eintanzen3", _STD * 8))
        self.assertEqual(self.strips()[:2], ["Standardrunde 1", "Standardrunde 2"])
        self.assertEqual(self.dance_cells()[0], "Langsamer Walzer")


class SettingsCheckboxTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_is_off_by_default_and_saved_when_ticked(self):
        dlg = self._dialog({})
        self.assertFalse(dlg._german_terms_chk.isChecked())
        self.assertFalse(dlg.values()["german_dance_terms"])
        dlg._german_terms_chk.setChecked(True)
        self.assertTrue(dlg.values()["german_dance_terms"])

    def test_a_saved_choice_is_shown(self):
        dlg = self._dialog({"german_dance_terms": True})
        self.assertTrue(dlg._german_terms_chk.isChecked())


if __name__ == "__main__":
    unittest.main(verbosity=2)
