"""Playlist assembly: turns a configured library + rounds into a Playlist.

Extracted from dancesport_planner.py (logical split): PlaylistSuggester builds
the per-round/per-heat grid using MusicLibrary, plus generate_hints for the
post-build advisory notes.
"""
import logging

from collections import Counter, defaultdict
import random
from typing import Any
from planner import i18n
from planner.db import (  # auto-resolved
    AudioFeatures,
)
from planner.similarity import (  # auto-resolved
    _STRONG_TIMBRE,
    _timbre_similarity,
)
from planner.models import (  # auto-resolved
    ALLOW_REPEAT,
    BELOW_TEMPO_EXT,
    FAST_DANCES,
    MusicEntry,
    Playlist,
    RoundConfig,
    SLOW_DANCES,
    TEMPO_RANGES,
    is_non_turnier,
)
from planner.terms import dance_name
from planner.parsing import (  # auto-resolved
    _bpm_fit,
)
from planner.scoring import (  # auto-resolved
    BONUS_CLASS_OK,
    BONUS_FRESH,
    BONUS_PROVEN,
    PENALTY_BELOW_TEMPO,
    PENALTY_CLASS_DILUTED,
    PENALTY_CLASS_MISMATCH,
    RANDOM_TIEBREAK,
    W_BPM_FIT,
    W_POPULARITY,
    W_TIMBRE,
    _PROVEN_MIN_POP,
    _resolve_strategy,
    class_dilutes,
    class_popularity,
    effective_popularity,
    prefer_late_rounds,
)
from planner.themes import (  # auto-resolved
    all_themes,
    load_user_themes,
)
from planner.warmup import (  # auto-resolved
    class_warmup_pool,
    entry_in_style,
    others_dance_of,
)
from planner.library import (  # auto-resolved
    MusicLibrary,
    _ANCHOR_DEFAULT,
)

log = logging.getLogger("dancesport.suggester")


