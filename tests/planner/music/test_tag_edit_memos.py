"""An in-app genre edit changes an entry's dance IN PLACE, so the library's
memos grouped by dance (by_dance, title twins) must be rebuilt, not served
until a rescan."""
import tempfile
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class _Cache:
    """The two AudioCache calls edit_tags makes (the temp files are empty)."""

    def __init__(self, fps: dict[str, str]):
        self.fps = fps

    def fingerprint(self, path):
        return self.fps.get(str(path))

    def recorded_fingerprint(self, path):
        return self.fps.get(str(path))


class TagEditMemoTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        use_scratch_db(self, root / "scratch.db")
        path = root / "Song.mp3"
        path.touch()
        self.entry = MusicEntry(path=path, title="Song", dance="CC", bpm=30)
        self.lib = MusicLibrary()
        self.lib.entries = [self.entry]
        self.cache = _Cache({str(path): "fp-song"})

    def test_by_dance_follows_a_genre_edit(self):
        self.assertEqual(self.lib.by_dance("CC"), [self.entry])   # memo built
        self.lib.edit_tags([self.entry], self.cache, {"genre": "Rumba"})
        self.assertEqual(self.entry.dance, "RB")
        self.assertEqual(self.lib.by_dance("CC"), [])
        self.assertEqual(self.lib.by_dance("RB"), [self.entry])

    def test_by_dance_follows_taking_the_edit_back(self):
        self.lib.edit_tags([self.entry], self.cache, {"genre": "Rumba"})
        self.assertEqual(self.lib.by_dance("RB"), [self.entry])   # memo built
        self.lib.reset_tag_edits([self.entry], self.cache)
        self.assertEqual(self.lib.by_dance("RB"), [])
        self.assertEqual(self.lib.by_dance("CC"), [self.entry])


if __name__ == "__main__":
    unittest.main()
