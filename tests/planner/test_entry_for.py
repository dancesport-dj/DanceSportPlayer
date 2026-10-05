"""MusicLibrary.entry_for — the one path→entry lookup.

Four modules used to each walk `lib.entries` twice (exact, then lowercased) and
then fall back to make_external_entry. The behaviour they shared is pinned here,
including the one place they genuinely differed: whether a path whose file is
gone may still be rebuilt from its filename.
"""
import tempfile
import unittest
from pathlib import Path

from planner.library import MusicLibrary
from planner.models import MusicEntry


class _FakeCache:
    """Stands in for AudioCache. Never used: every test that reaches the rebuild
    stubs make_external_entry, which is the seam entry_for delegates across."""


class EntryForTest(unittest.TestCase):
    def setUp(self):
        self.lib = MusicLibrary()
        self.lib.entries = [
            MusicEntry(path=Path(r"C:\music\Standard\Slowfox SF 29.mp3"),
                       title="Slowfox", dance="SF", bpm=29),
            MusicEntry(path=Path(r"C:\music\Latein\Rumba RB 25.mp3"),
                       title="Rumba", dance="RB", bpm=25),
        ]

    def test_exact_path_hits(self):
        e = self.lib.entry_for(r"C:\music\Latein\Rumba RB 25.mp3")
        self.assertIsNotNone(e)
        self.assertEqual(e.dance, "RB")

    def test_a_Path_and_a_str_are_the_same_lookup(self):
        p = r"C:\music\Latein\Rumba RB 25.mp3"
        self.assertIs(self.lib.entry_for(p), self.lib.entry_for(Path(p)))

    def test_case_folded_fallback(self):
        """Windows paths arrive in whatever case the drag source spelled them."""
        e = self.lib.entry_for(r"c:\MUSIC\latein\rumba rb 25.MP3")
        self.assertIsNotNone(e)
        self.assertEqual(e.dance, "RB")

    def test_exact_beats_case_folded(self):
        """Two entries differing only in case: the exact spelling wins, which is
        what walking the whole list for an exact match first used to guarantee."""
        exact = MusicEntry(path=Path(r"C:\music\dup\Track WW 29.mp3"),
                           title="exact", dance="WW", bpm=29)
        other = MusicEntry(path=Path(r"C:\music\dup\TRACK WW 29.MP3"),
                           title="other", dance="WW", bpm=29)
        # The case-folded one is listed FIRST, so a single lowercased pass would
        # return it.
        self.lib.entries = [other, exact]
        self.assertEqual(self.lib.entry_for(r"C:\music\dup\Track WW 29.mp3").title,
                         "exact")

    def test_unknown_path_without_a_cache_is_none(self):
        self.assertIsNone(self.lib.entry_for(r"C:\nowhere\ghost.mp3"))

    def test_the_index_follows_a_growing_library(self):
        """Entries are appended after a scan; a stale index would miss them."""
        self.assertIsNone(self.lib.entry_for(r"C:\music\new\Jive JI 43.mp3"))
        self.lib.entries.append(MusicEntry(path=Path(r"C:\music\new\Jive JI 43.mp3"),
                                           title="Jive", dance="JI", bpm=43))
        self.assertIsNotNone(self.lib.entry_for(r"C:\music\new\Jive JI 43.mp3"))

    def test_lookup_does_not_scan_the_list(self):
        """The point of the index: resolution stops being O(n) per path."""
        class _Loud(list):
            def __iter__(self):
                raise AssertionError("entry_for walked the whole entry list")

        self.lib.entry_for(r"C:\music\Latein\Rumba RB 25.mp3")   # builds the index
        n = len(self.lib.entries)
        self.lib.entries = _Loud(self.lib.entries)
        self.assertEqual(len(self.lib.entries), n)
        self.assertIsNotNone(self.lib.entry_for(r"C:\music\Latein\Rumba RB 25.mp3"))


class RequireFileTest(unittest.TestCase):
    """make_external_entry reads title/dance/bpm off the FILENAME and succeeds on
    a path that no longer exists. Restoring a session must not resurrect those;
    a drop or an .m3u import relies on exactly that behaviour."""

    def setUp(self):
        self.lib = MusicLibrary()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.built: list[Path] = []
        self.lib.make_external_entry = self._build

    def _build(self, path, cache):
        """Stands in for the real rebuild, which reads title/dance/bpm off the
        filename and does NOT care whether the file is there."""
        self.built.append(path)
        return MusicEntry(path=path, title=path.stem, dance="WW", bpm=29)

    def test_a_missing_file_still_builds_an_entry_by_default(self):
        e = self.lib.entry_for(Path(self.tmp.name) / "Gone WW 29.mp3", _FakeCache())
        self.assertIsNotNone(e, "an .m3u line for a moved file lost its slot")
        self.assertEqual(e.dance, "WW")

    def test_require_file_drops_it(self):
        e = self.lib.entry_for(Path(self.tmp.name) / "Gone WW 29.mp3", _FakeCache(),
                               require_file=True)
        self.assertIsNone(e, "a deleted track came back as a phantom row")
        self.assertEqual(self.built, [], "the rebuild ran for a file that is gone")

    def test_require_file_still_finds_a_file_that_is_there(self):
        p = Path(self.tmp.name) / "Here WW 29.mp3"
        p.write_bytes(b"")
        self.assertIsNotNone(self.lib.entry_for(p, _FakeCache(), require_file=True))

    def test_a_failing_rebuild_is_none_not_a_crash(self):
        def _boom(path, cache):
            raise OSError("not audio")
        self.lib.make_external_entry = _boom
        self.assertIsNone(self.lib.entry_for(Path(self.tmp.name) / "x.mp3",
                                             _FakeCache()))

    def test_require_file_never_blocks_a_library_hit(self):
        """The gate is about REBUILDING, not about looking up."""
        gone = Path(self.tmp.name) / "Indexed WW 29.mp3"
        self.lib.entries = [MusicEntry(path=gone, title="Indexed", dance="WW", bpm=29)]
        self.assertIsNotNone(self.lib.entry_for(gone, _FakeCache(), require_file=True))
        self.assertEqual(self.built, [], "a known path was rebuilt instead of found")


if __name__ == "__main__":
    unittest.main()
