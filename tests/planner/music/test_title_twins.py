"""The strict no-repeat knows a song by its last dash part, so a "Title - Artist" file
("01 Be my love - Werner Tauber") and the same song filed as "01 - Be My Love - SF 30"
were two songs to the picker. `title_twins` links such files once per library; the
suggester merges the links into its Chroma twin map, so a pick rules its twins out
without any per-pick work."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from planner.generate import suggester as sug_mod
from planner.generate.suggester import PlaylistSuggester, is_used, mark_used
from planner.music.library import MusicLibrary
from planner.music.parsing import (
    song_extra_keys,
    song_title_keys,
    song_use_and_extra_keys,
    song_use_keys,
)
from planner.music.title_twins import title_twins


def _e(name: str, dance: str | None = None):
    return SimpleNamespace(path=Path("C:/music") / f"{name}.mp3", dance=dance)


def _lib(*entries):
    lib = MusicLibrary()
    lib.entries.extend(entries)
    return lib


class ExtraKeysTest(unittest.TestCase):

    def test_the_artist_side_of_a_title_last_name_is_extra(self):
        self.assertEqual(song_extra_keys("Jessie J - Domino.mp3"), ["jessie j"])

    def test_the_title_side_of_a_title_first_name_is_extra(self):
        self.assertIn("be my love", song_extra_keys("01 Be my love - Werner Tauber.mp3"))

    def test_tags_and_dance_words_are_no_keys(self):
        self.assertEqual(song_extra_keys("Foxtrot - Some Song.mp3"), [])
        self.assertEqual(song_extra_keys("QS50 - Some Song.mp3"), [])

    def test_a_name_without_a_dash_has_none(self):
        self.assertEqual(song_extra_keys("Moon River (LW 29).mp3"), [])

    def test_the_one_pass_split_agrees_with_the_two_public_functions(self):
        # The twin map uses the one-pass form for speed; it must not drift from
        # `song_use_keys` (the strict no-repeat) or from `song_title_keys` (the rest).
        for name in ("Jessie J - Domino.mp3", "01 Be my love - Werner Tauber.mp3",
                     "01 - Be My Love - SF 30.mp3", "LW - Autumn.mp3",
                     "Brian Evans _ Croonerman - QS50.mp3", "Moon River (LW 29).mp3",
                     "Adele - Rolling in the deep - rumba remix - (Dj Mitya).mp3",
                     "Jive - Edoardo Bennato - Il Gatto e la Volpe.mp3", "Rhythm.mp3"):
            use, extra = song_use_and_extra_keys(name)
            self.assertEqual(use, song_use_keys(name), name)
            self.assertEqual(extra, song_extra_keys(name), name)
            self.assertTrue(set(extra) <= set(song_title_keys(name)) - set(use), name)


class TitleTwinsTest(unittest.TestCase):

    def test_a_title_first_file_meets_its_dance_sorted_twin(self):
        a, b = _e("01 Be my love - Werner Tauber", "SF"), _e("01 - Be My Love - SF 30", "SF")
        got = title_twins([a, b])
        self.assertEqual(got[str(a.path)], frozenset({str(b.path)}))
        self.assertEqual(got[str(b.path)], frozenset({str(a.path)}))

    def test_an_unknown_dance_does_not_rule_a_twin_out(self):
        a, b = _e("19-Charade - Matt Monro (LW 29)", "LW"), _e("Charade", None)
        self.assertIn(str(b.path), title_twins([a, b])[str(a.path)])

    def test_the_same_song_in_another_dance_is_no_twin(self):
        a, b = _e("19-Charade - Matt Monro (LW 29)", "LW"), _e("08- Charade-WW-60", "WW")
        self.assertEqual(title_twins([a, b]), {})

    def test_an_artist_with_many_tracks_ties_nothing_together(self):
        jj = [_e(f"Jessie J - {t}") for t in ("Domino", "Price Tag", "Bang Bang", "Flashlight")]
        title_first = _e("Sunrise - Jessie J")
        self.assertEqual(title_twins([*jj, title_first]), {})

    def test_five_or_six_tracks_by_one_artist_tie_nothing_together(self):
        """Counted apart, five holders and three extras each passed their own gate."""
        as_title = [_e(f"Song {t} - Matt Monro") for t in "ABCDE"]
        as_artist = [_e(f"Matt Monro - Other {t}") for t in "ABC"]
        self.assertEqual(title_twins([*as_title, *as_artist]), {})

    def test_two_songs_of_one_artist_in_opposite_orders_are_no_twins(self):
        a, b = _e("On Other Words - Matt Monro", "LW"), _e("Matt Monro - Honey On The Vine", "LW")
        self.assertEqual(title_twins([a, b]), {})

    def test_the_same_song_under_a_name_that_adds_the_artist_is_still_a_twin(self):
        a, b = _e("Charade - Matt Monro", "LW"), _e("Matt Monro - Charade", "LW")
        self.assertIn(str(b.path), title_twins([a, b]).get(str(a.path), ()))

    def test_a_dance_word_is_no_key(self):
        self.assertEqual(title_twins([_e("Foxtrot - Some Song"), _e("Foxtrot")]), {})

    def test_a_title_held_by_many_files_is_not_a_twin_group(self):
        many = [_e(f"{n:02d} - Hello - X{n}") for n in range(1, 9)]
        self.assertEqual(title_twins([*many, _e("Hello - Adele")]), {})

    def test_files_with_nothing_in_common_have_none(self):
        self.assertEqual(title_twins([_e("Moon River"), _e("Tennessee Waltz")]), {})


class SuggesterTwinsTest(unittest.TestCase):

    def setUp(self):
        self.a = _e("01 Be my love - Werner Tauber", "SF")
        self.b = _e("01 - Be My Love - SF 30", "SF")
        self.lib = _lib(self.a, self.b, _e("Moon River", "SF"))

    def test_the_twin_map_carries_title_twins_without_an_audio_cache(self):
        twins = PlaylistSuggester(self.lib).twins()
        self.assertEqual(twins[str(self.a.path)], frozenset({str(self.b.path)}))

    def test_a_used_song_rules_out_its_title_twin(self):
        used: set = set()
        mark_used(used, self.a, PlaylistSuggester(self.lib).twins())
        self.assertTrue(is_used(self.b, used))
        self.assertFalse(is_used(_e("Moon River", "SF"), used))

    def test_chroma_twins_and_title_twins_are_both_kept(self):
        cache = mock.Mock()
        cache.chroma_keys.return_value = [1]
        self.lib.audio_cache = cache
        other = str(Path("C:/music/copy on usb.mp3"))
        with mock.patch.object(sug_mod, "twin_paths",
                               return_value={str(self.a.path): frozenset({other})}):
            twins = PlaylistSuggester(self.lib).twins()
        self.assertEqual(twins[str(self.a.path)], frozenset({str(self.b.path), other}))

    def test_the_merge_is_not_rebuilt_on_every_pick(self):
        sug = PlaylistSuggester(self.lib)
        self.assertIs(sug.twins(), sug.twins())

    def test_the_library_builds_the_title_twins_once_for_all_its_suggesters(self):
        """A suggester is made per action; the map belongs to the entries."""
        from planner.music import library as lib_mod
        with mock.patch.object(lib_mod, "build_title_twins", return_value={}) as build:
            PlaylistSuggester(self.lib).twins()
            PlaylistSuggester(self.lib).twins()
            PlaylistSuggester(self.lib).twins()
        self.assertEqual(build.call_count, 1)

    def test_the_library_rebuilds_them_when_its_entries_change(self):
        from planner.music import library as lib_mod
        with mock.patch.object(lib_mod, "build_title_twins", return_value={}) as build:
            self.lib.title_twins()
            self.lib.entries.append(_e("Another Song", "SF"))
            self.lib.title_twins()
            self.lib.entries = [*self.lib.entries]
            self.lib.title_twins()
        self.assertEqual(build.call_count, 3)

    def test_a_suggester_without_a_library_has_no_twins(self):
        self.assertEqual(PlaylistSuggester(None).twins(), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
