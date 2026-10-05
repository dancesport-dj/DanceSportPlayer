"""🏷 Every ID3 frame of one MP3, read and written back for the tag editor's
form and "Extended tags" tab.

Run:  py -m unittest tests.planner.test_id3_frames -v

The library is mostly ID3v2.3 with UltraMixer's TXXX frames, WMP's POPM and
MediaMonkey's COMM in it. Writing one field must leave every other frame —
and the tag's version — exactly as it was, and a bad input must leave the file
untouched.
"""
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from mutagen.id3 import APIC, COMM, ID3, POPM, PRIV, TBPM, TDRC, TIT2, TPE1, TXXX, TYER, WXXX

from planner.id3_frames import (
    FORM_FIELDS,
    TagField,
    addable_frames,
    sample_custom,
    read_cover,
    read_fields,
    read_form,
    tag_version,
    write_app_fields,
    write_fields,
    write_tags,
)
from planner.parsing import _get_comment_tag, _parse_class_tag, parse_comment_markers, popm_stars

_AUDIO = b"\xff\xfb\x90\x00" + b"\x00" * 4000


class _FileTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_id3_"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def mp3(self, *frames, version=3, name="t.mp3") -> Path:
        p = self.dir / name
        p.write_bytes(_AUDIO)
        if frames:
            tags = ID3()
            for f in frames:
                tags.add(f)
            if version == 3:
                tags.update_to_v23()
            tags.save(p, v2_version=version, v23_sep=None)
        return p

    def by_key(self, path) -> dict[str, TagField]:
        return {f.key: f for f in read_fields(path)}


def _library_like():
    return (TIT2(encoding=1, text="Senorita"),
            TPE1(encoding=1, text="Band"),
            TBPM(encoding=0, text="50"),
            TYER(encoding=0, text="2019"),
            TXXX(encoding=1, desc="ultramixer_meter", text="4/4"),
            TXXX(encoding=1, desc="replaygain_track_gain", text="-6.10 dB"),
            COMM(encoding=1, lang="eng", desc="Songs-DB_Custom1", text="ab C;classic"),
            COMM(encoding=1, lang="eng", desc="", text="vocal_f"),
            POPM(email="Windows Media Player 9 Series", rating=196, count=3),
            WXXX(encoding=0, desc="shop", url="http://example.com/x"),
            APIC(encoding=0, mime="image/jpeg", type=3, desc="cover", data=b"\xff\xd8" * 50),
            PRIV(owner="WM/MediaClassPrimaryID", data=b"\x01\x02\x03"))


class ReadTest(_FileTest):

    def test_every_frame_is_listed_with_its_key(self):
        f = self.by_key(self.mp3(*_library_like()))
        self.assertEqual(f["TIT2"].value, "Senorita")
        self.assertEqual(f["TXXX:ultramixer_meter"].desc, "ultramixer_meter")
        self.assertEqual(f["TXXX:ultramixer_meter"].value, "4/4")
        self.assertEqual(f["COMM:Songs-DB_Custom1:eng"].value, "ab C;classic")
        self.assertEqual(f["POPM:Windows Media Player 9 Series"].value, "196")
        self.assertEqual(f["WXXX:shop"].value, "http://example.com/x")
        self.assertEqual(f["APIC:cover"].frame, "APIC")

    def test_text_comment_url_and_rating_are_editable_binary_is_not(self):
        f = self.by_key(self.mp3(*_library_like()))
        for key in ("TIT2", "TBPM", "TXXX:ultramixer_meter", "COMM::eng",
                    "POPM:Windows Media Player 9 Series", "WXXX:shop"):
            self.assertTrue(f[key].editable, key)
        for key in ("APIC:cover", "PRIV:WM/MediaClassPrimaryID:\x01\x02\x03"):
            self.assertFalse(f[key].editable, key)

    def test_a_binary_frame_says_what_it_is(self):
        apic = self.by_key(self.mp3(*_library_like()))["APIC:cover"]
        self.assertIn("image/jpeg", apic.value)
        self.assertIn("100", apic.value)

    def test_a_v23_year_is_shown_as_the_file_has_it(self):
        f = self.by_key(self.mp3(*_library_like()))
        self.assertIn("TYER", f)
        self.assertNotIn("TDRC", f)

    def test_several_values_are_joined(self):
        f = self.by_key(self.mp3(TPE1(encoding=1, text=["A", "B"])))
        self.assertEqual(f["TPE1"].value, "A; B")

    def test_a_file_without_a_tag_has_no_fields(self):
        self.assertEqual(read_fields(self.mp3()), [])

    def test_the_version_a_write_keeps(self):
        self.assertEqual(tag_version(self.mp3(TIT2(encoding=1, text="x"), name="3.mp3")), 3)
        self.assertEqual(tag_version(self.mp3(TIT2(encoding=1, text="x"), version=4,
                                              name="4.mp3")), 4)
        self.assertEqual(tag_version(self.mp3(name="none.mp3")), 3)


