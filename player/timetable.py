"""🕒 The evening's running order, as the presenter screen can show it.

The presenter shows what is playing. On a wedding — or any evening that is
more than a round grid — the hall also wants to know when dinner is, when the
opening dance is, and when the midnight snack comes out. That is not playback
state: nobody enters it into a deck, it is typed once and then stands there.

So it lives on its own: a list of (time, what, note) rows in a JSON file next
to the settings, edited in a dialog, and rendered by the presenter as a second
page it can be switched or faded to.

The module is deliberately Qt-free below `TimetableModel` — the file format and
"which entry is now" are the parts the tests care about, and they should not
need a QApplication to ask.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from planner.store import JsonStore

log = logging.getLogger("dancesport.gui.timetable")

TIMETABLE = JsonStore("presenter_timetable.json",
                      note="starting with an empty timetable")

FORMAT_VERSION = 1
DEFAULT_TITLE = "Ablauf"
# How long one page stands before the fade takes over, when rotation is on.
# Ten seconds: long enough to read the running order's four lines, short enough
# that somebody glancing up at the music page does not have to wait for the
# programme to come round again.
DEFAULT_ROTATE_SECS = 10
MIN_ROTATE_SECS = 5
MAX_ROTATE_SECS = 600
# One day in minutes — what a programme adds when it runs past midnight.
_DAY = 24 * 60


def _clock(text: str) -> int | None:
    """A clock time as minutes past midnight, or None when it isn't one."""
    # "20.30" is as normal a spelling as "20:30" on a German programme.
    head = text.strip().replace(".", ":")
    if ":" not in head:
        return None
    h, _, m = head.partition(":")
    try:
        hh, mm = int(h.strip()), int(m.strip()[:2])
    except ValueError:
        return None
    return hh * 60 + mm if 0 <= hh <= 23 and 0 <= mm <= 59 else None


@dataclass
class Entry:
    """One line of the running order. `time` is free text on purpose — "20:30"
    is the normal case, but "ca. 23 Uhr" and "im Anschluss" are things people
    really write on a wedding programme, and a screen that refuses them is
    worth less than one that just prints them.

    `until` is what makes a line a frame rather than a moment: given an end, a
    party from 19:00 to 01:00 can hold the opening dance inside it, and when
    the dance is over the party is what is running again. Empty is the normal
    case — a line without an end simply runs until the next one begins."""
    time: str = ""
    what: str = ""
    note: str = ""
    until: str = ""

    def minutes(self) -> int | None:
        """The time as minutes past midnight, or None when it isn't a clock
        time — that is what "now" is decided on, and free text simply never
        becomes the current line."""
        return _clock(self.time)

    def until_minutes(self) -> int | None:
        """The end as a clock time, or None when it is blank or a length."""
        return _clock(self.until)

    def length(self) -> int | None:
        """The end as a count of minutes, for the "20" or "20 min" somebody
        types when they know how long a dance takes but not when it lands.
        None when the end is a clock time or blank."""
        if not self.until.strip() or _clock(self.until) is not None:
            return None
        digits = "".join(c for c in self.until if c.isdigit())
        return int(digits) if digits else None

    def as_dict(self) -> dict:
        return {"time": self.time, "what": self.what, "note": self.note,
                "until": self.until}

    @classmethod
    def from_dict(cls, d) -> "Entry":
        if not isinstance(d, dict):
            return cls()
        return cls(time=str(d.get("time", "")), what=str(d.get("what", "")),
                   note=str(d.get("note", "")), until=str(d.get("until", "")))


def offset_for(target, now=None) -> timedelta:
    """How far the clock has to be moved for `target` to read as now.

    Evenings run late. Saying "it is only 20:00" at 20:45 is not a wish for
    the screen to stand still — it means the whole programme is three quarters
    of an hour behind, and should keep running from there. So what is kept is
    a shift, not a fixed time.

    The shift is always the nearer of the two readings: 00:30 typed at 23:50
    is forty minutes on, because the small hours belong to the evening that is
    running and not to the one that ended this morning."""
    now = now or datetime.now()
    off = now.replace(hour=target.hour, minute=target.minute,
                      second=0, microsecond=0) - now.replace(second=0,
                                                             microsecond=0)
    if off > timedelta(hours=12):
        off -= timedelta(days=1)
    elif off < -timedelta(hours=12):
        off += timedelta(days=1)
    return off


