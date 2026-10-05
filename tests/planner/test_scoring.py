"""Tests for planner.scoring: round-strategy resolution and the class-aware
popularity weighting used for proven-gating and ranking."""
import random
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.scoring import (
    _FINAL_MIN_PLAYS,
    _OTHER_CLASS_CAP,
    _resolve_strategy,
    class_dilutes,
    class_focused,
    class_popularity,
    effective_popularity,
    prefer_late_rounds,
)


def _e(popularity=0, class_plays=None, final_plays=0, semi_plays=0):
    return MusicEntry(path=Path(r"C:\music\lw30 - Song.mp3"), title="Song",
                      dance="LW", popularity=popularity, class_plays=class_plays,
                      final_plays=final_plays, semi_plays=semi_plays)


class ResolveStrategyTest(unittest.TestCase):

    def test_explicit_strategy_wins(self):
        self.assertEqual(_resolve_strategy("final", False, "fresh"), "fresh")
        self.assertEqual(_resolve_strategy("early", True, "all"), "all")

    def test_unknown_strategy_falls_back_to_tier(self):
        self.assertEqual(_resolve_strategy("final", False, "banana"), "top_proven")
        self.assertEqual(_resolve_strategy("final", False, None), "top_proven")
        self.assertEqual(_resolve_strategy("semi", False, None), "proven")

    def test_early_tier_uses_prefer_fresh_flag(self):
        self.assertEqual(_resolve_strategy("early", True, None), "fresh")
        self.assertEqual(_resolve_strategy("early", False, None), "proven")


class PreferLateRoundsTest(unittest.TestCase):
    """A final is picked from what a final has used, a semifinal from what a
    semifinal has used — not from what was played most. The most-played titles
    are usually heat music: a preliminary needs ten per dance, these two need
    one."""

    def setUp(self):
        self.warhorse = _e(popularity=40)                  # never a late round
        self.once = _e(popularity=6, final_plays=1)
        self.finalist = _e(popularity=8, final_plays=_FINAL_MIN_PLAYS)
        self.semifinalist = _e(popularity=7, semi_plays=_FINAL_MIN_PLAYS)
        self.pool = [self.warhorse, self.once, self.finalist, self.semifinalist]

    def test_the_final_keeps_only_the_proven_finalists(self):
        self.assertEqual(prefer_late_rounds(self.pool, "final"), [self.finalist])

    def test_the_semifinal_keeps_only_the_proven_semifinalists(self):
        self.assertEqual(prefer_late_rounds(self.pool, "semi"), [self.semifinalist])

    def test_neither_round_reaches_for_the_others_music_first(self):
        """The semifinal is generated first and `used` blocks a repeat, so a
        semifinal that grabbed the finalists would empty the final's shelf."""
        self.assertNotIn(self.finalist, prefer_late_rounds(self.pool, "semi"))
        self.assertNotIn(self.semifinalist, prefer_late_rounds(self.pool, "final"))

    def test_one_stray_final_is_not_enough_while_a_real_one_is_there(self):
        self.assertNotIn(self.once, prefer_late_rounds(self.pool, "final"))

    def test_a_single_final_still_beats_no_final_at_all(self):
        pool = [self.warhorse, self.once]
        self.assertEqual(prefer_late_rounds(pool, "final"), [self.once])

    def test_a_round_with_no_history_of_its_own_borrows_the_others(self):
        """Better a track chosen for a semifinal than the heat warhorse."""
        pool = [self.warhorse, self.semifinalist]
        self.assertEqual(prefer_late_rounds(pool, "final"), [self.semifinalist])

    def test_no_late_history_anywhere_keeps_the_whole_pool(self):
        """A dance nobody has round history for must not end up blank."""
        pool = [self.warhorse, _e(popularity=12)]
        for tier in ("final", "semi"):
            with self.subTest(tier=tier):
                self.assertEqual(prefer_late_rounds(pool, tier), pool)

    def test_the_earlier_rounds_are_left_alone(self):
        """Taking these titles out of the heats would make every preliminary
        sound like the leftovers — and the heats are where the rest belongs."""
        for tier in ("early", "pre_semi"):
            with self.subTest(tier=tier):
                self.assertEqual(prefer_late_rounds(self.pool, tier), self.pool)


