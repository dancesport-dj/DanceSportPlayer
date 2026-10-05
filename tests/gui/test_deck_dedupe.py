#!/usr/bin/env python3
"""Tests for 🧹 clearing a deck of what the other OPEN playlists already plan.

Run:  py -m unittest tests.gui.test_deck_dedupe -v

An evening is one thing to the people in the hall, so a title that ran in the
last competition should not come round again in the next. Which playlists that
is measured against is what is on screen: two decks in view means the other
one, eight means the other seven.

Only the deck the menu was opened on may lose tracks — reading the others and
writing to them are very different things when the operator is one right-click
away from an hour of work.
"""
import os
import tempfile
import unittest
from pathlib import Path

from gui.deck import Deck
from gui.running_order import Row, RunningOrder
from planner.models import MusicEntry


def _dupes_module():
    """gui.main_dupes resolves the state files at import time — keep the import
    at TEST time (see test_heat_tempo.py)."""
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_dedup_"))
    import gui.main_dupes as md
    return md


def _e(name, dance="LW"):
    return MusicEntry(path=Path(rf"C:\music\{name}.mp3"), title=name, dance=dance)


class _Table:
    """A deck reduced to what the clean reads — and to what it writes, which is
    the point of the test: `cleared` stays None on a deck nobody may touch."""

    _flat_mode = False

    def __init__(self, entries, confirm=True):
        self._row_meta = RunningOrder(
            [Row(entry=e, dance=(e.dance or "")) for e in entries])
        self._confirm = confirm
        self.asked = None
        self.cleared = None

    def _confirm_delete(self, title, text):
        self.asked = text
        return self._confirm

    def _clear_slots_at(self, rows):
        self.cleared = sorted(rows)
        return bool(rows)


class DeckCleanTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        md = _dupes_module()
        cls.md = md

        class Win(md.DuplicateCheckMixin):
            _cache = None

            def __init__(self, tables):
                self._tables = list(tables)

            def _visible_deck_tables(self):
                return self._tables

            def deck(self, table):
                return Deck(table, name=f"Playlist {self._tables.index(table) + 1}")

        cls.Win = Win

    def setUp(self):
        self.toasts = []
        real = self.md._show_toast
        self.md._show_toast = lambda _w, text, **kw: self.toasts.append(text)
        self.addCleanup(setattr, self.md, "_show_toast", real)

    def _win(self, *tables):
        return self.Win(tables)

    def test_a_title_the_other_playlist_has_is_cleared_from_this_one(self):
        a = _Table([_e("Waltz A"), _e("Waltz B")])
        b = _Table([_e("Waltz B")])
        n = self._win(a, b)._clean_deck_against_others(a)
        self.assertEqual(n, 1)
        self.assertEqual(a.cleared, [1])

    def test_the_other_playlist_is_read_not_touched(self):
        a = _Table([_e("Waltz B")])
        b = _Table([_e("Waltz B")])
        self._win(a, b)._clean_deck_against_others(a)
        self.assertEqual(a.cleared, [0])
        self.assertIsNone(b.cleared, "the deck that was only compared lost rows")

    def test_a_list_of_its_own_titles_keeps_all_of_them(self):
        a = _Table([_e("Waltz A")])
        b = _Table([_e("Waltz C")])
        self.assertEqual(self._win(a, b)._clean_deck_against_others(a), 0)
        self.assertIsNone(a.cleared)
        self.assertIsNone(a.asked, "asked to confirm a removal of nothing")
        self.assertTrue(any("Nothing here" in t for t in self.toasts))

    def test_the_only_playlist_open_has_nothing_to_compare_against(self):
        a = _Table([_e("Waltz A")])
        self.assertEqual(self._win(a)._clean_deck_against_others(a), 0)
        self.assertIsNone(a.cleared)
        self.assertTrue(any("No other open playlist" in t for t in self.toasts))

    def test_an_empty_other_deck_does_not_count_as_a_playlist(self):
        a = _Table([_e("Waltz A")])
        self.assertEqual(self._win(a, _Table([]))._clean_deck_against_others(a), 0)
        self.assertTrue(any("No other open playlist" in t for t in self.toasts))

    def test_a_paso_may_come_round_again(self):
        """ALLOW_REPEAT: the Paso is danced twice in an evening by design."""
        a = _Table([_e("Paso A", "PD"), _e("Waltz B")])
        b = _Table([_e("Paso A", "PD"), _e("Waltz B")])
        self.assertEqual(self._win(a, b)._clean_deck_against_others(a), 1)
        self.assertEqual(a.cleared, [1])

    def test_saying_no_removes_nothing(self):
        a = _Table([_e("Waltz B")], confirm=False)
        b = _Table([_e("Waltz B")])
        self.assertEqual(self._win(a, b)._clean_deck_against_others(a), 0)
        self.assertIsNone(a.cleared)
        self.assertIsNotNone(a.asked, "removed without asking")

    def test_the_question_names_the_playlists_it_compared_against(self):
        a = _Table([_e("Waltz B")])
        b = _Table([_e("Waltz B")])
        c = _Table([_e("Waltz C")])
        self._win(a, b, c)._clean_deck_against_others(a)
        self.assertIn("Playlist 2", a.asked)
        self.assertIn("Playlist 3", a.asked)

    def test_one_title_is_asked_about_in_the_singular(self):
        a = _Table([_e("Waltz B")])
        self._win(a, _Table([_e("Waltz B")]))._clean_deck_against_others(a)
        self.assertIn("Remove 1 title from", a.asked)
        self.assertIn("It is already planned in", a.asked)

    def test_several_titles_are_asked_about_in_the_plural(self):
        a = _Table([_e("Waltz B"), _e("Waltz C")])
        b = _Table([_e("Waltz B"), _e("Waltz C")])
        self._win(a, b)._clean_deck_against_others(a)
        self.assertIn("Remove 2 titles from", a.asked)
        self.assertIn("They are already planned in", a.asked)

    def test_the_toast_counts_in_the_same_grammar(self):
        a = _Table([_e("Waltz B")])
        self._win(a, _Table([_e("Waltz B")]))._clean_deck_against_others(a)
        self.assertTrue(any("Removed 1 title already" in t for t in self.toasts),
                        self.toasts)

    def test_eight_decks_open_means_the_other_seven(self):
        decks = [_Table([_e(f"Waltz {i}")]) for i in range(8)]
        target = decks[0]
        target._row_meta.append(Row(entry=_e("Waltz 7"), dance="LW"))
        self.assertEqual(self._win(*decks)._clean_deck_against_others(target), 1)
        self.assertEqual(target.cleared, [1])

    def test_the_same_file_written_differently_is_the_same_track(self):
        """Windows paths: case and separators must not decide this."""
        a = _Table([_e("Waltz B")])
        b = _Table([MusicEntry(path=Path(r"c:/MUSIC/Waltz B.mp3"),
                               title="Waltz B", dance="LW")])
        self.assertEqual(self._win(a, b)._clean_deck_against_others(a), 1)

    def test_a_wishlist_is_not_cleaned_this_way(self):
        """It has its own action, and it is a list of candidates — being in a
        playlist is not the same reason to drop it."""
        a = _Table([_e("Waltz B")])
        a._flat_mode = True
        b = _Table([_e("Waltz B")])
        self.assertEqual(self._win(a, b)._clean_deck_against_others(a), 0)
        self.assertIsNone(a.cleared)


class MenuLabelTest(unittest.TestCase):
    """The action names how many playlists it will measure this deck against,
    and that number decides the grammar."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                             tempfile.mkdtemp(prefix="dp_dedup_"))
        from gui.table_actions import _clean_deck_label
        cls.label = staticmethod(_clean_deck_label)

    def test_a_single_other_playlist_is_not_counted(self):
        self.assertEqual(self.label(1),
                         "🧹  Remove titles the other playlist has")

    def test_more_than_one_is_counted_and_plural(self):
        self.assertEqual(self.label(3),
                         "🧹  Remove titles the other 3 playlists have")

    def test_seven_others_is_the_eight_deck_view(self):
        self.assertIn("other 7 playlists have", self.label(7))


if __name__ == "__main__":
    unittest.main(verbosity=2)
