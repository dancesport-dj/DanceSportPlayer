"""The library scan reads new files on a thread pool, ahead of the walk.

Run:  py -m unittest tests.planner.music.test_scan_read_ahead -v

A file the scan has not seen before costs two reads: the head and tail for
its fingerprints, and the ID3 tag. One after the other on the scan thread,
the disk waited for Python and Python for the disk; a first start over a
large library sat on that for minutes. A pool now reads a window of files
ahead while the scan thread keeps the database writes (connections are per
thread) and the order of the entries.
"""
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
import planner.music.library as library
from planner.music.library import MusicLibrary, ScanCancelled
from tests.db_support import use_scratch_db

_FILES = 29


class ScanReadAheadTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_read_ahead_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music" / "standardcd"
        self.root.mkdir(parents=True)
        self.names = [f"Waltz {i:02d} LW 29" for i in range(_FILES)]
        for i, name in enumerate(self.names):
            (self.root / f"{name}.mp3").write_bytes(bytes([i]) * 64)
        self.reads = []   # (what, file name, read on the scan thread?)
        scan_thread = threading.get_ident()

        def spy(what, real):
            def read(path):
                self.reads.append((what, path.name,
                                   threading.get_ident() == scan_thread))
                return real(path)
            return read

        real_fingerprints = pdb._fingerprints
        for module in (pdb, library):
            if hasattr(module, "_fingerprints"):
                self.patch(module, "_fingerprints",
                           spy("fp", real_fingerprints))
        self.patch(library, "_read_tags_once",
                   spy("tags", library._read_tags_once))

    def patch(self, module, name, value):
        patcher = mock.patch.object(module, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, **kw):
        lib = MusicLibrary()
        lib.scan(pdb.AudioCache(), music_dir=self.root.parent,
                 learn=False, interactive=False, **kw)
        return lib

    def test_new_files_are_read_off_the_scan_thread(self):
        lib = self.scan()
        self.assertEqual([e.path.stem for e in lib.entries], self.names)
        self.assertTrue(all(e.dance == "LW" for e in lib.entries))
        for what in ("fp", "tags"):
            read = sorted(name for w, name, _ in self.reads if w == what)
            self.assertEqual(read, sorted(f"{n}.mp3" for n in self.names), what)
        on_scan_thread = [r for r in self.reads if r[2]]
        self.assertEqual(on_scan_thread, [])

    def test_known_files_are_not_read_again(self):
        self.scan()
        self.reads.clear()
        lib = self.scan()
        self.assertEqual(len(lib.entries), _FILES)
        self.assertEqual(self.reads, [])

    def test_a_cancelled_scan_leaves_no_reader_running(self):
        before = threading.active_count()
        # Polled every 25 files: it stops before the 25th.
        with self.assertRaises(ScanCancelled):
            self.scan(should_cancel=lambda: True)
        self.assertEqual(threading.active_count(), before)

    def test_the_readers_run_below_the_gui_and_the_player(self):
        lowered = []
        with mock.patch.object(library, "lower_thread_priority",
                               side_effect=lambda: lowered.append(threading.get_ident())):
            self.scan()
        self.assertTrue(lowered)
        self.assertNotIn(threading.get_ident(), lowered, "only the pool's threads")


if __name__ == "__main__":
    unittest.main()
