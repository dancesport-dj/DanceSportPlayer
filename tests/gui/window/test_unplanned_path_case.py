#!/usr/bin/env python3
"""🆕 Unplanned hides a planned track by its path, whatever its letter case.

Run:  py -m unittest tests.gui.window.test_unplanned_path_case -v

The deck side of the match lowercases every path (Windows paths are
case-insensitive), the library browser looks each track up by `str(path)` as
it is. So any path with a capital letter in it — `F:\\my music\\Tanzcds\\…` —
never matched, and a planned track stayed in the list unless its fingerprint
happened to be on record.
"""

import functools
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_unplanned_case_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from gui.window.main_decks import DeckLayoutMixin
from gui.window.main_dupes import DuplicateCheckMixin
from planner.models import MusicEntry
from planner.playlist.planned import path_key
from tests.qt_test_support import reap_widget


class UnplannedPathCaseTest(unittest.TestCase):

    def test_a_planned_track_with_capitals_in_its_path_is_hidden(self):
        planned = SimpleNamespace(path=Path(r"F:\My Music\Tanzcds\Moon River (LW 29).mp3"))
        other = SimpleNamespace(path=Path(r"F:\My Music\Tanzcds\Fly Me (QS 50).mp3"))
        deck = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: [planned]))
        browser = mock.Mock()
        browser.unplanned_active.return_value = True
        win = SimpleNamespace(
            _library=SimpleNamespace(
                cache=None, lib=SimpleNamespace(entries=[planned, other]), global_lib=None),
            _lib_browser=browser,
            _visible_deck_tables=lambda: [deck])
        win._deck_dedup_index = functools.partial(
            DuplicateCheckMixin._deck_dedup_index, win)

        DeckLayoutMixin._refresh_library_planned_filter(win)

        hidden = browser.set_planned_paths.call_args.args[0]
        # The browser looks each track up by its `path_key`.
        self.assertIn(path_key(planned.path), hidden)
        self.assertNotIn(path_key(other.path), hidden)


    def test_a_planned_track_only_in_the_whole_library_is_hidden(self):
        """🌐 lists the global index, which the favorites need not hold: the
        planned set then carries the deck's lower-cased path only, and the
        browser's case-sensitive lookup kept the track (BUG_REVIEW B5.6)."""
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        planned = MusicEntry(path=Path(r"F:\My Music\Tanzcds\Moon River (LW 29).mp3"),
                             title="Moon River", dance="LW")
        other = MusicEntry(path=Path(r"F:\My Music\Tanzcds\Fly Me (QS 50).mp3"),
                           title="Fly Me", dance="QS")
        deck = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: [planned]))
        browser = LibraryBrowser()
        self.addCleanup(reap_widget, browser)
        browser.set_entries([])
        browser.set_whole_entries([planned, other])
        win: Any = SimpleNamespace(
            _library=SimpleNamespace(cache=None, lib=SimpleNamespace(entries=[]),
                                     global_lib=None),
            _lib_browser=browser,
            _visible_deck_tables=lambda: [deck])
        win._deck_dedup_index = functools.partial(
            DuplicateCheckMixin._deck_dedup_index, win)
        browser._unplanned_chk.blockSignals(True)
        browser._unplanned_chk.setChecked(True)
        browser._unplanned_chk.blockSignals(False)

        DeckLayoutMixin._refresh_library_planned_filter(win)

        self.assertEqual([e.title for e in browser._shown], ["Fly Me"])

    def test_a_copy_of_a_planned_track_in_the_whole_library_is_hidden(self):
        """The favorites are matched by content too, so a copy of a planned
        recording at another path counts as planned. The 🌐 index was matched
        by path alone: its copy stayed listed."""
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        on_deck = MusicEntry(path=Path(r"F:\Favorites\Moon River (LW 29).mp3"),
                             title="Moon River", dance="LW")
        copy = MusicEntry(path=Path(r"F:\Repository\LW\Moon River.mp3"),
                          title="Moon River", dance="LW")
        other = MusicEntry(path=Path(r"F:\Repository\QS\Fly Me.mp3"),
                           title="Fly Me", dance="QS")
        fps = {str(on_deck.path): "fp-moon", str(copy.path): "fp-moon",
               str(other.path): "fp-fly"}
        cache = SimpleNamespace(fingerprint=lambda p: fps.get(str(p)),
                                recorded_fingerprint=lambda p: fps.get(str(p)))
        deck = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: [on_deck]))
        browser = LibraryBrowser()
        self.addCleanup(reap_widget, browser)
        browser.set_entries([on_deck])
        browser._unplanned_chk.blockSignals(True)
        browser._unplanned_chk.setChecked(True)
        browser._unplanned_chk.blockSignals(False)
        win: Any = SimpleNamespace(
            _library=SimpleNamespace(cache=cache, lib=SimpleNamespace(entries=[on_deck]),
                                     global_lib=SimpleNamespace(entries=[copy, other])),
            _lib_browser=browser,
            _visible_deck_tables=lambda: [deck])
        win._deck_dedup_index = functools.partial(
            DuplicateCheckMixin._deck_dedup_index, win)
        browser.unplannedToggled.connect(
            lambda on: DeckLayoutMixin._refresh_library_planned_filter(win))

        browser.set_whole_entries([copy, other])

        self.assertEqual([e.title for e in browser._shown], ["Fly Me"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
