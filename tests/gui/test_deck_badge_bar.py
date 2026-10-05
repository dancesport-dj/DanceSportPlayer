#!/usr/bin/env python3
"""The bar under a deck: the Σ count in German, and the switch beside it.

Run:  py -m unittest tests.gui.test_deck_badge_bar -v

Two things about that one bar.

The count is built as an f-string — `f"Σ  {n} song{'s' if n != 1 else ''}"` —
so the word "songs" could never reach the catalog, and the badge read
"Σ  12 songs  ·  ~40:00" with a German ⏭ Automatik sitting next to it. The
per-dance line under it has the same hole in "other".

And when that line is open the badge is two rows tall while the ⏭/✋ switch
stayed one row, pinned to the top — deliberately, so it would not float in
the middle of a tall badge. Growing with the bar is the third option, and
the one that keeps the two reading as one strip.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_badgebar_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from gui.main_decks import dance_counts_line  # noqa: E402
from planner import i18n  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_MUSIC = Path(tempfile.mkdtemp(prefix="dp_badgebar_music_"))


def _entry(name, dance=None, duration=180):
    path = _MUSIC / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, duration=duration)


class _Desk(unittest.TestCase):
    """A real main window with one loaded deck."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_badgebar_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def desk(self, language, songs):
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        win._lib = MusicLibrary()
        table = win._tableB
        table.load_player_list(songs, "Party", play_cb=None)
        win._settings["totals_by_dance"] = False
        win._update_deck_totals()
        return win, table


class BadgeWordsTest(_Desk):

    def badge(self, language, songs):
        win, table = self.desk(language, songs)
        return win.deck(table).total_lbl

    def test_english_is_unchanged(self):
        text = self.badge("en", [_entry("c1", "CC"), _entry("r1", "RB")]).text()
        self.assertIn("2 songs", text)

    def test_the_count_says_lieder(self):
        text = self.badge("de", [_entry("c1", "CC"), _entry("r1", "RB")]).text()
        self.assertNotIn("songs", text)
        self.assertIn("Lieder", text)

    def test_one_song_is_singular(self):
        text = self.badge("de", [_entry("c1", "CC")]).text()
        self.assertNotIn("song", text)
        self.assertIn("1 Lied", text)

    def test_the_dance_line_calls_the_rest_something_german(self):
        """"other 1" sits on the second line of the same badge."""
        i18n.set_active("de")
        line = dance_counts_line([_entry("x"), _entry("c1", "CC")])
        self.assertNotIn("other", line)
        self.assertIn("CC 1", line)

    def test_the_dance_line_is_unchanged_in_english(self):
        self.assertEqual(dance_counts_line([_entry("x"), _entry("c1", "CC")]),
                         "CC 1 · other 1")


class SwitchHeightTest(_Desk):
    """The ⏭/✋ switch grows with the badge instead of perching on top."""

    def heights(self):
        """The bar's own height and the switch's, closed and then opened.

        Measured on the bar rather than the window: the deck boxes sit in a
        splitter that never gets a real geometry pass under the offscreen
        platform, so `adjustSize()` on the bar is what makes it take the
        height its contents ask for.
        """
        win, table = self.desk("en", [_entry("c1", "CC"), _entry("r1", "RB")])
        table.set_advance_toggle(lambda: True, lambda _on: None)
        table.set_advance_toggle_visible(True)
        win.show()
        self.addCleanup(win.hide)
        badge = win.deck(table).total_lbl
        btn = table.advance_toggle()
        row = win.deck(table).badge_row

        def measure():
            win._update_deck_totals()
            row.adjustSize()            # the bar takes the height it asks for
            row.layout().invalidate()
            row.layout().setGeometry(row.rect())   # …and hands it down
            QTest.qWait(1)
            return row.height(), btn.height()

        closed = measure()
        QTest.mouseClick(badge, Qt.MouseButton.LeftButton)
        return closed, measure()

    def test_the_switch_fills_the_bar_when_the_dances_are_open(self):
        (row_closed, btn_closed), (row_open, btn_open) = self.heights()
        self.assertGreater(row_open, row_closed,
                           "the bar never grew — the dance line did not open")
        self.assertEqual(btn_open, row_open,
                         "the ⏭/✋ switch stayed short beside a tall badge")

    def test_the_switch_still_fits_the_closed_bar(self):
        (row_closed, btn_closed), _open = self.heights()
        self.assertEqual(btn_closed, row_closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
