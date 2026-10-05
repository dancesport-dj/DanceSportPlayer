"""Tests for dup_clashes: which replacement candidates the duplicate check would
flag again.

Run:  py -m unittest tests.planner.test_dup_clashes -v

Marcel: "if similar dialog for replacement opens make sure that if we coming from
duplicates check it does not show titles that are in other open lists. otherwise
it is a ping pong game". A candidate clashes by the report's own rule: the same
file, or the same song by title in a dance that does not rule it out.
"""
import unittest

from planner.checks import dup_clashes
from planner.parsing import _song_title_keys


def _rec(name: str, dance: str | None = "LW", exact: str | None = None) -> dict:
    return {"exact": exact or f"p:{name}", "tkeys": _song_title_keys(name),
            "dance": dance}


class DupClashesTest(unittest.TestCase):

    def test_the_same_file_clashes(self):
        taken = [_rec("Moon River")]
        self.assertEqual(dup_clashes([_rec("Other name", exact="p:Moon River")], taken), {0})

    def test_another_recording_of_a_taken_title_clashes(self):
        taken = [_rec("Andy Williams - Moon River")]
        cands = [_rec("Moon River (Instrumental)", exact="p:x"), _rec("Tennessee Waltz")]
        self.assertEqual(dup_clashes(cands, taken), {0})

    def test_a_taken_title_in_another_dance_does_not(self):
        taken = [_rec("Beautiful", dance="JI")]
        self.assertEqual(dup_clashes([_rec("Beautiful", dance="LW", exact="p:y")], taken), set())

    def test_an_unknown_dance_does_not_rule_it_out(self):
        taken = [_rec("Beautiful", dance=None)]
        self.assertEqual(dup_clashes([_rec("Beautiful", exact="p:y")], taken), {0})

    def test_nothing_taken_nothing_clashes(self):
        self.assertEqual(dup_clashes([_rec("Moon River")], []), set())


if __name__ == "__main__":
    unittest.main()
