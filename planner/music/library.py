"""The music library: scanning, caching, the entries and their queries.

MusicLibrary owns the scan + cache pipeline, the entries and the similarity
and past-competition queries. What the past playlists say about a track (the
playlist index and the popularity learned from it) comes from
planner.music.playlist_index, as PlaylistIndexMixin.
"""
import copy
import logging
import os

from collections import deque
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
from typing import Any
from collections.abc import Callable
from planner.config import (  # auto-resolved
    MUSIC_DIR,
    folders_below,
    playlist_dir,
)
from planner.music.db import (  # auto-resolved
    AudioCache,
    ChunkedWrites,
    _META_COLS,
    _fingerprints,
)
from planner.music.analysis import _tempo_prior
from planner.music.playlist_index import (
    PlaylistIndexMixin,
    _dq,
    _warn_unreadable,
)
from planner.music.scan_caches import (
    GlobalScanCache,
    ScanCache,
    _entry_meta,
)
from planner.music.similarity import (  # auto-resolved
    _timbre_similarity,
)
from planner.music import custom_field, tag_edits
from planner.system_info import UsageMeter, lower_thread_priority
from planner.models import (  # auto-resolved
    DANCE_NAMES,
    GENRE_TO_DANCE,
    MusicEntry,
    OTHER_GENRE_LABELS,
    ScanCancelled,
    _EXCLUDED_FOLDERS,
    fold_text,
    folder_category_of_parts,
    is_hidden_path,
    note_class_tag_use,
)
from planner.music.parsing import (  # auto-resolved
    _title_for,
    _detect_bpm_tagged,
    _get_tag_bpm,
    _detect_dance,
    _detect_year,
    dance_from_folders,
    _get_comment_tag,
    is_marker_noise,
    parse_comment_markers,
    _get_raw_genre_tag,
    _get_um_dance,
    _get_title_artist_tags,
    popm_stars,
    _is_christmas,
    _parse_class_tag,
    title_marks_instrumental,
    _read_duration,
    _read_tags_once,
    _song_title_key,
    _stem_key,
    _title_key,
)
from planner.event.competition import (  # auto-resolved
    CompetitionSpec,
    _is_superseded_playlist,
    _round_stages_in_name,
    competition_matches_file,
    is_competition_file,
    is_side_list,
    is_working_collection_path,
)
from planner.generate.warmup import (  # auto-resolved
    others_dance_from_path,
)
from planner.playlist.playlist_text import PlaylistEncodingError, playlist_files, read_playlist_text

log = logging.getLogger("dancesport.library")

# The category word some taggers put before the dance in the genre tag.
_GENRE_CATEGORY_RE = re.compile(r'^(?:ballroom|standard|latin|latein)\s+', re.IGNORECASE)


# Sentinel for regenerate()/anchor_similarity(): distinguishes "caller didn't pass an
# anchor → use the round's stored one" from "caller explicitly passed None → no timbre".
_ANCHOR_DEFAULT: Any = object()


def _library_mp3s(root: Path,
                  mtimes: dict[str, int] | None = None) -> list[tuple[Path, float]]:
    """Every .mp3 under `root` with the time it was created (breadth-first).

    Same trick as `_playlist_tree`: a Windows directory entry already carries the
    timestamps, so `DirEntry.stat()` needs no extra syscall — the whole library
    (3.8k files) walks in ~0.02 s, faster than the plain `rglob` this replaced,
    and the creation time comes along for free. That time is what the 🆕 "Added"
    column shows: a copied file gets a fresh creation time at its destination,
    while its mtime still carries whenever the tags were last written.
    `mtimes`, when given, receives that mtime per path, for the scan's cache keys.
    """
    out: list[tuple[Path, float]] = []
    queue = deque([str(root)])
    while queue:   # level by level; pathlib's own rglob order is no more meaningful
        try:
            with os.scandir(queue.popleft()) as it:
                entries = list(it)
        except OSError:
            continue
        for de in entries:
            try:
                if de.is_dir(follow_symlinks=False):
                    queue.append(de.path)
                elif de.name.lower().endswith(".mp3"):
                    st = de.stat()
                    # st_birthtime is the real creation time (Windows/macOS);
                    # elsewhere st_ctime is the closest thing on offer.
                    out.append((Path(de.path),
                                getattr(st, "st_birthtime", None) or st.st_ctime))
                    if mtimes is not None:
                        mtimes[de.path] = int(st.st_mtime)
            except OSError:
                continue
    return out


def _listed_mtimes(folders) -> dict[str, int]:
    """str(path) → mtime of every .mp3 directly in `folders`, one listing each.

    The key to a recorded fingerprint holds the file's mtime; for the whole
    repository (54k titles) one stat per file was 4.6 s of a 14.5 s cache load,
    the listing gives the same mtime for free (see `_library_mp3s`). A folder
    that cannot be listed is left out, so its files fall back to the stat.
    """
    out: dict[str, int] = {}
    for folder in folders:
        try:
            with os.scandir(folder) as it:
                for de in it:
                    if de.name.lower().endswith(".mp3"):
                        try:
                            out[de.path] = int(de.stat().st_mtime)
                        except OSError:
                            continue
        except OSError:
            continue
    return out


# ⏱ A cached duration of 0 means "never probed" (rows from before the column),
# so a header that gives no length is cached as this instead, or it would be
# probed again on every start. MusicEntry turns it back into 0.
_NO_LENGTH = -1

# Folders the favorites scan leaves out, unless a library category keeps them.
_SKIP_DIR = re.compile(r'christmas|weihnacht|endrunden|special', re.IGNORECASE)


def _left_out(rel_parts: list[str], skip_special: bool) -> str | None:
    """Why a file in these folders stays out of the library: '' for a hard-excluded
    folder (sox, unbearbeitet: in every scan mode), the special folder's name, or
    None when it loads."""
    if {p.lower() for p in rel_parts} & _EXCLUDED_FOLDERS:
        return ''
    if skip_special:
        skip_hit = next((p for p in rel_parts if _SKIP_DIR.search(p)), None)
        # A soft library category (anthems / background / seasonal /
        # wrong_tempo / duplicates) overrides the special/christmas
        # skip: the file loads (browsable) but is soft-excluded from
        # generation. endrunden / plain special/ stay skipped.
        if skip_hit and not folder_category_of_parts(rel_parts):
            return skip_hit
    return None


# 📖 A file the scan has not seen is read twice (fingerprints, then the tag), and
# one file after the other the disk waits for Python and Python for the disk. A
# pool reads this many files at once, at most _READ_AHEAD ahead of the scan.
_READ_WORKERS = 8
_READ_AHEAD = 32

