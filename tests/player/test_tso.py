#!/usr/bin/env python3
"""Tests for 🎚 TSO's arithmetic on its own, without a player or a window.

Run:  py -m unittest tests.player.test_tso -v

Which titles count as the playing title's round, and which takt the button
pitches it to. Setting the tempo and saying so stay with the window.
"""

import unittest
from types import SimpleNamespace

from gui.running_order import Row
from player.tso import round_takte, tso_band_of, tso_target


def row(dance, bpm, round_name=""):
    return Row(SimpleNamespace(dance=dance, bpm=bpm), dance, round_name)


def deck(rows, player_list=False, hdr=None):
    return SimpleNamespace(_row_meta=rows, _player_list=player_list,
                           _row_round_hdr=hdr or {})


class RoundTakteTest(unittest.TestCase):

    def test_a_grid_round_counts_its_own_titles_of_that_dance(self):
        d = deck([None,
                  row("SA", 50, "Vorrunde"), row("SA", 51, "Vorrunde"),
                  row("CC", 31, "Vorrunde"), row("SA", 52, "Finale"),
                  row("SA", 0, "Vorrunde")])
        self.assertEqual(round_takte(d, 1, "SA"), [50, 51])

    def test_a_running_order_counts_the_titles_under_the_same_strip(self):
        """Its rows carry no round name: twelve Sambas over four rounds must
        not set the takt of a Vorrunde of six."""
        rows = [None, row("SA", 50), row("SA", 50), None, row("SA", 52)]
        d = deck(rows, player_list=True, hdr={1: 0, 2: 0, 4: 3})
        self.assertEqual(round_takte(d, 1, "SA"), [50, 50])
        self.assertEqual(round_takte(d, 4, "SA"), [52])


class TsoTargetTest(unittest.TestCase):

    def test_the_round_joins_its_majority_takt(self):
        tso = tso_target([50, 51, 51], "SA", 50, "mean")
        self.assertEqual(tso.counts, {50: 1, 51: 2})
        self.assertEqual((tso.danced_at, tso.target), (51.0, 51.0))

    def test_mean_never_pitches_more_than_one_takt(self):
        """A T23 Rumba in a round at 25 comes up to 24, not to 25."""
        self.assertEqual(tso_target([25, 25], "RB", 23, "mean").target, 24)

    def test_a_title_below_the_band_comes_up_to_its_floor(self):
        self.assertEqual(tso_target([27], "SF", 27, "mean").target, 28)

    def test_a_fixed_band_takes_its_takt_whatever_the_round(self):
        self.assertEqual(tso_target([24, 24], "RB", 25, "upper").target, 26.0)
        self.assertEqual(tso_target([24, 24], "RB", 25, "middle").target, 25.0)

    def test_a_dance_without_a_band_stays_at_its_own_takt(self):
        tso = tso_target([], "XX", 40, "mean")
        self.assertEqual((tso.danced_at, tso.target), (40, 40))


class BandOfTest(unittest.TestCase):

    def test_an_unset_dance_keeps_the_mean(self):
        self.assertEqual(tso_band_of({}, "RB"), "mean")

    def test_the_setting_names_the_band(self):
        self.assertEqual(tso_band_of({"tso_band": {"RB": "upper"}}, "RB"), "upper")

    def test_an_unknown_band_falls_back_to_the_mean(self):
        self.assertEqual(tso_band_of({"tso_band": {"RB": "loud"}}, "RB"), "mean")
        self.assertEqual(tso_band_of({"tso_band": "RB"}, "RB"), "mean")


if __name__ == "__main__":
    unittest.main(verbosity=2)
