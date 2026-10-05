#!/usr/bin/env python3
"""
planner/embeddings.py – optional deep-audio-embedding backends for the dancesport planner.

OpenL3 is OPTIONAL and lazily imported, so the app runs fine without the heavy ML
dependencies installed:

  • OpenL3 – a pretrained music embedding (~512-d). Perceptual "sounds-alike"
    similarity, used as an alternative ranking to the librosa timbre+rhythm vector.
    Install:  pip install openl3 tensorflow

Embeddings are cached in the SAME SQLite DB as the librosa features (one extra
`embeddings(fp, model, vec)` table), keyed by content fingerprint so byte-identical
copies share a single vector — exactly like AudioCache. Read-only on the audio files
(load only), consistent with the rest of the pipeline.
"""

import importlib.util
import logging
import traceback
from array import array
from pathlib import Path
from collections.abc import Callable

logger = logging.getLogger(__name__)

import planner.db
from planner.models import MusicEntry
from planner.db import _db, quiet_native_stderr


class AudioTooShort(ValueError):
    """There is less audio in the file than the descriptor needs.

    A transition swish or a spoken jingle in the samples folder is not a track
    and never will be one — indexing has nothing to do here, so this is a skip,
    not a failure, and it must not colour the error count of a whole run.
    """


# Model identifiers used as the `model` column / dict key.
MODEL_OPENL3 = "openl3"
MODEL_CHROMA = "chroma2dftm"         # librosa-only chroma cover/remix matcher (melody, not timbre)

# Sample rates the backends expect.
_OPENL3_SR = 48000
_EMBED_SECONDS = 60.0                # analyse the first 60 s (same window as librosa)

_certs_injected = False


def _enable_system_certs() -> None:
    """Make Python trust the OS certificate store before any model download.

    On machines behind a corporate / antivirus TLS-intercepting proxy, the HTTPS
    connection to huggingface.co is re-signed by a local root CA that lives in the
    Windows cert store but NOT in Python's bundled `certifi`, so downloads fail with
    `CERTIFICATE_VERIFY_FAILED`. `truststore` routes verification through the OS store
    (which has that CA), fixing it. Optional + best-effort: a no-op if truststore is
    absent or already injected.
    """
    global _certs_injected
    if _certs_injected:
        return
    _certs_injected = True
    try:
        import truststore
        truststore.inject_into_ssl()
        logger.info("🔐 Using OS certificate store for model downloads (truststore)")
    except Exception as exc:
        logger.debug("truststore not active (%s) — using default certifi bundle", exc)


# The decoders' stderr muting is shared with the analysis pass (planner.db): fd 2
# is process-wide, so all decodes on all threads must go through one lock.
_quiet_native_stderr = quiet_native_stderr


# ── availability probes (no heavy import) ────────────────────────────────────────
def openl3_available() -> bool:
    return bool(importlib.util.find_spec("openl3") and importlib.util.find_spec("tensorflow"))


def chroma_available() -> bool:
    # Chroma uses librosa only — the same dependency the core feature pipeline needs,
    # so it's available whenever audio analysis is.
    return bool(importlib.util.find_spec("librosa"))


def install_hint(model: str) -> str:
    if model == MODEL_CHROMA:
        return "Chroma cover-match needs librosa.  Install with:  pip install librosa"
    return "OpenL3 not installed. Install with:  pip install openl3 tensorflow"


