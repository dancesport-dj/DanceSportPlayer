#!/usr/bin/env python3
"""🔄 Scan the whole music repository again — tags only, behind the window.

Run:  py -m unittest tests.gui.test_repository_rescan -v

Marcel: "currently lib is 3656 files and global 3824 but should be over 50k,
i want a button to fast scan this without deep analysis" — "primary for using
library tab to search a title", and "add the scan button also under settings
in path settings".

🌐 Whole library loads the global index from the database once it was ever
built, and that never walks the folder: whatever came to the repository since
the last walk was missing. The 🔄 button walks it again, reading the tags of
new and changed files (no librosa), in the background like the startup scan:
its progress, pause and stop in the status bar, not behind a modal dialog.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reposcan_"))

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPushButton, QWidget

import gui.workers
from gui.dialogs.settings_dialog import SettingsDialog
from gui.library_browser import LibraryBrowser
from gui.library_load_bar import LibraryLoadBar
from gui.window import main_global as mg
from gui.window.main_global import GlobalIndexMixin
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


def _entries(prefix, n):
    return [MusicEntry(path=Path(rf"C:\{prefix}\{i}.mp3"), title=f"{prefix} {i}",
                       dance="SW") for i in range(n)]


class BrowserButtonTest(unittest.TestCase):

    def setUp(self):
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.browser.set_entries(_entries("favs", 2))
        self.asked = []
        self.browser.wholeRescanWanted.connect(lambda: self.asked.append(1))

    def test_it_sits_in_the_header_and_only_while_the_whole_library_shows(self):
        btn = self.browser._rescan_btn
        self.assertIs(btn.parentWidget(), self.browser._hdr)
        self.assertTrue(btn.isHidden(), "⭐ favorites: they are rescanned on start")
        self.browser.set_whole_entries(_entries("repo", 3))
        self.assertFalse(btn.isHidden())
        self.browser._source_btn.click()
        self.assertTrue(btn.isHidden())

    def test_clicking_it_asks_for_the_scan(self):
        self.browser.set_whole_entries(_entries("repo", 3))
        self.browser._rescan_btn.click()
        self.assertEqual(self.asked, [1])

    def test_the_browser_says_which_list_it_shows(self):
        self.assertFalse(self.browser.whole_shown)
        self.browser.set_whole_entries(_entries("repo", 3))
        self.assertTrue(self.browser.whole_shown)


class RepoBarTest(unittest.TestCase):

    def setUp(self):
        self.root = QWidget()
        self.addCleanup(self.root.deleteLater)
        self.gated = QPushButton("generate", self.root)
        self.gated.setProperty("needs_library", True)
        self.bar = LibraryLoadBar(self.root, repository=True)

    def test_it_greys_out_nothing(self):
        self.bar.start()
        self.assertTrue(self.bar.running)
        self.assertTrue(self.gated.isEnabled(), "the favorites library is loaded")
        self.bar.finish()
        self.assertFalse(self.bar.running)

    def test_it_names_the_repository(self):
        self.bar.start()
        self.bar.set_progress(0, 0)
        self.assertIn("repository", self.bar.label.text())
        self.bar.set_progress(1234, 54000)
        self.assertIn("Repository", self.bar.label.text())
        self.assertIn("1,234 / 54,000", self.bar.label.text())
        self.bar.pause_btn.click()
        self.assertIn("Repository scan paused", self.bar.label.text())
        self.assertIn("repository", self.bar.stop_btn.toolTip())


class LoaderTest(unittest.TestCase):

    def test_pause_and_stop_reach_the_scan(self):
        seen = {}

        def scan(_lib, _cache, **kw):
            seen.update(kw)

        loader = gui.workers.GlobalLibraryLoader(mock.Mock(), "C:/m")
        self.addCleanup(loader.deleteLater)
        done = []
        loader.done.connect(done.append)
        with (mock.patch.object(gui.workers.MusicLibrary, "scan", scan),
              mock.patch.object(gui.workers, "lower_thread_priority") as lower):
            loader.run()
        lower.assert_called_once()
        self.assertEqual(len(done), 1)
        self.assertFalse(seen["analyze"], "tags only, no librosa")
        self.assertFalse(seen["should_pause"]())
        self.assertFalse(seen["should_stop"]())
        loader.pause(True)
        loader.stop()
        self.assertTrue(seen["should_pause"]())
        self.assertTrue(seen["should_stop"]())


class _Host(QMainWindow, GlobalIndexMixin):
    def __init__(self, gdir, lib_loading=False, whole_shown=False):
        super().__init__()
        self._library = SimpleNamespace(
            lib=SimpleNamespace(entries=[]), global_lib=None, cache=mock.Mock(),
            global_loader=None, load_bar=mock.Mock(running=lib_loading),
            repo_bar=mock.Mock())
        self._settings = {"global_dir": gdir}
        self._lib_browser = mock.Mock(whole_shown=whole_shown)
        self.refreshed = 0

    def _refresh_library_status(self, enable_generate=False):
        self.refreshed += 1


class WindowTest(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.object(mg, "GlobalLibraryLoader")
        self.loader_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.loader = self.loader_cls.return_value
        self.loader.isRunning.return_value = True
        self.warned = []
        for kind in ("warning", "critical"):
            p = mock.patch.object(QMessageBox, kind,
                                  side_effect=lambda *a, **k: self.warned.append(a))
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(mg, "show_toast")
        self.toast = p.start()
        self.addCleanup(p.stop)
        self.gdir = tempfile.mkdtemp(prefix="dp_reposcan_dir_")

    def host(self, **kw):
        win = _Host(kw.pop("gdir", self.gdir), **kw)
        self.addCleanup(reap_widget, win)
        return win

    def test_it_walks_the_repository_in_the_background(self):
        win = self.host()
        win._rescan_repository()
        self.loader_cls.assert_called_once_with(win._library.cache, self.gdir, win,
                                                share_from=win._library.lib)
        self.assertIs(win._library.global_loader, self.loader)
        self.loader.progress.connect.assert_called_once_with(win._on_repository_scan_progress)
        self.loader.done.connect.assert_called_once_with(win._on_repository_rescanned)
        self.loader.start.assert_called_once()
        win._library.repo_bar.start.assert_called_once_with()

    def test_its_progress_goes_to_the_status_bar(self):
        win = self.host()
        win._on_repository_scan_progress(25, 54000, "a.mp3", True)
        win._library.repo_bar.set_progress.assert_called_once_with(25, 54000)

    def test_one_scan_at_a_time(self):
        win = self.host()
        win._rescan_repository()
        win._rescan_repository()
        self.loader_cls.assert_called_once()
        self.toast.assert_called_once()

    def test_not_while_the_favorites_scan_still_runs(self):
        win = self.host(lib_loading=True)
        win._rescan_repository()
        self.loader_cls.assert_not_called()

    def test_no_repository_folder_says_where_to_set_it(self):
        win = self.host(gdir="C:/does/not/exist")
        win._rescan_repository()
        self.loader_cls.assert_not_called()
        self.assertEqual(len(self.warned), 1)

    def test_the_scanned_index_replaces_the_cached_one(self):
        win = self.host(whole_shown=True)
        lib = SimpleNamespace(entries=_entries("repo", 4),
                              share_playlist_index_from=mock.Mock())
        win._on_repository_rescanned(lib)
        win._library.repo_bar.finish.assert_called_once()
        self.assertIs(win._library.global_lib, lib)
        lib.share_playlist_index_from.assert_called_once_with(win._library.lib)
        win._lib_browser.set_whole_entries.assert_called_once_with(lib.entries)
        self.assertEqual(win.refreshed, 1)
        self.assertIn("4", win.statusBar().currentMessage())

    def test_the_favorites_on_screen_stay_there(self):
        win = self.host(whole_shown=False)
        lib = SimpleNamespace(entries=_entries("repo", 4),
                              share_playlist_index_from=mock.Mock())
        win._on_repository_rescanned(lib)
        win._lib_browser.set_whole_entries.assert_not_called()
        self.assertIs(win._library.global_lib, lib, "🌐 shows it on the next click")

    def test_a_failed_scan_takes_the_bar_down_and_says_why(self):
        win = self.host()
        win._on_repository_rescan_error("drive gone")
        win._library.repo_bar.finish.assert_called_once()
        self.assertIn("drive gone", self.warned[0])


class SettingsButtonTest(unittest.TestCase):

    def test_it_sits_on_the_paths_tab_and_hands_over_the_values(self):
        got = []
        dlg = SettingsDialog({"global_dir": "F:/my music"}, None, rescan_cb=got.append)
        self.addCleanup(dlg.deleteLater)
        page = dlg._glob_edit.parentWidget()
        self.assertTrue(page.isAncestorOf(dlg._rescan_btn))
        self.assertTrue(dlg._rescan_btn.isEnabled())
        dlg._rescan_btn.click()
        self.assertEqual(got[0]["global_dir"], "F:/my music")
        self.assertEqual(dlg.result(), SettingsDialog.DialogCode.Accepted)

    def test_without_a_callback_it_is_off(self):
        dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertFalse(dlg._rescan_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
