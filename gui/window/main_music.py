"""🎵 The music check: what is wrong with the tracks themselves.

Split off gui/window/main_import.py as a MainWindow mixin — too short, too long, off
tempo, hissing, half silence — plus the report it all lands in and the jumps
from a finding back into the deck it came from. Reading and writing a title's
tags is a mixin of its own, in gui/window/main_tags.py.
"""
import html
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import shiboken6
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import planner.music.analysis
import planner.music.db
from gui.common import (
    BusyDialog,
    entry_tooltip,
)
from gui.dialogs import (  # auto-resolved
    MusicSpeedDialog,
)
from gui.dialogs.drop_check import FileDropCheckPanel
from gui.dialogs.readiness_dialog import ReadinessDialog
from gui.window.main_tags import TagEditMixin
from planner import i18n
from planner.event import readiness
from planner.music.analysis import tempo_prior
from planner.music.parsing import detect_bpm, get_tag_bpm
from planner.playlist import checks as planner_checks
from planner.playlist import party_check
from planner.playlist.m3u import import_playlist_m3u
from planner.terms import dance_name
from shared.audio.audio_probes import detect_silences, find_ffmpeg, measure_noise_floor  # auto-resolved
from shared.columns import (
    _COL_TITLE,
)
from shared.widgets import (
    show_toast,
)

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.music")

# ffmpeg probes a Check-music pass runs side by side: each is one
# decode-bound process, so they spread over the cores instead of queueing.
_PROBE_WORKERS = 8

class _MusicCheckAbort(Exception):
    """Raised from the 🎵 Check-Music progress callback to really stop the scan
    when the user hits Cancel/ESC (not just hide the dialog)."""


class _MusicReportDialog(QDialog):
    """The kept 🎵 Music check window, with the parts a re-run fills in again."""
    _play_state: dict[str, int]
    _info: QLabel
    _long_chk: QCheckBox
    _noise_chk: QCheckBox
    _body_lyt: QVBoxLayout
    _music_panel: FileDropCheckPanel

    def reset_play_marker(self):
        """An all-clear report has no ▶ to reset; a suspects table replaces this."""
        self._play_state["row"] = -1


