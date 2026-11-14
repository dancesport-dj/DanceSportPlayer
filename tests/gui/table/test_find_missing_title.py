"""🔭 Find this title: the context menu of a red row looks the song up by its title.

Run:  py -m unittest tests.gui.table.test_find_missing_title -v

Marcel's list, 6.5: "For a red title give a context menu option to find it
(e.g. renamed with _cut). Equal file names on other drive letters are found
already." The red row's file is gone; the library may hold it under another name.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_find_missing_"))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from gui.table.table_host import TableHost
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

FIND = "🔭  Find this title…"


class FindMissingTitleTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.toasts = []
        patcher = mock.patch.object(
            table_menu, "show_toast",
            lambda _w, text, *a, **kw: self.toasts.append(text))
        patcher.start()
        self.addCleanup(patcher.stop)

    def entry(self, name, dance="LW", exists=True) -> MusicEntry:
        p = self.dir / f"{name}.mp3"
        if exists:
            p.write_bytes(b"x")
        return MusicEntry(path=p, title=name, dance=dance, duration=150)

    def party(self, held, library):
        t = PlaylistTable()
        t.resize(700, 600)
        self.addCleanup(reap_widget, t)
        t.load_warmup(held, "Party", "Standard", "S", False, mock.Mock(), None)
        # `table.host` is a fresh TableHost on every access: patch the class.
        for name, value in (("file_there", lambda _h, p: Path(p).is_file()),
                            ("library_entries", lambda _h: library),
                            ("entry_for", lambda _h, p: MusicEntry(
                                path=Path(p), title=Path(p).stem, dance="LW",
                                duration=150))):
            patcher = mock.patch.object(TableHost, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        return t

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in t._row_meta.numbered() if m.entry.title == title)

    @staticmethod
    def titles(t):
        return [e.title for e in t._row_meta.entries()]

    def menu(self, t, row, pick=None):
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen

    def pick_item(self, index=0, ok=True):
        """Stand in for the chooser; `index` is the item taken."""
        def getItem(_parent, _title, _label, items, *_a, **_kw):
            self.offered = list(items)
            return (items[index], ok) if items else ("", False)
        return mock.patch.object(table_menu.QInputDialog, "getItem", getItem)

    def test_a_red_row_offers_to_find_the_title(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        ok = self.entry("Moon River (LW 29)")
        t = self.party([red, ok], [])
        self.assertIn(FIND, self.menu(t, self.row_of(t, red.title)))

    def test_a_row_whose_file_is_there_has_no_such_entry(self):
        ok = self.entry("Moon River (LW 29)")
        t = self.party([ok], [])
        self.assertNotIn(FIND, self.menu(t, self.row_of(t, ok.title)))

    def test_the_renamed_file_takes_the_place_of_the_red_title(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        ok = self.entry("Moon River (LW 29)")
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red, ok], [cut, ok])
        with self.pick_item():
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [cut.title, ok.title])
        self.assertEqual(len(self.offered), 1)
        self.assertIn(cut.path.name, self.offered[0])

    def test_a_wishlist_row_is_found_too(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        t.load_wishlist([red], mock.Mock(), None)
        with self.pick_item():
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [cut.title])

    def test_nothing_is_replaced_when_the_chooser_is_cancelled(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        with self.pick_item(ok=False):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [red.title])

    def test_no_file_with_that_title_says_so(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        other = self.entry("Moon River (LW 29)")
        t = self.party([red], [other])
        with self.pick_item():
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [red.title])
        self.assertEqual(self.toasts, ["🔭  No other file with this title found"])

    def test_a_file_renamed_in_place_is_found_without_the_library(self):
        red = self.entry("A New Life (LW 29)_cut", exists=False)
        renamed = self.entry("A New Life (LW 29)")      # on disk, not in the library
        t = self.party([red], [])
        with self.pick_item():
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [renamed.title])

    def test_a_file_the_list_holds_is_not_offered_again(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red, cut], [cut])
        with self.pick_item():
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [red.title, cut.title])
        self.assertEqual(len(self.toasts), 1)

    def planned(self, value):
        """What the other decks plan, or the error the deck index raises."""
        def planned_paths(_h):
            if isinstance(value, Exception):
                raise value
            return set(value)
        patcher = mock.patch.object(TableHost, "planned_paths", planned_paths)
        patcher.start()
        self.addCleanup(patcher.stop)

    def asked(self, answer):
        """Stand in for the planned-elsewhere question; records what it said."""
        self.questions = []

        def question(_parent, _title, text, *_a, **_kw):
            self.questions.append(text)
            return answer
        return mock.patch.object(table_menu.QMessageBox, "question", question)

    def test_a_file_another_deck_plans_is_offered(self):
        """The search is for the renamed file, and the renamed file may be the
        one another list already plans: it is offered like any other."""
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        self.planned({str(cut.path).lower()})
        with self.pick_item(ok=False), self.asked(table_menu.QMessageBox.StandardButton.Yes):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(len(self.offered), 1)
        self.assertIn(cut.path.name, self.offered[0])

    def test_taking_a_planned_file_says_so_and_takes_it_on_yes(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        self.planned({str(cut.path).lower()})
        with self.pick_item(), self.asked(table_menu.QMessageBox.StandardButton.Yes):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(len(self.questions), 1)
        self.assertIn("another open playlist", self.questions[0])
        self.assertIn(cut.path.name, self.questions[0])
        self.assertEqual(self.titles(t), [cut.title])

    def test_no_keeps_the_red_title(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        self.planned({str(cut.path).lower()})
        with self.pick_item(), self.asked(table_menu.QMessageBox.StandardButton.No):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.titles(t), [red.title])

    def test_a_file_planned_nowhere_is_taken_without_a_question(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        self.planned(set())
        with self.pick_item(), self.asked(table_menu.QMessageBox.StandardButton.No):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.questions, [])
        self.assertEqual(self.titles(t), [cut.title])

    def test_a_deck_index_that_fails_takes_the_file_without_a_question(self):
        red = self.entry("A New Life (LW 29)", exists=False)
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        t = self.party([red], [cut])
        self.planned(RuntimeError("deck gone"))
        with self.pick_item(), self.asked(table_menu.QMessageBox.StandardButton.No):
            self.menu(t, self.row_of(t, red.title), pick=FIND)
        self.assertEqual(self.questions, [])
        self.assertEqual(self.titles(t), [cut.title])


if __name__ == "__main__":
    unittest.main()
