#!/usr/bin/env python3
"""The party check's near-duplicate clustering: same answer, far fewer pairs.

Run:  py -m unittest tests.planner.test_title_clusters -v

`title_cluster_map` compared every title with every other one — six seconds
for 1,500 titles, on the GUI thread. It now only tests the pairs an index says
could match; what it answers must not change, so the reference here is the
definition itself, every pair through `title_similar`.
"""

import random
import string
import unittest

from planner import checks
from planner.checks import title_cluster_map, title_similar

WORDS = ("love", "night", "dance", "heart", "fire", "dream", "summer", "rain",
         "tango", "moon", "baby", "time", "light", "shadow", "river", "angel",
         "world", "golden", "dreamer", "forever", "tonight", "paradise",
         "the", "of", "my", "you", "instr", "remix", "dj", "from", "twilight")


def _titles(n: int, seed: int = 7) -> list:
    """Titles as the cleaned keys look, with the variants the clustering is for:
    typos, a subtitle or '(Instr.)' tacked on, a DJ prefix, and short titles."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        base = " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 5)))
        out.append(base)
        roll = rng.random()
        if roll < 0.3:
            chars = list(base)
            for _ in range(rng.randint(1, 3)):
                i = rng.randrange(len(chars))
                op = rng.choice("sdi")
                if op == "s":
                    chars[i] = rng.choice(string.ascii_lowercase)
                elif op == "d" and len(chars) > 1:
                    del chars[i]
                else:
                    chars.insert(i, rng.choice(string.ascii_lowercase))
            out.append("".join(chars))
        elif roll < 0.45:
            out.append(base + " " + rng.choice(("instr", "remix", "from twilight")))
        elif roll < 0.55:
            out.append("dj " + base)
        elif roll < 0.6:
            out.append(base[:rng.randint(1, 6)])
    return out


def _reference(tkeys) -> dict:
    """The definition: every pair of distinct titles through `title_similar`."""
    titles = sorted(t for t in set(tkeys) if t)
    parent = {t: t for t in titles}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for i, a in enumerate(titles):
        for b in titles[i + 1:]:
            if title_similar(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    return {t: find(t) for t in titles}


class TitleClusterTest(unittest.TestCase):

    def test_the_clusters_are_the_all_pairs_clusters(self):
        for seed in (1, 2, 3):
            titles = _titles(300, seed)
            with self.subTest(seed=seed):
                got = title_cluster_map(titles)
                self.assertEqual(got, _reference(titles))
                # Not vacuous: the variants really did cluster.
                self.assertLess(len(set(got.values())), len(got) * 0.9)

    def test_typo_subtitle_and_prefix_variants_find_each_other(self):
        got = title_cluster_map(["enjoy the silence", "enjoy the silnce",
                                 "enjoy the silence instr", "dj ice love yourself",
                                 "love yourself", "higher", "riche"])
        self.assertEqual(got["enjoy the silnce"], got["enjoy the silence"])
        self.assertEqual(got["enjoy the silence instr"], got["enjoy the silence"])
        self.assertEqual(got["dj ice love yourself"], got["love yourself"])
        self.assertNotEqual(got["higher"], got["riche"])

    def test_only_a_small_share_of_the_pairs_is_compared(self):
        titles = sorted(set(_titles(800)))
        compared = []
        real = checks.title_similar
        checks.title_similar = lambda a, b: compared.append(1) or real(a, b)
        self.addCleanup(setattr, checks, "title_similar", real)
        title_cluster_map(titles)
        all_pairs = len(titles) * (len(titles) - 1) // 2
        self.assertLess(len(compared), all_pairs * 0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
