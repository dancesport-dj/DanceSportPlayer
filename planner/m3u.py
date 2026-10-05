"""M3U playlist writing & competition-import parsing.

Extracted from dancesport_planner.py (logical split): export_m3u / export_flat_m3u
and the round/heat-aware import_playlist_m3u that reconstructs a deck from a saved
.m3u (final-round backups → extra heats).
"""
import logging

from collections import Counter
from datetime import datetime
from pathlib import Path
import re
from collections.abc import Callable
from planner.config import (  # auto-resolved
    OUTPUT_DIR,
    replacing_text,
)
from planner.db import (  # auto-resolved
    AudioCache,
)
from planner.models import (  # auto-resolved
    DANCE_NAMES,
    GENRE_TO_DANCE,
    MusicEntry,
    Playlist,
    ROUND_NAMES,
    RoundConfig,
)
from planner.parsing import (  # auto-resolved
    _clean_title,
    _detect_bpm,
    _detect_dance,
    _fmt_bpm,
)
from planner.library import (  # auto-resolved
    MusicLibrary,
)
from planner.planned import path_key
from planner.paths import (  # auto-resolved
    foreign_name,
)
from planner.playlist_text import PlaylistEncodingError, read_playlist_text
from planner.warmup import (  # auto-resolved
    warmup_rounds,
)

log = logging.getLogger("dancesport.m3u")


# How many warm-up rounds a list has to fall into before it is read as one. A
# tournament tops out at the seven rounds ROUND_NAMES knows, so anything the
# competition naming can't name and that still cuts into this many rounds is an
# Eintanzen / party list — while a themed single pass through the dances stays
# below it and keeps its old naming.
_WARMUP_MIN_ROUNDS = 3


# ── M3U Export ─────────────────────────────────────────────────────────────────
def export_m3u(playlist: Playlist, dances: list[str], basename: str,
               dance_class: str = "C", timestamp: bool = True,
               progress_cb: Callable[[int, int, str], None] | None = None,
               out_path: Path | None = None,
               path_for: Callable[[Path], Path] | None = None) -> Path:
    """`path_for` maps each track path before it is written (the desk re-roots
    them under the Referenzpfad); None writes the paths as they are."""
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M_") if timestamp else ""
        out = OUTPUT_DIR / f"{ts}{basename}.m3u"

    total = sum(1 for heats in playlist.values() for heat in heats
                for e in heat if e is not None)
    done  = 0
    with replacing_text(out) as f:
        f.write("#EXTM3U\n")
        for round_name, heats in playlist.items():
            f.write(f"\n# ══ {round_name} ({len(heats)} {'Heat' if len(heats)==1 else 'Heats'}) ══\n")
            multi = len(heats) > 1
            for d_idx, dance in enumerate(dances):
                dn = DANCE_NAMES.get(dance, dance)
                f.write(f"\n# ── {dn} ──\n")
                for h_idx, heat in enumerate(heats, 1):
                    if multi:
                        f.write(f"# Heat {h_idx}\n")
                    entry = heat[d_idx]
                    if entry:
                        bpm_s = _fmt_bpm(entry.bpm, dance, dance_class)
                        f.write(f"#EXTINF:{entry.duration},{entry.title}{bpm_s}\n")
                        f.write(f"{path_for(entry.path) if path_for else entry.path}\n")
                        done += 1
                        if progress_cb:
                            progress_cb(done, total, entry.title)
                    else:
                        f.write("# (no song found)\n")
    return out


def export_flat_m3u(entries: list[MusicEntry], basename: str,
                    timestamp: bool = True,
                    progress_cb: Callable[[int, int, str], None] | None = None,
                    out_dir: Path | None = None,
                    out_path: Path | None = None,
                    path_for: Callable[[Path], Path] | None = None) -> Path:
    """Export a flat playlist – a simple ordered song list.
    `path_for` maps each track path before it is written, as in export_m3u.

    An Eintanzen / party list gets its ROUNDS written in as comments — the same
    'Standardrunde 1' / 'Lateinrunde 1' / 'Socialrunde 1' the panel heads its
    ─── strips with — because that is what the operator reads the printed file
    for. It is the one thing the flat file cannot say by itself: a party list
    has no heats and no draw, so the competition scaffolding `export_m3u`
    writes would only be noise. Anything shorter than `_WARMUP_MIN_ROUNDS`
    rounds is not a party list (a theme list, a wishlist) and goes out bare,
    exactly as before."""
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = Path(out_dir) if out_dir is not None else OUTPUT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M_") if timestamp else ""
        out = target_dir / f"{ts}{basename}.m3u"
    total = len(entries)
    round_at = _flat_round_starts(entries)
    with replacing_text(out) as f:
        f.write("#EXTM3U\n")
        for i, e in enumerate(entries, 1):
            name = round_at.get(i - 1)
            if name:
                f.write(f"\n# ── {name} ──\n")
            dn   = DANCE_NAMES.get(e.dance, e.dance or '')
            tag  = f" [{dn}]" if dn else ""
            yr   = f" ({e.year})" if e.year else ""
            f.write(f"#EXTINF:{e.duration},{e.title}{tag}{yr}\n")
            f.write(f"{path_for(e.path) if path_for else e.path}\n")
            if progress_cb:
                progress_cb(i, total, e.title)
    return out


