#!/usr/bin/env python3
"""The librosa analysis of one audio file: the packed feature vector and the
Gaussian timbre model (`AudioFeatures`), the dance-seeded tempo read off the
tempogram, the shared mute of the decoders' native stderr, and the up-front
probe of whether this machine can decode an MP3 at all. AudioCache in
planner.music.db stores what `analyze_file` returns."""

import contextlib
import logging
import os
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import librosa
    HAS_LIBROSA = HAS_NUMPY   # librosa is unusable without numpy
except ImportError:
    HAS_LIBROSA = False

from planner.dances import BEATS_PER_BAR, default_takt

log = logging.getLogger("dancesport.db")


# Length of the packed feature vector stored in AudioFeatures.mfcc. The name is
# historical — it now holds MFCC *plus* spectral-contrast and rhythm features:
#   60  MFCC      (20 means | 20 stds | 20 delta-means)   – timbre
#   10  contrast  (5 means | 5 stds, spectral_contrast)   – brightness/genre
#   14  rhythm    (12 tempogram lag-profile bins | onset mean | onset std) – groove
# = 84 total. Bumping this (and CACHE_VERSION) invalidates shorter cached vectors.
AUDIO_FEAT_DIM = 84

# Only the first 60 dims of the 84-dim vector are pure MFCC timbre (20 means | 20 stds
# | 20 delta-means). The contrast (10) + rhythm (14) tail is still STORED in the DB but
# deliberately EXCLUDED from timbre similarity — BPM already handles tempo, and mixing
# rhythm/brightness into the cosine diluted the timbre signal. See `_feat_vector`.
TIMBRE_MFCC_DIM = 60

# Per-song single-Gaussian timbre model (Mandel-Ellis): k MFCC coefficients →
# mean (k) + full covariance (k×k), compared by symmetric KL. Independent of the
# summary vector above; uses raw per-frame MFCCs with short (Java-matched) frames.
GAUSS_MFCC = 20


def tempo_prior(dance: str | None, takt: float | None) -> float | None:
    """Expected musical tempo (beats/min) to seed librosa's beat tracker.

    Dance-agnostic beat tracking snaps syncopated grooves (esp. samba — the "and" of
    beat 1 and "e" of beat 2 fire strong off-beat transients) to a metric harmonic of
    the true pulse. Seeding `start_bpm` with the dance's expected tempo pulls the
    estimate back onto the real beat. Returns None when the dance is unknown (→ keep
    librosa's default prior). Prefers the per-file takt; falls back to the dance norm.
    """
    bpb = BEATS_PER_BAR.get(dance or "")
    if bpb is None:
        return None
    t = takt if takt else default_takt(dance)
    return float(t * bpb) if t else None


def _tempo_from_tempogram(tg, sr, expected_bpm, hop_length=512, band=0.10):
    """Read the tempo off an already-computed tempogram, constrained to the dance's
    expected band (`expected_bpm` ± `band`).

    A library-wide comparison (samba especially) showed a plain beat tracker — even
    seeded with `start_bpm` — drifts onto metric harmonics (×0.8 / ×1.3 / ×1.4 of the
    real pulse) because syncopated off-beats out-vote the true beat. Picking the
    strongest tempogram-autocorrelation lag *within* the expected band can't land on a
    harmonic, so it tracked the label on 96% of files (100% of sambas) vs 65% for the
    unconstrained tracker. Returns None when no prior is given or the band is empty
    (caller then falls back to `librosa.beat.beat_track`).

    The lag axis is integer onset frames, so its BPM grid is hyperbolically coarse at
    fast tempi: at Viennese-Waltz pulse (~177 bpm) the only grid points are lag 7 =
    185 bpm and lag 8 = 162 bpm — nothing between — so every WW snapped to 185 ≈ T62.
    We refine the winning lag to sub-frame precision with a parabola through it and its
    two neighbours before converting back to BPM.
    """
    if tg is None or not expected_bpm:
        return None
    ac = np.nan_to_num(np.mean(tg, axis=1))                       # mean lag profile
    freqs = librosa.tempo_frequencies(len(ac), sr=sr, hop_length=hop_length)
    lo, hi = expected_bpm * (1.0 - band), expected_bpm * (1.0 + band)
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        return None
    idx = np.where(mask)[0]
    peak = int(idx[int(np.argmax(ac[idx]))])
    # Sub-lag refinement: parabolic interpolation of the peak (uses the raw lag
    # neighbours, even if they fall just outside the band) → fractional lag.
    delta = 0.0
    if 0 < peak < len(ac) - 1:
        ym1, y0, yp1 = float(ac[peak - 1]), float(ac[peak]), float(ac[peak + 1])
        denom = ym1 - 2.0 * y0 + yp1
        if denom != 0.0:
            delta = max(-0.5, min(0.5, 0.5 * (ym1 - yp1) / denom))
    lag = peak + delta
    if lag <= 0:
        return None
    return float(60.0 * sr / (hop_length * lag))