class WriteTest(_FileTest):

    def test_one_field_changes_and_nothing_else(self):
        p = self.mp3(*_library_like())
        before = self.by_key(p)
        self.assertTrue(write_fields(p, sets={"TXXX:ultramixer_meter": "3/4"}))
        after = self.by_key(p)
        self.assertEqual(after.pop("TXXX:ultramixer_meter").value, "3/4")
        before.pop("TXXX:ultramixer_meter")
        self.assertEqual(after, before)

    def test_the_tag_keeps_its_version(self):
        for version in (3, 4):
            p = self.mp3(TIT2(encoding=1, text="x"), version=version, name=f"v{version}.mp3")
            write_fields(p, sets={"TIT2": "y"})
            self.assertEqual(ID3(p).version, (2, version, 0))

    def test_a_v22_tag_is_written_as_v23(self):
        p = self.dir / "v22.mp3"
        body = b"\x00Old title"
        frame = b"TT2" + struct.pack(">I", len(body))[1:] + body
        size = len(frame)
        syncsafe = bytes((size >> s) & 0x7F for s in (21, 14, 7, 0))
        p.write_bytes(b"ID3\x02\x00\x00" + syncsafe + frame + _AUDIO)
        self.assertEqual(self.by_key(p)["TIT2"].value, "Old title")
        write_fields(p, sets={"TIT2": "New title"})
        self.assertEqual(ID3(p).version, (2, 3, 0))
        self.assertEqual(self.by_key(p)["TIT2"].value, "New title")

    def test_several_values_are_split_back(self):
        p = self.mp3(TPE1(encoding=1, text=["A", "B"]))
        write_fields(p, sets={"TPE1": "A; C"})
        self.assertEqual(ID3(p)["TPE1"].text, ["A", "C"])

    def test_one_value_with_a_semicolon_stays_one(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="classic"))
        write_fields(p, sets={"COMM::eng": "ab C;classic"})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["ab C;classic"])

    def test_a_latin1_frame_takes_any_text(self):
        p = self.mp3(TIT2(encoding=0, text="Senorita"))
        write_fields(p, sets={"TIT2": "Señorita ♥"})
        self.assertEqual(self.by_key(p)["TIT2"].value, "Señorita ♥")

    def test_the_rating_keeps_its_play_count(self):
        p = self.mp3(*_library_like())
        write_fields(p, sets={"POPM:Windows Media Player 9 Series": "255"})
        popm = ID3(p)["POPM:Windows Media Player 9 Series"]
        self.assertEqual((popm.rating, popm.count), (255, 3))

    def test_a_frame_goes_binary_ones_too(self):
        p = self.mp3(*_library_like())
        write_fields(p, deletes=["APIC:cover", "TXXX:replaygain_track_gain"])
        f = self.by_key(p)
        self.assertNotIn("APIC:cover", f)
        self.assertNotIn("TXXX:replaygain_track_gain", f)
        self.assertIn("TXXX:ultramixer_meter", f)

    def test_new_fields_are_added(self):
        p = self.mp3(*_library_like())
        write_fields(p, adds=[("TXXX", "my_note", "slow intro"),
                              ("COMM", "Songs-DB_Custom2", "ab B"),
                              ("TALB", "", "Best of")])
        f = self.by_key(p)
        self.assertEqual(f["TXXX:my_note"].value, "slow intro")
        self.assertEqual(f["COMM:Songs-DB_Custom2:eng"].value, "ab B")
        self.assertEqual(f["TALB"].value, "Best of")

    def test_an_emptied_text_field_is_gone(self):
        p = self.mp3(*_library_like())
        write_fields(p, sets={"TXXX:ultramixer_meter": "", "TIT2": ""})
        f = self.by_key(p)
        self.assertNotIn("TXXX:ultramixer_meter", f)
        self.assertNotIn("TIT2", f)
        self.assertIn("TPE1", f)

    def test_a_file_without_a_tag_gets_a_v23_one(self):
        p = self.mp3()
        write_fields(p, adds=[("TXXX", "my_note", "x")])
        self.assertEqual(ID3(p).version, (2, 3, 0))
        self.assertEqual(self.by_key(p)["TXXX:my_note"].value, "x")
        self.assertTrue(p.read_bytes().endswith(_AUDIO))

    def test_the_old_v1_tag_is_left_as_it_was(self):
        """377 library files carry their classes only in the ID3v1 comment;
        mutagen's save(v1=1) rebuilds that tag from v2 and blanks the comment."""
        p = self.mp3(*_library_like())
        v1 = (b"TAG" + b"Old title".ljust(30, b"\0") + b"Old artist".ljust(30, b"\0")
              + b"Album".ljust(30, b"\0") + b"2001"
              + b"D;C;B;vocal_f".ljust(28, b"\0") + b"\0\x05\xff")
        with open(p, "ab") as fh:
            fh.write(v1)
        write_fields(p, sets={"TIT2": "New"}, adds=[("TXXX", "my_note", "x")])
        self.assertEqual(p.read_bytes()[-128:], v1)
        self.assertEqual(self.by_key(p)["TIT2"].value, "New")

    def test_no_v1_tag_is_made_up(self):
        p = self.mp3(*_library_like())
        write_fields(p, sets={"TIT2": "New"})
        self.assertNotEqual(p.read_bytes()[-128:-125], b"TAG")

    def test_nothing_to_do_leaves_the_file_alone(self):
        p = self.mp3(*_library_like())
        before = p.read_bytes()
        self.assertFalse(write_fields(p))
        self.assertEqual(p.read_bytes(), before)


