"""🔬 The analysis runs over the library: librosa, loudness, silences, PD, vocals.

Split off gui/main_global.py as a MainWindow mixin. Each one is a worker plus
the four things that happen to it — progress, done, cancelled, error — so they
sit together, away from what the results are then used for.
"""
import importlib.util
import logging


HAS_MULTIMEDIA = importlib.util.find_spec("PySide6.QtMultimedia") is not None

from PySide6.QtWidgets import (
    QCheckBox,
    QMessageBox,
)
from gui.common import (
    BusyDialog,
    _fmt_duration,
)
from planner import i18n
from planner.vocals import (
    DEMUCS_INSTALL_HINT,
    apply_vocal_shares,
    demucs_available,
    learn_instrumental_probs,
)
from gui.workers import (  # auto-resolved
    AudioAnalyzer,
    LoudnessAnalyzer,
    SilenceAnalyzer,
    PdHighlightAnalyzer,
    VocalShareAnalyzer,
)
from shared.audio_probes import find_ffmpeg

log = logging.getLogger("dancesport.gui.analyze")


class AnalysisMixin:
    """🔬 Library-wide analysis runs and what they report back."""

    def _library_paths(self, dance: str | None = None) -> list:
        """Every distinct track path of the loaded library, optionally of one
        dance only — the pool every pass below is offered."""
        lib = self._lib
        paths, seen = [], set()
        for e in (lib.entries if lib else []):
            if dance is not None and e.dance != dance:
                continue
            if str(e.path) not in seen:
                seen.add(str(e.path))
                paths.append(e.path)
        return paths

    def _run_library_pass(self, worker, caption: str, glyph: str,
                          noun: str, unit: str, after=None):
        """Run one analysis pass and report it: the busy dialog, the cancel
        button, the four signals and the status line every pass shows.

        Each pass used to bring its own copy of this plus a quartet of handlers
        that differed in the glyph and the noun alone. `after` is what this
        particular pass has to touch once results exist (retrain, re-filter,
        drop a session cache) — the only thing that is really per-pass.
        """
        self._busy = BusyDialog(self, caption, cancelable=True)
        self._busy.cancel_requested.connect(worker.cancel)
        self._busy.show_after(300)

        def on_progress(done, total, errors, name, eta):
            if self._busy:
                self._busy.set_progress(done, total, glyph + " " + name, eta)
            # `noun` and `unit` stay English at the call sites — the noun is
            # also handed to QMessageBox.warning below, where the patched
            # static translates it — so every line asks for its own here.
            eta_txt = (i18n.t("  ~%s left") % _fmt_duration(eta)
                       if eta >= 0 else "")
            self.statusBar().showMessage(
                f"{i18n.t(noun)}: {done}/{total}{eta_txt}  "
                + (i18n.t("(%s errors)") % errors if errors else ""))

        def on_done(ok, errors):
            if self._busy:
                self._busy.finish()
            if after:
                after(ok)
            self.statusBar().showMessage(
                i18n.t("%s done — %s %s") % (i18n.t(noun), ok, i18n.t(unit))
                + (i18n.t(", %s errors") % errors if errors else "")
                + ("" if ok or errors
                   else i18n.t(" (all were already cached)")))

        def on_cancelled(done_so_far):
            if self._busy:
                self._busy.finish()
            if after:
                after(done_so_far)
            self.statusBar().showMessage(
                i18n.t("%s cancelled — %s %s so far.")
                % (i18n.t(noun), done_so_far, i18n.t(unit)))

        def on_error(msg):
            if self._busy:
                self._busy.finish()
            QMessageBox.warning(self, noun,
                                i18n.t("%s failed:\n%s") % (i18n.t(noun), msg))

        worker.progress.connect(on_progress)
        worker.done.connect(on_done)
        worker.cancelled.connect(on_cancelled)
        if hasattr(worker, "error"):
            worker.error.connect(on_error)
        worker.start()

    def _analyze_audio(self, force: bool = False):
        if not self._lib or not self._cache:
            return
        missing = [e for e in self._lib.entries if e.features is None]
        if not force and not missing:
            # Nothing missing → offer a full refresh (e.g. after a tempo-method change).
            ans = QMessageBox.question(
                self, "Re-analyze Audio",
                i18n.t("All %s files are already cached.\n\n"
                       "Re-analyze the whole library anyway to refresh the "
                       "measured tempo with the current method?")
                % len(self._lib.entries),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                self._analyze_audio(force=True)
            return
        targets = list(self._lib.entries) if force else missing
        why = self._librosa_unavailable(targets)
        if why:
            QMessageBox.warning(self, "Audio analysis unavailable", why)
            return
        eta_min = max(1, int(len(targets) * 0.8 / 60))
        # Two whole sentences rather than one with a verb slot: German puts the
        # verb at the end, so "%s files will be %s" cannot hold both readings.
        body = (i18n.t("%s files will be re-analyzed (~%s min, cached "
                       "afterwards).\n\nRun now?") if force else
                i18n.t("%s files need librosa analysis (~%s min, cached "
                       "afterwards).\n\nRun now?"))
        ans = QMessageBox.question(
            self, "Re-analyze All Audio" if force else "Analyze Audio (Timbre)",
            body % (len(targets), eta_min),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self.statusBar().showMessage(
            i18n.t("Audio analysis started — %s files…") % len(targets)
        )
        self._analyzer = AudioAnalyzer(self._cache, targets, self, force=force)
        self._run_library_pass(self._analyzer, "Analyzing audio (timbre)…", "🔬",
                               "Audio analysis", "files cached",
                               after=self._apply_analysis_results)

    def _apply_analysis_results(self, _ok: int):
        if self._lib:
            # Newly analyzed tracks now have features → give them a vocal/instr
            # probability too (and retrain on any features analyzed fresh).
            learn_instrumental_probs(self._lib.entries)
        self._refresh_library_status()

    def _analyze_loudness(self):
        """📊 in the Playing panel: measure every library track that has no
        cached loudness yet (whole competition library, not just the decks)."""
        if not self._cache:
            return
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            QMessageBox.warning(
                self, "Analyze loudness",
                "ffmpeg was not found (neither on PATH nor the copy bundled\n"
                "with the project) — loudness cannot be measured.")
            return
        lib = self._lib
        if lib is None or not lib.entries:
            QMessageBox.information(self, "Analyze loudness",
                                    "The music library is not loaded yet.")
            return
        paths = self._library_paths()
        if QMessageBox.question(
                self, "Analyze loudness",
                i18n.t("Measure the loudness of the whole library "
                       "(%s tracks)?\n\n"
                       "Already-measured tracks are skipped — only new "
                       "ones are\ndecoded (≈1 s each). You can cancel "
                       "anytime; results so far\nare kept.") % len(paths)) != QMessageBox.StandardButton.Yes:
            return
        self._loudness_worker = LoudnessAnalyzer(self._cache, paths, ffmpeg, self)
        self._run_library_pass(self._loudness_worker,
                               "Measuring loudness (EBU R128)…", "📊",
                               "Loudness analysis", "tracks measured",
                               after=lambda _ok: self._sync_loudness_available())

    def _analyze_silences(self):
        """🔇 in ⚙ Settings: probe every library track that has no cached silence
        spans yet, so playback never has to run an ffmpeg decode of its own."""
        if not self._cache:
            return
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            QMessageBox.warning(
                self, "Probe silences",
                "ffmpeg was not found (neither on PATH nor the copy bundled\n"
                "with the project) — silences cannot be probed.")
            return
        lib = self._lib
        if lib is None or not lib.entries:
            QMessageBox.information(self, "Probe silences",
                                    "The music library is not loaded yet.")
            return
        paths = self._library_paths()
        todo = sum(1 for p in paths if self._cache.get_silences(p) is None)
        if QMessageBox.question(
                self, "Probe silences",
                i18n.t("Probe the silent stretches of the whole library "
                       "(%s tracks, %s not probed yet)?\n\n"
                       "Already-probed tracks are skipped — only new "
                       "ones are\ndecoded (≈0.3 s each). You can "
                       "cancel anytime; results so far\nare kept.")
                % (len(paths), todo)) != QMessageBox.StandardButton.Yes:
            return
        self._silence_analyzer = SilenceAnalyzer(self._cache, paths, ffmpeg, self)
        self._run_library_pass(self._silence_analyzer,
                               "Probing silent stretches…", "🔇",
                               "Silence probe", "tracks probed",
                               after=lambda _ok: self._repaint_silence_flags(paths))

    def _repaint_silence_flags(self, paths) -> None:
        """Re-fill the rows of every open list showing one of `paths`, so the
        red ⏱ flag appears (or clears) as soon as the probe has an answer.
        Rows are painted at load time and would otherwise keep whatever the
        spans said then — for a freshly probed library, nothing at all."""
        for table in getattr(self, "_all_tables", ()):
            table.refresh_paths(paths)

    def _sync_loudness_available(self):
        """Enable the 🔊 equalize checkbox only when EVERY track currently in
        the visible playlists has a measured loudness — a half-equalized round
        would jump in level between songs."""
        if self._cache is None or self._cache.lufs_count() == 0:
            self._play_panel.set_loudness_available(False, -1)
            return
        missing = 0
        seen = set()
        for t in self._visible_deck_tables():
            for e in t._row_meta.entries():
                if str(e.path) in seen:
                    continue
                seen.add(str(e.path))
                if self._cache.get_lufs(e.path, touch_disk=False) is None:
                    missing += 1
        self._play_panel.set_loudness_available(missing == 0, missing)

    def _analyze_vocals(self):
        """🎙️ in ⚙ Settings: measure the Demucs vocal-stem share of every
        library track not yet in the vocals table (optional demucs install)."""
        if not self._cache:
            return
        if not demucs_available():
            QMessageBox.information(self, "Analyze vocals (Demucs)",
                                    DEMUCS_INSTALL_HINT)
            return
        lib = self._lib
        if lib is None or not lib.entries:
            QMessageBox.information(self, "Analyze vocals (Demucs)",
                                    "The music library is not loaded yet.")
            return
        paths = self._library_paths()
        remaining = sum(1 for p in paths if self._cache.get_vocal_share(p) is None)
        if not remaining:
            QMessageBox.information(
                self, "Analyze vocals (Demucs)",
                i18n.t("All %s tracks already have a measured vocal "
                       "share.") % len(paths))
            return
        eta_min = max(1, int(remaining * 7 / 60))
        if QMessageBox.question(
                self, "Analyze vocals (Demucs)",
                i18n.t("Separate the vocals of %s not-yet-measured "
                       "tracks (~%s min)?\n\n"
                       "Demucs actually extracts the singing from each "
                       "track — slow\n(~7 s per track) but far more "
                       "reliable than the heuristics.\nYou can cancel "
                       "anytime; results so far are kept.")
                % (remaining, eta_min)
                ) != QMessageBox.StandardButton.Yes:
            return
        self._vocals_worker = VocalShareAnalyzer(self._cache, paths, self)
        self._run_library_pass(self._vocals_worker,
                               "Separating vocals (Demucs)…", "🎙️",
                               "Vocal separation", "tracks measured",
                               after=self._apply_vocals_results)

    def _apply_vocals_results(self, _ok: int):
        """Push freshly measured shares onto the entries and re-filter the
        library browser, so the Vocal/Instr. filter reflects them right away."""
        if self._lib and self._cache:
            apply_vocal_shares(self._lib.entries, self._cache)
            self._lib_browser.set_entries(self._lib.entries)

    def _analyze_pd_highlights(self):
        """🐂 in the Playing panel: detect the highlights of every Paso Doble
        of the library that has none stored yet → instant arming on playback."""
        if not self._cache:
            return
        lib = self._lib
        if lib is None or not lib.entries:
            QMessageBox.information(self, "Analyze PD highlights",
                                    "The music library is not loaded yet.")
            return
        paths = self._library_paths("PD")
        if not paths:
            QMessageBox.information(self, "Analyze PD highlights",
                                    "No Paso Doble tracks in the library.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Analyze PD highlights")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(
            i18n.t("Detect the highlights of every Paso Doble in the "
                   "library (%s tracks)?\n\n"
                   "Already-analyzed tracks are skipped — only new "
                   "ones are\ndecoded (a few seconds each). You can "
                   "cancel anytime;\nresults so far are kept.")
            % len(paths))
        redo = QCheckBox("Re-analyze tracks that already have highlights")
        redo.setToolTip(
            "Redo the 🐂 auto-detection for the whole library — for after the\n"
            "detector changed. Hand-set 🎯 marks are kept untouched.")
        box.setCheckBox(redo)
        box.setStandardButtons(QMessageBox.StandardButton.Yes
                               | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        self._pd_analyzer = PdHighlightAnalyzer(self._cache, paths, self,
                                                force=redo.isChecked())
        self._run_library_pass(self._pd_analyzer,
                               "Detecting Paso Doble highlights…", "🐂",
                               "PD highlight detection", "tracks analyzed",
                               after=self._apply_pd_results)

    def _apply_pd_results(self, ok: int):
        if not ok:
            return
        # The DB moved under the session cache — drop it so the next play
        # reads the fresh marks, and re-arm the track playing right now.
        self._pd_highlights.clear()
        if self._playback.dance == "PD" and self._playback.path is not None:
            self._ensure_pd_highlights(self._playback.path)
