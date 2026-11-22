"""🏷 Fuzz: tags come out of files that converters, shops and old taggers wrote.

Callers: the library scan uses `read_tags_once` and `get_comment_tag` with no
guard of its own, so a damaged file must give "no tags", never an exception
that stops the scan. The tag editor (gui/dialogs/tag_edit_dialog.py) catches
OSError, ValueError and MutagenError around `id3_frames`.
"""
import tempfile
import unittest
from pathlib import Path

from hypothesis import given
from mutagen import MutagenError
from mutagen.id3 import COMM, ID3, POPM, TBPM, TIT2, TPE1, TXXX

from planner.music import id3_frames, parsing
from tests.fuzz_support import MP3_FRAME, fuzz, mutated, texts


def _seed() -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "seed.mp3"
        p.write_bytes(MP3_FRAME * 40)
        tag = ID3()
        tag.add(TIT2(encoding=3, text="Song 01 (LW 29)"))
        tag.add(TPE1(encoding=1, text="Orchester Beispiel"))
        tag.add(COMM(encoding=3, lang="eng", desc="", text="B;A;S;instr"))
        tag.add(COMM(encoding=0, lang="eng", desc="iTunNORM", text="00000000 000002a0"))
        tag.add(TBPM(encoding=3, text="29"))
        tag.add(TXXX(encoding=3, desc="ultramixer_meter", text="3/4"))
        tag.add(POPM(email="Windows Media Player 9 Series", rating=196, count=0))
        tag.save(p, v1=2)            # an ID3v1 tail as well
        return p.read_bytes()


SEED = _seed()


class TagReadFuzzTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "Song 01 (LW 29).mp3"

    @fuzz(80)
    @given(mutated(SEED))
    def test_the_scan_reads_a_damaged_file_without_raising(self, data):
        self.path.write_bytes(data)
        tags, secs = parsing.read_tags_once(self.path)
        self.assertIsInstance(secs, int)
        comment = parsing.get_comment_tag(self.path, tags)
        if comment is not None:
            parsing.parse_class_tag(comment)
            parsing.parse_comment_markers(comment)
        parsing.read_id3v1_comment(self.path)

    @fuzz(60)
    @given(mutated(SEED))
    def test_the_tag_editor_reads_a_damaged_file_or_says_why(self, data):
        self.path.write_bytes(data)
        try:
            id3_frames.read_fields(self.path)
            id3_frames.read_form(self.path)
            id3_frames.read_cover(self.path)
            id3_frames.tag_version(self.path)
        except (OSError, ValueError, MutagenError):
            pass


class CommentFieldFuzzTest(unittest.TestCase):
    """The comment field is free text: whatever is in it, the class parser
    answers with a list of codes or None, and a bool."""

    @fuzz(150)
    @given(texts)
    def test_any_comment_parses(self, s):
        classes, instr = parsing.parse_class_tag(s)
        self.assertIsInstance(instr, bool)
        self.assertTrue(classes is None or all(isinstance(c, str) for c in classes))
        markers = parsing.parse_comment_markers(s)
        self.assertEqual(len(markers), len(set(markers)))


if __name__ == "__main__":
    unittest.main()
