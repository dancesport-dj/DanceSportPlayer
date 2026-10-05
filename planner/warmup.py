"""Warm-up ('Eintanzen') & per-class practice playlist generators.

Extracted from dancesport_planner.py (logical split): the ETDS-style shuffled
practice-floor builder plus the 'Others' (social-dance) classification helpers.
"""
import math
import random
import statistics
from collections import deque
from pathlib import Path
from types import SimpleNamespace

from planner.models import (
    DANCE_NAMES, OTHERS_DANCES, STYLE_FOLDERS, _RESERVED_STYLE_FOLDERS,
    DEFAULT_DANCES, TEMPO_RANGES, BELOW_TEMPO_EXT, _EXCLUDED_FOLDERS,
    fold_text, MusicEntry, is_non_turnier,
)
from planner.scoring import effective_popularity


# ── Warm-up ("Eintanzen") playlist generator ────────────────────────────────
# A long shuffled practice-floor playlist (NOT competition rounds): dances are
# drawn in 3-dance rounds, alternating Latin / Standard, optionally interleaved
# with social "Modetanz" rounds. Ported in spirit from the Java TurnierCheck
# Analyzer.sortForEintanzen (ETDS party mode) — same constraints, restated
# without the global mutable state.
_WARMUP_BALLROOM = ('LW', 'TG', 'WW', 'SF', 'QS')


_WARMUP_LATIN = ('SA', 'CC', 'RB', 'PD', 'JI')


_WARMUP_MODE = ('DISCOFOX', 'SALSA', 'BACHATA', 'WCS', 'KIZOMBA', 'FORRO')


# Competition running order, to optionally sort the dances inside a round.
_WARMUP_ORDER = {d: i for i, d in enumerate(
    ('LW', 'TG', 'WW', 'SF', 'QS', 'SA', 'CC', 'RB', 'PD', 'JI')
    + _WARMUP_MODE + ('TANGOARG',))}


# ETDS appearance weights (Java getEtdsProbability) — each section sums to ~1.
_ETDS_PROB = {
    'SA': 0.125, 'CC': 0.2375, 'RB': 0.4, 'PD': 0.025, 'JI': 0.2125,
    'LW': 0.4, 'TG': 0.2, 'WW': 0.05, 'SF': 0.15, 'QS': 0.2,
    'DISCOFOX': 0.5, 'SALSA': 0.1125, 'BACHATA': 0.1125,
    'WCS': 0.15, 'KIZOMBA': 0.075, 'FORRO': 0.05,
}


# Chance that a Latin round owes a Paso Doble while "late PD" is ticked.
# `_ETDS_PROB` states a share of the section's TRACKS, so a round of three slots
# owes 3 × 0.025 of one. The three-round spacing then blackens the three rounds
# after every Paso, which would quietly take a quarter of that away again;
# q / (1 - 3q) hands those rounds back, so what comes out is the share the table
# states — about three Pasos in an evening's worth of Latin rounds.
_PD_SLOT_SHARE = 3 * _ETDS_PROB['PD']
_PD_ROUND_RATE = _PD_SLOT_SHARE / (1 - 3 * _PD_SLOT_SHARE)


# Social-dance display label → code (accent-folded), to bucket library entries
# whose .dance is None but .other_genre names a Modetanz. Tango Argentino comes
# in the same way; it is a dance, only not one the warm-up builder deals.
_WARMUP_OTHER_CODE = {fold_text(DANCE_NAMES[c]): c
                      for c in _WARMUP_MODE + ('TANGOARG',)}


# Dance code → German section header used to separate warm-up rounds in the list
# view (Standardrunde / Lateinrunde / Socialrunde), so the flat Eintanzen list
# reads as the alternating rounds it was actually built from.
_WARMUP_SECTION_LABEL = {
    **{d: 'Standardrunde' for d in _WARMUP_BALLROOM},
    **{d: 'Lateinrunde' for d in _WARMUP_LATIN},
    **{d: 'Socialrunde' for d in _WARMUP_MODE},
}


def warmup_section(entry) -> str | None:
    """Section base label an entry belongs to for warm-up round separators —
    'Standardrunde', 'Lateinrunde' or 'Socialrunde' — or None when its dance
    doesn't map to one of the warm-up sections."""
    return _WARMUP_SECTION_LABEL.get(warmup_code(entry))


