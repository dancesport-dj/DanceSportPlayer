#!/usr/bin/env python3
"""Background QThread workers of the Dancesport Playlist Planner GUI.

Extracted from dancesport_gui.py (light split): every long-running job the GUI
runs off the UI thread — library scans (favorites + whole repo + warm-cache
reload), librosa audio analysis, deep-embedding index/rank jobs, the
similar-to-dropped-file pipeline and the OpenRouter chat / model fetches.
Pure logic + signals only, no widgets.
"""

import itertools
import threading
import time
import logging
from collections import deque
from contextlib import closing
from concurrent.futures import CancelledError, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QThread, Signal

log = logging.getLogger("dancesport.workers")

from planner.ai import openrouter_chat, openrouter_free_models
from planner.db import AudioCache, GlobalScanCache, db_maintenance
from planner.library import MusicLibrary
from planner.models import ScanCancelled, ALLOW_REPEAT
from planner.warmup import build_class_warmup, build_warmup_playlist
from planner.parsing import _detect_dance
from planner import custom_field, event_plan, i18n, llm
from planner.planned import path_key
from planner.playlist_text import read_playlist_text
from shared.audio_probes import detect_pd_highlights, detect_silences, measure_lufs


# ─────────────────────────────────────────────────────────────────────────────
# Orphaned workers
# ─────────────────────────────────────────────────────────────────────────────
# Qt aborts the process (0xC0000409, no traceback) when a QThread is destroyed
# while it still runs. A window that goes away mid-job hands its workers here:
# they run out unparented and silent, held until they are done.
_ORPHANS: list = []


def adopt_running(worker) -> bool:
    """Keep `worker` alive past its window if it is still running.

    Cancels it where it can be, unparents it and blocks its signals — the
    slots it would reach belong to a window that is gone. Finished orphans are
    let go on the next adoption, not from their own `finished`: that slot would
    run in the worker's thread and free the QThread from inside itself."""
    _ORPHANS[:] = [w for w in _ORPHANS if w.isRunning()]
    if not worker.isRunning():
        return False
    cancel = getattr(worker, "cancel", None)
    if callable(cancel):
        cancel()
    worker.blockSignals(True)
    worker.setParent(None)
    _ORPHANS.append(worker)
    return True


def orphans_running() -> bool:
    """Whether an adopted worker still runs (see `dancesport_gui.exit_app`)."""
    return any(w.isRunning() for w in _ORPHANS)

# ─────────────────────────────────────────────────────────────────────────────
# Library Loader (background QThread)
# ─────────────────────────────────────────────────────────────────────────────
class LibraryLoader(QThread):
    """Loads the favorites MusicLibrary in a background thread.
    Runs the scan non-interactively (no stdin prompt; analysis is deferred to
    the explicit AudioAnalyzer worker).
    """
    status      = Signal(str)
    finished_ok = Signal(object, object)   # (MusicLibrary, AudioCache)
    error       = Signal(str)

    def __init__(self, music_dir=None, parent=None):
        super().__init__(parent)
        self._music_dir = Path(music_dir) if music_dir else None
        self._cancel = False

    def cancel(self):
        """Give up the scan — the window is closing before it finished.

        A cold start walks a few thousand files, and Qt aborts the process
        outright (0xC0000409, no traceback) if this thread is still running
        when it is destroyed. Polled by the scan itself, like every other
        worker here, so quitting on the splash costs a file rather than the
        five-second wait _stop_workers would otherwise sit through."""
        self._cancel = True

    def run(self):
        try:
            self.status.emit("Loading audio cache…")
            cache = AudioCache()
            self.status.emit("Scanning music files…")
            lib = MusicLibrary()
            lib.scan(cache, music_dir=self._music_dir, interactive=False,
                     progress_cb=self._report,
                     should_cancel=lambda: self._cancel)
            self.finished_ok.emit(lib, cache)
        except ScanCancelled:
            pass          # the window is going; there is nobody to tell
        except Exception as exc:
            self.error.emit(str(exc))

    def _report(self, done: int, total: int, path: Path, _reused: bool):
        """Splash text for the scan. A cold start reads a few thousand files and
        used to sit on one unchanging line the whole time, which is
        indistinguishable from a hang. The library already throttles this to
        every 25th file."""
        if not total:            # the "listing the folder" phase, before the count
            self.status.emit("Scanning music files…\nlisting the library folder")
            return
        name = path.name
        if len(name) > 46:       # the splash is a fixed 420 px wide
            name = name[:45] + "…"
        self.status.emit(f"Scanning music files… {done:,} / {total:,}\n{name}")


