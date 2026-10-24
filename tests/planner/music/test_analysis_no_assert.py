"""🎼 The feature-vector length check holds under python -O too.

Run:  py -m unittest tests.planner.music.test_analysis_no_assert -v

An assert is stripped by -O, and a vector of the wrong length would then
be stored and compared against the 84-dim ones of every other track.
"""
import ast
import unittest
from pathlib import Path

import planner.music.analysis as analysis


class NoAssertTest(unittest.TestCase):

    def test_the_analysis_checks_with_raise_not_assert(self):
        tree = ast.parse(Path(analysis.__file__).read_text(encoding="utf-8"))
        lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
