"""🏷 An MP3 that carries only an APEv2 tag (foobar2000, mp3gain) is read as ID3.

Run:  py -m unittest tests.planner.music.test_apev2_tags -v
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from mutagen.apev2 import APEv2, APEBinaryValue
from mutagen.id3 import ID3, TIT2

from dancesport_planner import AudioCache, MusicLibrary
from planner.music import parsing
from planner.music.foreign_tags import as_id3

# One 417-byte MPEG frame (128 kbit/s, 44.1 kHz): mutagen reads a real length.
_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413


def _mp3(folder: Path, seconds: int) -> Path:
    path = folder / "sway.mp3"
    path.write_bytes(_FRAME * int(seconds * 44100 / 1152))
    return path


def _text(id3, key):
    return [str(t) for t in id3[key].text]


class AdapterTest(unittest.TestCase):

    def test_the_known_keys_land_in_their_frames_whatever_their_case(self):
        tags = APEv2()
        tags["Title"] = "Sway"
        tags["ARTIST"] = ["Dean Martin", "Pérez Prado"]
        tags["Genre"] = "Cha Cha"
        tags["BPM"] = "124"
        tags["Year"] = "1954"
        tags["Comment"] = "party"
        tags["ULTRAMIXER_DANCESTYLE"] = "Cha Cha Cha"
        tags["Rating"] = "80"
        id3 = as_id3(tags)
        assert id3 is not None
        self.assertEqual(_text(id3, "TIT2"), ["Sway"])
        self.assertEqual(_text(id3, "TPE1"), ["Dean Martin", "Pérez Prado"])
        self.assertEqual(_text(id3, "TCON"), ["Cha Cha"])
        self.assertEqual(_text(id3, "TBPM"), ["124"])
        self.assertEqual(_text(id3, "TDRC"), ["1954"])
        self.assertEqual(_text(id3, "COMM::eng"), ["party"])
        self.assertEqual([(f.desc, list(f.text)) for f in id3.getall("TXXX")],
                         [("ULTRAMIXER_DANCESTYLE", ["Cha Cha Cha"])])
        self.assertEqual(parsing.popm_stars(id3), 4)

    def test_a_cover_picture_is_skipped(self):
        tags = APEv2()
        tags["Cover Art (Front)"] = APEBinaryValue(b"front.jpg\x00\xff\xd8")
        self.assertIsNone(as_id3(tags))


class FileTest(unittest.TestCase):

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_ape_"))
        self.addCleanup(shutil.rmtree, folder, True)
        self.path = _mp3(folder, 180)

    def ape(self, **fields):
        tags = APEv2()
        for k, v in fields.items():
            tags[k] = v
        tags.save(self.path)

    def test_an_mp3_without_id3_reads_its_ape_tag(self):
        self.ape(Title="Sway", ULTRAMIXER_DANCESTYLE="Rumba")
        self.assertEqual(_text(parsing._id3_of(self.path), "TIT2"), ["Sway"])
        tags, secs = parsing._read_tags_once(self.path)
        self.assertEqual(secs, 180)
        self.assertEqual(parsing._get_um_dance(tags), "RB")

    def test_an_id3_tag_wins_over_the_ape_tag(self):
        self.ape(Title="from APE")
        id3 = ID3()
        id3.add(TIT2(encoding=3, text="from ID3"))
        id3.save(self.path)
        self.assertEqual(_text(parsing._id3_of(self.path), "TIT2"), ["from ID3"])

    def test_no_tag_at_all_is_none(self):
        self.assertIsNone(parsing._id3_of(self.path))

    def test_a_library_scan_lists_it(self):
        self.ape(Title="Sway", ULTRAMIXER_DANCESTYLE="Rumba", Rating="5")
        lib = MusicLibrary()
        lib.scan(AudioCache(), music_dir=self.path.parent, learn=False, analyze=False,
                 interactive=False)
        (entry,) = lib.entries
        self.assertEqual((entry.tag_title, entry.dance, entry.rating), ("Sway", "RB", 5))


if __name__ == "__main__":
    unittest.main()
