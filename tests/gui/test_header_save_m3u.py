#!/usr/bin/env python3
"""Right-click on a playlist's name, or on a Group tab, saves it as .m3u.

Run:  py -m unittest tests.gui.test_header_save_m3u -v

Marcel: "right click on header of playlist should also give me option to save
playlist as m3u" — "also if i click on a tab group". A song row's menu had
💾 Save as M3U… already; the header now offers the same, and a Group A–D /
E–H tab saves every playlist on its page, the way the 📅 tab saves its
competitions.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_header_save_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QMenu  # noqa: E402

from dancesport_planner import MusicLibrary  # noqa: E402
from tests.gui.test_deck_file_reveal import _DIR, _RightClick, _entry  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402


def _menu_class(seen: dict, pick: str | None):
    class _Menu(QMenu):
        def exec(self, *_args):
            chosen = None
            for a in self.actions():
                if a.isSeparator():
                    continue
                seen[a.text()] = a.isEnabled()
                if pick and a.text().startswith(pick):
                    chosen = a
            return chosen
    return _Menu


class HeaderSaveM3uTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_header_save_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        self.table = self.win._tableB
        self.table.load_player_list([_entry("c1"), _entry("r1", "RB")],
                                    "Party", play_cb=None)

    def header_menu(self, table, pick=None) -> dict:
        from gui import main_decks
        seen = {}
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, pick)):
            self.win._on_header_press(_RightClick(), table)
        return seen

    def tab_menu(self, page, pick=None) -> dict:
        from gui import main_decks
        seen = {}
        with mock.patch.object(main_decks, "QMenu", _menu_class(seen, pick)):
            self.win._group_tab_menu(page, QPoint(10, 10))
        return seen

    # ── the header ──────────────────────────────────────────────────────────
    def test_the_deck_header_saves_it(self):
        with mock.patch.object(self.win, "_on_table_save_requested") as save:
            menu = self.header_menu(self.table, pick="💾")
        self.assertTrue(menu["💾  Save as M3U…"])
        save.assert_called_once_with(self.table)

    def test_an_empty_deck_offers_it_greyed_out(self):
        self.assertFalse(self.header_menu(self.win._tableA)["💾  Save as M3U…"])

    def test_the_wishlist_header_saves_it(self):
        wish = self.win._wishlists[0]
        tracks = [_entry("w1")]
        self.win._lib.entries = tracks
        wish.load_wishlist(tracks, play_cb=None, suggester=None)
        with mock.patch.object(self.win, "_on_table_save_requested") as save:
            self.header_menu(wish, pick="💾")
        save.assert_called_once_with(wish)

    def test_with_tournaments_it_can_file_it_too(self):
        with mock.patch.object(self.win, "_tourney_tree", mock.Mock()), \
                mock.patch.object(self.win, "_on_table_save_requested") as save:
            self.header_menu(self.table, pick="🏆")
        save.assert_called_once_with(self.table, file_in_tree=True)

    def test_without_tournaments_there_is_no_filing(self):
        with mock.patch.object(self.win, "_tourney_tree", None):
            menu = self.header_menu(self.table)
        self.assertFalse(any(t.startswith("🏆") for t in menu))

    # ── the Group tab ───────────────────────────────────────────────────────
    def test_a_group_tab_saves_every_playlist_on_its_page(self):
        page = self.win._deck_tab_index(self.table)
        other = next(t for t in self.win._decks
                     if self.win._deck_tab_index(t) != page)
        other_tracks, wish_tracks = [_entry("s1", "SA")], [_entry("w2")]
        other.load_player_list(other_tracks, "Other", play_cb=None)
        wish = self.win._wishlists[0]
        wish.load_wishlist(wish_tracks, play_cb=None, suggester=None)
        # A saved list names its titles through the library.
        self.win._lib.entries = [*self.table._row_meta.entries(),
                                 *other_tracks, *wish_tracks]
        from gui import main_export
        out_dir = _DIR / "grouptab"
        box = mock.MagicMock()
        box.clickedButton.return_value = None
        with mock.patch.object(main_export, "OUTPUT_DIR", out_dir), \
                mock.patch("planner.m3u.OUTPUT_DIR", out_dir), \
                mock.patch.object(main_export, "QMessageBox", return_value=box):
            menu = self.tab_menu(page, pick="💾")
        self.assertTrue(menu["💾  Save all playlists as M3U"])
        self.assertIsNotNone(self.table._m3u_path)
        self.assertTrue(self.table._m3u_path.exists())
        self.assertIsNone(other._m3u_path, "the other page stays unsaved")
        self.assertIsNone(wish._m3u_path, "the wishlists are not on a Group tab")

    def test_an_empty_group_tab_offers_it_greyed_out(self):
        page = self.win._deck_tab_index(self.table)
        self.win._blank_deck(self.table)
        self.assertFalse(self.tab_menu(page)["💾  Save all playlists as M3U"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
