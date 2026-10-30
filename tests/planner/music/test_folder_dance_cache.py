#!/usr/bin/env python3
"""A dance read off the folder follows the file to its next folder.

Run:  py -m unittest tests.planner.music.test_folder_dance_cache -v

The scan cache keys a row by the file's content and name, on the premise that
what it holds is a function of those two. The folder fallback is not: it reads
the parent folders. Stored under that key, a misfiled track moved from
latin/Rumba to latin/Samba stayed a Rumba after the rescan, and two identical
copies in two dance folders both took whichever was scanned first
(BUG_REVIEW B6.2).
"""

import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

from planner.music import db
from planner.music.library import MusicLibrary
from planner.music.parsing import dance_from_folders
from planner.music.scan_caches import ScanCache
from tests.db_support import use_scratch_db


class _StemCache:
    """A scan cache keyed like the real one: content (all the same here) plus
    the file name — the folder is not part of the key."""

    def __init__(self):
        self.rows = {}

    def get(self, path):
        row = self.rows.get(path.stem)
        return dict(row) if row else None

    def put(self, path, data):
        self.rows[path.stem] = dict(data)


def _path(folder: str) -> Path:
    return Path(rf"C:\music\latin\{folder}\Some Title.mp3")


class FolderDanceCacheTest(unittest.TestCase):

    def setUp(self):
        self.cache = _StemCache()
        for target, value in (("get_raw_genre_tag", None),
                              ("get_comment_tag", None),
                              ("get_title_artist_tags", (None, None, "")),
                              ("read_duration", 180)):
            patch = mock.patch(f"planner.music.library.{target}", return_value=value)
            patch.start()
            self.addCleanup(patch.stop)

    def entry(self, folder: str):
        return MusicLibrary()._make_entry(_path(folder), cast(ScanCache, self.cache))

    def test_the_folders_are_dance_folders(self):
        self.assertEqual(dance_from_folders(_path("Rumba")), "RB")
        self.assertEqual(dance_from_folders(_path("Samba")), "SA")

    def test_a_scan_reads_the_dance_off_the_folder(self):
        self.assertEqual(self.entry("Rumba").dance, "RB")

    def test_a_file_moved_to_another_dance_folder_takes_its_dance(self):
        self.entry("Rumba")
        self.assertEqual(self.entry("Samba").dance, "SA")

    def test_the_cached_row_keeps_no_folder_dance(self):
        self.entry("Rumba")
        self.assertIsNone(self.cache.rows["Some Title"]["dance"])

    def test_a_cache_hit_gives_the_same_entry_as_the_scan(self):
        scanned = self.entry("Rumba")
        hit = self.entry("Rumba")
        self.assertEqual((hit.dance, hit.bpm, hit.other_genre),
                         (scanned.dance, scanned.bpm, scanned.other_genre))

    def test_a_file_moved_to_another_social_folder_takes_its_genre(self):
        """The social classifier reads the folders as well (a Forró folder),
        so its label follows the file like the folder's dance does."""
        self.assertEqual(self.social("Forro").other_genre, "Forró")
        self.assertEqual(self.social("Salsa").other_genre, "Salsa")

    def test_the_cached_row_keeps_no_folder_genre(self):
        self.social("Forro")
        self.assertIsNone(self.cache.rows["Some Title"]["other_genre"])

    def test_a_genre_tag_still_wins_over_the_folder(self):
        with mock.patch("planner.music.library.get_raw_genre_tag",
                        return_value="SL"):
            self.social("Forro")
        self.assertEqual(self.social("Forro").other_genre, "Salsa")

    def social(self, folder: str):
        path = Path(rf"C:\music\social\{folder}\Some Title.mp3")
        return MusicLibrary()._make_entry(path, cast(ScanCache, self.cache))

class OldRowsTest(unittest.TestCase):
    """Rows written before this carry the folder's dance or label as if a tag
    had named it. They are read again once, and only they: the rest of the
    library keeps its rows instead of re-reading every file's tags."""

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_folder_dance_"))
        use_scratch_db(self, folder / "scratch.db")
        self.conn = db._db()
        self.conn.execute("DELETE FROM app_meta WHERE key = 'path_meta_dropped'")
        for ckey, dance, other in (
                ("fp1::Some Title", "RB", None),        # a folder's, or a tag's
                ("fp2::Artist - Title RB 25", "RB", None),
                ("fp3::Some Title", None, "Forró"),     # a folder's, or a tag's
                ("fp4::Forro de Rua", None, "Forró"),
                ("fp5::Some Title", None, None)):
            self.put(ckey, dance, other)

    def put(self, ckey, dance, other):
        self.conn.execute("INSERT INTO scan_meta (ckey, dance, other_genre) "
                          "VALUES (?, ?, ?)", (ckey, dance, other))

    def kept(self):
        return sorted(c for (c,) in self.conn.execute("SELECT ckey FROM scan_meta"))

    def test_only_rows_the_folder_may_have_filled_are_dropped(self):
        db._drop_path_derived_meta(self.conn)
        self.assertEqual(self.kept(), ["fp2::Artist - Title RB 25",
                                       "fp4::Forro de Rua", "fp5::Some Title"])

    def test_it_runs_once(self):
        db._drop_path_derived_meta(self.conn)
        self.put("fp6::Another Title", "SA", None)
        db._drop_path_derived_meta(self.conn)
        self.assertIn("fp6::Another Title", self.kept())

    def test_the_detection_version_does_not_clear_the_whole_library(self):
        self.assertEqual(db._DANCE_DETECT_VERSION, 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
