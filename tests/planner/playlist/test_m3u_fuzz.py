"""📃 Fuzz: an .m3u comes from any player, in any encoding, edited by hand.

Callers: the library's playlist learning and the import read every .m3u in
the folder; one odd file must give its tracks or none, never stop the scan.
`read_m3u_tracks` answers [] for a file it cannot decode. `read_playlist_text`
refuses one that is neither UTF-8 nor cp1252 with PlaylistEncodingError (a
ValueError), so that no umlaut is lost on write-back; every caller catches
it or Exception (checked 2026-11-17).
"""
import tempfile
import unittest
from pathlib import Path

from hypothesis import example, given
from hypothesis import strategies as st

from planner.playlist import m3u
from planner.playlist.playlist_text import PlaylistEncodingError, read_playlist_text
from tests.fuzz_support import fuzz, texts

lines = st.lists(st.one_of(
    texts,
    st.builds(lambda secs, t: f"#EXTINF:{secs},{t}", st.integers(-5, 10**12), texts),
    st.sampled_from(["#EXTM3U", "#EXTINF:", "#EXTINF:-1,", "#EXTINF:abc,x",
                     "C:\\musik\\LW\\Song (LW 29).mp3", "..\\..\\x.mp3",
                     "\\\\server\\share\\a.mp3", "file:///C:/a.mp3", "a" * 600])),
    max_size=20)
encodings = st.sampled_from(["utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16"])


class M3uFuzzTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "Liste.m3u"

    def _read(self):
        tracks = m3u.read_m3u_tracks(self.path)
        for path, title in tracks:
            self.assertIsInstance(path, Path)
            self.assertIsInstance(title, str)
        try:
            text, _enc = read_playlist_text(self.path)
        except PlaylistEncodingError:
            return
        self.assertIsInstance(text, str)

    @fuzz(80)
    @given(st.binary(max_size=400))
    @example(b"\xff\xfe#\x00E\x00")          # a UTF-16 BOM, cut short
    @example(b"#EXTM3U\r\n#EXTINF:99999999999999999999,x\r\nC:\\a.mp3")
    def test_any_bytes_read(self, data):
        self.path.write_bytes(data)
        self._read()

    @fuzz(80)
    @given(lines, encodings, st.sampled_from(["\n", "\r\n", "\r"]))
    def test_any_playlist_text_reads(self, rows, enc, nl):
        self.path.write_bytes(nl.join(rows).encode(enc, "replace"))
        self._read()


if __name__ == "__main__":
    unittest.main()
