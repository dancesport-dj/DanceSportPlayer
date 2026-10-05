#!/usr/bin/env python3
"""⏱ How many songs per dance a party list of N hours needs.

Run:  py -m unittest tests.planner.test_warmup_estimate -v

The estimate runs the real ETDS builder on made-up pools whose lengths come
from the library, and counts each list up to the target play time. The builder
is random, so the tests seed `random` and check invariants, not exact lists.
"""

import random
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.warmup import (
    _WARMUP_BALLROOM,
    _WARMUP_LATIN,
    _WARMUP_MODE,
    estimate_warmup_counts,
    warmup_lengths,
)


def _lengths(secs, codes=_WARMUP_BALLROOM + _WARMUP_LATIN + _WARMUP_MODE):
    return {c: [secs] for c in codes}


class WarmupLengthsTest(unittest.TestCase):

    def test_lengths_are_collected_per_dance_and_unknown_ones_skipped(self):
        entries = [
            MusicEntry(path=Path("C:/m/a.mp3"), title="a", dance="LW", duration=190),
            MusicEntry(path=Path("C:/m/b.mp3"), title="b", dance="LW", duration=0),
            MusicEntry(path=Path("C:/m/c.mp3"), title="c", dance=None, other_genre="Discofox",
                       duration=230),
            MusicEntry(path=Path("C:/m/d.mp3"), title="d", dance=None, duration=200),
        ]
        self.assertEqual(warmup_lengths(entries), {"LW": [190], "DISCOFOX": [230]})


class EstimateTest(unittest.TestCase):

    def setUp(self):
        random.seed(7)

    def test_the_songs_fill_the_hours(self):
        # Every song 3 min: one hour is exactly 20 songs, every time.
        counts, total = estimate_warmup_counts(_lengths(180), 1, runs=10)
        self.assertEqual(total, (20, 20))
        self.assertAlmostEqual(sum(mean for mean, _ in counts.values()), 20)

    def test_longer_songs_need_fewer(self):
        _, short = estimate_warmup_counts(_lengths(150), 6, runs=10)
        _, long_ = estimate_warmup_counts(_lengths(240), 6, runs=10)
        self.assertGreater(short[0], long_[0])

    def test_stock_is_at_least_the_mean(self):
        """What to stock never reads below what an evening averages — give or
        take the one track a percentile cannot resolve.

        `stock` is the 90th percentile of whole-track counts, and a dance that
        lands on 12 in eighteen runs out of twenty and on 13-14 in the other
        two has a p90 of 12 against a mean of 12.05. That is arithmetic, not a
        bad estimate: measured on 3 of 20 seeds here and on 2 of 20 with the
        LW/WW round rule reverted, always by exactly that 0.05. The whole-list
        total is wide enough that it never happens, so that one stays exact."""
        counts, total = estimate_warmup_counts(_lengths(180), 6, runs=20,
                                               include_modetaenze=True)
        for code, (mean, stock) in counts.items():
            self.assertGreaterEqual(stock, mean - 1, code)
        self.assertGreaterEqual(total[1], total[0])

    def test_the_options_decide_which_dances_appear(self):
        counts, _ = estimate_warmup_counts(_lengths(180), 3, runs=10,
                                           include_latin=False)
        self.assertTrue(counts)
        self.assertLessEqual(set(counts), set(_WARMUP_BALLROOM))

        counts, _ = estimate_warmup_counts(_lengths(180), 6, runs=10, no_paso=True)
        self.assertNotIn("PD", counts)
        self.assertFalse(set(counts) & set(_WARMUP_MODE))

        counts, _ = estimate_warmup_counts(_lengths(180), 6, runs=10,
                                           include_modetaenze=True,
                                           modetaenze=["DISCOFOX", "SALSA"])
        self.assertIn("SALSA", counts)
        self.assertFalse(set(counts) & (set(_WARMUP_MODE) - {"DISCOFOX", "SALSA"}))

    def test_a_dance_without_known_lengths_still_counts(self):
        lengths = _lengths(180, _WARMUP_BALLROOM)
        counts, _ = estimate_warmup_counts(lengths, 6, runs=10, include_latin=False,
                                           include_modetaenze=True,
                                           modetaenze=["DISCOFOX"],
                                           fallback_secs=180)
        self.assertIn("DISCOFOX", counts)

    def test_a_stopped_estimate_gives_up(self):
        asked = []

        def stop():
            asked.append(1)
            return len(asked) > 2
        self.assertIsNone(estimate_warmup_counts(_lengths(180), 6, runs=40,
                                                 should_stop=stop))
        self.assertEqual(len(asked), 3)

    def test_long_parties_do_not_run_out_of_songs(self):
        _, total = estimate_warmup_counts(_lengths(120), 12, runs=3,
                                          include_modetaenze=True)
        self.assertEqual(total, (360, 360))


if __name__ == "__main__":
    unittest.main(verbosity=2)
