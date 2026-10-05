#!/usr/bin/env python3
"""Timbre-similarity metrics of the Dancesport Playlist Planner.

Extracted from dancesport_planner.py (light split): the two similarity
methods (`gaussian_kl` Mandel-Ellis symmetric KL — the app default — and the
pool-z-scored cosine `librosa` method), their KL→percent calibration, and the
`_timbre_similarity` dispatcher shared by display and playlist scoring.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from planner.models import MusicEntry

try:
    import numpy as np
except ImportError:   # similarity then stays neutral via HAS_LIBROSA=False
    np = None

from planner.db import (
    AudioFeatures, HAS_LIBROSA, _GAUSS_MFCC, _TIMBRE_MFCC_DIM,
)

def _feat_vector(f: AudioFeatures) -> list[float]:
    """Raw timbre-only feature vector [centroid, rms, *mfcc(60)] for pool standardization.

    Only the first `_TIMBRE_MFCC_DIM` (60) MFCC dims are used — the spectral-contrast
    and rhythm tail of the stored 84-dim vector is deliberately dropped (it's still kept
    in the DB, just not used for similarity: BPM already handles tempo, and mixing
    rhythm/brightness in diluted the timbre signal).

    Returns the untouched coordinates so the caller can z-score every dimension
    across the comparison pool (no hand-scaling of centroid/rms). After z-scoring
    no single coordinate — e.g. MFCC-0 energy (~100-500) vs ±20 for the real timbre
    coefficients — can hijack the cosine direction, giving a discriminative,
    perceptual ranking instead of everything bunched at ~99.9 %.
    """
    return [f.centroid, f.rms] + list(f.mfcc[:_TIMBRE_MFCC_DIM])


# Timbre similarity (0..1) at/above which a track is treated as a "strong" sound-alike:
# such tracks join the replace/↺ shortlist even when they rank below the top 10.
_STRONG_TIMBRE = 0.80

# Default timbre metric for the whole app (display + playlist scoring). The Gaussian /
# symmetric-KL (Mandel-Ellis) model matches the Java app's good suggestions far better
# than the summary-vector cosine, so it is the default everywhere.
_DEFAULT_TIMBRE_METHOD = "gaussian_kl"

# Calibration of the symmetric-KL (Jeffreys) divergence J → similarity 0..1.
# These are ABSOLUTE anchors measured on real same-dance pools (so the 80 % the user
# uses as the suggestion threshold is meaningful, not pool-relative):
#   J ≲ _KL_FLOOR  → ~1.0   (near-identical timbre / duplicate)
#   J ≈ 8          → ~0.80  (genuine sound-alike — the top ~10 % of a same-dance pool)
#   J ≈ median(11) → ~0.58
#   J ≳ 30         → ~0.0
# sim = exp(−(J − _KL_FLOOR) / _KL_SCALE), clamped to [0, 1].
_KL_FLOOR = 5.5
_KL_SCALE = 11.0

# A symmetric-KL divergence this small means the two MFCC Gaussians are numerically
# identical — i.e. the SAME audio content (a byte-identical / same-fingerprint file,
# since the content-addressed cache shares one Gaussian per fingerprint). Only such a
# pair may read a perfect 100 %; every genuinely different recording is capped at 99 %.
_KL_IDENTICAL = 1e-6


def _kl_to_sim(j: float) -> float:
    """Map a symmetric-KL divergence J to an absolute similarity in [0, 1].

    Confidence is capped at 0.99 unless J ≈ 0 (identical Gaussian → same-fingerprint
    file): two different recordings should never claim a perfect 100 % match."""
    sim = float(min(1.0, max(0.0, np.exp(-(j - _KL_FLOOR) / _KL_SCALE))))
    if j > _KL_IDENTICAL:
        sim = min(sim, 0.99)
    return sim


def _pool_similarity(anchor: AudioFeatures,
                     entries: list[MusicEntry]) -> dict[str, float]:
    """Standardized (z-scored) cosine of each entry's timbre to `anchor`, pool-local.

    Every feature dimension is z-scored across this pool (plus the anchor) BEFORE
    the cosine, so the loudness term (MFCC-0, ~100-500) can no longer dominate the
    direction and drag every score up to ~99.9 %. Each dimension then gets equal
    say and the scores spread out to reflect real timbral differences within the
    pool. Returns {str(entry.path): similarity 0..1}; entries without features (or when
    librosa is absent) get a neutral 0.5. Used by both `similar_tracks` (display)
    and `_pick` (playlist scoring) so the whole app shares one un-broken metric.
    """
    qv = _feat_vector(anchor)
    dim = len(qv)
    # Only compare vectors of the matching schema length — during a re-analysis after
    # a feature-vector change, stale shorter vectors may still be around; they stay
    # neutral (0.5) rather than crashing the stack or skewing the standardization.
    feats = [e for e in entries
             if e.features is not None and len(_feat_vector(e.features)) == dim]
    if not HAS_LIBROSA or not feats:
        return {str(e.path): 0.5 for e in entries}
    matrix = np.array(
        [_feat_vector(e.features) for e in feats] + [qv],
        dtype=float)
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std < 1e-9] = 1.0                       # dead dimensions → no contribution
    z = (matrix - mean) / std
    zq = z[-1]
    qnorm = float(np.linalg.norm(zq))
    out: dict[int, float] = {}
    for i, e in enumerate(feats):
        v = z[i]
        denom = float(np.linalg.norm(v)) * qnorm
        cos = float(np.dot(v, zq) / denom) if denom > 0 else 0.0
        out[str(e.path)] = (cos + 1.0) / 2.0    # map [-1,1] cosine → [0,1]
    for e in entries:
        out.setdefault(str(e.path), 0.5)        # featureless entries stay neutral
    return out


def _gauss_of(f: AudioFeatures):
    """(mean, covariance, inverse-covariance) triple for a Gaussian, memoized.

    Computed once per AudioFeatures instance and cached on it (`gauss_cache`), so
    a full playlist generation no longer re-inverts the same 20×20 covariance for
    every pick. Returns (None, None, None) when the model is absent or singular.
    """
    if f is None:
        return None, None, None
    if f.gauss_cache is not None:
        return f.gauss_cache
    triple = (None, None, None)
    if f.mfcc_mean is not None and f.mfcc_cov is not None:
        k = _GAUSS_MFCC
        if len(f.mfcc_mean) == k and len(f.mfcc_cov) == k * k:
            mu = np.asarray(f.mfcc_mean, dtype=float)
            cov = np.asarray(f.mfcc_cov, dtype=float).reshape(k, k)
            try:
                triple = (mu, cov, np.linalg.inv(cov))
            except np.linalg.LinAlgError:
                pass
    f.gauss_cache = triple
    return triple


def _gaussian_kl_similarity(anchor: AudioFeatures,
                            entries: list[MusicEntry]) -> dict[str, float]:
    """Timbre similarity via the symmetric KL divergence between per-song Gaussians.

    This is the Mandel-Ellis model (a single full-covariance Gaussian over the raw
    per-frame MFCCs) — the distribution-based metric the Java app uses, ported to a
    fast closed form. For two Gaussians N0(μ0,Σ0), N1(μ1,Σ1) the symmetric KL
    (Jeffreys divergence) is

        J = ½[ tr(Σ1⁻¹Σ0) + tr(Σ0⁻¹Σ1) + (μ1-μ0)ᵀ(Σ0⁻¹+Σ1⁻¹)(μ1-μ0) − 2k ]

    J ≥ 0, and 0 iff the songs have identical timbre distributions. Unlike the
    summary-vector cosine, this compares the *whole distribution* (spread + cross-
    coefficient covariance), so it is far more discriminative and — crucially —
    absolute (a song-pair score does not depend on what else is in the pool).

    The divergence is mapped to a 0..1 similarity with the ABSOLUTE calibration
    `_kl_to_sim` (see _KL_FLOOR / _KL_SCALE): genuine sound-alikes read ≳ 0.80 — the
    level the user treats as a suggestion — while the bulk of a same-dance pool spreads
    out below. The mapping is monotone in J, so the ranking is unchanged. Entries
    without a Gaussian (or when librosa is absent) get a neutral 0.5. Returns
    {str(entry.path): similarity 0..1}.
    """
    a_mu, a_cov, a_inv = _gauss_of(anchor)
    if not HAS_LIBROSA or a_mu is None:
        return {str(e.path): 0.5 for e in entries}
    k = _GAUSS_MFCC
    dists: dict[str, float] = {}
    for e in entries:
        mu, cov, inv = _gauss_of(e.features)
        if mu is None:
            continue
        diff = mu - a_mu
        # einsum('ij,ji->') = tr(A·B) without materializing the product (O(k²) not O(k³));
        # the inverses themselves come memoized from _gauss_of.
        j = 0.5 * (
            float(np.einsum('ij,ji->', inv, a_cov))
            + float(np.einsum('ij,ji->', a_inv, cov))
            + float(diff @ (a_inv + inv) @ diff) - 2 * k
        )
        dists[str(e.path)] = max(0.0, j)
    if not dists:
        return {str(e.path): 0.5 for e in entries}
    # Map divergence → similarity with the absolute calibration (see `_kl_to_sim`):
    # genuine sound-alikes land ≳ 0.80, the rest of the pool spreads out below.
    out: dict[str, float] = {}
    for e in entries:
        j = dists.get(str(e.path))
        out[str(e.path)] = _kl_to_sim(j) if j is not None else 0.5
    return out


def _timbre_similarity(anchor: AudioFeatures,
                       entries: list[MusicEntry],
                       method: str | None = None) -> dict[str, float]:
    """Dispatch to the app's timbre metric (default `_DEFAULT_TIMBRE_METHOD`).

    The single entry point shared by display (`similar_tracks`) and playlist scoring
    (`_pick`, `anchor_similarity`) so the whole app uses one calibrated metric.
    """
    method = method or _DEFAULT_TIMBRE_METHOD
    if method == "gaussian_kl":
        return _gaussian_kl_similarity(anchor, entries)
    return _pool_similarity(anchor, entries)


# ── Three views at once: timbre, groove and melody ──────────────────────────────
SOUND_VIEWS = ("timbre", "groove", "melody")

# Anchors whose rankings are kept: the event planner asks about a dozen per
# dance, then one per heat — each a whole dance's worth of numbers.
_SOUND_MEMO = 64


def _z_cosines(query, rows) -> list[float]:
    """Cosine of each row to `query` after z-scoring every dimension across the
    rows and the query — the pool-relative standardization `_pool_similarity`
    and `embedding_similar` use, so no single loud dimension decides."""
    m = np.vstack([np.asarray(rows, dtype=float), np.asarray(query, dtype=float)])
    sd = m.std(axis=0)
    sd[sd < 1e-9] = 1.0
    z = (m - m.mean(axis=0)) / sd
    q, rest = z[-1], z[:-1]
    denom = np.linalg.norm(rest, axis=1) * float(np.linalg.norm(q))
    return list(np.divide(rest @ q, denom, out=np.zeros(len(rest)), where=denom > 0))


def _shares(scores: dict[str, float]) -> dict[str, float]:
    """Each title's place among the others, 1.0 for the best down towards 0."""
    n = len(scores)
    order = sorted(scores, key=scores.get, reverse=True)
    return {path: 1.0 - rank / n for rank, path in enumerate(order)}


