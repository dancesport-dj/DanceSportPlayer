#!/usr/bin/env python3
"""Upkeep of the shared database: dropping rows of music files that are gone,
the daily backup of the user's own data and its restore, and the VACUUM pass
of Database maintenance."""

import contextlib
import datetime
import logging
import os
import platform
import sqlite3
from pathlib import Path

from planner.config import audio_db_file
from planner.music.db import _db, bulk_writes_held
from planner.music.embeddings import MODELS as EMBEDDING_MODELS

log = logging.getLogger("dancesport.db")


def _vanished(path: Path, drives: dict[str, bool] | None = None) -> bool:
    """Really deleted, as opposed to sitting on a drive that isn't plugged in.

    The playlist tree lives on an external drive here, and "the folder isn't
    there" would otherwise throw away a whole tournament index every time the
    drive is unplugged. A missing folder counts only when its drive answers.
    `drives` remembers each drive's answer across the calls of one sweep.
    """
    if path.exists() or not path.anchor:
        return False
    if drives is None:
        return Path(path.anchor).exists()
    if path.anchor not in drives:
        drives[path.anchor] = Path(path.anchor).exists()
    return drives[path.anchor]


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
    drives: dict[str, bool] = {}
    dead_ids = [fid for (fid, path) in conn.execute("SELECT id, path FROM files").fetchall()
                if _vanished(Path(path), drives)]
    # One transaction: a crash half-way leaves the DB as it was, not half
    # cleaned, and the deletes share one commit instead of one each. IMMEDIATE:
    # a deferred one that reads first fails at its first DELETE, without
    # waiting, once another thread has committed in between.
    conn.execute("BEGIN IMMEDIATE")
    try:
        removed = _delete_orphans(conn, dead_ids, prune_features)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    if any(removed.values()):
        log.info("  🧹 Orphan cleanup:\n"
                 "    files: %s\n"
                 "    scan_meta: %s\n"
                 "    features: %s",
                 f"{removed['files']:,}", f"{removed['scan_meta']:,}",
                 f"{removed['features']:,}")
    return removed


def _delete_orphans(conn: sqlite3.Connection, dead_ids: list[int],
                    prune_features: bool) -> dict:
    """The deletes of `cleanup_orphans`, inside its transaction."""
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

    return {"files": len(dead_ids), "scan_meta": len(dead_ckeys),
            "features": feat_removed, "audio_fps": afp_removed}


BACKUPS_KEPT = 7

# ⚙ Settings → Analysis can name a folder of the operator's own (a Dropbox
# folder, so the backups live off this PC). None: next to the database.
_backup_folder: Path | None = None


def apply_settings(settings: dict) -> None:
    """The settings hook: where `backup_user_data` writes from now on."""
    global _backup_folder
    folder = str(settings.get("backup_dir") or "").strip()
    _backup_folder = Path(folder) if folder else None


def _backup_dir() -> Path:
    """Where the backups go. A configured folder is shared - Dropbox syncs it
    to every PC - so each PC writes into a subfolder named after itself: a
    file per day under the same name would overwrite another PC's backup of
    that day, and the rotation would delete theirs."""
    if _backup_folder is not None:
        return _backup_folder / (platform.node() or "this-pc")
    return audio_db_file().parent / "backups"


def backup_user_data(today: datetime.date | None = None,
                     refresh: bool = False) -> Path | None:
    """A small dated copy of the rows no rescan can rebuild: the tag edits made
    in the app, the hand-set Paso Doble highlights, the 📜 play log, and the
    audio fingerprints behind the first two (so a restore still finds a
    re-tagged copy). Features, loudness
    and the rest are left out: they are recomputed, and they are most of the
    file. At most one backup per day, the newest BACKUPS_KEPT are kept.
    `refresh` writes today's backup again even when it exists (at quit, so the
    session's own changes are in it).

    Returns the file written, or None when there is nothing to keep or today's
    backup already exists."""
    conn = _db()
    n_keep = (conn.execute("SELECT COUNT(*) FROM tag_edits").fetchone()[0]
              + conn.execute("SELECT COUNT(*) FROM pd_highlights WHERE manual = 1")
              .fetchone()[0]
              + conn.execute("SELECT COUNT(*) FROM play_log").fetchone()[0])
    if not n_keep:
        return None
    today = today or datetime.date.today()
    dest = _backup_dir() / f"user-data-{today.isoformat()}.db"
    if dest.exists() and not refresh:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.unlink(missing_ok=True)
    try:
        out = sqlite3.connect(str(part))
        try:
            out.execute("ATTACH DATABASE ? AS src", (str(audio_db_file()),))
            out.execute("CREATE TABLE tag_edits AS SELECT * FROM src.tag_edits")
            out.execute("CREATE TABLE pd_highlights AS "
                        "SELECT * FROM src.pd_highlights WHERE manual = 1")
            out.execute("CREATE TABLE audio_fps AS SELECT * FROM src.audio_fps "
                        "WHERE fp IN (SELECT fp FROM tag_edits "
                        "             UNION SELECT fp FROM pd_highlights)")
            out.execute("CREATE TABLE play_log AS SELECT * FROM src.play_log")
            out.commit()
            out.execute("DETACH DATABASE src")
        finally:
            out.close()
        os.replace(part, dest)
    except BaseException:
        # A half-written copy is no backup: don't leave it beside the real ones.
        part.unlink(missing_ok=True)
        raise
    for old in sorted(_backup_dir().glob("user-data-*.db"))[:-BACKUPS_KEPT]:
        old.unlink(missing_ok=True)
    return dest


