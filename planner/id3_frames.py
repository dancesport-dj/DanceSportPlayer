"""🏷 Every ID3 frame of one MP3, for the tag editor's form and "Extended tags".

The tag editor's top half stores stars, classes and markers in the DB; this is
the other half, which writes straight into the file — UltraMixer's TXXX frames,
MediaMonkey's COMM fields, WMP's POPM rating and every standard text frame.

A field's key is mutagen's HashKey ('TIT2', 'TXXX:ultramixer_meter',
'COMM:Songs-DB_Custom1:eng', 'POPM:Windows Media Player 9 Series'), unique per
tag. Text, comment, URL and rating frames are editable; pictures and other
binary frames are listed with a summary and can only be deleted.

write_app_fields() is the bridge between the halves: once the user agrees, it
puts the app's own fields into the file where other programs look for them —
the stars into WMP's POPM rating, classes, instrumental and markers into the
plain comment, merged with whatever text that comment already holds, and the
Custom field into the frame it is mapped to (planner.custom_field).

read_form() finds Mp3tag's fixed fields (title, year, comment, replay gain, …)
wherever this file keeps them; write_tags() writes the extended table, the
form and the app fields together, in one save.

The tag is read as it is in the file (a v2.3 year stays TYER) and written back
in its own version, so a v2.3 tag stays readable for the players that want one
and frames mutagen doesn't know survive. Only a v2.2 tag, which mutagen can't
write, becomes v2.3; a file without a tag gets a v2.3 one.
"""
from dataclasses import dataclass
from pathlib import Path

from mutagen.id3 import (
    COMM,
    ID3,
    POPM,
    TXXX,
    Encoding,
    Frames,
    ID3NoHeaderError,
    PairedTextFrame,
    TextFrame,
    UrlFrame,
)

from planner.parsing import (
    _CLASS_CODES,
    _CLASS_ORDER,
    _INSTR_WORDS,
    _WMP_POPM_EMAIL,
    _ab_classes,
    _get_comment_tag,
    is_marker_noise,
    stars_popm,
)
from planner import custom_field

_SEP = "; "
_SUMMARY_LEN = 200
_SAMPLE = 80        # files the Custom mapping dialog looks into
_V1_SIZE = 128
_APP_FIELDS = ("rating", "classes_ok", "is_instrumental", "comment_tags", "custom")
_COMMENT_FIELDS = ("classes_ok", "is_instrumental", "comment_tags")

# What "➕ Add field" offers after the two custom ones, in this order.
_STANDARD = ("TIT2", "TPE1", "TALB", "TPE2", "TCON", "TBPM", "TKEY", "TCOM", "TPOS",
             "TRCK", "TIT1", "TIT3", "TPUB", "TCOP", "TLAN", "TSRC")

# Plain names for the frames a dance library holds; the GUI translates them.
FRAME_NAMES = {
    "TXXX": "Custom text",
    "COMM": "Comment",
    "WXXX": "Custom link",
    "POPM": "Rating",
    "APIC": "Picture",
    "PRIV": "Private data",
    "GEOB": "Embedded object",
    "MCDI": "CD identifier",
    "UFID": "Unique file id",
    "USLT": "Lyrics",
    "PCNT": "Play count",
    "RVA2": "Volume adjustment",
    "TIT1": "Grouping",
    "TIT2": "Title",
    "TIT3": "Subtitle",
    "TPE1": "Artist",
    "TPE2": "Album artist",
    "TPE3": "Conductor",
    "TPE4": "Remixed by",
    "TALB": "Album",
    "TCON": "Genre",
    "TBPM": "BPM",
    "TKEY": "Key",
    "TCOM": "Composer",
    "TEXT": "Lyricist",
    "TRCK": "Track number",
    "TPOS": "Disc number",
    "TYER": "Year",
    "TDRC": "Recording date",
    "TPUB": "Publisher",
    "TCOP": "Copyright",
    "TLAN": "Language",
    "TSRC": "ISRC",
    "TLEN": "Length (ms)",
    "TENC": "Encoded by",
    "TSSE": "Encoder settings",
    "TMED": "Media type",
    "GRP1": "Grouping (iTunes)",
}


@dataclass(frozen=True)
class TagField:
    key: str        # mutagen HashKey, unique in the tag
    frame: str      # 'TXXX', 'TIT2', …
    desc: str       # a TXXX/COMM/WXXX description, a POPM e-mail, a picture's name
    value: str      # the text; for a binary frame a summary
    editable: bool


