#!/usr/bin/env python3
"""The strict no-repeat must not treat another track of the same artist as used.

Run:  py -m unittest tests.planner.generate.test_no_repeat_keys -v
"""

import unittest
from pathlib import Path

from planner.generate.suggester import is_used, mark_used
from planner.models import MusicEntry
from planner.music.parsing import song_use_keys


def _entry(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{name}"), title=name, dance="RB",
                      bpm=None, popularity=3)


class NoRepeatKeysTest(unittest.TestCase):

    def test_another_track_by_the_same_artist_is_not_used(self):
        used: set = set()
        mark_used(used, _entry("Michael Buble - Sway.mp3"))
        self.assertFalse(is_used(_entry("Michael Buble - Home.mp3"), used))

    def test_another_recording_of_the_same_song_is_used(self):
        used: set = set()
        mark_used(used, _entry("Michael Buble - Sway.mp3"))
        self.assertTrue(is_used(_entry("Sway (RB 30).mp3"), used))

    def test_the_same_file_is_used(self):
        used: set = set()
        e = _entry("Michael Buble - Sway.mp3")
        mark_used(used, e)
        self.assertTrue(is_used(e, used))


class TitleFirstNamesTest(unittest.TestCase):
    """Library names in the opposite order, 'Title - CODE-Artist': the part after
    the last dash is the artist (or a bitrate, or a disc number), not the song."""

    ROSS = ("01 - Baila Con Migo - CC 31-Ross Mitchell.mp3",
            "02 - Wheels - CC 31-Ross Mitchell.mp3")

    def test_the_artist_behind_a_tempo_code_is_no_use_key(self):
        for name in self.ROSS:
            with self.subTest(name=name):
                self.assertNotIn("ross mitchell", song_use_keys(name))

    def test_two_songs_of_one_artist_share_no_use_key(self):
        self.assertFalse(set(song_use_keys(self.ROSS[0])) & set(song_use_keys(self.ROSS[1])))

    def test_a_bitrate_or_disc_tail_is_no_use_key_and_the_title_before_it_is(self):
        for name, tail in (("Dj Mitya Vs Bruno Mars - Treasure - (cha-cha31)128kb.mp3", "128kb"),
                           ("Foo - Treasure - cd 1.mp3", "cd 1"),
                           ("Foo - Treasure - mav 1.mp3", "mav 1"),
                           ("Foo - Treasure - 51bpm.mp3", "51bpm")):
            with self.subTest(name=name):
                keys = song_use_keys(name)
                self.assertNotIn(tail, keys)
                self.assertIn("treasure", keys)

    def test_the_one_pass_split_agrees_with_song_use_keys_on_every_shape(self):
        from planner.music.parsing import song_extra_keys, song_use_and_extra_keys
        names = (*self.ROSS, "Michael Buble - Sway.mp3", "Sway (RB 30).mp3", "LW - Autumn.mp3",
                 "Zaz - Paris - rumba remix - (Dj Mitya).mp3", "Foo - Treasure - cd 1.mp3",
                 "Dj Mitya Vs Bruno Mars - Treasure - (cha-cha31)128kb.mp3",
                 "01 Be my love - Werner Tauber.mp3", "Rhythm.mp3", "Kygo - Hot Stuff - 50.mp3",
                 "Jive - Edoardo Bennato - Il Gatto e la Volpe.mp3", "Artist - Mr. Brightside.mp3")
        for name in names:
            with self.subTest(name=name):
                use, extra = song_use_and_extra_keys(name)
                self.assertEqual(use, song_use_keys(name))
                self.assertEqual(extra, song_extra_keys(name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
