#!/usr/bin/env python3
"""Shared SQLite layer of the Dancesport Playlist Planner.

Extracted from dancesport_planner.py (light split): the normalized schema +
migrations, the thread-local connection factory `_db`, and the three caches
built on it (AudioCache incl. librosa analysis, ScanCache, GlobalScanCache)
plus orphan cleanup and the cheap coverage queries.

`MusicEntry` lives in dancesport_planner; everything here only duck-types it
(`entry.path` / `entry.features`), so there is no circular import.
"""

import contextlib
import gc
import hashlib
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING
from collections.abc import Callable

if TYPE_CHECKING:
    from planner.models import MusicEntry

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import librosa
    HAS_LIBROSA = HAS_NUMPY   # librosa is unusable without numpy
except ImportError:
    HAS_LIBROSA = False

from planner.config import (
    AUDIO_DB_FILE, CACHE_FILE, SCAN_CACHE_FILE, GLOBAL_SCAN_CACHE_FILE,
)

log = logging.getLogger("dancesport.db")

# Length of the packed feature vector stored in AudioFeatures.mfcc. The name is
# historical — it now holds MFCC *plus* spectral-contrast and rhythm features:
#   60  MFCC      (20 means | 20 stds | 20 delta-means)   – timbre
#   10  contrast  (5 means | 5 stds, spectral_contrast)   – brightness/genre
#   14  rhythm    (12 tempogram lag-profile bins | onset mean | onset std) – groove
# = 84 total. Bumping this (and CACHE_VERSION) invalidates shorter cached vectors.
_AUDIO_FEAT_DIM = 84

# Only the first 60 dims of the 84-dim vector are pure MFCC timbre (20 means | 20 stds
# | 20 delta-means). The contrast (10) + rhythm (14) tail is still STORED in the DB but
# deliberately EXCLUDED from timbre similarity — BPM already handles tempo, and mixing
# rhythm/brightness into the cosine diluted the timbre signal. See `_feat_vector`.
_TIMBRE_MFCC_DIM = 60

# Per-song single-Gaussian timbre model (Mandel-Ellis): k MFCC coefficients →
# mean (k) + full covariance (k×k), compared by symmetric KL. Independent of the
# summary vector above; uses raw per-frame MFCCs with short (Java-matched) frames.
_GAUSS_MFCC = 20

# Beats per BAR (takt) per dance code. The filename label is a TAKT (bars/min); the
# librosa tempo estimator works in musical BPM (beats/min) = takt × beats-per-bar.
_BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4,
                  "CC": 4, "SA": 2, "RB": 4, "PD": 2, "JI": 4}

# Standard takt midpoint per dance, used as a fallback prior when the per-file takt
# is unknown. Mirrors planner.TEMPO_RANGES (kept local to avoid a circular import).
_DEFAULT_TAKT = {"LW": 29, "TG": 32, "WW": 59, "SF": 29, "QS": 51,
                 "CC": 31, "SA": 51, "RB": 25, "PD": 59, "JI": 42}


def _tempo_prior(dance: str | None, takt: float | None) -> float | None:
    """Expected musical tempo (beats/min) to seed librosa's beat tracker.

    Dance-agnostic beat tracking snaps syncopated grooves (esp. samba — the "and" of
    beat 1 and "e" of beat 2 fire strong off-beat transients) to a metric harmonic of
    the true pulse. Seeding `start_bpm` with the dance's expected tempo pulls the
    estimate back onto the real beat. Returns None when the dance is unknown (→ keep
    librosa's default prior). Prefers the per-file takt; falls back to the dance norm.
    """
    bpb = _BEATS_PER_BAR.get(dance or "")
    if bpb is None:
        return None
    t = takt if takt else _DEFAULT_TAKT.get(dance or "")
    return float(t * bpb) if t else None


def _tempo_from_tempogram(tg, sr, expected_bpm, hop_length=512, band=0.10):
    """Read the tempo off an already-computed tempogram, constrained to the dance's
    expected band (`expected_bpm` ± `band`).

    A library-wide comparison (samba especially) showed a plain beat tracker — even
    seeded with `start_bpm` — drifts onto metric harmonics (×0.8 / ×1.3 / ×1.4 of the
    real pulse) because syncopated off-beats out-vote the true beat. Picking the
    strongest tempogram-autocorrelation lag *within* the expected band can't land on a
    harmonic, so it tracked the label on 96% of files (100% of sambas) vs 65% for the
    unconstrained tracker. Returns None when no prior is given or the band is empty
    (caller then falls back to `librosa.beat.beat_track`).

    The lag axis is integer onset frames, so its BPM grid is hyperbolically coarse at
    fast tempi: at Viennese-Waltz pulse (~177 bpm) the only grid points are lag 7 =
    185 bpm and lag 8 = 162 bpm — nothing between — so every WW snapped to 185 ≈ T62.
    We refine the winning lag to sub-frame precision with a parabola through it and its
    two neighbours before converting back to BPM.
    """
    if tg is None or not expected_bpm:
        return None
    ac = np.nan_to_num(np.mean(tg, axis=1))                       # mean lag profile
    freqs = librosa.tempo_frequencies(len(ac), sr=sr, hop_length=hop_length)
    lo, hi = expected_bpm * (1.0 - band), expected_bpm * (1.0 + band)
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        return None
    idx = np.where(mask)[0]
    peak = int(idx[int(np.argmax(ac[idx]))])
    # Sub-lag refinement: parabolic interpolation of the peak (uses the raw lag
    # neighbours, even if they fall just outside the band) → fractional lag.
    delta = 0.0
    if 0 < peak < len(ac) - 1:
        ym1, y0, yp1 = float(ac[peak - 1]), float(ac[peak]), float(ac[peak + 1])
        denom = ym1 - 2.0 * y0 + yp1
        if denom != 0.0:
            delta = max(-0.5, min(0.5, 0.5 * (ym1 - yp1) / denom))
    lag = peak + delta
    if lag <= 0:
        return None
    return float(60.0 * sr / (hop_length * lag))


@dataclass
class AudioFeatures:
    bpm: float
    mfcc: Any  # 84-dim float32 ndarray (list w/o numpy), see _AUDIO_FEAT_DIM
    centroid: float  # spectral centroid mean
    rms: float  # root-mean-square energy mean
    # Single-Gaussian timbre model over raw per-frame MFCCs (Mandel-Ellis). Used by the
    # "gaussian_kl" similarity method. None for vectors analyzed before schema v9.
    # Stored as float32 ndarrays — check `is None`, never truthiness.
    mfcc_mean: Any = None  # _GAUSS_MFCC means
    mfcc_cov: Any = None  # _GAUSS_MFCC × _GAUSS_MFCC covariance, row-major
    # Lazily-memoized (mu, cov, inv) float64 triple filled by _gauss_of on first
    # use, so repeated similarity calls skip the 20×20 matrix inversion. Never
    # persisted; (None, None, None) marks an absent/singular Gaussian.
    gauss_cache: Any = field(default=None, repr=False, compare=False)


# ── Content fingerprint (duplicate detection) ──────────────────────────────────
_FP_SAMPLE = 256 * 1024   # bytes read from head + tail for the content hash
_AFP_WINDOW = 64 * 1024   # bytes of AUDIO hashed at each end, tag blocks skipped
_AFP_TAIL_PROBE = 256     # short file: bytes read from the end to spot a trailing tag


def _synchsafe(b: bytes) -> int:
    """The 7-bits-per-byte integer ID3v2 stores its tag size in."""
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _tag_offsets(head: bytes, tail: bytes) -> tuple[int, int]:
    """(tag bytes in front of the audio, tag bytes behind it).

    Covers what a tag editor actually writes: an ID3v2 header at the front, an
    ID3v1 block and/or an APEv2 tag at the back. Anything unrecognised counts as
    zero — that only leaves tag bytes inside the audio hash, which costs a missed
    re-attach, never a wrong one.
    """
    front = 0
    if head[:3] == b"ID3" and len(head) >= 10 and all(b < 0x80 for b in head[6:10]):
        front = 10 + _synchsafe(head[6:10])
        if head[5] & 0x10:      # a footer repeats the 10-byte header behind the tag
            front += 10
    back = 0
    if len(tail) >= 128 and tail[-128:-125] == b"TAG":
        back = 128
    start = len(tail) - back - 32
    ape = tail[start:start + 32] if start >= 0 else b""
    if ape[:8] == b"APETAGEX":
        back += int.from_bytes(ape[12:16], "little")        # items + footer
        if int.from_bytes(ape[20:24], "little") & 0x80000000:
            back += 32                                      # … plus the header
    return front, back


def _window(f, off: int, want: int, head: bytes, tail: bytes, tail_off: int) -> bytes:
    """`want` bytes of the file from `off`, out of a buffer we already hold if possible."""
    for buf, base in ((head, 0), (tail, tail_off)):
        if base <= off and off + want <= base + len(buf):
            return buf[off - base:off - base + want]
    f.seek(off)
    return f.read(want)


def _audio_fingerprint(f, size: int, head: bytes, tail: bytes, tail_off: int) -> str:
    """Fingerprint of the AUDIO alone — unchanged when only the tags are rewritten.

    Same idea as the content fingerprint (length + a window from each end), but
    measured from the first byte AFTER the ID3v2 header to the last byte before
    the trailing tags, so an mp3tag round-trip leaves it alone. `f` is the file
    the caller already has open; it is only read from again when a window falls
    outside the buffers (a cover-art tag bigger than the head sample).
    """
    front, back = _tag_offsets(head, tail)
    audio_len = max(0, size - front - back)
    want = min(_AFP_WINDOW, audio_len)
    h = hashlib.sha1()
    h.update(str(audio_len).encode())
    h.update(_window(f, front, want, head, tail, tail_off))
    h.update(_window(f, max(front, size - back - want), want, head, tail, tail_off))
    return f"{audio_len}_{h.hexdigest()[:20]}"


def _fingerprints(path: Path) -> tuple[str, str]:
    """(content fingerprint, audio fingerprint) of a music file, from one read.

    The content fingerprint is the cheap byte identity: file size + sha1 of a head
    & tail sample. Byte-identical copies (same song in several folders) share it, so
    their MFCC vector is analyzed + stored only ONCE, and different files virtually
    never collide (same size AND same first/last 256 KB). It is also the key to
    every analysed row — and a tag editor changes it, which is what the audio
    fingerprint beside it is for (see `AudioCache.reattach_retagged`).

    Read-only — opens the file 'rb'.
    """
    size = path.stat().st_size
    h = hashlib.sha1()
    h.update(str(size).encode())
    with path.open('rb') as f:
        head = f.read(_FP_SAMPLE)
        h.update(head)
        if size > _FP_SAMPLE * 2:
            f.seek(-_FP_SAMPLE, os.SEEK_END)
            tail = f.read(_FP_SAMPLE)
            tail_off = size - len(tail)
            h.update(tail)
        else:
            # Not part of the content hash — just enough of the end to see a
            # trailing ID3v1/APE tag on a short file (a cartwall jingle).
            tail_off = max(0, size - _AFP_TAIL_PROBE)
            f.seek(tail_off)
            tail = f.read(_AFP_TAIL_PROBE)
        fp = f"{size}_{h.hexdigest()[:20]}"
        afp = _audio_fingerprint(f, size, head, tail, tail_off)
    return fp, afp


# Tables keyed by the content fingerprint, with the columns that travel with it
# when a re-tagged file gets a new key. `scan_meta` is deliberately absent: it
# caches what the TAGS say, and after a tag edit re-reading them is the point.
_FP_TABLES = {
    "features": "bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov",
    "embeddings": "model, vec",
    "loudness": "lufs",
    "pd_highlights": "times, manual",
    "silences": "spans",
    "vocals": "vocal_share",
    "noise": "floor_db",
    "tag_edits": "rating, classes_ok, is_instrumental, comment_tags, custom",
}


