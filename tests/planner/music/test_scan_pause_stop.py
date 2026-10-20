"""The library scan can be paused, and stopped with what it has read so far.

Run:  py -m unittest tests.planner.music.test_scan_pause_stop -v

Marcel: "for the background library scan ... it would be nice to have a button
to pause or abort it". The scan runs with the window open, next to the music.
Paused, it must not sit on the database's write lock: the loudness worker and
the session's own writes wait for that lock 10 s at most. Stopped, it keeps
the titles read so far as the library, so what waits for the library switches
on; the next start scans the rest.
"""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
import planner.music.library as library
from planner.music.library import MusicLibrary, ScanCancelled
from tests.db_support import use_scratch_db

_FILES = 12


class ScanPauseStopTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_pause_stop_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.db_path = use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music" / "standardcd"
        self.root.mkdir(parents=True)
        for i in range(_FILES):
            (self.root / f"Waltz {i:02d} LW 29.mp3").write_bytes(bytes([i]) * 64)
        patcher = mock.patch.object(library, "_PAUSE_POLL_SECS", 0.001, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, **kw):
        lib = MusicLibrary()
        lib.scan(pdb.AudioCache(), music_dir=self.root.parent,
                 learn=False, interactive=False, **kw)
        return lib

    def another_writer_gets_the_lock(self) -> bool:
        other = sqlite3.connect(str(self.db_path), timeout=0)
        try:
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
            return True
        except sqlite3.OperationalError:
            return False
        finally:
            other.close()

    def test_a_stopped_scan_keeps_what_it_read(self):
        asked = []

        def stop():
            asked.append(1)
            return len(asked) > 5      # before the 6th file

        lib = self.scan(should_stop=stop)
        self.assertEqual(len(lib.entries), 5)
        self.assertFalse(pdb._db().in_transaction)

    def test_a_paused_scan_lets_go_of_the_write_lock(self):
        polls = []
        lock_free = []

        def pause():
            polls.append(1)
            if len(polls) < 4:
                return False
            if len(polls) == 4:        # before the 4th file: pause
                return True
            if len(polls) < 8:         # held for a few polls, then resumed
                lock_free.append(self.another_writer_gets_the_lock())
                return True
            return False

        lib = self.scan(should_pause=pause)
        self.assertEqual(len(lib.entries), _FILES, "it went on after the pause")
        self.assertTrue(lock_free)
        self.assertTrue(all(lock_free), "the paused scan held the write lock")

    def test_a_pause_still_ends_when_the_window_closes(self):
        with self.assertRaises(ScanCancelled):
            self.scan(should_pause=lambda: True, should_cancel=lambda: True)
        self.assertFalse(pdb._db().in_transaction)

    def test_a_stop_while_paused_ends_the_pause(self):
        stop = []
        lib = self.scan(should_pause=lambda: stop.append(1) or len(stop) >= 3,
                        should_stop=lambda: len(stop) >= 5)
        self.assertLess(len(lib.entries), _FILES)


if __name__ == "__main__":
    unittest.main()
