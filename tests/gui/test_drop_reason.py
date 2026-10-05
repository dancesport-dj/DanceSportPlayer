#!/usr/bin/env python3
"""What a dynamic deck says when a dropped track does not land.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_drop_reason -v

One toast lives per window and the newest message replaces the one before it
(see `_show_toast`), so a drop that ends in a summary wipes out whatever a
single track said on its way past. Dragging a wishlist track that the deck
cannot place therefore read "Already planned — nothing added" whatever the
real reason was — and the reason is usually not that at all.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reason_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

import gui.table_dynamic as table_dynamic  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402


def _planned(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, bpm=None)


def _wish(name, title, dance=None):
    """A wishlist row: the library could not say what it is, so `dance` is
    empty and `title` is the cleaned display title — the one string the dance
    marker has already been taken out of."""
    return MusicEntry(path=Path(rf"C:\wish\{name}"), title=title, dance=dance,
                      bpm=None)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}


class DropReasonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self):
        """A dynamic two-dance deck holding one heat."""
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        self.addCleanup(reap_widget, win)
        t.load({"Vorrunde": [[_planned("LW", 1), _planned("TG", 2)]]},
               ["LW", "TG"],
               [RoundConfig(name="Vorrunde", heats=1, tier="early")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        # …through the real door: _enter_dynamic is what recovers the dance
        # columns from the grid, and without them the first new column rebuilds
        # every heat as empty.
        t._enter_dynamic([1])
        t._notify_changed = lambda *a, **kw: None
        t._confirm_cross_style = lambda entries: True
        return t

    def drop(self, table, entries):
        """Drop `entries` on the first row and report every toast, in order."""
        seen = []
        real = table_dynamic._show_toast
        table_dynamic._show_toast = lambda anchor, text, *a, **kw: seen.append(text)
        table._collect_drop_entries = lambda e: list(entries)
        try:
            table._dynamic_drop(None, 0)
        finally:
            table_dynamic._show_toast = real
        return seen

    def test_a_dance_written_in_the_file_name_is_read(self):
        """The title has had the marker stripped out of it; the file name is
        where the dance still stands."""
        t = self.deck()
        seen = self.drop(t, [_wish("Something (WW 29).mp3", "Something")])
        self.assertTrue(seen and seen[-1].startswith("➕"), seen)
        planned = [e.title for e in t._iter_planned_entries()]
        self.assertIn("Something", planned)

    def test_a_track_with_no_dance_is_not_called_already_planned(self):
        t = self.deck()
        seen = self.drop(t, [_wish("Ed Sheeran - Perfect.mp3", "Perfect")])
        self.assertNotIn("Already planned — nothing added", seen)
        self.assertIn("Perfect", seen[-1])

    def test_several_tracks_with_no_dance_say_how_many(self):
        t = self.deck()
        seen = self.drop(t, [_wish("A - One.mp3", "One"),
                             _wish("B - Two.mp3", "Two")])
        self.assertNotIn("Already planned — nothing added", seen)
        self.assertIn("2", seen[-1])

    def test_a_track_really_in_the_list_still_says_so(self):
        t = self.deck()
        seen = self.drop(t, [_planned("LW", 1)])
        self.assertIn("already", seen[-1].lower())

    def test_one_lands_and_one_is_a_duplicate(self):
        t = self.deck()
        seen = self.drop(t, [_wish("Something (WW 29).mp3", "Something"),
                             _planned("LW", 1)])
        self.assertTrue(seen[-1].startswith("➕"), seen)
        self.assertIn("1", seen[-1])


if __name__ == "__main__":
    unittest.main()
