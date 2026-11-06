#!/usr/bin/env python3
"""🧱 Build ALL caches — the pipeline itself: entry, each runner, the exits.

Run:  py -m unittest tests.gui.test_allcache_pipeline -v

`test_allcache_i18n` pins the words. This pins the flow: which question is
asked when, which worker a step starts and how its signals are wired, and what
the three ways out (finished, cancelled, died) leave behind. The window, the
workers and the busy bar are fakes; the mixin's own methods are the real ones.
"""

import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_allcache_pipe_"))

from gui.window import main_allcache as mac
from planner import i18n
from planner.models import MusicEntry


def _entry(name, dance="SA", features=None):
    return MusicEntry(path=Path(f"C:/lib/{dance}/{name}.mp3"), title=name,
                      dance=dance, bpm=51, features=features)


class Sig:
    def __init__(self):
        self.slots = []

    def connect(self, fn):
        self.slots.append(fn)

    def emit(self, *args):
        for fn in list(self.slots):
            fn(*args)


class FakeWorker:
    """Any of the QThread workers: signals, a start() and a cancel()."""
    made = []

    def __init__(self, *args, **kw):
        self.args, self.kw = args, kw
        self.progress, self.report, self.done = Sig(), Sig(), Sig()
        self.cancelled, self.error = Sig(), Sig()
        self.started = self.was_cancelled = False
        FakeWorker.made.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.was_cancelled = True


class FakeBusy:
    made = []

    def __init__(self, parent, caption, cancelable=False):
        self.caption, self.cancelable = caption, cancelable
        self.cancel_requested = Sig()
        self.shown_after = None
        self.progress = []
        self.finished = False
        FakeBusy.made.append(self)

    def show_after(self, ms):
        self.shown_after = ms

    def set_progress(self, *args):
        self.progress.append(args)

    def finish(self):
        self.finished = True


class Box:
    class StandardButton:
        Yes = 1
        No = 0

    def __init__(self, answer=1):
        self.answer = answer
        self.shown = []

    def question(self, parent, title, text, buttons=None):
        self.shown.append(("question", title, text))
        return self.answer

    def information(self, parent, title, text):
        self.shown.append(("information", title, text))

    def warning(self, parent, title, text):
        self.shown.append(("warning", title, text))

    def critical(self, parent, title, text):
        self.shown.append(("critical", title, text))


class Bar:
    def __init__(self):
        self.messages = []

    def showMessage(self, msg):
        self.messages.append(msg)


class Host(mac.AllCacheMixin):
    """The window, reduced to what the pipeline touches."""

    def __init__(self, cache=object(), pool=None):
        self._library = types.SimpleNamespace(cache=cache)
        self._pool = list(pool if pool is not None else [_entry("A"), _entry("B")])
        self._busy = None
        self._allcache = None
        self._emb_store_cache = "stale"
        self._pd_highlights = {"x": 1}
        self._bar = Bar()
        self.calls = []
        self.scope_loaded = True
        self.scope = "local"
        self.plan = ("", ["librosa"], [])

    def statusBar(self):
        return self._bar

    def _ask_index_scope(self, title):
        return self.scope

    def _ensure_scope_loaded(self, scope, then):
        self.calls.append(("ensure", scope))
        return self.scope_loaded

    def _scoped_pool(self, scope, name):
        return self._pool, "the library"

    def _plan_allcache(self, pool):
        return self.plan

    def _run_behind_busy(self, message, fn):
        return fn(lambda _c: None)

    def _refresh_library_status(self, *a, **kw):
        self.calls.append("refresh")

    def _sync_loudness_available(self):
        self.calls.append("sync")

    def _stop_background_analysis(self):
        self.calls.append("stop-analysis")

    def _on_index_progress(self, *a):
        self.calls.append("progress")


