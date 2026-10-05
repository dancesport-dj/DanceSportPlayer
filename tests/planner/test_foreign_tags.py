"""Star ratings and class tags written by other programs are read too.

Run:  py -m unittest tests.planner.test_foreign_tags -v

The file from the user feedback ('…Ugoy_Lullaby_Langsamer_Walzer_29BPM.mp3')
carried two tags the app ignored: a POPM rating under the e-mail 'no@email'
(255 = five stars) and a Songs-DB comment 'ab C', meaning class C and up.
Marcel: read both; any POPM e-mail counts, 'ab C' becomes C;B;A;S.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mutagen.id3 import COMM, ID3, POPM

from planner.db import _meta_to_row, _row_to_meta
from planner.library import MusicLibrary
from planner.parsing import (
    _parse_class_tag,
    parse_comment_markers,
    popm_stars,
    stars_popm,
)


class AbClassTest(unittest.TestCase):

    def test_ab_c_means_c_and_up(self):
        self.assertEqual(_parse_class_tag("ab C"), (["C", "B", "A", "S"], False))

    def test_every_class_floor_is_read(self):
        """Marcel: make sure 'ab B', 'ab D' and 'ab A' are recognised too."""
        for text, want in (("ab D", ["D", "C", "B", "A", "S"]),
                           ("ab B", ["B", "A", "S"]),
                           ("ab A", ["A", "S"]),
                           ("ab S", ["S"]),
                           ("Ab  d", ["D", "C", "B", "A", "S"])):
            self.assertEqual(_parse_class_tag(text), (want, False), text)

    def test_ab_mixes_with_other_parts(self):
        self.assertEqual(_parse_class_tag("AB b;instr"), (["B", "A", "S"], True))

    def test_ab_c_is_no_free_marker(self):
        self.assertEqual(parse_comment_markers("ab C;classic"), ["classic"])


class PopmStarsTest(unittest.TestCase):

    def _tags(self, *frames):
        tags = ID3()
        for f in frames:
            tags.add(f)
        return tags

    def test_any_email_counts(self):
        tags = self._tags(POPM(email="no@email", rating=255, count=0))
        self.assertEqual(popm_stars(tags), 5)

    def test_the_windows_scale(self):
        for raw, stars in ((1, 1), (64, 2), (128, 3), (196, 4), (255, 5)):
            tags = self._tags(POPM(email="Windows Media Player 9 Series",
                                   rating=raw, count=0))
            self.assertEqual(popm_stars(tags), stars, raw)

    def test_the_windows_frame_wins_over_another(self):
        tags = self._tags(POPM(email="no@email", rating=255, count=0),
                          POPM(email="Windows Media Player 9 Series",
                               rating=64, count=0))
        self.assertEqual(popm_stars(tags), 2)

    def test_unrated(self):
        self.assertIsNone(popm_stars(self._tags()))
        self.assertIsNone(popm_stars(self._tags(POPM(email="x", rating=0, count=0))))
        self.assertIsNone(popm_stars(None))

    def test_stars_round_trip(self):
        for stars in range(1, 6):
            self.assertEqual(popm_stars(self._tags(
                POPM(email="x", rating=stars_popm(stars), count=0))), stars)


class RatingCachedTest(unittest.TestCase):

    def test_the_scan_cache_row_keeps_the_rating(self):
        meta = {"title": "t", "rating": 4}
        self.assertEqual(_row_to_meta(_meta_to_row(meta))["rating"], 4)
        self.assertIsNone(_row_to_meta(_meta_to_row({"title": "t"}))["rating"])


class _NoCache:
    def get(self, path):
        return None

    def put(self, path, data):
        self.data = dict(data)


class EntryFromFileTest(unittest.TestCase):

    def test_the_feedback_file_reads_five_stars_and_c_and_up(self):
        d = tempfile.mkdtemp()
        path = Path(d) / "Ugoy_Lullaby_Langsamer_Walzer_29BPM.mp3"
        path.write_bytes(b"")
        tags = ID3()
        tags.add(POPM(email="no@email", rating=255, count=0))
        tags.add(COMM(encoding=0, lang="XXX", desc="Songs-DB_Custom1", text=["ab C"]))
        tags.save(path)
        self.addCleanup(os.remove, path)
        with mock.patch("planner.library._read_tags_once",
                        return_value=(ID3(path), 180)):
            e = MusicLibrary()._make_entry(path, _NoCache())
        self.assertEqual(e.rating, 5)
        self.assertEqual(e.classes_ok, ["C", "B", "A", "S"])
        self.assertEqual(e.comment_tags, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
