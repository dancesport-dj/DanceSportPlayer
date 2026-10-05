"""🐂 Where a Paso Doble stops: the highlight the music is cut on.

The policy alone — no window, no player, no Qt. `player.main_pd` gathers what
it needs (the marks, the chosen highlight, the track's length and takt) and
arms the stop it answers.
"""
import logging

log = logging.getLogger("dancesport.gui.pd")

# 🐂 Where the tournament PD phrasing puts the highlights at T60 — highlight 1
# at 0:45, highlight 2 at 1:18. Both scale with the takt (see `pd_position`).
# They are TWO things at once: the stand-in when detection pinned nothing down,
# and the zone (± tolerance) a detected mark has to land in to be believed.
_PD_FALLBACK = {1: 45.0, 2: 78.0}
_PD_TOL = 10.0
# The shortest PD that can still carry a highlight 2 at all.
_PD_H2_FROM = 70.0
# Measured highlight-2 position per takt (bars per minute).
_PD_H2_BY_TAKT = {58: 82.0, 59: 80.0, 60: 78.0, 62: 76.0}


def pd_position(n: int, takt: float) -> float:
    """Where highlight `n` sits in a Paso Doble played at `takt` bars per
    minute — the phrase position both the fallback and the accept zone use.

    Highlight 2 has its own measured table; highlight 1 lands on a fixed bar
    just the same, so it scales by tempo alone.
    """
    if n == 2:
        return pd_h2_position(takt)
    return _PD_FALLBACK[1] * (60.0 / takt if takt and takt > 0 else 1.0)


def pd_h2_position(takt: float) -> float:
    """Where highlight 2 sits in a Paso Doble played at `takt` bars per minute.

    The choreography lands on a fixed BAR of the phrase, so the faster the music
    the sooner the same highlight comes round: 1:22 at T58, 1:20 at T59, 1:18 at
    T60, 1:16 at T62. Between those it interpolates; beyond them the same bar is
    reached in inverse proportion to the tempo. Unknown takt → the T60 position.
    """
    if not takt or takt <= 0:
        return _PD_FALLBACK[2]
    tks = sorted(_PD_H2_BY_TAKT)
    for lo, hi in zip(tks, tks[1:]):
        if lo <= takt <= hi:
            f = (takt - lo) / (hi - lo)
            return _PD_H2_BY_TAKT[lo] + f * (_PD_H2_BY_TAKT[hi] - _PD_H2_BY_TAKT[lo])
    edge = tks[0] if takt < tks[0] else tks[-1]
    return _PD_H2_BY_TAKT[edge] * edge / takt


def distinct_pd_highlights(raw: list, min_gap: float = 15.0) -> list:
    """Auto highlight times with near-duplicates merged: a Paso Doble swell
    that detection split across the h1/h2 windows collapses to one highlight.
    Keeps the earliest mark of each close cluster (the swell's onset); real
    tournament highlights are spaced far wider than `min_gap` seconds."""
    distinct: list = []
    for t in raw:
        if t is None:
            continue
        if distinct and t - distinct[-1] < min_gap:
            continue
        distinct.append(t)
    return distinct


def pd_stop_at(raw: list, n: int, manual: bool, duration: float, takt: float,
               name: str = "") -> float | None:
    """The second highlight `n` stops the title at, or None to play it out.

    Auto highlights are positional [h1,h2,h3], cross-checked against the PD
    phrase position for this tempo (0:45 and 1:18 at T60, ±10 s — see
    `pd_position`): a mark outside its zone is not that highlight, so a mark
    inside it wins, and failing that the phrase position itself does. A track
    too short to reach the highlight-2 zone stops at highlight 1 instead.
    Manually learned marks are exact stop points: the chosen one, or the LAST
    mark when fewer were learned than requested. `duration` is 0 when unknown,
    `takt` too; `name` is only for the log."""
    if manual:
        marks = [t for t in raw if t is not None]
        return (marks[n - 1] if n <= len(marks) else marks[-1]) if marks else None
    # Auto positional [h1,h2,h3]: collapse marks that sit too close to be
    # separate highlights — a short PD edit often gets ONE musical swell
    # split across the h1/h2 detection windows (e.g. 34s + 43s for the same
    # crash), which would otherwise stop the song a few seconds after the
    # first highlight when #2 is asked for. Fewer DISTINCT highlights than
    # requested → play to the end.
    distinct = distinct_pd_highlights(raw)
    n_eff = n
    # A track that ends before the typical highlight-2 zone (~1:10,
    # minus tolerance) can only carry highlight 1 → stop there.
    if n >= 2 and 0 < duration <= _PD_H2_FROM - _PD_TOL:
        n_eff = 1
        log.info("🐂 Track too short for highlight %d (%.0f s) — "
                 "stopping at highlight 1\n"
                 "file: %s", n, duration, name)
    mark = distinct[n_eff - 1] if n_eff <= len(distinct) else None
    # Second instance against wrong marks: the choreography lands on a
    # fixed bar, so highlight n belongs within ±_PD_TOL of its phrase
    # position for THIS tempo — 0:45 and 1:18 at T60, later at T58.
    # A mark outside that zone is a crash the detector mistook for the
    # rung (the run of España Cañí edits shows both: an h1 picked ~9 s
    # early, an h2 picked ~17 s late). Another detected mark inside the
    # zone wins; failing that the phrase position does. Only when the
    # phrase position doesn't fit into the track at all does the
    # off-zone mark stand — it is then the one thing measured on this
    # file.
    if n_eff in (1, 2):
        fb = pd_position(n_eff, takt)
        lo, hi = fb - _PD_TOL, fb + _PD_TOL
        if mark is None or not (lo <= mark <= hi):
            in_zone = [t for t in distinct if lo <= t <= hi]
            if in_zone:
                log.info("🐂 Highlight %d re-anchored to its phrase "
                         "zone (%.0f–%.0f s)\n"
                         "file: %s\n"
                         "mark: %.1fs (positional pick: %s)",
                         n_eff, lo, hi, name, in_zone[0],
                         f"{mark:.1f}s" if mark is not None else "none")
                mark = in_zone[0]
            elif duration <= 0 or fb <= duration - 2.0:
                log.info("🐂 No highlight %d in its phrase zone "
                         "(%.0f–%.0f s) — falling back to the phrase "
                         "position\n"
                         "file: %s\n"
                         "mark: %.0fs (positional pick: %s)",
                         n_eff, lo, hi, name, fb,
                         f"{mark:.1f}s" if mark is not None else "none")
                mark = fb
    if mark is None:
        return None
    # When the chosen highlight IS the finale (the last one, landing
    # in the final stretch of the track) its crash is the song's own
    # ending — let it play out instead of clipping the last seconds.
    # A short PD whose 2nd highlight sits at the very end thus plays
    # full. An earlier highlight still cuts EXACTLY at the gong (music
    # off at once, no ring-out, no fade: TSO practice).
    is_finale = (duration > 0 and mark >= duration * 0.85
                 and distinct and mark == distinct[-1])
    return None if is_finale else mark