def warmup_code(entry) -> str | None:
    """Dance code used to bucket an entry for the warm-up list: the competition
    code when present, else the social-genre code resolved from other_genre."""
    d = getattr(entry, 'dance', None)
    if d:
        return d
    og = getattr(entry, 'other_genre', None)
    if og:
        return _WARMUP_OTHER_CODE.get(fold_text(og))
    return None


def warmup_rounds(entries, *, min_rounds: int = 0) -> list[tuple[str, list]]:
    """Cut a flat warm-up list into the rounds it was built from, numbered per
    section: 'Standardrunde 1', 'Lateinrunde 1', 'Standardrunde 2', …

    A new round starts when the section (Standard / Latin / Social) changes OR a
    dance repeats within the current one: an ETDS list alternates its sections,
    while a per-class list round-robins a single one (SA CC RB PD JI, SA CC RB …)
    so the repeat is what marks each fresh pass. A round opened by a track that
    belongs to no warm-up section is named ''.

    `min_rounds` asks whether the list reads as a warm-up / party list at all:
    set it and the result is [] unless there are at least that many rounds and
    every one of them is named — so a caller can keep whatever it called the
    stretches before. Left at 0 the list is always cut, which is what the
    Eintanzen panel wants: it knows what it is holding."""
    rounds: list[tuple[str | None, list]] = []
    cur_section = None
    cur_codes: set = set()
    for e in entries:
        section = warmup_section(e)
        code = warmup_code(e)
        if (not rounds
                or (section and section != cur_section)
                or (code and code in cur_codes)):
            rounds.append((section, []))
            cur_codes = set()
        rounds[-1][1].append(e)
        if section:
            cur_section = section
        if code:
            cur_codes.add(code)

    counts: dict[str, int] = {}
    named: list[tuple[str, list]] = []
    for section, songs in rounds:
        if not section:
            named.append(("", songs))
            continue
        counts[section] = counts.get(section, 0) + 1
        named.append((f"{section} {counts[section]}", songs))

    if min_rounds and (len(named) < min_rounds
                       or not all(name for name, _ in named)):
        return []
    return named


def warmup_leftover_start(entries) -> int:
    """Index of the first leftover of a party list, len(entries) when it has none.

    The builder alternates Standard and Latin until one of them runs dry; after
    that the other one plays round after round. Those rounds at the end are the
    leftovers. Read backwards from the end, the tail holds only one of the two
    sections. Its first round still follows the last round of the other section
    as it should, so the leftovers start at its second one. Social rounds don't
    count either way. A list cut short by max_tracks ends on at most one round
    of one section, so it has no leftovers."""
    core = ('Standardrunde', 'Lateinrunde')
    rounds = warmup_rounds(entries)
    starts, pos = [], 0
    for _name, songs in rounds:
        starts.append(pos)
        pos += len(songs)
    sections = [name.rsplit(' ', 1)[0] for name, _songs in rounds]
    if not all(c in sections for c in core):
        return len(entries)
    tail = []   # the tail's core rounds, back to front
    for i in range(len(rounds) - 1, -1, -1):
        if sections[i] not in core:
            continue
        if tail and sections[i] != sections[tail[0]]:
            break
        tail.append(i)
    if len(tail) < 2:
        return len(entries)
    return starts[tail[-2]]


