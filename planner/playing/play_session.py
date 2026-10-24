"""▶ Which titles the evening has played, for picking it up after a crash or a restart.

The decks come back with the autosave anyway, and the title that was on air
has its own crash note (shared.stores.ON_AIR). What a restart lost was the
evening itself: which titles had already run, greyed in playing mode but held
in memory only. This keeps that list in a file of its own, written each time
a title greys.

No Qt. An evening ends where the play log says one does (GAP_HOURS without a
title): a list older than that is another evening and is never offered, so a
party that runs past midnight can still be picked up, and last Saturday's
cannot.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from planner.playing.play_log import GAP_HOURS
from planner.store import JsonStore

STORE = JsonStore("play_session.json", note="no evening to pick up")


@dataclass
class Session:
    saved_at: dt.datetime
    played: list[str] = field(default_factory=list)   # paths heard ≥ 10 s


def to_json(session: Session) -> dict:
    return {"saved_at": session.saved_at.replace(microsecond=0).isoformat(),
            "played": list(session.played)}


def load(now: dt.datetime) -> Session | None:
    """The evening to offer, or None: no file, a broken one, another
    evening's, or one with nothing played in it."""
    raw = STORE.read()
    if not isinstance(raw, dict):
        return None
    try:
        s = Session(dt.datetime.fromisoformat(str(raw["saved_at"])),
                    [str(p) for p in raw.get("played") or []])
    except (KeyError, TypeError, ValueError):
        return None
    age = now - s.saved_at
    if not dt.timedelta(0) <= age <= dt.timedelta(hours=GAP_HOURS):
        return None   # another evening
    return s if s.played else None


def clear() -> None:
    STORE.remove()
