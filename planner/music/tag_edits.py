"""Tag edits made in the app: star rating, class tags, instrumental flag, free
markers and the Custom field — and, from the editor's database mode, the title,
artist, album, year, genre and comment the app shows (DB_FIELDS).

They live in the `tag_edits` table, keyed by the content fingerprint like every
other per-track row (so `AudioCache.reattach_retagged` carries them over when the
file is re-tagged), and they WIN over what the file's own tags say. The file is
only written when asked to.

A stored field means "overridden"; a missing (NULL) one means "the file's value".
`classes_ok = []` is an explicit "every class", `rating = 0` an explicit "unrated",
`custom = ""` an explicit blank, and so are `year = 0` and a text field's "".

`genre` is the one field that is no attribute of the entry: it says what the
genre tag would, and sets `dance` or `other_genre` from it (`genre_parts`).
"""

import json
from typing import Any

from planner.models import GENRE_TO_DANCE, OTHER_GENRE_LABELS, fold_text
from planner.music.db import _db

DB_FIELDS = ("title", "tag_artist", "tag_album", "year", "genre", "tag_comment")
EDIT_FIELDS = ("rating", "classes_ok", "is_instrumental", "comment_tags", "custom",
               *DB_FIELDS)
_LIST_FIELDS = ("classes_ok", "comment_tags")
_TEXT_FIELDS = ("custom", "title", "tag_artist", "tag_album", "genre", "tag_comment")

def genre_parts(text) -> tuple:
    """(dance, other_genre) a genre tag reading `text` gives: a dance
    ('SW', 'Slowfox') or a social genre ('SL') as the scan reads them, any
    other text as a genre of its own. Blank: neither."""
    text = (text or "").strip()
    if not text:
        return None, None
    key = fold_text(text)
    dance = GENRE_TO_DANCE.get(key)
    if dance:
        return dance, None
    return None, OTHER_GENRE_LABELS.get(key, text)


def genre_label(dance, other) -> str:
    """The genre an entry has, as the editor shows it: its dance code, else
    its other genre."""
    return dance or other or ""


def _pack(field: str, value):
    if value is None:
        return None
    if field in _LIST_FIELDS:
        return json.dumps(list(value), ensure_ascii=False)
    if field == "is_instrumental":
        return 1 if value else 0
    if field in _TEXT_FIELDS:
        return str(value)
    return int(value)


def _unpack(row) -> dict:
    out = {}
    for field, raw in zip(EDIT_FIELDS, row, strict=True):
        if raw is None:
            continue
        if field in _LIST_FIELDS:
            out[field] = json.loads(raw)
        elif field == "is_instrumental":
            out[field] = bool(raw)
        else:
            out[field] = raw
    return out


def load_all() -> dict[str, dict]:
    """Every edit: {fingerprint: {field: value}}."""
    rows = _db().execute(
        f"SELECT fp, {', '.join(EDIT_FIELDS)} FROM tag_edits").fetchall()  # nosec B608: constant names
    return {r[0]: e for r in rows if (e := _unpack(r[1:]))}


def load(fp: str) -> dict:
    """The edit for one fingerprint ({} when the track has none)."""
    row = _db().execute(
        f"SELECT {', '.join(EDIT_FIELDS)} FROM tag_edits WHERE fp = ?", (fp,)).fetchone()  # nosec B608: constant names
    return _unpack(row) if row else {}


def save(fp: str, changes: dict) -> dict:
    """Merge `changes` into the track's edit; a None value drops that field.
    Returns the edit as it now stands (the row goes when nothing is left)."""
    unknown = set(changes) - set(EDIT_FIELDS)
    if unknown:
        raise ValueError(f"not an editable tag field: {sorted(unknown)}")
    edit = {**load(fp), **changes}
    edit = {k: v for k, v in edit.items() if v is not None}
    conn = _db()
    if not edit:
        conn.execute("DELETE FROM tag_edits WHERE fp = ?", (fp,))
        return {}
    conn.execute(
        f"INSERT OR REPLACE INTO tag_edits (fp, {', '.join(EDIT_FIELDS)}) "
        f"VALUES (?, {', '.join('?' * len(EDIT_FIELDS))})",
        (fp, *(_pack(f, edit.get(f)) for f in EDIT_FIELDS)))
    return edit


def file_value(entry, field: str) -> Any:
    """What the file itself says for `field`, edit or not."""
    edits = entry.tag_edits or {}
    if field == "genre":
        if "genre" in edits:
            return genre_label(*edits["genre"])
        # The plain genre tag is the same last fallback the Dance column uses.
        return (genre_label(entry.dance, entry.other_genre)
                or getattr(entry, "tag_genre", None) or "")
    return edits[field] if field in edits else getattr(entry, field)


def same_value(field: str, a, b) -> bool:
    """Whether two values of `field` mean the same thing: no stars and 0 stars,
    no classes and an empty list, the classes in any order."""
    if field in ("rating", "year"):
        return (a or None) == (b or None)
    if field == "classes_ok":
        return set(a or ()) == set(b or ())
    if field == "is_instrumental":
        return bool(a) == bool(b)
    if field == "genre":
        return genre_parts(a) == genre_parts(b)
    if field in _TEXT_FIELDS:
        return (a or "") == (b or "")
    return list(a or ()) == list(b or ())


def apply(entry, edit: dict | None) -> None:
    """Lay `edit` over the entry's file values, in place.

    The file values of overridden fields are kept in `entry.tag_edits`, so applying
    again (or applying None) starts from the file and never stacks edits."""
    for field, original in (entry.tag_edits or {}).items():
        if field == "genre":
            entry.dance, entry.other_genre = original
        else:
            setattr(entry, field, original)
    entry.tag_edits = None
    if not edit:
        return
    originals = {}
    for field, value in edit.items():
        if field == "genre":
            originals[field] = (entry.dance, entry.other_genre)
            entry.dance, entry.other_genre = genre_parts(value)
            continue
        originals[field] = getattr(entry, field)
        if field == "classes_ok":
            value = list(value) or None
        elif field in ("rating", "year"):
            value = value or None
        elif field == "comment_tags":
            value = list(value)
        setattr(entry, field, value)
    entry.tag_edits = originals
