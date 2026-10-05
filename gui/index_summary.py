"""The 🧱 coverage lines: which library is indexed for which model.

Shown in the library status block and in ⚙ Settings. Built from the loaded
libraries, the audio cache and the embedding store — no window, no Qt.
"""
import planner.db
from planner import i18n


def index_summary(cache, store, favorites, repository) -> dict:
    """Per-library coverage for each model: 'which is indexed for which model'.

    Favorites counts come from the loaded library (I/O-free in-memory). The
    Repository line uses the loaded global library when present, otherwise falls
    back to DB-only coverage (`planner.global_coverage`) so it still shows even
    before the repo is loaded into memory.
    """
    from planner import embeddings as ae
    libro_parts, ol3_parts, chroma_parts = [], [], []
    loud_parts, sil_parts, pd_parts, afp_parts = [], [], [], []
    # 🔗 The audio fingerprints have no in-memory mirror — one query here,
    # shared by both libraries, instead of one per coverage call.
    afps = cache.audio_fp_keys() if cache is not None else set()
    # Whether a build would still find work in the FAVORITES library — the
    # only scope the panel's 🧱 shortcut offers to fix. A model whose backend
    # isn't installed is not a gap: no build can close it.
    gaps: list[bool] = []

    def note_gap(label, done, total, buildable=True):
        if label == "Favorites" and buildable and done < total:
            gaps.append(True)

    def add_loaded(label, lib):
        # `label` stays English for note_gap's scope test; `shown` is the
        # half that reaches the screen.
        shown = i18n.t(label)
        n = len(lib.entries)
        libro = sum(1 for e in lib.entries if e.features is not None)
        libro_parts.append(f"{shown} {libro:,}/{n:,}")
        note_gap(label, libro, n)
        if cache is not None:
            # ffmpeg-measured caches: loudness and silences cover every
            # track, PD highlights only the Paso Dobles — counting those
            # against the whole library would read as permanently unfinished.
            cov = cache.coverage_counts([e.path for e in lib.entries], afps)
            afp_parts.append(f"{shown} {cov['audiofp']:,}/{n:,}")
            loud_parts.append(f"{shown} {cov['loudness']:,}/{n:,}")
            sil_parts.append(f"{shown} {cov['silences']:,}/{n:,}")
            note_gap(label, cov["audiofp"], n)
            note_gap(label, cov["loudness"], n)
            note_gap(label, cov["silences"], n)
            pds = [e.path for e in lib.entries if e.dance == "PD"]
            if pds:
                npd = cache.coverage_counts(pds, afps)["pd"]
                pd_parts.append(f"{shown} {npd:,}/{len(pds):,}")
                note_gap(label, npd, len(pds))
        if store and cache is not None:
            # The fingerprint SETS, not the vectors: asking the store for
            # each entry's embedding unpacked every model's whole mirror —
            # five seconds of startup to print three counts.
            have_ol3 = store.fps(ae.MODEL_OPENL3)
            have_chroma = store.fps(ae.MODEL_CHROMA)
            ol3 = chroma = 0
            for e in lib.entries:
                fp = cache.known_fingerprint(e.path)
                if not fp:
                    continue
                if fp in have_ol3:
                    ol3 += 1
                if fp in have_chroma:
                    chroma += 1
            ol3_parts.append(f"{shown} {ol3:,}/{n:,}")
            chroma_parts.append(f"{shown} {chroma:,}/{n:,}")
            note_gap(label, ol3, n, ae.openl3_available())
            note_gap(label, chroma, n, ae.chroma_available())

    if favorites and favorites.entries:
        add_loaded("Favorites", favorites)
    # Repository: loaded library if present, else DB-only coverage.
    if repository and repository.entries:
        add_loaded("Repository", repository)
    elif planner.db.global_index_count() > 0:
        cov = planner.db.global_coverage(
            [ae.MODEL_OPENL3, ae.MODEL_CHROMA])
        tot = cov["total"]
        libro_parts.append(f"Repository {cov['librosa']:,}/{tot:,}")
        if store:
            ol3_parts.append(
                f"Repository {cov['embeddings'].get(ae.MODEL_OPENL3, 0):,}/{tot:,}")
            chroma_parts.append(
                f"Repository {cov['embeddings'].get(ae.MODEL_CHROMA, 0):,}/{tot:,}")

    join = lambda parts: " · ".join(parts) if parts else "—"
    return {
        "audiofp": join(afp_parts),
        "librosa": join(libro_parts),
        "openl3": join(ol3_parts) if store else i18n.t("(OpenL3 not available)"),
        "chroma": join(chroma_parts) if store else i18n.t("(chroma not available)"),
        "loudness": join(loud_parts),
        "silences": join(sil_parts),
        "pd": join(pd_parts) if pd_parts else i18n.t("no Paso Doble in the library"),
        "favorites_gap": bool(gaps),
    }
