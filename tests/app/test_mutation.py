"""tools.dev.mutation: which tests a module gets, and how a session is counted."""
import os
import shlex
import tempfile
import unittest
from pathlib import Path

from cosmic_ray import work_item
from cosmic_ray.work_db import WorkDB, use_db
from cosmic_ray.work_item import MutationSpec, WorkerOutcome, WorkItem, WorkResult

from tools.dev import mutation as mu


class TestsForTest(unittest.TestCase):
    def test_a_module_gets_its_area_folder(self):
        self.assertEqual(mu.tests_for("planner/music/parsing.py"), "tests/planner")
        self.assertEqual(mu.tests_for("gui/table/view.py"), "tests/gui")
        self.assertEqual(mu.tests_for("tools/dev/mutation.py"), "tests/app")

    def test_shared_code_gets_the_whole_suite(self):
        self.assertEqual(mu.tests_for("shared/remote/server.py"), "tests")


class TestCommandTest(unittest.TestCase):
    def test_a_windows_path_with_a_space_survives_cosmic_rays_split(self):
        command = mu.test_command(r"C:\My Apps\venv\python.exe", [r"tests\planner\music"])
        args = shlex.split(command)
        self.assertEqual(args[0], "C:/My Apps/venv/python.exe")
        self.assertEqual(args[-1], "tests/planner/music")

    def test_each_mutant_runs_serial_and_stops_at_the_first_failure(self):
        args = shlex.split(mu.test_command("python", ["tests"]))
        self.assertIn("-x", args)
        self.assertIn("-n0", args)


class SessionPathTest(unittest.TestCase):
    def test_one_session_per_module(self):
        self.assertEqual(mu.session_path("planner/music/parsing.py").name, "planner.music.parsing.sqlite")


def item(job_id: str, line: int) -> WorkItem:
    return WorkItem.single(job_id, MutationSpec(Path("m.py"), "core/ReplaceBinaryOperator_Add_Sub", 0,
                                                (line, 0), (line, 5)))


class SummaryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "s.sqlite")

    def counted(self, results: dict[str, WorkResult]):
        with use_db(self.path, WorkDB.Mode.create) as db:
            for n, (job_id, result) in enumerate(results.items(), start=1):
                db.add_work_item(item(job_id, n * 10))
                db.set_result(job_id, result)
            return mu.summarize(db), mu.survivors(db)

    def test_the_rate_counts_only_mutants_the_tests_ran_against(self):
        normal = WorkerOutcome.NORMAL
        counts, left = self.counted({
            "a": WorkResult(normal, test_outcome=work_item.TestOutcome.KILLED),
            "b": WorkResult(normal, test_outcome=work_item.TestOutcome.KILLED),
            "c": WorkResult(normal, test_outcome=work_item.TestOutcome.KILLED),
            "d": WorkResult(normal, test_outcome=work_item.TestOutcome.SURVIVED, diff="-a + b\n+a - b"),
            "e": WorkResult(normal, test_outcome=work_item.TestOutcome.INCOMPETENT),
            "f": WorkResult(WorkerOutcome.SKIPPED),
            "g": WorkResult(WorkerOutcome.NO_TEST),
        })
        self.assertEqual(counts, {"killed": 3, "survived": 1, "incompetent": 1, "skipped": 1, "other": 1})
        self.assertEqual(mu.kill_rate(counts), 0.75)
        self.assertEqual(left, [(40, "ReplaceBinaryOperator_Add_Sub", "-a + b\n+a - b")])

    def test_nothing_tested_has_no_rate(self):
        counts, _ = self.counted({"a": WorkResult(WorkerOutcome.SKIPPED)})
        self.assertIsNone(mu.kill_rate(counts))


class AnnotationTest(unittest.TestCase):
    SOURCE = ("def f(a: int | None, b=1) -> str | None:\n"   # line 1
              "    x: list[int] | None = None\n"             # line 2
              "    return a | b\n")                          # line 3

    def test_the_spans_cover_arguments_returns_and_annotated_names(self):
        spans = mu.annotation_spans(self.SOURCE)
        self.assertEqual(sorted(spans), [((1, 9), (1, 19)), ((1, 29), (1, 39)), ((2, 7), (2, 23))])

    def test_a_mutant_in_an_annotation_is_skipped_and_one_in_code_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "m.py").write_text(self.SOURCE, encoding="utf-8")
            with use_db(os.path.join(tmp, "s.sqlite"), WorkDB.Mode.create) as db:
                for job_id, pos in {"arg": (1, 13), "ret": (1, 34), "var": (2, 17), "code": (3, 13)}.items():
                    db.add_work_item(WorkItem.single(job_id, MutationSpec(
                        Path("m.py"), "core/ReplaceBinaryOperator_BitOr_Add", 0, pos, (pos[0], pos[1] + 1))))
                db.set_result("ret", WorkResult(WorkerOutcome.NORMAL, test_outcome=work_item.TestOutcome.SURVIVED))
                self.assertEqual(mu.skip_annotations(db, Path(tmp)), 3)
                results = {item.job_id: result.worker_outcome for item, result in db.completed_work_items}
                pending = [item.job_id for item in db.pending_work_items]
        self.assertEqual(results, {"arg": WorkerOutcome.SKIPPED, "ret": WorkerOutcome.SKIPPED,
                                   "var": WorkerOutcome.SKIPPED})
        self.assertEqual(pending, ["code"])


if __name__ == "__main__":
    unittest.main()
