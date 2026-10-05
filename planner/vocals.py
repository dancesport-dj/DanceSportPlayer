"""Audio-based instrumental/vocal detection.

The explicit labels (COMM 'instr' tag, '(Instr.)' filename marker) only cover
tracks the user annotated by hand. A tiny logistic regression trained ON those
labels over the already-cached 84-dim librosa feature vectors gives every other
analyzed track an instrumental probability — no extra audio pass, no new
dependency (numpy only, which the feature pipeline already needs).

Training set (rebuilt per session, instant for a few-thousand-track library):
  positives — entries with the explicit instrumental tag/marker;
  negatives — entries whose COMM comment carries a class tag but NO 'instr'
              (the user curated that comment, so no tag ≈ deliberately vocal).

Validated on the real library (5-fold CV, 545 pos / 1838 curated neg):
AUC 0.96; at the 0.8 threshold ≈88% precision / 79% recall against the raw
labels — and several "false positives" turned out to be untagged instrumentals
(Espana Cani, orchestra covers), so the true precision is higher.

Optionally (🎙️ Analyze vocals, `pip install demucs`), Demucs source separation
MEASURES each track's vocal-stem energy share — near zero for instrumentals,
~0.3 for vocal tracks. Benchmarked on 120 labeled tracks: AUC 0.97, 98%
precision / 93% recall at the 0.10 share threshold. A measured share outranks
both heuristics above; only the explicit user tag beats it.
"""
import importlib.util
import logging
import threading
from pathlib import Path

from planner.models import MusicEntry

log = logging.getLogger("dancesport.vocals")

# audio_instr_prob at or above this counts as instrumental (see module docstring).
INSTR_PROB_THRESHOLD = 0.8

# A measured vocal-stem share at or below this counts as instrumental
# (benchmark: 98% precision / 93% recall at 0.10).
VOCAL_SHARE_INSTR_MAX = 0.10

# Below this many positives/negatives the regression would just memorize noise.
_MIN_LABELS = 20

DEMUCS_INSTALL_HINT = ("Demucs not installed. Install with:  pip install demucs\n"
                       "(or everything optional at once:  pip install -r requirements-full.txt)")


def entry_is_instrumental(e: MusicEntry) -> bool:
    """Effective instrumental flag, most trustworthy source first: the explicit
    tag/filename marker wins; then a Demucs-MEASURED vocal share; then the
    curation heuristic (a class comment WITHOUT the tag ≈ deliberately vocal);
    then the learned audio probability (unknown → vocal, the safe default)."""
    if getattr(e, "is_instrumental", False):
        return True
    share = getattr(e, "vocal_share", None)
    if share is not None:
        return share <= VOCAL_SHARE_INSTR_MAX
    if getattr(e, "classes_ok", None):
        return False
    p = getattr(e, "audio_instr_prob", None)
    return p is not None and p >= INSTR_PROB_THRESHOLD


def _feature_vec(e: MusicEntry):
    feat = getattr(e, "features", None)
    mfcc = getattr(feat, "mfcc", None) if feat is not None else None
    return mfcc if mfcc is not None and len(mfcc) > 0 else None


def learn_instrumental_probs(entries: list[MusicEntry]) -> int:
    """Train on the user's own labels and set `audio_instr_prob` on every entry
    with cached audio features. Returns the number of entries annotated (0 when
    numpy is missing or the labels are too few/one-sided).

    Logistic regression on standardized features with balanced class weights
    and L2 — plain numpy, a few milliseconds for a few thousand tracks.
    """
    try:
        import numpy as np
    except ImportError:
        return 0

    pos, neg = [], []
    for e in entries:
        vec = _feature_vec(e)
        if vec is None:
            continue
        if getattr(e, "is_instrumental", False):
            pos.append(vec)
        elif getattr(e, "classes_ok", None):
            neg.append(vec)
    if len(pos) < _MIN_LABELS or len(neg) < _MIN_LABELS:
        log.info("🎙️ Too few labeled tracks to learn instrumental/vocal\n"
                 "instrumental: %d\n"
                 "curated vocal: %d (need %d each)",
                 len(pos), len(neg), _MIN_LABELS)
        return 0

    X = np.stack([np.asarray(v, dtype=np.float64) for v in pos + neg])
    y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    mu = X.mean(axis=0)
    sd = X.std(axis=0) + 1e-9
    Xs = (X - mu) / sd
    n, d = Xs.shape
    w = np.zeros(d)
    b = 0.0
    sample_w = np.where(y == 1, n / (2.0 * len(pos)), n / (2.0 * len(neg)))
    for _ in range(400):
        p = 1.0 / (1.0 + np.exp(-(Xs @ w + b)))
        grad_w = (sample_w * (p - y)) @ Xs / n + w / n   # + L2 (λ=1)
        grad_b = float((sample_w * (p - y)).mean())
        w -= 0.5 * grad_w
        b -= 0.5 * grad_b

    annotated = 0
    detected = 0
    for e in entries:
        vec = _feature_vec(e)
        if vec is None:
            continue
        xs = (np.asarray(vec, dtype=np.float64) - mu) / sd
        e.audio_instr_prob = float(1.0 / (1.0 + np.exp(-(xs @ w + b))))
        annotated += 1
        if entry_is_instrumental(e) and not e.is_instrumental:
            detected += 1
    log.info("🎙️ Instrumental/vocal learned from audio\n"
             "trained on: %d instrumental + %d curated vocal\n"
             "annotated: %d tracks\n"
             "newly detected instrumentals (≥%.2f): %d",
             len(pos), len(neg), annotated, INSTR_PROB_THRESHOLD, detected)
    return annotated


