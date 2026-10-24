"""Global library, audio/index analysis, similar search, settings.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import importlib.util
import json
import logging

import planner.config
import planner.music.db_upkeep
import planner.music.scan_caches
import planner.playlist.m3u

HAS_MULTIMEDIA = importlib.util.find_spec("PySide6.QtMultimedia") is not None

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
)
from pathlib import Path
from collections.abc import Callable
from planner.music.analysis import HAS_LIBROSA
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary
from planner.models import note_class_tag_use, set_hidden_folders, set_no_class_exclusion
from shared import error_reports
from shared.appearance import theme
from planner import i18n
from gui.common import (
    BusyDialog,
    apply_taskbar_icon,
    set_dblclick_action,
)
from gui.index_summary import index_summary
from shared.widgets import _show_toast
from gui.dialogs.reset_db_dialog import ResetDatabaseDialog
from gui.dialogs.settings_cartwall import CART_WALL_KEYS
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs import (  # auto-resolved
    SimilarTracksDialog,
    media_backend_of,
    restart_app,
)
from shared.stores import (
    save_settings,
)
from planner.music.vocals import (
    apply_vocal_shares,
    learn_instrumental_probs,
)
from gui.workers import (  # auto-resolved
    DbMaintenanceWorker,
    DbResetWorker,
    GlobalCacheLoader,
    GlobalLibraryLoader,
    PlaylistRelearnWorker,
    SimilarFromFileWorker,
)
from gui.window.main_allcache import (
    AllCacheMixin,
    plan_allcache_steps,  # noqa: F401 — re-exported for existing callers
)
from gui.window.main_analyze import AnalysisMixin
from gui.window.main_embed import EmbeddingIndexMixin

log = logging.getLogger("dancesport.gui.global")

# 🧹 Clean up database reports what it removed; the DB table names mean nothing
# to whoever clicked the button.
_MAINT_LABELS = {
    "files": "deleted tracks", "scan_meta": "tag records",
    "features": "feature vectors", "audio_fps": "audio fingerprints",
    "embeddings": "AI embeddings", "loudness": "loudness values",
    "pd_highlights": "PD highlights", "silences": "silence maps",
    "vocals": "vocal shares", "noise": "noise floors",
    "playlist_index": "playlist index entries", "app_meta": "stale index markers",
}


class GlobalIndexMixin(AnalysisMixin, EmbeddingIndexMixin, AllCacheMixin):
    """The libraries themselves: the local one, the global one, the ≈ search, and
    ⚙ the Settings dialog that points them all at their folders.

    What is RUN over them lives next door: 🔬 the analyses (gui.window.main_analyze),
    🧠 the indexes (gui.window.main_embed) and 🧱 build-all (gui.window.main_allcache).
    MainWindow keeps importing this one name.
    """

    def _on_cache_ready(self, cache: AudioCache):
        """The audio cache is open, the library scan not yet started: bring the
        last session back and open the window, then let the scan run.

        A first start on a big ~/Music used to sit behind the splash for the
        whole scan. Only what the window is unusable without happens in front
        of it now: the playlist the last session was left on, each title read
        from its own file (LibraryService.resolver). The scan follows behind
        the open window, its progress in the status bar."""
        self._library.cache = cache
        for t in self._deckset.all_tables:
            t._cache = cache   # enable chained drops in the similar-tracks dialog
        self._loading_dlg.set_status("♻️  Restoring your last session…")
        QApplication.processEvents()   # keep the modal splash's bar pulsing
        self._restore_playlist()
        # Anchor the undo timeline at the restored state so the first edit is undoable.
        self._seed_undo_baseline()

        # Reveal the window and drop the splash.
        self._loading_dlg.accept()   # accept() bypasses closeEvent (which ignores close())
        self.show()
        # HWND exists only now → push the app icon to the taskbar button so it
        # doesn't fall back to the generic Python icon after the splash closes.
        apply_taskbar_icon(self)
        self._offer_crash_resume()   # 🆘 over the restored decks, not the splash
        if self._library.load_bar is not None:
            self._library.load_bar.start(self)
        # Only now: the restore above writes fingerprints, and the scan's
        # write transactions would have kept it waiting.
        if self._library.loader is not None:
            self._library.loader.go()

    def _on_library_loaded(self, lib: MusicLibrary, cache: AudioCache):
        self._library.lib   = lib
        self._library.cache = cache
        note_class_tag_use(lib.entries)   # 🏷 'No class' only where classes are used
        n          = len(lib.entries)
        comp       = sum(1 for e in lib.entries if e.dance is not None)
        cached     = sum(1 for e in lib.entries if e.features is not None)
        self._hand_over_library(lib)
        self._load_play_counts()     # 🔁 the Plays column, now the database is there
        if self._library.load_bar is not None:
            self._library.load_bar.finish()
        # The browser list, the vocal learning, the counting of what is
        # analyzed: none of it needed to look at the playlist, so it runs
        # step by step in the open window and says where it is.
        # An f-string is never a catalog key, so the hook on showMessage had
        # nothing to match and a German screen ended its startup in English.
        self._finish_library_load(
            lib, i18n.t("Library loaded — %s MP3 files, %s favorites songs, "
                        "%s audio cached.") % (n, comp, cached))

    def _hand_over_library(self, lib: MusicLibrary):
        """The decks were restored before the scan was done: their tracks get
        what the library knows about them, and their suggesters, built on no
        library at all, get this one."""
        for t in self._deckset.all_tables:
            entries = t._row_meta.entries()
            for e in entries:
                lib.adopt(e)
            t.refresh_paths([e.path for e in entries])
            if t._suggester is not None and t._suggester.lib is None:
                t._suggester.lib = lib
        # A wishlist shown, or a warm-up armed, during the scan got no
        # suggester at all (both wire one only with a library), and a file
        # dropped on it was "Couldn't read … as an audio track".
        for t in self._deckset.all_tables:
            if t._suggester is not None:
                continue
            if t in self._deckset.wishlists:
                self._wire_wishlist(t)
            else:
                self._ensure_deck_ready(t)
        if self._suggester is not None and self._suggester.lib is None:
            self._suggester.lib = lib

    def _library_still_loading(self) -> bool:
        """True, and a toast saying so, while the library scan still runs —
        for an action that works on the library."""
        bar = self._library.load_bar
        if bar is None or not bar.running:
            return False
        _show_toast(self, i18n.t("📚 The library is still loading — "
                                 "this works once it is done."), 2500)
        return True

    def _finish_library_load(self, lib: MusicLibrary, ready_msg: str):
        """The tail of the load, run in the open window instead of before it.

        One step per turn of the event loop rather than one long block: the
        window stays answerable between them, and the status bar has a chance
        to actually repaint — a message posted and then overwritten inside the
        same call is a message nobody ever sees.

        Nothing here is needed to look at the playlist, which is what the
        window is opened for; each step just turns something on."""
        steps = [
            # The library browser's Vocal/Instr. filter also catches untagged
            # tracks — learned from the cached features, then overruled by
            # whatever 🎙️ Analyze vocals has really measured.
            ("🎙️  Learning vocal / instrumental…",
             lambda: (learn_instrumental_probs(lib.entries),
                      apply_vocal_shares(lib.entries, self._library.cache))),
            # 📚 the browser pane (it filters lazily from this list) and the
            # 🏆 tree, which names a playlist's tracks from the same one.
            ("📚  Filling the library browser…",
             lambda: (self._lib_browser.set_entries(lib.entries),
                      self._tourney_tree.set_entries(lib.entries))),
            # Counting what is indexed reads the DB, and 🔊 Equalize volume
            # only becomes selectable once loudness data is known to exist.
            ("🔬  Counting what is analyzed…",
             lambda: (self._refresh_library_status(enable_generate=True),
                      self._sync_loudness_available())),
        ]

        def run(i: int = 0):
            if i >= len(steps):
                self.statusBar().showMessage(ready_msg)
                self._preload_global_lib()
                return
            msg, fn = steps[i]
            self.statusBar().showMessage(msg)
            QTimer.singleShot(0, lambda: (guarded(msg, fn), run(i + 1)))

        def guarded(msg: str, fn):
            # One step that fails must not cost the ones after it — the
            # chain would end in this turn of the event loop.
            try:
                fn()
            except Exception:
                log.exception("💥 Startup step failed, carrying on\n"
                              "step: %s", msg.strip())

        run()

    def _mode_line(self) -> str:
        """Human-readable description of which library similarity searches hit."""
        if self._settings.get("global_search"):
            return i18n.t("🌐  Search mode: Global — whole repository")
        return i18n.t("🎯  Search mode: Favorites library only")

    def _refresh_library_status(self, enable_generate: bool = False):
        """Recompose the ConfigPanel status label (mode + counts + per-model index)."""
        if not self._library.lib:
            return
        n          = len(self._library.lib.entries)
        comp       = sum(1 for e in self._library.lib.entries if e.dance is not None)
        cached     = sum(1 for e in self._library.lib.entries if e.features is not None)
        unanalyzed = n - cached
        # Every line takes its numbers through a placeholder: the assembled
        # block is unique on each refresh and would match no catalog key.
        status = "\n".join((self._mode_line(),
                            i18n.t("Library: %d files") % n,
                            i18n.t("Favorites: %d") % comp))
        # Always show the global-index state, regardless of the active search mode.
        status += "\n" + self._global_index_line()
        # Which library is indexed right now for which model.
        summ = self._index_summary()
        status += "\n" + "\n".join((
            i18n.t("— Indexes (analyzed / total) —"),
            i18n.t("🔗 Fingerprints: %s") % summ["audiofp"],
            i18n.t("🎚️ librosa: %s") % summ["librosa"],
            i18n.t("🎼 Chroma: %s") % summ["chroma"],
            i18n.t("🧠 MERT: %s") % summ["mert"],
            i18n.t("📊 Loudness: %s") % summ["loudness"],
            i18n.t("🔇 Silences: %s") % summ["silences"],
            i18n.t("🐂 PD highlights: %s") % summ["pd"]))
        if self._library.cache is not None and self._library.cache.vocal_share_count():
            status += "\n" + i18n.t("🎙️ Demucs vocals: %s measured") % (
                f"{self._library.cache.vocal_share_count():,}")
        self._cfg.set_library_status(status, enable_generate=enable_generate,
                                     n_unanalyzed=unanalyzed,
                                     needs_build=bool(summ.get("favorites_gap")))

    def _index_summary(self) -> dict:
        return index_summary(self._library.cache, self._embedding_store(),
                             self._library.lib, self._library.global_lib)

    def _global_index_line(self) -> str:
        """One-line global-repo index state — shown in every mode."""
        if self._library.global_lib is not None:
            gn = len(self._library.global_lib.entries)
            gc = sum(1 for e in self._library.global_lib.entries if e.features is not None)
            return i18n.t("🌐 Global index: %s files, %s analyzed") % (
                f"{gn:,}", f"{gc:,}")
        built = planner.music.scan_caches.global_index_count()
        if built:
            return i18n.t("🌐 Global index: %s files built "
                          "(loads on first global search)") % f"{built:,}"
        return i18n.t("🌐 Global index: not built (⚙ Settings to build)")

    def _on_library_error(self, msg: str):
        if self._library.load_bar is not None and self._library.load_bar.running:
            self._library.load_bar.finish()   # the window is open already
        else:
            self._loading_dlg.accept()   # accept() bypasses closeEvent
            self.show()
            apply_taskbar_icon(self)
        self._cfg.set_library_status(f"Error loading library:\n{msg}")
        self.statusBar().showMessage(i18n.t("Library error: %s") % msg)
        QMessageBox.critical(self, "Library Load Error", msg)

    def _on_file_dropped(self, path: str):
        if self._library_still_loading():
            return
        if not self._library.lib or not self._library.cache:
            return
        if not HAS_LIBROSA:
            QMessageBox.warning(
                self, "Audio analysis unavailable",
                "Finding similar tracks for a file needs librosa + ffmpeg.\n"
                "Install them, then retry."
            )
            return
        if self._sim_worker and self._sim_worker.isRunning():
            return
        # Global search → match against the whole repo (build the index lazily once);
        # otherwise match against the favorites library only.
        if self._settings.get("global_search"):
            if self._library.global_lib is not None:
                self._start_similar_worker(path, self._library.global_lib)
            else:
                self._ensure_global_lib(then_drop=path)
        else:
            self._start_similar_worker(path, self._library.lib)

    def _start_similar_worker(self, path: str, lib: MusicLibrary):
        self._sim_lib = lib
        self.statusBar().showMessage(i18n.t("Analyzing %s …") % Path(path).name)
        self._busy = BusyDialog(self, i18n.t("Analyzing %s …") % Path(path).name)
        self._busy.show_after(500)
        self._sim_worker = SimilarFromFileWorker(
            lib, self._library.cache, path, n=100, min_display=0.5, parent=self)
        self._sim_worker.done.connect(self._on_similar_ready)
        self._sim_worker.error.connect(self._on_similar_error)
        self._sim_worker.start()

    def _on_similar_ready(self, source, results):
        if self._busy:
            self._busy.finish()
        search_lib = getattr(self, "_sim_lib", None) or self._library.lib
        scope = (i18n.t("the whole repository") if search_lib is self._library.global_lib
                 else i18n.t("the favorites library"))
        if not results:
            self.statusBar().showMessage("No similar tracks found.")
            entries = getattr(search_lib, "entries", []) or []
            analyzed = sum(1 for e in entries if e.features is not None)
            total = len(entries)
            if analyzed == 0:
                hint = "\n\n" + i18n.t(
                    "Global search is on but the repository isn't analyzed yet — "
                    "open ⚙ Settings → “Build / refresh global audio index”."
                    if search_lib is self._library.global_lib else
                    "No tracks are analyzed yet — run 'Analyze Audio' first.")
            elif analyzed < total:
                running = (getattr(self, "_analyzer", None) and self._analyzer.isRunning())
                hint = "\n\n" + (
                    i18n.t("Only %s of %s tracks are analyzed so far (analysis is "
                           "still running). Let analysis finish and try again.")
                    if running else
                    i18n.t("Only %s of %s tracks are analyzed so far. Let analysis "
                           "finish and try again.")) % (f"{analyzed:,}", f"{total:,}")
            else:
                hint = "\n\n" + i18n.t(
                    "All tracks are analyzed — this file just has no close match.")
            QMessageBox.information(
                self, "Similar Tracks",
                i18n.t("No similar tracks found in %s.") % scope + hint
            )
            return
        self.statusBar().showMessage(
            i18n.t("Found %d similar to %s (%s)") % (len(results), source.title[:40], scope))
        SimilarTracksDialog(source, results, self, play_cb=self._prehear,
                            lib=search_lib, cache=self._library.cache,
                            seek_cb=self._prehear_seek,
                            is_global=(search_lib is self._library.global_lib),
                            wishlist_paths=self.current_wishlist_paths()).exec()

    def _on_similar_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        self.statusBar().showMessage("Similar-track analysis failed.")
        QMessageBox.critical(self, "Analysis Error", msg)

    def _ensure_global_lib(self, then_drop: str | None = None,
                           then_build: Callable[[], None] | None = None):
        """Scan the whole repo (metadata + cached features) once, then resume the
        pending drop and/or build callback."""
        self._pending_after_global = then_build
        gdir = self._settings.get("global_dir")
        if not gdir or not Path(gdir).exists():
            self._pending_after_global = None
            QMessageBox.warning(
                self, "Global search",
                "Set a valid music repository folder in ⚙ Settings first."
            )
            return
        # Fast path: if the global index was already built, rebuild the library
        # straight from the warm cache — no filesystem re-walk, no indexing window.
        # Reconstructing 53k+ entries still takes a moment, so do it OFF the UI thread
        # behind a small load window. (New / changed files need a ⚙ Settings rebuild.)
        if self._library.cache is not None and planner.music.scan_caches.global_index_count() > 0:
            if self._library.cache_loader and self._library.cache_loader.isRunning():
                if (self._library.cache_loader is self._library.preloader
                        and self._library.preload_busy is None):
                    # The startup preload is at it: wait for that one, not a second.
                    self._pending_drop = then_drop
                    self._library.preload_busy = BusyDialog(
                        self, "Loading repository from cache…")
                    self._library.preload_busy.show_after(200)
                return
            self._pending_drop = then_drop
            self._busy = BusyDialog(self, "Loading repository from cache…")
            self._busy.show_after(200)
            self._library.cache_loader = GlobalCacheLoader(self._library.cache, self,
                                                           share_from=self._library.lib)
            self._library.cache_loader.done.connect(self._on_global_cache_loaded)
            self._library.cache_loader.error.connect(self._on_global_error)
            self._library.cache_loader.start()
            return
        self._start_global_scan(then_drop)

    def _show_whole_library(self):
        """🌐 in the library browser: list the global index, loading it first."""
        lib = self._library.global_lib
        if lib is None:
            pre = self._library.preloader
            if pre is not None and pre is self._library.cache_loader and pre.isRunning():
                # The startup preload is at it: wait for that one without a
                # dialog, the window stays usable (_on_global_preloaded lists it).
                self._library.whole_waiting = True
                self._lib_browser.show_whole_loading(True)
                self.statusBar().showMessage(
                    "🌐 The whole library is still loading — it is listed when it is there.")
                return
            self._ensure_global_lib(then_build=self._show_whole_library)
            return
        # Even when empty: loading again would just rescan the repository.
        self._lib_browser.set_whole_entries(lib.entries)

    def _stop_whole_wait(self):
        """⭐ clicked while 🌐 waits for the preload: the favorites stay. The
        preload goes on and keeps the index for the next 🌐."""
        self._library.whole_waiting = False
        self.statusBar().clearMessage()

    def _rescan_repository(self, values: dict | None = None):
        """🔄 Walk the whole repository again, tags only, behind the open window.

        The cached index (`_ensure_global_lib`'s fast path) never walks the
        folder, so what came to the repository since the last walk was missing
        from 🌐 — 3.8k of 54k files. This is that walk without the librosa
        pass, and like the startup scan its progress, pause and stop sit in the
        status bar instead of a modal dialog: unchanged files are reused, but a
        first walk reads tens of thousands of tags. `values`: ⚙ Settings'
        current ones, which may name a folder not saved yet."""
        if values is not None:
            save_settings(values)
            self._settings = values
        if self._library_still_loading():
            return
        loader = self._library.global_loader
        if loader is not None and loader.isRunning():
            _show_toast(self, i18n.t("🌐 The repository is being scanned already."), 2500)
            return
        gdir = self._settings.get("global_dir")
        if not gdir or not Path(gdir).exists():
            QMessageBox.warning(
                self, "Scan repository",
                "Set a valid music repository folder in ⚙ Settings first.")
            return
        loader = GlobalLibraryLoader(self._library.cache, gdir, self,
                                     share_from=self._library.lib)
        self._library.global_loader = loader
        loader.progress.connect(self._on_repository_scan_progress)
        loader.done.connect(self._on_repository_rescanned)
        loader.error.connect(self._on_repository_rescan_error)
        bar = self._library.repo_bar
        if bar is not None:
            loader.cancelled.connect(bar.finish)
            bar.start()
        loader.start()

    def _on_repository_scan_progress(self, done: int, total: int, _name: str, _reused: bool):
        if self._library.repo_bar is not None:
            self._library.repo_bar.set_progress(done, total)

    def _on_repository_rescanned(self, lib: MusicLibrary):
        if self._library.repo_bar is not None:
            self._library.repo_bar.finish()
        if self._library.lib is not None:
            lib.share_playlist_index_from(self._library.lib)
        self._library.global_lib = lib
        # The favorites on screen stay there; 🌐 shows the new index next time.
        if self._lib_browser.whole_shown:
            self._lib_browser.set_whole_entries(lib.entries)
        self._refresh_library_status()
        n = len(lib.entries)
        cached = sum(1 for e in lib.entries if e.features is not None)
        self.statusBar().showMessage(
            i18n.t("Global index: %s files, %s analyzed.") % (f"{n:,}", f"{cached:,}"))

    def _on_repository_rescan_error(self, msg: str):
        if self._library.repo_bar is not None:
            self._library.repo_bar.finish()
        self.statusBar().showMessage("Global index failed.")
        QMessageBox.critical(self, "Global Index Error", msg)

    def _start_global_scan(self, then_drop: str | None = None):
        """Full repository walk (cold cache or explicit rebuild) with progress."""
        gdir = self._settings.get("global_dir")
        if not gdir or not Path(gdir).exists():
            return
        self._pending_drop = then_drop
        if self._library.global_loader and self._library.global_loader.isRunning():
            return
        self._busy = BusyDialog(self, "Indexing whole repository…", cancelable=True)
        self._library.global_loader = GlobalLibraryLoader(self._library.cache, gdir, self,
                                                          share_from=self._library.lib)
        self._busy.cancel_requested.connect(self._library.global_loader.cancel)
        self._busy.show_after(300)
        self._library.global_loader.progress.connect(self._on_global_scan_progress)
        self._library.global_loader.done.connect(self._on_global_ready)
        self._library.global_loader.error.connect(self._on_global_error)
        self._library.global_loader.cancelled.connect(self._on_global_cancelled)
        self._library.global_loader.start()

    def _preload_global_lib(self):
        """🌐 After startup: load the whole library from the cache in the
        background, so the first 🌐 / global search finds it ready instead of
        waiting 12-15 s behind a dialog (46k titles). A repository never
        walked is left alone: that walk is minutes, and stays a click."""
        lib = self._library
        if lib.global_lib is not None or lib.cache is None or lib.lib is None:
            return
        if any(t is not None and t.isRunning() for t in (lib.cache_loader, lib.global_loader)):
            return
        gdir = self._settings.get("global_dir")
        if not gdir or not Path(gdir).exists():
            return
        if planner.music.scan_caches.global_index_count() == 0:
            return
        self._pending_drop = None   # no load runs, so nothing waits yet
        self._pending_after_global = None
        loader = GlobalCacheLoader(lib.cache, self, share_from=lib.lib)
        lib.cache_loader = lib.preloader = loader
        loader.done.connect(self._on_global_preloaded)
        loader.error.connect(self._on_global_preload_error)
        loader.start()

    def _on_global_preloaded(self, lib: MusicLibrary):
        busy, self._library.preload_busy = self._library.preload_busy, None
        whole, self._library.whole_waiting = self._library.whole_waiting, False
        if whole:
            self._lib_browser.show_whole_loading(False)
        if busy is not None:
            busy.finish()   # someone asked meanwhile: theirs, as if they had loaded it
        elif not lib.entries and whole and self._library.global_lib is None:
            # 🌐 waited for an empty index: walk, as its click would have.
            self._pending_after_global = self._show_whole_library
            self._start_global_scan()
            return
        elif not lib.entries or self._library.global_lib is not None:
            # No walk unasked, and a 🔄 finished first is newer.
            if whole and self._library.global_lib is not None:
                self._lib_browser.set_whole_entries(self._library.global_lib.entries)
            return
        self._use_cached_global(lib)
        if whole and self._library.global_lib is not None:
            self._lib_browser.set_whole_entries(self._library.global_lib.entries)

    def _on_global_preload_error(self, msg: str):
        log.warning("🌐 Loading the whole library in the background failed:\n%s", msg)
        busy, self._library.preload_busy = self._library.preload_busy, None
        whole, self._library.whole_waiting = self._library.whole_waiting, False
        if whole:
            self._lib_browser.show_whole_loading(False)
        if busy is None and not whole:
            return   # nobody waited for it; the next 🌐 loads it again
        if busy is not None:
            busy.finish()
        self._pending_drop = None
        self._pending_after_global = None
        self.statusBar().showMessage("Global index failed.")
        QMessageBox.critical(self, "Global Index Error", msg)

    def _on_global_cache_loaded(self, lib: MusicLibrary):
        if self._busy:
            self._busy.finish()
        self._use_cached_global(lib)

    def _use_cached_global(self, lib: MusicLibrary):
        # Cold / empty cache → fall back to a full scan.
        if not lib.entries:
            self._start_global_scan(self._pending_drop)
            return
        if self._library.lib is not None:
            lib.share_playlist_index_from(self._library.lib)
        self._library.global_lib = lib
        self._refresh_library_status()
        self.statusBar().showMessage(
            i18n.t("Global library ready from cache — %s files.") % f"{len(lib.entries):,}")
        drop = self._pending_drop
        self._pending_drop = None
        if drop:
            self._start_similar_worker(drop, lib)
        self._run_pending_after_global()

    def _on_global_ready(self, lib: MusicLibrary):
        if self._busy:
            self._busy.finish()
        if self._library.lib is not None:
            lib.share_playlist_index_from(self._library.lib)
        self._library.global_lib = lib
        n      = len(lib.entries)
        cached = sum(1 for e in lib.entries if e.features is not None)
        self._refresh_library_status()   # add the global-index line to the label
        self.statusBar().showMessage(
            i18n.t("Global index: %s files, %s analyzed.") % (f"{n:,}", f"{cached:,}"))
        drop = self._pending_drop
        self._pending_drop = None
        if drop:
            self._start_similar_worker(drop, lib)
        self._run_pending_after_global()

    def _run_pending_after_global(self):
        """Resume an index build that was waiting for the repository to load."""
        after = self._pending_after_global
        self._pending_after_global = None
        if after:
            after()

    def _on_global_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        self._pending_drop = None
        self._pending_after_global = None
        self.statusBar().showMessage("Global index failed.")
        QMessageBox.critical(self, "Global Index Error", msg)

    def _on_global_cancelled(self):
        if self._busy:
            self._busy.finish()
        self._pending_drop = None
        self._pending_after_global = None
        self.statusBar().showMessage("Repository scan cancelled.")

    def _build_global_index(self, values: dict):
        """Settings → 'Build / refresh librosa index': analyze missing audio.

        Asks whether to cover the whole repository, the favorites library, or
        both. 'local' analyzes the already-scanned favorites library directly;
        'global'/'both' scan the repo first, then analyze (scope honoured in
        `_on_global_index_scanned`). Read-only — only the feature cache is written.
        """
        save_settings(values)
        self._settings = values
        scope = self._ask_index_scope("Build / refresh librosa audio index")
        if scope is None:
            return
        self._librosa_scope = scope
        if scope == "local":
            entries, label = self._scoped_pool("local", "Build librosa index")
            if entries is None:
                return
            self._run_librosa_analysis(entries, label)
            return
        gdir = values.get("global_dir")
        if not gdir or not Path(gdir).exists():
            QMessageBox.warning(
                self, "Build librosa index",
                "Set a valid music repository folder first."
            )
            return
        if self._library.global_loader and self._library.global_loader.isRunning():
            return
        self._busy = BusyDialog(self, "Scanning repository…", cancelable=True)
        self._library.global_loader = GlobalLibraryLoader(self._library.cache, gdir, self,
                                                          share_from=self._library.lib)
        self._busy.cancel_requested.connect(self._library.global_loader.cancel)
        self._busy.show_after(300)
        self._library.global_loader.progress.connect(self._on_global_scan_progress)
        self._library.global_loader.done.connect(self._on_global_index_scanned)
        self._library.global_loader.error.connect(self._on_global_error)
        self._library.global_loader.cancelled.connect(self._on_global_cancelled)
        self._library.global_loader.start()

    def _on_global_scan_progress(self, done: int, total: int, name: str, reused: bool):
        if not self._busy:
            return
        tag = "♻️ " if reused else "🔍 "
        self._busy.set_progress(done, total, tag + name)
        if total > 0:
            self.statusBar().showMessage(
                i18n.t("Scanning repository… %s/%s  (%s left)")
                % (f"{done:,}", f"{total:,}", f"{total - done:,}"))

    def _on_global_index_scanned(self, lib: MusicLibrary):
        if self._busy:
            self._busy.finish()
        if self._library.lib is not None:
            lib.share_playlist_index_from(self._library.lib)
        self._library.global_lib = lib
        self._refresh_library_status()
        # 'both' analyzes the repo + favorites library together (deduped by path).
        scope = getattr(self, "_librosa_scope", "global")
        if scope == "both" and self._library.lib is not None and self._library.lib.entries:
            seen = set()
            entries = []
            for e in list(lib.entries) + list(self._library.lib.entries):
                k = str(e.path)
                if k in seen:
                    continue
                seen.add(k)
                entries.append(e)
            label = i18n.t("the whole repository + favorites library")
        else:
            entries = lib.entries
            label = i18n.t("the whole repository")
        self._run_librosa_analysis(entries, label)

    # ── ⚙ Settings, the restart offer and the maintenance jobs ──────────────────
    def _open_settings(self, open_sound=False, open_cartwall=False):
        n_unanalyzed = (sum(1 for e in self._library.lib.entries if e.features is None)
                        if self._library.lib else 0)
        given = dict(self._settings)
        dlg = SettingsDialog({**self._settings, **self.cart_wall_settings()},
                             self, build_cb=self._build_global_index,
                             embed_cb=self._build_embedding_index,
                             index_summary=self._index_summary(),
                             all_cb=self._build_all_caches,
                             maintenance_cb=self._run_db_maintenance,
                             relearn_cb=self._relearn_playlists,
                             rescan_cb=self._rescan_repository,
                             analyze_cb=self._analyze_audio,
                             loudness_cb=self._analyze_loudness,
                             silence_cb=self._analyze_silences,
                             pd_cb=self._analyze_pd_highlights,
                             vocals_cb=self._analyze_vocals,
                             gaps_cb=self._show_library_gaps,
                             n_unanalyzed=n_unanalyzed,
                             pd_export_cb=self._export_manual_pd,
                             pd_import_cb=self._import_manual_pd,
                             backup_restore_cb=self._restore_user_data,
                             venue_export_cb=self._export_venue_pack,
                             venue_import_cb=self._import_venue_pack,
                             remote_cb=self.start_remote_server,
                             remote_running=lambda: self._remote is not None,
                             remote_stop_cb=lambda: self.set_remote_running(False),
                             remote_changed=self.remote_hub().changed,
                             guests_cb=self.open_guest_window,
                             controller_cb=self.open_controller_window,
                             desk_keys_cb=self.open_desk_keys_window,
                             announce_test_cb=self._announce_test,
                             open_sound=open_sound,
                             open_cartwall=open_cartwall,
                             reset_cb=self._reset_database)
        # 📊 Library gaps runs from inside this dialog and may want it out of the
        # way (see _show_library_gaps) — leave it a handle while it is open.
        self._settings_dlg = dlg
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        self._settings_dlg = None
        if not accepted:
            dlg.deleteLater()
            return
        # Only what the operator changed in the dialog: it hands back the whole
        # dict as it was when it opened, and the evening went on behind it —
        # the 🔕 guard's record of the devices it muted, the master fader.
        values = dlg.values()
        # 🎛 The wall's fade-out and colour are the wall's, kept in its own file.
        wall = {k: values.pop(k) for k in CART_WALL_KEYS if k in values}
        edited = {k: v for k, v in values.items()
                  if k not in given or given[k] != v}
        new = {**self._settings, **edited}
        lib_changed    = new.get("library_dir") != self._settings.get("library_dir")
        global_changed = new.get("global_dir")  != self._settings.get("global_dir")
        pl_changed     = new.get("playlist_dir") != self._settings.get("playlist_dir")
        hidden_changed = (new.get("hidden_folders") or []) != (self._settings.get("hidden_folders") or [])
        mode_changed   = new.get("app_mode") != self._settings.get("app_mode")
        backend_changed = (media_backend_of(new)
                           != media_backend_of(self._settings))
        look_changed = (theme.theme_of(new) != theme.theme_of(self._settings)
                        or theme.accent_of(new) != theme.accent_of(self._settings)
                        or i18n.language_of(new) != i18n.language_of(self._settings)
                        or bool(new.get("german_dance_terms"))
                        != bool(self._settings.get("german_dance_terms"))
                        # The same pick, but the running look itself edited
                        # or deleted: saved already, shown after a restart.
                        or dlg.running_look_touched())
        # Read out: it goes now. It hangs off this window, so otherwise every
        # opening left one more dialog alive, still following the remote hub.
        # Not on its own `finished`: Qt runs that delete as exec() returns,
        # before values() above.
        dlg.deleteLater()
        old = self._settings
        self._settings = new
        save_settings(new)
        self._follow_play_sets(old, new)   # 🎛 lists on a set edited move with it
        self._autosave_playlist()
        planner.playlist.m3u.set_m3u_format(new.get("m3u_format"))
        set_no_class_exclusion(new.get("exclude_no_class"))
        set_dblclick_action(new.get("dblclick_action"))
        set_hidden_folders(new.get("hidden_folders"))
        self._audio_device.sync()   # 🔊 a changed output choice, at once
        self._sync_dance_len()      # 🏆 per-dance lengths edited: the panel shows them
        self._sync_big_player_limit()
        self._set_artwork_shown(bool(new.get("show_artwork", True)))
        self._set_waveform_shown(bool(new.get("show_waveform", True)))
        self.apply_duck_level()     # 🔉 the buttons name it; a held duck moves to it
        self.apply_cart_settings()  # 🎶 background pads: stop or mute under a title
        self.apply_cart_wall(wall)  # ⏱ 🖌 the wall's fade-out and colour
        if "presenter_theme" in edited:   # 🖥 an open presenter repaints at once
            self._theme_presenter(edited["presenter_theme"])
        error_reports.apply_settings(new)   # 🐞 on or off at once, no restart
        planner.music.db_upkeep.apply_settings(new)   # 💾 the next backup goes there
        if mode_changed:
            # Only visibility — no restart needed, both sides stay wired up.
            self._apply_app_mode()
        if global_changed or hidden_changed:
            self._library.global_lib = None   # force a rebuild of the global index on next use
        if pl_changed and new.get("playlist_dir"):
            # Apply right away: repoint the learning dir, then rebuild the
            # popularity / co-occurrence index from it (no library rescan).
            planner.config.set_playlist_dir(new["playlist_dir"])
            self._relearn_playlists()
        if lib_changed:
            QMessageBox.information(
                self, "Settings saved",
                "The favorites library path changed.\n"
                "Restart the app to load the new library."
            )
        # Apply the preview-player toggle immediately — don't wait for the next ▶.
        if self._preview:
            if not new.get("preview_player", True):
                self._preview.hide()
            else:
                self._sync_preview_to_playback()
        # ▶ …the player's dock, if it moved.
        self._apply_player_layout()
        # 🎙 …and the announcement voice: the next call is made in it, and the
        # panel names it under 🔈, with where the call sits against the music.
        voice = str(new.get("announce_voice", "random"))
        self._announcer.set_voice(voice)
        self._play_panel.set_announce_style(
            voice, bool(new.get("announce_heat", False)),
            bool(new.get("announce_wait", False)))
        self._refresh_library_status()   # reflect any search-mode change in the label
        self.statusBar().showMessage("Settings saved.")
        self._offer_settings_restart(backend_changed, look_changed, hidden_changed)

    def _offer_settings_restart(self, backend_changed, look_changed, hidden_changed=False):
        """🔊/🎨/🙈 Offer the restart a startup-only setting needs, last of all."""
        if backend_changed:
            # Last, so everything else is applied and saved before the app may
            # go down: the backend is picked at startup and nowhere else.
            self._offer_restart(
                "🔊 Audio backend",
                "The audio backend is chosen when the app starts, so the new "
                "one takes over after a restart.\n\n"
                "Restart now?")
        elif look_changed:
            # Same reason: the stylesheet hook and the shared row colours are
            # put in place before the first widget is built, so the windows
            # already standing keep the look they were made with.
            self._offer_restart(
                "🎨 Look",
                "The theme, the accent colour and the language are applied "
                "while the app starts, so they take over after a restart.\n\n"
                "Restart now?")
        elif hidden_changed:
            # The favorites are scanned once, at startup: the next load is
            # what leaves the excluded folders out (or brings them back).
            self._offer_restart(
                "🙈 Excluded folders",
                "The library is loaded when the app starts, so the excluded "
                "folders change with the next start.\n\n"
                "Restart now?")

    def _offer_restart(self, title: str, question: str):
        """Ask whether to restart for a setting that only takes effect at
        startup, and do it. The window is closed FIRST — if the operator backs
        out of that (an unsaved playlist, say), nothing is restarted and they
        keep the app they were in."""
        ans = QMessageBox.question(
            self, title, question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if ans != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage(
                "Saved — it takes effect the next time you start the app.")
            return
        if not self.close():
            return
        if restart_app():
            QApplication.quit()
        else:
            QMessageBox.warning(
                None, title,
                "Could not start a new instance — please start the app again "
                "yourself.")

    # ── Maintenance (⚙ Settings) ──────────────────────────────────────────────
    def _run_db_maintenance(self):
        """🧹 Clean up database: orphan cleanup + VACUUM, off the UI thread."""
        db_file = planner.config.audio_db_file()
        size_mb = db_file.stat().st_size / 1e6 if db_file.exists() else 0.0
        ans = QMessageBox.question(
            self, "Clean up database",
            i18n.t("Remove cached data of deleted music files and compact "
                   "%s (%s MB)?") % (db_file.name, f"{size_mb:,.0f}") + "\n\n"
            + i18n.t("Feature vectors, embeddings and loudness of files that no longer "
                     "exist on disk are removed for good (they would simply be re-analyzed "
                     "if the files ever come back). Compacting can take a few minutes."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._busy = BusyDialog(self, "Cleaning up database…")
        self._busy.show_after(200)
        self._maint_worker = DbMaintenanceWorker(self)
        self._maint_worker.done.connect(self._on_maintenance_done)
        self._maint_worker.error.connect(self._on_maintenance_error)
        self._maint_worker.start()

    def _on_maintenance_done(self, res: dict):
        if self._busy:
            self._busy.finish()
        removed = res.get("removed", {})
        before = res.get("size_before", 0)
        after = res.get("size_after", 0)
        # Table names are not a report — say what was thrown away.
        lines = ", ".join(f"{i18n.t(_MAINT_LABELS.get(t, t))} {c:,}"
                          for t, c in removed.items() if c)
        QMessageBox.information(
            self, "Clean up database",
            i18n.t("🧹 Database compacted: %s MB → %s MB (%s MB freed).")
            % (f"{before / 1e6:,.1f}", f"{after / 1e6:,.1f}",
               f"{max(0, before - after) / 1e6:,.1f}") + "\n\n"
            + i18n.t("Removed rows: %s.")
            % (lines or i18n.t("none — everything is still in use")))
        self.statusBar().showMessage("Database cleanup done.")

    def _on_maintenance_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        QMessageBox.warning(self, "Clean up database",
                            i18n.t("Cleanup did not run:") + "\n\n" + msg)

    def _reset_database(self):
        """🗑 Reset database: the dialog picks the parts, a worker empties
        them, then the app restarts - its in-memory caches still hold the rows."""
        dlg = ResetDatabaseDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.chosen():
            return
        self._busy = BusyDialog(self, "Resetting database…")
        self._busy.show_after(200)
        self._maint_worker = DbResetWorker(dlg.chosen(), self)
        self._maint_worker.done.connect(self._on_reset_done)
        self._maint_worker.error.connect(self._on_reset_error)
        self._maint_worker.start()

    def _on_reset_done(self, removed: dict):
        if self._busy:
            self._busy.finish()
        lines = ", ".join(f"{i18n.t(_MAINT_LABELS.get(t, t))} {c:,}"
                          for t, c in removed.items() if c)
        self._offer_restart(
            "🗑 Reset database",
            i18n.t("Removed rows: %s.") % (lines or i18n.t("none")) + "\n\n"
            + i18n.t("The app still shows the old data until it restarts. "
                     "Restart now?"))

    def _on_reset_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        QMessageBox.warning(self, "🗑 Reset database",
                            i18n.t("Reset did not run:") + "\n\n" + msg)

    def _export_manual_pd(self):
        """📤 The hand-set Paso Doble highlights to a JSON file for another PC."""
        title = "Export manual PD marks"
        marks = self._library.cache.export_manual_pd() if self._library.cache else []
        if not marks:
            QMessageBox.information(self, title, "No Paso Doble highlight has been set by hand yet.")
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / "manual_pd_marks.json"),
            "JSON files (*.json);;All files (*)")
        if not chosen:
            return
        try:
            Path(chosen).write_text(
                json.dumps({"manual_pd_marks": marks}, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, title, i18n.t("Could not write the file:") + "\n\n" + str(exc))
            return
        log.info("📤 Manual PD marks exported\n"
                 "tracks: %d\n"
                 "file: %s", len(marks), chosen)
        QMessageBox.information(self, title,
                                i18n.t("📤 %d hand-set Paso Doble highlight(s) saved to:\n%s")
                                % (len(marks), chosen))

    def _import_manual_pd(self):
        """📥 Hand-set Paso Doble highlights from a file another PC exported."""
        title = "Import manual PD marks"
        if not self._library.cache:
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, title, str(Path.home()), "JSON files (*.json);;All files (*)")
        if not chosen:
            return
        try:
            marks = json.loads(Path(chosen).read_text(encoding="utf-8"))["manual_pd_marks"]
            n, found = self._library.cache.import_manual_pd(marks)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            QMessageBox.warning(self, title, i18n.t("This is no manual-PD-marks file:") + "\n\n" + str(exc))
            return
        log.info("📥 Manual PD marks imported\n"
                 "tracks: %d\n"
                 "found in this library: %d\n"
                 "file: %s", n, found, chosen)
        QMessageBox.information(self, title,
                                i18n.t("📥 %d hand-set Paso Doble highlight(s) imported — "
                                       "%d of them belong to a track this PC already knows.\n\n"
                                       "The others are kept and apply as soon as that "
                                       "music turns up here.") % (n, found))

    def _restore_user_data(self):
        """♻ Merge a daily user-data backup (tag edits, hand-set PD marks, play
        log) back in."""
        title = "Restore user data backup"
        chosen, _ = QFileDialog.getOpenFileName(
            self, title, str(planner.music.db_upkeep._backup_dir()),
            "Backups (user-data-*.db);;All files (*)")
        if not chosen:
            return
        try:
            edits, marks, plays = planner.music.db_upkeep.restore_user_data(Path(chosen))
        except ValueError as exc:
            QMessageBox.warning(self, title, i18n.t("This is no user data backup:") + "\n\n" + str(exc))
            return
        log.info("♻ User data backup restored\n"
                 "tag edits: %d\n"
                 "manual PD marks: %d\n"
                 "plays added: %d\n"
                 "file: %s", edits, marks, plays, chosen)
        QMessageBox.information(self, title,
                                i18n.t("♻ %d tag edit(s) and %d hand-set Paso Doble highlight(s) "
                                       "restored, %d played title(s) added to the play log.\n\n"
                                       "They take effect after a restart of the app.")
                                % (edits, marks, plays))

    def _relearn_playlists(self):
        """📜 Rebuild playlist popularity from the M3U folder — no library rescan."""
        if self._library_still_loading():
            return
        if self._library.lib is None:
            QMessageBox.information(self, "Re-learn playlists",
                                    "The library is still loading — try again in a moment.")
            return
        worker = getattr(self, "_relearn_worker", None)
        if worker is not None and worker.isRunning():
            return   # one at a time — the busy dialog shows only after 200 ms
        self._busy = BusyDialog(self, "Re-learning playlist popularity…")
        self._busy.show_after(200)
        self._relearn_worker = PlaylistRelearnWorker(self._library.lib, self)
        self._relearn_worker.done.connect(self._on_relearn_done)
        self._relearn_worker.error.connect(self._on_relearn_error)
        self._relearn_worker.start()

    def _on_relearn_done(self, learned):
        if self._busy:
            self._busy.finish()
        lib = self._library.lib
        if lib is None:
            return      # the library went away while the worker ran
        n = lib.adopt_playlist_index(learned)
        # The global library borrows the competition library's playlist index —
        # re-share so 'based on my playlist history' sees the fresh counts too.
        if self._library.global_lib is not None:
            self._library.global_lib.share_playlist_index_from(lib)
        self._refresh_library_status()
        self.statusBar().showMessage(
            i18n.t("Playlist popularity re-learned from %s playlists.") % f"{n:,}")
        QMessageBox.information(
            self, "Re-learn playlists",
            i18n.t("📜 %s playlists analyzed (M3U files + tournament folders) — "
                   "popularity and co-occurrence are "
                   "up to date, so a just-exported tournament counts now.\n\n"
                   "Rows already in the grid keep their old Pop value until regenerated.")
            % f"{n:,}")

    def _on_relearn_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        QMessageBox.warning(self, "Re-learn playlists",
                            i18n.t("Re-learn failed:") + "\n\n" + msg)