class GlobalLibraryLoader(QThread):
    """Scans the whole music repository (metadata + already-cached features only).

    No playlist learning, no librosa analysis and no special-folder skipping —
    just the widest read-only index, so a dropped file can be matched against
    everything. Files without cached features are simply skipped at ranking time.
    """
    done      = Signal(object)        # MusicLibrary
    error     = Signal(str)
    cancelled = Signal()
    progress  = Signal(int, int, str, bool)   # done, total, current filename, reused

    def __init__(self, cache, music_dir, parent=None):
        super().__init__(parent)
        self._cache = cache
        self._dir   = Path(music_dir)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            lib = MusicLibrary()
            lib.scan(self._cache, music_dir=self._dir,
                     skip_special=False, learn=False, analyze=False,
                     global_cache=GlobalScanCache(),
                     progress_cb=lambda done, total, path, reused:
                         self.progress.emit(done, total, path.name, reused),
                     should_cancel=lambda: self._cancel,
                     interactive=False)
            self.done.emit(lib)
        except ScanCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class GlobalCacheLoader(QThread):
    """Rebuilds the whole-repo library from the warm global cache, OFF the UI thread.

    No filesystem walk and no analysis — just reconstructs cached entries (53k+ of
    them, which still takes a moment) so the UI stays responsive behind a small
    'Loading from cache…' window. Emits an empty library when the cache is cold so
    the caller can fall back to a full scan.
    """
    done  = Signal(object)   # MusicLibrary
    error = Signal(str)

    def __init__(self, cache, parent=None):
        super().__init__(parent)
        self._cache = cache

    def run(self):
        try:
            lib = MusicLibrary()
            lib.load_from_global_cache(self._cache, GlobalScanCache())
            self.done.emit(lib)
        except Exception as exc:
            self.error.emit(str(exc))


class DbMaintenanceWorker(QThread):
    """Runs planner.db_maintenance() (orphan cleanup + VACUUM) off the UI thread.

    VACUUM rewrites the whole DB file (hundreds of MB), so this can take a while.
    """
    done  = Signal(object)   # result dict {"removed": …, "size_before": …, "size_after": …}
    error = Signal(str)

    def run(self):
        try:
            self.done.emit(db_maintenance())
        except Exception as exc:
            self.error.emit(str(exc))


class PlaylistRelearnWorker(QThread):
    """Re-learns playlist popularity from the M3U folder alone, off the UI thread.

    No file walk / no audio analysis — MusicLibrary.relearn_playlists() just
    re-reads the playlist text files and re-applies popularity per entry.
    """
    done  = Signal(int)      # number of M3U files analyzed
    error = Signal(str)

    def __init__(self, lib: MusicLibrary, parent=None):
        super().__init__(parent)
        self._lib = lib

    def run(self):
        try:
            self.done.emit(self._lib.relearn_playlists())
        except Exception as exc:
            self.error.emit(str(exc))


class CustomFieldReader(QThread):
    """Reads the frame the Custom field is newly mapped to, for every listed
    file — one ID3 read each, some seconds for a whole library. Only reads:
    MusicLibrary.read_custom stores the values on the GUI thread."""
    done = Signal(object)    # {path: value}

    def __init__(self, paths: list[str], parent=None):
        super().__init__(parent)
        self._paths = paths

    def run(self):
        self.done.emit({p: custom_field.read_file(p) for p in self._paths})


# ─────────────────────────────────────────────────────────────────────────────
# Audio Analyzer (background QThread)
# ─────────────────────────────────────────────────────────────────────────────
class AudioAnalyzer(QThread):
    """Runs librosa analysis on files missing from cache; emits per-file progress.

    Byte-identical duplicates are analyzed once (shared MFCC bucket), and the run
    can be cancelled cooperatively via cancel().
    """
    progress  = Signal(int, int, int, str, float)  # (done, total, errors, name, eta_seconds)
    # NOT named `finished`: QThread already has a built-in `finished` signal and
    # shadowing it breaks native thread-lifecycle connections (e.g. deleteLater).
    done      = Signal(int, int)             # (ok, errors)
    report    = Signal(dict)                 # {ok, errors, skipped, reasons}
    cancelled = Signal(int)                  # (analyzed so far)

    def __init__(self, cache: AudioCache, entries: list, parent=None, force: bool = False):
        super().__init__(parent)
        self._cache   = cache
        self._entries = entries
        self._cancel  = False
        self._force   = force

    def cancel(self):
        self._cancel = True

    def run(self):
        # Why files failed, and how many of those failures no retry could ever
        # fix: a track the library still lists but that is gone from disk is
        # reported as skipped, not as an error.
        reasons: dict[str, int] = {}
        skipped = 0

        def note(path: Path, exc: Exception):
            nonlocal skipped
            if not path.exists():
                why = "not on disk any more"
                skipped += 1
            else:
                why = str(exc)[:120] or exc.__class__.__name__
            reasons[why] = reasons.get(why, 0) + 1

        ok, errors, was_cancelled = self._cache.analyze_entries(
            self._entries,
            progress_cb=lambda done, total, errors, path, eta:
                self.progress.emit(done, total, errors, path.name, eta),
            should_cancel=lambda: self._cancel,
            force=self._force,
            on_error=note)
        if was_cancelled:
            self.cancelled.emit(ok)
        else:
            self.report.emit({"ok": ok, "errors": errors - skipped,
                              "skipped": skipped, "reasons": reasons})
            self.done.emit(ok, errors - skipped)


