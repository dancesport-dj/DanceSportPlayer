"""What a fresh install's 🎉 party and 🏆 tournament sets stand on — Marcel's
own desk values of 2026-10-17, shipped as the defaults."""
import unittest

from planner.playing.play_sets import DANCE_SECS_KEY, dance_secs_of, play_set_of


class SetDefaultsTest(unittest.TestCase):

    def test_a_heat_fades_in_2_5_s_after_its_length(self):
        """Marcel: "default tournament set not with the length ticked" and
        "default tournament set fadeout 2.5s"."""
        t = play_set_of({}, "tournament")
        self.assertEqual(t["fade"], 2.5)
        self.assertIs(t["fade_inside"], False)

    def test_a_party_fades_within_its_length_and_does_not_crossfade(self):
        """Marcel: "for party set within the length ticked, but crossfade not
        ticked". The crossfade keeps its seconds for switching it on."""
        p = play_set_of({}, "party")
        self.assertIs(p["fade_inside"], True)
        self.assertIs(p["xfade_on"], False)
        self.assertEqual(p["xfade"], 4.0)


class DanceSecsDefaultsTest(unittest.TestCase):

    def test_nothing_stored_is_the_shipped_length_per_dance(self):
        """Marcel: "make also the play length per dance default" — 1:30 for
        the quick ones, 1:37 for the rest."""
        self.assertEqual(dance_secs_of({}), {
            "LW": 90, "TG": 97, "WW": 90, "SF": 97, "QS": 90,
            "SA": 97, "CC": 97, "RB": 97, "PD": 0, "JI": 90})

    def test_a_heats_paso_doble_plays_in_full(self):
        """Marcel: "default tournent set for paso is full" — not cut at the
        set's 1:45; the chairman ends it."""
        self.assertEqual(dance_secs_of({})["PD"], 0)

    def test_a_list_emptied_in_settings_stays_empty(self):
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: {}}), {})

    def test_the_default_is_a_copy(self):
        dance_secs_of({})["LW"] = 1
        self.assertEqual(dance_secs_of({})["LW"], 90)


if __name__ == "__main__":
    unittest.main()
