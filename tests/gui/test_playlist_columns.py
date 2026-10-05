#!/usr/bin/env python3
"""↔ Resizing and hiding the columns of a deck / wishlist / party list.

Run:  py -m unittest tests.gui.test_playlist_columns -v

Two complaints, one header. Title could not be dragged at all — it was the one
column left on `Stretch`, and Qt does not let the user resize a stretched
section, so the handle beside Artist worked and the one beside Title did not.
And there was no way to put a column away: every list showed all ten, whether
its kind had any use for them (Heat and ↺ mean nothing in a wishlist).

So every column is Interactive, Title keeps soaking up the leftover width on a
resize (that is what Stretch was there for), and a right-click on the header
ticks columns on and off — remembered per KIND of list, so hiding Heat in one
wishlist hides it in all of them and leaves the decks alone.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cols_"))

from PySide6.QtWidgets import QApplication, QHeaderView  # noqa: E402

from shared.columns import (  # noqa: E402
    _COL_ARTIST, _COL_BPM, _COL_DANCE, _COL_HEAT, _COL_POP, _COL_REGEN,
    _COL_TITLE, _N_COLS,
)
from gui.playlist_table import PlaylistTable  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _TableTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, kind="playlist") -> PlaylistTable:
        t = PlaylistTable()
        t.list_kind = kind
        self.addCleanup(reap_widget, t)
        t.resize(900, 400)
        return t


class ResizableTest(_TableTest):

    def test_every_column_can_be_dragged(self):
        """Stretch is not draggable — that is why Title's handle did nothing."""
        hh = self.table().horizontalHeader()
        for c in range(_N_COLS):
            self.assertEqual(hh.sectionResizeMode(c),
                             QHeaderView.ResizeMode.Interactive,
                             f"column {c} is not user-resizable")

    def test_the_title_column_still_takes_the_leftover_width(self):
        """What Stretch was for: no empty gap on the right of the table."""
        t = self.table()
        t.show()
        t.resize(1000, 400)
        QApplication.processEvents()
        others = sum(t.columnWidth(c) for c in range(_N_COLS)
                     if c != _COL_TITLE and not t.isColumnHidden(c))
        self.assertAlmostEqual(t.columnWidth(_COL_TITLE),
                               t.viewport().width() - others, delta=2)

    def test_a_narrower_table_shrinks_the_title_not_the_rest(self):
        t = self.table()
        t.show()
        t.resize(1000, 400)
        QApplication.processEvents()
        artist = t.columnWidth(_COL_ARTIST)
        wide = t.columnWidth(_COL_TITLE)
        t.resize(700, 400)
        QApplication.processEvents()
        self.assertEqual(t.columnWidth(_COL_ARTIST), artist)
        self.assertLess(t.columnWidth(_COL_TITLE), wide)

    def test_a_dragged_width_survives_until_the_table_is_resized(self):
        t = self.table()
        t.show()
        t.resize(1000, 400)
        QApplication.processEvents()
        t.setColumnWidth(_COL_ARTIST, 320)
        QApplication.processEvents()
        self.assertEqual(t.columnWidth(_COL_ARTIST), 320)


class HideColumnsTest(_TableTest):

    def test_a_hidden_column_is_hidden(self):
        t = self.table()
        t.set_hidden_columns([_COL_HEAT, _COL_POP])
        self.assertTrue(t.isColumnHidden(_COL_HEAT))
        self.assertTrue(t.isColumnHidden(_COL_POP))
        self.assertFalse(t.isColumnHidden(_COL_DANCE))

    def test_what_is_hidden_reads_back(self):
        t = self.table()
        t.set_hidden_columns([_COL_POP, _COL_HEAT])
        self.assertEqual(t.hidden_columns(), [_COL_HEAT, _COL_POP])

    def test_showing_them_again_restores_the_width_they_had(self):
        """A column that comes back 0 px wide reads as still missing."""
        t = self.table()
        t.show()
        t.resize(1000, 400)
        QApplication.processEvents()
        was = t.columnWidth(_COL_POP)
        t.set_hidden_columns([_COL_POP])
        t.set_hidden_columns([])
        QApplication.processEvents()
        self.assertFalse(t.isColumnHidden(_COL_POP))
        self.assertEqual(t.columnWidth(_COL_POP), was)

    def test_the_title_column_cannot_be_put_away(self):
        """Without it a row cannot be told apart from any other."""
        t = self.table()
        t.set_hidden_columns([_COL_TITLE, _COL_POP])
        self.assertFalse(t.isColumnHidden(_COL_TITLE))
        self.assertEqual(t.hidden_columns(), [_COL_POP])

    def test_the_leftover_width_is_re_shared_when_a_column_goes(self):
        t = self.table()
        t.show()
        t.resize(1000, 400)
        QApplication.processEvents()
        before = t.columnWidth(_COL_TITLE)
        t.set_hidden_columns([_COL_DANCE, _COL_HEAT, _COL_POP])
        QApplication.processEvents()
        self.assertGreater(t.columnWidth(_COL_TITLE), before)


