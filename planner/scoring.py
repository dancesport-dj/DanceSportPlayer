"""Pick-scoring weights & round-pool strategy for the planner.

Extracted from dancesport_planner.py (logical split): the composite-score
weights/bonuses, the class-aware popularity weighting and the round strategy
table + resolver used by MusicLibrary._pick / regenerate.
"""
import logging

from planner.models import MusicEntry

log = logging.getLogger("dancesport.scoring")


# ── Pick-scoring weights ─────────────────────────────────────────────────────
# One place to tune how `_pick` ranks candidates. Composite score:
#   popularity·W_POPULARITY + bpm_fit·W_BPM_FIT + timbre·W_TIMBRE + bonuses/maluses
W_POPULARITY = 3            # ×popularity (forced to 0 under 'all' — no proven bias)


W_BPM_FIT = 2               # ×_bpm_fit (1.0 = perfectly inside tournament tempo)


W_TIMBRE = 5                # ×similarity-to-anchor (0..1)


PENALTY_BELOW_TEMPO = 1.5   # flat malus for songs below minimum tempo (marked *)


BONUS_FRESH = 4             # 'fresh' strategy: bonus for barely/never-played songs


BONUS_PROVEN = 2            # 'proven' strategy: bonus for proven songs


BONUS_CLASS_OK = 5          # class tag includes the current class


PENALTY_CLASS_DILUTED = 5   # …but the tag also names D/C in a B/A/S round


PENALTY_CLASS_MISMATCH = 7  # class tags exist but exclude the current class


RANDOM_TIEBREAK = 0.05      # tiny jitter so exact ties don't always order the same


# The start classes, and where the line runs. A comment tag that leaves the
# lower classes out ("B,A,S") is a deliberate statement: this is music for the
# higher rounds. One that also names D or C is a title the lower classes dance
# well to and the higher ones only tolerably — fine, but not the
# first choice for a B/A/S event.
LOWER_CLASSES = ("D", "C")


HIGHER_CLASSES = ("B", "A", "S")


def class_focused(entry) -> bool:
    """True when the track's class tag names only the higher classes.

    Untagged tracks are not focused — nobody said anything about them, and a
    silent tag must not outrank one that was actually written."""
    allowed = getattr(entry, "classes_ok", None)
    if not allowed:
        return False
    return not any(c in LOWER_CLASSES for c in allowed)


# Class-aware popularity weights (see `effective_popularity`): how much a playlist
# appearance counts toward the popularity used for proven-gating and ranking, by
# where it happened relative to the SELECTED start class. Other-class plays are
# nearly ignored — a title played 30× in D and once in S must not outrank a real
# S staple; class-unknown lists count by the song's OWN class mix (see below).
_W_SAME_CLASS = 1.0


_W_UNKNOWN_CLASS = 0.5


_W_OTHER_CLASS = 0.1


# Other-class plays can hint that a song works, but no amount of them may add up
# to "proven here": 75 D/C plays once pushed a zero-S title over the proven
# threshold (0.1 × 75 = 7.5). Their total contribution is capped well below it.
_OTHER_CLASS_CAP = 2.0


# Plays from lists whose class couldn't be parsed are attributed by the song's own
# classified mix (a 30×D/1×S title's unknown plays are ~3% S, not 50%). The mix is
# smoothed with this many pseudo-plays at the neutral `_W_UNKNOWN_CLASS` share, so
# a song with NO classified plays keeps the old flat 0.5 weight instead of
# snapping to 0 or 1 on a single observation.
_UNKNOWN_PRIOR = 2.0


# A title must appear in at least this many REAL (non-superseded) playlists to count
# as "proven" / played. Fewer than this → treated as fresh. This is a numeric safety
# net on top of the name-based `_is_superseded_playlist` filter: we can't name every
# dump / holding-bin list, so a song surfacing in only one or two of them (popularity
# 1–4) is still treated as never-really-played rather than 'proven'.
_PROVEN_MIN_POP = 5


# A final is not simply "the most-played tracks". A title can lead the library on
# play count and still be a heat title — played twice in every preliminary,
# never once in an Endrunde. `final_plays` counts the past lists that danced it
# in THEIR final and `semi_plays` the ones that danced it in their semifinal, and
# those two rounds prefer the titles that have been there.
# Two, not one, so a single stray hit doesn't read as a finalist; the pool falls
# back through one play and then the whole strategy pool, so a dance with no
# round history at all can still be filled.
_FINAL_MIN_PLAYS = 2


def final_plays(entry) -> int:
    """How many past playlists danced this title in their FINAL round."""
    return int(getattr(entry, "final_plays", 0) or 0)


def semi_plays(entry) -> int:
    """…and how many in their SEMIFINAL."""
    return int(getattr(entry, "semi_plays", 0) or 0)


def late_plays(entry) -> int:
    """Either of the two — the title was somewhere in the sharp end of an event."""
    return final_plays(entry) + semi_plays(entry)


