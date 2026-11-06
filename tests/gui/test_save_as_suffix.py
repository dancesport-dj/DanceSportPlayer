#!/usr/bin/env python3
"""💾 Save as M3U keeps the whole name the user typed.

Run:  py -m unittest tests.gui.test_save_as_suffix -v

"Playlist v1.2" was saved as "Playlist v1.m3u": `with_suffix` takes ".2" for
an extension and replaces it, and the overwrite prompt of the dialog had only
seen the name that was typed.
"""
import unittest
from pathlib import Path

from gui.window.main_export import with_m3u_suffix
from planner.playlist.m3u import m3u_suffix


class WithM3uSuffixTest(unittest.TestCase):

    def test_a_dotted_name_keeps_its_tail(self):
        out = with_m3u_suffix(Path("C:/lists/Playlist v1.2"))
        self.assertEqual(out.name, "Playlist v1.2" + m3u_suffix())

    def test_a_name_without_a_dot_gets_the_suffix(self):
        self.assertEqual(with_m3u_suffix(Path("C:/lists/Latein")).name,
                         "Latein" + m3u_suffix())

    def test_a_playlist_suffix_is_left_alone_whatever_the_case(self):
        for name in ("a.m3u", "a.m3u8", "a.M3U"):
            with self.subTest(name):
                self.assertEqual(with_m3u_suffix(Path("C:/lists") / name).name, name)

    def test_the_folder_is_untouched(self):
        self.assertEqual(with_m3u_suffix(Path("C:/lists v1.2/x")).parent,
                         Path("C:/lists v1.2"))


if __name__ == "__main__":
    unittest.main()
