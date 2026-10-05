#!/usr/bin/env python3
"""Σ badge under a playlist: ▸ opens a second line with the songs per dance.

Run:  py -m unittest tests.gui.test_deck_dance_counts -v

The badge reads "Σ  12 songs  ·  ~40:00". A click on it (the arrow shows it can
be opened) adds "LW 3 · TG 3 · …" in running order, for every playlist at once,
and the choice is kept in the settings.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dance_counts_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from gui.main_decks import dance_counts_line  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_MUSIC = Path(tempfile.mkdtemp(prefix="dp_dance_counts_music_"))


def _entry(name, dance=None, other_genre=None, duration=180):
    path = _MUSIC / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, other_genre=other_genre,
                      duration=duration)


class DanceCountsLineTest(unittest.TestCase):

    def test_counts_in_running_order(self):
        entries = [_entry("r1", "RB"), _entry("c1", "CC"), _entry("r2", "RB"),
                   _entry("l1", "LW")]
        self.assertEqual(dance_counts_line(entries), "LW 1 · CC 1 · RB 2")

    def test_social_dances_and_the_rest_last(self):
        entries = [_entry("x"), _entry("d1", other_genre="Discofox"),
                   _entry("s1", "SA")]
        self.assertEqual(dance_counts_line(entries), "SB 1 · DF 1 · other 1")

    def test_social_dances_read_their_short_codes(self):
        entries = [_entry(n, other_genre=g) for n, g in (
            ("f", "Forró"), ("k", "Kizomba"), ("w", "West Coast Swing"),
            ("b", "Bachata"), ("s", "Salsa"), ("d", "Discofox"))]
        self.assertEqual(dance_counts_line(entries),
                         "DF 1 · SL 1 · BC 1 · WCS 1 · KZ 1 · FR 1")

    def test_tango_argentino_reads_ta(self):
        # Marcel: "Tango Argentino hat TA" — not the internal TANGOARG.
        entries = [_entry("t1", "TANGOARG")]
        self.assertEqual(dance_counts_line(entries), "TA 1")

    def test_samba_and_jive_read_sb_and_jv(self):
        entries = [_entry("j1", "JI"), _entry("s1", "SA"), _entry("c1", "CC")]
        self.assertEqual(dance_counts_line(entries), "SB 1 · CC 1 · JV 1")


class BadgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_dance_counts_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        self.table = self.win._tableB
        self.table.load_player_list(
            [_entry("c1", "CC"), _entry("r1", "RB"), _entry("c2", "CC")],
            "Party", play_cb=None)
        self.win._update_deck_totals()
        self.badge = self.win.deck(self.table).total_lbl

    def test_closed_it_is_one_line_with_an_arrow(self):
        text = self.badge.text()
        self.assertTrue(text.startswith("▸"), text)
        self.assertIn("3 songs", text)
        self.assertNotIn("\n", text)

    def test_a_click_opens_the_dances_and_a_second_closes_them(self):
        QTest.mouseClick(self.badge, Qt.MouseButton.LeftButton)
        text = self.badge.text()
        self.assertTrue(text.startswith("▾"), text)
        self.assertEqual(text.split("\n")[1], "CC 2 · RB 1")
        self.assertTrue(self.win._settings.get("totals_by_dance"))

        QTest.mouseClick(self.badge, Qt.MouseButton.LeftButton)
        self.assertNotIn("\n", self.badge.text())
        self.assertFalse(self.win._settings.get("totals_by_dance"))

    def test_the_line_follows_the_list(self):
        QTest.mouseClick(self.badge, Qt.MouseButton.LeftButton)
        self.table.load_player_list([_entry("l1", "LW")], "Party", play_cb=None)
        self.win._update_deck_totals()
        self.assertEqual(self.badge.text().split("\n")[1], "LW 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