# ─────────────────────────────────────────────────────────────────────────────
# Warm-up / ETDS playlist builder (background QThread)
# ─────────────────────────────────────────────────────────────────────────────
class WarmupBuilder(QThread):
    """Builds a warm-up / ETDS party playlist off the UI thread so a large
    library doesn't freeze the window during generation.

    mode='class' → planner.build_class_warmup (one tournament class, round-robin,
    TSO-conform, popular+fresh mix); mode='etds' → planner.build_warmup_playlist
    (alternating 3-dance party rounds). Emits per-track progress for a BusyDialog.
    """
    progress = Signal(int, int)        # (done, total)
    done     = Signal(object)          # list[MusicEntry]
    error    = Signal(str)

    def __init__(self, entries, mode, params, parent=None):
        super().__init__(parent)
        self._entries = list(entries)
        self._mode    = mode
        self._params  = dict(params)

    def run(self):
        try:
            if self._mode == "class":
                params = dict(self._params)
                style = params.pop("style")
                dance_class = params.pop("dance_class")
                res = build_class_warmup(
                    self._entries, style, dance_class,
                    progress_cb=lambda d, t: self.progress.emit(d, t),
                    **params)
            else:
                res = build_warmup_playlist(
                    self._entries,
                    progress_cb=lambda d, t: self.progress.emit(d, t),
                    **self._params)
            self.done.emit(res)
        except Exception as exc:
            log.exception("🤸 warm-up build failed")
            self.error.emit(str(exc))



class AiPlaylistWorker(QThread):
    """Asks an LLM for a playlist off the UI thread — `claude -p` can easily
    think for a couple of minutes over a 1500-track catalog.

    Emits the raw picks (catalog numbers); turning those back into MusicEntry
    rows is the window's job, since only it knows the round structure."""
    done  = Signal(object, str, str)   # (picks, notes, backend)
    error = Signal(str)
    step  = Signal(str, str, str)      # (role, title, text) — the live transcript
    cancelled = Signal()               # ⏹ — stopped on request, nothing to show

    def __init__(self, rules, task, candidates, model, config_dir, parent=None,
                 dance_class=None, used_paths=(), lib=None):
        super().__init__(parent)
        self._rules = rules
        self._task = task
        self._candidates = list(candidates)
        self._model = model
        self._config_dir = config_dir
        # Only used to describe a track to the model: the play count is weighted
        # for the start class, and "used" means an open deck already took it.
        self._dance_class = dance_class
        self._used_paths = set(used_paths)
        # The library's playlist index, so the model can be told which of the
        # tracks on the table have been played in the same events. Read-only
        # lookups in a dict of sets — safe to reach into from this thread.
        self._lib = lib
        self._cancel = threading.Event()

    def cancel(self):
        """Ask the run to stop. Safe from the UI thread: a `claude -p` still
        thinking is killed, a retry wait ends, no fallback is started. An HTTP
        request already on the wire can't be cut; its answer is dropped."""
        self._cancel.set()

    def run(self):
        try:
            picks, notes, backend = llm.ask_playlist(
                self._rules, self._task, self._candidates,
                model=self._model, config_dir=self._config_dir,
                dance_class=self._dance_class, used_paths=self._used_paths,
                on_step=self.step.emit,
                playlists_of=self._lib.playlists_for if self._lib else None,
                cancel=self._cancel)
            self.done.emit(picks, notes, backend)
        except llm.Cancelled:
            log.info("⏹ AI playlist stopped")
            self.cancelled.emit()
        except Exception as exc:
            log.exception("🤖 AI playlist failed")
            self.error.emit(str(exc))