class RefusedTest(_FileTest):
    """Every input is checked before the file is opened for writing: one bad
    field means nothing is written, not the good half."""

    def assertRefused(self, p, **kw):
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            write_fields(p, **kw)
        self.assertEqual(p.read_bytes(), before)

    def test_a_rating_must_be_0_to_255(self):
        p = self.mp3(*_library_like())
        for bad in ("x", "256", "-1", "4.5"):
            self.assertRefused(p, sets={"TIT2": "fine",
                                        "POPM:Windows Media Player 9 Series": bad})

    def test_a_field_not_in_the_file(self):
        p = self.mp3(*_library_like())
        self.assertRefused(p, sets={"TXXX:nope": "x"})
        self.assertRefused(p, deletes=["TALB"])

    def test_a_binary_frame_cant_be_edited(self):
        self.assertRefused(self.mp3(*_library_like()), sets={"APIC:cover": "x"})

    def test_a_new_field_that_already_exists(self):
        p = self.mp3(*_library_like())
        self.assertRefused(p, adds=[("TXXX", "ultramixer_meter", "x")])
        self.assertRefused(p, adds=[("TIT2", "", "x")])
        self.assertRefused(p, adds=[("TXXX", "a", "x"), ("TXXX", "a", "y")])

    def test_a_frame_that_cant_be_added(self):
        self.assertRefused(self.mp3(*_library_like()), adds=[("APIC", "", "x")])

    def test_a_url_must_be_latin1(self):
        self.assertRefused(self.mp3(*_library_like()), sets={"WXXX:shop": "http://ä♥"})

    def test_only_mp3_files(self):
        p = self.dir / "t.flac"
        p.write_bytes(b"fLaC" + _AUDIO)
        self.assertRefused(p, adds=[("TXXX", "a", "x")])


