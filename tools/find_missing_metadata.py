#!/usr/bin/env python3
"""Find indexed library tracks that are missing tempo (speed) or dance (genre).

Reads the app's content-addressed scan index (`scan_meta` in audio_features.db)
and reports every cached track where:
  • no tempo could be read at all — neither a takt parsed from the file name/tag
    (the `bpm` column) nor a measured tempo (librosa `features.bpm`), and
  • the dance / genre is unknown (empty `dance`) — limited to Standard/Latin
    tournament folders (standardcd / lateincd), since social-dance 'Others',
    anthems and background tracks legitimately have no Standard/Latin dance.

A softer bucket lists tracks whose takt label is missing but a measured tempo
exists (so the library still shows a speed, just not the file's own label).

By default only the Standard/Latin tournament folders (standardcd / lateincd)
are scanned; every social-dance folder (salsa, bachata, forró, …) is ignored,
since those carry no Standard/Latin takt or dance. Pass --all to scan every
folder. Tracks under the hymnen / special / forró folders are always skipped —
they are anthems, background and social-dance material that don't belong here.

For every listed track a Casa Musica single-tracks search link is added so the
speed/genre can be looked up by hand. (Casa Musica sits behind Cloudflare's
managed challenge — every scripted request gets a 403 "Just a moment…" page —
so the page can't be scraped from here; the clickable search URL is the next
best thing: open it and read the speed off the matching album.)

Read-only — nothing in the database is modified.

Run:  .venv\\Scripts\\python.exe -m tools.find_missing_metadata [--all] [--save report.txt]
"""
import io
import re
import sys
from pathlib import PurePath
from urllib.parse import quote_plus

# Windows console is cp1252; force UTF-8 so dance/title emojis don't crash.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from planner import db as db
from planner.db import _row_to_meta, _META_COLS, _BEATS_PER_BAR
from planner.models import STYLE_FOLDERS
from planner.parsing import _detect_bpm_tagged

CASA_SEARCH = "https://casa-musica.com/de/23-single-tracks?title={}"

# Default: only look at the Standard/Latin tournament folders (standardcd /
# lateincd) and ignore every social-dance folder (salsa, bachata, forró, …) —
# those legitimately have no Standard/Latin takt or dance, so they'd only add
# noise. Pass --all on the command line to scan every folder instead.
TOURNAMENT_ONLY = True

# Standard/Latin tournament folders (standardcd / lateincd). A missing dance is
# only worth a lookup here — social-dance 'Others' (salsa, forró, boogie …),
# anthems and background tracks legitimately carry no Standard/Latin dance.
_TOURNAMENT_FOLDERS = {f.lower() for fs in STYLE_FOLDERS.values() for f in fs}


def is_tournament_path(path: str) -> bool:
    """True when the file lives under a Standard/Latin tournament folder."""
    return any(p.lower() in _TOURNAMENT_FOLDERS for p in PurePath(path).parts)


# Folders that are pure noise for this report and are dropped from every bucket:
# anthems (hymnen), the 'special' umbrella (background, hymns, …) and the forró
# social-dance folder. Matched case-insensitively as exact path segments.
_SKIP_FOLDERS = {"hymnen", "special", "forro"}


def is_skipped_path(path: str) -> bool:
    """True when the file sits under a skipped folder (hymnen / special / forró)."""
    return any(p.lower() in _SKIP_FOLDERS for p in PurePath(path).parts)


# Leading track/disc numbers to drop from a search tag: one or more 1–3 digit
# groups (space-separated), the run ending in at least one space/dash/dot, and
# only when a real (letter-starting) title follows. So "02 04 Ta Me Mo Shui",
# "09 11-Open Up" and "215-DJ Rico" lose their prefix, while "5-10-15 Hours"
# (numbers dash-glued) and "2raumwohnung" (digit glued to the word) are kept.
_TRACK_NUM_RE = re.compile(r"^\d{1,3}(?: +\d{1,3})*[ .-]+(?=[^\W\d_])")


def search_title(title: str) -> str:
    """Title cleaned for searching: leading track/disc numbers stripped."""
    return _TRACK_NUM_RE.sub("", title.strip())


def casa_url(title: str) -> str:
    """Casa Musica single-tracks search link for a title (track numbers stripped,
    spaces → '+'), or '' when there's nothing searchable to look up."""
    title = search_title(title or "")
    if not title or title == "(untitled)":
        return ""
    return CASA_SEARCH.format(quote_plus(title))


def measured_bpm_by_fp(conn) -> dict:
    """fingerprint → measured tempo (beats/min) from the audio analysis."""
    return {fp: bpm for fp, bpm in conn.execute("SELECT fp, bpm FROM features")}


