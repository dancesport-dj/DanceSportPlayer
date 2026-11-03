"""Model replies are untrusted: odd numbers, trailing sentences and string
flags must not abort a run (review items 3, 4, 32, 108, 115)."""
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from planner.generate import ai, llm


class NumberGuardTests(unittest.TestCase):
    def test_infinite_pick_number_is_skipped(self):
        out = llm.parse_reply('{"playlist": [{"n": 1e999}, {"n": 4}]}')
        self.assertEqual([p["n"] for p in out["picks"]], [4])

    def test_infinite_swap_number_is_skipped(self):
        out = llm.parse_swaps('{"swaps": [{"n": 1e999}, {"n": 2, "heat": 1}]}')
        self.assertEqual([s["n"] for s in out["swaps"]], [2])

    def test_infinite_query_limit_falls_back(self):
        cands = [NS(path=str(i)) for i in range(3)]
        with mock.patch.object(llm, "_matches", return_value=True):
            got = llm.run_queries([{"limit": float("inf"), "sort": "random"}], cands)
        self.assertTrue(got)

    def test_superscript_digit_heat_does_not_abort(self):
        out = llm.parse_reply('{"playlist": [{"n": 3, "heat": "\u00b2"}]}')
        self.assertEqual(out["picks"][0]["n"], 3)
        self.assertEqual(out["picks"][0]["heat"], 0)

    def test_heat_digits_still_work(self):
        out = llm.parse_reply('{"playlist": [{"n": 3, "heat": "2"}]}')
        self.assertEqual(out["picks"][0]["heat"], 2)


class QueriesTests(unittest.TestCase):
    def test_trailing_sentence_with_braces(self):
        text = '{"queries": [{"dance": "TG"}]}\nHope {this} helps.'
        self.assertEqual(llm.parse_queries(text), [{"dance": "TG"}])

    def test_second_object_wins(self):
        text = '{"queries": [{"a": 1}]} Wait: {"queries": [{"b": 2}]}'
        self.assertEqual(llm.parse_queries(text), [{"b": 2}])

    def test_nothing_usable(self):
        self.assertEqual(llm.parse_queries("no json"), [])


class FlagTests(unittest.TestCase):
    def test_string_false_is_false(self):
        for value, expected in (("false", False), ("False", False), ("no", False),
                                ("0", False), ("true", True), (True, True),
                                (False, False), (1, True), (0, False)):
            with self.subTest(value):
                self.assertEqual(llm._flag(value), expected)


class RetryEndTests(unittest.TestCase):
    def test_reset_three_times_then_silence_raises_the_error(self):
        call = mock.Mock(side_effect=[ConnectionResetError("x")] * 3
                         + [ai.NoOutput("silent")])
        with self.assertRaises(ai.NoOutput):
            llm._try_backend(call, "host", sleep=mock.Mock())


if __name__ == "__main__":
    unittest.main()
