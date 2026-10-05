#!/usr/bin/env python3
"""Tests for the 📅 tournament-day planner's planner-side pieces:
rounds_from_pattern(), PlaylistSuggester.suggest(exclude=…) and the
deck-stacking helpers merge_day_playlists() / split_day_rounds().

Run:  py -m unittest tests.planner.test_day_plan -v

The library is built by hand (paths under lateincd/ so the Latin style filter
passes); no files are read, use_timbre stays off.
"""

import unittest
from pathlib import Path

from dancesport_planner import (
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    merge_day_playlists,
    rounds_from_pattern,
    split_day_rounds,
)


class RoundsFromPatternTest(unittest.TestCase):
    def test_standard_pattern(self):
        cfgs = rounds_from_pattern("6-3-2-1")
        self.assertEqual([rc.heats for rc in cfgs], [6, 3, 2, 1])
        self.assertEqual([rc.tier for rc in cfgs],
                         ["early", "pre_semi", "semi", "final"])
        self.assertEqual([rc.prefer_fresh for rc in cfgs],
                         [False, True, False, False])

    def test_comma_and_space_separators(self):
        self.assertEqual([rc.heats for rc in rounds_from_pattern("6, 3 2")],
                         [6, 3, 2])

    def test_invalid_patterns_give_empty_list(self):
        for raw in ("", "abc", "0-1", "31", None):
            self.assertEqual(rounds_from_pattern(raw or ""), [], raw)

    def test_trailing_separators_are_ignored(self):
        # matches the old GUI parser: empty parts are dropped, not an error
        self.assertEqual([rc.heats for rc in rounds_from_pattern("6-3-")], [6, 3])


def _entry(name: str, dance: str) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\{dance}\{name}.mp3"),
        title=name, dance=dance, bpm=None, popularity=3)


class SuggestExcludeTest(unittest.TestCase):
    def _lib(self, entries) -> MusicLibrary:
        lib = MusicLibrary()
        lib.entries.extend(entries)
        return lib

    def test_excluded_paths_never_picked(self):
        e1 = _entry("Cha One (CC 30)", "CC")
        e2 = _entry("Cha Two (CC 30)", "CC")
        e3 = _entry("Cha Three (CC 30)", "CC")
        lib = self._lib([e1, e2, e3])
        rounds = rounds_from_pattern("1")
        exclude = {str(e1.path), str(e2.path)}
        playlist = PlaylistSuggester(lib).suggest(
            "S", rounds, ["CC"], use_timbre=False, style="Latin",
            exclude=exclude)
        picks = [e for heats in playlist.values()
                 for heat in heats for e in heat if e is not None]
        self.assertEqual([str(p.path) for p in picks], [str(e3.path)])

    def test_paso_doble_is_exempt(self):
        p1 = _entry("Espana (PD 60)", "PD")
        p2 = _entry("Malaguena (PD 60)", "PD")
        lib = self._lib([p1, p2])
        rounds = rounds_from_pattern("1")
        exclude = {str(p1.path), str(p2.path)}   # "already played" — PD may repeat
        playlist = PlaylistSuggester(lib).suggest(
            "S", rounds, ["PD"], use_timbre=False, style="Latin",
            exclude=exclude)
        picks = [e for heats in playlist.values()
                 for heat in heats for e in heat if e is not None]
        self.assertEqual(len(picks), 1)   # slot still fills despite the exclusion


def _comp(label, dances, entries_by_round, cls="S", style="Latin", pattern="1"):
    """A generated-competition dict as _plan_tournament_day builds them.
    entries_by_round: {round_name: [[entry per dance] per heat]}."""
    return {"label": label, "playlist": entries_by_round, "dances": dances,
            "rounds": rounds_from_pattern(pattern), "cls": cls, "style": style}