class ClassPopularityTest(unittest.TestCase):

    def test_no_plays_or_no_class_is_zero(self):
        self.assertEqual(class_popularity(_e(popularity=9), "S"), 0)
        self.assertEqual(class_popularity(_e(class_plays={"S": 3}), None), 0)

    def test_counts_only_the_selected_class(self):
        e = _e(class_plays={"S": 3, "D": 8})
        self.assertEqual(class_popularity(e, "S"), 3)
        self.assertEqual(class_popularity(e, "B"), 0)


class EffectivePopularityTest(unittest.TestCase):

    def test_no_class_returns_raw_popularity(self):
        self.assertEqual(effective_popularity(_e(popularity=7), None), 7.0)

    def test_all_same_class_counts_fully(self):
        e = _e(popularity=6, class_plays={"S": 6})
        self.assertAlmostEqual(effective_popularity(e, "S"), 6.0)

    def test_other_class_plays_are_capped(self):
        # 75 D-plays once pushed a zero-S title over the proven threshold
        # (0.1 × 75 = 7.5); their contribution must stay capped.
        e = _e(popularity=75, class_plays={"D": 75})
        eff = effective_popularity(e, "S")
        same_share = (0 + 0.5 * 2.0) / (75 + 2.0)   # no S plays → tiny share
        self.assertAlmostEqual(eff, 0 + 0 * same_share + _OTHER_CLASS_CAP)
        self.assertLess(eff, 5)   # stays below _PROVEN_MIN_POP

    def test_unknown_plays_follow_the_songs_own_class_mix(self):
        # 30×D / 1×S with 57 unclassified plays: the unknowns are ~3% S,
        # so they add ≈3.5 — not ≈28.5 as under a flat 0.5 weight.
        e = _e(popularity=88, class_plays={"D": 30, "S": 1})
        same_share = (1 + 0.5 * 2.0) / (31 + 2.0)
        expected = 1 * 1.0 + 57 * same_share + min(30 * 0.1, _OTHER_CLASS_CAP)
        self.assertAlmostEqual(effective_popularity(e, "S"), expected)

    def test_no_classified_plays_keeps_neutral_half_weight(self):
        e = _e(popularity=10, class_plays={})
        self.assertAlmostEqual(effective_popularity(e, "S"), 5.0)


def _won(lib, cls, title, runs=40):
    """How often `title` fills the single slot of a one-heat CC round."""
    from dancesport_planner import PlaylistSuggester, rounds_from_pattern

    picked = []
    for _ in range(runs):
        playlist = PlaylistSuggester(lib).suggest(
            cls, rounds_from_pattern("1"), ["CC"], use_timbre=False,
            style="Latin")
        picked += [e.title for heats in playlist.values()
                   for heat in heats for e in heat if e is not None]
    return picked.count(title)


class FinalRoundPickTest(unittest.TestCase):
    """The whole point, end to end: the final draws from what a final has used.

    The library's most-played titles are heat music — a preliminary needs ten
    per dance and a final needs one, so play count alone keeps handing the final
    the tracks that never got there."""

    def _cc(self, name, pop, finals, semis=0):
        return MusicEntry(
            path=Path(rf"C:\music\tanzcds\lateincd\CC\{name}.mp3"),
            title=name, dance="CC", bpm=31, popularity=pop,
            class_plays={"S": pop}, final_plays=finals, semi_plays=semis)

    def _lib(self):
        from dancesport_planner import MusicLibrary
        lib = MusicLibrary()
        lib.entries.extend([self._cc("Warhorse", 40, 0),
                            self._cc("Finalist", 8, 3)])
        return lib

    def test_the_final_takes_the_finalist_over_the_warhorse(self):
        random.seed(4)
        self.assertEqual(_won(self._lib(), "S", "Warhorse"), 0)

    def test_the_semifinal_does_not_eat_the_finals_music(self):
        """Two rounds, and the semifinal is dealt first. If it took the finalist
        the final would be left with the warhorse."""
        from dancesport_planner import MusicLibrary, PlaylistSuggester, rounds_from_pattern
        lib = MusicLibrary()
        lib.entries.extend([self._cc("Warhorse", 40, 0),
                            self._cc("Finalist", 8, 3),
                            self._cc("Semifinalist", 6, 0, semis=3)])
        random.seed(4)
        rounds = rounds_from_pattern("1-1")
        playlist = PlaylistSuggester(lib).suggest(
            "S", rounds, ["CC"], use_timbre=False, style="Latin")
        picked = [e.title for heats in playlist.values()
                  for heat in heats for e in heat if e is not None]
        self.assertEqual(picked, ["Semifinalist", "Finalist"])

    def test_a_library_with_no_final_history_still_fills_the_slot(self):
        """Most of the library has no round information at all — the preference
        must never be the reason a slot comes back blank."""
        from dancesport_planner import MusicLibrary
        lib = MusicLibrary()
        lib.entries.extend([self._cc("Warhorse", 40, 0),
                            self._cc("Other", 12, 0)])
        random.seed(4)
        self.assertEqual(_won(lib, "S", "Warhorse"), 40)