def _load(path: Path) -> tuple[ID3, int]:
    """The file's tag as it is, and the version (3 or 4) it is written in.
    ValueError for a file that isn't an MP3."""
    path = Path(path)
    if path.suffix.lower() != ".mp3":
        raise ValueError(f"{path.name} is not an MP3")
    try:
        tags = ID3(path, translate=False, load_v1=False)
    except ID3NoHeaderError:
        return ID3(), 3
    if tags.version[1] == 4:
        return tags, 4
    if tags.version[1] < 3:     # v2.2 frame ids (TT2) can't be written
        tags = ID3(path, v2_version=3, load_v1=False)
    return tags, 3


def _editable(frame) -> bool:
    return (isinstance(frame, (TextFrame, UrlFrame, POPM))
            and not isinstance(frame, PairedTextFrame))


def _summary(frame) -> str:
    data = getattr(frame, "data", None)
    if isinstance(data, bytes):
        mime = getattr(frame, "mime", "")
        return f"{mime}, {len(data)} bytes" if mime else f"{len(data)} bytes"
    try:
        text = frame.pprint().split("=", 1)[-1]
    except Exception:
        text = ""
    if not text or text == "[unrepresentable data]":
        return frame.FrameID
    text = " ".join(text.split())
    return text if len(text) <= _SUMMARY_LEN else text[:_SUMMARY_LEN] + "…"


def _field(key: str, frame) -> TagField:
    desc = ""
    for attr in ("desc", "email", "owner"):
        v = getattr(frame, attr, None)
        if isinstance(v, str):
            desc = v
            break
    if isinstance(frame, POPM):
        value = str(frame.rating)
    elif isinstance(frame, UrlFrame):
        value = frame.url
    elif _editable(frame):
        value = _SEP.join(str(t) for t in frame.text)
    else:
        value = _summary(frame)
    return TagField(key, frame.FrameID, desc, value, _editable(frame))


def read_fields(path) -> list[TagField]:
    """Every frame of the file's ID3 tag, sorted by key; [] without a tag."""
    tags, _version = _load(path)
    return [_field(k, tags[k]) for k in sorted(tags.keys())]


def tag_version(path) -> int:
    """3 or 4: the ID3v2 version a write keeps (v2.2 and no tag at all → 3)."""
    return _load(path)[1]


def addable_frames(version: int, present=()) -> list[str]:
    """The frame ids "➕ Add field" offers: the custom ones (always, they are
    told apart by their description), then the standard frames the tag doesn't
    have yet — the year as the tag's version spells it."""
    year = "TDRC" if version == 4 else "TYER"
    standard = _STANDARD[:5] + (year,) + _STANDARD[5:]
    return ["TXXX", "COMM"] + [f for f in standard if f not in set(present)]


def custom_frames() -> list[str]:
    """The frame ids the Custom field can be mapped to: the custom ones, then
    the standard text frames the form doesn't show — one mapped to Title
    would be edited in two places."""
    form = set(_FORM_FRAMES.values()) | {"TYER", "TDRC"}
    return ["TXXX", "COMM"] + [f for f in _STANDARD if f not in form]


