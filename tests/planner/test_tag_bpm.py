#!/usr/bin/env python3
"""The tempo also comes from the ID3 BPM tag (TBPM), not just the file name.

Run:  py -m unittest tests.planner.test_tag_bpm -v

DJ tools write TBPM in beats per minute (a Slow Waltz at 87), the planner
works in bars per minute (T29). The tag is converted by the dance's meter and
only taken when the result lands near the dance's TSO window — a half- or
double-time reading is folded back, nonsense is ignored. Precedence:
file name → TBPM → title tag text.
"""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mutagen.id3 import ID3, TBPM, TCON, TIT2

from planner.music.db import _meta_to_row, _migrate_meta_tag_bpm, _row_to_meta
from planner.music.library import MusicLibrary
from planner.models import MusicEntry
from planner.music.parsing import _detect_bpm_tagged, _takt_from_tag_bpm, bpm_source

# One MPEG-1 Layer III frame header (128 kbit/s, 44.1 kHz): 417 bytes a frame.
_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413


class TaktFromTagBpmTest(unittest.TestCase):

    def test_beats_per_minute_are_divided_by_the_meter(self):
        self.assertEqual(_takt_from_tag_bpm(87, "LW"), 29)     # 3/4
        self.assertEqual(_takt_from_tag_bpm(177, "WW"), 59)    # 3/4
        self.assertEqual(_takt_from_tag_bpm(172, "JI"), 43)    # 4/4
        self.assertEqual(_takt_from_tag_bpm(204, "QS"), 51)    # 4/4
        self.assertEqual(_takt_from_tag_bpm(100, "SA"), 50)    # 2/4
        self.assertEqual(_takt_from_tag_bpm(176.6, "WW"), 59)  # fractional tag

    def test_a_tag_already_in_bars_per_minute_is_kept(self):
        self.assertEqual(_takt_from_tag_bpm(29, "LW"), 29)
        self.assertEqual(_takt_from_tag_bpm(25, "RB"), 25)

    def test_half_and_double_time_readings_are_folded_back(self):
        self.assertEqual(_takt_from_tag_bpm(86, "JI"), 43)     # half time
        self.assertEqual(_takt_from_tag_bpm(128, "TG"), 32)    # double time

    def test_a_reading_far_from_the_window_is_ignored(self):
        # 120 for a Viennese Waltz: 120, 40, 20 and 80 are all far off T58-60.
        self.assertIsNone(_takt_from_tag_bpm(120, "WW"))

    def test_an_analyser_misread_is_ignored(self):
        # Real library tags on Slow Waltzes labelled T29 in the name: 158 → 26,
        # 139.65 → 23 — too far from T28-30 to trust.
        self.assertIsNone(_takt_from_tag_bpm(158, "LW"))
        self.assertIsNone(_takt_from_tag_bpm(139.65, "LW"))

    def test_no_dance_no_tag_no_tempo(self):
        self.assertIsNone(_takt_from_tag_bpm(87, None))
        self.assertIsNone(_takt_from_tag_bpm(87, "SL"))        # social dance
        self.assertIsNone(_takt_from_tag_bpm(None, "LW"))
        self.assertIsNone(_takt_from_tag_bpm(0, "LW"))


class PrecedenceTest(unittest.TestCase):

    def test_the_file_name_wins(self):
        self.assertEqual(
            _detect_bpm_tagged("Moon River (LW 29)", None, tag_bpm=84, dance="LW"), 29)

    def test_the_bpm_tag_wins_over_the_title_tag_text(self):
        self.assertEqual(
            _detect_bpm_tagged("Moon River", "Moon River (LW 28)",
                               tag_bpm=87, dance="LW"), 29)

    def test_the_title_tag_text_is_the_last_resort(self):
        self.assertEqual(
            _detect_bpm_tagged("Moon River", "Moon River (LW 28)",
                               tag_bpm=120, dance="LW"), 28)
        self.assertEqual(_detect_bpm_tagged("Moon River", "Moon River (LW 28)"), 28)


def _entry(stem, bpm, tag_title=None, tag_bpm=None):
    return MusicEntry(path=Path(rf"C:\music\{stem}.mp3"), title=stem, dance="LW",
                      bpm=bpm, tag_title=tag_title, tag_bpm=tag_bpm)


class SourceTest(unittest.TestCase):
    """The BPM cell's tooltip names where the tempo came from."""

    def test_each_source_is_named(self):
        self.assertEqual(bpm_source(_entry("Moon River (LW 29)", 29, tag_bpm=87)), "name")
        self.assertEqual(bpm_source(_entry("Moon River", 29, tag_bpm=87)), "tag")
        self.assertEqual(bpm_source(_entry("Moon River", 28, "Moon River (LW 28)")),
                         "title")

    def test_no_tempo_no_source(self):
        self.assertEqual(bpm_source(_entry("Moon River", None, tag_bpm=87)), "")

    def test_the_tooltip_text(self):
        from gui.common import bpm_tooltip
        self.assertEqual(bpm_tooltip(_entry("Moon River (LW 29)", 29)),
                         "Tempo from the file name")
        self.assertEqual(bpm_tooltip(_entry("Moon River", 29, tag_bpm=87.0)),
                         "Tempo from the BPM tag (87 bpm)")
        self.assertEqual(bpm_tooltip(_entry("Moon River", 28, "Moon River (LW 28)")),
                         "Tempo from the title tag")
        self.assertEqual(bpm_tooltip(_entry("Moon River", None)), "")


class _ScanCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.put_data = None

    def get(self, path):
        return self.cached

    def put(self, path, data):
        self.put_data = data


class ScanTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tagbpm_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.mp3 = self.dir / "Moon River.mp3"
        self.mp3.write_bytes(_FRAME * 100)
        tags = ID3()
        tags.add(TIT2(encoding=3, text="Moon River"))
        tags.add(TCON(encoding=3, text="LW"))
        tags.add(TBPM(encoding=3, text="87"))
        tags.save(self.mp3)

    def test_a_new_file_takes_its_tempo_from_the_tag(self):
        cache = _ScanCache()
        e = MusicLibrary._make_entry(SimpleNamespace(), self.mp3, cache)
        self.assertEqual((e.bpm, e.tag_bpm), (29, 87.0))
        self.assertEqual(cache.put_data["tag_bpm"], 87.0)

    def test_the_cache_hit_self_heal_keeps_the_tag_tempo(self):
        cached = {"title": "Moon River", "dance": "LW", "bpm": 29,
                  "tag_title": "Moon River", "tag_album": "", "duration": 3,
                  "comment_tags": [], "tag_bpm": 87.0}
        e = MusicLibrary._make_entry(SimpleNamespace(), self.mp3,
                                     _ScanCache(cached))
        self.assertEqual(e.bpm, 29)


class StorageTest(unittest.TestCase):

    def test_the_tag_bpm_survives_a_row_round_trip(self):
        meta = _row_to_meta(_meta_to_row({"title": "x", "tag_bpm": 87.0}))
        self.assertEqual(meta["tag_bpm"], 87.0)
        self.assertIsNone(_row_to_meta(_meta_to_row({"title": "x"}))["tag_bpm"])

    def test_the_column_is_appended_to_old_tables(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute("CREATE TABLE scan_meta (ckey TEXT, custom TEXT)")
        conn.execute("CREATE TABLE global_meta (file_id INTEGER, custom TEXT)")
        _migrate_meta_tag_bpm(conn)
        for table in ("scan_meta", "global_meta"):
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            self.assertEqual(cols[-1], "tag_bpm")


if __name__ == "__main__":
    unittest.main()
