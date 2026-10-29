"""Playlist assembly: turns a configured library + rounds into a Playlist.

Extracted from dancesport_planner.py (logical split): PlaylistSuggester builds
the per-round/per-heat grid using MusicLibrary, plus generate_hints for the
post-build advisory notes.
"""
import logging
import math
import random
import secrets
from collections import Counter, defaultdict
from typing import Any

from planner import i18n
from planner.generate.scoring import (  # auto-resolved
    BONUS_CLASS_OK,
    BONUS_FRESH,
    BONUS_PROVEN,
    PENALTY_BELOW_TEMPO,
    PENALTY_CLASS_DILUTED,
    PENALTY_CLASS_MISMATCH,
    PROVEN_MIN_POP,
    RANDOM_TIEBREAK,
    W_BPM_FIT,
    W_POPULARITY,
    W_TIMBRE,
    class_dilutes,
    class_popularity,
    effective_popularity,
    prefer_late_rounds,
    resolve_strategy,
)
from planner.generate.warmup import (  # auto-resolved
    class_warmup_pool,
    entry_in_style,
    others_dance_of,
)
from planner.models import (  # auto-resolved
    ALLOW_REPEAT,
    BELOW_TEMPO_EXT,
    FAST_DANCES,
    SLOW_DANCES,
    TEMPO_RANGES,
    MusicEntry,
    Playlist,
    RoundConfig,
    RoundTier,
    Strategy,
    is_non_turnier,
)
from planner.music.db import (  # auto-resolved
    AudioFeatures,
)
from planner.music.library import (  # auto-resolved
    ANCHOR_DEFAULT,
    MusicLibrary,
)
from planner.music.parsing import (  # auto-resolved
    bpm_fit,
)
from planner.music.similarity import (  # auto-resolved
    STRONG_TIMBRE,
    timbre_measured,
    timbre_similarity,
)
from planner.terms import dance_name
from planner.themes import (  # auto-resolved
    all_themes,
    load_user_themes,
)

log = logging.getLogger("dancesport.suggester")


class _SoftUses(set):
    """The Paso Doble soft no-repeat set, also keeping each pick in order."""

    def __init__(self, paths=()):
        super().__init__(paths)
        self.order: list[str] = list(paths)

    def add(self, path):
        super().add(path)
        self.order.append(path)


def _next_cycle(bpm_ok: list[MusicEntry], soft_used) -> list[MusicEntry]:
    """Every in-tempo Paso Doble is used: go round again. The least-used ones,
    never the previous heat's while another is left. Without the pick order
    (a plain set) the whole in-tempo pool is open, as before."""
    order = getattr(soft_used, "order", None)
    if not order or not bpm_ok:
        return bpm_ok
    uses = Counter(order)
    fewest = min(uses[str(e.path)] for e in bpm_ok)
    pool = [e for e in bpm_ok
            if uses[str(e.path)] == fewest and str(e.path) != order[-1]]
    return pool or [e for e in bpm_ok if str(e.path) != order[-1]] or bpm_ok


