"""The library scan logs how far it is and how long it takes.

Run:  py -m unittest tests.planner.music.test_scan_progress_log -v

A tester's first start sat on a long scan, and session.log had nothing
between "📂 Scanning music library …" and the end: not how many files, not
how far, not which file it hung on. The scan now logs the listing, a
progress line every _PROGRESS_LOG_SECS, any file slower than
_SLOW_FILE_SECS, and the time it took.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
import planner.music.library as library
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db

_FILES = 6


class ScanProgressLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_scan_log_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.root = self.dir / "music" / "standardcd"
        self.root.mkdir(parents=True)
        for i in range(_FILES):
            (self.root / f"Waltz {i:02d} LW 29.mp3").write_bytes(bytes([i]) * 64)

    def scan_log(self, **consts) -> list[str]:
        consts = {"_PROGRESS_LOG_SECS": 15.0, "_SLOW_FILE_SECS": 2.0, **consts}
        with mock.patch.multiple(library, create=True, **consts), \
                self.assertLogs("dancesport.library", "INFO") as logs:
            MusicLibrary().scan(pdb.AudioCache(), music_dir=self.root.parent,
                                learn=False, interactive=False)
        return logs.output

    def test_listing_and_total_time_are_logged(self):
        out = "\n".join(self.scan_log())
        self.assertIn("Music library listed", out)
        self.assertIn(f"files: {_FILES}\nnew to read: {_FILES}\n", out)
        self.assertIn("Library scan finished", out)
        self.assertRegex(out, r"Library scan finished\nfiles: 6\ntime: [\d.]+ s\n"
                              r"app ram: \d+ MB\nfree ram: [\d.]+ GB\napp cpu: \d+ %")

    def test_a_progress_line_comes_at_the_interval(self):
        out = self.scan_log(_PROGRESS_LOG_SECS=0)
        progress = [line for line in out if "Scan progress" in line]
        self.assertEqual(len(progress), _FILES)
        self.assertIn(f"files: 3 / {_FILES}", progress[3])
        self.assertIn("current: ", progress[3])
        self.assertRegex(progress[3], r"app ram: \d+ MB\nfree ram: [\d.]+ GB\napp cpu: \d+ %")

    def test_a_slow_file_is_named(self):
        out = self.scan_log(_SLOW_FILE_SECS=0)
        slow = [line for line in out if "Slow file" in line]
        self.assertEqual(len(slow), _FILES)
        self.assertIn("Waltz 05 LW 29.mp3", slow[-1])

    def test_a_quick_scan_logs_no_progress_lines(self):
        out = "\n".join(self.scan_log())
        self.assertNotIn("Scan progress", out)
        self.assertNotIn("Slow file", out)


if __name__ == "__main__":
    unittest.main()
