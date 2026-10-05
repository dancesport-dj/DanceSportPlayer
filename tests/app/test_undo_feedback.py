"""Undo/redo feedback: change descriptions must cover ALL 16 decks + the four
wishlists + the Eintanzen panel, and pure moves/swaps must be named instead of
the generic fallback text.

These read a SessionEnv — plain dicts in, a sentence out — so no QApplication,
no window and no state dir are needed to ask what an undo step would say."""
import unittest

from gui.session_env import SessionEnv, deck_slots, list_moved


def _deck(grid_paths, name="Final"):
    """Minimal serialized deck: {slot_d_idx: path} for one round, one heat."""
    return {
        "mode": "Favorites",
        "rounds": [{
            "name": name,
            "grid": {"0": {str(d): p for d, p in grid_paths.items()}},
        }],
    }


A = r"C:\music\standardcd\WW 58 - Alpha.mp3"
B = r"C:\music\standardcd\WW 59 - Bravo.mp3"
C = r"C:\music\standardcd\WW 60 - Charlie.mp3"


def _describe(before, after):
    return SessionEnv(after).describe_change_from(SessionEnv(before))


class UndoFeedbackTest(unittest.TestCase):

    def test_env_all_paths_covers_decks_e_h_and_warmup(self):
        c = SessionEnv({"deck_g": _deck({0: A}),
                        "warmup": {"paths": [B]}}).all_paths()
        self.assertEqual(c[A], 1)
        self.assertEqual(c[B], 1)

    def test_remove_in_deck_e_is_named(self):
        desc = _describe({"deck_e": _deck({0: A, 1: B})},
                         {"deck_e": _deck({0: A})})
        self.assertIn("removed", desc)
        self.assertIn("Bravo", desc)

    def test_swap_within_deck_is_reported_as_moved(self):
        desc = _describe({"deck_a": _deck({0: A, 1: B})},
                         {"deck_a": _deck({0: B, 1: A})})
        self.assertIn("moved", desc)
        self.assertIn("Alpha", desc)
        self.assertIn("Bravo", desc)

    def test_swap_within_a_day_deck_is_reported_as_moved(self):
        """The 📅 day decks were left out of the move walk while being counted
        by the path walk — so a swap there matched on tracks, found no move and
        came back as the "view / settings change" fallback."""
        desc = _describe({"day_a": _deck({0: A, 1: B})},
                         {"day_a": _deck({0: B, 1: A})})
        self.assertIn("moved", desc)
        self.assertIn("Alpha", desc)

    def test_cross_deck_move_is_reported_as_moved(self):
        desc = _describe({"deck_a": _deck({0: A, 1: B}), "deck_b": _deck({0: C})},
                         {"deck_a": _deck({0: A}), "deck_b": _deck({0: C, 1: B})})
        self.assertIn("moved", desc)
        self.assertIn("Bravo", desc)

    def test_warmup_reorder_is_reported_as_moved(self):
        desc = _describe({"warmup": {"paths": [A, B, C]}},
                         {"warmup": {"paths": [C, A, B]}})
        self.assertIn("moved", desc)

    def test_wishlist_reorder_is_reported_as_moved(self):
        desc = _describe({"wishlist2": [A, B]}, {"wishlist2": [B, A]})
        self.assertIn("moved", desc)

    def test_pure_view_change_falls_back(self):
        desc = _describe({"deck_a": _deck({0: A}), "wish_state": 1},
                         {"deck_a": _deck({0: A}), "wish_state": 2})
        self.assertEqual(desc, "view / settings change")

    def test_env_deck_slots(self):
        slots = deck_slots(_deck({0: A, 1: B}, name="VF"))
        self.assertEqual(slots[("VF", "0", "0")], A)
        self.assertEqual(slots[("VF", "0", "1")], B)
        self.assertEqual(deck_slots({"mode": "Theme"}), {})

    def test_list_moved(self):
        self.assertEqual(list_moved([A, B], [A, B]), [])
        self.assertEqual(list_moved([A, B], [B, A]), [B, A])
        self.assertEqual(list_moved([A], [A, B]), [B])


if __name__ == "__main__":
    unittest.main()
