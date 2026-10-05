"""The music library: scanning, caching, popularity learning and round picking.

Extracted from dancesport_planner.py (logical split). MusicLibrary owns the scan
+ cache pipeline and the _pick / regenerate playlist-building logic; it pulls its
data tables, parsing, scoring, caches and similarity metrics from the sibling
planner_* leaf modules.
"""
import copy
import hashlib
import logging
import os

from collections import Counter
from collections import deque
from collections import defaultdict
from pathlib import Path
import re
from typing import Any
from collections.abc import Callable
from planner.config import (  # auto-resolved
    MUSIC_DIR,
    PLAYLIST_DIR,
)
from planner.db import (  # auto-resolved
    AudioCache,
    _META_COLS,
    GlobalScanCache,
    PlaylistIndexCache,
    ScanCache,
    _entry_meta,
    _tempo_prior,
)
from planner.similarity import (  # auto-resolved
    _timbre_similarity,
)
from planner import custom_field, tag_edits
from planner.models import (  # auto-resolved
    DANCE_NAMES,
    GENRE_TO_DANCE,
    MusicEntry,
    OTHER_GENRE_LABELS,
    ScanCancelled,
    _EXCLUDED_FOLDERS,
    fold_text,
    folder_category_of_parts,
)
from planner.parsing import (  # auto-resolved
    _title_for,
    _detect_bpm_tagged,
    _detect_dance,
    _detect_year,
    dance_from_folders,
    _get_comment_tag,
    is_marker_noise,
    parse_comment_markers,
    _get_raw_genre_tag,
    _get_title_artist_tags,
    popm_stars,
    _is_christmas,
    _norm_title,
    _parse_class_tag,
    _playlist_class_of,
    title_marks_instrumental,
    _read_duration,
    _read_tags_once,
    _song_title_key,
    _stem_key,
    _title_key,
)
from planner.competition import (  # auto-resolved
    CompetitionSpec,
    _is_superseded_playlist,
    _round_stages_in_name,
    competition_matches_file,
    is_competition_file,
    is_side_list,
    is_working_collection_path,
)
from planner.warmup import (  # auto-resolved
    others_dance_from_path,
)
from planner.playlist_text import PlaylistEncodingError, read_playlist_text

log = logging.getLogger("dancesport.library")


def _warn_unreadable(m3u: Path, exc: PlaylistEncodingError) -> None:
    """A playlist left out of a folder walk because its text can't be decoded
    without losing characters — said out loud, not skipped in silence."""
    log.warning("⚠️ Playlist skipped, not read\n"
                "file: %s\n"
                "reason: %s", m3u, exc)


# Sentinel for regenerate()/anchor_similarity(): distinguishes "caller didn't pass an
# anchor → use the round's stored one" from "caller explicitly passed None → no timbre".
_ANCHOR_DEFAULT: Any = object()


def _is_warmup_list_name(name: str) -> bool:
    """Playlist / folder names that mark warm-up, party or seasonal lists — those
    never count for popularity or co-occurrence."""
    low = name.lower()
    return any(k in low for k in ('eintanzen', 'party', 'weihn', 'christmas', 'xmas'))


# (path, "mtime:size") for one file under the playlist dir.
_TreeFile = tuple[Path, str]


def _playlist_tree() -> tuple[list[_TreeFile], list[_TreeFile]]:
    """One walk over PLAYLIST_DIR returning its .m3u and .mp3 files with a change
    signature each.

    Both learners used to `rglob` the tree themselves (three walks in total). One
    `os.scandir` pass costs ~0.03 s for 2100 files INCLUDING the stat, because a
    Windows directory entry already carries mtime and size — so the signature that
    tells `PlaylistIndexCache` what actually changed is essentially free.
    """
    m3us: list[_TreeFile] = []
    mp3s: list[_TreeFile] = []
    stack = [str(PLAYLIST_DIR)]
    while stack:
        try:
            with os.scandir(stack.pop()) as it:
                entries = list(it)
        except OSError:
            continue
        for de in entries:
            try:
                if de.is_dir(follow_symlinks=False):
                    stack.append(de.path)
                    continue
                low = de.name.lower()
                bucket = m3us if low.endswith(".m3u") else mp3s if low.endswith(".mp3") else None
                if bucket is not None:
                    st = de.stat()
                    bucket.append((Path(de.path), f"{st.st_mtime_ns}:{st.st_size}"))
            except OSError:
                continue
    m3us.sort()
    mp3s.sort()
    return m3us, mp3s