class PlaylistSuggester:
    def __init__(self, library: MusicLibrary):
        self.lib = library
        self._anchors: dict[str, AudioFeatures | None] = {}

    def suggest(
        self,
        dance_class: str,
        rounds:      list[RoundConfig],
        dances:      list[str],
        use_timbre:  bool = True,
        style:       str | None = None,
        round_pools: list[list[MusicEntry]] | None = None,
        exclude:     set | None = None,
    ) -> Playlist:
        # `exclude` seeds the no-repeat set with paths already used elsewhere
        # (the day planner's cross-competition pool). ALLOW_REPEAT dances (PD)
        # are exempt automatically — their pools never consult `used`.
        used: set      = set(exclude or ())   # strict no-repeat (non-ALLOW_REPEAT dances)
        pd_used: set   = set()   # soft no-repeat for PD – prefer variety, allow reuse
        result: Playlist = {}

        for ri, rc in enumerate(rounds):
            # 'Past competitions' mode passes per-round candidate pools so each
            # round draws only from songs history used in that same round.
            candidates = (round_pools[ri]
                          if round_pools and ri < len(round_pools) else None)
            result[rc.name] = self._suggest_round(
                rc, dances, dance_class, used, pd_used,
                use_timbre=use_timbre, style=style, candidates=candidates,
            )

        return result

    def _suggest_round(
        self,
        rc:          RoundConfig,
        dances:      list[str],
        dance_class: str,
        used:        set,
        pd_used:     set,
        use_timbre:  bool = True,
        style:       str | None = None,
        candidates:  list[MusicEntry] | None = None,
    ) -> list[list[MusicEntry | None]]:
        """Build one round's heats, mutating `used`/`pd_used` so the rest of the
        playlist (or other untouched rounds, when re-rolling a single round) stays
        repeat-free. Records the round's timbral anchor for later regeneration."""
        heats_data: list[list[MusicEntry | None]] = []
        anchor: AudioFeatures | None = None   # round's timbral reference
        for _ in range(rc.heats):
            heat: list[MusicEntry | None] = []
            for dance in dances:
                soft = pd_used if dance in ALLOW_REPEAT else None
                entry = self._pick(dance, dance_class,
                                   rc.tier, used,
                                   anchor if use_timbre else None,
                                   soft,
                                   prefer_fresh=rc.prefer_fresh,
                                   strategy=rc.strategy or None,
                                   style=style,
                                   candidates=candidates)
                if entry:
                    if anchor is None and entry.features and use_timbre:
                        anchor = entry.features
                    if dance in ALLOW_REPEAT:
                        pd_used.add(str(entry.path))
                    else:
                        used.add(str(entry.path))
                heat.append(entry)
            heats_data.append(heat)
        self._anchors[rc.name] = anchor
        return heats_data

    def regenerate_round(
        self,
        rc:          RoundConfig,
        dances:      list[str],
        dance_class: str,
        used:        set,
        pd_used:     set | None = None,
        use_timbre:  bool = True,
        style:       str | None = None,
        candidates:  list[MusicEntry] | None = None,
    ) -> list[list[MusicEntry | None]]:
        """Re-roll a whole round in place (used when a strategy combo changes).

        `used` must already hold the paths picked by the OTHER rounds so the
        re-rolled round does not duplicate them. `candidates` is that round's
        history pool ('past competitions'); empty dances fall back to the full
        library inside `_get_pool`."""
        return self._suggest_round(
            rc, dances, dance_class, used,
            pd_used if pd_used is not None else set(),
            use_timbre=use_timbre, style=style, candidates=candidates,
        )

    def _get_pool(self, dance: str, dance_class: str,
                  tier: str, used: set,
                  soft_used: set | None = None,
                  prefer_fresh: bool = False,
                  strategy: str | None = None,
                  style: str | None = None,
                  candidates: list[MusicEntry] | None = None) -> list[MusicEntry]:
        """Return a candidate pool for this dance + tier, honouring `strategy`.

        Strategy decides which songs the round may draw from (see STRATEGIES);
        when not given it derives from the tier / legacy prefer_fresh flag via
        `_resolve_strategy`. `style` (Standard/Latin/Others) restricts the pool
        to the matching library folder so cross-style folders never leak in.
        `candidates`, when given ('past competitions' per-round pool), replaces the
        whole-library base — falling back to the full library for a dance that the
        round's history never used, so the slot is not forced blank.
        """
        strat = _resolve_strategy(tier, prefer_fresh, strategy)
        lo, hi = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))

        if style == 'Others':
            # Social dances: classify by folder/name, no tournament-tempo filter.
            base = candidates if candidates is not None else self.lib.entries
            all_songs = [e for e in base
                         if not e.is_xmas and not is_non_turnier(e)
                         and others_dance_of(e) == dance
                         and entry_in_style(e, 'Others')]
            if not all_songs and candidates is not None:
                all_songs = [e for e in self.lib.entries
                             if not e.is_xmas and not is_non_turnier(e)
                             and others_dance_of(e) == dance
                             and entry_in_style(e, 'Others')]
            bpm_ok = all_songs
        else:
            if candidates is not None:
                base = [e for e in candidates if e.dance == dance]
                if not base:
                    base = self.lib.by_dance(dance)
            else:
                base = self.lib.by_dance(dance)
            all_songs = [e for e in base
                         if not e.is_xmas and not is_non_turnier(e)
                         and entry_in_style(e, style)]
            ext    = BELOW_TEMPO_EXT.get(dance, 0)
            bpm_ok = [e for e in all_songs if e.bpm is None or (lo - ext) <= e.bpm <= hi]

        # Hard-exclude songs that carry class tags incompatible with the current class
        # (e.g. a song tagged [D] should never appear in an S-class playlist).
        # Fall back to unfiltered only if every song in the dance is class-restricted.
        class_fit = [e for e in bpm_ok if not e.classes_ok or dance_class in e.classes_ok]
        bpm_ok = class_fit or bpm_ok

        if dance in ALLOW_REPEAT:
            not_soft = [e for e in bpm_ok if str(e.path) not in (soft_used or set())]
            base     = not_soft or bpm_ok or all_songs
            if strat in ('proven', 'top_proven'):
                # In a final or a semifinal, having BEEN in that round comes
                # first — see the long comment on the same step below.
                base = prefer_late_rounds(base, tier)
                pool = [e for e in base if e.popularity >= _PROVEN_MIN_POP] or base
                pool = ([e for e in pool
                         if class_popularity(e, dance_class) > 0
                         and effective_popularity(e, dance_class) >= _PROVEN_MIN_POP]
                        or [e for e in pool if class_popularity(e, dance_class) > 0]
                        or pool)
            elif strat == 'fresh':
                fresh = [e for e in base if e.popularity < _PROVEN_MIN_POP]
                pool  = fresh or base
            else:   # mixed / all → whole base pool
                pool = base
            return pool

        # `available` = in-tempo songs NOT already used elsewhere in this playlist.
        # All fallbacks stay within `available`, so a song's path is never reused
        # (hard no-repeat for non-PD dances). When `available` runs dry the pool is
        # empty → the slot stays blank rather than duplicating an earlier pick.
        available = [e for e in bpm_ok if str(e.path) not in used]

        # A FINAL — and a SEMIFINAL — is picked from what that round has used.
        # This has to happen BEFORE the play-count cuts below, not after:
        # 'top_proven' keeps only the most-played tracks, and the most-played
        # tracks are heat music — a preliminary needs ten per dance, these two
        # rounds need one. Applied afterwards the finalists would already be gone.
        if strat in ('proven', 'top_proven'):
            available = prefer_late_rounds(available, tier)

        proven    = [e for e in available if e.popularity >= _PROVEN_MIN_POP]
        fresh     = [e for e in available if e.popularity <  _PROVEN_MIN_POP]
        high_pop  = [e for e in available if e.popularity >= _PROVEN_MIN_POP * 2]
        mid_pop   = proven

        if strat == 'top_proven':
            pool = high_pop or mid_pop or proven or available
        elif strat == 'proven':
            pool = proven or available
        elif strat == 'fresh':
            pool = fresh or available
        else:   # mixed / all → proven + fresh together, widest in-tempo pool
            pool = available

        # Class-aware popularity: under the proven strategies, prefer the songs that
        # were really PLAYED in this start class (class parsed from the playlist
        # file/folder names) — a title proven only in D/C lists shouldn't lead an
        # S-class round. Two stages: proven FOR THIS CLASS (≥1 same-class play AND
        # class-weighted popularity over the threshold) first, then merely
        # played-once-in-class, then the full strategy pool (a class with little
        # history must not end up with blank slots).
        if strat in ('proven', 'top_proven'):
            pool = ([e for e in pool
                     if class_popularity(e, dance_class) > 0
                     and effective_popularity(e, dance_class) >= _PROVEN_MIN_POP]
                    or [e for e in pool if class_popularity(e, dance_class) > 0]
                    or pool)

        return pool

    def _pick(
        self,
        dance:        str,
        dance_class:  str,
        tier:         str,
        used:         set,
        anchor:       AudioFeatures | None,
        soft_used:    set | None = None,
        prefer_fresh: bool = False,
        strategy:     str | None = None,
        style:        str | None = None,
        candidates:   list[MusicEntry] | None = None,
        timbre_first: bool = False,
    ) -> MusicEntry | None:
        lo, hi = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))

        strat = _resolve_strategy(tier, prefer_fresh, strategy)
        # Pass the RESOLVED strategy down so _get_pool doesn't re-derive it.
        pool = self._get_pool(dance, dance_class, tier, used, soft_used,
                              prefer_fresh, strat, style, candidates)
        if not pool:
            return None

        # Timbre similarity of the whole pool to the round anchor, via the app's
        # default metric (`_timbre_similarity` → Gaussian/KL). Empty when no anchor.
        sims = _timbre_similarity(anchor, pool) if anchor else {}

        def score(e: MusicEntry) -> float:
            # 'all' = no proven/fresh preference → popularity must not bias the pick.
            # Popularity is CLASS-WEIGHTED (see effective_popularity): plays in the
            # selected start class count fully, other-class plays barely — so a
            # D-class warhorse can't outrank the genuine S staples in an S round.
            s = effective_popularity(e, dance_class) * (0 if strat == 'all' else W_POPULARITY)
            s += _bpm_fit(e.bpm, lo, hi) * W_BPM_FIT
            if e.bpm is not None and e.bpm < lo:
                s -= PENALTY_BELOW_TEMPO
            if anchor and e.features:
                s += sims.get(str(e.path), 0.5) * W_TIMBRE
            if strat == 'fresh' and e.popularity < _PROVEN_MIN_POP:
                s += BONUS_FRESH
            if strat == 'proven' and e.popularity >= _PROVEN_MIN_POP:
                s += BONUS_PROVEN
            if e.classes_ok:
                if dance_class in e.classes_ok:
                    s += BONUS_CLASS_OK
                    # A B/A/S event prefers the music tagged for that level over
                    # the titles that also carry D and C — unless this one has
                    # been played in this class before, which was a decision.
                    if class_dilutes(e, dance_class):
                        s -= PENALTY_CLASS_DILUTED
                else:
                    s -= PENALTY_CLASS_MISMATCH
            s += random.random() * RANDOM_TIEBREAK   # spread comes from weighting
            return s

        # ── Replace / ↺ mode: TIMBRE is the first criterion, popularity orders within ──
        # The pool is already gated by strategy (e.g. proven-only) + BPM + class. Build a
        # closest-sounding shortlist, then pick PROBABILISTICALLY among it so the better
        # match comes up most of the time but a weaker one still surfaces now and then.
        #
        # Shortlist = the 10 closest tracks, but:
        #   • every track tied with the 10th's similarity is kept too (no arbitrary
        #     boundary cut when several sound equally close), and
        #   • any strong match (similarity ≥ 0.80) is included even if it ranks below 10,
        #     so a deep pool of near-identical tracks isn't truncated to 10.
        # Weight = (popularity + 1) × similarity²: among equally-played tracks the closer
        # match wins more often, yet a lower one keeps a real chance (not deterministic).
        if timbre_first and anchor:
            by_timbre = sorted(pool, key=lambda e: sims.get(str(e.path), 0.5), reverse=True)
            n = max(1, min(10, len(by_timbre)))
            cutoff = sims.get(str(by_timbre[n - 1].path), 0.5)   # similarity of the 10th
            threshold = min(cutoff, _STRONG_TIMBRE)        # ≥ top-10 floor, and ≥ 0.80
            shortlist = [e for e in by_timbre if sims.get(str(e.path), 0.5) >= threshold] \
                or by_timbre[:n]

            # How strongly playlist-proven-ness tilts the ↺ pick depends on the strategy
            # (timbre, the sim² term, always stays the dominant factor — this only breaks
            # ties among similar-sounding matches):
            #   all    → no bias at all (egalitarian; playlists ignored)
            #   fresh  → strongly favour never-played tracks
            #   mixed  → gentle proven lean (≤ 2.2×), so a fresh track keeps a real chance
            #   proven / top_proven → favour your most-played tracks
            # Previously this was always (popularity+1), so 'all' wasn't neutral and 'mixed'
            # buried fresh tracks under heavily-played ones (a pop-6 track outweighed a fresh
            # one 6:1 even when both sounded equally close).
            def _pop_weight(e: MusicEntry) -> float:
                # Proven-ness is CLASS-WEIGHTED (effective_popularity) so a ↺ in an
                # S round leans on real S history; 'fresh' keeps the GLOBAL count
                # (fresh = never played anywhere, regardless of class).
                ep = effective_popularity(e, dance_class)
                if strat == 'all':
                    return 1.0
                if strat == 'fresh':
                    return 2.0 if e.popularity < _PROVEN_MIN_POP else 0.4
                if strat == 'mixed':
                    return 1.0 + min(ep, 3) * 0.4
                return ep + 1.0

            # +0.01 floor so a near-zero similarity (cosine ≈ -1) still yields a positive
            # weight — random.choices() raises if every weight sums to zero.
            weights = [_pop_weight(e) * (sims.get(str(e.path), 0.5) ** 2 + 0.01)
                       for e in shortlist]
            chosen = random.choices(shortlist, weights=weights, k=1)[0]
            chosen.sim_score = sims.get(str(chosen.path), 0.5)
            return chosen

        # ── Generation / whole-round: composite score (popularity-led), weighted pick ──
        # Better score → higher chance, but not deterministic; weight = how far each
        # candidate sits above the weakest of the shortlist (+ a floor so it keeps a chance).
        scored = sorted(((score(e), e) for e in pool), key=lambda x: x[0], reverse=True)
        top = scored[:max(1, min(10, len(scored)))]
        base = top[-1][0]
        weights = [(s - base) + 0.1 for s, _ in top]
        chosen = random.choices([e for _, e in top], weights=weights, k=1)[0]
        # Store timbral similarity to the round anchor for display
        if anchor and chosen.features:
            chosen.sim_score = sims.get(str(chosen.path), 0.5)
        else:
            chosen.sim_score = None
        return chosen

    def regenerate(
        self,
        dance:        str,
        dance_class:  str,
        tier:         str,
        exclude:      set,
        prefer_fresh: bool = False,
        round_name:   str | None = None,
        use_timbre:   bool = True,
        strategy:     str | None = None,
        style:        str | None = None,
        candidates:   list[MusicEntry] | None = None,
        anchor:       Any = _ANCHOR_DEFAULT,
    ) -> MusicEntry | None:
        # `anchor` lets the caller override the round's stored reference — e.g. when
        # re-rolling the anchor song ITSELF, the GUI passes the next song's features so
        # the replacement matches the rest of the round instead of the song being removed.
        if anchor is _ANCHOR_DEFAULT:
            anchor = self._anchors.get(round_name) if round_name else None
        if not use_timbre:
            anchor = None
        # PD's pool never consults `used`, only the soft set — so hand it the
        # planned songs there: a re-roll prefers a PD the list doesn't have yet
        # and still repeats one when the library has no other.
        soft = exclude if dance in ALLOW_REPEAT else None
        return self._pick(dance, dance_class, tier, exclude, anchor=anchor,
                          soft_used=soft,
                          prefer_fresh=prefer_fresh, strategy=strategy, style=style,
                          candidates=candidates, timbre_first=True)

    def anchor_similarity(self, entry: MusicEntry,
                          round_name: str | None,
                          anchor: Any = _ANCHOR_DEFAULT) -> float | None:
        """Timbral similarity (0..1) of `entry` to a round's anchor, for display.

        Used when a song is placed manually (e.g. dropped from the Similar-Tracks
        window) so its ≈ / hover-% matches how the auto-picker would have scored it.
        Pass `anchor` to override the round's stored reference (same fallback as
        `regenerate` when the anchor song itself is the one being replaced). Returns
        None when there is no anchor or the track has no audio features."""
        if anchor is _ANCHOR_DEFAULT:
            anchor = self._anchors.get(round_name) if round_name else None
        if anchor is None or entry.features is None:
            return None
        return _timbre_similarity(anchor, [entry]).get(str(entry.path))

    def regenerate_warmup(self, dance: str, style: str | None,
                          dance_class: str | None, exclude: set, *,
                          anchor_entry: MusicEntry | None = None,
                          relax: bool = True) -> MusicEntry | None:
        """Pick a replacement warm-up track: same dance, TSO-conform for the class,
        not already used (`exclude` = set of paths), ranked by timbre similarity to
        `anchor_entry` (the track being replaced) with a popularity + jitter tie-break.
        `style` may be None / unknown (ETDS party) — then every style is tried."""
        dance_class = dance_class or "S"
        styles = [style] if style in ("Standard", "Latin", "Others") \
            else ["Standard", "Latin", "Others"]
        pool: list[MusicEntry] = []
        for st in styles:
            pool = [e for e in class_warmup_pool(self.lib.entries, st, dance,
                                                 dance_class, relax=relax)
                    if str(e.path) not in exclude]
            if pool:
                break
        if not pool:
            return None
        sims = {}
        if anchor_entry is not None and getattr(anchor_entry, "features", None) is not None:
            sims = _timbre_similarity(anchor_entry.features, pool)

        def score(e: MusicEntry) -> float:
            sim = sims.get(str(e.path), 0.0)
            pop = min(effective_popularity(e, dance_class), 10.0)
            return sim * 5.0 + pop * 0.3 + random.random() * 0.5
        pool.sort(key=score, reverse=True)
        return pool[0]

    # ── Theme mode ─────────────────────────────────────────────────────────────
    def suggest_theme(self, theme_name: str, count: int = 30) -> list[MusicEntry]:
        """Build a flat, themed playlist (wedding, 90s, party …).

        Picks the best `count` matching tracks (popularity + light randomness),
        then round-robins across dances so the same dance doesn't cluster.
        """
        themes = all_themes()
        spec = themes.get(theme_name)
        if spec is None:
            return []
        _, track_themes = load_user_themes()

        def matches(e: MusicEntry) -> bool:
            if e.is_xmas or is_non_turnier(e):
                return False
            forced = theme_name in track_themes.get(e.path.stem.lower(), [])
            if forced:
                return True
            if e.dance is None:          # only danceable competition tracks otherwise
                return False
            if 'dances' in spec and e.dance not in spec['dances']:
                return False
            if 'year_range' in spec:
                lo, hi = spec['year_range']
                if e.year is None or not (lo <= e.year <= hi):
                    return False
            mood = spec.get('mood')
            if mood == 'slow' and e.dance in FAST_DANCES:
                return False
            if mood == 'fast' and e.dance in SLOW_DANCES:
                return False
            if e.popularity < spec.get('min_pop', 0):
                return False
            return True

        pool = [e for e in self.lib.entries if matches(e)]
        if not pool:
            return []

        def score(e: MusicEntry) -> float:
            return e.popularity * 3 + random.random() * 2

        pool.sort(key=score, reverse=True)
        selected = pool[:max(count, 0)]

        # Round-robin de-clustering across dances
        buckets: dict[str, list[MusicEntry]] = defaultdict(list)
        for e in selected:
            buckets[e.dance or '?'].append(e)
        order: list[MusicEntry] = []
        while any(buckets.values()):
            for d in list(buckets.keys()):
                if buckets[d]:
                    order.append(buckets[d].pop(0))
        return order