class EventPlanWorker(QThread):
    """🏆 Event: plans the day's variants off the UI thread and, if asked, has
    the AI check them — one question per competition, all at once.

    Handed `variants` and `cands_list` of an earlier run it gathers and plans
    nothing and only asks again, for the competitions in `only` (the ones a
    rate limit held back, or the second round)."""
    done = Signal(object, object)      # (event_plan.RefineResult, cands_list)
    error = Signal(str)
    step = Signal(str, str, str)       # (role, title, text) — the live transcript
    cancelled = Signal()

    def __init__(self, lib, specs, editions, *, profiles=(), use_class=True,
                 new_share=None, rare_share=None, ask_ai=True, rules="", model="",
                 config_dir="",
                 variants=None, cands_list=None, only=None, ask=None,
                 similar=None, parent=None):
        super().__init__(parent)
        self._lib = lib
        self._specs = list(specs)
        self._editions = list(editions)
        self._profiles = list(profiles)
        self._use_class = use_class
        self._new_share = new_share
        self._rare_share = rare_share
        self._ask_ai = ask_ai or variants is not None
        self._rules = rules
        self._model = model
        self._config_dir = config_dir
        self._variants = variants
        self._cands_list = cands_list
        self._only = only
        self._ask = ask            # tests: stands in for the model
        self._similar = similar    # tests: stands in for the timbre look-up
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            cands_list = self._cands_list
            if cands_list is None:
                cands_list = []
                for spec in self._specs:
                    if self._cancel.is_set():
                        raise llm.Cancelled()
                    cands_list.append(event_plan.gather_candidates(
                        self._lib, spec, self._editions, similar=self._similar,
                        use_class=self._use_class))
                self.step.emit("note", "Titles to choose from", "\n".join(
                    f"{c.spec.label}: "
                    + i18n.t("%d from this event's past years, %d from other "
                             "events' lists of the class, %d new in the archive, "
                             "%d rarely played at the class (new ones included)") % (
                        len({str(p.entry.path) for rnd in c.event
                             for picks in rnd.values() for p in picks}),
                        len({str(p.entry.path) for rnd in c.klass
                             for picks in rnd.values() for p in picks}),
                        sum(len(picks) for picks in c.new.values()),
                        sum(len(picks) for picks in c.rare.values()))
                    for c in cands_list))
            variants = self._variants
            if variants is None:
                if self._cancel.is_set():
                    raise llm.Cancelled()
                variants = {p: event_plan.plan_variant(
                                cands_list, p, new_share=self._new_share,
                                rare_share=self._rare_share)
                            for p in self._profiles}
            if self._ask_ai:
                result = event_plan.refine_with_ai(
                    variants, cands_list, rules=self._rules, ask=self._ask,
                    model=self._model, config_dir=self._config_dir,
                    on_step=self.step.emit, cancel=self._cancel,
                    only=self._only)
            else:
                result = event_plan.RefineResult(variants)
            self.done.emit(result, cands_list)
        except llm.Cancelled:
            log.info("⏹ event plan stopped")
            self.cancelled.emit()
        except Exception as exc:
            log.exception("🏆 event plan failed")
            self.error.emit(str(exc))


