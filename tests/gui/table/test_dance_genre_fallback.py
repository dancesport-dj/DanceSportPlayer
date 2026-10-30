#!/usr/bin/env python3
"""The Dance column falls back to the track's own genre.

Run:  py -m unittest tests.gui.table.test_dance_genre_fallback -v

A file whose dance cannot be determined is not a blank cell: the social genre
label comes first (Boogie Woogie, Line Dance), then the plain genre tag. Both
the playlist table and the library pane read that order.
"""

import os
import tempfile
import types
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dancegenre_"))

from PySide6.QtWidgets import QApplication, QWidget

from gui.library_browser import LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_DIR = Path(tempfile.mkdtemp(prefix="dp_dancegenre_m_"))
_COL_DANCE = 0


def _e(title, dance=None, other_genre=None, tag_genre=None):
    path = _DIR / f"{title}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=title, dance=dance, duration=150,
                      other_genre=other_genre, tag_genre=tag_genre)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class DanceColumnFallbackTest(unittest.TestCase):
    """The Dance cell never stays blank when the file names a genre."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        entries = [_e("Boogie 1", other_genre="Boogie Woogie"),
                   _e("Whatever 1", tag_genre="Pop"),
                   _e("PD 1", "PD")]
        t.load_warmup(entries, "ETDS Party", "", "S", True, lambda _p: None, None)
        return t

    def cell_of(self, t, title):
        row = next(r for r, m in t._row_meta.numbered() if m.entry.title == title)
        return t.item(row, _COL_DANCE).text()

    def test_a_boogie_woogie_shows_its_genre(self):
        t = self.table()
        self.assertEqual(self.cell_of(t, "Boogie 1"), "Boogie Woogie")

    def test_an_unknown_genre_shows_the_plain_tag(self):
        t = self.table()
        self.assertEqual(self.cell_of(t, "Whatever 1"), "Pop")

    def test_a_known_dance_keeps_its_name(self):
        t = self.table()
        self.assertEqual(self.cell_of(t, "PD 1"), "Paso Doble")


class WishlistDanceColumnTest(unittest.TestCase):
    """A wishlist row reads its dance from the track itself, so the genre
    fallback fills there exactly as it does in a deck."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wishlist(self, entries):
        t = PlaylistTable()
        t.list_kind = "wishlist"
        t.resize(700, 400)
        self.addCleanup(reap_widget, t)
        t.load_wishlist(entries, play_cb=lambda *a: None, suggester=None)
        return t

    def cell_of(self, t, title):
        row = next(r for r, m in t._row_meta.numbered() if m.entry.title == title)
        return t.item(row, _COL_DANCE).text()

    def test_a_boogie_woogie_is_named_in_the_wishlist(self):
        t = self.wishlist([_e("Boogie 1", other_genre="Boogie Woogie")])
        self.assertEqual(self.cell_of(t, "Boogie 1"), "Boogie Woogie")

    def test_a_line_dance_is_named_in_the_wishlist(self):
        t = self.wishlist([_e("LD 1", other_genre="Line Dance")])
        self.assertEqual(self.cell_of(t, "LD 1"), "Line Dance")

    def test_a_plain_genre_tag_fills_the_wishlist_cell(self):
        t = self.wishlist([_e("Whatever 1", tag_genre="Pop")])
        self.assertEqual(self.cell_of(t, "Whatever 1"), "Pop")

    def test_a_wishlist_track_with_a_dance_keeps_its_name(self):
        t = self.wishlist([_e("PD 1", "PD")])
        self.assertEqual(self.cell_of(t, "PD 1"), "Paso Doble")


class LibraryDanceColumnTest(unittest.TestCase):
    """The library pane's Dance column uses the same fallback order."""

    def label(self, entry):
        # Only `_short_dances` is read, so a stand-in object is enough.
        return LibraryBrowser._dance_label(types.SimpleNamespace(_short_dances=False),
                                           entry)

    def test_no_dance_falls_back_to_the_plain_tag(self):
        self.assertEqual(self.label(_e("T", tag_genre="Pop")), "Pop")

    def test_a_social_label_comes_before_the_plain_tag(self):
        self.assertEqual(self.label(_e("T", other_genre="Boogie Woogie",
                                       tag_genre="Pop")), "Boogie Woogie")


class ShortDanceGenreFallbackTest(unittest.TestCase):
    """The genre fallback in short mode: the same switch writes BW and LD here
    as it writes LW and SB for the competition dances."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def label(self, entry):
        return LibraryBrowser._dance_label(types.SimpleNamespace(_short_dances=True),
                                           entry)

    def test_the_library_writes_a_line_dance_as_ld(self):
        self.assertEqual(self.label(_e("T", other_genre="Line Dance")), "LD")

    def test_a_raw_genre_tag_naming_the_dance_shortens_too(self):
        """Only the TCON text names it, no social label - the label still
        reaches the same short table."""
        self.assertEqual(self.label(_e("T", tag_genre="Boogie Woogie")), "BW")

    def test_a_plain_genre_keeps_its_text(self):
        self.assertEqual(self.label(_e("T", tag_genre="Pop")), "Pop")

    def test_the_wishlist_cell_reads_bw(self):
        t = PlaylistTable()
        t.list_kind = "wishlist"
        t.resize(700, 400)
        self.addCleanup(reap_widget, t)
        t.load_wishlist([_e("Boogie 1", other_genre="Boogie Woogie")],
                        play_cb=lambda *a: None, suggester=None)
        t.set_short_dances(True)
        row = next(r for r, m in t._row_meta.numbered()
                   if m.entry.title == "Boogie 1")
        self.assertEqual(t.item(row, _COL_DANCE).text(), "BW")


if __name__ == "__main__":
    unittest.main(verbosity=2)
