"""🧱 Build ALL caches: one click, every analysis, in a useful order.

Split off gui/main_global.py as a MainWindow mixin. The pipeline is a list of
steps walked one at a time, because each step is a worker that only reports back
when it is finished — and what it could NOT do has to survive to the closing
report.
"""
import importlib.util
import logging

import planner.db
from planner import i18n

HAS_MULTIMEDIA = importlib.util.find_spec("PySide6.QtMultimedia") is not None

from PySide6.QtCore import QEventLoop, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QMessageBox,
)
from gui.common import (
    BusyDialog,
)
from shared.stores import (  # auto-resolved
    save_settings,
)
from gui.workers import (  # auto-resolved
    AudioAnalyzer,
    AudioFpAnalyzer,
    EmbeddingIndexWorker,
    LoudnessAnalyzer,
    SilenceAnalyzer,
    PdHighlightAnalyzer,
)
from shared.audio_probes import find_ffmpeg

log = logging.getLogger("dancesport.gui.allcache")

# What 🧱 Build ALL caches runs, in order. Names double as the labels shown in
# the confirmation and the finished message — and as identity: they key
# st["reports"] and travel through _allcache_step_done. So they stay English
# here and go through i18n.t() where they are rendered.
_ALLCACHE_NAMES = {"audiofp": "audio fingerprints", "librosa": "librosa",
                   "loudness": "loudness", "silences": "silences",
                   "pd": "PD highlights", "openl3": "OpenL3", "chroma": "Chroma"}


def plan_allcache_steps(has_pd: bool, have_librosa: bool, have_ffmpeg: bool,
                        have_openl3: bool, have_chroma: bool) -> tuple:
    """(steps to run, what was left out and why) for the build-all pipeline.

    The playback caches come before the search indexes: they are the cheap ones
    and the ones a tournament actually needs, so cancelling halfway through
    leaves the useful half built. Demucs vocals are NOT in here — minutes per
    track against seconds, so they stay a deliberate, separate choice.
    """
    steps = []
    skipped = []
    if have_librosa:
        steps.append("librosa")
    else:
        # Grinding through the whole library only to fail on every single file
        # helps nobody — the caller has already said why in a dialog.
        skipped.append(i18n.t("librosa audio analysis (no working audio decoder)"))
    if have_ffmpeg:
        steps += ["loudness", "silences"]
    else:
        skipped.append(i18n.t("loudness + silences (no ffmpeg)"))
    if has_pd:
        steps.append("pd")     # nothing to detect in a library without Paso Dobles
    for key, available in (("openl3", have_openl3), ("chroma", have_chroma)):
        if available:
            steps.append(key)
        else:
            skipped.append(i18n.t("%s (not installed)")
                           % i18n.t(_ALLCACHE_NAMES[key]))
    if steps:
        # Cheapest of them all and dependent on nothing, so it leads — but only
        # where something is actually being built: it protects what the other
        # steps cache against the next tag edit, and on a machine that can build
        # nothing "nothing can be built" is still the honest answer.
        steps.insert(0, "audiofp")
    return steps, skipped


class _BusyWorker(QThread):
    """Runs one blocking stretch off the UI thread, so a wait bar can paint.

    Done on the UI thread — where both callers started life — the please-wait bar
    in front of the work never reaches its paint event and stands there as an
    empty white rectangle: showing a widget only queues the paint, and the work
    never hands the thread back.

    `fn` is called with a `say` for its captions; whatever it returns lands in
    `result`, and so does an exception, to be re-raised on the UI thread where it
    can still reach a message box.
    """

    step = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
        self.result = None            # the return value, or the exception

    def run(self):
        try:
            self.result = self._fn(self.step.emit)
        except Exception as exc:      # carried across and re-raised on the UI thread
            self.result = exc


