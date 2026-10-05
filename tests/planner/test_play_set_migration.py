"""🏆 The tournament set's fade-out went from 1.5 s to 3 s.

Run:  py -m unittest tests.planner.test_play_set_migration -v

⚙ Settings saves a play set whole, so a settings file holds the old 1.5 s
default even where nobody ever chose it — and a stored value wins over the
default. A stored 1.5 is lifted to 3 once; any other value was chosen and
stays.
"""
import unittest

from planner.play_sets import PLAY_SETS_VERSION, migrate_play_sets, play_set_of


class TournamentFadeMigrationTest(unittest.TestCase):

    def test_the_old_default_is_lifted(self):
        s = migrate_play_sets({"tournament_set": {"secs": 100, "fade": 1.5}})
        self.assertEqual(play_set_of(s, "tournament")["fade"], 3.0)
        self.assertEqual(s["tournament_set"]["secs"], 100)

    def test_a_chosen_value_stays(self):
        s = migrate_play_sets({"tournament_set": {"fade": 2.0}})
        self.assertEqual(play_set_of(s, "tournament")["fade"], 2.0)

    def test_it_runs_once(self):
        s = migrate_play_sets({"tournament_set": {"fade": 1.5}})
        self.assertEqual(s["play_sets_version"], PLAY_SETS_VERSION)
        s["tournament_set"]["fade"] = 1.5      # chosen again, after the update
        self.assertEqual(migrate_play_sets(s)["tournament_set"]["fade"], 1.5)

    def test_no_stored_set_takes_the_default(self):
        s = migrate_play_sets({})
        self.assertEqual(play_set_of(s, "tournament")["fade"], 3.0)

    def test_the_party_set_is_left_alone(self):
        s = migrate_play_sets({"party_set": {"fade": 1.5}})
        self.assertEqual(s["party_set"]["fade"], 1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