def warmup_swap_partner(entries, index, rng=random) -> int | None:
    """Index of the title ↺ swaps entries[index] with on a party list, or None.

    Same dance only. A leftover (see warmup_leftover_start) comes first, else
    any title from the last third of the list, picked at random."""
    code = warmup_code(entries[index])
    if not code:
        return None
    same = [i for i, e in enumerate(entries) if i != index and warmup_code(e) == code]
    start = warmup_leftover_start(entries)
    pool = ([i for i in same if i >= start]
            or [i for i in same if i >= (2 * len(entries)) // 3])
    return rng.choice(pool) if pool else None


def reshuffle_warmup(entries, *, start_with_latin=None, late_ww=True, late_pd=True):
    """🔀 The titles of a party list in a fresh order, as building it again would.

    The sections come from what the list holds, so no title drops out for want
    of a ticked box. `start_with_latin` None keeps the section the list opens
    with. Titles the builder can't place follow at the end, in their old order."""
    codes = [warmup_code(e) for e in entries]
    if start_with_latin is None:
        first = next((c for c in codes if c in _WARMUP_BALLROOM or c in _WARMUP_LATIN), None)
        start_with_latin = first in _WARMUP_LATIN
    order = build_warmup_playlist(
        entries,
        include_standard=any(c in _WARMUP_BALLROOM for c in codes),
        include_latin=any(c in _WARMUP_LATIN for c in codes),
        include_modetaenze=any(c in _WARMUP_MODE for c in codes),
        start_with_latin=start_with_latin, late_ww=late_ww, late_pd=late_pd)
    placed = {id(e) for e in order}
    return order + [e for e in entries if id(e) not in placed]


def _warmup_pick(candidates, pools, exclude=()):
    """Weighted-random one dance from `candidates` that still has tracks left and
    isn't excluded, using the ETDS weights. None when nothing qualifies."""
    avail = [d for d in candidates if d not in exclude and pools.get(d)]
    if not avail:
        return None
    weights = [(_ETDS_PROB.get(d, 0.0) or 0.001) for d in avail]
    return random.choices(avail, weights=weights, k=1)[0]


def _rounds_since(rounds, dance):
    """How many complete rounds of this section have gone by since `dance` was
    last played: 0 when it was in the round right before, 1 when it sat that one
    out, and more than the evening is long when it has never been played.

    `rounds` is the section's own round history — a list of the dance-code lists
    each round planned. Counting ROUNDS is the point: the rule this feeds used
    to look back over "the last six tracks of this section", which is two rounds
    only while every round is three tracks long, and a round that came out short
    silently widened the window."""
    for i, rnd in enumerate(reversed(rounds)):
        if dance in rnd:
            return i
    return len(rounds) + 1


def _section_lead(section):
    """The dance whose ETDS weight a 3-of-5 round cannot deliver on its own —
    LW in Standard, RB in Latin, both asked for at 0.40 where a round can give
    at most 1/3. None when no dance in the section is weighted that heavily."""
    top = max(section, key=lambda d: _ETDS_PROB.get(d, 0.0))
    return top if _ETDS_PROB.get(top, 0.0) > 1 / 3 else None


def _warmup_section_round(result, pools, section, *, late_ww, late_pd, rounds,
                          deferred):
    """Choose three distinct dances for one Standard/Latin round, honouring the
    opener / coverage / lead / late-WW / late-PD / no-Samba-back-to-back rules,
    then pop one track per chosen dance and append to `result`.

    `rounds` is this section's round history (see `_rounds_since`) and is
    APPENDED to with the round that was planned, so the caller keeps one list
    per section and the rules below can count in rounds.

    `deferred` is this section's hand-on: a dance the LAST round drew but could
    not play in competition order (see the Wiener Walzer rule at the bottom).
    It is a one-slot queue the caller keeps alongside `rounds`, emptied by the
    round that honours it."""
    is_latin = section is _WARMUP_LATIN
    avail = [d for d in section if pools.get(d)]
    if not avail:
        return False

    # Very first round of this section gets fixed competition openers.
    first_round = not rounds
    # A dance handed on by the last round opens this one, before every other
    # rule: it was already drawn once and waiting a second round would be the
    # eviction this rule is not.
    owed = deferred.pop() if deferred else None
    if owed and not pools.get(owed):
        owed = None
    if first_round:
        openers = (['CC', 'RB', 'JI'] if is_latin else ['LW', 'TG', 'QS'])
        chosen = [d for d in openers if pools.get(d)]
    else:
        chosen = [owed] if owed else []

    last_round = rounds[-1] if rounds else []
    prev_round = rounds[-2] if len(rounds) > 1 else []
    n_played = len(result)
    lead = _section_lead(section)

    # Does the Paso fall due this round? It is kept out of the weighted fill
    # entirely and placed here instead, on its own percentage.
    #
    # Leaving it in the fill cannot deliver that percentage: `_warmup_pick`
    # renormalises the weights over whoever is still eligible, and with five
    # dances filling three slots the Paso is regularly the last one standing —
    # which is how a weight of 0.025 came to take a sixth of every Latin round.
    # Drawn once per round against the three slots it could have had, it lands
    # where the table asks: a handful of Pasos in an evening, the way the
    # operator's own party lists read. The three-round spacing still comes
    # first, and under "late PD" the 40-track gate ahead of that: the switch
    # says WHEN the Paso may first turn up, not how often — "if I untick late
    # PD it should still use percentage, it not makes sense to enforce PD in 3
    # rounds".
    pd_due = (is_latin and pools.get('PD')
              and (n_played >= 40 or not late_pd)
              and _rounds_since(rounds, 'PD') >= 3
              and random.random() < _PD_ROUND_RATE)

    def in_a_rut(d):
        """Two rounds running is a repeat, three is a rut — "a lot of SF, three
        rounds after each other" is what the floor complained about. Only the
        lead dance is asked for more often than a round can hold (LW / RB at
        0.40 against a third of a round), so only it may run on."""
        return d != lead and d in last_round and d in prev_round

    def late_gated(d):
        """Held back by the operator's own "late WW" / "late PD" switch."""
        if d == 'PD':
            return True     # never drawn by the fill — see `pd_due` above
        return bool(d == 'WW' and late_ww
                    and (n_played < 12 or 'WW' in last_round))

    def forbidden(d):
        if late_gated(d):
            return True
        if d == 'SA' and 'SA' in last_round:   # Samba at most every 2nd round
            return True
        return in_a_rut(d)

    # Coverage guarantee: every dance of the section is played within three of
    # its rounds. One that sat out the last two rounds is overdue and goes into
    # this one BEFORE the probabilistic fill — so a Standard round of LW/TG/QS
    # is followed by the Slow Foxtrot, a Latin one of CC/RB/JI by the Samba.
    # Stalest first, because two can fall due at once and a round has 3 slots.
    #
    # The Paso is never in the set, whichever way its switch is set: a dance
    # weighted 0.025 has no business in every third round, and forcing it there
    # the moment its track gate opened turned it from rare into COMMON —
    # measured at a Paso in 27% of all Latin rounds, against 4% in the
    # operator's own party lists. "After the Paso was first planned it should
    # not be FORCED again in the next 3 rounds, but based on his percentage":
    # that is `pd_due`. The Wiener Walzer, weighted twice as heavily and played
    # in 15-28% of the operator's Standard rounds, is in the set as soon as
    # "late WW" is off.
    if not first_round:
        core = (['SA', 'CC', 'RB', 'JI'] if is_latin
                else ['LW', 'TG', 'SF', 'QS'])
        if not is_latin and not late_ww and pools.get('WW'):
            core.append('WW')
        overdue = sorted((d for d in core if pools.get(d)
                          and d not in chosen
                          and _rounds_since(rounds, d) >= 2
                          and not forbidden(d)),
                         key=lambda d: -_rounds_since(rounds, d))
        if pd_due:
            overdue.insert(0, 'PD')
        for d in overdue:
            if len(chosen) >= 3:
                break
            chosen.append(d)
        # The lead dance (LW / RB) is weighted above the third of a round that
        # is even available to it, so it should sit out at most one round. It
        # comes after the coverage picks — those are a promise, this is a
        # tendency — but ahead of the weighted fill.
        if (lead and lead not in last_round and lead not in chosen
                and pools.get(lead) and not forbidden(lead) and len(chosen) < 3):
            chosen.append(lead)

    while len(chosen) < 3:
        # A round is three dances. Only two things may leave it short of that,
        # in this order: first the rut rule is given up (a dance takes a third
        # round running), and only then does the round shrink.
        #
        # It has to give: the Latin section fills from SA/CC/RB/JI — the Paso
        # is placed on its own percentage, not drawn here — and the Samba may
        # not play two rounds running, so every other round has exactly CC, RB
        # and JI to offer. Two such rounds in a row and all three are in a rut,
        # which is the 28% of Latin rounds that used to come out short.
        #
        # The Samba spacing and the late gates never bend: those are the two
        # the operator asked for by name.
        good = [d for d in avail if d not in chosen and not forbidden(d)]
        if not good:
            good = [d for d in avail if d not in chosen and not late_gated(d)
                    and not (d == 'SA' and 'SA' in last_round)]
        d = _warmup_pick(good, pools) if good else None
        if d is None:
            break
        chosen.append(d)

    if not chosen:
        # Every dance ruled out and tracks still on the shelf: the floor must
        # not go silent, so take the best of a bad lot rather than end the
        # section here (build_warmup_playlist stops as soon as a section stops
        # placing tracks).
        d = _warmup_pick(avail, pools)
        if d:
            chosen.append(d)

    if not chosen:
        return False

    chosen = list(dict.fromkeys(chosen))   # de-dupe, keep order
    chosen.sort(key=lambda d: _WARMUP_ORDER.get(d, 99))

    # No Wiener Walzer directly after a Langsamer Walzer inside the round. This
    # has to be judged AFTER the sort, on the order the round is actually
    # played: _WARMUP_ORDER runs LW, TG, WW, so every round holding both
    # waltzes without a Tango between them comes out of the sort adjacent, in
    # whatever order the picks happened to arrive.
    #
    # The round is NOT rearranged around them. Competition order inside a round
    # is fixed — "i want the order to be fixed in copetition order. in this
    # case where lw ww is shuffled put one of them into the next round" — so
    # the rule is honoured across the round boundary instead: one of the two
    # waltzes is handed to the next round, which opens with it. That is what
    # separates this from dropping a waltz outright, which starves it: it is
    # not lost, it is owed, and the very next round pays it back.
    #
    # WHICH one waits is decided by whose coverage is at stake. Normally the
    # Wiener waits: it was a free draw this round and nothing is owed to it.
    # But once it has sat out two rounds it is the dance the three-round
    # guarantee is about to fail, and a round's delay is exactly what breaks
    # it — so then the Langsamer waits instead. That costs the Langsamer
    # nothing: it is the lead dance, and its own rule ("sits out at most one
    # round") brings it back in the very next round anyway.
    #
    # This also ends the hand-on: a Wiener passed over twice has been sitting
    # out two rounds by definition, so the third collision hands on the
    # Langsamer and the Wiener plays.
    #
    # The freed slot is refilled by the ordinary weighted pick, under the same
    # rules as any other — an earlier version took a stand-in straight from
    # ('QS', 'SF', 'TG') and so could hand a dance the third round running that
    # the fill above had just refused it.
    if 'LW' in chosen and 'WW' in chosen \
            and chosen.index('WW') == chosen.index('LW') + 1:
        hand = ('LW' if _rounds_since(rounds, 'WW') >= 2 and 'LW' in last_round
                else 'WW')
        chosen.remove(hand)
        deferred.append(hand)
        fill = _warmup_pick([d for d in avail
                             if d != hand and d not in chosen
                             and not forbidden(d)], pools)
        if fill is None:
            # Two tiers, the same way the fill loop above has them: a round
            # that comes out short is one `check_party_list` reports as broken
            # ("'Standardrunde 3' is 2 titles long, not 3"), so the rut rule
            # gives way before the round does.
            fill = _warmup_pick([d for d in avail
                                 if d != hand and d not in chosen
                                 and not late_gated(d)], pools)
        if fill:
            chosen.append(fill)
            chosen.sort(key=lambda d: _WARMUP_ORDER.get(d, 99))

    took = []
    for d in chosen:
        lst = pools.get(d)
        if lst:
            result.append(lst.pop())
            took.append(d)
    # Only what actually got a track counts as played — a dance whose pool ran
    # dry between the choice and the draw must not start a coverage countdown.
    if took:
        rounds.append(took)
    return bool(took)


def _warmup_mode_round(result, pools, mode_dances, *, first=False,
                       allow_double=True):
    """One social-dance interlude: one Modetanz, or two — and a double opens
    with Discofox.

    How LONG the round is gets decided first, because that is what the floor
    feels: two rounds in three hold a single title, so the socials stay the
    breather between the competition rounds instead of becoming a block of
    their own. A double is the one that fills the floor, and Discofox is what
    fills it — it leads, and the second title is a weighted pick from the rest.
    A single is a weighted pick like any other (Discofox may well win it) —
    except the evening's very FIRST social round (`first`), which always leads
    with Discofox: that one has to get the floor filled in the first place.

    With Discofox unticked both slots are plain weighted picks; the round keeps
    its length either way.

    `allow_double` False holds it to a single title whatever the draw says —
    see the Paso rule in `build_warmup_playlist`."""
    avail = [d for d in mode_dances if pools.get(d)]
    if not avail:
        return False
    two = allow_double and random.random() < 1 / 3
    if (two or first) and 'DISCOFOX' in avail:
        chosen = ['DISCOFOX']
    else:
        chosen = [_warmup_pick(avail, pools)]
    if two:
        second = _warmup_pick(avail, pools, exclude=chosen)
        if second:
            chosen.append(second)
    took = False
    for d in chosen:
        lst = pools.get(d)
        if lst:
            result.append(lst.pop())
            took = True
    return took


def build_warmup_playlist(entries, *, include_standard=True, include_latin=True,
                          include_modetaenze=False, modetaenze=None, no_paso=False,
                          start_with_latin=False, late_ww=True, late_pd=True,
                          max_tracks=None, progress_cb=None):
    """Build a warm-up ('Eintanzen') playlist from `entries` — a flat, ordered
    list of MusicEntry, each track used once. Dances are drawn in alternating
    3-dance Standard / Latin rounds with optional Modetanz interludes.

    `modetaenze` restricts which social dances may appear (a subset of
    _WARMUP_MODE codes); None means all of them. Ignored unless
    `include_modetaenze` is set. `max_tracks` caps the list length (mainly to keep a whole-library party list
    manageable); None / 0 means use every eligible track. `progress_cb(done,
    total)` is called as tracks are placed (`total` is the number of tracks the
    active sections can contribute, capped at `max_tracks`), so a big library
    shows a real progress bar instead of an indeterminate pulse."""
    pools: dict[str, list] = {}
    for e in entries:
        code = warmup_code(e)
        if code:
            pools.setdefault(code, []).append(e)
    for lst in pools.values():
        random.shuffle(lst)
    if no_paso:
        pools.pop('PD', None)
    if not include_standard:
        for d in _WARMUP_BALLROOM:
            pools.pop(d, None)
    if not include_latin:
        for d in _WARMUP_LATIN:
            pools.pop(d, None)
    if include_modetaenze:
        allowed = set(modetaenze) if modetaenze is not None else set(_WARMUP_MODE)
        mode_dances = [d for d in _WARMUP_MODE if d in allowed]
    else:
        mode_dances = []

    def section_has(section):
        return any(pools.get(d) for d in section)

    # Tracks the active sections can contribute — the progress-bar denominator.
    # (Mode pools linger in `pools` when Modetänze are off, so count only what
    # will actually be drawn.)
    drawable = list(_WARMUP_BALLROOM) + list(_WARMUP_LATIN) + mode_dances
    total = sum(len(pools.get(d, [])) for d in drawable)
    cap = int(max_tracks) if max_tracks else 0
    if cap:
        total = min(total, cap)
    if progress_cb:
        progress_cb(0, total)

    result: list = []
    # Fixed section cycle per pass — Standard, then Latin, then an optional social
    # interlude — so the list reads STD → LAT → Social → STD → LAT → Social …
    # (start_with_latin swaps the two competition sections). The order is NOT
    # flipped every pass; flipping produced the wrong STD LAT | LAT STD | … run.
    order = ([_WARMUP_LATIN, _WARMUP_BALLROOM] if start_with_latin
             else [_WARMUP_BALLROOM, _WARMUP_LATIN])
    # One round history per section — what the coverage and no-rut rules count.
    history: dict[tuple, list[list[str]]] = {_WARMUP_BALLROOM: [],
                                             _WARMUP_LATIN: []}
    # One hand-on slot per section, alongside the history — see
    # _warmup_section_round's `deferred`.
    owing: dict[tuple, list[str]] = {_WARMUP_BALLROOM: [], _WARMUP_LATIN: []}
    # The first social round of the evening leads with Discofox — see
    # _warmup_mode_round. A round that placed nothing does not count as opened.
    social_opened = False
    # Cap iterations so a tiny / lopsided pool can never spin forever.
    guard = sum(len(v) for v in pools.values()) * 2 + 50

    def cap_reached():
        """`max_tracks` is a length the operator asked for, not a place to
        cut. The loop therefore stops BETWEEN rounds: a round that has
        started is played out, so the list can run a title or two past the
        cap rather than end on half a round — "i dont want a round run
        short". Slicing the result to the cap instead ended 40 of 40 seeds
        on a one-track round at the spinbox's own default of 100."""
        return bool(cap) and len(result) >= cap
    while guard > 0 and (section_has(_WARMUP_BALLROOM) or section_has(_WARMUP_LATIN)
                         or any(pools.get(d) for d in mode_dances)):
        guard -= 1
        progressed = False
        for section in order:
            if ((section is _WARMUP_BALLROOM and not include_standard)
                    or (section is _WARMUP_LATIN and not include_latin)):
                continue
            if _warmup_section_round(result, pools, section,
                                     late_ww=late_ww, late_pd=late_pd,
                                     rounds=history[section],
                                     deferred=owing[section]):
                progressed = True
            if cap_reached():
                break
        # A Paso that closes the Latin round opens straight onto the social
        # interlude, and two Modetänze behind it empty the floor for two titles
        # running right after the evening's rarest dance. So that interlude is
        # held to a single title. It is the interlude that gives way, not the
        # Paso: moving the Paso instead would eat into the percentage its
        # placement was tuned to. A Jive drawn into the same round sorts BEHIND
        # the Paso (SA CC RB PD JI) and separates the two, so that round keeps
        # its double.
        after_paso = bool(result) and warmup_code(result[-1]) == 'PD'
        if (not cap_reached() and mode_dances
                and _warmup_mode_round(result, pools, mode_dances,
                                       first=not social_opened,
                                       allow_double=not after_paso)):
            social_opened = True
            progressed = True
        if progress_cb:
            progress_cb(min(len(result), total), total)
        if cap_reached():
            break
        if not progressed:
            break
    if progress_cb:
        progress_cb(len(result), len(result))
    return result


def warmup_lengths(entries) -> dict[str, list[float]]:
    """Known track lengths (seconds) per warm-up dance code; tracks without a
    length or outside the warm-up dances are left out."""
    lengths: dict[str, list[float]] = {}
    for e in entries:
        code = warmup_code(e)
        secs = getattr(e, 'duration', 0) or 0
        if code and secs > 0:
            lengths.setdefault(code, []).append(secs)
    return lengths


def estimate_warmup_counts(lengths, hours, *, runs=40, fallback_secs=210.0,
                           should_stop=None, **options):
    """⏱ How many songs per dance a party list of `hours` play time needs.

    Builds `runs` lists with the real `build_warmup_playlist` (`options` are its
    keyword options) from made-up pools, each track's length drawn from that
    dance's `lengths` (see `warmup_lengths`; `fallback_secs` for a dance with
    none), and counts every list up to the target — full length, no pauses.

    Returns `(counts, total)`: `counts` maps each dance that appeared to
    `(mean, stock)`, `total` is the same pair for the whole list. `stock` is the
    count that suffices for 9 of 10 lists. `should_stop()` is asked between runs;
    when it says yes the estimate is abandoned and None comes back."""
    target = hours * 3600
    codes = _WARMUP_BALLROOM + _WARMUP_LATIN + _WARMUP_MODE
    label = {c: k for k, c in _WARMUP_OTHER_CODE.items()}
    # The builder slows down with the square of the list length, so build only
    # about as long as the target needs (sized by the shortest typical dance),
    # doubling when a list still falls short. Pools hold `cap` per dance, so no
    # dance ever runs dry and bends the round shape.
    typical = min(statistics.median(lengths.get(c) or [fallback_secs]) for c in codes)
    cap = int(target / typical) + 3
    per_run = []
    for _ in range(runs):
        if should_stop and should_stop():
            return None
        while True:
            pool = []
            for c in codes:
                known = lengths.get(c) or [fallback_secs]
                pool += [SimpleNamespace(dance=None if c in label else c,
                                         other_genre=label.get(c),
                                         duration=random.choice(known))
                         for _ in range(cap)]
            tracks = build_warmup_playlist(pool, max_tracks=cap, **options)
            if len(tracks) < cap or sum(e.duration for e in tracks) >= target:
                break
            cap *= 2
        played = 0.0
        counts: dict[str, int] = {}
        for e in tracks:
            if played >= target:
                break
            played += e.duration
            code = warmup_code(e)
            counts[code] = counts.get(code, 0) + 1
        per_run.append(counts)

    def mean_and_stock(values):
        values = sorted(values)
        return sum(values) / len(values), values[max(0, math.ceil(len(values) * 0.9) - 1)]
    seen = {c for counts in per_run for c in counts}
    return ({c: mean_and_stock([counts.get(c, 0) for counts in per_run])
             for c in codes if c in seen},
            mean_and_stock([sum(counts.values()) for counts in per_run]))


def class_warmup_pool(entries, style, dance, dance_class, *, relax=True):
    """TSO-conform, class- and style-scoped candidate list for one dance of a
    tournament-class warm-up. Mirrors the competition pool's tempo/class/style
    filters; `relax` keeps the slight pitch-up margin (BELOW_TEMPO_EXT, e.g.
    T30 Tango) the normal playlist also allows. rb23 stays out."""
    lo, hi = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))
    ext = BELOW_TEMPO_EXT.get(dance, 0) if relax else 0
    out = []
    for e in entries:
        if getattr(e, 'is_xmas', False) or is_non_turnier(e):
            continue
        if getattr(e, 'dance', None) != dance:
            continue
        if not entry_in_style(e, style):
            continue
        bpm = getattr(e, 'bpm', None)
        if bpm is not None and not ((lo - ext) <= bpm <= hi):
            continue
        cok = getattr(e, 'classes_ok', None)
        if cok and dance_class not in cok:
            continue
        out.append(e)
    return out