@dataclass
class AudioFeatures:
    bpm: float
    mfcc: Any  # 84-dim float32 ndarray (list w/o numpy), see _AUDIO_FEAT_DIM
    centroid: float  # spectral centroid mean
    rms: float  # root-mean-square energy mean
    # Single-Gaussian timbre model over raw per-frame MFCCs (Mandel-Ellis). Used by the
    # "gaussian_kl" similarity method. None for vectors analyzed before schema v9.
    # Stored as float32 ndarrays — check `is None`, never truthiness.
    mfcc_mean: Any = None  # _GAUSS_MFCC means
    mfcc_cov: Any = None  # _GAUSS_MFCC × _GAUSS_MFCC covariance, row-major
    # Lazily-memoized (mu, cov, inv) float64 triple filled by _gauss_of on first
    # use, so repeated similarity calls skip the 20×20 matrix inversion. Never
    # persisted; (None, None, None) marks an absent/singular Gaussian.
    gauss_cache: Any = field(default=None, repr=False, compare=False)


# Why audio analysis cannot run here. A library fails file by file for one single
# reason — no librosa, or nothing on this machine that can decode an MP3 — so 3638
# identical tracebacks in the log say no more than one probe up front does.
PROBE_NO_LIBROSA = "no_librosa"
PROBE_NO_BACKEND = "no_backend"
PROBE_FAILED = "probe_failed"


_quiet_lock = threading.Lock()
_quiet_depth = 0
_quiet_saved: tuple[int, int] | None = None


