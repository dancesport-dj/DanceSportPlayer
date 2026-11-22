"""Property tests for the title keys and the POPM star bands.

A match key is compared with keys made from other spellings of the same song,
so it must be a fixed point: normalising a key again must not change it, or a
key read back from the database stops matching the one made fresh. The star
bands must be monotonic and give back what `stars_popm` wrote.

Run:  .venv/Scripts/python.exe -m pytest tests/planner/music/test_parsing_properties.py -n0
"""
import unittest

from hypothesis import example, given, settings
from hypothesis import strategies as st
from mutagen.id3 import ID3, POPM

from planner.music.parsing import (
    WMP_POPM_EMAIL,
    norm_title,
    popm_stars,
    song_title_key_of_stem,
    stars_popm,
    stem_key,
)

text = st.text(st.characters(exclude_categories=("Cs",)), max_size=40)


def tags(*frames: tuple[str, int]) -> ID3:
    t = ID3()
    for email, rating in frames:
        t.add(POPM(email=email, rating=rating, count=0))
    return t


class NormTitleTest(unittest.TestCase):
    @settings(max_examples=500)
    @given(text)
    @example("25℃")   # NFKD turns ℃ into °C: an upper-case letter after the lower()
    def test_a_normalised_title_is_a_fixed_point(self, s):
        once = norm_title(s)
        self.assertEqual(norm_title(once), once)

    @given(text)
    def test_a_key_has_no_upper_case_and_no_outer_space(self, s):
        key = norm_title(s)
        self.assertEqual(key, key.strip())
        self.assertEqual(key, key.lower())


class SongTitleKeyTest(unittest.TestCase):
    @settings(max_examples=300)
    @given(text)
    def test_a_song_key_is_already_normalised(self, stem):
        key = song_title_key_of_stem(stem)
        self.assertEqual(norm_title(key), key)

    @given(st.lists(st.text("bcfghkmnoxyz", min_size=4, max_size=8), min_size=1, max_size=4),
           st.sampled_from(["(JI43)", "[SA50]", "DJ Ice", "JI43", "(cut)"]))
    def test_a_re_encoded_copy_gets_the_same_key(self, words, tag):
        title = " ".join(words)
        self.assertEqual(song_title_key_of_stem(f"{title} {tag}"), song_title_key_of_stem(title))


class StemKeyTest(unittest.TestCase):
    @given(st.text(st.characters(codec="ascii", categories=("L", "N")), min_size=1, max_size=20),
           st.sampled_from(["C:/Musik/Samba", "D:/other drive", "/home/x"]),
           st.sampled_from([".mp3", ".FLAC", ".m4a"]))
    def test_the_folder_and_the_extension_do_not_count(self, name, folder, ext):
        self.assertEqual(stem_key(f"{folder}/{name}{ext}"), name.lower())


class PopmStarsTest(unittest.TestCase):
    def test_what_stars_popm_writes_reads_back_as_the_same_stars(self):
        for stars in range(1, 6):
            self.assertEqual(popm_stars(tags(("any@x", stars_popm(stars)))), stars)

    @given(st.integers(1, 255), st.integers(1, 255))
    def test_a_higher_byte_never_means_fewer_stars(self, a, b):
        lo, hi = sorted((a, b))
        self.assertLessEqual(popm_stars(tags(("x", lo))), popm_stars(tags(("x", hi))))

    @given(st.integers(1, 255), st.lists(st.tuples(st.text("abc@.", min_size=1, max_size=8)
                                                   .filter(lambda e: e != WMP_POPM_EMAIL),
                                                   st.integers(0, 255)), max_size=3))
    def test_the_windows_frame_wins_over_any_other(self, wmp, others):
        rated = tags((WMP_POPM_EMAIL, wmp), *others)
        self.assertEqual(popm_stars(rated), popm_stars(tags(("x", wmp))))

    def test_a_zero_byte_is_unrated(self):
        self.assertIsNone(popm_stars(tags(("x", 0))))


if __name__ == "__main__":
    unittest.main()
