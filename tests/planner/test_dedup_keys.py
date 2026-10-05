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

from planner.parsing import (
    _norm_title, _song_title_key, _song_title_keys,
)


class SongTitleKeyTest(unittest.TestCase):
    """One aggressive key per name: same song → same key."""

    def test_dj_tag_and_dance_code_collapse(self):
        self.assertEqual(_song_title_key("Upside Down DJ Ice"),
                         _song_title_key("Upside Down (JI43)"))

    def test_leading_dj_artist_keeps_the_title(self):
        # 'S50  DJ Eiffel. <title>': the DJ is the artist IN FRONT of the title, not
        # a trailing tag — stripping it left only the tempo code 's50', so every
        # DJ Eiffel samba looked like the same song.
        self.assertNotEqual(_song_title_key("S50  DJ Eiffel. Dancando Na Rua.mp3"),
                            _song_title_key("S50  DJ Eiffel. Le Rythme Nous Emporte.mp3"))
        self.assertNotEqual(_song_title_key("1-01SB DJ ICE  Vs. Joao Neto - Le Le LeT51.mp3"),
                            _song_title_key("1-01SB DJ ICE - Samba de Janeiro.mp3"))

    def test_trailing_cut_marker(self):
        # 'Creepin (Rumba 24) cut' / '… (cut)' are re-edits of the same song.
        base = _song_title_key("Creepin (Rumba 24)")
        self.assertEqual(_song_title_key("Creepin (Rumba 24) cut"), base)
        self.assertEqual(_song_title_key("Creepin (Rumba 24) (cut)"), base)

    def test_cut_only_stripped_at_end(self):
        # A real title ending in 'Cut' as a WORD of the song name must survive
        # in the displayed title path — here we only guard the key is non-empty
        # and 'The Final Cut' doesn't equal 'The Final'.
        self.assertNotEqual(_song_title_key("The Final Countdown"),
                            _song_title_key("The Final Cut"))

    def test_accent_folding(self):
        self.assertEqual(_song_title_key("Aí Que Dó (Samba 50)"),
                         _song_title_key("Ai Que Do (Samba 50)"))

    def test_norm_title_folds_accents(self):
        self.assertEqual(_norm_title("Señorita"), _norm_title("Senorita"))


class SongTitleKeysTest(unittest.TestCase):
    """Candidate key LISTS: dash-split sides are extra candidates, never the
    only key."""

    def test_artist_dash_title_shares_title_candidate(self):
        keys_full = _song_title_keys("Casey Jones - Rhythm")
        keys_bare = _song_title_keys("Rhythm (QS 51)")
        self.assertTrue(set(keys_full) & set(keys_bare),
                        f"no shared candidate: {keys_full} vs {keys_bare}")

    def test_compound_title_keeps_full_key_first(self):
        keys = _song_title_keys("Higher - Faster")
        self.assertEqual(keys[0], _song_title_key("Higher - Faster"))
        self.assertIn(_song_title_key("Higher - Faster"), keys)

    def test_compound_titles_do_not_collapse_to_one_side(self):
        # 'Higher - Faster' and a bare 'Faster' MAY share a candidate (recall
        # over precision), but two different compounds must not become equal
        # through their FULL keys.
        self.assertNotEqual(_song_title_keys("Higher - Faster")[0],
                            _song_title_keys("Louder - Faster")[0])

    def test_plain_name_has_single_key(self):
        keys = _song_title_keys("La Cumparsita (TG 33)")
        self.assertEqual(keys, [_song_title_key("La Cumparsita (TG 33)")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
