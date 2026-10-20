#!/usr/bin/env python3
"""The libraries behind the window: ≈ search, the global repository, ⚙ Settings.

Run:  py -m unittest tests.gui.window.test_main_global -v

`GlobalIndexMixin` runs the ≈ similar search for a dropped file, loads the whole
repository from the warm cache or a full scan, builds the librosa index over a
chosen scope, applies what ⚙ Settings changed and runs the maintenance jobs
next to it (database cleanup, PD marks export/import, backup restore, playlist
re-learning). Workers, busy dialogs and file pickers are replaced by mocks;
what is checked is the window's side of each outcome.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest import mock

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox

import planner.config
import planner.music.db
import planner.music.db_upkeep
import planner.music.scan_caches
import planner.playlist.m3u
from gui.window import main_global as mg
from gui.window.main_global import GlobalIndexMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No


def _entry(name, features=None):
    return SimpleNamespace(path=Path(f"C:/m/{name}.mp3"), features=features)


def _lib(*entries):
    return mock.Mock(entries=list(entries))


def _running(flag=True):
    return mock.Mock(**{"isRunning.return_value": flag})


class _Host(QMainWindow, GlobalIndexMixin):
    def __init__(self, lib=None, global_lib=None, cache=None, settings=None):
        super().__init__()
        self._library = SimpleNamespace(lib=lib, global_lib=global_lib, cache=cache,
                                        cache_loader=None, global_loader=None,
                                        load_bar=None, preloader=None, preload_busy=None)
        self._settings = dict(settings or {})
        self._busy = None
        self._sim_worker = None
        self._cfg = mock.Mock()
        self.refreshed = 0
        self.analyses = []

    def _refresh_library_status(self, enable_generate=False):
        self.refreshed += 1

    def _run_librosa_analysis(self, entries, label):
        self.analyses.append((entries, label))


class _Dialogs:
    """Records every QMessageBox static call; question() answers `answer`."""

    def __init__(self, test, answer=_YES):
        self.calls = []
        self.answer = answer
        for kind in ("information", "warning", "critical", "question"):
            patcher = mock.patch.object(QMessageBox, kind, side_effect=self._record(kind))
            patcher.start()
            test.addCleanup(patcher.stop)

    def _record(self, kind):
        def call(parent, title, text, *args):
            self.calls.append((kind, title, text))
            return self.answer if kind == "question" else QMessageBox.StandardButton.Ok
        return call

    def kinds(self):
        return [c[0] for c in self.calls]

    def text(self):
        return self.calls[-1][2]


class _TestBase(unittest.TestCase):

    def setUp(self):
        self.dialogs = _Dialogs(self)
        self.busy = self.patch(mg, "BusyDialog")

    def host(self, **kw):
        win = _Host(**kw)
        self.addCleanup(reap_widget, win)
        return win

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found

    def folder(self):
        return tempfile.mkdtemp(prefix="dp_main_global_")

    @staticmethod
    def status(win):
        return win.statusBar().currentMessage()


class LibraryErrorTest(_TestBase):

    def test_the_splash_goes_and_the_error_is_shown(self):
        icon = self.patch(mg, "apply_taskbar_icon")
        win = self.host()
        win._loading_dlg = mock.Mock()
        win._on_library_error("disk gone")
        win._loading_dlg.accept.assert_called_once()
        icon.assert_called_once_with(win)
        win._cfg.set_library_status.assert_called_once_with(
            "Error loading library:\ndisk gone")
        self.assertEqual(self.status(win), "Library error: disk gone")
        self.assertEqual(self.dialogs.kinds(), ["critical"])


class FileDropTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.patch(mg, "HAS_LIBROSA", new=True)

    def drop_host(self, **kw):
        win = self.host(lib=_lib(), cache=mock.Mock(), **kw)
        self.start = self.patch(win, "_start_similar_worker")
        self.ensure = self.patch(win, "_ensure_global_lib")
        return win

    def test_nothing_happens_before_the_library_is_loaded(self):
        win = self.host(lib=_lib(), cache=None)
        start = self.patch(win, "_start_similar_worker")
        win._on_file_dropped("C:/a.mp3")
        start.assert_not_called()

    def test_without_librosa_it_says_what_to_install(self):
        self.patch(mg, "HAS_LIBROSA", new=False)
        win = self.drop_host()
        win._on_file_dropped("C:/a.mp3")
        self.start.assert_not_called()
        self.assertIn("librosa + ffmpeg", self.dialogs.text())

    def test_a_search_already_running_is_left_alone(self):
        win = self.drop_host()
        win._sim_worker = _running()
        win._on_file_dropped("C:/a.mp3")
        self.start.assert_not_called()

    def test_the_favorites_library_is_searched_by_default(self):
        win = self.drop_host()
        win._on_file_dropped("C:/a.mp3")
        self.start.assert_called_once_with("C:/a.mp3", win._library.lib)

    def test_global_search_uses_the_repository_or_loads_it_first(self):
        win = self.drop_host(settings={"global_search": True})
        win._on_file_dropped("C:/a.mp3")
        self.ensure.assert_called_once_with(then_drop="C:/a.mp3")
        win._library.global_lib = _lib()
        win._on_file_dropped("C:/b.mp3")
        self.start.assert_called_once_with("C:/b.mp3", win._library.global_lib)


class SimilarSearchTest(_TestBase):

    def test_the_worker_starts_on_the_dropped_file(self):
        make = self.patch(mg, "SimilarFromFileWorker")
        lib = _lib()
        win = self.host(lib=lib, cache=mock.Mock())
        win._start_similar_worker("C:/m/song.mp3", lib)
        make.assert_called_once_with(lib, win._library.cache, "C:/m/song.mp3", n=100,
                                     min_display=0.5, parent=win)
        worker = make.return_value
        worker.done.connect.assert_called_once_with(win._on_similar_ready)
        worker.error.connect.assert_called_once_with(win._on_similar_error)
        worker.start.assert_called_once()
        self.busy.return_value.show_after.assert_called_once_with(500)
        self.assertEqual(self.status(win), "Analyzing song.mp3 …")

    def no_result_text(self, lib, is_global=False, analyzer=None):
        win = self.host(lib=lib, global_lib=lib if is_global else None)
        win._busy = mock.Mock()
        if analyzer is not None:
            win._analyzer = analyzer
        win._on_similar_ready(SimpleNamespace(title="Src"), [])
        win._busy.finish.assert_called_once()
        self.assertEqual(self.status(win), "No similar tracks found.")
        return self.dialogs.text()

    def test_an_empty_answer_explains_why(self):
        text = self.no_result_text(_lib(_entry("a")), is_global=True)
        self.assertIn("the whole repository", text)
        self.assertIn("repository isn't analyzed yet", text)
        text = self.no_result_text(_lib(_entry("a")))
        self.assertIn("the favorites library", text)
        self.assertIn("run 'Analyze Audio' first", text)
        half = _lib(_entry("a", features=[1.0]), _entry("b"))
        self.assertIn("still running", self.no_result_text(half, analyzer=_running()))
        text = self.no_result_text(half, analyzer=_running(False))
        self.assertIn("Only 1 of 2 tracks", text)
        self.assertNotIn("still running", text)
        self.assertIn("no close match", self.no_result_text(_lib(_entry("a", features=[1.0]))))

    def test_results_open_the_similar_tracks_dialog(self):
        dialog = self.patch(mg, "SimilarTracksDialog")
        lib = _lib()
        win = self.host(lib=lib)
        win._prehear, win._prehear_seek = mock.Mock(), mock.Mock()
        win.current_wishlist_paths = lambda: {"C:/w.mp3"}
        win._sim_lib = lib
        source = SimpleNamespace(title="Src")
        win._on_similar_ready(source, [("hit", 0.9)])
        self.assertEqual(self.status(win), "Found 1 similar to Src (the favorites library)")
        kw = dialog.call_args.kwargs
        self.assertEqual((kw["lib"], kw["is_global"], kw["wishlist_paths"]),
                         (lib, False, {"C:/w.mp3"}))
        self.assertIs(kw["seek_cb"], win._prehear_seek, "🎧 seeks what it pre-listens")
        dialog.return_value.exec.assert_called_once()

    def test_a_failed_search_is_reported(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_similar_error("no ffmpeg")
        win._busy.finish.assert_called_once()
        self.assertEqual(self.status(win), "Similar-track analysis failed.")
        self.assertEqual(self.dialogs.calls, [("critical", "Analysis Error", "no ffmpeg")])


class GlobalLibraryTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.count = self.patch(planner.music.scan_caches, "global_index_count", return_value=0)
        self.cache_loader = self.patch(mg, "GlobalCacheLoader")
        self.scanner = self.patch(mg, "GlobalLibraryLoader")

    def test_no_repository_folder_says_where_to_set_it(self):
        win = self.host(settings={"global_dir": "C:/does/not/exist"})
        win._ensure_global_lib(then_build=lambda: None)
        self.assertIsNone(win._pending_after_global)
        self.assertIn("⚙ Settings", self.dialogs.text())
        win._start_global_scan("C:/a.mp3")
        self.scanner.assert_not_called()

    def test_a_built_index_loads_from_the_warm_cache(self):
        self.count.return_value = 3
        win = self.host(cache=mock.Mock(), settings={"global_dir": self.folder()})
        win._ensure_global_lib(then_drop="C:/a.mp3")
        self.assertEqual(win._pending_drop, "C:/a.mp3")
        loader = self.cache_loader.return_value
        loader.done.connect.assert_called_once_with(win._on_global_cache_loaded)
        loader.start.assert_called_once()
        win._library.cache_loader = _running()
        win._ensure_global_lib()
        self.cache_loader.assert_called_once()

    def test_a_cold_cache_walks_the_repository(self):
        gdir = self.folder()
        win = self.host(cache=mock.Mock(), settings={"global_dir": gdir})
        win._ensure_global_lib(then_drop="C:/a.mp3")
        self.scanner.assert_called_once_with(win._library.cache, gdir, win,
                                             share_from=win._library.lib)
        scan = self.scanner.return_value
        self.busy.return_value.cancel_requested.connect.assert_called_once_with(scan.cancel)
        scan.done.connect.assert_called_once_with(win._on_global_ready)
        scan.cancelled.connect.assert_called_once_with(win._on_global_cancelled)
        scan.start.assert_called_once()
        win._library.global_loader = _running()
        win._start_global_scan("C:/b.mp3")
        self.assertEqual(win._pending_drop, "C:/b.mp3")
        self.scanner.assert_called_once()

    def test_an_empty_cache_falls_back_to_a_scan(self):
        win = self.host()
        win._busy = mock.Mock()
        win._pending_drop = "C:/a.mp3"
        scan = self.patch(win, "_start_global_scan")
        win._on_global_cache_loaded(_lib())
        scan.assert_called_once_with("C:/a.mp3")
        self.assertIsNone(win._library.global_lib)

    def loaded(self, handler, message):
        local = _lib()
        win = self.host(lib=local)
        win._busy = mock.Mock()
        win._pending_drop = "C:/a.mp3"
        after = mock.Mock()
        win._pending_after_global = after
        start = self.patch(win, "_start_similar_worker")
        repo = _lib(_entry("a", features=[1.0]), _entry("b"))
        getattr(win, handler)(repo)
        repo.share_playlist_index_from.assert_called_once_with(local)
        self.assertIs(win._library.global_lib, repo)
        self.assertEqual(win.refreshed, 1)
        self.assertEqual(self.status(win), message)
        start.assert_called_once_with("C:/a.mp3", repo)
        after.assert_called_once()
        self.assertIsNone(win._pending_drop)
        self.assertIsNone(win._pending_after_global)

    def test_the_cached_repository_resumes_the_drop_and_the_build(self):  # overconfidence:short-test-ok - asserts in the helper
        self.loaded("_on_global_cache_loaded", "Global library ready from cache — 2 files.")

    def test_the_scanned_repository_resumes_the_drop_and_the_build(self):  # overconfidence:short-test-ok - asserts in the helper
        self.loaded("_on_global_ready", "Global index: 2 files, 1 analyzed.")

    def test_a_repository_without_a_local_library_shares_nothing(self):
        win = self.host()
        repo = _lib(_entry("a"))
        win._pending_drop = None
        win._pending_after_global = None
        win._on_global_ready(repo)
        repo.share_playlist_index_from.assert_not_called()
        self.assertIs(win._library.global_lib, repo)

    def test_an_error_or_a_cancel_drops_what_was_pending(self):
        win = self.host()
        win._busy = mock.Mock()
        win._pending_after_global = mock.Mock()
        win._on_global_error("walk failed")
        self.assertIsNone(win._pending_after_global)
        self.assertEqual(self.status(win), "Global index failed.")
        self.assertEqual(self.dialogs.calls, [("critical", "Global Index Error", "walk failed")])
        win._pending_drop, win._pending_after_global = "C:/a.mp3", mock.Mock()
        win._on_global_cancelled()
        self.assertEqual((win._pending_drop, win._pending_after_global), (None, None))
        self.assertEqual(self.status(win), "Repository scan cancelled.")
        self.assertEqual(win._busy.finish.call_count, 2)


class BuildIndexTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.saved = self.patch(mg, "save_settings")
        self.scanner = self.patch(mg, "GlobalLibraryLoader")

    def build_host(self, scope, **kw):
        win = self.host(**kw)
        self.patch(win, "_ask_index_scope", return_value=scope)
        return win

    def test_no_scope_picked_builds_nothing(self):
        win = self.build_host(None)
        win._build_global_index({"global_dir": "x"})
        self.saved.assert_called_once_with({"global_dir": "x"})
        self.assertEqual(win._settings, {"global_dir": "x"})
        self.assertEqual(win.analyses, [])

    def test_the_favorites_scope_analyzes_its_pool_directly(self):
        win = self.build_host("local")
        pool = self.patch(win, "_scoped_pool", return_value=(None, ""))
        win._build_global_index({})
        self.assertEqual(win.analyses, [])
        pool.return_value = ([_entry("a")], "the favorites library")
        win._build_global_index({})
        self.assertEqual(win.analyses, [([_entry("a")], "the favorites library")])
        self.scanner.assert_not_called()

    def test_the_repository_scope_needs_its_folder(self):
        win = self.build_host("global")
        win._build_global_index({"global_dir": "C:/does/not/exist"})
        self.assertIn("valid music repository folder", self.dialogs.text())
        self.scanner.assert_not_called()

    def test_the_repository_scope_scans_first(self):
        gdir = self.folder()
        win = self.build_host("both", cache=mock.Mock())
        win._build_global_index({"global_dir": gdir})
        self.assertEqual(win._librosa_scope, "both")
        self.scanner.assert_called_once_with(win._library.cache, gdir, win,
                                             share_from=win._library.lib)
        scan = self.scanner.return_value
        scan.done.connect.assert_called_once_with(win._on_global_index_scanned)
        scan.progress.connect.assert_called_once_with(win._on_global_scan_progress)
        scan.start.assert_called_once()
        win._library.global_loader = _running()
        win._build_global_index({"global_dir": gdir})
        self.scanner.assert_called_once()

    def test_scan_progress_goes_to_the_busy_dialog_and_the_status_bar(self):
        win = self.host()
        win._on_global_scan_progress(1, 2, "a.mp3", False)   # no dialog: ignored
        win._busy = mock.Mock()
        win._on_global_scan_progress(3, 0, "a.mp3", True)
        win._busy.set_progress.assert_called_with(3, 0, "♻️ a.mp3")
        self.assertEqual(self.status(win), "")
        win._on_global_scan_progress(1_000, 1_500, "b.mp3", False)
        win._busy.set_progress.assert_called_with(1_000, 1_500, "🔍 b.mp3")
        self.assertEqual(self.status(win), "Scanning repository… 1,000/1,500  (500 left)")

    def test_both_analyzes_repository_and_favorites_without_doubles(self):
        a, b, a_again = _entry("a"), _entry("b"), _entry("a")
        local = _lib(a_again, b)
        win = self.host(lib=local)
        win._busy = mock.Mock()
        win._librosa_scope = "both"
        repo = _lib(a)
        win._on_global_index_scanned(repo)
        repo.share_playlist_index_from.assert_called_once_with(local)
        self.assertIs(win._library.global_lib, repo)
        self.assertEqual(win.analyses, [([a, b], "the whole repository + favorites library")])

    def test_the_repository_alone_is_analyzed_by_default(self):
        win = self.host()
        repo = _lib(_entry("a"))
        win._on_global_index_scanned(repo)
        self.assertEqual(win.analyses, [(repo.entries, "the whole repository")])


class _Settings:
    """⚙ Settings handing back the given dict with `edits` applied."""
    edits: dict = {}
    accepted = True
    look_touched = False

    def __init__(self, settings, parent, **kw):
        self._given = dict(settings)

    def exec(self):
        return (QDialog.DialogCode.Accepted if _Settings.accepted
                else QDialog.DialogCode.Rejected)

    def values(self):
        return {**self._given, **_Settings.edits}

    def running_look_touched(self):
        return _Settings.look_touched


class SettingsTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.patch(mg, "SettingsDialog", new=_Settings)
        self.addCleanup(setattr, _Settings, "edits", {})
        self.addCleanup(setattr, _Settings, "accepted", True)
        self.addCleanup(setattr, _Settings, "look_touched", False)
        self.saved = self.patch(mg, "save_settings")
        self.patch(planner.playlist.m3u, "set_m3u_format")
        self.patch(mg, "set_no_class_exclusion")
        self.patch(mg, "error_reports")
        self.playlist_dir = self.patch(planner.config, "set_playlist_dir")
        self.win = mock.Mock()
        self.win._settings = {"app_mode": "both", "library_dir": "L", "global_dir": "G",
                              "playlist_dir": "P", "media_backend": "ffmpeg"}
        self.win._library.lib = None
        # The real restart offer, so its calls reach the mocked _offer_restart.
        self.win._offer_settings_restart = MethodType(
            GlobalIndexMixin._offer_settings_restart, self.win)

    def open(self, **edits):
        _Settings.edits = edits
        GlobalIndexMixin._open_settings(self.win)

    def test_a_cancelled_dialog_changes_nothing(self):
        _Settings.accepted = False
        self.open(global_dir="G2")
        self.saved.assert_not_called()
        self.assertIsNone(self.win._settings_dlg)

    def test_new_folders_reset_relearn_and_ask_for_a_restart(self):
        self.win._library.global_lib = _lib()
        self.open(global_dir="G2", playlist_dir="P2", library_dir="L2", preview_player=False)
        self.assertIsNone(self.win._library.global_lib)
        self.playlist_dir.assert_called_once_with("P2")
        self.win._relearn_playlists.assert_called_once()
        self.assertIn("Restart the app to load the new library", self.dialogs.text())
        self.win._preview.hide.assert_called_once()
        self.win._offer_restart.assert_not_called()
        self.saved.assert_called_once_with(self.win._settings)
        self.assertEqual(self.win._settings["global_dir"], "G2")

    def test_the_preview_player_follows_the_playback_when_on(self):
        self.open()
        self.win._sync_preview_to_playback.assert_called_once()
        self.win._relearn_playlists.assert_not_called()

    def test_a_new_audio_backend_offers_a_restart(self):
        self.open(media_backend="windows")
        self.assertEqual(self.win._offer_restart.call_args.args[0], "🔊 Audio backend")

    def test_a_touched_look_offers_a_restart(self):
        _Settings.look_touched = True
        self.open()
        self.assertEqual(self.win._offer_restart.call_args.args[0], "🎨 Look")


class MaintenanceTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.worker = self.patch(mg, "DbMaintenanceWorker")
        db = Path(self.folder()) / "audio_features.db"
        db.write_bytes(b"x" * 2_000_000)
        self.patch(planner.config, "audio_db_file", return_value=db)

    def test_cleanup_runs_only_on_a_yes(self):
        win = self.host()
        self.dialogs.answer = _NO
        win._run_db_maintenance()
        self.assertIn("audio_features.db (2 MB)", self.dialogs.text())
        self.worker.assert_not_called()
        self.dialogs.answer = _YES
        win._run_db_maintenance()
        self.worker.return_value.done.connect.assert_called_once_with(win._on_maintenance_done)
        self.worker.return_value.start.assert_called_once()

    def test_the_report_names_what_was_removed(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_maintenance_done({"removed": {"files": 3, "features": 0, "odd_table": 2},
                                  "size_before": 5_000_000, "size_after": 2_000_000})
        text = self.dialogs.text()
        self.assertIn("5.0 MB → 2.0 MB (3.0 MB freed)", text)
        self.assertIn("deleted tracks 3, odd_table 2", text)
        self.assertNotIn("feature vectors", text)
        self.assertEqual(self.status(win), "Database cleanup done.")
        win._on_maintenance_done({})
        self.assertIn("none — everything is still in use", self.dialogs.text())

    def test_a_failed_cleanup_is_reported(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_maintenance_error("locked")
        win._busy.finish.assert_called_once()
        self.assertIn("Cleanup did not run:\n\nlocked", self.dialogs.text())


class ManualPdTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.save = self.patch(QFileDialog, "getSaveFileName", return_value=("", ""))
        self.pick = self.patch(QFileDialog, "getOpenFileName", return_value=("", ""))

    def test_nothing_to_export_says_so(self):
        self.host(cache=None)._export_manual_pd()
        cache = mock.Mock(**{"export_manual_pd.return_value": []})
        self.host(cache=cache)._export_manual_pd()
        self.assertEqual(self.dialogs.kinds(), ["information", "information"])
        self.assertIn("No Paso Doble highlight", self.dialogs.text())
        self.save.assert_not_called()

    def test_the_marks_are_written_where_chosen(self):
        marks = [{"fp": "abc", "start": 1.5}]
        win = self.host(cache=mock.Mock(**{"export_manual_pd.return_value": marks}))
        win._export_manual_pd()
        self.assertEqual(self.dialogs.calls, [])
        target = Path(self.folder()) / "marks.json"
        self.save.return_value = (str(target), "")
        win._export_manual_pd()
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"manual_pd_marks": marks})
        self.assertIn("1 hand-set Paso Doble highlight(s) saved to", self.dialogs.text())

    def test_an_unwritable_target_is_reported(self):
        win = self.host(cache=mock.Mock(**{"export_manual_pd.return_value": [{"fp": "a"}]}))
        self.save.return_value = (str(Path(self.folder()) / "missing" / "marks.json"), "")
        win._export_manual_pd()
        self.assertIn("Could not write the file:", self.dialogs.text())

    def test_an_import_reads_the_marks_into_the_cache(self):
        self.host(cache=None)._import_manual_pd()
        self.pick.assert_not_called()
        cache = mock.Mock(**{"import_manual_pd.return_value": (2, 1)})
        win = self.host(cache=cache)
        win._import_manual_pd()
        cache.import_manual_pd.assert_not_called()
        src = Path(self.folder()) / "marks.json"
        src.write_text(json.dumps({"manual_pd_marks": [{"fp": "a"}, {"fp": "b"}]}),
                       encoding="utf-8")
        self.pick.return_value = (str(src), "")
        win._import_manual_pd()
        cache.import_manual_pd.assert_called_once_with([{"fp": "a"}, {"fp": "b"}])
        self.assertIn("2 hand-set Paso Doble highlight(s) imported — 1 of them",
                      self.dialogs.text())

    def test_a_file_without_marks_is_refused(self):
        cache = mock.Mock()
        win = self.host(cache=cache)
        src = Path(self.folder()) / "other.json"
        src.write_text("{}", encoding="utf-8")
        self.pick.return_value = (str(src), "")
        win._import_manual_pd()
        cache.import_manual_pd.assert_not_called()
        self.assertIn("This is no manual-PD-marks file:", self.dialogs.text())


class RestoreUserDataTest(_TestBase):

    def setUp(self):
        super().setUp()
        self.pick = self.patch(QFileDialog, "getOpenFileName", return_value=("", ""))
        self.patch(planner.music.db_upkeep, "_backup_dir", return_value=Path("C:/backups"))
        self.restore = self.patch(planner.music.db_upkeep, "restore_user_data", return_value=(4, 2, 7))

    def test_nothing_picked_restores_nothing(self):
        self.host()._restore_user_data()
        self.restore.assert_not_called()
        self.assertEqual(self.pick.call_args.args[2], str(Path("C:/backups")))

    def test_a_backup_is_merged_back(self):
        self.pick.return_value = ("C:/backups/user-data-1.db", "")
        self.host()._restore_user_data()
        self.restore.assert_called_once_with(Path("C:/backups/user-data-1.db"))
        self.assertIn("4 tag edit(s) and 2 hand-set Paso Doble highlight(s) restored, "
                      "7 played title(s)", self.dialogs.text())

    def test_a_file_that_is_no_backup_is_refused(self):
        self.pick.return_value = ("C:/backups/x.db", "")
        self.restore.side_effect = ValueError("no user_data table")
        self.host()._restore_user_data()
        self.assertIn("This is no user data backup:\n\nno user_data table", self.dialogs.text())


class RelearnTest(_TestBase):

    def test_while_the_library_loads_it_asks_to_wait(self):
        make = self.patch(mg, "PlaylistRelearnWorker")
        self.host()._relearn_playlists()
        make.assert_not_called()
        self.assertIn("still loading", self.dialogs.text())

    def test_the_fresh_index_is_adopted_and_shared(self):
        local = mock.Mock(**{"adopt_playlist_index.return_value": 1234})
        repo = _lib()
        win = self.host(lib=local, global_lib=repo)
        win._busy = mock.Mock()
        win._on_relearn_done({"learned": 1})
        local.adopt_playlist_index.assert_called_once_with({"learned": 1})
        repo.share_playlist_index_from.assert_called_once_with(local)
        self.assertEqual(win.refreshed, 1)
        self.assertEqual(self.status(win), "Playlist popularity re-learned from 1,234 playlists.")
        self.assertIn("1,234 playlists analyzed", self.dialogs.text())

    def test_a_library_gone_meanwhile_adopts_nothing(self):
        win = self.host()
        win._on_relearn_done({})
        self.assertEqual((win.refreshed, self.dialogs.calls), (0, []))

    def test_a_failed_relearn_is_reported(self):
        win = self.host()
        win._busy = mock.Mock()
        win._on_relearn_error("bad m3u")
        win._busy.finish.assert_called_once()
        self.assertIn("Re-learn failed:\n\nbad m3u", self.dialogs.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
