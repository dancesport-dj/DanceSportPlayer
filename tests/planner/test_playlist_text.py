#!/usr/bin/env python3
"""Tests for reading a playlist's text without losing a character of it.

Run:  py -m unittest tests.planner.test_playlist_text -v

The tournament folder holds UTF-8 playlists (the app's own, with or without a
BOM) next to cp1252 ones from the old Java app and Windows tools. A file that
is neither must fail loudly: reading it with the errors thrown away drops
every umlaut and quietly miscounts the titles in it.
"""
import tempfile
import unittest
from pathlib import Path

from planner.playlist_text import PlaylistEncodingError, read_playlist_text


class ReadPlaylistTextTest(unittest.TestCase):

    def setUp(self):
        self.path = Path(tempfile.mkdtemp(prefix="dp_pltext_")) / "Grünwald.m3u"

    def _read(self, raw: bytes):
        self.path.write_bytes(raw)
        return read_playlist_text(self.path)

    def test_utf8(self):
        self.assertEqual(self._read("Grüße\n".encode("utf-8")),
                         ("Grüße\n", "utf-8"))

    def test_utf8_with_a_bom(self):
        self.assertEqual(self._read("Grüße\n".encode("utf-8-sig")),
                         ("Grüße\n", "utf-8-sig"))

    def test_cp1252(self):
        self.assertEqual(self._read("Grüße – Tango\n".encode("cp1252")),
                         ("Grüße – Tango\n", "cp1252"))

    def test_utf16_with_a_bom(self):
        self.assertEqual(self._read("Grüße\n".encode("utf-16")),
                         ("Grüße\n", "utf-16"))

    def test_neither_fails_and_names_the_file(self):
        with self.assertRaises(PlaylistEncodingError) as cm:
            self._read(b"Gr\x81\x8d\n")
        self.assertIn("Grünwald.m3u", str(cm.exception))

    def test_plain_ascii_is_utf8(self):
        self.assertEqual(self._read(b"#EXTM3U\n"), ("#EXTM3U\n", "utf-8"))


if __name__ == "__main__":
    unittest.main()