@dataclass
class Timetable:
    """The whole programme: a heading, its rows, and how the presenter is to
    show it."""
    title: str = DEFAULT_TITLE
    entries: list = field(default_factory=list)
    rotate: bool = False          # fade between music and timetable…
    rotate_secs: int = DEFAULT_ROTATE_SECS   # …every this many seconds

    def as_dict(self) -> dict:
        return {"version": FORMAT_VERSION,
                "title": self.title,
                "rotate": bool(self.rotate),
                "rotate_secs": int(self.rotate_secs),
                "entries": [e.as_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, d) -> "Timetable":
        """Anything unreadable becomes an empty timetable rather than an error:
        this is decoration on a screen, never a reason to lose the evening."""
        if not isinstance(d, dict):
            return cls()
        rows = d.get("entries")
        secs = d.get("rotate_secs", DEFAULT_ROTATE_SECS)
        try:
            secs = int(secs)
        except (TypeError, ValueError):
            secs = DEFAULT_ROTATE_SECS
        return cls(
            title=str(d.get("title", DEFAULT_TITLE)) or DEFAULT_TITLE,
            entries=[Entry.from_dict(r) for r in rows] if isinstance(rows, list) else [],
            rotate=bool(d.get("rotate", False)),
            rotate_secs=max(MIN_ROTATE_SECS, min(MAX_ROTATE_SECS, secs)))

    def is_empty(self) -> bool:
        """Nothing worth putting on a screen — no row names anything."""
        return not any(e.time.strip() or e.what.strip() for e in self.entries)

    def _unrolled(self) -> list:
        """The clock times laid out on one continuous evening, in minutes from
        the midnight it begins after: a time that falls back behind the one
        above it has passed midnight, so "01:00 Ende" under an 18:00 party is
        1500 and not 60. Free text keeps its place in the list as None."""
        out, day, prev = [], 0, None
        for e in self.entries:
            m = e.minutes()
            if m is None:
                out.append(None)
                continue
            if prev is not None and m < prev:
                day += _DAY
            prev = m
            out.append(m + day)
        return out

    def _reading(self, now=None) -> tuple:
        """The programme's times and the wall clock, laid on the same evening:
        `(unrolled times, minutes)`.

        Which day the clock belongs to is the question here. 00:30 is the tail
        of an evening that began at 18:00; 13:00 is the afternoon before it.
        Whichever of the two readings falls nearer the programme wins, which
        decides it without a rule about how long a night may run."""
        now = now or datetime.now()
        minutes = now.hour * 60 + now.minute
        times = self._unrolled()
        clock = [t for t in times if t is not None]
        if clock:
            first, last = clock[0], clock[-1]

            def off(t):
                return max(first - t, t - last, 0)

            if off(minutes + _DAY) < off(minutes):
                minutes += _DAY
        return times, minutes

    def _spans(self, now=None) -> tuple:
        """`(starts, ends, minutes)` — the same reading as `_reading`, with
        each row's end beside its start, or None where it has none.

        An end laid out on the same evening as its start: "19:00 bis 01:00"
        runs six hours on, not eighteen back. A length ("20 min") is simply
        added to the start, which needs no such care."""
        times, minutes = self._reading(now)
        ends = []
        for entry, start in zip(self.entries, times):
            if start is None:
                ends.append(None)
                continue
            clock = entry.until_minutes()
            if clock is not None:
                end = clock + start // _DAY * _DAY
                if end < start:
                    end += _DAY
            else:
                length = entry.length()
                end = start + length if length is not None else None
            ends.append(end)
        return times, ends, minutes

    def state(self, now=None) -> tuple:
        """`(the row the accent stands on, the rows that are behind us)`.

        The accent goes to the last row that has begun and has not ended —
        so while the opening dance runs it is on the dance, and the minute the
        dance is over it is back on the party the dance stands in. A row
        without an end never ends, which is the old behaviour of a programme
        that gives no ends at all: the last row reached keeps it.

        Behind us is every row whose own time has passed and that is not the
        accent — by its time, not by its place in the list, or the dance that
        just finished would read as still to come because it is written under
        the party. A row with no clock time has no time to have passed, so it
        goes by its place instead."""
        times, ends, minutes = self._spans(now)
        cur = -1
        for i, start in enumerate(times):
            if start is not None and start <= minutes \
                    and (ends[i] is None or minutes < ends[i]):
                cur = i
        spent = set()
        for i, start in enumerate(times):
            if i == cur:
                continue
            if start is not None:
                if start <= minutes:
                    spent.add(i)
            elif 0 <= cur and i < cur:
                spent.add(i)
        return cur, spent

    def current_index(self, now=None) -> int:
        """Which row the evening is standing on: the last one that has begun
        and has not ended, so a party that starts at 18:00 is still the
        current line at 19:15 even with "01:00 Ende" written under it.

        -1 before the first clock time, and -1 for a programme that gives no
        clock times at all — then nothing is highlighted and every line reads
        the same, which is the honest answer.

        There was once a second reading beside this one, which let a point go
        done half an hour on when the next was more than an hour away. It is
        gone: what tells "Hochzeitstanz 19:00 with the party behind it" from
        "Hochzeitstanz 20:00 with nothing behind it" is not in the times —
        it is in whether the party was given an end, which is now a column
        somebody can type."""
        return self.state(now)[0]


def load_timetable() -> Timetable:
    """What was typed last time, or an empty programme on a first start."""
    return Timetable.from_dict(TIMETABLE.read())


def save_timetable(table: Timetable) -> bool:
    ok = TIMETABLE.write(table.as_dict())
    if ok:
        log.info("🕒 Timetable saved\n"
                 "entries: %s\n"
                 "rotate: %s", len(table.entries),
                 f"every {table.rotate_secs}s" if table.rotate else "off")
    return ok
