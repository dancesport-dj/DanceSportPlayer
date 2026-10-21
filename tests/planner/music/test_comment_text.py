"""The comment as the file has it, for a Comment column.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.music.test_comment_text -v

The comment was only ever kept in pieces: its classes, the instrumental flag
and the free markers (lower-cased). A Mac tester wanted it in a column, the way
UltraMixer shows it ('vocal AS'), so the text itself is cached as `tag_comment`:
'' = read, the file has none; None = a row cached before the column existed,
which reads the comment once on its next look.
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_comment_text_"))

from mutagen.id3 import COMM, ID3, TIT2

import planner.music.db as pdb
from planner.music.library import MusicLibrary
from planner.music.scan_caches import _ENTRY_META_KEYS
from tests.db_support import use_scratch_db

_AUDIO = b"\xff\xfb\x90\x00" + b"\x00" * 4000


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


class CommentTextTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_comment_text_db_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.lib = MusicLibrary()

    def mp3(self, comment=None) -> Path:
        p = self.dir / "SW29_Lady Hear Me Tonight_DJ Maksy.mp3"
        p.write_bytes(_AUDIO)
        tags = ID3()
        tags.add(TIT2(encoding=1, text="Lady Hear Me Tonight"))
        if comment is not None:
            tags.add(COMM(encoding=1, lang="eng", desc="", text=comment))
        tags.update_to_v23()
        tags.save(p, v2_version=3, v23_sep=None)
        return p

    def test_a_scan_keeps_the_comment_as_written(self):
        p = self.mp3("vocal AS")
        scan = _StubScan()
        e = self.lib._make_entry(p, scan)
        self.assertEqual(e.tag_comment, "vocal AS")
        self.assertEqual(scan.store[str(p)]["tag_comment"], "vocal AS")
        self.assertEqual(e.classes_ok, ["A", "S"])   # the pieces stay as they were

    def test_no_comment_is_an_empty_text(self):
        e = self.lib._make_entry(self.mp3(), _StubScan())
        self.assertEqual(e.tag_comment, "")

    def test_a_row_cached_before_the_column_reads_it_once(self):
        p = self.mp3("vocal AS")
        scan = _StubScan({str(p): {"title": "x", "duration": 1, "comment_tags": [],
                                   "tag_album": "", "tag_comment": None}})
        self.assertEqual(self.lib._make_entry(p, scan).tag_comment, "vocal AS")
        self.assertEqual(scan.store[str(p)]["tag_comment"], "vocal AS")

    def test_a_cached_empty_text_is_not_read_again(self):
        p = self.mp3("vocal AS")
        scan = _StubScan({str(p): {"title": "x", "duration": 1, "comment_tags": [],
                                   "tag_album": "", "tag_comment": ""}})
        self.assertEqual(self.lib._make_entry(p, scan).tag_comment, "")

    def test_the_database_row_keeps_it(self):
        row = pdb._meta_to_row({"title": "x", "tag_comment": "vocal AS"})
        self.assertEqual(pdb._row_to_meta(row)["tag_comment"], "vocal AS")
        self.assertIsNone(pdb._row_to_meta(pdb._meta_to_row({"title": "x"}))["tag_comment"])

    def test_the_global_cache_keeps_it(self):
        self.assertIn("tag_comment", _ENTRY_META_KEYS)

    def test_an_older_database_gets_the_column(self):
        conn = sqlite3.connect(":memory:")
        cols = [c for c in pdb._META_COLS if c != "tag_comment"]
        conn.execute(f"CREATE TABLE scan_meta (ckey TEXT PRIMARY KEY, {', '.join(cols)})")
        conn.execute(f"CREATE TABLE global_meta (file_id INTEGER, {', '.join(cols)})")
        pdb._migrate_meta_tag_comment(conn)
        for table in ("scan_meta", "global_meta"):
            have = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            self.assertEqual(have[-1], "tag_comment", table)
        self.assertEqual(pdb._META_COLS[-1], "tag_comment")


if __name__ == "__main__":
    unittest.main()
