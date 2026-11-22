"""tools.dev.coverage_contexts: which lines only the GUI walks reach."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from coverage import CoverageData

from tools.dev import coverage_contexts as cc

WALK = "tests/gui/test_monkey.py::MonkeyTest::test_walk|run"
UNIT = "tests/gui/test_table.py::TableTest::test_sort|run"


def recorded(path: str, by_context: dict[str, list[int]], basename=None) -> CoverageData:
    data = CoverageData(basename=basename, no_disk=basename is None)
    for context, lines in by_context.items():
        data.set_context(context)
        data.add_lines({path: lines})
    return data


class WalkOnlyLinesTest(unittest.TestCase):
    def test_a_line_only_a_walk_ran_is_listed(self):
        data = recorded("/app/x.py", {WALK: [3, 4], UNIT: [4]})
        self.assertEqual(cc.walk_only_lines(data, "/app/x.py"), [3])

    def test_a_line_a_unit_test_also_ran_is_not(self):
        data = recorded("/app/x.py", {WALK: [5], UNIT: [5]})
        self.assertEqual(cc.walk_only_lines(data, "/app/x.py"), [])

    def test_an_import_time_line_belongs_to_no_test(self):
        data = recorded("/app/x.py", {"": [1, 2], WALK: [2]})
        # Line 1 ran only at import; line 2 at import and in a walk.
        self.assertEqual(cc.walk_only_lines(data, "/app/x.py"), [2])

    def test_a_windows_path_in_the_context_still_counts_as_the_walk(self):
        self.assertTrue(cc.is_walk(WALK.replace("/", "\\")))
        self.assertFalse(cc.is_walk(UNIT))


class RangesTest(unittest.TestCase):
    def test_runs_of_lines_collapse(self):
        self.assertEqual(cc.ranges([1, 2, 3, 7, 9, 10]), [(1, 3), (7, 7), (9, 10)])
        self.assertEqual(cc.ranges([]), [])


class MainTest(unittest.TestCase):
    def test_a_file_without_contexts_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, ".coverage")
            data = CoverageData(basename=base)
            data.add_lines({os.path.join(tmp, "x.py"): [1]})
            data.write()
            out = io.StringIO()
            with redirect_stdout(out):
                code = cc.main(["--data", base])
        self.assertEqual(code, 2)
        self.assertIn("--cov-context=test", out.getvalue())

    def test_the_summary_counts_walk_only_lines_per_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, ".coverage")
            path = os.path.join(os.getcwd(), "gui", "fake_for_test.py")
            recorded(path, {WALK: [1, 2, 3], UNIT: [3]}, basename=base).write()
            out = io.StringIO()
            with redirect_stdout(out):
                code = cc.main(["--data", base])
                cc.main(["--data", base, "gui/fake_for_test.py"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("2 lines in 1 files", text)
        self.assertIn("gui/fake_for_test.py: 2 lines only the walks reach", text)
        self.assertIn("  1-2", text)


if __name__ == "__main__":
    unittest.main()