def _library_mp3s(root: Path) -> list[tuple[Path, float]]:
    """Every .mp3 under `root` with the time it was created (breadth-first).

    Same trick as `_playlist_tree`: a Windows directory entry already carries the
    timestamps, so `DirEntry.stat()` needs no extra syscall — the whole library
    (3.8k files) walks in ~0.02 s, faster than the plain `rglob` this replaced,
    and the creation time comes along for free. That time is what the 🆕 "Added"
    column shows: a copied file gets a fresh creation time at its destination,
    while its mtime still carries whenever the tags were last written.
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
            except OSError:
                continue
    return out


# A 4-digit year in a playlist path ('Turnier 2019 …') — the only date a plain
# M3U carries, and what 'last played' is read from.
_PLAYLIST_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def playlist_year(path_str: str) -> int | None:
    """Newest year in a playlist's path, None when it carries no date."""
    years = [int(m.group(0)) for m in _PLAYLIST_YEAR_RE.finditer(path_str)]
    return max(years) if years else None


# Round stages as `_round_stages_in_name` numbers them: 50 is the Halbfinale,
# 60 the Endrunde. Those two are the rounds worth remembering — they are the
# ones a DJ picks by hand, one track per dance.
_SEMI_STAGE = 50
_FINAL_STAGE = 60

# A trailing block only counts as a round when the list uses at least this many
# dances. A one- or two-line list has a "last round without a repeated dance"
# too, and it says nothing at all about who danced a final.
_FINAL_MIN_DANCES = 3


def _split_last_round(lines: list[str], dances: list[str | None],
                      known: set[str]) -> tuple[list[str], list[str]]:
    """(the last round in `lines`, everything before it) — ([], lines) if there
    is none.

    A round is one pass through the dances, so it is the trailing run in which
    no dance comes up twice, and it only counts when that run covers EVERY dance
    the list uses. A preliminary laid out in heats ends on two of the same dance,
    so its run stops early and is correctly not read as a round of its own.

    Lines whose dance could not be worked out neither break the run nor have to
    be covered by it — about one line in twenty is one of those, and letting a
    single unrecognised filename veto the round cost more than half the finals
    in the real tree."""
    seen: set[str] = set()
    tail: list[str] = []
    for line, dance in zip(reversed(lines), reversed(dances)):
        if dance in seen:
            break
        if dance:
            seen.add(dance)
        tail.append(line)
    if seen != known:
        return [], lines
    return list(reversed(tail)), lines[:len(lines) - len(tail)]


def _named_stage(name: str) -> int | None:
    """The one round a playlist's own name declares, or None.

    'HGR S Lat Finale' is a final and nothing else; a name that lists several
    rounds ('VR-ZR-ER') holds all of them, so it is treated like a silent one
    and sectioned by position instead."""
    stages = _round_stages_in_name(name)
    return stages[0] if len(stages) == 1 else None


def _dq(dance: str | None, key: str) -> str:
    """Namespace a title-derived match key by its dance so same-title, different-dance
    tracks don't collapse together. `_clean_title` strips the leading dance code, so
    'QS - No Roots' and 'TG - No Roots' both reduce to 'no roots' — without this they
    would share popularity. The full-filename stem key already carries the dance, so it
    stays plain. Dance unknown → the bare key (best effort, as before)."""
    return f"{dance}\x1f{key}" if dance else key




