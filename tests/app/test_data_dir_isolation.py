"""The suite never writes the real app data.

Run:  py -m unittest tests.app.test_data_dir_isolation -v

A suite run used to touch the real audio_features.db (every first `_db()`
migrates and backs up) and drop a dated copy into the real backups/ folder
(MainWindow.closeEvent refreshes the day's backup). DANCEPLAYLIST_STATE_DIR
only ever covered the JSON stores; DANCEPLAYLIST_DATA_DIR moves the whole
data folder, and tests/__init__.py sets it before anything is imported.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from planner import config, db

_ROOT = Path(__file__).resolve().parents[2]


class SuiteIsolationTest(unittest.TestCase):
    def test_the_suite_runs_on_a_data_folder_of_its_own(self):
        self.assertNotEqual(config._BASE_DIR.resolve(), config.INSTALL_DIR.resolve())
        self.assertNotEqual(config.audio_db_file().resolve(),
                            (config.INSTALL_DIR / "audio_features.db").resolve())

    def test_backups_land_in_that_folder_too(self):
        self.assertTrue(db._backup_dir().resolve().is_relative_to(
            config._BASE_DIR.resolve()))


class DataDirOverrideTest(unittest.TestCase):
    def _base_dir_with(self, value):
        env = dict(os.environ)
        env.pop("DANCEPLAYLIST_DATA_DIR", None)
        if value is not None:
            env["DANCEPLAYLIST_DATA_DIR"] = value
        out = subprocess.run(
            [sys.executable, "-c",
             "from planner import config; print(config._BASE_DIR)"],
            cwd=_ROOT, env=env, capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())

    def test_the_variable_moves_the_data_folder(self):
        target = Path(tempfile.mkdtemp(prefix="dp_datadir_env_")) / "nested"
        self.assertEqual(self._base_dir_with(str(target)), target)
        self.assertTrue(target.is_dir())

    def test_without_it_the_app_folder_stays_the_data_folder(self):
        self.assertEqual(self._base_dir_with(None).resolve(),
                         config.INSTALL_DIR.resolve())


if __name__ == "__main__":
    unittest.main()