def backup_safely(refresh: bool = False) -> None:
    """Back the user's own rows up: at the first DB use of a start, and again
    (`refresh`) when the app closes. A failure is logged and never stops the
    app."""
    try:
        written = backup_user_data(refresh=refresh)
    except (OSError, sqlite3.Error) as exc:
        log.warning("💾 User data backup failed: %s", exc)
        return
    if written:
        log.info("💾 User data backed up\n"
                 "file: %s", written)


def restore_user_data(src: Path) -> tuple[int, int, int]:
    """Merge a `backup_user_data` file back in: its tag edits and hand-set PD
    highlights replace this DB's rows for the same tracks, and also land on
    every local copy with the same audio (a re-tagged file). Plays missing from
    the 📜 play log are added. Other rows stay. The in-memory caches read them
    on the next start.

    Returns (tag edits, PD marks, plays added). Raises ValueError for a file
    that is no such backup."""
    play_cols = "started_at, path, artist, title, dance, list_name, length"
    try:
        with contextlib.closing(sqlite3.connect(
                f"{Path(src).as_uri()}?mode=ro", uri=True)) as bak:
            cur = bak.execute("SELECT * FROM tag_edits")
            edit_cols = [d[0] for d in cur.description]
            edits = cur.fetchall()
            marks = bak.execute("SELECT fp, times FROM pd_highlights").fetchall()
            afps = dict(bak.execute("SELECT fp, afp FROM audio_fps").fetchall())
            # A backup from before the play log has none, one from before the
            # composer column has no composers.
            bak_play_cols = {r[1] for r in bak.execute("PRAGMA table_info(play_log)")}
            if "composer" in bak_play_cols:
                play_cols += ", composer"
            plays = (bak.execute(f"SELECT {play_cols} FROM play_log").fetchall()  # nosec B608: constant names
                     if bak_play_cols else [])
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"{src} is no user data backup: {exc}") from exc
    conn = _db()
    local_cols = {r[1] for r in conn.execute("PRAGMA table_info(tag_edits)")}
    if edit_cols[:1] != ["fp"] or not set(edit_cols) <= local_cols:
        raise ValueError(f"{src} is no user data backup: unknown tag edit columns")

    def targets(fp: str) -> set:
        afp = afps.get(fp)
        if not afp:
            return {fp}
        conn.execute("INSERT OR IGNORE INTO audio_fps (fp, afp) VALUES (?,?)", (fp, afp))
        return {fp} | {r[0] for r in conn.execute(
            "SELECT fp FROM audio_fps WHERE afp = ?", (afp,))}

    insert_edit = (f"INSERT OR REPLACE INTO tag_edits ({', '.join(edit_cols)}) "
                   f"VALUES ({', '.join('?' * len(edit_cols))})")
    conn.execute("BEGIN")
    try:
        for row in edits:
            for t in targets(row[0]):
                conn.execute(insert_edit, (t, *row[1:]))
        for fp, times in marks:
            for t in targets(fp):
                conn.execute("INSERT OR REPLACE INTO pd_highlights (fp, times, manual) "
                             "VALUES (?,?,1)", (t, times))
        added = 0
        for row in plays:
            added += conn.execute(f"INSERT OR IGNORE INTO play_log ({play_cols}) "
                                  f"VALUES ({', '.join('?' * len(row))})", row).rowcount
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return len(edits), len(marks), added


# 🗑 Reset database: what each part of its dialog empties, as (table, WHERE).
# "scan" is rebuilt by the next library scan (minutes), "analysis" by ⚗ Analysis
# (hours), "user" by nothing - only the backup taken first brings it back.
# app_meta keeps its settings (the Custom field mapping) under every tick.
RESET_GROUPS: dict[str, tuple[tuple[str, str], ...]] = {
    "scan": (("fingerprints", ""), ("global_meta", ""), ("files", ""), ("scan_meta", ""),
             ("audio_fps", ""), ("playlist_index", ""),
             ("app_meta", "key LIKE 'playlist_index_dance:%'")),
    "analysis": (("features", ""), ("embeddings", ""), ("loudness", ""), ("silences", ""),
                 ("waveforms", ""), ("vocals", ""), ("noise", ""),
                 ("pd_highlights", "manual = 0")),
    "user": (("tag_edits", ""), ("pd_highlights", "manual = 1"), ("play_log", "")),
}


