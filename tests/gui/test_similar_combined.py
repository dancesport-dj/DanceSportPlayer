#!/usr/bin/env python3
"""The "Similar to" dialog ranks by all three methods at once.

Run:  py -m unittest tests.gui.test_similar_combined -v

Marcel: add a method all or combined which lists the combined Mittelwert
values, so I do not have to click through the three method lists. It is the
event plan's `SoundAlike`: timbre (Gaussian/KL), groove (librosa) and melody
(chroma) each rank a title within the dance, the mean decides, and the
tooltip names all three.
"""

import os
import unittest
from unittest import mock

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.dialogs.similar_dialog import SimilarTracksDialog
from planner.music import embeddings as ae
from tests.planner import test_sound_alike


class _Store:
    def __init__(self, chroma, mert=None):
        self.chroma = chroma
        self.mert = mert or {}

    def recorded(self, path, model):
        if model == ae.MODEL_MERT:
            return self.mert.get(path)
        return self.chroma.get(path) if model == ae.MODEL_CHROMA else None


class SimilarCombinedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        fixture = test_sound_alike.SoundAlikeTest(
            "test_the_title_alike_in_all_three_views_comes_first")
        fixture.setUp()
        self.f = fixture
        rng = np.random.default_rng(3)
        self.mert = {e.path: rng.normal(size=768) for e in fixture.lib.entries}
        # The dialog ranks by "combined" while it is built, so its chroma store
        # has to be there before.
        with mock.patch.object(ae, "EmbeddingStore",
                               lambda _cache: _Store(fixture.chroma, self.mert)):
            self.dlg = SimilarTracksDialog(fixture.anchor, [], lib=fixture.lib,
                                           cache=mock.Mock())
        self.addCleanup(self.dlg.deleteLater)

    def choose(self, key):
        combo = self.dlg._method_combo
        combo.setCurrentIndex(combo.findData(key))

    def test_combined_is_a_method(self):
        self.assertGreaterEqual(self.dlg._method_combo.findData("combined"), 0)

    def test_it_lists_the_mean_of_the_three_views(self):
        self.choose("combined")
        first = self.dlg._row_entries[0]
        self.assertIs(first, self.f.alike)
        mean = self.f.sound.agreement(self.f.anchor, self.f.alike)
        self.assertEqual(self.dlg._table.item(0, 1).text(), f"{mean * 100:.2f}%")
        tip = self.dlg._table.item(0, 3).toolTip()
        for view in ("timbre top", "groove top", "melody top"):
            self.assertIn(view, tip)

    def test_combined_is_the_default(self):
        self.assertEqual(self.dlg._method_combo.currentData(), "combined")
        self.assertIs(self.dlg._row_entries[0], self.f.alike)

    def test_a_dropped_file_ranks_combined_too(self):
        others = [e for e in self.f.lib.entries
                  if e is not self.f.anchor and e is not self.f.alike]
        self.dlg._on_worker_done(self.f.anchor, [(0.99, others[0])])
        self.assertIs(self.dlg._row_entries[0], self.f.alike)

    def test_the_other_methods_still_rank_alone(self):
        self.choose("combined")
        self.choose("gaussian_kl")
        self.assertNotIn("groove top", self.dlg._table.item(0, 3).toolTip())

    def test_combined_mert_is_a_method(self):
        self.assertGreaterEqual(self.dlg._method_combo.findData("combined_mert"), 0)

    def test_combined_mert_adds_mert_to_the_mean(self):
        self.choose("combined_mert")
        tip = self.dlg._table.item(0, 3).toolTip()
        for view in ("timbre top", "groove top", "melody top", "MERT top"):
            self.assertIn(view, tip)

    def test_plain_combined_leaves_mert_out(self):
        self.choose("combined_mert")
        self.choose("combined")
        self.assertNotIn("MERT top", self.dlg._table.item(0, 3).toolTip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
