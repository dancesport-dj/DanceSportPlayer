#!/usr/bin/env python3
"""An analysis pass may decode several tracks at once, and still write one.

Run:  py -m unittest tests.gui.test_library_pass_parallel -v

Measured 2026-09-18 on the 3859-track library: one ffmpeg at a time is 30
minutes with fifteen of sixteen cores idle, eight at a time is five. The
expensive half of a pass (`compute`) is cache-free and may therefore run in a
pool; the half that writes (`store`) stays on the pass thread, so SQLite keeps
seeing a single writer and the save cadence, the ETA and the error tally are
unchanged. A pass that overrides neither keeps its old serial `measure`.
"""

import os
import tempfile
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pass_par_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.workers import LibraryPass  # noqa: E402


class _Cache:
    def __init__(self):
        self.saves = 0

    def save(self):
        self.saves += 1


class _Paths(list):
    """Path-like enough for the run loop (it only reads `.name`)."""


class _P:
    def __init__(self, name):
        self.name = name

    def exists(self):
        return True


class _Pass(LibraryPass):
    """Counts how many computes overlap, and in what order stores happen."""
    workers = 4

    def __init__(self, paths, fail=(), delay=0.05):
        super().__init__(_Cache(), paths)
        self.fail = set(fail)
        self.delay = delay
        self.stored = []
        self.store_threads = set()
        self._live = 0
        self._peak = 0
        self._lock = threading.Lock()

    def todo(self):
        return list(self.paths)

    def compute(self, path):
        with self._lock:
            self._live += 1
            self._peak = max(self._peak, self._live)
        time.sleep(self.delay)
        with self._lock:
            self._live -= 1
        return None if path.name in self.fail else f"v:{path.name}"

    def store(self, path, result):
        self.store_threads.add(threading.current_thread().ident)
        self.stored.append((path.name, result))
        return True


def _run(p):
    """Run the pass body synchronously — QThread.run() without a thread."""
    got = {}
    p.report.connect(lambda d: got.update(d))
    p.run()
    return got


class ParallelPassTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _paths(self, n):
        return _Paths(_P(f"t{i}.mp3") for i in range(n))

    def test_the_computes_actually_overlap(self):
        p = _Pass(self._paths(8))
        _run(p)
        self.assertGreater(p._peak, 1)

    def test_it_is_faster_than_one_at_a_time(self):
        p = _Pass(self._paths(8), delay=0.05)
        t = time.monotonic()
        _run(p)
        # 8 × 50 ms serial = 400 ms; with four at a time it cannot need that.
        self.assertLess(time.monotonic() - t, 0.35)

    def test_results_are_stored_in_the_order_of_the_list(self):
        p = _Pass(self._paths(8))
        _run(p)
        self.assertEqual([n for n, _ in p.stored],
                         [f"t{i}.mp3" for i in range(8)])

    def test_every_store_happens_on_one_single_thread(self):
        p = _Pass(self._paths(8))
        _run(p)
        self.assertEqual(len(p.store_threads), 1)

    def test_a_failed_compute_is_never_stored_and_is_counted(self):
        p = _Pass(self._paths(4), fail={"t1.mp3"})
        rep = _run(p)
        self.assertEqual([n for n, _ in p.stored],
                         ["t0.mp3", "t2.mp3", "t3.mp3"])
        self.assertEqual(rep["ok"], 3)
        self.assertEqual(rep["errors"], 1)

    def test_a_cancelled_pass_stops_and_keeps_what_it_had(self):
        p = _Pass(self._paths(40), delay=0.02)
        done = []
        p.cancelled.connect(done.append)
        p.progress.connect(lambda i, *a: p.cancel() if i >= 4 else None)
        p.run()
        self.assertTrue(done, "the pass never reported itself cancelled")
        self.assertLess(len(p.stored), 40)
        self.assertGreaterEqual(p.cache.saves, 1)

    def test_a_cancelled_pass_reports_only_once_its_decodes_ran_out(self):
        # The decodes in the pool are ffmpeg or Demucs runs. `cancelled` is what
        # closes the busy dialog and frees the GUI to start the next pass, and a
        # pass that has returned is what quitting no longer waits for — so
        # neither may happen while one is still decoding.
        class _FirstFast(_Pass):
            def compute(self, path):
                if path.name == "t0.mp3":
                    return f"v:{path.name}"
                return super().compute(path)

        p = _FirstFast(self._paths(8), delay=0.3)
        live_at_cancel = []
        p.cancelled.connect(lambda n: live_at_cancel.append(p._live))
        p.progress.connect(lambda *a: p.cancel())
        p.run()
        self.assertEqual(live_at_cancel, [0])


class SerialPassStaysSerialTest(unittest.TestCase):
    """A pass that overrides only `measure` must behave exactly as before."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    class _Old(LibraryPass):
        def __init__(self, paths):
            super().__init__(_Cache(), paths)
            self.seen = []

        def todo(self):
            return list(self.paths)

        def measure(self, path):
            self.seen.append(path.name)
            return path.name != "t1.mp3"

    def test_measure_is_still_what_runs(self):
        p = self._Old(_Paths(_P(f"t{i}.mp3") for i in range(3)))
        rep = {}
        p.report.connect(lambda d: rep.update(d))
        p.run()
        self.assertEqual(p.seen, ["t0.mp3", "t1.mp3", "t2.mp3"])
        self.assertEqual(rep["ok"], 2)
        self.assertEqual(rep["errors"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
