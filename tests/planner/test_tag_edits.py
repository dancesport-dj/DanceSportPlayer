"""Tag edits made in the app live in the DB and win over the file's tags.

Run:  py -m unittest tests.planner.test_tag_edits -v

Marcel's tag editor: stars, the class tags and free markers can be changed in
the app. By default they are stored in the database (the MP3 is only written
on request), keyed by the content fingerprint like every other per-track row,
and they win over what the file's own tags say.
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tagedits_"))

import planner.db as pdb  # noqa: E402
from planner import tag_edits  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


class _ScratchDb(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tagedits_db_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved


def _entry(**kw) -> MusicEntry:
    return MusicEntry(path=Path("C:/m/x.mp3"), title="x", dance="LW", **kw)


class StoreTest(_ScratchDb):

    def test_an_edit_is_kept_in_the_database(self):
        tag_edits.save("fp1", {"rating": 4, "classes_ok": ["B", "A", "S"]})
        self.assertEqual(tag_edits.load_all(),
                         {"fp1": {"rating": 4, "classes_ok": ["B", "A", "S"]}})
        self.assertEqual(tag_edits.load("fp1"), {"rating": 4, "classes_ok": ["B", "A", "S"]})

    def test_a_later_save_merges_and_none_drops_a_field(self):
        tag_edits.save("fp1", {"rating": 4, "comment_tags": ["classic"]})
        tag_edits.save("fp1", {"rating": None, "is_instrumental": True})
        self.assertEqual(tag_edits.load("fp1"),
                         {"comment_tags": ["classic"], "is_instrumental": True})

    def test_dropping_every_field_deletes_the_row(self):
        tag_edits.save("fp1", {"rating": 2})
        tag_edits.save("fp1", {"rating": None})
        self.assertEqual(tag_edits.load_all(), {})

    def test_the_row_follows_a_retag(self):
        """Its table is one of those `reattach_retagged` re-keys."""
        self.assertIn("tag_edits", pdb._FP_TABLES)


class ApplyTest(unittest.TestCase):

    def test_the_edit_wins_and_the_file_value_is_remembered(self):
        e = _entry(rating=2, classes_ok=["D", "C"])
        tag_edits.apply(e, {"rating": 5, "classes_ok": ["A", "S"]})
        self.assertEqual((e.rating, e.classes_ok), (5, ["A", "S"]))
        self.assertEqual(e.tag_edits, {"rating": 2, "classes_ok": ["D", "C"]})

    def test_no_classes_means_every_class(self):
        e = _entry(classes_ok=["S"])
        tag_edits.apply(e, {"classes_ok": []})
        self.assertIsNone(e.classes_ok)

    def test_zero_stars_means_unrated(self):
        e = _entry(rating=3)
        tag_edits.apply(e, {"rating": 0})
        self.assertIsNone(e.rating)

    def test_applying_again_starts_from_the_file_values(self):
        e = _entry(rating=2, comment_tags=["old"])
        tag_edits.apply(e, {"rating": 5, "comment_tags": ["new"]})
        tag_edits.apply(e, {"comment_tags": ["newer"]})
        self.assertEqual((e.rating, e.comment_tags), (2, ["newer"]))
        tag_edits.apply(e, None)
        self.assertEqual((e.rating, e.comment_tags, e.tag_edits), (2, ["old"], None))


class _Cache:
    """Only what the library asks of the AudioCache here."""

    def __init__(self, fps):
        self.fps = fps

    def recorded_fingerprint(self, path):
        return self.fps.get(str(path))


class LibraryTest(_ScratchDb):

    def setUp(self):
        super().setUp()
        from planner.library import MusicLibrary
        self.lib = MusicLibrary()
        self.e = _entry(rating=2, classes_ok=["D"])
        self.lib.entries = [self.e]
        self.cache = _Cache({str(self.e.path): "fpX"})

    def test_the_library_lays_the_edits_over_its_entries(self):
        tag_edits.save("fpX", {"rating": 5})
        self.lib.apply_tag_edits(self.cache)
        self.assertEqual(self.e.rating, 5)

    def test_a_track_never_fingerprinted_keeps_its_file_values(self):
        tag_edits.save("fpX", {"rating": 5})
        self.lib.apply_tag_edits(_Cache({}))
        self.assertEqual(self.e.rating, 2)

    def test_re_reading_the_tags_keeps_the_edit(self):
        """🔄 Re-read tags takes the file's new values, the edit still wins."""
        from unittest import mock
        tag_edits.save("fpX", {"rating": 5})
        self.lib.apply_tag_edits(self.cache)
        fresh = _entry(rating=3, classes_ok=["C"])
        sc = mock.Mock()
        sc._cache = self.cache
        with mock.patch.object(self.lib, "_get_scan_cache", return_value=sc), \
             mock.patch.object(self.lib, "_make_entry", return_value=fresh):
            self.lib.rescan_tags(self.e, self.cache)
        self.assertEqual((self.e.rating, self.e.classes_ok), (5, ["C"]))
        self.assertEqual(self.e.tag_edits, {"rating": 3})


