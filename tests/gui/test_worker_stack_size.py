#!/usr/bin/env python3
"""Every thread that can reach librosa, numba or torch gets a roomy stack.

Run:  py -m unittest tests.gui.test_worker_stack_size -v

A QThread runs on the platform's default thread stack unless told otherwise,
and on macOS that is 512 KiB. The Full .app crashed half a minute after start
(EXC_BAD_ACCESS in the stack guard, DanceSport-Planner-Player-Full
2026-11-04-011018.ips): the 🔬 background analysis touched a lazily imported
librosa submodule, numba compiled its kernels on that thread, and LLVM's
arm64 code generator ran off the bottom of the 544 KiB stack. Windows (1-2 MiB)
and CPython's own threads (16 MiB on macOS) never got near it.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_worker_stack_"))

from PySide6.QtWidgets import QApplication

from gui import workers
from gui.window import main_allcache

_app = QApplication.instance() or QApplication([])


def _audio_workers():
    cache, lib, fn = mock.Mock(), mock.Mock(), mock.Mock()
    return {
        "AudioAnalyzer": workers.AudioAnalyzer(cache, []),
        "BackgroundAnalyzer": workers.BackgroundAnalyzer(cache, []),
        "LibraryPass": workers.LibraryPass(cache, []),
        "VocalShareAnalyzer": workers.VocalShareAnalyzer(cache, []),
        "EmbeddingIndexWorker": workers.EmbeddingIndexWorker(mock.Mock(), "mert", []),
        "EmbeddingRankWorker": workers.EmbeddingRankWorker(fn),
        "SimilarFromFileWorker": workers.SimilarFromFileWorker(lib, cache, str(Path("x.mp3"))),
        "_BusyWorker": main_allcache._BusyWorker(fn),
    }


class WorkerStackSizeTest(unittest.TestCase):
    def test_audio_workers_get_the_roomy_stack(self):
        for name, worker in _audio_workers().items():
            with self.subTest(worker=name):
                self.assertGreaterEqual(worker.stackSize(), workers.AUDIO_STACK_SIZE)

    def test_roomy_stack_is_at_least_what_cpython_gives_its_threads_on_macos(self):
        self.assertGreaterEqual(workers.AUDIO_STACK_SIZE, 16 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
