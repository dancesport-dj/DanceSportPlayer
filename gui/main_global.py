"""Global library, audio/index analysis, similar search, settings.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import importlib.util
import json
import logging

import planner.config
import planner.db

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
from planner.db import AudioCache, HAS_LIBROSA
from planner.library import MusicLibrary
from shared import error_reports, theme
from planner import i18n
from gui.common import (
    BusyDialog,
    apply_taskbar_icon,
)
from gui.index_summary import index_summary
from gui.dialogs import (  # auto-resolved
    SettingsDialog,
    SimilarTracksDialog,
    media_backend_of,
    restart_app,
)
from shared.stores import (
    save_settings,
)
from planner.vocals import (
    apply_vocal_shares,
    learn_instrumental_probs,
)
from gui.workers import (  # auto-resolved
    DbMaintenanceWorker,
    GlobalCacheLoader,
    GlobalLibraryLoader,
    PlaylistRelearnWorker,
    SimilarFromFileWorker,
)
from gui.main_allcache import (
    AllCacheMixin,
    plan_allcache_steps,  # noqa: F401 — re-exported for existing callers
)
from gui.main_analyze import AnalysisMixin
from gui.main_embed import EmbeddingIndexMixin

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

    What is RUN over them lives next door: 🔬 the analyses (gui.main_analyze),
    🧠 the indexes (gui.main_embed) and 🧱 build-all (gui.main_allcache).
    MainWindow keeps importing this one name.
    """

    def _on_library_loaded(self, lib: MusicLibrary, cache: AudioCache):
        self._lib   = lib
        self._cache = cache
        for t in self._all_tables:
            t._cache = cache   # enable chained drops in the similar-tracks dialog
        n          = len(lib.entries)
        comp       = sum(1 for e in lib.entries if e.dance is not None)
        cached     = sum(1 for e in lib.entries if e.features is not None)

        # Only what the window is unusable without happens in front of the
        # splash: the playlist the last session was left on. Everything else —
        # the browser list, the vocal learning, the counting of what is
        # analyzed — used to run here too, and every second of it was a second
        # of staring at a splash screen. It now runs behind the open window and
        # says where it is in the status bar.
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
        # An f-string is never a catalog key, so the hook on showMessage had
        # nothing to match and a German screen ended its startup in English.
        self._finish_library_load(
            lib, i18n.t("Library loaded — %s MP3 files, %s favorites songs, "
                        "%s audio cached.") % (n, comp, cached))

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
                      apply_vocal_shares(lib.entries, self._cache))),
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
                return
            msg, fn = steps[i]
            self.statusBar().showMessage(msg)
            QTimer.singleShot(0, lambda: (fn(), run(i + 1)))

        run()

    def _mode_line(self) -> str:
        """Human-readable description of which library similarity searches hit."""
        if self._settings.get("global_search"):
            return i18n.t("🌐  Search mode: Global — whole repository")
        return i18n.t("🎯  Search mode: Favorites library only")

    def _refresh_library_status(self, enable_generate: bool = False):
        """Recompose the ConfigPanel status label (mode + counts + per-model index)."""
        if not self._lib:
            return
        n          = len(self._lib.entries)
        comp       = sum(1 for e in self._lib.entries if e.dance is not None)
        cached     = sum(1 for e in self._lib.entries if e.features is not None)
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
            i18n.t("📊 Loudness: %s") % summ["loudness"],
            i18n.t("🔇 Silences: %s") % summ["silences"],
            i18n.t("🐂 PD highlights: %s") % summ["pd"],
            i18n.t("🧠 OpenL3: %s") % summ["openl3"]))
        if self._cache is not None and self._cache.vocal_share_count():
            status += "\n" + i18n.t("🎙️ Demucs vocals: %s measured") % (
                f"{self._cache.vocal_share_count():,}")
        self._cfg.set_library_status(status, enable_generate=enable_generate,
                                     n_unanalyzed=unanalyzed,
                                     needs_build=bool(summ.get("favorites_gap")))

    def _index_summary(self) -> dict:
        return index_summary(self._cache, self._embedding_store(),
                             self._lib, self._global_lib)

    def _global_index_line(self) -> str:
        """One-line global-repo index state — shown in every mode."""
        if self._global_lib is not None:
            gn = len(self._global_lib.entries)
            gc = sum(1 for e in self._global_lib.entries if e.features is not None)
            return i18n.t("🌐 Global index: %s files, %s analyzed") % (
                f"{gn:,}", f"{gc:,}")
        built = planner.db.global_index_count()
        if built:
            return i18n.t("🌐 Global index: %s files built "
                          "(loads on first global search)") % f"{built:,}"
        return i18n.t("🌐 Global index: not built (⚙ Settings to build)")

    def _on_library_error(self, msg: str):
        self._loading_dlg.accept()   # accept() bypasses closeEvent
        self.show()
        apply_taskbar_icon(self)
        self._cfg.set_library_status(f"Error loading library:\n{msg}")
        self.statusBar().showMessage(i18n.t("Library error: %s") % msg)
        QMessageBox.critical(self, "Library Load Error", msg)

    def _on_file_dropped(self, path: str):
        if not self._lib or not self._cache:
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
            if self._global_lib is not None:
                self._start_similar_worker(path, self._global_lib)
            else:
                self._ensure_global_lib(then_drop=path)
        else:
            self._start_similar_worker(path, self._lib)

    def _start_similar_worker(self, path: str, lib: MusicLibrary):
        self._sim_lib = lib
        self.statusBar().showMessage(i18n.t("Analyzing %s …") % Path(path).name)
        self._busy = BusyDialog(self, i18n.t("Analyzing %s …") % Path(path).name)
        self._busy.show_after(500)
        self._sim_worker = SimilarFromFileWorker(
            lib, self._cache, path, n=100, min_display=0.5, parent=self)
        self._sim_worker.done.connect(self._on_similar_ready)
        self._sim_worker.error.connect(self._on_similar_error)
        self._sim_worker.start()

    def _on_similar_ready(self, source, results):
        if self._busy:
            self._busy.finish()
        search_lib = getattr(self, "_sim_lib", None) or self._lib
        scope = (i18n.t("the whole repository") if search_lib is self._global_lib
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
                    if search_lib is self._global_lib else
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
        SimilarTracksDialog(source, results, self, play_cb=self._play_or_stop,
                            lib=search_lib, cache=self._cache, seek_cb=self._seek,
                            is_global=(search_lib is self._global_lib),
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
        if self._cache is not None and planner.db.global_index_count() > 0:
            if getattr(self, "_cache_loader", None) and self._cache_loader.isRunning():
                return
            self._pending_drop = then_drop
            self._busy = BusyDialog(self, "Loading repository from cache…")
            self._busy.show_after(200)
            self._cache_loader = GlobalCacheLoader(self._cache, self)
            self._cache_loader.done.connect(self._on_global_cache_loaded)
            self._cache_loader.error.connect(self._on_global_error)
            self._cache_loader.start()
            return
        self._start_global_scan(then_drop)

    def _start_global_scan(self, then_drop: str | None = None):
        """Full repository walk (cold cache or explicit rebuild) with progress."""
        gdir = self._settings.get("global_dir")
        if not gdir or not Path(gdir).exists():
            return
        self._pending_drop = then_drop
        if self._global_loader and self._global_loader.isRunning():
            return
        self._busy = BusyDialog(self, "Indexing whole repository…", cancelable=True)
        self._global_loader = GlobalLibraryLoader(self._cache, gdir, self)
        self._busy.cancel_requested.connect(self._global_loader.cancel)
        self._busy.show_after(300)
        self._global_loader.progress.connect(self._on_global_scan_progress)
        self._global_loader.done.connect(self._on_global_ready)
        self._global_loader.error.connect(self._on_global_error)
        self._global_loader.cancelled.connect(self._on_global_cancelled)
        self._global_loader.start()

    def _on_global_cache_loaded(self, lib: MusicLibrary):
        if self._busy:
            self._busy.finish()
        # Cold / empty cache → fall back to a full scan.
        if not lib.entries:
            self._start_global_scan(self._pending_drop)
            return
        if self._lib is not None:
            lib.share_playlist_index_from(self._lib)
        self._global_lib = lib
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
        if self._lib is not None:
            lib.share_playlist_index_from(self._lib)
        self._global_lib = lib
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
        if self._global_loader and self._global_loader.isRunning():
            return
        self._busy = BusyDialog(self, "Scanning repository…", cancelable=True)
        self._global_loader = GlobalLibraryLoader(self._cache, gdir, self)
        self._busy.cancel_requested.connect(self._global_loader.cancel)
        self._busy.show_after(300)
        self._global_loader.progress.connect(self._on_global_scan_progress)
        self._global_loader.done.connect(self._on_global_index_scanned)
        self._global_loader.error.connect(self._on_global_error)
        self._global_loader.cancelled.connect(self._on_global_cancelled)
        self._global_loader.start()

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
        if self._lib is not None:
            lib.share_playlist_index_from(self._lib)
        self._global_lib = lib
        self._refresh_library_status()
        # 'both' analyzes the repo + favorites library together (deduped by path).
        scope = getattr(self, "_librosa_scope", "global")
        if scope == "both" and self._lib is not None and self._lib.entries:
            seen = set()
            entries = []
            for e in list(lib.entries) + list(self._lib.entries):
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
    def _open_settings(self):
        n_unanalyzed = (sum(1 for e in self._lib.entries if e.features is None)
                        if self._lib else 0)
        given = dict(self._settings)
        dlg = SettingsDialog(self._settings, self, build_cb=self._build_global_index,
                             embed_cb=self._build_embedding_index,
                             index_summary=self._index_summary(),
                             all_cb=self._build_all_caches,
                             maintenance_cb=self._run_db_maintenance,
                             relearn_cb=self._relearn_playlists,
                             analyze_cb=self._analyze_audio,
                             loudness_cb=self._analyze_loudness,
                             silence_cb=self._analyze_silences,
                             pd_cb=self._analyze_pd_highlights,
                             vocals_cb=self._analyze_vocals,
                             gaps_cb=self._show_library_gaps,
                             n_unanalyzed=n_unanalyzed,
                             pd_export_cb=self._export_manual_pd,
                             pd_import_cb=self._import_manual_pd)
        # 📊 Library gaps runs from inside this dialog and may want it out of the
        # way (see _show_library_gaps) — leave it a handle while it is open.
        self._settings_dlg = dlg
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        self._settings_dlg = None
        if not accepted:
            return
        # Only what the operator changed in the dialog: it hands back the whole
        # dict as it was when it opened, and the evening went on behind it —
        # the 🔕 guard's record of the devices it muted, the master fader.
        edited = {k: v for k, v in dlg.values().items()
                  if k not in given or given[k] != v}
        new = {**self._settings, **edited}
        lib_changed    = new.get("library_dir") != self._settings.get("library_dir")
        global_changed = new.get("global_dir")  != self._settings.get("global_dir")
        pl_changed     = new.get("playlist_dir") != self._settings.get("playlist_dir")
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
        self._settings = new
        save_settings(new)
        error_reports.apply(new)   # 🐞 on or off at once, no restart
        if mode_changed:
            # Only visibility — no restart needed, both sides stay wired up.
            self._apply_app_mode()
        if global_changed:
            self._global_lib = None   # force a rebuild of the global index on next use
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
        # 🎙 …and the advanced voice controls: shown or gone on the panel now.
        self._play_panel.set_voice_advanced_shown(
            bool(new.get("announce_advanced", False)))
        self._refresh_library_status()   # reflect any search-mode change in the label
        self.statusBar().showMessage("Settings saved.")
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
        db_file = planner.config.AUDIO_DB_FILE
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

    def _export_manual_pd(self):
        """📤 The hand-set Paso Doble highlights to a JSON file for another PC."""
        title = "Export manual PD marks"
        marks = self._cache.export_manual_pd() if self._cache else []
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
        if not self._cache:
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, title, str(Path.home()), "JSON files (*.json);;All files (*)")
        if not chosen:
            return
        try:
            marks = json.loads(Path(chosen).read_text(encoding="utf-8"))["manual_pd_marks"]
            n, found = self._cache.import_manual_pd(marks)
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

    def _relearn_playlists(self):
        """📜 Rebuild playlist popularity from the M3U folder — no library rescan."""
        if self._lib is None:
            QMessageBox.information(self, "Re-learn playlists",
                                    "The library is still loading — try again in a moment.")
            return
        self._busy = BusyDialog(self, "Re-learning playlist popularity…")
        self._busy.show_after(200)
        self._relearn_worker = PlaylistRelearnWorker(self._lib, self)
        self._relearn_worker.done.connect(self._on_relearn_done)
        self._relearn_worker.error.connect(self._on_relearn_error)
        self._relearn_worker.start()

    def _on_relearn_done(self, n: int):
        if self._busy:
            self._busy.finish()
        # The global library borrows the competition library's playlist index —
        # re-share so 'based on my playlist history' sees the fresh counts too.
        if self._global_lib is not None:
            self._global_lib.share_playlist_index_from(self._lib)
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
