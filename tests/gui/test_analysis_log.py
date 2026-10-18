#!/usr/bin/env python3
"""A run over the library tells the log what it is doing, not only how it ended.

Run:  py -m unittest tests.gui.test_analysis_log -v

Marcel: "when model are trained/files analysed i miss a log which shows what
is going on". Every pass (fingerprints, silence, loudness, vocals, Paso Doble
highlights), the librosa analysis and the embedding index log a start block,
a line every 5 % with the file and the time left, and a closing summary.
The workers run on the test's own thread (`run()`, not `start()`).
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_analysis_log_"))

from PySide6.QtWidgets import QApplication

from gui.workers import (AudioAnalyzer, EmbeddingIndexWorker, LibraryPass,
                         LoudnessAnalyzer, PdHighlightAnalyzer)
from planner.music import embeddings as ae


class _Cache:
    def save(self):
        pass


class _P:
    def __init__(self, name):
        self.name = name

    def exists(self):
        return True


class _Pass(LibraryPass):
    label = "📊 Loudness"

    def __init__(self, n, fail=()):
        super().__init__(_Cache(), [_P(f"t{i}.mp3") for i in range(n)])
        self.fail = set(fail)

    def todo(self):
        return list(self.paths)

    def measure(self, path):
        return path.name not in self.fail


def _lines(cm):
    return [r.getMessage() for r in cm.records]


class AnalysisLogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_pass_logs_its_start_its_progress_and_its_end(self):
        with self.assertLogs("dancesport.workers", level="INFO") as cm:
            _Pass(100, fail={"t7.mp3"}).run()
        lines = _lines(cm)
        self.assertIn("📊 Loudness started", lines[0])
        self.assertIn("files to do: 100", lines[0])
        steps = [m for m in lines if "%" in m.splitlines()[0]]
        # The first file, then every 5 %: enough to see it move, not 100 lines.
        self.assertEqual(len(steps), 21, steps)
        self.assertIn("(1/100)", steps[0])
        self.assertIn("file: t0.mp3", steps[0])
        self.assertIn("50% (50/100)", "\n".join(steps))
        self.assertIn("remaining:", steps[1])
        end = lines[-1]
        self.assertIn("📊 Loudness finished", end)
        self.assertIn("ok: 99", end)
        self.assertIn("errors: 1", end)
        self.assertIn("time:", end)

    def test_a_short_pass_logs_every_file(self):
        with self.assertLogs("dancesport.workers", level="INFO") as cm:
            _Pass(3).run()
        self.assertEqual(sum("%" in m.splitlines()[0] for m in _lines(cm)), 3)

    def test_a_pass_with_nothing_to_do_says_so(self):
        with self.assertLogs("dancesport.workers", level="INFO") as cm:
            _Pass(0).run()
        self.assertIn("files to do: 0", _lines(cm)[0])

    def test_a_cancelled_pass_logs_where_it_stopped(self):
        p = _Pass(40)
        p.progress.connect(lambda i, *a: p.cancel() if i >= 4 else None)
        with self.assertLogs("dancesport.workers", level="INFO") as cm:
            p.run()
        self.assertIn("📊 Loudness stopped", _lines(cm)[-1])
        self.assertIn("ok so far: 4", _lines(cm)[-1])

    def test_every_pass_has_a_name_of_its_own(self):
        self.assertIn("Loudness", LoudnessAnalyzer.label)
        self.assertIn("Paso Doble", PdHighlightAnalyzer.label)

    def test_the_librosa_analysis_logs_too(self):
        class _Lib:
            def analyze_entries(self, entries, progress_cb, should_cancel,
                                force, on_error):
                for i in range(1, 5):
                    progress_cb(i, 4, 0, _P(f"t{i}.mp3"), 3.0)
                return 4, 0, False
        with self.assertLogs("dancesport.workers", level="INFO") as cm:
            AudioAnalyzer(_Lib(), [object()] * 4).run()
        lines = _lines(cm)
        self.assertIn("🎵 Audio features started", lines[0])
        self.assertIn("files: 4", lines[0])
        self.assertIn("(4/4)", lines[-2])
        self.assertIn("ok: 4", lines[-1])

    def test_the_embedding_index_logs_the_download_and_the_titles(self):
        def build(entries, model, store, progress_cb, should_cancel, download_cb):
            for done in (0, 100_000_000, 380_000_000):
                download_cb(done, 380_000_000)
            for i in (1, 10, 20):
                progress_cb(i, 20, f"t{i}.mp3")
            return 20, 0, None
        with mock.patch.object(ae, "build_index", side_effect=build), \
                self.assertLogs("dancesport.workers", level="INFO") as cm:
            EmbeddingIndexWorker(None, ae.MODEL_MERT, [object()] * 20).run()
        text = "\n".join(_lines(cm))
        self.assertIn("🧠 MERT index started", text)
        self.assertIn("Downloading the MERT model\nsize: 380 MB", text)
        self.assertIn("MERT model downloaded", text)
        self.assertIn("50% (10/20)", text)
        self.assertIn("🧠 MERT index finished", _lines(cm)[-1])
        self.assertIn("ok: 20", _lines(cm)[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
