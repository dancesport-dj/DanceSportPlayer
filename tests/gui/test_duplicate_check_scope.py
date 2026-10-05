#!/usr/bin/env python3
"""🔁 Check duplicates looks at every playlist, not only the decks on screen.

Run:  py -m unittest tests.gui.test_duplicate_check_scope -v

Marcel: "check duplicates does not recognize duplicate in wishlist or
eintanzlist only normal playlists" and "make sure all playlist are checked, in
danceconvention 2026 we have 5 which cant be shown on one screen so it has
another tab". The check only took the decks of the current view. Every deck
that holds titles counts now, on whichever tab it sits, and so do the shown
wishlists and the shown Eintanzen panel, both inside themselves and against
the decks.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_scope_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.main_decks import DeckLayoutMixin  # noqa: E402
from gui.main_dupes import DuplicateCheckMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from planner.suggester import PlaylistSuggester  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _waltz(name: str, folder: str = "standardcd") -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{folder}\{name} (LW 29).mp3"),
                      title=name, dance="LW", bpm=29)


class _Win(QWidget, DuplicateCheckMixin):
    """The main window as far as the duplicate check reaches: eight decks (only
    deck A in the current view), a wishlist, a second wishlist that is not
    shown, and the Eintanzen panel."""

    deck = DeckLayoutMixin.deck
    _checkable_deck_tables = DeckLayoutMixin._checkable_deck_tables

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}
        self._cache = None
        self._lib = MusicLibrary()
        self._deck_of = {}
        self._decks = [self._table(f"Deck {c}") for c in "ABCDEFGH"]
        self._day_decks = [self._table(f"Day {i}") for i in range(8)]
        self._wishlists = [self._table("Wishlist"), self._table("Wishlist 2")]
        self._warmup_table = self._table("Eintanzen")
        self.deck(self._wishlists[1]).box.setVisible(False)

    def _table(self, name: str) -> PlaylistTable:
        t = PlaylistTable()
        box = QWidget(self)
        t.setParent(box)
        self.deck(t).box = box
        self.deck(t).name = name
        return t

    def fill_deck(self, table, songs):
        self._lib.entries += songs
        heats = [[s] for s in songs]
        table.load({"Vorrunde": heats}, ["LW"],
                   [RoundConfig(name="Vorrunde", heats=len(heats), tier="early")],
                   "D", play_cb=None, suggester=PlaylistSuggester(self._lib),
                   use_timbre=False)

    def fill_list(self, table, songs):
        table.load_wishlist(songs, play_cb=None, suggester=None)

    def _visible_deck_tables(self):
        return [self._decks[0]]           # the 1-deck view: only A on screen


def _pairs(report) -> set:
    return {frozenset((c["file_a"], c["file_b"])) for c in report["cross"]}


def _withins(report) -> set:
    return {w["file"] for w in report["within"]}


class DuplicateCheckScopeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _Win()
        self.addCleanup(reap_widget, self.win)
        self.a, self.b = _waltz("Alpha"), _waltz("Beta")
        self.win.fill_deck(self.win._decks[0], [self.a, self.b])

    def test_a_deck_on_the_other_tab_is_checked(self):
        self.win.fill_deck(self.win._decks[4], [_waltz("Gamma"), self.a])
        self.assertIn(frozenset(("Deck A", "Deck E")), _pairs(self.win._deck_dup_report()))

    def test_a_day_deck_is_checked(self):
        self.win.fill_deck(self.win._day_decks[2], [self.b])
        self.assertIn(frozenset(("Deck A", "Day 2")), _pairs(self.win._deck_dup_report()))

    def test_a_wishlist_title_also_in_a_deck(self):
        self.win.fill_list(self.win._wishlists[0], [_waltz("Gamma"), self.b])
        self.assertIn(frozenset(("Deck A", "Wishlist")), _pairs(self.win._deck_dup_report()))

    def test_a_title_twice_in_one_wishlist(self):
        again = _waltz("Gamma", folder="other")          # another recording
        self.win.fill_list(self.win._wishlists[0], [_waltz("Gamma"), again])
        self.assertIn("Wishlist", _withins(self.win._deck_dup_report()))

    def test_an_eintanzen_title_also_in_a_deck(self):
        self.win.fill_list(self.win._warmup_table, [self.a])
        self.assertIn(frozenset(("Deck A", "Eintanzen")), _pairs(self.win._deck_dup_report()))

    def test_a_wishlist_that_is_not_shown_is_left_out(self):
        self.win.fill_list(self.win._wishlists[1], [self.a])
        self.assertEqual(_pairs(self.win._deck_dup_report()), set())

    def test_a_copy_in_a_wishlist_can_be_replaced(self):
        wl = self.win._wishlists[0]
        self.win.fill_list(wl, [self.b])
        self.win._deck_dup_report()
        slot = next(i for i, s in enumerate(self.win._dup_slots) if s[0] is wl)
        new = _waltz("New")
        self.win.statusBar = lambda: _Status()
        self.win._apply_dup_resolutions([(slot, new)])
        self.assertEqual(wl.wishlist_entries(), [new])


class _Status:
    def showMessage(self, *_a):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
