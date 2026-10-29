"""The tags of a FLAC/Ogg/Opus or M4A file, read as ID3 frames.

Every tag reader in planner.music.parsing looks for ID3 frames, so the adapter
has to put each field where an MP3 tagger would have: title in TIT2, the
UltraMixer dance style in a TXXX, the comment in COMM, and so on.

Run:  py -m unittest tests.planner.music.test_flac_m4a_tags -v
"""

import tempfile
import unittest
from pathlib import Path

from mutagen.flac import FLAC, VCFLACDict
from mutagen.id3 import ID3
from mutagen.mp4 import MP4FreeForm, MP4Tags

from dancesport_planner import AudioCache, MusicLibrary
from planner.music import parsing
from planner.music.foreign_tags import as_id3


def _id3(tags) -> ID3:
    id3 = as_id3(tags)
    assert id3 is not None
    return id3


def _text(id3, key):
    return [str(t) for t in id3[key].text]


class VorbisTest(unittest.TestCase):
    """FLAC, Ogg and Opus: free NAME=value pairs."""

    def test_the_known_names_land_in_their_frames(self):
        tags = VCFLACDict()
        tags["TITLE"] = "Moon River"
        tags["Artist"] = "Andy Williams"
        tags["album"] = "Waltzes"
        tags["GENRE"] = "Slow Waltz"
        tags["BPM"] = "84"
        tags["DATE"] = "1962"
        id3 = as_id3(tags)
        self.assertEqual(_text(id3, "TIT2"), ["Moon River"])
        self.assertEqual(_text(id3, "TPE1"), ["Andy Williams"])
        self.assertEqual(_text(id3, "TALB"), ["Waltzes"])
        self.assertEqual(_text(id3, "TCON"), ["Slow Waltz"])
        self.assertEqual(_text(id3, "TBPM"), ["84"])
        self.assertEqual(_text(id3, "TDRC"), ["1962"])

    def test_the_comment_becomes_comm(self):
        tags = VCFLACDict()
        tags["COMMENT"] = "great intro"
        self.assertEqual(_text(as_id3(tags), "COMM::eng"), ["great intro"])

    def test_any_other_field_becomes_a_txxx_of_its_name(self):
        tags = VCFLACDict()
        tags["ULTRAMIXER_DANCESTYLE"] = "Rumba"
        frames = _id3(tags).getall("TXXX")
        self.assertEqual([(f.desc.lower(), list(f.text)) for f in frames],
                         [("ultramixer_dancestyle", ["Rumba"])])

    def test_bpm_wins_over_tempo(self):
        tags = VCFLACDict()
        tags["BPM"] = "120"
        tags["TEMPO"] = "60"
        self.assertEqual(_text(as_id3(tags), "TBPM"), ["120"])

    def test_empty_tags_are_none(self):
        self.assertIsNone(as_id3(VCFLACDict()))
        tags = VCFLACDict()
        tags["TITLE"] = "   "
        self.assertIsNone(as_id3(tags))


class Mp4Test(unittest.TestCase):
    """M4A: iTunes atoms."""

    def test_the_atoms_land_in_their_frames(self):
        tags = MP4Tags()
        tags["\xa9nam"] = ["Sway"]
        tags["\xa9ART"] = ["Dean Martin"]
        tags["\xa9gen"] = ["Cha Cha"]
        tags["tmpo"] = [124]
        tags["\xa9cmt"] = ["party"]
        id3 = as_id3(tags)
        self.assertEqual(_text(id3, "TIT2"), ["Sway"])
        self.assertEqual(_text(id3, "TPE1"), ["Dean Martin"])
        self.assertEqual(_text(id3, "TCON"), ["Cha Cha"])
        self.assertEqual(_text(id3, "TBPM"), ["124"])
        self.assertEqual(_text(id3, "COMM::eng"), ["party"])

    def test_a_freeform_atom_becomes_a_txxx(self):
        tags = MP4Tags()
        tags["----:com.apple.iTunes:ULTRAMIXER_DANCESTYLE"] = [MP4FreeForm(b"Jive")]
        tags["----:com.other:IGNORED"] = [MP4FreeForm(b"x")]
        frames = _id3(tags).getall("TXXX")
        self.assertEqual([(f.desc, list(f.text)) for f in frames],
                         [("ULTRAMIXER_DANCESTYLE", ["Jive"])])

    def test_unknown_atoms_alone_are_none(self):
        tags = MP4Tags()
        tags["cpil"] = True
        self.assertIsNone(as_id3(tags))


