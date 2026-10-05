#!/usr/bin/env python3
"""Right-click on a playlist's name: 📂 Show in Explorer opens the folder of the
.m3u the playlist was loaded from or last saved to.

Run:  py -m unittest tests.gui.test_deck_file_reveal -v

A song row already has the same entry for its audio file. The deck has to
remember its file for that: an import and a save both set it, emptying the deck
drops it, and the session file carries it over a restart.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_deck_reveal_"))

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtWidgets import QMenu  # noqa: E402

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_DIR = Path(tempfile.mkdtemp(prefix="dp_deck_reveal_files_"))


def _entry(name, dance="CC"):
    path = _DIR / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, duration=180)


class _RightClick:
    """What `_on_header_press` reads off a mouse event."""

    def button(self):
        return Qt.MouseButton.RightButton

    def globalPosition(self):
        return QPointF(10, 10)


class DeckFileRevealTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_deck_reveal_qs_"))
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

    def header_menu(self, pick: str | None = None, table=None):
        """Open the deck header's right-click menu; return {text: enabled} and,
        when `pick` starts an action's text, choose that action."""
        from gui import main_decks

        table = table if table is not None else self.table
        seen = {}

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

        with mock.patch.object(main_decks, "QMenu", _Menu):
            self.win._on_header_press(_RightClick(), table)
        return seen

    def reveal_entry(self, menu: dict):
        found = [(t, on) for t, on in menu.items() if "Show in Explorer" in t]
        self.assertEqual(len(found), 1, list(menu))
        return found[0]

    def write_m3u(self, name="Tanzparty.m3u") -> Path:
        m3u = _DIR / name
        tracks = [_entry(n) for n in ("a1", "a2")]
        self.win._lib.entries = tracks   # empty stubs only resolve from the library
        m3u.write_text("#EXTM3U\n" + "\n".join(str(e.path) for e in tracks) + "\n",
                       encoding="utf-8")
        return m3u

    def test_a_playlist_that_was_never_a_file_offers_it_greyed_out(self):
        text, enabled = self.reveal_entry(self.header_menu())
        self.assertFalse(enabled, text)

    def test_the_entry_reveals_the_playlist_file(self):
        m3u = self.write_m3u()
        self.table._m3u_path = m3u
        from gui import main_decks
        with mock.patch.object(main_decks, "reveal_in_explorer") as reveal:
            menu = self.header_menu(pick="📂")
        self.assertTrue(self.reveal_entry(menu)[1])
        reveal.assert_called_once()
        self.assertEqual(Path(reveal.call_args.args[0]), m3u)

    def test_loading_an_m3u_as_a_running_order_remembers_the_file(self):
        m3u = self.write_m3u()
        self.win._load_player_list_from_m3u(self.table, str(m3u))
        self.assertEqual(self.table._m3u_path, m3u)

    def test_save_as_remembers_the_file(self):
        out = _DIR / "Gespeichert.m3u"
        from gui import main_export
        with mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                               return_value=(str(out), "")), \
                mock.patch.object(main_export, "save_settings"):
            self.win._on_table_save_requested(self.table)
        self.assertTrue(out.exists())
        self.assertEqual(self.table._m3u_path, out)

    def test_emptying_the_playlist_forgets_the_file(self):
        self.table._m3u_path = self.write_m3u()
        self.win._blank_deck(self.table)
        self.assertIsNone(self.table._m3u_path)

    def test_the_file_comes_back_with_the_session(self):
        m3u = self.write_m3u()
        self.table._m3u_path = m3u
        env = self.win._build_env()
        self.win._apply_env({})          # a desk with nothing on it
        self.assertIsNone(self.table._m3u_path)
        self.win._apply_env(env)
        self.assertEqual(self.table._m3u_path, m3u)

    # ── ⭐ wishlists get the same entry ────────────────────────────────────────
    def wishlist(self, index=0, names=("w1", "w2")):
        wish = self.win._wishlists[index]
        tracks = [_entry(n) for n in names]
        self.win._lib.entries = tracks
        wish.load_wishlist(tracks, play_cb=None, suggester=None)
        return wish

    def test_a_wishlist_offers_it_greyed_out_before_it_is_a_file(self):
        text, enabled = self.reveal_entry(self.header_menu(table=self.wishlist()))
        self.assertFalse(enabled, text)

    def test_a_wishlist_reveals_its_file(self):
        wish = self.wishlist()
        wish._m3u_path = self.write_m3u("Wunsch.m3u")
        from gui import main_decks
        with mock.patch.object(main_decks, "reveal_in_explorer") as reveal:
            menu = self.header_menu(pick="📂", table=wish)
        self.assertTrue(self.reveal_entry(menu)[1])
        self.assertEqual(Path(reveal.call_args.args[0]), wish._m3u_path)

    def test_a_wishlist_can_still_be_renamed_from_the_menu(self):
        wish = self.wishlist()
        with mock.patch.object(self.win, "_begin_inline_rename") as rename:
            menu = self.header_menu(pick="✏", table=wish)
        self.assertTrue(any("Rename" in t for t in menu), list(menu))
        rename.assert_called_once_with(wish)

    def test_save_all_remembers_the_wishlist_file(self):
        wish = self.wishlist()
        from gui import main_export
        out_dir = _DIR / "saveall"
        box = mock.MagicMock()
        box.clickedButton.return_value = None
        with mock.patch.object(main_export, "OUTPUT_DIR", out_dir), \
                mock.patch("planner.m3u.OUTPUT_DIR", out_dir), \
                mock.patch.object(main_export, "QMessageBox", return_value=box):
            self.win._save_all_playlists()
        self.assertIsNotNone(wish._m3u_path)
        self.assertTrue(wish._m3u_path.exists())
        self.assertEqual(wish._m3u_path.parent.name, "wishlists")

    def test_emptying_a_wishlist_forgets_the_file(self):
        wish = self.wishlist()
        wish._m3u_path = self.write_m3u("Wunsch.m3u")
        self.win._reset_wishlist_name(wish)
        self.assertIsNone(wish._m3u_path)

    def test_swapping_two_wishlists_swaps_their_files(self):
        a, b = self.wishlist(0), self.wishlist(1, ("w3",))
        a._m3u_path = self.write_m3u("A.m3u")
        b._m3u_path = None
        self.win._swap_wishlists(a, b)
        self.assertIsNone(a._m3u_path)
        self.assertEqual(b._m3u_path, _DIR / "A.m3u")

    def test_the_wishlist_file_comes_back_with_the_session(self):
        wish = self.wishlist()
        m3u = self.write_m3u("Wunsch.m3u")
        wish._m3u_path = m3u
        env = self.win._build_env()
        self.win._apply_env({})          # a desk with nothing on it
        self.assertIsNone(self.win._wishlists[0]._m3u_path)
        self.win._apply_env(env)
        self.assertEqual(self.win._wishlists[0]._m3u_path, m3u)


if __name__ == "__main__":
    unittest.main(verbosity=2)