class AppFieldsTest(_FileTest):
    """Stars, classes, instrumental and markers written where the app reads
    them: the Windows POPM rating and the comment."""

    def read_back(self, p):
        """What a library scan makes of the file."""
        comment = _get_comment_tag(p)
        classes, instr = _parse_class_tag(comment) if comment else (None, False)
        markers = parse_comment_markers(comment) if comment else []
        return popm_stars(ID3(p)), classes, instr, markers

    def test_stars_go_into_the_windows_rating(self):
        p = self.mp3(TIT2(encoding=1, text="x"))
        self.assertTrue(write_app_fields(p, {"rating": 4}))
        popm = ID3(p)["POPM:Windows Media Player 9 Series"]
        self.assertEqual((popm.rating, popm.count), (196, 0))
        self.assertEqual(self.read_back(p)[0], 4)

    def test_the_windows_rating_keeps_its_play_count(self):
        p = self.mp3(*_library_like())
        write_app_fields(p, {"rating": 2})
        popm = ID3(p)["POPM:Windows Media Player 9 Series"]
        self.assertEqual((popm.rating, popm.count), (64, 3))

    def test_no_stars_unrates(self):
        p = self.mp3(*_library_like())
        write_app_fields(p, {"rating": 0})
        self.assertIsNone(self.read_back(p)[0])

    def test_classes_replace_only_the_classes(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="ab C;instr;vocal_f"))
        write_app_fields(p, {"classes_ok": ["S", "A"]})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["A;S;instr;vocal_f"])
        self.assertEqual(self.read_back(p)[1:], (["A", "S"], True, ["vocal_f"]))

    def test_no_class_means_every_class(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="C;B;vocal_f"))
        write_app_fields(p, {"classes_ok": []})
        self.assertEqual(self.read_back(p)[1:], (None, False, ["vocal_f"]))

    def test_instrumental_and_markers(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="C;B;Vocal_F;classic"))
        write_app_fields(p, {"is_instrumental": True, "comment_tags": ["slow intro"]})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["C;B;instr;slow intro"])
        write_app_fields(p, {"is_instrumental": False})
        self.assertEqual(self.read_back(p)[1:], (["C", "B"], False, ["slow intro"]))

    def test_other_text_in_the_comment_stays(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="",
                          text="Erscheinungsdatum 2016;C;vocal_m"))
        write_app_fields(p, {"comment_tags": []})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["Erscheinungsdatum 2016;C"])

    def test_a_file_without_a_comment_gets_one(self):
        p = self.mp3(TIT2(encoding=0, text="x"))
        write_app_fields(p, {"classes_ok": ["D", "C"], "comment_tags": ["vocal_f"]})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["D;C;vocal_f"])
        self.assertEqual(self.read_back(p)[1:], (["D", "C"], False, ["vocal_f"]))

    def test_classes_from_the_v1_comment_move_up_and_the_comment_text_stays(self):
        """260 library files: the classes in the ID3v1 comment, a release date
        in the v2 one. The write puts both into the v2 comment."""
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="Erscheinungsdatum 2016"))
        v1 = (b"TAG" + b"t".ljust(30, b"\0") + b"a".ljust(30, b"\0") + b"b".ljust(30, b"\0")
              + b"2016" + b"C;B;vocal_m".ljust(28, b"\0") + b"\0\x01\xff")
        with open(p, "ab") as fh:
            fh.write(v1)
        write_app_fields(p, {"classes_ok": ["B", "A"]})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["B;A;vocal_m;Erscheinungsdatum 2016"])
        self.assertEqual(self.read_back(p)[1:], (["B", "A"], False, ["vocal_m"]))
        self.assertEqual(p.read_bytes()[-128:], v1)

    def test_technical_comments_are_left_alone(self):
        p = self.mp3(COMM(encoding=1, lang="eng", desc="iTunNORM", text=" 0000 0001"),
                     *_library_like())
        write_app_fields(p, {"classes_ok": ["S"]})
        self.assertEqual(ID3(p)["COMM:iTunNORM:eng"].text, [" 0000 0001"])
        self.assertEqual(ID3(p)["COMM:Songs-DB_Custom1:eng"].text, ["ab C;classic"])

    def test_everything_else_in_the_tag_stays(self):
        p = self.mp3(*_library_like())
        before = self.by_key(p)
        write_app_fields(p, {"classes_ok": ["S"]})
        after = self.by_key(p)
        self.assertEqual(after.pop("COMM::eng").value, "S;classic;vocal_f")
        before.pop("COMM::eng")
        self.assertEqual(after, before)

    def test_refused_without_touching_the_file(self):
        p = self.mp3(*_library_like())
        before = p.read_bytes()
        for bad in ({"rating": 6}, {"rating": -1}, {"classes_ok": ["X"]}, {"title": "x"}):
            with self.assertRaises(ValueError):
                write_app_fields(p, bad)
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse(write_app_fields(p, {}))