# ── Shared application database (SQLite, normalized schema) ────────────────────
# One DB file holds everything. NORMALIZED (schema v2): paths live ONCE in `files`
# (id ↔ path), and every other table references that id instead of repeating the full
# Windows path string (paths were ~18 MB duplicated across 3-4 tables before). Metadata
# is stored as real COLUMNS (not a JSON blob) so the field names aren't re-stored on
# every one of ~110k rows (~12 MB of repeated JSON keys before).
#
#   files        (id, path UNIQUE)                         – canonical path registry
#   features     (fp, bpm, centroid, rms, mfcc)            – deduped by content fingerprint
#   fingerprints (file_id, mtime, fp)                      – path::mtime → fingerprint
#   audio_fps    (fp, afp)                                 – fingerprint → TAG-FREE audio hash
#   scan_meta    (ckey, <10 metadata columns>)            – competition lib, CONTENT-addressed
#   global_meta  (file_id, mtime, <10 metadata columns>)  – global repo (mtime-invalidated)
#
# scan_meta is keyed by `ckey = "{fingerprint}::{filename stem}"` (schema v3), NOT by path:
# the detected dance/title/bpm/year are a pure function of the file CONTENT plus its
# filename, so the same audio at a new path (or a renamed-back copy) reuses the cached
# ID3-derived metadata instead of re-reading tags — and it's stored once, not per path.
#
# Connections are THREAD-LOCAL: the loader QThread, the main thread and the
# AudioAnalyzer thread each get their own connection (sqlite3's default
# check_same_thread=True stays on). WAL mode + busy_timeout make concurrent
# access safe; schema creation/migrations run exactly once under a lock.
_DB_LOCAL = threading.local()
_DB_INIT_LOCK = threading.Lock()
_DB_INITIALIZED = False
_SCHEMA_VERSION = 3   # v3: scan_meta re-keyed from file_id → content fingerprint (+ stem)
# Bump when dance/BPM/metadata DETECTION logic changes, to invalidate the cached
# scan_meta/global_meta dance values (which carry no per-row version of their own).
#   v1 → genre tag now wins over the filename guess (fixes 'Ta' → Tango false match)
#   v2 → class tag now read from the STANDARD comment, skipping iTunes/UltraMixer
#        technical COMM frames that previously shadowed it (e.g. 'D;C;B;vocal_f')
#   v3 → is_instrumental now also set by a filename/title marker ('(Instr.)',
#        '(inst)'), not just the COMM tag
#   v4 → a slug filename (Store_Download_Name_29BPM) takes the spaced ID3 title
#   v5 → + the POPM star rating, and a Songs-DB class floor ('ab C' = C and up)
_DANCE_DETECT_VERSION = 5

# How quiet a stretch has to be before it counts as silence (ffmpeg
# silencedetect). −30 dB was a fade-out still playing to the floor — “Fare Thee
# Well” fades under it for twenty seconds — and every one of those reads as
# dead air the player cuts away. Real silence is down at the noise floor of a
# tape rip, so that is where the line sits. Stored spans note the threshold they
# were probed at (_invalidate_stale_silences); moving it re-probes the library.
SILENCE_NOISE_DB = -50

# Metadata columns shared by scan_meta + global_meta (order matters for row packing).
# `duration` (track length, whole seconds) and `tag_album` were appended later —
# `_migrate_meta_duration` / `_migrate_meta_album` ALTER them onto existing tables, so
# any newly appended column MUST stay at the end (ALTER always appends).
_META_COLS = ("title", "dance", "bpm", "year", "other_genre", "classes_ok",
              "is_instrumental", "is_xmas", "tag_title", "tag_artist", "duration",
              "tag_album", "comment_tags", "rating", "custom")

# SQL column declarations for the metadata columns above (kept in one place so the
# scan_meta / global_meta DDL and the v3 migration can't drift apart).
_META_COLS_SQL = (
    "title TEXT, dance TEXT, bpm INTEGER, year INTEGER, other_genre TEXT, "
    "classes_ok TEXT, is_instrumental INTEGER, is_xmas INTEGER, "
    "tag_title TEXT, tag_artist TEXT, duration INTEGER, tag_album TEXT, "
    "comment_tags TEXT, rating INTEGER, custom TEXT"
)


def _meta_to_row(d: dict) -> tuple:
    """Pack a metadata dict into a column tuple (lists→JSON text, bools→0/1)."""
    classes = d.get('classes_ok')
    markers = d.get('comment_tags')
    return (
        d.get('title'), d.get('dance'), d.get('bpm'), d.get('year'),
        d.get('other_genre'),
        json.dumps(classes, ensure_ascii=False) if classes is not None else None,
        1 if d.get('is_instrumental') else 0,
        1 if d.get('is_xmas') else 0,
        d.get('tag_title'), d.get('tag_artist'),
        d.get('duration') or 0,
        d.get('tag_album'),
        json.dumps(markers, ensure_ascii=False) if markers is not None else None,
        d.get('rating'),
        d.get('custom'),
    )


def _row_to_meta(row) -> dict:
    """Unpack a column tuple back into the metadata dict (exact original types)."""
    (title, dance, bpm, year, other_genre, classes_ok,
     is_instr, is_xmas, tag_title, tag_artist, duration, tag_album,
     comment_tags, rating, custom) = row
    return {
        'title': title, 'dance': dance, 'bpm': bpm, 'year': year,
        'other_genre': other_genre,
        'classes_ok': json.loads(classes_ok) if classes_ok else None,
        'is_instrumental': bool(is_instr),
        'is_xmas': bool(is_xmas),
        'tag_title': tag_title, 'tag_artist': tag_artist,
        'duration': duration or 0,   # NULL (pre-duration rows) → 0 = "unknown, re-probe"
        'tag_album': tag_album,
        # NULL → None ("this row predates the column"), '[]' → [] ("read, no
        # markers"). _make_entry heals the None rows one ID3 read at a time.
        'comment_tags': json.loads(comment_tags) if comment_tags else None,
        'rating': rating,   # 1–5 stars from POPM, None = unrated
        # The mapped frame's text (planner.custom_field); NULL = not read
        # under the current mapping yet, '' = read, the file has none.
        'custom': custom,
    }


def _file_id(path_str: str, create: bool = True) -> int | None:
    """Resolve (or create) the files.id for a path string."""
    conn = _db()
    row = conn.execute("SELECT id FROM files WHERE path = ?", (path_str,)).fetchone()
    if row:
        return row[0]
    if not create:
        return None
    conn.execute("INSERT OR IGNORE INTO files (path) VALUES (?)", (path_str,))
    return conn.execute("SELECT id FROM files WHERE path = ?", (path_str,)).fetchone()[0]


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # Statement by statement, not executescript: that COMMITs whatever
    # transaction is open first, and this runs inside the migration's one.
    script = (
        "CREATE TABLE IF NOT EXISTS files ("
        "  id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL);"
        "CREATE TABLE IF NOT EXISTS features ("
        "  fp TEXT PRIMARY KEY, bpm REAL, centroid REAL, rms REAL, mfcc BLOB,"
        "  mfcc_mean BLOB, mfcc_cov BLOB);"
        "CREATE TABLE IF NOT EXISTS fingerprints ("
        "  file_id INTEGER PRIMARY KEY REFERENCES files(id), mtime INTEGER, fp TEXT);"
        f"CREATE TABLE IF NOT EXISTS scan_meta ("
        f"  ckey TEXT PRIMARY KEY, {_META_COLS_SQL});"
        f"CREATE TABLE IF NOT EXISTS global_meta ("
        f"  file_id INTEGER PRIMARY KEY REFERENCES files(id), mtime INTEGER, {_META_COLS_SQL});"
        "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT);"
        # One row per learned playlist (an .m3u file OR a tournament folder), with
        # the match keys its lines derive. `sig` is the file's mtime+size, so an
        # untouched playlist is never re-read. See PlaylistIndexCache.
        "CREATE TABLE IF NOT EXISTS playlist_index ("
        "  root TEXT NOT NULL, pl_id TEXT NOT NULL, sig TEXT NOT NULL,"
        "  cls TEXT, mkeys TEXT NOT NULL, fkeys TEXT, skeys TEXT,"
        "  PRIMARY KEY (root, pl_id));"
        # EBU R128 integrated loudness, content-addressed like `features` (byte-identical
        # copies share one measurement). Filled by the GUI's ffmpeg loudness pass.
        "CREATE TABLE IF NOT EXISTS loudness (fp TEXT PRIMARY KEY, lufs REAL);"
        # Paso Doble highlight times, content-addressed too. `times` is a JSON
        # array [h1,h2,h3] in seconds; h1/h2 may be null (no clear candidate).
        # Filled by the GUI's 🐂 highlight pass / on-the-fly during playback.
        "CREATE TABLE IF NOT EXISTS pd_highlights ("
        "  fp TEXT PRIMARY KEY, times TEXT, manual INTEGER DEFAULT 0);"
        # Silent stretches inside a track, content-addressed too. `spans` is a
        # JSON array of [start, end] pairs in seconds (ffmpeg silencedetect).
        # Used to measure the REAL play length and to skip stillness in playback.
        "CREATE TABLE IF NOT EXISTS silences (fp TEXT PRIMARY KEY, spans TEXT);"
        # Vocal-stem energy share (0..1), content-addressed too. Measured by the
        # optional Demucs source separation (🎙️ Analyze vocals); a track whose
        # vocal stem carries almost no energy is instrumental (planner.vocals).
        "CREATE TABLE IF NOT EXISTS vocals (fp TEXT PRIMARY KEY, vocal_share REAL);"
        # Noise floor in dBFS, content-addressed too: the quietest moment a track
        # ever reaches (ffmpeg astats). A clean digital file gets down to its
        # lead-in silence, a tape or vinyl rip never gets below its own hiss —
        # that's the 🔇 Check-Music warning.
        "CREATE TABLE IF NOT EXISTS noise (fp TEXT PRIMARY KEY, floor_db REAL);"
        # Stars / classes / markers changed in the app's tag editor; they win over
        # the file's own tags (planner.tag_edits). NULL = the file's value.
        "CREATE TABLE IF NOT EXISTS tag_edits (fp TEXT PRIMARY KEY, rating INTEGER, "
        "  classes_ok TEXT, is_instrumental INTEGER, comment_tags TEXT, custom TEXT);"
        # The tag-independent audio fingerprint behind each content fingerprint,
        # written whenever a file is hashed. A tag editor rewrites the file and
        # with it `fp`, the key to every analysed row; this is what still matches,
        # so the analysis under the old key is copied onto the new one instead of
        # decoding the library again (AudioCache.reattach_retagged).
        "CREATE TABLE IF NOT EXISTS audio_fps (fp TEXT PRIMARY KEY, afp TEXT NOT NULL);"
        "CREATE INDEX IF NOT EXISTS idx_audio_fps_afp ON audio_fps(afp);"
    )
    for statement in script.split(";"):
        if statement.strip():
            conn.execute(statement)


def _migrate_meta_duration(conn: sqlite3.Connection) -> None:
    """Append the `duration` column to pre-existing scan_meta / global_meta tables.

    Older DBs predate track lengths; ALTER keeps the expensive cached metadata and
    leaves duration NULL — `_make_entry` then re-probes just the length (cheap mutagen
    header read) once per file and heals the row in place."""
    for table in ("scan_meta", "global_meta"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if cols and 'duration' not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN duration INTEGER")
            log.info("  ♻️  %s: added duration column (track lengths fill in lazily)", table)


def _migrate_pd_manual(conn: sqlite3.Connection) -> None:
    """Append the `manual` flag column to a pre-existing pd_highlights table.

    Manually learned Paso Doble highlights (set by the user at the playhead) are
    flagged so the 🐂 auto-detection never overwrites them."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(pd_highlights)").fetchall()]
    if cols and 'manual' not in cols:
        conn.execute("ALTER TABLE pd_highlights ADD COLUMN manual INTEGER DEFAULT 0")
        log.info("  ♻️  pd_highlights: added manual flag column")


def _migrate_playlist_index_finals(conn: sqlite3.Connection) -> None:
    """Append the `fkeys` / `skeys` columns to a pre-existing playlist_index table.

    Which of a playlist's keys were danced in its FINAL and in its SEMIFINAL came
    later than the index itself. The columns are left NULL here and the rows are
    dropped by the cache's own VERSION bump anyway — this only keeps the INSERT
    from failing on a table that predates them."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(playlist_index)").fetchall()]
    for col in ('fkeys', 'skeys'):
        if cols and col not in cols:
            conn.execute(f"ALTER TABLE playlist_index ADD COLUMN {col} TEXT")
            log.info("  ♻️  playlist_index: added %s column "
                     "(the late rounds are re-derived on the next start)", col)