# ── embedding store (SQLite, shared DB) ──────────────────────────────────────────
class EmbeddingStore:
    """Content-addressed cache of deep embeddings in the shared normalized DB.

    Table `embeddings(fp, model, vec)` PRIMARY KEY (fp, model): one float32-packed
    vector per (content fingerprint, model). An in-memory mirror per model keeps
    ranking fast. Fingerprints are resolved through the passed AudioCache so they
    match the librosa feature dedup exactly.
    """

    def __init__(self, cache: planner.db.AudioCache):
        self._cache = cache
        self._mirror: dict[str, dict[str, list]] = {}   # model → {fp → vec list}
        self._fps: dict[str, set[str]] = {}             # model → {fp}, keys only
        self._ensure_schema()

    @staticmethod
    def _ensure_schema() -> None:
        _db().execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "  fp TEXT NOT NULL, model TEXT NOT NULL, vec BLOB NOT NULL,"
            "  PRIMARY KEY (fp, model))")
        # PK is (fp, model), so a lookup by model alone can't use it as a
        # prefix seek — every _load_model()/fps() call was a full table scan.
        _db().execute(
            "CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model)")
        _db().commit()

    @staticmethod
    def _pack(vec) -> bytes:
        return array('f', (float(x) for x in vec)).tobytes()

    @staticmethod
    def _unpack(blob: bytes) -> list[float]:
        a = array('f'); a.frombytes(blob); return list(a)

    def _load_model(self, model: str) -> dict[str, list[float]]:
        if model not in self._mirror:
            rows = _db().execute(
                "SELECT fp, vec FROM embeddings WHERE model = ?", (model,)).fetchall()
            self._mirror[model] = {fp: self._unpack(v) for fp, v in rows}
        return self._mirror[model]

    def fps(self, model: str) -> set[str]:
        """Which fingerprints this model has a vector for — the KEYS only.

        "How many of these tracks are indexed" needs no vectors, and the whole
        mirror is an expensive way to answer it: 53k OpenL3 blobs unpacked into
        53k Python lists cost five seconds of every startup, for three numbers
        on a status label. Reading the keys alone is a tenth of a second.

        The already-unpacked mirror is preferred when there is one — which is
        also what keeps this honest without any invalidation: `put` loads the
        mirror before it writes, so a store that has gained an embedding is
        answering out of the mirror by then, never out of a stale key set."""
        if model in self._mirror:
            return set(self._mirror[model])
        if model not in self._fps:
            self._fps[model] = {fp for (fp,) in _db().execute(
                "SELECT fp FROM embeddings WHERE model = ?", (model,))}
        return self._fps[model]

    def fingerprint(self, path: Path) -> str | None:
        return self._cache.fingerprint(path)

    def get(self, path: Path, model: str) -> list[float] | None:
        fp = self._cache.fingerprint(path)
        if fp is None:
            return None
        return self._load_model(model).get(fp)

    def get_by_fp(self, fp: str | None, model: str) -> list[float] | None:
        return self._load_model(model).get(fp) if fp else None

    def recorded(self, path: Path, model: str) -> list[float] | None:
        """The vector for `path` by the fingerprint on record — never touches
        the disk, for look-ups over a whole dance."""
        return self.get_by_fp(self._cache.recorded_fingerprint(path), model)

    def put(self, fp: str, model: str, vec) -> None:
        vec = list(vec)
        self._load_model(model)[fp] = vec
        _db().execute(
            "INSERT OR REPLACE INTO embeddings (fp, model, vec) VALUES (?,?,?)",
            (fp, model, self._pack(vec)))

    def has(self, fp: str, model: str) -> bool:
        return fp in self._load_model(model)

    def count(self, model: str) -> int:
        return len(self._load_model(model))

    def save(self) -> None:
        _db().commit()


# ── backends (heavy imports happen lazily, on first use) ──────────────────────────
class _OpenL3Backend:
    """Lazy wrapper around the OpenL3 music embedding model (loaded once)."""

    def __init__(self):
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            _enable_system_certs()
            import openl3   # heavy import on first use
            self._model = openl3.models.load_audio_embedding_model(
                input_repr="mel256", content_type="music", embedding_size=512)
        return self._model

    def embed_file(self, path: Path) -> list[float]:
        import numpy as np
        import openl3
        import librosa
        with _quiet_native_stderr():
            y, sr = librosa.load(str(path), sr=_OPENL3_SR, mono=True,
                                 offset=0.0, duration=_EMBED_SECONDS)
        emb, _ = openl3.get_audio_embedding(
            y, sr, model=self._ensure_model(), hop_size=1.0, verbose=False)
        vec = np.mean(emb, axis=0)                     # average over time → (512,)
        norm = float(np.linalg.norm(vec))
        return (vec / norm).tolist() if norm else vec.tolist()