class LibraryPass(QThread):
    """One measurement pass over a list of library tracks.

    A pass says two things about itself — `todo()`, the tracks that still need
    the measurement, and `measure(path)`, how one track is measured and stored.
    Everything around them lives here: the cooperative cancel, the save cadence,
    the live ETA, the error tally and the four signals the GUI wires up. That is
    what the four passes below had a copy of each, and a fix to one copy (the
    save-on-cancel, say) reached only the pass it was made in.

    Results are content-fingerprint-keyed by the cache, so byte-identical files
    share one measurement whichever pass wrote it.
    """
    progress = Signal(int, int, int, str, float)   # (done, total, errors, name, eta)
    done = Signal(int, int)                        # (measured, errors)
    # What the run ran into, for the closing report: counts plus {reason: files}.
    # Separate from `done` so the pipeline keeps one flow signal.
    report = Signal(dict)                          # {ok, errors, skipped, reasons}
    cancelled = Signal(int)                        # (measured so far)
    error = Signal(str)

    save_every = 20
    fail_hint = "the measurement failed, see the log"
    # How many tracks may be measured side by side. 1 keeps the pass strictly
    # serial (`measure`); above that the pass must split itself into `compute`
    # (expensive, cache-free, runs in the pool) and `store` (writes, always on
    # this thread — SQLite keeps one writer and the save cadence is unchanged).
    # Measured 2026-09-18 over the 3859-track library, cold: one ffmpeg at a
    # time is 30 min with 15 of 16 cores idle, four is 7.5, eight is 5.0,
    # twelve is 4.2. Eight is where the curve flattens.
    workers = 1

    def __init__(self, cache: AudioCache, paths: list, parent=None):
        super().__init__(parent)
        self.cache = cache
        self.paths = paths
        self._cancel = False
        self._pool = None

    def cancel(self):
        self._cancel = True
        pool = self._pool
        if pool is not None:
            # Drop what has not started; the few already decoding run out.
            pool.shutdown(wait=False, cancel_futures=True)

    def todo(self) -> list:
        """The subset of `paths` this pass still has work for."""
        raise NotImplementedError

    def measure(self, path: Path) -> bool:
        """Measure one track and put it in the cache; False when it failed.

        The serial form, and still the whole of a pass that sets `workers = 1`.
        A parallel pass overrides `compute`/`store` instead and never gets here.
        """
        raise NotImplementedError

    def compute(self, path: Path):
        """The expensive half of the measurement, or None when it failed.

        Runs in a worker thread, possibly several at once, so it must touch
        nothing shared — above all not the cache, whose SQLite connection is
        thread-local. Only called when `workers` > 1."""
        raise NotImplementedError

    def store(self, path: Path, result) -> bool:
        """Put one computed result in the cache; False when it was no good.
        Always on the pass thread, one track at a time."""
        raise NotImplementedError

    def _measured(self, todo: list):
        """Yield (path, ok-flag-or-result) for each track, in the order of
        `todo`, measuring `workers` of them at a time.

        Order matters: progress, the ETA and the closing report all read as if
        the pass walked the list, and it does — only the decoding runs ahead.
        The window is bounded so a 4000-track pass does not submit 4000 jobs
        and lose the ability to stop."""
        if self.workers <= 1:
            for path in todo:
                # Before the measurement, not after: a cancelled serial pass has
                # always stopped without decoding one more track.
                if self._cancel:
                    return
                yield path, self.measure(path)
            return
        pool = ThreadPoolExecutor(max_workers=self.workers,
                                  thread_name_prefix="pass")
        self._pool = pool
        try:
            pending = deque()
            nxt = iter(todo)
            # Keep one full window in flight ahead of what is being stored.
            for path in itertools.islice(nxt, self.workers * 2):
                pending.append((path, pool.submit(self.compute, path)))
            while pending:
                path, fut = pending.popleft()
                if self._cancel:
                    return
                try:
                    result = fut.result()
                except CancelledError:
                    return
                yield path, (self.store(path, result)
                             if result is not None else False)
                follow = next(nxt, None)
                if follow is not None and not self._cancel:
                    pending.append((follow, pool.submit(self.compute, follow)))
        finally:
            self._pool = None
            # Wait for the decodes already running: a pass that has returned
            # must not leave ffmpeg or Demucs behind it (see `run`).
            pool.shutdown(wait=True, cancel_futures=True)

    def failure(self, path: Path) -> tuple[bool, str]:
        """Why `measure` failed on `path`, and whether it counts as a failure.

        A file that is not on disk any more cannot be measured by any number of
        retries: it is reported as skipped, never as an error, so a library that
        still lists a deleted track does not colour a run that did everything it
        could do.
        """
        if not path.exists():
            return False, "not on disk any more"
        return True, self.fail_hint

    def run(self):
        try:
            todo = self.todo()
            total = len(todo)
            ok = errors = skipped = 0
            reasons: dict[str, int] = {}
            t0 = time.monotonic()
            measured_all = self._measured(todo)
            # Closed before `cancelled` goes out, which waits for the decodes
            # still in flight: the signal frees the GUI to start the next pass,
            # and a pass that has returned is what quitting no longer waits for.
            with closing(measured_all):
                for i, (path, measured) in enumerate(measured_all, 1):
                    if self._cancel:
                        break
                    if measured:
                        ok += 1
                    else:
                        counts, why = self.failure(path)
                        reasons[why] = reasons.get(why, 0) + 1
                        if counts:
                            errors += 1
                        else:
                            skipped += 1
                    if i % self.save_every == 0:
                        self.cache.save()
                    elapsed = time.monotonic() - t0
                    eta = (elapsed / i) * (total - i) if elapsed > 0 else -1.0
                    self.progress.emit(i, total, errors, path.name, eta)
            if self._cancel:
                self.cache.save()
                self.cancelled.emit(ok)
                return
            self.cache.save()
            self.report.emit({"ok": ok, "errors": errors, "skipped": skipped,
                              "reasons": reasons})
            self.done.emit(ok, errors)
        except Exception as exc:
            self.error.emit(str(exc))


