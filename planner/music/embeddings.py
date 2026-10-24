#!/usr/bin/env python3
"""
planner/music/embeddings.py – optional deep-audio-embedding backends for the dancesport planner.

MERT is OPTIONAL and lazily imported, so the app runs fine without the heavy ML
dependencies installed:

  • MERT – m-a-p's self-supervised music model (MERT-v1-95M, 768-d). Perceptual
    "sounds-alike" similarity, used as an alternative ranking to the librosa
    timbre+rhythm vector. Runs on torch, which the FULL build already carries
    for Demucs; the weights (~380 MB) download on first use.
    Install:  pip install torch transformers

Embeddings are cached in the SAME SQLite DB as the librosa features (one extra
`embeddings(fp, model, vec)` table), keyed by content fingerprint so byte-identical
copies share a single vector — exactly like AudioCache. Read-only on the audio files
(load only), consistent with the rest of the pipeline.
"""

import contextlib
import importlib.util
import io
import logging
import traceback
from array import array
from pathlib import Path
from collections.abc import Callable

logger = logging.getLogger(__name__)

import planner.music.db
from planner.models import MusicEntry
from planner.music.analysis import quiet_native_stderr
from planner.music.db import _db


class AudioTooShort(ValueError):
    """There is less audio in the file than the descriptor needs.

    A transition swish or a spoken jingle in the samples folder is not a track
    and never will be one — indexing has nothing to do here, so this is a skip,
    not a failure, and it must not colour the error count of a whole run.
    """


# Model identifiers used as the `model` column / dict key.
MODEL_MERT = "mert"
MODEL_CHROMA = "chroma2dftm"         # librosa-only chroma cover/remix matcher (melody, not timbre)
# Every model the app still computes and reads. 🧹 Database maintenance drops
# the vectors of any other (OpenL3, the CLAP audio tower), so a new model must
# be added here.
MODELS = (MODEL_MERT, MODEL_CHROMA)

_MERT_REPO = "m-a-p/MERT-v1-95M"
# The model runs code from its own repo (trust_remote_code). Pinned, so a later
# push to that repo is never fetched and run unseen.
_MERT_REVISION = "12af15fef9d0ac838c3f475bfbbf26d2060dd4f5"
# What from_pretrained reads of that revision, the ~380 MB weights last:
# fetched one by one before the first title, so the dialog shows the download.
_MERT_FILES = ("config.json", "configuration_MERT.py", "modeling_MERT.py",
               "preprocessor_config.json", "pytorch_model.bin")
_MERT_SR = 24000
# ~3 s a title on a CPU; the full 60 s would double the hours a 50k-title
# library takes to index, and 30 s is already deep into the music.
_MERT_SECONDS = 30.0
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
        import truststore  # pyright: ignore[reportMissingImports]
        truststore.inject_into_ssl()
        logger.info("🔐 Using OS certificate store for model downloads (truststore)")
    except Exception as exc:
        logger.debug("truststore not active (%s) — using default certifi bundle", exc)


class _HubRequestFilter(logging.Filter):
    """httpx logs every request at INFO; the model's HEAD probes (a 404 for
    each file the repo lacks) are no news to the user. Other requests stay."""

    def filter(self, record):
        msg = record.getMessage()
        return "huggingface.co" not in msg and "hf.co" not in msg


_HUB_REQUESTS = _HubRequestFilter()


def _quiet_model_chatter() -> None:
    """The hub's requests out of the log, and of the hub and transformers
    only their errors: no hint to log in, no deprecation notes. After their
    import, which sets their loggers' level once."""
    logging.getLogger("httpx").addFilter(_HUB_REQUESTS)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("transformers").setLevel(logging.ERROR)


def _byte_bar(cb: Callable[[int, int], None]):
    """A tqdm class for hf_hub_download that draws nothing and hands
    `cb(done, total)` the bytes of all the files it was given so far."""
    from tqdm.auto import tqdm  # pyright: ignore[reportMissingModuleSource]
    bars = []

    class _Bar(tqdm):
        def __init__(self, *args, **kwargs):
            kwargs["disable"] = True        # keeps n and total, draws nothing
            super().__init__(*args, **kwargs)
            self.transfer = 0
            bars.append(self)
            self._report()                  # the file's size, before a byte

        def _report(self):
            cb(sum(min(max(b.n, b.transfer), b.total or b.n) for b in bars),
               sum(b.total or 0 for b in bars))

        def update(self, n=1):
            self.n += n
            self._report()

        # With these, a Xet download sends its network bytes here, not to a
        # bar of its own on the console. They run ahead of the bytes it
        # writes, which arrive in large flushes.
        def update_transfer(self, n=1):
            self.transfer += n
            self._report()

        def set_transfer_postfix_str(self, s="", refresh=True):
            pass

    return _Bar


# The decoders' stderr muting is shared with the analysis pass (planner.music.db): fd 2
# is process-wide, so all decodes on all threads must go through one lock.
_quiet_native_stderr = quiet_native_stderr


# ── availability probes (no heavy import) ────────────────────────────────────────
def mert_available() -> bool:
    return bool(importlib.util.find_spec("torch") and importlib.util.find_spec("transformers"))


def chroma_available() -> bool:
    # Chroma uses librosa only — the same dependency the core feature pipeline needs,
    # so it's available whenever audio analysis is.
    return bool(importlib.util.find_spec("librosa"))


def install_hint(model: str) -> str:
    if model == MODEL_CHROMA:
        return "Chroma cover-match needs librosa.  Install with:  pip install librosa"
    return "MERT not installed. Install with:  pip install torch transformers"


