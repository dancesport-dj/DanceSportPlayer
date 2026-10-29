"""The one free "Custom" field of a track, and the MP3 frame that can fill it.

The DJ types what they like into it in the 🏷 editor; that is kept in the app
like the classes (planner.music.tag_edits). It can also be mapped to a frame the
files already carry — UltraMixer's TXXX "ultramixer_last_played", a MediaMonkey
comment, the grouping — and then the frame fills it: what the scan reads from
there is the file's value, and a value typed in the app wins over it.

ID3v1 has no frames to map, only a comment; V1 names that one. It is read
only: 28 Latin-1 characters, and where many older files keep their classes.

The mapping is one per database, in app_meta, as "TXXX:description" or a bare
frame id. The scan cache keeps the mapped frame's value per file (scan_meta
`custom`), so a new mapping clears that column: NULL there is "not read under
this mapping yet", and _make_entry reads it on the next look.
"""
from pathlib import Path

from mutagen import MutagenError
from mutagen.id3 import ID3, Frame

from planner.music.db import _db
from planner.music.parsing import read_id3v1_comment

_KEY = "custom_source"
V1 = "ID3v1"    # the old tag's comment, in the last 128 bytes of the file
_WITH_DESC = ("TXXX", "COMM")
_SEP = "; "


def _stored() -> str | None:
    row = _db().execute("SELECT value FROM app_meta WHERE key = ?", (_KEY,)).fetchone()
    return row[0] if row and row[0] else None


def source() -> tuple[str, str] | None:
    """(frame id, description) the Custom field is mapped to, or None."""
    value = _stored()
    if value is None:
        return None
    frame, _, desc = value.partition(":")
    return frame, desc


def writable() -> bool:
    """Whether a value typed in the app can go into the file on Save: into
    any mapped frame of the ID3v2 tag, never into the old tag's comment."""
    src = source()
    return src is not None and src[0] != V1


def set_source(frame: str | None, desc: str = "") -> bool:
    """Map the Custom field to `frame` (with `desc` for TXXX/COMM), or to
    nothing with None. True when that changed the mapping — the values read
    for the old one are dropped then."""
    value = None
    if frame:
        value = f"{frame}:{desc.strip()}" if frame in _WITH_DESC else frame
    if value == _stored():
        return False
    conn = _db()
    if value is None:
        conn.execute("DELETE FROM app_meta WHERE key = ?", (_KEY,))
    else:
        conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
                     (_KEY, value))
    conn.execute("UPDATE scan_meta SET custom = NULL")
    conn.execute("UPDATE global_meta SET custom = NULL")
    return True


def find(tags, src: tuple[str, str] | None = None) -> Frame | None:
    """The frame of `tags` the mapping names, or None. A description matches
    in any case: taggers disagree on it, the frame is the same."""
    src = src or source()
    if src is None or tags is None:
        return None
    frame_id, desc = src
    for frame in tags.values():
        if frame.FrameID != frame_id:
            continue
        if frame_id not in _WITH_DESC or frame.desc.lower() == desc.lower():
            return frame
    return None


def value_of(tags, path=None) -> str:
    """The mapped frame's text in `tags`; '' without a mapping or the frame.
    The old tag's comment is not in `tags`: it is read from `path`."""
    src = source()
    if src is not None and src[0] == V1:
        return (read_id3v1_comment(Path(path)) or "") if path is not None else ""
    frame = find(tags, src)
    if frame is None:
        return ""
    return _SEP.join(str(t) for t in getattr(frame, "text", ()))


def read_file(path) -> str:
    """The mapped frame's text in the MP3 at `path`; '' when there is no
    mapping, no such frame or no readable tag. Opens the file only when
    something is mapped."""
    src = source()
    if src is None:
        return ""
    if src[0] == V1:
        return read_id3v1_comment(Path(path)) or ""
    try:
        tags = ID3(Path(path))
    except (MutagenError, OSError, ValueError):     # no tag, not an MP3, gone
        return ""
    return value_of(tags)
