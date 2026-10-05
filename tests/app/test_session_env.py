#!/usr/bin/env python3
"""Tests for the session envelope — what one autosave / undo snapshot IS.

Run:  py -m unittest tests.app.test_session_env -v

The shape of an env used to be spelled out at each of the eight places that
walked it, so "does this walk cover the day decks?" could only be answered by
reading all eight. Asked of one module it is a test.
"""
import unittest

from gui.session_env import (
    ALL_DECK_KEYS,
    DAY_KEYS,
    DECK_KEYS,
    SessionEnv,
    WISH_KEYS,
    deck_paths,
    deck_slots,
    fmt_track_list,
)

A = r"C:\music\standardcd\WW 58 - Alpha.mp3"
B = r"C:\music\standardcd\WW 59 - Bravo.mp3"
C = r"C:\music\standardcd\WW 60 - Charlie.mp3"


def _deck(grid_paths, name="Final", backups=None):
    return {
        "mode": "Favorites",
        "rounds": [{
            "name": name,
            "grid": {"0": {str(d): p for d, p in grid_paths.items()}},
            "backups": backups or {},
        }],
    }


class EnvShapeTest(unittest.TestCase):
    """The keys the envelope is made of — eight decks, eight day decks, four
    wishlists, none of them overlapping."""

    def test_there_are_eight_decks_and_eight_day_decks(self):
        self.assertEqual(len(DECK_KEYS), 8)
        self.assertEqual(len(DAY_KEYS), 8)
        self.assertEqual(len(WISH_KEYS), 4)

    def test_all_deck_keys_is_the_decks_then_the_day_decks(self):
        """Zipped against `self._decks + self._day_decks` — the order IS the
        mapping from key to table, so it may not be sorted or reshuffled."""
        self.assertEqual(ALL_DECK_KEYS, DECK_KEYS + DAY_KEYS)

    def test_no_key_names_two_different_things(self):
        keys = ALL_DECK_KEYS + WISH_KEYS
        self.assertEqual(len(set(keys)), len(keys))


class DeckPathsTest(unittest.TestCase):
    """What one serialized deck holds."""

    def test_a_grid_deck_gives_up_its_slots(self):
        self.assertEqual(deck_paths(_deck({0: A, 1: B})), [A, B])

    def test_the_stacked_final_backups_count_too(self):
        """They are songs in the session — an undo that drops one has to say so."""
        d = _deck({0: A}, backups={"0/0": [B, C]})
        self.assertEqual(sorted(deck_paths(d)), sorted([A, B, C]))

    def test_a_theme_deck_gives_up_its_running_order(self):
        d = {"mode": "Theme", "theme_entries": [A, B]}
        self.assertEqual(deck_paths(d), [A, B])

    def test_an_empty_deck_holds_nothing(self):
        self.assertEqual(deck_paths(None), [])
        self.assertEqual(deck_paths({}), [])

    def test_empty_slots_are_not_tracks(self):
        self.assertEqual(deck_paths(_deck({0: A, 1: None})), [A])

    def test_a_theme_deck_has_no_slots_to_move_within(self):
        """Position, not slot, is what a track moves within there."""
        self.assertEqual(deck_slots({"mode": "Theme", "theme_entries": [A]}), {})


