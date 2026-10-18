#!/usr/bin/env python3
"""The deep-embedding index run off the UI thread, and the model download in it.

Run:  py -m unittest tests.gui.test_embedding_index_worker -v

The worker is run on the test's own thread (`run()`, not `start()`), so its
signals arrive at once. `build_index` is a fake that downloads, then indexes.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_embed_worker_"))

from PySide6.QtWidgets import QApplication

from gui.workers import EmbeddingIndexWorker
from planner.music import embeddings as ae


class EmbeddingIndexWorkerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_model_download_shows_in_megabytes(self):
        """Marcel: "show it in the progress dialog so he user can note if
        download happens or analysis"."""
        def build(entries, model, store, progress_cb, should_cancel, download_cb):
            for done, total in ((0, 0), (0, 380_000_000), (100_000, 380_000_000),
                                (2_500_000, 380_000_000), (2_600_000, 380_000_000),
                                (380_000_000, 380_000_000)):
                download_cb(done, total)
            progress_cb(1, 1, "a.mp3")
            return 1, 0, None
        worker = EmbeddingIndexWorker(None, ae.MODEL_MERT, [])
        got = []
        worker.progress.connect(lambda *a: got.append(a))
        with mock.patch.object(ae, "build_index", side_effect=build):
            worker.run()
        download = got[:-1]
        self.assertEqual([(d, t) for d, t, _, _ in download], [(0, 380), (2, 380), (380, 380)])
        for _, _, name, eta in download:
            self.assertIn("MERT", name)
            self.assertEqual(eta, -1.0)
        # The ETA is measured from the first title, the download left out.
        self.assertEqual(got[-1], (1, 1, "a.mp3", -1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