def build_class_warmup(entries, style, dance_class, *, max_tracks=200,
                       fresh_ratio=0.25, relax=True, progress_cb=None):
    """Warm-up playlist for ONE tournament class (e.g. Latin 'S'): the class's
    dances (DEFAULT_DANCES[style][dance_class]) repeated round-robin —
    SA, CC, RB, PD, JI, SA, CC, … — each track used once, every track TSO-conform.

    `fresh_ratio` (0..1) is the share of slots that should lean FRESH. Each dance
    keeps ONE queue ordered by class-weighted popularity (most-played first); a
    proven-leaning slot takes the popular FRONT, a fresh-leaning slot the
    least-played BACK. So fresh_ratio≈1.0 really does pull in the never/barely-
    played tracks (and falls back through the rest from least to most popular when
    the truly-fresh ones run out) instead of just topping up the favourites — the
    old hard proven/fresh split capped "fresh" at however few pop<5 tracks existed.
    Stops at `max_tracks` or when the pools run dry. `progress_cb(done, total)` is
    called as slots fill.
    """
    dances = DEFAULT_DANCES.get(style, {}).get(dance_class)
    if not dances:
        return []
    fresh_ratio = max(0.0, min(1.0, float(fresh_ratio)))

    # One queue per dance, ordered by class-weighted popularity DESC (with a little
    # jitter so two runs aren't byte-identical). Proven picks come off the left
    # (most-played), fresh picks off the right (least-played / never used).
    queues: dict[str, deque] = {}
    for d in dances:
        pool = class_warmup_pool(entries, style, d, dance_class, relax=relax)
        pool.sort(key=lambda e: (effective_popularity(e, dance_class),
                                 random.random()), reverse=True)
        queues[d] = deque(pool)

    avail_total = sum(len(q) for q in queues.values())
    total = min(int(max_tracks), avail_total)
    if total <= 0:
        if progress_cb:
            progress_cb(0, 0)
        return []

    result: list = []
    guard = total * 4 + 50
    while len(result) < total and guard > 0:
        guard -= 1
        progressed = False
        for d in dances:
            if len(result) >= total:
                break
            q = queues[d]
            if not q:
                continue
            # Fresh-leaning slot → least-played end; otherwise → most-played end.
            pick = q.pop() if random.random() < fresh_ratio else q.popleft()
            result.append(pick)
            progressed = True
            if progress_cb:
                progress_cb(len(result), total)
        if not progressed:
            break
    if progress_cb:
        progress_cb(len(result), total)
    return result


