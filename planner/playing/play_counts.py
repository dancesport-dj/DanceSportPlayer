"""🔁 How often each title has played today, whichever list played it.

Read off the 📜 play log, so a play is what the log calls one (heard 10 s in
playing mode). "Today" is the last 24 hours (Marcel: "play count for day is
24h not 4h"), not the log's evening: a play stops counting a day after it ran.
Kept by file, not by list: the same track played from deck A and from the
party list counts twice.

A reset only moves the point the counting starts from (kept in app_meta, so a
restart does not bring the old counts back). The log itself — the report for
the music rights society — stays as it is.
"""

import datetime as dt

from planner.music.db import _db
from planner.playlist.planned import path_key

DAY = dt.timedelta(hours=24)
_RESET_KEY = "play_counts_reset"

_plays: dict[str, list[dt.datetime]] = {}   # path key → when it was heard

def clear() -> None:
    """Forget every count (the window starting over, or a test)."""
    _plays.clear()


def load(now: dt.datetime | None = None) -> None:
    """Read the last day's plays from the log, since the last reset."""
    clear()
    now = now or dt.datetime.now()
    row = _db().execute("SELECT value FROM app_meta WHERE key = ?",
                        (_RESET_KEY,)).fetchone()
    since = now - DAY
    if row:
        since = max(since, dt.datetime.fromisoformat(row[0]))
    for raw, path in _db().execute(
            "SELECT started_at, path FROM play_log WHERE started_at >= ?",
            (since.replace(microsecond=0).isoformat(),)):
        _plays.setdefault(path_key(path), []).append(dt.datetime.fromisoformat(raw))


def count(path, now: dt.datetime | None = None) -> int:
    since = (now or dt.datetime.now()) - DAY
    return sum(1 for when in _plays.get(path_key(path), ()) if when >= since)


def any_counted(now: dt.datetime | None = None) -> bool:
    since = (now or dt.datetime.now()) - DAY
    return any(when >= since for times in _plays.values() for when in times)


def bump(path, now: dt.datetime | None = None) -> None:
    """One more play of `path`, heard `now`."""
    _plays.setdefault(path_key(path), []).append(now or dt.datetime.now())


def reset(now: dt.datetime | None = None) -> None:
    """Every counter back to zero, from `now` on."""
    clear()
    stamp = (now or dt.datetime.now()).replace(microsecond=0).isoformat()
    _db().execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
                  (_RESET_KEY, stamp))
