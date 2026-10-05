#!/usr/bin/env python3
"""Which pool ⚡ Generate is handed for each "Draw tracks from" choice.

Run:  .venv\Scripts\python.exe -m unittest tests.gui.test_generate_source -v

The wishlist and .m3u sources are strict on purpose: the suggester gets a
RESTRICTED view of the library and nothing else, so a dance the pool cannot
cover stays blank. Two things have to hold for that to be honest — the view
really carries only the chosen tracks, and an empty choice stops the run with
a reason instead of silently planning from the whole library.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gensrc_"))

from gui import main_generate as gen  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


def _entry(name, dance="SA"):
    return MusicEntry(path=Path(f"C:/lib/lateincd/{dance}/{name}.mp3"),
                      title=name, dance=dance, bpm=51)


class _Wishlist:
    def __init__(self, entries):
        self._entries = entries

    def wishlist_entries(self):
        return list(self._entries)


class _Dlg:
    def finish(self, *_a):
        pass


class _Cfg:
    def __init__(self, source):
        self._source = source

    def get_source(self):
        return self._source


class _Win:
    """MainWindow reduced to what `_source_library` reads."""

    def __init__(self, source, lib_entries, wishlists=(), m3u_entries=()):
        self._lib = MusicLibrary()
        self._lib.entries = list(lib_entries)
        self._cfg = _Cfg(source)
        self._wishlists = list(wishlists)
        self._m3u_entries = list(m3u_entries)

    _source_library = gen.GenerateMixin._source_library

    def _m3u_progress(self, _path):
        return _Dlg(), (lambda *_a, **_k: None)

    def _entries_from_m3u_file(self, _path, _tick=None):
        return list(self._m3u_entries)


class GenerateSourceTest(unittest.TestCase):

    @staticmethod
    def _titles(lib):
        return [e.title for e in lib.entries]

    def test_the_default_source_is_the_untouched_library(self):
        win = _Win(("library", ""), [_entry("A"), _entry("B")])
        lib, label, problem = win._source_library()
        self.assertIs(lib, win._lib)
        self.assertEqual((label, problem), ("", ""))

    def test_the_wishlist_source_carries_only_parked_tracks(self):
        parked = _entry("Parked")
        win = _Win(("wishlists", ""), [_entry("A"), parked],
                   wishlists=[_Wishlist([parked])])
        lib, label, problem = win._source_library()
        self.assertEqual(self._titles(lib), ["Parked"])
        self.assertEqual(self._titles(win._lib), ["A", "Parked"])   # untouched
        self.assertIn("wishlists", label)
        self.assertEqual(problem, "")

    def test_the_same_track_in_two_wishlists_is_pooled_once(self):
        parked = _entry("Parked")
        win = _Win(("wishlists", ""), [parked],
                   wishlists=[_Wishlist([parked]), _Wishlist([parked])])
        self.assertEqual(self._titles(win._source_library()[0]), ["Parked"])

    def test_empty_wishlists_stop_the_run_with_a_reason(self):
        win = _Win(("wishlists", ""), [_entry("A")], wishlists=[_Wishlist([])])
        lib, _label, problem = win._source_library()
        self.assertIsNone(lib)
        self.assertIn("wishlists are empty", problem)

    def test_the_m3u_source_carries_only_that_files_tracks(self):
        picked = _entry("Picked")
        win = _Win(("m3u", "C:/lists/party.m3u"), [_entry("A")],
                   m3u_entries=[picked])
        lib, label, problem = win._source_library()
        self.assertEqual(self._titles(lib), ["Picked"])
        self.assertEqual(label, "📂 party.m3u")
        self.assertEqual(problem, "")

    def test_an_m3u_that_resolves_to_nothing_stops_the_run(self):
        win = _Win(("m3u", "C:/lists/party.m3u"), [_entry("A")])
        lib, _label, problem = win._source_library()
        self.assertIsNone(lib)
        self.assertIn("party.m3u", problem)

    def test_no_file_chosen_stops_the_run(self):
        win = _Win(("m3u", ""), [_entry("A")])
        lib, _label, problem = win._source_library()
        self.assertIsNone(lib)
        self.assertIn("Choose an .m3u file", problem)

    def test_the_restricted_view_answers_by_dance_from_the_pool_alone(self):
        """The suggester picks per dance — the whole point of the view."""
        parked = _entry("Parked", "CC")
        win = _Win(("wishlists", ""), [_entry("A", "CC"), parked],
                   wishlists=[_Wishlist([parked])])
        lib = win._source_library()[0]
        self.assertEqual([e.title for e in lib.by_dance("CC")], ["Parked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
