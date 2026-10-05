"""Tag edits made in the app: star rating, class tags, instrumental flag, free
markers and the Custom field.

They live in the `tag_edits` table, keyed by the content fingerprint like every
other per-track row (so `AudioCache.reattach_retagged` carries them over when the
file is re-tagged), and they WIN over what the file's own tags say. The file is
only written when asked to.

A stored field means "overridden"; a missing (NULL) one means "the file's value".
`classes_ok = []` is an explicit "every class", `rating = 0` an explicit "unrated",
`custom = ""` an explicit blank.
"""
from __future__ import annotations

import json

from planner.db import _db

EDIT_FIELDS = ("rating", "classes_ok", "is_instrumental", "comment_tags", "custom")
_LIST_FIELDS = ("classes_ok", "comment_tags")


def _pack(field: str, value):
    if value is None:
        return None
    if field in _LIST_FIELDS:
        return json.dumps(list(value), ensure_ascii=False)
    if field == "is_instrumental":
        return 1 if value else 0
    if field == "custom":
        return str(value)
    return int(value)


def _unpack(row) -> dict:
    out = {}
    for field, raw in zip(EDIT_FIELDS, row):
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
        f"SELECT fp, {', '.join(EDIT_FIELDS)} FROM tag_edits").fetchall()
    return {r[0]: e for r in rows if (e := _unpack(r[1:]))}


def load(fp: str) -> dict:
    """The edit for one fingerprint ({} when the track has none)."""
    row = _db().execute(
        f"SELECT {', '.join(EDIT_FIELDS)} FROM tag_edits WHERE fp = ?", (fp,)).fetchone()
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


def file_value(entry, field: str):
    """What the file itself says for `field`, edit or not."""
    edits = entry.tag_edits or {}
    return edits[field] if field in edits else getattr(entry, field)


def same_value(field: str, a, b) -> bool:
    """Whether two values of `field` mean the same thing: no stars and 0 stars,
    no classes and an empty list, the classes in any order."""
    if field == "rating":
        return (a or None) == (b or None)
    if field == "classes_ok":
        return set(a or ()) == set(b or ())
    if field == "is_instrumental":
        return bool(a) == bool(b)
    if field == "custom":
        return (a or "") == (b or "")
    return list(a or ()) == list(b or ())


def apply(entry, edit: dict | None) -> None:
    """Lay `edit` over the entry's file values, in place.

    The file values of overridden fields are kept in `entry.tag_edits`, so applying
    again (or applying None) starts from the file and never stacks edits."""
    for field, original in (entry.tag_edits or {}).items():
        setattr(entry, field, original)
    entry.tag_edits = None
    if not edit:
        return
    originals = {}
    for field, value in edit.items():
        originals[field] = getattr(entry, field)
        if field == "classes_ok":
            value = list(value) or None
        elif field == "rating":
            value = value or None
        elif field == "comment_tags":
            value = list(value)
        setattr(entry, field, value)
    entry.tag_edits = originals