class RatingTest(unittest.TestCase):
    """⭐ The stars a tagger left in a FLAC/Ogg/M4A file, read as POPM."""

    def stars(self, tags):
        return parsing.popm_stars(as_id3(tags))

    def vorbis(self, name, value):
        tags = VCFLACDict()
        tags[name] = value
        return self.stars(tags)

    def test_a_five_star_scale_is_read_as_is(self):   # foobar2000
        self.assertEqual([self.vorbis("RATING", v) for v in "12345"], [1, 2, 3, 4, 5])

    def test_a_hundred_point_scale_is_read_in_fifths(self):   # MusicBee, MediaMonkey
        self.assertEqual([self.vorbis("RATING", str(v)) for v in (20, 40, 60, 80, 100)],
                         [1, 2, 3, 4, 5])
        self.assertEqual(self.vorbis("RATING", "50"), 3)

    def test_fmps_is_a_fraction(self):   # Picard, Amarok, Clementine
        self.assertEqual(self.vorbis("FMPS_RATING", "0.6"), 3)
        self.assertEqual(self.vorbis("FMPS_RATING", "1.0"), 5)

    def test_zero_or_text_is_unrated(self):
        self.assertIsNone(self.vorbis("RATING", "0"))
        self.assertIsNone(self.vorbis("RATING", "good"))

    def test_the_rating_is_no_txxx(self):
        tags = VCFLACDict()
        tags["RATING"] = "4"
        self.assertEqual(_id3(tags).getall("TXXX"), [])

    def test_an_m4a_freeform_rating(self):
        tags = MP4Tags()
        tags["----:com.apple.iTunes:RATING"] = [MP4FreeForm(b"80")]
        self.assertEqual(self.stars(tags), 4)


def _flac(seconds: int) -> Path:
    """A FLAC file with no audio: just the STREAMINFO block saying how long."""
    bits = (44100 << 44) | (1 << 41) | (15 << 36) | (44100 * seconds)
    info = (4096).to_bytes(2, "big") * 2 + bytes(6) + bits.to_bytes(8, "big") + bytes(16)
    path = Path(tempfile.mkdtemp(prefix="dp_flac_")) / "sway.flac"
    path.write_bytes(b"fLaC" + bytes([0x80, 0, 0, 34]) + info)
    return path


class ReadFromAFileTest(unittest.TestCase):
    """The parsing helpers see a FLAC file's tags as an MP3's."""

    def setUp(self):
        self.path = _flac(180)
        flac = FLAC(self.path)
        flac.add_tags()
        flac["TITLE"] = "Sway"
        flac["ULTRAMIXER_DANCESTYLE"] = "Rumba"
        flac["RATING"] = "4"
        flac.save()

    def test_the_one_parse_scan_reads_tags_and_length(self):
        tags, secs = parsing.read_tags_once(self.path)
        self.assertEqual(secs, 180)
        self.assertEqual(_text(tags, "TIT2"), ["Sway"])
        self.assertEqual(parsing.get_um_dance(tags), "RB")

    def test_the_single_readers_see_them_too(self):
        self.assertEqual(_text(parsing._id3_of(self.path), "TIT2"), ["Sway"])

    def test_a_library_scan_lists_it(self):
        lib = MusicLibrary()
        lib.scan(AudioCache(), music_dir=self.path.parent, learn=False, analyze=False,
                 interactive=False)
        (entry,) = lib.entries
        self.assertEqual((entry.path, entry.tag_title, entry.dance), (self.path, "Sway", "RB"))
        self.assertEqual(entry.rating, 4)


class UnknownTypeTest(unittest.TestCase):

    def test_an_id3_or_none_is_no_foreign_tag(self):
        self.assertIsNone(as_id3(None))
        self.assertIsNone(as_id3(ID3()))


if __name__ == "__main__":
    unittest.main()
