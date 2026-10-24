"""Column choices saved before ★ Rating and Custom existed still mean the same columns.

Run:  py -m unittest tests.gui.test_column_migration -v

The ticks, widths and the library's order are saved by column INDEX. ★ came in
at 9 in the decks (↺ moved to 10 and stays last) and at 10 in the library, so a
saved 9 means ↺ in an old file and ★ in a new one. Custom came next, at 10 in
the decks (↺ to 11) and at 11 in the library, then File name at 11 (↺ to 12)
and 12, then Album at 12 (↺ to 13) and 13. Marcel wanted all four hidden
until asked for. 🔁 Plays came in at 14 in the decks (↺ to 15) and not at
all in the library, whose saved columns it leaves as they were.
"""
import unittest

from gui.dialogs import COLUMNS_VERSION, migrate_column_settings
from shared.columns import (_COL_ALBUM, _COL_COMMENT, _COL_CUSTOM, _COL_FILE, _COL_PLAYS, _COL_RATING,
                            _COL_REGEN)


class MigrateColumnSettingsTest(unittest.TestCase):

    def test_the_real_settings_file(self):
        """The shape of Marcel's gui_settings.json on 2026-10-03."""
        s = {"hidden_columns": {"wishlist": [1, 9]},
             "column_widths": {"playlist": {"0": 119, "8": 60, "9": 30}},
             "library_hidden_columns": [],
             "library_col_widths": {"0": 30, "9": 52}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {"0": 119, "8": 60, str(_COL_REGEN): 30})
        self.assertEqual(s["library_hidden_columns"], [10, 11, 12, 13, 14, 15])
        self.assertEqual(s["library_col_widths"], {"0": 30, "9": 52})
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)

    def test_runs_once(self):
        s = {"hidden_columns": {"wishlist": [1, 9]}}
        migrate_column_settings(s)
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS, _COL_REGEN]})

    def test_a_kind_ticked_all_on_gets_the_rating_hidden(self):
        """A saved empty list is a decision about the OLD columns only."""
        s = {"hidden_columns": {"playlist": []}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"], {"playlist": [_COL_RATING, _COL_CUSTOM, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS]})

    def test_a_saved_library_order_keeps_working(self):
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9]
        s = {"library_columns": list(order)}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], order + [10, 11, 12, 13, 14, 15])

    def test_a_fresh_install_starts_with_the_rating_hidden(self):
        s = {"hidden_columns": {}, "library_hidden_columns": []}
        migrate_column_settings(s)
        self.assertEqual(s["library_hidden_columns"], [10, 11, 12, 13, 14, 15])


class CustomColumnMigrationTest(unittest.TestCase):
    """Settings saved with ★ already in (columns_version 2)."""

    def test_regen_moves_behind_custom(self):
        s = {"columns_version": 2,
             "hidden_columns": {"playlist": [9], "wishlist": [1, 9, 10]},
             "column_widths": {"playlist": {"8": 60, "9": 72, "10": 30}}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [_COL_RATING, _COL_CUSTOM, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS],
                          "wishlist": [1, _COL_RATING, _COL_CUSTOM, _COL_FILE,
                                       _COL_ALBUM, _COL_COMMENT, _COL_PLAYS, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {"8": 60, str(_COL_RATING): 72, str(_COL_REGEN): 30})
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)

    def test_the_library_gets_it_at_the_end(self):
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9, 10]
        s = {"columns_version": 2, "library_columns": list(order),
             "library_hidden_columns": [8]}
        migrate_column_settings(s)
        self.assertEqual(s["library_columns"], order + [11, 12, 13, 14, 15])
        self.assertEqual(s["library_hidden_columns"], [8, 11, 12, 13, 14, 15])

    def test_a_shown_rating_stays_shown(self):
        s = {"columns_version": 2, "library_hidden_columns": [],
             "hidden_columns": {"playlist": []}}
        migrate_column_settings(s)
        self.assertEqual(s["library_hidden_columns"], [11, 12, 13, 14, 15])
        self.assertEqual(s["hidden_columns"], {"playlist": [_COL_CUSTOM, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS]})

    def test_album_comes_in_hidden_in_front_of_regen(self):
        """Settings saved with File name already in (columns_version 4)."""
        order = [3, 2, 0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        s = {"columns_version": 4,
             "hidden_columns": {"playlist": [1, 11], "wishlist": [12]},
             "column_widths": {"playlist": {"11": 240, "12": 30}},
             "library_columns": list(order), "library_hidden_columns": [12]}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"],
                         {"playlist": [1, _COL_FILE, _COL_ALBUM, _COL_COMMENT, _COL_PLAYS],
                          "wishlist": [_COL_ALBUM, _COL_COMMENT, _COL_PLAYS, _COL_REGEN]})
        self.assertEqual(s["column_widths"]["playlist"],
                         {str(_COL_FILE): 240, str(_COL_REGEN): 30})
        self.assertEqual(s["library_columns"], order + [13, 14, 15])
        self.assertEqual(s["library_hidden_columns"], [12, 13, 14, 15])

    def test_a_current_file_is_left_alone(self):
        s = {"columns_version": COLUMNS_VERSION, "hidden_columns": {"playlist": [10]}}
        migrate_column_settings(s)
        self.assertEqual(s["hidden_columns"], {"playlist": [10]})

    def test_a_hand_edited_value_resets_the_layout_instead_of_the_start(self):
        # load_settings runs this at start-up: a ValueError here stopped the app.
        for bad in ({"columns_version": "six"},
                    {"hidden_columns": {"playlist": ["x"]}},
                    {"library_columns": [0, None]}):
            with self.subTest(bad=bad):
                s = {"hidden_columns": {"playlist": [1]}, "theme": "light", **bad}
                with self.assertLogs("dancesport.gui", "WARNING"):
                    migrate_column_settings(s)
                self.assertNotIn("hidden_columns", s)
                self.assertNotIn("library_columns", s)
                self.assertEqual(s["columns_version"], COLUMNS_VERSION)
                self.assertEqual(s["theme"], "light")

    def test_a_version_below_one_counts_as_the_oldest(self):
        # Stepping up from -3 asked for columns no version ever added (KeyError).
        s = {"columns_version": -3, "hidden_columns": {"playlist": [1]}}
        migrate_column_settings(s)
        self.assertEqual(s["columns_version"], COLUMNS_VERSION)
        self.assertEqual(s["hidden_columns"]["playlist"][0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
