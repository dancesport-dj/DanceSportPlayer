"""📜 What actually ran: every title heard in playing mode, kept per evening.

The player records a title once it has played for 10 s (the point the deck
greys it). A run of plays with no gap over GAP_HOURS is one evening, so a party
that goes past midnight stays one. The report for a music rights society (GEMA
and the like) is a CSV of one evening.

How long a title ran is not recorded but worked out: until the next title
started, at most the track's own length. A cut at 1:30 reads 1:30, a title
followed by a break reads its full length.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile

from planner import i18n
from planner.music.db import _db
from planner.terms import dance_name

GAP_HOURS = 4
_COLS = "started_at, path, artist, title, dance, list_name, length, composer"

log = logging.getLogger("dancesport.play_log")


@dataclass(frozen=True)
class Play:
    started_at: dt.datetime
    path: str
    artist: str
    title: str
    dance: str
    list_name: str
    length: float
    composer: str = ""


@dataclass(frozen=True)
class Evening:
    start: dt.datetime    # the first title's start
    end: dt.datetime      # the last title's start
    count: int


def _stamp(when: dt.datetime) -> str:
    return when.replace(microsecond=0).isoformat()


def record(started_at: dt.datetime, path, artist: str, title: str, dance: str,
           list_name: str, length: float, composer: str = "") -> None:
    """Log one play. The same file at the same second is logged once."""
    _db().execute(f"INSERT OR IGNORE INTO play_log ({_COLS}) VALUES (?,?,?,?,?,?,?,?)",
                  (_stamp(started_at), str(path), artist or "", title or "",
                   dance or "", list_name or "", float(length or 0), composer or ""))


def composer_of(path) -> str:
    """The composer tag of the file (TCOM, or its FLAC/M4A twin), "" without
    one. No library row carries it, so the play reads it from the file."""
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        log.debug("📜 No composer read\n"
                  "file: %s", path, exc_info=True)
        return ""
    if audio is None or audio.tags is None:
        return ""
    return "; ".join(audio.tags.get("composer", []))


def evenings(gap_hours: float = GAP_HOURS) -> list[Evening]:
    """Every evening in the log, newest first."""
    gap = dt.timedelta(hours=gap_hours)
    out = []
    first = last = None
    count = 0
    for (raw,) in _db().execute("SELECT started_at FROM play_log ORDER BY started_at"):
        when = dt.datetime.fromisoformat(raw)
        if first is not None and last is not None and when - last > gap:
            out.append(Evening(first, last, count))
            first, count = None, 0
        first = first or when
        last = when
        count += 1
    if first is not None and last is not None:
        out.append(Evening(first, last, count))
    return out[::-1]


def plays(evening: Evening) -> list[Play]:
    """The titles of one evening, in the order they ran."""
    rows = _db().execute(
        f"SELECT {_COLS} FROM play_log WHERE started_at BETWEEN ? AND ? "  # nosec B608: constant names
        "ORDER BY started_at", (_stamp(evening.start), _stamp(evening.end)))
    return [Play(dt.datetime.fromisoformat(r[0]), r[1], r[2], r[3], r[4], r[5], r[6] or 0.0,
                 r[7] or "") for r in rows]


def delete(evening: Evening) -> None:
    _db().execute("DELETE FROM play_log WHERE started_at BETWEEN ? AND ?",
                  (_stamp(evening.start), _stamp(evening.end)))


def durations(plays_: list[Play]) -> list[float]:
    """Seconds each title ran: up to the next start, at most its own length."""
    out = []
    for i, p in enumerate(plays_):
        own = p.length or 0.0
        if i + 1 < len(plays_):
            gap = (plays_[i + 1].started_at - p.started_at).total_seconds()
            own = min(gap, own) if own else gap
        out.append(own)
    return out


def _mss(secs: float) -> str:
    s = int(round(secs))
    return f"{s // 60}:{s % 60:02d}"


def to_csv(plays_: list[Play], file: Path) -> None:
    """The evening as a `;`-separated UTF-8 file with BOM, so Excel opens it
    with the umlauts intact on a German Windows."""
    with Path(file).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([i18n.t(c) for c in
                    ("Date", "Start", "Artist", "Title", "Composer", "Dance", "List",
                     "Duration")])
        for p, secs in zip(plays_, durations(plays_), strict=True):
            w.writerow([p.started_at.date().isoformat(),
                        p.started_at.time().isoformat("seconds"),
                        p.artist, p.title, p.composer, dance_name(p.dance, p.dance) or "",
                        p.list_name, _mss(secs)])
