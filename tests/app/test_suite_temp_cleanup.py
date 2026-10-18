#!/usr/bin/env python3
"""A test run leaves nothing behind in the temp folder.

Run:  py -m unittest tests.app.test_suite_temp_cleanup -v

Test modules make their scratch folders with `tempfile.mkdtemp` and leave them
there, and pytest-xdist workers end without running `atexit` — runs on one
day left 1775 `dp_suite_data_*` folders alone (~500 MB), and thousands more
of the modules' own.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MODULE = "tests.gui.test_build_env_failure"   # writes a data dir and a scratch dir


def _clean_env(temp: Path) -> dict:
    """This run's environment without what the suite set up for itself."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("DANCEPLAYLIST_", "PYTEST_"))}
    # TMPDIR too: tempfile looks at it first, and tests/__init__.py sets it.
    env.update(TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp),
               QT_QPA_PLATFORM="offscreen")
    return env


class SuiteTempCleanupTest(unittest.TestCase):

    def _run_in_fresh_temp(self, *args, env=()):
        temp = Path(tempfile.mkdtemp(prefix="dp_tempcheck_"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        proc = subprocess.run([sys.executable, *args], cwd=_REPO,
                              env={**_clean_env(temp), **dict(env)},
                              capture_output=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-2000:])
        # Norton's scanner leaves a _norton_ folder in every temp dir it sees;
        # pytest-of-<user> is pytest's own, which keeps its last three runs.
        return sorted(p.name for p in temp.iterdir()
                      if p.name != "_norton_" and not p.name.startswith("pytest-of-"))

    def test_a_unittest_run_cleans_up(self):
        self.assertEqual(self._run_in_fresh_temp("-m", "unittest", _MODULE), [])

    def test_a_pytest_xdist_run_cleans_up(self):
        self.assertEqual(self._run_in_fresh_temp(
            "-m", "pytest", "-q", "-n", "2", "-p", "no:cacheprovider",
            _MODULE.replace(".", "/") + ".py"), [])

    def test_a_coverage_run_cleans_up(self):
        # pytest-cov turns the "unclosed database" ResourceWarning on; pytest
        # keeps every recorded warning, the warning keeps its connection, and
        # the connection's cached statements keep the database file open.
        data = Path(tempfile.mkdtemp(prefix="dp_tempcheck_cov_"))
        self.addCleanup(shutil.rmtree, data, ignore_errors=True)
        self.assertEqual(self._run_in_fresh_temp(
            "-m", "pytest", "-q", "-n", "2", "-p", "no:cacheprovider",
            "--cov", "--cov-report=", "tests/app/unclosed_db_case.py",
            env={"COVERAGE_FILE": str(data / ".coverage")}), [])


if __name__ == "__main__":
    unittest.main()
