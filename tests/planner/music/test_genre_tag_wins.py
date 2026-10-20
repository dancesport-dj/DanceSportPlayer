#!/usr/bin/env python3
"""The ID3 genre tag beats the filename — for SOCIAL genres too.

Run:  py -m unittest tests.planner.music.test_genre_tag_wins -v

A filename is a guess: 'Cha Chicki Salsa 2' carries the letters 'cha' and reads
as a Cha-Cha, 'Je Ne Serai Jamais Ta Parisienne' carries 'ta' and reads as a
Tango. The genre tag is what the file itself says, so it wins — that already
held for competition dances, and it has to hold just as much when the tag names
a social genre (SL, DF, BC …). A Salsa tagged SL is not a Cha-Cha with an
opinion; it is not a competition dance at all, so neither the filename nor the
folder it sits in gets a vote.
"""

import unittest
from pathlib import Path
from unittest import mock

from mutagen.id3 import ID3, TXXX

from planner.music.library import MusicLibrary


class _NoCache:
    """A scan cache that never has the row — forces the slow ID3 path."""

    def __init__(self):
        self.data = None

    def get(self, path):
        return None

    def put(self, path, data):
        self.data = dict(data)


def _entry(name: str, genre: str | None, folder: str = "others"):
    path = Path(rf"C:\music\tanzcds\{folder}\{name}.mp3")
    with mock.patch("planner.music.library._get_raw_genre_tag", return_value=genre), \
         mock.patch("planner.music.library._get_comment_tag", return_value=None), \
         mock.patch("planner.music.library._get_title_artist_tags",
                    return_value=(None, None, None)), \
         mock.patch("planner.music.library._read_duration", return_value=180):
        return MusicLibrary()._make_entry(path, _NoCache())


class SocialGenreTagTest(unittest.TestCase):

    def test_a_salsa_tagged_sl_is_no_cha_cha(self):
        """The reported case: 'Cha Chicki Salsa 2', genre tag SL."""
        e = _entry("Cha Chicki Salsa 2", "SL")
        self.assertIsNone(e.dance)
        self.assertEqual(e.other_genre, "Salsa")

    def test_the_folder_does_not_override_it_either(self):
        """A social track filed under lateincd is still what its tag says."""
        e = _entry("Cha Chicki Salsa 2", "SL", folder="lateincd")
        self.assertIsNone(e.dance)
        self.assertEqual(e.other_genre, "Salsa")

    def test_a_competition_tag_still_wins_over_the_filename(self):
        """Unchanged: the tag beat the filename for dances all along."""
        e = _entry("Je Ne Serai Jamais Ta Parisienne", "LW")
        self.assertEqual(e.dance, "LW")
        self.assertIsNone(e.other_genre)

    def test_a_compound_tag_still_finds_the_dance_behind_the_social_part(self):
        """'SL;CC' names a dance in one of its parts — that part decides."""
        e = _entry("Some Title", "SL;CC")
        self.assertEqual(e.dance, "CC")

    def test_an_unreadable_tag_leaves_the_filename_in_charge(self):
        e = _entry("Cha Chicki Salsa 2", None)
        self.assertEqual(e.dance, "CC")

    def test_a_tag_naming_nothing_leaves_the_filename_in_charge(self):
        e = _entry("Cha Chicki Salsa 2", "Pop")
        self.assertEqual(e.dance, "CC")


def _um_entry(name: str, genre: str | None, dancestyle: str | None):
    """An entry whose tag carries UltraMixer's TXXX dance style."""
    tags = ID3()
    if dancestyle is not None:
        tags.add(TXXX(encoding=3, desc="ultramixer_dancestyle", text=[dancestyle]))
    with mock.patch("planner.music.library._read_tags_once", return_value=(tags, 180)):
        return _entry(name, genre)


class UltraMixerDanceTest(unittest.TestCase):
    """The sample 'SW29_Children_DJ Maksy': genre 'Ballroom SW', UltraMixer
    dance style 'SW' — and no dance at all came out of it."""

    def test_a_ballroom_genre_names_its_dance(self):
        e = _entry("Some Title", "Ballroom SW")
        self.assertEqual(e.dance, "LW")

    def test_a_latin_genre_names_its_dance(self):
        e = _entry("Some Title", "Latin Cha Cha")
        self.assertEqual(e.dance, "CC")

    def test_the_ultramixer_dance_style_names_the_dance(self):
        e = _um_entry("Some Title", None, "SW")
        self.assertEqual(e.dance, "LW")

    def test_the_genre_tag_wins_over_the_ultramixer_dance_style(self):
        e = _um_entry("Some Title", "TG", "SW")
        self.assertEqual(e.dance, "TG")

    def test_the_ultramixer_dance_style_wins_over_the_filename(self):
        e = _um_entry("Cha Chicki Salsa 2", None, "SW")
        self.assertEqual(e.dance, "LW")

    def test_an_unknown_dance_style_leaves_the_filename_in_charge(self):
        e = _um_entry("Cha Chicki Salsa 2", None, "Disco")
        self.assertEqual(e.dance, "CC")


if __name__ == "__main__":
    unittest.main(verbosity=2)
