#!/usr/bin/env python3
"""🌐 The repository's popularity is worked out in the loader thread, not the GUI's.

Run:  py -m unittest tests.gui.test_whole_library_popularity_thread -v

Marcel: "loading repository from cache takes a while and thereafter freeze
before import dialog comes". Measured on a copy of his database (46 204
titles): once "Loading repository from cache…" closed, the GUI thread ran
`share_playlist_index_from` (every title matched against the playlist index
by regex, ~8 s) with nothing on screen. The loaders now adopt the favorites'
index themselves, behind the dialog that is already up, and the window's own
call finds it adopted and returns at once.
"""

import os
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wholepop_"))

from PySide6.QtWidgets import QApplication

import gui.workers
from gui.window import main_global as mg
from planner.models import MusicEntry
from planner.music.library import MusicLibrary

_app = QApplication.instance() or QApplication([])


def _favorites():
    fav = MusicLibrary()
    fav._track_playlists = defaultdict(set, {"song": {"pl1"}})
    return fav


def _repo(n=2):
    lib = MusicLibrary()
    lib.entries = [MusicEntry(path=Path(rf"C:\repo\{i}.mp3"), title=f"T{i}", dance="LW")
                   for i in range(n)]
    return lib


class AdoptOnceTest(unittest.TestCase):

    def test_the_same_index_is_not_applied_twice(self):
        fav, repo = _favorites(), _repo(3)
        with mock.patch.object(MusicLibrary, "_apply_popularity") as apply:
            repo.share_playlist_index_from(fav)
            self.assertEqual(apply.call_count, 3)
            repo.share_playlist_index_from(fav)
            self.assertEqual(apply.call_count, 3, "already adopted: nothing to do")

    def test_a_relearned_index_is_applied_again(self):
        fav, repo = _favorites(), _repo(2)
        with mock.patch.object(MusicLibrary, "_apply_popularity") as apply:
            repo.share_playlist_index_from(fav)
            fav._track_playlists = defaultdict(set, {"other": {"pl2"}})  # relearn swaps it
            repo.share_playlist_index_from(fav)
            self.assertEqual(apply.call_count, 4)


class LoaderThreadTest(unittest.TestCase):

    def run_loader(self, loader, patch_name):
        self.addCleanup(loader.deleteLater)
        done = []
        loader.done.connect(done.append)
        repo = _repo(2)

        def fill(lib, *a, **kw):
            lib.entries = repo.entries

        with (mock.patch.object(MusicLibrary, patch_name, fill),
              mock.patch.object(gui.workers, "lower_thread_priority"),
              mock.patch.object(gui.workers, "GlobalScanCache"),
              mock.patch.object(MusicLibrary, "share_playlist_index_from") as share):
            loader.run()
        self.assertEqual(len(done), 1)
        return done[0], share

    def test_the_cache_loader_adopts_the_favorites_index(self):
        fav = _favorites()
        lib, share = self.run_loader(
            gui.workers.GlobalCacheLoader(mock.Mock(), share_from=fav),
            "load_from_global_cache")
        share.assert_called_once_with(fav)

    def test_the_repository_walk_adopts_it_too(self):
        fav = _favorites()
        lib, share = self.run_loader(
            gui.workers.GlobalLibraryLoader(mock.Mock(), "C:/m", share_from=fav), "scan")
        share.assert_called_once_with(fav)

    def test_without_favorites_there_is_nothing_to_adopt(self):
        _lib, share = self.run_loader(gui.workers.GlobalCacheLoader(mock.Mock()),
                                      "load_from_global_cache")
        share.assert_not_called()


class _Host(mg.GlobalIndexMixin):
    def __init__(self, gdir):
        self._library = SimpleNamespace(
            lib=_favorites(), global_lib=None, cache=mock.Mock(), cache_loader=None,
            global_loader=None, load_bar=mock.Mock(running=False), repo_bar=mock.Mock())
        self._settings = {"global_dir": gdir}

    def _library_still_loading(self):
        return False


class WindowPassesTheFavoritesTest(unittest.TestCase):

    def setUp(self):
        for name in ("BusyDialog", "GlobalCacheLoader", "GlobalLibraryLoader"):
            patcher = mock.patch.object(mg, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.win = _Host(tempfile.mkdtemp(prefix="dp_wholepop_dir_"))

    def favorites_given(self, loader_cls):
        self.assertIs(loader_cls.call_args.kwargs.get("share_from"), self.win._library.lib)

    def test_the_cache_load(self):
        with mock.patch.object(mg.planner.music.scan_caches, "global_index_count",
                               return_value=5):
            self.win._ensure_global_lib()
        self.favorites_given(self.GlobalCacheLoader)

    def test_the_first_walk(self):
        with mock.patch.object(mg.planner.music.scan_caches, "global_index_count",
                               return_value=0):
            self.win._ensure_global_lib()
        self.favorites_given(self.GlobalLibraryLoader)

    def test_the_rescan(self):
        self.win._rescan_repository()
        self.favorites_given(self.GlobalLibraryLoader)


if __name__ == "__main__":
    unittest.main()