# ── Playlist Hints ─────────────────────────────────────────────────────────────
def generate_hints(
    lib: MusicLibrary,
    playlist: Playlist | None,
    dances: list[str],
    dance_class: str,
    rounds: list[RoundConfig],
) -> list[str]:
    """Return human-readable warnings/tips about library coverage and a playlist."""
    hints: list[str] = []

    # Proven-pool depth vs what semi/final rounds demand
    final_need = max((rc.heats for rc in rounds if rc.tier in ('semi', 'final')), default=0)
    for d in dances:
        songs  = [e for e in lib.by_dance(d)
                  if not e.is_xmas and not is_non_turnier(e)]
        proven = [e for e in songs if e.popularity > 0]
        if d not in ALLOW_REPEAT and final_need and len(proven) < final_need:
            hints.append(
                i18n.t("⚠ %s: only %d proven song(s) — finals need %d; expect fresh fill-ins.")
                % (dance_name(d, d), len(proven), final_need)
            )
        lo, hi = TEMPO_RANGES.get(d, {}).get(dance_class, (20, 70))
        center = (lo + hi) / 2
        if songs and not any(e.bpm is not None and abs(e.bpm - center) <= 0.5 for e in songs):
            hints.append(
                i18n.t("♪ %s: no track near the ideal %s bpm.")
                % (dance_name(d, d), f"{center:.0f}")
            )

    # Freshness of the generated playlist
    if playlist:
        total = fresh = 0
        for heats in playlist.values():
            for heat in heats:
                for e in heat:
                    if e is not None:
                        total += 1
                        if e.popularity == 0:
                            fresh += 1
        if total:
            hints.append(i18n.t("✦ %d/%d songs are fresh (%d%% new).")
                         % (fresh, total, 100 * fresh // total))

    return hints


def source_gap_hint(playlist: Playlist | None, dances: list[str],
                    source_label: str) -> str:
    """One hint naming the slots a hand-picked source could not fill, or "".

    Only for the wishlist / .m3u sources (`source_label` empty = the whole
    Favorites library, where a blank slot means the library itself ran dry and
    `generate_hints` already says so). Those pools are meant to be small, so a
    blank slot is expected rather than broken — but it has to be said out loud,
    per dance, or the gaps read as a bug.
    """
    if not playlist or not source_label:
        return ""
    blanks = Counter()
    total = 0
    for heats in playlist.values():
        for heat in heats:
            for i, e in enumerate(heat):
                total += 1
                if e is None and i < len(dances):
                    blanks[dances[i]] += 1
    if not blanks:
        return ""
    per_dance = ", ".join(f"{dance_name(d, d)} {n}"
                          for d, n in sorted(blanks.items(), key=lambda kv: -kv[1]))
    return (i18n.t("⚠ %s could not fill %d of %d slots (%s) — park more tracks there "
                   "or switch the source back to the Favorites library.")
            % (source_label, sum(blanks.values()), total, per_dance))
