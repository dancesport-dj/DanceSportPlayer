#!/usr/bin/env python3
"""Tests for the running order a playlist list holds.

Run:  py -m unittest tests.gui.test_running_order -v

A list on the desk is a table of rows of which only some are songs, and the two
readings of it — "the songs, in playing order" and "the table rows holding a
song" — have to stay in step. They used to be written out at every call site,
which is how they drifted apart. Here they are asked once, and this is where
the conventions are pinned down: a header row is a None in the order, an
unfilled grid slot is a Row without a track, and a stacked final-round spare is
in the list but is not a heat of it.

No Qt: the order is plain data, so the rules are tested without a window.
"""
import unittest
from pathlib import Path

from gui.running_order import Row, RunningOrder


def _e(title):
    class E:
        def __init__(self, t):
            self.title = t
            self.path = Path(rf"C:\music\{t}.mp3")
    return E(title)


def _slot(title=None, **kw):
    return Row(entry=_e(title) if title else None, **kw)


class RowTest(unittest.TestCase):
    """What one row says about itself."""

    def test_an_empty_slot_is_a_row_without_a_track(self):
        r = _slot(round_name="Finale", dance="WW", h_idx=1, d_idx=2)
        self.assertFalse(r.filled)
        self.assertEqual(r.path_str, "")
        self.assertEqual(r.slot(), ("Finale", 1, 2))

    def test_a_filled_slot_reports_its_path_as_a_string(self):
        self.assertEqual(_slot("Alpha").path_str, str(Path(r"C:\music\Alpha.mp3")))

    def test_a_spare_keeps_the_slot_and_takes_the_track(self):
        slot = _slot("Alpha", round_name="Finale", dance="WW", h_idx=1, d_idx=2)
        spare = slot.spare(_e("Bravo"), 2)
        self.assertEqual(spare.slot(), slot.slot())
        self.assertEqual(spare.entry.title, "Bravo")
        self.assertTrue(spare.backup)
        self.assertEqual(spare.backup_n, 2)
        self.assertFalse(slot.backup, "the slot it was stacked under is untouched")


class ShapeTest(unittest.TestCase):
    """The sequence a table widget renders — row numbers and all."""

    def setUp(self):
        self.o = RunningOrder([None, _slot("Alpha"), _slot(), _slot("Bravo")])

    def test_it_is_as_long_as_the_table(self):
        self.assertEqual(len(self.o), 4)

    def test_an_empty_order_is_falsy(self):
        self.assertFalse(RunningOrder())
        self.assertTrue(self.o)

    def test_it_compares_equal_to_the_plain_list(self):
        self.assertEqual(RunningOrder([None]), [None])

    def test_rows_can_be_replaced_dropped_and_inserted(self):
        self.o[2] = _slot("Charlie")
        self.assertEqual(self.o.entries()[1].title, "Charlie")
        del self.o[0]
        self.assertEqual(len(self.o), 3)
        self.o.insert(0, None)
        self.assertIsNone(self.o[0])

    def test_clear_empties_it_in_place(self):
        self.o.clear()
        self.assertEqual(len(self.o), 0)


class LookupTest(unittest.TestCase):
    """A row number can outlive the render that produced it."""

    def setUp(self):
        self.o = RunningOrder([None, _slot("Alpha")])

    def test_a_header_row_holds_nothing(self):
        self.assertIsNone(self.o.at(0))
        self.assertIsNone(self.o.entry_at(0))

    def test_a_song_row_holds_its_track(self):
        self.assertEqual(self.o.at(1).entry.title, "Alpha")
        self.assertEqual(self.o.entry_at(1).title, "Alpha")

    def test_a_row_past_the_end_is_not_an_error(self):
        self.assertIsNone(self.o.at(99))
        self.assertIsNone(self.o.at(-1))
        self.assertIsNone(self.o.entry_at(99))


class SongsTest(unittest.TestCase):
    """"The songs" and "the rows they are on" — the pairing that drifted."""

    def setUp(self):
        # header, song, empty slot, song, header, song
        self.o = RunningOrder([None, _slot("Alpha"), _slot(), _slot("Bravo"),
                               None, _slot("Charlie")])

    def test_headers_and_empty_slots_are_not_songs(self):
        self.assertEqual([e.title for e in self.o.entries()],
                         ["Alpha", "Bravo", "Charlie"])
        self.assertEqual(self.o.song_count(), 3)
        self.assertTrue(self.o.has_songs())

    def test_the_rows_run_parallel_to_the_songs(self):
        self.assertEqual(self.o.song_rows(), [1, 3, 5])
        self.assertEqual([r for r, _m in self.o.numbered()], self.o.song_rows())
        self.assertEqual([m.entry for _r, m in self.o.numbered()],
                         self.o.entries())

    def test_a_list_of_nothing_but_headers_holds_no_songs(self):
        empty = RunningOrder([None, _slot(), None])
        self.assertFalse(empty.has_songs())
        self.assertEqual(empty.entries(), [])
        self.assertEqual(empty.song_rows(), [])

    def test_the_paths_are_the_set_a_drop_checks_against(self):
        self.assertEqual(self.o.paths(),
                         {str(Path(rf"C:\music\{t}.mp3"))
                          for t in ("Alpha", "Bravo", "Charlie")})

    def test_an_empty_slot_contributes_no_path(self):
        self.assertNotIn("", RunningOrder([_slot()]).paths())


class BackupTest(unittest.TestCase):
    """A stacked spare is in the list but is not danced."""

    def setUp(self):
        slot = _slot("Alpha", round_name="Finale", dance="WW")
        self.o = RunningOrder([None, slot, slot.spare(_e("Bravo"), 1),
                               _slot("Charlie", round_name="Finale",
                                     dance="TG", theme=False)])

    def test_a_spare_is_a_song_of_the_list(self):
        self.assertEqual([e.title for e in self.o.entries()],
                         ["Alpha", "Bravo", "Charlie"])

    def test_but_not_a_heat_of_it(self):
        self.assertEqual([e.title for e in self.o.heat_entries()],
                         ["Alpha", "Charlie"])

    def test_and_not_a_slot_a_drag_may_drop_into(self):
        self.assertEqual(self.o.heat_rows(), {1, 3})

    def test_a_theme_row_is_no_heat_slot_either(self):
        o = RunningOrder([_slot("Alpha", theme=True), _slot("Bravo")])
        self.assertEqual(o.heat_rows(), {1})


if __name__ == "__main__":
    unittest.main()
