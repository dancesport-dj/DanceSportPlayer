#!/usr/bin/env python3
r"""The two walks that still read a Row like the dict it used to be.

Run:  .venv\Scripts\python.exe -m unittest test_row_access -v

A deck's rows became `Row` objects (gui.running_order); everything that used to
say `m['h_idx']` had to become `m.h_idx`. Two walks were missed, and both only
run on a shape that is rare in testing and normal at a tournament: a round that
dances more than one dance, and a final with a stacked spare under a slot. The
print sheet raised `TypeError: 'Row' object is not subscriptable`, and saving
the desk state would have done the same.
"""
import unittest
from pathlib import Path
from types import SimpleNamespace

from gui.main_persist import PersistenceMixin
from gui.main_print import PrintMixin
from gui.print_sheet import deck_print_html
from gui.running_order import Row, RunningOrder


def _entry(name, bpm=58):
    return SimpleNamespace(path=Path(rf"C:\music\standardcd\{name}.mp3"),
                           title=name, bpm=bpm, duration=180,
                           tag_artist="Artist", tag_album="Album")


class PrintHeatLabelTest(unittest.TestCase):
    """🖨 The Heat column: the row's own heat number, or which spare it is."""

    @staticmethod
    def _html(*rows):
        return "".join(deck_print_html("Deck A", list(rows)))

    def test_a_multi_dance_round_numbers_its_heats(self):
        html = self._html(Row(entry=_entry("Alpha"), dance="LW",
                              round_name="Vorrunde", h_idx=2, multi=True))
        self.assertIn("<td>Heat 3</td>", html)

    def test_a_single_dance_round_leaves_the_heat_column_empty(self):
        html = self._html(Row(entry=_entry("Bravo"), dance="LW",
                              round_name="Vorrunde", h_idx=2))
        self.assertIn("<td></td>", html)
        self.assertNotIn("Heat 3", html)   # "Heat" alone is the column header

    def test_a_stacked_spare_says_which_spare_it_is(self):
        html = self._html(Row(entry=_entry("Charlie"), dance="LW",
                              round_name="Finale", backup=True, backup_n=2))
        self.assertIn("↳ backup 2", html)

    def test_a_spare_without_a_number_still_prints(self):
        """backup_n defaults to 0 — the label drops the number rather than
        printing 'backup 0'."""
        html = self._html(Row(entry=_entry("Delta"), dance="LW",
                              round_name="Finale", backup=True))
        self.assertIn("<td>↳ backup</td>", html)


class PrintDroppedFilesTest(unittest.TestCase):
    """🖨 Files dragged into the print dialog print like a deck's rows."""

    def test_a_dropped_playlist_and_a_loose_file_print(self):
        tracks = {"Echo": _entry("Echo"), "Foxtrot": _entry("Foxtrot")}
        win = SimpleNamespace(
            _lib=object(), _cache=object(),
            _external_entry=lambda p: tracks.get(Path(p).stem),
            _m3u_track_paths=lambda p: [Path("Echo.mp3")])
        decks = PrintMixin._dropped_print_decks(
            win, [Path("Abend.m3u"), Path("Foxtrot.mp3")])
        self.assertEqual([n for n, _ in decks], ["Abend", "Dropped files"])
        html = "".join(part for name, metas in decks
                       for part in deck_print_html(name, metas))
        self.assertIn("<td>Echo</td>", html)
        self.assertIn("<td>Foxtrot</td>", html)


class SerializeBackupsTest(unittest.TestCase):
    """💾 Save state: the spares stacked under a final's slots."""

    @staticmethod
    def _state(*rows):
        table = SimpleNamespace(
            _row_meta=RunningOrder(rows),
            _player_list=False,
            _dynamic=False,
            _dynamic_dances=[],
            _dynamic_capacity=[],
            _use_timbre=False,
            _marked_paths=set(),
            _round_ctx={},
            _round_skip_dances={},
        )
        win = SimpleNamespace(_deck_meta=lambda t: {
            "mode": "Favorites", "ui_mode": "Favorites", "style": "Standard",
            "dance_class": "D", "age": "Hgr", "theme_label": ""})
        return PersistenceMixin._serialize_playlist_state(win, table)

    def test_a_spare_is_keyed_by_the_slot_it_sits_under(self):
        heat = Row(entry=_entry("Alpha"), dance="LW", round_name="Finale",
                   h_idx=1, d_idx=3)
        spare = Row(entry=_entry("Bravo"), dance="LW", round_name="Finale",
                    h_idx=1, d_idx=3, backup=True, backup_n=1)
        state = self._state(heat, spare)
        self.assertEqual(state["rounds"][0]["backups"],
                         {"1/3": [str(spare.entry.path)]})

    def test_a_final_without_spares_carries_no_backups_key(self):
        state = self._state(Row(entry=_entry("Alpha"), dance="LW",
                                round_name="Finale"))
        self.assertNotIn("backups", state["rounds"][0])


if __name__ == "__main__":
    unittest.main()
