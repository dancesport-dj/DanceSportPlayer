"""⏹ When the music stops by itself: after this title, after a number of
titles, or at a time of day.

No Qt. The ▶ panel sets it, the player asks it at every title end. It lives
for the evening only and is never saved: a "stop at 23:30" left over from last
Saturday would silence the next party without anyone having asked for it.

A stop never cuts a title unless asked to: the one that is playing when the
condition is met plays to its end, then nothing follows. Only the "At …" rule
can be set (saved, unlike the rule) to fade the title at the time instead.
A title ends the way the play length, a fade or its own end ends it; a ⏭ skip
is not an end and does not count.
"""
from datetime import datetime, timedelta

from planner import i18n

# The hybrid "At …" mode: a title that had played this long at the time fades,
# a younger one plays to its end.
HYBRID_FADE_SECS = 90


class PartyStop:
    """The armed condition, or none (`kind` None)."""

    def __init__(self):
        self.kind: str | None = None  # None, "count" or "time"
        self.left = 0  # titles still to end, the running one included
        self.at: datetime | None = None  # the first title end at or after it stops

    def clear(self):
        self.kind, self.left, self.at = None, 0, None

    def arm_count(self, n: int):
        """Stop once `n` titles have ended — 1 is the one playing now."""
        self.kind, self.left, self.at = "count", max(1, int(n)), None

    def arm_time(self, hour: int, minute: int, now: datetime):
        """Stop at the first title end at or after hour:minute. A time already
        past today is meant for after midnight."""
        at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if at <= now:
            at += timedelta(days=1)
        self.kind, self.left, self.at = "time", 0, at

    def due(self, end: datetime) -> bool:
        """Whether a title ending at `end` is the last one."""
        if self.kind == "count":
            return self.left <= 1
        if self.kind == "time" and self.at is not None:
            return end >= self.at
        return False

    def fade_due(self, now: datetime, played_secs: float, mode: str) -> bool:
        """Whether the title playing now fades out because the "At …" time
        has come. `mode` is the saved stop_at_mode: "end" plays it out (the
        rule above), "fade" fades every title that was playing at the time,
        "hybrid" only one that had played HYBRID_FADE_SECS by then. A title
        started after the time always plays to its end."""
        if mode not in ("fade", "hybrid") or self.kind != "time" or self.at is None:
            return False
        if now < self.at:
            return False
        at_time = played_secs - (now - self.at).total_seconds()
        if mode == "hybrid":
            return at_time >= HYBRID_FADE_SECS
        return at_time >= 0

    def title_ended(self, now: datetime, can_stop: bool = True) -> bool:
        """A title has ended: True when the music stops here (and the
        condition is spent). `can_stop` False is a 🔀 crossfade that already
        brought the next title in — it counts, but cannot stop anything; a
        time reached in its course stops at the next end instead."""
        if self.kind is None:
            return False
        if can_stop and self.due(now):
            self.clear()
            return True
        if self.kind == "count":
            self.left = max(1, self.left - 1)
        return False

    def text(self) -> str:
        """The condition as the player card and the panel show it ("" = none)."""
        if self.kind == "count":
            return (i18n.t("⏹  Stops after this title") if self.left <= 1
                    else i18n.t("⏹  Stops after %d titles") % self.left)
        if self.kind == "time" and self.at is not None:
            return i18n.t("⏹  Stops at %s") % self.at.strftime("%H:%M")
        return ""