def _sync_win32_stderr() -> None:
    """Point the Win32 STD_ERROR_HANDLE at whatever fd 2 now holds.

    audioread's ffmpeg subprocess inherits that handle, not the CRT fd 2. The CRT
    re-points it on `dup2(…, 2)` only in console processes, so it is set here
    explicitly — and always to fd 2's live handle: a handle saved before `dup2`
    is closed by it, and restoring that one leaves every later child a dead or
    recycled stderr.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        import msvcrt
        ctypes.windll.kernel32.SetStdHandle(-12, msvcrt.get_osfhandle(2))   # STD_ERROR_HANDLE
    except Exception:
        log.debug("🪟 Could not point the Win32 stderr handle at fd 2", exc_info=True)


def _mute_stderr() -> tuple[int, int] | None:
    """Point fd 2 and the Win32 STD_ERROR_HANDLE at the null device.

    Returns what `_unmute_stderr` needs to put them back, or None when there is
    no fd 2 to redirect.
    """
    try:
        saved_fd = os.dup(2)
    except OSError:
        return None
    null_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null_fd, 2)                  # CRT stderr (mpg123 / libav)
    _sync_win32_stderr()
    return saved_fd, null_fd


def _unmute_stderr(saved: tuple[int, int]) -> None:
    saved_fd, null_fd = saved
    os.dup2(saved_fd, 2)
    _sync_win32_stderr()
    os.close(saved_fd)
    os.close(null_fd)


@contextlib.contextmanager
def quiet_native_stderr() -> Iterator[None]:
    """Silence the decoders' C-level stderr (mpg123 / ffmpeg / libsndfile chatter).

    Python's `sys.stderr` can't catch what is written below Python, so fd 2 itself
    is pointed at the null device. That is process-wide state, and the analysis
    pass decodes on several threads at once: were each decode to save and restore
    it on its own, the second one in would save the null device and put it back
    last, muting stderr for the rest of the session. So the mute is shared — the
    first decode in redirects, the last one out restores.
    """
    global _quiet_depth, _quiet_saved
    with _quiet_lock:
        if _quiet_depth == 0:
            _quiet_saved = _mute_stderr()
        _quiet_depth += 1
    try:
        yield
    finally:
        with _quiet_lock:
            _quiet_depth -= 1
            if _quiet_depth == 0 and _quiet_saved is not None:
                _unmute_stderr(_quiet_saved)
                _quiet_saved = None


def probe_decode_backend(path: Path) -> str | None:
    """Decode 2 s of `path`: None when that works, else a `PROBE_*` reason.

    librosa reads MP3 through soundfile when libsndfile is new enough, and falls
    back to audioread — which shells out to `ffmpeg` BY NAME, so a copy bundled
    next to the app but absent from PATH does not count there. Either way the
    verdict holds for the whole library, and it is worth having before the user
    commits to an hour of analysis.
    """
    if not HAS_LIBROSA:
        return PROBE_NO_LIBROSA
    # Same stderr muting as _analyze_file: a decoder that fails is a loud one.
    exc = None
    with quiet_native_stderr():
        try:
            librosa.load(str(path), sr=11025, offset=0.0, duration=2.0, mono=True)
        except Exception as ex:
            exc = ex
    if exc is None:
        return None
    log.error("🔬 Audio decode probe failed\n"
              "file: %s\n"
              "error: %s: %s", path, type(exc).__name__, exc)
    if "NoBackendError" in type(exc).__qualname__ or "backend" in str(exc).lower():
        return PROBE_NO_BACKEND
    return PROBE_FAILED


def release_free_heap() -> None:
    """Hand already-freed heap pages back to the operating system.

    Analysing one file allocates a decoded 60 s window plus a stack of feature
    matrices and frees them again. Freeing returns them to the *allocator*, not
    to the OS: glibc and macOS' magazine malloc both keep the emptied pages
    mapped for reuse, and over tens of thousands of files that reservation is
    what the user sees as the process eating all the memory. These two calls
    release it. No Windows equivalent is needed — its heap decommits on free.
    """
    try:
        import ctypes
        if sys.platform == 'darwin':
            ctypes.CDLL(None).malloc_zone_pressure_relief(None, 0)
        elif sys.platform.startswith('linux'):
            ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:   # best effort: a missing symbol only costs us the release
        log.debug("🧹 No malloc release on this platform", exc_info=True)


def _gaussian_timbre(y, sr):
    """The per-frame MFCCs' mean and flattened covariance, or (None, None)."""
    # ── Single-Gaussian timbre model (Mandel-Ellis), compared by symmetric KL.
    # Unlike the summary vector above (one averaged point), this keeps the full
    # distribution of per-frame MFCCs: mean + full covariance. Short, Java-matched
    # frames (512 win / 256 hop @ 11025 ≈ 46 ms / 23 ms) give finer time resolution
    # than the librosa default (n_fft=2048 ≈ 186 ms) before any averaging. Pure MFCC
    # only — no rhythm/contrast (BPM handles tempo).
    g_mfcc = librosa.feature.mfcc(
        y=y, sr=sr, n_mfcc=GAUSS_MFCC, n_fft=512, hop_length=256)   # (k, frames)
    frames = g_mfcc.T                                                # (frames, k)
    if frames.shape[0] >= GAUSS_MFCC + 1:
        mu = frames.mean(axis=0)
        cov = np.cov(frames, rowvar=False)                          # (k, k)
        # Regularize so the covariance is invertible (KL needs Σ⁻¹ and ln|Σ|).
        cov += np.eye(GAUSS_MFCC) * (1e-3 * float(np.trace(cov)) / GAUSS_MFCC + 1e-6)
        mfcc_mean = mu.astype(np.float32)
        mfcc_cov = cov.reshape(-1).astype(np.float32)
    else:
        mfcc_mean = mfcc_cov = None   # too few frames → no Gaussian (stays neutral)
    return mfcc_mean, mfcc_cov


