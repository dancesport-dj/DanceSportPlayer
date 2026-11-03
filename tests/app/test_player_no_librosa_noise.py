"""The player build does not tell the user about librosa, which it never ships.

Run:  .venv/Scripts/python.exe -m unittest tests.app.test_player_no_librosa_noise -v

A tester on the macOS player build saw "librosa not installed - skipping audio
analysis. Install: pip install librosa" in the log, and again when building the
index anew. The player flavor leaves librosa out on purpose, so neither a
warning nor an install hint helps: the step is simply not part of that build.
"""
import logging
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import planner.music.db as pdb
from gui.window.main_allcache import plan_allcache_steps
from tests.db_support import use_scratch_db

_ARGS = dict(has_pd=True, have_ffmpeg=True, have_mert=True, have_chroma=True)


class PlayerBuildAllCacheTest(unittest.TestCase):
    def test_the_player_plans_no_librosa_step_and_names_none_as_missing(self):
        steps, skipped = plan_allcache_steps(have_librosa=False, player=True, **_ARGS)
        self.assertNotIn("librosa", steps)
        self.assertEqual([s for s in skipped if "librosa" in s.lower()], [])

    def test_a_full_build_still_reports_a_missing_librosa(self):
        steps, skipped = plan_allcache_steps(have_librosa=False, **_ARGS)
        self.assertNotIn("librosa", steps)
        self.assertTrue(any("librosa" in s.lower() for s in skipped))


class PlayerBuildLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_no_librosa_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        patcher = mock.patch.object(pdb, "HAS_LIBROSA", False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_player_logs_no_warning_and_no_install_hint(self):
        with mock.patch.object(pdb, "player_build", return_value=True), \
                self.assertLogs(pdb.log, logging.DEBUG) as logs:
            pdb.AudioCache().analyze_missing([], interactive=False)
        self.assertEqual([r for r in logs.records if r.levelno >= logging.WARNING], [])
        self.assertFalse(any("pip install" in r.getMessage() for r in logs.records))

    def test_a_full_build_still_warns(self):
        with mock.patch.object(pdb, "player_build", return_value=False), \
                self.assertLogs(pdb.log, logging.WARNING) as logs:
            pdb.AudioCache().analyze_missing([], interactive=False)
        self.assertTrue(any("pip install librosa" in r.getMessage() for r in logs.records))


if __name__ == "__main__":
    unittest.main()
