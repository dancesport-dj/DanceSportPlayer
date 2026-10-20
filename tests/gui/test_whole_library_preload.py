#!/usr/bin/env python3
"""🌐 The whole library loads from the cache in the background after startup.

Run:  py -m unittest tests.gui.test_whole_library_preload -v

Marcel: "loading repository from cache takes a while" — the first 🌐 of a
session waited 12-15 s behind "Loading repository from cache…" (46 204
titles: rebuilding the entries, then their playlist popularity). Asked to
choose, he picked "load the index in the background after startup": once the
favorites are loaded, the same cache load runs in a thread with nothing on
screen, so the first 🌐, ≈ global search or repository index finds it ready.

Clicked while it still runs, nothing loads twice: 🌐 waits for that load
without a dialog (the window stays usable, the 🌐 button says it is loading,
the list comes when the load is done); a ≈ drop or an index build still waits
behind the usual one. A repository never walked is left alone — the walk is
minutes, and stays a click. A preload that fails says nothing, unless
someone was waiting for it.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_preload_"))

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

import gui.workers
from gui.window import main_global as mg
from gui.window.library_service import LibraryService
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


def _lib(n=2):
    return mock.Mock(entries=[MusicEntry(path=Path(rf"C:\repo\{i}.mp3"), title=f"T{i}")
                              for i in range(n)])


def _running():
    return mock.Mock(**{"isRunning.return_value": True})


class _Host(QMainWindow, mg.GlobalIndexMixin):
    def __init__(self, gdir):
        super().__init__()
        self._library = LibraryService()
        self._library.lib = _lib(1)
        self._library.cache = mock.Mock()
        self._settings = {"global_dir": gdir}
        self._busy = None
        self._lib_browser = mock.Mock()
        self.refreshed = 0

    def _refresh_library_status(self, enable_generate=False):
        self.refreshed += 1


class _Base(unittest.TestCase):

    def setUp(self):
        self.loader_cls = self.patch(mg, "GlobalCacheLoader")
        self.scanner = self.patch(mg, "GlobalLibraryLoader")
        self.busy_cls = self.patch(mg, "BusyDialog")
        self.count = self.patch(mg.planner.music.scan_caches, "global_index_count",
                                return_value=46204)
        self.critical = self.patch(QMessageBox, "critical")
        self.win = _Host(tempfile.mkdtemp(prefix="dp_preload_dir_"))
        self.addCleanup(reap_widget, self.win)

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found

    def preload(self):
        self.win._preload_global_lib()
        return self.loader_cls.return_value


class StartTest(_Base):

    def test_it_loads_the_cache_quietly_with_the_favorites_popularity(self):
        loader = self.preload()
        self.loader_cls.assert_called_once_with(self.win._library.cache, self.win,
                                                share_from=self.win._library.lib)
        loader.done.connect.assert_called_once_with(self.win._on_global_preloaded)
        loader.error.connect.assert_called_once_with(self.win._on_global_preload_error)
        loader.start.assert_called_once()
        self.assertIs(self.win._library.cache_loader, loader)
        self.assertIs(self.win._library.preloader, loader)
        self.busy_cls.assert_not_called()

    def test_a_repository_never_walked_is_left_for_a_click(self):
        self.count.return_value = 0
        self.preload()
        self.loader_cls.assert_not_called()
        self.scanner.assert_not_called()

    def test_without_a_repository_folder_nothing_loads(self):
        for gdir in (None, "C:/does/not/exist"):
            self.win._settings["global_dir"] = gdir
            self.preload()
        self.loader_cls.assert_not_called()
        self.critical.assert_not_called()

    def test_a_loaded_or_loading_repository_is_not_loaded_again(self):
        self.win._library.global_lib = _lib()
        self.preload()
        self.win._library.global_lib = None
        self.win._library.cache_loader = _running()
        self.preload()
        self.win._library.cache_loader = None
        self.win._library.global_loader = _running()
        self.preload()
        self.loader_cls.assert_not_called()

    def test_the_end_of_the_startup_load_starts_it(self):
        self.win._lib_browser = mock.Mock()
        self.win._tourney_tree = mock.Mock()
        self.win._sync_loudness_available = mock.Mock()
        self.patch(mg, "learn_instrumental_probs")
        self.patch(mg, "apply_vocal_shares")
        with mock.patch.object(self.win, "_preload_global_lib") as preload:
            self.win._finish_library_load(self.win._library.lib, "ready")
            for _ in range(20):
                _app.processEvents()
        preload.assert_called_once()
        self.assertEqual(self.win.statusBar().currentMessage(), "ready")


class DoneTest(_Base):

    def test_nobody_waiting_keeps_it_for_the_first_click(self):
        repo = _lib(3)
        self.preload()
        self.win._on_global_preloaded(repo)
        self.assertIs(self.win._library.global_lib, repo)
        self.assertEqual(self.win.refreshed, 1)
        self.win._show_whole_library()
        self.win._lib_browser.set_whole_entries.assert_called_once_with(repo.entries)
        self.loader_cls.assert_called_once()   # the click loaded nothing

    def test_an_empty_index_starts_no_walk_unasked(self):
        self.preload()
        self.win._on_global_preloaded(_lib(0))
        self.assertIsNone(self.win._library.global_lib)
        self.scanner.assert_not_called()

    def test_a_newer_index_meanwhile_is_not_overwritten(self):
        newer = _lib(5)
        self.preload()
        self.win._library.global_lib = newer   # a 🔄 rescan finished first
        self.win._on_global_preloaded(_lib(3))
        self.assertIs(self.win._library.global_lib, newer)

    def test_a_click_meanwhile_waits_without_a_dialog(self):
        """Marcel: the window must stay usable while the whole library loads."""
        loader = self.preload()
        loader.isRunning.return_value = True
        browser = self.win._lib_browser
        self.win._show_whole_library()
        self.win._show_whole_library()   # clicked twice
        self.assertEqual(self.loader_cls.call_count, 1, "no second load")
        self.busy_cls.assert_not_called()
        browser.show_whole_loading.assert_called_with(True)
        self.assertIn("loading", self.win.statusBar().currentMessage())
        browser.set_whole_entries.assert_not_called()
        repo = _lib(3)
        self.win._on_global_preloaded(repo)
        browser.show_whole_loading.assert_called_with(False)
        browser.set_whole_entries.assert_called_once_with(repo.entries)
        self.assertIs(self.win._library.global_lib, repo)
        self.assertFalse(self.win._library.whole_waiting)

    def test_going_back_meanwhile_keeps_the_favorites_on_screen(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        self.win._show_whole_library()
        self.win._stop_whole_wait()        # ⭐ clicked again while it loads
        self.assertFalse(self.win._library.whole_waiting)
        repo = _lib(3)
        self.win._on_global_preloaded(repo)
        self.win._lib_browser.set_whole_entries.assert_not_called()
        self.assertIs(self.win._library.global_lib, repo, "kept for the next click")

    def test_a_click_meanwhile_takes_a_newer_rescan(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        self.win._show_whole_library()
        newer = _lib(5)
        self.win._library.global_lib = newer   # a 🔄 rescan finished first
        self.win._on_global_preloaded(_lib(3))
        self.assertIs(self.win._library.global_lib, newer)
        self.win._lib_browser.set_whole_entries.assert_called_once_with(newer.entries)

    def test_a_drop_meanwhile_is_searched_once_it_is_there(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        start = self.patch(self.win, "_start_similar_worker")
        self.win._ensure_global_lib(then_drop="C:/a.mp3")
        self.busy_cls.return_value.show_after.assert_called_once()
        repo = _lib(3)
        self.win._on_global_preloaded(repo)
        start.assert_called_once_with("C:/a.mp3", repo)

    def test_a_drop_and_a_click_meanwhile_both_get_it(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        start = self.patch(self.win, "_start_similar_worker")
        self.win._show_whole_library()
        self.win._ensure_global_lib(then_drop="C:/a.mp3")
        repo = _lib(3)
        self.win._on_global_preloaded(repo)
        self.busy_cls.return_value.finish.assert_called_once()
        start.assert_called_once_with("C:/a.mp3", repo)
        self.win._lib_browser.set_whole_entries.assert_called_once_with(repo.entries)

    def test_a_click_on_an_empty_preload_walks_the_repository(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        self.win._show_whole_library()
        self.win._on_global_preloaded(_lib(0))
        self.scanner.assert_called_once()
        walked = _lib(4)
        self.win._on_global_ready(walked)
        self.win._lib_browser.set_whole_entries.assert_called_once_with(walked.entries)

    def test_a_failure_nobody_waited_for_says_nothing(self):
        self.preload()
        with self.assertLogs("dancesport.gui.global", "WARNING"):
            self.win._on_global_preload_error("disk gone")
        self.critical.assert_not_called()
        self.assertIsNone(self.win._library.global_lib)

    def test_a_failure_someone_waited_for_is_shown(self):
        loader = self.preload()
        loader.isRunning.return_value = True
        self.win._show_whole_library()
        with self.assertLogs("dancesport.gui.global", "WARNING"):
            self.win._on_global_preload_error("disk gone")
        self.busy_cls.assert_not_called()
        self.win._lib_browser.show_whole_loading.assert_called_with(False)
        self.critical.assert_called_once()
        self.assertIsNone(self.win._pending_after_global)
        self.assertFalse(self.win._library.whole_waiting)


class WaitingButtonTest(unittest.TestCase):

    def test_the_button_says_it_is_loading_until_the_list_is_there(self):
        from gui.library_browser import LibraryBrowser
        pane = LibraryBrowser()
        self.addCleanup(reap_widget, pane)
        btn = pane._source_btn
        pane.show_whole_loading(True)
        self.assertEqual(btn.text(), "⏳ Whole library…")
        self.assertTrue(btn.isChecked())
        pane.set_whole_entries(_lib(2).entries)
        self.assertEqual(btn.text(), "🌐 Whole library")

    def test_a_failed_load_puts_the_favorites_back_on_the_button(self):
        from gui.library_browser import LibraryBrowser
        pane = LibraryBrowser()
        self.addCleanup(reap_widget, pane)
        pane.show_whole_loading(True)
        pane.show_whole_loading(False)
        self.assertEqual(pane._source_btn.text(), "⭐ Favorites")
        self.assertFalse(pane._source_btn.isChecked())


class LoaderPriorityTest(unittest.TestCase):

    def test_the_cache_load_yields_to_the_gui_and_the_player(self):
        loader = gui.workers.GlobalCacheLoader(mock.Mock())
        self.addCleanup(loader.deleteLater)
        with (mock.patch.object(gui.workers.MusicLibrary, "load_from_global_cache"),
              mock.patch.object(gui.workers, "GlobalScanCache"),
              mock.patch.object(gui.workers, "lower_thread_priority") as lower):
            loader.run()
        lower.assert_called_once()


if __name__ == "__main__":
    unittest.main()
