"""The Chromaprint matcher: the same recording through another encode or cut,
told apart from a different song. Synthetic fingerprints, so it runs without
fpcalc; the thresholds themselves are calibrated on real files separately."""
import unittest

import numpy as np

from planner.music import chroma_match as cm


def _random_fp(seed: int, n: int = 800) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2**32, n, dtype=np.uint32)


def _noisy(fp: np.ndarray, flip: float, seed: int = 99) -> np.ndarray:
    """`fp` with each bit flipped at rate `flip`, like another encode of it."""
    rng = np.random.default_rng(seed)
    mask = np.zeros(len(fp), dtype=np.uint32)
    for bit in range(32):
        mask |= (rng.random(len(fp)) < flip).astype(np.uint32) << np.uint32(bit)
    return fp ^ mask


class PackTests(unittest.TestCase):
    def test_roundtrip(self):
        fp = _random_fp(1)
        self.assertTrue(np.array_equal(cm.unpack(cm.pack(fp)), fp))

    def test_parse_accepts_signed_values(self):
        """fpcalc -raw may print a 32-bit word as a negative integer."""
        got = cm.parse_raw("-1,0,4294967295,7")
        self.assertEqual(list(got), [0xFFFFFFFF, 0, 0xFFFFFFFF, 7])


class SimilarityTests(unittest.TestCase):
    def test_identical(self):
        a = _random_fp(1)
        m = cm.compare(a, a)
        self.assertIsNotNone(m)
        self.assertEqual(m.score, 1.0)
        self.assertEqual(m.shift, 0)
        self.assertTrue(cm.is_same(m))

    def test_another_encode_matches(self):
        a = _random_fp(1)
        m = cm.compare(a, _noisy(a, 0.10))
        self.assertTrue(cm.is_same(m), m)
        self.assertGreater(m.score, 0.8)

    def test_cut_start_and_end_found_with_shift(self):
        a = _random_fp(1)
        c = a[60:500]
        m = cm.compare(a, c)
        self.assertTrue(cm.is_same(m), m)
        self.assertEqual(m.shift, 60)           # a[i + 60] lines up with c[i]
        self.assertAlmostEqual(m.coverage, 1.0)  # the short one lies inside

    def test_cut_other_direction(self):
        a = _random_fp(1)
        m = cm.compare(a[60:500], a)
        self.assertEqual(m.shift, -60)
        self.assertTrue(cm.is_same(m), m)

    def test_cut_and_reencoded(self):
        a = _random_fp(1)
        m = cm.compare(a, _noisy(a[:400], 0.12))
        self.assertTrue(cm.is_same(m), m)

    def test_different_song_does_not_match(self):
        m = cm.compare(_random_fp(1), _random_fp(2))
        self.assertFalse(cm.is_same(m), m)

    def test_too_short_to_judge(self):
        a = _random_fp(1)
        self.assertIsNone(cm.compare(a, a[:cm.MIN_ITEMS - 1]))
        self.assertFalse(cm.is_same(None))

    def test_small_overlap_is_not_a_match(self):
        """Two tracks that only agree over a few seconds are not one recording."""
        a = _random_fp(1)
        b = np.concatenate([_random_fp(3, 100), a[:cm.MIN_ITEMS + 5]])
        m = cm.compare(a, b)
        self.assertFalse(cm.is_same(m), m)


class EdgeShiftTests(unittest.TestCase):
    """The best of 321 alignments is picked, so a weak score at the very edge of
    the search is likelier chance than a match: on the real library two
    unrelated songs reached 0.72 at a shift of 150+. Far shifts need more."""

    def test_weak_score_at_a_far_shift_is_not_a_match(self):
        a = _random_fp(1)
        far = cm.EDGE_SHIFT + 20
        m = cm.compare(a, _noisy(a[far:far + 400], 0.28))
        self.assertEqual(m.shift, far)
        self.assertTrue(0.70 <= m.score < cm.EDGE_SCORE, m)
        self.assertFalse(cm.is_same(m), m)

    def test_same_score_near_the_start_is_a_match(self):
        a = _random_fp(1)
        m = cm.compare(a, _noisy(a[5:405], 0.28))
        self.assertTrue(cm.is_same(m), m)

    def test_strong_score_at_a_far_shift_is_a_match(self):
        a = _random_fp(1)
        far = cm.MAX_SHIFT - 5
        m = cm.compare(a, _noisy(a[far:far + 400], 0.05))
        self.assertEqual(m.shift, far)
        self.assertTrue(cm.is_same(m), m)


class FindPairsTests(unittest.TestCase):
    def test_pairs_over_a_library(self):
        a = _random_fp(1)
        tracks = {
            "a": a,
            "a_reenc": _noisy(a, 0.10),
            "a_cut": a[60:500],
            "other1": _random_fp(2),
            "other2": _random_fp(3),
        }
        pairs = {frozenset((x, y)) for x, y, _m in cm.find_pairs(tracks)}
        self.assertEqual(pairs, {frozenset(("a", "a_reenc")),
                                 frozenset(("a", "a_cut")),
                                 frozenset(("a_reenc", "a_cut"))})

    def test_cancel_stops_the_scan(self):
        tracks = {str(i): _random_fp(i) for i in range(10)}
        calls = []

        def cancel():
            calls.append(1)
            return True
        self.assertEqual(cm.find_pairs(tracks, should_cancel=cancel), [])
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()
