"""Check duplicates between many lists: only list pairs that can share a song
are compared, and the report stays what comparing every pair gave.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.playlist.test_dup_report_pairs -v

Marcel, 2026-11-12: checking about 300 dropped files "took quite a while".
Each loose file is a list of its own, so the cross section compared 44,850
list pairs, and every pair built its own title clusters and Chromaprint
index: 29 s for 300 library tracks, measured. The oracle below is that loop,
made of the same `pair_dups` and `_cross_recordings` the report uses.
"""
import random
import unittest
from unittest import mock

import numpy as np

from planner.playlist import checks
from planner.playlist.checks import (
    ALLOW_REPEAT,
    _cross_recordings,
    build_dropped_dup_report,
    pair_dups,
)

_TITLES = ["moon river", "moon rivers", "moon river waltz", "tennessee waltz",
           "tennessee waltzs", "butterfly waltz", "butterfly waltz from twilight",
           "sway", "beautiful", "espana cani", "higher", "riche",
           "fly me to the moon", "fly me to the moon remix", "save the last dance"]
_DANCES = ["LW", "SW", "CC", "PD", None]


def _fp(seed: int, n: int = 800) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2**32, n, dtype=np.uint32)


_BASES = [_fp(100 + k) for k in range(4)]


def _old_cross(files: list) -> list:
    """The cross section as it was: every pair of lists through the pair checks."""
    def crossable(recs):
        return [r for r in recs if (r.get("dance") or "") not in ALLOW_REPEAT]
    cross = []
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            ra, rb = crossable(files[i][1]), crossable(files[j][1])
            exact, similar = pair_dups(ra, rb)
            seen = {frozenset((id(p["a"]), id(p["b"]))) for p in exact + similar}
            recording = [{"a": a, "b": b} for a, b in _cross_recordings(ra, rb, seen)]
            if exact or similar or recording:
                cross.append({"file_a": files[i][0], "file_b": files[j][0],
                              "exact": exact, "similar": similar, "recording": recording})
    return cross


def _shape(cross: list) -> list:
    """The cross section by record identity (records carry numpy arrays)."""
    return [(c["file_a"], c["file_b"],
             *([(id(p["a"]), id(p["b"])) for p in c[kind]]
               for kind in ("exact", "similar", "recording")))
            for c in cross]


def _random_files(seed: int) -> list:
    rnd = random.Random(seed)
    files = []
    for n in range(rnd.randint(2, 12)):
        recs = []
        for idx in range(1, rnd.randint(1, 6) + 1):
            title = rnd.choice(_TITLES)
            keys = [title] if rnd.random() < 0.9 else []
            roll = rnd.random()
            if roll < 0.4:
                chroma = None
            elif roll < 0.8:
                base = rnd.choice(_BASES)
                start = rnd.randint(0, 60)
                chroma = base[start:start + rnd.randint(300, 700)].copy()
                if rnd.random() < 0.3:      # another encode: some words changed
                    flip = rnd.sample(range(len(chroma)), len(chroma) // 3)
                    chroma[flip] ^= np.uint32(1)
            else:
                chroma = _fp(rnd.randint(1000, 9999))
            exact = f"fp:{rnd.randint(0, 5)}" if rnd.random() < 0.3 else f"p:{seed}:{n}:{idx}"
            recs.append({"idx": idx, "title": title, "path": f"C:/m/{title}.mp3",
                         "exact": exact, "tkeys": keys, "dance": rnd.choice(_DANCES),
                         "chroma": chroma})
        files.append((f"list{n}.m3u", recs))
    return files


def _loose(i: int, title: str, chroma=None) -> tuple:
    return (f"{i}.mp3", [{"idx": 1, "title": title, "path": f"C:/m/{i}.mp3",
                          "exact": f"p:{i}", "tkeys": [title], "dance": None,
                          "chroma": chroma}])


def _nonsense(rnd: random.Random) -> str:
    return "".join(rnd.choice("bcdfghjklmnpqrstvwxz") for _ in range(14))


class SameReportTest(unittest.TestCase):

    def test_random_lists_give_the_report_every_pair_gave(self):
        for seed in range(80):
            files = _random_files(seed)
            with self.subTest(seed=seed):
                self.assertEqual(_shape(build_dropped_dup_report(files)["cross"]),
                                 _shape(_old_cross(files)))

    def test_one_recording_in_more_files_than_a_bucket_holds(self):
        # 45 loose files, one recording under 45 names: more than find_pairs'
        # MAX_BUCKET, which only caps a word shared inside one comparison.
        rnd = random.Random(7)
        base = _fp(1)
        files = [_loose(i, _nonsense(rnd), base[i:i + 600].copy()) for i in range(45)]
        report = build_dropped_dup_report(files)
        self.assertEqual(len(report["cross"]), 45 * 44 // 2)
        self.assertEqual(_shape(report["cross"]), _shape(_old_cross(files)))

    def test_a_title_chain_through_a_third_list_joins_no_other_pair(self):
        files = [_loose(1, "butterfly waltz"),
                 _loose(2, "butterfly waltz from twilight"),
                 _loose(3, "butterfly waltz from twilight remix")]
        self.assertEqual(_shape(build_dropped_dup_report(files)["cross"]),
                         _shape(_old_cross(files)))


class PairsComparedTest(unittest.TestCase):

    def test_lists_with_nothing_in_common_are_not_compared(self):
        rnd = random.Random(3)
        files = [_loose(i, _nonsense(rnd), _fp(500 + i)) for i in range(40)]
        files.append(_loose(40, files[5][1][0]["title"]))
        with mock.patch.object(checks, "pair_dups", wraps=checks.pair_dups) as spy:
            report = build_dropped_dup_report(files)
        self.assertEqual(spy.call_count, 1, "only list 5 and list 40 share a song")
        self.assertEqual([(c["file_a"], c["file_b"]) for c in report["cross"]],
                         [("5.mp3", "40.mp3")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