# ── embedding store (SQLite, shared DB) ──────────────────────────────────────────
class EmbeddingStore:
    """Content-addressed cache of deep embeddings in the shared normalized DB.

    Table `embeddings(fp, model, vec)` PRIMARY KEY (fp, model): one float32-packed
    vector per (content fingerprint, model). An in-memory mirror per model keeps
    ranking fast. Fingerprints are resolved through the passed AudioCache so they
    match the librosa feature dedup exactly.
    """

    def __init__(self, cache: planner.music.db.AudioCache):
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
        mirror is an expensive way to answer it: 53k embedding blobs unpacked into
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
class _MertBackend:
    """Lazy wrapper around the MERT music model (loaded once).

    Its 12 transformer layers each hear a different side of the music — the
    lower ones timbre and texture, the upper ones rhythm and harmony — so the
    vector is every layer's time average, averaged over the layers: one 768-d
    description of how the title sounds. Layer 0 is the convolutional front
    end, raw waveform features rather than music, and is left out.
    """

    def __init__(self):
        self._model = None
        self._proc = None

    def fetch(self, cb: Callable[[int, int], None] | None = None) -> None:
        """Download what the cache lacks of the model, `cb(done, total)` in
        bytes along the way. Nothing to do once it is there."""
        from huggingface_hub import hf_hub_download, try_to_load_from_cache  # pyright: ignore[reportMissingImports]
        missing = [f for f in _MERT_FILES if not isinstance(
            try_to_load_from_cache(_MERT_REPO, f, revision=_MERT_REVISION), str)]
        if not missing:
            return
        _enable_system_certs()
        _quiet_model_chatter()
        bar = _byte_bar(cb or (lambda done, total: None))
        for f in missing:
            hf_hub_download(_MERT_REPO, f, revision=_MERT_REVISION, tqdm_class=bar)

    def _ensure_model(self):
        if self._model is None or self._proc is None:
            _enable_system_certs()
            # optional, heavy import on first use
            import transformers  # pyright: ignore[reportMissingImports]
            from transformers import AutoModel, Wav2Vec2FeatureExtractor  # pyright: ignore[reportMissingImports]
            _quiet_model_chatter()
            transformers.utils.logging.disable_progress_bar()   # "Loading weights"
            self._proc = Wav2Vec2FeatureExtractor.from_pretrained(
                _MERT_REPO, revision=_MERT_REVISION, trust_remote_code=True)
            # The model's own code print()s that it lacks nnAudio, which it
            # needs only for a feature extractor never used here.
            with contextlib.redirect_stdout(io.StringIO()):
                self._model = AutoModel.from_pretrained(
                    _MERT_REPO, revision=_MERT_REVISION, trust_remote_code=True).eval()
        return self._model, self._proc

    def embed_file(self, path: Path) -> list[float]:
        import torch  # pyright: ignore[reportMissingImports]
        import librosa
        with _quiet_native_stderr():
            y, sr = librosa.load(str(path), sr=_MERT_SR, mono=True,
                                 offset=0.0, duration=_MERT_SECONDS)
        if y.size < sr:
            raise AudioTooShort("audio too short for MERT")
        model, proc = self._ensure_model()
        inputs = proc(y, sampling_rate=int(sr), return_tensors="pt")
        with torch.inference_mode():
            out = model(**inputs, output_hidden_states=True)
        layers = torch.stack(tuple(out.hidden_states[1:]))   # (12, 1, frames, 768)
        vec = layers.mean(dim=2).mean(dim=0).reshape(-1)
        norm = float(torch.linalg.norm(vec))
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

    def fetch(self, cb: Callable[[int, int], None] | None = None) -> None:
        """librosa only: no model to download."""

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
_mert = _MertBackend()
_chroma = _ChromaBackend()


def get_backend(model: str):
    if model == MODEL_CHROMA:
        return _chroma
    return _mert


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
    download_cb: Callable[[int, int], None] | None = None,
) -> tuple[int, int, str | None]:
    """Embed every entry not yet cached for `model`. Deduplicates by content
    fingerprint (each unique audio embedded once). A model the cache lacks is
    downloaded first, its bytes reported to `download_cb(done, total)`.

    Returns (computed, errors, first_error). `first_error` is a short message from the
    FIRST failure (e.g. model failed to load) so callers can show *why* nothing indexed
    instead of just a count — the full traceback goes to the log.
    """
    # One entry per unique fingerprint → embed each once. Which ones are done
    # needs only the keys, not every vector unpacked (EmbeddingStore.fps).
    seen: set = set()
    unique: list[MusicEntry] = []
    indexed = store.fps(model)
    for e in entries:
        fp = store.fingerprint(e.path)
        if fp is None or fp in seen or fp in indexed:
            continue
        seen.add(fp)
        unique.append(e)
    if unique:
        try:
            get_backend(model).fetch(download_cb)
        except Exception as exc:
            # Without the model no title can be embedded: one failure for
            # the run, not a fresh download attempt per title.
            logger.error("🧠 Model download failed (%s)\n%s", model, traceback.format_exc())
            return 0, len(unique), f"{type(exc).__name__}: {exc}"
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
    # + source) BEFORE the cosine. Deep-embedding vectors — MERT especially — live in
    # a narrow cone: a strong shared "music" direction dominates every track, so RAW
    # cosines bunch at ~0.9+ and everything shows ~100%. Centering + scaling per dim
    # removes that common bias and amplifies the within-pool differences that actually
    # separate tracks. Same principle as planner.music.similarity._pool_similarity for the librosa vector.
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