class FormTest(_FileTest):
    """The Mp3tag-style form: fixed fields, found wherever this file keeps them."""

    def form(self, p) -> dict:
        return {k: (f.key, f.value) for k, f in read_form(p).items() if f is not None}

    def test_the_fields_of_a_library_file(self):
        f = self.form(self.mp3(*_library_like()))
        self.assertEqual(f, {"title": ("TIT2", "Senorita"),
                             "artist": ("TPE1", "Band"),
                             "year": ("TYER", "2019"),
                             "comment": ("COMM::eng", "vocal_f"),
                             "replaygain": ("TXXX:replaygain_track_gain", "-6.10 dB")})
        self.assertEqual(set(read_form(self.mp3(*_library_like()))), set(FORM_FIELDS))

    def test_the_year_where_the_version_keeps_it(self):
        self.assertEqual(self.form(self.mp3(TDRC(encoding=0, text="2021"), version=4)),
                         {"year": ("TDRC", "2021")})
        # A v2.3 tag with only a TDRC, as other taggers write it (mutagen
        # turns it into a TYER): a small v2.4 frame is byte-identical in v2.3.
        p = self.mp3(TDRC(encoding=0, text="2020"), version=4, name="b.mp3")
        data = bytearray(p.read_bytes())
        data[3] = 3
        p.write_bytes(bytes(data))
        self.assertEqual(tag_version(p), 3)
        self.assertEqual(self.form(p), {"year": ("TDRC", "2020")})

    def test_replaygain_in_any_case(self):
        p = self.mp3(TXXX(encoding=0, desc="REPLAYGAIN_TRACK_GAIN", text="+1.20 dB"))
        self.assertEqual(self.form(p), {"replaygain": ("TXXX:REPLAYGAIN_TRACK_GAIN", "+1.20 dB")})

    def test_a_file_without_a_tag(self):
        p = self.mp3()
        self.assertEqual(self.form(p), {})
        self.assertIsNone(read_cover(p))

    def test_set_add_and_blank(self):
        p = self.mp3(*_library_like())
        self.assertTrue(write_tags(p, form={"title": "Señorita", "album": "Latin Hits",
                                            "disc": "1/2", "replaygain": "-5.00 dB",
                                            "comment": ""}))
        f = self.by_key(p)
        self.assertEqual(f["TIT2"].value, "Señorita")
        self.assertEqual(f["TALB"].value, "Latin Hits")
        self.assertEqual(f["TPOS"].value, "1/2")
        self.assertEqual(f["TXXX:replaygain_track_gain"].value, "-5.00 dB")
        self.assertNotIn("COMM::eng", f)
        self.assertEqual(f["COMM:Songs-DB_Custom1:eng"].value, "ab C;classic")
        self.assertEqual(tag_version(p), 3)

    def test_a_new_year_and_replaygain_as_the_file_spells_them(self):
        p3 = self.mp3(TIT2(encoding=0, text="x"))
        p4 = self.mp3(TIT2(encoding=0, text="x"), version=4, name="b.mp3")
        for p in (p3, p4):
            write_tags(p, form={"year": "2024", "replaygain": "-3.00 dB"})
        self.assertIn("TYER", self.by_key(p3))
        self.assertIn("TDRC", self.by_key(p4))
        self.assertIn("TXXX:replaygain_track_gain", self.by_key(p3))

    def test_a_typed_comment_and_app_classes_in_one_write(self):
        p = self.mp3(*_library_like())
        write_tags(p, form={"comment": "Erscheinungsdatum 2016"}, app={"classes_ok": ["C"]})
        self.assertEqual(ID3(p)["COMM::eng"].text, ["C;classic;Erscheinungsdatum 2016"])

    def test_the_extended_table_form_and_app_together(self):
        p = self.mp3(*_library_like())
        write_tags(p, raw={"sets": {"TXXX:ultramixer_meter": "3/4"}},
                   form={"artist": "Other"}, app={"rating": 5})
        f = self.by_key(p)
        self.assertEqual((f["TXXX:ultramixer_meter"].value, f["TPE1"].value), ("3/4", "Other"))
        self.assertEqual(popm_stars(ID3(p)), 5)

    def test_refused_without_touching_the_file(self):
        p = self.mp3(*_library_like())
        before = p.read_bytes()
        for bad in ({"form": {"bpm": "50"}}, {"form": {"title": "x"}, "app": {"rating": 9}},
                    {"form": {"title": "x"}, "raw": {"sets": {"TIT2": "y"}}}):
            with self.assertRaises(ValueError):
                write_tags(p, **bad)
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse(write_tags(p))
        self.assertFalse(write_tags(p, form={"album": ""}), "blank and not there: nothing")

    def test_the_front_cover(self):
        p = self.mp3(APIC(encoding=0, mime="image/png", type=0, desc="", data=b"other"),
                     APIC(encoding=0, mime="image/jpeg", type=3, desc="front", data=b"front"))
        self.assertEqual(read_cover(p), b"front")
        self.assertEqual(read_cover(self.mp3(*_library_like(), name="b.mp3")), b"\xff\xd8" * 50)


