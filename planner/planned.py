"""Whether a track is already planned in an open deck.

The open decks are indexed as a set of paths and a set of content
fingerprints (`_deck_dedup_index`); a track counts as planned when its path
is in the one or its fingerprint in the other — so a renamed or relocated
copy of a planned recording counts too. Windows paths are not
case-sensitive, so every path is compared as `path_key` has it.
"""
import logging
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger("dancesport.planner")


def path_key(path) -> str:
    """A path as the planned index holds it: normalised and lower-cased."""
    return str(Path(path)).lower()


def is_planned(path, paths: set, fps: set,
               fingerprint: Callable | None = None) -> bool:
    """Whether the track at `path` is in the index (`paths`, `fps`).

    `fingerprint(path)` is asked only when the path alone does not match and
    there are fingerprints to match against — it may hash the file, so each
    caller passes the lookup it can afford. One that fails counts as no
    match."""
    if not path:
        return False
    if path_key(path) in paths:
        return True
    if not fps or fingerprint is None:
        return False
    try:
        fp = fingerprint(Path(path))
    except Exception as exc:
        log.debug("🔑 Fingerprinting failed for %s: %s", path, exc)
        return False
    return bool(fp and fp in fps)