def entry_in_style(entry: MusicEntry, style: str | None) -> bool:
    """True if `entry` belongs to the given competition style based on its folder.

    Standard/Latin → the track must live under the style's folder. 'Others' →
    the track must live OUTSIDE every Standard/Latin folder. style=None means
    no folder scoping (legacy behaviour: accept everything).
    """
    segs = {p.lower() for p in entry.path.parts}
    if segs & _EXCLUDED_FOLDERS:        # hard-excluded folders (e.g. sox) – never used
        return False
    if style is None:
        return True
    folders = STYLE_FOLDERS.get(style)
    if folders is not None:
        return any(f in segs for f in folders)
    return not (segs & _RESERVED_STYLE_FOLDERS)   # 'Others' = the complement


def others_dance_from_path(path: Path) -> str | None:
    """Classify a social track into one of OTHERS_DANCES by its path alone.

    The filename is checked first so a track inside a mixed-compilation folder
    is classified by its own name; only then do we fall back to the dedicated
    folder name. Both sides are accent-folded, so 'Forró' in any Unicode
    normalization matches the plain 'forro' key. Returns the dance code, or
    None when nothing matches.
    """
    stem = fold_text(path.stem)
    for code, spec in OTHERS_DANCES.items():
        if any(len(k) >= 4 and k in stem for k in spec['keys']):
            return code
    segs = [fold_text(p) for p in path.parts[:-1]]   # folders only
    for code, spec in OTHERS_DANCES.items():
        for k in spec['keys']:
            if any(s == k for s in segs):
                return code
            if len(k) >= 4 and any(k in s for s in segs):
                return code
    return None


def others_dance_of(entry: MusicEntry) -> str | None:
    """Classify an 'Others' (social) track into one of OTHERS_DANCES."""
    return others_dance_from_path(entry.path)