class AllCacheMixin:
    """🧱 The build-all pipeline: one step at a time, failures kept."""

    # ── One-click: build ALL caches (librosa → ffmpeg probes → AI models) ───────
    def _build_all_caches(self, vals: dict):
        """Settings → 'Build ALL caches': run every index for one library in turn.

        Asks the scope once, then chains every analysis sequentially over the same
        pool. Models that aren't installed are skipped. Read-only — only the
        feature/embedding caches are written, never the audio files.
        """
        save_settings(vals)
        self._settings = vals
        if self._cache is None:
            QMessageBox.information(
                self, "Build all caches",
                "Audio cache not ready yet — try again shortly.")
            return
        scope = self._ask_index_scope("Build ALL caches")
        if scope is None:
            return
        # Repo scopes need the global library in memory — load it first if missing,
        # then resume here automatically.
        if not self._ensure_scope_loaded(scope, lambda: self._do_build_all_caches(scope)):
            return
        self._do_build_all_caches(scope)

    def _do_build_all_caches(self, scope: str):
        """Continuation of `_build_all_caches` once the scope's library is loaded."""
        from planner import embeddings as ae
        pool, label = self._scoped_pool(scope, "Build all caches")
        if pool is None:
            return
        why, steps, skipped = self._plan_allcache(pool)
        if why:
            QMessageBox.warning(self, "Audio analysis unavailable", why)
        names = _ALLCACHE_NAMES
        models = {"openl3": ae.MODEL_OPENL3, "chroma": ae.MODEL_CHROMA}
        skip_note = (i18n.t("\n\nSkipped: %s") % ", ".join(skipped)) if skipped else ""
        if not steps:
            QMessageBox.information(
                self, "Build ALL caches",
                i18n.t("Nothing can be built on this machine right now.") + skip_note)
            return
        ans = QMessageBox.question(
            self, "Build ALL caches",
            i18n.t("Build every index over %s tracks from %s?")
            % (f"{len(pool):,}", i18n.t(label))
            + "\n\n"
            + i18n.t("Runs %s back-to-back. Each is slow the first time, then "
                     "cached; reuses anything already built. You can cancel "
                     "between or within steps.")
            % " → ".join(i18n.t(names[s]) for s in steps)
            + "\n\n"
            + i18n.t("Read-only — your audio files are never modified.")
            + skip_note,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        # Explicit full rebuild → reclaim DB rows for files that vanished from disk.
        # Behind the bar as well: it stats every registered path, which is seconds
        # over a real library — and on the UI thread that is the same frozen window
        # the please-wait bar was added to cure, only now behind the Yes.
        try:
            self._run_behind_busy(
                i18n.t("🧹  Checking which files are still on disk…"),
                lambda _say: planner.db.cleanup_orphans())
        except Exception as exc:
            log.warning("  ⚠️ Orphan cleanup skipped: %s", exc)
        # "notes" collects what went wrong per step, so the closing report can say
        # so — a step that failed on every file must not read as a success.
        # "reports" holds each step's own account of it: the reasons its files
        # failed and how many of them no retry could fix.
        self._allcache = {"pool": pool, "label": label, "steps": steps,
                          "names": names, "models": models, "i": 0, "notes": [],
                          "reports": {}}
        self._allcache_next()

    def _run_behind_busy(self, message: str, fn):
        """Run `fn(say)` in a worker while a please-wait bar spins in front of it.

        A nested event loop, so the bar is drawn and keeps pulsing instead of
        standing there as an empty white rectangle. The dialog is app-modal, so
        the loop cannot take a second click on the button behind it, and it is
        always closed before the caller's message boxes: an app-modal dialog
        stacked under another one is one nobody can dismiss.
        """
        busy = BusyDialog(self, message=message)
        busy.show_after(0)
        worker = _BusyWorker(fn)
        worker.step.connect(busy.set_message)
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        # Polled as well: a worker that finished before exec() got going would have
        # quit a loop that was not running yet, and the wait would never end.
        poll = QTimer()
        poll.timeout.connect(lambda: worker.isFinished() and loop.quit())
        try:
            worker.start()
            poll.start(50)
            loop.exec()
        finally:
            poll.stop()
            worker.wait()
            busy.finish()
        if isinstance(worker.result, Exception):
            raise worker.result
        return worker.result

    def _plan_allcache(self, pool) -> tuple:
        """(why librosa can't run, steps, skipped) — behind a please-wait bar.

        Working out what this machine can build takes seconds: a two-second decode
        probe, an ffmpeg lookup and an import attempt per embedding backend. Between
        the scope question and the confirmation the window just sat there, which
        reads as a hang and invites a second click.
        """
        def probe(say):
            from planner import embeddings as ae
            # librosa is the first and most important step, and when it cannot run
            # it fails identically on every file: the pipeline used to churn through
            # the whole library, cache nothing and still report "all caches are
            # built", leaving "Find similar tracks" greyed out with no explanation.
            why = self._librosa_unavailable(pool)
            say(i18n.t("🧱  Looking for ffmpeg and the AI backends…"))
            steps, skipped = plan_allcache_steps(
                has_pd=any(e.dance == "PD" for e in pool),
                have_librosa=not why,
                have_ffmpeg=bool(find_ffmpeg()),
                have_openl3=ae.openl3_available(),
                have_chroma=ae.chroma_available())
            return why, steps, skipped

        return self._run_behind_busy(
            i18n.t("🧱  Checking what this machine can build…"), probe)

    def _librosa_unavailable(self, pool) -> str:
        """Why the librosa analysis cannot run over `pool` — "" when it can.

        One two-second decode, up front. Without it a machine that cannot decode
        audio at all fails every file with the same error, ends with an empty
        feature cache, and the only visible sign is "Find similar tracks" staying
        greyed out.
        """
        probe = next((e.path for e in pool), None)
        if probe is None:
            return ""
        why = planner.db.probe_decode_backend(probe)
        if why is None:
            return ""
        log.warning("🔬 Audio analysis unavailable\n"
                    "reason: %s\n"
                    "probe: %s", why, probe)
        if why == planner.db.PROBE_NO_LIBROSA:
            return i18n.t("librosa is not installed, so tempo and timbre cannot be "
                          "measured and similar-track search stays unavailable.\n\n"
                          "Install it, then restart the app:\n"
                          "    pip install librosa")
        if why == planner.db.PROBE_NO_BACKEND:
            return i18n.t("Nothing on this computer can decode an MP3, so tempo and "
                          "timbre cannot be measured and similar-track search stays "
                          "unavailable.\n\nInstall ffmpeg and make sure it is on PATH "
                          "(not just next to the app), then restart.")
        return i18n.t("The audio decoder could not read %s, so the analysis "
                      "would fail for every file. See the log for the error."
                      ) % probe.name

    def _allcache_next(self):
        """Run the next step in the build-all pipeline, or finish."""
        st = getattr(self, "_allcache", None)
        if not st:
            return
        if st["i"] >= len(st["steps"]):
            self._emb_store_cache = None
            self._refresh_library_status()
            self._allcache = None
            ran = ", ".join(i18n.t(st["names"][s]) for s in st["steps"])
            label = i18n.t(st["label"])
            # Files that are gone from disk are listed, never counted: they are
            # the one failure no rebuild can fix.
            skips = st.get("skips") or []
            skip_text = ("\n\n" + i18n.t("Nothing could be built for these, and "
                                         "nothing will be:") + "\n"
                         + "\n".join("• " + s for s in skips)) if skips else ""
            if st["notes"]:
                self.statusBar().showMessage(
                    i18n.t("Caches built for %s — with problems, see the log.")
                    % label)
                QMessageBox.warning(
                    self, "Build all caches",
                    i18n.t("Finished for %s, but not everything worked:") % label
                    + "\n\n"
                    + "\n".join("• " + n for n in st["notes"])
                    + skip_text
                    + "\n\n" + i18n.t("Ran: %s.") % ran)
                return
            self.statusBar().showMessage(
                i18n.t("All caches built for %s.") % label)
            QMessageBox.information(
                self, "Build all caches",
                i18n.t("All caches are built for %s.") % label + "\n"
                + i18n.t("Ran: %s.") % ran + skip_text)
            return
        step = st["steps"][st["i"]]
        if step == "librosa":
            self._allcache_run_librosa(st["pool"])
        elif step in ("audiofp", "loudness", "silences", "pd"):
            self._allcache_run_probe(step, st["names"][step], st["pool"])
        else:
            self._allcache_run_embedding(st["models"][step], st["names"][step],
                                         st["pool"])

    def _allcache_run_librosa(self, pool):
        to_do = [e for e in pool if e.features is None]
        if not to_do:
            self._allcache_advance()
            return
        self.statusBar().showMessage(
            i18n.t("Build all caches — librosa: analyzing %s files…")
            % f"{len(to_do)}")
        self._busy = BusyDialog(self, i18n.t("Build all caches — librosa…"),
                                cancelable=True)
        self._index_analyzer = AudioAnalyzer(self._cache, pool, self)
        self._busy.cancel_requested.connect(self._index_analyzer.cancel)
        self._busy.show_after(300)
        self._index_analyzer.progress.connect(self._on_index_progress)
        self._index_analyzer.report.connect(
            lambda rep: self._allcache_note_report("librosa", rep))
        self._index_analyzer.done.connect(
            lambda ok, err: self._allcache_step_done("librosa", ok, err))
        self._index_analyzer.cancelled.connect(lambda done: self._allcache_cancel("librosa", done))
        self._index_analyzer.start()

    def _allcache_run_embedding(self, model: str, name: str, pool):
        from planner import embeddings as ae
        store = ae.EmbeddingStore(self._cache)
        self.statusBar().showMessage(
            i18n.t("Build all caches — %s…") % i18n.t(name))
        self._busy = BusyDialog(
            self, i18n.t("Build all caches — %s embeddings…") % i18n.t(name),
            cancelable=True)
        self._emb_idx_worker = EmbeddingIndexWorker(store, model, pool, self)
        self._emb_idx_worker.progress.connect(
            lambda d, t, n, eta: self._busy and self._busy.set_progress(d, t, "🧠 " + n, eta))
        self._emb_idx_worker.done.connect(
            lambda computed, errors, first_error: (
                self._allcache_note_report(
                    name, {"reasons": {first_error[:120]: errors}} if first_error else {}),
                self._allcache_step_done(name, computed, errors)))
        self._emb_idx_worker.cancelled.connect(
            lambda done: self._allcache_cancel(name, done))
        self._emb_idx_worker.error.connect(self._allcache_embedding_error)
        self._busy.cancel_requested.connect(self._emb_idx_worker.cancel)
        self._busy.show_after(300)
        self._emb_idx_worker.start()

    def _allcache_run_probe(self, step: str, name: str, pool):
        """One file-by-file step: 🔗 audio fingerprints, 📊 loudness, 🔇 silences
        or 🐂 PD highlights.

        All four analyzers share LibraryPass's signal shape, so one runner covers
        them; only the worker, the pool and the caption differ. PD runs over the
        Paso Dobles alone — the other tracks have no highlight to find.
        """
        icons = {"audiofp": "🔗 ", "loudness": "📊 ", "silences": "🔇 ", "pd": "🐂 "}
        paths, seen = [], set()
        for e in pool:
            if step == "pd" and e.dance != "PD":
                continue
            if str(e.path) not in seen:
                seen.add(str(e.path))
                paths.append(e.path)
        if not paths:
            self._allcache_advance()
            return
        if step == "audiofp":
            worker = AudioFpAnalyzer(self._cache, paths, self)
        elif step == "pd":
            worker = PdHighlightAnalyzer(self._cache, paths, self, force=False)
        else:
            cls = LoudnessAnalyzer if step == "loudness" else SilenceAnalyzer
            worker = cls(self._cache, paths, find_ffmpeg(), self)
        caption = i18n.t("Build all caches — %s…") % i18n.t(name)
        self.statusBar().showMessage(caption)
        self._busy = BusyDialog(self, caption, cancelable=True)
        self._allcache_worker = worker
        worker.progress.connect(
            lambda d, t, err, n, eta: self._busy
            and self._busy.set_progress(d, t, icons[step] + n, eta))
        worker.report.connect(lambda rep, n=name: self._allcache_note_report(n, rep))
        worker.done.connect(lambda ok, err: self._allcache_probe_done(step, name, ok, err))
        worker.cancelled.connect(lambda done: self._allcache_cancel(name, done))
        worker.error.connect(self._allcache_embedding_error)
        self._busy.cancel_requested.connect(worker.cancel)
        self._busy.show_after(300)
        worker.start()

    def _allcache_probe_done(self, step: str, name: str, ok: int, errors: int):
        if step == "pd" and ok:
            # The DB moved under the session cache — drop it so the next play
            # reads the fresh marks.
            self._pd_highlights.clear()
        self._allcache_step_done(name, ok, errors)

    def _allcache_note_report(self, name: str, rep: dict):
        """Keep a step's own account of what went wrong, for the closing box.

        It arrives just before the step's `done`, which is what actually moves
        the pipeline on — so by the time the note is written it is here.
        """
        st = getattr(self, "_allcache", None)
        if st is not None:
            st.setdefault("reports", {})[name] = dict(rep or {})

    @staticmethod
    def _allcache_reason(rep: dict) -> str:
        """The reason most of a step's files failed for, as a short phrase."""
        reasons = (rep or {}).get("reasons") or {}
        if not reasons:
            return ""
        why, hits = max(reasons.items(), key=lambda kv: kv[1])
        if len(reasons) > 1:
            return i18n.t("mostly: %s") % why
        return why

    def _allcache_step_done(self, name: str, ok: int, errors: int):
        """A step finished — note any failures, then move on.

        Every step reports how many files it could not do, and every one of them
        used to be dropped on the floor: a run in which nothing at all succeeded
        still ended with "All caches are built". Files nothing could ever fix —
        gone from disk — are named separately and NOT counted as failures.
        """
        st = getattr(self, "_allcache", None)
        if st is None:
            self._allcache_advance()
            return
        rep = st.get("reports", {}).get(name, {})
        skipped = int(rep.get("skipped") or 0)
        if errors or skipped:
            log.warning("🧱 Build-all step finished with errors\n"
                        "step: %s\n"
                        "done: %s\n"
                        "failed: %s\n"
                        "skipped: %s\n"
                        "reasons: %s", name, ok, errors, skipped,
                        rep.get("reasons") or {})
        if errors:
            why = self._allcache_reason(rep)
            note = i18n.t("%s: %s file(s) failed") % (i18n.t(name), f"{errors:,}")
            if why:
                note += i18n.t(" (%s)") % why
            st["notes"].append(note + i18n.t(", %s cached") % f"{ok:,}")
        if skipped:
            # A file that is gone from disk is not a failure of this run: no
            # retry can ever build it, so it is reported apart from the errors
            # and never turns a clean run into a warning.
            st.setdefault("skips", []).append(
                i18n.t("%s: %s file(s) skipped — not on disk any more")
                % (i18n.t(name), f"{skipped:,}"))
        self._allcache_advance()

    def _allcache_advance(self):
        """A pipeline step finished — refresh labels and move to the next."""
        if self._busy:
            self._busy.finish()
        self._emb_store_cache = None
        self._refresh_library_status()
        self._sync_loudness_available()   # the loudness step re-gates 🔊
        st = getattr(self, "_allcache", None)
        if not st:
            return
        st["i"] += 1
        self._allcache_next()

    def _allcache_cancel(self, name: str, done: int):
        """User cancelled a step — stop the whole pipeline, keep cached progress."""
        if self._busy:
            self._busy.finish()
        self._emb_store_cache = None
        self._refresh_library_status()
        self._sync_loudness_available()
        self._allcache = None
        self.statusBar().showMessage(
            i18n.t("Build all caches cancelled during %s — %s done so far "
                   "(cached).") % (i18n.t(name), f"{done}"))

    def _allcache_embedding_error(self, msg: str):
        """A step died outright — say so, and leave the labels telling the truth.

        Whatever it managed before it fell over is cached, so the status block
        and the 🔊 gate are refreshed here exactly as on the two orderly exits.
        """
        if self._busy:
            self._busy.finish()
        self._emb_store_cache = None
        self._refresh_library_status()
        self._sync_loudness_available()
        self._allcache = None
        QMessageBox.critical(self, "Build all caches", msg)
