"""The right-click menu reads the same way in every kind of list.

Run:  py -m unittest tests.gui.table.test_menu_order -v

Marcel's list, 6.7: "Improve the ordering of context menu entries." From the
title outwards: what to look up for it, where it stands, what it is marked as,
the file behind it, then the rounds and what comes out, then the whole list
with its emptying last, furthest from the mouse.
"""
import os
import tempfile
import unittest
from itertools import pairwise
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_menu_order_"))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

# The groups, top to bottom, each by how its entries begin.
GROUPS = (("🔎", "⭐", "🌱", "📜"),
          ("⇅", "⬇"),
          ("🔁",),
          ("📌",),
          ("📋", "📂  Show", "🎵", "🏷", "↩"),
          ("➕",),
          ("🗑", "⬆"),
          ("🔒", "🔓", "↔"),
          ("🔍",),
          ("💾", "🏆", "📂  Import", "📥"),
          ("🧹  Remove", "♊"),
          ("🧹  Empty",))


def _group(text):
    return next(i for i, starts in enumerate(GROUPS) if text.startswith(starts))


def _e(title, dance="LW"):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance=dance,
                      duration=150)


class MenuOrderTest(unittest.TestCase):

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def party(self):
        t = self.table()
        t.load_warmup([_e("A"), _e("B"), _e("C")], "Party", "Standard", "S", False,
                      mock.Mock(), None)
        return t

    def free_order(self):
        t = self.table()
        t.load_warmup([_e("A"), _e("B"), _e("C")], "Party", "Standard", "S", False,
                      mock.Mock(), None, running_order=True)
        return t

    def wishlist(self):
        t = self.table()
        t.load_wishlist([_e("A"), _e("B")], mock.Mock(), None)
        return t

    def grid(self, **kw):
        t = self.table()
        t.load({"Final": [[_e("A"), _e("B", "TG")]]}, ["LW", "TG"],
               [RoundConfig(name="Final", heats=1, tier="final")], "S", mock.Mock(),
               suggester=None, use_timbre=False, style="Standard", **kw)
        return t

    def lists(self):
        return {"party": self.party(), "free order": self.free_order(),
                "wishlist": self.wishlist(), "static deck": self.grid(),
                "dynamic deck": self.grid(dynamic=True, capacity=[1, 1])}

    @staticmethod
    def menu(t):
        """The menu on the list's first title, a separator as None."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(None if a.isSeparator() else a.text()
                            for a in self.actions())

        row = t._row_meta.song_rows()[0]
        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen

    def test_the_groups_stand_in_the_same_order_in_every_list(self):
        for name, t in self.lists().items():
            with self.subTest(list=name):
                groups = [_group(x) for x in self.menu(t) if x is not None]
                self.assertEqual(groups, sorted(groups))

    def test_a_line_stands_between_any_two_groups(self):
        for name, t in self.lists().items():
            entries = self.menu(t)
            for above, below in pairwise(entries):
                if above is None or below is None or _group(above) == _group(below):
                    continue
                with self.subTest(list=name, above=above, below=below):
                    self.fail("no line between two groups")

    def test_the_wishlist_removes_where_a_deck_removes(self):
        """Below the file, not between it and the move."""
        entries = [x for x in self.menu(self.wishlist()) if x is not None]
        self.assertLess(entries.index("🏷  Edit tags…	Ctrl+T"),
                        entries.index("🗑  Remove from wishlist	Del"))
        self.assertLess(entries.index("⬇  Move to the end of the list"),
                        entries.index("🗑  Remove from wishlist	Del"))

    def test_swap_and_move_stand_together(self):
        t = self.party()
        rows = t._row_meta.song_rows()
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(rows[0])
        t.selectRow(rows[1])
        entries = self.menu(t)
        swap = next(i for i, x in enumerate(entries) if x and x.startswith("⇅"))
        self.assertTrue(entries[swap + 1].startswith("⬇"))

    def test_emptying_the_list_comes_last(self):
        for name, t in self.lists().items():
            with self.subTest(list=name):
                self.assertTrue(self.menu(t)[-1].startswith("🧹  Empty"))

    def test_a_player_install_opens_without_a_line_on_top(self):
        """It has no lookups, so the first group is another one there."""
        t = self.party()
        host = mock.MagicMock()
        host.player_only.return_value = True
        host.has_tournaments.return_value = False
        host.can_clean_decks.return_value = False
        with mock.patch.object(PlaylistTable, "host", new_callable=mock.PropertyMock,
                               return_value=host):
            entries = self.menu(t)
        self.assertIsNotNone(entries[0])


if __name__ == "__main__":
    unittest.main()