class _HashingCache(_Cache):
    """…plus `fingerprint`, which hashes the file the editor is pointed at."""

    def fingerprint(self, path):
        return self.fps.get(str(path))


class EditTagsTest(_ScratchDb):
    """MusicLibrary.edit_tags — what the ★ column and the editor dialog call."""

    def setUp(self):
        super().setUp()
        from planner.library import MusicLibrary
        self.lib = MusicLibrary()
        self.e = _entry(rating=2, classes_ok=["D", "C"], comment_tags=["classic"])
        self.lib.entries = [self.e]
        self.cache = _HashingCache({str(self.e.path): "fpX"})

    def test_the_edit_is_stored_and_shown(self):
        self.lib.edit_tags([self.e], self.cache, {"rating": 5})
        self.assertEqual(self.e.rating, 5)
        self.assertEqual(tag_edits.load("fpX"), {"rating": 5})

    def test_going_back_to_the_files_value_drops_the_override(self):
        self.lib.edit_tags([self.e], self.cache, {"rating": 5})
        self.lib.edit_tags([self.e], self.cache, {"rating": 2})
        self.assertEqual(tag_edits.load("fpX"), {})
        self.assertEqual((self.e.rating, self.e.tag_edits), (2, None))

    def test_clearing_the_stars_of_an_unrated_file_stores_nothing(self):
        e = _entry()
        self.lib.entries.append(e)
        cache = _HashingCache({str(e.path): "fpY"})
        self.lib.edit_tags([e], cache, {"rating": 0})
        self.assertEqual(tag_edits.load("fpY"), {})

    def test_clearing_the_stars_of_a_rated_file_is_an_explicit_unrated(self):
        self.lib.edit_tags([self.e], self.cache, {"rating": 0})
        self.assertIsNone(self.e.rating)
        self.assertEqual(tag_edits.load("fpX"), {"rating": 0})

    def test_every_copy_of_the_same_content_follows(self):
        """A deck row can hold an outside copy (the old library folder) of a
        track the library also has — same content, same fingerprint."""
        copy = MusicEntry(path=Path("C:/old/x.mp3"), title="x", dance="LW", rating=2)
        self.cache.fps[str(copy.path)] = "fpX"
        touched = self.lib.edit_tags([copy], self.cache, {"rating": 4})
        self.assertEqual((copy.rating, self.e.rating), (4, 4))
        self.assertEqual({str(p) for p in touched}, {str(copy.path), str(self.e.path)})

    def test_several_tracks_at_once(self):
        f = MusicEntry(path=Path("C:/m/y.mp3"), title="y", dance="LW")
        self.lib.entries.append(f)
        self.cache.fps[str(f.path)] = "fpY"
        self.lib.edit_tags([self.e, f], self.cache, {"classes_ok": ["A", "S"]})
        self.assertEqual((self.e.classes_ok, f.classes_ok), (["A", "S"], ["A", "S"]))

    def test_reset_brings_back_every_file_value(self):
        self.lib.edit_tags([self.e], self.cache,
                           {"rating": 5, "classes_ok": [], "comment_tags": ["x"]})
        self.lib.reset_tag_edits([self.e], self.cache)
        self.assertEqual((self.e.rating, self.e.classes_ok, self.e.comment_tags),
                         (2, ["D", "C"], ["classic"]))
        self.assertEqual(tag_edits.load("fpX"), {})

    def test_a_file_that_cannot_be_hashed_is_refused(self):
        e = MusicEntry(path=Path("C:/gone.mp3"), title="g", dance="LW")
        with self.assertRaises(ValueError):
            self.lib.edit_tags([e], self.cache, {"rating": 3})


if __name__ == "__main__":
    unittest.main(verbosity=2)
