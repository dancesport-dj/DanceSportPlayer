"""Pure playlist-check logic (no Qt): duplicate detection across dropped
playlists and the Check-Music per-track / round-structure rules.

Extracted from gui/main_import.py so the rules are testable without PySide6;
the ImportMixin methods are thin wrappers that fill in the GUI-side context
(settings thresholds, silence cache, beats-per-bar table).
"""

from planner import i18n
from planner.models import ALLOW_REPEAT, TEMPO_RANGES
from planner.terms import dance_name


# ── ≈ Similar-song matching: Levenshtein on the cleaned title ──────────────────
# The old TurnierCheck matched "similar" songs by an edit distance on names. We run
# it on the CLEANED title (track number / dance code / BPM already stripped by
# planner.parsing._song_title_key) so typo-level variants of one song group together while
# the shared "(Instr.) (TG 32)" scaffolding that made the old tool noisy is gone.
SIMILAR_RATIO = 0.85


def levenshtein(a: str, b: str, max_dist: int | None = None) -> int:
    """Edit distance. With max_dist set it's a cutoff search: as soon as the best
    possible distance exceeds max_dist it bails out with max_dist + 1, which makes the
    all-pairs title clustering fast (most title pairs are wildly different)."""
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    if max_dist is not None and abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            v = min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb))
            cur.append(v)
            if v < row_min:
                row_min = v
        if max_dist is not None and row_min > max_dist:
            return max_dist + 1
        prev = cur
    return prev[-1]


def title_ratio(a: str, b: str) -> float:
    """1.0 = identical, 0.0 = nothing alike — normalised Levenshtein similarity."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    longest = max(len(a), len(b))
    allowed = int((1.0 - SIMILAR_RATIO) * longest)   # max edits that still pass
    d = levenshtein(a, b, allowed)
    return 0.0 if d > allowed else 1.0 - d / longest


# Words that don't tell one song from another — dropped before the containment
# test so a subtitle, an '(Instr.)' marker or a 'DJ …' prefix doesn't stop two
# encodings of the SAME song from matching ('Enjoy The Silence' ≡ 'Enjoy The
# Silence (Instr.)', 'Love Yourself' ≡ 'DJ Ice … Love Yourself').
TITLE_STOPWORDS = frozenset({
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "my", "me",
    "you", "your", "is", "im", "instr", "instrumental", "orig", "original",
    "version", "vers", "remix", "edit", "mix", "feat", "ft", "dj", "radio",
    "extended", "club", "from", "live",
})


def sig_tokens(key: str) -> frozenset:
    """The meaningful words of a cleaned title key (stopwords / tags removed)."""
    return frozenset(key.split()) - TITLE_STOPWORDS


def title_similar(a: str, b: str) -> bool:
    """True when two cleaned titles name the SAME song: either their Levenshtein
    similarity clears the threshold (typo-level variants) or one's significant-word
    set is wholly contained in the other's — a subtitle / '(Instr.)' / DJ prefix made
    one title longer ('butterfly waltz' ⊂ 'butterfly waltz from twilight'). Needs ≥2
    shared significant words so single-word titles ('Higher' vs 'Riche') don't collide."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = sig_tokens(a), sig_tokens(b)
    if ta and tb and (ta <= tb or tb <= ta) and min(len(ta), len(tb)) >= 2:
        return True
    return title_ratio(a, b) >= SIMILAR_RATIO


