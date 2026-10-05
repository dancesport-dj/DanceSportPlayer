#!/usr/bin/env python3
"""Tests for 🧭 Fix & overwrite — rewriting the path lines of a dropped .m3u.

Run:  py -m unittest tests.gui.test_path_fix_rewrite -v

About 500 of the playlists in the tournament folder are cp1252, written by
the old Java app and by Windows tools. They used to be read as UTF-8 with the
errors thrown away and written back as UTF-8, so every umlaut in them was gone
for good — with no copy to go back to.
"""
import tempfile
import unittest
from pathlib import Path

from planner.playlist_text import (  # noqa: E402
    PlaylistEncodingError,
    rerooted,
    rewrite_playlist_paths,
)

_OLD = r"C:\old\tanzcds\LW\Mondschein über Wien (LW 29).mp3"
_NEW = r"F:\my music\tanzcds\LW\Mondschein über Wien (LW 29).mp3"


class _Remapper:
    def __init__(self, new=_NEW):
        self.new = new

    def remap(self, path):
        return Path(self.new) if str(path) == _OLD else None


def _rewrite(m3u, remapper=None):
    return rewrite_playlist_paths(m3u, remapper or _Remapper())


class RewriteKeepsTheTextTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_pathfix_m3u_"))
        self.m3u = self.dir / "Grünwald Latein.m3u"

    def _write(self, text, encoding):
        self.m3u.write_bytes(text.encode(encoding))
        return self.m3u.read_bytes()

    def test_a_cp1252_playlist_keeps_its_umlauts_and_its_encoding(self):
        self._write("#EXTM3U\r\n#EXTINF:90,Mondschein über Wien\r\n"
                    + _OLD + "\r\n", "cp1252")
        self.assertEqual(_rewrite(self.m3u), 1)
        self.assertEqual(self.m3u.read_bytes().decode("cp1252"),
                         "#EXTM3U\r\n#EXTINF:90,Mondschein über Wien\r\n"
                         + _NEW + "\r\n")

    def test_a_utf8_playlist_with_a_bom_keeps_the_bom(self):
        self._write("#EXTM3U\n#EXTINF:90,Grüße\n" + _OLD + "\n", "utf-8-sig")
        _rewrite(self.m3u)
        raw = self.m3u.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(raw.decode("utf-8-sig"),
                         "#EXTM3U\n#EXTINF:90,Grüße\n" + _NEW + "\n")

    def test_the_original_is_kept_next_to_it(self):
        before = self._write("#EXTM3U\n" + _OLD + "\n", "cp1252")
        _rewrite(self.m3u)
        backup = self.m3u.with_name(self.m3u.name + ".bak")
        self.assertEqual(backup.read_bytes(), before)

    def test_an_undecodable_playlist_is_left_alone(self):
        before = self.m3u.write_bytes(b"#EXTM3U\n\x81\x8d " + _OLD.encode("cp1252")
                                      + b"\n") and self.m3u.read_bytes()
        with self.assertRaises(PlaylistEncodingError):
            _rewrite(self.m3u)
        self.assertEqual(self.m3u.read_bytes(), before)

    def test_a_new_path_the_encoding_cannot_hold_writes_nothing(self):
        """A cp1252 file cannot take a path with a Polish ł in it — writing it
        as UTF-8 would turn every other umlaut in the file to garbage."""
        before = self._write("#EXTINF:90,Grüße\n" + _OLD + "\n", "cp1252")
        with self.assertRaises(UnicodeEncodeError):
            _rewrite(self.m3u, _Remapper(r"F:\my music\Łódź.mp3"))
        self.assertEqual(self.m3u.read_bytes(), before)
        self.assertFalse(self.m3u.with_name(self.m3u.name + ".bak").exists())


class ReRootedTest(unittest.TestCase):
    """Which path lines 🧭 counts, lists and rewrites as fixable."""

    def test_a_path_found_elsewhere_is_re_rooted(self):
        self.assertEqual(rerooted(Path(_OLD), _Remapper()), Path(_NEW))

    def test_a_path_the_search_folders_do_not_know_is_left(self):
        self.assertIsNone(rerooted(Path(r"C:\x\gone.mp3"), _Remapper()))

    def test_a_path_already_where_it_belongs_is_left_whatever_the_case(self):
        self.assertIsNone(rerooted(Path(_OLD), _Remapper(new=_OLD.upper())))


if __name__ == "__main__":
    unittest.main()
