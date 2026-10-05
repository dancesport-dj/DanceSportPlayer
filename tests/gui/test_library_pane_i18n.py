#!/usr/bin/env python3
"""📚 The library pane, opened in a German app.

Run:  py -m unittest tests.gui.test_library_pane_i18n -v

"Libary pane open is still english." Most of the pane already goes through a
patched setter, so the rest is the two shapes the hook can never reach on its
own:

* a caption built by an f-string — "Class D", "★ Proven (≥10)", the
  "(123/3638 tracks)" count — arrives at `t()` as a sentence that is not a
  catalog key and never will be, because the number in it is not known until
  it runs;
* a `QTableWidgetItem` tooltip, because that class is deliberately NOT one of
  i18n's patched constructors (`planner/i18n.py` `_CTOR_CLASSES`) and is not a
  QWidget either, so `setToolTip` on one reaches the screen as written — even
  for the two phrases the catalog has carried all along.

`DEFAULT_LANGUAGE` is English and `t()` is then the identity, so a test that
does not switch the language cannot see a missing entry at all. Hence
`speak("de")`: that is the switch this file exists for. The pane is built
AFTER it, because the combos are filled in `__init__`.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libi18n_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.common import _PROVEN_MIN_PLAYS  # noqa: E402
from gui.library_browser import LibraryBrowser  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import LIBRARY_CATEGORIES, MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

# One of each kind the cells describe: a track with class tags and a play
# history, one nobody has played, and one played only in undated lists.
TAGGED = MusicEntry(path=Path(r"C:\music\tanzcds\LW1.mp3"), title="LW one",
                    dance="LW", duration=180, bpm=29, popularity=4,
                    classes_ok=["D", "C"], last_played=2024, added=1.0)
FRESH = MusicEntry(path=Path(r"C:\music\tanzcds\TG1.mp3"), title="TG one",
                   dance="TG", duration=180, bpm=32, added=1.0)
UNDATED = MusicEntry(path=Path(r"C:\music\tanzcds\QS1.mp3"), title="QS one",
                     dance="QS", duration=180, bpm=51, popularity=2, added=1.0)


class _GermanPane(unittest.TestCase):
    """A pane built while the app speaks German."""

    def setUp(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    @staticmethod
    def items(combo):
        return [combo.itemText(i) for i in range(combo.count())]


class FilterComboTest(_GermanPane):
    """The six filter combos. Every one is read back by `currentData()`, so
    the caption is free to change — see `focus_filter` and `_refilter`."""

    def test_the_class_filter(self):
        """"Class D" is an f-string, so it is not a key — the template is."""
        said = self.items(self.b._class_combo)
        self.assertIn("Klasse D", said, said)
        self.assertIn("Klasse S", said, said)

    def test_the_plays_filter(self):
        said = self.items(self.b._plays_combo)
        self.assertIn("★ Selten (1–%d)" % (_PROVEN_MIN_PLAYS - 1), said, said)
        self.assertIn("★ Bewährt (≥%d)" % _PROVEN_MIN_PLAYS, said, said)

    def test_the_plays_filter_tooltip(self):
        tip = self.b._plays_combo.toolTip()
        self.assertIn("Filtern danach, wie der Titel bisher benutzt wurde",
                      tip, tip)
        self.assertIn("★ selten / bewährt", tip, tip)

    def test_the_library_categories(self):
        """The five non-tournament folders, named in the combo."""
        said = self.items(self.b._cat_combo)
        for cid in LIBRARY_CATEGORIES:
            self.assertNotIn(LIBRARY_CATEGORIES[cid][0], said,
                             "%s is still English:\n%s" % (cid, said))
        self.assertIn("🎄 Saison / Weihnachten", said, said)
        self.assertIn("👥 Doppelte / Rohfassungen", said, said)


class CountLabelTest(_GermanPane):
    """The "(123/3638 tracks)" beside the 📚 header."""

    def test_the_count_beside_the_header(self):
        self.b.set_entries([TAGGED, FRESH, UNDATED])
        said = self.b._count_lbl.text()
        self.assertEqual("(3/3 Titel)", said)


class ColumnMenuTest(_GermanPane):
    """The header's right-click tick list."""

    def test_the_two_glyph_columns(self):
        said = [a.text() for a in self.b.build_column_menu().actions()]
        self.assertIn("▶  Abspielen", said, said)
        self.assertIn("⏱  Länge", said, said)


class CellTooltipTest(_GermanPane):
    """Tooltips set on a QTableWidgetItem — unpatched, every one of them."""

    def setUp(self):
        super().setUp()
        self.b.set_entries([TAGGED, FRESH, UNDATED])

    def tip(self, row, col):
        return self.b._table.item(row, col).toolTip()

    def test_the_play_cell(self):
        self.assertEqual("Diesen Titel abspielen / stoppen", self.tip(0, 0))

    def test_the_class_cell(self):
        self.assertEqual("Klassen-Tags aus dem MP3-Kommentarfeld",
                         self.tip(0, 7))

    def test_the_added_cell(self):
        self.assertEqual("Wann diese Datei in der Bibliothek angelegt wurde",
                         self.tip(0, 8))

    def test_the_last_cell_of_a_played_track(self):
        self.assertEqual("Neueste Playlist mit diesem Titel", self.tip(0, 9))

    def test_the_last_cell_of_a_fresh_track(self):
        self.assertEqual("Nie gelaufen", self.tip(1, 9))

    def test_the_last_cell_of_an_undated_track(self):
        self.assertEqual("Gelaufen, aber keine dieser Playlists ist datiert",
                         self.tip(2, 9))


class EnglishIsUnchangedTest(unittest.TestCase):
    """The catalog is a lookup on the English string, so English has to come
    back byte for byte — the f-strings that became templates most of all."""

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)

    def test_the_filters_and_the_count_read_the_way_they_did(self):
        said = [self.b._class_combo.itemText(i)
                for i in range(self.b._class_combo.count())]
        self.assertIn("Class D", said, said)
        said = [self.b._plays_combo.itemText(i)
                for i in range(self.b._plays_combo.count())]
        self.assertIn("★ Rarely (1–%d)" % (_PROVEN_MIN_PLAYS - 1), said, said)
        self.assertIn("★ Proven (≥%d)" % _PROVEN_MIN_PLAYS, said, said)
        self.b.set_entries([TAGGED, FRESH])
        self.assertEqual("(2/2 tracks)", self.b._count_lbl.text())


if __name__ == "__main__":
    unittest.main()