def _mean(views: dict[str, float]) -> float:
    return sum(views.values()) / len(views)


class SoundAlike:
    """How much titles sound like one another, three ways: `timbre` (the
    Gaussian/KL of the MFCC frames), `groove` (the librosa vector — timbre,
    brightness and rhythm) and `melody` (the chroma cover match). Each view
    ranks a title among the anchor's dance, 1.0 for the closest, and the
    agreement is the mean of the views — Marcel: the title all three put
    highest wins. A view the anchor has but a title lacks puts that title in
    its middle (0.5).

    Callable like `MusicLibrary.similar_tracks`, returning (agreement, entry)
    best-first. `chroma` maps an entry to its chroma vector, or None."""

    def __init__(self, lib, chroma=None):
        self._lib = lib
        self._chroma = chroma
        self._memo: dict[str, dict[str, dict[str, float]]] = {}

    def __call__(self, anchor, n: int = 10, same_dance: bool = True,
                 min_display: float = 0.0, method=None):
        ranks = self._ranks(anchor, same_dance)
        scored = sorted(((_mean(v), e) for e in self._pool(anchor, same_dance)
                         if (v := ranks.get(str(e.path)))),
                        key=lambda t: t[0], reverse=True)
        return [(s, e) for s, e in scored if s >= min_display][:n]

    def views(self, anchor, other, same_dance: bool = True) -> dict[str, float]:
        """{view: 0..1} of `other` against `anchor`, empty when neither is analysed."""
        return self._ranks(anchor, same_dance).get(str(other.path), {})

    def agreement(self, anchor, other) -> float:
        views = self.views(anchor, other)
        return _mean(views) if views else 0.0

    def _pool(self, anchor, same_dance: bool):
        base = (self._lib.by_dance(anchor.dance) if same_dance and anchor.dance
                else self._lib.entries)
        return [e for e in base if e is not anchor and not e.is_xmas]

    def _ranks(self, anchor, same_dance: bool) -> dict[str, dict[str, float]]:
        key = f"{same_dance}:{anchor.path}"
        if key in self._memo:
            return self._memo[key]
        pool = self._pool(anchor, same_dance)
        views = {}
        f = anchor.features
        if f is not None and HAS_LIBROSA:
            gauss = [e for e in pool if _gauss_of(e.features)[0] is not None]
            if gauss and _gauss_of(f)[0] is not None:
                views["timbre"] = _gaussian_kl_similarity(f, gauss)
            dim = len(f.mfcc)
            rows = [e for e in pool
                    if e.features is not None and len(e.features.mfcc) == dim]
            if len(rows) >= 2:
                vec = lambda x: [x.centroid, x.rms, *x.mfcc]  # noqa: E731
                views["groove"] = dict(zip(
                    (str(e.path) for e in rows),
                    _z_cosines(vec(f), [vec(e.features) for e in rows])))
        own = self._chroma(anchor) if self._chroma else None
        if own is not None and HAS_LIBROSA:
            have = [(e, v) for e in pool
                    if (v := self._chroma(e)) is not None and len(v) == len(own)]
            if len(have) >= 2:
                views["melody"] = dict(zip(
                    (str(e.path) for e, _v in have),
                    _z_cosines(own, [v for _e, v in have])))
        shares = {view: _shares(scores) for view, scores in views.items()}
        out: dict[str, dict[str, float]] = {}
        for e in pool:
            path = str(e.path)
            got = {view: s[path] for view, s in shares.items() if path in s}
            if got:
                out[path] = {view: got.get(view, 0.5) for view in shares}
        if len(self._memo) >= _SOUND_MEMO:
            self._memo.pop(next(iter(self._memo)))
        self._memo[key] = out
        return out