def _flat_round_starts(entries: list[MusicEntry]) -> dict[int, str]:
    """{index of the first track of a round → round name} for a party list,
    empty for anything that does not read as one."""
    starts: dict[int, str] = {}
    at = 0
    for name, songs in warmup_rounds(entries, min_rounds=_WARMUP_MIN_ROUNDS):
        starts[at] = name
        at += len(songs)
    return starts


# ── Venue bundle (USB export): numbered per-playlist folder ────────────────────
def _index_prefix(i: int) -> str:
    """0_0_1-style track number (the M3U Copy Tool's underscore index format)."""
    return "_".join(f"{i:03d}")


def _safe_filename(name: str) -> str:
    """Strip filesystem-hostile characters from a title used as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    return re.sub(r"\s+", " ", name).strip()


_BPM_TAG_RE = re.compile(r"\s*\[(?:T(\d+)\*?|\?BPM)\]")


def numbered_folder_m3u(m3u_path: Path,
                        progress_cb: Callable[[int, int, str], None] | None = None,
                        ) -> tuple[list[Path], int]:
    """Turn the already-written M3U at `m3u_path` into a self-contained numbered
    folder (the 🧳 USB-export layout, matching the user's M3U Copy Tool): every
    referenced track is copied NEXT TO the M3U as ``0_0_1 - Title WW29.mp3`` —
    the index is the play order, the title comes from the #EXTINF line, and the
    trailing tag is the dance code + takt (dance from the ``# ── Dance ──``
    section header or the source filename; takt from the ``[T29]`` EXTINF tag
    or the source filename) — and the path line is rewritten to that bare
    filename. Sorted by name the folder plays in playlist order even WITHOUT
    the M3U (e.g. imported file-by-file on a USB player / UltraMixer). Missing
    files keep their original absolute line but still consume their index, so
    the numbering mirrors the playlist slots.
    Returns (copied target paths, missing count)."""
    import shutil

    folder = Path(m3u_path).parent
    lines = Path(m3u_path).read_text(encoding="utf-8").splitlines()
    total = sum(1 for ln in lines
                if ln.strip() and not ln.lstrip().startswith("#"))
    copied: list[Path] = []
    missing = 0
    idx = 0
    pending_title = ""
    cur_dance: str | None = None
    for i, raw in enumerate(lines):
        ln = raw.strip()
        if not ln:
            continue
        m = _IMPORT_EXTINF_RE.match(ln)
        if m:
            pending_title = m.group(2).strip()
            continue
        m = _IMPORT_DANCE_RE.match(ln)
        if m:
            cur_dance = _dance_from_header(m.group(1))
            continue
        if ln.startswith("#"):
            continue
        idx += 1
        src = Path(ln)
        raw_title = pending_title or _clean_title(src.stem) or src.stem
        pending_title = ""
        m = _BPM_TAG_RE.search(raw_title)
        title = _BPM_TAG_RE.sub("", raw_title).strip() or src.stem
        if progress_cb:
            progress_cb(idx, total, title)
        if not src.is_file():
            missing += 1
            continue
        bpm = (m.group(1) if m and m.group(1) else None) or _detect_bpm(src.name)
        dance = cur_dance or _detect_dance(src.name) or _detect_dance(title)
        tag = f" {dance or ''}{bpm or ''}" if (dance or bpm) else ""
        name = f"{_index_prefix(idx)} - {_safe_filename(title)}{tag}{src.suffix}"
        shutil.copy2(src, folder / name)
        copied.append(folder / name)
        lines[i] = name
    with replacing_text(Path(m3u_path)) as f:
        f.write("\n".join(lines) + "\n")
    return copied, missing


# ── Playlist import (existing M3U → editable grid) ─────────────────────────────
_IMPORT_ROUND_RE = re.compile(r'^#\s*═+\s*(.*?)\s*\(\s*\d+\s*Heats?\s*\)\s*═+\s*$',
                              re.IGNORECASE)


_IMPORT_DANCE_RE = re.compile(r'^#\s*─+\s*(.*?)\s*─+\s*$')


_IMPORT_HEAT_RE  = re.compile(r'^#\s*Heat\s*\d+\s*$', re.IGNORECASE)


_IMPORT_NOSONG_RE = re.compile(r'^#\s*\(\s*no song found\s*\)\s*$', re.IGNORECASE)


_IMPORT_EXTINF_RE = re.compile(r'^#EXTINF:\s*(-?\d+)\s*,(.*)$')


def _explicit_tier(name: str) -> str | None:
    """The tier a round name SAYS it is, or None when the name doesn't say.

    'Zwischenrunde' and 'Runde 2' name no tier — only where the round is called
    a final, a semifinal or a quarter/eighth-final does the name settle it."""
    n = name.lower()
    if 'halbfinal' in n or 'semifinal' in n or 'semi-final' in n or n.strip() == 'semi':
        return 'semi'
    if 'viertelfinal' in n or 'achtelfinal' in n:
        return 'early'
    if 'final' in n:
        return 'final'
    return None


def _tier_for_round_name(name: str) -> str:
    """Map a round display name (German) to a planner tier code."""
    return _explicit_tier(name) or 'early'


def _round_tiers(names: list[str]) -> list[str]:
    """One tier per round of an imported playlist, counted back from the end:
    final, semi, pre_semi, then early — the very same ladder the '6-3-2-1' heat
    pattern lays down in `rounds_from_pattern`. A name that says which round it
    is ('Semifinale', 'Viertelfinale') still wins over its position.

    Read off the names alone, a three-round import had no semifinal at all: the
    round before the final is called 'Zwischenrunde', which matches nothing, so
    it came in as 'early' and was re-rolled (↺) from early-round material — while
    the same event typed as 6-3-1 made it the semifinal. Same event, same tiers,
    however it reached the deck."""
    n = len(names)
    out = []
    for i, name in enumerate(names):
        by_position = ('final'    if i == n - 1 else
                       'semi'     if i == n - 2 else
                       'pre_semi' if i == n - 3 else
                       'early')
        out.append(_explicit_tier(name) or by_position)
    return out


def _dance_from_header(name: str) -> str | None:
    """Reverse-map a dance section header (e.g. 'Cha-Cha', 'Wiener Walzer') to a code."""
    code = GENRE_TO_DANCE.get(name.strip().lower())
    return code or _detect_dance(name)


def _entry_dance_for_import(entry: MusicEntry, extinf_title: str) -> str | None:
    """Best dance code for an entry: its own tag/filename detection, then the EXTINF
    label (flat exports write '… [Samba] (2007)')."""
    if entry.dance:
        return entry.dance
    for src in (entry.path.name, entry.title or "", extinf_title or ""):
        d = _detect_dance(src)
        if d:
            return d
    return None


# A line that names a root of its own — a drive (`F:`), a UNC share or a leading
# separator. It is never joined to the playlist's folder, even on a Mac, where
# `Path` does not see a Windows path as absolute.
_ROOTED_LINE_RE = re.compile(r"^([A-Za-z]:|[\\/])")


def _resolve_import_path(path_str: str, lib: MusicLibrary, cache: AudioCache,
                         extinf_title: str, remapper=None, base: Path | None = None,
                         ) -> tuple[MusicEntry, bool, Path | None]:
    """Resolve one M3U path line to a MusicEntry.

    Library hit (exact then case-insensitive) → reuse the live entry. Otherwise build
    an external entry from the file's tags. A path the machine that WROTE the list
    could resolve and this one cannot (`F:\\my music\\…` carried to a Mac, or to a PC
    keeping the library on another drive) is handed to `remapper` — the same re-rooting
    🧭 Fix paths uses, so it only ever answers with a file that is really there. If it
    is gone after all, fall back to a ghost entry (path + EXTINF title + filename-
    detected dance) so the slot is still editable.
    A relative line is relative to the playlist's folder `base` — the 🧳 USB
    bundle writes bare filenames — and quotes around a line are not part of it.
    Returns (entry, found_on_disk, re-rooted path or None)."""
    path_str = path_str.strip().strip('"')
    p = Path(path_str)
    if base is not None and not p.is_absolute() and not _ROOTED_LINE_RE.match(path_str):
        p = base / p
    target = str(p)
    for ent in lib.entries:
        if str(ent.path) == target:
            return ent, True, None
    tl = path_key(target)
    for ent in lib.entries:
        if path_key(ent.path) == tl:
            return ent, True, None
    try:
        if p.is_file():
            return lib.make_external_entry(p, cache), True, None
    except Exception:
        pass
    if remapper is not None:
        hit = remapper.remap(path_str)
        if hit is not None:
            hl = path_key(hit)
            for ent in lib.entries:
                if path_key(ent.path) == hl:
                    return ent, True, hit
            try:
                return lib.make_external_entry(hit, cache), True, hit
            except Exception:
                pass
    # The filename is cut by hand: on macOS a Windows path is ONE filename to
    # `Path`, so `p.stem` would title the slot with the whole backslash line and
    # the dance detection would read the folder names too.
    name = foreign_name(path_str) or p.name
    title = (extinf_title or "").strip() or Path(name).stem
    return MusicEntry(path=p, title=title, dance=_detect_dance(name)), False, None


def _segment_buckets(segment: list[tuple[str | None, MusicEntry]],
                     dances: list[str]) -> dict[str, list[MusicEntry]]:
    """Bucket one round-segment of (dance, entry) by dance. Entries with an unknown
    (None) dance can't be placed in a column → dropped from the grid."""
    buckets: dict[str, list[MusicEntry]] = {d: [] for d in dances}
    for dance, entry in segment:
        if dance in buckets:
            buckets[dance].append(entry)
    return buckets


def _segment_to_heats(segment: list[tuple[str | None, MusicEntry]],
                      dances: list[str]) -> list[list[MusicEntry | None]]:
    """Turn one round-segment of (dance, entry) into rectangular heats.

    Buckets entries by dance; the heat count is the deepest bucket, so a round carrying
    backup variants (e.g. two Sambas) simply widens to two heats, with the other dances'
    second heat left empty (None)."""
    buckets = _segment_buckets(segment, dances)
    heat_n = max((len(v) for v in buckets.values()), default=1) or 1
    heats: list[list[MusicEntry | None]] = []
    for h in range(heat_n):
        row: list[MusicEntry | None] = []
        for d in dances:
            col = buckets[d]
            row.append(col[h] if h < len(col) else None)
        heats.append(row)
    return heats


def _round_heats_and_backups(
    buckets: dict[str, list[MusicEntry]], dances: list[str], round_name: str
) -> tuple[list[list[MusicEntry | None]], dict[tuple[str, int, int], list[MusicEntry]]]:
    """Build any round's heats + a backups overlay.

    Every dance in a round shares the same heat count, so a lone dance carrying MORE
    songs than the rest (e.g. an extra Tango in the semifinal, or a couple of alternative
    Jives in the final) are alternatives, NOT reasons to widen every other dance with empty
    cells. So `base` = the heat depth most dances share (mode of the non-empty bucket
    sizes); each dance's entries beyond `base` stack as backups under its last primary
    heat. Returns (heats, backups) where backups is keyed
    {(round_name, h_idx, d_idx): [entry, …]} to match the GUI's dynamic backups map."""
    sizes = [len(buckets[d]) for d in dances if buckets[d]]
    base = max(1, Counter(sizes).most_common(1)[0][0]) if sizes else 1
    heats: list[list[MusicEntry | None]] = []
    for h in range(base):
        heats.append([buckets[d][h] if h < len(buckets[d]) else None for d in dances])
    backups: dict[tuple[str, int, int], list[MusicEntry]] = {}
    for d_idx, d in enumerate(dances):
        extra = buckets[d][base:]
        if extra:
            backups[(round_name, base - 1, d_idx)] = list(extra)
    return heats, backups


def _split_round_segments(
    seq: list[tuple[str | None, MusicEntry]]
) -> tuple[list[list[tuple[str | None, MusicEntry]]], list[str]]:
    """Split a flat (dance, entry) sequence into the round-segments it was played
    in, keeping the original order. Returns (segments, dance order).

    Merge consecutive same-dance tracks into runs (blocks). Competition M3Us come in
    two layouts and this handles BOTH:
      • ROUND-ROBIN — one heat of each dance per cycle: LW TG WW SF QS | LW TG WW SF QS
        Adjacent dances differ, so every run is size 1 → identical to the old per-track
        split (a new round each time the cycle returns to a dance).
      • GROUPED — each round lists ALL heats of a dance as one block:
        LW×7 TG×7 WW×7 SF×7 QS×7 | LW×… …  Each dance block is one run, so a round spans
        one block per dance and its heat count = the block depth (a 7-song LW block → 7
        heats). The old per-track split mis-saw every repeated LW as a new round and
        then folded everything into one giant round.
    An undetected (None) track sitting INSIDE a block is kept in that block so a stray
    unrecognised title doesn't break the round apart — but it KEEPS its own None dance
    (the run's leading dance is only the block label, not re-stamped onto the entry), so
    `_segment_to_heats` drops it from the grid instead of mis-filling a real dance's heat."""
    runs: list[tuple[str | None, list[tuple[str | None, MusicEntry]]]] = []
    for dance, entry in seq:
        if runs and runs[-1][0] is not None and (dance is None or dance == runs[-1][0]):
            runs[-1][1].append((dance, entry))
        else:
            runs.append((dance, [(dance, entry)]))

    # Split runs into passes (rounds): a new pass begins when a dance's block reappears
    # after it already closed within the current pass.
    dances: list[str] = []
    passes: list[list[tuple[str | None, MusicEntry]]] = []
    cur: list[tuple[str | None, MusicEntry]] = []
    cur_dances: set = set()
    for run_dance, run_items in runs:
        if run_dance is not None and run_dance in cur_dances:
            passes.append(cur)
            cur = []
            cur_dances = set()
        cur.extend(run_items)  # each item keeps its ORIGINAL dance (None stays None)
        if run_dance is not None:
            cur_dances.add(run_dance)
            if run_dance not in dances:
                dances.append(run_dance)
    if cur:
        passes.append(cur)

    # Fold a short trailing pass (final backups) into the previous round-segment.
    threshold = max(2, (len(dances) // 2) + 1) if dances else 1
    segments: list[list[tuple[str | None, MusicEntry]]] = []
    for p in passes:
        distinct = len({d for d, _ in p if d is not None})
        if segments and distinct < threshold:
            segments[-1].extend(p)
        else:
            segments.append(list(p))
    return segments, dances


def _named_round_segments(
    seq: list[tuple[str | None, MusicEntry]]
) -> tuple[list[list[tuple[str | None, MusicEntry]]], list[str], list[str]]:
    """(segments, round names, dance order) for a sequence nothing has named.

    Full passes through the dance set are the rounds of a competition. When
    there are more of them than a tournament has rounds, the list is not a draw
    at all but a warm-up / party one — so it is re-cut into the rounds it was
    built from and named after them ('Standardrunde 1', 'Lateinrunde 1', …)
    instead of being numbered 'Runde 1…n'. A warm-up round holding nothing the
    grid has a column for (a Socialrunde: Discofox and Salsa are no competition
    dances) is dropped rather than shown as an empty round."""
    segments, dances = _split_round_segments(seq)
    names = ROUND_NAMES.get(len(segments))
    if names:
        return segments, list(names), dances

    wu_segments: list[list[tuple[str | None, MusicEntry]]] = []
    wu_names: list[str] = []
    at = 0
    for name, songs in warmup_rounds([e for _d, e in seq],
                                     min_rounds=_WARMUP_MIN_ROUNDS):
        seg = seq[at:at + len(songs)]
        at += len(songs)
        if any(d for d, _e in seg):
            wu_segments.append(seg)
            wu_names.append(name)
    if wu_segments:
        return wu_segments, wu_names, dances

    return segments, [f"Runde {i + 1}" for i in range(len(segments))], dances


def _segments_by_section(
    seq: list[tuple[str | None, MusicEntry]], labels: list[str]
) -> tuple[list[list[tuple[str | None, MusicEntry]]], list[str], list[str]]:
    """Cut a (dance, entry) sequence at every change of the round it is IN.

    For a list that already knows its rounds (a player's running order heads its
    ─── strips with them): the names are taken, not guessed, so a re-built grid
    shows the same rounds the operator was looking at. `labels` names the round
    of each entry POSITIONALLY — an evening can play the same file in two rounds,
    and then a path could not say which one. Returns (segments, round names,
    dance order); a stretch nothing names becomes 'Runde n' by its position, and
    a name that comes back later is kept apart (' (2)') so two rounds never
    collapse into one."""
    segments: list[list[tuple[str | None, MusicEntry]]] = []
    names: list[str] = []
    dances: list[str] = []
    cur = None
    for (dance, entry), name in zip(seq, labels):
        if not segments or name != cur:
            segments.append([])
            names.append(name)
            cur = name
        segments[-1].append((dance, entry))
        if dance is not None and dance not in dances:
            dances.append(dance)
    seen: dict[str, int] = {}
    for i, name in enumerate(names):
        name = name or f"Runde {i + 1}"
        seen[name] = seen.get(name, 0) + 1
        names[i] = name if seen[name] == 1 else f"{name} ({seen[name]})"
    return segments, names, dances


def _grid_from_segments(
    segments: list[list[tuple[str | None, MusicEntry]]],
    names: list[str], dances: list[str]
) -> tuple[dict[str, list[list[MusicEntry | None]]], list[RoundConfig], dict[tuple[str, int, int], list[MusicEntry]]]:
    """Round-segments → (playlist grid, RoundConfigs, backups overlay).

    Every round (not just the final) detects backups: a lone dance with one extra
    song stacks the surplus as a backup instead of widening the whole round with
    empty cells — e.g. a 3rd Tango in a 2-heat semifinal becomes a Tango backup."""
    tiers = _round_tiers(names)
    playlist: dict[str, list[list[MusicEntry | None]]] = {}
    rounds: list[RoundConfig] = []
    backups: dict[tuple[str, int, int], list[MusicEntry]] = {}
    for idx, (name, seg) in enumerate(zip(names, segments)):
        heats, seg_backups = _round_heats_and_backups(
            _segment_buckets(seg, dances), dances, name)
        backups.update(seg_backups)
        playlist[name] = heats
        rounds.append(RoundConfig(name=name, heats=len(heats), tier=tiers[idx]))
    return playlist, rounds, backups


def grid_from_running_order(
    entries: list[MusicEntry], sections: list[str] | None = None
) -> dict:
    """Rebuild a round/heat grid out of a flat running order.

    The way back out of a freely draggable list into a planned draw: every
    track's dance is detected and the order is cut into rounds — by `sections`
    (the round name of each entry, positionally) when the list carries them,
    otherwise by the same full-pass heuristic that imports a marker-less .m3u.
    Nothing is re-sorted, so the songs and their order survive the trip. A track
    whose dance nothing can name has no column to sit in and is left out;
    `unknown` counts those, so a caller can say so instead of losing them
    silently.

    Returns {playlist, dances, rounds, backups, unknown, total}."""
    seq = [(_entry_dance_for_import(e, ""), e) for e in entries]
    unknown = sum(1 for d, _e in seq if d is None)
    if sections and any(sections):
        segments, names, dances = _segments_by_section(seq, list(sections))
    else:
        segments, names, dances = _named_round_segments(seq)
    playlist, rounds, backups = _grid_from_segments(segments, names, dances)
    total = (sum(1 for hl in playlist.values() for h in hl for e in h if e is not None)
             + sum(len(v) for v in backups.values()))
    return {"playlist": playlist, "dances": dances, "rounds": rounds,
            "backups": backups, "unknown": unknown, "total": total}


def running_order_rounds(
    entries: list[MusicEntry], *, warmup: bool = True
) -> list[tuple[str, list[MusicEntry]]]:
    """Split a flat running order into the rounds it plays out, as
    [(round name, entries), …] in the ORDER GIVEN — the list is what is being
    played, so nothing is regrouped, only cut.

    Used to head a player's running order with 'Vorrunde' / 'Zwischenrunde' /
    'Finale' instead of a plain dance grouping. A list that runs through the
    dances all evening is no tournament — more passes than a tournament has
    rounds — but it is not nameless either: it is a warm-up or a party list, and
    those are cut into the 'Standardrunde 1' / 'Lateinrunde 1' / 'Socialrunde 1'
    rounds they were built from.

    `warmup=False` asks the narrower question — is this a COMPETITION running
    order? — for the caller that has its own warm-up cut and only wants to know
    whether to reach for it instead. Either way: empty when the list reads as
    neither, e.g. a single pass over the dances."""
    seq = [(_entry_dance_for_import(e, ""), e) for e in entries]
    segments, _dances = _split_round_segments(seq)
    names = ROUND_NAMES.get(len(segments)) if len(segments) > 1 else None
    if not names:
        return warmup_rounds(entries, min_rounds=_WARMUP_MIN_ROUNDS) if warmup else []
    return [(name, [e for _d, e in seg]) for name, seg in zip(names, segments)]


def m3u_marker_rounds_in_order(m3u_path) -> list[tuple[str, str]]:
    """(track path lower-cased, round name) per marked track line, in FILE order.

    The reading a per-ROW view needs: the same file may be listed in two rounds —
    a paso doble played again in the semifinal — and then the path alone no
    longer says which round a given line belongs to."""
    try:
        lines = read_playlist_text(m3u_path)[0].splitlines()
    except OSError:
        return []
    except PlaylistEncodingError as exc:
        log.warning("⚠️ Playlist not read\n"
                    "file: %s\n"
                    "reason: %s", m3u_path, exc)
        return []
    out: list[tuple[str, str]] = []
    cur = ""
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        m = _IMPORT_ROUND_RE.match(ln)
        if m:
            cur = m.group(1).strip()
            continue
        if ln.startswith('#') or not cur:
            continue
        out.append((path_key(ln.strip('"')), cur))
    return out


def m3u_marker_rounds(m3u_path) -> dict[str, str]:
    """Round name per track path (lower-cased), read from the '# ══ Round ══'
    markers this app writes into its own exports. Empty for a file without them,
    which is the signal to derive the rounds from the order instead."""
    out: dict[str, str] = {}
    for path, name in m3u_marker_rounds_in_order(m3u_path):
        out.setdefault(path, name)
    return out


def read_m3u_tracks(m3u_path) -> list[tuple[Path, str]]:
    """The tracks of an .m3u as (path, #EXTINF title), in FILE order.

    The plain reading of a playlist file — no grid, no rounds, no library
    lookup: what it lists, in the order it lists it. Empty when the file can't
    be read at all, so a browsing view can show it as empty rather than fail.
    """
    try:
        lines = read_playlist_text(m3u_path)[0].splitlines()
    except OSError:
        return []
    except PlaylistEncodingError as exc:
        log.warning("⚠️ Playlist not read\n"
                    "file: %s\n"
                    "reason: %s", m3u_path, exc)
        return []
    out: list[tuple[Path, str]] = []
    title = ""
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        m = _IMPORT_EXTINF_RE.match(ln)
        if m:
            title = m.group(2).strip()
            continue
        if ln.startswith('#'):
            continue
        out.append((Path(ln.strip('"')), title))
        title = ""
    return out


def import_playlist_m3u(m3u_path, lib: MusicLibrary, cache: AudioCache,
                        progress_cb: Callable[[int, int, str], None] | None = None,
                        remapper=None) -> dict:
    """Load an existing .m3u into the structured grid model so it can be edited.

    Two strategies, picked automatically:
      • Files exported by THIS app carry markers (# ══ Round ══ / # ── Dance ──) →
        rounds, dances and heats are reconstructed exactly. A dance that lists more
        songs than the others (final backup variants) just widens that round's heats.
      • Arbitrary M3Us (UltraMixer, hand-made) → the dance of every track is detected,
        the sequence is split into rounds by full passes through the dance set, and a
        short trailing run of repeats (the final's backups) folds into the last round
        as extra heats.

    `remapper` (a `planner.paths.PathRemapper`, optional) re-roots the lines this
    machine cannot resolve — a playlist written on another PC names the library at
    ITS drive, and on a Mac none of `F:\\my music\\…` can exist. What it re-rooted
    comes back as `remapped`: (line as written, file found instead) per track, so
    the import can report what it changed instead of doing it silently.

    Returns {playlist, dances, rounds (List[RoundConfig]), dance_class, structured,
    missing, unknown, total, remapped, raw, dupes, dropped}. The last three are the
    accounting: `raw` is how many tracks the FILE listed (the number the progress
    bar counted up to), `dupes` how many of those lines repeat a path listed
    earlier, `dropped` how many danceable tracks the round structure could not
    place. raw - unknown - dropped == total, so a grid that comes out smaller
    than the file can always say where the rest of it went."""
    lines = read_playlist_text(m3u_path)[0].splitlines()
    base = Path(m3u_path).parent
    structured = any(_IMPORT_ROUND_RE.match(ln.strip()) for ln in lines)
    missing = 0
    unknown = 0
    remapped: list[tuple[str, Path]] = []   # (line as written, file found instead)

    # Progress reporting: the slow part is resolving each track (tag/cache reads), so
    # count the path lines upfront and tick after every resolve.
    path_lines = [ln.strip() for ln in lines
                  if ln.strip() and not ln.strip().startswith('#')]
    total_tracks = len(path_lines)
    seen_paths: set[str] = set()
    dupes = 0
    for _ln in path_lines:
        key = _ln.strip('"').lower()
        if key in seen_paths:
            dupes += 1
        seen_paths.add(key)
    _done = 0

    def _accounting(placed: int) -> dict:
        """What the file listed, and where the difference to the grid went."""
        return {"raw": total_tracks, "dupes": dupes,
                "dropped": max(0, total_tracks - unknown - placed)}

    def _tick(name: str = ""):
        nonlocal _done
        _done += 1
        if progress_cb:
            progress_cb(_done, total_tracks, name)

    # round_name → {dance_code: [entry|None per heat-slot]}, preserving order
    rounds_ord: list[tuple[str, dict[str, list[MusicEntry | None]]]] = []
    dance_order: list[str] = []

    def _note_dance(code: str | None):
        if code and code not in dance_order:
            dance_order.append(code)

    if structured:
        cur_round: dict[str, list[MusicEntry | None]] | None = None
        cur_dance: str | None = None
        pending_title = ""
        for raw in lines:
            ln = raw.strip()
            if not ln:
                continue
            m = _IMPORT_ROUND_RE.match(ln)
            if m:
                name = m.group(1).strip()
                cur_round = {}
                cur_dance = None
                rounds_ord.append((name, cur_round))
                continue
            m = _IMPORT_DANCE_RE.match(ln)
            if m and cur_round is not None:
                cur_dance = _dance_from_header(m.group(1))
                _note_dance(cur_dance)
                if cur_dance and cur_dance not in cur_round:
                    cur_round[cur_dance] = []
                continue
            if _IMPORT_HEAT_RE.match(ln):
                continue
            if _IMPORT_NOSONG_RE.match(ln):
                if cur_round is not None and cur_dance:
                    cur_round[cur_dance].append(None)
                continue
            m = _IMPORT_EXTINF_RE.match(ln)
            if m:
                pending_title = m.group(2).strip()
                continue
            if ln.startswith('#'):
                continue
            # A real path line.
            entry, found, hit = _resolve_import_path(ln, lib, cache,
                                                     pending_title, remapper, base)
            _tick(entry.title if entry else ln)
            if hit is not None:
                remapped.append((ln, hit))
            if not found:
                missing += 1
            pending_title = ""
            if cur_round is None:
                # stray track before any header → start a generic round
                cur_round = {}
                rounds_ord.append(("Imported", cur_round))
            dance = cur_dance or _entry_dance_for_import(entry, "")
            if dance is None:
                unknown += 1
                continue
            _note_dance(dance)
            cur_round.setdefault(dance, []).append(entry)

        dances = dance_order
        playlist: dict[str, list[list[MusicEntry | None]]] = {}
        rounds: list[RoundConfig] = []
        tiers = _round_tiers([name for name, _ in rounds_ord])
        for (name, dmap), tier in zip(rounds_ord, tiers):
            heat_n = max((len(v) for v in dmap.values()), default=1) or 1
            heats: list[list[MusicEntry | None]] = []
            for h in range(heat_n):
                row = [dmap.get(d, [])[h] if h < len(dmap.get(d, [])) else None
                       for d in dances]
                heats.append(row)
            playlist[name] = heats
            rounds.append(RoundConfig(name=name, heats=heat_n, tier=tier))
        total = sum(1 for hl in playlist.values() for h in hl for e in h if e is not None)
        return {"playlist": playlist, "dances": dances, "rounds": rounds,
                "dance_class": "S", "structured": True, "backups": {},
                "missing": missing, "unknown": unknown, "total": total,
                "remapped": remapped, **_accounting(total)}

    # ── Heuristic parse (no markers) ────────────────────────────────────────────
    seq: list[tuple[str | None, MusicEntry]] = []
    pending_title = ""
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        m = _IMPORT_EXTINF_RE.match(ln)
        if m:
            pending_title = m.group(2).strip()
            continue
        if ln.startswith('#'):
            continue
        entry, found, hit = _resolve_import_path(ln, lib, cache,
                                                 pending_title, remapper, base)
        _tick(entry.title if entry else ln)
        if hit is not None:
            remapped.append((ln, hit))
        if not found:
            missing += 1
        dance = _entry_dance_for_import(entry, pending_title)
        pending_title = ""
        if dance is None:
            unknown += 1
        seq.append((dance, entry))

    segments, names, dances = _named_round_segments(seq)
    playlist, rounds, backups = _grid_from_segments(segments, names, dances)
    total = (sum(1 for hl in playlist.values() for h in hl for e in h if e is not None)
             + sum(len(v) for v in backups.values()))
    return {"playlist": playlist, "dances": dances, "rounds": rounds,
            "dance_class": "S", "structured": False, "backups": backups,
            "missing": missing, "unknown": unknown, "total": total,
            "remapped": remapped, **_accounting(total)}
