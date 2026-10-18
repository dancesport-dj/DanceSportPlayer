#!/usr/bin/env python3
"""Finding a track again when its playlist was written on another PC.

The same music folder is `F:\\my music` on one machine and
`C:\\Users\\…\\Documents\\datein\\my music` on the next, so every path an .m3u
or a saved deck carries is broken the moment it travels. 🧭 Fix paths hands
each broken reference to a `PathRemapper` built from the folders named in
Settings and keeps the first candidate that is really on disk — nothing is
guessed, a path is only rewritten to a file that exists.
"""

import logging
import re
import sys
from pathlib import Path

log = logging.getLogger("dancesport.paths")

# `F:\…`, `C:/…` — a volume of the machine that wrote the path, and never a
# folder to look for anywhere else.
_DRIVE_RE = re.compile(r"^[A-Za-z]:$")


def foreign_parts(path) -> tuple[str, ...]:
    """The folder names of a path, whichever OS wrote it.

    `Path` only ever knows the separator of the system it runs on: on macOS
    `Path("F:\\\\my music\\\\x.mp3")` is a single filename with backslashes in
    it, so there is nothing to re-root and nothing to match by name — and a
    Windows .m3u carries exactly that. Both separators are cut here instead,
    and the leading drive letter or UNC server is dropped: `F:` names a volume
    of the other machine, so the part worth matching starts behind it."""
    text = str(path).strip().strip('"')
    parts = [p for p in re.split(r"[\\/]+", text) if p not in ("", ".")]
    if parts and _DRIVE_RE.match(parts[0]):
        parts = parts[1:]
    return tuple(parts)


def foreign_name(path) -> str:
    """The filename of a path, whichever OS wrote it (see `foreign_parts`)."""
    parts = foreign_parts(path)
    return parts[-1] if parts else ""


def home_search_roots() -> list[Path]:
    """Folders to fall back on when no search folder is configured yet.

    Only away from Windows, and that is the whole point: the `C:`/`F:` in a
    carried-over playlist name drives of Marcel's PC. Windows has them, so the
    paths are either right or genuinely gone; a Mac has neither, and a fresh
    install there has no Referenzpfad and no search folders either — nothing to
    try at all. The user's home folder is the one place that is always present
    and always the right neighbourhood.

    Marcel's Mac keeps the library at `/Users/<user>/Music/my music`, which is
    where `~/Music` lands: a German Finder shows that folder as "Musik", but
    its real name on disk stays "Music" (that is what the `.localized` marker
    does). They go LAST, so anything configured still wins."""
    if sys.platform == "win32":
        return []
    home = Path.home()
    return [home, home / "Music"]


def parse_remap_paths(value) -> list[str]:
    """The 'search folders' setting → a clean list, order kept.

    Takes what the settings file holds (a list) as well as what the text box
    in the dialog produces (one folder per line), so neither side has to know
    about the other's shape."""
    if isinstance(value, str):
        items = value.splitlines()
    elif isinstance(value, (list, tuple)):
        items = [str(v) for v in value]
    else:
        items = []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        p = item.strip().strip('"')
        key = p.lower().rstrip("\\/")
        if p and key not in seen:
            seen.add(key)
            out.append(p)
    return out


class PathRemapper:
    """Re-roots a foreign track path under the folders this PC keeps music in.

    The roots are tried in order and the first hit wins, so the Referenzpfad
    (root #1) keeps deciding what it decided before the extra search folders
    existed.
    """

    def __init__(self, roots):
        self.roots = [Path(r) for r in parse_remap_paths(list(roots or []))]

    def __bool__(self) -> bool:
        return bool(self.roots)

    def remap(self, broken) -> Path | None:
        """The real file behind `broken`, or None when no root holds it."""
        for root in self.roots:
            hit = self._under(broken, root)
            if hit is not None:
                return hit
        return None

    @staticmethod
    def _under(broken, root: Path) -> Path | None:
        """`broken` re-rooted under one folder, if that lands on a real file.

        Two ways to cut the foreign path, both keeping the filename:
        anchoring on the root's own leaf name (`…\\my music\\tanzcds\\SB\\x.mp3`
        under a root named `tanzcds` → `<root>\\SB\\x.mp3`), and otherwise the
        tail of the path, longest first — the most specific folder chain that
        is actually there wins.

        The cut is made by `foreign_parts`, not by `Path`: on macOS a Windows
        path is one long filename to `Path`, and there would be no folders to
        line up at all."""
        parts = foreign_parts(broken)
        cands: list[Path] = []
        anchor = root.name.lower()
        idx = next((i for i in range(len(parts) - 1, -1, -1)
                    if parts[i].lower() == anchor), None)
        if idx is not None and idx + 1 < len(parts):
            cands.append(root.joinpath(*parts[idx + 1:]))
        # From the whole chain down to the bare filename. The whole chain counts
        # because `foreign_parts` has already dropped the drive letter: what is
        # left of `F:\my music\…` is `my music\…`, and `~/Music/my music/…` is
        # exactly where it lands on the Mac.
        for n in range(len(parts), 0, -1):
            cands.append(root.joinpath(*parts[-n:]))
        seen: set[str] = set()
        for cand in cands:
            key = str(cand).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                if cand.is_file():
                    return cand
            except OSError:
                continue
        return None
