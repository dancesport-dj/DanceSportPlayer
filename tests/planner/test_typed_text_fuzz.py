"""⌨ Fuzz: what the operator types or pastes into the planner.

Each of these parsers answers None or an empty list for text it cannot read;
the dialogs that call them show "not a time" and the like, and catch nothing.
"""
import unittest

from hypothesis import example, given

from planner.event.competition import parse_competition_schedule
from planner.music.paths import parse_remap_paths
from planner.playing.cartwall import parse_cell
from planner.playing.party_stop import parse_stop_time
from planner.playing.play_sets import parse_play_length
from tests.fuzz_support import fuzz, json_values, texts


class TypedTextFuzzTest(unittest.TestCase):
    @fuzz(150)
    @given(texts)
    @example("99:99")
    @example("2400")
    def test_times_and_lengths(self, s):
        length = parse_play_length(s)
        self.assertTrue(length is None or (isinstance(length, int) and length >= 0))
        stop = parse_stop_time(s)
        if stop is not None:
            h, m = stop
            self.assertTrue(0 <= h <= 23 and 0 <= m <= 59, stop)

    @fuzz(150)
    @given(texts)
    @example("10:30 Hgr C Standard\n11:00 Sen I S Latein 999999 Paare")
    def test_a_pasted_schedule(self, s):
        self.assertIsInstance(parse_competition_schedule(s), list)

    @fuzz(100)
    @given(json_values)
    def test_cartwall_keys_and_search_folders(self, v):
        cell = parse_cell(v)
        self.assertTrue(cell is None or len(cell) == 2)
        try:
            folders = parse_remap_paths(v)
        except (TypeError, AttributeError):
            self.fail(f"parse_remap_paths({v!r}) raised")
        self.assertTrue(all(isinstance(f, str) for f in folders))


if __name__ == "__main__":
    unittest.main()
