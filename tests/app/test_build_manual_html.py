#!/usr/bin/env python3
"""Tests for tools/build_manual_html.py — which manual it builds, and its title.

Run:  py -m unittest tests.app.test_build_manual_html -v

There are two manuals: the player's in docs/manual (public) and the
planner's, kept on this machine only. The builder takes either folder and
names the page after that manual's own index heading.
"""

import tempfile
import unittest
from pathlib import Path

from tools import build_manual_html as bm


class BuildManualTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "README.md").write_text(
            "# The Player Manual\n\n1. [Start](01-start.md)\n", encoding="utf-8")
        (self.dir / "01-start.md").write_text(
            "# 1 · Start\n\nHello.\n", encoding="utf-8")

    def test_the_page_is_named_after_the_index_heading(self):
        page, broken = bm.buildHtml(self.dir)
        self.assertIn("<title>The Player Manual</title>", page)
        self.assertEqual(broken, [])

    def test_a_folder_given_is_built_into_its_own_manual_html(self):
        with self.assertLogs(bm.log, "INFO"):
            code = bm.main([str(self.dir)])
        self.assertEqual(code, 0)
        self.assertIn("Hello.", (self.dir / "manual.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