class Case(unittest.TestCase):
    def setUp(self):
        FakeWorker.made = []
        FakeBusy.made = []
        self.box = Box()
        for name, value in (("QMessageBox", self.box), ("BusyDialog", FakeBusy),
                            ("AudioAnalyzer", FakeWorker),
                            ("EmbeddingIndexWorker", FakeWorker),
                            ("AudioFpAnalyzer", FakeWorker),
                            ("PdHighlightAnalyzer", FakeWorker),
                            ("LoudnessAnalyzer", FakeWorker),
                            ("SilenceAnalyzer", FakeWorker)):
            patcher = mock.patch.object(mac, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        cleanup = mock.patch.object(mac.planner.music.db_upkeep, "cleanup_orphans",
                                    lambda *a, **kw: None)
        cleanup.start()
        self.addCleanup(cleanup.stop)
        store = mock.patch("planner.music.embeddings.EmbeddingStore")
        self.store = store.start()
        self.addCleanup(store.stop)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        i18n.set_active("en")
        self.win = Host()

    def texts(self, kind):
        return [t for k, _title, t in self.box.shown if k == kind]


class EntryTest(Case):
    def test_without_a_cache_the_question_is_not_asked(self):
        self.win._library.cache = None
        self.win._build_all_caches()
        self.assertEqual(len(self.texts("information")), 1)
        self.assertEqual(self.win.calls, [])

    def test_a_cancelled_scope_question_stops_there(self):
        self.win.scope = None
        self.win._build_all_caches()
        self.assertEqual(self.win.calls, [])

    def test_a_scope_that_has_to_load_first_resumes_later(self):
        self.win.scope_loaded = False
        with mock.patch.object(self.win, "_do_build_all_caches") as build:
            self.win._build_all_caches()
        build.assert_not_called()
        self.assertEqual(self.win.calls, [("ensure", "local")])

    def test_a_loaded_scope_goes_straight_to_the_build(self):
        with mock.patch.object(self.win, "_do_build_all_caches") as build:
            self.win._build_all_caches()
        build.assert_called_once_with("local")


class StartTest(Case):
    def test_no_pool_means_nothing_is_asked(self):
        with mock.patch.object(self.win, "_scoped_pool", return_value=(None, "")):
            self.win._do_build_all_caches("local")
        self.assertEqual(self.box.shown, [])

    def test_a_reason_the_analysis_cannot_run_is_shown_first(self):
        self.win.plan = ("No decoder here", ["librosa"], [])
        self.win._do_build_all_caches("local")
        self.assertEqual(self.texts("warning"), ["No decoder here"])
        self.assertEqual(len(self.texts("question")), 1)

    def test_nothing_to_build_says_so_and_names_what_was_skipped(self):
        self.win.plan = ("", [], ["MERT (not installed)"])
        self.win._do_build_all_caches("local")
        self.assertIn("Nothing can be built", self.texts("information")[0])
        self.assertIn("MERT (not installed)", self.texts("information")[0])
        self.assertIsNone(self.win._allcache)

    def test_a_no_leaves_the_caches_alone(self):
        self.box.answer = Box.StandardButton.No
        self.win._do_build_all_caches("local")
        self.assertIsNone(self.win._allcache)

    def test_a_yes_starts_the_first_step(self):
        self.win.plan = ("", ["audiofp", "librosa"], [])
        with mock.patch.object(self.win, "_allcache_next") as nxt:
            self.win._do_build_all_caches("local")
        nxt.assert_called_once()
        st = self.win._allcache
        self.assertEqual((st["steps"], st["i"], st["notes"]), (["audiofp", "librosa"], 0, []))
        self.assertEqual(st["models"].keys(), {"mert", "chroma"})

    def test_a_failing_orphan_cleanup_does_not_stop_the_run(self):
        with mock.patch.object(self.win, "_run_behind_busy",
                               side_effect=OSError("disk gone")), \
                mock.patch.object(self.win, "_allcache_next") as nxt:
            self.win._do_build_all_caches("local")
        nxt.assert_called_once()


class DispatchTest(Case):
    def start(self, steps):
        self.win._allcache = {"pool": self.win._pool, "label": "the library",
                              "steps": steps, "names": mac._ALLCACHE_NAMES,
                              "models": {"mert": "M", "chroma": "C"}, "i": 0,
                              "notes": [], "reports": {}}

    def test_with_no_run_going_nothing_happens(self):
        self.win._allcache_next()
        self.assertEqual(self.win.calls, [])

    def test_each_step_starts_its_own_runner(self):
        for step, runner in (("librosa", "_allcache_run_librosa"),
                             ("audiofp", "_allcache_run_probe"),
                             ("loudness", "_allcache_run_probe"),
                             ("silences", "_allcache_run_probe"),
                             ("pd", "_allcache_run_probe"),
                             ("mert", "_allcache_run_embedding")):
            with self.subTest(step=step), mock.patch.object(self.win, runner) as run:
                self.start([step])
                self.win._allcache_next()
                run.assert_called_once()

    def test_a_clean_run_reports_success_and_what_ran(self):
        self.start(["audiofp", "librosa"])
        self.win._allcache["i"] = 2
        self.win._allcache_next()
        self.assertIsNone(self.win._allcache)
        self.assertIn("All caches are built for the library.", self.texts("information")[0])
        self.assertIn("Ran: ", self.texts("information")[0])
        self.assertEqual(self.win.statusBar().messages[-1], "All caches built for the library.")
        self.assertIsNone(self.win._emb_store_cache)

    def test_a_run_with_failures_is_a_warning_not_a_success(self):
        self.start(["librosa"])
        self.win._allcache.update(i=1, notes=["librosa: 3 file(s) failed, 0 cached"])
        self.win._allcache_next()
        self.assertEqual(self.texts("information"), [])
        self.assertIn("• librosa: 3 file(s) failed", self.texts("warning")[0])
        self.assertIn("with problems", self.win.statusBar().messages[-1])

    def test_files_gone_from_disk_are_listed_and_not_counted(self):
        self.start(["librosa"])
        self.win._allcache.update(i=1, skips=["librosa: 2 file(s) skipped"])
        self.win._allcache_next()
        self.assertIn("• librosa: 2 file(s) skipped", self.texts("information")[0])


class LibrosaStepTest(Case):
    def test_nothing_left_to_analyse_moves_on(self):
        pool = [_entry("A", features=object())]
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_run_librosa(pool)
        adv.assert_called_once()
        self.assertEqual(FakeWorker.made, [])

    def test_no_cache_moves_on(self):
        self.win._library.cache = None
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_run_librosa([_entry("A")])
        adv.assert_called_once()

    def test_the_analyser_is_started_behind_a_cancellable_bar(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["librosa"], "i": 0}
        self.win._allcache_run_librosa([_entry("A"), _entry("B")])
        worker, busy = FakeWorker.made[0], FakeBusy.made[0]
        self.assertTrue(worker.started)
        self.assertTrue(busy.cancelable)
        self.assertEqual(busy.shown_after, 300)
        self.assertIn("stop-analysis", self.win.calls)
        busy.cancel_requested.emit()
        self.assertTrue(worker.was_cancelled)
        self.assertIn("2", self.win.statusBar().messages[0])

    def test_its_signals_feed_the_pipeline(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["librosa", "x"], "i": 0}
        self.win._allcache_run_librosa([_entry("A")])
        worker = FakeWorker.made[0]
        worker.report.emit({"reasons": {"bad": 3}})
        self.assertEqual(self.win._allcache["reports"]["librosa"], {"reasons": {"bad": 3}})
        with mock.patch.object(self.win, "_allcache_next"):
            worker.done.emit(7, 3)
        self.assertEqual(self.win._allcache["notes"], ["librosa: 3 file(s) failed (bad), 7 cached"])
        worker.progress.emit(1, 2)
        self.assertIn("progress", self.win.calls)

    def test_a_cancel_and_an_error_end_the_run(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["librosa"], "i": 0}
        self.win._allcache_run_librosa([_entry("A")])
        worker = FakeWorker.made[0]
        worker.cancelled.emit(4)
        self.assertIsNone(self.win._allcache)
        self.assertIn("cancelled during librosa", self.win.statusBar().messages[-1])
        self.win._allcache = {}
        worker.error.emit("boom")
        self.assertEqual(self.texts("critical"), ["boom"])


class EmbeddingStepTest(Case):
    def test_no_cache_moves_on(self):
        self.win._library.cache = None
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_run_embedding("M", "MERT", [])
        adv.assert_called_once()

    def test_the_worker_gets_the_store_the_model_and_the_pool(self):
        pool = [_entry("A")]
        self.win._allcache_run_embedding("M", "MERT", pool)
        worker = FakeWorker.made[0]
        self.assertEqual(worker.args[1:3], ("M", pool))
        self.assertTrue(worker.started)
        self.store.assert_called_once_with(self.win._library.cache)

    def test_progress_reaches_the_bar_with_the_brain_icon(self):
        self.win._allcache_run_embedding("M", "MERT", [_entry("A")])
        FakeBusy.made[0].cancel_requested.emit()
        FakeWorker.made[0].progress.emit(1, 5, "song", 30)
        self.assertEqual(FakeBusy.made[0].progress, [(1, 5, "🧠 song", 30)])
        self.assertTrue(FakeWorker.made[0].was_cancelled)

    def test_the_first_error_becomes_the_reason(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["mert", "x"], "i": 0}
        self.win._allcache_run_embedding("M", "MERT", [_entry("A")])
        with mock.patch.object(self.win, "_allcache_next"):
            FakeWorker.made[0].done.emit(2, 5, "model file missing")
        self.assertIn("(model file missing)", self.win._allcache["notes"][0])

    def test_a_clean_finish_has_no_reason_and_the_exits_are_wired(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["mert", "x"], "i": 0}
        self.win._allcache_run_embedding("M", "MERT", [_entry("A")])
        worker = FakeWorker.made[0]
        with mock.patch.object(self.win, "_allcache_next"):
            worker.done.emit(2, 0, "")
        self.assertEqual(self.win._allcache["notes"], [])
        worker.cancelled.emit(1)
        self.assertIsNone(self.win._allcache)
        worker.error.emit("boom")
        self.assertEqual(self.texts("critical"), ["boom"])


class ProbeStepTest(Case):
    def test_a_title_in_two_lists_is_probed_once(self):
        pool = [_entry("A"), _entry("A"), _entry("B")]
        self.win._allcache_run_probe("audiofp", "audio fingerprints", pool)
        self.assertEqual(len(FakeWorker.made[0].args[1]), 2)

    def test_pd_looks_only_at_the_paso_dobles(self):
        pool = [_entry("A"), _entry("P", dance="PD")]
        self.win._allcache_run_probe("pd", "PD highlights", pool)
        worker = FakeWorker.made[0]
        self.assertEqual([p.stem for p in worker.args[1]], ["P"])
        self.assertEqual(worker.kw, {"force": False})

    def test_nothing_to_probe_moves_on(self):
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_run_probe("pd", "PD highlights", [_entry("A")])
        adv.assert_called_once()
        self.assertEqual(FakeWorker.made, [])

    def test_no_cache_moves_on(self):
        self.win._library.cache = None
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_run_probe("audiofp", "x", [_entry("A")])
        adv.assert_called_once()

    def test_loudness_and_silences_need_ffmpeg(self):
        for step, cls_name in (("loudness", "LoudnessAnalyzer"), ("silences", "SilenceAnalyzer")):
            with self.subTest(step=step), \
                    mock.patch.object(mac, "find_ffmpeg", return_value="ffmpeg"), \
                    mock.patch.object(mac, cls_name, FakeWorker):
                FakeWorker.made = []
                self.win._allcache_run_probe(step, step, [_entry("A")])
                self.assertEqual(FakeWorker.made[0].args[2], "ffmpeg")

    def test_ffmpeg_gone_since_planning_fails_every_file_at_once(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["loudness", "x"], "i": 0}
        with mock.patch.object(mac, "find_ffmpeg", return_value=None), \
                mock.patch.object(self.win, "_allcache_next"):
            self.win._allcache_run_probe("loudness", "loudness", [_entry("A"), _entry("B")])
        self.assertEqual(FakeWorker.made, [])
        self.assertIn("2 file(s) failed", self.win._allcache["notes"][0])

    def test_progress_done_and_the_exits_are_wired(self):
        self.win._allcache = {"reports": {}, "notes": [], "steps": ["audiofp", "x"], "i": 0}
        self.win._allcache_run_probe("audiofp", "audio fingerprints", [_entry("A")])
        worker, busy = FakeWorker.made[0], FakeBusy.made[0]
        worker.progress.emit(1, 2, 0, "song", 9)
        self.assertEqual(busy.progress, [(1, 2, "🔗 song", 9)])
        worker.report.emit({"skipped": 1})
        busy.cancel_requested.emit()
        self.assertTrue(worker.was_cancelled)
        with mock.patch.object(self.win, "_allcache_next"):
            worker.done.emit(1, 0)
        self.assertIn("skipped", self.win._allcache["skips"][0])
        worker.cancelled.emit(1)
        self.assertIsNone(self.win._allcache)
        worker.error.emit("boom")
        self.assertEqual(self.texts("critical"), ["boom"])

    def test_pd_marks_make_the_play_cache_forget(self):
        with mock.patch.object(self.win, "_allcache_step_done") as done:
            self.win._allcache_probe_done("pd", "PD highlights", 3, 0)
            self.assertEqual(self.win._pd_highlights, {})
            self.win._pd_highlights["x"] = 1
            self.win._allcache_probe_done("pd", "PD highlights", 0, 0)
            self.win._allcache_probe_done("audiofp", "x", 5, 0)
        self.assertEqual(self.win._pd_highlights, {"x": 1})
        self.assertEqual(done.call_count, 3)


class ReportTest(Case):
    def test_a_report_with_no_run_going_is_dropped(self):
        self.win._allcache_note_report("librosa", {"reasons": {"x": 1}})
        self.assertIsNone(self.win._allcache)

    def test_the_reason_is_the_commonest_one(self):
        self.assertEqual(mac.AllCacheMixin._allcache_reason({}), "")
        self.assertEqual(mac.AllCacheMixin._allcache_reason(None), "")
        self.assertEqual(mac.AllCacheMixin._allcache_reason({"reasons": {"a": 1}}), "a")
        self.assertEqual(mac.AllCacheMixin._allcache_reason({"reasons": {"a": 1, "b": 5}}),
                         "mostly: b")

    def test_a_step_done_with_no_run_going_just_moves_on(self):
        with mock.patch.object(self.win, "_allcache_advance") as adv:
            self.win._allcache_step_done("librosa", 1, 0)
        adv.assert_called_once()


class ExitTest(Case):
    def test_advancing_closes_the_bar_refreshes_and_goes_on(self):
        self.win._busy = FakeBusy(None, "x")
        self.win._allcache = {"i": 0, "steps": ["a"], "reports": {}, "notes": []}
        with mock.patch.object(self.win, "_allcache_next") as nxt:
            self.win._allcache_advance()
        self.assertTrue(self.win._busy.finished)
        self.assertEqual(self.win._allcache["i"], 1)
        self.assertIn("sync", self.win.calls)
        nxt.assert_called_once()
        self.assertIsNone(self.win._emb_store_cache)

    def test_advancing_with_no_run_going_stops_after_the_refresh(self):
        with mock.patch.object(self.win, "_allcache_next") as nxt:
            self.win._allcache_advance()
        nxt.assert_not_called()

    def test_a_cancel_keeps_what_was_cached_and_ends_the_run(self):
        self.win._busy = FakeBusy(None, "x")
        self.win._allcache = {"i": 0}
        self.win._allcache_cancel("loudness", 12)
        self.assertTrue(self.win._busy.finished)
        self.assertIsNone(self.win._allcache)
        self.assertIn("12 done so far", self.win.statusBar().messages[-1])

    def test_a_dead_step_is_shown_and_ends_the_run(self):
        self.win._busy = FakeBusy(None, "x")
        self.win._allcache = {"i": 0}
        self.win._allcache_embedding_error("out of memory")
        self.assertTrue(self.win._busy.finished)
        self.assertIsNone(self.win._allcache)
        self.assertEqual(self.texts("critical"), ["out of memory"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
