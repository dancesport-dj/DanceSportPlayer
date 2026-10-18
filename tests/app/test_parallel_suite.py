#!/usr/bin/env python3
"""Tests for tools/dev/parallel_suite.py — the suite across several processes.

Run:  py -m unittest tests.app.test_parallel_suite -v

The retry is only honest if it is limited to a native crash: a red batch has to
stay red. That is what is pinned down here, with the processes faked.
"""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.dev import parallel_suite as ps

GREEN = (0, "Ran 3 tests in 0.1s\n\nOK\n")
RED = (1, "Ran 3 tests in 0.1s\n\nFAILED (failures=1)\n")
CRASH = (0xC0000005, "🎛 No free cartwall voice\n")
WORK = [["tests.gui.test_a"], ["tests.player.test_b"], ["tests.app.test_c"]]


def run_with(outcomes: dict[str, list]) -> tuple[int, str, dict[str, int]]:
    """run_all(WORK) with each batch's processes ending as listed, in order."""
    calls = {batch[0]: 0 for batch in WORK}

    def fake(batch):
        calls[batch[0]] += 1
        return outcomes.get(batch[0], [GREEN])[calls[batch[0]] - 1]

    out = io.StringIO()
    with mock.patch.object(ps, "run_batch", side_effect=fake), \
            contextlib.redirect_stdout(out):
        code = ps.run_all(WORK)
    return code, out.getvalue(), calls


class RunAllTest(unittest.TestCase):

    def test_all_green_passes_with_one_run_each(self):
        code, out, calls = run_with({})
        self.assertEqual(code, 0)
        self.assertEqual(set(calls.values()), {1})
        self.assertIn("Ran 9 tests", out)
        self.assertNotIn("retried", out)

    def test_a_red_batch_fails_and_is_not_retried(self):
        code, out, calls = run_with({"tests.gui.test_a": [RED]})
        self.assertEqual(code, 1)
        self.assertEqual(calls["tests.gui.test_a"], 1)
        self.assertIn("red: tests.gui.test_a", out)

    def test_a_crash_is_retried_once_and_passes(self):
        code, out, calls = run_with({"tests.player.test_b": [CRASH, GREEN]})
        self.assertEqual(code, 0)
        self.assertEqual(calls["tests.player.test_b"], 2)
        self.assertIn("native crash, retried: tests.player.test_b", out)
        self.assertIn("Ran 9 tests", out)

    def test_a_crash_twice_fails(self):
        code, out, calls = run_with({"tests.player.test_b": [CRASH, CRASH]})
        self.assertEqual(code, 1)
        self.assertEqual(calls["tests.player.test_b"], 2)
        self.assertIn("red: tests.player.test_b", out)

    def test_a_crash_then_a_real_failure_fails(self):
        code, _, _ = run_with({"tests.app.test_c": [CRASH, RED]})
        self.assertEqual(code, 1)

    def test_every_crash_spelling_counts(self):
        for crash in (139, -11, 3221225477, -1073741819):
            code, _, calls = run_with({"tests.app.test_c": [(crash, ""), GREEN]})
            self.assertEqual((code, calls["tests.app.test_c"]), (0, 2), crash)


class BatchTest(unittest.TestCase):

    def test_the_batches_cover_every_test_module_once(self):
        names = [name for batch in ps.batches() for name in batch]
        on_disk = {".".join(p.relative_to(ps.ROOT).with_suffix("").parts)
                   for p in Path(ps.ROOT).glob("tests/**/test_*.py")}
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), on_disk)
        self.assertIn("tests.app.test_parallel_suite", names)

    def test_a_test_module_in_a_subpackage_is_found(self):
        # tests/<side>/<subpackage>/ mirrors the app's own subpackages.
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for rel in ("tests/gui/test_top.py", "tests/gui/decks/test_deep.py"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("")
        with mock.patch.object(ps, "ROOT", root):
            names = [name for batch in ps.batches() for name in batch]
        self.assertEqual(names, ["tests.gui.decks.test_deep", "tests.gui.test_top"])

    def test_each_child_makes_its_own_data_folder(self):
        with mock.patch.dict(os.environ, {"DANCEPLAYLIST_DATA_DIR": "shared"}):
            self.assertNotIn("DANCEPLAYLIST_DATA_DIR", ps.child_env())

    def test_qt_runs_offscreen_unless_told_otherwise(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("QT_QPA_PLATFORM", None)
            self.assertEqual(ps.child_env()["QT_QPA_PLATFORM"], "offscreen")
            os.environ["QT_QPA_PLATFORM"] = "windows"
            self.assertEqual(ps.child_env()["QT_QPA_PLATFORM"], "windows")

    def test_tests_ran_reads_the_unittest_tail(self):
        self.assertEqual(ps.tests_ran(RED[1]), 3)
        self.assertEqual(ps.tests_ran(CRASH[1]), 0)


if __name__ == "__main__":
    unittest.main()
