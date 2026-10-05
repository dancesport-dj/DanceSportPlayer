"""Reading a playlist's text without losing a character of it.

The tournament folder holds the app's own UTF-8 playlists (with or without a
BOM) next to cp1252 ones written by the old Java app and by Windows tools, and
the odd UTF-16 export. Each is decoded strictly, in that order of likelihood.
A file that is none of them raises: read with the errors thrown away it loses
every umlaut, and a title with an umlaut in its path no longer matches the
library — so it is counted as never played, or re-imported as missing.
"""
import os
import shutil
from pathlib import Path

from planner.planned import path_key

_BOMS = ((b"\xef\xbb\xbf", "utf-8-sig"),
         (b"\xff\xfe", "utf-16"),
         (b"\xfe\xff", "utf-16"))


class PlaylistEncodingError(ValueError):
    """A playlist that is neither UTF-8 nor cp1252 (nor UTF-16 with a BOM)."""


def read_playlist_text(path) -> tuple[str, str]:
    """The text of the playlist at `path` and the encoding it was read in —
    the one to write it back in. Raises PlaylistEncodingError."""
    raw = Path(path).read_bytes()
    for bom, encoding in _BOMS:
        if raw.startswith(bom):
            try:
                return raw.decode(encoding), encoding
            except UnicodeDecodeError as e:
                raise PlaylistEncodingError(
                    f"{Path(path).name}: starts like {encoding} but is not ({e})"
                ) from e
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise PlaylistEncodingError(
        f"{Path(path).name}: neither UTF-8 nor cp1252 — not read, so that no "
        "umlaut in it is lost")


def rerooted(path: Path, remapper) -> Path | None:
    """Where 🧭 Fix paths points `path` instead, or None to leave it.

    Covers broken references AND valid-but-off-root paths (normalised to the
    search folders); a path that is already canonical — the remap equals it,
    case aside — is left alone."""
    remap = remapper.remap(path)
    if remap is None or path_key(remap) == path_key(path):
        return None
    return remap


def rewrite_playlist_paths(m3u: Path, remapper) -> int:
    """Rewrite ONLY the broken track-path lines of an .m3u in place, re-rooting each
    under the search folders. Every comment / #EXTINF line and each line's terminator
    are preserved exactly. Returns the number of path lines changed.

    The file is written back in the encoding it was read in — about 500 of
    the tournament playlists are cp1252 — and the original is kept next to
    it as `<name>.bak`. A file that decodes as neither UTF-8 nor cp1252
    (PlaylistEncodingError), or a new path its encoding cannot hold
    (UnicodeEncodeError), raises before anything is written."""
    raw, encoding = read_playlist_text(m3u)
    lines = raw.splitlines(keepends=True)
    base = Path(m3u).parent
    changed = 0
    for i, ln in enumerate(lines):
        body = ln.rstrip("\r\n")
        stripped = body.strip()
        if not stripped or stripped.startswith("#"):
            continue
        p = Path(stripped)
        abs_p = p if p.is_absolute() else base / p
        remap = rerooted(abs_p, remapper)
        if remap is None:
            continue
        lines[i] = str(remap) + ln[len(body):]   # keep this line's terminator
        changed += 1
    if changed:
        data = "".join(lines).encode(encoding)
        m3u = Path(m3u)
        shutil.copy2(m3u, m3u.with_name(m3u.name + ".bak"))
        tmp = m3u.with_name(m3u.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, m3u)
    return changed