class AudioFpAnalyzer(LibraryPass):
    """Records the tag-free audio fingerprint of every file that has none yet.

    Not a measurement but insurance: it is what lets a LATER mp3tag edit keep the
    track's analysis instead of orphaning it (AudioCache.reattach_retagged), and
    once the tag editor has written, the audio fingerprint of the file as it was
    can never be recovered. Two ~64 KB reads per track and no decoding, so this is
    by far the cheapest pass — and after one run it has nothing left to do.
    """
    save_every = 200
    fail_hint = "the file could not be read"
    # Stays serial, unlike the decoding passes: measured at 0.19 s per 120 cold
    # files, the whole library is ~6 s, and `ensure_audio_fp` interleaves its DB
    # reads with the file reads, so splitting it would mean restructuring
    # AudioCache to save four seconds.

    def todo(self) -> list:
        have = self.cache.audio_fp_keys()
        # An unhashed file has no known fingerprint yet → None, which is never in
        # `have`, so it is included and gets hashed here.
        return [p for p in self.paths if self.cache.known_fingerprint(p) not in have]

    def measure(self, path: Path) -> bool:
        """False only when the file itself cannot be read — one already on record
        is not a failure."""
        return self.cache.ensure_audio_fp(path) or self.cache.fingerprint(path) is not None


class SilenceAnalyzer(LibraryPass):
    """Probes the silent stretches of every file not yet in the silences table.

    Playback fills this table one track at a time (`SilenceWorker`); doing the
    whole library up front means no ffmpeg decode ever runs during a tournament,
    where it competes with the player for the same disk."""

    fail_hint = "ffmpeg could not read it"

    def __init__(self, cache: AudioCache, paths: list, ffmpeg: str, parent=None):
        super().__init__(cache, paths, parent)
        self.ffmpeg = ffmpeg

    workers = 8

    def todo(self) -> list:
        return [p for p in self.paths if self.cache.get_silences(p) is None]

    def compute(self, path: Path):
        return detect_silences(self.ffmpeg, path)

    def store(self, path: Path, spans) -> bool:
        self.cache.put_silences(path, spans)
        return True


class LoudnessAnalyzer(LibraryPass):
    """Measures EBU R128 loudness for entries not yet in the loudness table."""

    fail_hint = "ffmpeg could not read it"

    def __init__(self, cache: AudioCache, paths: list, ffmpeg: str, parent=None):
        super().__init__(cache, paths, parent)
        self.ffmpeg = ffmpeg

    workers = 8

    def todo(self) -> list:
        return [p for p in self.paths if self.cache.get_lufs(p) is None]

    def compute(self, path: Path):
        return measure_lufs(self.ffmpeg, path)

    def store(self, path: Path, lufs) -> bool:
        self.cache.put_lufs(path, lufs)
        return True


class VocalShareAnalyzer(LibraryPass):
    """Measures the Demucs vocal-stem share for entries not yet in the vocals
    table (🎙️ Analyze vocals — needs the optional demucs install).

    Expensive (~7 s of CPU per track), so results are saved often and cancel
    loses nothing."""
    save_every = 5
    fail_hint = "the vocal separation failed, see the log"
    # Only two: torch already spreads one separation over the cores, so the
    # measured gain is 1.5× (7.6 s → 5.1 s per track), not 8×, and every
    # separation in flight holds its own tensors. The shared htdemucs model is
    # read-only during inference (see planner.vocals._get_demucs_model).
    workers = 2

    def todo(self) -> list:
        return [p for p in self.paths if self.cache.get_vocal_share(p) is None]

    def compute(self, path: Path):
        from planner.vocals import measure_vocal_share
        try:
            return measure_vocal_share(path)
        except Exception as exc:
            log.warning("🎙️ Vocal separation failed\n"
                        "file: %s\n"
                        "error: %s", path, exc)
            return None

    def store(self, path: Path, share) -> bool:
        self.cache.put_vocal_share(path, share)
        return True


class PdHighlightAnalyzer(LibraryPass):
    """Detects highlights for every Paso Doble not yet in the pd_highlights
    table, so playback can arm the highlight stop instantly from the DB.

    force=True also redoes the tracks that already have highlights — for when
    the detector itself changed. Hand-set 🎯 marks are never touched: they are
    the operator's ear, and no detector run should overrule it."""
    save_every = 10

    def __init__(self, cache: AudioCache, paths: list, parent=None,
                 force: bool = False):
        super().__init__(cache, paths, parent)
        self.force = force

    @staticmethod
    def select_todo(cache, paths: list, force: bool) -> list:
        """The tracks that actually need decoding: the ones never analyzed,
        plus — with force — the auto-detected ones. Hand-set 🎯 marks are left
        alone either way."""
        return [p for p in paths
                if cache.get_pd_highlights(p) is None
                or (force and not cache.is_pd_manual(p))]

    def todo(self) -> list:
        return self.select_todo(self.cache, self.paths, self.force)

    def measure(self, path: Path) -> bool:
        try:
            times = detect_pd_highlights(path)
            self.cache.put_pd_highlights(path, times)
        except Exception as exc:
            log.warning("🐂 Paso Doble highlight detection failed\n"
                        "file: %s\n"
                        "error: %s", path, exc)
            return False
        return True