_CHROMA_SR = 22050
_CHROMA_TIME_BINS = 128       # chromagram resampled to this many frames → tempo/length invariant
_CHROMA_KEEP_FREQ = 40        # low time-frequency coefficients kept after the 2-D FFT


class _ChromaBackend:
    """Key- and tempo-invariant chroma descriptor (librosa only, no ML deps).

    Computes a CENS chromagram (12 pitch classes × time), resamples the time axis to
    a fixed length, then takes the MAGNITUDE of its 2-D Fourier transform. That
    magnitude is invariant to circular pitch shifts (a cover in a different key) and
    to time translation, while the fixed-length resample absorbs global tempo
    differences — so two recordings of the SAME composition land close even when the
    timbre (instrumentation, vocals, production) is completely different. This is what
    lets remixes / AI covers match, where the timbre metrics correctly do not.
    """

    def embed_file(self, path: Path) -> list[float]:
        import numpy as np
        import librosa
        with _quiet_native_stderr():
            y, sr = librosa.load(str(path), sr=_CHROMA_SR, mono=True,
                                 offset=0.0, duration=_EMBED_SECONDS)
        if y.size < sr:
            raise AudioTooShort("audio too short for a chroma descriptor")
        C = librosa.feature.chroma_cens(y=y, sr=sr)                  # (12, T)
        if C.shape[1] < 8:
            raise AudioTooShort("chromagram too short")
        T = C.shape[1]
        xs = np.linspace(0, T - 1, _CHROMA_TIME_BINS)
        Cr = np.vstack([np.interp(xs, np.arange(T), C[i]) for i in range(12)])
        F = np.abs(np.fft.fft2(Cr))[:, :_CHROMA_KEEP_FREQ]
        F[0, 0] = 0.0                                                # drop DC (overall energy)
        vec = F.flatten()
        norm = float(np.linalg.norm(vec))
        return (vec / norm).tolist() if norm else vec.tolist()


# Singletons (models are expensive; reuse across calls).
_openl3 = _OpenL3Backend()
_chroma = _ChromaBackend()


def get_backend(model: str):
    if model == MODEL_CHROMA:
        return _chroma
    return _openl3


# ── index building (compute + cache embeddings over a set of entries) ─────────────
def _embed_entry(entry: MusicEntry, model: str, store: EmbeddingStore) -> bool:
    """Compute + cache the embedding for one entry. Returns True if newly computed."""
    fp = store.fingerprint(entry.path)
    if fp is None or store.has(fp, model):
        return False
    backend = get_backend(model)
    vec = backend.embed_file(entry.path)
    store.put(fp, model, vec)
    return True


