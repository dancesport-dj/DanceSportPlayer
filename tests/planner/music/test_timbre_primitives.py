"""The pieces of timbre matching, one by one.

Run:  py -m unittest tests.planner.music.test_timbre_primitives -v

`test_similarity_nonfinite` pins the NaN cases and `test_sound_alike` the
three-view ranking. This covers what was left: the KL-to-percent calibration,
the Gaussian memo, the divergence itself (identical audio reads 100 %, a
different recording never does, nearer ranks higher), the dispatcher and
`timbre_measured`, the pool-relative cosine, and the rank helpers.
"""
import unittest
from types import SimpleNamespace as NS

import numpy as np

from planner.music import similarity as sim
from planner.music.analysis import GAUSS_MFCC, HAS_LIBROSA, TIMBRE_MFCC_DIM


def _gauss(rng, shift=0.0, scale=1.0):
    """A song's Gaussian over GAUSS_MFCC coefficients, as the analysis stores it."""
    a = rng.normal(size=(GAUSS_MFCC, 300)) * scale + shift
    return list(a.mean(axis=1)), list(np.cov(a).ravel())


def _feat(rng=None, shift=0.0, scale=1.0, mfcc=None, centroid=1.0, rms=0.1):
    rng = rng or np.random.default_rng(0)
    mean, cov = _gauss(rng, shift, scale)
    return NS(mfcc_mean=mean, mfcc_cov=cov, gauss_cache=None, centroid=centroid, rms=rms,
              mfcc=list(mfcc if mfcc is not None else rng.normal(size=TIMBRE_MFCC_DIM + 24)))


def _entry(path, features):
    return NS(path=path, features=features)


class KlToSimTest(unittest.TestCase):

    def test_zero_divergence_is_a_perfect_match(self):
        self.assertEqual(sim.kl_to_sim(0.0), 1.0)

    def test_a_small_divergence_is_capped_at_99_percent(self):
        # Only the numerically identical Gaussian (same audio) may read 100 %.
        self.assertEqual(sim.kl_to_sim(1.0), 0.99)
        self.assertEqual(sim.kl_to_sim(sim._KL_FLOOR), 0.99)

    def test_the_identical_threshold_is_the_edge(self):
        self.assertEqual(sim.kl_to_sim(sim._KL_IDENTICAL), 1.0)
        self.assertEqual(sim.kl_to_sim(sim._KL_IDENTICAL * 10), 0.99)

    def test_the_calibration_anchors(self):
        # J = 8 is the "genuine sound-alike" ~80 %, the median 11 is ~58 %.
        self.assertAlmostEqual(sim.kl_to_sim(8.0), 0.80, delta=0.03)
        self.assertAlmostEqual(sim.kl_to_sim(11.0), 0.58, delta=0.03)

    def test_it_falls_with_the_divergence_and_stays_in_range(self):
        values = [sim.kl_to_sim(j) for j in (0.0, 1.0, 6.0, 8.0, 11.0, 20.0, 30.0, 100.0)]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertTrue(all(0.0 <= v <= 1.0 for v in values))
        self.assertLess(sim.kl_to_sim(100.0), 0.01)


