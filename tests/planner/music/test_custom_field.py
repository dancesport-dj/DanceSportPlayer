"""The one free "Custom" field of a track, and the MP3 tag it can be mapped to.

Run:  py -m unittest tests.planner.music.test_custom_field -v

Marcel: a field the DJ fills in the 🏷 editor, kept in the app like the
classes — and a mapping, so an existing MP3 tag (Custom text (TXXX) with the
description ultramixer_last_played) fills it. The mapped tag fills the field,
what is typed in the app wins; on Save, after asking, the typed value goes into
that frame.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_custom_"))

from mutagen.id3 import COMM, ID3, TIT1, TIT2, TXXX

import planner.music.db as pdb
import planner.music.scan_caches as scan_caches
from planner.music import custom_field, id3_frames, tag_edits
from planner.music.library import MusicLibrary
from planner.models import MusicEntry
from tests.db_support import use_scratch_db

_AUDIO = b"\xff\xfb\x90\x00" + b"\x00" * 4000


class _ScratchDb(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_custom_db_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        use_scratch_db(self, self.dir / "scratch.db")

    def mp3(self, *frames, name="t.mp3") -> Path:
        p = self.dir / name
        p.write_bytes(_AUDIO)
        if frames:
            tags = ID3()
            for f in frames:
                tags.add(f)
            tags.update_to_v23()
            tags.save(p, v2_version=3, v23_sep=None)
        return p


def _ultramixer(value="-1"):
    return TXXX(encoding=1, desc="ultramixer_last_played", text=value)


def v1_tail(comment=b"vocal AS", title=b"T") -> bytes:
    """An ID3v1.1 tag: 128 bytes at the end of the file, track number 1."""
    tag = (b"TAG" + title.ljust(30, b"\0") + b"A".ljust(30, b"\0")
           + b"Al".ljust(30, b"\0") + b"2000" + comment.ljust(28, b"\0")
           + b"\0\x01" + b"\xff")
    assert len(tag) == 128
    return tag


class SourceTest(_ScratchDb):

    def test_nothing_is_mapped_at_first(self):
        self.assertIsNone(custom_field.source())

    def test_a_mapping_is_kept_in_the_database(self):
        self.assertTrue(custom_field.set_source("TXXX", "ultramixer_last_played"))
        self.assertEqual(custom_field.source(), ("TXXX", "ultramixer_last_played"))

    def test_a_standard_frame_has_no_description(self):
        custom_field.set_source("TIT1", "ignored")
        self.assertEqual(custom_field.source(), ("TIT1", ""))

    def test_setting_the_same_mapping_again_changes_nothing(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.assertFalse(custom_field.set_source("TXXX", "ultramixer_last_played"))

    def test_none_takes_the_mapping_away(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.assertTrue(custom_field.set_source(None))
        self.assertIsNone(custom_field.source())

    def test_a_new_mapping_forgets_the_values_read_for_the_old_one(self):
        """The scan cache keeps the file value of the mapped frame; under a new
        mapping it is NULL again, which the next scan reads afresh."""
        custom_field.set_source("TXXX", "a")
        conn = pdb._db()
        cols = ",".join(pdb._META_COLS)
        meta = {"title": "x", "custom": "old"}
        conn.execute(f"INSERT INTO scan_meta (ckey, {cols}) VALUES "
                     f"(?, {','.join('?' * len(pdb._META_COLS))})",
                     ("fp::x", *pdb._meta_to_row(meta)))
        custom_field.set_source("TXXX", "b")
        row = conn.execute(f"SELECT {cols} FROM scan_meta").fetchone()
        self.assertIsNone(pdb._row_to_meta(row)["custom"])

    def test_the_frames_a_mapping_can_name(self):
        """The custom ones, then standard text frames the form doesn't own —
        Title or Year mapped to Custom would be edited in two places."""
        frames = id3_frames.custom_frames()
        self.assertEqual(frames[:2], ["TXXX", "COMM"])
        self.assertIn("TIT1", frames)
        for owned in ("TIT2", "TPE1", "TALB", "TCON", "TYER", "TDRC", "TRCK"):
            self.assertNotIn(owned, frames)


class ReadTest(_ScratchDb):

    def test_the_mapped_frame_is_read(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("1696263829"))
        self.assertEqual(custom_field.read_file(p), "1696263829")

    def test_the_description_is_matched_in_any_case(self):
        custom_field.set_source("TXXX", "UltraMixer_Last_Played")
        self.assertEqual(custom_field.read_file(self.mp3(_ultramixer("-1"))), "-1")

    def test_a_comment_with_a_description(self):
        custom_field.set_source("COMM", "Songs-DB_Custom2")
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="C;B"),
                     COMM(encoding=1, lang="eng", desc="Songs-DB_Custom2", text="Hochzeit"))
        self.assertEqual(custom_field.read_file(p), "Hochzeit")

    def test_a_standard_frame(self):
        custom_field.set_source("TIT1", "")
        self.assertEqual(custom_field.read_file(self.mp3(TIT1(encoding=1, text="Gala"))), "Gala")

    def test_blank_without_the_frame_or_without_a_mapping(self):
        p = self.mp3(TIT2(encoding=1, text="x"))
        self.assertEqual(custom_field.read_file(p), "")
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.assertEqual(custom_field.read_file(p), "")
        self.assertEqual(custom_field.read_file(self.dir / "gone.mp3"), "")


class Id3v1Test(_ScratchDb):
    """Marcel: "for the custom fields mapping make sure you support v1 and v2
    of mp3tags". ID3v1 has no custom fields; its comment is what can fill
    Custom. Read only: 28 Latin-1 characters, and where the classes of many
    older files live."""

    def v1(self, *frames, comment=b"vocal AS", name="v1.mp3") -> Path:
        p = self.mp3(*frames, name=name)
        with open(p, "ab") as fh:
            fh.write(v1_tail(comment))
        return p

    def test_it_can_be_named(self):
        self.assertIn(custom_field.V1, id3_frames.custom_frames())
        custom_field.set_source(custom_field.V1, "ignored")
        self.assertEqual(custom_field.source(), (custom_field.V1, ""))

    def test_a_file_with_only_the_old_tag(self):
        custom_field.set_source(custom_field.V1)
        self.assertEqual(custom_field.read_file(self.v1()), "vocal AS")

    def test_the_old_tag_beside_a_new_one(self):
        """The v1 comment, not the v2 one."""
        custom_field.set_source(custom_field.V1)
        p = self.v1(COMM(encoding=1, lang="eng", desc="", text="C;B"))
        self.assertEqual(custom_field.read_file(p), "vocal AS")

    def test_blank_without_the_old_tag(self):
        custom_field.set_source(custom_field.V1)
        self.assertEqual(custom_field.read_file(self.mp3(TIT2(encoding=1, text="x"))), "")
        self.assertEqual(custom_field.read_file(self.dir / "gone.mp3"), "")

    def test_a_scan_reads_it_with_the_path(self):
        custom_field.set_source(custom_field.V1)
        p = self.v1(TIT2(encoding=1, text="x"))
        self.assertEqual(custom_field.value_of(ID3(p), p), "vocal AS")

    def test_only_a_frame_of_the_new_tag_is_written(self):
        self.assertFalse(custom_field.writable())
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.assertTrue(custom_field.writable())
        custom_field.set_source(custom_field.V1)
        self.assertFalse(custom_field.writable())

    def test_a_write_into_it_is_refused(self):
        custom_field.set_source(custom_field.V1)
        p = self.v1(TIT2(encoding=1, text="x"))
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            id3_frames.write_tags(p, app={"custom": "Gala"})
        self.assertEqual(p.read_bytes(), before)


class _StubScan:
    """The ScanCache seam, as a dict."""

    def __init__(self, cached=None):
        self._cache = None
        self.store = dict(cached or {})

    def get(self, path):
        return self.store.get(str(path))

    def put(self, path, data):
        self.store[str(path)] = dict(data)

    def save(self):
        pass

    def forget_custom(self):
        for meta in self.store.values():
            meta["custom"] = None


class ScanTest(_ScratchDb):

    def setUp(self):
        super().setUp()
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.lib = MusicLibrary()

    def test_a_scan_reads_the_mapped_frame(self):
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("-1"))
        scan = _StubScan()
        self.assertEqual(self.lib._make_entry(p, scan).custom, "-1")
        self.assertEqual(scan.store[str(p)]["custom"], "-1")

    def test_a_cached_row_without_it_reads_it_once(self):
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("7"))
        scan = _StubScan({str(p): {"title": "x", "duration": 1, "comment_tags": [],
                                   "tag_album": "", "custom": None}})
        self.assertEqual(self.lib._make_entry(p, scan).custom, "7")
        self.assertEqual(scan.store[str(p)]["custom"], "7")

    def test_without_a_mapping_a_cached_row_is_not_rewritten(self):
        """None and '' both show a blank cell; healing them would write every
        row of the library once on the first load after the upgrade."""
        custom_field.set_source(None)
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("7"))
        row = {"title": "x", "duration": 1, "comment_tags": [], "tag_album": "",
               "custom": None}
        scan = _StubScan({str(p): row})
        puts = []
        scan.put = lambda path, data: puts.append(data)
        self.assertEqual(self.lib._make_entry(p, scan).custom, None)
        # The row's other lazy heals may still write it; Custom stays unread.
        self.assertEqual([d["custom"] for d in puts if "custom" in d and d["custom"] is not None], [])

    def test_the_column_is_in_the_scan_cache(self):
        self.assertIn("custom", pdb._META_COLS)
        self.assertEqual(pdb._row_to_meta(pdb._meta_to_row({"custom": "x"}))["custom"], "x")


class _Cache:

    def __init__(self, fps):
        self.fps = fps

    def recorded_fingerprint(self, path):
        return self.fps.get(str(path))

    fingerprint = recorded_fingerprint


class EditTest(_ScratchDb):

    def setUp(self):
        super().setUp()
        self.lib = MusicLibrary()
        self.e = MusicEntry(path=Path("C:/m/x.mp3"), title="x", custom="-1")
        self.lib.entries = [self.e]
        self.cache = _Cache({str(self.e.path): "fpX"})

    def test_what_is_typed_in_the_app_wins(self):
        self.lib.edit_tags([self.e], self.cache, {"custom": "Hochzeit 2025"})
        self.assertEqual(self.e.custom, "Hochzeit 2025")
        self.assertEqual(tag_edits.load("fpX"), {"custom": "Hochzeit 2025"})
        self.assertEqual(self.e.tag_edits, {"custom": "-1"})

    def test_emptying_it_is_an_explicit_blank(self):
        self.lib.edit_tags([self.e], self.cache, {"custom": ""})
        self.assertEqual(self.e.custom, "")
        self.assertEqual(tag_edits.load("fpX"), {"custom": ""})

    def test_typing_the_files_value_stores_nothing(self):
        self.lib.edit_tags([self.e], self.cache, {"custom": "-1"})
        self.assertEqual(tag_edits.load("fpX"), {})

    def test_reset_brings_back_the_files_value(self):
        self.lib.edit_tags([self.e], self.cache, {"custom": "x"})
        self.lib.reset_tag_edits([self.e], self.cache)
        self.assertEqual((self.e.custom, self.e.tag_edits), ("-1", None))


class ReadAgainTest(_ScratchDb):
    """A new mapping: the loaded tracks read the new frame, in the background."""

    def setUp(self):
        super().setUp()
        self.lib = MusicLibrary()
        self.p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("-1"),
                          TIT1(encoding=1, text="Gala"))
        self.e = MusicEntry(path=self.p, title="x", custom="-1")
        self.lib.entries = [self.e]
        self.scan = _StubScan({str(self.p): {"title": "x", "custom": "-1"}})
        self.lib._scan_cache = self.scan
        self.lib._scan_cache._cache = self.cache = _Cache({})

    def test_the_new_frame_is_read_and_kept(self):
        custom_field.set_source("TIT1", "")
        changed = self.lib.read_custom([self.e], self.cache)
        self.assertEqual(self.e.custom, "Gala")
        self.assertEqual(self.scan.store[str(self.p)]["custom"], "Gala")
        self.assertEqual([str(p) for p in changed], [str(self.p)])

    def test_an_app_value_still_wins(self):
        tag_edits.apply(self.e, {"custom": "mine"})
        custom_field.set_source("TIT1", "")
        self.lib.read_custom([self.e], self.cache)
        self.assertEqual(self.e.custom, "mine")
        self.assertEqual(self.e.tag_edits, {"custom": "Gala"})

    def test_an_unchanged_value_is_not_reported(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.assertEqual(self.lib.read_custom([self.e], self.cache), [])

    def test_values_read_by_the_worker_are_used(self):
        """The window reads the files off the GUI thread and hands the values
        in; the scan cache is written on the thread that owns it."""
        custom_field.set_source("TIT1", "")
        self.lib.read_custom([self.e], self.cache, {str(self.p): "from the worker"})
        self.assertEqual(self.e.custom, "from the worker")
        self.assertEqual(self.scan.store[str(self.p)]["custom"], "from the worker")

    def test_a_file_not_handed_in_reads_the_new_frame_on_its_next_look(self):
        """The scan cache holds the whole table in memory; the old mapping's
        value must not survive there for a file no list shows right now."""
        custom_field.set_source("TXXX", "ultramixer_last_played")
        scan = scan_caches.ScanCache(_Cache({str(self.p): "fpP"}))
        self.lib._scan_cache = scan
        self.assertEqual(self.lib._make_entry(self.p, scan).custom, "-1")
        custom_field.set_source("TIT1", "")
        self.lib.read_custom([], scan._cache)
        self.assertEqual(self.lib._make_entry(self.p, scan).custom, "Gala")


class ClassesTest(_ScratchDb):
    """DJ Maksy's class codes ('BAS', 'vocal AS') can sit in the mapped frame
    instead of the comment. They count when the comment names no classes."""

    def setUp(self):
        super().setUp()
        custom_field.set_source("TXXX", "grp")
        self.lib = MusicLibrary()
        self.cache = _Cache({})

    def entry(self, **kw):
        e = MusicEntry(path=self.dir / "x.mp3", title="x", **kw)
        self.lib.entries = [e]
        self.lib.apply_tag_edits(self.cache)
        return e

    def test_the_mapped_frame_gives_the_classes(self):
        self.assertEqual(self.entry(custom="vocal BAS").classes_ok, ["B", "A", "S"])

    def test_the_comment_wins(self):
        self.assertEqual(self.entry(classes_ok=["D"], custom="AS").classes_ok, ["D"])

    def test_a_custom_text_without_classes_gives_none(self):
        self.assertIsNone(self.entry(custom="Hochzeit").classes_ok)

    def test_the_scan_cache_keeps_the_comments_own(self):
        """So a new mapping can start over from what the comment says."""
        p = self.mp3(TIT2(encoding=1, text="x"), TXXX(encoding=1, desc="grp", text="DCB"))
        scan = _StubScan()
        e = self.lib._make_entry(p, scan)
        self.lib.entries = [e]
        self.lib.apply_tag_edits(self.cache)
        self.assertEqual(e.classes_ok, ["D", "C", "B"])
        self.assertIsNone(scan.store[str(p)]["classes_ok"])

    def test_a_typed_custom_value_sets_no_classes(self):
        tag_edits.apply(e := self.entry(), {"custom": "AS"})
        self.lib.apply_tag_edits(self.cache)
        self.assertIsNone(e.classes_ok)

    def remapped(self, cached_classes, custom="AS", new="Gala"):
        p = self.mp3(TIT2(encoding=1, text="x"), TIT1(encoding=1, text=new))
        e = MusicEntry(path=p, title="x", classes_ok=cached_classes, custom=custom)
        self.lib.entries = [e]
        self.lib.apply_tag_edits(self.cache)
        self.lib._scan_cache = _StubScan({str(p): {"title": "x", "custom": custom,
                                                    "classes_ok": cached_classes}})
        self.lib._scan_cache._cache = self.cache
        custom_field.set_source("TIT1", "")
        return e, self.lib.read_custom([e], self.cache)

    def test_a_new_mapping_drops_the_old_frames_classes(self):
        e, changed = self.remapped(None)
        self.assertIsNone(e.classes_ok)
        self.assertEqual(changed, [e.path])

    def test_a_new_mapping_takes_the_new_frames_classes(self):
        e, _ = self.remapped(None, new="vocal BAS")
        self.assertEqual(e.classes_ok, ["B", "A", "S"])

    def test_a_new_mapping_keeps_the_comments_classes(self):
        e, _ = self.remapped(["A", "S"])
        self.assertEqual(e.classes_ok, ["A", "S"])

    def test_without_a_cached_row_the_old_frames_classes_still_go(self):
        p = self.mp3(TIT2(encoding=1, text="x"), TIT1(encoding=1, text="Gala"))
        e = self.entry(custom="AS")
        e.path = p
        self.lib._scan_cache = _StubScan()
        self.lib._scan_cache._cache = self.cache
        custom_field.set_source("TIT1", "")
        self.lib.read_custom([e], self.cache)
        self.assertIsNone(e.classes_ok)

    def test_a_new_mapping_leaves_an_app_class_edit_on_top(self):
        p = self.mp3(TIT2(encoding=1, text="x"), TIT1(encoding=1, text="BAS"))
        e = MusicEntry(path=p, title="x", custom="DC")
        self.lib.entries = [e]
        self.lib.apply_tag_edits(self.cache)
        tag_edits.apply(e, {"classes_ok": ["S"]})
        self.lib._scan_cache = _StubScan({str(p): {"title": "x", "custom": "DC",
                                                    "classes_ok": None}})
        self.lib._scan_cache._cache = self.cache
        custom_field.set_source("TIT1", "")
        self.lib.read_custom([e], self.cache)
        self.assertEqual(e.classes_ok, ["S"])
        self.assertEqual(e.tag_edits["classes_ok"], ["B", "A", "S"])


class WriteTest(_ScratchDb):

    def test_the_value_goes_into_the_mapped_frame(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("-1"))
        self.assertTrue(id3_frames.write_tags(p, app={"custom": "Gala"}))
        tags = ID3(p)
        self.assertEqual(str(tags["TXXX:ultramixer_last_played"]), "Gala")
        self.assertEqual(str(tags["TIT2"]), "x")

    def test_a_missing_frame_is_added(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(TIT2(encoding=1, text="x"))
        id3_frames.write_tags(p, app={"custom": "Gala"})
        self.assertEqual(str(ID3(p)["TXXX:ultramixer_last_played"]), "Gala")

    def test_the_frame_is_found_in_any_case(self):
        custom_field.set_source("TXXX", "ULTRAMIXER_LAST_PLAYED")
        p = self.mp3(_ultramixer("-1"))
        id3_frames.write_tags(p, app={"custom": "5"})
        self.assertEqual(list(ID3(p).keys()), ["TXXX:ultramixer_last_played"])

    def test_a_blank_value_removes_the_frame(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(TIT2(encoding=1, text="x"), _ultramixer("-1"))
        id3_frames.write_tags(p, app={"custom": ""})
        self.assertNotIn("TXXX:ultramixer_last_played", ID3(p))

    def test_a_standard_frame(self):
        custom_field.set_source("TIT1", "")
        p = self.mp3(TIT2(encoding=1, text="x"))
        id3_frames.write_tags(p, app={"custom": "Gala"})
        self.assertEqual(str(ID3(p)["TIT1"]), "Gala")

    def test_without_a_mapping_nothing_is_written(self):
        p = self.mp3(TIT2(encoding=1, text="x"))
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            id3_frames.write_tags(p, app={"custom": "Gala"})
        self.assertEqual(p.read_bytes(), before)

    def test_the_frame_changed_in_the_table_too_is_refused(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(_ultramixer("-1"))
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            id3_frames.write_tags(p, raw={"sets": {"TXXX:ultramixer_last_played": "9"}},
                                  app={"custom": "Gala"})
        with self.assertRaises(ValueError):
            id3_frames.write_tags(self.mp3(name="u.mp3"),
                                  raw={"adds": [("TXXX", "Ultramixer_last_played", "9")]},
                                  app={"custom": "Gala"})
        self.assertEqual(p.read_bytes(), before)

    def test_the_comment_is_left_alone(self):
        """Custom is not one of the fields merged into the plain comment."""
        custom_field.set_source("TXXX", "ultramixer_last_played")
        p = self.mp3(COMM(encoding=1, lang="eng", desc="", text="C;B;vocal_f"))
        id3_frames.write_tags(p, app={"custom": "Gala"})
        self.assertEqual(str(ID3(p)["COMM::eng"]), "C;B;vocal_f")


if __name__ == "__main__":
    unittest.main(verbosity=2)
