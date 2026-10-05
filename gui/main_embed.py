"""🧠 The search indexes: the librosa vectors and the deep embeddings.

Split off gui/main_global.py as a MainWindow mixin — the scope chooser both
builds share, the pools it hands them and the OpenL3 / Chroma runs.
"""
import importlib.util
import logging


HAS_MULTIMEDIA = importlib.util.find_spec("PySide6.QtMultimedia") is not None

from PySide6.QtWidgets import (
    QMessageBox,
)
from collections.abc import Callable
from gui.common import (
    BusyDialog,
    _fmt_duration,
)
from planner import i18n
from gui.workers import (  # auto-resolved
    AudioAnalyzer,
    EmbeddingIndexWorker,
)

log = logging.getLogger("dancesport.gui.embed")


class EmbeddingIndexMixin:
    """🧠 The librosa and deep-embedding indexes, and their scope."""

    def _embedding_store(self):
        """Lazily-created EmbeddingStore for read-only coverage queries."""
        if getattr(self, "_emb_store_cache", None) is None and self._cache is not None:
            try:
                from planner import embeddings as ae
                self._emb_store_cache = ae.EmbeddingStore(self._cache)
            except Exception:
                self._emb_store_cache = None
        return getattr(self, "_emb_store_cache", None)

    def _run_librosa_analysis(self, entries, scope_label: str):
        """Analyze any entries missing librosa features (read-only) with progress."""
        to_do = [e for e in entries if e.features is None]
        if not to_do:
            QMessageBox.information(
                self, "Audio index",
                i18n.t("All %s files in %s are already analyzed.")
                % (f"{len(entries):,}", scope_label))
            return
        why = self._librosa_unavailable(to_do)
        if why:
            QMessageBox.warning(self, "Audio analysis unavailable", why)
            return
        eta_min = max(1, int(len(to_do) * 0.8 / 60))
        ans = QMessageBox.question(
            self, "Build audio index",
            i18n.t("%s of %s files in %s need analysis (~%s min).\n\n"
                   "Analysis only reads your files — never modifies them. "
                   "Results are cached.\n\nRun now?")
            % (f"{len(to_do):,}", f"{len(entries):,}", scope_label, eta_min),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._index_scope_label = scope_label
        self.statusBar().showMessage(
            i18n.t("Audio index: analyzing %s files…") % len(to_do))
        self._busy = BusyDialog(
            self, i18n.t("Building audio index (%s)…") % scope_label, cancelable=True)
        self._index_analyzer = AudioAnalyzer(self._cache, entries, self)
        self._busy.cancel_requested.connect(self._index_analyzer.cancel)
        self._busy.show_after(300)
        self._index_analyzer.progress.connect(self._on_index_progress)
        self._index_analyzer.done.connect(self._on_index_done)
        self._index_analyzer.cancelled.connect(self._on_index_cancelled)
        self._index_analyzer.start()

    def _on_index_progress(self, done: int, total: int, errors: int, name: str, eta: float):
        if self._busy:
            self._busy.set_progress(done, total, "🔬 " + name, eta)
        eta_txt = (i18n.t("  ~%s left") % _fmt_duration(eta)) if eta >= 0 else ""
        self.statusBar().showMessage(
            i18n.t("Global index: %s/%s%s") % (done, total, eta_txt)
            + ((i18n.t("  (%s errors)") % errors) if errors else ""))

    def _on_index_done(self, ok: int, errors: int):
        if self._busy:
            self._busy.finish()
        self._refresh_library_status()
        scope_label = getattr(self, "_index_scope_label",
                              i18n.t("the whole repository"))
        self.statusBar().showMessage(
            i18n.t("Audio index built — %s files analyzed") % ok
            + ((i18n.t(", %s errors") % errors) if errors else ""))
        QMessageBox.information(
            self, "Audio index ready",
            i18n.t("Analyzed %s files in %s") % (ok, scope_label)
            + ((i18n.t(" (%s errors)") % errors) if errors else "")
            + i18n.t(".\nSimilarity search will now match across them."))

    def _on_index_cancelled(self, done_so_far: int):
        if self._busy:
            self._busy.finish()
        self._refresh_library_status()
        self.statusBar().showMessage(
            i18n.t("Audio index cancelled — %s files analyzed so far "
                   "(progress is cached).") % done_so_far)

    # ── Index scope chooser (shared by the librosa + embedding builds) ──────────
    def _ask_index_scope(self, title: str) -> str | None:
        """Ask which library an index build should cover.

        Returns 'global' (whole repo), 'local' (favorites tanzcds library),
        'both', or None when the user cancels.
        """
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("Which library should this index cover?")
        box.setInformativeText(
            "🌐  Whole repository — every file under your music repo (global search).\n"
            "🎯  Favorites library — just your tanzcds folder.\n"
            "➕  Both — the repository and the favorites library.")
        b_global = box.addButton("🌐  Whole repository", QMessageBox.ButtonRole.AcceptRole)
        b_local = box.addButton("🎯  Favorites library", QMessageBox.ButtonRole.AcceptRole)
        b_both = box.addButton("➕  Both", QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_global:
            return "global"
        if clicked is b_local:
            return "local"
        if clicked is b_both:
            return "both"
        return None

    def _ensure_scope_loaded(self, scope: str, on_ready: Callable[[], None]) -> bool:
        """Make sure the library a scope needs is in memory before a build runs.

        Returns True when the pool is ready right now (the caller proceeds). For a
        'global'/'both' scope with the repository not yet loaded, it kicks off a
        lazy load from the warm cache and runs `on_ready` once it finishes, then
        returns False so the caller defers.
        """
        if scope in ("global", "both") and not (self._global_lib and self._global_lib.entries):
            self._ensure_global_lib(then_build=on_ready)
            return False
        return True

    def _scoped_pool(self, scope: str, name: str):
        """Resolve a scope choice to a deduped entry pool + a human label.

        Returns (entries, label); (None, "") with a message shown when the
        requested library isn't loaded yet.
        """
        glob = self._global_lib if (self._global_lib and self._global_lib.entries) else None
        comp = self._lib if (self._lib and self._lib.entries) else None
        if scope in ("global", "both") and glob is None:
            QMessageBox.information(
                self, name,
                "The whole-repository library isn't loaded yet. Drop a file (or build "
                "the librosa index over the repository) once to load it, then retry.")
            return None, ""
        if scope in ("local", "both") and comp is None:
            QMessageBox.information(self, name, "Favorites library isn't loaded yet.")
            return None, ""
        if scope == "global":
            return list(glob.entries), i18n.t("the whole repository")
        if scope == "local":
            return list(comp.entries), i18n.t("the favorites library")
        # both: union by path, repo first
        seen = set()
        pool = []
        for e in list(glob.entries) + list(comp.entries):
            k = str(e.path)
            if k in seen:
                continue
            seen.add(k)
            pool.append(e)
        return pool, i18n.t("the whole repository + favorites library")

    def _embedding_pool(self, scope: str, name: str):
        return self._scoped_pool(scope, name)

    # ── Deep-embedding index (OpenL3 / Chroma) from Settings ──────────────────────
    @staticmethod
    def _embed_model_name(model: str) -> str:
        from planner import embeddings as ae
        return {ae.MODEL_CHROMA: "Chroma"}.get(model, "OpenL3")

    def _build_embedding_index(self, vals: dict, model: str):
        """Build the OpenL3/Chroma embedding index over the active library.

        Uses the global repo when global search is on (and already loaded), else the
        favorites library. Read-only — only the embedding cache is written.
        """
        from planner import embeddings as ae
        name = self._embed_model_name(model)
        available = {ae.MODEL_CHROMA: ae.chroma_available}.get(
            model, ae.openl3_available)()
        if not available:
            QMessageBox.information(self, i18n.t("%s not installed") % name,
                                    ae.install_hint(model))
            return
        if self._cache is None:
            QMessageBox.information(self, name, "Audio cache not ready yet — try again shortly.")
            return
        # Let the user choose which library this index should cover.
        scope = self._ask_index_scope(f"Build {name} index")
        if scope is None:
            return
        # Repo scopes need the global library in memory — load it first if missing,
        # then resume here automatically.
        if not self._ensure_scope_loaded(
                scope, lambda: self._do_build_embedding_index(vals, model, scope)):
            return
        self._do_build_embedding_index(vals, model, scope)

    def _do_build_embedding_index(self, vals: dict, model: str, scope: str):
        """Continuation of `_build_embedding_index` once the scope's library is loaded."""
        from planner import embeddings as ae
        name = self._embed_model_name(model)
        pool, scope_label = self._embedding_pool(scope, name)
        if pool is None:
            return
        is_chroma = model == ae.MODEL_CHROMA
        how = ("Analyses the melody/harmony of each track once (slow the first time, "
               "then cached)." if is_chroma else
               "Loads a neural model and embeds each track once (slow the first time, "
               "then cached).")
        ans = QMessageBox.question(
            self, i18n.t("Build %s index") % name,
            i18n.t("Build the %s index over %s tracks from %s?")
            % (name, f"{len(pool):,}", scope_label) + "\n\n"
            + i18n.t(how) + " " + i18n.t("Reuses anything already computed.") + "\n\n"
            + i18n.t("Read-only — your audio files are never modified."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        store = ae.EmbeddingStore(self._cache)
        self.statusBar().showMessage(i18n.t("Building %s index…") % name)
        self._busy = BusyDialog(self, i18n.t("Building %s embedding index…") % name,
                                cancelable=True)
        self._emb_idx_worker = EmbeddingIndexWorker(store, model, pool, self)
        self._emb_idx_worker.progress.connect(
            lambda d, t, n, eta: self._busy and self._busy.set_progress(d, t, "🧠 " + n, eta))
        self._emb_idx_worker.done.connect(
            lambda computed, errors, first_error: self._on_embedding_index_done(
                name, computed, errors, first_error))
        self._emb_idx_worker.cancelled.connect(
            lambda done: self._on_embedding_index_cancelled(name, done))
        self._emb_idx_worker.error.connect(self._on_embedding_index_error)
        self._busy.cancel_requested.connect(self._emb_idx_worker.cancel)
        self._busy.show_after(300)
        self._emb_idx_worker.start()

    def _on_embedding_index_done(self, name: str, computed: int, errors: int, first_error: str):
        if self._busy:
            self._busy.finish()
        self._emb_store_cache = None        # drop stale mirror so labels reflect new vectors
        self._refresh_library_status()
        if computed == 0 and errors > 0:
            QMessageBox.critical(
                self, i18n.t("%s indexing failed") % name,
                i18n.t("All %d file(s) failed to embed.\n\nFirst error:\n%s\n\n"
                       "See the console log for the full traceback.")
                % (errors, first_error or i18n.t("unknown")))
            self.statusBar().showMessage(i18n.t("%s indexing failed.") % name)
            return
        self.statusBar().showMessage(
            i18n.t("%s index built — %d embedded, %d failed.") % (name, computed, errors)
            if errors else
            i18n.t("%s index built — %d embedded.") % (name, computed))
        QMessageBox.information(
            self, i18n.t("%s index ready") % name,
            (i18n.t("Embedded %d track(s) (%d failed — see log).") % (computed, errors)
             if errors else i18n.t("Embedded %d track(s).") % computed)
            + "\n" + i18n.t("The %s method is now ready in the Similar-Tracks window.")
            % name)

    def _on_embedding_index_cancelled(self, name: str, done: int):
        if self._busy:
            self._busy.finish()
        # Partial progress IS cached — refresh the coverage labels to reflect it.
        self._emb_store_cache = None
        self._refresh_library_status()
        self.statusBar().showMessage(
            i18n.t("%s indexing cancelled — %d embedded so far (cached).") % (name, done))

    def _on_embedding_index_error(self, msg: str):
        if self._busy:
            self._busy.finish()
        QMessageBox.critical(self, "Embedding index error", msg)