def build_index(
    entries: list[MusicEntry],
    model: str,
    store: EmbeddingStore,
    progress_cb: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> tuple[int, int, str | None]:
    """Embed every entry not yet cached for `model`. Deduplicates by content
    fingerprint (each unique audio embedded once).

    Returns (computed, errors, first_error). `first_error` is a short message from the
    FIRST failure (e.g. model failed to load) so callers can show *why* nothing indexed
    instead of just a count — the full traceback goes to the log.
    """
    # One entry per unique fingerprint → embed each once.
    seen: set = set()
    unique: list[MusicEntry] = []
    for e in entries:
        fp = store.fingerprint(e.path)
        if fp is None or fp in seen or store.has(fp, model):
            continue
        seen.add(fp)
        unique.append(e)
    computed = errors = short = 0
    first_error: str | None = None
    total = len(unique)
    for i, e in enumerate(unique, 1):
        if should_cancel and should_cancel():
            break
        try:
            if _embed_entry(e, model, store):
                computed += 1
        except AudioTooShort as exc:
            # A jingle or an FX sample, not a track: nothing to index, and
            # nothing wrong either. Noted, not counted as a failure.
            short += 1
            logger.info("🧠 Too short to embed (%s): %s\n"
                        "reason: %s", model, e.path.name, exc)
        except Exception as exc:
            errors += 1
            if first_error is None:
                first_error = f"{type(exc).__name__}: {exc}"
                logger.error("🧠 Embedding failed (%s) on %s\n%s",
                             model, e.path, traceback.format_exc())
            else:
                # Subsequent failures: short one-liner so every culprit is findable
                # in the log without dumping a full traceback per file.
                logger.warning("🧠 Skipped (%s): %s\n%s",
                               model, e.path.name, f"{type(exc).__name__}: {exc}")
        if progress_cb and (i == 1 or i % 10 == 0 or i == total):
            progress_cb(i, total, e.path.name)
        if i % 50 == 0:
            store.save()
    store.save()
    if short:
        logger.info("🧠 Index run finished (%s)\n"
                    "computed: %d\n"
                    "too short to embed: %d\n"
                    "errors: %d", model, computed, short, errors)
    return computed, errors, first_error


# ── similarity / search ──────────────────────────────────────────────────────────
def _cosine(a, b) -> float:
    import numpy as np
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def embedding_similar(
    source: MusicEntry,
    entries: list[MusicEntry],
    store: EmbeddingStore,
    model: str,
    n: int = 100,
    same_dance: bool = True,
) -> list[tuple[float, MusicEntry]]:
    """Rank `entries` by deep-embedding cosine to `source`.

    Uses cached embeddings; the source is embedded live if it isn't cached yet.
    Entries without a cached embedding are skipped (build the index first). Returns
    (similarity 0..1, entry) best-first, excluding the source and Christmas songs.
    """
    import numpy as np
    src_fp = store.fingerprint(source.path)
    src_vec = store.get_by_fp(src_fp, model) if src_fp else None
    if src_vec is None:
        src_vec = (_embed_entry_live(source, model, store))
    if src_vec is None:
        return []
    cands: list[tuple[MusicEntry, list[float]]] = []
    for e in entries:
        if e is source or e.is_xmas:
            continue
        if same_dance and source.dance and e.dance != source.dance:
            continue
        fp = store.fingerprint(e.path)
        vec = store.get_by_fp(fp, model) if fp else None
        if vec is None:
            continue
        if fp == src_fp:
            continue                         # same audio as the source
        cands.append((e, vec))
    if not cands:
        return []

    # Pool-relative standardization (z-score each dimension across the candidate pool
    # + source) BEFORE the cosine. Deep-embedding vectors — OpenL3 especially — live in
    # a narrow cone: a strong shared "music" direction dominates every track, so RAW
    # cosines bunch at ~0.9+ and everything shows ~100%. Centering + scaling per dim
    # removes that common bias and amplifies the within-pool differences that actually
    # separate tracks. Same principle as planner.similarity._pool_similarity for the librosa vector.
    src = np.asarray(src_vec, dtype=float)
    M = np.asarray([v for _, v in cands], dtype=float)
    if len(cands) >= 4 and M.shape[1] == src.shape[0]:
        stack = np.vstack([M, src[None, :]])
        mu = stack.mean(axis=0)
        sd = stack.std(axis=0)
        sd[sd < 1e-9] = 1.0
        Mz = (M - mu) / sd
        sz = (src - mu) / sd
        sn = float(np.linalg.norm(sz))
        rn = np.linalg.norm(Mz, axis=1)
        denom = sn * rn
        cos = np.divide(Mz @ sz, denom, out=np.zeros(len(cands)), where=denom > 0)
    else:
        # Tiny pool → standardization is unstable; fall back to plain cosine.
        cos = np.array([_cosine(src_vec, v) for _, v in cands], dtype=float)
    sims = (cos + 1.0) / 2.0
    out = [(float(sims[i]), cands[i][0]) for i in range(len(cands))]
    out.sort(key=lambda x: x[0], reverse=True)
    return out[:n]


def _embed_entry_live(entry: MusicEntry, model: str, store: EmbeddingStore) -> list[float] | None:
    """Embed (and cache) a single entry right now, returning its vector."""
    fp = store.fingerprint(entry.path)
    if fp is None:
        return None
    backend = get_backend(model)
    vec = backend.embed_file(entry.path)
    store.put(fp, model, vec)
    store.save()
    return vec
