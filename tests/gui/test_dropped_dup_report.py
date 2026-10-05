#!/usr/bin/env python3
"""Tests for build_dropped_dup_report (Check duplicates, within-one-list view).

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_dropped_dup_report -v

Pins the Paso Doble rule: PD repeats inside ONE list are normal tournament
practice, so within a list only byte-identical PD copies are reported —
similar recordings (same title, different file) are not. Other dances and
exact PD copies keep warning as before.

The builder lives in planner.checks (pure, Qt-free), so no window is needed.
"""

import os
import tempfile
import unittest
from pathlib import Path

if "DANCEPLAYLIST_STATE_DIR" not in os.environ:
    os.environ["DANCEPLAYLIST_STATE_DIR"] = tempfile.mkdtemp(prefix="dp_state_")


def _rec(idx: int, path: str, dance: str, exact: str = ""):
    """A report record like _check_dropped_duplicates builds them."""
    from planner.parsing import _song_title_keys
    return {"idx": idx, "title": Path(path).stem, "path": path,
            "exact": exact or f"p:{path.lower()}",
            "tkeys": _song_title_keys(path), "dance": dance}


class WithinListPdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from planner.checks import build_dropped_dup_report
        cls.build = staticmethod(build_dropped_dup_report)

    def test_pd_similar_within_one_list_is_suppressed(self):
        recs = [_rec(1, r"C:\a\Espana Cani.mp3", "PD"),
                _rec(2, r"C:\b\Espana Cani.mp3", "PD")]
        report = self.build([("finale.m3u", recs)])
        self.assertEqual(report["within"], [])

    def test_pd_exact_copy_within_one_list_still_warns(self):
        recs = [_rec(1, r"C:\a\Espana Cani.mp3", "PD", exact="fp:abc"),
                _rec(2, r"C:\b\Espana Cani.mp3", "PD", exact="fp:abc")]
        report = self.build([("finale.m3u", recs)])
        kinds = [c["kind"] for f in report["within"] for c in f["clusters"]]
        self.assertEqual(kinds, ["exact"])

    def test_other_dance_similar_within_one_list_still_warns(self):
        recs = [_rec(1, r"C:\a\Sway.mp3", "CC"),
                _rec(2, r"C:\b\Sway.mp3", "CC")]
        report = self.build([("vorrunde.m3u", recs)])
        kinds = [c["kind"] for f in report["within"] for c in f["clusters"]]
        self.assertEqual(kinds, ["similar"])


if __name__ == "__main__":
    unittest.main()
