"""🏆 The window's half of "Load into…": the playlist lands on the chosen list.

Run:  py -m unittest tests.gui.test_tournament_load_into_window -v

Decks A-D ("Playlist 1-4") are replaced after the usual question, wishlists
take the tracks flat, and the Party panel reads the file as its list. Every one
of them comes on screen, or the load looks like nothing happened.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_load_into_"))

from PySide6.QtWidgets import QApplication

from planner.models import MusicEntry
from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup

_STD = ("LW", "TG", "WW", "SF", "QS")


class LoadIntoWindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_load_into_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_load_into_m3u_"))

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._library.lib = self.lib

    def m3u(self, name, dances=_STD):
        paths = []
        for i, d in enumerate(dances):
            p = self.dir / f"{name}_{i:03d}_{d}.mp3"
            self.lib.entries.append(
                MusicEntry(path=p, title=f"{d} {i}", dance=d, duration=180))
            paths.append(str(p))
        f = self.dir / f"{name}.m3u"
        f.write_text("#EXTM3U\n" + "\n".join(paths), encoding="utf-8")
        return str(f)

    def songs(self, table):
        return table._row_meta.song_count()

    def test_playlist_3_is_loaded_into_the_third_deck(self):
        win = self.win
        deck_c = win._deckset.decks[2]
        win._load_tournament_m3u_into(self.m3u("pl3"), "deck", 3)
        self.assertEqual(self.songs(deck_c), 5)
        self.assertEqual(self.songs(win._deckset.tableA), 0, "the focused deck was spared")

    def test_the_deck_it_loads_into_comes_on_screen_and_in_focus(self):
        win = self.win
        win._deckset.deck_count = 1
        win._apply_deck_view()
        deck_d = win._deckset.decks[3]
        win._load_tournament_m3u_into(self.m3u("pl4"), "deck", 4)
        self.assertIs(win._deckset.table, deck_d)
        self.assertGreaterEqual(win._deckset.deck_count, 4)

    def test_wishlist_2_takes_the_tracks_flat(self):
        win = self.win
        wish = win._deckset.wishlists[1]
        win._load_tournament_m3u_into(self.m3u("w2"), "wish", 2)
        self.assertEqual(len(wish.wishlist_entries()), 5)
        self.assertEqual(len(win._deckset.wishlists[0].wishlist_entries()), 0)
        self.assertIs(win._focused_table, wish)

    def test_party_reads_the_file_as_its_list(self):
        win = self.win
        win._load_tournament_m3u_into(self.m3u("partyset"), "party", 1)
        self.assertEqual(self.songs(win._deckset.warmup_table), 5)
        self.assertEqual(win.deck(win._deckset.warmup_table).name, "🤸  partyset")

    def test_a_deck_that_holds_tracks_asks_before_it_is_replaced(self):
        win = self.win
        deck_a = win._deckset.decks[0]
        win._load_tournament_m3u_into(self.m3u("first"), "deck", 1)
        asked = []
        deck_a._confirm_m3u_replaces = lambda m3u: asked.append(m3u.name) or False
        win._load_tournament_m3u_into(self.m3u("second", _STD * 2), "deck", 1)
        self.assertEqual(asked, ["second.m3u"])
        self.assertEqual(self.songs(deck_a), 5, "declined: the old list stays")


if __name__ == "__main__":
    unittest.main()
