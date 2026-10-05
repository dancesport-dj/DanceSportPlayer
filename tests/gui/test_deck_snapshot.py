#!/usr/bin/env python3
"""Tests for 💾 a deck's saved form, without a window or a Qt table.

Run:  py -m unittest tests.gui.test_deck_snapshot -v

The snapshot is what autosave, undo and export store for a deck; the grid
rebuild turns its rounds back into {round: [[entry per dance] per heat]}.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

from gui.deck_snapshot import playlist_from_grid, serialize_deck
from gui.running_order import Row

META = {"mode": "Favorites", "ui_mode": "Favorites", "style": "Latin",
        "dance_class": "S", "age": "Hgr", "theme_label": ""}


def entry(name):
    return SimpleNamespace(path=Path(f"C:/m/{name}.mp3"))


def p(name):
    return str(Path(f"C:/m/{name}.mp3"))


def table(rows, **kw):
    t = SimpleNamespace(_row_meta=rows, _marked_paths=set(), _dynamic=False,
                        _dynamic_dances=[], _dynamic_capacity=[],
                        _use_timbre=True)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def grid_rows():
    """Vorrunde, 2 heats × SA/CC, with one empty slot and a header row."""
    return [None,
            Row(entry("s1"), "SA", "Vorrunde", 0, 0, tier="early"),
            Row(entry("c1"), "CC", "Vorrunde", 0, 1, tier="early"),
            Row(entry("s2"), "SA", "Vorrunde", 1, 0, tier="early"),
            Row(None, "CC", "Vorrunde", 1, 1, tier="early")]


class GridTest(unittest.TestCase):

    def test_an_empty_deck_is_nothing_to_save(self):
        self.assertIsNone(serialize_deck(table([None]), META))

    def test_a_grid_saves_its_dances_and_rounds(self):
        state = serialize_deck(table(grid_rows()), META)
        self.assertEqual(state["dances"], ["SA", "CC"])
        (r,) = state["rounds"]
        self.assertEqual((r["name"], r["tier"], r["heats"]), ("Vorrunde", "early", 2))
        self.assertEqual(r["grid"], {"0": {"0": p("s1"), "1": p("c1")},
                                     "1": {"0": p("s2"), "1": None}})
        self.assertEqual((state["style"], state["age"]), ("Latin", "Hgr"))

    def test_the_grid_rebuilds_into_heats_of_entries(self):
        rounds = serialize_deck(table(grid_rows()), META)["rounds"]
        got = playlist_from_grid(rounds, 2, resolve=lambda path: Path(path).stem)
        self.assertEqual(got, {"Vorrunde": [["s1", "c1"], ["s2", None]]})

    def test_the_rebuild_reports_its_progress_per_track(self):
        rounds = serialize_deck(table(grid_rows()), META)["rounds"]
        seen = []
        playlist_from_grid(rounds, 2, resolve=str,
                           progress_cb=lambda done, total, name: seen.append((done, total, name)))
        self.assertEqual(seen, [(1, 3, "s1.mp3"), (2, 3, "c1.mp3"), (3, 3, "s2.mp3")])

    def test_a_dynamic_deck_keeps_its_empty_columns(self):
        t = table(grid_rows(), _dynamic=True, _dynamic_dances=["SA", "CC", "RB"],
                  _dynamic_capacity=[2, 2, 0])
        state = serialize_deck(t, META)
        self.assertEqual(state["dances"], ["SA", "CC", "RB"])
        self.assertEqual(state["dynamic_capacity"], [2, 2, 0])

    def test_backups_and_skipped_dances_ride_on_their_round(self):
        rows = grid_rows() + [Row(entry("b1"), "SA", "Vorrunde", 0, 0, backup=True)]
        t = table(rows, _round_skip_dances={"Vorrunde": {"CC"}, "Gone": {"SA"}})
        (r,) = serialize_deck(t, META)["rounds"]
        self.assertEqual(r["backups"], {"0/0": [p("b1")]})
        self.assertEqual(r["skip_dances"], ["CC"])

    def test_a_day_plan_round_carries_its_competition(self):
        t = table(grid_rows(), _round_ctx={"Vorrunde": {"age": "Sen I"}})
        (r,) = serialize_deck(t, META)["rounds"]
        self.assertEqual(r["ctx"], {"age": "Sen I"})

    def test_only_marks_of_titles_still_on_the_deck_are_saved(self):
        t = table(grid_rows(), _marked_paths={p("s2"), p("gone")})
        self.assertEqual(serialize_deck(t, META)["marked"], [p("s2")])


class ThemeTest(unittest.TestCase):

    def test_a_theme_deck_saves_its_titles_in_order(self):
        rows = [Row(entry("a"), theme=True), None, Row(entry("b"), theme=True)]
        meta = dict(META, mode="Theme", theme_label="Party")
        state = serialize_deck(table(rows), meta)
        self.assertEqual(state["mode"], "Theme")
        self.assertEqual(state["theme_entries"], [p("a"), p("b")])
        self.assertEqual(state["theme_label"], "Party")

    def test_a_theme_deck_without_titles_is_nothing_to_save(self):
        meta = dict(META, mode="Theme")
        self.assertIsNone(serialize_deck(table([Row(None, theme=True)]), meta))


class PlayerListTest(unittest.TestCase):

    def test_a_running_order_saves_as_a_flagged_flat_list(self):
        rows = [Row(entry("a"), "LW", "R1"), Row(entry("b"), "TG", "R1")]
        t = table(rows, _player_list=True, _warmup_label="Abend",
                  _player_sections={p("a"): "R1", p("gone"): "R9"},
                  _marked_paths={p("b")})
        state = serialize_deck(t, META)
        self.assertTrue(state["player_list"])
        self.assertEqual(state["theme_entries"], [p("a"), p("b")])
        self.assertEqual(state["theme_label"], "Abend")
        self.assertEqual(state["player_sections"], {p("a"): "R1"})
        self.assertEqual(state["marked"], [p("b")])

    def test_an_empty_running_order_is_nothing_to_save(self):
        self.assertIsNone(serialize_deck(table([None], _player_list=True), META))


if __name__ == "__main__":
    unittest.main(verbosity=2)
