#!/usr/bin/env python3
"""A title's playlist match keys come from one split of its path.

Run:  py -m unittest tests.planner.music.test_match_keys_one_split -v

Marcel picked "do 2" from the title-matching speedups: `_match_keys` turned
the path into a string and a file name once per key, three times a title.
It now splits the path once: 3.28 -> 2.87 s over his 49 860 titles. The
keys must not change by a single character, because popularity and playlist
history hang on them: a name with a dot in it ('03. …', 'Mr. Saxobeat')
loses text if the already-split name is split a second time.
"""

import unittest
import unittest.mock
from pathlib import Path

from planner.models import MusicEntry
from planner.music import parsing
from planner.music.library import MusicLibrary
from planner.music.playlist_index import _dq

_NAMES = [
    r"F:\my music\lateincd\08 1-16 SB50 El Sonador (Samba 50).mp3",
    r"F:\my music\standardcd\03. Mr. Saxobeat (QS 50).mp3",
    r"F:\my music\standardcd\LW29 - Moon River DJ Ice.flac",
    r"F:\my music\lateincd\Ai Que Dó (CC 31) cut.mp3",
    r"F:\my music\lateincd\Casey Kasem - Rhythm.mp3",
    r"F:\my music\x\No extension",
    r"F:\my music\x\Ends with a dot..mp3",
    r"F:\my music\x\.hidden.mp3",
    r"F:\my music\x\42.mp3",
]


def _keys_from_the_full_path(entry: MusicEntry) -> set[str]:
    """What `_match_keys` returned before: each key from the full path string."""
    name, d = str(entry.path), entry.dance
    keys = {parsing._stem_key(name)}
    if tkey := parsing._title_key(name):
        keys.add(_dq(d, tkey))
    if len(skey := parsing._song_title_key(name)) >= 3:
        keys.add(_dq(d, skey))
    if entry.tag_title:
        if len(tt := parsing._norm_title(entry.tag_title)) >= 3:
            keys.add(_dq(d, tt))
        if entry.tag_artist:
            at = parsing._norm_title(f"{entry.tag_artist} {entry.tag_title}")
            if len(at) >= 3:
                keys.add(_dq(d, at))
    return keys


class OneSplitTest(unittest.TestCase):

    def test_the_keys_are_the_ones_the_full_path_gives(self):
        lib = MusicLibrary()
        for name in _NAMES:
            for dance, tag_title, tag_artist in ((None, "", ""), ("SB", "Sonador", "Raul")):
                entry = MusicEntry(path=Path(name), title="t", dance=dance,
                                   tag_title=tag_title, tag_artist=tag_artist)
                with self.subTest(name=name, dance=dance):
                    self.assertEqual(lib._match_keys(entry), _keys_from_the_full_path(entry))

    def test_the_path_is_split_once(self):
        entry = MusicEntry(path=Path(_NAMES[1]), title="t", dance="QS")
        real = Path.stem.fget
        calls = []

        def counted(p):
            calls.append(p)
            return real(p)

        with unittest.mock.patch.object(Path, "stem", property(counted)):
            MusicLibrary()._match_keys(entry)
        self.assertEqual(len(calls), 1, calls)


if __name__ == "__main__":
    unittest.main()
