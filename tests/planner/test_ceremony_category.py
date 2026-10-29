#!/usr/bin/env python3
"""🏅 Background: entrance & awards — the library category for Einmarsch and
Siegerehrung music (item 29).

Run:  .venv/Scripts/python.exe -m unittest tests.planner.test_ceremony_category -v

Marcel: "New library category "Background". Shows only entrance (Einmarsch)
and award ceremony (Siegerehrung) music. Based on tag and/or file path,
configurable under Paths in the settings." A word from ⚙ Settings → 📁 Paths
in the file or folder name, the title or the comment tag, or a folder named
there, puts the title in the category.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ceremony_"))

from PySide6.QtWidgets import QApplication

import planner.models as models
from gui.dialogs.settings_dialog import SettingsDialog
from planner.models import (
    CEREMONY_WORDS,
    MusicEntry,
    ceremony_words_of,
    is_non_turnier,
    library_category,
    set_ceremony_match,
)
from tests.qt_test_support import reap_widget

_LIB = Path("F:/my music/tanzcds")


def _entry(*parts, **tags):
    return MusicEntry(path=_LIB.joinpath(*parts), title=Path(parts[-1]).stem, **tags)


class _Case(unittest.TestCase):

    def setUp(self):
        self.addCleanup(set_ceremony_match, CEREMONY_WORDS, ())


class WordTest(_Case):

    def test_the_real_library_names_are_found(self):
        for parts in (("special", "John Miles - Music Einmarsch.mp3"),
                      ("special", "Musikbett", "fame_einmarsch_hohequali.mp3"),
                      ("special", "20-Udo Jürgens_ Musik war meine erste Liebe "
                                  "( Background Award).mp3"),
                      ("special", "Hans Zimmer - Chevaliers De Sangreal "
                                  "(Background for ceremony).mp3")):
            self.assertEqual(library_category(_entry(*parts)), "ceremony", parts[-1])

    def test_it_wins_over_the_background_folder(self):
        # special/ and Musikbett/ are 🎶 Background / non-dance otherwise.
        self.assertEqual(library_category(_entry("special", "Horn.mp3")), "background")
        self.assertEqual(library_category(
            _entry("special", "Musikbett", "Helele (Einmarsch Latein).mp3")), "ceremony")

    def test_a_folder_name_counts(self):
        self.assertEqual(library_category(
            _entry("Siegerehrung", "Simply the Best.mp3")), "ceremony")

    def test_the_title_and_comment_tags_count(self):
        self.assertEqual(library_category(
            _entry("special", "01.mp3", tag_title="Einmarsch der Paare")), "ceremony")
        self.assertEqual(library_category(
            _entry("special", "02.mp3", tag_comment="siegerehrung")), "ceremony")

    def test_a_tournament_track_stays_one(self):
        e = _entry("lateincd", "Samba", "002 SA Cinema Italiano T51.mp3", dance="SA")
        self.assertEqual(library_category(e), "")
        self.assertFalse(is_non_turnier(e))

    def test_it_stays_out_of_generation(self):
        self.assertTrue(is_non_turnier(_entry("special", "Music Einmarsch.mp3")))

    def test_an_explicit_category_marker_still_wins(self):
        e = _entry("special", "Einmarsch copy.mp3", comment_tags=["doppelte"])
        self.assertEqual(library_category(e), "duplicates")

    def test_own_words_replace_the_built_in_ones(self):
        set_ceremony_match(["Fanfare", " "], ())
        self.assertEqual(library_category(_entry("special", "MGM Fanfare.mp3")), "ceremony")
        self.assertEqual(library_category(_entry("special", "Music Einmarsch.mp3")),
                         "background")

    def test_no_words_no_match(self):
        set_ceremony_match([], ())
        self.assertEqual(library_category(_entry("Einmarsch", "a.mp3")), "")


class FolderTest(_Case):

    def test_everything_below_a_named_folder(self):
        set_ceremony_match([], [str(_LIB / "Party" / "Ehrung")])
        self.assertEqual(library_category(
            _entry("Party", "Ehrung", "x", "We are the Champions.mp3")), "ceremony")
        self.assertEqual(library_category(
            _entry("Party", "Ehrung 2", "We are the Champions.mp3")), "")


class SettingsWordsTest(unittest.TestCase):

    def test_never_saved_means_the_built_in_words(self):
        self.assertEqual(ceremony_words_of({}), list(CEREMONY_WORDS))

    def test_an_empty_list_stays_empty(self):
        self.assertEqual(ceremony_words_of({"ceremony_words": []}), [])

    def test_the_category_is_offered(self):
        self.assertIn("ceremony", models.LIBRARY_CATEGORIES)


class SettingsDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_built_in_words_are_shown_and_saved(self):
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        vals = dlg.values()
        self.assertEqual(vals["ceremony_words"], list(CEREMONY_WORDS))
        self.assertEqual(vals["ceremony_folders"], [])

    def test_words_and_folders_round_trip(self):
        dlg = SettingsDialog({"ceremony_words": ["Einmarsch"],
                              "ceremony_folders": ["F:\\m\\Ehrung"]})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._ceremony_words_edit.text(), "Einmarsch")
        dlg._ceremony_words_edit.setText(" Einmarsch ,, Fanfare,")
        dlg._ceremony_edit.setPlainText("F:\\m\\Ehrung\n\nF:\\m\\Award")
        vals = dlg.values()
        self.assertEqual(vals["ceremony_words"], ["Einmarsch", "Fanfare"])
        self.assertEqual(vals["ceremony_folders"], ["F:\\m\\Ehrung", "F:\\m\\Award"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
