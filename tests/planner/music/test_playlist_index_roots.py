"""PlaylistIndexCache forgets the index of a playlist tree that was deleted or
renamed, but keeps the index of one on a drive that is merely unplugged."""
import os
import string
import tempfile
import unittest
from pathlib import Path

from planner.music.db import _db
from planner.music.scan_caches import PlaylistIndexCache
from tests.db_support import use_scratch_db


def _absent_volume_root() -> str:
    """A playlist folder on a drive / mount that is not there right now."""
    if os.name == "nt":
        for letter in reversed(string.ascii_uppercase):
            if not Path(f"{letter}:\\").exists():
                return f"{letter}:\\Playlists"
        raise unittest.SkipTest("every drive letter is in use")
    return "/Volumes/DPTestStick/Playlists"


def _indexed_roots() -> set[str]:
    return {r for (r,) in _db().execute(
        "SELECT DISTINCT root FROM playlist_index").fetchall()}


class VanishedRootsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        use_scratch_db(self, Path(self.tmp.name) / "scratch.db")
        self.live = Path(self.tmp.name) / "live"
        self.live.mkdir()
        self.deleted = str(Path(self.tmp.name) / "deleted")   # drive is present
        self.unplugged = _absent_volume_root()
        for root in (self.deleted, self.unplugged):
            _db().execute(
                "INSERT INTO playlist_index (root, pl_id, sig, mkeys) "
                "VALUES (?, 'a', 's', 'k')", (root,))

    def test_a_deleted_tree_is_forgotten(self):
        PlaylistIndexCache(self.live, "digest")
        self.assertNotIn(self.deleted, _indexed_roots())

    def test_an_unplugged_drive_keeps_its_index(self):
        PlaylistIndexCache(self.live, "digest")
        self.assertIn(self.unplugged, _indexed_roots())


if __name__ == "__main__":
    unittest.main()
