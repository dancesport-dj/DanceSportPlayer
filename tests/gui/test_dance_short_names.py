#!/usr/bin/env python3
"""↔ The Dance column, written short: "LW" instead of "Langsamer Walzer".

Run:  py -m unittest tests.gui.test_dance_short_names -v

"Langsamer Walzer" is 16 characters of a column that has to share a narrow
window with Artist and Title, and on a small screen the operator pays for it in
Title width. The Σ song-count line under every list has read "LW 3 · TG 3 · DF
2" for a while; the column can now be switched to exactly those labels — same
dict, so Samba is SB and Jive JV there as well, and the social dances keep
their own short codes.

It is a per-KIND option like the column ticks next to it in the header's
right-click menu: switched in one wishlist, switched in all four.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_shortdance_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared.columns import _COL_DANCE  # noqa: E402
from gui.main_decks import dance_counts_line  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _e(dance, n, other_genre=None):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None,
                      other_genre=other_genre)


class _DanceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, kind="playlist") -> PlaylistTable:
        t = PlaylistTable()
        t.list_kind = kind
        self.addCleanup(reap_widget, t)
        t.resize(900, 400)
        return t

    def deck(self, dances=("LW", "SA", "JI")) -> PlaylistTable:
        t = self.table()
        playlist = {"Vorrunde": [[_e(d, 1) for d in dances]]}
        rounds = [RoundConfig(name="Vorrunde", heats=1, tier="early")]
        t.load(playlist, list(dances), rounds, "S",
               play_cb=lambda *a: None, suggester=None, use_timbre=False)
        return t

    def cells(self, t) -> list:
        """The Dance column, song rows only."""
        return [t.item(r, _COL_DANCE).text() for r in t._row_meta.song_rows()]

    def headers(self, t) -> list:
        """The span rows — round and dance headers."""
        return [t.item(r, 0).text().strip()
                for r, m in enumerate(t._row_meta)
                if m is None and t.item(r, 0) is not None]


class ShortDanceNamesTest(_DanceTest):

    def test_a_deck_spells_the_dance_out_by_default(self):
        self.assertEqual(self.cells(self.deck()),
                         ["Langsamer Walzer", "Samba", "Jive"])

    def test_switched_on_the_column_reads_the_way_the_sigma_line_does(self):
        t = self.deck()
        t.set_short_dances(True)
        self.assertEqual(self.cells(t), ["LW", "SB", "JV"])

    def test_the_column_and_the_sigma_line_use_the_same_labels(self):
        """"like in the song count label view" — literally the same dict."""
        t = self.deck()
        t.set_short_dances(True)
        line = dance_counts_line(t._row_meta.entries())
        self.assertEqual([part.split()[0] for part in line.split(" · ")],
                         self.cells(t))

    def test_a_social_dance_keeps_its_own_short_code(self):
        t = self.table(kind="wishlist")
        t.load_wishlist([_e("DISCOFOX", 1), _e("BACHATA", 2)],
                        play_cb=lambda *a: None, suggester=None)
        self.assertEqual(self.cells(t), ["Discofox", "Bachata"])
        t.set_short_dances(True)
        self.assertEqual(self.cells(t), ["DF", "BC"])

    def test_switching_back_spells_them_out_again(self):
        t = self.deck()
        t.set_short_dances(True)
        t.set_short_dances(False)
        self.assertEqual(self.cells(t), ["Langsamer Walzer", "Samba", "Jive"])

    def test_a_list_loaded_afterwards_is_written_short_too(self):
        """The option outlives the rows it was switched on for."""
        t = self.table(kind="wishlist")
        t.set_short_dances(True)
        t.load_wishlist([_e("LW", 1), _e("SA", 2)],
                        play_cb=lambda *a: None, suggester=None)
        self.assertEqual(self.cells(t), ["LW", "SB"])

    def test_the_dance_headers_still_spell_it_out(self):
        """A header row spans the whole table — it has the room the column
        doesn't, and "LW" alone over a block of songs reads worse."""
        t = self.deck(dances=("LW", "SA"))
        t.set_short_dances(True)
        heads = " | ".join(self.headers(t))
        self.assertIn("Langsamer Walzer", heads)
        self.assertIn("Samba", heads)

    def test_it_reads_back(self):
        t = self.deck()
        self.assertFalse(t.short_dances())
        t.set_short_dances(True)
        self.assertTrue(t.short_dances())


class ShortDanceMenuTest(_DanceTest):

    def _act(self, menu):
        """The one checkable action that is not a column tick."""
        return next(a for a in menu.actions()
                    if a.isCheckable() and a.data() is None)

    def test_the_header_menu_offers_it(self):
        t = self.deck()
        menu = t.build_column_menu()
        act = self._act(menu)
        self.assertFalse(act.isChecked())
        self.assertIn("LW", act.text())
        menu.deleteLater()

    def test_the_tick_switches_the_column_and_tells_the_window(self):
        t = self.table(kind="wishlist")
        t.load_wishlist([_e("SA", 1)], play_cb=lambda *a: None,
                        suggester=None)
        seen = []
        t.set_dance_names_callback(lambda kind, on: seen.append((kind, on)))
        menu = t.build_column_menu()
        self._act(menu).trigger()
        self.assertEqual(self.cells(t), ["SB"])
        self.assertEqual(seen, [("wishlist", True)])
        menu.deleteLater()

    def test_ticking_it_off_says_so_too(self):
        t = self.table(kind="party")
        t.load_wishlist([_e("SA", 1)], play_cb=lambda *a: None,
                        suggester=None)
        t.set_short_dances(True)
        seen = []
        t.set_dance_names_callback(lambda kind, on: seen.append((kind, on)))
        menu = t.build_column_menu()
        act = self._act(menu)
        self.assertTrue(act.isChecked())
        act.trigger()
        self.assertEqual(self.cells(t), ["Samba"])
        self.assertEqual(seen, [("party", False)])
        menu.deleteLater()


if __name__ == "__main__":
    unittest.main(verbosity=2)