def analyze_file(path: Path, expected_bpm: float | None = None) -> AudioFeatures:
    """Load audio and extract features, suppressing all ffmpeg/mpg123 stderr output.

    `expected_bpm` (beats/min, from `_tempo_prior`) seeds the beat tracker so
    syncopated grooves don't lock onto a metric harmonic; None keeps the default.

    On Windows, audioread runs ffmpeg as a subprocess that inherits the Win32
    STD_ERROR_HANDLE (not the CRT fd 2); `quiet_native_stderr` mutes both layers.
    """
    with quiet_native_stderr():
        # Analyze the MIDDLE of the track, not the intro. Dance-track intros are
        # atypical (count-ins, fades, talk-ins, slow builds); the steady body is
        # representative. Mirrors the Java extractor's skip-intro/skip-outro. We
        # center a 60 s window: for a 3-min song this is ≈ 60–120 s.
        try:
            total = float(librosa.get_duration(path=str(path)))
        except Exception:
            log.debug("⏱ No length for the analysis window, reading from the start\n"
                      "file: %s", path, exc_info=True)
            total = 0.0
        win = 60.0
        offset = max(0.0, (total - win) / 2.0) if total > win else 0.0
        y, sr = librosa.load(str(path), sr=11025, offset=offset, duration=win, mono=True)
    # ── Timbre: 20 MFCCs – mean + std per coefficient + delta-means (60 values).
    # The std captures temporal variation (e.g. steady waltz vs energetic jive);
    # the delta-means capture articulation dynamics (staccato tango vs legato waltz).
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    deltas = librosa.feature.delta(mfccs)     # frame-to-frame rate of change
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)
    mfcc_block = (
        [float(np.mean(c)) for c in mfccs]  +   # 20 means  (timbral shape)
        [float(np.std(c)) for c in mfccs]  +    # 20 stds   (temporal spread)
        [float(np.mean(c)) for c in deltas]     # 20 delta-means (articulation dynamics)
    )
    # ── Brightness / genre: spectral contrast (peak-vs-valley energy per band).
    # n_bands=4 keeps the top band (200·2^4 = 3200 Hz) below the 5512 Hz Nyquist
    # at sr=11025 (the default n_bands=6 would exceed it and raise). → 5 sub-bands.
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=4)   # (5, t)
    contrast_block = (
        [float(np.mean(c)) for c in contrast] +  # 5 means
        [float(np.std(c))  for c in contrast]    # 5 stds
    )
    # ── Groove: a compact rhythmic fingerprint. The tempogram is the local
    # autocorrelation of the onset envelope (how the pulse recurs); averaging it
    # over time gives a lag-profile that captures the *rhythmic feel*, not just the
    # BPM number. We compress that profile into RHYTHM_BINS bins, plus onset
    # strength mean/std (how driving/sharp the rhythm is).
    rhythm_bins = 12
    tg = None
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size and float(np.max(onset_env)) > 0:
        tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)   # (win, t)
        lag_profile = np.nan_to_num(np.mean(tg, axis=1))                  # (win,)
        usable = (lag_profile.size // rhythm_bins) * rhythm_bins
        rhythm_fp = (lag_profile[:usable].reshape(rhythm_bins, -1).mean(axis=1)
                     if usable else np.zeros(rhythm_bins))
        onset_mean, onset_std = float(np.mean(onset_env)), float(np.std(onset_env))
    else:
        rhythm_fp = np.zeros(rhythm_bins)
        onset_mean = onset_std = 0.0
    rhythm_block = [float(x) for x in rhythm_fp] + [onset_mean, onset_std]

    # ── Tempo. When the dance is known, read it off the tempogram inside the
    # expected band (robust to syncopation — see `_tempo_from_tempogram`); reusing
    # the rhythm tempogram makes this nearly free. Otherwise fall back to librosa's
    # unconstrained beat tracker.
    bpm = _tempo_from_tempogram(tg, sr, expected_bpm)
    if bpm is None:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
        bpm = float(np.mean(tempo))

    feat_vec = mfcc_block + contrast_block + rhythm_block
    if len(feat_vec) != AUDIO_FEAT_DIM:   # not an assert: -O would strip it
        raise RuntimeError(
            f"feature vector is {len(feat_vec)}, expected {AUDIO_FEAT_DIM}")

    mfcc_mean, mfcc_cov = _gaussian_timbre(y, sr)

    return AudioFeatures(
        bpm=float(bpm),
        mfcc=np.asarray(feat_vec, dtype=np.float32),
        centroid=float(np.mean(centroid)),
        rms=float(np.mean(rms)),
        mfcc_mean=mfcc_mean,
        mfcc_cov=mfcc_cov,
    )
