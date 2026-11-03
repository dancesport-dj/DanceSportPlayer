r"""Check duplicates: one recording under different files, found by Chromaprint.

Run:  .venv\Scripts\python.exe -m unittest tests.gui.test_recording_dups -v

A record may carry `chroma`, the stored fingerprint words. Two records with
different files and unrelated titles but one recording are reported as kind
"recording"; a pair the title check already reports is not reported twice.
"""
import os
import tempfile
import unittest

import numpy as np

if "DANCEPLAYLIST_STATE_DIR" not in os.environ:
    os.environ["DANCEPLAYLIST_STATE_DIR"] = tempfile.mkdtemp(prefix="dp_state_")

from planner.playlist.checks import build_dropped_dup_report


def _fp(seed, n=800):
    return np.random.default_rng(seed).integers(0, 2**32, n, dtype=np.uint32)


def _rec(idx, name, chroma=None, exact=None):
    return {"idx": idx, "title": name, "path": f"C:/m/{name}.mp3",
            "exact": exact or f"fp:{name}", "tkeys": [name.lower()],
            "dance": "LW", "chroma": chroma}


class RecordingTest(unittest.TestCase):
    def test_within_one_list(self):
        a = _fp(1)
        recs = [_rec(1, "zzfirst", a), _rec(2, "qqsecond", a[40:700]),
                _rec(3, "other", _fp(2))]
        report = build_dropped_dup_report([("list.m3u", recs)])
        got = [(c["kind"], [m["idx"] for m in c["members"]])
               for f in report["within"] for c in f["clusters"]]
        self.assertEqual(got, [("recording", [1, 2])])

    def test_across_two_lists(self):
        a = _fp(1)
        report = build_dropped_dup_report([
            ("a.m3u", [_rec(1, "zzfirst", a)]),
            ("b.m3u", [_rec(1, "qqsecond", a), _rec(2, "other", _fp(2))])])
        self.assertEqual(len(report["cross"]), 1)
        pairs = report["cross"][0]["recording"]
        self.assertEqual([(p["a"]["idx"], p["b"]["idx"]) for p in pairs], [(1, 1)])

    def test_exact_copies_are_not_also_recordings(self):
        a = _fp(1)
        recs = [_rec(1, "x", a, exact="fp:same"), _rec(2, "y", a, exact="fp:same")]
        kinds = [c["kind"] for f in build_dropped_dup_report([("l.m3u", recs)])["within"]
                 for c in f["clusters"]]
        self.assertEqual(kinds, ["exact"])

    def test_title_match_is_not_reported_twice(self):
        a = _fp(1)
        recs = [_rec(1, "same", a), _rec(2, "same", a, exact="fp:other")]
        kinds = [c["kind"] for f in build_dropped_dup_report([("l.m3u", recs)])["within"]
                 for c in f["clusters"]]
        self.assertEqual(kinds, ["similar"])

    def test_records_without_chroma_change_nothing(self):
        recs = [_rec(1, "aaa"), _rec(2, "bbb")]
        self.assertEqual(build_dropped_dup_report([("l.m3u", recs)]),
                         {"within": [], "cross": []})


if __name__ == "__main__":
    unittest.main()
