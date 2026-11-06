"""A non-finite BPM tag, and names that only contain a Christmas word (review items 91, 92)."""
import unittest
from pathlib import Path
from unittest import mock

from planner.music import parsing


class TagBpmTests(unittest.TestCase):
    def bpm(self, text):
        with mock.patch.object(parsing, "HAS_MUTAGEN", True), \
                mock.patch.object(parsing, "_id3_of", return_value={"TBPM": text}):
            return parsing.get_tag_bpm(Path("x.mp3"))

    def test_non_finite_is_no_bpm(self):
        for text in ("nan", "inf", "-inf", "1e999"):
            with self.subTest(text=text):
                self.assertIsNone(self.bpm(text))

    def test_normal_value_is_kept(self):
        self.assertEqual(self.bpm("128"), 128.0)

    def test_a_decimal_comma_is_read(self):
        """A tagger on a German locale writes '128,5'; it was dropped."""
        self.assertEqual(self.bpm("128,5"), 128.5)
        self.assertEqual(self.bpm(" 128.5 "), 128.5)

    def test_a_value_that_is_no_single_number_is_no_bpm(self):
        for text in ("120/121", "", "fast", "1,000,5"):
            with self.subTest(text=text):
                self.assertIsNone(self.bpm(text))


class XmasNameTests(unittest.TestCase):
    def test_names_that_only_contain_the_word_are_not_christmas(self):
        for stem in ("Santana - Smooth", "Santa Esmeralda - Don't Be Shy",
                     "Adventure of a Lifetime", "Kerstin - Lied", "Noelle - Song",
                     "Chanoel - Mix"):
            with self.subTest(stem=stem):
                self.assertFalse(parsing.is_christmas(stem, ""))

    def test_real_christmas_names_still_are(self):
        for stem in ("Santa Baby", "01_Santa_Baby", "Noel - Carol", "Jingle Bells",
                     "Last Christmas", "Weihnachtslied", "Stille Nacht", "Advent, Advent",
                     "Kerst Medley", "Feliz Navidad", "Santa Claus Is Coming"):
            with self.subTest(stem=stem):
                self.assertTrue(parsing.is_christmas(stem, ""))


class XmasHealTests(unittest.TestCase):
    def heal(self, name, flagged):
        from planner.music.library import _heal_cached
        cached = {"title": name, "dance": "CC", "bpm": 120.0, "is_xmas": flagged,
                  "tag_title": None, "tag_bpm": None, "duration": 100, "comment_tags": [],
                  "tag_album": "", "tag_comment": "", "custom": "", "tag_genre": None}
        scan_cache = mock.Mock()
        with mock.patch("planner.music.library.title_for", return_value=name),                 mock.patch("planner.music.library.detect_bpm_tagged", return_value=120.0):
            return _heal_cached(Path(f"C:/m/{name}.mp3"), cached, scan_cache)

    def test_a_wrongly_flagged_row_is_corrected(self):
        self.assertFalse(self.heal("Santana - Smooth", True)["is_xmas"])

    def test_a_christmas_row_stays(self):
        self.assertTrue(self.heal("Santa Baby", True)["is_xmas"])


if __name__ == "__main__":
    unittest.main()
