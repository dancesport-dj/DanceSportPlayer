"""🔭 A red title whose file is gone: which files of the library are that song?

Equal file names on another drive letter are found by themselves (see
`resolve_file`). What is left is the file that was renamed ("Song_cut.mp3") or
re-encoded: no path in common, only the title. This looks for it by the cleaned
title (`song_title_key`), the way the duplicate drop does.
"""

from collections.abc import Iterable
from pathlib import Path

from planner.music.parsing import song_title_key
from planner.music.paths import is_foreign_network

LIMIT = 50
# A title this short is contained in far too many others to say anything.
_MIN_CONTAINED = 5


def _same_dance(a: str | None, b: str | None) -> bool:
    """A known dance on both sides must agree; 'Candela' the Cha Cha is not the Rumba."""
    return not a or not b or a.upper() == b.upper()


def _rank(mine: str, other: str) -> int | None:
    """0: the same title, 1: one holds the other as whole words ('Friends and
    Lovers' in 'Friends and Lovers Cut Version'), None: not the same song."""
    if mine == other:
        return 0
    short, long_ = sorted((mine, other), key=len)
    if len(short) >= _MIN_CONTAINED and f" {short} " in f" {long_} ":
        return 1
    return None


def same_song_files(path, dance: str | None, entries: Iterable,
                    skip: Iterable = ()) -> list:
    """The `entries` whose file exists and holds the song `path` names: the same
    title first, a longer or shorter version of it after. Files in `skip` (the ones
    the list holds already) and the missing path itself are left out."""
    mine = song_title_key(str(path))
    if not mine:
        return []
    own = str(path).lower()
    left_out = {str(p).lower() for p in skip}
    found = []
    for e in entries:
        p = getattr(e, "path", None)
        if not p or str(p).lower() in left_out or str(p).lower() == own:
            continue
        if not _same_dance(dance, getattr(e, "dance", None)):
            continue
        rank = _rank(mine, song_title_key(str(p)))
        if rank is not None and Path(p).is_file():
            found.append((rank, str(p).lower(), e))
    found.sort(key=lambda t: t[:2])
    return [e for _rank_, _p, e in found[:LIMIT]]


def folder_matches(path, exts: tuple[str, ...]) -> list[Path]:
    """The audio files (suffix in `exts`) lying in the folder `path` was in that
    hold its song, best match first. The library only knows what its last scan
    saw: a file renamed in place ("Song_cut.mp3" → "Song.mp3") is not in it yet,
    but it lies right where the red title did. The missing file itself is left
    out. Names only, no tags read: the caller turns the few hits into entries."""
    mine = song_title_key(str(path))
    if not mine or is_foreign_network(path):
        return []          # someone else's share is never listed (7.A)
    own = str(path).lower()
    found = []
    try:
        for p in Path(path).parent.iterdir():
            if (p.suffix.lower() not in exts or str(p).lower() == own
                    or not p.is_file()):
                continue
            rank = _rank(mine, song_title_key(str(p)))
            if rank is not None:
                found.append((rank, str(p).lower(), p))
    except OSError:
        return []          # the folder is gone, or on a drive that is not there
    found.sort(key=lambda t: t[:2])
    return [p for _rank_, _s, p in found[:LIMIT]]