class EmbeddingIndexWorker(QThread):
    """Builds a deep-embedding index (OpenL3 or Chroma) over entries; cancelable.

    Each unique audio (by content fingerprint) is embedded once and cached in the
    shared SQLite `embeddings` table. The neural model is loaded lazily on first use.
    """
    progress  = Signal(int, int, str, float)   # (done, total, current filename, eta_seconds)
    done      = Signal(int, int, str)          # (computed, errors, first_error or "")
    cancelled = Signal(int)                     # (computed so far)
    error     = Signal(str)

    def __init__(self, store, model: str, entries: list, parent=None):
        super().__init__(parent)
        self._store, self._model, self._entries = store, model, entries
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _emit_progress(self, done: int, total: int, name: str):
        # Measure the rate from the FIRST callback onwards so the (one-time, slow)
        # neural-model load isn't baked into the per-file estimate.
        now = time.monotonic()
        if self._t0 is None:
            self._t0, self._done0 = now, done
            self.progress.emit(done, total, name, -1.0)
            return
        elapsed = now - self._t0
        steps = done - self._done0
        eta = (elapsed / steps) * (total - done) if steps > 0 and elapsed > 0 else -1.0
        self.progress.emit(done, total, name, eta)

    def run(self):
        try:
            from planner import embeddings as ae
            self._t0 = None
            self._done0 = 0
            computed, errors, first_error = ae.build_index(
                self._entries, self._model, self._store,
                progress_cb=self._emit_progress,
                should_cancel=lambda: self._cancel)
            if self._cancel:
                self.cancelled.emit(computed)
            else:
                self.done.emit(computed, errors, first_error or "")
        except Exception as exc:
            self.error.emit(str(exc))


class EmbeddingRankWorker(QThread):
    """Runs a deep-embedding ranking (similar-tracks) off the UI
    thread. `fn` is a no-arg callable returning (label, results). The first call also
    loads the model, which is why this must not block the UI."""
    done  = Signal(object, object)   # (source-or-prompt, results)
    error = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            label, results = self._fn()
            self.done.emit(label, results)
        except Exception as exc:
            self.error.emit(str(exc))


class SimilarFromFileWorker(QThread):
    """Analyzes a dropped file (librosa) then finds similar library tracks."""
    done  = Signal(object, object)   # (source MusicEntry, results list)
    error = Signal(str)

    def __init__(self, lib, cache, path: str, n: int = 12, min_display: float = 0.0, parent=None):
        super().__init__(parent)
        self._lib, self._cache, self._path, self._n = lib, cache, Path(path), n
        self._min_display = min_display

    def run(self):
        try:
            entry, results = self._lib.similar_to_file(
                self._path, self._cache, n=self._n, min_display=self._min_display)
            self.done.emit(entry, results)
        except Exception as exc:
            self.error.emit(str(exc))


class OpenRouterChatWorker(QThread):
    """Runs one chat completion off the UI thread (OpenRouter, or whichever
    OpenAI-compatible host `base_url` names)."""
    done  = Signal(str)
    error = Signal(str)

    def __init__(self, api_key, model, system, user, parent=None, base_url=""):
        super().__init__(parent)
        self._key, self._model, self._system, self._user = api_key, model, system, user
        self._base = base_url

    def run(self):
        try:
            self.done.emit(openrouter_chat(self._key, self._model, self._system,
                                           self._user, base_url=self._base))
        except Exception as exc:
            self.error.emit(str(exc))


class OpenRouterModelsWorker(QThread):
    """Fetches the host's model list off the UI thread (free ones only when the
    host is OpenRouter — nobody else prices that list)."""
    done  = Signal(object)
    error = Signal(str)

    def __init__(self, api_key, parent=None, base_url=""):
        super().__init__(parent)
        self._key = api_key
        self._base = base_url

    def run(self):
        try:
            self.done.emit(openrouter_free_models(self._key, base_url=self._base))
        except Exception as exc:
            self.error.emit(str(exc))