def prefer_late_rounds(pool: list, tier: str) -> list:
    """Narrow a final's or a semifinal's pool to the titles that have been there.

    Those are the two rounds a DJ picks rather than fills: one track per dance,
    chosen for that moment. The preliminaries are where the rest of a proven
    library belongs, and taking these titles out of them would make every heat
    sound like the leftovers — so the earlier tiers are left alone.

    Each round asks for its OWN history first. The semifinal is generated before
    the final and `used` keeps a track from appearing twice, so a semifinal that
    reached for the finalists would empty the final's shelf before it is opened.
    Only when its own history runs out does either round fall back to the other's,
    and then to the whole pool: nothing may end up blank."""
    if tier == "final":
        own = final_plays
    elif tier == "semi":
        own = semi_plays
    else:
        return pool
    return ([e for e in pool if own(e) >= _FINAL_MIN_PLAYS]
            or [e for e in pool if own(e) > 0]
            or [e for e in pool if late_plays(e) >= _FINAL_MIN_PLAYS]
            or [e for e in pool if late_plays(e) > 0]
            or pool)


# ── Round pool strategies ───────────────────────────────────────────────────────
# Selectable per round. Each decides which candidate songs a round may draw from.
#   proven     – songs you have really played (popularity >= _PROVEN_MIN_POP), fresh fallback
#   top_proven – only your most-played songs (>= 2× the proven threshold → proven fallback)
#   fresh      – barely/never-used songs (popularity < _PROVEN_MIN_POP) first, proven fallback
#   mixed      – proven + fresh together, ranked by fit (proven naturally leads)
#   all        – widest in-tempo pool, no proven/fresh preference at all
# Under proven / top_proven the FINAL and the SEMIFINAL additionally prefer the
# titles that have been in that round before — see `prefer_late_rounds`.
STRATEGIES = ("proven", "top_proven", "fresh", "mixed", "all")


STRATEGY_LABELS = {
    "proven":     "Proven",
    "top_proven": "Top Proven",
    "fresh":      "Fresh",
    "mixed":      "Mostly Proven",
    "all":        "Even Mix",
}


STRATEGY_HELP = {
    "proven":     "Songs you have played before (fresh as fallback).",
    "top_proven": "Only your most-played songs.",
    # (In a final or semifinal, both prefer what you have played in that round.)
    "fresh":      "Unused songs first (proven as fallback).",
    "mixed":      "Proven + fresh together, but favors songs you have played before.",
    "all":        "Proven + fresh with no preference — equal chance, maximum variety.",
}


def _resolve_strategy(tier: str, prefer_fresh: bool, strategy: str | None) -> str:
    """Effective pool strategy for a round.

    An explicit `strategy` wins; otherwise fall back to the tier's natural
    default (final → top_proven, semi → proven, else the legacy prefer_fresh
    flag). Keeps behaviour identical for callers that still pass only
    prefer_fresh.
    """
    if strategy in STRATEGIES:
        return strategy
    if tier == "final":
        return "top_proven"
    if tier == "semi":
        return "proven"
    return "fresh" if prefer_fresh else "proven"


def class_popularity(entry: MusicEntry, dance_class: str | None) -> int:
    """Distinct playlists of exactly `dance_class` this song appeared in (0 when
    the class is unknown or the song has no class-attributed plays)."""
    if not entry.class_plays or not dance_class:
        return 0
    return entry.class_plays.get(dance_class, 0)


def class_dilutes(entry: MusicEntry, dance_class: str | None) -> bool:
    """True when a B/A/S round should hold this track back.

    Its class tag also names D or C, so it is music the lower classes dance
    well to — unless it has already been played in THIS class, which was a
    decision somebody made while planning a real event and outranks the tag.
    """
    if dance_class not in HIGHER_CLASSES:
        return False
    allowed = getattr(entry, "classes_ok", None)
    if not allowed or not any(c in LOWER_CLASSES for c in allowed):
        return False
    return class_popularity(entry, dance_class) <= 0


def effective_popularity(entry: MusicEntry, dance_class: str | None) -> float:
    """Popularity reweighted for the SELECTED start class.

    Same-class plays count fully; plays attributed to OTHER classes barely count
    (`_W_OTHER_CLASS`, capped). Plays in lists whose class couldn't be detected are
    attributed by the song's OWN classified mix — smoothed toward the neutral
    `_W_UNKNOWN_CLASS` share with `_UNKNOWN_PRIOR` pseudo-plays — so a title
    played 30×D/1×S with 57 unclassified plays reads ≈6 for S (its unknowns are
    ~3% S), not ≈31 as under a flat 0.5-per-unknown weight. This is what
    proven-gating and ranking use."""
    p = entry.popularity
    if not dance_class:
        return float(p)
    plays = entry.class_plays or {}
    same = plays.get(dance_class, 0)
    attributed = sum(plays.values())
    other = attributed - same
    unknown = max(0, p - attributed)
    same_share = ((same + _W_UNKNOWN_CLASS * _UNKNOWN_PRIOR)
                  / (attributed + _UNKNOWN_PRIOR))
    return (same * _W_SAME_CLASS
            + unknown * same_share
            + min(other * _W_OTHER_CLASS, _OTHER_CLASS_CAP))
