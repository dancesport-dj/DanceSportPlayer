#!/usr/bin/env python3
"""The search of Find in list: titles, the genre fallback, the highlight.

Run:  py -m unittest tests.gui.table.test_find_genre -v

The search dialog has a title row and a genre row: the title steps to the next
match and tints every match at once, the genre highlights every matching row -
"show me every Paso Doble of this party list". A row matches by dance code, full
dance name, social genre label or plain genre tag, accent-, case- and
punctuation-insensitively, so 'chacha' finds a Cha-Cha. A title that finds no
title falls through to the dance, so 'CC' names a dance from either field.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_findgenre_"))

from PySide6.QtWidgets import QApplication, QDialog, QWidget

from gui.dialogs import FindInListDialog
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import _C_FIND_BG
from planner.models import MusicEntry
from shared.columns import _COL_DANCE
from tests.qt_test_support import reap_widget

_DIR = Path(tempfile.mkdtemp(prefix="dp_findgenre_m_"))


def _e(title, dance=None, other_genre=None):
    path = _DIR / f"{title}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=title, dance=dance, duration=150,
                      other_genre=other_genre)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class GenreRowTest(unittest.TestCase):
    """A party list holding two Paso Dobles among the other dances."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        entries = [_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD"),
                   _e("RB 1", "RB")]
        t.load_warmup(entries, "ETDS Party", "", "S", True, lambda _p: None, None)
        return t

    def titles_of(self, t, rows):
        return [t._row_meta[r].entry.title for r in rows]

    def test_paso_doble_finds_both_pasos(self):
        t = self.table()
        self.assertEqual(self.titles_of(t, t._genre_match_rows("paso doble")),
                         ["PD 1", "PD 2"])

    def test_the_code_alone_finds_them_too(self):
        t = self.table()
        self.assertEqual(self.titles_of(t, t._genre_match_rows("PD")),
                         ["PD 1", "PD 2"])

    def test_a_partial_word_and_any_case_find_them(self):
        t = self.table()
        self.assertEqual(self.titles_of(t, t._genre_match_rows("pAsO")),
                         ["PD 1", "PD 2"])

    def test_a_genre_the_list_does_not_hold_finds_nothing(self):
        t = self.table()
        self.assertEqual(t._genre_match_rows("Jive"), [])

    def test_a_social_genre_is_found_by_its_label(self):
        t = self.table()
        t._row_meta[t._row_meta.song_rows()[1]].entry.other_genre = "Boogie Woogie"
        self.assertIn(t._row_meta.song_rows()[1],
                      t._genre_match_rows("boogie"))

    def test_chacha_finds_the_cha_cha_dance_without_its_hyphen(self):
        t = self.table()
        self.assertEqual(self.titles_of(t, t._genre_match_rows("chacha")),
                         ["CC 1"])