class FeatVectorTest(unittest.TestCase):

    def test_it_is_centroid_rms_and_the_first_sixty_mfcc(self):
        f = NS(centroid=3.0, rms=0.5, mfcc=list(range(84)))
        v = sim._feat_vector(f)
        self.assertEqual(v[:2], [3.0, 0.5])
        self.assertEqual(v[2:], list(range(TIMBRE_MFCC_DIM)))
        self.assertEqual(len(v), 2 + TIMBRE_MFCC_DIM)

    def test_a_shorter_stored_vector_gives_a_shorter_result(self):
        v = sim._feat_vector(NS(centroid=1.0, rms=1.0, mfcc=[1.0, 2.0, 3.0]))
        self.assertEqual(len(v), 5)


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class GaussOfTest(unittest.TestCase):

    def test_no_features_no_gaussian(self):
        self.assertEqual(sim._gauss_of(None), (None, None, None))

    def test_a_record_without_a_model_has_none(self):
        f = NS(mfcc_mean=None, mfcc_cov=None, gauss_cache=None)
        self.assertEqual(sim._gauss_of(f), (None, None, None))
        self.assertEqual(f.gauss_cache, (None, None, None))

    def test_a_model_of_the_wrong_size_has_none(self):
        f = NS(mfcc_mean=[0.0] * 5, mfcc_cov=[0.0] * 25, gauss_cache=None)
        self.assertEqual(sim._gauss_of(f)[0], None)

    def test_a_singular_covariance_has_none(self):
        f = NS(mfcc_mean=[0.0] * GAUSS_MFCC, mfcc_cov=[0.0] * GAUSS_MFCC**2, gauss_cache=None)
        self.assertEqual(sim._gauss_of(f), (None, None, None))

    def test_the_triple_is_mean_covariance_and_a_true_inverse(self):
        f = _feat(np.random.default_rng(3))
        mu, cov, inv = sim._gauss_of(f)
        self.assertEqual(mu.shape, (GAUSS_MFCC,))
        self.assertEqual(cov.shape, (GAUSS_MFCC, GAUSS_MFCC))
        self.assertTrue(np.allclose(cov @ inv, np.eye(GAUSS_MFCC), atol=1e-6))

    def test_it_is_computed_once_and_remembered(self):
        f = _feat(np.random.default_rng(3))
        first = sim._gauss_of(f)
        self.assertIs(f.gauss_cache, first)
        self.assertIs(sim._gauss_of(f), first)


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class GaussianKlTest(unittest.TestCase):

    def test_the_anchor_against_itself_reads_a_perfect_match(self):
        anchor = _feat(np.random.default_rng(1))
        out = sim._gaussian_kl_similarity(anchor, [_entry("self", anchor)])
        self.assertEqual(out["self"], 1.0)

    def test_the_same_audio_in_another_record_reads_a_perfect_match(self):
        a = _feat(np.random.default_rng(1))
        twin = _feat(np.random.default_rng(1))              # same numbers, own cache
        self.assertEqual(sim._gaussian_kl_similarity(a, [_entry("t", twin)])["t"], 1.0)

    def test_a_different_recording_never_reads_100_percent(self):
        a = _feat(np.random.default_rng(1))
        near = _feat(np.random.default_rng(2))
        self.assertLessEqual(sim._gaussian_kl_similarity(a, [_entry("n", near)])["n"], 0.99)

    def test_a_nearer_timbre_ranks_above_a_farther_one(self):
        a = _feat(np.random.default_rng(1))
        near = _feat(np.random.default_rng(2), shift=0.05)
        far = _feat(np.random.default_rng(3), shift=3.0, scale=4.0)
        out = sim._gaussian_kl_similarity(a, [_entry("near", near), _entry("far", far)])
        self.assertGreater(out["near"], out["far"])
        self.assertLess(out["far"], 0.5)

    def test_the_score_does_not_depend_on_what_else_is_in_the_pool(self):
        a = _feat(np.random.default_rng(1))
        e = _entry("e", _feat(np.random.default_rng(2)))
        alone = sim._gaussian_kl_similarity(a, [e])["e"]
        crowd = sim._gaussian_kl_similarity(
            a, [e] + [_entry(f"x{i}", _feat(np.random.default_rng(10 + i), shift=i))
                      for i in range(5)])["e"]
        self.assertEqual(alone, crowd)

    def test_the_score_is_the_same_both_ways_round(self):
        a, b = _feat(np.random.default_rng(1)), _feat(np.random.default_rng(2), shift=0.3)
        ab = sim._gaussian_kl_similarity(a, [_entry("b", b)])["b"]
        ba = sim._gaussian_kl_similarity(b, [_entry("a", a)])["a"]
        self.assertAlmostEqual(ab, ba, places=9)

    def test_an_entry_without_a_model_is_neutral(self):
        a = _feat(np.random.default_rng(1))
        bare = NS(mfcc_mean=None, mfcc_cov=None, gauss_cache=None)
        out = sim._gaussian_kl_similarity(
            a, [_entry("ok", _feat(np.random.default_rng(2))), _entry("bare", bare),
                _entry("none", None)])
        self.assertEqual(out["bare"], 0.5)
        self.assertEqual(out["none"], 0.5)
        self.assertNotEqual(out["ok"], 0.5)

    def test_an_anchor_without_a_model_makes_everything_neutral(self):
        bare = NS(mfcc_mean=None, mfcc_cov=None, gauss_cache=None)
        entries = [_entry("a", _feat(np.random.default_rng(2))), _entry("b", None)]
        self.assertEqual(sim._gaussian_kl_similarity(bare, entries), {"a": 0.5, "b": 0.5})

    def test_no_entry_with_a_model_makes_everything_neutral(self):
        a = _feat(np.random.default_rng(1))
        self.assertEqual(sim._gaussian_kl_similarity(a, [_entry("b", None)]), {"b": 0.5})

    def test_an_empty_pool_gives_an_empty_answer(self):
        self.assertEqual(sim._gaussian_kl_similarity(_feat(np.random.default_rng(1)), []), {})


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class PoolSimilarityTest(unittest.TestCase):

    def _vec_feat(self, mfcc, centroid=1.0, rms=0.1):
        return NS(centroid=centroid, rms=rms, mfcc=mfcc)

    def test_the_closest_vector_scores_highest_and_all_stay_in_range(self):
        rng = np.random.default_rng(5)
        base = rng.normal(size=TIMBRE_MFCC_DIM)
        anchor = self._vec_feat(list(base))
        near = self._vec_feat(list(base + rng.normal(size=TIMBRE_MFCC_DIM) * 0.05))
        far = self._vec_feat(list(-base))
        other = self._vec_feat(list(rng.normal(size=TIMBRE_MFCC_DIM)))
        out = sim._pool_similarity(anchor, [_entry("near", near), _entry("far", far),
                                            _entry("other", other)])
        self.assertGreater(out["near"], out["other"])
        self.assertGreater(out["other"], out["far"])
        self.assertTrue(all(0.0 <= v <= 1.0 for v in out.values()))

    def test_an_entry_without_features_is_neutral(self):
        anchor = self._vec_feat([0.0] * TIMBRE_MFCC_DIM)
        out = sim._pool_similarity(anchor, [_entry("a", self._vec_feat([1.0] * TIMBRE_MFCC_DIM)),
                                            _entry("none", None)])
        self.assertEqual(out["none"], 0.5)

    def test_a_stale_shorter_vector_is_neutral_and_does_not_crash(self):
        anchor = self._vec_feat([0.5] * TIMBRE_MFCC_DIM)
        out = sim._pool_similarity(anchor, [_entry("old", self._vec_feat([0.5] * 10)),
                                            _entry("new", self._vec_feat([0.4] * TIMBRE_MFCC_DIM))])
        self.assertEqual(out["old"], 0.5)
        self.assertIn("new", out)

    def test_nothing_comparable_makes_everything_neutral(self):
        anchor = self._vec_feat([0.5] * TIMBRE_MFCC_DIM)
        self.assertEqual(sim._pool_similarity(anchor, [_entry("n", None)]), {"n": 0.5})


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class DispatchTest(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(1)
        self.anchor = _feat(rng)
        self.entries = [_entry("a", _feat(np.random.default_rng(2))),
                        _entry("b", _feat(np.random.default_rng(3), shift=2.0))]

    def test_the_default_is_the_gaussian_method(self):
        self.assertEqual(sim.timbre_similarity(self.anchor, self.entries),
                         sim._gaussian_kl_similarity(self.anchor, self.entries))

    def test_gaussian_kl_by_name_is_the_default(self):
        self.assertEqual(sim.timbre_similarity(self.anchor, self.entries, "gaussian_kl"),
                         sim.timbre_similarity(self.anchor, self.entries))

    def test_any_other_name_falls_to_the_pool_cosine(self):
        self.assertEqual(sim.timbre_similarity(self.anchor, self.entries, "librosa"),
                         sim._pool_similarity(self.anchor, self.entries))


@unittest.skipUnless(HAS_LIBROSA, "needs librosa")
class TimbreMeasuredTest(unittest.TestCase):

    def test_a_gaussian_default_needs_the_model(self):
        self.assertTrue(sim.timbre_measured(_entry("a", _feat(np.random.default_rng(1)))))
        self.assertFalse(sim.timbre_measured(_entry("a", None)))
        bare = NS(mfcc_mean=None, mfcc_cov=None, gauss_cache=None)
        self.assertFalse(sim.timbre_measured(_entry("a", bare)))

    def test_the_cosine_method_only_needs_some_features(self):
        bare = NS(mfcc_mean=None, mfcc_cov=None, gauss_cache=None)
        self.assertTrue(sim.timbre_measured(_entry("a", bare), "librosa"))
        self.assertFalse(sim.timbre_measured(_entry("a", None), "librosa"))


class RankHelpersTest(unittest.TestCase):

    def test_shares_give_the_best_title_one_and_step_down(self):
        got = sim._shares({"a": 0.9, "b": 0.5, "c": 0.1, "d": 0.7})
        self.assertEqual(got, {"a": 1.0, "d": 0.75, "b": 0.5, "c": 0.25})

    def test_a_single_title_has_the_top_share(self):
        self.assertEqual(sim._shares({"only": 0.3}), {"only": 1.0})

    def test_the_mean_of_the_views(self):
        self.assertEqual(sim._mean({"timbre": 1.0, "groove": 0.5, "melody": 0.0}), 0.5)

    def test_z_cosines_of_a_row_equal_to_the_query_is_one(self):
        out = sim._z_cosines([1.0, 2.0, 3.0], [[1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [0.0, 5.0, 1.0]])
        self.assertAlmostEqual(out[0], 1.0, places=9)
        self.assertLess(out[1], 0.0)

    def test_z_cosines_with_a_non_finite_query_are_all_zero(self):
        self.assertEqual(sim._z_cosines([float("nan"), 1.0], [[1.0, 2.0], [2.0, 1.0]]),
                         [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
