"""Tests for the stepped audio analysis (`AudioCache.analyze_entries`).

A first run over a big repo analyses tens of thousands of files. Done as one
uninterrupted loop that is where memory went wrong on macOS — ~80 GB and a full
disk on a 50k-file library — so the loop has to close a step every BATCH_FILES
files: commit what is done and release the memory those files used.

What must hold:
  • a checkpoint lands after every BATCH_FILES files, not just at the end
  • the tail of the library is committed too, even when it is a partial step
  • a big library says so, a small one keeps quiet
  • releasing the heap is a no-op that never raises, whatever the platform is
"""
import logging
import unittest
from pathlib import Path

from planner.db import AudioCache, _release_free_heap
from planner.models import MusicEntry


class _StubCache:
    """Just enough cache for the real `analyze_entries` loop to run on.

    No files, no librosa, no database — the loop's own bookkeeping is what is
    under test, so `_analyze_file` returns a marker and `put`/`get` keep it in a
    dict. `_finish_batch` is the real one, and it records where it fired.
    """

    BATCH_FILES = 4
    BIG_LIBRARY = 10

    analyze_entries = AudioCache.analyze_entries
    _finish_batch = AudioCache._finish_batch

    def __init__(self, fail: set = frozenset()):
        self.analyzed = []          # paths, in the order the loop asked for them
        self.checkpoints = []       # how many files were done at each checkpoint
        self._store = {}
        self._fail = fail

    def fingerprint(self, path):
        return f"fp-{path.name}"

    def _analyze_file(self, path, expected_bpm=None):
        if path.name in self._fail:
            raise RuntimeError("simulated decode failure")
        self.analyzed.append(path)
        return f"feat-{path.name}"

    def put(self, path, feat):
        self._store[str(path)] = feat

    def get(self, path):
        return self._store.get(str(path))

    def save(self):
        self.checkpoints.append(len(self.analyzed))


def _entries(n: int) -> list:
    return [MusicEntry(path=Path(f"X:/music/{i:03d} some title (SA 50).mp3"),
                       title=f"{i:03d} some title", dance="SA", bpm=50)
            for i in range(n)]


class SteppedAnalysisTest(unittest.TestCase):

    def test_checkpoints_after_every_step_not_only_at_the_end(self):
        cache = _StubCache()
        cache.analyze_entries(_entries(12))
        # 12 files in steps of 4: after 4, after 8, after 12, plus the final one.
        self.assertEqual(cache.checkpoints, [4, 8, 12, 12])

    def test_a_partial_last_step_is_committed_too(self):
        cache = _StubCache()
        cache.analyze_entries(_entries(10))
        self.assertEqual(cache.checkpoints[-1], 10,
                         "the 2 files after the last full step must be saved")

    def test_every_file_is_analyzed_once_and_kept(self):
        entries = _entries(12)
        ok, errors, cancelled = _StubCache().analyze_entries(entries)
        self.assertEqual((ok, errors, cancelled), (12, 0, False))
        self.assertEqual([e.features for e in entries],
                         [f"feat-{e.path.name}" for e in entries])

    def test_a_failing_file_does_not_break_the_step(self):
        """One bad file is counted and skipped — the rest of the step still lands."""
        bad = "005 some title (SA 50).mp3"
        cache = _StubCache(fail={bad})
        ok, errors, _ = cache.analyze_entries(_entries(12))
        self.assertEqual((ok, errors), (11, 1))
        self.assertEqual(cache.checkpoints[-1], 11)

    def test_a_failing_file_says_which_one_and_why(self):
        """Counting failures is not enough — the build-all report names them."""
        bad = "005 some title (SA 50).mp3"
        cache = _StubCache(fail={bad})
        seen = []
        cache.analyze_entries(_entries(12), on_error=lambda p, exc: seen.append(
            (p.name, str(exc))))
        self.assertEqual(seen, [(bad, "simulated decode failure")])

    def test_a_clean_run_reports_no_reason(self):
        cache = _StubCache()
        seen = []
        cache.analyze_entries(_entries(6), on_error=lambda p, exc: seen.append(p))
        self.assertEqual(seen, [])

    def test_cancelling_saves_what_was_analyzed(self):
        cache = _StubCache()
        entries = _entries(12)
        ok, errors, cancelled = cache.analyze_entries(
            entries, should_cancel=lambda: len(cache.analyzed) >= 6)
        self.assertTrue(cancelled)
        self.assertEqual(ok, 6)
        self.assertTrue(cache.checkpoints, "partial results must be committed")


class StepPlanLogTest(unittest.TestCase):
    """The step plan is worth saying out loud — but only when it matters."""

    def _log(self, n: int) -> str:
        with self.assertLogs("dancesport.db", level=logging.INFO) as cm:
            logging.getLogger("dancesport.db").info("marker")
            _StubCache().analyze_entries(_entries(n))
        return "\n".join(cm.output)

    def test_a_big_library_announces_the_steps(self):
        out = self._log(_StubCache.BIG_LIBRARY + 2)
        self.assertIn("analysing in steps", out)
        self.assertIn(f"step size: {_StubCache.BATCH_FILES}", out)

    def test_a_small_library_says_nothing(self):
        self.assertNotIn("analysing in steps", self._log(_StubCache.BIG_LIBRARY - 2))

    def test_the_real_threshold_is_the_one_the_user_asked_for(self):
        self.assertEqual(AudioCache.BIG_LIBRARY, 5000)
        self.assertLess(AudioCache.BATCH_FILES, AudioCache.BIG_LIBRARY)


class ReleaseFreeHeapTest(unittest.TestCase):

    def test_it_never_raises(self):
        """Best effort by design: a missing symbol may only cost us the release."""
        _release_free_heap()
        _release_free_heap()


if __name__ == "__main__":
    unittest.main(verbosity=2)