class EnvWalkTest(unittest.TestCase):
    """Asking a snapshot about itself instead of indexing it by key."""

    def test_every_deck_is_walked_even_the_empty_ones(self):
        env = SessionEnv({"deck_a": _deck({0: A})})
        self.assertEqual(len(env.decks()), 16)
        self.assertEqual([k for k, d in env.decks() if d], ["deck_a"])

    def test_the_ordered_lists_are_the_wishlists_and_the_panel(self):
        env = SessionEnv({"wishlist": [A], "warmup": {"paths": [B]}})
        got = dict(env.ordered_lists())
        self.assertEqual(sorted(got), sorted(list(WISH_KEYS) + ["warmup"]))
        self.assertEqual(got["wishlist"], [A])
        self.assertEqual(got["warmup"], [B])

    def test_blank_entries_are_dropped_from_a_list(self):
        env = SessionEnv({"wishlist": [A, "", None]})
        self.assertEqual(dict(env.ordered_lists())["wishlist"], [A])

    def test_a_session_with_a_track_anywhere_holds_tracks(self):
        for key in ("deck_a", "day_h", "wishlist4"):
            self.assertTrue(SessionEnv({key: _deck({0: A})
                                        if "deck" in key or "day" in key
                                        else [A]}).holds_tracks(), key)

    def test_a_warmup_list_alone_holds_tracks(self):
        """The player-first layout holds nothing but the party list — a session
        like that was never autosaved at all."""
        self.assertTrue(SessionEnv({"warmup": {"paths": [A]}}).holds_tracks())

    def test_an_empty_warmup_panel_holds_none(self):
        self.assertFalse(SessionEnv({"warmup": {"paths": ["", None]}})
                         .holds_tracks())

    def test_a_session_of_nothing_but_view_state_holds_none(self):
        """Saving that over the last real autosave would lose the session."""
        self.assertFalse(SessionEnv({"deck_count": 4, "wish_state": 2,
                                     "deck_modes": {"deck_a": "static"}})
                         .holds_tracks())

    def test_an_absent_snapshot_is_falsy_and_empty(self):
        env = SessionEnv(None)
        self.assertFalse(env)
        self.assertEqual(env.all_paths(), {})
        self.assertFalse(env.holds_tracks())

    def test_the_same_track_in_two_decks_counts_twice(self):
        """A multiset, not a set — removing one of two copies is a change."""
        env = SessionEnv({"deck_a": _deck({0: A}), "day_c": _deck({0: A})})
        self.assertEqual(env.all_paths()[A], 2)


class MovedTest(unittest.TestCase):
    """Which tracks sit somewhere else than they did."""

    def test_an_untouched_session_moved_nothing(self):
        env = SessionEnv({"deck_a": _deck({0: A, 1: B})})
        self.assertEqual(env.moved_from(env), [])

    def test_a_track_is_named_once_even_if_it_moved_in_two_ways(self):
        before = SessionEnv({"deck_a": _deck({0: A}), "wishlist": [B, A]})
        after = SessionEnv({"deck_a": _deck({1: A}), "wishlist": [A, B]})
        self.assertEqual(after.moved_from(before).count(A), 1)

    def test_a_day_deck_move_is_seen(self):
        before = SessionEnv({"day_e": _deck({0: A, 1: B})})
        after = SessionEnv({"day_e": _deck({0: B, 1: A})})
        self.assertEqual(sorted(after.moved_from(before)), sorted([A, B]))


class WordingTest(unittest.TestCase):
    """How the change is said — one name, two names, then a count."""

    def test_one_track_is_quoted(self):
        self.assertEqual(fmt_track_list([A]), "“58 - Alpha”")

    def test_two_tracks_are_joined_by_and(self):
        self.assertEqual(fmt_track_list([A, B]), "“58 - Alpha” and “59 - Bravo”")

    def test_more_than_two_are_counted(self):
        out = fmt_track_list([A, B, C])
        self.assertTrue(out.startswith("3 tracks ("))
        self.assertIn("58 - Alpha", out)
        self.assertNotIn("Charlie", out)

    def test_a_rename_is_named_when_nothing_else_changed(self):
        before = SessionEnv({"deck_a": _deck({0: A}), "names": {"deck_a": "X"}})
        after = SessionEnv({"deck_a": _deck({0: A}), "names": {"deck_a": "Y"}})
        self.assertEqual(after.describe_change_from(before), "playlist rename")

    def test_a_deck_view_change_is_named(self):
        before = SessionEnv({"deck_a": _deck({0: A}), "deck_count": 2})
        after = SessionEnv({"deck_a": _deck({0: A}), "deck_count": 4})
        self.assertEqual(after.describe_change_from(before), "deck layout change")

    def test_a_replacement_names_both_sides(self):
        before = SessionEnv({"deck_a": _deck({0: A})})
        after = SessionEnv({"deck_a": _deck({0: B})})
        desc = after.describe_change_from(before)
        self.assertIn("replaced", desc)
        self.assertIn("58 - Alpha", desc)
        self.assertIn("59 - Bravo", desc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
