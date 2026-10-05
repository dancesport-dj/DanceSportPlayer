"""Tests for instrumental/vocal detection: the filename marker
(planner.parsing.title_marks_instrumental) and the learned audio probability
(planner.vocals)."""
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from planner.models import MusicEntry
from planner.parsing import title_marks_instrumental
from planner.vocals import (
    INSTR_PROB_THRESHOLD,
    VOCAL_SHARE_INSTR_MAX,
    apply_vocal_shares,
    entry_is_instrumental,
    learn_instrumental_probs,
)


class TitleMarkerTest(unittest.TestCase):

    def test_markers_match(self):
        for name in ("Golden Earrings (Instr.)", "Mi mi Mi instr",
                     "Nobody Knows (inst)", "Higher Instrumental Version",
                     "When I See An Elephant Fly (Instr.)"):
            self.assertTrue(title_marks_instrumental(name), name)

    def test_plain_words_do_not_match(self):
        for name in ("Instant Karma", "Einstürzende Neubauten",
                     "Against All Odds", "Winston Tells All"):
            self.assertFalse(title_marks_instrumental(name), name)


def _entry(title, **kw):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, **kw)


def _feat(vec):
    return SimpleNamespace(mfcc=np.asarray(vec, dtype=np.float32))


class EffectiveFlagTest(unittest.TestCase):

    def test_explicit_tag_wins(self):
        e = _entry("a", is_instrumental=True, audio_instr_prob=0.0)
        self.assertTrue(entry_is_instrumental(e))

    def test_curated_comment_without_tag_is_vocal(self):
        # The user wrote a class comment and did NOT tag instr → vocal, even
        # when the audio model is confident.
        e = _entry("b", classes_ok=["B", "A", "S"], audio_instr_prob=0.99)
        self.assertFalse(entry_is_instrumental(e))

    def test_audio_probability_decides_the_untagged(self):
        self.assertTrue(entry_is_instrumental(
            _entry("c", audio_instr_prob=INSTR_PROB_THRESHOLD)))
        self.assertFalse(entry_is_instrumental(
            _entry("d", audio_instr_prob=INSTR_PROB_THRESHOLD - 0.05)))

    def test_unknown_defaults_to_vocal(self):
        self.assertFalse(entry_is_instrumental(_entry("e")))

    def test_measured_share_decides(self):
        self.assertTrue(entry_is_instrumental(
            _entry("f", vocal_share=VOCAL_SHARE_INSTR_MAX)))
        self.assertFalse(entry_is_instrumental(
            _entry("g", vocal_share=VOCAL_SHARE_INSTR_MAX + 0.01)))

    def test_measured_share_outranks_the_heuristics(self):
        # Curated comment says vocal, but Demucs found no singing → instrumental.
        e = _entry("h", classes_ok=["S"], vocal_share=0.01)
        self.assertTrue(entry_is_instrumental(e))
        # The learned probability says instrumental, but Demucs heard vocals.
        e = _entry("i", audio_instr_prob=0.99, vocal_share=0.4)
        self.assertFalse(entry_is_instrumental(e))

    def test_explicit_tag_beats_the_measured_share(self):
        e = _entry("j", is_instrumental=True, vocal_share=0.9)
        self.assertTrue(entry_is_instrumental(e))


class ApplySharesTest(unittest.TestCase):

    def test_applies_only_measured_tracks(self):
        measured = _entry("measured")
        unmeasured = _entry("unmeasured")
        shares = {str(measured.path): 0.02}
        cache = SimpleNamespace(
            get_vocal_share=lambda p: shares.get(str(p)))
        self.assertEqual(apply_vocal_shares([measured, unmeasured], cache), 1)
        self.assertEqual(measured.vocal_share, 0.02)
        self.assertIsNone(unmeasured.vocal_share)


class LearnProbsTest(unittest.TestCase):

    def _make_library(self, n_pos=25, n_neg=25):
        rng = np.random.default_rng(42)
        dim = 84
        entries = []
        for i in range(n_pos):
            vec = rng.normal(0.0, 0.3, dim)
            vec[:10] += 2.0
            entries.append(_entry(f"instr{i}", is_instrumental=True,
                                  features=_feat(vec)))
        for i in range(n_neg):
            vec = rng.normal(0.0, 0.3, dim)
            vec[:10] -= 2.0
            entries.append(_entry(f"vocal{i}", classes_ok=["S"],
                                  features=_feat(vec)))
        return entries, rng, dim

    def test_learns_separable_labels_and_annotates_unlabeled(self):
        entries, rng, dim = self._make_library()
        near_pos = rng.normal(0.0, 0.3, dim)
        near_pos[:10] += 2.0
        near_neg = rng.normal(0.0, 0.3, dim)
        near_neg[:10] -= 2.0
        u_pos = _entry("untagged instrumental", features=_feat(near_pos))
        u_neg = _entry("untagged vocal", features=_feat(near_neg))
        no_feat = _entry("not analyzed")
        entries += [u_pos, u_neg, no_feat]

        annotated = learn_instrumental_probs(entries)
        self.assertEqual(annotated, 52)
        self.assertGreaterEqual(u_pos.audio_instr_prob, INSTR_PROB_THRESHOLD)
        self.assertLess(u_neg.audio_instr_prob, 0.2)
        self.assertIsNone(no_feat.audio_instr_prob)
        self.assertTrue(entry_is_instrumental(u_pos))
        self.assertFalse(entry_is_instrumental(u_neg))

    def test_too_few_labels_learns_nothing(self):
        entries, _, _ = self._make_library(n_pos=5, n_neg=5)
        u = _entry("untagged", features=_feat(np.zeros(84)))
        entries.append(u)
        self.assertEqual(learn_instrumental_probs(entries), 0)
        self.assertIsNone(u.audio_instr_prob)


if __name__ == "__main__":
    unittest.main()
