"""🤖 Fuzz: a model's answer is text nobody checked.

Callers: `parse_reply` and `parse_swaps` raise RuntimeError on an answer with
no JSON at all (their docstrings say so); planner/generate/llm.py and
planner/event/event_plan.py catch Exception around them. `parse_queries` and
`parse_ai_suggestions` are lenient: they answer [] instead.
"""
import json
import unittest

from hypothesis import example, given
from hypothesis import strategies as st

from planner.generate import ai, llm
from tests.fuzz_support import fuzz, json_docs, texts

answers = st.one_of(
    texts,
    json_docs(["playlist", "swaps", "notes", "queries", "artist", "title", "dance",
               "variant", "out", "in", "reason"]).map(json.dumps),
    st.tuples(texts, json_docs(["playlist", "swaps", "notes"]).map(json.dumps), texts)
    .map(lambda t: f"{t[0]}\n```json\n{t[1]}\n```\n{t[2]}"))


class ModelReplyFuzzTest(unittest.TestCase):
    @fuzz(150)
    @given(answers)
    @example('{"playlist": [null, 1, {"title": []}]}')
    @example('{"swaps": [{"out": {}}], "notes": []}')
    def test_the_strict_parsers_raise_only_what_their_callers_catch(self, text):
        for parse in (llm.parse_reply, llm.parse_swaps):
            try:
                out = parse(text)
            except RuntimeError:
                continue
            self.assertIsInstance(out, dict)

    @fuzz(150)
    @given(answers)
    def test_the_lenient_parsers_never_raise(self, text):
        queries = llm.parse_queries(text)
        self.assertIsInstance(queries, list)
        self.assertTrue(all(isinstance(q, dict) for q in queries))
        picks = ai.parse_ai_suggestions(text)
        self.assertIsInstance(picks, list)
        for p in picks:
            self.assertIsInstance(p.get("artist", ""), str)
            self.assertIsInstance(p.get("title", ""), str)


if __name__ == "__main__":
    unittest.main()
