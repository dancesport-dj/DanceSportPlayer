"""Which library files are one song filed under different names.

The strict no-repeat knows a song by its full title and by the last dash part
(`song_use_keys`). A "Title - Artist" file ("01 Be my love - Werner Tauber") and the
same song as "01 - Be My Love - SF 30" share neither, so a pick could draw both. The
duplicate finder's wider keys do pair them, but also tie every track of one artist
together, which is right for a list a person reads and wrong for a pool.

This links file A to file B when one of A's EXTRA keys (a dash part the use keys
leave out) is a use key of B, in a dance that does not rule it out, and the key names
one song rather than an artist or a tag. Two tests, both on ALL the files that carry
the key, as a use key or as an extra one:

- one budget: at most `MAX_FILES` of them. An artist with five tracks and a title
  tag seen on three more each passed a gate of their own once.
- one song: the words the key leaves over in those files' full titles are the same
  in every file that has any. 'Charade' in 'Charade - Matt Monro' and in 'Matt Monro
  - Charade' leaves 'matt monro' both times; 'matt monro' in 'On Other Words - Matt
  Monro' and in 'Matt Monro - Honey On The Vine' leaves two different songs.

The result has the shape of `chroma_twins.twin_paths`, so the suggester can merge
the two. The keys of 58k file names take seconds once per process (`_keys` is cached
by file name); the link pass over them takes a fraction of a second.
"""
import logging
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from planner.music.parsing import song_use_and_extra_keys

log = logging.getLogger("dancesport.title_twins")

MAX_FILES = 6


@lru_cache(maxsize=300_000)
def _keys(name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    use, extra = song_use_and_extra_keys(name)
    return tuple(use), tuple(extra)


def title_twins(entries) -> dict[str, frozenset[str]]:
    """{path: the other paths that are the same song} for every entry that has one."""
    rows = [(str(e.path), Path(str(e.path)).name, getattr(e, "dance", None) or None)
            for e in entries if getattr(e, "path", None) is not None]
    keys = [_keys(name) for _p, name, _d in rows]
    holders: dict[str, list[int]] = defaultdict(list)
    extra_holders: dict[str, list[int]] = defaultdict(list)
    for i, (use, extra) in enumerate(keys):
        for k in use:
            holders[k].append(i)
        for k in extra:
            extra_holders[k].append(i)
    links: dict[int, set[int]] = defaultdict(set)
    for k, tied in extra_holders.items():
        held = holders.get(k)
        if not held or len(held) + len(tied) > MAX_FILES:
            continue
        # The words k leaves over in each file's full title: one song has one set
        # (or none), an artist has a different title behind it in every file.
        key_words = set(k.split())
        left = {frozenset(set(keys[i][0][0].split()) - key_words)
                for i in {*held, *tied} if keys[i][0]} - {frozenset()}
        if len(left) > 1:
            continue
        for i in tied:
            for j in held:
                if j != i and (not rows[i][2] or not rows[j][2] or rows[i][2] == rows[j][2]):
                    links[i].add(j)
                    links[j].add(i)
    out = {rows[i][0]: frozenset(rows[j][0] for j in js) for i, js in links.items()}
    log.info("🎵 Title twins\nfiles with a twin: %d", len(out))
    return out
