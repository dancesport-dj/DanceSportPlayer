#!/usr/bin/env python3
"""`MusicLibrary.restricted_to` — the pool view the ⚡ generator's source
selector ("open wishlists" / an .m3u file) draws from.

Run:  py -m unittest tests.planner.test_library_restrict -v

The promise is narrow on purpose: only the candidate set shrinks. Everything a
pick is scored on (popularity, the finals/semi history, the class index) is the
library's own learned data and must stay shared, and the original library must
come back unchanged — the panel switches the source back and forth.
"""

import unittest
from pathlib import Path

from planner.library import MusicLibrary
from planner.models import MusicEntry


def _entry(name, dance="SA"):
    return MusicEntry(path=Path(f"C:/lib/lateincd/{dance}/{name}.mp3"),
                      title=name, dance=dance, bpm=51)


class RestrictedToTest(unittest.TestCase):

    def _lib(self):
        lib = MusicLibrary()
        lib.entries = [_entry("a"), _entry("b"), _entry("t", "TG")]
        return lib

    def test_the_view_holds_only_the_given_entries(self):
        lib = self._lib()
        view = lib.restricted_to(lib.entries[:1])
        self.assertEqual([e.title for e in view.entries], ["a"])

    def test_the_original_library_is_untouched(self):
        lib = self._lib()
        lib.restricted_to([])
        self.assertEqual(len(lib.entries), 3)

    def test_by_dance_sees_only_the_view(self):
        lib = self._lib()
        view = lib.restricted_to([e for e in lib.entries if e.dance == "SA"])
        self.assertEqual(len(view.by_dance("SA")), 2)
        # The dance the pool has nothing for yields nothing — it does not reach
        # back into the whole library.
        self.assertEqual(view.by_dance("TG"), [])

    def test_the_path_index_is_rebuilt_for_the_subset(self):
        lib = self._lib()
        lib.entry_for(Path("C:/lib/lateincd/SA/a.mp3"))     # builds the full index
        view = lib.restricted_to([lib.entries[2]])
        self.assertIsNone(view.entry_for(Path("C:/lib/lateincd/SA/a.mp3")))
        self.assertIsNotNone(view.entry_for(Path("C:/lib/lateincd/TG/t.mp3")))
        # …and the library it came from still finds its own tracks.
        self.assertIsNotNone(lib.entry_for(Path("C:/lib/lateincd/SA/a.mp3")))

    def test_learned_playlist_data_stays_shared(self):
        lib = self._lib()
        lib._track_playlists["a.mp3"].add("some.m3u")
        view = lib.restricted_to(lib.entries)
        self.assertEqual(view._track_playlists["a.mp3"], {"some.m3u"})


if __name__ == "__main__":
    unittest.main()
