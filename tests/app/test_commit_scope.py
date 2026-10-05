#!/usr/bin/env python3
"""Tests for tools/commit_scope.py — which tests the pre-commit hook runs.

Run:  py -m unittest tests.app.test_commit_scope -v

A scope that is too narrow lets a commit through that breaks another area, and
nothing notices until the push. So the cases that must run the whole suite are
what is pinned down here.
"""

import unittest
from pathlib import Path

from tools import commit_scope as cs

ROOT = Path(__file__).resolve().parents[2]


class PlanTest(unittest.TestCase):

    def test_one_area_runs_that_package(self):
        runs, _ = cs.plan([("player/player.py", 20), ("tests/player/test_pd_stop.py", 30)])
        self.assertEqual(runs, [("tests/player", cs.ALL_TESTS)])

    def test_the_root_modules_belong_to_their_package(self):
        self.assertEqual(cs.area_of("dancesport_gui.py"), "gui")
        self.assertEqual(cs.area_of("dancesport_planner.py"), "planner")
        self.assertEqual(cs.area_of("tools/announce_eq.py"), "app")

    def test_two_areas_run_everything(self):
        runs, reason = cs.plan([("gui/deck.py", 5), ("player/player.py", 5)])
        self.assertIsNone(runs)
        self.assertIn("gui, player", reason)

    def test_a_test_file_counts_for_its_area(self):
        runs, _ = cs.plan([("planner/scoring.py", 5), ("tests/gui/test_deck.py", 5)])
        self.assertIsNone(runs)

    def test_a_big_change_in_one_area_runs_everything(self):
        many = [(f"gui/m{i}.py", 1) for i in range(cs.BIG_FILES)]
        self.assertIsNone(cs.plan(many)[0])
        self.assertIsNone(cs.plan([("gui/deck.py", cs.BIG_LINES)])[0])
        self.assertIsNotNone(cs.plan([("gui/deck.py", cs.BIG_LINES - 1)])[0])

    def test_shared_plumbing_runs_everything(self):
        for path in ("tests/qt_test_support.py", "requirements.txt", "requirements-full.txt",
                     "pyproject.toml", ".githooks/pre-commit"):
            with self.subTest(path=path):
                self.assertIsNone(cs.plan([(path, 1)])[0])

    def test_shared_widgets_run_everything(self):
        # shared/ is what the desk and the evening both build on, so a change
        # there can break either side's tests.
        self.assertIsNone(cs.plan([("shared/theme.py", 1)])[0])

    def test_the_catalog_adds_i18n_tests_without_an_area(self):
        runs, _ = cs.plan([("player/cartwall.py", 10), (cs.CATALOG, 10)])
        self.assertEqual(runs, [("tests/player", cs.ALL_TESTS), ("tests", cs.I18N_PATTERN)])

    def test_the_catalog_does_not_count_towards_size(self):
        runs, _ = cs.plan([("gui/deck.py", 10), (cs.CATALOG, 5000)])
        self.assertIsNotNone(runs)

    def test_no_python_runs_nothing(self):
        runs, _ = cs.plan([("README.md", 40), ("speech/announcements/male/RB.mp3", 0), ("gui/icon.png", 0)])
        self.assertEqual(runs, [])

    def test_every_test_package_is_an_area(self):
        # A new tests/<pkg>/ that no area maps to would never run on a commit.
        packages = {p.name for p in (ROOT / "tests").iterdir()
                    if p.is_dir() and (p / "__init__.py").exists()}
        self.assertEqual(packages, set(cs.AREAS))


if __name__ == "__main__":
    unittest.main()
