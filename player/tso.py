"""🎚 TSO — which takt the playing title is pitched to.

Split off the player mixin: which titles make up the playing title's round, and
the one takt that round is danced at, need the deck's rows and the settings, not
the window. So they are plain functions here, tested without one; the window
keeps what is glue — setting the tempo, the status line and the log.
"""
from typing import NamedTuple

import planner.models
from shared.playback import _TSO_FLOOR_OVERRIDE


class TsoTarget(NamedTuple):
    counts: dict      # takt → how many titles of the round are on it
    danced_at: float  # the one takt the round is danced at
    target: float     # where this title is pitched to


def tso_band_of(settings: dict, dance: str) -> str:
    """Where in its TSO band this dance is pitched — ⚙ Settings → 🎛 Play sets.

    Unset dances keep the heat mean, which is what the button did before the
    setting existed."""
    stored = settings.get("tso_band")
    stored = stored if isinstance(stored, dict) else {}
    band = str(stored.get(dance, "mean"))
    return band if band in planner.models.TSO_BANDS else "mean"


def round_strip(deck, row: int) -> int | None:
    """The ─── strip a running order's row hangs under, or None on a planned
    grid, whose rows name their round themselves."""
    return deck._row_round_hdr.get(row, -1) if deck._player_list else None


def round_takte(deck, row: int, dance: str) -> list:
    """The takte of the titles that count as `row`'s round for `dance`.

    A planned grid says per row which round it is in; a RUNNING ORDER does
    not — its rows carry no round name at all, the cut lives in the ─── strip
    they hang under, which is what the panel heads with "Vorrunde" / "Finale".
    Grouping by the name alone made every Samba of a whole competition one
    round: twelve titles over four rounds set the takt of a Vorrunde of six.

    A warm-up list is left counting as a whole. Its strips cut at every repeat
    of a dance, and a strip of one title is no round."""
    rname = deck._row_meta[row].round_name
    hdr = round_strip(deck, row)
    return [e.bpm for r, m in enumerate(deck._row_meta) if m
            for e in (m.entry,)
            if e is not None and e.dance == dance
            and m.round_name == rname
            and (hdr is None or deck._row_round_hdr.get(r, -1) == hdr)
            and getattr(e, "bpm", 0)]


def tso_target(bpms: list, dance: str, own_bpm: float, band: str) -> TsoTarget:
    """The takt a title recorded at `own_bpm` is pitched to in a round on `bpms`.

    The one takt the round is danced at — the takt most of it is already on
    where joining that one is cheap, the middle of its takte where it is not.
    `round_takt_target` carries that rule; it needs the band to know which
    takte were recorded outside it."""
    counts = planner.models.takt_counts(bpms)
    rng = planner.models.TEMPO_RANGES.get(dance, {}).get("S")
    lo, hi = ((_TSO_FLOOR_OVERRIDE.get(dance, rng[0]), rng[1]) if rng
              else (None, None))
    danced_at = planner.models.round_takt_target(counts, lo, hi) or own_bpm
    # Where in the TSO band the dance is danced: by default the round's own
    # takt pulled into the range (raise a too-slow Rumba/Paso Doble to the
    # legal minimum, cap a too-fast one), or the fixed lower / middle / upper
    # takt this dance is set to in ⚙ Settings → 🎛 Play sets.
    target = danced_at
    if rng:
        target = planner.models.tso_band_target(lo, hi, danced_at, band)
    if band == "mean":
        # Never more than a whole takt off what was recorded: a T27 Slow Fox
        # comes up to the 28 it is allowed, not to the 28.5 the rest of the
        # round is on. Past a takt the pitch is heard on the voice.
        target = min(max(target, own_bpm - 1), own_bpm + 1)
    return TsoTarget(counts, danced_at, target)