def reset_database(groups) -> dict:
    """Empty the tables of the chosen `RESET_GROUPS` and VACUUM. The user's
    own rows are backed up first, whatever is picked; a failed backup resets
    nothing. The app's in-memory caches still hold the old rows, so it restarts
    afterwards. Returns {table: rows removed}."""
    unknown = set(groups) - RESET_GROUPS.keys()
    if unknown:
        raise ValueError(f"unknown reset parts: {sorted(unknown)}")
    backup_user_data(refresh=True)
    conn = _db()
    tables = {n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    removed: dict[str, int] = {}
    with bulk_writes_held():
        conn.execute("BEGIN IMMEDIATE")
        try:
            for group, parts in RESET_GROUPS.items():
                if group not in groups:
                    continue
                for table, where in parts:
                    if table in tables:
                        sql = f"DELETE FROM {table}" + (f" WHERE {where}" if where else "")
                        removed[table] = removed.get(table, 0) + conn.execute(sql).rowcount  # nosec B608: constant names
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        conn.execute("VACUUM")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    log.info("  🗑 Database reset\n"
             "    parts: %s\n"
             "    removed rows: %s", ", ".join(sorted(groups)),
             ", ".join(f"{t}={n:,}" for t, n in removed.items()))
    return removed


def db_maintenance() -> dict:
    """Reclaim database disk space: full orphan cleanup + VACUUM.

    Beyond `cleanup_orphans(prune_features=True)` this also prunes the OTHER
    content-addressed side tables (embeddings / loudness / pd_highlights / silences /
    waveforms / vocals / noise) whose
    fingerprint no live file references any more, then VACUUMs so the freed pages
    actually shrink the file on disk. Slow (stats every registered path, then
    rewrites the whole DB) — run it from an explicit maintenance action only.

    Returns {"removed": {table: count, …}, "size_before": bytes, "size_after": bytes}.

    Raises RuntimeError when most registered files look missing: that almost
    always means the music drive isn't mounted, and cleaning then would wipe the
    expensive cached analysis for the entire library.
    """
    conn = _db()
    size_before = audio_db_file().stat().st_size

    total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    missing = sum(1 for (p,) in conn.execute("SELECT path FROM files")
                  if not Path(p).exists())
    if total and missing > max(100, total // 2):
        raise RuntimeError(
            f"{missing:,} of {total:,} registered files are missing — is the music "
            "drive mounted? Cleanup aborted so the cached analysis isn't wiped.")

    # A running library scan waits meanwhile instead of keeping the write lock.
    with bulk_writes_held():
        removed = cleanup_orphans(prune_features=True)

        # Side tables keyed by content fingerprint (embeddings has one row per
        # fp+model; the others one per fp) — drop rows no live file points at.
        live_fps = {fp for (fp,) in conn.execute("SELECT DISTINCT fp FROM fingerprints")}
        for table in ("embeddings", "loudness", "pd_highlights", "silences", "waveforms",
                      "vocals", "noise"):
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                            (table,)).fetchone() is None:
                removed[table] = 0
                continue
            dead_fps = [fp for (fp,) in conn.execute(f"SELECT DISTINCT fp FROM {table}")  # nosec B608: constant names
                        if fp not in live_fps]
            before = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608: constant names
            conn.executemany(f"DELETE FROM {table} WHERE fp = ?",  # nosec B608: constant names
                             [(fp,) for fp in dead_fps])
            if table == "embeddings":
                # …and the vectors of a retired model, live track or not.
                conn.execute("DELETE FROM embeddings WHERE model NOT IN "
                             f"({', '.join('?' * len(EMBEDDING_MODELS))})",  # nosec B608: placeholders only
                             EMBEDDING_MODELS)
            removed[table] = before - conn.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608: constant names

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

        log.info("  🧹 VACUUM %s (%.1f MB) …", audio_db_file().name, size_before / 1e6)
        conn.execute("VACUUM")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    size_after = audio_db_file().stat().st_size
    log.info("  🧹 Database maintenance done:\n"
             "    size: %.1f MB → %.1f MB\n"
             "    removed rows: %s",
             size_before / 1e6, size_after / 1e6,
             ", ".join(f"{t}={n:,}" for t, n in removed.items()))
    return {"removed": removed, "size_before": size_before, "size_after": size_after}
