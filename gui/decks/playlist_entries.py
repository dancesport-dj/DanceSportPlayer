"""📄 A playlist's lines as library entries — a dropped .m3u, a party list.

Split off the generator and the drop handler, which each parsed the lines
themselves: reading which files a list names, and turning those into the
library's own entries, needs the library and a remapper, not the window. So
both are plain functions here, tested without one; the window keeps reading
the file and saying so when it can't.
"""
from pathlib import Path

from PySide6.QtCore import QUrl


def playlist_paths(lines: list[str]) -> list[Path]:
    """The track paths a playlist's lines name, in file order: comments and
    blank lines skipped, a file: URL read as its local path, quotes dropped."""
    out: list[Path] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.lower().startswith("file:"):
            u = QUrl(s)
            if u.isLocalFile():
                s = u.toLocalFile()
        out.append(Path(s.strip('"')))
    return out


def resolve_playlist_entries(paths: list[Path], lib, cache, remapper=None,
                             progress_cb=None) -> list:
    """Each path as the library's entry for it (built as an external entry when
    the library has none). Order preserved, duplicates dropped.

    A list carried over from another machine — or written before the library
    moved — names the library at ITS drive, and none of those lines resolve
    here; `remapper` re-roots them under the search folders (Settings), or a
    party list fills the panel with references to files that are not there.

    `progress_cb(done, total, detail)` is called every 25 tracks: a long list
    reads the tags of everything that isn't in the library, which takes
    seconds, and a window that simply stops looks broken."""
    by_path = {str(e.path): e for e in lib.entries}
    by_lower = {k.lower(): v for k, v in by_path.items()}
    total = len(paths)
    out, seen = [], set()
    for i, path in enumerate(paths):
        if progress_cb is not None and not i % 25:
            progress_cb(i, total, f"{len(out)} tracks")
        tp = str(path)
        ent = by_path.get(tp) or by_lower.get(tp.lower())
        if ent is None and remapper:
            hit = remapper.remap(Path(tp))
            if hit is not None:
                tp = str(hit)
                ent = by_path.get(tp) or by_lower.get(tp.lower())
        if ent is None:
            try:
                ent = lib.make_external_entry(Path(tp), cache)
            except Exception:
                ent = None
        if ent is not None and str(ent.path) not in seen:
            seen.add(str(ent.path))
            out.append(ent)
    return out
