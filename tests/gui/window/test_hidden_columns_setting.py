"""🗂️ A damaged hidden_columns setting falls back to the default (#24)."""
import unittest

from gui.common import DEFAULT_HIDDEN_COLUMNS
from gui.window.main_deck_setup import hiddenColumnsFor


class HiddenColumnsForTest(unittest.TestCase):

    def test_a_saved_list_wins_even_when_empty(self):
        self.assertEqual(hiddenColumnsFor({"playlist": [3, "4"]}, "playlist"), [3, 4])
        self.assertEqual(hiddenColumnsFor({"playlist": []}, "playlist"), [])

    def test_a_missing_key_gives_the_default(self):
        self.assertEqual(hiddenColumnsFor({}, "wishlist"),
                         list(DEFAULT_HIDDEN_COLUMNS.get("wishlist", [])))

    def test_damaged_values_give_the_default(self):
        default = list(DEFAULT_HIDDEN_COLUMNS.get("playlist", []))
        for bad in (None, 5, "abc", ["x"], [None], [[1]]):
            with self.subTest(bad=bad):
                self.assertEqual(hiddenColumnsFor({"playlist": bad}, "playlist"), default)


if __name__ == "__main__":
    unittest.main()
