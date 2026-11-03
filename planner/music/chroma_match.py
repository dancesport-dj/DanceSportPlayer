"""Telling the same recording apart from another song by its Chromaprint.

A Chromaprint is a list of 32-bit words, about eight per second of audio, built
from the pitch-class (chroma) content of the sound. Two files of one recording
give nearly the same words even when they were encoded differently, at another
bitrate or cut short, so the bit difference between them is small where an
unrelated song differs in about half the bits.

Pure numpy, no fpcalc and no Qt: the fingerprints come from
`shared.audio.chromaprint`, are kept by `AudioCache` and are compared here.

Calibrated 2026-11-03 on 30 real library MP3s (fpcalc 1.6.2, first 120 s): 32
variants (96 kbit/s, 64 kbit/s at 22 kHz, -6 dB, cut 7 s off the start) scored
0.92 to 0.99 against their original and all 32 came out of `find_pairs`; 435
unrelated pairs scored 0.52 on average and 0.58 at most. MATCH_SCORE sits in
that gap. On 400 random library tracks `find_pairs` took 0.2 s and flagged 4
pairs, all real (scores 1.00, 0.93, 0.89, 0.77: same song, different files);
19,900 unrelated pairs scored 0.52 on average, 0.597 at the 99.9th percentile
and 0.658 at most, so the margin to MATCH_SCORE is thin at library scale and
the weakest real pair (0.77) is not far above it.

Full library, 3,688 C: MP3s, 2026-11-03: fingerprinting took 116 s on 8 threads
and `find_pairs` 1.9 s. At a 0.60 floor there were 532 pairs. Judged by file
name, the 0.60 to 0.70 band is almost all the same song (pitch-shifted or cut
copies, other labels' releases of it), so 0.70 trades those away on purpose: a
pitched copy is a different tempo, not a duplicate. The only clear false
positives were two pairs at 0.72 with a shift of 145 and 158 words, the edge of
the search; hence EDGE_SHIFT / EDGE_SCORE. Vocal and instrumental versions of
one backing track score 0.74 to 0.80 and count as the same recording.
"""
import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("dancesport.chroma")

# About eight words per second of audio.
MIN_ITEMS = 40        # ≈ 5 s: shorter than this is too little to judge
MIN_OVERLAP = 120     # ≈ 15 s that must line up (or the whole shorter one)
MAX_SHIFT = 160       # ≈ 20 s: how far one copy may start after the other
MATCH_SCORE = 0.70    # 1 − the share of differing bits, over the overlap
# Beyond this shift (≈ 12 s) the best of 321 alignments is likelier chance, so
# the score must be higher.
EDGE_SHIFT = 100
EDGE_SCORE = 0.80
# `find_pairs` shortlist: two files are compared in full only when they share
# this many identical words, and a word found in more than MAX_BUCKET files
# (silence, a common lead-in) is no evidence of anything.
MIN_SHARED = 4
MAX_BUCKET = 40


@dataclass(frozen=True)
class Chroma:
    duration: float        # seconds, as fpcalc reports the file
    words: np.ndarray      # uint32 sub-fingerprints, about 8 per second


@dataclass(frozen=True)
class Match:
    score: float      # 1.0 = identical, about 0.5 = unrelated
    shift: int        # a[i + shift] lines up with b[i], in words (≈ 1/8 s)
    overlap: int      # words that line up
    coverage: float   # overlap as a share of the shorter fingerprint


def pack(fp: np.ndarray) -> bytes:
    """The fingerprint as the blob the cache stores."""
    return np.asarray(fp, dtype="<u4").tobytes()


def unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<u4").astype(np.uint32)


def parse_raw(text: str) -> np.ndarray:
    """The words of fpcalc's `-raw` output. They may be printed as negative
    integers, so each is taken modulo 2**32."""
    words = [int(w) & 0xFFFFFFFF for w in text.split(",") if w.strip()]
    return np.array(words, dtype=np.uint32)


def compare(a: np.ndarray, b: np.ndarray) -> Match | None:
    """The best alignment of two fingerprints within ±MAX_SHIFT words, or None
    when either is too short to judge or no alignment has enough overlap."""
    shorter = min(len(a), len(b))
    if shorter < MIN_ITEMS:
        return None
    need = min(MIN_OVERLAP, shorter)
    best: Match | None = None
    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        x, y = (a[shift:], b) if shift >= 0 else (a, b[-shift:])
        n = min(len(x), len(y))
        if n < need:
            continue
        bits = int(np.bitwise_count(x[:n] ^ y[:n]).sum())
        score = 1.0 - bits / (32.0 * n)
        if best is None or score > best.score or (
                score == best.score and abs(shift) < abs(best.shift)):
            best = Match(score, shift, n, n / shorter)
    return best


def is_same(match: Match | None) -> bool:
    """True when `compare` found one recording, not just two similar songs."""
    if match is None:
        return False
    need = EDGE_SCORE if abs(match.shift) > EDGE_SHIFT else MATCH_SCORE
    return match.score >= need


def find_pairs(tracks: dict, should_cancel: Callable[[], bool] | None = None
               ) -> list[tuple]:
    """Every pair of `tracks` ({key: fingerprint}) that is one recording, as
    `(key_a, key_b, Match)`, best first.

    Comparing every pair is too slow for a library, so a pair is only compared
    when the two share MIN_SHARED identical 32-bit words: a recording passed
    through another encode keeps a fair share of them, while an unrelated pair
    has essentially none. The price is recall — a copy so different that it
    keeps no identical words is not found."""
    if should_cancel is not None and should_cancel():
        return []
    keys = list(tracks)
    if len(keys) < 2:
        return []
    uniq = [np.unique(np.asarray(tracks[k], dtype=np.uint32)) for k in keys]
    vals = np.concatenate(uniq)
    owner = np.concatenate([np.full(len(u), i, dtype=np.int32)
                            for i, u in enumerate(uniq)])
    order = np.argsort(vals, kind="stable")
    vals, owner = vals[order], owner[order]
    edges = np.flatnonzero(np.diff(vals)) + 1
    starts = np.concatenate(([0], edges))
    ends = np.concatenate((edges, [len(vals)]))
    sizes = ends - starts
    shared: Counter = Counter()
    usable = (sizes >= 2) & (sizes <= MAX_BUCKET)
    for s, e in zip(starts[usable], ends[usable], strict=True):
        group = owner[s:e].tolist()
        for i, x in enumerate(group):
            for y in group[i + 1:]:
                shared[(x, y)] += 1
    found = []
    for n, ((x, y), count) in enumerate(shared.items()):
        if count < MIN_SHARED:
            continue
        if should_cancel is not None and n % 50 == 0 and should_cancel():
            return []
        m = compare(tracks[keys[x]], tracks[keys[y]])
        if is_same(m):
            found.append((keys[x], keys[y], m))
    found.sort(key=lambda t: -t[2].score)
    return found
