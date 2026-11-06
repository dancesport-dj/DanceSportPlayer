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

from planner.music.drives import on_other_drives

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


def search_roots(settings) -> list:
    """Where 🧭 Fix paths looks for a moved file, in order: the Referenzpfad,
    the extra search folders (Settings) and — away from Windows — the home
    folder (see `home_search_roots`)."""
    settings = settings or {}
    return [settings.get("reference_path") or "",
            *(settings.get("remap_paths") or []), *home_search_roots()]


def resolve_file(path, settings) -> Path | None:
    """The file behind a stored path on this PC — the one resolver decks,
    wishlists and 🎛 pads share: the path itself while it is there, else the
    same path on another local drive (the stick came back as G:), else the
    copy `search_roots` holds, else None. It only finds; the stored path is
    the caller's and stays as it was, so a stick that comes back under its
    old letter is used again."""
    if is_network_path(path):
        if is_own_share(path, settings) and _is_file(path):
            return Path(path)
        # Someone else's UNC line: no stat on it (see `is_local_file`).
        # Its folder names may still match a copy under the local search roots.
    elif _is_file(path):
        return Path(path)
    return FileFinder(search_roots(settings)).remap(path)


def _is_file(path) -> bool:
    try:
        return Path(path).is_file()
    except (OSError, ValueError):
        return False


def is_local_file(path) -> bool:
    """`is_file()` for a path that came out of someone else's playlist or pack.

    A `\\\\host\\share` or `//host/…` line, or a `scheme://` one, is refused
    before any filesystem call: Windows would open an SMB session for it (the
    user's NTLM hash goes to the host) and the calling thread hangs on a dead
    one. A library kept on a NAS is not affected, its entries never come
    through here."""
    if is_network_path(path):
        return False
    return _is_file(str(path).strip().strip('"'))


def is_network_path(path) -> bool:
    """A UNC (`//host/share`, either slash) path, or a `scheme://` one."""
    text = str(path).strip().strip('"')
    return text.startswith(("\\\\", "//")) or "://" in text


def _slashes(path) -> str:
    return str(path).strip().strip('"').replace("\\", "/").rstrip("/").lower()


def is_own_share(path, settings) -> bool:
    """True when a network `path` lies under a share the user configured themself:
    the library or global folder, the Referenzpfad or a search folder. A library kept
    on a NAS has to resolve; a UNC line from someone else's file does not."""
    settings = settings or {}
    roots = [settings.get("library_dir"), settings.get("global_dir"),
             settings.get("reference_path"), *(settings.get("remap_paths") or [])]
    target = _slashes(path)
    for root in roots:
        base = _slashes(root) if root else ""
        if base.startswith("//") and (target == base or target.startswith(base + "/")):
            return True
    return False


_own_shares: dict = {}


def set_own_shares(settings) -> None:
    """Remember which network folders the user configured themself, for the
    callers that have no settings at hand (the audio probes, the playlist
    reader). Called wherever the settings are loaded or replaced."""
    global _own_shares
    settings = settings or {}
    _own_shares = {key: settings.get(key) for key in
                   ("library_dir", "global_dir", "reference_path", "remap_paths")}


def is_foreign_network(path) -> bool:
    """A network path that is NOT under a share the user configured."""
    return is_network_path(path) and not is_own_share(path, _own_shares)


def is_probeable(path) -> bool:
    """True when `path` is a real file that is safe to stat and to hand to
    ffmpeg/fpcalc: never a foreign UNC or URL line (see `is_local_file`), but
    a library on a configured NAS share is."""
    if is_foreign_network(path):
        return False
    return _is_file(str(path).strip().strip('"'))


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
        tails: list[tuple[str, ...]] = []
        anchor = root.name.lower()
        idx = next((i for i in range(len(parts) - 1, -1, -1)
                    if parts[i].lower() == anchor), None)
        if idx is not None and idx + 1 < len(parts):
            tails.append(parts[idx + 1:])
        # From the whole chain down to the bare filename. The whole chain counts
        # because `foreign_parts` has already dropped the drive letter: what is
        # left of `F:\my music\…` is `my music\…`, and `~/Music/my music/…` is
        # exactly where it lands on the Mac.
        tails.extend(parts[-n:] for n in range(len(parts), 0, -1))
        # A '..' could climb out of the root, and a part like 'D:' re-roots a
        # Windows join onto that drive: such a tail is never a candidate.
        cands = [root.joinpath(*tail) for tail in tails
                 if ".." not in tail and not any(":" in part for part in tail)]
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


class FileFinder(PathRemapper):
    """`PathRemapper` looking everywhere playback looks: first the same path on
    another local drive, then the roots. An import asks this one, so a row holds
    the file that will play. 🧭 Fix paths keeps the plain remapper: it rewrites a
    list for good, and a stick's new letter is not worth that."""

    def __bool__(self) -> bool:
        return True     # the drives can answer without a single root

    def remap(self, broken) -> Path | None:
        # Only now the drive list: a row fill asks this for every title.
        for cand in on_other_drives(broken):
            if _is_file(cand):
                return Path(cand)
        return super().remap(broken)