class PlaylistSuggester:
    def __init__(self, library: MusicLibrary | None, seed: int | None = None):
        # None for a deck restored before the library scan is done, or loaded
        # from an .m3u in a player-only install: it keeps its seed and its
        # similarities, but has nothing to draw from.
        self.lib = library
        # Every draw comes from this one generator, so a generation replays
        # exactly from its seed, and the interpreter's global `random` stays out.
        self.seed = secrets.randbits(32) if seed is None else seed
        self.rng = random.Random(self.seed)
        self._anchors: dict[str, AudioFeatures | None] = {}
        # Each pick's timbre similarity to its round's anchor, for display — kept
        # here per (round, path), not on the library entry every deck shares.
        self._sims: dict[tuple[str | None, str], float | None] = {}

    def _library(self) -> MusicLibrary:
        """The library a draw comes from; a suggester without one cannot draw."""
        if self.lib is None:
            raise RuntimeError("this suggester has no library to draw from")
        return self.lib

    def suggest(
        self,
        dance_class: str,
        rounds: list[RoundConfig],
        dances: list[str],
        use_timbre: bool = True,
        style: str | None = None,
        round_pools: list[list[MusicEntry]] | None = None,
        exclude: set | None = None,
    ) -> Playlist:
        log.info("🎲 Generating a playlist\n"
                 "class: %s\n"
                 "seed: %s", dance_class, self.seed)
        # `exclude` seeds the no-repeat set with paths already used elsewhere
        # (the day planner's cross-competition pool). ALLOW_REPEAT dances (PD)
        # are exempt automatically — their pools never consult `used`.
        used: set = set(exclude or ())   # strict no-repeat (non-ALLOW_REPEAT dances)
        pd_used: set = _SoftUses()   # soft no-repeat for PD – prefer variety, allow reuse
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
        rc: RoundConfig,
        dances: list[str],
        dance_class: str,
        used: set,
        pd_used: set,
        use_timbre: bool = True,
        style: str | None = None,
        candidates: list[MusicEntry] | None = None,
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
                entry, sim = self._pick(dance, dance_class,
                                   rc.tier, used,
                                   anchor if use_timbre else None,
                                   soft,
                                   prefer_fresh=rc.prefer_fresh,
                                   strategy=rc.strategy,
                                   style=style,
                                   candidates=candidates)
                if entry:
                    self.set_similarity(entry, rc.name, sim)
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
        rc: RoundConfig,
        dances: list[str],
        dance_class: str,
        used: set,
        pd_used: set | None = None,
        use_timbre: bool = True,
        style: str | None = None,
        candidates: list[MusicEntry] | None = None,
    ) -> list[list[MusicEntry | None]]:
        """Re-roll a whole round in place (used when a strategy combo changes).

        `used` must already hold the paths picked by the OTHER rounds so the
        re-rolled round does not duplicate them. `candidates` is that round's
        history pool ('past competitions'); empty dances fall back to the full
        library inside `_get_pool`."""
        return self._suggest_round(
            rc, dances, dance_class, used,
            _SoftUses(pd_used or ()),
            use_timbre=use_timbre, style=style, candidates=candidates,
        )

    def _get_pool(self, dance: str, dance_class: str,
                  tier: RoundTier, used: set,
                  soft_used: set | None = None,
                  prefer_fresh: bool = False,
                  strategy: Strategy | str | None = None,
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
        strat = resolve_strategy(tier, prefer_fresh, strategy)
        lo, hi = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))

        all_songs, bpm_ok = self._dance_songs(dance, style, candidates, lo, hi)

        # Hard-exclude songs that carry class tags incompatible with the current class
        # (e.g. a song tagged [D] should never appear in an S-class playlist).
        # Fall back to unfiltered only if every song in the dance is class-restricted.
        class_fit = [e for e in bpm_ok if not e.classes_ok or dance_class in e.classes_ok]
        bpm_ok = class_fit or bpm_ok

        if dance in ALLOW_REPEAT:
            not_soft = [e for e in bpm_ok if str(e.path) not in (soft_used or set())]
            # No in-tempo Paso in this pool (a round's own history may hold
            # only slow ones): replay an in-tempo one the playlist already
            # has. Out of tempo only when nothing in tempo has played yet.
            played = [] if bpm_ok else [
                e for e in self._dance_songs(dance, style, None, lo, hi)[1]
                if str(e.path) in (soft_used or set())]
            base = (not_soft or _next_cycle(bpm_ok, soft_used)
                    or _next_cycle(played, soft_used) or all_songs)
            if strat in (Strategy.PROVEN, Strategy.TOP_PROVEN):
                # In a final or a semifinal, having BEEN in that round comes
                # first — see the long comment on the same step below.
                base = prefer_late_rounds(base, tier)
                pool = [e for e in base if e.popularity >= PROVEN_MIN_POP] or base
                pool = ([e for e in pool
                         if class_popularity(e, dance_class) > 0
                         and effective_popularity(e, dance_class) >= PROVEN_MIN_POP]
                        or [e for e in pool if class_popularity(e, dance_class) > 0]
                        or pool)
            elif strat == Strategy.FRESH:
                fresh = [e for e in base if e.popularity < PROVEN_MIN_POP]
                pool = fresh or base
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
        if strat in (Strategy.PROVEN, Strategy.TOP_PROVEN):
            available = prefer_late_rounds(available, tier)

        proven = [e for e in available if e.popularity >= PROVEN_MIN_POP]
        fresh = [e for e in available if e.popularity < PROVEN_MIN_POP]
        high_pop = [e for e in available if e.popularity >= PROVEN_MIN_POP * 2]
        mid_pop = proven

        if strat == Strategy.TOP_PROVEN:
            pool = high_pop or mid_pop or proven or available
        elif strat == Strategy.PROVEN:
            pool = proven or available
        elif strat == Strategy.FRESH:
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
        if strat in (Strategy.PROVEN, Strategy.TOP_PROVEN):
            pool = ([e for e in pool
                     if class_popularity(e, dance_class) > 0
                     and effective_popularity(e, dance_class) >= PROVEN_MIN_POP]
                    or [e for e in pool if class_popularity(e, dance_class) > 0]
                    or pool)

        return pool

    def _dance_songs(self, dance, style, candidates, lo, hi):
        """The dance's songs in the style (all_songs), and those in tempo (bpm_ok)."""
        if style == 'Others':
            # Social dances: classify by folder/name, no tournament-tempo filter.
            base = candidates if candidates is not None else self._library().entries
            all_songs = [e for e in base
                         if not e.is_xmas and not is_non_turnier(e)
                         and others_dance_of(e) == dance
                         and entry_in_style(e, 'Others')]
            if not all_songs and candidates is not None:
                all_songs = [e for e in self._library().entries
                             if not e.is_xmas and not is_non_turnier(e)
                             and others_dance_of(e) == dance
                             and entry_in_style(e, 'Others')]
            bpm_ok = all_songs
        else:
            if candidates is not None:
                base = [e for e in candidates if e.dance == dance]
                if not base:
                    base = self._library().by_dance(dance)
            else:
                base = self._library().by_dance(dance)
            all_songs = [e for e in base
                         if not e.is_xmas and not is_non_turnier(e)
                         and entry_in_style(e, style)]
            ext = BELOW_TEMPO_EXT.get(dance, 0)
            bpm_ok = [e for e in all_songs if e.bpm is None or (lo - ext) <= e.bpm <= hi]
        return all_songs, bpm_ok

    def _pick(
        self,
        dance: str,
        dance_class: str,
        tier: RoundTier,
        used: set,
        anchor: AudioFeatures | None,
        soft_used: set | None = None,
        prefer_fresh: bool = False,
        strategy: Strategy | str | None = None,
        style: str | None = None,
        candidates: list[MusicEntry] | None = None,
        timbre_first: bool = False,
    ) -> tuple[MusicEntry | None, float | None]:
        """Pick one song, with its timbre similarity to `anchor` (None when
        there is no anchor or the song has no audio features)."""
        lo, hi = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))

        strat = resolve_strategy(tier, prefer_fresh, strategy)
        # Pass the RESOLVED strategy down so _get_pool doesn't re-derive it.
        pool = self._get_pool(dance, dance_class, tier, used, soft_used,
                              prefer_fresh, strat, style, candidates)
        if not pool:
            return None, None

        # Timbre similarity of the whole pool to the round anchor, via the app's
        # default metric (`_timbre_similarity` → Gaussian/KL). Empty when no anchor.
        sims = timbre_similarity(anchor, pool) if anchor else {}

        # Popularity on the pool's own 0..1 scale, logarithmic so the 20th play
        # adds less than the 2nd. A raw play count next to the 0..1 timbre and
        # tempo terms let one extra play outweigh the best possible sound match.
        top_pop = math.log1p(max((effective_popularity(e, dance_class) for e in pool),
                                 default=0.0))

        def score(e: MusicEntry) -> float:
            # 'all' = no proven/fresh preference → popularity must not bias the pick.
            # Popularity is CLASS-WEIGHTED (see effective_popularity): plays in the
            # selected start class count fully, other-class plays barely — so a
            # D-class warhorse can't outrank the genuine S staples in an S round.
            pop = (math.log1p(effective_popularity(e, dance_class)) / top_pop
                   if top_pop else 0.0)
            s = pop * (0 if strat == Strategy.ALL else W_POPULARITY)
            s += bpm_fit(e.bpm, lo, hi) * W_BPM_FIT
            if e.bpm is not None and e.bpm < lo:
                s -= PENALTY_BELOW_TEMPO
            if anchor and e.features:
                s += sims.get(str(e.path), 0.5) * W_TIMBRE
            if strat == Strategy.FRESH and e.popularity < PROVEN_MIN_POP:
                s += BONUS_FRESH
            if strat == Strategy.PROVEN and e.popularity >= PROVEN_MIN_POP:
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
            s += self.rng.random() * RANDOM_TIEBREAK   # spread comes from weighting
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
            # A song without audio features has no similarity: it ranks below
            # every measured one instead of passing for an average match. The
            # metric gives it a neutral 0.5, so it leaves `sims` first.
            sims = {str(e.path): sims[str(e.path)] for e in pool
                    if timbre_measured(e)}

            def sim_of(e: MusicEntry) -> float:
                return sims.get(str(e.path), float("-inf"))

            by_timbre = sorted(pool, key=sim_of, reverse=True)
            n = max(1, min(10, len(by_timbre)))
            cutoff = sim_of(by_timbre[n - 1])              # similarity of the 10th
            threshold = min(cutoff, STRONG_TIMBRE)        # ≥ top-10 floor, and ≥ 0.80
            shortlist = [e for e in by_timbre
                         if str(e.path) in sims and sim_of(e) >= threshold] \
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
                if strat == Strategy.ALL:
                    return 1.0
                if strat == Strategy.FRESH:
                    return 2.0 if e.popularity < PROVEN_MIN_POP else 0.4
                if strat == Strategy.MIXED:
                    return 1.0 + min(ep, 3) * 0.4
                return ep + 1.0

            # +0.01 floor so a near-zero similarity (cosine ≈ -1) still yields a positive
            # weight — random.choices() raises if every weight sums to zero.
            weights = [_pop_weight(e) * (sims.get(str(e.path), 0.0) ** 2 + 0.01)
                       for e in shortlist]
            chosen = self.rng.choices(shortlist, weights=weights, k=1)[0]
            return chosen, sims.get(str(chosen.path))

        # ── Generation / whole-round: composite score, weighted pick ──
        # Better score → higher chance, but not deterministic; weight = how far each
        # candidate sits above the weakest of the shortlist (+ a floor so it keeps a chance).
        scored = sorted(((score(e), e) for e in pool), key=lambda x: x[0], reverse=True)
        top = scored[:max(1, min(10, len(scored)))]
        base = top[-1][0]
        weights = [(s - base) + 0.1 for s, _ in top]
        chosen = self.rng.choices([e for _, e in top], weights=weights, k=1)[0]
        return chosen, sims.get(str(chosen.path))

    def regenerate(
        self,
        dance: str,
        dance_class: str,
        tier: RoundTier,
        exclude: set,
        prefer_fresh: bool = False,
        round_name: str | None = None,
        use_timbre: bool = True,
        strategy: Strategy | str | None = None,
        style: str | None = None,
        candidates: list[MusicEntry] | None = None,
        anchor: Any = ANCHOR_DEFAULT,
    ) -> MusicEntry | None:
        # `anchor` lets the caller override the round's stored reference — e.g. when
        # re-rolling the anchor song ITSELF, the GUI passes the next song's features so
        # the replacement matches the rest of the round instead of the song being removed.
        if anchor is ANCHOR_DEFAULT:
            anchor = self._anchors.get(round_name) if round_name else None
        if not use_timbre:
            anchor = None
        # PD's pool never consults `used`, only the soft set — so hand it the
        # planned songs there: a re-roll prefers a PD the list doesn't have yet
        # and still repeats one when the library has no other.
        soft = exclude if dance in ALLOW_REPEAT else None
        chosen, sim = self._pick(dance, dance_class, tier, exclude, anchor=anchor,
                                 soft_used=soft,
                                 prefer_fresh=prefer_fresh, strategy=strategy,
                                 style=style, candidates=candidates, timbre_first=True)
        if chosen is not None:
            self.set_similarity(chosen, round_name, sim)
        return chosen

    def similarity(self, entry: MusicEntry, round_name: str | None) -> float | None:
        """The timbre similarity shown for `entry` in `round_name` (≈ / hover-%),
        as last picked or placed there; None when nothing was measured."""
        return self._sims.get((round_name, str(entry.path)))

    def set_similarity(self, entry: MusicEntry, round_name: str | None,
                       score: float | None) -> None:
        """Record the similarity of a song picked or placed in `round_name`."""
        self._sims[(round_name, str(entry.path))] = score

    def anchor_similarity(self, entry: MusicEntry,
                          round_name: str | None,
                          anchor: Any = ANCHOR_DEFAULT) -> float | None:
        """Timbral similarity (0..1) of `entry` to a round's anchor, for display.

        Used when a song is placed manually (e.g. dropped from the Similar-Tracks
        window) so its ≈ / hover-% matches how the auto-picker would have scored it.
        Pass `anchor` to override the round's stored reference (same fallback as
        `regenerate` when the anchor song itself is the one being replaced). Returns
        None when there is no anchor or the track has no audio features."""
        if anchor is ANCHOR_DEFAULT:
            anchor = self._anchors.get(round_name) if round_name else None
        if anchor is None or entry.features is None:
            return None
        return timbre_similarity(anchor, [entry]).get(str(entry.path))

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
            pool = [e for e in class_warmup_pool(self._library().entries, st, dance,
                                                 dance_class, relax=relax)
                    if str(e.path) not in exclude]
            if pool:
                break
        if not pool:
            return None
        sims = {}
        anchor = getattr(anchor_entry, "features", None)
        if anchor is not None:
            sims = timbre_similarity(anchor, pool)

        def score(e: MusicEntry) -> float:
            sim = sims.get(str(e.path), 0.0)
            pop = min(effective_popularity(e, dance_class), 10.0)
            return sim * 5.0 + pop * 0.3 + self.rng.random() * 0.5
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
            return e.popularity >= spec.get('min_pop', 0)

        pool = [e for e in self._library().entries if matches(e)]
        if not pool:
            return []

        def score(e: MusicEntry) -> float:
            return e.popularity * 3 + self.rng.random() * 2

        pool.sort(key=score, reverse=True)
        selected = pool[:max(count, 0)]

        # Round-robin de-clustering across dances
        buckets: dict[str, list[MusicEntry]] = defaultdict(list)
        for e in selected:
            buckets[e.dance or '?'].append(e)
        order: list[MusicEntry] = []
        while any(buckets.values()):
            order.extend(buckets[d].pop(0) for d in list(buckets) if buckets[d])
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
    final_need = max((rc.heats for rc in rounds
                      if rc.tier in (RoundTier.SEMI, RoundTier.FINAL)), default=0)
    for d in dances:
        songs = [e for e in lib.by_dance(d)
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
    blanks: Counter[str] = Counter()
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
