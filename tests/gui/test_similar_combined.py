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

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner import embeddings as ae  # noqa: E402
from tests.planner import test_sound_alike  # noqa: E402


class _Store:
    def __init__(self, chroma):
        self.chroma = chroma

    def recorded(self, path, model):
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
        # The dialog ranks by "combined" while it is built, so its chroma store
        # has to be there before.
        with mock.patch.object(ae, "EmbeddingStore",
                               lambda _cache: _Store(fixture.chroma)):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
