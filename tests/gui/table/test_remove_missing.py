#!/usr/bin/env python3
"""Several "file not found" titles selected go together, by Del or by 🗑.

Run:  py -m unittest tests.gui.table.test_remove_missing -v

Marcel: unavailable titles could not be removed via multi-select (wishlist,
possibly playlist); a single delete and "clear all" worked. Every title here
names a file that does not exist, so each row is painted as missing (❗).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_remove_missing_"))

from PySide6.QtCore import QEvent, QItemSelectionModel, QPoint, Qt
from PySide6.QtGui import QContextMenuEvent, QKeyEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)
_ROWS = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows


def _gone(dance, n):
    return MusicEntry(path=Path(rf"X:\unplugged\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class _Base(unittest.TestCase):

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def select(self, t, *rows):
        t.clearSelection()
        for r in rows:
            t.selectionModel().select(t.model().index(r, 0), _ROWS)

    def press_delete(self, t):
        t.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete,
                                  Qt.KeyboardModifier.NoModifier))

    def pick_from_menu(self, t, row, caption):
        """Right-click `row` and pick the entry whose text starts with `caption`."""
        class _Menu(QMenu):
            def exec(self, *_args):
                return next((a for a in self.actions()
                             if a.text().startswith(caption)), None)
        y = t.rowViewportPosition(row) + 2
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(5, y), QPoint(5, y)))


class WishlistTest(_Base):

    def wishlist(self):
        t = self.table()
        t.load_wishlist([_gone("LW", 1), _gone("TG", 2), _gone("SF", 3),
                         _gone("QS", 4)], play_cb=lambda *a: None, suggester=None)
        return t

    def titles(self, t):
        return [e.title for e in t.wishlist_entries()]

    def test_del_removes_every_selected_missing_title(self):
        t = self.wishlist()
        self.select(t, 0, 2)
        self.press_delete(t)
        self.assertEqual(self.titles(t), ["TG 2", "QS 4"])

    def test_the_menu_removes_the_selection_it_was_opened_in(self):
        t = self.wishlist()
        self.select(t, 0, 2)
        self.pick_from_menu(t, 2, "🗑  Remove")
        self.assertEqual(self.titles(t), ["TG 2", "QS 4"])

    def test_the_menu_outside_the_selection_removes_that_row_only(self):
        t = self.wishlist()
        self.select(t, 0, 2)
        self.pick_from_menu(t, 3, "🗑  Remove")
        self.assertEqual(self.titles(t), ["LW 1", "TG 2", "SF 3"])


class DeckTest(_Base):

    def deck(self):
        t = self.table()
        playlist = {"Finale": [[_gone("LW", 1), _gone("TG", 2), _gone("SF", 3)]]}
        t.load(playlist, ["LW", "TG", "SF"],
               [RoundConfig(name="Finale", heats=1, tier="final")], "S",
               play_cb=lambda *a: None, suggester=None, use_timbre=False)
        mock.patch.object(t, "_confirm_delete", return_value=True).start()
        self.addCleanup(mock.patch.stopall)
        return t

    def song_rows(self, t):
        return [r for r, m in t._row_meta.numbered() if m.entry is not None]

    def titles(self, t):
        return [t._row_meta[r].entry.title for r in self.song_rows(t)]

    def test_del_empties_every_selected_missing_slot(self):
        t = self.deck()
        lw, _tg, sf = self.song_rows(t)
        self.select(t, lw, sf)
        self.press_delete(t)
        self.assertEqual(self.titles(t), ["TG 2"])


if __name__ == "__main__":
    unittest.main()
