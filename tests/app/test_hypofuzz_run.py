"""tools.dev.hypofuzz_run: what it fuzzes, and that the suite's TEMP lives on."""
import os
import sys
import unittest
from unittest import mock

import conftest
from tools.dev import hypofuzz_run as hf


class CommandTest(unittest.TestCase):
    def pytest_part(self, args):
        cmd = hf.command(args, 3, False)
        return cmd[cmd.index("--") + 1:]

    def test_no_paths_fuzzes_every_fuzz_module(self):
        picks = self.pytest_part([])[3:]
        self.assertIn("tests/planner/playlist/test_m3u_fuzz.py", picks)
        self.assertIn("tests/gui/test_state_files_fuzz.py", picks)
        self.assertTrue(all(p.endswith("_fuzz.py") for p in picks), picks)

    def test_a_k_filter_still_gets_the_fuzz_modules(self):
        picks = self.pytest_part(["-k", "venue_pack"])
        self.assertEqual(picks[3:5], ["-k", "venue_pack"])
        self.assertIn("tests/planner/event/test_venue_pack_fuzz.py", picks)

    def test_a_path_replaces_them(self):
        self.assertEqual(self.pytest_part(["tests/shared/remote"]),
                         ["-n0", "-p", "no:cacheprovider", "tests/shared/remote"])

    def test_its_pytest_runs_serial_and_the_fuzzer_gets_the_workers(self):
        cmd = hf.command([], 3, True)
        self.assertEqual(cmd[cmd.index("-n") + 1], "3")
        self.assertIn("--dashboard", cmd)
        self.assertIn("-n0", cmd[cmd.index("--"):])


class EnvTest(unittest.TestCase):
    def test_the_workers_get_the_temp_folder_the_run_removes(self):
        env = hf.fuzz_env("X:/fuzz-temp")
        self.assertEqual({env["TMP"], env["TEMP"], env["TMPDIR"]}, {"X:/fuzz-temp"})
        self.assertEqual(env["PYTHONUNBUFFERED"], "1")


class TempRootTest(unittest.TestCase):
    """HypoFuzz collects with a pytest run of its own, then runs the tests in
    the same process: the end of that run must not take TEMP away."""

    def test_the_root_stays_while_hypofuzz_runs(self):
        with mock.patch.dict(os.environ, {"DANCEPLAYLIST_HYPOFUZZ": "1"}), \
                mock.patch.object(sys.modules["tests"], "remove_temp_root") as remove:
            conftest.pytest_unconfigure(None)
        remove.assert_not_called()
        self.assertEqual(hf.fuzz_env("X:/t")["DANCEPLAYLIST_HYPOFUZZ"], "1")

    def test_a_plain_run_still_removes_it(self):
        """Even with hypofuzz installed: Hypothesis loads it as a plugin in
        every run, so its being imported says nothing."""
        with mock.patch.dict(os.environ), \
                mock.patch.object(sys.modules["tests"], "remove_temp_root") as remove:
            os.environ.pop("DANCEPLAYLIST_HYPOFUZZ", None)
            conftest.pytest_unconfigure(None)
        remove.assert_called_once()


if __name__ == "__main__":
    unittest.main()