class ColumnWidthTest(_TableTest):
    """A dragged width is worth keeping — the seeded defaults are a starting
    point, not the operator's choice."""

    def flush(self, t):
        """Fire the debounce the way Qt would — only if a save is pending."""
        if t._width_timer.isActive():
            t._width_timer.stop()
            t._width_timer.timeout.emit()

    def test_the_widths_read_back_for_every_column_but_title(self):
        t = self.table()
        w = t.column_widths()
        self.assertEqual(sorted(w), [c for c in range(_N_COLS)
                                     if c != _COL_TITLE])
        self.assertEqual(w[_COL_ARTIST], t.columnWidth(_COL_ARTIST))

    def test_title_is_never_saved(self):
        """It is the leftover width, recomputed on every resize — storing it
        would only fight _fill_title_column on the next start."""
        self.assertNotIn(_COL_TITLE, self.table().column_widths())

    def test_a_saved_width_is_applied(self):
        t = self.table()
        t.set_column_widths({_COL_ARTIST: 321, _COL_BPM: 77})
        self.assertEqual(t.columnWidth(_COL_ARTIST), 321)
        self.assertEqual(t.columnWidth(_COL_BPM), 77)

    def test_json_string_keys_survive_the_round_trip(self):
        """gui_settings.json has no integer keys."""
        t = self.table()
        t.set_column_widths({"3": 210, "5": 64})
        self.assertEqual(t.columnWidth(_COL_ARTIST), 210)
        self.assertEqual(t.columnWidth(_COL_BPM), 64)

    def test_a_hidden_column_keeps_the_width_it_had(self):
        """Qt reports 0 for a hidden section; saving that would bring the column
        back as an invisible sliver."""
        t = self.table()
        t.set_column_widths({_COL_POP: 90})
        t.set_hidden_columns([_COL_POP])
        self.assertEqual(t.column_widths()[_COL_POP], 90)

    def test_dragging_a_column_tells_the_window(self):
        t = self.table(kind="wishlist")
        seen = []
        t.set_widths_callback(lambda kind, w: seen.append((kind, w)))
        t.setColumnWidth(_COL_ARTIST, 260)
        self.flush(t)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], "wishlist")
        self.assertEqual(seen[0][1][_COL_ARTIST], 260)
        self.assertEqual(t.column_widths()[_COL_ARTIST], 260)

    def test_a_whole_drag_saves_once_not_once_per_pixel(self):
        t = self.table()
        seen = []
        t.set_widths_callback(lambda kind, w: seen.append(w))
        for px in range(200, 240):
            t.setColumnWidth(_COL_ARTIST, px)
        self.flush(t)
        self.assertEqual(len(seen), 1, f"{len(seen)} saves for one drag")

    def test_the_title_soaking_up_width_is_not_a_save(self):
        """_fill_title_column resizes a section on every table resize — that is
        the app's own doing, not the user's."""
        t = self.table()
        t.show()
        seen = []
        t.set_widths_callback(lambda kind, w: seen.append(w))
        t.resize(1000, 400)
        QApplication.processEvents()
        t.resize(700, 400)
        QApplication.processEvents()
        self.flush(t)
        self.assertEqual(seen, [])

    def test_applying_saved_widths_is_not_a_save_either(self):
        t = self.table()
        seen = []
        t.set_widths_callback(lambda kind, w: seen.append(w))
        t.set_column_widths({_COL_ARTIST: 300})
        self.flush(t)
        self.assertEqual(seen, [])


class ColumnMenuTest(_TableTest):

    def test_the_header_offers_a_tick_per_column(self):
        t = self.table()
        menu = t.build_column_menu()
        # A column tick carries its column in data(); the short-dance-names
        # option under them is checkable too, and carries none.
        ticks = {a.text(): a for a in menu.actions() if a.data() is not None}
        self.assertEqual(len(ticks), _N_COLS - 1)   # Title is not offered
        self.assertTrue(all(a.isChecked() for a in ticks.values()))
        menu.deleteLater()

    def test_a_tick_hides_the_column_and_tells_the_window(self):
        t = self.table(kind="wishlist")
        seen = []
        t.set_columns_callback(lambda kind, hidden: seen.append((kind, hidden)))
        menu = t.build_column_menu()
        act = next(a for a in menu.actions()
                   if a.isCheckable() and a.data() == _COL_REGEN)
        act.trigger()
        self.assertTrue(t.isColumnHidden(_COL_REGEN))
        self.assertEqual(seen, [("wishlist", [_COL_REGEN])])
        menu.deleteLater()

    def test_ticking_it_back_on_says_so_too(self):
        t = self.table(kind="party")
        seen = []
        t.set_hidden_columns([_COL_REGEN])
        t.set_columns_callback(lambda kind, hidden: seen.append((kind, hidden)))
        menu = t.build_column_menu()
        act = next(a for a in menu.actions()
                   if a.isCheckable() and a.data() == _COL_REGEN)
        self.assertFalse(act.isChecked())
        act.trigger()
        self.assertFalse(t.isColumnHidden(_COL_REGEN))
        self.assertEqual(seen, [("party", [])])
        menu.deleteLater()

    def test_the_menu_names_the_columns_the_way_the_header_does(self):
        t = self.table()
        menu = t.build_column_menu()
        texts = [a.text() for a in menu.actions() if a.isCheckable()]
        self.assertIn("Artist", texts)
        self.assertNotIn("Title", texts)
        menu.deleteLater()


if __name__ == "__main__":
    unittest.main(verbosity=2)
