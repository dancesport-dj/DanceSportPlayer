"""Which library files are one recording, by their stored Chromaprints.

The picker's no-repeat sets know a song by its file path and by the title in
its file name. A cut or re-encoded copy under another name ("La Cintura
(SB 50)cut.mp3" next to "La Cintura (SB 50).mp3", or a copy on another drive)
slips through both. This groups the files whose stored Chromaprints
`chroma_match.find_pairs` calls one recording, so a pick can rule out its twins.

Stored fingerprints only: nothing here reads an audio file or runs fpcalc.
Files without a Chromaprint (the index is built from the settings dialog or by
the duplicate check) have no twins.
"""
import logging
from pathlib import Path

from planner.music import chroma_match

log = logging.getLogger("dancesport.chroma")


def twin_paths(cache, paths) -> dict[str, frozenset[str]]:
    """{path: the other paths that are the same recording} for every path that
    has at least one twin. `cache` is the AudioCache; None gives {}."""
    if cache is None:
        return {}
    by_fp: dict[str, list[str]] = {}
    for p in paths:
        fp = cache.known_fingerprint(Path(p))
        if fp:
            by_fp.setdefault(fp, []).append(str(p))
    if len(by_fp) < 2:
        return {}
    tracks = {fp: w for fp, w in cache.all_chromas().items() if fp in by_fp}
    twins: dict[str, set[str]] = {}
    for fp_a, fp_b, _match in chroma_match.find_pairs(tracks):
        # find_pairs gives pairs, not groups: a three-way copy needs the union.
        group = set(by_fp[fp_a]) | set(by_fp[fp_b])
        group |= twins.get(by_fp[fp_a][0], set()) | twins.get(by_fp[fp_b][0], set())
        for p in group:
            twins[p] = group
    out = {p: frozenset(g - {p}) for p, g in twins.items() if len(g) > 1}
    log.info("🎼 Chroma twins\nfiles with a twin: %d", len(out))
    return out