# ─────────────────────────────────────────────────────────────────────────────
# Reference-base cleaner (Referenzbasis → export unused)
# ─────────────────────────────────────────────────────────────────────────────
def _parse_m3u_blocks(m3u: Path) -> list:
    """Split an .m3u into one block per track: {'raw': [original lines incl. the
    #EXTINF header and the path line], 'path': absolute Path, 'title': str|None}.
    A leading '#EXTM3U' is dropped from the blocks (re-emitted once on write).
    Relative paths are resolved against the playlist's own folder. Raises
    PlaylistEncodingError for a file it can't decode: the run fails with it."""
    try:
        lines = read_playlist_text(m3u)[0].splitlines()
    except OSError:
        return []
    base = Path(m3u).parent
    blocks: list = []
    buf: list = []
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("#"):
            p = Path(s)
            p = p if p.is_absolute() else base / p
            title = None
            for b in buf:
                if b.strip().upper().startswith("#EXTINF") and "," in b:
                    title = b.split(",", 1)[1].strip()
            raw = [b for b in buf if b.strip().upper() != "#EXTM3U"] + [ln]
            blocks.append({"raw": raw, "path": p, "title": title})
            buf = []
        else:
            buf.append(ln)
    return blocks


class ReferenceCleanWorker(QThread):
    """Compare a reference playlist (Referenzbasis) against a set of tournament
    playlists and split the reference into tracks that are HARD duplicates of a
    tournament track — same audio content (content fingerprint) or same path,
    incl. renamed / re-encoded copies — and the rest ('unused').

    Paso Doble is excluded from the check (PD may legitimately repeat), so PD
    reference tracks are always kept. Runs off the UI thread because fingerprinting
    many files reads each one from disk.

    done(result) with keys: ref_path, kept_blocks, removed [(Path,title)],
    ref_total, pd_kept.
    """
    progress = Signal(int, int)        # done, total
    done     = Signal(dict)            # result
    failed   = Signal(str)

    def __init__(self, ref_path, tournament_paths, cache, parse_m3u, parent=None):
        super().__init__(parent)
        self._ref      = Path(ref_path)
        self._tours    = [Path(p) for p in tournament_paths]
        self._cache    = cache
        self._parse_m3u = parse_m3u    # Callable[[Path], List[Path]]
        self._cancel   = False

    def cancel(self):
        """Stop at the next track — the dialog that asked is closing."""
        self._cancel = True

    @staticmethod
    def _is_pd(path: Path) -> bool:
        # '_' is a word char, so the \bPD\b detector misses 'PD_58_Espana' — treat
        # underscores as separators (only widens word boundaries, never hides a token).
        return _detect_dance(path.name.replace("_", " ")) in ALLOW_REPEAT

    def _hard_key(self, path: Path) -> str:
        """Content fingerprint (byte-identical / re-encoded copies collapse), else
        the lowercased path."""
        try:
            fp = self._cache.fingerprint(path)
        except Exception:
            fp = None
        return f"fp:{fp}" if fp else f"p:{path_key(path)}"

    def _tracks_of(self, p: Path) -> list:
        if p.suffix.lower() in (".m3u", ".m3u8"):
            return list(self._parse_m3u(p))
        return [p]

    def run(self):
        try:
            ref_blocks = _parse_m3u_blocks(self._ref)
            tour_tracks: list = []
            for t in self._tours:
                tour_tracks.extend(self._tracks_of(t))
            total = len(tour_tracks) + len(ref_blocks)
            done  = 0

            # Hard keys of every tournament track (PD skipped — never checked).
            tour_keys = set()
            for t in tour_tracks:
                if self._cancel:
                    return
                if not self._is_pd(t):
                    tour_keys.add(self._hard_key(t))
                done += 1
                if done % 10 == 0 or done == total:
                    self.progress.emit(done, total)

            kept_blocks: list = []
            removed: list = []
            pd_kept = 0
            seen_ref_keys = set()   # hard keys already kept from the reference itself
            for blk in ref_blocks:
                if self._cancel:
                    return
                p = blk["path"]
                if self._is_pd(p):
                    pd_kept += 1
                    kept_blocks.append(blk)
                else:
                    key = self._hard_key(p)
                    # Drop a reference track that is byte-identical to a tournament
                    # track, or to an earlier kept reference track (within-reference dup).
                    if key in tour_keys or key in seen_ref_keys:
                        removed.append((p, blk.get("title") or p.stem))
                    else:
                        seen_ref_keys.add(key)
                        kept_blocks.append(blk)
                done += 1
                if done % 10 == 0 or done == total:
                    self.progress.emit(done, total)

            self.done.emit({
                "ref_path":    self._ref,
                "kept_blocks": kept_blocks,
                "removed":     removed,
                "ref_total":   len(ref_blocks),
                "pd_kept":     pd_kept,
            })
        except Exception as exc:
            self.failed.emit(str(exc))