class SearchTest(unittest.TestCase):
    """Ctrl+F answered as the operator would: a title, a genre, or both."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, entries):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        t.load_warmup(entries, "ETDS Party", "", "S", True, lambda _p: None, None)
        return t

    def search(self, t, title="", genre="", seen=None, accept=True):
        """Answer the find dialog as if the operator had typed `title`/`genre`."""
        class _FindInList:
            def __init__(self, _parent, remembered_title="", remembered_genre=""):
                if seen is not None:
                    seen.append((remembered_title, remembered_genre))

            def exec(self):
                return (QDialog.DialogCode.Accepted if accept
                        else QDialog.DialogCode.Rejected)

            def title(self):
                return title

            def genre(self):
                return genre

        with mock.patch("gui.dialogs.FindInListDialog", _FindInList):
            t._search_title()

    def row_of(self, t, title):
        return next(r for r, m in t._row_meta.numbered()
                    if m.entry is not None and m.entry.title == title)

    def dance_bg(self, t, row):
        return t.item(row, _COL_DANCE).background().color()

    def test_chacha_finds_a_cha_cha_title(self):
        t = self.table([_e("Cha-Cha One", "CC"), _e("Rumba One", "RB")])
        self.search(t, title="chacha")
        cha = self.row_of(t, "Cha-Cha One")
        self.assertEqual(t.currentRow(), cha)
        self.assertEqual(t._find_rows, [cha])

    def test_cc_in_the_title_field_finds_the_cha_chas(self):
        t = self.table([_e("First", "CC"), _e("Second", "RB"),
                        _e("Third", "CC")])
        self.search(t, title="CC")
        first, third = self.row_of(t, "First"), self.row_of(t, "Third")
        self.assertEqual(t._find_rows, [first, third])
        self.assertEqual(t.currentRow(), first, "jumped to the first match")

    def test_every_title_match_is_tinted(self):
        t = self.table([_e("Topic One", "PD"), _e("Other", "RB"),
                        _e("Topic Two", "PD")])
        self.search(t, title="topic")
        one, two = self.row_of(t, "Topic One"), self.row_of(t, "Topic Two")
        self.assertEqual(t._find_rows, [one, two])
        self.assertEqual(self.dance_bg(t, one), _C_FIND_BG)
        self.assertEqual(self.dance_bg(t, two), _C_FIND_BG)
        self.assertNotEqual(self.dance_bg(t, self.row_of(t, "Other")), _C_FIND_BG)

    def test_a_genre_search_jumps_to_the_first_match(self):
        t = self.table([_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD")])
        self.search(t, genre="PD")
        first = self.row_of(t, "PD 1")
        self.assertEqual(t._find_rows, [first, self.row_of(t, "PD 2")])
        self.assertEqual(t.currentRow(), first)

    def test_a_fresh_genre_search_starts_at_the_first_match_not_after_it(self):
        """The row the operator was looking at is no head start: searching its
        own genre must land on the first PD, not the second."""
        t = self.table([_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD")])
        first, second = self.row_of(t, "PD 1"), self.row_of(t, "PD 2")
        t.setCurrentCell(first, _COL_DANCE)
        self.search(t, genre="PD")
        self.assertEqual(t.currentRow(), first)
        self.assertNotEqual(t.currentRow(), second)

    def test_a_fresh_title_search_starts_at_the_first_match_too(self):
        t = self.table([_e("Topic One", "PD"), _e("Other", "RB"),
                        _e("Topic Two", "PD")])
        first = self.row_of(t, "Topic One")
        t.setCurrentCell(first, _COL_DANCE)
        self.search(t, title="topic")
        self.assertEqual(t.currentRow(), first)

    def test_running_the_same_search_again_steps_on(self):
        t = self.table([_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD")])
        first, second = self.row_of(t, "PD 1"), self.row_of(t, "PD 2")
        self.search(t, genre="PD")
        self.assertEqual(t.currentRow(), first)
        self.search(t, genre="PD")
        self.assertEqual(t.currentRow(), second)

    def test_another_genre_starts_at_its_own_first_match(self):
        t = self.table([_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD")])
        self.search(t, genre="PD")
        self.search(t, genre="CC")
        self.assertEqual(t.currentRow(), self.row_of(t, "CC 1"))

    def test_a_cancel_between_two_searches_does_not_step(self):
        t = self.table([_e("PD 1", "PD"), _e("CC 1", "CC"), _e("PD 2", "PD")])
        first = self.row_of(t, "PD 1")
        self.search(t, genre="PD")
        self.search(t, genre="PD", accept=False)
        self.search(t, genre="PD")
        self.assertEqual(t.currentRow(), first)

    def test_a_search_that_finds_nothing_takes_the_tint_back(self):
        t = self.table([_e("Topic One", "PD")])
        one = self.row_of(t, "Topic One")
        self.search(t, title="topic")
        self.assertEqual(t._find_rows, [one])
        self.search(t, title="no such title")
        self.assertEqual(t._find_rows, [])
        self.assertNotEqual(self.dance_bg(t, one), _C_FIND_BG)

    def test_the_last_search_comes_back_and_a_cleared_title_stays_clear(self):
        t = self.table([_e("PD 1", "PD")])
        seen = []
        self.search(t, title="PD 1", genre="PD", seen=seen)
        self.search(t, title="", genre="PD", seen=seen)
        self.search(t, title="", genre="PD", seen=seen)
        self.assertEqual(seen, [("", ""), ("PD 1", "PD"), ("", "PD")])


class FindDialogWidthTest(unittest.TestCase):
    """The dialog is as wide as the example it shows, and no wider."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_fields_are_as_wide_as_the_example_text(self):
        dlg = FindInListDialog(None)
        self.addCleanup(dlg.deleteLater)
        dlg.adjustSize()
        need = dlg._genre.fontMetrics().horizontalAdvance(
            dlg._genre.placeholderText())
        self.assertGreaterEqual(dlg._genre.width(), need)
        self.assertLessEqual(dlg.width(), need + 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
