#!/usr/bin/env python3
"""↔ The column ticks reach every list of the same kind, and survive a restart.

Run:  py -m unittest tests.gui.test_playlist_column_wiring -v

A tick on one wishlist's header is not a setting for that one wishlist: there
are four of them and the user sees one at a time. It is a setting for
wishlists. Same for the decks (eight, plus eight day decks) and for the party
list. So the window fans the change out over the tables of that kind and
writes it to gui_settings.json, and a fresh window puts it back.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_colwire_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared.columns import (  # noqa: E402
    _COL_ARTIST, _COL_CUSTOM, _COL_HEAT, _COL_POP, _COL_RATING, _COL_REGEN,
)
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class ColumnWiringTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_colwire_qs_"))
        cls.gui = stub_window_startup(cls)

    def window(self, settings: dict | None = None):
        """A MainWindow whose settings are ours, and which saves nowhere real."""
        self.gui.load_settings = lambda *_a, **_kw: dict(settings or {})
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win

    def setUp(self):
        # Every window in this module writes through the same seam; patch the
        # module function so no test can reach gui_settings.json.
        import gui.main_decks as md
        self.written = []
        real = md.save_settings
        md.save_settings = self.written.append
        self.addCleanup(lambda: setattr(md, "save_settings", real))

    def test_each_table_knows_which_kind_of_list_it_is(self):
        win = self.window()
        for t in win._decks + win._day_decks:
            self.assertEqual(t.list_kind, "playlist")
        for t in win._wishlists:
            self.assertEqual(t.list_kind, "wishlist")
        self.assertEqual(win._warmup_table.list_kind, "party")

    def test_hiding_a_column_on_one_wishlist_hides_it_on_all_of_them(self):
        win = self.window()
        win._wishlist2._toggle_column(_COL_HEAT, False)
        for t in win._wishlists:
            self.assertTrue(t.isColumnHidden(_COL_HEAT),
                            "a wishlist kept the column")

    def test_the_decks_are_left_alone(self):
        win = self.window()
        win._wishlist._toggle_column(_COL_POP, False)
        for t in win._decks + win._day_decks + [win._warmup_table]:
            self.assertFalse(t.isColumnHidden(_COL_POP))

    def test_the_tick_is_written_to_the_settings(self):
        win = self.window()
        win._wishlist._toggle_column(_COL_POP, False)
        # Heat, Rating and Custom were already off
        self.assertEqual(win._settings["hidden_columns"]["wishlist"],
                         [_COL_HEAT, _COL_POP, _COL_RATING, _COL_CUSTOM])
        self.assertTrue(self.written, "nothing was saved")

    def test_a_saved_tick_comes_back_on_the_next_start(self):
        win = self.window({"hidden_columns": {"wishlist": [_COL_REGEN],
                                              "party": [_COL_HEAT]}})
        for t in win._wishlists:
            self.assertTrue(t.isColumnHidden(_COL_REGEN))
        self.assertTrue(win._warmup_table.isColumnHidden(_COL_HEAT))
        self.assertFalse(win._tableA.isColumnHidden(_COL_REGEN))

    def test_a_fresh_install_hides_heat_where_there_are_no_heats(self):
        """Heat only ever reads "Heat 2" on a deck with multiple heats per
        dance. A wishlist and a party list are flat, so the column is 56 px of
        blank — off by default, still tickable back on. ★ Rating is off
        everywhere until asked for."""
        win = self.window()
        for t in win._wishlists + [win._warmup_table]:
            self.assertEqual(t.hidden_columns(), [_COL_HEAT, _COL_RATING, _COL_CUSTOM])
        for t in win._decks + win._day_decks:
            self.assertEqual(t.hidden_columns(), [_COL_RATING, _COL_CUSTOM])

    def test_a_saved_numbers_view_reaches_the_wishlists_too(self):
        """The 🔢 state is restored per table at startup, and the wishlists were
        missing from that list exactly as they were missing from the button."""
        win = self.window({"compact": 3})
        for t in win._all_tables:
            self.assertTrue(t._numbered, "a list came back unnumbered")

    def test_a_dragged_width_is_saved_and_shared_by_the_kind(self):
        win = self.window()
        t = win._wishlist2
        t.setColumnWidth(_COL_ARTIST, 275)
        t._width_timer.stop()
        t._width_timer.timeout.emit()
        for other in win._wishlists:
            self.assertEqual(other.columnWidth(_COL_ARTIST), 275)
        self.assertEqual(
            win._settings["column_widths"]["wishlist"][str(_COL_ARTIST)], 275)
        self.assertTrue(self.written, "nothing was saved")
        self.assertNotEqual(win._tableA.columnWidth(_COL_ARTIST), 275)

    def test_saved_widths_come_back_on_the_next_start(self):
        win = self.window({"column_widths": {"wishlist": {"3": 265, "5": 71}}})
        for t in win._wishlists:
            self.assertEqual(t.columnWidth(_COL_ARTIST), 265)
        self.assertNotEqual(win._tableA.columnWidth(_COL_ARTIST), 265)

    def test_a_width_for_a_hidden_column_does_not_unhide_it(self):
        """Heat is off by default in a wishlist; a saved width is for when it
        comes back, not an instruction to bring it back."""
        win = self.window({"column_widths": {"wishlist": {"1": 99}}})
        for t in win._wishlists:
            self.assertTrue(t.isColumnHidden(_COL_HEAT))
            self.assertEqual(t.column_widths()[_COL_HEAT], 99)

    def test_short_dance_names_reach_every_list_of_the_kind(self):
        win = self.window()
        win._wishlist2.set_short_dances(True)
        win._wishlist2._notify_dance_names()
        for t in win._wishlists:
            self.assertTrue(t.short_dances(), "a wishlist kept the long names")
        self.assertTrue(win._settings["short_dances"]["wishlist"])
        self.assertTrue(self.written, "nothing was saved")
        self.assertFalse(win._tableA.short_dances())

    def test_a_saved_short_name_setting_comes_back_on_the_next_start(self):
        win = self.window({"short_dances": {"wishlist": True}})
        for t in win._wishlists:
            self.assertTrue(t.short_dances())
        self.assertFalse(win._tableA.short_dances())
        self.assertFalse(win._warmup_table.short_dances())

    def test_ticking_heat_back_on_is_remembered_over_the_default(self):
        """An empty saved list is a decision, not an absent setting."""
        win = self.window({"hidden_columns": {"wishlist": []}})
        for t in win._wishlists:
            self.assertEqual(t.hidden_columns(), [])
        self.assertEqual(win._warmup_table.hidden_columns(),
                         [_COL_HEAT, _COL_RATING, _COL_CUSTOM])


if __name__ == "__main__":
    unittest.main(verbosity=2)
