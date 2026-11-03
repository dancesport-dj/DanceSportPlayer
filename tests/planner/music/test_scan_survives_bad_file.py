"""🛡 One file that breaks the tag reader must not end the library scan.

Run:  py -m unittest tests.planner.music.test_scan_survives_bad_file -v

A header reporting a nan length, a parser bug on an odd tag: whatever the
cause, the scan used to leave through the exception, so the caches were not
saved, the playlists were not learned and every retry died on the same file.
"""
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dancesport_planner import AudioCache, MusicLibrary
from planner.music import library as library_mod
from planner.music import parsing

_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413


class BadFileTest(unittest.TestCase):

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="dp_badfile_"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        for name in ("a.mp3", "b.mp3", "c.mp3"):
            (self.folder / name).write_bytes(_FRAME * 400)

    def _scan(self) -> MusicLibrary:
        lib = MusicLibrary()
        lib.scan(AudioCache(), music_dir=self.folder, learn=False, analyze=False,
                 interactive=False)
        return lib

    def test_a_file_whose_entry_cannot_be_built_is_skipped(self):
        real = MusicLibrary._make_entry

        def make(self_, path, *args, **kw):
            if path.name == "b.mp3":
                raise ValueError("odd tag")
            return real(self_, path, *args, **kw)

        with mock.patch.object(MusicLibrary, "_make_entry", make):
            lib = self._scan()
        self.assertEqual(sorted(e.path.name for e in lib.entries), ["a.mp3", "c.mp3"])

    def test_a_failing_read_ahead_falls_back_to_the_scan_thread(self):
        # The pool worker raising anything but OSError used to propagate.
        def boom(*a, **k):
            raise ValueError("odd header")

        with mock.patch.object(library_mod, "read_tags_once", boom):
            lib = self._scan()
        # Every read failed, so the entries come from the fallback read, which
        # also fails on the same patch: skipped, not fatal.
        self.assertIsInstance(lib.entries, list)

    def test_a_nan_length_reads_as_no_length(self):
        fake = mock.Mock()
        fake.info.length = math.nan
        fake.tags = None
        with mock.patch.object(parsing, "MutagenFile", return_value=fake):
            _, secs = parsing.read_tags_once(self.folder / "a.mp3")
        self.assertEqual(secs, 0)


if __name__ == "__main__":
    unittest.main()
