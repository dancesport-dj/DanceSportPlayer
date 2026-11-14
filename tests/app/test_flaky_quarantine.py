#!/usr/bin/env python3
"""🧪 Tests known to fail under load run apart in CI, so red means a real failure.

Run:  py -m pytest tests/app/test_flaky_quarantine.py -n0

The list is in the root conftest.py (FLAKY), which marks those tests `flaky`.
The main CI step runs `-m "not flaky"`, a second one runs `-m flaky` and may
fail (11-12 review, suggestion 3 and T2).
"""

import importlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def flaky_ids() -> tuple[str, ...]:
    sys.path.insert(0, str(ROOT))
    try:
        return importlib.import_module("conftest").FLAKY
    finally:
        sys.path.remove(str(ROOT))


class FlakyQuarantineTest(unittest.TestCase):

    def test_every_listed_test_still_exists(self):
        """A renamed test would leave the quarantine without a word."""
        for node in flaky_ids():
            with self.subTest(node=node):
                path, cls, method = node.split("::")
                module = importlib.import_module(path[:-3].replace("/", "."))
                self.assertTrue(callable(getattr(getattr(module, cls), method, None)))

    def collected(self, mark: str) -> set[str]:
        files = sorted({n.split("::")[0] for n in flaky_ids()})
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-n0",
             "-p", "no:cacheprovider", "-m", mark, *files],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}, check=False)
        return {ln.strip() for ln in out.stdout.splitlines() if "::" in ln}

    def test_the_marker_picks_exactly_the_listed_tests(self):
        self.assertEqual(self.collected("flaky"), set(flaky_ids()))
        rest = self.collected("not flaky")
        self.assertTrue(rest, "the rest of those files still runs")
        self.assertFalse(rest & set(flaky_ids()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
