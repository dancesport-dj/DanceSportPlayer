"""Review items 106, 107, 7: marker words must be whole words, and only folders
below the playlist root count as working folders."""
import unittest
from pathlib import Path
from unittest import mock

from planner.event import competition
from planner.event.competition import is_superseded_playlist


class AlleMarkerTests(unittest.TestCase):
    def test_words_that_start_with_alle_are_kept(self):
        for name in ("Allegro_S_STD", "Allen_Masters", "Allee"):
            with self.subTest(name):
                self.assertFalse(is_superseded_playlist(Path(f"{name}.m3u")))

    def test_real_alle_lists_are_dropped(self):
        for name in ("Alle_Tanze", "alle", "LAT_alle", "neuAlle"):
            with self.subTest(name):
                self.assertTrue(is_superseded_playlist(Path(f"{name}.m3u")))


class RestMarkerTests(unittest.TestCase):
    def test_mid_word_rest_is_kept(self):
        for name in ("Prestige_S_STD", "Restaurant_Music", "Bukarest", "Forrest"):
            with self.subTest(name):
                self.assertFalse(is_superseded_playlist(Path(f"{name}.m3u")))

    def test_rest_lists_are_dropped(self):
        for name in ("Restliste", "LAT_Rest", "latRest"):
            with self.subTest(name):
                self.assertTrue(is_superseded_playlist(Path(f"{name}.m3u")))


class RootAncestorTests(unittest.TestCase):
    def test_folders_above_the_root_do_not_count(self):
        root = Path("C:/Selektionen/Playlists")
        with mock.patch.object(competition, "playlist_dir", return_value=root):
            self.assertFalse(is_superseded_playlist(root / "2019" / "HGR_S_STD.m3u"))
            self.assertFalse(competition.is_working_collection_path(
                root / "2019" / "HGR_S_STD.m3u"))
            self.assertTrue(competition.is_working_collection_path(
                root / "Vorsortierungen" / "HGR_S_STD.m3u"))


if __name__ == "__main__":
    unittest.main()
