"""A feature that is NaN or infinite must not turn into a perfect match or
poison the scores of every other title (review items 89 and 90)."""
import unittest
from types import SimpleNamespace as NS

import numpy as np

from planner.music import similarity as sim
from planner.music.analysis import GAUSS_MFCC, HAS_LIBROSA


def feat(rng, nan=False, centroid=1.0):
    a = rng.normal(size=(GAUSS_MFCC, 200))
    mu = a.mean(axis=1)
    if nan:
        mu[0] = np.nan
    return NS(mfcc_mean=list(mu), mfcc_cov=list(np.cov(a).ravel()),
              gauss_cache=None, centroid=centroid, rms=0.1,
              mfcc=list(rng.normal(size=60)))


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class NonFiniteTests(unittest.TestCase):
    def test_nan_gaussian_is_not_a_perfect_match(self):
        rng = np.random.default_rng(0)
        anchor = feat(rng)
        entries = [NS(path="good", features=feat(rng)),
                   NS(path="bad", features=feat(rng, nan=True))]
        out = sim._gaussian_kl_similarity(anchor, entries)
        self.assertEqual(out["bad"], 0.5)
        self.assertLess(out["good"], 1.0)

    def test_nan_feature_does_not_collapse_the_pool(self):
        rng = np.random.default_rng(1)
        anchor = feat(rng)
        entries = [NS(path=f"g{i}", features=feat(rng)) for i in range(4)]
        entries.append(NS(path="bad", features=feat(rng, centroid=float("nan"))))
        out = sim._pool_similarity(anchor, entries)
        good = [out[f"g{i}"] for i in range(4)]
        self.assertTrue(all(np.isfinite(good)))
        self.assertGreater(len(set(good)), 1)
        self.assertEqual(out["bad"], 0.5)

    def test_z_cosines_ignore_non_finite_rows(self):
        out = sim._z_cosines([1, 2, 3], [[1, 2, 3], [3, 2, 1], [float("nan"), 1, 1]])
        self.assertTrue(all(np.isfinite(out[:2])))
        self.assertEqual(out[2], 0.0)


if __name__ == "__main__":
    unittest.main()
