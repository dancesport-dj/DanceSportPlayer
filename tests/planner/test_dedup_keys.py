#!/usr/bin/env python3
"""Regression tests for the dedup title keys (Check duplicates / hide-copies).

Run:  py -m unittest tests.planner.test_dedup_keys -v

Pins the three real-world cases the multi-candidate key work fixed:
  • a trailing 'cut' tournament-edit marker must not hide a duplicate
  • accented vs plain spellings must fold together (NFKD)
  • an 'Artist - Title' name must share a candidate key with the bare title,
    WITHOUT compound titles ('Higher - Faster') collapsing to one side
plus the long-standing DJ-tag / dance-code collapses they build on.
"""

import unittest

from planner.music.parsing import (
    norm_title,
    song_title_key,
    song_title_keys,
    song_use_keys,
)


class SongTitleKeyTest(unittest.TestCase):
    """One aggressive key per name: same song → same key."""

    def test_dj_tag_and_dance_code_collapse(self):
        self.assertEqual(song_title_key("Upside Down DJ Ice"),
                         song_title_key("Upside Down (JI43)"))

    def test_leading_dj_artist_keeps_the_title(self):
        # 'S50  DJ Eiffel. <title>': the DJ is the artist IN FRONT of the title, not
        # a trailing tag — stripping it left only the tempo code 's50', so every
        # DJ Eiffel samba looked like the same song.
        self.assertNotEqual(song_title_key("S50  DJ Eiffel. Dancando Na Rua.mp3"),
                            song_title_key("S50  DJ Eiffel. Le Rythme Nous Emporte.mp3"))
        self.assertNotEqual(song_title_key("1-01SB DJ ICE  Vs. Joao Neto - Le Le LeT51.mp3"),
                            song_title_key("1-01SB DJ ICE - Samba de Janeiro.mp3"))

    def test_trailing_cut_marker(self):
        # 'Creepin (Rumba 24) cut' / '… (cut)' are re-edits of the same song.
        base = song_title_key("Creepin (Rumba 24)")
        self.assertEqual(song_title_key("Creepin (Rumba 24) cut"), base)
        self.assertEqual(song_title_key("Creepin (Rumba 24) (cut)"), base)

    def test_cut_only_stripped_at_end(self):
        # A real title ending in 'Cut' as a WORD of the song name must survive
        # in the displayed title path — here we only guard the key is non-empty
        # and 'The Final Cut' doesn't equal 'The Final'.
        self.assertNotEqual(song_title_key("The Final Countdown"),
                            song_title_key("The Final Cut"))

    def test_accent_folding(self):
        self.assertEqual(song_title_key("Aí Que Dó (Samba 50)"),
                         song_title_key("Ai Que Do (Samba 50)"))

    def test_norm_title_folds_accents(self):
        self.assertEqual(norm_title("Señorita"), norm_title("Senorita"))

    def test_norm_title_folds_letters_that_do_not_decompose(self):
        """ø, ł, ß, æ have no combining form: they used to be dropped and
        left a space in the middle of the word ('s ren odz')."""
        self.assertEqual(norm_title("Søren Łódź"), "soren lodz")
        self.assertEqual(norm_title("Straße"), "strasse")
        self.assertEqual(norm_title("Æon"), "aeon")

    def test_norm_title_keeps_non_latin_scripts(self):
        """A Cyrillic or Greek title normalised to '' — every one of them was
        the same key as every other."""
        self.assertEqual(norm_title("Привет, Мир!"), "привет мир")
        self.assertNotEqual(norm_title("Привет"), norm_title("Прощай"))
        self.assertEqual(norm_title("Αγάπη"), "αγαπη")

    def test_norm_title_still_splits_on_punctuation_and_underscores(self):
        self.assertEqual(norm_title("Rock_n-Roll (Live)!"), "rock n roll live")