class MergeDayPlaylistsTest(unittest.TestCase):
    def test_union_columns_and_prefixed_rounds(self):
        cc = _entry("Cha One (CC 30)", "CC")
        lw = MusicEntry(path=Path(r"C:\music\tanzcds\standardcd\lw\Waltz.mp3"),
                        title="Waltz", dance="LW")
        c1 = _comp("HGR · S · Latin", ["CC"], {"Finale": [[cc]]})
        c2 = _comp("HGR · D · Standard", ["LW"], {"Finale": [[lw]]},
                   cls="D", style="Standard")
        merged, union, rounds, skip, ctx = merge_day_playlists([c1, c2])

        self.assertEqual(union, ["CC", "LW"])
        names = [rc.name for rc in rounds]
        self.assertEqual(names, ["HGR · S · Latin — Finale",
                                 "HGR · D · Standard — Finale"])
        # Slots land on the union index; foreign columns stay None and are skipped.
        self.assertEqual(merged[names[0]], [[cc, None]])
        self.assertEqual(merged[names[1]], [[None, lw]])
        self.assertEqual(skip[names[0]], {"LW"})
        self.assertEqual(skip[names[1]], {"CC"})
        self.assertEqual(ctx[names[1]],
                         {"comp": "HGR · D · Standard", "cls": "D",
                          "style": "Standard"})

    def test_shared_dances_share_columns(self):
        a = _entry("Cha A (CC 30)", "CC")
        b = _entry("Cha B (CC 30)", "CC")
        c1 = _comp("HGR · S · Latin", ["CC"], {"Finale": [[a]]})
        c2 = _comp("HGR · A · Latin", ["CC"], {"Finale": [[b]]}, cls="A")
        merged, union, rounds, skip, _ = merge_day_playlists([c1, c2])
        self.assertEqual(union, ["CC"])
        self.assertEqual(skip, {})   # nothing to hide — both use every column

    def test_identical_labels_get_numbered(self):
        a = _entry("Cha A (CC 30)", "CC")
        c1 = _comp("HGR · S · Latin", ["CC"], {"Finale": [[a]]})
        c2 = _comp("HGR · S · Latin", ["CC"], {"Finale": [[a]]})
        merged, _, rounds, _, ctx = merge_day_playlists([c1, c2])
        names = [rc.name for rc in rounds]
        self.assertEqual(names, ["HGR · S · Latin — Finale",
                                 "HGR · S · Latin (2) — Finale"])
        self.assertEqual(ctx[names[1]]["comp"], "HGR · S · Latin (2)")


class SplitDayRoundsTest(unittest.TestCase):
    _DANCES = ["CC", "LW"]
    _ROUNDS = [
        {"name": "HGR · S · Latin — Finale", "tier": "final", "heats": 1,
         "grid": {"0": {"0": r"C:\m\cha.mp3"}}, "skip_dances": ["LW"],
         "ctx": {"comp": "HGR · S · Latin", "cls": "S", "style": "Latin"}},
        {"name": "HGR · D · Standard — Finale", "tier": "final", "heats": 1,
         "grid": {"0": {"1": r"C:\m\waltz.mp3"}}, "skip_dances": ["CC"],
         "ctx": {"comp": "HGR · D · Standard", "cls": "D", "style": "Standard"}},
    ]

    def test_split_regroups_per_competition(self):
        groups = split_day_rounds(self._ROUNDS, self._DANCES)
        self.assertEqual(len(groups), 2)
        latin, std = groups
        self.assertEqual(latin["comp"], "HGR · S · Latin")
        self.assertEqual(latin["dances"], ["CC"])
        # Round name back to plain, grid re-indexed into the comp's own columns.
        self.assertEqual(latin["rounds"][0]["name"], "Finale")
        self.assertEqual(latin["rounds"][0]["grid"], {"0": {"0": r"C:\m\cha.mp3"}})
        self.assertEqual(std["cls"], "D")
        self.assertEqual(std["dances"], ["LW"])
        self.assertEqual(std["rounds"][0]["grid"], {"0": {"0": r"C:\m\waltz.mp3"}})

    def test_single_competition_deck_is_left_alone(self):
        plain = [{"name": "Finale", "tier": "final", "heats": 1,
                  "grid": {"0": {"0": r"C:\m\cha.mp3"}}}]
        self.assertEqual(split_day_rounds(plain, ["CC"]), [])
        self.assertEqual(split_day_rounds(self._ROUNDS[:1], self._DANCES), [])


if __name__ == "__main__":
    unittest.main()
