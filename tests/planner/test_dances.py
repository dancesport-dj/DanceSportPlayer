"""📏 The dance tempo tables live once, in planner.dances."""
import unittest

from planner import dances, models
from planner.music import analysis


class OneTableTest(unittest.TestCase):
    def test_models_reads_the_same_tempo_table(self):
        self.assertIs(models.TEMPO_RANGES, dances.TEMPO_RANGES)

    def test_every_dance_has_beats_per_bar(self):
        self.assertEqual(set(dances.BEATS_PER_BAR), set(dances.TEMPO_RANGES))

    def test_default_takt_is_the_range_midpoint(self):
        self.assertEqual(dances.default_takt("LW"), 29)
        self.assertEqual(dances.default_takt("JI"), 43)
        self.assertIsNone(dances.default_takt("SALSA"))
        self.assertIsNone(dances.default_takt(None))

    def test_the_tempo_prior_follows_the_table(self):
        # No per-file takt: the midpoint × beats per bar.
        self.assertEqual(analysis.tempo_prior("JI", None), 43 * 4)
        self.assertEqual(analysis.tempo_prior("SA", 50), 50 * 2)
        self.assertIsNone(analysis.tempo_prior("SALSA", None))
        self.assertFalse(hasattr(analysis, "_DEFAULT_TAKT"))


if __name__ == "__main__":
    unittest.main()