# ─────────────────────────────────────────────────────────────────────────────
# Optional: measured vocal share via Demucs source separation
# ─────────────────────────────────────────────────────────────────────────────

def demucs_available() -> bool:
    """Cheap probe — no heavy import."""
    return bool(importlib.util.find_spec("demucs") and importlib.util.find_spec("torch"))


_demucs_model = None
# Several worker threads may ask for the model at once; without this the first
# two would each build (and each download) their own copy.
_demucs_lock = threading.Lock()


def _get_demucs_model():
    """Load htdemucs once per process (first call may download ~80 MB weights).

    The loaded model is shared: `measure_vocal_share` only reads it, under
    `torch.no_grad()` and with the model in eval mode, so several threads may
    separate at the same time."""
    global _demucs_model
    with _demucs_lock:
        if _demucs_model is not None:
            return _demucs_model
        try:
            # Trust the OS certificate store for the weight download (corporate /
            # antivirus TLS proxies re-sign HTTPS with a CA certifi doesn't know).
            import truststore
            truststore.inject_into_ssl()
        except Exception:
            pass
        from demucs.pretrained import get_model
        _demucs_model = get_model("htdemucs")
        _demucs_model.eval()
        log.info("🎙️ Demucs htdemucs model loaded (sources: %s)", _demucs_model.sources)
    return _demucs_model


def measure_vocal_share(path: Path) -> float:
    """Vocal-stem energy share (0..1) of a 20 s excerpt, via Demucs htdemucs.

    Near zero for instrumentals, typically ≥0.2 for vocal tracks. ~7 s of CPU
    per track — call from a background worker and cache the result. Raises on
    decode/separation failure."""
    import numpy as np
    import librosa
    import torch

    model = _get_demucs_model()
    sr = model.samplerate
    y, _ = librosa.load(str(path), sr=sr, mono=False, offset=40.0, duration=20.0)
    if y.ndim == 1:
        y = np.stack([y, y])
    if y.shape[1] < sr * 5:   # short track — take the excerpt from the start
        y, _ = librosa.load(str(path), sr=sr, mono=False, duration=20.0)
        if y.ndim == 1:
            y = np.stack([y, y])
    from demucs.apply import apply_model
    wav = torch.from_numpy(np.ascontiguousarray(y, dtype=np.float32))
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (float(ref.std()) + 1e-8)
    with torch.no_grad():
        sources = apply_model(model, wav[None], device="cpu", progress=False)[0]
    rms = sources.pow(2).mean(dim=(1, 2)).sqrt()
    total = float(rms.sum()) + 1e-9
    return float(rms[model.sources.index("vocals")]) / total


def apply_vocal_shares(entries: list[MusicEntry], cache) -> int:
    """Annotate entries with their cached Demucs vocal share (`vocal_share`
    stays None for unmeasured tracks). Returns how many got a measurement."""
    applied = 0
    for e in entries:
        share = cache.get_vocal_share(e.path)
        if share is not None:
            e.vocal_share = float(share)
            applied += 1
    if applied:
        instr = sum(1 for e in entries
                    if e.vocal_share is not None
                    and e.vocal_share <= VOCAL_SHARE_INSTR_MAX)
        log.info("🎙️ Demucs vocal shares applied\n"
                 "measured tracks: %d\n"
                 "instrumental (share ≤ %.2f): %d",
                 applied, VOCAL_SHARE_INSTR_MAX, instr)
    return applied