class SampleCustomTest(_FileTest):
    """What the Custom mapping dialog offers: the descriptions some MP3s of
    the archive really have, how often, and one value."""

    def test_it_counts_each_description_once_per_file(self):
        a = self.mp3(*_library_like(), name="a.mp3")
        b = self.mp3(TXXX(encoding=1, desc="ULTRAMIXER_meter", text="3/4"),
                     TXXX(encoding=1, desc="ultramixer_last_played", text="-1"), name="b.mp3")
        read, found = sample_custom([a, b])
        self.assertEqual(read, 2)
        self.assertEqual(found[("TXXX", "ultramixer_meter")], (2, "4/4"))
        self.assertEqual(found[("COMM", "Songs-DB_Custom1")], (1, "ab C;classic"))
        self.assertEqual(found[("TXXX", "ultramixer_last_played")], (1, "-1"))

    def test_what_cannot_be_mapped_is_left_out(self):
        _read, found = sample_custom([self.mp3(*_library_like())])
        fids = {fid for fid, _d in found}
        self.assertNotIn(("COMM", ""), found)       # the plain comment: the classes
        self.assertNotIn("TIT2", fids)              # the form shows it
        self.assertNotIn("APIC", fids)

    def test_a_file_without_a_tag_is_not_counted(self):
        read, found = sample_custom([self.mp3(name="bare.mp3"), self.dir / "gone.mp3"])
        self.assertEqual((read, found), (0, {}))

    def test_it_looks_into_at_most_the_limit_spread_over_all(self):
        paths = [self.mp3(TXXX(encoding=1, desc=f"d{i}", text="x"), name=f"{i}.mp3")
                 for i in range(10)]
        read, found = sample_custom(paths, limit=3)
        self.assertEqual(read, 3)
        self.assertEqual(sorted(d for _f, d in found), ["d0", "d3", "d6"])


class AddableTest(unittest.TestCase):

    def test_custom_fields_first_and_the_year_per_version(self):
        v3, v4 = addable_frames(3), addable_frames(4)
        self.assertEqual(v3[:2], ["TXXX", "COMM"])
        self.assertIn("TYER", v3)
        self.assertNotIn("TDRC", v3)
        self.assertIn("TDRC", v4)

    def test_frames_already_there_are_not_offered(self):
        self.assertNotIn("TIT2", addable_frames(3, present={"TIT2", "TXXX:a"}))
        self.assertIn("TXXX", addable_frames(3, present={"TIT2", "TXXX:a"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