def sample_custom(paths, limit: int = _SAMPLE) -> tuple[int, dict]:
    """What the frames Custom can be mapped to hold in up to `limit` of
    `paths`, spread evenly over them, so the mapping dialog can offer the
    descriptions the archive really has: (files read, {(frame id,
    description): (files holding it, one value)}). A description is matched
    in any case, keeping the first spelling met; a comment without one is
    the plain comment and can't be mapped."""
    paths = list(paths)
    step = max(1, len(paths) // limit) if limit else 1
    mappable = set(custom_frames())
    read, found = 0, {}
    for path in paths[::step][:limit]:
        try:
            tags = ID3(Path(path))
        except Exception:       # no tag, not an MP3, gone: just not counted
            continue
        read += 1
        here = set()
        for frame in tags.values():
            fid = frame.FrameID
            desc = frame.desc if fid in custom_field._WITH_DESC else ""
            key = (fid, desc.lower())
            if (fid not in mappable or key in here
                    or (fid in custom_field._WITH_DESC and not desc.strip())):
                continue
            here.add(key)
            text = _SEP.join(str(t) for t in getattr(frame, "text", ()))
            name, count, example = found.get(key, (desc, 0, ""))
            found[key] = (name, count + 1, example or text)
    return read, {(fid, name): (count, example)
                  for (fid, _low), (name, count, example) in found.items()}


def _check_text(frame, value: str) -> None:
    if isinstance(frame, UrlFrame):
        try:
            value.encode("latin-1")
        except UnicodeEncodeError:
            raise ValueError(f"{frame.HashKey}: a link can only hold Latin-1 "
                             f"characters") from None


def _rating(key: str, value: str) -> int:
    try:
        rating = int(value.strip())
    except ValueError:
        raise ValueError(f"{key}: the rating must be a whole number "
                         f"from 0 to 255, not {value!r}") from None
    if not 0 <= rating <= 255:
        raise ValueError(f"{key}: the rating must be 0 to 255, not {rating}")
    return rating


def _set(frame, value: str) -> None:
    if isinstance(frame, POPM):
        frame.rating = _rating(frame.HashKey, value)
        return
    if isinstance(frame, UrlFrame):
        frame.url = value
        return
    if len(frame.text) > 1:
        text = [v.strip() for v in value.split(";") if v.strip()]
    else:
        text = [value]
    if frame.encoding == Encoding.LATIN1:
        try:
            "".join(text).encode("latin-1")
        except UnicodeEncodeError:
            frame.encoding = Encoding.UTF8      # v2.3 writes that as UTF-16
    frame.text = text


def _new_frame(frame_id: str, desc: str, value: str, version: int):
    if frame_id == "TXXX":
        return TXXX(encoding=Encoding.UTF8, desc=desc, text=[value])
    if frame_id == "COMM":
        return COMM(encoding=Encoding.UTF8, lang="eng", desc=desc, text=[value])
    if frame_id not in addable_frames(version):
        raise ValueError(f"{frame_id} can't be added here")
    return Frames[frame_id](encoding=Encoding.UTF8, text=[value])


def write_fields(path, sets=None, deletes=(), adds=()) -> bool:
    """Write `sets` ({key: new value}), drop `deletes` (keys) and add `adds`
    ((frame id, description, value) each) into the MP3 at `path`.

    Every input is checked before the file is written — one field the file
    doesn't have, a rating that isn't 0–255 or a new field that already exists
    raises ValueError and nothing is written. Returns False when there was
    nothing to do (the file isn't touched), True after a write.

    A text field set to '' is gone afterwards: mutagen writes no empty text
    frame, and drops the empty ones some taggers leave behind (an empty TPE3
    in three of 381 library files) on the same save.
    """
    return write_tags(path, raw={"sets": sets, "deletes": deletes, "adds": adds})


def _apply_fields(tags: ID3, version: int, sets: dict, deletes: list, adds: list) -> None:
    """write_fields' change on the tag in memory, every input checked first."""
    for key, value in sets.items():
        frame = tags.get(key)
        if frame is None:
            raise ValueError(f"{key} is not in the file")
        if not _editable(frame):
            raise ValueError(f"{key} can only be deleted, not edited")
        if isinstance(frame, POPM):
            _rating(key, value)
        _check_text(frame, value)
    for key in deletes:
        if key not in tags:
            raise ValueError(f"{key} is not in the file")
    new = []
    taken = set(tags.keys()) - set(deletes)
    for frame_id, desc, value in adds:
        frame = _new_frame(frame_id, desc, value, version)
        if frame.HashKey in taken:
            raise ValueError(f"{frame.HashKey} is already in the file")
        taken.add(frame.HashKey)
        new.append(frame)

    for key, value in sets.items():
        _set(tags[key], value)
    for key in deletes:
        del tags[key]
    for frame in new:
        tags.add(frame)


def _comment_part_kind(part: str) -> str:
    """Which app field a part of a ';'-separated comment belongs to."""
    if part.upper() in _CLASS_CODES or _ab_classes(part):
        return "classes_ok"
    if part.lower() in _INSTR_WORDS:
        return "is_instrumental"
    if is_marker_noise(part.lower()):
        return "other"
    return "comment_tags"


def _comment_target(tags: ID3):
    """The plain comment frame (no description) the app reads first, or None."""
    plain = [f for k, f in tags.items() if k.startswith("COMM") and f.desc == ""]
    with_text = [f for f in plain if f.text and str(f.text[0]).strip()]
    return (with_text or plain or [None])[0]


def _app_comment(tags: ID3, path: Path, changes: dict) -> str:
    """The comment with the changed app fields in it: the one the app reads
    now, plus whatever the plain comment frame holds besides (its text is not
    lost when the classes came from another comment or the ID3v1 tag)."""
    parts = []
    target = _comment_target(tags)
    for text in (_get_comment_tag(path, tags),
                 str(target.text[0]) if target is not None and target.text else ""):
        for part in (p.strip() for p in (text or "").split(";")):
            if part and part not in parts:
                parts.append(part)
    kept = [p for p in parts if _comment_part_kind(p) not in changes]
    front = [c for c in _CLASS_ORDER if c in changes.get("classes_ok", ())]
    back = ["instr"] if changes.get("is_instrumental") else []
    back += list(changes.get("comment_tags", ()))
    return ";".join(front + kept + back)


def write_app_fields(path, changes: dict) -> bool:
    """Write the app's own fields into the MP3, where a library scan reads them:
    `rating` (0–5 stars, 0 = unrated) as Windows' POPM rating, `classes_ok`,
    `is_instrumental` and `comment_tags` into the plain comment, e.g.
    'C;B;A;S;instr;vocal_f', `custom` into the frame it is mapped to ('' removes
    it). Only the fields in `changes` are touched; the comment's other parts
    and every other frame stay.

    ValueError for an unknown field, stars outside 0–5, an unknown class or a
    Custom value with nothing mapped, before anything is written. False when
    `changes` is empty."""
    return write_tags(path, app=changes)


def _check_app(changes: dict) -> None:
    unknown = set(changes) - set(_APP_FIELDS)
    if unknown:
        raise ValueError(f"not an app tag field: {sorted(unknown)}")
    if "rating" in changes and changes["rating"] not in range(6):
        raise ValueError(f"stars must be 0 to 5, not {changes['rating']!r}")
    bad = set(changes.get("classes_ok", ())) - set(_CLASS_ORDER)
    if bad:
        raise ValueError(f"not a class: {sorted(bad)}")
    if "custom" in changes and custom_field.source() is None:
        raise ValueError("the Custom field is not mapped to an MP3 tag")


def _apply_app(tags: ID3, path: Path, version: int, changes: dict) -> None:
    """write_app_fields' change on the tag in memory."""
    if "rating" in changes:
        key = f"POPM:{_WMP_POPM_EMAIL}"
        stars = changes["rating"]
        if key in tags:
            tags[key].rating = stars_popm(stars) if stars else 0
        elif stars:
            tags.add(POPM(email=_WMP_POPM_EMAIL, rating=stars_popm(stars), count=0))
    if "custom" in changes:
        frame = custom_field.find(tags)
        value = changes["custom"] or ""
        if frame is None:
            if value:
                tags.add(_new_frame(*custom_field.source(), value, version))
        elif value:
            _set(frame, value)
        else:
            del tags[frame.HashKey]
    if set(changes) & set(_COMMENT_FIELDS):
        text = _app_comment(tags, path, changes)
        target = _comment_target(tags)
        if target is None:
            tags.add(COMM(encoding=Encoding.UTF8, lang="eng", desc="", text=[text]))
        else:
            if target.encoding == Encoding.LATIN1:
                try:
                    text.encode("latin-1")
                except UnicodeEncodeError:
                    target.encoding = Encoding.UTF8
            target.text = [text]


# ── The Mp3tag-style form ───────────────────────────────────────────────────
# Its fields in form order; each is found wherever this file keeps it.
FORM_FIELDS = ("title", "artist", "album", "year", "track", "genre", "comment",
               "albumartist", "composer", "disc", "replaygain")
_FORM_FRAMES = {"title": "TIT2", "artist": "TPE1", "album": "TALB", "track": "TRCK",
                "genre": "TCON", "albumartist": "TPE2", "composer": "TCOM", "disc": "TPOS"}
# 3504 library files carry it, all spelled like this.
_REPLAYGAIN = "replaygain_track_gain"


def _year_id(version: int) -> str:
    return "TDRC" if version == 4 else "TYER"


def _form_key(tags: ID3, version: int, field: str) -> str | None:
    """The key of the frame holding `field` in this tag, or None."""
    if field in _FORM_FRAMES:
        return _FORM_FRAMES[field] if _FORM_FRAMES[field] in tags else None
    if field == "year":     # a v2.3 tag may hold only a TDRC (22 library files)
        order = ("TDRC", "TYER") if version == 4 else ("TYER", "TDRC")
        return next((k for k in order if k in tags), None)
    if field == "comment":
        target = _comment_target(tags)
        return target.HashKey if target is not None else None
    return next((k for k, f in tags.items()
                 if k.startswith("TXXX:") and f.desc.lower() == _REPLAYGAIN), None)


def _form_new(field: str, version: int, value: str) -> tuple:
    """The (frame id, description, value) a field the tag lacks is added as."""
    if field in _FORM_FRAMES:
        return _FORM_FRAMES[field], "", value
    if field == "year":
        return _year_id(version), "", value
    if field == "comment":
        return "COMM", "", value
    return "TXXX", _REPLAYGAIN, value


def form_frame_ids(version: int) -> set:
    """The frames the form adds — "➕ Add field" leaves those to it."""
    return set(_FORM_FRAMES.values()) | {_year_id(version)}


def read_form(path) -> dict:
    """{form field: its TagField, or None when the file doesn't have it}."""
    tags, version = _load(path)
    out = {}
    for field in FORM_FIELDS:
        key = _form_key(tags, version, field)
        out[field] = _field(key, tags[key]) if key else None
    return out


def read_cover(path) -> bytes | None:
    """The front cover's image data — any picture without one — or None."""
    tags, _version = _load(path)
    pics = [f for k, f in tags.items() if k.startswith("APIC")]
    front = [f for f in pics if f.type == 3]
    return (front or pics)[0].data if pics else None


def write_tags(path, raw=None, form=None, app=None) -> bool:
    """Everything the 🏷 editor writes into one MP3, in one save: `raw` the
    extended table's {"sets", "deletes", "adds"} (see write_fields), `form`
    {form field: value} ('' removes it), `app` the app's own fields (see
    write_app_fields) — last, so a typed comment gets the classes merged in.

    Checked as a whole first; ValueError leaves the file untouched. False when
    there is nothing to do."""
    raw = raw or {}
    sets = dict(raw.get("sets") or {})
    deletes = list(raw.get("deletes") or ())
    adds = list(raw.get("adds") or ())
    form = dict(form or {})
    app = dict(app or {})
    unknown = set(form) - set(FORM_FIELDS)
    if unknown:
        raise ValueError(f"not a form field: {sorted(unknown)}")
    _check_app(app)
    path = Path(path)
    tags, version = _load(path)
    for field, value in form.items():
        key = _form_key(tags, version, field)
        if key is None:
            if value:
                adds.append(_form_new(field, version, value))
        elif key in sets or key in deletes:
            raise ValueError(f"{key} is changed both in the form and the table")
        elif value:
            sets[key] = value
        else:
            deletes.append(key)
    if "custom" in app:
        _check_custom_alone(tags, sets, deletes, adds)
    if not (sets or deletes or adds or app):
        return False
    _apply_fields(tags, version, sets, deletes, adds)
    if app:
        _apply_app(tags, path, version, app)
    _save(tags, path, version)
    return True


def _check_custom_alone(tags: ID3, sets: dict, deletes: list, adds: list) -> None:
    """ValueError when the frame the Custom field writes is changed in the
    table or the form as well — which of the two should the file keep?"""
    frame_id, desc = custom_field.source()
    frame = custom_field.find(tags)
    if frame is not None and (frame.HashKey in sets or frame.HashKey in deletes):
        raise ValueError(f"{frame.HashKey} is changed both as Custom and in the table")
    for fid, d, _value in adds:
        if fid == frame_id and (fid not in ("TXXX", "COMM") or d.lower() == desc.lower()):
            raise ValueError(f"{fid} {d} is added in the table and written as Custom")


def _v1_tail(path: Path) -> bytes | None:
    """The file's ID3v1 tag, the last 128 bytes, or None without one."""
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        if fh.tell() < _V1_SIZE:
            return None
        fh.seek(-_V1_SIZE, 2)
        tail = fh.read(_V1_SIZE)
    return tail if tail.startswith(b"TAG") else None


def _save(tags: ID3, path: Path, version: int) -> None:
    """Save the v2 tag and leave an ID3v1 tag exactly as it was: mutagen
    rebuilds it from v2 and finds no comment there (it looks for a frame keyed
    'COMM', which v2 keys never are), so the classes 377 library files keep
    only in the v1 comment would be blanked."""
    old_v1 = _v1_tail(path)
    tags.save(path, v1=1, v2_version=version, v23_sep=None)
    if old_v1 is not None and _v1_tail(path) is not None:
        with open(path, "r+b") as fh:
            fh.seek(-_V1_SIZE, 2)
            fh.write(old_v1)
