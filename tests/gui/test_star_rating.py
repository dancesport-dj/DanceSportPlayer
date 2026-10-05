"""★ Rating: a click on a star in a deck row rates that track.

Run:  py -m unittest tests.gui.test_star_rating -v

The stars are stored as an in-app tag edit (planner.tag_edits, keyed by the
content fingerprint), not in the MP3. What matters here is the window's part:
the click reaches MusicLibrary.edit_tags, and every row showing the track
repaints — including a row holding a different MusicEntry object for the same
file (a deck restored from an M3U that names a file outside the library).
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_star_rating_"))

from PySide6.QtCore import Qt  # noqa: E402

import planner.db as pdb  # noqa: E402
from dancesport_planner import (  # noqa: E402
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from gui.library_browser import _LIB_COL_RATING  # noqa: E402
from gui.star_rating import (  # noqa: E402
    RATING_ROLE, clicked_rating, star_at, star_rects)
from planner import tag_edits  # noqa: E402
from shared.columns import _COL_RATING  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_MUSIC = Path(tempfile.mkdtemp(prefix="dp_star_music_"))


class _Cache:
    """The two AudioCache calls edit_tags makes, keyed by path (the temp files
    are empty, there is nothing to hash), plus the empty answers the window's
    repaint and autosave ask a cache for."""

    def __init__(self, fps: dict[str, str]):
        self.fps = fps

    def fingerprint(self, path):
        return self.fps.get(str(path))

    def recorded_fingerprint(self, path):
        return self.fps.get(str(path))

    def get_silences(self, *_a, **_kw):
        return None

    def lufs_count(self):
        return 0


def _entry(name: str, dance: str, **kw) -> MusicEntry:
    path = _MUSIC / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, bpm=30, **kw)


class StarHelpersTest(unittest.TestCase):

    def test_clicking_the_last_lit_star_clears_the_rating(self):
        self.assertEqual(clicked_rating(3, 3), 0)
        self.assertEqual(clicked_rating(3, 5), 5)
        self.assertEqual(clicked_rating(0, 1), 1)

    def test_the_whole_cell_is_a_target(self):
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QFont, QFontMetrics
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        fm = QFontMetrics(QFont())
        rect = QRect(0, 0, 200, 20)
        rects = star_rects(rect, fm)
        self.assertEqual(star_at(rect, fm, 0), 1)
        self.assertEqual(star_at(rect, fm, 199), 5)
        self.assertEqual(star_at(rect, fm, rects[2].center().x()), 3)


class RatingClickTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_star_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        db_dir = Path(tempfile.mkdtemp(prefix="dp_star_db_"))
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = db_dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)

        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

        self.cha = _entry("Cha One (CC 30)", "CC", rating=2)
        self.rum = _entry("Rum One (RB 25)", "RB")
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._lib = lib
        self.win._cache = _Cache({str(self.cha.path): "fpCha",
                                  str(self.rum.path): "fpRum"})
        # Deck B holds the library's object; deck C an outside copy of the
        # same file, as a restored M3U would.
        self.copy = _entry("Cha One (CC 30)", "CC", rating=2)
        self._load(self.win._tableB, self.cha)
        self._load(self.win._tableC, self.copy)
        # The 🏷 editor's "also write into the MP3?" — No: these are DB edits.
        self.win._ask_write_to_mp3 = lambda n, fields: False

    def _load(self, table, entry):
        table.load({"Runde 1": [[entry, self.rum]]}, ["CC", "RB"],
                   [RoundConfig(name="Runde 1", heats=1, tier="final")], "S",
                   play_cb=self.win._play_or_stop,
                   suggester=PlaylistSuggester(self.win._lib),
                   use_timbre=False, style="Latin", dynamic=True, capacity=[1])

    def _stars(self, table, entry) -> int:
        for r, m in table._row_meta.numbered():
            if m.entry is entry:
                return table.item(r, _COL_RATING).data(RATING_ROLE)
        self.fail(f"no row for {entry.title}")

    def _click(self, table, entry, stars):
        for r, m in table._row_meta.numbered():
            if m.entry is entry:
                table._on_star_clicked(table.model().index(r, _COL_RATING), stars)
                return
        self.fail(f"no row for {entry.title}")

    def test_a_click_stores_the_rating_in_the_database(self):
        self._click(self.win._tableB, self.cha, 5)
        self.assertEqual(self.cha.rating, 5)
        self.assertEqual(tag_edits.load("fpCha"), {"rating": 5})

    def test_every_row_showing_the_track_repaints(self):
        self._click(self.win._tableB, self.cha, 4)
        self.assertEqual(self._stars(self.win._tableB, self.cha), 4)
        self.assertEqual(self._stars(self.win._tableC, self.copy), 4)
        self.assertEqual(self.copy.rating, 4)

    def test_the_other_track_is_left_alone(self):
        self._click(self.win._tableB, self.cha, 4)
        self.assertEqual(self._stars(self.win._tableB, self.rum), 0)
        self.assertEqual(tag_edits.load("fpRum"), {})

    # ----- the 📚 library pane ------------------------------------------------

    def _lib_row(self, entry) -> int:
        t = self.win._lib_browser._table
        for r in range(t.rowCount()):
            if str(t.item(r, 0).data(Qt.ItemDataRole.UserRole)) == str(entry.path):
                return r
        self.fail(f"no library row for {entry.title}")

    def test_the_library_starts_with_the_rating_put_away(self):
        self.assertIn(_LIB_COL_RATING, self.win._lib_browser.hidden_columns())

    def test_the_library_shows_the_stars(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        it = browser._table.item(self._lib_row(self.cha), _LIB_COL_RATING)
        self.assertEqual(it.data(RATING_ROLE), 2)

    def test_a_click_in_the_library_rates_the_track_everywhere(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        row = self._lib_row(self.cha)
        browser._on_star_clicked(browser._table.model().index(row, _LIB_COL_RATING), 3)
        self.assertEqual(tag_edits.load("fpCha"), {"rating": 3})
        self.assertEqual(self._stars(self.win._tableC, self.copy), 3)
        it = browser._table.item(self._lib_row(self.cha), _LIB_COL_RATING)
        self.assertEqual(it.data(RATING_ROLE), 3)

    def test_a_deck_click_reaches_the_library_row(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        self._click(self.win._tableB, self.cha, 5)
        it = browser._table.item(self._lib_row(self.cha), _LIB_COL_RATING)
        self.assertEqual(it.data(RATING_ROLE), 5)

    # ----- two quick star clicks are not a double-click on the track ---------

    def test_a_double_click_on_the_stars_does_not_play_the_deck_row(self):
        """In playing mode a double-click puts the row on the speakers."""
        from PySide6.QtTest import QTest
        table = self.win._tableB
        table.setColumnHidden(_COL_RATING, False)
        table.resize(900, 300)
        table.show()
        self.app.processEvents()
        seen = []
        table._on_row_double_clicked = lambda row, col: seen.append(col)
        row = next(r for r, m in table._row_meta.numbered() if m.entry is self.cha)
        pos = table.visualRect(table.model().index(row, _COL_RATING)).center()
        QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        self.assertEqual(seen, [])

    def test_a_double_click_on_the_stars_does_not_open_the_library_file(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        opened = []
        browser._open_external = opened.append
        browser._on_double_click(self._lib_row(self.cha), _LIB_COL_RATING)
        self.assertEqual(opened, [])

    # ----- the 🏷 editor dialog's result, stored by the window ----------------

    class _Answer:
        """A TagEditDialog after Save (or ↺), without opening one."""

        def __init__(self, changes=None, reset=False):
            self._changes = changes or {}
            self.reset_requested = reset

        def changes_for(self, entry):
            return dict(self._changes)

        def raw_edits(self):
            return None

        def form_changes(self):
            return {}

        def form_mp3s(self):
            return []

    def test_the_editor_stores_every_field_and_repaints(self):
        self.win._apply_tag_dialog(
            [self.cha], self._Answer({"rating": 4, "classes_ok": ["A", "S"],
                                      "comment_tags": ["classic"]}))
        self.assertEqual(tag_edits.load("fpCha"),
                         {"rating": 4, "classes_ok": ["A", "S"], "comment_tags": ["classic"]})
        self.assertEqual(self.copy.classes_ok, ["A", "S"])
        self.assertEqual(self._stars(self.win._tableC, self.copy), 4)

    def test_the_editor_edits_a_whole_selection(self):
        self.win._apply_tag_dialog([self.cha, self.rum], self._Answer({"rating": 1}))
        self.assertEqual(tag_edits.load("fpCha"), {"rating": 1})
        self.assertEqual(tag_edits.load("fpRum"), {"rating": 1})

    def test_back_to_the_files_tags(self):
        self.win._apply_tag_dialog([self.cha], self._Answer({"rating": 5}))
        self.win._apply_tag_dialog([self.cha], self._Answer(reset=True))
        self.assertEqual(tag_edits.load("fpCha"), {})
        self.assertEqual((self.cha.rating, self.copy.rating), (2, 2))
        self.assertEqual(self._stars(self.win._tableC, self.copy), 2)

    def test_the_library_pane_shows_an_edited_class(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        self.win._apply_tag_dialog([self.cha], self._Answer({"classes_ok": ["S"]}))
        self.assertEqual(browser._table.item(self._lib_row(self.cha), 7).text(), "[S]")

    def _lib_menu(self, row, choose):
        """Right-click library `row` and pick `choose`; the window's editor
        records what it was handed instead of opening."""
        from unittest import mock

        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QMenu

        from gui import library_browser
        browser = self.win._lib_browser
        handed = []
        self.win._edit_entry_tags = handed.append

        class _Menu(QMenu):
            def exec(self, *_args):
                return next(a for a in self.actions() if a.text() == choose)

        class _Event:
            def pos(self):
                return QPoint(5, browser._table.rowViewportPosition(row) + 2)

            def globalPos(self):
                return QPoint(0, 0)

        with mock.patch.object(library_browser, "QMenu", _Menu):
            browser._on_context_menu(_Event())
        return handed

    def test_the_library_menu_edits_the_row(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        handed = self._lib_menu(self._lib_row(self.rum), "🏷  Edit tags…")
        self.assertEqual(handed, [[self.rum]])

    def test_the_library_menu_edits_the_selection(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        t = browser._table
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(self._lib_row(self.cha))
        t.selectRow(self._lib_row(self.rum))
        handed = self._lib_menu(self._lib_row(self.rum), "🏷  Edit tags of 2 tracks…")
        self.assertEqual(sorted(e.title for e in handed[0]), [self.cha.title, self.rum.title])

    def test_a_file_that_cannot_be_hashed_changes_nothing(self):
        self.win._cache.fps.pop(str(self.cha.path))
        self._click(self.win._tableB, self.cha, 5)
        self.assertEqual(self.cha.rating, 2)
        self.assertEqual(self._stars(self.win._tableB, self.cha), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