def _similar_candidates(titles: list) -> set:
    """Every pair of distinct titles `title_similar` could accept, and few others.

    Testing all pairs is quadratic — six seconds for 1,500 titles, on the GUI
    thread. Both of its tests have a necessary condition an index can answer:

    - containment: every significant word of the smaller set is in the larger,
      so the larger is in the posting of each of those words;
    - Levenshtein: a pair within k edits, the shorter title cut into k + 1
      pieces, keeps at least one piece whole inside the longer (one edit breaks
      at most one piece), so the longer is in the posting of that piece's
      rarest trigram.
    """
    pairs = set()

    def add(a, b):
        pairs.add((a, b) if a < b else (b, a))

    by_word: dict = {}
    sig = {t: sig_tokens(t) for t in titles}
    for t, words in sig.items():
        for w in words:
            by_word.setdefault(w, set()).add(t)
    for t, words in sig.items():
        if len(words) >= 2:
            postings = sorted((by_word[w] for w in words), key=len)
            for other in postings[0].intersection(*postings[1:]):
                if other != t:
                    add(t, other)

    by_trigram: dict = {}
    for t in titles:
        for i in range(len(t) - 2):
            by_trigram.setdefault(t[i:i + 3], set()).add(t)
    by_length: dict = {}
    for t in titles:
        by_length.setdefault(len(t), []).append(t)
    for a in titles:
        la = longest = len(a)
        # The longest partner a can still be close to — `title_ratio` allows
        # int(0.15 × the longer length) edits, and a length gap costs one each.
        while longest + 1 - la <= int((1.0 - SIMILAR_RATIO) * (longest + 1)):
            longest += 1
        k = int((1.0 - SIMILAR_RATIO) * longest)
        if k == 0:
            continue                  # only an identical title, and they are distinct
        cuts = [la * i // (k + 1) for i in range(k + 2)]
        pieces = [a[cuts[i]:cuts[i + 1]] for i in range(k + 1)]
        if min(map(len, pieces)) < 3:
            # Too short to index: every title in the length window is a candidate.
            for lb in range(la, longest + 1):
                for b in by_length.get(lb, ()):
                    if b != a:
                        add(a, b)
            continue
        for piece in pieces:
            rarest = min((piece[i:i + 3] for i in range(len(piece) - 2)),
                         key=lambda g: len(by_trigram[g]))
            for b in by_trigram[rarest]:
                if b != a and la <= len(b) <= longest and piece in b:
                    add(a, b)
    return pairs


def title_cluster_map(tkeys) -> dict:
    """Map each distinct cleaned title to a canonical cluster key, union-ing titles that
    name the same song (Levenshtein-similar OR significant-word containment, see
    `title_similar`). The canonical key is the lexicographically smallest in the group."""
    titles = sorted(t for t in set(tkeys) if t)
    parent = {t: t for t in titles}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ti, tj in _similar_candidates(titles):
        if title_similar(ti, tj):
            ri, rj = find(ti), find(tj)
            if ri != rj:
                parent[max(ri, rj)] = min(ri, rj)
    return {t: find(t) for t in titles}


def similar_reps(recs: list, cluster_map: dict) -> dict:
    """cluster key → {exact-key → first rec}: one representative file per cleaned-title
    cluster, so byte-identical copies collapse but distinct recordings stay separate.
    A record carries several candidate title keys (full title + 'Artist - Title' parts)
    and is registered under each distinct cluster it touches, so a match on ANY of them
    surfaces the pair."""
    out: dict[str, dict] = {}
    for r in recs:
        seen = set()
        for k in r.get("tkeys") or ():
            c = cluster_map.get(k)
            if c is None or c in seen:
                continue
            seen.add(c)
            out.setdefault(c, {}).setdefault(r["exact"], r)
    return out


def dance_compatible(r1: dict, r2: dict) -> bool:
    """Two similar-title tracks are the same song only when their dances match — a Slow
    Waltz 'Beautiful' and a Jive 'Beautiful' are false friends. An unknown dance on
    either side is permissive (shown), so a possible duplicate is never hidden."""
    d1, d2 = r1.get("dance"), r2.get("dance")
    return not d1 or not d2 or d1 == d2


def dance_split(reps: list) -> list:
    """Split one title cluster's representative tracks into groups that never mix two
    DETERMINABLE dances. Same (or only one) known dance → kept together; two+ known
    dances → one group per dance, with unknown-dance tracks shown alongside each (so
    they surface for the user instead of being silently dropped)."""
    knowns = sorted({r["dance"] for r in reps if r.get("dance")})
    if len(knowns) <= 1:
        return [reps]
    unknown = [r for r in reps if not r.get("dance")]
    return [[r for r in reps if r.get("dance") == d] + unknown for d in knowns]


def dup_clashes(candidates: list, taken: list) -> set:
    """Indices of the `candidates` records the duplicate check would flag against
    the `taken` ones: the same file, or the same song by title (clustered as
    `pair_dups` does) in a dance that does not rule it out. For a replacement
    picker, so a picked track is not itself reported on the next check."""
    exacts = {r["exact"] for r in taken if r.get("exact")}
    cmap = title_cluster_map([k for r in candidates + taken for k in (r.get("tkeys") or ())])
    dances: dict[str, list] = {}           # cluster → the taken records' dances
    for r in taken:
        for k in r.get("tkeys") or ():
            dances.setdefault(cmap[k], []).append(r)
    out = set()
    for i, r in enumerate(candidates):
        if r.get("exact") in exacts or any(
                dance_compatible(r, t)
                for k in (r.get("tkeys") or ()) for t in dances.get(cmap[k], ())):
            out.add(i)
    return out


def pair_dups(recs_a: list, recs_b: list) -> tuple:
    """Songs shared between two playlists' track records. Returns (exact, similar):
    exact = same file (content fingerprint / path); similar = same song in a different
    recording (cleaned titles within the Levenshtein threshold but different files —
    fingerprints can't catch those). One representative pair per song, by line number."""
    ex_a, ex_b = {}, {}
    for r in recs_a:
        ex_a.setdefault(r["exact"], r)
    for r in recs_b:
        ex_b.setdefault(r["exact"], r)
    exact = [{"a": ex_a[k], "b": ex_b[k]} for k in (set(ex_a) & set(ex_b))]

    cmap = title_cluster_map([k for r in recs_a for k in (r.get("tkeys") or ())]
                             + [k for r in recs_b for k in (r.get("tkeys") or ())])
    ca, cb = similar_reps(recs_a, cmap), similar_reps(recs_b, cmap)
    similar = []
    for c in (set(ca) & set(cb)):
        a_ex, b_ex = ca[c], cb[c]
        # A real "similar" needs one track from each side that are DIFFERENT files;
        # if every shared-title track is the same file it's already an exact match.
        pair = next(((ra, rb) for ea, ra in a_ex.items()
                              for eb, rb in b_ex.items()
                              if ea != eb and dance_compatible(ra, rb)), None)
        if pair:
            similar.append({"a": pair[0], "b": pair[1]})

    exact.sort(key=lambda p: p["a"]["idx"])
    similar.sort(key=lambda p: p["a"]["idx"])
    return exact, similar


def build_dropped_dup_report(files: list) -> dict:
    """Turn [(name, [rec,…]), …] into the tab-2 report. Each rec carries idx / title /
    path / exact (file identity) / tkeys (cleaned-title candidates). 'within' lists songs doubled
    inside one playlist; 'cross' lists songs shared between each pair of playlists."""
    within = []
    for name, recs in files:
        clusters = []
        by_exact: dict[str, list] = {}
        for r in recs:
            by_exact.setdefault(r["exact"], []).append(r)
        for group in by_exact.values():
            if len(group) >= 2:
                clusters.append({"kind": "exact", "members": group})
        cmap = title_cluster_map([k for r in recs for k in (r.get("tkeys") or ())])
        for reps in similar_reps(recs, cmap).values():
            for group in dance_split(list(reps.values())):
                if len(group) >= 2:          # same song + dance, ≥2 different files
                    # PD repeats inside one list are the norm (rounds re-use the
                    # same pasos) — only byte-identical copies are worth a warning
                    # there, different recordings of one paso are fine.
                    dances = {r["dance"] for r in group if r.get("dance")}
                    if dances and dances <= ALLOW_REPEAT:
                        continue
                    members = sorted(group, key=lambda r: r["idx"])
                    clusters.append({"kind": "similar", "members": members})
        if clusters:
            clusters.sort(key=lambda c: c["members"][0]["idx"])
            within.append({"file": name, "clusters": clusters})

    cross = []
    # PD may legitimately be shared between lists (repeats across rounds are the
    # norm) — only compare it within its OWN list, never between two lists.
    def _crossable(recs: list) -> list:
        return [r for r in recs if (r.get("dance") or "") not in ALLOW_REPEAT]
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            exact, similar = pair_dups(_crossable(files[i][1]),
                                       _crossable(files[j][1]))
            if exact or similar:
                cross.append({"file_a": files[i][0], "file_b": files[j][0],
                              "exact": exact, "similar": similar})
    return {"within": within, "cross": cross}


# ── 🎵 Check-Music rules (per track + round structure) ──────────────────────────
def entry_takt(e, beats_per_bar: dict) -> int:
    """A track's takt (bars/min): the filename label, else the measured
    tempo ÷ the dance's meter. 0 when neither is known."""
    takt = int(getattr(e, "bpm", 0) or 0)
    if takt:
        return takt
    bpb = beats_per_bar.get(e.dance or "")
    measured = float(getattr(e.features, "bpm", 0) or 0) if e.features else 0.0
    return round(measured / bpb) if (measured > 0 and bpb) else 0


# A round is the final when its config says so, or when it is called one —
# an imported .m3u carries a name ("Finale", "Final") but no tier. A semifinal
# is called one too, in both languages, and is NOT the final.
_FINAL_NAMES = ("final", "endrunde")
_NOT_THE_FINAL = ("halb", "semi", "viertel", "achtel", "zwischen")


def is_final_round(round_name: str = "", tier: str = "") -> bool:
    """Is this slot in the final? Used by the checks that only bite there."""
    if (tier or "").strip().lower() == "final":
        return True
    name = (round_name or "").strip().lower()
    if any(word in name for word in _NOT_THE_FINAL):
        return False
    return any(word in name for word in _FINAL_NAMES)


# How much stillness the 🔇 skip acts on, and how close to an edge a span has to
# reach to count as the head or the tail of the track. Mirrors the playing side
# (player.main_audio._maybe_skip_silence): a span is only skipped when it is at
# least _SKIP_MIN long, a tail is anything that runs to within _TAIL_GAP of the
# end, and a head is anything starting in the first _HEAD_GAP.
_SKIP_MIN = 2.0
_TAIL_GAP = 1.5
_HEAD_GAP = 0.5

# How much stillness at ONE end earns the red ⏱ cell. The player skips anything
# over _SKIP_MIN, but two or three seconds of room tone before the first note is
# ordinary mastering — flagging that would paint half the library red and the
# flag would stop meaning anything. Red is for a track that will visibly not
# play as long as it says.
FLAG_EDGE_SILENCE = 5.0


def edge_silence_secs(duration, spans, *,
                      min_span: float = _SKIP_MIN) -> tuple[float, float]:
    """(head, tail) seconds of stillness the 🔇 skip takes off the two ends.

    Stillness in the MIDDLE belongs to neither end — it is played as recorded,
    because it may be a break the dancers know. Empty or None spans (the track
    was never probed) give (0.0, 0.0)."""
    dur = float(duration or 0)
    if dur <= 0 or not spans:
        return 0.0, 0.0
    head = tail = 0.0
    for start, end in spans:
        start = max(0.0, float(start))
        end = min(dur, float(end))
        if end - start < min_span:
            continue
        if end >= dur - _TAIL_GAP:
            tail = max(tail, dur - start)
        elif start <= _HEAD_GAP:
            head = max(head, end - start)
    return head, tail


def audible_track_secs(duration, spans, *, min_span: float = _SKIP_MIN) -> float:
    """Seconds of a track the floor actually hears.

    The player jumps a silent intro and ends the song when only dead air is
    left, so a file with a minute of padding behind the last note plays a
    minute shorter than its tag says. Stillness in the MIDDLE is played as
    recorded — it may be a break the dancers know — so it stays in the count.

    `spans` are the [[start, end], …] seconds of the ffmpeg silence probe;
    empty or None (never probed) gives the full length back."""
    dur = float(duration or 0)
    if dur <= 0:
        return max(0.0, dur)
    head, tail = edge_silence_secs(dur, spans, min_span=min_span)
    return max(0.0, dur - head - tail)


def trailing_silence_secs(duration, spans, *,
                          min_span: float = _SKIP_MIN) -> float | None:
    """Second the dead air behind the last note begins, or None.

    That is where the 🔇 skip ends the song, so it is also where the player's
    countdown has to end — the seconds after it are never danced. Only a span
    that reaches the end of the file counts; stillness in the middle is played
    as recorded, and a silent intro is skipped, not stopped on."""
    dur = float(duration or 0)
    if dur <= 0 or not spans:
        return None
    for start, end in spans:
        start = max(0.0, float(start))
        end = min(dur, float(end))
        if end - start >= min_span and end >= dur - _TAIL_GAP:
            return start
    return None


def track_issues(e, *, beats_per_bar: dict, tempo_ratios, tempo_pct: float,
                 min_secs: int, max_secs: int, silence_secs: float = 0.0,
                 check_long: bool = False, noise_db: float | None = None,
                 noise_max_db: float = -50.0,
                 in_final: bool = False) -> list[str]:
    """Collect every tournament problem for one track as a list of short
    strings: tempo mismatch (measured vs label), TSO takt out of range,
    too-short / too-long play length, and background hiss. Empty list → the
    track is fine.
    `silence_secs` is the stillness inside the file (probed by the caller) —
    not play time, so it's subtracted before the length is judged.
    `noise_db` is the measured noise floor (also probed by the caller); None
    means the hiss check is off or the track was never probed.
    `in_final` says the track is planned in a final — the only round where a
    short Paso Doble is a problem (see below). Unknown placement counts as
    not-in-a-final."""
    issues: list[str] = []
    bpb = beats_per_bar.get(e.dance or "")
    measured = float(getattr(e.features, "bpm", 0) or 0) if e.features else 0.0
    label_takt = int(e.bpm) if getattr(e, "bpm", 0) else 0

    # 1) Tempo sanity — does the measured tempo back up the filename label?
    #    Both in beats/min; detector octave/meter slips (×2, ×3 …) excused.
    if label_takt and bpb and measured > 0:
        expected = label_takt * bpb
        dev = min(abs(measured * r - expected) / expected
                  for r in tempo_ratios)
        if dev > tempo_pct / 100.0:
            issues.append(i18n.t("⚡ Tempo: measured ~%s vs label %s bpm (off %s%%)")
                          % (f"{measured:.0f}", f"{expected:.0f}", f"{dev * 100:.0f}"))

    # 2) TSO range — is the takt inside the official per-dance window? Prefer
    #    the filename label; fall back to the measured tempo ÷ meter.
    rng = TEMPO_RANGES.get(e.dance or "", {}).get("S")
    takt = label_takt or (round(measured / bpb) if (measured > 0 and bpb) else 0)
    if rng and takt:
        lo, hi = rng
        src = i18n.t("label") if label_takt else i18n.t("measured")
        if takt < lo:
            issues.append(i18n.t("🐢 Too slow: T%s (%s), TSO %s-%s") % (takt, src, lo, hi))
        elif takt > hi:
            issues.append(i18n.t("🐇 Too fast: T%s (%s), TSO %s-%s") % (takt, src, lo, hi))

    # 3) Play length — too short to cover a full heat, or so long it drags.
    #    Stillness inside the file (fade-out padding, hidden-track gaps) is
    #    not play time — subtract it so the REAL play length is judged.
    dur = int(getattr(e, "duration", 0) or 0)
    sil = silence_secs if dur > 0 else 0.0
    eff = int(dur - sil)
    mn = min_secs
    mx = max_secs
    # A Paso Doble is played to the first highlight in the early rounds, so a
    # short one is normal there — only a final needs the whole España cañí.
    check_short = not ((e.dance or "") == "PD" and not in_final)
    if check_short and 0 < eff <= mn:
        if sil >= 1.0:
            issues.append(i18n.t("⏱ Short: real play %s — %s file minus %ss silence (≤ %s)")
                          % (f"{eff // 60}:{eff % 60:02d}", f"{dur // 60}:{dur % 60:02d}",
                             f"{sil:.0f}", f"{mn // 60}:{mn % 60:02d}"))
        else:
            issues.append(i18n.t("⏱ Short: %s (≤ %s play length)")
                          % (f"{dur // 60}:{dur % 60:02d}", f"{mn // 60}:{mn % 60:02d}"))
    elif eff > mx and check_long:
        # Long tracks only matter when building an Eintanzen (warm-up) list —
        # opt-in via the report's ⏳ checkbox, off by default.
        issues.append(i18n.t("⏳ Long: %s (> %s)")
                      % (f"{dur // 60}:{dur % 60:02d}", f"{mx // 60}:{mx % 60:02d}"))

    # 4) Background hiss — how quiet does the track ever get? A clean digital
    #    file reaches its lead-in silence; a tape or vinyl rip never gets below
    #    its own hiss, and in a quiet hall that hiss is audible between the
    #    heats. Opt-in (the caller measures only when asked).
    if noise_db is not None and noise_db > noise_max_db:
        issues.append(i18n.t("🔇 Hiss: never quieter than %s dB (> %s dB)")
                      % (f"{noise_db:.0f}", f"{noise_max_db:.0f}"))
    return issues


def grid_structure_issues(pl: dict, dances: list[str],
                          beats_per_bar: dict) -> list[str]:
    """Round-structure warnings for a grid, as plain strings."""
    return ["".join(t for t, _ in f)
            for f in grid_structure_findings(pl, dances, beats_per_bar)]


def grid_structure_findings(pl: dict, dances: list[str],
                            beats_per_bar: dict) -> list:
    """Round-structure sanity for a rounds→heats grid (mirrors the Java
    checkIfAllDancesForClassAreInRounds): within a round every dance should fill
    the same number of slots, the heat count should taper to a 2-heat
    semifinal and a 1-heat final, and the heats of a round should dance each
    dance at (nearly) the same takt. Empty list → the structure looks sound.

    Each warning is a list of (text, target) segments; target is None for
    plain text or a (round_name, h_idx, d_idx) grid slot, so the report can
    render that segment as a jump link into the deck."""
    warns: list = []
    rounds = list(pl.items())   # dict preserves the round order

    # A) Per-round dance balance — each dance should be filled in every heat.
    for rname, heats in rounds:
        if not heats:
            continue
        counts = {}
        missing = {}   # dance → heat numbers without a track (to find the gap)
        for d_idx, dance in enumerate(dances):
            filled = [d_idx < len(h) and h[d_idx] is not None for h in heats]
            counts[dance] = sum(filled)
            missing[dance] = [n for n, ok in enumerate(filled, start=1) if not ok]
        if not counts or len(set(counts.values())) == 1:
            continue   # all dances even → fine
        top = max(counts.values())
        segs = [(i18n.t("“%s”: uneven dance counts — ") % rname, None)]
        any_short = False
        for d_idx, dance in enumerate(dances):
            if counts[dance] >= top:
                continue
            if any_short:
                segs.append(("; ", None))
            any_short = True
            segs.append((i18n.t("%s %d/%d (missing in heat ")
                         % (dance_name(dance, dance), counts[dance], top), None))
            for i, n in enumerate(missing[dance]):
                if i:
                    segs.append((", ", None))
                segs.append((str(n), (rname, n - 1, d_idx)))
            segs.append((")", None))
        if any_short:
            warns.append(segs)

    # B) Final / semifinal taper — only meaningful with a multi-round field.
    if len(rounds) >= 2:
        final_name, final_heats = rounds[-1]
        if len(final_heats) != 1:
            warns.append([(i18n.t("Final "), None),
                          (i18n.t("“%s”") % final_name, (final_name, 0, 0)),
                          (i18n.t(" has %d heats, expected 1.") % len(final_heats), None)])
        semi_name, semi_heats = rounds[-2]
        if len(semi_heats) != 2:
            warns.append([(i18n.t("Semifinal "), None),
                          (i18n.t("“%s”") % semi_name, (semi_name, 0, 0)),
                          (i18n.t(" has %d heats, expected 2.") % len(semi_heats), None)])

    # C) Heat tempo evenness — the heats of a round dance the same dance to
    #    different titles, so their takte should differ by at most 1: a WW
    #    round split over T58 / T59 / T60 heats is unfair to the T60 heat.
    for rname, heats in rounds:
        if len(heats) < 2:
            continue
        for d_idx, dance in enumerate(dances):
            takte = []   # (takt, heat number, title) — so the warning can name them
            for h_no, h in enumerate(heats, start=1):
                e = h[d_idx] if d_idx < len(h) else None
                if e is not None:
                    takt = entry_takt(e, beats_per_bar)
                    if takt:
                        takte.append((takt, h_no, e.title))
            vals = [t for t, _, _ in takte]
            if len(vals) >= 2 and max(vals) - min(vals) > 1:
                segs = [(i18n.t("“%s”: %s heats differ by %d takte (allowed: 1) — ")
                         % (rname, dance_name(dance, dance), max(vals) - min(vals)), None)]
                for i, (t, n, title) in enumerate(takte):
                    if i:
                        segs.append((", ", None))
                    segs.append((i18n.t("heat %d: T%s “%s”") % (n, t, title),
                                 (rname, n - 1, d_idx)))
                warns.append(segs)
    return warns
