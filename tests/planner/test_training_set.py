"""The 🏃 training set: a pause between the titles, and a short wait on the Paso.

Run:  py -m unittest tests.planner.test_training_set -v
"""
import unittest

from planner.playing.play_sets import (
    PARTY_SET,
    dblclick_ask_of,
    pd_of,
    play_set_of,
    tso_of,
)


class TrainingSetTest(unittest.TestCase):

    def test_pause_is_on_for_25_seconds(self):
        s = play_set_of({}, "training")
        self.assertFalse(s["pause_off"])
        self.assertEqual(s["pause_secs"], 25)

    def test_the_paso_doble_starts_after_2_seconds(self):
        self.assertEqual(pd_of({}, "training")["pd_delay"], 2)

    def test_it_otherwise_plays_like_a_party(self):
        s = play_set_of({}, "training")
        for k in ("secs", "advance", "announce", "dblclick"):
            self.assertEqual(s[k], PARTY_SET[k], k)
        self.assertFalse(tso_of({}, "training"))
        self.assertTrue(dblclick_ask_of({}, "training"))

    def test_party_and_tournament_carry_no_pause_seconds(self):
        self.assertNotIn("pause_secs", play_set_of({}, "party"))
        self.assertNotIn("pause_secs", play_set_of({}, "tournament"))

    def test_settings_override_the_pause_and_a_broken_value_falls_back(self):
        self.assertEqual(
            play_set_of({"training_set": {"pause_secs": 40}}, "training")["pause_secs"], 40)
        self.assertEqual(
            play_set_of({"training_set": {"pause_secs": "x"}}, "training")["pause_secs"], 25)
        self.assertEqual(
            play_set_of({"training_set": {"pause_secs": 999}}, "training")["pause_secs"], 120)


if __name__ == "__main__":
    unittest.main()
