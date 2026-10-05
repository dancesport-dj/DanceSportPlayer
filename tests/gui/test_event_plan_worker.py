#!/usr/bin/env python3
"""The 🏆 Event run off the UI thread: gather, plan the variants, ask the AI.

Run:  py -m unittest tests.gui.test_event_plan_worker -v

The worker is run on the test's own thread (`run()`, not `start()`), so its
signals arrive at once. A second run — the rate limit lifted, or the second
round — starts from the plan it is handed and gathers nothing again.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_event_worker_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.workers import EventPlanWorker  # noqa: E402
from planner import event_plan  # noqa: E402
from planner.competition import parse_competition_schedule  # noqa: E402
from tests.planner.test_event_ai import FakeModel  # noqa: E402
from tests.planner.test_event_variants import EventFixture  # noqa: E402


class EventPlanWorkerTest(EventFixture, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.specs = parse_competition_schedule("HGR S STD 2-1\nSEN I S STD 2-1")
        self.editions = event_plan.past_editions("danceconvention", root=self.root)
        self.got = {}

    def run_worker(self, worker):
        worker.done.connect(lambda result, cands: self.got.update(
            result=result, cands=cands))
        worker.error.connect(lambda msg: self.got.update(error=msg))
        worker.cancelled.connect(lambda: self.got.update(cancelled=True))
        steps = []
        worker.step.connect(lambda role, title, text: steps.append((role, title)))
        worker.run()
        return steps

    def worker(self, **kw):
        kw.setdefault("similar", self.similar)
        return EventPlanWorker(self.lib, self.specs, self.editions, **kw)

    def test_the_chosen_variants_are_planned(self):
        self.run_worker(self.worker(profiles=["like_last_year", "variety"],
                                    ask_ai=False))
        result = self.got["result"]
        self.assertEqual(list(result.variants), ["like_last_year", "variety"])
        self.assertEqual([c.spec.label for c in self.got["cands"]],
                         ["HGR S STD", "SEN I S STD"])
        self.assertEqual(len(result.variants["variety"]), 2)

    def test_the_ai_is_asked_once_per_competition(self):
        model = FakeModel(lambda i, user: ([], {}))
        steps = self.run_worker(self.worker(profiles=["variety"], ask=model))
        self.assertEqual(len(model.calls), 2)
        self.assertIn("sent", [role for role, _t in steps])
        self.assertEqual(self.got["result"].failed, [])

    def test_the_new_share_and_class_lists_reach_the_plan(self):
        self.run_worker(self.worker(profiles=["variety"], ask_ai=False,
                                    use_class=False, new_share=0.0))
        tiers = {p.tier for c in self.got["result"].variants["variety"]
                 for p in self.picks(c)}
        self.assertNotIn("class", tiers)
        self.assertNotIn("new", tiers)

    def test_the_rare_share_reaches_the_plan(self):
        for n in range(4):
            self.entry(f"Rare {n} LW", "LW", s_plays=1, months_ago=60)
        steps = []
        worker = self.worker(profiles=["variety"], ask_ai=False, rare_share=0.5)
        worker.step.connect(lambda role, title, text: steps.append(text))
        self.run_worker(worker)
        tiers = {p.tier for c in self.got["result"].variants["variety"]
                 for p in self.picks(c)}
        self.assertIn("rare", tiers)
        self.assertIn("4 rarely played at the class", steps[0])
        self.assertIn("from other events' lists of the class", steps[0])

    def test_asking_again_starts_from_the_plan(self):
        """Nothing is gathered or planned again — no library needed."""
        self.run_worker(self.worker(profiles=["variety"], ask_ai=False))
        first = self.got["result"]
        model = FakeModel(lambda i, user: ([], {}))
        again = EventPlanWorker(None, [], [], variants=first.variants,
                                cands_list=self.got["cands"], only=[1], ask=model)
        self.run_worker(again)
        self.assertEqual(len(model.calls), 1)
        self.assertIn("SEN I S", model.calls[0][1])
        self.assertIsNot(self.got["result"], first)

    def test_a_stop_before_the_plan_plans_nothing(self):
        w = self.worker(profiles=["variety"], ask_ai=False)
        w.cancel()
        self.run_worker(w)
        self.assertTrue(self.got.get("cancelled"))
        self.assertNotIn("result", self.got)

    def test_a_failure_is_reported(self):
        w = EventPlanWorker(None, self.specs, self.editions,
                            profiles=["variety"], ask_ai=False)
        with self.assertLogs("dancesport.workers", level="ERROR"):
            self.run_worker(w)
        self.assertIn("error", self.got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
