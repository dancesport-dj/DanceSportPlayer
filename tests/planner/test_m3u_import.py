"""Tests for planner.m3u: export → import round-trip of the structured grid,
the marker-less heuristic import (round-robin / grouped layouts, trailing
backup variants) and the round-name → tier mapping."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner.m3u import (_round_tiers, _tier_for_round_name, export_m3u,
                         grid_from_running_order, import_playlist_m3u,
                         m3u_marker_rounds, m3u_marker_rounds_in_order,
                         running_order_rounds)
from planner.models import MusicEntry


def _e(name, dance, bpm=None, duration=120):
    return MusicEntry(path=Path(rf"C:\music\{name}.mp3"), title=name,
                      dance=dance, bpm=bpm, duration=duration)


def _lib(*entries):
    """Minimal stand-in for MusicLibrary: import only needs `.entries` for path
    resolution (make_external_entry is never hit — the paths don't exist)."""
    return SimpleNamespace(entries=list(entries))


def _write_m3u(lines) -> Path:
    p = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "test.m3u"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class TierForRoundNameTest(unittest.TestCase):

    def test_mappings(self):
        self.assertEqual(_tier_for_round_name("Finale"), "final")
        self.assertEqual(_tier_for_round_name("Semifinale"), "semi")
        self.assertEqual(_tier_for_round_name("Halbfinale"), "semi")
        self.assertEqual(_tier_for_round_name("Viertelfinale"), "early")
        self.assertEqual(_tier_for_round_name("Vorrunde"), "early")
        self.assertEqual(_tier_for_round_name("1. Zwischenrunde"), "early")


class RoundTiersTest(unittest.TestCase):
    """Tiers of an IMPORTED playlist are counted back from the final, exactly as
    `rounds_from_pattern` counts them for a typed '6-3-2-1'."""

    def test_the_round_before_the_final_is_the_semifinal(self):
        """Read off the names alone there was no semifinal in a three-round
        import: 'Zwischenrunde' says nothing, so it came in as an early round."""
        self.assertEqual(_round_tiers(["Vorrunde", "Zwischenrunde", "Finale"]),
                         ["pre_semi", "semi", "final"])

    def test_the_ladder_reaches_back_four_rounds(self):
        self.assertEqual(
            _round_tiers(["Vorrunde", "1. Zwischenrunde", "2. Zwischenrunde",
                          "3. Zwischenrunde", "Semifinale", "Finale"]),
            ["early", "early", "early", "pre_semi", "semi", "final"])

    def test_a_name_that_says_which_round_it_is_wins(self):
        """A file whose rounds are named out of position keeps its own word for
        it — a Viertelfinale is an early round wherever it stands."""
        self.assertEqual(_round_tiers(["Achtelfinale", "Viertelfinale", "Finale"]),
                         ["early", "early", "final"])

    def test_nameless_rounds_still_get_the_ladder(self):
        self.assertEqual(_round_tiers(["Runde 1", "Runde 2", "Runde 3"]),
                         ["pre_semi", "semi", "final"])

    def test_a_single_round_is_the_final(self):
        self.assertEqual(_round_tiers(["Finale"]), ["final"])


class StructuredRoundTripTest(unittest.TestCase):
    """A grid exported by export_m3u re-imports to the identical grid."""

    def setUp(self):
        self.lw = [_e(f"lw30 - Waltz {i}", "LW", bpm=30) for i in range(3)]
        self.tg = [_e(f"tg33 - Tango {i}", "TG", bpm=33) for i in range(2)]
        self.playlist = {
            "Vorrunde": [[self.lw[0], self.tg[0]], [self.lw[1], self.tg[1]]],
            "Finale": [[self.lw[2], None]],   # TG final slot left unfilled
        }
        out = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "roundtrip.m3u"
        export_m3u(self.playlist, ["LW", "TG"], "roundtrip", dance_class="S",
                   out_path=out)
        self.res = import_playlist_m3u(out, _lib(*self.lw, *self.tg), None)

    def test_structure_detected(self):
        self.assertTrue(self.res["structured"])
        self.assertEqual(self.res["dances"], ["LW", "TG"])
        self.assertEqual([r.name for r in self.res["rounds"]],
                         ["Vorrunde", "Finale"])
        self.assertEqual([r.tier for r in self.res["rounds"]],
                         ["semi", "final"])   # the round before the final

    def test_grid_identical(self):
        def paths(pl):
            return {rn: [[e.path if e else None for e in h] for h in heats]
                    for rn, heats in pl.items()}
        self.assertEqual(paths(self.res["playlist"]), paths(self.playlist))

    def test_counts(self):
        self.assertEqual(self.res["missing"], 0)
        self.assertEqual(self.res["unknown"], 0)
        self.assertEqual(self.res["total"], 5)

    def test_library_entries_are_reused(self):
        self.assertIs(self.res["playlist"]["Vorrunde"][0][0], self.lw[0])

    def test_vanished_file_becomes_ghost_with_detected_dance(self):
        out = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "ghost.m3u"
        export_m3u({"Finale": [[self.lw[0]]]}, ["LW"], "ghost", out_path=out)
        res = import_playlist_m3u(out, _lib(), None)   # library doesn't know it
        self.assertEqual(res["missing"], 1)
        ghost = res["playlist"]["Finale"][0][0]
        self.assertEqual(ghost.path, self.lw[0].path)
        self.assertEqual(ghost.dance, "LW")


class HeuristicImportTest(unittest.TestCase):
    """Marker-less M3Us: dances from filenames, rounds from dance-set passes."""

    @staticmethod
    def _import(names):
        lines = ["#EXTM3U"]
        for n in names:
            lines += [f"#EXTINF:120,{n}", rf"C:\music\{n}.mp3"]
        return import_playlist_m3u(_write_m3u(lines), _lib(), None)

    def test_round_robin_passes_become_rounds(self):
        res = self._import(["lw30 - Waltz A", "tg33 - Tango A",
                            "lw30 - Waltz B", "tg33 - Tango B"])
        self.assertFalse(res["structured"])
        self.assertEqual(res["dances"], ["LW", "TG"])
        self.assertEqual([r.name for r in res["rounds"]],
                         ["Vorrunde", "Finale"])
        self.assertEqual([len(h) for h in res["playlist"].values()], [1, 1])

    def test_grouped_blocks_become_heats(self):
        # One pass with two songs per dance block → a single 2-heat round.
        res = self._import(["lw30 - Waltz A", "lw30 - Waltz B",
                            "tg33 - Tango A", "tg33 - Tango B"])
        self.assertEqual([r.name for r in res["rounds"]], ["Finale"])
        self.assertEqual(len(res["playlist"]["Finale"]), 2)

    def test_trailing_extra_song_becomes_backup(self):
        # A lone extra Tango after the final is an alternative, not a new round
        # and not an empty-celled second heat.
        res = self._import(["lw30 - Waltz A", "tg33 - Tango A",
                            "lw30 - Waltz B", "tg33 - Tango B",
                            "tg33 - Tango C"])
        self.assertEqual([r.name for r in res["rounds"]],
                         ["Vorrunde", "Finale"])
        self.assertEqual(len(res["playlist"]["Finale"]), 1)
        (slot, extras), = res["backups"].items()
        self.assertEqual(slot, ("Finale", 0, 1))   # under the last TG heat
        self.assertEqual([e.title for e in extras], ["tg33 - Tango C"])
        self.assertEqual(res["total"], 5)   # 4 grid slots + 1 backup


class ImportAccountingTest(unittest.TestCase):
    """Where the tracks the file listed ended up.

    The import dialog counts every path line while it works, then reports the
    songs the grid holds — and an operator watching 500 go by and reading 282
    afterwards has no way of knowing whether the rest were duplicates, lines the
    reader choked on, or tracks quietly left out. So the result carries the
    file's own count and the two ways a track can fail to reach the grid."""

    @staticmethod
    def _import(names, paths=None):
        lines = ["#EXTM3U"]
        for i, n in enumerate(names):
            path = paths[i] if paths else rf"C:\music\{n}.mp3"
            lines += [f"#EXTINF:120,{n}", path]
        return import_playlist_m3u(_write_m3u(lines), _lib(), None)

    def test_a_clean_list_imports_every_track_it_lists(self):
        res = self._import(["lw30 - Waltz A", "tg33 - Tango A",
                            "lw30 - Waltz B", "tg33 - Tango B"])
        self.assertEqual(res["raw"], 4)
        self.assertEqual(res["total"], 4)
        self.assertEqual(res["dupes"], 0)
        self.assertEqual(res["dropped"], 0)

    def test_a_file_listed_twice_is_counted_as_a_duplicate(self):
        """UltraMixer exports and merged lists repeat paths; the tracks still
        come in, but the file listed more than it holds and says so."""
        names = ["lw30 - Waltz A", "tg33 - Tango A",
                 "lw30 - Waltz A", "tg33 - Tango A"]
        res = self._import(names)
        self.assertEqual(res["raw"], 4)
        self.assertEqual(res["dupes"], 2)

    def test_the_same_path_written_differently_is_still_a_duplicate(self):
        res = self._import(["lw30 - Waltz A", "lw30 - Waltz A"],
                           paths=[r"C:\music\lw30 - Waltz A.mp3",
                                  r'"C:\MUSIC\LW30 - WALTZ A.mp3"'])
        self.assertEqual(res["dupes"], 1)

    def test_a_track_of_no_known_dance_is_missing_from_the_grid_not_the_count(self):
        res = self._import(["lw30 - Waltz A", "tg33 - Tango A",
                            "Some Party Song", "lw30 - Waltz B",
                            "tg33 - Tango B"])
        self.assertEqual(res["raw"], 5)
        self.assertEqual(res["unknown"], 1)
        self.assertEqual(res["dropped"], 0)
        self.assertEqual(res["raw"] - res["unknown"], res["total"])

    def test_the_numbers_add_up(self):
        """raw - unknown - dropped == total, whichever way a track fell out."""
        for names in (["lw30 - Waltz A", "tg33 - Tango A"],
                      ["lw30 - Waltz A", "Party", "tg33 - Tango A",
                       "lw30 - Waltz B", "tg33 - Tango B", "tg33 - Tango C"],
                      ["Party A", "Party B", "lw30 - Waltz A"]):
            with self.subTest(names=names):
                res = self._import(names)
                self.assertEqual(
                    res["raw"] - res["unknown"] - res["dropped"], res["total"])

    def test_an_exported_grid_accounts_for_itself_too(self):
        lw = [_e(f"lw30 - Waltz {i}", "LW", bpm=30) for i in range(2)]
        out = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "acct.m3u"
        export_m3u({"Vorrunde": [[lw[0]]], "Finale": [[lw[1]]]}, ["LW"], "acct",
                   out_path=out)
        res = import_playlist_m3u(out, _lib(*lw), None)
        self.assertTrue(res["structured"])
        self.assertEqual(res["raw"], 2)
        self.assertEqual(res["total"], 2)
        self.assertEqual(res["dropped"], 0)


class RunningOrderRoundsTest(unittest.TestCase):
    """The rounds behind a FLAT running order — what heads the ─── strips of a
    player-only install. The order is only cut, never regrouped: it is the list
    the evening is played from."""

    def rounds(self, *dances):
        return running_order_rounds([_e(f"{d} {i}", d)
                                     for i, d in enumerate(dances)])

    def test_a_round_robin_order_is_cut_into_named_rounds(self):
        got = self.rounds("LW", "TG", "LW", "TG")
        self.assertEqual([n for n, _ in got], ["Vorrunde", "Finale"])
        self.assertEqual([[e.title for e in seg] for _, seg in got],
                         [["LW 0", "TG 1"], ["LW 2", "TG 3"]])

    def test_a_grouped_order_is_cut_the_same_way(self):
        """Each round listing all its heats of a dance in one block."""
        got = self.rounds("LW", "LW", "TG", "TG", "LW", "TG")
        self.assertEqual([n for n, _ in got], ["Vorrunde", "Finale"])
        self.assertEqual([len(seg) for _, seg in got], [4, 2])

    def test_three_passes_get_the_three_round_names(self):
        self.assertEqual([n for n, _ in self.rounds("LW", "TG", "LW", "TG",
                                                    "LW", "TG")],
                         ["Vorrunde", "Zwischenrunde", "Finale"])

    def test_a_single_pass_names_nothing(self):
        """One round over the whole list says nothing a strip could show."""
        self.assertEqual(self.rounds("LW", "TG", "WW"), [])

    def test_an_evening_of_passes_is_read_as_a_warm_up_list(self):
        """More passes than a tournament has rounds — that is no draw but a
        warm-up or a party list, and it is cut into the rounds those are built
        from instead of being left nameless."""
        got = self.rounds(*(["LW", "TG"] * 8))
        self.assertEqual([n for n, _ in got],
                         [f"Standardrunde {n}" for n in range(1, 9)])
        self.assertEqual([[e.title for e in seg] for _, seg in got][0],
                         ["LW 0", "TG 1"])

    def test_a_warm_up_list_alternates_its_sections(self):
        """Standard and Latin rounds take turns, each numbered in its own
        section — what the 🤸 panel has always shown."""
        got = self.rounds(*(["LW", "TG", "CC", "SA"] * 8))
        self.assertEqual([n for n, _ in got][:6],
                         ["Standardrunde 1", "Lateinrunde 1",
                          "Standardrunde 2", "Lateinrunde 2",
                          "Standardrunde 3", "Lateinrunde 3"])

    def test_asked_for_a_competition_only_a_warm_up_list_names_nothing(self):
        """The 🤸 panel has its own warm-up cut and only wants to know whether
        the file is a competition running order instead."""
        entries = [_e(f"{d} {i}", d)
                   for i, d in enumerate(["LW", "TG"] * 8)]
        self.assertEqual(running_order_rounds(entries, warmup=False), [])


class GridFromRunningOrderTest(unittest.TestCase):
    """A flat running order read back into a round/heat grid — the way out of a
    deck's free order. Nothing is re-sorted: the songs, their order and the
    rounds they are shown in are what the grid is built from."""

    def order(self, *dances):
        return [_e(f"{d} {i}", d) for i, d in enumerate(dances)]

    def test_the_rounds_it_is_told_are_the_rounds_it_builds(self):
        res = grid_from_running_order(
            self.order("LW", "TG", "LW", "TG"),
            ["Vorrunde", "Vorrunde", "Endrunde", "Endrunde"])
        self.assertEqual([r.name for r in res["rounds"]], ["Vorrunde", "Endrunde"])
        self.assertEqual([e.title for e in res["playlist"]["Endrunde"][0]],
                         ["LW 2", "TG 3"])

    def test_without_names_the_rounds_are_worked_out(self):
        """Same heuristic as importing a marker-less .m3u."""
        res = grid_from_running_order(self.order("LW", "TG", "LW", "TG"))
        self.assertEqual([r.name for r in res["rounds"]], ["Vorrunde", "Finale"])

    def test_a_round_that_comes_back_is_kept_apart(self):
        """Two stretches called the same thing are two rounds, not one — a dict
        key would have quietly swallowed the first."""
        res = grid_from_running_order(
            self.order("LW", "TG", "LW"), ["Vorrunde", "Finale", "Vorrunde"])
        self.assertEqual([r.name for r in res["rounds"]],
                         ["Vorrunde", "Finale", "Vorrunde (2)"])

    def test_a_track_of_no_known_dance_is_counted_not_hidden(self):
        entries = self.order("LW", "TG")
        entries.append(MusicEntry(path=Path(r"C:\music\x.mp3"), title="x"))
        res = grid_from_running_order(entries)
        self.assertEqual(res["unknown"], 1)
        self.assertEqual(res["total"], 2)

    def test_an_evening_of_passes_names_its_warm_up_rounds(self):
        """'Runde 1…16' said nothing the deck could use; the rounds an Eintanzen
        list was actually built from do."""
        res = grid_from_running_order(self.order(*(["LW", "TG", "CC", "SA"] * 8)))
        self.assertEqual([r.name for r in res["rounds"]][:4],
                         ["Standardrunde 1", "Lateinrunde 1",
                          "Standardrunde 2", "Lateinrunde 2"])
        self.assertEqual([e.title for e in res["playlist"]["Standardrunde 1"][0]
                          if e is not None], ["LW 0", "TG 1"])
        self.assertEqual(res["total"], 32)   # every track keeps its place

    def test_a_list_of_nothing_danceable_builds_no_grid(self):
        res = grid_from_running_order(
            [MusicEntry(path=Path(r"C:\music\x.mp3"), title="x")])
        self.assertEqual(res["dances"], [])
        self.assertEqual(res["total"], 0)


class MarkerRoundsTest(unittest.TestCase):
    """Rounds read straight from the markers this app writes into its exports —
    exact names ('Endrunde', not a guessed 'Finale') and exact boundaries."""

    def test_every_track_gets_the_round_it_was_exported_under(self):
        lw = [_e(f"lw30 - Waltz {i}", "LW", bpm=30) for i in range(2)]
        out = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "marked.m3u"
        export_m3u({"Vorrunde": [[lw[0]]], "Endrunde": [[lw[1]]]}, ["LW"],
                   "marked", dance_class="S", out_path=out)
        self.assertEqual(m3u_marker_rounds(out),
                         {str(lw[0].path).lower(): "Vorrunde",
                          str(lw[1].path).lower(): "Endrunde"})

    def test_the_ordered_reading_keeps_a_track_played_twice(self):
        """A paso doble played again in the final is two lines in the file, and
        each line has its own round — which a path→round map cannot say."""
        lw = _e("lw30 - Waltz", "LW", bpm=30)
        out = Path(tempfile.mkdtemp(prefix="dp_m3u_")) / "twice.m3u"
        export_m3u({"Vorrunde": [[lw]], "Finale": [[lw]]}, ["LW"], "twice",
                   dance_class="S", out_path=out)
        self.assertEqual([name for _p, name in m3u_marker_rounds_in_order(out)],
                         ["Vorrunde", "Finale"])
        self.assertEqual(m3u_marker_rounds(out),
                         {str(lw.path).lower(): "Vorrunde"})   # first one wins

    def test_a_plain_m3u_carries_none(self):
        p = _write_m3u(["#EXTM3U", r"C:\music\lw30 - Waltz.mp3"])
        self.assertEqual(m3u_marker_rounds(p), {})

    def test_an_unreadable_file_carries_none(self):
        self.assertEqual(m3u_marker_rounds(Path("nope") / "gone.m3u"), {})


if __name__ == "__main__":
    unittest.main()
