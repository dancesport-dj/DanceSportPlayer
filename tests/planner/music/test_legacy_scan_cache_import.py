"""♻️ The legacy JSON scan caches import only sound entries, and only for files
that are still the ones the cache described (#63, #81)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.music import scan_caches
from planner.music.db import AudioCache
from planner.music.scan_caches import GlobalScanCache, ScanCache
from tests.db_support import use_scratch_db

_GOOD = {"title": "Good", "duration": 1, "comment_tags": [], "tag_album": ""}


class _Legacy(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_legacy_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.song = self.dir / "song.mp3"
        self.song.write_bytes(b"\xff\xfb\x90\x00" * 100)

    def write(self, name, payload):
        file = self.dir / name
        file.write_text(json.dumps(payload), encoding="utf-8")
        return file


class ScanCacheImportTest(_Legacy):

    def load(self, entries):
        file = self.write("scan_cache.json", {"version": ScanCache.VERSION, "entries": entries})
        with mock.patch.object(scan_caches, "SCAN_CACHE_FILE", file):
            return ScanCache(AudioCache())

    def test_a_damaged_entry_costs_a_rescan_not_the_start(self):
        size = self.song.stat().st_size
        cache = self.load({f"{self.song}::{size}": None, f"{self.dir / 'b.mp3'}::1": "x"})
        self.assertEqual(cache._data, {})

    def test_a_file_that_changed_since_is_not_imported(self):
        size = self.song.stat().st_size
        cache = self.load({f"{self.song}::{size + 1}": dict(_GOOD)})
        self.assertEqual(cache._data, {})

    def test_entries_that_are_not_an_object_are_skipped(self):
        self.assertEqual(self.load([1, 2])._data, {})

    def test_an_unchanged_file_is_imported(self):
        size = self.song.stat().st_size
        cache = self.load({f"{self.song}::{size}": dict(_GOOD)})
        self.assertEqual(len(cache._data), 1)


class GlobalImportTest(_Legacy):

    def test_a_damaged_record_costs_a_rescan_not_the_start(self):
        file = self.write("global_scan_cache.json", {
            "version": GlobalScanCache.VERSION,
            "entries": {str(self.song): None, "b": "x",
                        "c": {"mtime": 5, "entry": dict(_GOOD)}}})
        with mock.patch.object(scan_caches, "GLOBAL_SCAN_CACHE_FILE", file):
            cache = GlobalScanCache()
        self.assertEqual(list(cache._data), ["c"])

    def test_entries_that_are_not_an_object_are_skipped(self):
        file = self.write("global_scan_cache.json", {
            "version": GlobalScanCache.VERSION, "entries": [1, 2]})
        with mock.patch.object(scan_caches, "GLOBAL_SCAN_CACHE_FILE", file):
            cache = GlobalScanCache()
        self.assertEqual(cache._data, {})


if __name__ == "__main__":
    unittest.main()
