"""Tests for the loop every library-wide analysis run shares
(gui.workers.LibraryPass): what it decodes, what it tallies, what it saves and
what it reports when cancelled or thrown out of.

Each of the four passes used to own a copy of this loop and none of the copies
was tested; run() is called straight on the object here, so no thread starts
and the emissions are collected in order.
"""
import os
import tempfile
import unittest
from pathlib import Path


def _library_pass():
    # Lazy import, same reason as test_pd_analyze: gui.workers pulls in modules
    # that resolve the GUI state files at import time.
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_pass_"))
    from gui.workers import LibraryPass
    return LibraryPass


class _FakeCache:
    def __init__(self):
        self.saves = 0
        self.stored = []

    def save(self):
        self.saves += 1


def _pass_class(**over):
    """A LibraryPass that measures the paths it is given, failing the ones
    whose name starts with "bad"."""
    base = _library_pass()

    class _Pass(base):
        save_every = over.get("save_every", 20)

        def todo(self):
            return [p for p in self.paths if p.name != "cached.mp3"]

        def measure(self, path):
            self.cache.stored.append(path)
            return not path.name.startswith("bad")

    return _Pass


# A failure is only counted when the file is really there: one that is gone
# from disk can never be measured, whatever the pass does (see the skip test
# at the bottom). So the tracks under test have to exist.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_pass_music_"))


def _paths(*names):
    out = []
    for n in names:
        p = _MUSIC / n
        p.touch()
        out.append(p)
    return out


class LibraryPassTest(unittest.TestCase):

    def _run(self, paths, cls=None, cancel_after=None):
        cache = _FakeCache()
        worker = (cls or _pass_class())(cache, paths)
        seen = {"progress": [], "done": [], "cancelled": [], "error": [],
                "report": []}
        for sig in seen:
            getattr(worker, sig).connect(
                lambda *a, _s=sig: seen[_s].append(a))
        if cancel_after is not None:
            worker.progress.connect(
                lambda done, *a: done == cancel_after and worker.cancel())
        worker.run()
        return cache, seen

    def test_only_the_tracks_the_pass_asked_for_are_measured(self):
        cache, seen = self._run(_paths("a.mp3", "cached.mp3", "b.mp3"))
        self.assertEqual([p.name for p in cache.stored], ["a.mp3", "b.mp3"])

    def test_failures_are_counted_not_raised(self):
        cache, seen = self._run(_paths("a.mp3", "bad1.mp3", "bad2.mp3"))
        self.assertEqual(seen["done"], [(1, 2)])
        self.assertEqual(seen["error"], [])

    def test_progress_reports_the_running_error_tally(self):
        cache, seen = self._run(_paths("bad.mp3", "a.mp3"))
        done, total, errors, name, _eta = seen["progress"][0]
        self.assertEqual((done, total, errors, name), (1, 2, 1, "bad.mp3"))
        self.assertEqual(seen["progress"][1][2], 1)

    def test_a_track_that_is_gone_is_skipped_not_failed(self):
        """No rebuild can measure a file that is not there — counting it as a
        failure would make every run over a stale library look broken."""
        gone = Path(r"C:\music\bad_gone.mp3")  # fails AND is not there
        cache, seen = self._run(_paths("a.mp3") + [gone])
        self.assertEqual(seen["done"], [(1, 0)])
        rep = seen["report"][-1][0]
        self.assertEqual((rep["ok"], rep["errors"], rep["skipped"]), (1, 0, 1))
        self.assertEqual(rep["reasons"], {"not on disk any more": 1})

    def test_the_report_names_the_reason_the_pass_gives(self):
        cache, seen = self._run(_paths("a.mp3", "bad1.mp3"))
        rep = seen["report"][-1][0]
        self.assertEqual((rep["ok"], rep["errors"], rep["skipped"]), (1, 1, 0))
        self.assertEqual(list(rep["reasons"]), [_library_pass().fail_hint])

    def test_the_last_track_reports_no_time_left(self):
        # -1 is the "no estimate yet" the busy dialog checks for; anything else
        # is a real estimate, and on the last track there is nothing left.
        cache, seen = self._run(_paths("a.mp3", "b.mp3"))
        eta = seen["progress"][-1][4]
        self.assertIn(eta, (0.0, -1.0))

    def test_cancel_stops_before_the_next_track_and_keeps_results(self):
        cache, seen = self._run(_paths("a.mp3", "b.mp3", "c.mp3"),
                                cancel_after=1)
        self.assertEqual([p.name for p in cache.stored], ["a.mp3"])
        self.assertEqual(seen["cancelled"], [(1,)])
        self.assertEqual(seen["done"], [])
        # a cancelled run still writes what it measured
        self.assertGreaterEqual(cache.saves, 1)

    def test_results_are_saved_on_the_pass_cadence(self):
        cls = _pass_class(save_every=2)
        cache, seen = self._run(_paths(*[f"t{i}.mp3" for i in range(5)]), cls)
        # every 2nd track, plus the final save
        self.assertEqual(cache.saves, 3)

    def test_a_pass_that_throws_reports_instead_of_dying(self):
        base = _library_pass()

        class _Broken(base):
            def todo(self):
                raise RuntimeError("no cache table")

        cache, seen = self._run(_paths("a.mp3"), _Broken)
        self.assertEqual(seen["error"], [("no cache table",)])
        self.assertEqual(seen["done"], [])

    def test_an_empty_pass_still_finishes(self):
        cache, seen = self._run(_paths("cached.mp3"))
        self.assertEqual(seen["done"], [(0, 0)])
        self.assertEqual(seen["progress"], [])


if __name__ == "__main__":
    unittest.main()
