#!/usr/bin/env python3
"""A track new to the scan cache has its tags parsed once, not six times.

Run:  py -m unittest tests.planner.test_scan_one_tag_read -v

The slow path of `_make_entry` asked a separate helper for the genre, the
comment, title/artist/album, the year and the duration — each opened and
parsed the file's ID3 again. Measured on 400 real library files: 8.2 ms per
file that way, 1.9 ms with one parse; ~30 s against ~7 s for a cold scan of
the 3,649-track library.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mutagen.id3 import COMM, ID3, TALB, TCON, TDRC, TIT2, TPE1

from planner.library import MusicLibrary

# One MPEG-1 Layer III frame header (128 kbit/s, 44.1 kHz): 417 bytes a frame.
_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413


def _tagged_mp3(path: Path, seconds: int = 3) -> Path:
    path.write_bytes(_FRAME * int(seconds * 44100 / 1152))
    tags = ID3()
    tags.add(TIT2(encoding=3, text="Moon River"))
    tags.add(TPE1(encoding=3, text="Some Artist"))
    tags.add(TALB(encoding=3, text="Ballroom Album"))
    tags.add(TDRC(encoding=3, text="1999"))
    tags.add(TCON(encoding=3, text="LW"))
    tags.add(COMM(encoding=3, lang="eng", desc="", text="D;C;fav"))
    tags.save(path)
    return path


class _Cache:
    def __init__(self):
        self.put_data = None

    def get(self, path):
        return None

    def put(self, path, data):
        self.put_data = data


class ScanOneTagReadTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tagread_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.mp3 = _tagged_mp3(self.dir / "Moon River (LW 29).mp3")

    def _entry(self):
        return MusicLibrary._make_entry(SimpleNamespace(), self.mp3, _Cache())

    def test_the_file_is_parsed_once(self):
        # Counted where every route ends — `ID3(path)` and `MutagenFile` alike.
        with mock.patch.object(ID3, "load", autospec=True,
                               side_effect=ID3.load) as loads:
            self._entry()
        self.assertEqual(loads.call_count, 1)

    def test_every_field_still_comes_from_the_tags(self):
        e = self._entry()
        self.assertEqual((e.title, e.tag_title, e.tag_artist, e.tag_album),
                         ("Moon River", "Moon River", "Some Artist", "Ballroom Album"))
        self.assertEqual((e.dance, e.year, e.bpm), ("LW", 1999, 29))
        self.assertEqual(e.classes_ok, ["D", "C"])
        self.assertIn("fav", e.comment_tags)
        self.assertEqual(e.duration, 3)

    def test_a_file_without_audio_frames_still_gives_its_tags(self):
        # MutagenFile refuses an MP3 it finds no MPEG frame in; the tags are
        # still there to read, as they were when each helper opened ID3 alone.
        self.mp3.write_bytes(b"")
        tags = ID3()
        tags.add(TIT2(encoding=3, text="Moon River"))
        tags.add(TCON(encoding=3, text="LW"))
        tags.save(self.mp3)
        e = self._entry()
        self.assertEqual((e.tag_title, e.dance, e.duration), ("Moon River", "LW", 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