# ── Music Library ──────────────────────────────────────────────────────────────
class MusicLibrary:
    def __init__(self):
        self.entries: list[MusicEntry] = []
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
        # `entries` changes length (a scan, a cache load, an append).
        self._by_path: dict[str, MusicEntry] = {}
        self._by_path_ci: dict[str, MusicEntry] = {}
        self._path_idx_n = -1
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
        """
        scan_cache = self._get_scan_cache(cache)
        music_dir = music_dir or MUSIC_DIR
        added_ts: dict[str, float] = {}   # file path → creation time (see the walk below)
        log.info("  📂 Scanning music library …  %s", music_dir)
        if not music_dir.exists():
            log.warning("  ⚠️ Music directory not found: %s", music_dir)
        else:
            _SKIP_DIR = re.compile(r'christmas|weihnacht|endrunden|special', re.IGNORECASE)
            skipped_dirs: set = set()
            seen: set = set()
            reused = 0
            # Materialise the file list first so total (and "how many left") is known.
            if progress_cb is not None:
                progress_cb(0, 0, music_dir, False)   # signal "listing files…" phase
            found = _library_mp3s(music_dir)
            added_ts = {str(p): ts for p, ts in found}
            all_mp3 = [p for p, _ in found]
            total = len(all_mp3)
            for idx, mp3 in enumerate(all_mp3, 1):
                if should_cancel is not None and idx % 25 == 0 and should_cancel():
                    if global_cache is not None:
                        global_cache.save()   # keep what we scanned so far
                    scan_cache.save()
                    raise ScanCancelled(f"Scan cancelled after {idx}/{total} files")
                was_reused = False
                # Hard-excluded folders (sox, unbearbeitet) never enter the library,
                # regardless of scan mode.
                excl_parts = {p.lower() for p in mp3.relative_to(music_dir).parts[:-1]}
                if excl_parts & _EXCLUDED_FOLDERS:
                    if progress_cb is not None and (idx % 25 == 0 or idx == total):
                        progress_cb(idx, total, mp3, True)
                    continue
                if skip_special:
                    # parts[:-1] = all directory segments below music_dir (not the filename)
                    rel_parts = mp3.relative_to(music_dir).parts[:-1]
                    skip_hit  = next((p for p in rel_parts if _SKIP_DIR.search(p)), None)
                    # A soft library category (anthems / background / seasonal /
                    # wrong_tempo / duplicates) overrides the special/christmas
                    # skip: the file loads (browsable) but is soft-excluded from
                    # generation. endrunden / plain special/ stay skipped.
                    if skip_hit and not folder_category_of_parts(rel_parts):
                        skipped_dirs.add(skip_hit)
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
                        bpm = _detect_bpm_tagged(mp3.stem, cached_entry.get('tag_title'))
                        if bpm != cached_entry.get('bpm'):
                            cached_entry = {**cached_entry, 'bpm': bpm}
                            global_cache.put(mp3, cached_entry)
                        # ⏱ Rows written before the duration column carry 0 —
                        # probe the length once, like `_make_entry` does.
                        if not cached_entry.get('duration'):
                            secs = _read_duration(mp3)
                            if secs:
                                cached_entry = {**cached_entry, 'duration': secs}
                                global_cache.put(mp3, cached_entry)
                        self.entries.append(MusicEntry(path=mp3, **cached_entry))
                        reused += 1
                        was_reused = True
                    else:
                        entry = self._make_entry(mp3, scan_cache)
                        global_cache.put(mp3, _entry_meta(entry))
                        self.entries.append(entry)
                else:
                    self.entries.append(self._make_entry(mp3, scan_cache))
                if progress_cb is not None and (idx % 25 == 0 or idx == total):
                    progress_cb(idx, total, mp3, was_reused)
            if skipped_dirs:
                log.info("  Skipped dirs: %s", ', '.join(sorted(skipped_dirs)))
            log.info("  🎶 %s MP3 files found", len(self.entries))
            scan_cache.save()
            if global_cache is not None:
                global_cache.prune(seen)
                global_cache.save()
                log.info("  ♻️  %s reused from global cache, %s (re)scanned",
                         reused, len(self.entries) - reused)
            self.apply_tag_edits(cache)

        if learn:
            log.info("  📜 Analyzing existing playlists … %s", PLAYLIST_DIR)
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
        for path_str, meta in global_cache.all_entries():
            p = Path(path_str)
            entry = MusicEntry(path=p, **meta)
            # 🩹 Self-heal bpm from the name + title tag so global-cache
            # entries built before the detection fix get tempo-filtered too.
            bpm = _detect_bpm_tagged(p.stem, getattr(entry, "tag_title", None))
            if bpm != entry.bpm:
                entry.bpm = bpm
                global_cache.put(p, {**meta, 'bpm': bpm})
            entry.cluster = p.parent.name
            entry.features = cache.get(p, hash_if_missing=False)
            self.entries.append(entry)
        self.apply_tag_edits(cache)
        return len(self.entries)

    def apply_tag_edits(self, cache: AudioCache) -> None:
        """Lay the in-app tag edits (planner.tag_edits) over every entry.

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
        for e, fp in zip(entries, fps):
            edit = tag_edits.save(fp, changes_for(e))
            same = [x for x in self.entries
                    if x is not e and cache.recorded_fingerprint(x.path) == fp]
            for target in (e, *same):
                tag_edits.apply(target, edit)
                touched[str(target.path)] = Path(target.path)
        return list(touched.values())

    def _make_entry(self, path: Path, scan_cache: ScanCache) -> MusicEntry:
        # Fast path: metadata already cached for this file size
        cached = scan_cache.get(path)
        if cached:
            # 🩹 Re-derive bpm from the filename on every cache hit: it's a pure
            # function of the name (+ title tag), so an old cache built before
            # the detection was fixed (e.g. slow 'Nicht TSO Turniertempo'
            # versions at 19 bars/min, or a name truncated past its '(RB 25)'
            # tact that survives in the tag) self-heals without a re-scan.
            bpm = _detect_bpm_tagged(path.stem, cached.get('tag_title'))
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
                if secs:
                    cached = {**cached, 'duration': secs}
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
        tags, duration = _read_tags_once(path)
        raw_genre = _get_raw_genre_tag(path, tags) or ''
        genre_dance = None
        genre_other = None
        if raw_genre:
            parts = [raw_genre] + raw_genre.split(';')
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
            dance = genre_dance or file_dance
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
        if not is_instr:
            # No COMM 'instr' tag — a filename/title marker like '(Instr.)' or
            # '(inst)' flags the track as instrumental too.
            is_instr = title_marks_instrumental(f"{name} {tag_title or ''}")

        data = {
            'title':          _title_for(name, tag_title),
            'dance':          dance,
            'bpm':            _detect_bpm_tagged(name, tag_title),
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
            'duration':       duration,
        }
        scan_cache.put(path, data)
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

    def _path_index(self) -> tuple[dict[str, MusicEntry], dict[str, MusicEntry]]:
        """(exact, case-folded) path → entry, rebuilt when `entries` changes size.

        Two maps rather than one so an exact hit always beats a case-folded one,
        which is what the linear scans this replaced did: they walked the whole
        list looking for an exact match before ever lowercasing anything."""
        if self._path_idx_n != len(self.entries):
            exact: dict[str, MusicEntry] = {}
            ci: dict[str, MusicEntry] = {}
            for e in self.entries:
                s = str(e.path)
                exact.setdefault(s, e)
                ci.setdefault(s.lower(), e)
            self._by_path, self._by_path_ci = exact, ci
            self._path_idx_n = len(self.entries)
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

    def _dance_map_digest(self) -> str:
        """Fingerprint of the stem → dance map `_line_keys` qualifies its keys by.

        The cached keys of an untouched playlist are only still correct while this
        is unchanged — see `PlaylistIndexCache`."""
        h = hashlib.blake2b(digest_size=16)
        for stem in sorted(self._stem_dance):
            h.update(f"{stem}\x1f{self._stem_dance[stem] or ''}\n".encode("utf-8", "ignore"))
        return h.hexdigest()

    def _index_playlist(self, cache: PlaylistIndexCache, pl_id: str, sig: str,
                        derive: Callable[[], tuple[str | None, list[str],
                                                   list[str], list[str]]]
                        ) -> None:
        """Fold one playlist into the co-occurrence index, from cache when it has
        not changed on disk. `derive` is only called on a miss."""
        hit = cache.get(pl_id, sig)
        if hit is None:
            hit = derive()
            cache.put(pl_id, sig, *hit)
        cls, keys, final_keys, semi_keys = hit
        self._playlist_cls[pl_id] = cls
        for k in keys:
            self._track_playlists[k].add(pl_id)
        for k in final_keys:
            self._track_finals[k].add(pl_id)
        for k in semi_keys:
            self._track_semis[k].add(pl_id)

    def _learn_playlists(self) -> int:
        count = 0
        if not PLAYLIST_DIR.exists():
            return count
        self._refresh_stem_dance()   # so lines qualify by the file's calculated dance
        m3us, mp3s = _playlist_tree()
        cache = PlaylistIndexCache(PLAYLIST_DIR, self._dance_map_digest())
        seen: set[str] = set()
        for m3u, sig in m3us:
            try:
                if _is_superseded_playlist(m3u):
                    continue
                count += 1
                # Eintanzen playlists count for nothing — neither popularity nor
                # co-occurrence — so they are never even read.
                if _is_warmup_list_name(m3u.stem):
                    continue
                pl_id = str(m3u)
                seen.add(pl_id)
                self._index_playlist(
                    cache, pl_id, sig,
                    lambda m=m3u: (_playlist_class_of(m), *self._m3u_keys(m)))
            except Exception:
                pass
        count += self._learn_playlist_folders(cache, seen, m3us, mp3s)
        cache.prune(seen)
        cache.save()
        return count

    def _m3u_keys(self, m3u: Path) -> tuple[list[str], list[str], list[str]]:
        """Every match key the lines of one playlist file derive, and the subsets
        of them that were danced in its FINAL and in its SEMIFINAL round.

        Dance-qualified (stem + title + aggressive song-title) so 'jive(43) - Bim
        Bam', '16 Bim Bam' and 'Bim Bam' map together within a dance, while 'No
        Roots' QS vs TG stay apart — see `_line_keys` / `_dq`. Renamed / moved
        files still match, because no key is a path."""
        try:
            raw = read_playlist_text(m3u)[0].splitlines()
        except OSError:
            return [], [], []
        except PlaylistEncodingError as exc:
            _warn_unreadable(m3u, exc)
            return [], [], []
        lines = [ln.strip() for ln in raw
                 if ln.strip() and not ln.strip().startswith('#')]
        return self._keys_and_rounds(m3u.stem, lines)

    def _folder_keys(self, folder: Path, files: list[_TreeFile]
                     ) -> tuple[list[str], list[str], list[str]]:
        """`_m3u_keys` for a tournament folder — the copied files ARE its lines."""
        return self._keys_and_rounds(folder.name, [str(mp3) for mp3, _sig in files])

    def _keys_and_rounds(self, name: str, lines: list[str]
                         ) -> tuple[list[str], list[str], list[str]]:
        """(all match keys, the final's, the semifinal's) for one playlist's lines.

        Two things say which round a line belongs to, and both are needed here:
        the NAME, when the list is one round ('… Finale.m3u', a 'Finale' folder),
        and otherwise the POSITION, because most saved lists hold a whole
        competition back to back — see `_late_lines`."""
        keys: set[str] = set()
        for line in lines:
            keys |= self._line_keys(line)
        stage = _named_stage(name)
        if stage is not None:
            final_lines = lines if stage == _FINAL_STAGE else []
            semi_lines = lines if stage == _SEMI_STAGE else []
        else:
            final_lines, semi_lines = self._late_lines(lines)

        def _keys_of(block: list[str]) -> set[str]:
            out: set[str] = set()
            for line in block:
                out |= self._line_keys(line)
            return out

        return sorted(keys), sorted(_keys_of(final_lines)), sorted(_keys_of(semi_lines))

    def _late_lines(self, lines: list[str]) -> tuple[list[str], list[str]]:
        """(final, semifinal) of a list that holds a whole competition.

        A saved competition reads SA SA CC CC … | SA CC RB PD JI | SA CC RB PD JI
        — the heats first, then the two rounds that are danced once through. So
        the final is the last full pass (`_split_last_round`) and the semifinal
        is the one before it. A preliminary never reaches back that far: its heats
        repeat the dances, the run stops early, and nothing is claimed.

        What sits before the final is not always a Halbfinale by name — in a
        three-round event it is the Zwischenrunde. It is picked the same way a
        semifinal is, one track per dance, so it counts as one.

        The guess is deliberately generous: two independent lists are needed
        before anything acts on it (`planner.scoring._FINAL_MIN_PLAYS`), so a
        stray misread washes out, while a miss is a fact nothing can recover."""
        dances = [self._line_dance(line) for line in lines]
        known = {d for d in dances if d}
        if len(known) < _FINAL_MIN_DANCES:
            return [], []
        final, rest = _split_last_round(lines, dances, known)
        if not final:
            return [], []
        semi, _ = _split_last_round(rest, dances[:len(rest)], known)
        return final, semi

    def _learn_playlist_folders(self, cache: PlaylistIndexCache, seen: set[str],
                                m3us: list[_TreeFile], mp3s: list[_TreeFile]) -> int:
        """Learn popularity + co-occurrence from tournament FOLDER trees: not
        everyone writes .m3u files — many DJs just copy the music into one folder
        per tournament (e.g. 'H:\\DM Latein 2026\\HGR S Lat\\Finale\\…').

        Every directory under PLAYLIST_DIR that directly contains MP3s acts as one
        virtual playlist (its files are the lines), so class detection and
        co-occurrence work per round folder the same way they do per M3U file.
        Top-level trees that contain any .m3u are skipped — those are already
        learned from their playlists, and counting the copied files again would
        double every song. Warm-up / party / seasonal folders are skipped like
        their M3U counterparts. Returns the number of folder playlists learned."""
        # Top-level subfolders whose tree already carries .m3u playlists
        # ('' = playlist dir root itself).
        m3u_tops = set()
        for m3u, _sig in m3us:
            rel = m3u.relative_to(PLAYLIST_DIR).parts
            m3u_tops.add(rel[0] if len(rel) > 1 else "")
        groups: dict[Path, list[_TreeFile]] = defaultdict(list)
        for mp3, sig in mp3s:
            groups[mp3.parent].append((mp3, sig))
        count = 0
        for folder in sorted(groups):
            rel_parts = folder.relative_to(PLAYLIST_DIR).parts
            top = rel_parts[0] if rel_parts else ""
            if top in m3u_tops:
                continue
            if any(_is_warmup_list_name(p) for p in rel_parts):
                continue
            files = sorted(groups[folder])
            pl_id = str(folder)
            seen.add(pl_id)
            # A folder playlist IS its file list, so its own names+mtimes are the
            # signature — adding or replacing one track re-derives just that folder.
            self._index_playlist(
                cache, pl_id, "|".join(f"{p.name}:{s}" for p, s in files),
                lambda f=folder, fl=files: (_playlist_class_of(f),
                                            *self._folder_keys(f, fl)))
            count += 1
        return count

    def relearn_playlists(self) -> int:
        """Re-learn playlist popularity + co-occurrence from PLAYLIST_DIR alone.

        No filesystem walk and no audio analysis: the existing `entries` are kept;
        only the M3U-derived index (co-occurrence + playlist classes) is rebuilt
        from scratch and popularity re-applied per entry — so a freshly exported
        tournament counts without a full library reload.
        Returns the number of M3U files analyzed."""
        self._track_playlists.clear()
        self._playlist_cls.clear()
        self._track_finals.clear()
        self._track_semis.clear()
        n = self._learn_playlists()
        for e in self.entries:
            e.source_info = ""   # _apply_popularity only overwrites on a hit
            self._apply_popularity(e)
        return n

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
        view._path_idx_n = -1   # force the path index to rebuild for the subset
        return view

    def _refresh_stem_dance(self) -> None:
        """(Re)build the stem-key → calculated-dance map from the current entries, so
        `_line_keys` can qualify a playlist line by the SAME dance the library assigned
        the file (genre tag wins over the filename — see `_make_entry`)."""
        self._stem_dance = {_stem_key(str(e.path)): e.dance for e in self.entries}
        self._line_key_memo.clear()   # the map the memoized keys were derived from

    def _line_dance(self, line: str) -> str | None:
        """Dance for a playlist line: the calculated dance of the library file it points
        at (via stem key), else detected from the filename / path. This keeps the line's
        qualifier consistent with the entry's `dance` even when an ID3 genre tag overrode
        the filename guess."""
        d = self._stem_dance.get(_stem_key(line))
        if d:
            return d
        return _detect_dance(Path(line).name) or _detect_dance(line)

    def _line_keys(self, line: str) -> set[str]:
        """Dance-qualified co-occurrence keys for one playlist entry (a file path / M3U
        line). Mirrors `_match_keys` so the learn side and the entry side meet on the
        same keys. Title / song-title keys are namespaced by the line's dance; the bare
        filename stem key stays plain (it already carries the dance).

        Memoized on the raw line, and never mutated by a caller. 2000 playlists
        hold ~141k lines but only ~8k distinct ones — a well-used track derives
        the same keys twenty times over, which was ~4 s of every single start."""
        hit = self._line_key_memo.get(line)
        if hit is not None:
            return hit
        d = self._line_dance(line)
        keys = {_stem_key(line)}
        tkey = _title_key(line)
        if tkey:
            keys.add(_dq(d, tkey))
        skey = _song_title_key(line)
        if len(skey) >= 3:
            keys.add(_dq(d, skey))
        self._line_key_memo[line] = keys
        return keys

    def _match_keys(self, entry: MusicEntry) -> set[str]:
        """All keys under which `entry` may appear in the playlist index:
        exact filename, filename-derived title, and ID3 tag title / 'artist title'.
        This is what lets a renamed file still match its old playlist entries.

        Title-derived keys are namespaced by the track's own dance (`_dq`) so a
        same-titled track of a DIFFERENT dance ('No Roots' QS vs TG, 'Flowers' SF vs
        RB) can't borrow its popularity — mirroring `_line_keys` on the
        learn side. The bare filename stem key stays plain (it already carries the dance)."""
        d = entry.dance
        keys = {_stem_key(str(entry.path))}
        tkey = _title_key(str(entry.path))
        if tkey:
            keys.add(_dq(d, tkey))
        # Same aggressive key the learn side indexes — matches renamed / moved /
        # re-encoded copies (different path, same song) to their playlist history.
        skey = _song_title_key(str(entry.path))
        if len(skey) >= 3:
            keys.add(_dq(d, skey))
        if entry.tag_title:
            tt = _norm_title(entry.tag_title)
            if len(tt) >= 3:
                keys.add(_dq(d, tt))
            if entry.tag_artist:
                at = _norm_title(f"{entry.tag_artist} {entry.tag_title}")
                if len(at) >= 3:
                    keys.add(_dq(d, at))
        return keys

    def share_playlist_index_from(self, other: MusicLibrary) -> None:
        """Adopt another library's learned playlist co-occurrence + popularity data.

        The playlist index is keyed by filename / title (path-independent), so a
        library scanned WITHOUT playlist learning (e.g. the global repo, which uses
        learn=False for speed) can reuse the index the competition library already
        built — making 'based on my playlist history' work there too. Popularity is
        recomputed per entry from the shared index (filename-matched, so it works
        even when the repo lives on a different drive than the playlists).
        """
        if other is self or not getattr(other, "_track_playlists", None):
            return
        self._track_playlists = other._track_playlists
        self._playlist_cls = getattr(other, "_playlist_cls", {})
        self._track_finals = getattr(other, "_track_finals", {})
        self._track_semis = getattr(other, "_track_semis", {})
        for e in self.entries:
            self._apply_popularity(e)

    def playlists_for(self, entry: MusicEntry) -> set[str]:
        """Which past playlists this track turns up in — for anything outside
        this class that wants to reason about what was played together."""
        return self._playlists_for(entry)

    def _playlists_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """Union of every playlist this entry appears in, across all match keys.

        `keys` lets a caller that already has `_match_keys(entry)` (regex-heavy)
        pass it in rather than have this recompute it — see `_apply_popularity`."""
        out: set[str] = set()
        for k in keys if keys is not None else self._match_keys(entry):
            pls = self._track_playlists.get(k)
            if pls:
                out |= pls
        return out

    def _finals_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """…of those, the ones that danced it in their FINAL round."""
        return self._round_playlists_for(entry, self._track_finals, keys)

    def _semis_for(self, entry: MusicEntry, keys: set[str] | None = None) -> set[str]:
        """…and the ones that danced it in their SEMIFINAL."""
        return self._round_playlists_for(entry, self._track_semis, keys)

    def _round_playlists_for(self, entry: MusicEntry, index: dict[str, set[str]],
                             keys: set[str] | None = None) -> set[str]:
        out: set[str] = set()
        for k in keys if keys is not None else self._match_keys(entry):
            pls = index.get(k)
            if pls:
                out |= pls
        return out

    def _apply_popularity(self, entry: MusicEntry) -> None:
        """Set entry.popularity + source_info from the playlist index.

        popularity = number of DISTINCT (non-eintanzen) playlists this track appears
        in, matched by the path-independent keys in `_match_keys` (filename, derived
        title, aggressive song-title, ID3 tags). This is what makes a moved / renamed /
        re-encoded copy still count — exact-path matching missed e.g.
        'LatinEnergy\\08 1-16 El Sonador (CC 31).mp3', which lives under a
        different folder/name than its playlist entries.
        """
        keys = self._match_keys(entry)
        pls = self._playlists_for(entry, keys)
        entry.popularity = len(pls)
        # Per-class play counts: how many of those playlists were run as which start
        # class (parsed from the playlist file/folder name). Lists whose class can't
        # be detected still count toward `popularity`, just not toward any class.
        cls_counts: Counter = Counter()
        for p in pls:
            c = self._playlist_cls.get(p)
            if c:
                cls_counts[c] += 1
        entry.class_plays = dict(cls_counts) or None
        # How many of those plays were a FINAL, and how many a SEMIFINAL. A title
        # can be the most-played in the library and still be a heat title — which
        # is exactly what the two picked rounds must not reach for first (see
        # planner.scoring / `_get_pool`).
        entry.final_plays = len(self._finals_for(entry, keys) & pls)
        entry.semi_plays = len(self._semis_for(entry, keys) & pls)
        # When it was last used: the newest year any of those playlists is dated
        # to. Lists without a date in their path say nothing, so a track that
        # only ever appears in those stays None rather than counting as old.
        years = []
        for p in pls:
            if p not in self._playlist_year:
                self._playlist_year[p] = playlist_year(p)
            y = self._playlist_year[p]
            if y:
                years.append(y)
        entry.last_played = max(years) if years else None
        if pls:
            # Only the first three names are ever shown. A well-used track sits in
            # 149 playlists, and building a Path for every one of them to throw 146
            # away was ~40 % of this call — stop as soon as three distinct stems are
            # in hand (still in sorted order, so the shown names don't wobble).
            stems: list[str] = []
            for p in sorted(pls):
                stem = Path(p).stem
                if stem not in stems:
                    stems.append(stem)
                    if len(stems) == 3:
                        break
            entry.source_info = ", ".join(stems)

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
        if PLAYLIST_DIR.exists():
            for m3u in PLAYLIST_DIR.rglob("*.m3u"):
                if _is_superseded_playlist(m3u):
                    continue
                stem_lower = m3u.stem.lower()
                if ('eintanzen' in stem_lower or 'party' in stem_lower
                        or 'weihn' in stem_lower or 'christmas' in stem_lower
                        or 'xmas' in stem_lower):
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
    ) -> tuple[list[MusicEntry], list[list[MusicEntry]], int]:
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

        if PLAYLIST_DIR.exists():
            for m3u in PLAYLIST_DIR.rglob("*.m3u"):
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
        cands = _pool(self.by_dance(entry.dance) if want_same else self.entries)
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
        takt = _detect_bpm_tagged(path.stem, tag_title)
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
