"""Sanity test: do the timbre methods return same-dance, sound-alike tracks for
"Senorita (SB 50)" when matched against the tanzcds library?

Mirrors the GUI "Similar to…" dialog: same-dance pool, top-N best matches.
Compares the two methods side by side:
  • librosa     – pool-z-scored cosine over the (timbre-only) summary vector
  • gaussian_kl – Mandel-Ellis single Gaussian compared by symmetric KL

Run:  py test_senorita_similarity.py
Audio analysis is cached in audio_features.db, so the first run is slow
(~minutes for the samba pool) and later runs are instant.
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import dancesport_planner as P

from planner.parsing import _detect_dance

# The exact file from the user's screenshots (falls back to the C: mirror).
ANCHOR_CANDIDATES = [
    Path(r"F:\my music\tanzcds\lateincd\vlt\02 Senorita (SB 50).mp3"),
    Path.home() / "Documents" / "datein" / "my music" / "tanzcds" / "lateincd"
    / "vlt" / "02 Senorita (SB 50).mp3",
]
BASE_CANDIDATES = [
    Path(r"F:\my music\tanzcds"),
    Path.home() / "Documents" / "datein" / "my music" / "tanzcds",
]
TOP_N = 15


def _first_existing(paths):
    return next((p for p in paths if p.exists()), None)


def _build_entry(path: Path) -> P.MusicEntry:
    """Lightweight MusicEntry: dance from the filename (enough for this timbre test)."""
    return P.MusicEntry(path=path, title=path.stem, dance=_detect_dance(path.name))


def main():
    anchor_path = _first_existing(ANCHOR_CANDIDATES)
    base = _first_existing(BASE_CANDIDATES)
    if anchor_path is None or base is None:
        print("❌ Could not find the Senorita file or the tanzcds folder.")
        return 1
    print(f"🎵 Anchor : {anchor_path}")
    print(f"📂 Library: {base}")

    if not P.HAS_LIBROSA:
        print("❌ librosa is not installed — cannot run audio analysis.")
        return 1

    cache = P.AudioCache()

    anchor = _build_entry(anchor_path)
    anchor_dance = anchor.dance
    print(f"💃 Detected dance for anchor: {anchor_dance}")

    # Same-dance pool (like the GUI's 'same_dance=True' default = the Java genre gate).
    pool = []
    for p in base.rglob("*.mp3"):
        if p == anchor_path:
            continue
        e = _build_entry(p)
        if anchor_dance and e.dance != anchor_dance:
            continue
        pool.append(e)
    print(f"🔍 Same-dance candidates: {len(pool)}")

    # Analyze (cached). analyze_missing prompts on a cold run; auto-accept here.
    import builtins
    _orig_input = builtins.input
    builtins.input = lambda *a, **k: "y"
    try:
        cache.analyze_missing([anchor] + pool)
    finally:
        builtins.input = _orig_input

    anchor.features = cache.get(anchor.path)
    if anchor.features is None:
        print("❌ Anchor could not be analyzed (too short?).")
        return 1
    for e in pool:
        e.features = cache.get(e.path)
    analyzed = [e for e in pool if e.features is not None]
    print(f"✅ Analyzed candidates: {len(analyzed)}\n")

    lib = P.MusicLibrary.__new__(P.MusicLibrary)
    lib.entries = [anchor] + analyzed

    def show(method: str):
        res = lib.similar_tracks(anchor, n=TOP_N, same_dance=True,
                                 min_display=0.0, method=method)
        print(f"=== Top {TOP_N} — method '{method}' ===")
        for rank, (sim, e) in enumerate(res, 1):
            print(f"  {rank:2d}. {sim*100:6.2f}%  {e.title[:60]}")
        print()

    show("librosa")
    show("gaussian_kl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