# ⏱ A long first scan logged nothing between its first and its last line, so a
# tester's session.log could not tell how far it got or which file it sat on.
_PROGRESS_LOG_SECS = 15.0
_SLOW_FILE_SECS = 2.0

# ⏸ How often a paused scan looks whether it may go on (or must end).
_PAUSE_POLL_SECS = 0.2


class _ScanClock:
    """⏱ The walk's progress line every _PROGRESS_LOG_SECS, and every file that
    took _SLOW_FILE_SECS or more (a stalling disk, a cloud placeholder)."""

    def __init__(self, total: int):
        self.total = total
        self.started = time.perf_counter()
        self.last_log = self.started
        self.tick = self.started
        self.current: Path | None = None
        self.usage = UsageMeter()

    def step(self, done: int, path: Path | None):
        """Call before each file (`path`), and once with None after the last."""
        now = time.perf_counter()
        if self.current is not None and now - self.tick >= _SLOW_FILE_SECS:
            log.warning("  🐢 Slow file in the library scan\n"
                        "file: %s\n"
                        "time: %.1f s", self.current, now - self.tick)
        if path is not None and now - self.last_log >= _PROGRESS_LOG_SECS:
            self.last_log = now
            elapsed = now - self.started
            log.info("  ⏳ Scan progress\n"
                     "files: %d / %d\n"
                     "elapsed: %.0f s\n"
                     "rate: %.0f files/s\n"
                     "current: %s\n"
                     "%s", done, self.total, elapsed,
                     done / elapsed if elapsed else 0, path, self.usage.lines())
        self.tick, self.current = now, path

    def paused(self, seconds: float):
        """A pause is neither the file's time nor the scan's."""
        self.started += seconds
        self.tick += seconds


def _hold(should_pause, should_quit, writes, clock) -> bool:
    """⏸ Wait here while the scan is paused, until it may go on or must end
    (`should_quit`). What it wrote so far is committed first: a paused scan
    must not keep the other writers off the database. True if it paused."""
    if should_pause is None or not should_pause():
        return False
    writes.release()
    log.info("  ⏸ Library scan paused")
    began = time.perf_counter()
    while should_pause() and not should_quit():
        time.sleep(_PAUSE_POLL_SECS)
    waited = time.perf_counter() - began
    clock.paused(waited)
    log.info("  ▶ Library scan goes on\n"
             "paused: %.0f s", waited)
    return True


def _read_new_file(path, cache, scan_cache):
    """The file reads `_make_entry` needs for `path`, made on a pool thread:
    (fingerprints, or None when on record; (tags, duration), or None when a scan
    row exists). Touches no database: connections are per thread, and the scan
    thread's holds the open write transaction."""
    fps = None
    fp = cache.known_fingerprint(path)
    if fp is None:
        fps = _fingerprints(path)
        fp = fps[0]
    tags = None if scan_cache.has_row(fp, path) else _read_tags_once(path)
    return fps, tags


class _ReadAhead:
    """Runs `read(path, *args)` for `paths` on a thread pool, in order, a window ahead.

    `take(path)` hands back the result once the scan reaches that file. Any other
    file gets (None, None) and is read on the scan thread, as is a file whose read
    failed: the scan's own read then reports it the way it always did."""

    def __init__(self, paths, read: Callable[..., Any], *args):
        self._todo = iter(paths)
        self._read = read
        self._args = args
        self._window = deque()
        self._pool = (ThreadPoolExecutor(_READ_WORKERS, initializer=lower_thread_priority)
                      if paths else None)
        for _ in range(_READ_AHEAD):
            self._submit_next()

    def _submit_next(self) -> None:
        path = next(self._todo, None)
        if path is not None and self._pool is not None:
            self._window.append(
                (path, self._pool.submit(self._read, path, *self._args)))

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        if self._pool is not None:
            self._pool.shutdown(cancel_futures=True)

    def take(self, path):
        if not self._window or self._window[0][0] != path:
            return None, None
        _, future = self._window.popleft()
        self._submit_next()
        try:
            return future.result()
        except OSError:
            return None, None


# ── Music Library ──────────────────────────────────────────────────────────────
def _heal_cached(path, cached, scan_cache):
    """🩹 A cached row with every lazily healed field brought up to date."""
    # 🩹 Re-derive bpm from the filename on every cache hit: it's a pure
    # function of the name (+ title tag), so an old cache built before
    # the detection was fixed (e.g. slow 'Nicht TSO Turniertempo'
    # versions at 19 bars/min, or a name truncated past its '(RB 25)'
    # tact that survives in the tag) self-heals without a re-scan.
    bpm = _detect_bpm_tagged(path.stem, cached.get('tag_title'),
                             cached.get('tag_bpm'), cached.get('dance'))
    if bpm != cached.get('bpm'):
        cached = {**cached, 'bpm': bpm}
        scan_cache.put(path, cached)
    # 🩹 Title heals lazily too: it's a pure function of the name (+ title
    # tag), so titles cached before the disc-track / copy-index cleanup
    # self-heal without a full re-scan.
    title = _title_for(path.stem, cached.get('tag_title'))
    if title != cached.get('title'):
        cached = {**cached, 'title': title}
        scan_cache.put(path, cached)
    # 🩹 Duration heals lazily too: rows cached before the duration column
    # existed carry 0 — probe the header once and persist, no full re-scan.
    if not cached.get('duration'):
        secs = _read_duration(path)
        cached = {**cached, 'duration': secs or _NO_LENGTH}
        scan_cache.put(path, cached)
    # 🩹 Comment markers heal lazily: rows cached before the column
    # existed carry None, which is NOT the same as [] ("read it, there
    # were none"). Re-reading the COMM frame costs one ID3 open, so a
    # library scanned before this pays it once and never again.
    if cached.get('comment_tags') is None:
        comment = _get_comment_tag(path)
        cached = {**cached,
                  'comment_tags': parse_comment_markers(comment)
                  if comment else []}
        scan_cache.put(path, cached)
    # 🩹 And junk markers heal lazily too: caches written before the
    # noise filter knew about release dates and the iTunes gapless blob
    # still carry them, and filtering a cached list costs no ID3 read.
    tags = cached.get('comment_tags')
    if tags and any(is_marker_noise(t) for t in tags):
        cached = {**cached,
                  'comment_tags': [t for t in tags
                                   if not is_marker_noise(t)]}
        scan_cache.put(path, cached)
    # 🩹 Folder-structure dance heals lazily: rows cached before the folder
    # fallback existed carry None — pure function of the path, so classify
    # once and persist without a re-scan.
    if cached.get('dance') is None and not cached.get('other_genre'):
        code = dance_from_folders(path)
        if code:
            cached = {**cached, 'dance': code}
            scan_cache.put(path, cached)
    # 🩹 Social-dance label heals lazily: rows cached before the path
    # classifier existed carry None — classify once and persist.
    if cached.get('dance') is None and not cached.get('other_genre'):
        code = others_dance_from_path(path)
        if code:
            cached = {**cached, 'other_genre': DANCE_NAMES[code]}
            scan_cache.put(path, cached)
    # 🩹 Album heals lazily: rows cached before the tag_album column existed
    # carry None — read the TALB tag once and persist ('' = checked, no album)
    # so later cache hits skip the ID3 read.
    if cached.get('tag_album') is None:
        _, _, album = _get_title_artist_tags(path)
        cached = {**cached, 'tag_album': album or ''}
        scan_cache.put(path, cached)
    # 🩹 The Custom field heals lazily: None is "not read under the
    # current mapping" (a new mapping clears the column), '' is read.
    # Unmapped, both show a blank cell, so the row is left as it is.
    if cached.get('custom') is None and custom_field.source() is not None:
        cached = {**cached, 'custom': custom_field.read_file(path)}
        scan_cache.put(path, cached)
    return cached


