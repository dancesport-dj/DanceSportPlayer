#!/usr/bin/env python3
"""Tests for the 🔢 Numbers view: no groups plus a leading Nb. column.

Run:  py -m unittest tests.gui.test_number_column -v

The 🗜 header cycle gets a fourth step after 🚫 No groups. The list stays flat and
every title carries its number up front, like line numbers, so the operator sees
how far into the list a song sits.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_numbers_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.main_decks import DeckLayoutMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class NumberColumnTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        playlist = {"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                    "Finale": [[_e("LW", 3), _e("TG", 4)]]}
        rounds = [RoundConfig(name="Vorrunde", heats=1, tier="early"),
                  RoundConfig(name="Finale", heats=1, tier="final")]
        t.load(playlist, ["LW", "TG"], rounds, "S",
               play_cb=lambda *a: None, suggester=None, use_timbre=False)
        return t

    def test_numbers_are_hidden_up_to_no_groups(self):
        t = self.deck()
        for state in (0, 1, 2):
            t.set_grouping(state)
            self.assertFalse(t.verticalHeader().isVisibleTo(t))
            self.assertFalse(t._nb_label.isVisibleTo(t))

    def test_numbers_view_is_flat_with_an_nb_column(self):
        t = self.deck()
        t.set_grouping(3)
        self.assertTrue(t._nogroup)
        self.assertTrue(t.verticalHeader().isVisibleTo(t))
        self.assertEqual(t._nb_label.text(), "Nb.")
        self.assertEqual(t._nb_label.font(), t.horizontalHeader().font())
        self.assertTrue(t._nb_label.isVisibleTo(t))
        songs = [t.song_number_label(r) for r in t._row_meta.song_rows()]
        self.assertEqual(songs, ["1", "2", "3", "4"])

    def test_header_rows_get_no_number(self):
        t = self.deck()
        t.set_grouping(0)                  # headers stay, the numbers skip them
        t.set_numbered(True)
        labels = [t.song_number_label(r) for r in range(t.rowCount())]
        self.assertEqual([x for x in labels if x], ["1", "2", "3", "4"])
        self.assertEqual(labels.count(""), t.rowCount() - 4)

    def test_back_to_full_drops_the_numbers(self):
        t = self.deck()
        t.set_grouping(3)
        t.set_grouping(0)
        self.assertFalse(t.verticalHeader().isVisibleTo(t))
        self.assertFalse(t._nogroup)


class WishlistNumbersTest(unittest.TestCase):
    """A wishlist is flat already, so 🔢 means one thing there: the Nb. column."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wishlist(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t.load_wishlist([_e("LW", 1), _e("TG", 2), _e("CC", 3)],
                        play_cb=lambda *a: None, suggester=None)
        return t

    def test_numbers_turn_the_nb_column_on(self):
        t = self.wishlist()
        t.set_grouping(3)
        self.assertTrue(t._numbered)
        self.assertFalse(t.verticalHeader().isHidden())

    def test_every_title_is_counted_from_one(self):
        t = self.wishlist()
        t.set_grouping(3)
        self.assertEqual([t.song_number_label(r) for r in range(t.rowCount())],
                         ["1", "2", "3"])

    def test_the_earlier_steps_leave_a_flat_list_alone(self):
        """0/1/2 drop headers a wishlist never had — only step 3 does anything."""
        t = self.wishlist()
        for state in (0, 1, 2):
            t.set_grouping(state)
            self.assertFalse(t._numbered)
            self.assertEqual(t.rowCount(), 3)


class CycleTest(unittest.TestCase):
    """The 🗜 button walks full → Compact → No groups → Numbers → full."""

    def win(self, state):
        warm, wish = mock.Mock(), mock.Mock()
        w = SimpleNamespace(_compact_state=state, _decks=[], _day_decks=[],
                            _warmup_table=warm, _wishlists=[wish],
                            _all_tables=[warm, wish], _settings={},
                            _compact_btn=mock.Mock(),
                            _set_toolbar_btn_text=mock.Mock(),
                            statusBar=mock.Mock())
        w._set_compact_state = lambda s: DeckLayoutMixin._set_compact_state(w, s)
        w._apply_compact_label = lambda: DeckLayoutMixin._apply_compact_label(w)
        return w

    def test_the_wishlists_are_cycled_too(self):
        """🔢 is a view of the whole desk, not of the decks only — a wishlist
        is exactly the flat list whose titles want counting."""
        with mock.patch("gui.main_decks.save_settings"):
            w = self.win(2)
            DeckLayoutMixin._cycle_compact(w)
        w._wishlists[0].set_grouping.assert_called_once_with(3)

    def test_cycle(self):
        with mock.patch("gui.main_decks.save_settings"):
            for state, nxt in ((0, 1), (1, 2), (2, 3), (3, 0)):
                w = self.win(state)
                DeckLayoutMixin._cycle_compact(w)
                self.assertEqual(w._compact_state, nxt)
                w._warmup_table.set_grouping.assert_called_once_with(nxt)

    def test_numbers_caption(self):
        with mock.patch("gui.main_decks.save_settings"):
            w = self.win(2)
            DeckLayoutMixin._cycle_compact(w)
        self.assertIn("Numbers", w._set_toolbar_btn_text.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
