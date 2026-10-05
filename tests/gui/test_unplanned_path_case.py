#!/usr/bin/env python3
"""🆕 Unplanned hides a planned track by its path, whatever its letter case.

Run:  py -m unittest tests.gui.test_unplanned_path_case -v

The deck side of the match lowercases every path (Windows paths are
case-insensitive), the library browser looks each track up by `str(path)` as
it is. So any path with a capital letter in it — `F:\\my music\\Tanzcds\\…` —
never matched, and a planned track stayed in the list unless its fingerprint
happened to be on record.
"""

import functools
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gui.main_decks import DeckLayoutMixin
from gui.main_dupes import DuplicateCheckMixin


class UnplannedPathCaseTest(unittest.TestCase):

    def test_a_planned_track_with_capitals_in_its_path_is_hidden(self):
        planned = SimpleNamespace(path=Path(r"F:\My Music\Tanzcds\Moon River (LW 29).mp3"))
        other = SimpleNamespace(path=Path(r"F:\My Music\Tanzcds\Fly Me (QS 50).mp3"))
        deck = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: [planned]))
        browser = mock.Mock()
        browser.unplanned_active.return_value = True
        win = SimpleNamespace(
            _cache=None, _lib_browser=browser,
            _lib=SimpleNamespace(entries=[planned, other]),
            _visible_deck_tables=lambda: [deck])
        win._deck_dedup_index = functools.partial(
            DuplicateCheckMixin._deck_dedup_index, win)

        DeckLayoutMixin._refresh_library_planned_filter(win)

        hidden = browser.set_planned_paths.call_args.args[0]
        # The browser's own test: `str(e.path) in self._planned_paths`.
        self.assertIn(str(planned.path), hidden)
        self.assertNotIn(str(other.path), hidden)


if __name__ == "__main__":
    unittest.main(verbosity=2)
