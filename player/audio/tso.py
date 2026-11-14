"""🎚 TSO — which takt the playing title is pitched to.

Split off the player mixin: which titles make up the playing title's round, and
the one takt that round is danced at, need the deck's rows and the settings, not
the window. So they are plain functions here, tested without one; the window
keeps what is glue — setting the tempo, the status line and the log.
"""
from typing import NamedTuple

import planner.models
from planner.dances import BEATS_PER_BAR
from planner.playlist.checks import entry_takt
from shared.audio.playback import TSO_FLOOR_OVERRIDE

# The analyser's table covers the tournament dances only. 🛋 Gemütlich has a top
# tempo for every dance the app knows (it is not TSO, which pitches the
# tournament dances into their band), so a social title without a takt in its
# name needs a meter too, or its measured tempo never becomes a takt and it
# plays as recorded. All of them are counted in 4; Tango Argentino like the
# ballroom Tango. Kept here: the shared table also seeds the tempo analysis
# and the list checks, which should not change with it.
PITCH_BEATS_PER_BAR = {
    **BEATS_PER_BAR,
    "SALSA": 4, "DISCOFOX": 4, "BACHATA": 4, "WCS": 4, "KIZOMBA": 4,
    "FORRO": 4, "BW": 4, "LD": 4, "TANGOARG": BEATS_PER_BAR["TG"],
}


class TsoTarget(NamedTuple):
    counts: dict      # takt → how many titles of the round are on it
    danced_at: float  # the one takt the round is danced at
    target: float     # where this title is pitched to


def tso_band_of(settings: dict, dance: str) -> planner.models.TsoBand:
    """Where in its TSO band this dance is pitched — ⚙ Settings → 🎛 Playsets.

    Unset dances keep the heat mean, which is what the button did before the
    setting existed."""
    stored = settings.get("tso_band")
    stored = stored if isinstance(stored, dict) else {}
    return planner.models.TsoBand.of(stored.get(dance, planner.models.TsoBand.MEAN))


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
    of a dance, and a strip of one title is no round.

    A "?" title counts with its measured takt (`pitch_takt`), unless that is
    too far outside the band to be believed."""
    rname = deck._row_meta[row].round_name
    hdr = round_strip(deck, row)
    return [t for r, m in enumerate(deck._row_meta) if m
            for e in (m.entry,)
            if e is not None and e.dance == dance
            and m.round_name == rname
            and (hdr is None or deck._row_round_hdr.get(r, -1) == hdr)
            for t in (pitch_takt(e),)
            # A "?" title counts with its measured takt, unless that is too
            # far off the band to be believed (see `doubtful_for_tso`).
            if t and (getattr(e, "bpm", 0) or not doubtful_for_tso(dance, t))]


def pitch_takt(ent, dance: str | None = None) -> int:
    """The takt a title is pitched from: its file name's label, and for a "?"
    title the measured tempo ÷ the dance's beats per bar. 0 when neither is
    known. `dance` is the row's, for a title with none of its own: a social
    title known by its folder only keeps .dance empty."""
    return entry_takt(ent, PITCH_BEATS_PER_BAR, dance)


# How far a MEASURED takt may be from where its dance lives before it is taken
# for a wrong measure (half or double time) and the title is left alone: two
# takte outside the TSO band, three over the gemütlich top (more than three
# takte of pitch is never good for the ear). A measured takt within the TSO
# margin counts in the round and is pitched: a T22 Rumba (band 24-26) is. A
# label in the file name is trusted and never judged.
MEASURE_TSO_MARGIN = 2
MEASURE_GEMUETLICH_MARGIN = 3


def tso_range_of(dance: str) -> tuple | None:
    """The (low, high) takt TSO pitches `dance` into, None when it has no band."""
    rng = planner.models.TEMPO_RANGES.get(dance, {}).get("S")
    return (TSO_FLOOR_OVERRIDE.get(dance, rng[0]), rng[1]) if rng else None


def doubtful_for_tso(dance: str, takt: float) -> bool:
    """A measured `takt` more than two takte outside the TSO band of `dance`."""
    rng = tso_range_of(dance)
    return rng is not None and not (
        rng[0] - MEASURE_TSO_MARGIN <= takt <= rng[1] + MEASURE_TSO_MARGIN)


def doubtful_for_gemuetlich(takt: float, top: float) -> bool:
    """A measured `takt` more than three over the gemütlich `top`."""
    return takt - top > MEASURE_GEMUETLICH_MARGIN


def gemuetlich_target(own_bpm: float, top: float | None) -> float | None:
    """🛋 The takt a title recorded at `own_bpm` is slowed to under gemütlich,
    or None when it is left alone: no limit for its dance, no tempo known, or
    already at or under the top. Never faster than it was recorded."""
    if not own_bpm or top is None or own_bpm <= top:
        return None
    return top


def tso_target(bpms: list, dance: str, own_bpm: float,
               band: planner.models.TsoBand | str,
               measured: bool = False) -> TsoTarget:
    """The takt a title recorded at `own_bpm` is pitched to in a round on `bpms`.

    The one takt the round is danced at — the takt most of it is already on
    where joining that one is cheap, the middle of its takte where it is not.
    `round_takt_target` carries that rule; it needs the band to know which
    takte were recorded outside it."""
    counts = planner.models.takt_counts(bpms)
    lo, hi = tso_range_of(dance) or (None, None)
    danced_at = planner.models.round_takt_target(counts, lo, hi) or own_bpm
    # Where in the TSO band the dance is danced: by default the round's own
    # takt pulled into the range (raise a too-slow Rumba/Paso Doble to the
    # legal minimum, cap a too-fast one), or the fixed lower / middle / upper
    # takt this dance is set to in ⚙ Settings → 🎛 Playsets.
    target = danced_at
    if lo is not None and hi is not None:     # the dance has a band
        target = planner.models.tso_band_target(lo, hi, danced_at, band)
    if band == planner.models.TsoBand.MEAN:
        # Never more than a whole takt off what was recorded: a T27 Slow Fox
        # comes up to the 28 it is allowed, not to the 28.5 the rest of the
        # round is on. Past a takt the pitch is heard on the voice. A measured
        # takt is believed up to the margin outside the band, so it may be
        # pitched that far: the T22 Rumba the measure found goes to 24.
        step = MEASURE_TSO_MARGIN if measured else 1
        target = min(max(target, own_bpm - step), own_bpm + step)
    return TsoTarget(counts, danced_at, target)
