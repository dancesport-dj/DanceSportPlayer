"""A tag read that failed on the file system (AV lock, cloud placeholder) is not
cached as "no tags" (review item 93)."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.library as plib
from planner.music import parsing
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class FailedReadTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_failed_read_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.song = self.dir / "Atemlos (DF 30).mp3"
        self.song.write_bytes(b"x" * 400)

    def test_an_os_error_marks_the_read_as_failed(self):
        with mock.patch.object(parsing, "HAS_MUTAGEN", True), \
                mock.patch.object(parsing, "MutagenFile", side_effect=PermissionError("locked")):
            read = parsing.read_tags_once(self.song)
        self.assertIsInstance(read, parsing.FailedRead)
        self.assertEqual(tuple(read), (None, 0))

    def test_a_file_without_tags_is_not_a_failed_read(self):
        with mock.patch.object(parsing, "HAS_MUTAGEN", True), \
                mock.patch.object(parsing, "MutagenFile", return_value=None), \
                mock.patch.object(parsing, "_id3_of", return_value=None):
            read = parsing.read_tags_once(self.song)
        self.assertNotIsInstance(read, parsing.FailedRead)

    def test_a_failed_read_is_not_cached(self):
        lib = MusicLibrary()
        cache = AudioCache()
        scan_cache = lib._get_scan_cache(cache)
        with mock.patch.object(plib, "read_tags_once",
                               return_value=parsing.FailedRead((None, 0))):
            lib._make_entry(self.song, scan_cache)
        self.assertIsNone(scan_cache.get(self.song))

    def test_a_failed_rescan_leaves_the_entry_alone(self):
        lib = MusicLibrary()
        cache = AudioCache()
        entry = plib.MusicEntry(path=self.song, title="Kept", dance="DF")
        with mock.patch.object(plib, "read_tags_once",
                               return_value=parsing.FailedRead((None, 0))):
            changed = lib.rescan_tags(entry, cache)
        self.assertEqual(changed, {})
        self.assertEqual(entry.title, "Kept")


if __name__ == "__main__":
    unittest.main()
