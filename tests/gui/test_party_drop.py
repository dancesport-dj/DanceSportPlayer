"""Tests for dropping wishes into the warm-up / ETDS party list: a normal drop
INSERTS at the cursor gap, Shift REPLACES the title under it — and the gap is
translated past the ─── round headers, not around them."""
import os
import tempfile
import unittest

from PySide6.QtCore import Qt

from gui.running_order import Row, RunningOrder


def _list_mixins():
    # Lazy import (see test_drop_target): these pull in gui.dialogs, which
    # resolves the GUI state files at import time.
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_party_"))
    from gui.table_dnd import TableDragDropMixin
    from gui.table_actions import TableActionsMixin
    return TableDragDropMixin, TableActionsMixin


class _Event:
    def __init__(self, shift=False):
        self._shift = shift

    def modifiers(self):
        return (Qt.KeyboardModifier.ShiftModifier if self._shift
                else Qt.KeyboardModifier.NoModifier)


class _PartyList:
    """A two-round ETDS party list, one ─── header per round:

        0  ───  Standardrunde 1  ───
        1      <LW song>
        2      <TG song>
        3  ───  Lateinrunde 1  ───
        4      <SA song>
        5      <CC song>
    """

    def __init__(self):
        def song():
            return Row(dance="LW", entry=object(), warmup=True)
        self._row_meta = RunningOrder(
            [None, song(), song(), None, song(), song()])


class WarmupDropModeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Party(_PartyList, *_list_mixins()):
            pass
        cls.Party = Party

    def setUp(self):
        self.p = self.Party()

    def test_plain_drop_is_an_insert(self):
        self.assertFalse(self.p._warmup_replace_drop(_Event(), 2))

    def test_shift_on_a_song_row_replaces_it(self):
        self.assertTrue(self.p._warmup_replace_drop(_Event(shift=True), 2))

    def test_shift_on_a_round_header_still_inserts(self):
        # A ─── header has no title to overwrite — don't swallow the drop.
        self.assertFalse(self.p._warmup_replace_drop(_Event(shift=True), 3))

    def test_shift_below_the_list_still_inserts(self):
        self.assertFalse(self.p._warmup_replace_drop(_Event(shift=True), 99))


class SongPosAtTest(unittest.TestCase):
    """The gap translation that decides WHERE a wish lands."""

    @classmethod
    def setUpClass(cls):
        class Party(_PartyList, *_list_mixins()):
            pass
        cls.Party = Party

    def setUp(self):
        self.p = self.Party()

    def test_top_of_the_list(self):
        self.assertEqual(self.p._song_pos_at(0), 0)
        self.assertEqual(self.p._song_pos_at(1), 0)   # gap under the 1st header

    def test_between_two_songs_of_a_round(self):
        self.assertEqual(self.p._song_pos_at(2), 1)

    def test_gap_below_a_second_header_skips_it(self):
        # Row 4 is the first song of round 2; two songs precede it. Counting from
        # the first song row instead would say 3 — one off per header passed.
        self.assertEqual(self.p._song_pos_at(4), 2)

    def test_append_at_the_end(self):
        self.assertEqual(self.p._song_pos_at(6), 4)


if __name__ == "__main__":
    unittest.main()
