#!/usr/bin/env python3
"""Library gap statistics — where the tournament pools run thin.

One row per dance × start class (Standard + Latin): how many tracks the
suggester can actually draw from (style folder, tournament tempo, class tags),
how many pass the 'proven' filter, the tempo-compliance rate, and staleness.

There is no as-played log, so staleness is derived from what IS known:
- never played = popularity 0 (the track appears in no tournament M3U at all)
- stale = last playlist it appeared in dates from ≥ `stale_years` ago, where
  the year is parsed from the playlist's path (event folders like
  'Turnier 2019 …'); tracks that were played but carry no dateable playlist
  get the benefit of the doubt and do NOT count as stale.
"""

from datetime import date

from planner.library import playlist_year
from planner.models import (
    BELOW_TEMPO_EXT,
    DANCE_NAMES,
    DEFAULT_DANCES,
    TEMPO_RANGES,
    is_non_turnier,
)
from planner.scoring import _PROVEN_MIN_POP
from planner.warmup import entry_in_style

# A 6-3-2-1 competition needs 12 distinct tracks per dance; below these floors
# a dance × class combination counts as a gap worth shopping for.
GAP_MIN_POOL = 15
GAP_MIN_PROVEN = 12


def last_played_year(lib, entry) -> int | None:
    """Newest 4-digit year found in the paths of the playlists this entry
    appears in — a rough 'last played' date. None when nothing is dateable.

    A scanned library has this on the entry already (`_apply_popularity`); the
    walk is only for entries that never went through it."""
    cached = getattr(entry, "last_played", None)
    if cached:
        return cached
    years = [y for y in (playlist_year(str(p))
                         for p in lib._playlists_for(entry)) if y]
    return max(years) if years else None


def gap_stats(lib, stale_years: int = 3,
              today_year: int | None = None) -> list[dict]:
    """One stats row per style × class × dance (mirrors `_get_pool` filters).

    Row keys: style, cls, dance, lo, hi (takt range), total (in style, non-
    xmas, tournament folders), pool (in tempo + class tag ok), tempo_known /
    tempo_ok (only tracks with a takt in the name), proven, fresh, never,
    stale (see module docstring).
    """
    cutoff = (today_year or date.today().year) - stale_years
    year_cache: dict = {}
    rows: list[dict] = []
    for style in ("Standard", "Latin"):
        for cls in ("D", "C", "B", "A", "S"):
            for dance in DEFAULT_DANCES[style][cls]:
                base = [e for e in lib.by_dance(dance)
                        if not e.is_xmas and not is_non_turnier(e)
                        and entry_in_style(e, style)]
                lo, hi = TEMPO_RANGES.get(dance, {}).get(cls, (20, 70))
                ext = BELOW_TEMPO_EXT.get(dance, 0)
                known = [e for e in base if e.bpm is not None]
                tempo_ok = [e for e in known if (lo - ext) <= e.bpm <= hi]
                in_tempo = [e for e in base
                            if e.bpm is None or (lo - ext) <= e.bpm <= hi]
                pool = [e for e in in_tempo
                        if not e.classes_ok or cls in e.classes_ok]
                proven = sum(1 for e in pool if e.popularity >= _PROVEN_MIN_POP)
                never = sum(1 for e in pool if e.popularity == 0)
                stale = 0
                for e in pool:
                    if e.popularity == 0:
                        stale += 1
                        continue
                    key = id(e)
                    if key not in year_cache:
                        year_cache[key] = last_played_year(lib, e)
                    y = year_cache[key]
                    if y is not None and y <= cutoff:
                        stale += 1
                rows.append(dict(
                    style=style, cls=cls, dance=dance, lo=lo, hi=hi,
                    total=len(base), pool=len(pool),
                    tempo_known=len(known), tempo_ok=len(tempo_ok),
                    proven=proven, fresh=len(pool) - proven,
                    never=never, stale=stale,
                ))
    return rows


def gap_reasons(row: dict) -> list[str]:
    """Why this dance × class is a gap — empty list when the pool is healthy."""
    out = []
    if row["pool"] < GAP_MIN_POOL:
        out.append(f"pool only {row['pool']} tracks (want ≥ {GAP_MIN_POOL})")
    if row["proven"] < GAP_MIN_PROVEN:
        out.append(f"only {row['proven']} proven "
                   f"(a 6-3-2-1 needs {GAP_MIN_PROVEN})")
    return out


def ai_prompt(row: dict) -> str:
    """Seed prompt for the AI-suggestions dialog, phrased around the gap."""
    return (f"fresh {row['cls']}-class {DANCE_NAMES.get(row['dance'], row['dance'])} "
            f"tournament tracks at {row['lo']}–{row['hi']} bars/min")


def shopping_list(rows: list[dict]) -> list[str]:
    """Human-readable lines for every gap row — the export payload."""
    out = []
    for r in rows:
        reasons = gap_reasons(r)
        if reasons:
            out.append(f"{r['style']} {r['cls']}: "
                       f"{DANCE_NAMES.get(r['dance'], r['dance'])} ({r['dance']}, "
                       f"{r['lo']}–{r['hi']} TPM) — " + "; ".join(reasons))
    return out
