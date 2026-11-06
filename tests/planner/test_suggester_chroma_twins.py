#!/usr/bin/env python3
"""A cut or re-encoded copy under another name is the same song to the picker.

Run:  py -m unittest tests.planner.test_suggester_chroma_twins -v

"1-04 La Cintura (SB 50)cut.mp3" next to "1-04 La Cintura (SB 50).mp3" are two
files; the picker's no-repeat sets knew a song by path and file-name title only,
so a differently named copy could be drawn too. The stored Chromaprints now
rule such twins out when the library has them.
"""

import unittest
from pathlib import Path

import numpy as np

from planner.generate.suggester import PlaylistSuggester
from planner.models import MusicEntry, rounds_from_pattern
from planner.music.chroma_twins import twin_paths
from planner.music.library import MusicLibrary

_RNG = np.random.default_rng(7)
_SONG = _RNG.integers(0, 2**32, 400, dtype=np.uint64).astype(np.uint32)
_OTHER = _RNG.integers(0, 2**32, 400, dtype=np.uint64).astype(np.uint32)
# Names that share no title key: only the audio says they are one recording.
_TWIN_A, _TWIN_B, _OTHER_SONG = "Alpha Song", "Zulu Tune", "Mango Dance"


class _Cache:
    """The three AudioCache calls the twin lookup makes."""

    def __init__(self, words_by_name):
        self.words_by_name = words_by_name

    def known_fingerprint(self, path):
        return Path(path).stem

    def all_chromas(self):
        return dict(self.words_by_name)

    def chroma_keys(self):
        return set(self.words_by_name)


def _cache(*names_and_words):
    return _Cache(dict(names_and_words))


def _library(cache) -> MusicLibrary:
    lib = MusicLibrary()
    lib.entries.extend(
        MusicEntry(path=Path(rf"C:\music\LateinCD\{n}.mp3"), title=n, dance="SA", bpm=51)
        for n in (_TWIN_A, _TWIN_B))
    lib.audio_cache = cache
    return lib


class _CountingCache(_Cache):
    """What AudioCache offers: a cheap count beside the full key list."""

    def __init__(self, words_by_name):
        super().__init__(words_by_name)
        self.keys_read = 0

    def chroma_keys(self):
        self.keys_read += 1
        return super().chroma_keys()

    def chroma_count(self):
        return len(self.words_by_name)


class ChromaTwinsTest(unittest.TestCase):

    def test_asking_for_twins_again_does_not_read_every_key(self):
        """twins() runs on every mark_used/expand_used; the key list is a full
        table read on a big library."""
        cache = _CountingCache({_TWIN_A: _SONG, _TWIN_B: _SONG.copy()})
        sugg = PlaylistSuggester(_library(cache), seed=1)
        for _ in range(4):
            self.assertTrue(sugg.twins())
        self.assertEqual(cache.keys_read, 0)

    def test_a_grown_index_is_still_noticed(self):
        cache = _CountingCache({_TWIN_A: _SONG})
        sugg = PlaylistSuggester(_library(cache), seed=1)
        self.assertEqual(sugg.twins(), {})
        cache.words_by_name[_TWIN_B] = _SONG.copy()
        self.assertTrue(sugg.twins())

    def test_two_files_with_one_chromaprint_are_twins(self):
        cache = _cache((_TWIN_A, _SONG), (_TWIN_B, _SONG.copy()), (_OTHER_SONG, _OTHER))
        paths = [rf"C:\music\{n}.mp3" for n in (_TWIN_A, _TWIN_B, _OTHER_SONG)]
        twins = twin_paths(cache, paths)
        self.assertEqual(twins[paths[0]], frozenset({paths[1]}))
        self.assertEqual(twins[paths[1]], frozenset({paths[0]}))
        self.assertNotIn(paths[2], twins)

    def test_no_cache_no_twins(self):
        self.assertEqual(twin_paths(None, ["a.mp3", "b.mp3"]), {})

    def test_a_round_does_not_draw_both_twins(self):
        lib = _library(_cache((_TWIN_A, _SONG), (_TWIN_B, _SONG.copy())))
        playlist = PlaylistSuggester(lib, seed=1).suggest(
            "S", rounds_from_pattern("2"), ["SA"], use_timbre=False, style="Latin")
        picked = [e for heats in playlist.values() for heat in heats
                  for e in heat if e is not None]
        self.assertEqual(len(picked), 1, [e.title for e in picked])

    def test_without_chroma_both_are_drawn(self):
        """The control: different names, nothing known about the audio."""
        lib = _library(None)
        playlist = PlaylistSuggester(lib, seed=1).suggest(
            "S", rounds_from_pattern("2"), ["SA"], use_timbre=False, style="Latin")
        picked = [e for heats in playlist.values() for heat in heats
                  for e in heat if e is not None]
        self.assertEqual(len(picked), 2)

    def test_a_reroll_skips_the_twin_of_a_planned_song(self):
        lib = _library(_cache((_TWIN_A, _SONG), (_TWIN_B, _SONG.copy())))
        sugg = PlaylistSuggester(lib, seed=1)
        tier = rounds_from_pattern("1")[0].tier
        planned = {str(lib.entries[0].path)}
        self.assertIsNone(sugg.regenerate("SA", "S", tier, planned,
                                          use_timbre=False, style="Latin"))

    def test_a_practice_reroll_skips_the_twin_of_a_planned_song(self):
        lib = _library(_cache((_TWIN_A, _SONG), (_TWIN_B, _SONG.copy())))
        sugg = PlaylistSuggester(lib, seed=1)
        planned = {str(lib.entries[0].path)}
        got = sugg.regenerate_warmup("SA", "Latin", "S", planned)
        self.assertNotEqual(getattr(got, "path", None), lib.entries[1].path)

    def test_a_whole_round_reroll_skips_the_twin_of_a_planned_song(self):
        """The GUI hands over a plain mark_used set — no twins in it."""
        lib = _library(_cache((_TWIN_A, _SONG), (_TWIN_B, _SONG.copy())))
        sugg = PlaylistSuggester(lib, seed=1)
        rc = rounds_from_pattern("1")[0]
        planned = {str(lib.entries[0].path)}
        heats = sugg.regenerate_round(rc, ["SA"], "S", planned,
                                      use_timbre=False, style="Latin")
        picked = [e for heat in heats for e in heat if e is not None]
        self.assertEqual(picked, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
