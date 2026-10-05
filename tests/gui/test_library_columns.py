#!/usr/bin/env python3
"""↔ The 🎼 library pane's header: ticking columns away, and short dance names.

Run:  py -m unittest tests.gui.test_library_columns -v

The decks and wishlists got a right-click header menu — a tick per column plus
"short dance names" — and the library pane, which is the widest list on the
desk and the one that most often has to share a small screen, did not have one.
It could already be resized column by column (and has saved those widths as
`library_col_widths` for a while); what it could not do was put a column away
or write "LW" instead of "Langsamer Walzer".

Same rules as the playlist tables: Title is never offered, a hidden column
remembers the width it had, and the labels are the Σ line's own
(`DANCE_SHORT`). Unlike them, the library is a single pane, so the choice is
one setting rather than one per kind of list.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libcols_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QContextMenuEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.library_browser import LibraryBrowser  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_COL_PLAY, _COL_DANCE, _COL_ARTIST, _COL_TITLE, _COL_BPM = 0, 1, 2, 3, 4
_COL_LEN, _COL_POP, _COL_CLASS, _COL_ADDED, _COL_LAST = 5, 6, 7, 8, 9
_COL_RATING, _COL_CUSTOM = 10, 11
_N_COLS = 12


def _e(dance, n, other_genre=None):
    return MusicEntry(path=Path(rf"C:\music\{dance or 'X'}{n}.mp3"),
                      title=f"track {n}", dance=dance, bpm=None,
                      other_genre=other_genre)


class _LibTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def browser(self, entries=()) -> LibraryBrowser:
        lb = LibraryBrowser()
        self.addCleanup(reap_widget, lb)
        lb.resize(1000, 400)
        lb.show()
        self.app.processEvents()
        if entries:
            lb.set_entries(list(entries))
            self.app.processEvents()
        return lb

    def dances(self, lb) -> dict:
        """{title -> what the Dance column says}."""
        t = lb._table
        return {t.item(r, _COL_TITLE).text(): t.item(r, _COL_DANCE).text()
                for r in range(t.rowCount())}


class LibraryHideColumnsTest(_LibTest):

    def test_the_header_offers_a_tick_per_column(self):
        lb = self.browser()
        menu = lb.build_column_menu()
        ticks = [a for a in menu.actions() if a.data() is not None]
        self.assertEqual(len(ticks), _N_COLS - 1)   # Title is not offered
        # ★ Rating and Custom start put away; every other column is on.
        self.assertEqual([a.data() for a in ticks if not a.isChecked()],
                         [_COL_RATING, _COL_CUSTOM])
        menu.deleteLater()

    def test_right_clicking_the_header_opens_it(self):
        """The ROW menu needed a contextMenuEvent override to fire at all (see
        _LibTable) — the header is a different widget, so prove a real click
        reaches it.

        The event goes to the header's VIEWPORT, which is what sits under the
        cursor; a QHeaderView is a scroll area and drops one delivered to the
        frame itself, so sending it there would prove nothing.
        """
        lb = self.browser()
        opened = []

        class _FakeMenu:
            def exec(self, *_a):
                opened.append(True)

        lb.build_column_menu = lambda: _FakeMenu()
        hh = lb._table.horizontalHeader()
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5),
                               hh.mapToGlobal(QPoint(5, 5)))
        QApplication.sendEvent(hh.viewport(), ev)
        self.app.processEvents()
        self.assertTrue(opened, "the header's right-click menu never opened")

    def test_a_tick_hides_the_column_and_says_so(self):
        lb = self.browser()
        seen = []
        lb.columnsChanged.connect(seen.append)
        menu = lb.build_column_menu()
        act = next(a for a in menu.actions() if a.data() == _COL_CLASS)
        act.trigger()
        self.assertTrue(lb._table.isColumnHidden(_COL_CLASS))
        # ★ and Custom were already off
        self.assertEqual(seen, [[_COL_CLASS, _COL_RATING, _COL_CUSTOM]])
        menu.deleteLater()

    def test_what_is_hidden_reads_back(self):
        lb = self.browser()
        lb.set_hidden_columns([_COL_POP, _COL_LAST])
        self.assertEqual(lb.hidden_columns(), [_COL_POP, _COL_LAST])

    def test_showing_it_again_restores_the_width_it_had(self):
        lb = self.browser()
        lb._table.setColumnWidth(_COL_BPM, 77)
        lb.set_hidden_columns([_COL_BPM])
        lb.set_hidden_columns([])
        self.assertEqual(lb._table.columnWidth(_COL_BPM), 77)

    def test_the_title_column_cannot_be_put_away(self):
        """A row without its title cannot be told from any other."""
        lb = self.browser()
        lb.set_hidden_columns([_COL_TITLE, _COL_POP])
        self.assertFalse(lb._table.isColumnHidden(_COL_TITLE))
        self.assertEqual(lb.hidden_columns(), [_COL_POP])

    def test_a_hidden_column_is_saved_with_the_width_it_had(self):
        """Qt reports 0 for a hidden section; saving that would bring the column
        back as an invisible sliver."""
        lb = self.browser()
        lb._table.setColumnWidth(_COL_BPM, 77)
        lb.set_hidden_columns([_COL_BPM])
        self.assertEqual(lb._table.columnWidth(_COL_BPM), 0)
        self.assertEqual(lb.column_widths()[_COL_BPM], 77)

    def test_the_freed_width_goes_to_artist_and_title(self):
        """While the pane is still auto-filling, putting a column away must not
        leave a gap on the right."""
        lb = self.browser()
        before = lb._table.columnWidth(_COL_TITLE)
        lb.set_hidden_columns(lb.hidden_columns() + [_COL_ADDED, _COL_LAST])
        self.app.processEvents()
        self.assertGreater(lb._table.columnWidth(_COL_TITLE), before)


class LibraryShortDancesTest(_LibTest):

    def test_the_dance_column_spells_it_out_by_default(self):
        lb = self.browser([_e("LW", 1), _e("SA", 2), _e("JI", 3)])
        self.assertEqual(self.dances(lb),
                         {"track 1": "Langsamer Walzer", "track 2": "Samba",
                          "track 3": "Jive"})

    def test_short_dance_names_read_the_way_the_sigma_line_does(self):
        lb = self.browser([_e("LW", 1), _e("SA", 2), _e("JI", 3)])
        lb.set_short_dances(True)
        self.assertEqual(self.dances(lb),
                         {"track 1": "LW", "track 2": "SB", "track 3": "JV"})

    def test_a_social_track_keeps_its_own_short_code(self):
        """Those have no .dance at all — the genre names the dance."""
        lb = self.browser([_e(None, 1, other_genre="Discofox"),
                           _e(None, 2, other_genre="Bachata")])
        self.assertEqual(self.dances(lb),
                         {"track 1": "Discofox", "track 2": "Bachata"})
        lb.set_short_dances(True)
        self.assertEqual(self.dances(lb),
                         {"track 1": "DF", "track 2": "BC"})

    def test_tango_argentino_by_its_genre_reads_english(self):
        """Labelled by its genre like a social track, it showed its German
        name on an English screen."""
        from planner import i18n, terms
        self.addCleanup(i18n.set_active, i18n.active_language())
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)
        i18n.set_active("en")
        terms.apply_settings({})
        lb = self.browser([_e(None, 1, other_genre="Tango Argentino")])
        self.assertEqual(self.dances(lb), {"track 1": "Argentine Tango"})
        lb.set_short_dances(True)
        self.assertEqual(self.dances(lb), {"track 1": "TA"})

    def test_a_german_genre_label_reads_english_in_both_modes(self):
        from planner import i18n, terms
        self.addCleanup(i18n.set_active, i18n.active_language())
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)
        i18n.set_active("en")
        terms.apply_settings({})
        lb = self.browser([_e(None, 1, other_genre="Einmarsch")])
        self.assertEqual(self.dances(lb), {"track 1": "Entrance"})
        lb.set_short_dances(True)
        self.assertEqual(self.dances(lb), {"track 1": "Entrance"})

    def test_a_genre_that_is_no_dance_is_left_as_it_is(self):
        lb = self.browser([_e(None, 1, other_genre="Schlager")])
        lb.set_short_dances(True)
        self.assertEqual(self.dances(lb), {"track 1": "Schlager"})

    def test_switching_back_spells_them_out_again(self):
        lb = self.browser([_e("LW", 1)])
        lb.set_short_dances(True)
        lb.set_short_dances(False)
        self.assertEqual(self.dances(lb), {"track 1": "Langsamer Walzer"})

    def test_a_list_filled_afterwards_is_written_short_too(self):
        lb = self.browser()
        lb.set_short_dances(True)
        lb.set_entries([_e("SA", 1)])
        self.app.processEvents()
        self.assertEqual(self.dances(lb), {"track 1": "SB"})

    def test_it_reads_back(self):
        lb = self.browser()
        self.assertFalse(lb.short_dances())
        lb.set_short_dances(True)
        self.assertTrue(lb.short_dances())

    def test_the_menu_offers_it_and_says_so(self):
        lb = self.browser([_e("SA", 1)])
        seen = []
        lb.danceNamesChanged.connect(seen.append)
        menu = lb.build_column_menu()
        act = next(a for a in menu.actions()
                   if a.isCheckable() and a.data() is None)
        self.assertIn("LW", act.text())
        act.trigger()
        self.assertEqual(self.dances(lb), {"track 1": "SB"})
        self.assertEqual(seen, [True])
        menu.deleteLater()


class LibraryColumnWiringTest(unittest.TestCase):
    """The window keeps the pane's choices in gui_settings.json."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        cls.app = QApplication.instance() or QApplication([])
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_libwire_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        import gui.main_decks as md
        self.written = []
        real = md.save_settings
        md.save_settings = self.written.append
        self.addCleanup(lambda: setattr(md, "save_settings", real))

    def window(self, settings: dict | None = None):
        self.gui.load_settings = lambda *_a, **_kw: dict(settings or {})
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win

    def test_a_hidden_library_column_is_saved(self):
        win = self.window()
        win._lib_browser.set_hidden_columns([_COL_POP])
        win._lib_browser.columnsChanged.emit([_COL_POP])
        self.assertEqual(win._settings["library_hidden_columns"], [_COL_POP])
        self.assertTrue(self.written, "nothing was saved")

    def test_saved_library_columns_come_back_on_the_next_start(self):
        win = self.window({"library_hidden_columns": [_COL_CLASS, _COL_LAST]})
        self.assertEqual(win._lib_browser.hidden_columns(),
                         [_COL_CLASS, _COL_LAST])

    def test_short_dance_names_are_saved_and_come_back(self):
        win = self.window()
        win._lib_browser.danceNamesChanged.emit(True)
        self.assertTrue(win._settings["library_short_dances"])
        self.assertTrue(self.written, "nothing was saved")
        win2 = self.window({"library_short_dances": True})
        self.assertTrue(win2._lib_browser.short_dances())


if __name__ == "__main__":
    unittest.main(verbosity=2)