class MusicCheckMixin(TagEditMixin):
    """🎵 The music check: per-track findings, the report, the jump back."""

    _custom_reader = None    # the CustomFieldReader of a new Custom mapping, while it runs

    def _entry_takt(self, e) -> int:
        """A track's takt (bars/min) — see planner.playlist.checks.entry_takt."""
        return planner_checks.entry_takt(e, self._BEATS_PER_BAR)

    def _check_min_secs(self) -> int:
        """⏱ too-short threshold in seconds — Settings → 🎵 Checks, default 1:45."""
        return int(self._settings.get("check_min_play_secs", self._MIN_PLAY_SECS))

    def _check_max_secs(self) -> int:
        """⏳ too-long threshold in seconds — Settings → 🎵 Checks, default 4:00."""
        return int(self._settings.get("check_max_play_secs", self._MAX_PLAY_SECS))

    def _check_tempo_pct(self) -> float:
        """⚡ measured-vs-label tempo tolerance in % — Settings → 🎵 Checks."""
        return float(self._settings.get("check_tempo_dev_pct", 10))

    def _check_noise_db(self) -> float:
        """🔇 noise-floor threshold in dBFS — Settings → 🎵 Checks, default −50."""
        return float(self._settings.get("check_noise_floor_db",
                                        self._NOISE_FLOOR_DB))

    def _track_issues(self, e, probe_silence=True, in_final=False):
        """Collect every tournament problem for one track (see
        planner.playlist.checks.track_issues). Thresholds come from Settings → 🎵 Checks.
        `probe_silence=False` skips the on-the-fly ffmpeg silence / noise probe
        (cached results still count) — used by the live grid marks, which
        re-check whole decks on every edit.
        `in_final` says this slot is a final — a short Paso Doble only matters
        there."""
        dur = int(getattr(e, "duration", 0) or 0)
        sil = self._track_silence_total(e, dur, probe=probe_silence) if dur > 0 else 0.0
        issues = planner_checks.track_issues(
            e,
            beats_per_bar=self._BEATS_PER_BAR,
            tempo_ratios=self._TEMPO_RATIOS,
            tempo_pct=self._check_tempo_pct(),
            min_secs=self._check_min_secs(),
            max_secs=self._check_max_secs(),
            silence_secs=sil,
            check_long=getattr(self, "_check_long", False),
            noise_db=self._track_noise_floor(e, probe=probe_silence),
            noise_max_db=self._check_noise_db(),
            in_final=in_final,
        )
        # A title that would not play this session (see _playback_failed).
        playback = getattr(self, "_playback", None)
        failed = playback.failed.get(str(e.path)) if playback is not None else None
        if failed is not None:
            issues.append(i18n.t("🔇 would not play: %s") % failed)
        return issues

    def _track_noise_floor(self, e, probe: bool = True) -> float | None:
        """A track's noise floor in dBFS, or None when the 🔇 check is off or
        the floor isn't known. Measuring means decoding the whole file through
        ffmpeg, so it happens only when the user asked for the check — and the
        result is cached by content, so a re-run is instant."""
        if not getattr(self, "_check_noise", False) or self._library.cache is None:
            return None
        p = Path(e.path)
        try:
            floor = self._library.cache.get_noise_floor(p, touch_disk=probe)
        except Exception:
            return None
        if floor is None and probe:
            ffmpeg = find_ffmpeg()
            if ffmpeg:
                floor = measure_noise_floor(ffmpeg, p)
                if floor is not None:
                    self._library.cache.put_noise_floor(p, floor)
                    self._library.cache.save()
        return floor

    def _track_silence_total(self, e, dur: int, probe: bool = True) -> float:
        """Total silent seconds inside a track (≥2 s stretches under −30 dB).
        Cached spans are used when present (also filled during playback);
        borderline-short tracks are probed on the fly via ffmpeg and the result
        cached, so re-checks are instant. 0.0 when unknown."""
        if self._library.cache is None:
            return 0.0
        p = Path(e.path)
        try:
            spans = self._library.cache.get_silences(p, touch_disk=probe)
        except Exception:
            return 0.0
        # Probe only borderline-short tracks (a whole deck would take minutes):
        # anything longer would need >1 min of hidden silence to fall under the
        # ⏱ threshold; cached spans from playback still count for the rest.
        if spans is None and probe and 0 < dur < self._check_min_secs() + 60:
            ffmpeg = find_ffmpeg()
            if ffmpeg:
                spans = detect_silences(ffmpeg, p)
                if spans is not None:
                    self._library.cache.put_silences(p, spans)
                    self._library.cache.save()
        return sum(end - start for start, end in (spans or []))

    def _submit_probes(self, pool, entries) -> dict:
        """Start on `pool` every uncached ffmpeg probe `_track_issues` would run
        inline for `entries` — the noise floor with 🔇 on, the silences of the
        borderline-short ones — so a long check decodes several files at once.
        Returns {path: [(cache put, future), …]} for `_collect_probes`."""
        cache = self._library.cache
        noise = getattr(self, "_check_noise", False)
        ffmpeg = None
        jobs: dict[str, list] = {}
        if cache is None:
            return jobs
        for e in entries:
            dur = int(getattr(e, "duration", 0) or 0)
            want_noise = noise
            want_silence = dur > 0 and dur < self._check_min_secs() + 60
            if not (want_noise or want_silence):
                continue
            p = Path(e.path)
            if str(p) in jobs:
                continue
            ffmpeg = ffmpeg or find_ffmpeg()
            if not ffmpeg:
                return jobs
            todo = []
            try:
                if want_noise and cache.get_noise_floor(p) is None:
                    todo.append((cache.put_noise_floor,
                                 pool.submit(measure_noise_floor, ffmpeg, p)))
                if want_silence and cache.get_silences(p) is None:
                    todo.append((cache.put_silences,
                                 pool.submit(detect_silences, ffmpeg, p)))
            except Exception:
                pass
            if todo:
                jobs[str(p)] = todo
        return jobs

    def _collect_probes(self, jobs: dict, e, tick) -> None:
        """Wait for the probes `_submit_probes` started for `e` and cache what
        they found, calling `tick()` every 100 ms meanwhile so the panel keeps
        redrawing and hears Cancel."""
        if not jobs:
            return
        todo = jobs.pop(str(Path(e.path)), ())
        for put, fut in todo:
            while True:
                try:
                    res = fut.result(timeout=0.1)
                    break
                except TimeoutError:
                    tick()
            if res is not None:
                put(Path(e.path), res)
        if todo and self._library.cache is not None:
            self._library.cache.save()

    def _track_play_secs(self, e) -> int | None:
        """Seconds a track will really PLAY — its length minus the stillness at
        its edges that the 🔇 skip jumps over (planner.playlist.checks.audible_track_secs).

        Cached spans only: this runs for every row of every repaint, so it must
        never start an ffmpeg decode. None = never probed, and the ⏱ column
        then shows the file's own length."""
        dur = int(getattr(e, "duration", 0) or 0)
        if dur <= 0 or self._library.cache is None:
            return None
        try:
            spans = self._library.cache.get_silences(Path(e.path), touch_disk=False)
        except Exception:
            return None
        if spans is None:
            return None
        return int(round(planner_checks.audible_track_secs(dur, spans)))

    def _track_edge_silence(self, e) -> float:
        """The LONGER of the two stretches of stillness the 🔇 skip takes off
        this track's ends — what the red ⏱ flag is measured against.

        Longer, not summed: three seconds before the first note and three
        behind the last are two ordinary edges, not one track that ends early.
        Cached spans only, like `_track_play_secs` — this runs for every row of
        every repaint and must never start a decode. 0.0 = nothing to flag."""
        dur = int(getattr(e, "duration", 0) or 0)
        if dur <= 0 or self._library.cache is None:
            return 0.0
        try:
            spans = self._library.cache.get_silences(Path(e.path), touch_disk=False)
        except Exception:
            return 0.0
        return max(planner_checks.edge_silence_secs(dur, spans or []))

    def _check_track_speed(self, entry):
        """Context-menu 🎵 'Check music speed' for ONE track: open a dialog showing
        its tempo from three independent sources — the file NAME (takt, bars/min),
        the MP3 BPM tag (ID3 TBPM), and the tempo librosa MEASURES (beats/min).
        When the track hasn't been analyzed yet it's measured on the spot, so this
        works without a full library scan."""
        if entry is None or not getattr(entry, "path", None):
            return
        p = Path(entry.path)
        dance = entry.dance or ""
        bpb = self._BEATS_PER_BAR.get(dance)
        file_takt = detect_bpm(p.stem) or 0
        tag_bpm = get_tag_bpm(p) or 0.0

        # Measured musical tempo (beats/min): reuse cached features, else analyze now.
        measured = float(getattr(entry.features, "bpm", 0) or 0) if entry.features else 0.0
        if measured <= 0 and planner.music.analysis.HAS_LIBROSA:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                feat = planner.music.db.AudioCache._analyze_file(
                    p, tempo_prior(dance, entry.bpm))
                entry.features = feat
                if self._library.cache is not None:
                    self._library.cache.put(p, feat)
                measured = float(getattr(feat, "bpm", 0) or 0)
            except Exception as exc:
                log.warning("🎵 Couldn't measure %s: %s", p.name, exc)
            finally:
                QApplication.restoreOverrideCursor()

        dlg = MusicSpeedDialog(entry.title or p.stem, dance, bpb, int(file_takt),
                               tag_bpm, measured, self._TEMPO_RATIOS, self)
        dlg.exec()

    def _playlist_structure_issues(self, table) -> list[str]:
        """Round-structure warnings for a deck, as plain strings."""
        return ["".join(t for t, _ in f)
                for f in self._playlist_structure_findings(table)]

    def _playlist_structure_findings(self, table) -> list:
        """Round-structure sanity for a built / imported playlist deck.
        Flat / themed decks (no rounds) are skipped."""
        pl = getattr(table, "_playlist", None)
        if not pl:
            return []
        if hasattr(table, "current_dances"):
            dances = table.current_dances()
        else:
            dances = list(getattr(table, "_loaded_dances", []))
        return self._grid_structure_findings(pl, dances)

    def _grid_structure_issues(self, pl: dict, dances: list[str]) -> list[str]:
        """Round-structure warnings for a grid, as plain strings (the 📂 drop
        tab and tests — no deck to jump into)."""
        return planner_checks.grid_structure_issues(pl, dances,
                                                    self._BEATS_PER_BAR)

    def _grid_structure_findings(self, pl: dict, dances: list[str]) -> list:
        """Round-structure sanity for a rounds→heats grid — see
        planner.playlist.checks.grid_structure_findings for the rules and the
        (text, target) segment format of each warning."""
        return planner_checks.grid_structure_findings(pl, dances,
                                                      self._BEATS_PER_BAR)

    def _compute_music_suspects(self, progress_cb=None):
        """Scan visible-deck tracks for tournament problems. Returns
        (suspects, checked, skipped, structure, any_tracks); pure (no UI).
        `progress_cb(done, total, title)` ticks once per track — the scan can
        be slow when un-analyzed borderline tracks need an ffmpeg silence probe."""
        def _slot(meta) -> tuple:
            """What makes a track its own case: the file AND whether it is
            played in a final. The same Paso in a Vorrunde and in the Finale is
            two checks — ⏱ too short only counts in the final."""
            return (str(meta.entry.path),
                    planner_checks.is_final_round(meta.round_name, meta.tier))

        total = len({_slot(m) for table in self._checkable_deck_tables()
                     for m in table._row_meta.songs()})
        suspects = []
        by_path: dict[tuple, int] = {}   # slot → index in `suspects` (merge cross-deck dupes)
        checked = skipped = 0
        seen = set()
        pool = ThreadPoolExecutor(max_workers=_PROBE_WORKERS)
        try:
            jobs = (self._submit_probes(pool, [m.entry for table in self._checkable_deck_tables()
                                               for m in table._row_meta.songs()])
                    if self._library.cache is not None else {})
            for table in self._checkable_deck_tables():
                pname = self.deck(table).name or "Playlist"
                for meta in table._row_meta.songs():
                    e = meta.entry
                    key = _slot(meta)
                    if key in seen:
                        # Same track in more than one open playlist — just record the
                        # extra playlist on the existing suspect (if it was flagged).
                        idx = by_path.get(key)
                        if idx is not None and pname not in suspects[idx][5]:
                            suspects[idx][5].append(pname)
                        continue
                    seen.add(key)
                    if progress_cb:
                        progress_cb(len(seen), total, e.title)
                    bpb = self._BEATS_PER_BAR.get(e.dance or "")
                    measured = float(getattr(e.features, "bpm", 0) or 0) if e.features else 0.0
                    dur = int(getattr(e, "duration", 0) or 0)
                    # Nothing to test: no label / unknown dance / not analyzed / no length.
                    if not e.bpm and not (measured > 0 and bpb) and not dur:
                        skipped += 1
                        continue
                    checked += 1
                    self._collect_probes(
                        jobs, e, lambda n=len(seen), t=e.title:
                        progress_cb and progress_cb(n, total, t))
                    issues = self._track_issues(e, in_final=key[1])
                    if issues:
                        by_path[key] = len(suspects)
                        suspects.append((e, bpb, measured, dur, issues, [pname]))
        finally:
            # A Cancel leaves the probes already running to finish on their own.
            pool.shutdown(wait=False, cancel_futures=True)
        # Playlist-level round-structure warnings, per deck (findings carry the
        # deck table so the report can render jump links into it).
        structure = []
        for table in self._checkable_deck_tables():
            w = self._playlist_structure_findings(table)
            if w:
                structure.append((self.deck(table).name or "Playlist",
                                  w, table))
        # Order by issue badness: a wrong tempo (too fast / too slow) is the
        # worst, then too short, then too long; ties broken by issue count.
        suspects.sort(key=lambda s: (self._issue_severity(s[4]), -len(s[4])))
        return suspects, checked, skipped, structure, bool(seen)

    @staticmethod
    def _issue_severity(issues) -> int:
        """Worst (lowest) severity rank across a track's issue strings, by their
        leading emoji: tempo off (⚡/🐢/🐇) < too short (⏱) < too long (⏳) /
        hissy (🔇)."""
        rank = {"⚡": 0, "🐢": 0, "🐇": 0, "⏱": 1, "⏳": 2, "🔇": 2}
        sev = [rank[txt[0]] for txt in issues if txt and txt[0] in rank]
        return min(sev) if sev else 3

    def _music_suspects_with_progress(self):
        """_compute_music_suspects behind a BusyDialog: un-analyzed borderline
        tracks get an on-the-fly ffmpeg silence probe (seconds each), so a first
        run over fresh decks can take a while — show per-track progress. Quick
        re-runs (everything cached) finish before the 250 ms delay shows it.
        Cancel (button or ESC) really aborts the scan → returns None."""
        dlg = BusyDialog(self, message="🎵 Checking music…", cancelable=True)
        dlg.show_after(250)
        aborted = []
        dlg.cancel_requested.connect(lambda: aborted.append(True))

        def _prog(done: int, total: int, name: str = ""):
            dlg.set_progress(done, total, name)
            QApplication.processEvents()
            if aborted:
                raise _MusicCheckAbort()

        try:
            return self._compute_music_suspects(progress_cb=_prog)
        except _MusicCheckAbort:
            log.info("🎵 Music check aborted by user")
            self.statusBar().showMessage("🎵 Music check aborted.")
            return None
        finally:
            dlg.finish()

    def _check_music(self):
        """🎵: scan visible-deck tracks for tournament problems — tempo label vs
        measured, TSO takt range, and too-short play length — and report suspects.
        A filename label (T51) is the TAKT (bars/min), converted to beats/min via
        the dance's meter (3/4, 2/4, 4/4) for the tempo cross-check."""
        result = self._music_suspects_with_progress()
        if result is None:
            return   # user aborted the scan — no report
        suspects, checked, skipped, structure, _ = result
        # Always open the report (even when everything is clean) so the ⏳
        # long-track toggle and the 📂 drag-files-in tab stay reachable —
        # same reasoning as the Check-duplicates dialog.
        self._show_music_report(suspects, checked, skipped, structure)

    def _readiness_findings(self) -> list:
        """Grade what will be played tonight: every deck holding titles and the
        Eintanzen list (planner/event/readiness.py)."""
        tables = self._checkable_deck_tables()
        if self._deckset.warmup_table._row_meta.has_songs():
            tables.append(self._deckset.warmup_table)
        tracks = [(e.path, e.dance) for t in tables for e in t._row_meta.entries()
                  if getattr(e, "path", None)]
        # The duplicate report renumbers `_dup_slots`, which an open 🔁 dialog's
        # ✅ Apply still resolves through.
        slots = getattr(self, "_dup_slots", None)
        report = self._deck_dup_report() if tracks else {}
        if slots is not None:
            self._dup_slots = slots
        # 🎵 runs behind its cancelable progress; cancelled, its line is left out.
        music = None
        result = self._music_suspects_with_progress() if tracks else None
        if result is not None:
            suspects, _checked, _skipped, structure, _any = result
            music = ([s[0].title for s in suspects], [name for name, _w, _t in structure])
        findings = readiness.readiness_findings(tracks, self._library.cache, report, music,
                                                self._settings.get("reference_path") or "")
        return findings + self._desk_findings()

    def _desk_findings(self) -> list:
        """🔈 🎛 ☀ The desk around the music: the chosen sound outputs, the
        hardware controller (left out while none is set up) and keep-awake."""
        dev = self._audio_device
        out = [readiness.outputs_finding(dev.unplugged(), dev.cue_on_music(),
                                         dev.cue_shares_music())]
        connected, _shown = self.controller_status()
        ctl = readiness.controller_finding(self.controller_config()["device"], connected)
        if ctl is not None:
            out.append(ctl)
        out.append(readiness.awake_finding(self._play_panel.keep_awake()))
        return out

    def _ready_keep_awake(self):
        """🚦's ☀ fix: tick ☀ Keep the screen awake (it saves and takes the
        lock itself) and grade again, since nothing runs in the background."""
        self._play_panel.awake_check.setChecked(True)
        dlg = getattr(self, "_ready_dlg", None)
        if dlg is not None:
            dlg.refresh()

    def _check_readiness(self):
        """🚦: one pre-flight over the existing checks, a traffic light each."""
        dlg = getattr(self, "_ready_dlg", None)
        if dlg is not None:
            dlg.refresh()
            dlg.raise_()
            dlg.activateWindow()
            return
        # Looked up on the click, not now: the window's actions, as they are then.
        dlg = ReadinessDialog(self._readiness_findings, {
            "paths": lambda: self._fix_deck_paths(),
            "loudness": lambda: self._analyze_loudness(),
            "silences": lambda: self._analyze_silences(),
            "pd": lambda: self._analyze_pd_highlights(),
            "duplicates": lambda: self._check_duplicates(),
            "music": lambda: self._check_music(),
            "outputs": lambda: self._open_settings(open_sound=True),
            "controller": lambda: self.open_controller_window(),
            "awake": lambda: self._ready_keep_awake(),
        }, self)
        log.info("🚦 Readiness check\n"
                 "light: %s", ("green", "yellow", "red")[dlg.level])
        dlg.finished.connect(lambda _r: self._close_readiness(dlg))
        self._ready_dlg = dlg
        dlg.show()

    def _close_readiness(self, dlg):
        self._ready_dlg = None
        dlg.deleteLater()

    def _reveal_deck_row(self, table, r) -> None:
        """Bring deck `table` on screen (unhide / unfold / expand as needed),
        select + scroll to row `r`, and raise the window. Shared by the
        Music-check report's jump actions."""
        self._reveal_deck(table)
        if table.isRowHidden(r):   # row sits inside a collapsed section
            table.expand_all()
        table.setCurrentCell(r, _COL_TITLE)
        item = table.item(r, _COL_TITLE)
        if item is not None:
            table.scrollToItem(
                item, QAbstractItemView.ScrollHint.PositionAtCenter)
        table.setFocus(Qt.FocusReason.OtherFocusReason)
        self.raise_()
        self.activateWindow()

    def _focus_track_in_deck(self, path) -> bool:
        """Select + scroll to the track at `path` in whichever visible deck holds
        it, make that deck the active one, and raise the window. Used by the
        Music-check report's double-click. Returns True when found."""
        target = str(path)
        for table in self._checkable_deck_tables():
            for r, m in table._row_meta.numbered():
                if str(getattr(m.entry, "path", "")) != target:
                    continue
                self._reveal_deck_row(table, r)
                return True
        return False

    def _focus_slot_in_deck(self, table, round_name, h_idx, d_idx) -> bool:
        """Select + scroll to the grid slot (round, heat, dance) in `table` —
        the jump behind the 🧩 round-structure links. Works for empty slots
        too (a “missing in heat …” warning has no track to search for)."""
        for r, m in enumerate(table._row_meta):
            if m is None:
                continue   # a ═══ header row sits in no slot
            if (m.round_name == round_name and m.h_idx == h_idx
                    and m.d_idx == d_idx and not m.backup):
                self._reveal_deck_row(table, r)
                return True
        return False

    def _show_music_report(self, suspects, checked: int, skipped: int,
                           structure=None):
        """Non-modal suspect list with per-row ▶ listen / 🗑 remove / ↺ replace,
        so the playlists stay usable while working through the report.

        The dialog shell (info line, Close, Ctrl+←/→ seek) is built once and
        kept; only the body (structure panel + suspects table) is rebuilt on a
        re-run — so refreshing doesn't flash a brand-new window."""
        dlg = getattr(self, "_bpm_dlg", None)
        fresh = dlg is None or not dlg.isVisible()
        if dlg is None or fresh:
            dlg = self._build_music_report_shell()

        self._set_music_report_texts(dlg, suspects, checked, skipped, structure)

        # Stop any track left playing by the previous body, then clear the body.
        st = dlg._play_state
        if st["row"] >= 0:
            self._play_or_stop(None)
            st["row"] = -1
        body_lyt = dlg._body_lyt
        while body_lyt.count():
            item = body_lyt.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)   # leave the hierarchy now (no lingering ghost)
                w.deleteLater()

        # Playlist-level round-structure warnings (uneven dance counts, heat
        # taper, heat tempo spread). Slot segments become links that jump to
        # the exact round/heat/dance row in the deck, like the suspects table.
        if structure:
            struct_lbl = self._build_structure_label(structure)
            body_lyt.addWidget(struct_lbl)

        if not suspects:
            none_lbl = QLabel(
                "✅  No tempo / length issues in the current tracks."
                if checked else
                "No tracks in any open playlist — drag playlists into the "
                "📂 tab to check loose files.")
            none_lbl.setStyleSheet("color:#2a7a45;")
            body_lyt.addWidget(none_lbl)
            body_lyt.addStretch(1)
            if fresh:
                dlg.show()
            return

        t = self._build_suspects_table(dlg, suspects)
        body_lyt.addWidget(t, stretch=1)

        if fresh:
            dlg.show()   # non-modal: the decks stay clickable next to the report

    def _build_music_report_shell(self):
        """The kept dialog shell: info line, check toggles, tabs, Close, seek keys."""
        dlg = _MusicReportDialog(self)
        dlg.setWindowTitle("🎵  Music check")
        dlg.resize(1040, 480)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._bpm_dlg = dlg
        dlg._play_state = {"row": -1}

        lyt = QVBoxLayout(dlg)
        info = QLabel()
        info.setWordWrap(True)
        lyt.addWidget(info)
        dlg._info = info

        def rerun():
            result = self._music_suspects_with_progress()
            if result is None:
                return   # aborted — keep the current report
            s, c, sk, st, _ = result
            self._show_music_report(s, c, sk, st)
            dlg._music_panel.refresh()

        long_chk = QCheckBox()
        long_chk.setChecked(bool(getattr(self, "_check_long", False)))
        dlg._long_chk = long_chk

        def on_long_toggled(on: bool):
            self._check_long = on
            rerun()
        long_chk.toggled.connect(on_long_toggled)
        lyt.addWidget(long_chk)

        noise_chk = QCheckBox()
        noise_chk.setChecked(bool(getattr(self, "_check_noise", False)))
        dlg._noise_chk = noise_chk

        def on_noise_toggled(on: bool):
            self._check_noise = on
            rerun()
        noise_chk.toggled.connect(on_noise_toggled)
        lyt.addWidget(noise_chk)

        body = QWidget()
        body_lyt = QVBoxLayout(body)
        body_lyt.setContentsMargins(0, 0, 0, 0)
        dlg._body_lyt = body_lyt

        music_panel = FileDropCheckPanel(
            "Drag <b>.m3u playlists</b> (or audio files) here to check their tracks "
            "for the same issues — tempo label vs measured, TSO takt range, play "
            "length — plus the playlists' round structure (heat tempo spread).",
            run_fn=self._dropped_music_results)
        dlg._music_panel = music_panel
        tabs = QTabWidget()
        tabs.addTab(body, "🎚️  Open playlists")
        tabs.addTab(music_panel, "📂  Drag files in")
        lyt.addWidget(tabs, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.close)
        lyt.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Ctrl+←/→ seek the player ∓30 s while the (non-modal) report is focused.
        sk_back = QShortcut(QKeySequence("Ctrl+Left"), dlg)
        sk_back.activated.connect(lambda: self._seek(-30000))
        sk_fwd = QShortcut(QKeySequence("Ctrl+Right"), dlg)
        sk_fwd.activated.connect(lambda: self._seek(30000))

        def on_finished(_result=0):
            st = getattr(dlg, "_play_state", None)
            if st and st["row"] >= 0:
                self._play_or_stop(None)
            if getattr(self, "_drop_play_btn", None) is not None:
                self._play_or_stop(None)
                self._drop_play_btn = None
            if getattr(self, "_bpm_dlg", None) is dlg:
                self._bpm_dlg = None
        dlg.finished.connect(on_finished)
        return dlg

    def _set_music_report_texts(self, dlg, suspects, checked: int, skipped: int, structure):
        """The info line and the toggle captions for this run's findings."""
        mn = self._check_min_secs()
        mx = self._check_max_secs()
        n_struct = sum(len(w) for _, w, _ in structure) if structure else 0
        mn_txt = f"{mn // 60}:{mn % 60:02d}"
        mx_txt = f"{mx // 60}:{mx % 60:02d}"
        info = (i18n.t("<b>%d</b> of %d checked tracks have at least one issue.")
                % (len(suspects), checked))
        if n_struct:
            info += " " + (
                i18n.t("Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.")
                if n_struct == 1 else
                i18n.t("Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.")) % n_struct
        if skipped:
            info += "<br>" + i18n.t("%d tracks skipped — no label/dance/length or not "
                                    "audio-analyzed.") % skipped
        info += "<br>" + i18n.t("⚡ tempo label vs measured off > %.0f%% (×2, ×3, ×1.5 … slips "
                                "excused) · 🐢/🐇 takt outside the official TSO range · "
                                "⏱ real play ≤ %s") % (self._check_tempo_pct(), mn_txt)
        if getattr(self, "_check_long", False):
            info += " · " + i18n.t("⏳ longer than %s") % mx_txt
        if getattr(self, "_check_noise", False):
            info += " · " + i18n.t("🔇 noise floor above %.0f dB") % self._check_noise_db()
        dlg._info.setText(info + ". " + i18n.t("Thresholds: ⚙ Settings → 🎵 Checks."))
        dlg._long_chk.setText(
            i18n.t("⏳  Also flag long tracks (> %s) — only relevant when building a "
                   "Practice playlist") % mx_txt)
        dlg._noise_chk.setText(
            i18n.t("🔇  Also flag hissy tracks (never quieter than %.0f dB) — measures "
                   "each track once with ffmpeg, so the first run takes a moment")
            % self._check_noise_db())

    def _build_structure_label(self, structure):
        """The yellow round-structure box; its slot links jump into the decks."""
        targets = []   # href index → (deck table, (round, h_idx, d_idx))
        lines = []
        for name, findings, table in structure:
            lines.append(f"<b>{html.escape(name)}</b>")
            for segs in findings:
                parts = []
                for text, slot in segs:
                    esc = html.escape(text)
                    if slot is None:
                        parts.append(esc)
                    else:
                        targets.append((table, slot))
                        parts.append(f'<a href="{len(targets) - 1}">{esc}</a>')
                lines.append("&nbsp;&nbsp;• " + "".join(parts))
        struct_lbl = QLabel(i18n.t("🧩 <b>Round structure</b> — click a spot to "
                                   "jump to it") + "<br>" + "<br>".join(lines))
        struct_lbl.setWordWrap(True)
        struct_lbl.setStyleSheet(
            "background:#fff6e0; border:1px solid #e0c060;"
            "border-radius:4px; padding:6px;")

        def on_struct_link(href, targets=targets):
            table, (rname, h_idx, d_idx) = targets[int(href)]
            if not self._focus_slot_in_deck(table, rname, h_idx, d_idx):
                self.statusBar().showMessage(
                    "⚠  That spot is no longer in an open deck.")
        struct_lbl.linkActivated.connect(on_struct_link)
        return struct_lbl

    def _build_suspects_table(self, dlg, suspects):
        """One row per suspect track, with ▶ listen / 🗑 remove / ↺ replace."""
        t = self._new_suspects_table(suspects)

        state = dlg._play_state
        play_btns: list[QPushButton] = []

        def reset_play_marker():
            if 0 <= state["row"] < len(play_btns):
                play_btns[state["row"]].setText("▶")
            state["row"] = -1
        dlg.reset_play_marker = reset_play_marker

        def on_play(row: int, path: Path):
            if state["row"] == row:
                reset_play_marker()
                self._play_or_stop(None)
                return
            reset_play_marker()
            for tb in self._deckset.all_tables:
                tb.on_playback_stopped()
            self._lib_browser.on_playback_stopped()
            self._play_or_stop(path)
            play_btns[row].setText("■")
            state["row"] = row

        def mark_done(row: int, note: str, new_title: str = ""):
            if state["row"] == row:   # the handled song was playing — stop it
                reset_play_marker()
                self._play_or_stop(None)
            for col in (0, 7):
                w = t.cellWidget(row, col)
                if w is not None:
                    w.setEnabled(False)
            it = t.item(row, 3)
            if it is not None:
                if new_title:
                    it.setText(f"↺  {new_title}")
                else:
                    f = it.font()
                    f.setStrikeOut(True)
                    it.setFont(f)
                it.setToolTip(note)
            self.statusBar().showMessage(note)
            show_toast(self, note)

        def on_remove(row: int, e):
            n = self._remove_track_everywhere(e.path)
            if not n:
                note = i18n.t("⚠  Track no longer in any open deck")
            elif n == 1:
                note = i18n.t("🗑  Removed “%s” from 1 slot — Ctrl+Z undoes") % e.title
            else:
                note = (i18n.t("🗑  Removed “%s” from %d slots — Ctrl+Z undoes")
                        % (e.title, n))
            mark_done(row, note)

        def on_replace(row: int, e):
            new_entry = self._pick_replacement(e)
            if new_entry is None:
                return
            n = self._replace_track_everywhere(e.path, new_entry)
            if not n:
                note = i18n.t("⚠  Track no longer in any open deck")
            elif n == 1:
                note = (i18n.t("↺  Replaced “%s” with “%s” in 1 slot — Ctrl+Z undoes")
                        % (e.title, new_entry.title))
            else:
                note = (i18n.t("↺  Replaced “%s” with “%s” in %d slots — Ctrl+Z undoes")
                        % (e.title, new_entry.title, n))
            mark_done(row, note, new_title=new_entry.title if n else "")

        for r, suspect in enumerate(suspects):
            play_btns.append(self._fill_suspect_row(t, r, suspect, on_play, on_remove, on_replace))

        # Cap the Playlist column to its natural width but never past _PL_COL_CAP,
        # so a multi-playlist Paso Doble can't starve the Title column.
        _PL_COL_CAP = 220
        t.resizeColumnToContents(1)
        if t.columnWidth(1) > _PL_COL_CAP:
            t.setColumnWidth(1, _PL_COL_CAP)

        def on_row_double(row: int, _col: int = 0):
            if 0 <= row < len(suspects):
                e = suspects[row][0]
                if not self._focus_track_in_deck(e.path):
                    self.statusBar().showMessage(
                        i18n.t("⚠  “%s” is no longer in an open deck.") % e.title)
        t.cellDoubleClicked.connect(on_row_double)
        return t

    def _new_suspects_table(self, suspects):
        """The empty suspects table: its columns and how they size."""
        t = QTableWidget(len(suspects), 8)
        t.setHorizontalHeaderLabels(["▶", "Playlist", "Dance", "Title", "Label",
                                     "Length", "Issue(s)", "Action"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # Title
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)   # Issue(s)
        for c in (0, 2, 4, 5, 7):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        # Playlist (1): size to content but CAPPED — a track that sits in many
        # playlists (typical for Paso Doble) would otherwise blow this column up
        # and crush the Title to the point it's unreadable. Full list is in the
        # cell tooltip + the item elides with "…" when the cap kicks in.
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hh.setMinimumSectionSize(24)
        return t

    def _fill_suspect_row(self, t, r: int, suspect, on_play, on_remove, on_replace):
        """Fill row `r` for one suspect; returns its ▶ button."""
        e, _bpb, _measured, dur, issues, pnames = suspect
        pb = QPushButton("▶")
        pb.setFixedSize(26, 22)
        pb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pb.setToolTip("Listen to this track")
        pb.clicked.connect(lambda _=False, row=r, p=e.path: on_play(row, p))
        t.setCellWidget(r, 0, pb)
        pl_txt = ", ".join(pnames)
        pl_it = QTableWidgetItem(pl_txt)
        pl_it.setToolTip(i18n.t("In playlist: %s") % pl_txt)
        t.setItem(r, 1, pl_it)
        tip = entry_tooltip(e)
        dance_it = QTableWidgetItem(dance_name(e.dance, e.dance or "?"))
        dance_it.setToolTip(tip)
        t.setItem(r, 2, dance_it)
        title_it = QTableWidgetItem(e.title or "")
        title_it.setToolTip(tip)
        t.setItem(r, 3, title_it)
        label_txt = f"T{e.bpm}" if getattr(e, "bpm", 0) else "—"
        len_txt = f"{dur // 60}:{dur % 60:02d}" if dur else "—"
        for col, txt, center in ((4, label_txt, True), (5, len_txt, True),
                                 (6, "  ·  ".join(issues), False)):
            it = QTableWidgetItem(txt)
            if center:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it.setToolTip(tip)
            else:
                it.setToolTip("\n".join(issues))
            t.setItem(r, col, it)
        act = QWidget()
        ah = QHBoxLayout(act)
        ah.setContentsMargins(2, 0, 2, 0)
        ah.setSpacing(4)
        rm = QPushButton("🗑")
        rm.setFixedSize(26, 22)
        rm.setToolTip("Remove from the playlist(s) — the slot stays "
                      "empty (Ctrl+Z undoes)")
        rm.clicked.connect(lambda _=False, row=r, ent=e: on_remove(row, ent))
        rp = QPushButton("↺")
        rp.setFixedSize(26, 22)
        rp.setToolTip("Replace via the similar-tracks picker")
        rp.clicked.connect(lambda _=False, row=r, ent=e: on_replace(row, ent))
        ah.addWidget(rm)
        ah.addWidget(rp)
        t.setCellWidget(r, 7, act)
        t.setRowHeight(r, 26)
        return pb

    def _dropped_music_results(self, paths: list, progress_cb=None) -> QWidget:
        """Tab 2 of the Music check: run the same tempo / TSO / length checks over the
        tracks of dragged-in .m3u playlists (or loose audio files). Read-only — ▶ to
        listen; the open-deck remove / replace actions don't apply here."""
        if getattr(self, "_drop_play_btn", None) is not None:
            self._play_or_stop(None)
            self._drop_play_btn = None
        box = QWidget()
        v = QVBoxLayout(box)
        if not self._library.lib or self._library.cache is None:
            v.addWidget(QLabel("Load the music library first."))
            v.addStretch(1)
            return box

        checked, skipped, suspects = self._check_dropped_tracks(paths, progress_cb)

        # Round-structure warnings for dropped .m3u playlists: rebuild each one's
        # rounds/heats grid the same way 📂 Import does, so playlist-level issues
        # (e.g. a WW round split over T58 / T59 / T60 heats) are flagged here too —
        # the per-track checks above can't see across heats.
        structure = self._dropped_structure_issues(paths, self._library.lib,
                                                   self._library.cache)

        n_struct = sum(len(w) for _, w in structure)
        head_txt = (i18n.t("<b>%d</b> of %d checked tracks have an issue.")
                    % (len(suspects), checked))
        if n_struct:
            head_txt += " " + (
                i18n.t("Plus <b>%d</b> 🧩 round-structure issue — see the yellow box below.")
                if n_struct == 1 else
                i18n.t("Plus <b>%d</b> 🧩 round-structure issues — see the yellow box below.")) % n_struct
        if skipped:
            head_txt += "<br>" + i18n.t("%d skipped — not found / not audio-analyzed.") % skipped
        head = QLabel(
            head_txt + "<br>"
            + i18n.t("⚡ tempo label vs measured · 🐢/🐇 takt outside the TSO range · "
                     "⏱ short · ⏳ long · 🔇 hiss · 🧩 round structure (uneven dances, "
                     "heat taper, heat tempo spread)."))
        head.setWordWrap(True)
        v.addWidget(head)
        self._add_structure_box(v, structure)
        if not suspects:
            v.addStretch(1)
            return box

        t = QTableWidget(len(suspects), 6)
        t.setHorizontalHeaderLabels(["▶", "Playlist", "Dance", "Title", "Label",
                                     "Issue(s)"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 2, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        def on_play(p, btn):
            cur = getattr(self, "_drop_play_btn", None)
            if cur is btn:                          # same row → stop
                self._play_or_stop(None)
                btn.setText("▶")
                self._drop_play_btn = None
                return
            if cur is not None:
                cur.setText("▶")
            for tb in self._deckset.all_tables:
                tb.on_playback_stopped()
            self._lib_browser.on_playback_stopped()
            self._play_or_stop(p)
            btn.setText("■")
            self._drop_play_btn = btn

        for r, (e, issues, pname) in enumerate(suspects):
            pb = QPushButton("▶")
            pb.setFixedSize(26, 22)
            pb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            pb.setToolTip("Listen to this track")
            pb.clicked.connect(lambda _=False, p=e.path, b=pb: on_play(p, b))
            t.setCellWidget(r, 0, pb)
            pl_it = QTableWidgetItem(pname)
            pl_it.setToolTip(pname)
            t.setItem(r, 1, pl_it)
            t.setItem(r, 2, QTableWidgetItem(dance_name(e.dance, e.dance or "?")))
            title_it = QTableWidgetItem(e.title or "")
            title_it.setToolTip(str(e.path))
            t.setItem(r, 3, title_it)
            lab = QTableWidgetItem(f"T{e.bpm}" if getattr(e, "bpm", 0) else "—")
            lab.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 4, lab)
            iss_it = QTableWidgetItem("  ·  ".join(issues))
            iss_it.setToolTip("\n".join(issues))
            t.setItem(r, 5, iss_it)
            t.setRowHeight(r, 26)
        v.addWidget(t, stretch=1)
        return box

    def _check_dropped_tracks(self, paths, progress_cb):
        """The per-track checks over every dropped list's tracks."""
        file_tracks: list[tuple] = []
        for p in paths:
            if p.suffix.lower() in (".m3u", ".m3u8"):
                file_tracks.append((p.name, self._m3u_track_paths(p)))
            else:
                file_tracks.append((p.name, [p]))
        total = sum(len(ts) for _, ts in file_tracks)
        resolved: list[tuple] = []          # (playlist_name, entry or None)
        for name, tracks in file_tracks:
            for t in tracks:
                resolved.append((name, self._external_entry(t)))
                if progress_cb and len(resolved) % 25 == 0:
                    progress_cb(0, total)
        done = checked = skipped = 0
        suspects: list[tuple] = []          # (entry, issues, playlist_name)
        pool = ThreadPoolExecutor(max_workers=_PROBE_WORKERS)
        try:
            jobs = self._submit_probes(pool, [e for _, e in resolved if e is not None])
            for name, e in resolved:
                done += 1
                # Every track: with 🔇 on each one may wait on a seconds-long noise
                # probe, and the tick is where the panel redraws and hears Cancel.
                if progress_cb:
                    progress_cb(done, total)
                if e is None:
                    skipped += 1
                    continue
                checked += 1
                self._collect_probes(
                    jobs, e, lambda d=done: progress_cb and progress_cb(d, total))
                issues = self._track_issues(e)
                if issues:
                    suspects.append((e, issues, name))
        finally:
            # A Cancel leaves the probes already running to finish on their own.
            pool.shutdown(wait=False, cancel_futures=True)
        return checked, skipped, suspects

    def _dropped_structure_issues(self, paths, lib, cache):
        """🧩 Each dropped .m3u's round-structure warnings, by file name."""
        structure: list[tuple] = []
        for p in paths:
            if p.suffix.lower() not in (".m3u", ".m3u8"):
                continue
            try:
                res = import_playlist_m3u(p, lib, cache)
                warns = (self._grid_structure_issues(res["playlist"], res["dances"])
                         if res.get("playlist") else [])
            except Exception:
                warns = []
            if warns:
                structure.append((p.name, warns))
        return structure

    def _add_structure_box(self, v, structure):
        """🧩 The yellow box listing the round-structure warnings."""
        if structure:
            lines = []
            for name, warns in structure:
                lines.append(f"<b>{html.escape(name)}</b>")
                lines.extend("&nbsp;&nbsp;• " + html.escape(w) for w in warns)
            struct_lbl = QLabel(i18n.t("🧩 <b>Round structure</b>") + "<br>" + "<br>".join(lines))
            struct_lbl.setWordWrap(True)
            struct_lbl.setStyleSheet(
                "background:#fff6e0; border:1px solid #e0c060;"
                "border-radius:4px; padding:6px;")
            v.addWidget(struct_lbl)

    def _remove_track_everywhere(self, path) -> int:
        """Empty every open-deck slot holding `path` (incl. ↳ backups).
        Returns the number of slots cleared."""
        n = 0
        for table in self._checkable_deck_tables():
            rows = {r for r, m in enumerate(table._row_meta)
                    if m and m.entry is not None
                    and str(m.entry.path) == str(path)}
            if rows and table._clear_slots_at(rows):
                n += len(rows)
        return n

    def _replace_track_everywhere(self, path, new_entry) -> int:
        """Swap every open-deck occurrence of `path` for `new_entry`.
        Returns the number of slots replaced."""
        n = 0
        for table in self._checkable_deck_tables():
            hit = False
            for r, m in enumerate(table._row_meta):
                if (m and m.entry is not None
                        and str(m.entry.path) == str(path)
                        and self._replace_occurrence(table, r, new_entry)):
                    n += 1
                    hit = True
            if hit:
                table._notify_changed()
        return n

    # ── 🎉 The party check: the rules the Eintanzen list was built from ────────
    # Grouped in the report the way they are grouped in the engine, with the
    # heading each group gets and the colour the panel is drawn in.
    _PARTY_GROUPS = (
        (party_check.ROUNDS, "🔁 Rounds", "#fff6e0", "#e0c060"),
        (party_check.SPACING, "⏳ Spacing", "#fff6e0", "#e0c060"),
        (party_check.DUPLICATES, "👯 Duplicates", "#ffeaea", "#e0a0a0"),
        (party_check.TAKT, "🎚 Takt", "#eaf2ff", "#a0b8e0"),
        (party_check.LENGTH, "⏱ Length", "#eaf2ff", "#a0b8e0"),
    )

    def _party_findings(self) -> list:
        """The loaded party list read back against its own rules.

        The two late gates come from the options the list was last built with
        — checking against a gate the operator turned off would be inventing a
        rule they declined. Likewise the openers: one the source had no
        tracks for was never owed."""
        t = self._deckset.warmup_table
        opts = getattr(self, "_warmup_opts", None) or {}
        etds = opts.get("etds") or {}
        return party_check.party_findings(
            t._row_meta.entries(),
            beats_per_bar=self._BEATS_PER_BAR,
            late_ww=etds.get("late_ww", True),
            late_pd=etds.get("late_pd", True),
            available=opts.get("dances"))

    def _check_party_list(self):
        """🩺 on the 🤸 Eintanzen header: check the list in place and report."""
        t = self._deckset.warmup_table
        n = len(t._row_meta.song_rows())
        if not n:
            return
        findings = self._party_findings()
        log.info("🎉 Party list checked\n"
                 "tracks: %d\n"
                 "findings: %d", n, len(findings))
        self._show_party_report(findings, n)

    def _reveal_warmup_row(self, row: int) -> None:
        """Jump to a row of the party list — the panel unfolds first, since a
        finding is worth nothing if it points into a collapsed header strip."""
        if self._warmup_closed:
            self._on_warmup_toggle(True)
        if self._warmup_folded:
            self._toggle_warmup_fold(False)
        self._reveal_deck_row(self._deckset.warmup_table, row)

    def _show_party_report(self, findings, n_tracks: int):
        """Non-modal report: one panel per rule group, every row number a link
        back into the list. Non-modal on purpose — the point is to fix the
        list while reading it."""
        dlg = getattr(self, "_party_dlg", None)
        # It deletes itself on close, so a report closed earlier is gone.
        if dlg is not None and shiboken6.isValid(dlg) and dlg.isVisible():
            dlg.close()
        dlg = QDialog(self)
        dlg.setWindowTitle("🎉  Party check")
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._party_dlg = dlg
        lyt = QVBoxLayout(dlg)

        label = self._deckset.warmup_table._warmup_label or i18n.t("Party list")
        # Built by `%`, so the hook never sees it: the whole sentence is the
        # key, one per plural, rather than a "finding"/"findings" word dropped
        # into a template that no language but English builds that way.
        head = QLabel(
            i18n.t("🎉 <b>%s</b> — %d titles, 1 finding"
                   if len(findings) == 1 else
                   "🎉 <b>%s</b> — %d titles, %d findings")
            % ((html.escape(label), n_tracks) if len(findings) == 1
               else (html.escape(label), n_tracks, len(findings))))
        head.setWordWrap(True)
        lyt.addWidget(head)

        # Song row N of the engine is table row song_rows[N] — the ═══ section
        # headers sit between them and are rows of their own.
        song_rows = self._deckset.warmup_table._row_meta.song_rows()
        targets: list[int] = []

        def panel(title, group, bg, border):
            lines = []
            for f in group:
                parts = []
                for text, row in f.segments:
                    esc = html.escape(text)
                    if row is None or row >= len(song_rows):
                        parts.append(esc)
                    else:
                        targets.append(song_rows[row])
                        parts.append(f'<a href="{len(targets) - 1}">{esc}</a>')
                lines.append("&nbsp;&nbsp;• " + "".join(parts))
            lbl = QLabel(f"<b>{i18n.t(title)}</b><br>" + "<br>".join(lines))
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"background:{bg}; border:1px solid {border};"
                              "border-radius:4px; padding:6px;")
            lbl.linkActivated.connect(
                lambda href: self._reveal_warmup_row(targets[int(href)]))
            lyt.addWidget(lbl)

        for category, title, bg, border in self._PARTY_GROUPS:
            group = [f for f in findings if f.category == category]
            if group:
                panel(title, group, bg, border)

        if not findings:
            ok = QLabel("✅  Nothing to report — the list reads like one the "
                        "party builder would have made.")
            ok.setWordWrap(True)
            lyt.addWidget(ok)

        lyt.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        again = QPushButton("↻  Check again")
        again.clicked.connect(lambda: (dlg.close(), self._check_party_list()))
        row.addWidget(again)
        close = QPushButton("Close")
        close.clicked.connect(dlg.close)
        row.addWidget(close)
        lyt.addLayout(row)

        dlg.resize(760, 420)
        dlg.show()
