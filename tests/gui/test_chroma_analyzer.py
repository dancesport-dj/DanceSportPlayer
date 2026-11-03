"""The Chromaprint pass: reads only what is missing and stores what fpcalc gave.

Run:  py -m unittest tests.gui.test_chroma_analyzer -v
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_chroma_pass_"))

import numpy as np

import planner.music.db as pdb
from gui import workers
from planner.music.chroma_match import Chroma
from tests.db_support import use_scratch_db


class ChromaAnalyzerTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_chroma_pass_db_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.songs = []
        for i in range(3):
            p = self.dir / f"s{i}.mp3"
            p.write_bytes(bytes([i]) * 5000)
            self.songs.append(p)
        self.cache = pdb.AudioCache()
        self.words = np.arange(50, dtype=np.uint32)

    def run_pass(self, results):
        with mock.patch.object(workers, "fingerprint_file", side_effect=results) as fp:
            w = workers.ChromaAnalyzer(self.cache, self.songs, "fpcalc")
            w.run()
        return fp

    def test_stores_each_result_and_skips_what_it_has(self):
        self.run_pass([Chroma(200.0, self.words)] * 3)
        self.assertEqual(len(self.cache.chroma_keys()), 3)
        fp = self.run_pass([])
        fp.assert_not_called()

    def test_a_failed_track_stays_open(self):
        self.run_pass([Chroma(200.0, self.words), None, Chroma(200.0, self.words)])
        self.assertEqual(len(self.cache.chroma_keys()), 2)
        todo = workers.ChromaAnalyzer(self.cache, self.songs, "fpcalc").todo()
        self.assertEqual(len(todo), 1)


if __name__ == "__main__":
    unittest.main()
