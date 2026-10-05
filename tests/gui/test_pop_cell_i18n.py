#!/usr/bin/env python3
"""The Pop column's value for a track nobody has played yet.

Run:  py -m unittest tests.gui.test_pop_cell_i18n -v

A played track shows "★3" — a number, nothing to translate. A fresh one
shows a word instead, and the word stayed English in both tables that draw
it: "✦new" in a deck (gui/playlist_table.py) and a bare "new" in the 🔍
Similar-tracks dialog (gui/similar_dialog.py).

Nothing catches these on the way out: QTableWidgetItem is deliberately not
one of i18n's patched constructors (planner/i18n.py `_CTOR_CLASSES`), so a
literal in a table CELL reaches the screen exactly as written. The headers
above them are fine — `setHorizontalHeaderLabels` IS patched.

The ✦ filter that hides everything else already says "neu" in the catalog
("  ·  ✦ %d new" → "  ·  ✦ %d neu"), so the cell follows that spelling.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_popcell_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from shared.columns import _COL_POP  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

FRESH = MusicEntry(path=Path(r"C:\music\tanzcds\LW1.mp3"),
                   title="LW one", dance="LW", duration=180)
PLAYED = MusicEntry(path=Path(r"C:\music\tanzcds\LW2.mp3"),
                    title="LW two", dance="LW", duration=180, popularity=3)


class _Pop(unittest.TestCase):
    """Both tables, in whichever language the test asks for."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    @staticmethod
    def speak(language):
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked


class DeckPopCellTest(_Pop):
    """The Pop column of a deck."""

    def cells(self, language):
        self.speak(language)
        from gui.playlist_table import PlaylistTable

        win = QWidget()
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        t.load(playlist={"Vorrunde": [[FRESH], [PLAYED]]},
               dances=["LW"], rounds=[RoundConfig(name="Vorrunde", heats=2,
                                                  tier="early")],
               dance_class="S", play_cb=lambda *a: None, suggester=None)
        return [t.item(r, _COL_POP).text()
                for r in sorted(t._row_meta.song_rows())]

    def test_english_is_unchanged(self):
        self.assertEqual(self.cells("en"), ["✦new", "★3"])

    def test_the_fresh_track_says_neu(self):
        fresh, played = self.cells("de")
        self.assertNotIn("new", fresh)
        self.assertEqual(fresh, "✦neu")
        self.assertEqual(played, "★3", "a play count is a number, not a word")


class SimilarDialogPopCellTest(_Pop):
    """The Pop column of the 🔍 Similar-tracks dialog."""

    def cells(self, language):
        self.speak(language)
        from gui.similar_dialog import SimilarTracksDialog

        source = MusicEntry(path=Path(r"C:\music\tanzcds\source.mp3"),
                            title="source", dance="LW")   # never lists itself
        dlg = SimilarTracksDialog(source, [(0.9, FRESH), (0.8, PLAYED)])
        self.addCleanup(reap_widget, dlg)
        table = dlg._table
        return [table.item(r, 6).text() for r in range(table.rowCount())]

    def test_english_is_unchanged(self):
        self.assertEqual(self.cells("en"), ["new", "★3"])

    def test_the_fresh_track_says_neu(self):
        fresh, played = self.cells("de")
        self.assertNotIn("new", fresh)
        self.assertEqual(fresh, "neu")
        self.assertEqual(played, "★3", "a play count is a number, not a word")


if __name__ == "__main__":
    unittest.main(verbosity=2)