class MusicLibrary(PlaylistIndexMixin):
    def __init__(self):
        self._entries_version = 0
        self.entries = []
        # normalised path → set of playlist ids it appears in (for co-occurrence)
        self._track_playlists: dict[str, set[str]] = defaultdict(set)
        # playlist id → start class parsed from its file/folder name (None = unknown)
        self._playlist_cls: dict[str, str | None] = {}
        # playlist id → the year in its path, memoised (None = it carries no date)
        self._playlist_year: dict[str, int | None] = {}
        # …the same, but only the tracks that were danced in that playlist's FINAL
        # round. A title can sit in 40 lists and never once be in one of these.
        self._track_finals: dict[str, set[str]] = defaultdict(set)
        # …and in its SEMIFINAL. Those are the two rounds that are chosen rather
        # than filled, so they are the two worth counting apart.
        self._track_semis: dict[str, set[str]] = defaultdict(set)
        # stem key → that file's CALCULATED dance (genre tag wins over filename), so a
        # playlist line can be dance-qualified the same way its library entry is.
        self._stem_dance: dict[str, str | None] = {}
        # playlist line → its co-occurrence keys, see `_line_keys`.
        self._line_key_memo: dict[str, set[str]] = {}
        # path → entry, built lazily by `_path_index` and rebuilt whenever
        # `entries` is replaced or changes length (a scan, a cache load, an append).
        self._by_path: dict[str, MusicEntry] = {}
        self._by_path_ci: dict[str, MusicEntry] = {}
        self._path_idx_key: tuple[int, int] | None = None
        # Reused across make_external_entry() calls so restoring a playlist full
        # of external tracks doesn't reload the whole scan_meta table per track.
        self._scan_cache: ScanCache | None = None

    def scan(
        self,
        cache: AudioCache,
        music_dir: Path | None = None,
        skip_special: bool = True,
        learn: bool = True,
        analyze: bool = True,
        global_cache: GlobalScanCache | None = None,
        progress_cb: Callable[[int, int, Path, bool], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        interactive: bool = True,
        should_pause: Callable[[], bool] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        """Scan a music directory into `self.entries` (read-only — never writes MP3s).

        music_dir    – directory to scan (default: the competition library MUSIC_DIR)
        skip_special – drop christmas / endrunden / special sub-folders (competition only)
        learn        – learn playlist popularity + co-occurrence from PLAYLIST_DIR
        analyze      – run librosa on missing files; if False, only apply already-cached
                       features (fast, no analysis) — used for the large global repo.
        global_cache – optional GlobalScanCache for the big repo: reuses entries for
                       unchanged files (mtime match), only re-reads changed ones.
        progress_cb  – optional callback(done, total, current_path, reused) invoked while
                       walking files, so a GUI can show "which file / how many left".
        should_cancel – optional predicate polled during the walk; when it returns True the
                       scan stops early and raises ScanCancelled (partial cache is saved).
        interactive  – False (GUI): never block on stdin prompts; missing-feature
                       analysis is deferred to the caller (see analyze_missing).
        should_pause – optional predicate polled before every file; while it returns
                       True the walk waits there, its writes committed.
        should_stop  – optional predicate polled before every file; when it returns
                       True the walk ends there and the files read so far are the
                       library, finished as after a whole walk.
        """
        started = time.perf_counter()
        usage = UsageMeter()   # its CPU share is the whole scan's average
        try:
            self._scan(cache, music_dir, skip_special, learn, analyze, global_cache,
                       progress_cb, should_cancel, interactive, should_pause, should_stop)
            log.info("  ⏱ Library scan finished\n"
                     "files: %d\n"
                     "time: %.1f s\n"
                     "%s", len(self.entries), time.perf_counter() - started,
                     usage.lines())
        finally:
            # The listing's times are only as fresh as the scan: a file re-tagged
            # later in the session must be stat'ed again.
            cache.listed_mtimes = {}
            cache.read_ahead = {}

    def _scan(self, cache, music_dir, skip_special, learn, analyze, global_cache,
              progress_cb, should_cancel, interactive, should_pause=None,
              should_stop=None) -> None:
        scan_cache = self._get_scan_cache(cache)
        music_dir = music_dir or MUSIC_DIR
        added_ts: dict[str, float] = {}   # file path → creation time (see the walk below)
        log.info("  📂 Scanning music library …  %s", music_dir)
        if not music_dir.exists():
            log.warning("  ⚠️ Music directory not found: %s", music_dir)
        else:
            skipped_dirs: set = set()
            seen: set = set()
            reused = 0
            # Materialise the file list first so total (and "how many left") is known.
            listing = time.perf_counter()
            if progress_cb is not None:
                progress_cb(0, 0, music_dir, False)   # signal "listing files…" phase
            # The walk already has every file's mtime: lent to the cache, it
            # spares the fingerprint lookups a stat per file (two, in fact).
            mtimes: dict[str, int] = {}
            found = _library_mp3s(music_dir, mtimes)
            cache.listed_mtimes = mtimes
            added_ts = {str(p): ts for p, ts in found}
            all_mp3 = [p for p, _ in found]
            total = len(all_mp3)
            root = str(music_dir)
            hidden = {p for p in all_mp3 if is_hidden_path(p)}
            if hidden:
                log.info("  🙈 Excluded folders leave out %d files", len(hidden))
            # Every path comes from the walk of music_dir, so it is below it.
            left_out = ['' if p in hidden
                        else _left_out(folders_below(str(p), root) or [], skip_special)
                        for p in all_mp3]
            # Files not seen before are read ahead on a pool. Not in the whole-repo
            # scan: telling its known files apart (global_cache) costs a stat each.
            unread = [p for p, why in zip(all_mp3, left_out, strict=True)
                      if why is None and global_cache is None
                      and ((fp := cache.known_fingerprint(p)) is None
                           or not scan_cache.has_row(fp, p))]
            log.info("  📂 Music library listed\n"
                     "files: %d\n"
                     "new to read: %d\n"
                     "time: %.1f s", total, len(unread), time.perf_counter() - listing)
            clock = _ScanClock(total)
            stopped = False

            def should_quit():
                return any(f is not None and f() for f in (should_cancel, should_stop))

            with (ChunkedWrites() as writes,
                  _ReadAhead(unread, _read_new_file, cache, scan_cache) as ahead):
                for idx, mp3 in enumerate(all_mp3, 1):
                    held = _hold(should_pause, should_quit, writes, clock)
                    if should_stop is not None and should_stop():
                        stopped = True
                        log.info("  ⏹ Library scan stopped\n"
                                 "files: %d / %d", idx - 1, total)
                        break
                    clock.step(idx - 1, mp3)
                    writes.step()
                    if (should_cancel is not None and (held or idx % 25 == 0)
                            and should_cancel()):
                        if global_cache is not None:
                            global_cache.save()   # keep what we scanned so far
                        scan_cache.save()
                        raise ScanCancelled(f"Scan cancelled after {idx}/{total} files")
                    was_reused = False
                    why = left_out[idx - 1]
                    if why is not None:
                        if why:
                            skipped_dirs.add(why)
                        if mp3 in hidden and global_cache is not None:
                            seen.add(str(mp3))   # hidden, not gone: its row stays
                        if progress_cb is not None and (idx % 25 == 0 or idx == total):
                            progress_cb(idx, total, mp3, True)
                        continue
                    if global_cache is not None:
                        seen.add(str(mp3))
                        cached_entry = global_cache.get(mp3)
                        if cached_entry is not None:
                            # 🩹 Self-heal bpm (pure fn of the name + title tag) on
                            # reuse so entries cached before the detection fix get
                            # corrected.
                            bpm = _detect_bpm_tagged(mp3.stem, cached_entry.get('tag_title'),
                                                     cached_entry.get('tag_bpm'),
                                                     cached_entry.get('dance'))
                            if bpm != cached_entry.get('bpm'):
                                cached_entry = {**cached_entry, 'bpm': bpm}
                                global_cache.put(mp3, cached_entry)
                            # ⏱ Rows written before the duration column carry 0 —
                            # probe the length once, like `_make_entry` does.
                            if not cached_entry.get('duration'):
                                secs = _read_duration(mp3)
                                cached_entry = {**cached_entry,
                                                'duration': secs or _NO_LENGTH}
                                global_cache.put(mp3, cached_entry)
                            self.entries.append(MusicEntry(path=mp3, **cached_entry))
                            reused += 1
                            was_reused = True
                        else:
                            entry = self._make_entry(mp3, scan_cache)
                            global_cache.put(mp3, {**_entry_meta(entry),
                                                   'duration': entry.duration or _NO_LENGTH})
                            self.entries.append(entry)
                    else:
                        fps, tags = ahead.take(mp3)
                        if fps is not None:
                            cache.read_ahead[str(mp3)] = fps
                        self.entries.append(self._make_entry(mp3, scan_cache, tags))
                    if progress_cb is not None and (idx % 25 == 0 or idx == total):
                        progress_cb(idx, total, mp3, was_reused)
                clock.step(total, None)
            if skipped_dirs:
                log.info("  Skipped dirs: %s", ', '.join(sorted(skipped_dirs)))
            log.info("  🎶 %s MP3 files found", len(self.entries))
            scan_cache.save()
            if global_cache is not None:
                if not stopped:     # a file not reached is not a file gone
                    global_cache.prune(seen)
                global_cache.save()
                log.info("  ♻️  %s reused from global cache, %s (re)scanned",
                         reused, len(self.entries) - reused)
            self.apply_tag_edits(cache)

        self._finish_scan(cache, learn, analyze, interactive, added_ts)

    def _finish_scan(self, cache, learn, analyze, interactive, added_ts):
        """After the walk: learn the playlists, popularity and source, features."""
        if learn:
            log.info("  📜 Analyzing existing playlists … %s", playlist_dir())
            n = self._learn_playlists()
            log.info("  📜 %s playlists analyzed (M3U files + tournament folders)", n)

        # Apply popularity + source info (popularity only meaningful when we learned playlists)
        for e in self.entries:
            if learn:
                self._apply_popularity(e)
            e.cluster = e.path.parent.name
            e.added = added_ts.get(str(e.path))

        # Audio feature extraction (with cache)
        if analyze:
            log.info("  🎵 Loading audio features …")
            cache.analyze_missing(self.entries, interactive=interactive)
        else:
            # Global / lightweight mode: attach already-cached features WITHOUT hashing
            # every file (keeps warm loads instant). Fingerprints get populated when the
            # global audio index is built (AudioAnalyzer), enabling deduped resolution.
            for e in self.entries:
                e.features = cache.get(e.path, hash_if_missing=False)

    def load_from_global_cache(
        self, cache: AudioCache, global_cache: GlobalScanCache
    ) -> int:
        """Rebuild the whole-repo entry list straight from the persisted global cache.

        NO filesystem walk and NO librosa indexing — just reconstruct the cached
        entries and attach already-cached features. Used so a dropped file matches
        the repo instantly without the "indexing whole repository" window when the
        cache is already warm. New/changed files on disk are NOT picked up here (do a
        full ⚙ Settings rebuild for that). Returns the number of entries loaded.
        """
        self.entries = []
        rows = global_cache.all_entries()
        mtimes = _listed_mtimes({os.path.dirname(path_str) for path_str, _ in rows})
        cache.load_all_features()
        for path_str, meta in rows:
            if is_hidden_path(path_str):
                continue
            p = Path(path_str)
            entry = MusicEntry(path=p, **meta)
            # 🩹 Self-heal bpm from the name + title tag so global-cache
            # entries built before the detection fix get tempo-filtered too.
            bpm = _detect_bpm_tagged(p.stem, entry.tag_title, entry.tag_bpm, entry.dance)
            if bpm != entry.bpm:
                entry.bpm = bpm
                global_cache.put(p, {**meta, 'bpm': bpm})
            entry.cluster = p.parent.name
            entry.features = cache.get(p, hash_if_missing=False,
                                       mtime=mtimes.get(str(p)))
            self.entries.append(entry)
        self.apply_tag_edits(cache)
        return len(self.entries)

    def apply_tag_edits(self, cache: AudioCache) -> None:
        """Lay the in-app tag edits (planner.music.tag_edits) over every entry.

        Runs AFTER the scan/global caches were written, so those keep the file's
        own values and an edit taken back restores them. Resolved through the
        recorded fingerprints only — no file is read; a track never fingerprinted
        cannot have been edited."""
        edits = tag_edits.load_all()
        for e in self.entries:
            fp = cache.recorded_fingerprint(e.path)
            tag_edits.apply(e, edits.get(fp) if fp else None)

    def edit_tags(self, entries: list[MusicEntry], cache: AudioCache,
                  changes: dict) -> list[Path]:
        """Store an in-app tag edit for each of `entries` and show it.

        A value equal to what the file itself says drops that override instead
        of storing it, so going back to the file's value leaves no trace. The
        edit is keyed by content, so every copy of the same file follows: the
        entries handed in, and the library's own ones (a deck row may hold an
        outside copy of a library track). Returns the paths whose entries
        changed, for the caller to repaint. ValueError when a file cannot be
        hashed (it is gone) — an edit with no key would be lost."""
        return self._edit_tags(entries, cache, lambda e: {
            field: (None if tag_edits.same_value(field, value,
                                                 tag_edits.file_value(e, field))
                    else value)
            for field, value in changes.items()})

    def reset_tag_edits(self, entries: list[MusicEntry], cache: AudioCache) -> list[Path]:
        """Drop every in-app edit of `entries`: back to what the files say."""
        return self._edit_tags(entries, cache,
                               lambda e: dict.fromkeys(tag_edits.EDIT_FIELDS))

    def _edit_tags(self, entries, cache, changes_for) -> list[Path]:
        fps = []
        for e in entries:
            fp = cache.fingerprint(Path(e.path))
            if fp is None:
                raise ValueError(f"cannot read {Path(e.path).name}")
            fps.append(fp)
        touched: dict[str, Path] = {}
        for e, fp in zip(entries, fps, strict=True):
            edit = tag_edits.save(fp, changes_for(e))
            same = [x for x in self.entries
                    if x is not e and cache.recorded_fingerprint(x.path) == fp]
            for target in (e, *same):
                tag_edits.apply(target, edit)
                touched[str(target.path)] = Path(target.path)
        note_class_tag_use(self.entries)   # only the main library is edited
        return list(touched.values())

    def _make_entry(self, path: Path, scan_cache: ScanCache,
                    tags_read: tuple | None = None) -> MusicEntry:
        # tags_read: what `_read_tags_once` gave the scan's read-ahead pool.
        # Fast path: metadata already cached for this file size
        cached = scan_cache.get(path)
        if cached:
            cached = _heal_cached(path, cached, scan_cache)
            return MusicEntry(path=path, **cached)

        # Slow path: read ID3 tags (happens once per file, then cached)
        name  = path.stem
        file_dance = _detect_dance(name)
        other = None

        # Read TCON genre tag once – used for dance detection, other_genre, AND is_xmas.
        # The ID3 genre tag is authoritative: when it names a dance it WINS over the
        # filename guess, because the filename can false-positive — e.g. the title word
        # 'Ta' in 'Je Ne Serai Jamais Ta Parisienne' looks like the Tango code 'TA',
        # though its genre tag correctly says 'LW' (Slow Waltz).
        tags, duration = tags_read or _read_tags_once(path)
        raw_genre = _get_raw_genre_tag(path, tags) or ''
        genre_dance = None
        genre_other = None
        if raw_genre:
            parts = [raw_genre] + raw_genre.split(';')
            # 'Ballroom SW', 'Latin Cha Cha': the dance behind a category word
            parts += [_GENRE_CATEGORY_RE.sub('', p.strip()) for p in parts]
            for part in parts:
                result = GENRE_TO_DANCE.get(fold_text(part.strip()))
                if result:
                    genre_dance = result
                    break
            if genre_dance is None:
                for part in parts:
                    label = OTHER_GENRE_LABELS.get(fold_text(part.strip()))
                    if label:
                        genre_other = label
                        break
        if genre_other:
            # A SOCIAL genre tag is just as authoritative as a dance one: the
            # track is no competition dance at all, so neither the filename nor
            # the folder gets a vote. 'Cha Chicki Salsa 2' reads as a Cha-Cha
            # by its letters, but its tag says SL, and a Salsa it is.
            dance, other = None, genre_other
        else:
            # UltraMixer's own dance style comes after the genre, before the name.
            dance = genre_dance or _get_um_dance(tags) or file_dance
            if dance is None:
                # Fallback layer: libraries organised by FOLDER (my music/standard/LW)
                # instead of tags or coded filenames.
                dance = dance_from_folders(path)
        if dance is None and other is None:
            # Social dance without a genre tag → classify by path (folder /
            # filename keywords), so e.g. Forró shows up in the library.
            code = others_dance_from_path(path)
            if code:
                other = DANCE_NAMES[code]

        comment = _get_comment_tag(path, tags)
        classes_ok, is_instr = _parse_class_tag(comment) if comment else (None, False)
        comment_tags = parse_comment_markers(comment) if comment else []
        is_xmas = _is_christmas(name, raw_genre)
        tag_title, tag_artist, tag_album = _get_title_artist_tags(path, tags)
        tag_bpm = _get_tag_bpm(path, tags)
        if not is_instr:
            # No COMM 'instr' tag — a filename/title marker like '(Instr.)' or
            # '(inst)' flags the track as instrumental too.
            is_instr = title_marks_instrumental(f"{name} {tag_title or ''}")

        data = {
            'title':          _title_for(name, tag_title),
            'dance':          dance,
            'bpm':            _detect_bpm_tagged(name, tag_title, tag_bpm, dance),
            'year':           _detect_year(name, path, tags),
            'other_genre':    other,
            'classes_ok':     classes_ok,
            'comment_tags':   comment_tags,
            'rating':         popm_stars(tags),
            'custom':         custom_field.value_of(tags),
            'is_instrumental': is_instr,
            'is_xmas':        is_xmas,
            'tag_title':      tag_title,
            'tag_artist':     tag_artist,
            'tag_album':      tag_album,
            'tag_bpm':        tag_bpm,
            'duration':       duration,
        }
        scan_cache.put(path, {**data, 'duration': duration or _NO_LENGTH})
        return MusicEntry(path=path, **data)

    def _get_scan_cache(self, cache: AudioCache) -> ScanCache:
        """The ScanCache for `cache`, built once and reused — its `_load()` reads
        the whole scan_meta table, so rebuilding it per call (e.g. once per
        external entry while restoring a playlist) is a full table reload each
        time for no reason."""
        if self._scan_cache is None or self._scan_cache._cache is not cache:
            self._scan_cache = ScanCache(cache)
        return self._scan_cache

    def rescan_tags(self, entry: MusicEntry, cache: AudioCache) -> dict[str, tuple]:
        """Re-read ONE file's ID3 tags and push the result onto `entry` in place.

        For the track whose tags were edited (mp3tag & co.) while the app was
        running: the scan cache would only notice on the next startup. Deck rows
        and the library hold the very SAME MusicEntry objects, so the fields are
        written onto the entry — and onto the library's own entry for that path
        when that is a different object — rather than returned as a replacement.
        Returns {field: (old, new)} for everything the re-read changed."""
        path = Path(entry.path)
        scan_cache = self._get_scan_cache(cache)
        scan_cache.forget(path)
        fresh = self._make_entry(path, scan_cache)
        scan_cache.save()
        fp = cache.recorded_fingerprint(path) if cache is not None else None
        tag_edits.apply(fresh, tag_edits.load(fp) if fp else None)

        targets = [entry]
        twin = self.entry_for(path)
        if twin is not None and twin is not entry:
            targets.append(twin)
        changed: dict[str, tuple] = {}
        for col in _META_COLS:
            new = getattr(fresh, col)
            old = getattr(entry, col)
            if old != new:
                changed[col] = (old, new)
            for target in targets:
                setattr(target, col, new)
        for target in targets:
            target.tag_edits = fresh.tag_edits
        return changed

    def read_custom(self, entries: list[MusicEntry], cache: AudioCache,
                    values: dict[str, str] | None = None) -> list[Path]:
        """Read the Custom field's mapped frame again for `entries` — after the
        mapping changed — and keep it in the scan cache; every other cached
        row forgets the old mapping's value. A value typed in the app still
        wins: the file's goes underneath it. Returns the paths whose shown
        value changed.

        That is one ID3 read per file, seconds for a whole library: the window
        reads them off the GUI thread (custom_field.read_file) and hands them
        in as `values`, {path: value}, so the scan cache is only written here,
        on the thread its connection belongs to."""
        scan_cache = self._get_scan_cache(cache)
        scan_cache.forget_custom()
        by_path: dict[str, list[MusicEntry]] = {}
        for e in entries:
            by_path.setdefault(str(e.path), []).append(e)
        changed = []
        for path_str, same in by_path.items():
            path = Path(path_str)
            value = (values[path_str] if values is not None and path_str in values
                     else custom_field.read_file(path))
            cached = scan_cache.get(path)
            if cached is not None and cached.get('custom') != value:
                scan_cache.put(path, {**cached, 'custom': value})
            shown = False
            for e in same:
                if e.tag_edits and 'custom' in e.tag_edits:
                    e.tag_edits['custom'] = value
                elif e.custom != value:
                    e.custom = value
                    shown = True
            if shown:
                changed.append(path)
        scan_cache.save()
        return changed

    def make_external_entry(self, path: Path, cache: AudioCache) -> MusicEntry:
        """Build a MusicEntry for a file dragged in from OUTSIDE the library
        (VLC, Windows Explorer, …) so it can replace a song in a playlist slot.

        Reads the same tag/dance/bpm metadata as a normal scan and attaches
        already-cached audio features if present (no librosa analysis here, so a
        drop is instant; the ≈ similarity stays blank until analysis is run). The
        entry is NOT added to self.entries — it just lives in the playlist slot."""
        entry = self._make_entry(path, self._get_scan_cache(cache))
        fp = cache.recorded_fingerprint(path)
        tag_edits.apply(entry, tag_edits.load(fp) if fp else None)
        # The playlist index is keyed by filename and title, not by path, so an
        # outside copy of a planned track (a list naming an old library copy)
        # counts its past playlists too instead of reading ✦new.
        if self._track_playlists:
            self._apply_popularity(entry)
        entry.cluster = path.parent.name
        try:
            entry.features = cache.get(path, hash_if_missing=True)
        except Exception:
            entry.features = None
        return entry

    def adopt(self, entry: MusicEntry) -> None:
        """Give an entry built before this library was scanned what the scan
        knows: its playlist popularity and when the file came in.

        The window restores the last session while the scan still runs, each
        track rebuilt from its file through an empty stand-in library (see
        LibraryService.resolver), which knows neither."""
        if self._track_playlists:
            self._apply_popularity(entry)
        known = self.entry_for(entry.path)
        if known is not None:
            entry.added = known.added

    @property
    def entries(self) -> list[MusicEntry]:
        return self._entries

    @entries.setter
    def entries(self, entries: list[MusicEntry]) -> None:
        # A new list may hold as many entries as the old one: the version, not
        # the length, tells `_path_index` it is stale.
        self._entries = entries
        self._entries_version += 1

    def _path_index(self) -> tuple[dict[str, MusicEntry], dict[str, MusicEntry]]:
        """(exact, case-folded) path → entry, rebuilt when `entries` is replaced
        or changes size.

        Two maps rather than one so an exact hit always beats a case-folded one,
        which is what the linear scans this replaced did: they walked the whole
        list looking for an exact match before ever lowercasing anything."""
        key = (self._entries_version, len(self.entries))
        if self._path_idx_key != key:
            exact: dict[str, MusicEntry] = {}
            ci: dict[str, MusicEntry] = {}
            for e in self.entries:
                s = str(e.path)
                exact.setdefault(s, e)
                ci.setdefault(s.lower(), e)
            self._by_path, self._by_path_ci = exact, ci
            self._path_idx_key = key
        return self._by_path, self._by_path_ci

    def entry_for(self, path: Path | str, cache: AudioCache | None = None, *,
                  require_file: bool = False) -> MusicEntry | None:
        """The library entry for `path`, or None.

        Exact match wins over a case-folded one (Windows paths reach us in
        whatever case the drag source spelled them). With a `cache`, a path the
        library doesn't know is rebuilt as an external entry — a track dragged in
        from Explorer or named by a foreign .m3u.

        `require_file` gates that rebuild on the file existing. It is NOT
        cosmetic: `make_external_entry` derives title, dance and bpm from the
        FILENAME and succeeds happily on a path that is gone. Restoring a session
        wants the gate (a deleted track should drop out, not come back as a
        phantom row); a drop or an .m3u import deliberately does not (the name is
        all we have, and it is enough to fill the slot)."""
        target = str(path)
        exact, ci = self._path_index()
        hit = exact.get(target) or ci.get(target.lower())
        if hit is not None:
            return hit
        if cache is None:
            return None
        p = Path(path)
        if require_file and not p.is_file():
            return None
        try:
            return self.make_external_entry(p, cache)
        except Exception as exc:
            log.debug("🎵 Could not build an external entry for %s: %s", path, exc)
            return None

    def by_dance(self, dance: str) -> list[MusicEntry]:
        return [e for e in self.entries if e.dance == dance]

    def restricted_to(self, entries: list[MusicEntry]) -> "MusicLibrary":
        """A view of this library holding only `entries` — everything a pick is
        scored on (playlist popularity, finals/semi history, the class index)
        stays shared, only the candidate set shrinks.

        Lets a generator draw from a hand-picked pool (the open wishlists, an
        .m3u file) through the ordinary PlaylistSuggester: a dance the pool has
        no track for simply yields nothing, rather than quietly reaching back
        into the whole library.
        """
        view = copy.copy(self)
        view.entries = list(entries)
        return view

    def past_competition_entries(
        self, spec: CompetitionSpec
    ) -> tuple[list[MusicEntry], int]:
        """Library entries that appear in past per-class M3U files matching `spec`.

        Walks every '*.m3u' under PLAYLIST_DIR, keeps the files whose FILENAME
        matches the competition class/style (`competition_matches_file`; event name
        irrelevant), collects each song's match keys (same normalisation as
        `_learn_playlists`), and returns the library entries hitting any of them —
        plus how many M3U files matched (for the GUI hint / sanity-check).
        Eintanzen / party / christmas lists are skipped, as for popularity.

        The entries are not modified: their `replay_sources` (the tooltip's source
        lists) is the caller's to set — see `past_competition_round_pools`.
        """
        # match key → set of relevant M3U paths that contained that key
        key_to_files: dict[str, set[Path]] = defaultdict(set)
        n_files = 0
        self._refresh_stem_dance()
        if (root := playlist_dir()).exists():
            for m3u in playlist_files(root):
                if _is_superseded_playlist(m3u):
                    continue
                if is_side_list(m3u.stem):
                    continue
                if not competition_matches_file(spec, m3u):
                    continue
                n_files += 1
                try:
                    lines = read_playlist_text(m3u)[0].splitlines()
                except PlaylistEncodingError as exc:
                    _warn_unreadable(m3u, exc)
                    continue
                except Exception:
                    continue
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    for k in self._line_keys(line):
                        key_to_files[k].add(m3u)
        if not key_to_files:
            return [], n_files
        out: list[MusicEntry] = []
        for e in self.entries:
            if any(k in key_to_files for k in self._match_keys(e)):
                out.append(e)
        return out, n_files

    def line_resolver(self):
        """A function from one M3U line to the library entry it names, or None.

        Path-independent: a list written on another machine, or before the
        library moved, still resolves by filename stem, then by the
        dance-qualified title / song-title keys — the same namespacing as
        `_match_keys` / `_line_keys`. Build it once per batch of lists."""
        # key → first library entry carrying it.
        self._refresh_stem_dance()
        key_index: dict[str, MusicEntry] = {}
        for e in self.entries:
            for k in self._match_keys(e):
                key_index.setdefault(k, e)

        def _resolve(line: str) -> MusicEntry | None:
            sk = _stem_key(line)
            if sk in key_index:
                return key_index[sk]
            d = self._line_dance(line)
            tk = _title_key(line)
            if tk and _dq(d, tk) in key_index:
                return key_index[_dq(d, tk)]
            qk = _song_title_key(line)
            if len(qk) >= 3 and _dq(d, qk) in key_index:
                return key_index[_dq(d, qk)]
            return None
        return _resolve

    def past_competition_round_pools(
        self,
        spec: CompetitionSpec | None,
        schedule_heats: list[int],
        num_dances: int,
    ) -> tuple[list[MusicEntry], list[list[MusicEntry]], int, list[dict[int, list[str]]]]:
        """Per-round candidate pools for a competition, so a new round draws only
        from songs that history used in the SAME round ('final↔final, semi↔semi').

        `spec=None` matches EVERY past list (no class/style gate) — used by the
        per-slot 'find planned before' look-up, which only cares about dance + tier.

        Two historical layouts are handled:
          • round-tagged files (VR/ZR/2ZR/SEMI/ER in the filename) — every song in
            the file is added to that stage's pool (multi-stage files contribute to
            each stage they name; we do not section them, only range-restrict);
          • plain per-class files with no round marker — sliced bottom-up by the
            new schedule's heat counts (final = last `heats[-1]·dances` songs, etc.).

        Tagged stages are aligned to the schedule from the FINAL upward: the
        highest stage present feeds the final, the next the semi, and so on; when
        the schedule has more rounds than history, the earliest rounds share the
        earliest history stage. With `spec=None`, only files that look like real
        tournament lists (`is_competition_file`) are read. Returns (all matched
        entries, per-round pools aligned to `schedule_heats`, number of matched
        files, per-round source labels `id(entry) → list-names that placed it there`).
        """
        n_rounds = max(1, len(schedule_heats))
        round_pools_raw: list[list[MusicEntry]] = [[] for _ in range(n_rounds)]
        stage_pools: dict[int, list[tuple[MusicEntry, Path]]] = defaultdict(list)
        # Per-round source attribution: which lists put a song into THAT round (so
        # 'planned before' shows only the lists where it sat in the matched round,
        # not every list it appears anywhere in).
        round_files: list[dict[int, set[Path]]] = [defaultdict(set) for _ in range(n_rounds)]
        n_files = 0

        _resolve = self.line_resolver()

        if (root := playlist_dir()).exists():
            for m3u in playlist_files(root):
                if _is_superseded_playlist(m3u):
                    continue
                if is_side_list(m3u.stem):
                    continue
                if spec is not None:
                    if not competition_matches_file(spec, m3u):
                        continue
                elif not is_competition_file(m3u.stem) or is_working_collection_path(m3u):
                    continue   # not a tournament list, or a working/pre-sorting draft
                n_files += 1
                try:
                    lines = read_playlist_text(m3u)[0].splitlines()
                except PlaylistEncodingError as exc:
                    _warn_unreadable(m3u, exc)
                    continue
                except Exception:
                    continue

                songs: list[MusicEntry | None] = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    e = _resolve(line)
                    songs.append(e)
                if not any(s is not None for s in songs):
                    continue

                stages = _round_stages_in_name(m3u.stem)
                resolved = [e for e in songs if e is not None]
                if stages:
                    # Round-tagged: range-restrict to the stage(s) the file names.
                    for st in stages:
                        stage_pools[st].extend((e, m3u) for e in resolved)
                else:
                    # Plain combined list: slice bottom-up by the schedule's heats.
                    idx = len(songs)
                    for s in range(n_rounds - 1, -1, -1):
                        cnt = max(0, schedule_heats[s]) * max(1, num_dances)
                        seg = songs[max(0, idx - cnt):idx]
                        idx -= cnt
                        for e in seg:
                            if e is not None:
                                round_pools_raw[s].append(e)
                                round_files[s][id(e)].add(m3u)
                        if idx <= 0:
                            break
                    if idx > 0:   # leftover (history longer than schedule) → first round
                        for e in songs[:idx]:
                            if e is not None:
                                round_pools_raw[0].append(e)
                                round_files[0][id(e)].add(m3u)

        # Align tagged stages to schedule rounds from the final upward.
        present = sorted(stage_pools.keys(), reverse=True)   # final-most first
        if present:
            for s in range(n_rounds):
                rank = n_rounds - 1 - s                       # 0 = final
                st = present[rank] if rank < len(present) else present[-1]
                for e, m3u in stage_pools[st]:
                    round_pools_raw[s].append(e)
                    round_files[s][id(e)].add(m3u)
            for st in present[n_rounds:]:                      # extra-deep history
                for e, m3u in stage_pools[st]:
                    round_pools_raw[0].append(e)
                    round_files[0][id(e)].add(m3u)

        # De-duplicate each round pool by path (preserve order).
        round_pools: list[list[MusicEntry]] = []
        for pool in round_pools_raw:
            seen: set[str] = set()
            dedup: list[MusicEntry] = []
            for e in pool:
                p = str(e.path)
                if p not in seen:
                    seen.add(p)
                    dedup.append(e)
            round_pools.append(dedup)

        # Union across rounds = full matched set. The entries are shared library
        # objects: their `replay_sources` is left to the caller (round_sources).
        all_entries: list[MusicEntry] = []
        seen_all: set[str] = set()
        for pool in round_pools:
            for e in pool:
                p = str(e.path)
                if p not in seen_all:
                    seen_all.add(p)
                    all_entries.append(e)

        # Per-round source labels (id(e) → lists that placed it in THAT round), so a
        # caller can show the round-correct subset instead of the cross-round union.
        round_sources: list[dict[int, list[str]]] = []
        for dct in round_files:
            round_sources.append({
                eid: sorted(f"{p.parent.name} / {p.stem}" for p in files)
                for eid, files in dct.items()
            })
        return all_entries, round_pools, n_files, round_sources

    def similar_tracks(
        self,
        entry: MusicEntry,
        n: int = 10,
        same_dance: bool = True,
        min_display: float = 0.0,
        method: str | None = None,
    ) -> list[tuple[float, MusicEntry]]:
        """Return up to n tracks most similar to `entry` by timbre.

        Requires that audio analysis has run (entry.features must be set).
        Ranking z-scores every feature dimension across the candidate pool first
        (`_pool_similarity`), then takes the cosine — this stops the loudness term
        (MFCC-0) from dominating, so the scores spread out and the order is
        perceptual rather than bunched at ~99.9 %. `min_display` (0..1) drops
        results scoring below it (e.g. 0.5 → only tracks at least as aligned as
        orthogonal). Returns (display 0..1, MusicEntry) best-first; Christmas
        songs and the query itself are excluded.
        """
        if not entry.features:
            return []

        def _pool(base) -> list[MusicEntry]:
            return [
                e for e in base
                if e is not entry and e.features is not None and not e.is_xmas
            ]

        want_same = bool(same_dance and entry.dance)
        cands = _pool(self.by_dance(entry.dance) if same_dance and entry.dance else self.entries)
        # Graceful degradation while a full analysis is still running: if no track of
        # the SAME dance is analyzed yet, fall back to whatever subset IS analyzed
        # (any dance) so the user still gets results instead of an empty list.
        if not cands and want_same:
            cands = _pool(self.entries)
        if not cands:
            return []
        sims = _timbre_similarity(entry.features, cands, method)
        scored = [(sims[str(e.path)], e) for e in cands]
        scored.sort(key=lambda x: x[0], reverse=True)
        scored = [(d, e) for d, e in scored if d >= min_display]
        return scored[:n]

    def similar_by_playlists(
        self,
        entry: MusicEntry,
        n: int = 12,
        same_dance: bool = True,
    ) -> list[tuple[float, MusicEntry]]:
        """Return tracks that you tend to play *together* with `entry`.

        Behaviour-based: instead of timbre, this learns from your old M3U
        playlists. Two tracks score high when they keep showing up in the same
        playlists. Score is the Jaccard overlap of their playlist sets (0..1):
        shared playlists / total distinct playlists either appears in.
        Eintanzen/party playlists are excluded (same as for popularity).
        Tracks are matched to playlist entries by filename and by ID3 title/
        artist (not full path), so moved or renamed files still match. Returns
        (score, MusicEntry) sorted best-first.
        """
        mine = self._playlists_for(entry)
        if not mine:
            return []
        my_keys = self._match_keys(entry)
        pool = self.by_dance(entry.dance) if (same_dance and entry.dance) else self.entries
        scored: list[tuple[float, MusicEntry]] = []
        for e in pool:
            if e is entry or e.is_xmas:
                continue
            if self._match_keys(e) & my_keys:   # same track under any key → skip
                continue
            theirs = self._playlists_for(e)
            if not theirs:
                continue
            inter = len(mine & theirs)
            if inter == 0:
                continue
            score = inter / len(mine | theirs)   # Jaccard 0..1
            scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:n]

    def similar_to_file(
        self,
        path: Path,
        cache: AudioCache,
        n: int = 12,
        same_dance: bool = True,
        min_display: float = 0.0,
    ) -> tuple[MusicEntry, list[tuple[float, MusicEntry]]]:
        """Analyze an arbitrary (possibly external) audio file and find similar library tracks.

        Returns (pseudo_entry_for_the_file, results). Requires librosa for the analysis;
        the file's features are cached so repeated drops are fast.
        """
        tag_title = _get_title_artist_tags(path)[0]
        dance = _detect_dance(path.stem)
        takt = _detect_bpm_tagged(path.stem, tag_title, _get_tag_bpm(path), dance)
        feat = cache.get(path)
        if feat is None:
            # raises if librosa/ffmpeg unavailable; seed the beat tracker with the
            # dance's expected tempo so syncopated grooves don't lock to a harmonic.
            feat = cache._analyze_file(path, _tempo_prior(dance, takt))
            cache.put(path, feat)
            cache.save()
        entry = MusicEntry(
            path=path,
            title=_title_for(path.stem, tag_title),
            dance=dance,
            bpm=takt,
        )
        entry.features = feat
        return entry, self.similar_tracks(
            entry, n=n, same_dance=same_dance, min_display=min_display)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for e in self.entries:
            counts[e.dance or '?'] += 1
        return dict(counts)

    def other_genre_summary(self) -> dict[str, int]:
        """Count of undetected files grouped by their non-competition genre label."""
        counts: dict[str, int] = defaultdict(int)
        for e in self.entries:
            if e.dance is None and e.other_genre:
                counts[e.other_genre] += 1
        return dict(counts)
