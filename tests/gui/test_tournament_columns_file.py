"""🏆 The track list's saved column layout in tournaments.json.

Found by the state-file fuzz test (2026-11-17): an "order" with anything but
column numbers in it - a null from a hand edit, a name - made `sorted(order)`
raise TypeError in load_columns, and the tree is built with the main window,
so the app did not start until the file was fixed by hand.
"""
import json
import tempfile
import unittest
from pathlib import Path

from gui import tournament_tree as tree
from planner.store import JsonStore


class SavedOrderTest(unittest.TestCase):
    def columns(self, cols: dict) -> dict:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tournaments.json"
            path.write_text(json.dumps({"version": 1, "columns": cols}), encoding="utf-8")
            return tree.load_columns(JsonStore.at(path))

    def test_an_order_with_no_column_numbers_in_it_loads(self):
        for order in ([None, 1, 2], ["title", 0], [[0], 1], [0, 1.5, 2]):
            with self.subTest(order):
                got = self.columns({"hidden": [], "order": order, "count": 3})
                self.assertTrue(all(isinstance(c, int) for c in got["order"]))

    def test_the_column_numbers_in_it_are_kept(self):
        got = self.columns({"hidden": [], "order": [2, None, 0, 1],
                            "count": tree._TRACK_COLS})
        self.assertEqual(got["order"], [2, 0, 1])

    def test_a_good_order_is_untouched(self):
        order = list(reversed(range(tree._TRACK_COLS)))
        got = self.columns({"hidden": [1], "order": order, "count": tree._TRACK_COLS})
        self.assertEqual(got["order"], order)


if __name__ == "__main__":
    unittest.main()
