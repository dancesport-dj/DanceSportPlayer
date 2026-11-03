"""A scan over slow files (iCloud-evicted, network volume) stays cancellable and says where it is.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.music.test_scan_slow_files -v

A tester's scan of 34132 files sat for minutes with no progress and a slow
cancel: cancel and progress were only looked at every 25 files, so 25 slow
opens in a row were 25 waits. Cancel is now asked before every file, progress
is also reported by the clock.
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

_FILES = 12


class ScanSlowFilesTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_slow_files_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music" / "standardcd"
        self.root.mkdir(parents=True)
        for i in range(_FILES):
            (self.root / f"Waltz {i:02d} LW 29.mp3").write_bytes(bytes([i]) * 64)

    def scan(self, **kw):
        lib = MusicLibrary()
        lib.scan(pdb.AudioCache(), music_dir=self.root.parent,
                 learn=False, interactive=False, **kw)
        return lib

    def test_cancel_is_asked_before_every_file(self):
        asked = []

        def cancel():
            asked.append(1)
            return len(asked) >= 3

        with self.assertRaises(ScanCancelled):
            self.scan(should_cancel=cancel)
        self.assertEqual(len(asked), 3)

    def test_progress_is_also_reported_by_the_clock(self):
        reports = []
        with mock.patch.object(library, "_PROGRESS_SECS", 0.0, create=True):
            self.scan(progress_cb=lambda *a: reports.append(a[0]) if a[0] else None)
        self.assertEqual(reports, list(range(1, _FILES + 1)))

    def test_a_hanging_file_is_set_aside_and_read_at_the_end(self):
        # One file whose read waits (an evicted iCloud file) must not hold up the
        # rest: the others are scanned, the slow one comes last.
        release = threading.Event()
        slow = "Waltz 03 LW 29.mp3"
        real = library._read_new_file

        def read(path, *args):
            if path.name == slow:
                release.wait(10)
            return real(path, *args)

        timer = threading.Timer(1.0, release.set)   # frees it only after the others
        self.addCleanup(timer.cancel)
        self.addCleanup(release.set)
        timer.start()
        with mock.patch.object(library, "_STALL_SECS", 0.2),                 mock.patch.object(library, "_read_new_file", read):
            lib = self.scan()
        names = [e.path.name for e in lib.entries]
        self.assertEqual(len(names), _FILES)
        self.assertEqual(names[-1], slow)

    def test_the_late_read_can_still_be_cancelled(self):
        release = threading.Event()
        self.addCleanup(release.set)
        real = library._read_new_file

        def read(path, *args):
            if path.name == "Waltz 03 LW 29.mp3":
                release.wait(10)
            return real(path, *args)

        cancel = {"on": False}

        def should_cancel():
            return cancel["on"]

        threading.Timer(0.6, lambda: cancel.update(on=True)).start()
        with mock.patch.object(library, "_STALL_SECS", 0.2),                 mock.patch.object(library, "_read_new_file", read),                 self.assertRaises(ScanCancelled):
            self.scan(should_cancel=should_cancel)


if __name__ == "__main__":
    unittest.main()
