#!/usr/bin/env python3
"""The library's side caches on the shared database, next to AudioCache:
ScanCache (per-file tag metadata, content-addressed), GlobalScanCache (the
whole repo's assembled entries for the opt-in global search),
PlaylistIndexCache (the learned playlist index) and the cheap coverage
counts of the global index."""

import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from planner.config import GLOBAL_SCAN_CACHE_FILE, SCAN_CACHE_FILE, audio_db_file
from planner.music.db import META_COLS, _db, file_id, meta_to_row, row_to_meta

if TYPE_CHECKING:
    from planner.models import MusicEntry
    from planner.music.db import AudioCache

log = logging.getLogger("dancesport.db")


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
        cols = ",".join(META_COLS)
        for row in conn.execute(f"SELECT ckey, {cols} FROM scan_meta").fetchall():  # nosec B608: constant names
            self._data[row[0]] = row_to_meta(row[1:])
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
        placeholders = ",".join("?" * (1 + len(META_COLS)))
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
                f"INSERT OR REPLACE INTO scan_meta (ckey, {','.join(META_COLS)}) "
                f"VALUES ({placeholders})",
                (ckey, *meta_to_row(data)))
            imported += 1
        conn.commit()
        with contextlib.suppress(OSError):
            SCAN_CACHE_FILE.rename(SCAN_CACHE_FILE.with_suffix('.json.bak'))
        log.info("  ♻️  Scan cache migrated JSON → content-addressed scan_meta: "
                 "%s/%s files → %s", imported, len(entries), audio_db_file().name)

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

    def has_row(self, fp: str, path: Path) -> bool:
        """Whether a row exists for this content under this file name. Reads no
        file and no database (the scan's read-ahead pool asks it)."""
        return f"{fp}::{path.stem}" in self._data

    def put(self, path: Path, data: dict) -> None:
        ckey = self._ckey(path)
        if ckey is None:
            return
        self._data[ckey] = data
        placeholders = ",".join("?" * (1 + len(META_COLS)))
        _db().execute(
            f"INSERT OR REPLACE INTO scan_meta (ckey, {','.join(META_COLS)}) "
            f"VALUES ({placeholders})",
            (ckey, *meta_to_row(data)))
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


# Metadata keys persisted per entry (everything _make_entry derives except path).
# cluster is recomputed from the parent dir in scan(); features come from AudioCache.
ENTRY_META_KEYS = (
    "title", "dance", "bpm", "year", "other_genre", "classes_ok",
    "is_instrumental", "is_xmas", "tag_title", "tag_artist", "duration",
    "tag_album", "comment_tags", "rating", "custom", "tag_bpm", "tag_comment",
)


def entry_meta(entry: MusicEntry) -> dict:
    """Serializable metadata dict for an entry (used by GlobalScanCache)."""
    return {k: getattr(entry, k) for k in ENTRY_META_KEYS}


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
        cols = ",".join(META_COLS)
        for row in conn.execute(
                f"SELECT f.path, m.mtime, {cols} FROM global_meta m "  # nosec B608: constant names
                f"JOIN files f ON f.id = m.file_id").fetchall():
            path, mtime = row[0], row[1]
            self._data[path] = {'mtime': mtime, 'entry': row_to_meta(row[2:])}
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
        placeholders = ",".join("?" * (2 + len(META_COLS)))
        for p, rec in entries.items():
            entry = rec.get('entry', {})
            self._data[p] = {'mtime': rec.get('mtime', 0), 'entry': entry}
            conn.execute(
                f"INSERT OR REPLACE INTO global_meta (file_id, mtime, {','.join(META_COLS)}) "
                f"VALUES ({placeholders})",
                (file_id(p), rec.get('mtime', 0), *meta_to_row(entry)))
        conn.commit()
        with contextlib.suppress(OSError):
            GLOBAL_SCAN_CACHE_FILE.rename(GLOBAL_SCAN_CACHE_FILE.with_suffix('.json.bak'))
        log.info("  ♻️  Global scan cache migrated JSON → SQLite global_meta: "
                 "%s files → %s", len(entries), audio_db_file().name)

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
        mtime = self._mtime(path)   # 0: stat failed, so nothing proves it unchanged
        if rec is not None and mtime and rec.get('mtime') == mtime:
            return rec.get('entry')
        return None

    def put(self, path: Path, entry_data: dict) -> None:
        mtime = self._mtime(path)
        self._data[str(path)] = {'mtime': mtime, 'entry': entry_data}
        placeholders = ",".join("?" * (2 + len(META_COLS)))
        _db().execute(
            f"INSERT OR REPLACE INTO global_meta (file_id, mtime, {','.join(META_COLS)}) "
            f"VALUES ({placeholders})",
            (file_id(str(path)), mtime, *meta_to_row(entry_data)))
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
            fid = file_id(k, create=False)
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
        log.debug("🗄️ Global index not countable", exc_info=True)
        return 0


def global_coverage(models: list[str] | None = None) -> dict:
    """Repo index coverage straight from the DB — no in-memory library needed.

    Returns {'total': N, 'librosa': M, 'embeddings': {model: K, ...}} via cheap
    COUNT/JOINs over global_meta ⨝ fingerprints ⨝ features/embeddings. Lets the UI
    show 'Repository a/N' even before the global library is loaded into memory.
    """
    out: dict[str, Any] = {'total': 0, 'librosa': 0, 'embeddings': {}}
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
        log.debug("🗄️ Global index coverage not countable", exc_info=True)
    return out