def path_by_fp(conn) -> dict:
    """fingerprint → one on-disk path. Byte-identical copies share a fingerprint,
    so the same track is often indexed from more than one drive (the C: mirror and
    the F: library root). Prefer the F: copy for a consistent display, else fall
    back to the first path seen."""
    out = {}
    for fp, path in conn.execute(
            "SELECT fpr.fp, f.path FROM fingerprints fpr "
            "JOIN files f ON f.id = fpr.file_id"):
        cur = out.get(fp)
        if cur is None or (not cur.upper().startswith("F:")
                           and path.upper().startswith("F:")):
            out[fp] = path
    return out


def scan_rows(conn):
    """Yield (fingerprint, stem, metadata-dict) for every indexed track.
    `scan_meta.ckey` is '{fingerprint}::{filename stem}' (a fingerprint never
    contains '::', so a single split is safe)."""
    cols = ",".join(_META_COLS)
    for row in conn.execute(f"SELECT ckey, {cols} FROM scan_meta"):
        fp, _, stem = row[0].partition("::")
        yield fp, stem, _row_to_meta(row[1:])


def main() -> None:
    save_to = None
    if "--save" in sys.argv:
        save_to = sys.argv[sys.argv.index("--save") + 1]
    tournament_only = TOURNAMENT_ONLY and "--all" not in sys.argv

    conn = db._db()
    measured = measured_bpm_by_fp(conn)
    paths = path_by_fp(conn)

    no_tempo = []        # no takt label AND no measured tempo
    no_genre = []        # no dance
    takt_missing = []    # no takt label, but a measured tempo exists
    total = 0
    skipped = 0          # under a skipped folder (hymnen / special / forró)
    non_tournament = 0   # outside standardcd / lateincd (when --all not given)

    for fp, stem, m in scan_rows(conn):
        total += 1
        path = paths.get(fp, "(file not currently on disk)")
        if is_skipped_path(path):
            skipped += 1
            continue
        if tournament_only and not is_tournament_path(path):
            non_tournament += 1
            continue
        # Re-detect the takt from the name/title tag rather than trusting the
        # cached `bpm` column: entries scanned before a detector improvement keep
        # a stale None there (e.g. '(58VW)', '(29 SF)', '(29W)' — number-before-code
        # labels), and the cache isn't refreshed until the file itself changes.
        label_bpm = m.get("bpm") or _detect_bpm_tagged(stem, m.get("tag_title")) or 0
        meas = measured.get(fp) or 0
        dance = (m.get("dance") or "").strip()
        title = m.get("title") or stem or "(untitled)"

        if not label_bpm and not meas:
            no_tempo.append((title, path))
        elif not label_bpm:
            # measured tempo is musical beats/min; the library labels are TAKT
            # (bars/min) = beats/min ÷ beats-per-bar, so show both when the dance
            # code is known (no code → can't convert, bpm only).
            bpb = _BEATS_PER_BAR.get(dance)
            takt = round(meas / bpb, 1) if bpb else 0   # 0 = unknown (no dance code)
            takt_missing.append((title, round(meas), takt, path))
        if not dance and is_tournament_path(path):
            no_genre.append((title, path))

    lines = []
    lines.append(f"📚 Indexed tracks scanned: {total}")
    if tournament_only:
        lines.append(f"   🩰 ignored (outside standardcd / lateincd):  {non_tournament}")
    lines.append(f"   🚫 skipped (hymnen / special / forró):      {skipped}")
    lines.append(f"   ⚡ no tempo at all (no takt + no measured): {len(no_tempo)}")
    lines.append(f"   💃 no dance / genre (Standard/Latin):        {len(no_genre)}")
    lines.append(f"   🏷️  takt label missing (measured fallback):  {len(takt_missing)}")
    lines.append("")

    def block(header, rows, fmt):
        out = [header, "-" * len(header)]
        if not rows:
            out.append("  ✅ none")
        else:
            out += [fmt(r) for r in sorted(rows)]
        out.append("")
        return out

    def link_line(title):
        url = casa_url(title)
        return f"\n      🔎 {url}" if url else ""

    def takt_str(t):
        """' ≈ 29,5 takt/min' (1 decimal, German comma) or '' when unknown."""
        return f" ≈ {t:.1f} takt/min".replace(".", ",") if t else ""

    lines += block("⚡ NO TEMPO COULD BE READ", no_tempo,
                   lambda r: f"  {r[0]}\n      {r[1]}{link_line(r[0])}")
    lines += block("💃 NO DANCE / GENRE (Standard/Latin tournament folders)", no_genre,
                   lambda r: f"  {r[0]}\n      {r[1]}{link_line(r[0])}")
    lines += block("🏷️ TAKT LABEL MISSING (measured tempo shown)", takt_missing,
                   lambda r: f"  {r[0]}  (~{r[1]} bpm{takt_str(r[2])} measured)"
                             f"\n      {r[3]}{link_line(r[0])}")

    report = "\n".join(lines)
    print(report)
    if save_to:
        with open(save_to, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"\n💾 Saved report to {save_to}")


if __name__ == "__main__":
    main()
