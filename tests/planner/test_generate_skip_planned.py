#!/usr/bin/env python3
"""⚡ Generate can leave out the greyed titles — those already planned or played.

Run:  py -m unittest tests.planner.test_generate_skip_planned -v

Tier 4 #14: a tick in the config panel keeps a competition round from
picking a title another deck already holds (played ones stay in their deck,
greyed, so they count too). The deck being replaced does not count against
the draw: its content is going away.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_skipplan_"))

from gui.window import main_generate as gen
from gui.window.main_dupes import DuplicateCheckMixin
from planner.models import MusicEntry
from planner.music.library import MusicLibrary


def _entry(name):
    return MusicEntry(path=Path(f"C:/lib/lateincd/SA/{name}.mp3"),
                      title=name, dance="SA", bpm=51)


class _Win:
    """The MainWindow reduced to what `_skip_planned` reads."""

    def __init__(self, skip, planned_elsewhere=(), planned_here=()):
        self._cfg = SimpleNamespace(skip_planned=lambda: skip)
        self._library = SimpleNamespace(cache=None)
        self._target = self._table(planned_here)
        self._deckset = SimpleNamespace(table=self._target)
        self._other = self._table(planned_elsewhere)

    @staticmethod
    def _table(entries):
        meta = SimpleNamespace(entries=lambda: list(entries))
        return SimpleNamespace(_row_meta=meta)

    def _planned_source_tables(self):
        return [self._target, self._other]

    _skip_planned = gen.GenerateMixin._skip_planned
    _deck_dedup_index = DuplicateCheckMixin._deck_dedup_index


def _lib(*names):
    lib = MusicLibrary()
    lib.entries.extend(_entry(n) for n in names)
    return lib


class SkipPlannedTest(unittest.TestCase):

    @staticmethod
    def _titles(lib):
        return [e.title for e in lib.entries]

    def test_off_hands_the_library_back_untouched(self):
        lib = _lib("A", "B")
        win = _Win(False, planned_elsewhere=[_entry("A")])
        self.assertIs(win._skip_planned(lib), lib)

    def test_on_leaves_out_what_another_deck_holds(self):
        win = _Win(True, planned_elsewhere=[_entry("A")])
        self.assertEqual(self._titles(win._skip_planned(_lib("A", "B"))), ["B"])

    def test_the_deck_being_replaced_does_not_count(self):
        win = _Win(True, planned_here=[_entry("A")])
        self.assertEqual(self._titles(win._skip_planned(_lib("A", "B"))),
                         ["A", "B"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
