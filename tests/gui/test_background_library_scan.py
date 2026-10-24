"""📚 The window opens before the library scan is done.

Run:  py -m unittest tests.gui.test_background_library_scan -v

A tester's first start sat behind the splash for as long as the scan of his
~/Music took. Now the loader hands over the audio cache first, the decks of
the last session come back (each title rebuilt from its file, as for a track
dragged in from outside), the window opens, and only then does the scan run,
with its progress in the status bar. What needs the library is greyed out or
says it is still loading; when the scan is done the decks get what the
library knows about their titles and everything switches on.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget

import gui.workers as workers
from gui.library_load_bar import LibraryLoadBar
from gui.window import main_global as gmg
from gui.window.library_service import LibraryService
from gui.window.main_decks import DeckLayoutMixin
from gui.window.main_wish import WishlistMixin
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db


class _ScratchCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_bg_scan_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.music = self.dir / "music" / "standardcd"
        self.music.mkdir(parents=True)
        for i in range(2):
            (self.music / f"Waltz {i} LW 29.mp3").write_bytes(bytes([i]) * 64)


class LoaderOrderTest(_ScratchCase):
    def run_loader(self, on_cache):
        order = []
        loader = workers.LibraryLoader(music_dir=self.music.parent)
        loader.cache_ready.connect(lambda cache: (order.append("cache"), on_cache(loader)))
        loader.finished_ok.connect(lambda lib, cache: order.append("done"))
        # run() here is the test's own thread, which must keep its priority.
        with mock.patch.object(workers.MusicLibrary, "scan",
                               side_effect=lambda *a, **kw: order.append("scan")), \
                mock.patch.object(workers, "lower_thread_priority") as self.lowered:
            loader.run()
        return order

    def test_the_cache_comes_first_and_the_scan_waits_for_go(self):
        self.assertEqual(self.run_loader(lambda loader: loader.go()),
                         ["cache", "scan", "done"])

    def test_a_cancel_before_go_scans_nothing(self):
        self.assertEqual(self.run_loader(lambda loader: loader.cancel()), ["cache"])

    def test_the_scan_runs_below_the_gui_and_the_player(self):
        self.run_loader(lambda loader: loader.go())
        self.lowered.assert_called_once_with()

    def test_pause_and_stop_reach_the_scan(self):
        loader = workers.LibraryLoader(music_dir=self.music.parent)
        loader.go()
        with mock.patch.object(workers.MusicLibrary, "scan") as scan, \
                mock.patch.object(workers, "lower_thread_priority"):
            loader.run()
        kw = scan.call_args.kwargs
        self.assertFalse(kw["should_pause"]())
        self.assertFalse(kw["should_stop"]())
        loader.pause(True)
        loader.stop()
        self.assertTrue(kw["should_pause"]())
        self.assertTrue(kw["should_stop"]())
        loader.pause(False)
        self.assertFalse(kw["should_pause"]())

    def test_a_stopped_scan_still_hands_over_its_library(self):
        """Stopped before its first file: an empty library, but a library —
        what waits for it switches on."""
        loader = workers.LibraryLoader(music_dir=self.music.parent)
        done = []
        loader.finished_ok.connect(lambda lib, cache: done.append(len(lib.entries)))
        loader.go()
        loader.stop()
        with mock.patch.object(workers, "lower_thread_priority"):
            loader.run()
        self.assertEqual(done, [0])

    def test_the_scan_reports_its_progress(self):
        loader = workers.LibraryLoader()
        seen = []
        loader.progress.connect(lambda done, total: seen.append((done, total)))
        loader._report(25, 100, Path("a.mp3"), False)
        loader._report(0, 0, Path("."), False)
        self.assertEqual(seen, [(25, 100), (0, 0)])


class LoadBarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.root = QWidget()
        self.addCleanup(self.root.deleteLater)
        self.gated = QPushButton("generate", self.root)
        self.gated.setProperty("needs_library", True)
        self.off = QPushButton("already off", self.root)
        self.off.setProperty("needs_library", True)
        self.off.setEnabled(False)
        self.free = QPushButton("play", self.root)
        self.bar = LibraryLoadBar(self.root)

    def test_it_greys_out_what_needs_the_library_and_gives_it_back(self):
        self.bar.start(self.root)
        self.assertTrue(self.bar.running)
        self.assertFalse(self.gated.isEnabled())
        self.assertTrue(self.free.isEnabled())
        self.bar.finish()
        self.assertFalse(self.bar.running)
        self.assertTrue(self.gated.isEnabled())
        self.assertFalse(self.off.isEnabled(), "was off before, stays off")

    def test_it_shows_how_far_the_scan_is(self):
        self.bar.start(self.root)
        self.bar.set_progress(0, 0)
        self.assertEqual(self.bar.progress.maximum(), 0)   # busy: still listing
        self.bar.set_progress(1234, 34000)
        self.assertEqual(self.bar.progress.maximum(), 34000)
        self.assertEqual(self.bar.progress.value(), 1234)
        self.assertIn("1,234 / 34,000", self.bar.label.text())

    def test_it_sits_flush_right_in_the_status_bar(self):
        """Marcel: "the library scan text is in the middle and the progress bar
        and stop icons right side, move everything to the right side"."""
        win = QMainWindow()
        self.addCleanup(win.deleteLater)
        win.setCentralWidget(QWidget())
        win.resize(1400, 600)
        bar = LibraryLoadBar()
        win.statusBar().addPermanentWidget(bar)
        win.show()
        bar.start(win)
        bar.set_progress(1234, 34000)
        for _ in range(3):
            self.app.processEvents()
        text_end = bar.label.x() + bar.label.fontMetrics().horizontalAdvance(bar.label.text())
        self.assertLess(bar.progress.x() - text_end, 15, "a gap between the text and the bar")
        self.assertGreater(bar.x(), win.width() // 2, "the bar takes half the status bar")

    def test_pause_holds_the_scan_and_says_so(self):
        """Marcel: "it would be nice to have a button to pause or abort it"."""
        seen = []
        self.bar.paused.connect(seen.append)
        self.bar.start(self.root)
        self.bar.set_progress(1234, 34000)
        self.bar.pause_btn.click()
        self.assertEqual(seen, [True])
        self.assertIn("⏸", self.bar.label.text())
        self.assertIn("1,234 / 34,000", self.bar.label.text())
        self.bar.pause_btn.click()
        self.assertEqual(seen, [True, False])
        self.assertNotIn("⏸", self.bar.label.text())

    def test_stop_asks_once_and_says_it_is_stopping(self):
        stops = []
        self.bar.stop_requested.connect(lambda: stops.append(1))
        self.bar.start(self.root)
        self.bar.set_progress(10, 100)
        self.bar.stop_btn.click()
        self.assertEqual(stops, [1])
        self.assertFalse(self.bar.stop_btn.isEnabled())
        self.assertFalse(self.bar.pause_btn.isEnabled())
        self.bar.set_progress(25, 100)          # a report already on its way
        self.assertIn("⏹", self.bar.label.text())

    def test_a_new_scan_starts_with_the_buttons_back(self):
        self.bar.start(self.root)
        self.bar.pause_btn.click()
        self.bar.stop_btn.click()
        self.bar.finish()
        self.bar.start(self.root)
        self.assertTrue(self.bar.stop_btn.isEnabled())
        self.assertTrue(self.bar.pause_btn.isEnabled())
        self.assertFalse(self.bar.pause_btn.isChecked())


class ResolverTest(_ScratchCase):
    def test_before_the_scan_paths_resolve_through_a_stand_in(self):
        service = LibraryService()
        self.assertIsNone(service.resolver())   # not even a cache yet
        service.cache = AudioCache()
        stand_in = service.resolver()
        self.assertIsInstance(stand_in, MusicLibrary)
        self.assertEqual(stand_in.entries, [])
        self.assertIs(service.resolver(), stand_in)
        path = next(self.music.iterdir())
        entry = stand_in.entry_for(path, service.cache, require_file=True)
        self.assertEqual(entry.dance, "LW")
        service.lib = MusicLibrary()
        self.assertIs(service.resolver(), service.lib)


class AdoptTest(_ScratchCase):
    def test_a_restored_title_gets_what_the_library_knows(self):
        cache = AudioCache()
        lib = MusicLibrary()
        lib.scan(cache, music_dir=self.music.parent, learn=False, interactive=False)
        path = sorted(self.music.iterdir())[0]
        early = MusicLibrary().make_external_entry(path, cache)
        self.assertIsNone(early.added)
        lib._track_playlists = {"x": {"y"}}
        with mock.patch.object(lib, "_apply_popularity") as popularity:
            lib.adopt(early)
        popularity.assert_called_once_with(early)
        self.assertEqual(early.added, lib.entry_for(path).added)
        self.assertIsNotNone(early.added)


class _Splash:
    def __init__(self, log):
        self._log = log

    def set_status(self, msg):
        self._log.append(f"splash: {msg}")

    def accept(self):
        self._log.append("splash closed")


class _Table:
    def __init__(self, entries):
        self._suggester = mock.Mock(lib=None)
        self._cache = None
        self.entries = entries
        self._row_meta = mock.Mock(**{"entries.return_value": entries})
        self.refreshed = []

    def refresh_paths(self, paths):
        self.refreshed.extend(paths)
        return len(paths)


class _Win:
    """A MainWindow reduced to the load path, recording what happens in order."""

    _on_cache_ready = gmg.GlobalIndexMixin._on_cache_ready
    _on_library_loaded = gmg.GlobalIndexMixin._on_library_loaded
    _finish_library_load = gmg.GlobalIndexMixin._finish_library_load
    _hand_over_library = gmg.GlobalIndexMixin._hand_over_library
    _library_still_loading = gmg.GlobalIndexMixin._library_still_loading

    def __init__(self, tables):
        self.log = []
        self._deckset = mock.Mock(all_tables=tables)
        self._suggester = None
        self._loading_dlg = _Splash(self.log)
        self._lib_browser = mock.Mock()
        self._tourney_tree = mock.Mock()
        self._library = LibraryService()
        self._library.loader = mock.Mock(**{"go.side_effect": lambda: self.log.append("go")})
        self._library.load_bar = mock.Mock(running=False)
        self._library.load_bar.start.side_effect = lambda root: (
            setattr(self._library.load_bar, "running", True), self.log.append("bar on"))
        self._library.load_bar.finish.side_effect = lambda: (
            setattr(self._library.load_bar, "running", False), self.log.append("bar off"))
        self.bar = mock.Mock()

    def statusBar(self):
        return self.bar

    def _preload_global_lib(self):
        pass   # the background repository load has its own test

    def _offer_crash_resume(self):
        pass   # the crash resume has its own test

    def show(self):
        self.log.append("WINDOW SHOWN")

    def _restore_playlist(self):
        self.log.append(f"restore (library: {self._library.lib is not None})")

    def _seed_undo_baseline(self):
        self.log.append("undo baseline")

    def _load_play_counts(self):
        pass   # 🔁 the Plays column has its own test

    def _refresh_library_status(self, enable_generate=False):
        self.log.append(f"library status (generate={enable_generate})")

    def _sync_loudness_available(self):
        self.log.append("loudness available")


class WindowFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        for name in ("apply_taskbar_icon", "learn_instrumental_probs",
                     "apply_vocal_shares", "_show_toast"):
            patcher = mock.patch.object(gmg, name, create=True)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.entry = mock.Mock(path=Path("C:/m/Waltz LW 29.mp3"))
        self.table = _Table([self.entry])
        self.win = _Win([self.table])
        self.lib = mock.Mock(entries=[])
        self.lib.entry_for.return_value = None

    def settle(self):
        for _ in range(20):
            self.app.processEvents()

    def test_the_window_opens_on_the_cache_before_the_scan(self):
        cache = object()
        self.win._on_cache_ready(cache)
        log = self.win.log
        self.assertIs(self.win._library.cache, cache)
        self.assertIsNone(self.win._library.lib)
        self.assertLess(log.index("restore (library: False)"), log.index("WINDOW SHOWN"))
        self.assertEqual(log.index("splash closed"), log.index("WINDOW SHOWN") - 1)
        self.assertLess(log.index("WINDOW SHOWN"), log.index("bar on"))
        self.assertEqual(log[-1], "go")   # the scan starts only now
        self.assertIs(self.table._cache, cache)

    def test_the_finished_scan_switches_everything_on(self):
        self.win._on_cache_ready(object())
        self.win.log.clear()
        cache = object()
        self.win._on_library_loaded(self.lib, cache)
        self.settle()
        log = self.win.log
        self.assertIs(self.win._library.lib, self.lib)
        self.assertNotIn("WINDOW SHOWN", log)
        self.assertFalse(any(line.startswith("restore") for line in log))
        self.assertIn("bar off", log)
        self.assertIn("library status (generate=True)", log)
        self.lib.adopt.assert_called_once_with(self.entry)
        self.assertIs(self.table._suggester.lib, self.lib)
        self.assertEqual(self.table.refreshed, [self.entry.path])

    def test_a_library_function_says_it_is_still_loading(self):
        self.win._on_cache_ready(object())
        self.assertTrue(self.win._library_still_loading())
        self._show_toast.assert_called_once()
        self.win._on_library_loaded(self.lib, object())
        self.settle()
        self.assertFalse(self.win._library_still_loading())
        self._show_toast.assert_called_once()


class _DropWin(_Win):
    """_Win with real tables and the real wiring a shown wishlist and an armed
    warm-up get."""

    _wire_wishlist = WishlistMixin._wire_wishlist
    _ensure_deck_ready = DeckLayoutMixin._ensure_deck_ready

    def __init__(self, wishlist, warmup):
        super().__init__([wishlist, warmup])
        self._deckset.wishlists = [wishlist]
        self._play_or_stop = mock.Mock()


class DropAfterTheScanTest(_ScratchCase):
    """A wishlist shown, or a warm-up armed, while the scan still ran was left
    without a suggester: _wire_wishlist and _ensure_empty_warmup wire one only
    with a library. A file dropped on it after the scan then said "Couldn't
    read … as an audio track"."""

    def test_a_list_shown_during_the_scan_reads_a_dropped_file(self):
        from gui.table.playlist_table import PlaylistTable
        from tests.qt_test_support import reap_widget
        wishlist, warmup = PlaylistTable(), PlaylistTable()
        for t in (wishlist, warmup):
            self.addCleanup(reap_widget, t)
        win = _DropWin(wishlist, warmup)
        with mock.patch.object(gmg, "apply_taskbar_icon"):
            win._on_cache_ready(AudioCache())
        win._wire_wishlist(wishlist)       # shown while the scan runs
        lib = MusicLibrary()
        with mock.patch.object(gmg, "learn_instrumental_probs", create=True), \
                mock.patch.object(gmg, "apply_vocal_shares", create=True):
            win._on_library_loaded(lib, win._library.cache)
        path = sorted(self.music.iterdir())[0]
        for t in (wishlist, warmup):
            entry = t._entry_for(path)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.dance, "LW")


if __name__ == "__main__":
    unittest.main()