class SongTitleKeysTest(unittest.TestCase):
    """Candidate key LISTS: dash-split sides are extra candidates, never the
    only key."""

    def test_artist_dash_title_shares_title_candidate(self):
        keys_full = song_title_keys("Casey Jones - Rhythm")
        keys_bare = song_title_keys("Rhythm (QS 51)")
        self.assertTrue(set(keys_full) & set(keys_bare),
                        f"no shared candidate: {keys_full} vs {keys_bare}")

    def test_compound_title_keeps_full_key_first(self):
        keys = song_title_keys("Higher - Faster")
        self.assertEqual(keys[0], song_title_key("Higher - Faster"))
        self.assertIn(song_title_key("Higher - Faster"), keys)

    def test_compound_titles_do_not_collapse_to_one_side(self):
        # 'Higher - Faster' and a bare 'Faster' MAY share a candidate (recall
        # over precision), but two different compounds must not become equal
        # through their FULL keys.
        self.assertNotEqual(song_title_keys("Higher - Faster")[0],
                            song_title_keys("Louder - Faster")[0])

    def test_plain_name_has_single_key(self):
        keys = song_title_keys("La Cumparsita (TG 33)")
        self.assertEqual(keys, [song_title_key("La Cumparsita (TG 33)")])


class SongUseKeysTest(unittest.TestCase):
    """The strict no-repeat keys: the full key plus the title side only. The
    artist side must never count as 'used' (the duplicate finder keeps it)."""

    def test_artist_side_is_not_a_use_key(self):
        keys = song_use_keys("Michael Buble - Sway.mp3")
        self.assertIn(song_title_key("Michael Buble - Sway.mp3"), keys)
        self.assertIn(song_title_key("Sway"), keys)
        self.assertNotIn(song_title_key("Michael Buble"), keys)

    def test_two_tracks_of_one_artist_share_no_use_key(self):
        self.assertFalse(set(song_use_keys("Michael Buble - Sway.mp3"))
                         & set(song_use_keys("Michael Buble - Home.mp3")))

    def test_other_recording_of_the_song_still_shares_a_use_key(self):
        self.assertTrue(set(song_use_keys("Michael Buble - Sway.mp3"))
                        & set(song_use_keys("Sway (RB 30).mp3")))

    def test_plain_name_has_single_use_key(self):
        self.assertEqual(song_use_keys("La Cumparsita (TG 33).mp3"),
                         [song_title_key("La Cumparsita (TG 33).mp3")])


class UseKeyJunkTest(unittest.TestCase):
    """Real library names: the part after the last ' - ' is often no title at all
    (a dance word, a tempo, a remix or DJ tag). Such a part must never become a key
    that ties together every file carrying the same tag."""

    def test_junk_last_parts_give_only_the_full_key(self):
        for name in ("Prince Royce - Samba.mp3",
                     "Kygo - Hot Stuff - 50.mp3",
                     "Brian Evans _ Croonerman - QS50.mp3",
                     "Casa - Song - (Samba 51BPM).mp3",
                     "Samba - EO..mp3",
                     "Zaz - Paris - DJ Mitya.mp3"):
            with self.subTest(name=name):
                self.assertLessEqual(len(song_use_keys(name)), 2)
                self.assertNotIn("samba", song_use_keys(name))
                self.assertNotIn("qs50", song_use_keys(name))
                self.assertNotIn("dj mitya", song_use_keys(name))

    def test_two_files_with_the_same_junk_tail_share_no_key(self):
        self.assertFalse(set(song_use_keys("A One - Samba.mp3"))
                         & set(song_use_keys("B Two - Samba.mp3")))

    def test_a_remix_tag_is_skipped_for_the_title_before_it(self):
        self.assertIn(song_title_key("Paris"),
                      song_use_keys("Zaz - Paris - rumba remix - (Dj Mitya).mp3"))

    def test_a_dance_prefix_is_not_the_title_side(self):
        self.assertEqual(song_use_keys("LW - Autumn.mp3")[-1], song_title_key("Autumn"))
        self.assertNotIn("lw", song_use_keys("LW - Autumn.mp3"))


class DashPartKeyTest(unittest.TestCase):
    def test_a_dot_inside_a_dash_part_is_not_an_extension(self):
        for keys in (song_title_keys("Artist - Mr. Brightside.mp3"),
                     song_use_keys("Artist - Mr. Brightside.mp3")):
            self.assertIn("mr brightside", keys)
            self.assertNotIn("mr", keys)


if __name__ == "__main__":
    unittest.main(verbosity=2)