class ClassFocusTest(unittest.TestCase):
    """A B/A/S tag was written for the higher rounds; D,C,B,A,S only says the
    track is unrestricted. In a B/A/S event the first one wins."""

    def _tagged(self, classes):
        e = _e()
        e.classes_ok = classes
        return e

    def test_a_tag_without_d_and_c_is_focused(self):
        self.assertTrue(class_focused(self._tagged(["B", "A", "S"])))
        self.assertTrue(class_focused(self._tagged(["S"])))

    def test_a_tag_that_also_clears_the_low_classes_is_not(self):
        self.assertFalse(class_focused(self._tagged(["D", "C", "B", "A", "S"])))
        self.assertFalse(class_focused(self._tagged(["C", "B"])))

    def test_no_tag_at_all_is_not_focused(self):
        # Silence is not a statement — it must not outrank a written tag.
        self.assertFalse(class_focused(self._tagged(None)))
        self.assertFalse(class_focused(self._tagged([])))

    def test_a_d_or_c_tag_is_held_back_in_a_higher_round(self):
        self.assertTrue(class_dilutes(self._tagged(["D", "C", "B", "A", "S"]), "S"))
        self.assertFalse(class_dilutes(self._tagged(["B", "A", "S"]), "S"))
        self.assertFalse(class_dilutes(self._tagged(None), "S"))

    def test_the_lower_rounds_are_not_affected(self):
        wide = self._tagged(["D", "C", "B", "A", "S"])
        self.assertFalse(class_dilutes(wide, "D"))
        self.assertFalse(class_dilutes(wide, None))

    def test_having_been_played_in_this_class_overrules_the_tag(self):
        # Somebody put it in a real S list by hand: that decision stands.
        e = _e(class_plays={"S": 2})
        e.classes_ok = ["D", "C", "B", "A", "S"]
        self.assertFalse(class_dilutes(e, "S"))
        # …but plays in the lower classes say nothing about this one.
        e.class_plays = {"D": 9}
        self.assertTrue(class_dilutes(e, "S"))

    def test_an_s_round_reaches_for_the_focused_title(self):
        from dancesport_planner import MusicLibrary

        def _cc(name, classes):
            return MusicEntry(
                path=Path(rf"C:\music	anzcds\lateincd\CC\{name}.mp3"),
                title=name, dance="CC", bpm=31, popularity=3,
                classes_ok=classes)

        lib = MusicLibrary()
        lib.entries.extend([_cc("Open", ["D", "C", "B", "A", "S"]),
                            _cc("Focused", ["B", "A", "S"])])
        random.seed(4)
        self.assertGreater(_won(lib, "S", "Focused"), _won(lib, "S", "Open") * 3)

    def test_a_played_wide_tag_is_no_longer_held_back(self):
        from dancesport_planner import MusicEntry, MusicLibrary

        def _cc(name, classes, plays=None):
            return MusicEntry(
                path=Path(rf"C:\music	anzcds\lateincd\CC\{name}.mp3"),
                title=name, dance="CC", bpm=31, popularity=3,
                classes_ok=classes, class_plays=plays)

        lib = MusicLibrary()
        lib.entries.extend([_cc("Open", ["D", "C", "B", "A", "S"], {"S": 3}),
                            _cc("Focused", ["B", "A", "S"])])
        random.seed(4)
        # It was picked for an S event by hand before, so it competes normally.
        self.assertGreater(_won(lib, "S", "Open"), 8)

    def test_a_d_round_does_not_care(self):
        from dancesport_planner import MusicLibrary

        def _cc(name, classes):
            return MusicEntry(
                path=Path(rf"C:\music	anzcds\lateincd\CC\{name}.mp3"),
                title=name, dance="CC", bpm=28, popularity=3,
                classes_ok=classes)

        lib = MusicLibrary()
        lib.entries.extend([_cc("Open", ["D", "C", "B", "A", "S"]),
                            _cc("Focused", ["B", "A", "S"])])
        random.seed(4)
        # "Focused" is not cleared for D at all, so it is the one kept out.
        self.assertEqual(_won(lib, "D", "Focused"), 0)


if __name__ == "__main__":
    unittest.main()
