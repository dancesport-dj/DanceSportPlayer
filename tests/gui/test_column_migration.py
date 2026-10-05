"""Column choices saved before ★ Rating and Custom existed still mean the same columns.

Run:  py -m unittest tests.gui.test_column_migration -v

The ticks, widths and the library's order are saved by column INDEX. ★ came in
at 9 in the decks (↺ moved to 10 and stays last) and at 10 in the library, so a
saved 9 means ↺ in an old file and ★ in a new one. Custom came next, at 10 in
the decks (↺ to 11) and at 11 in the library. Marcel wanted both hidden until
asked for.
"""
import unittest

from gui.dialogs import COLUMNS_VERSION, migrate_column_settings
from shared.columns import _COL_CUSTOM, _COL_RATING, _COL_REGEN


class MigrateColumnSettingsTest(unittest.TestCase):

    def test_the_real_settings_file(self):
        """The shape of Marcel's gui_settings.json on 2026-10-03."""
        s = {"hidden_columns": {"wishlist": [1, 9]},
             "column_widths": {"playlist": {"0": 119, "8": 60, "9": 30}},
             "library_hidden_columns": [],
             "library_col_widths": {"0": 30, "9": 52}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {"0": 119, "8": 60, str(_COL_REGEN): 30})
        self.assertEqual(s["library_hidden_columns"], [10, 11])
        self.assertEqual(s["library_col_widths"], {"0": 30, "9": 52})
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)

    def test_runs_once(self):
        s = {"hidden_columns": {"wishlist": [1, 9]}}
        migrate_column_settings(s)
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_REGEN]})

    def test_a_kind_ticked_all_on_gets_the_rating_hidden(self):
        """A saved empty list is a decision about the OLD columns only."""
        s = {"hidden_columns": {"playlist": []}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"], {"playlist": [_COL_RATING, _COL_CUSTOM]})

    def test_a_saved_library_order_keeps_working(self):
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9]
        s = {"library_columns": list(order)}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], order + [10, 11])

    def test_a_fresh_install_starts_with_the_rating_hidden(self):
        s = {"hidden_columns": {}, "library_hidden_columns": []}
        migrate_column_settings(s)
        self.assertEqual(s["library_hidden_columns"], [10, 11])


class CustomColumnMigrationTest(unittest.TestCase):
    """Settings saved with ★ already in (columns_version 2)."""

    def test_regen_moves_behind_custom(self):
        s = {"columns_version": 2,
             "hidden_columns": {"playlist": [9], "wishlist": [1, 9, 10]},
             "column_widths": {"playlist": {"8": 60, "9": 72, "10": 30}}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [_COL_RATING, _COL_CUSTOM],
                          "wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {"8": 60, str(_COL_RATING): 72, str(_COL_REGEN): 30})
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)

    def test_the_library_gets_it_at_the_end(self):
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9, 10]
        s = {"columns_version": 2, "library_columns": list(order),
             "library_hidden_columns": [8]}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], order + [11])
        self.assertEqual(s["library_hidden_columns"], [8, 11])

    def test_a_shown_rating_stays_shown(self):
        s = {"columns_version": 2, "library_hidden_columns": [],
             "hidden_columns": {"playlist": []}}
        migrate_column_settings(s)
        self.assertEqual(s["library_hidden_columns"], [11])
        self.assertEqual(s["hidden_columns"], {"playlist": [_COL_CUSTOM]})

    def test_a_current_file_is_left_alone(self):
        s = {"columns_version": COLUMNS_VERSION, "hidden_columns": {"playlist": [10]}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"], {"playlist": [10]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
