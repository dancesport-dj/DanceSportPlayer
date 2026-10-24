#!/usr/bin/env python3
"""The index builds behind Settings: scope, pools and the two workers' outcomes.

Run:  py -m unittest tests.gui.window.test_main_embed -v

`EmbeddingIndexMixin` asks which library an index covers, resolves that to a
deduplicated pool, then hands it to the librosa analyzer or the MERT / Chroma
worker and reports how the run ended. The workers and the busy dialog are
replaced by mocks; what is checked is the window's side of each branch.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

import gui.window.main_embed as me
from gui.window.main_embed import EmbeddingIndexMixin
from planner.music import embeddings as ae
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No


def _entry(name, features=None):
    return SimpleNamespace(path=Path(f"C:/m/{name}.mp3"), features=features)


def _lib(*entries):
    return SimpleNamespace(entries=list(entries))


class _Host(QMainWindow, EmbeddingIndexMixin):
    def __init__(self, lib=None, global_lib=None, cache=None):
        super().__init__()
        self._library = SimpleNamespace(lib=lib, global_lib=global_lib, cache=cache)
        self._busy = None
        self.refreshed = 0
        self.global_loads = []
        self.unavailable = ""

    def _refresh_library_status(self):
        self.refreshed += 1

    def _ensure_global_lib(self, then_build=None):
        self.global_loads.append(then_build)

    def _librosa_unavailable(self, entries):
        return self.unavailable


class _Dialogs:
    """Records every QMessageBox static call; question() answers `answer`."""

    def __init__(self, test, answer=_YES):
        self.calls = []
        for kind in ("information", "warning", "critical", "question"):
            patcher = mock.patch.object(QMessageBox, kind, side_effect=self._record(kind, answer))
            patcher.start()
            test.addCleanup(patcher.stop)

    def _record(self, kind, answer):
        def call(parent, title, text, *args):
            self.calls.append((kind, title, text))
            return answer if kind == "question" else QMessageBox.StandardButton.Ok
        return call

    def kinds(self):
        return [c[0] for c in self.calls]


class _TestBase(unittest.TestCase):

    def host(self, **kw):
        win = _Host(**kw)
        self.addCleanup(reap_widget, win)
        return win

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found


class ScopedPoolTest(_TestBase):

    def test_global_and_local_hand_back_their_own_entries(self):
        a, b = _entry("a"), _entry("b")
        win = self.host(lib=_lib(b), global_lib=_lib(a))
        self.assertEqual(win._scoped_pool("global", "X"), ([a], "the whole repository"))
        self.assertEqual(win._scoped_pool("local", "X"), ([b], "the favorites library"))

    def test_both_is_the_union_by_path_repository_first(self):
        a, b, a_again = _entry("a"), _entry("b"), _entry("a")
        win = self.host(lib=_lib(a_again, b), global_lib=_lib(a))
        pool, label = win._embedding_pool("both", "X")
        self.assertEqual(pool, [a, b])
        self.assertIs(pool[0], a)
        self.assertEqual(label, "the whole repository + favorites library")

    def test_a_scope_whose_library_is_not_loaded_says_so(self):
        dialogs = _Dialogs(self)
        win = self.host(lib=_lib(), global_lib=None)
        self.assertEqual(win._scoped_pool("global", "X"), (None, ""))
        self.assertEqual(win._scoped_pool("local", "X"), (None, ""))
        self.assertEqual(dialogs.kinds(), ["information", "information"])
        self.assertIn("whole-repository", dialogs.calls[0][2])
        self.assertIn("Favorites", dialogs.calls[1][2])


class ScopeLoadingTest(_TestBase):

    def test_a_repository_scope_without_the_repository_loads_it_and_defers(self):
        win = self.host(global_lib=_lib())
        resume = mock.Mock()
        self.assertFalse(win._ensure_scope_loaded("both", resume))
        self.assertEqual(win.global_loads, [resume])

    def test_a_loaded_or_local_scope_proceeds_at_once(self):
        win = self.host(global_lib=_lib(_entry("a")))
        self.assertTrue(win._ensure_scope_loaded("global", mock.Mock()))
        self.assertTrue(self.host()._ensure_scope_loaded("local", mock.Mock()))
        self.assertEqual(win.global_loads, [])


class AskScopeTest(_TestBase):

    def _answer(self, label):
        class Box(QMessageBox):
            def exec(self):
                return 0

            def clickedButton(self):
                return next((b for b in self.buttons() if label and label in b.text()), None)

        self.patch(me, "QMessageBox", new=Box)

    def test_each_button_names_its_scope(self):
        for label, scope in (("Whole repository", "global"),
                             ("Favorites library", "local"), ("Both", "both")):
            with self.subTest(label):
                self._answer(label)
                self.assertEqual(self.host()._ask_index_scope("T"), scope)

    def test_cancel_is_none(self):
        self._answer(None)
        self.assertIsNone(self.host()._ask_index_scope("T"))


class LibrosaAnalysisTest(_TestBase):

    def setUp(self):
        self.busy = self.patch(me, "BusyDialog")
        self.analyzer = self.patch(me, "AudioAnalyzer")

    def test_without_a_cache_nothing_starts(self):
        dialogs = _Dialogs(self)
        self.host()._run_librosa_analysis([_entry("a")], "S")
        self.assertEqual(dialogs.kinds(), ["information"])
        self.analyzer.assert_not_called()

    def test_everything_analyzed_already_is_reported(self):
        dialogs = _Dialogs(self)
        self.host(cache=object())._run_librosa_analysis([_entry("a", features=[1])], "S")
        self.assertIn("already analyzed", dialogs.calls[0][2])
        self.analyzer.assert_not_called()

    def test_a_missing_librosa_warns(self):
        dialogs = _Dialogs(self)
        win = self.host(cache=object())
        win.unavailable = "librosa is missing"
        win._run_librosa_analysis([_entry("a")], "S")
        self.assertEqual(dialogs.calls, [("warning", "Audio analysis unavailable",
                                          "librosa is missing")])

    def test_declining_the_run_starts_nothing(self):
        _Dialogs(self, answer=_NO)
        self.host(cache=object())._run_librosa_analysis([_entry("a")], "S")
        self.analyzer.assert_not_called()

    def test_a_confirmed_run_starts_the_analyzer_with_its_signals_wired(self):
        dialogs = _Dialogs(self)
        cache = object()
        entries = [_entry("a"), _entry("b", features=[1])]
        win = self.host(cache=cache)
        win._run_librosa_analysis(entries, "S")
        self.assertIn("1 of 2", dialogs.calls[0][2])
        self.analyzer.assert_called_once_with(cache, entries, win)
        worker = self.analyzer.return_value
        worker.start.assert_called_once()
        self.busy.return_value.cancel_requested.connect.assert_called_once_with(worker.cancel)
        worker.done.connect.assert_called_once_with(win._on_index_done)
        worker.cancelled.connect.assert_called_once_with(win._on_index_cancelled)
        worker.error.connect.assert_called_once_with(win._on_index_error)
        self.assertEqual(win._index_scope_label, "S")


class LibrosaOutcomeTest(_TestBase):

    def test_progress_moves_the_busy_dialog_and_the_status_bar(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_index_progress(3, 10, 2, "a.mp3", 65.0)
        win._busy.set_progress.assert_called_once_with(3, 10, "🔬 a.mp3", 65.0)
        msg = win.statusBar().currentMessage()
        self.assertIn("3/10", msg)
        self.assertIn("left", msg)
        self.assertIn("2 errors", msg)

    def test_an_unknown_eta_shows_no_time_left(self):
        win = self.host()
        win._on_index_progress(1, 4, 0, "a", -1)
        self.assertNotIn("left", win.statusBar().currentMessage())

    def test_done_finishes_refreshes_and_reports(self):
        dialogs = _Dialogs(self)
        win = self.host()
        win._busy = mock.Mock()
        win._index_scope_label = "the favorites library"
        win._on_index_done(5, 1)
        win._busy.finish.assert_called_once()
        self.assertEqual(win.refreshed, 1)
        self.assertIn("5 files analyzed, 1 errors", win.statusBar().currentMessage())
        self.assertIn("in the favorites library (1 errors)", dialogs.calls[0][2])

    def test_cancelled_keeps_the_count_so_far(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_index_cancelled(7)
        win._busy.finish.assert_called_once()
        self.assertEqual(win.refreshed, 1)
        self.assertIn("7 files analyzed so far", win.statusBar().currentMessage())

    def test_an_error_closes_the_dialog_and_says_why(self):
        """A crashed analyzer left the BusyDialog up for good (review G1)."""
        dialogs = _Dialogs(self)
        win = self.host()
        win._busy = mock.Mock()
        win._on_index_error("database is locked")
        win._busy.finish.assert_called_once()
        self.assertEqual(win.refreshed, 1)
        self.assertEqual(dialogs.kinds(), ["critical"])
        self.assertIn("database is locked", dialogs.calls[0][2])


class EmbeddingBuildTest(_TestBase):

    def setUp(self):
        self.busy = self.patch(me, "BusyDialog")
        self.worker = self.patch(me, "EmbeddingIndexWorker")
        self.store = self.patch(ae, "EmbeddingStore")
        self.patch(ae, "mert_available", return_value=True)
        self.patch(ae, "chroma_available", return_value=True)

    def test_the_model_names(self):
        self.assertEqual(_Host._embed_model_name(ae.MODEL_CHROMA), "Chroma")
        self.assertEqual(_Host._embed_model_name("anything else"), "MERT")

    def test_a_model_that_is_not_installed_shows_its_install_hint(self):
        dialogs = _Dialogs(self)
        self.patch(ae, "chroma_available", return_value=False)
        self.host(cache=object())._build_embedding_index({}, ae.MODEL_CHROMA)
        self.assertEqual(dialogs.calls, [("information", "Chroma not installed",
                                          ae.install_hint(ae.MODEL_CHROMA))])

    def test_without_a_cache_no_scope_is_asked(self):
        dialogs = _Dialogs(self)
        win = self.host()
        ask = self.patch(_Host, "_ask_index_scope")
        win._build_embedding_index({}, "mert")
        ask.assert_not_called()
        self.assertIn("cache not ready", dialogs.calls[0][2])

    def test_a_cancelled_scope_builds_nothing(self):
        win = self.host(cache=object())
        self.patch(_Host, "_ask_index_scope", return_value=None)
        build = self.patch(_Host, "_do_build_embedding_index")
        win._build_embedding_index({}, "mert")
        build.assert_not_called()

    def test_a_scope_still_loading_resumes_the_build_when_loaded(self):
        win = self.host(cache=object(), global_lib=None)
        self.patch(_Host, "_ask_index_scope", return_value="global")
        build = self.patch(_Host, "_do_build_embedding_index")
        win._build_embedding_index({"k": 1}, "mert")
        build.assert_not_called()
        win.global_loads[0]()
        build.assert_called_once_with({"k": 1}, "mert", "global")

    def test_a_loaded_scope_builds_right_away(self):
        win = self.host(cache=object(), lib=_lib(_entry("a")))
        self.patch(_Host, "_ask_index_scope", return_value="local")
        build = self.patch(_Host, "_do_build_embedding_index")
        win._build_embedding_index({}, "mert")
        build.assert_called_once_with({}, "mert", "local")

    def test_declining_starts_no_worker(self):
        _Dialogs(self, answer=_NO)
        self.host(cache=object(), lib=_lib(_entry("a")))._do_build_embedding_index(
            {}, "mert", "local")
        self.worker.assert_not_called()

    def test_an_unloaded_pool_starts_no_worker(self):
        _Dialogs(self)
        self.host(cache=object())._do_build_embedding_index({}, "mert", "local")
        self.worker.assert_not_called()

    def test_a_confirmed_build_runs_the_worker_and_routes_its_outcomes(self):
        dialogs = _Dialogs(self)
        cache = object()
        pool = [_entry("a"), _entry("b")]
        win = self.host(cache=cache, lib=_lib(*pool))
        outcomes = {}
        for name in ("_on_embedding_index_done", "_on_embedding_index_cancelled"):
            outcomes[name] = self.patch(_Host, name)
        win._do_build_embedding_index({}, ae.MODEL_CHROMA, "local")
        self.assertIn("over 2 tracks from the favorites library", dialogs.calls[0][2])
        self.assertIn("melody/harmony", dialogs.calls[0][2])
        self.store.assert_called_once_with(cache)
        self.worker.assert_called_once_with(self.store.return_value, ae.MODEL_CHROMA, pool, win)
        worker = self.worker.return_value
        worker.start.assert_called_once()
        worker.error.connect.assert_called_once_with(win._on_embedding_index_error)

        worker.done.connect.call_args.args[0](4, 1, "boom")
        outcomes["_on_embedding_index_done"].assert_called_once_with("Chroma", 4, 1, "boom")
        worker.cancelled.connect.call_args.args[0](2)
        outcomes["_on_embedding_index_cancelled"].assert_called_once_with("Chroma", 2)
        worker.progress.connect.call_args.args[0](1, 2, "a", 3.0)
        self.busy.return_value.set_progress.assert_called_once_with(1, 2, "🧠 a", 3.0)


class EmbeddingOutcomeTest(_TestBase):

    def host_busy(self):
        win = self.host()
        win._busy = mock.Mock()
        win._emb_store_cache = object()
        return win

    def test_everything_failing_is_an_error_with_the_first_cause(self):
        dialogs = _Dialogs(self)
        win = self.host_busy()
        win._on_embedding_index_done("MERT", 0, 3, "no model")
        self.assertEqual(dialogs.kinds(), ["critical"])
        self.assertIn("All 3 file(s) failed", dialogs.calls[0][2])
        self.assertIn("no model", dialogs.calls[0][2])
        self.assertIn("failed", win.statusBar().currentMessage())
        self.assertIsNone(win._emb_store_cache)

    def test_some_failures_are_counted(self):
        dialogs = _Dialogs(self)
        win = self.host_busy()
        win._on_embedding_index_done("MERT", 4, 1, "x")
        self.assertIn("4 embedded, 1 failed", win.statusBar().currentMessage())
        self.assertIn("(1 failed", dialogs.calls[0][2])

    def test_a_clean_run_is_ready(self):
        dialogs = _Dialogs(self)
        win = self.host_busy()
        win._on_embedding_index_done("Chroma", 4, 0, "")
        win._busy.finish.assert_called_once()
        self.assertEqual(win.refreshed, 1)
        self.assertEqual(dialogs.calls[0][1], "Chroma index ready")
        self.assertIn("Embedded 4 track(s).", dialogs.calls[0][2])

    def test_cancelled_drops_the_stale_store_and_says_what_is_kept(self):
        win = self.host_busy()
        win._on_embedding_index_cancelled("MERT", 2)
        self.assertIsNone(win._emb_store_cache)
        self.assertEqual(win.refreshed, 1)
        self.assertIn("2 embedded so far", win.statusBar().currentMessage())

    def test_a_worker_error_is_shown(self):
        dialogs = _Dialogs(self)
        win = self.host_busy()
        win._on_embedding_index_error("disk full")
        win._busy.finish.assert_called_once()
        self.assertEqual(dialogs.calls, [("critical", "Embedding index error", "disk full")])


class EmbeddingStoreTest(_TestBase):

    def test_no_cache_no_store(self):
        self.assertIsNone(self.host()._embedding_store())

    def test_the_store_is_made_once(self):
        store = self.patch(ae, "EmbeddingStore")
        win = self.host(cache=object())
        self.assertIs(win._embedding_store(), store.return_value)
        self.assertIs(win._embedding_store(), store.return_value)
        store.assert_called_once()

    def test_a_store_that_cannot_open_is_none(self):
        self.patch(ae, "EmbeddingStore", side_effect=RuntimeError("locked"))
        self.assertIsNone(self.host(cache=object())._embedding_store())


if __name__ == "__main__":
    unittest.main(verbosity=2)