def _migrate_meta_album(conn: sqlite3.Connection) -> None:
    """Append the `tag_album` column to pre-existing scan_meta / global_meta tables.

    Album (ID3 TALB) was added after duration; ALTER keeps the cached metadata and
    leaves tag_album NULL — `_make_entry` heals the row in place once it re-reads the
    file's tags. MUST run after `_migrate_meta_duration` so tag_album stays last."""
    for table in ("scan_meta", "global_meta"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if cols and 'tag_album' not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN tag_album TEXT")
            log.info("  ♻️  %s: added tag_album column (album names fill in lazily)", table)


def _migrate_meta_comment_tags(conn: sqlite3.Connection) -> None:
    """Append the `comment_tags` column to pre-existing scan_meta / global_meta.

    The free COMM markers (vocal_f, classic, eintanzen, …) were added after
    tag_album; ALTER keeps the cached metadata and leaves the column NULL, which
    reads back as "no markers". Those rows only heal when the file is re-read, so
    a full re-scan is what actually fills them in. MUST run after
    `_migrate_meta_album` so the column order matches _META_COLS."""
    for table in ("scan_meta", "global_meta"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if cols and 'comment_tags' not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN comment_tags TEXT")
            log.info("  ♻️  %s: added comment_tags column "
                     "(markers fill in on the next full scan)", table)


def _migrate_meta_rating(conn: sqlite3.Connection) -> None:
    """Append the `rating` column (POPM stars) to pre-existing scan_meta /
    global_meta. MUST run after `_migrate_meta_comment_tags` so the column order
    matches _META_COLS. The v5 detect bump re-reads every file, which fills it."""
    for table in ("scan_meta", "global_meta"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if cols and 'rating' not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN rating INTEGER")
            log.info("  ♻️  %s: added rating column", table)


def _migrate_custom(conn: sqlite3.Connection) -> None:
    """Append the `custom` column (planner.custom_field) to pre-existing
    scan_meta / global_meta — after `rating`, so the order matches _META_COLS —
    and to tag_edits. NULL in the meta tables is "not read yet": the scan
    reads the mapped frame the next time it looks at the file."""
    for table in ("scan_meta", "global_meta", "tag_edits"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if cols and 'custom' not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN custom TEXT")
            log.info("  ♻️  %s: added custom column", table)


def _migrate_scan_meta_v3(conn: sqlite3.Connection) -> None:
    """v2 → v3: re-key scan_meta from `file_id` to a content fingerprint + filename stem.

    The old normalized scan_meta was `(file_id, size, <meta>)`. We rebuild it as
    `(ckey, <meta>)` where ckey = "{fingerprint}::{stem}" so the metadata is reused
    by CONTENT (a relocated/renamed-back file no longer re-reads its ID3 tags). Rows
    whose file has no fingerprint yet are dropped — they're re-derived cheaply from the
    ID3 tags on the next scan. The expensive `features` table is never touched.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(scan_meta)").fetchall()]
    if not cols or 'ckey' in cols or 'file_id' not in cols:
        return   # fresh db (no table / already new schema) or an unexpected shape

    meta = ",".join(_META_COLS)
    rows = conn.execute(
        f"SELECT f.path, fp.fp, {meta} FROM scan_meta m "
        f"JOIN files f        ON f.id = m.file_id "
        f"JOIN fingerprints fp ON fp.file_id = m.file_id").fetchall()
    conn.execute("DROP TABLE scan_meta")
    conn.execute(f"CREATE TABLE scan_meta (ckey TEXT PRIMARY KEY, {_META_COLS_SQL})")
    placeholders = ",".join("?" * (1 + len(_META_COLS)))
    seen: set = set()
    for row in rows:
        ckey = f"{row[1]}::{Path(row[0]).stem}"
        if ckey in seen:
            continue
        seen.add(ckey)
        conn.execute(
            f"INSERT OR REPLACE INTO scan_meta (ckey, {meta}) VALUES ({placeholders})",
            (ckey, *row[2:]))
    log.info("  ♻️  scan_meta re-keyed to content fingerprint (schema v3): "
             "%s rows kept", f"{len(seen):,}")


def _migrate_features_gauss(conn: sqlite3.Connection) -> None:
    """Add the mfcc_mean / mfcc_cov columns to an existing `features` table (schema v9).

    The Gaussian timbre model (Mandel-Ellis) needs per-song MFCC mean + covariance.
    Existing rows get NULL columns; `AudioCache.get` then treats them as un-analyzed so
    `analyze_missing` recomputes the richer features in place. Cheap ALTER, no data loss.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(features)").fetchall()]
    if not cols:
        return   # fresh db – CREATE already includes the columns
    if 'mfcc_mean' not in cols:
        conn.execute("ALTER TABLE features ADD COLUMN mfcc_mean BLOB")
    if 'mfcc_cov' not in cols:
        conn.execute("ALTER TABLE features ADD COLUMN mfcc_cov BLOB")


def _invalidate_stale_silences(conn: sqlite3.Connection) -> None:
    """Drop silence spans probed at a different threshold.

    Like the dance detection above, `silences` rows carry no version of their
    own — and a span is not merely stale when the threshold moves, it is wrong:
    at −30 dB a fade-out reads as silence, so the track was cut where it was
    still playing. The next play (or the bulk probe) fills them in again."""
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'silence_noise_db'").fetchone()
    current = str(SILENCE_NOISE_DB)
    if row is not None and row[0] == current:
        return
    n = conn.execute("SELECT COUNT(*) FROM silences").fetchone()[0]
    conn.execute("DELETE FROM silences")
    if n:
        log.info("  ♻️  Silence threshold %s dB: cleared %s probed tracks "
                 "→ will re-probe on play", current, n)
    conn.execute(
        "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('silence_noise_db', ?)",
        (current,))


def _invalidate_stale_metadata(conn: sqlite3.Connection) -> None:
    """Drop cached scan_meta/global_meta dance values when detection logic changed.

    These tables store the detected dance/BPM/etc. with no per-row version, so when
    `_DANCE_DETECT_VERSION` is bumped we clear them once; the next scan re-reads the
    ID3 tags and re-applies the new logic. Audio features/fingerprints are untouched.
    """
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'dance_detect_version'").fetchone()
    current = str(_DANCE_DETECT_VERSION)
    if row is not None and row[0] == current:
        return
    # Version missing (pre-existing db) or changed → clear cached metadata so the
    # next scan re-detects dance. No-op on a fresh db (tables already empty).
    n = conn.execute("SELECT COUNT(*) FROM scan_meta").fetchone()[0]
    conn.execute("DELETE FROM scan_meta")
    conn.execute("DELETE FROM global_meta")
    if n:
        log.info("  ♻️  Dance-detection logic v%s: cleared %s cached metadata "
                 "rows → will re-read ID3 tags on next scan", current, n)
    conn.execute(
        "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('dance_detect_version', ?)",
        (current,))


def _read_and_drop_legacy(conn: sqlite3.Connection) -> dict | None:
    """If the DB still has the old (key/JSON) tables, read them out and drop them.

    Returns the raw legacy rows for re-insertion into the normalized tables, or None
    when there is nothing to migrate (fresh DB or already normalized).
    """
    if conn.execute("PRAGMA user_version").fetchone()[0] >= _SCHEMA_VERSION:
        return None

    def cols(table: str) -> list:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]

    fp_legacy = 'key'  in cols('fingerprints')   # old: (key=path::mtime, fp)
    sm_legacy = 'data' in cols('scan_meta')      # old: (key=path::size, data=JSON)
    gm_legacy = 'data' in cols('global_meta')    # old: (path, mtime, data=JSON)
    if not (fp_legacy or sm_legacy or gm_legacy):
        return None

    legacy: dict = {}
    if fp_legacy:
        legacy['fp'] = conn.execute("SELECT key, fp FROM fingerprints").fetchall()
        conn.execute("DROP TABLE fingerprints")
    if sm_legacy:
        legacy['sm'] = conn.execute("SELECT key, data FROM scan_meta").fetchall()
        conn.execute("DROP TABLE scan_meta")
    if gm_legacy:
        legacy['gm'] = conn.execute("SELECT path, mtime, data FROM global_meta").fetchall()
        conn.execute("DROP TABLE global_meta")
    return legacy


def _insert_legacy(conn: sqlite3.Connection, legacy: dict) -> None:
    """Re-insert legacy rows into the normalized tables, registering paths in `files`."""
    ids: dict[str, int] = {}

    def gid(path: str) -> int:
        rid = ids.get(path)
        if rid is None:
            conn.execute("INSERT OR IGNORE INTO files (path) VALUES (?)", (path,))
            rid = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()[0]
            ids[path] = rid
        return rid

    n_fp = n_sm = n_gm = 0
    for key, fp in legacy.get('fp', []):
        path, _, mt = key.rpartition('::')
        path = path or key
        conn.execute("INSERT OR REPLACE INTO fingerprints (file_id, mtime, fp) VALUES (?,?,?)",
                     (gid(path), int(mt) if mt.isdigit() else 0, fp))
        n_fp += 1
    placeholders = ",".join("?" * (2 + len(_META_COLS)))   # file_id, mtime, + 10 cols
    # NOTE: legacy scan_meta (sm) is intentionally NOT migrated — the new schema is keyed
    # by content fingerprint (unavailable here without re-hashing every file), and the
    # ID3-derived metadata is cheap to rebuild on the next scan. global_meta still imports.
    for path, mtime, data in legacy.get('gm', []):
        try:
            d = json.loads(data)   # legacy global_meta.data held the flat entry dict
        except Exception:
            continue
        conn.execute(
            f"INSERT OR REPLACE INTO global_meta (file_id, mtime, {','.join(_META_COLS)}) "
            f"VALUES ({placeholders})",
            (gid(path), mtime or 0, *_meta_to_row(d)))
        n_gm += 1
    log.info("  ♻️  DB normalized to schema v%s: "
             "%s unique paths · %s fingerprints · "
             "%s scan_meta · %s global_meta → %s",
             _SCHEMA_VERSION, f"{len(ids):,}", f"{n_fp:,}",
             f"{n_sm:,}", f"{n_gm:,}", AUDIO_DB_FILE.name)


def _db() -> sqlite3.Connection:
    """Thread-local connection to the shared DB; first caller runs the migrations."""
    conn = getattr(_DB_LOCAL, 'conn', None)
    if conn is not None:
        return conn
    global _DB_INITIALIZED
    AUDIO_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None → autocommit: every write commits immediately instead of
    # leaving a deferred transaction open on this thread's connection. The caches are
    # shared across threads (main + loader + analyzer) but each thread has its OWN
    # connection; a thread that wrote (e.g. the main thread fingerprinting a track on
    # playback) used to sit on an uncommitted write transaction forever — never paired
    # with a save() on that thread — holding the write lock and making the loudness /
    # audio worker's INSERTs fail with 'database is locked'. Autocommit + WAL fixes it;
    # the explicit commit()/save() calls become harmless no-ops, and bulk executemany
    # in the one-time migrations still commits in a single batch.
    conn = sqlite3.connect(str(AUDIO_DB_FILE), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 10000")   # wait instead of 'database is locked'
    # NORMAL (not FULL) so autocommit doesn't fsync on every write — safe under WAL
    # (only the last commit can be lost on a power cut, never corruption); keeps the
    # per-write commits from the autocommit mode above cheap during a full scan.
    conn.execute("PRAGMA synchronous=NORMAL")
    _DB_LOCAL.conn = conn                       # set first: _file_id/helpers call _db()
    with _DB_INIT_LOCK:
        if not _DB_INITIALIZED:
            # One transaction for all of it: the legacy tables are DROPPED before
            # their rows go back in, and scan_meta is dropped before it is re-filled.
            # Committed step by step, a crash in between lost those rows for good.
            conn.execute("BEGIN")
            try:
                legacy = _read_and_drop_legacy(conn)    # pull out old key/JSON tables if present
                _ensure_schema(conn)                    # create normalized tables (no-op if exist)
                _migrate_meta_duration(conn)            # add duration col BEFORE inserts/migrations
                _migrate_meta_album(conn)               # add tag_album col (stays last, after duration)
                _migrate_meta_comment_tags(conn)        # add comment_tags col (after tag_album)
                _migrate_meta_rating(conn)              # add rating col (after comment_tags)
                _migrate_custom(conn)                   # add custom col (after rating), tag_edits too
                _migrate_pd_manual(conn)                # add manual flag to pd_highlights
                _migrate_playlist_index_finals(conn)    # add fkeys col to playlist_index
                if legacy:
                    _insert_legacy(conn, legacy)
                _migrate_scan_meta_v3(conn)             # v2→v3: scan_meta → content-addressed
                _migrate_features_gauss(conn)           # v9: add mfcc_mean/mfcc_cov columns
                conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                _invalidate_stale_metadata(conn)        # re-detect dance if logic version bumped
                _invalidate_stale_silences(conn)        # re-probe if the silence threshold moved
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
            _DB_INITIALIZED = True
    return conn


# Why audio analysis cannot run here. A library fails file by file for one single
# reason — no librosa, or nothing on this machine that can decode an MP3 — so 3638
# identical tracebacks in the log say no more than one probe up front does.
PROBE_NO_LIBROSA = "no_librosa"
PROBE_NO_BACKEND = "no_backend"
PROBE_FAILED = "probe_failed"


_quiet_lock = threading.Lock()
_quiet_depth = 0
_quiet_saved: tuple[int, int] | None = None


def _sync_win32_stderr() -> None:
    """Point the Win32 STD_ERROR_HANDLE at whatever fd 2 now holds.

    audioread's ffmpeg subprocess inherits that handle, not the CRT fd 2. The CRT
    re-points it on `dup2(…, 2)` only in console processes, so it is set here
    explicitly — and always to fd 2's live handle: a handle saved before `dup2`
    is closed by it, and restoring that one leaves every later child a dead or
    recycled stderr.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        import msvcrt
        ctypes.windll.kernel32.SetStdHandle(-12, msvcrt.get_osfhandle(2))   # STD_ERROR_HANDLE
    except Exception:
        pass


def _mute_stderr() -> tuple[int, int] | None:
    """Point fd 2 and the Win32 STD_ERROR_HANDLE at the null device.

    Returns what `_unmute_stderr` needs to put them back, or None when there is
    no fd 2 to redirect.
    """
    try:
        saved_fd = os.dup(2)
    except OSError:
        return None
    null_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null_fd, 2)                  # CRT stderr (mpg123 / libav)
    _sync_win32_stderr()
    return saved_fd, null_fd


def _unmute_stderr(saved: tuple[int, int]) -> None:
    saved_fd, null_fd = saved
    os.dup2(saved_fd, 2)
    _sync_win32_stderr()
    os.close(saved_fd)
    os.close(null_fd)


@contextlib.contextmanager
def quiet_native_stderr():
    """Silence the decoders' C-level stderr (mpg123 / ffmpeg / libsndfile chatter).

    Python's `sys.stderr` can't catch what is written below Python, so fd 2 itself
    is pointed at the null device. That is process-wide state, and the analysis
    pass decodes on several threads at once: were each decode to save and restore
    it on its own, the second one in would save the null device and put it back
    last, muting stderr for the rest of the session. So the mute is shared — the
    first decode in redirects, the last one out restores.
    """
    global _quiet_depth, _quiet_saved
    with _quiet_lock:
        if _quiet_depth == 0:
            _quiet_saved = _mute_stderr()
        _quiet_depth += 1
    try:
        yield
    finally:
        with _quiet_lock:
            _quiet_depth -= 1
            if _quiet_depth == 0 and _quiet_saved is not None:
                _unmute_stderr(_quiet_saved)
                _quiet_saved = None


def probe_decode_backend(path: Path) -> str | None:
    """Decode 2 s of `path`: None when that works, else a `PROBE_*` reason.

    librosa reads MP3 through soundfile when libsndfile is new enough, and falls
    back to audioread — which shells out to `ffmpeg` BY NAME, so a copy bundled
    next to the app but absent from PATH does not count there. Either way the
    verdict holds for the whole library, and it is worth having before the user
    commits to an hour of analysis.
    """
    if not HAS_LIBROSA:
        return PROBE_NO_LIBROSA
    # Same stderr muting as _analyze_file: a decoder that fails is a loud one.
    exc = None
    with quiet_native_stderr():
        try:
            librosa.load(str(path), sr=11025, offset=0.0, duration=2.0, mono=True)
        except Exception as ex:
            exc = ex
    if exc is None:
        return None
    log.error("🔬 Audio decode probe failed\n"
              "file: %s\n"
              "error: %s: %s", path, type(exc).__name__, exc)
    if "NoBackendError" in type(exc).__qualname__ or "backend" in str(exc).lower():
        return PROBE_NO_BACKEND
    return PROBE_FAILED


def _release_free_heap() -> None:
    """Hand already-freed heap pages back to the operating system.

    Analysing one file allocates a decoded 60 s window plus a stack of feature
    matrices and frees them again. Freeing returns them to the *allocator*, not
    to the OS: glibc and macOS' magazine malloc both keep the emptied pages
    mapped for reuse, and over tens of thousands of files that reservation is
    what the user sees as the process eating all the memory. These two calls
    release it. No Windows equivalent is needed — its heap decommits on free.
    """
    try:
        import ctypes
        if sys.platform == 'darwin':
            ctypes.CDLL(None).malloc_zone_pressure_relief(None, 0)
        elif sys.platform.startswith('linux'):
            ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass    # best effort: a missing symbol only costs us the release


# ── Audio Feature Cache ────────────────────────────────────────────────────────
class AudioCache:
    """Content-addressed MFCC feature store backed by SQLite.

    SQLite (not JSON) because the global repo holds ~50k files: a JSON store would be
    ~100 MB and every periodic save rewrote the WHOLE file (O(n²) I/O over a build).
    SQLite gives incremental keyed writes — `put` is one INSERT OR REPLACE, `save` is a
    cheap commit — and the float32-packed MFCC blobs cut the on-disk size ~8×.

    Stored in the shared normalized DB: `features` (content fingerprint → vector, deduped)
    and `fingerprints` (file_id + mtime → fingerprint, hashed once). An in-memory mirror
    (`_data`/`_fp`, the latter keyed by 'path::mtime') keeps similarity scoring fast; SQLite
    is the durable, incrementally-written backing store.
    """
    CACHE_VERSION = 9   # v9: + per-song Gaussian (mfcc_mean/cov) & middle-of-track window

    # A first run over a big repo analyses tens of thousands of files. As one
    # uninterrupted loop that is where memory goes wrong: a 50k-file run on macOS
    # climbed to ~80 GB and filled the disk with swap. So the loop runs in steps —
    # after every BATCH_FILES files the results are committed and the memory those
    # files used is released (see `_finish_batch`), which caps the growth at one
    # step's worth instead of the whole library's.
    BATCH_FILES = 200
    BIG_LIBRARY = 5000   # from here the step plan is worth telling the user about

    def __init__(self):
        self._data: dict[str, dict] = {}   # content fingerprint → feature dict (deduped)
        self._fp:   dict[str, str]  = {}   # 'path::mtime' → content fingerprint (hash once)
        # path → its newest 'path::mtime' key: what `recorded_fingerprint` reads
        # without a stat.
        self._path_key: dict[str, str] = {}
        self._lufs: dict[str, float] = {}  # content fingerprint → EBU R128 integrated LUFS
        self._pd_hl: dict[str, list] = {}  # content fingerprint → PD highlight times [h1,h2,h3]
        self._pd_hl_manual: set = set()    # fingerprints whose highlights were learned manually
        self._silences: dict[str, list] = {}  # content fingerprint → silence spans [[start, end], …]
        self._vocal_share: dict[str, float] = {}  # content fingerprint → Demucs vocal-stem share
        self._noise: dict[str, float] = {}  # content fingerprint → noise floor in dBFS
        # Audio (tag-free) fingerprint of the files actually hashed THIS session —
        # the only ones a re-tag can be detected for, see `reattach_retagged`.
        self._afp: dict[str, str] = {}
        self._dirty = False
        self._load()

    @staticmethod
    def _pack_mfcc(vec) -> bytes:
        """Pack a float sequence (list or ndarray) into a float32 blob."""
        if HAS_NUMPY:
            return np.asarray(vec, dtype=np.float32).tobytes()
        return array('f', vec).tobytes()

    @staticmethod
    def _unpack_mfcc(blob: bytes):
        """Unpack a float32 blob into a numpy array (read-only view, zero-copy).

        numpy arrays instead of Python float lists keep the in-memory mirror
        ~10× smaller (4 bytes/value vs boxed floats) — with ~50k tracks the
        difference is hundreds of MB. Falls back to a list without numpy.
        """
        if HAS_NUMPY:
            return np.frombuffer(blob, dtype=np.float32)
        a = array('f')
        a.frombytes(blob)
        return list(a)

    def _feat_dict(self, row) -> dict:
        """One `features` row (without its fp) as the in-memory feature dict."""
        bpm, centroid, rms, blob, mean_blob, cov_blob = row
        return {
            'bpm': bpm, 'centroid': centroid, 'rms': rms,
            'mfcc': self._unpack_mfcc(blob),
            'mfcc_mean': self._unpack_mfcc(mean_blob) if mean_blob else None,
            'mfcc_cov':  self._unpack_mfcc(cov_blob)  if cov_blob  else None,
        }

    def _load(self) -> None:
        conn = _db()
        rows = conn.execute(
            "SELECT fp, bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov FROM features"
        ).fetchall()
        for fp, *cols in rows:
            self._data[fp] = self._feat_dict(cols)
        for path, mtime, fp in conn.execute(
                "SELECT f.path, fp.mtime, fp.fp FROM fingerprints fp "
                "JOIN files f ON f.id = fp.file_id").fetchall():
            self._fp[f"{path}::{mtime}"] = fp
        self._lufs = dict(conn.execute("SELECT fp, lufs FROM loudness").fetchall())
        for fp, times, manual in conn.execute(
                "SELECT fp, times, manual FROM pd_highlights").fetchall():
            try:
                self._pd_hl[fp] = json.loads(times)
            except (TypeError, ValueError):
                continue
            if manual:
                self._pd_hl_manual.add(fp)
        for fp, spans in conn.execute("SELECT fp, spans FROM silences").fetchall():
            try:
                self._silences[fp] = json.loads(spans)
            except (TypeError, ValueError):
                continue
        self._vocal_share = dict(conn.execute("SELECT fp, vocal_share FROM vocals").fetchall())
        self._noise = dict(conn.execute("SELECT fp, floor_db FROM noise").fetchall())
        if not self._data and CACHE_FILE.exists():
            self._migrate_json()   # one-time import of the legacy JSON cache
        newest: dict[str, int] = {}
        for key in self._fp:
            path, _, mt = key.rpartition('::')
            mtime = int(mt) if mt.lstrip('-').isdigit() else 0
            if path and mtime >= newest.get(path, mtime):
                newest[path] = mtime
                self._path_key[path] = key

    def _migrate_json(self) -> None:
        """One-time import of the legacy JSON cache (v5 path::mtime or v6 content-addressed)."""
        try:
            payload = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        except Exception as exc:
            log.warning("⚠️ Legacy audio cache %s unreadable – skipping migration: %s",
                        CACHE_FILE.name, exc)
            return
        if not isinstance(payload, dict):
            return
        ver = payload.get('version')
        entries = payload.get('entries', {})
        kept = dropped = dups = 0
        if ver == 6:
            self._data = dict(entries)
            self._fp   = dict(payload.get('fingerprints', {}))
            kept = len(self._data)
        elif ver == 5:
            # Re-key old path::mtime entries by content fingerprint, collapsing dups.
            for key, feat in entries.items():
                path_str = key.rpartition('::')[0] or key
                p = Path(path_str)
                try:
                    fp = _fingerprints(p)[0]
                except Exception:
                    dropped += 1
                    continue
                self._fp[self._key(p)] = fp
                if fp in self._data:
                    dups += 1
                else:
                    self._data[fp] = feat
                    kept += 1
        else:
            return
        # Persist the imported data into SQLite.
        conn = _db()
        conn.executemany(
            "INSERT OR REPLACE INTO features (fp, bpm, centroid, rms, mfcc) VALUES (?,?,?,?,?)",
            [(fp, d['bpm'], d['centroid'], d['rms'], self._pack_mfcc(d['mfcc']))
             for fp, d in self._data.items()],
        )
        for key, fp in self._fp.items():
            path, _, mt = key.rpartition('::')
            conn.execute(
                "INSERT OR REPLACE INTO fingerprints (file_id, mtime, fp) VALUES (?,?,?)",
                (_file_id(path or key), int(mt) if mt.isdigit() else 0, fp))
        conn.commit()
        try:
            CACHE_FILE.rename(CACHE_FILE.with_suffix('.json.bak'))
        except OSError:
            pass
        log.info("  ♻️  Audio cache migrated JSON v%s → SQLite v%s: "
                 "%s unique vectors, %s duplicates merged, "
                 "%s missing files dropped → %s",
                 ver, self.CACHE_VERSION, kept, dups, dropped, AUDIO_DB_FILE.name)

    def save(self) -> None:
        if self._dirty:
            _db().commit()
            self._dirty = False

    @staticmethod
    def _key(path: Path) -> str:
        try:
            mtime = int(path.stat().st_mtime)
        except OSError:
            mtime = 0
        return f"{path}::{mtime}"

    def fingerprint(self, path: Path) -> str | None:
        """Content fingerprint for a file, hashed once per (path, mtime) then cached."""
        k = self._key(path)
        fp = self._fp.get(k)
        if fp is not None:
            self._path_key[str(path)] = k
            return fp
        try:
            fp, afp = _fingerprints(path)
        except OSError:
            return None
        self._fp[k] = fp
        self._path_key[str(path)] = k
        self._afp[fp] = afp
        path, _, mt = k.rpartition('::')
        conn = _db()
        conn.execute(
            "INSERT OR REPLACE INTO fingerprints (file_id, mtime, fp) VALUES (?,?,?)",
            (_file_id(path or k), int(mt) if mt.isdigit() else 0, fp))
        conn.execute("INSERT OR REPLACE INTO audio_fps (fp, afp) VALUES (?,?)", (fp, afp))
        self._dirty = True
        if fp not in self._data:
            # Freshly hashed and nothing analysed under this key: either a new file,
            # or one whose tags were edited since we last saw it — check.
            self.reattach_retagged(fp)
        return fp

    def reattach_retagged(self, fp: str) -> list[str]:
        """Re-key cached analysis onto `fp` after a tag editor rewrote the file.

        mp3tag & co. rewrite the file in place, so its content fingerprint — the key
        to every analysed row — changes while the music itself does not, and a whole
        library can lose its features, loudness and embeddings over an evening of
        tidying tags. The audio fingerprint ignores the tag blocks, so the rows under
        the file's previous key are found and copied onto the new one.

        Only works for a file hashed in THIS session (the audio fingerprint is a
        by-product of that read) and only when the OLD key's audio fingerprint is on
        record — which is what `ensure_audio_fp` is for. Returns the tables copied.
        """
        afp = self._afp.get(fp)
        if not afp:
            return []
        conn = _db()
        old = [r[0] for r in conn.execute(
            "SELECT fp FROM audio_fps WHERE afp = ? AND fp <> ?", (afp, fp)).fetchall()]
        if not old:
            return []
        copied = []
        for table, cols in _FP_TABLES.items():
            for prev in old:
                try:
                    cur = conn.execute(
                        f"INSERT OR IGNORE INTO {table} (fp, {cols}) "
                        f"SELECT ?, {cols} FROM {table} WHERE fp = ?", (fp, prev))
                except sqlite3.OperationalError:
                    break     # table not created yet (embeddings before their first use)
                if cur.rowcount:
                    copied.append(table)
                    break
        if not copied:
            return []
        self._refresh_fp_mirrors(fp)
        self._dirty = True
        log.info("🔗 Tags edited, cached analysis kept\n"
                 "new key: %s\n"
                 "old key: %s\n"
                 "reused: %s", fp, old[0], ", ".join(copied))
        return copied

    def _refresh_fp_mirrors(self, fp: str) -> None:
        """Re-read the in-memory mirrors for one fingerprint after a re-key."""
        conn = _db()
        row = conn.execute(
            "SELECT bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov FROM features "
            "WHERE fp = ?", (fp,)).fetchone()
        if row:
            self._data[fp] = self._feat_dict(row)
        for table, col, mirror in (("loudness", "lufs", self._lufs),
                                   ("vocals", "vocal_share", self._vocal_share),
                                   ("noise", "floor_db", self._noise)):
            r = conn.execute(f"SELECT {col} FROM {table} WHERE fp = ?", (fp,)).fetchone()
            if r is not None and r[0] is not None:
                mirror[fp] = r[0]
        for table, col, mirror in (("silences", "spans", self._silences),
                                   ("pd_highlights", "times", self._pd_hl)):
            r = conn.execute(f"SELECT {col} FROM {table} WHERE fp = ?", (fp,)).fetchone()
            if r and r[0]:
                try:
                    mirror[fp] = json.loads(r[0])
                except (TypeError, ValueError):
                    continue
        r = conn.execute("SELECT manual FROM pd_highlights WHERE fp = ?", (fp,)).fetchone()
        if r and r[0]:
            self._pd_hl_manual.add(fp)

    def ensure_audio_fp(self, path: Path) -> bool:
        """Put the file's tag-free audio fingerprint on record if it isn't already.

        Insurance against a LATER tag edit: what a re-tagged file gets matched
        against is the fingerprint of the audio as it is NOW, and once the editor has
        written, that number can never be recovered. Files hashed before this table
        existed therefore need one pass — two ~64 KB reads each, no decoding.
        Returns True when a fingerprint was written.
        """
        fp = self.fingerprint(path)
        if fp is None or fp in self._afp:
            return False
        if _db().execute("SELECT 1 FROM audio_fps WHERE fp = ?", (fp,)).fetchone():
            return False
        try:
            again, afp = _fingerprints(path)
        except OSError:
            return False
        if again != fp:
            return False    # written to while we read it; the next hash picks it up
        self._afp[fp] = afp
        _db().execute("INSERT OR REPLACE INTO audio_fps (fp, afp) VALUES (?,?)", (fp, afp))
        self._dirty = True
        return True

    def audio_fingerprint(self, path: Path) -> str | None:
        """The file's tag-free audio fingerprint — the same for two copies of one
        recording even when only one of them had its tags edited.

        Taken from this session's hashes, else from `audio_fps`, else read off the
        file once and put on record (`ensure_audio_fp`). None when unreadable.
        """
        fp = self.fingerprint(path)
        if fp is None:
            return None
        afp = self._afp.get(fp)
        if afp:
            return afp
        row = _db().execute("SELECT afp FROM audio_fps WHERE fp = ?", (fp,)).fetchone()
        if row:
            return row[0]
        self.ensure_audio_fp(path)
        return self._afp.get(fp)

    def known_fingerprint(self, path: Path) -> str | None:
        """Fingerprint resolved ONLY from the in-memory mirror — never reads the file.

        Returns None for files not fingerprinted yet (so coverage counts stay cheap:
        no disk I/O when summarising which tracks are indexed for which model).
        """
        return self._fp.get(self._key(path))

    def recorded_fingerprint(self, path) -> str | None:
        """The fingerprint last recorded for this path — never touches the disk,
        not even a stat.

        For lookups that run over whole decks or the whole library on every
        edit, where one stat per track adds up (and a sleeping USB disk makes
        each one a wait). The price: a file edited since it was last
        fingerprinted still answers with its old fingerprint until the next
        `fingerprint()` call sees the new mtime. None = never fingerprinted.
        """
        k = self._path_key.get(str(path))
        return self._fp.get(k) if k else None

    def audio_fp_keys(self) -> set:
        """The content fingerprints that already have an audio fingerprint on record.

        One query, so a backfill pass can skip in advance every file it would have
        nothing to do for (`ensure_audio_fp` would still have to read each one).
        """
        return {r[0] for r in _db().execute("SELECT fp FROM audio_fps").fetchall()}

    def coverage_counts(self, paths, audio_fps: set | None = None) -> dict[str, int]:
        """How many of `paths` have an audio fingerprint / loudness / silence /
        PD-highlight result.

        Resolved from the in-memory mirrors through `known_fingerprint`, so a
        coverage summary costs no disk I/O even over the whole repository —
        files never fingerprinted simply count as not analyzed, which is what
        they are. The one exception is the audio-fingerprint set, which has no
        mirror: pass `audio_fps` from `audio_fp_keys()` when several calls share
        one summary, and one query fetches it otherwise.
        """
        if audio_fps is None:
            audio_fps = self.audio_fp_keys()
        out = {"audiofp": 0, "loudness": 0, "silences": 0, "pd": 0}
        for p in paths:
            fp = self.known_fingerprint(p)
            if not fp:
                continue
            if fp in audio_fps:
                out["audiofp"] += 1
            if fp in self._lufs:
                out["loudness"] += 1
            if fp in self._silences:
                out["silences"] += 1
            if fp in self._pd_hl:
                out["pd"] += 1
        return out

    # ── EBU R128 loudness (content-addressed, measured externally via ffmpeg) ──

    def get_lufs(self, path: Path, touch_disk: bool = True) -> float | None:
        """Integrated loudness (LUFS) of a track, or None when not measured yet.
        `touch_disk=False` goes by `recorded_fingerprint` only — no stat, no hash."""
        fp = self.fingerprint(path) if touch_disk else self.recorded_fingerprint(path)
        if fp is None:
            return None
        return self._lufs.get(fp)

    def put_lufs(self, path: Path, lufs: float) -> None:
        fp = self.fingerprint(path)
        if fp is None:
            return
        self._lufs[fp] = float(lufs)
        _db().execute("INSERT OR REPLACE INTO loudness (fp, lufs) VALUES (?,?)",
                      (fp, float(lufs)))
        self._dirty = True

    def lufs_count(self) -> int:
        """How many tracks have a measured loudness (gates the equalize option)."""
        return len(self._lufs)

    # ── Paso Doble highlights (content-addressed, detected via librosa) ──

    def get_pd_highlights(self, path: Path) -> list | None:
        """Stored highlight times [h1,h2,h3] of a Paso Doble (h1/h2 may be
        None), or None when the track was never analyzed."""
        fp = self.fingerprint(path)
        if fp is None:
            return None
        return self._pd_hl.get(fp)

    def put_pd_highlights(self, path: Path, times: list, manual: bool = False) -> None:
        """Store highlight times. `manual=True` flags a user-learned highlight;
        auto-detection (`manual=False`) NEVER overwrites a manual one."""
        fp = self.fingerprint(path)
        if fp is None:
            return
        if not manual and fp in self._pd_hl_manual:
            return   # protect a manually learned highlight from auto-detection
        self._pd_hl[fp] = list(times)
        if manual:
            self._pd_hl_manual.add(fp)
        _db().execute(
            "INSERT OR REPLACE INTO pd_highlights (fp, times, manual) VALUES (?,?,?)",
            (fp, json.dumps(list(times)), 1 if manual else 0))
        self._dirty = True

    def clear_pd_highlights(self, path: Path) -> None:
        """Forget a track's highlights (manual or auto) so it can be re-learned
        or re-detected."""
        fp = self.fingerprint(path)
        if fp is None:
            return
        self._pd_hl.pop(fp, None)
        self._pd_hl_manual.discard(fp)
        _db().execute("DELETE FROM pd_highlights WHERE fp = ?", (fp,))
        self._dirty = True

    def is_pd_manual(self, path: Path) -> bool:
        """True when this track's highlights were learned manually."""
        fp = self.fingerprint(path)
        return fp is not None and fp in self._pd_hl_manual

    def export_manual_pd(self) -> list[dict]:
        """The Paso Doble highlights set by hand — the one correction no
        detection gets back — for carrying to another PC (`import_manual_pd`).
        One dict per track: content fingerprint, tag-free audio fingerprint (so a
        re-tagged copy still finds its marks), a file name to read, the times."""
        rows = _db().execute(
            "SELECT h.fp, h.times, a.afp, "
            "  (SELECT f.path FROM fingerprints p JOIN files f ON f.id = p.file_id "
            "   WHERE p.fp = h.fp LIMIT 1) "
            "FROM pd_highlights h LEFT JOIN audio_fps a ON a.fp = h.fp "
            "WHERE h.manual = 1 ORDER BY h.fp").fetchall()
        out = []
        for fp, times, afp, path in rows:
            try:
                times = json.loads(times)
            except (TypeError, ValueError):
                continue
            out.append({"fp": fp, "afp": afp, "file": Path(path).name if path else "",
                        "times": times})
        return out

    def import_manual_pd(self, marks: list[dict]) -> tuple[int, int]:
        """Store exported manual highlights as manual here, replacing what this
        PC had for those tracks. A mark also lands on every local copy with the
        same audio (a re-tagged file). Returns (marks imported, of them the ones
        whose track this PC already knows)."""
        conn = _db()
        known = {fp for (fp,) in conn.execute("SELECT DISTINCT fp FROM fingerprints")}
        n = hits = 0
        for m in marks:
            fp, times, afp = m.get("fp"), m.get("times"), m.get("afp")
            if not fp or not isinstance(times, list):
                continue
            targets = {fp}
            if afp:
                conn.execute("INSERT OR IGNORE INTO audio_fps (fp, afp) VALUES (?,?)",
                             (fp, afp))
                targets.update(r[0] for r in conn.execute(
                    "SELECT fp FROM audio_fps WHERE afp = ?", (afp,)))
            for t in targets:
                self._pd_hl[t] = list(times)
                self._pd_hl_manual.add(t)
                conn.execute(
                    "INSERT OR REPLACE INTO pd_highlights (fp, times, manual) "
                    "VALUES (?,?,1)", (t, json.dumps(list(times))))
            n += 1
            hits += bool(targets & known)
        self._dirty = True
        return n, hits

    def pd_highlight_count(self) -> int:
        """How many tracks have detected Paso Doble highlights."""
        return len(self._pd_hl)

    # ── Silence spans (content-addressed, detected via ffmpeg silencedetect) ──

    def get_silences(self, path: Path, touch_disk: bool = True) -> list | None:
        """Stored silence spans [[start, end], …] of a track (may be empty —
        no silence found), or None when the track was never probed.
        `touch_disk=False` goes by `recorded_fingerprint` only — no stat, no hash."""
        fp = self.fingerprint(path) if touch_disk else self.recorded_fingerprint(path)
        if fp is None:
            return None
        return self._silences.get(fp)

    def put_silences(self, path: Path, spans: list) -> None:
        fp = self.fingerprint(path)
        if fp is None:
            return
        spans = [list(s) for s in spans]
        self._silences[fp] = spans
        _db().execute("INSERT OR REPLACE INTO silences (fp, spans) VALUES (?,?)",
                      (fp, json.dumps(spans)))
        self._dirty = True

    # ── Vocal-stem share (content-addressed, measured via optional Demucs) ──

    def get_vocal_share(self, path: Path) -> float | None:
        """Measured vocal-stem energy share (0..1) of a track, or None when
        Demucs never analyzed it."""
        fp = self.fingerprint(path)
        if fp is None:
            return None
        return self._vocal_share.get(fp)

    def put_vocal_share(self, path: Path, share: float) -> None:
        fp = self.fingerprint(path)
        if fp is None:
            return
        self._vocal_share[fp] = float(share)
        _db().execute("INSERT OR REPLACE INTO vocals (fp, vocal_share) VALUES (?,?)",
                      (fp, float(share)))
        self._dirty = True

    def vocal_share_count(self) -> int:
        """How many tracks have a Demucs-measured vocal share."""
        return len(self._vocal_share)

    # ── Noise floor (content-addressed, measured via ffmpeg astats) ──────────

    def get_noise_floor(self, path: Path, touch_disk: bool = True) -> float | None:
        """Stored noise floor of a track in dBFS (−inf when it reaches true
        digital silence), or None when it was never probed.
        `touch_disk=False` goes by `recorded_fingerprint` only — no stat, no hash."""
        fp = self.fingerprint(path) if touch_disk else self.recorded_fingerprint(path)
        if fp is None:
            return None
        return self._noise.get(fp)

    def put_noise_floor(self, path: Path, floor_db: float) -> None:
        fp = self.fingerprint(path)
        if fp is None:
            return
        self._noise[fp] = float(floor_db)
        _db().execute("INSERT OR REPLACE INTO noise (fp, floor_db) VALUES (?,?)",
                      (fp, float(floor_db)))
        self._dirty = True

    def get(self, path: Path, hash_if_missing: bool = True) -> AudioFeatures | None:
        """Return cached features for a file via its content fingerprint.

        hash_if_missing=False resolves only from already-known fingerprints (no file
        read) — used when attaching features to the huge global repo, so a warm load
        stays instant instead of re-hashing 25k files.
        """
        if hash_if_missing:
            fp = self.fingerprint(path)
        else:
            fp = self._fp.get(self._key(path))
        if fp is None:
            return None
        d = self._data.get(fp)
        if not d:
            return None
        # Length guard: a shorter vector predates the current feature schema (e.g. the
        # old 60-dim MFCC-only one). Treat it as missing so analyze_missing recomputes
        # the richer 84-dim vector and put() overwrites the stale row in place.
        if len(d.get('mfcc', ())) != _AUDIO_FEAT_DIM:
            return None
        # Schema v9: rows lacking the Gaussian model (mfcc_mean/cov) predate the
        # middle-of-track + Mandel-Ellis change → recompute so both methods have data.
        # (`is None`, not truthiness — ndarray truthiness raises for size > 1.)
        if d.get('mfcc_mean') is None or d.get('mfcc_cov') is None:
            return None
        return AudioFeatures(**d)

    def put(self, path: Path, feat: AudioFeatures) -> None:
        fp = self.fingerprint(path)
        if fp is None:
            return
        self._data[fp] = {
            'bpm': feat.bpm, 'mfcc': feat.mfcc,
            'centroid': feat.centroid, 'rms': feat.rms,
            'mfcc_mean': feat.mfcc_mean, 'mfcc_cov': feat.mfcc_cov,
        }
        mean_blob = self._pack_mfcc(feat.mfcc_mean) if feat.mfcc_mean is not None else None
        cov_blob = self._pack_mfcc(feat.mfcc_cov) if feat.mfcc_cov is not None else None
        _db().execute(
            "INSERT OR REPLACE INTO features "
            "(fp, bpm, centroid, rms, mfcc, mfcc_mean, mfcc_cov) VALUES (?,?,?,?,?,?,?)",
            (fp, feat.bpm, feat.centroid, feat.rms,
             self._pack_mfcc(feat.mfcc), mean_blob, cov_blob))
        self._dirty = True

    def analyze_missing(self, entries: list[MusicEntry],
                        interactive: bool = True) -> None:
        """Run librosa on files not yet in cache. Shows progress.

        interactive=False (GUI) applies cached features but never prompts and
        never analyzes here — the GUI runs analysis explicitly via its own
        AudioAnalyzer worker thread.
        """
        if not HAS_LIBROSA:
            log.warning("  ⚠️ librosa not installed – skipping audio analysis.\n"
                        "  Install: pip install librosa")
            for e in entries:
                e.features = None
            return

        # Apply already-cached features first
        for e in entries:
            e.features = self.get(e.path)

        # Collapse byte-identical duplicates: analyze each unique content once.
        to_do = [e for e in entries if e.features is None]
        unique: list[MusicEntry] = []
        seen_fp: set[str] = set()
        for e in to_do:
            fp = self.fingerprint(e.path)
            if fp is not None and fp in seen_fp:
                continue   # duplicate of a file we'll analyze; filled in the final pass
            if fp is not None:
                seen_fp.add(fp)
            unique.append(e)
        dups = len(to_do) - len(unique)
        if not unique:
            log.info("  🎵 Audio features: all %s files already cached.", len(entries))
            return

        eta_s = len(unique) * 0.8   # rough estimate
        eta_min = int(eta_s / 60)
        log.info("  🎵 Audio analysis needed for %s files %s(~%s min first run, "
                 "cached afterwards).",
                 len(unique),
                 f"({dups} duplicates share results) " if dups else "",
                 eta_min or '<1')
        if not interactive:
            log.info("  Analysis deferred (non-interactive load).")
            return
        proceed = input("  Run analysis now? [Y/n]: ").strip().lower()
        if proceed == 'n':
            log.info("  Skipping – similarity scoring disabled for this session.")
            return

        # Probe: try loading 2 seconds of the first file to detect missing backends early
        probe = next((e.path for e in unique), None)
        why = probe_decode_backend(probe) if probe else None
        if why == PROBE_NO_BACKEND:
            log.error("  ✗ MP3 decoding unavailable – ffmpeg is not installed or not on PATH.\n"
                      "    Install ffmpeg, then restart:\n"
                      "      Windows:  winget install Gyan.FFmpeg\n"
                      "      or download from  https://www.gyan.dev/ffmpeg/builds/\n"
                      "  Skipping audio analysis for this session.")
            return
        if why is not None:
            log.error("  ✗ Audio probe failed (%s) – see above. Skipping analysis.", why)
            return

        def cli_progress(i: int, total: int, errors: int, path: Path, eta: float) -> None:
            if i == 1 or i % 20 == 0 or i == total:
                rem_m, rem_s = divmod(int(max(eta, 0)), 60)
                log.info("  🎵 %s/%s done  (~%sm%02ds remaining)", i, total, rem_m, rem_s)

        ok, errors, _ = self.analyze_entries(entries, progress_cb=cli_progress)
        log.info("  💾 Cached %s audio analyses → %s%s",
                 ok, AUDIO_DB_FILE,
                 f"  ({errors} files skipped)" if errors else "")

    def analyze_entries(
        self,
        entries: list[MusicEntry],
        progress_cb: Callable[[int, int, int, Path, float], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        force: bool = False,
        on_error: Callable[[Path, Exception], None] | None = None,
    ) -> tuple[int, int, bool]:
        """Core analysis loop shared by the CLI (analyze_missing) and the GUI worker.

        Collapses byte-identical duplicates (one analysis per content fingerprint),
        analyzes each unique file, persists every 200 files, then fills duplicate
        entries from the now-cached vectors.

        force=True re-analyzes every file even if already cached and overwrites the
        stored row in place (put() is INSERT OR REPLACE) — used to roll a changed
        feature/tempo method across the whole library.

        progress_cb(done, total, errors, path, eta_seconds) is invoked after every
        file; should_cancel() is polled per file — when it fires, partial results
        are saved and the loop stops. on_error(path, exc) is handed every file that
        failed, so a caller can report WHY instead of only how many.
        Returns (ok, errors, cancelled).
        """
        to_do = list(entries) if force else [e for e in entries if e.features is None]
        unique: list[MusicEntry] = []
        seen_fp: set[str] = set()
        for e in to_do:
            if should_cancel is not None and should_cancel():
                self.save()
                return 0, 0, True
            fp = self.fingerprint(e.path)
            if fp is not None and fp in seen_fp:
                continue   # duplicate of a file we'll analyze; filled in the final pass
            if fp is not None:
                seen_fp.add(fp)
            unique.append(e)

        total = len(unique)
        errors = 0
        t0 = time.time()
        if total > self.BIG_LIBRARY:
            log.info("🎵 Large library — analysing in steps so memory stays flat\n"
                     "files: %s\n"
                     "step size: %s (saved and memory released after each)",
                     total, self.BATCH_FILES)
        for i, e in enumerate(unique, 1):
            if should_cancel is not None and should_cancel():
                self.save()
                return i - 1 - errors, errors, True
            try:
                feat = self._analyze_file(e.path, _tempo_prior(e.dance, e.bpm))
                self.put(e.path, feat)
                e.features = feat
            except Exception as exc:
                errors += 1
                log.error("  ✗ analysis failed: %s: %s", e.path.name, exc)
                if on_error is not None:
                    on_error(e.path, exc)
            if progress_cb is not None:
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0.0
                eta = (total - i) / rate if rate > 0 else -1.0
                progress_cb(i, total, errors, e.path, eta)
            if i % self.BATCH_FILES == 0:
                self._finish_batch()

        # Fill in the byte-identical duplicates from the now-cached vectors (and,
        # under force, refresh every entry's stale in-memory features too).
        for e in entries:
            if force or e.features is None:
                e.features = self.get(e.path)
        self._finish_batch()
        return total - errors, errors, False

    def _finish_batch(self) -> None:
        """Close one step of the analysis loop: persist it, then give its memory back.

        Committing here means a run that is interrupted — or an app that has to be
        restarted halfway through a huge library — keeps everything up to this
        point. The collect afterwards drops the reference cycles the audio stack
        leaves behind (each one still holding a decoded window), and
        `_release_free_heap` unmaps the pages those freed.
        """
        self.save()
        gc.collect()
        _release_free_heap()

    @staticmethod
    def _analyze_file(path: Path, expected_bpm: float | None = None) -> AudioFeatures:
        """Load audio and extract features, suppressing all ffmpeg/mpg123 stderr output.

        `expected_bpm` (beats/min, from `_tempo_prior`) seeds the beat tracker so
        syncopated grooves don't lock onto a metric harmonic; None keeps the default.

        On Windows, audioread runs ffmpeg as a subprocess that inherits the Win32
        STD_ERROR_HANDLE (not the CRT fd 2); `quiet_native_stderr` mutes both layers.
        """
        with quiet_native_stderr():
            # Analyze the MIDDLE of the track, not the intro. Dance-track intros are
            # atypical (count-ins, fades, talk-ins, slow builds); the steady body is
            # representative. Mirrors the Java extractor's skip-intro/skip-outro. We
            # center a 60 s window: for a 3-min song this is ≈ 60–120 s.
            try:
                total = float(librosa.get_duration(path=str(path)))
            except Exception:
                total = 0.0
            win = 60.0
            offset = max(0.0, (total - win) / 2.0) if total > win else 0.0
            y, sr = librosa.load(str(path), sr=11025, offset=offset, duration=win, mono=True)
        # ── Timbre: 20 MFCCs – mean + std per coefficient + delta-means (60 values).
        # The std captures temporal variation (e.g. steady waltz vs energetic jive);
        # the delta-means capture articulation dynamics (staccato tango vs legato waltz).
        mfccs    = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        deltas   = librosa.feature.delta(mfccs)     # frame-to-frame rate of change
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        rms      = librosa.feature.rms(y=y)
        mfcc_block = (
            [float(np.mean(c)) for c in mfccs]  +   # 20 means  (timbral shape)
            [float(np.std(c))  for c in mfccs]  +   # 20 stds   (temporal spread)
            [float(np.mean(c)) for c in deltas]      # 20 delta-means (articulation dynamics)
        )
        # ── Brightness / genre: spectral contrast (peak-vs-valley energy per band).
        # n_bands=4 keeps the top band (200·2^4 = 3200 Hz) below the 5512 Hz Nyquist
        # at sr=11025 (the default n_bands=6 would exceed it and raise). → 5 sub-bands.
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=4)   # (5, t)
        contrast_block = (
            [float(np.mean(c)) for c in contrast] +  # 5 means
            [float(np.std(c))  for c in contrast]    # 5 stds
        )
        # ── Groove: a compact rhythmic fingerprint. The tempogram is the local
        # autocorrelation of the onset envelope (how the pulse recurs); averaging it
        # over time gives a lag-profile that captures the *rhythmic feel*, not just the
        # BPM number. We compress that profile into RHYTHM_BINS bins, plus onset
        # strength mean/std (how driving/sharp the rhythm is).
        rhythm_bins = 12
        tg = None
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if onset_env.size and float(np.max(onset_env)) > 0:
            tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)   # (win, t)
            lag_profile = np.nan_to_num(np.mean(tg, axis=1))                  # (win,)
            usable = (lag_profile.size // rhythm_bins) * rhythm_bins
            rhythm_fp = (lag_profile[:usable].reshape(rhythm_bins, -1).mean(axis=1)
                         if usable else np.zeros(rhythm_bins))
            onset_mean, onset_std = float(np.mean(onset_env)), float(np.std(onset_env))
        else:
            rhythm_fp = np.zeros(rhythm_bins)
            onset_mean = onset_std = 0.0
        rhythm_block = [float(x) for x in rhythm_fp] + [onset_mean, onset_std]

        # ── Tempo. When the dance is known, read it off the tempogram inside the
        # expected band (robust to syncopation — see `_tempo_from_tempogram`); reusing
        # the rhythm tempogram makes this nearly free. Otherwise fall back to librosa's
        # unconstrained beat tracker.
        bpm = _tempo_from_tempogram(tg, sr, expected_bpm)
        if bpm is None:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
            bpm = float(np.mean(tempo))

        feat_vec = mfcc_block + contrast_block + rhythm_block
        assert len(feat_vec) == _AUDIO_FEAT_DIM, \
            f"feature vector is {len(feat_vec)}, expected {_AUDIO_FEAT_DIM}"

        # ── Single-Gaussian timbre model (Mandel-Ellis), compared by symmetric KL.
        # Unlike the summary vector above (one averaged point), this keeps the full
        # distribution of per-frame MFCCs: mean + full covariance. Short, Java-matched
        # frames (512 win / 256 hop @ 11025 ≈ 46 ms / 23 ms) give finer time resolution
        # than the librosa default (n_fft=2048 ≈ 186 ms) before any averaging. Pure MFCC
        # only — no rhythm/contrast (BPM handles tempo).
        g_mfcc = librosa.feature.mfcc(
            y=y, sr=sr, n_mfcc=_GAUSS_MFCC, n_fft=512, hop_length=256)   # (k, frames)
        frames = g_mfcc.T                                                # (frames, k)
        if frames.shape[0] >= _GAUSS_MFCC + 1:
            mu = frames.mean(axis=0)
            cov = np.cov(frames, rowvar=False)                          # (k, k)
            # Regularize so the covariance is invertible (KL needs Σ⁻¹ and ln|Σ|).
            cov += np.eye(_GAUSS_MFCC) * (1e-3 * float(np.trace(cov)) / _GAUSS_MFCC + 1e-6)
            mfcc_mean = mu.astype(np.float32)
            mfcc_cov = cov.reshape(-1).astype(np.float32)
        else:
            mfcc_mean = mfcc_cov = None   # too few frames → no Gaussian (stays neutral)

        return AudioFeatures(
            bpm=float(bpm),
            mfcc=np.asarray(feat_vec, dtype=np.float32),
            centroid=float(np.mean(centroid)),
            rms=float(np.mean(rms)),
            mfcc_mean=mfcc_mean,
            mfcc_cov=mfcc_cov,
        )


# ── Scan Metadata Cache ────────────────────────────────────────────────────────
class ScanCache:
    """Caches per-file metadata (dance type, BPM, ID3 tags), CONTENT-addressed.

    Avoids re-reading ID3 tags for files already seen on every startup. The cache key
    is `ckey = "{content fingerprint}::{filename stem}"`: the detected dance/title/bpm/
    year are a pure function of the file's bytes plus its filename, so the same audio at
    a NEW path (relocated, or a renamed-back copy) reuses the cached metadata instead of
    re-reading tags — and each (content, name) is stored once, not once per path.

    The content fingerprint is resolved through the shared `AudioCache` (its `fingerprints`
    mirror already maps path::mtime → fp, so a warm file needs no disk read; only a
    genuinely new/relocated file is hashed, and that hash is shared with the audio
    analysis so the file is read at most once). Backed by the `scan_meta` table.
    """
    VERSION = 3  # added ID3 tag_title/tag_artist; v3 DB schema = content-addressed scan_meta

    def __init__(self, cache: AudioCache):
        self._cache = cache          # resolves content fingerprints (shared, deduped)
        self._data: dict[str, dict] = {}   # ckey → metadata dict
        self._dirty = False
        self._load()

    def _load(self) -> None:
        conn = _db()
        cols = ",".join(_META_COLS)
        for row in conn.execute(f"SELECT ckey, {cols} FROM scan_meta").fetchall():
            self._data[row[0]] = _row_to_meta(row[1:])
        if not self._data and SCAN_CACHE_FILE.exists():
            self._migrate_json()

    def _migrate_json(self) -> None:
        """One-time import of the legacy scan_cache.json into content-addressed scan_meta.

        Only files still present on disk can be imported (a fingerprint is needed to key
        them); anything missing is simply re-derived from ID3 on the next scan.
        """
        try:
            payload = json.loads(SCAN_CACHE_FILE.read_text(encoding='utf-8'))
        except Exception as exc:
            log.warning("⚠️ Legacy scan cache %s unreadable – skipping migration: %s",
                        SCAN_CACHE_FILE.name, exc)
            return
        if not isinstance(payload, dict) or payload.get('version') != self.VERSION:
            return
        entries = payload.get('entries', {})
        conn = _db()
        placeholders = ",".join("?" * (1 + len(_META_COLS)))
        imported = 0
        for key, data in entries.items():
            path = key.rpartition('::')[0] or key
            p = Path(path)
            fp = self._cache.fingerprint(p)   # needs the file on disk
            if fp is None:
                continue
            ckey = f"{fp}::{p.stem}"
            self._data[ckey] = data
            conn.execute(
                f"INSERT OR REPLACE INTO scan_meta (ckey, {','.join(_META_COLS)}) "
                f"VALUES ({placeholders})",
                (ckey, *_meta_to_row(data)))
            imported += 1
        conn.commit()
        try:
            SCAN_CACHE_FILE.rename(SCAN_CACHE_FILE.with_suffix('.json.bak'))
        except OSError:
            pass
        log.info("  ♻️  Scan cache migrated JSON → content-addressed scan_meta: "
                 "%s/%s files → %s", imported, len(entries), AUDIO_DB_FILE.name)

    def save(self) -> None:
        if self._dirty:
            _db().commit()
            self._dirty = False

    def _ckey(self, path: Path) -> str | None:
        """Content-addressed cache key for a file, or None if it can't be hashed."""
        fp = self._cache.fingerprint(path)
        if fp is None:
            return None
        return f"{fp}::{path.stem}"

    def get(self, path: Path) -> dict | None:
        ckey = self._ckey(path)
        return self._data.get(ckey) if ckey else None

    def put(self, path: Path, data: dict) -> None:
        ckey = self._ckey(path)
        if ckey is None:
            return
        self._data[ckey] = data
        placeholders = ",".join("?" * (1 + len(_META_COLS)))
        _db().execute(
            f"INSERT OR REPLACE INTO scan_meta (ckey, {','.join(_META_COLS)}) "
            f"VALUES ({placeholders})",
            (ckey, *_meta_to_row(data)))
        self._dirty = True

    def forget_custom(self) -> None:
        """The Custom field was mapped anew — custom_field.set_source cleared
        the column in the table: drop the values read for the old mapping from
        the rows held here too, so the next look reads the new frame."""
        for meta in self._data.values():
            meta['custom'] = None

    def forget(self, path: Path) -> bool:
        """Drop the cached metadata for `path` so the next read goes to the ID3
        tags again. True when there was a row to drop.

        The key is content-addressed, so a tag editor's rewrite normally misses
        the cache all by itself — this is for the file that was edited WHILE the
        app runs (the 🏷 context-menu re-read), and for the tool that rewrites
        tags without changing the bytes we fingerprint."""
        ckey = self._ckey(path)
        if ckey is None:
            return False
        had = self._data.pop(ckey, None) is not None
        _db().execute("DELETE FROM scan_meta WHERE ckey = ?", (ckey,))
        self._dirty = True
        return had


def _vanished(path: Path) -> bool:
    """Really deleted, as opposed to sitting on a drive that isn't plugged in.

    The playlist tree lives on an external drive here, and "the folder isn't
    there" would otherwise throw away a whole tournament index every time the
    drive is unplugged. A missing folder counts only when its drive answers.
    """
    return not path.exists() and bool(path.anchor) and Path(path.anchor).exists()


def cleanup_orphans(prune_features: bool = False) -> dict:
    """Drop DB rows for music files that no longer exist on disk.

    Removes the dead `files` rows (path gone) along with their `fingerprints` and
    `global_meta` rows, then prunes any content-addressed `scan_meta` row no longer
    referenced by a surviving file's (fingerprint, stem).

    Feature vectors are KEPT by default: they're content-addressed and expensive to
    recompute, so a deleted-then-re-added (or relocated) track still reattaches its
    timbre instantly. Pass ``prune_features=True`` to also reclaim feature rows that
    no fingerprint points at any more. Returns a dict of removed counts.

    Run this on an explicit full rebuild — NOT on warm startup loads — since it stats
    every registered path. A file whose drive is not plugged in is not dead
    (`_vanished`) — Build ALL with F: out used to wipe the whole music drive.
    """
    conn = _db()
    dead_ids = [fid for (fid, path) in conn.execute("SELECT id, path FROM files").fetchall()
                if _vanished(Path(path))]
    for fid in dead_ids:
        conn.execute("DELETE FROM fingerprints WHERE file_id = ?", (fid,))
        conn.execute("DELETE FROM global_meta  WHERE file_id = ?", (fid,))
    conn.executemany("DELETE FROM files WHERE id = ?", [(i,) for i in dead_ids])

    # scan_meta is content-addressed → keep only ckeys still referenced by a live file.
    live_ckeys = {
        f"{fp}::{Path(path).stem}"
        for (path, fp) in conn.execute(
            "SELECT f.path, fp.fp FROM fingerprints fp JOIN files f ON f.id = fp.file_id")
    }
    dead_ckeys = [c for (c,) in conn.execute("SELECT ckey FROM scan_meta")
                  if c not in live_ckeys]
    conn.executemany("DELETE FROM scan_meta WHERE ckey = ?", [(c,) for c in dead_ckeys])

    feat_removed = afp_removed = 0
    if prune_features:
        live_fps = {fp for (fp,) in conn.execute("SELECT DISTINCT fp FROM fingerprints")}
        dead_fps = [fp for (fp,) in conn.execute("SELECT fp FROM features")
                    if fp not in live_fps]
        conn.executemany("DELETE FROM features WHERE fp = ?", [(fp,) for fp in dead_fps])
        feat_removed = len(dead_fps)
        # audio_fps is the re-attach map (content fp → fingerprint of the audio
        # inside it). It goes exactly when the features go: while they are kept, it
        # is what lets a deleted-then-re-added track reattach even after a tag edit;
        # once they are gone it points at nothing.
        dead_afps = [fp for (fp,) in conn.execute("SELECT fp FROM audio_fps")
                     if fp not in live_fps]
        conn.executemany("DELETE FROM audio_fps WHERE fp = ?",
                         [(fp,) for fp in dead_afps])
        afp_removed = len(dead_afps)

    conn.commit()
    removed = {"files": len(dead_ids), "scan_meta": len(dead_ckeys),
               "features": feat_removed, "audio_fps": afp_removed}
    if any(removed.values()):
        log.info("  🧹 Orphan cleanup:\n"
                 "    files: %s\n"
                 "    scan_meta: %s\n"
                 "    features: %s",
                 f"{removed['files']:,}", f"{removed['scan_meta']:,}",
                 f"{removed['features']:,}")
    return removed


def db_maintenance() -> dict:
    """Reclaim database disk space: full orphan cleanup + VACUUM.

    Beyond `cleanup_orphans(prune_features=True)` this also prunes the OTHER
    content-addressed side tables (embeddings / loudness / pd_highlights / silences /
    vocals / noise) whose
    fingerprint no live file references any more, then VACUUMs so the freed pages
    actually shrink the file on disk. Slow (stats every registered path, then
    rewrites the whole DB) — run it from an explicit maintenance action only.

    Returns {"removed": {table: count, …}, "size_before": bytes, "size_after": bytes}.

    Raises RuntimeError when most registered files look missing: that almost
    always means the music drive isn't mounted, and cleaning then would wipe the
    expensive cached analysis for the entire library.
    """
    conn = _db()
    size_before = AUDIO_DB_FILE.stat().st_size

    total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    missing = sum(1 for (p,) in conn.execute("SELECT path FROM files")
                  if not Path(p).exists())
    if total and missing > max(100, total // 2):
        raise RuntimeError(
            f"{missing:,} of {total:,} registered files are missing — is the music "
            "drive mounted? Cleanup aborted so the cached analysis isn't wiped.")

    removed = cleanup_orphans(prune_features=True)

    # Side tables keyed by content fingerprint (embeddings has one row per
    # fp+model; the others one per fp) — drop rows no live file points at.
    live_fps = {fp for (fp,) in conn.execute("SELECT DISTINCT fp FROM fingerprints")}
    for table in ("embeddings", "loudness", "pd_highlights", "silences", "vocals",
                  "noise"):
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone() is None:
            removed[table] = 0
            continue
        dead_fps = [fp for (fp,) in conn.execute(f"SELECT DISTINCT fp FROM {table}")
                    if fp not in live_fps]
        before = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.executemany(f"DELETE FROM {table} WHERE fp = ?",
                         [(fp,) for fp in dead_fps])
        removed[table] = before - conn.execute(
            f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    # The playlist index is keyed by folder, not by fingerprint, so none of the above
    # reaches it. PlaylistIndexCache drops a vanished root only when it happens to
    # load a DIFFERENT one, and the root's dance digest in app_meta only while that
    # root still has index rows — so a digest whose rows were already gone could
    # never be reached again and piled up one row per temp folder ever indexed.
    gone_roots = [r for (r,) in conn.execute("SELECT DISTINCT root FROM playlist_index")
                  if _vanished(Path(r))]
    n_pl = 0
    for root in gone_roots:
        n_pl += conn.execute("DELETE FROM playlist_index WHERE root = ?",
                             (root,)).rowcount
    removed["playlist_index"] = n_pl
    dead_keys = [k for (k,) in conn.execute(
        "SELECT key FROM app_meta WHERE key LIKE 'playlist_index_dance:%'")
        if _vanished(Path(k.split(":", 1)[1]))]
    conn.executemany("DELETE FROM app_meta WHERE key = ?", [(k,) for k in dead_keys])
    removed["app_meta"] = len(dead_keys)
    conn.commit()

    log.info("  🧹 VACUUM %s (%.1f MB) …", AUDIO_DB_FILE.name, size_before / 1e6)
    conn.execute("VACUUM")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    size_after = AUDIO_DB_FILE.stat().st_size
    log.info("  🧹 Database maintenance done:\n"
             "    size: %.1f MB → %.1f MB\n"
             "    removed rows: %s",
             size_before / 1e6, size_after / 1e6,
             ", ".join(f"{t}={n:,}" for t, n in removed.items()))
    return {"removed": removed, "size_before": size_before, "size_after": size_after}


# Metadata keys persisted per entry (everything _make_entry derives except path).
# cluster is recomputed from the parent dir in scan(); features come from AudioCache.
_ENTRY_META_KEYS = (
    "title", "dance", "bpm", "year", "other_genre", "classes_ok",
    "is_instrumental", "is_xmas", "tag_title", "tag_artist", "duration",
    "tag_album", "comment_tags", "rating", "custom",
)


def _entry_meta(entry: MusicEntry) -> dict:
    """Serializable metadata dict for an entry (used by GlobalScanCache)."""
    return {k: getattr(entry, k) for k in _ENTRY_META_KEYS}


# ── Global Repo Scan Cache ─────────────────────────────────────────────────────
class GlobalScanCache:
    """Persists the assembled metadata for the whole music repo (~25k files).

    Unlike ScanCache (per-file ID3 metadata keyed by size), this caches the full
    entry list for the opt-in global search so a fresh session reloads instantly.
    Each file is invalidated individually by its last-modified time (mtime): if a
    file changed on disk its entry is re-read, otherwise the cached value is reused.
    Backed by the normalized `global_meta` table (file_id + mtime + one column per
    metadata field). Read-only w.r.t. the music files — only the DB is ever written.
    """
    VERSION = 1

    def __init__(self):
        self._data: dict[str, dict] = {}  # str(path) → {"mtime": int, "entry": {...}}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        conn = _db()
        cols = ",".join(_META_COLS)
        for row in conn.execute(
                f"SELECT f.path, m.mtime, {cols} FROM global_meta m "
                f"JOIN files f ON f.id = m.file_id").fetchall():
            path, mtime = row[0], row[1]
            self._data[path] = {'mtime': mtime, 'entry': _row_to_meta(row[2:])}
        if not self._data and GLOBAL_SCAN_CACHE_FILE.exists():
            self._migrate_json()

    def _migrate_json(self) -> None:
        """One-time import of the legacy global_scan_cache.json into the normalized DB."""
        try:
            payload = json.loads(GLOBAL_SCAN_CACHE_FILE.read_text(encoding='utf-8'))
        except Exception as exc:
            log.warning("⚠️ Legacy global scan cache %s unreadable – skipping migration: %s",
                        GLOBAL_SCAN_CACHE_FILE.name, exc)
            return
        if not isinstance(payload, dict) or payload.get('version') != self.VERSION:
            return
        entries = payload.get('entries', {})
        conn = _db()
        placeholders = ",".join("?" * (2 + len(_META_COLS)))
        for p, rec in entries.items():
            entry = rec.get('entry', {})
            self._data[p] = {'mtime': rec.get('mtime', 0), 'entry': entry}
            conn.execute(
                f"INSERT OR REPLACE INTO global_meta (file_id, mtime, {','.join(_META_COLS)}) "
                f"VALUES ({placeholders})",
                (_file_id(p), rec.get('mtime', 0), *_meta_to_row(entry)))
        conn.commit()
        try:
            GLOBAL_SCAN_CACHE_FILE.rename(GLOBAL_SCAN_CACHE_FILE.with_suffix('.json.bak'))
        except OSError:
            pass
        log.info("  ♻️  Global scan cache migrated JSON → SQLite global_meta: "
                 "%s files → %s", len(entries), AUDIO_DB_FILE.name)

    def save(self) -> None:
        if self._dirty:
            _db().commit()
            self._dirty = False

    @staticmethod
    def _mtime(path: Path) -> int:
        try:
            return int(path.stat().st_mtime)
        except OSError:
            return 0

    def get(self, path: Path) -> dict | None:
        """Return the cached entry-meta dict only if the file is unchanged (mtime match)."""
        rec = self._data.get(str(path))
        if rec is not None and rec.get('mtime') == self._mtime(path):
            return rec.get('entry')
        return None

    def put(self, path: Path, entry_data: dict) -> None:
        mtime = self._mtime(path)
        self._data[str(path)] = {'mtime': mtime, 'entry': entry_data}
        placeholders = ",".join("?" * (2 + len(_META_COLS)))
        _db().execute(
            f"INSERT OR REPLACE INTO global_meta (file_id, mtime, {','.join(_META_COLS)}) "
            f"VALUES ({placeholders})",
            (_file_id(str(path)), mtime, *_meta_to_row(entry_data)))
        self._dirty = True

    def all_entries(self) -> list[tuple[str, dict]]:
        """(path, entry-meta) for every cached file, WITHOUT a freshness/mtime check.

        Lets the GUI rebuild the whole-repo library instantly from the warm cache —
        no filesystem re-walk, no indexing window — when nothing needs re-reading.
        """
        return [(p, rec.get('entry', {})) for p, rec in self._data.items()]

    def prune(self, seen_paths: set) -> None:
        """Drop cache records for files no longer present in the repo."""
        stale = [k for k in self._data if k not in seen_paths]
        for k in stale:
            del self._data[k]
            fid = _file_id(k, create=False)
            if fid is not None:
                _db().execute("DELETE FROM global_meta WHERE file_id = ?", (fid,))
        if stale:
            self._dirty = True


class PlaylistIndexCache:
    """Persists what `MusicLibrary._learn_playlists` derives from PLAYLIST_DIR.

    Learning popularity means reading every .m3u under the playlist dir — ~2100
    files / 141k lines here — and turning each line into its match keys. Almost
    none of that changes between two starts: a tournament export is written once
    and then sits there for years. So each playlist is cached by its mtime+size
    and only re-read when it actually changed, exactly like `GlobalScanCache`
    does for music files.

    Cached per playlist: the start class parsed from its name, the set of
    match keys its lines derive, and the subsets of those keys that were danced
    in the playlist's FINAL (`fkeys`) and SEMIFINAL (`skeys`) round — both empty
    when the list does not say. Those keys depend on the library's calculated
    dances (`_line_keys` → `_stem_dance`), which is NOT part of any playlist's
    mtime — hence `dance_digest`: a changed dance map drops the whole root's
    rows and everything is derived again.

    Rows are namespaced by `root` (the playlist dir they came from), so pointing
    the setting at another folder — or a test at a temp dir — cannot make one
    tree's index answer for another's.
    """
    VERSION = 4       # v3: fkeys / skeys — the keys of its final and semifinal
    #                   v4: a 'S50 DJ Eiffel. <title>' line keeps its title key

    def __init__(self, root: Path, dance_digest: str):
        self._root = str(root)
        self._rows: dict[str, tuple[str, str | None, str, str, str]] = {}
        #                        pl_id → (sig, cls, mkeys, fkeys, skeys)
        self._writes: list[tuple] = []
        self._deletes: list[tuple] = []
        self._load(dance_digest)

    @property
    def _digest_key(self) -> str:
        return f"playlist_index_dance:{self._root}"

    def _load(self, dance_digest: str) -> None:
        conn = _db()
        want = f"{self.VERSION}:{dance_digest}"
        have = conn.execute("SELECT value FROM app_meta WHERE key = ?",
                            (self._digest_key,)).fetchone()
        if have is None or have[0] != want:
            # The dance map (or this code) changed — every cached key could be
            # qualified by the wrong dance, so none of them may be trusted.
            conn.execute("DELETE FROM playlist_index WHERE root = ?", (self._root,))
            conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
                         (self._digest_key, want))
            log.info("  📜 Playlist index cache rebuilding — the library's dance map changed")
        else:
            for pl_id, sig, cls, mkeys, fkeys, skeys in conn.execute(
                    "SELECT pl_id, sig, cls, mkeys, fkeys, skeys FROM playlist_index "
                    "WHERE root = ?", (self._root,)).fetchall():
                self._rows[pl_id] = (sig, cls, mkeys, fkeys or "", skeys or "")
        self._drop_vanished_roots()

    def _drop_vanished_roots(self) -> None:
        """Forget trees that are no longer on disk — a renamed playlist folder, or
        the temp dirs the tests point PLAYLIST_DIR at. Only ever called with the
        current root present, so a merely unplugged drive keeps its index."""
        conn = _db()
        for (root,) in conn.execute(
                "SELECT DISTINCT root FROM playlist_index WHERE root <> ?",
                (self._root,)).fetchall():
            if not Path(root).exists():
                conn.execute("DELETE FROM playlist_index WHERE root = ?", (root,))
                conn.execute("DELETE FROM app_meta WHERE key = ?",
                             (f"playlist_index_dance:{root}",))

    def get(self, pl_id: str, sig: str
            ) -> tuple[str | None, list[str], list[str], list[str]] | None:
        """(class, match keys, final-round keys, semifinal keys) for an unchanged
        playlist, else None."""
        rec = self._rows.get(pl_id)
        if rec is None or rec[0] != sig:
            return None
        return (rec[1],
                rec[2].split("\n") if rec[2] else [],
                rec[3].split("\n") if rec[3] else [],
                rec[4].split("\n") if rec[4] else [])

    def put(self, pl_id: str, sig: str, cls: str | None, keys: list[str],
            final_keys: list[str], semi_keys: list[str]) -> None:
        mkeys = "\n".join(keys)
        fkeys = "\n".join(final_keys)
        skeys = "\n".join(semi_keys)
        self._rows[pl_id] = (sig, cls, mkeys, fkeys, skeys)
        self._writes.append((self._root, pl_id, sig, cls, mkeys, fkeys, skeys))

    def prune(self, seen: set[str]) -> None:
        """Drop playlists that are gone from the tree."""
        for p in [p for p in self._rows if p not in seen]:
            del self._rows[p]
            self._deletes.append((self._root, p))

    def save(self) -> None:
        """Flush in ONE transaction — the connection is in autocommit mode, and a
        first run writes 2000+ rows."""
        if not self._writes and not self._deletes:
            return
        conn = _db()
        conn.execute("BEGIN")
        try:
            conn.executemany(
                "INSERT OR REPLACE INTO playlist_index "
                "(root, pl_id, sig, cls, mkeys, fkeys, skeys) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", self._writes)
            conn.executemany(
                "DELETE FROM playlist_index WHERE root = ? AND pl_id = ?", self._deletes)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        self._writes.clear()
        self._deletes.clear()


def global_index_count() -> int:
    """Number of files in the persisted global index (0 if not built yet)."""
    try:
        return _db().execute("SELECT COUNT(*) FROM global_meta").fetchone()[0]
    except Exception:
        return 0


def global_coverage(models: list[str] | None = None) -> dict:
    """Repo index coverage straight from the DB — no in-memory library needed.

    Returns {'total': N, 'librosa': M, 'embeddings': {model: K, ...}} via cheap
    COUNT/JOINs over global_meta ⨝ fingerprints ⨝ features/embeddings. Lets the UI
    show 'Repository a/N' even before the global library is loaded into memory.
    """
    out = {'total': 0, 'librosa': 0, 'embeddings': {}}
    conn = _db()
    try:
        out['total'] = conn.execute("SELECT COUNT(*) FROM global_meta").fetchone()[0]
        out['librosa'] = conn.execute(
            "SELECT COUNT(DISTINCT g.file_id) FROM global_meta g "
            "JOIN fingerprints f ON f.file_id = g.file_id "
            "JOIN features ft ON ft.fp = f.fp").fetchone()[0]
        for m in (models or []):
            out['embeddings'][m] = conn.execute(
                "SELECT COUNT(DISTINCT g.file_id) FROM global_meta g "
                "JOIN fingerprints f ON f.file_id = g.file_id "
                "JOIN embeddings e ON e.fp = f.fp AND e.model = ?", (m,)).fetchone()[0]
    except Exception:
        pass
    return out
