#!/usr/bin/env python3
"""A reference compare stops when its dialog lets it go.

Run:  py -m unittest tests.gui.test_reference_clean_cancel -v

The compare has no parent: closing the duplicate dialog mid-run hands it to
`adopt_running`, which cancels what it can. The worker had no `cancel`, so it
went on fingerprinting every track — each one a full read of the file on the
first run — for a window nobody had open any more.
"""

import os
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from gui.workers import ReferenceCleanWorker, adopt_running  # noqa: E402


class _SlowCache:
    """The first fingerprint waits until the test has let the worker go."""

    def __init__(self):
        self.calls = 0
        self.entered = threading.Event()
        self.release = threading.Event()

    def fingerprint(self, path):
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            self.release.wait(5)
        return f"fp-{path.name}"


class ReferenceCleanCancelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_an_adopted_compare_stops_fingerprinting(self):
        cache = _SlowCache()
        tracks = [Path(f"C:/t/{n} (LW 29).mp3") for n in range(20)]
        worker = ReferenceCleanWorker("missing-ref.m3u", tracks, cache,
                                      lambda p: [])
        done = []
        worker.done.connect(done.append)
        worker.start()
        self.assertTrue(cache.entered.wait(5))
        adopt_running(worker)           # what the closing dialog does
        cache.release.set()
        self.assertTrue(worker.wait(5000))
        self.assertEqual(cache.calls, 1)
        self.assertEqual(done, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
