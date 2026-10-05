#!/usr/bin/env python3
"""Tests for sorting a list by double-clicking a column header.

Run:  py -m unittest tests.gui.test_header_sort -v

Two kinds of table hold a plain list the user owns the order of: the Wishlist,
and a deck in ✋ free order. Those sort. A static or dynamic deck does not —
there the row order IS the draw (round, dance, heat), so re-ordering the rows
would mean re-ordering the tournament.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sort_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from shared.columns import _COL_ARTIST, _COL_DANCE, _COL_HEAT, _COL_TITLE  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402


def _e(dance, title, artist=None):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title,
                      dance=dance, bpm=None, tag_artist=artist)


def _social(genre, title):
    """A social-dance track: no competition dance, the genre label says it."""
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title,
                      dance=None, other_genre=genre, bpm=None)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _SortTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self) -> PlaylistTable:
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        return t

    def titles(self, table):
        return [m.entry.title for m in table._row_meta
                if m and m.entry is not None]

    def sort_by(self, table, col: int):
        """What a double-click on that column header does."""
        table._on_header_section_double_clicked(col)
        return self.titles(table)


class FreeOrderTest(_SortTest):
    """A deck in ✋ free order is a list — it sorts."""

    def deck(self) -> PlaylistTable:
        t = self.table()
        t.load_player_list([_e("TG", "Roxanne", "Sting"),
                            _e("LW", "Ballade", "Adele"),
                            _e("TG", "Assassin", "Muse")],
                           "Abend", play_cb=None)
        return t

    def test_dance_sorts_in_tournament_order(self):
        t = self.deck()
        # LW before TG — the tournament order, not the alphabet.
        self.assertEqual(self.sort_by(t, _COL_DANCE),
                         ["Ballade", "Assassin", "Roxanne"])

    def test_social_dances_group_by_dance_after_latin(self):
        """A social track has no competition dance — its genre is what the
        Dance column shows, and what the sort has to group by. Titles are
        picked so an alphabetical fallback would interleave the dances."""
        t = self.table()
        t.load_player_list([_social("Kizomba", "A Kizomba"),
                            _social("Salsa", "B Salsa"),
                            _social("Discofox", "C Discofox"),
                            _e("JI", "D Jive"),
                            _social("Salsa", "E Salsa"),
                            _social("Kizomba", "F Kizomba")],
                           "Party", play_cb=None)
        self.assertEqual(self.sort_by(t, _COL_DANCE),
                         ["D Jive", "C Discofox", "B Salsa", "E Salsa",
                          "A Kizomba", "F Kizomba"])

    def test_artist_sorts_by_artist(self):
        t = self.deck()
        self.assertEqual(self.sort_by(t, _COL_ARTIST),
                         ["Ballade", "Assassin", "Roxanne"])   # Adele, Muse, Sting

    def test_the_same_column_again_reverses(self):
        t = self.deck()
        self.sort_by(t, _COL_TITLE)
        self.assertEqual(self.titles(t), ["Assassin", "Ballade", "Roxanne"])
        self.assertEqual(self.sort_by(t, _COL_TITLE),
                         ["Roxanne", "Ballade", "Assassin"])

    def test_a_column_with_nothing_to_order_by_is_ignored(self):
        t = self.deck()
        before = self.titles(t)
        self.assertEqual(self.sort_by(t, _COL_HEAT), before)

    def test_the_list_stays_a_running_order(self):
        t = self.deck()
        self.sort_by(t, _COL_ARTIST)
        self.assertTrue(t._player_list)


class PlannedDeckTest(_SortTest):
    """A draw is not a view of a list — its rows stay where the plan put them."""

    def test_a_grid_ignores_the_header(self):
        t = self.table()
        t.load({"Vorrunde": [[_e("TG", "Roxanne"), _e("LW", "Ballade")]]},
               ["TG", "LW"],
               [RoundConfig(name="Vorrunde", heats=1, tier="early")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        before = self.titles(t)
        self.assertEqual(self.sort_by(t, _COL_DANCE), before)
        self.assertEqual(self.sort_by(t, _COL_TITLE), before)


class WishlistTest(_SortTest):
    """The gesture the Wishlist already had, now on double-click."""

    def wishlist(self) -> PlaylistTable:
        t = self.table()
        t.load_wishlist([_e("TG", "Roxanne", "Sting"),
                         _e("LW", "Ballade", "Adele")], play_cb=None,
                        suggester=None)
        return t

    def test_the_wishlist_sorts_by_artist(self):
        t = self.wishlist()
        self.assertEqual(self.sort_by(t, _COL_ARTIST), ["Ballade", "Roxanne"])

    def test_the_wishlist_sorts_by_dance(self):
        t = self.wishlist()
        self.assertEqual(self.sort_by(t, _COL_DANCE), ["Ballade", "Roxanne"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
