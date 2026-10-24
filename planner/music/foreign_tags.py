"""🏷 The tags of a FLAC, Ogg, Opus or M4A file, read as if they were ID3.

Everything in planner.music.parsing reads tags as ID3 frames (TIT2, TPE1,
TCON, TBPM, COMM, TXXX, …): the library was MP3 only. Rather than teach every
reader a second and a third tag format, the other formats' tags are turned
into an ID3 object once, here, and the readers stay as they are. Only for
reading: the tag editor writes MP3 files only.

Vorbis comments (FLAC, Ogg Vorbis, Opus) are free-form NAME=value pairs; an
M4A carries iTunes atoms ('©nam', 'tmpo', '----:com.apple.iTunes:NAME'). The
names the readers look for are mapped to their frames; any other free-form
field becomes a TXXX of the same name (UltraMixer's ULTRAMIXER_DANCESTYLE
among them), exactly as an MP3 tagger stores it.

An MP3 with no ID3 tag may still carry an APEv2 one (foobar2000 and mp3gain
write them): its keys are the Vorbis names in any case ('Title', 'Year'),
and are read the same way. A cover picture (a binary value) is skipped.

⭐ A star rating has no one home outside ID3: foobar2000 writes RATING=1–5,
MusicBee and MediaMonkey RATING=0–100, Picard and Amarok FMPS_RATING=0.0–1.0
(an M4A carries the same names as free-form atoms). Each is read as the
Windows POPM frame an MP3 would carry for the same stars.
"""
from mutagen._vorbis import VCommentDict
from mutagen.apev2 import APETextValue, APEv2
from mutagen.id3 import COMM, ID3, POPM, TALB, TBPM, TCON, TDRC, TIT2, TPE1, TXXX
from mutagen.mp4 import MP4Tags

# Vorbis comment name (lower-case) → the ID3 frame the readers know it as.
_VORBIS = {"title": TIT2, "artist": TPE1, "album": TALB, "genre": TCON,
           "bpm": TBPM, "tempo": TBPM, "date": TDRC, "year": TDRC}
_VORBIS_COMMENT = ("comment", "description")
# Rating field names (lower-case), Vorbis or M4A free-form.
_RATING = ("rating", "fmps_rating")

# iTunes atom → frame. 'tmpo' is a number, the rest are text.
_MP4 = {"\xa9nam": TIT2, "\xa9ART": TPE1, "\xa9alb": TALB, "\xa9gen": TCON,
        "tmpo": TBPM, "\xa9day": TDRC}
_MP4_COMMENT = "\xa9cmt"
_MP4_FREEFORM = "----:com.apple.iTunes:"


def _texts(values) -> list[str]:
    """Text values of one field: str, bytes (an M4A free-form atom) or a number."""
    out = []
    for v in values if isinstance(values, list) else [values]:
        if isinstance(v, bytes):
            v = v.decode("utf-8", "replace")
        text = str(v).strip()
        if text:
            out.append(text)
    return out


def as_id3(tags) -> ID3 | None:
    """An ID3 holding what `tags` (a mutagen VComment or MP4Tags) says, or
    None when there is nothing in it — or it is no format this knows."""
    pairs = _pairs(tags)
    if pairs is None:
        return None
    id3 = ID3()
    for name, frame, values in pairs:
        texts = _texts(values)
        if not texts:
            continue
        if frame is POPM:
            stars = _stars(name, texts[0])
            if stars is not None and not id3.getall("POPM"):
                id3.add(POPM(email="", rating=_popm_byte(stars), count=0))
        elif frame is COMM:
            id3.add(COMM(encoding=3, lang="eng", desc="", text=texts))
        elif frame is TXXX:
            id3.add(TXXX(encoding=3, desc=name, text=texts))
        elif frame.__name__ not in id3:   # the first of two names wins
            id3.add(frame(encoding=3, text=texts))
    return id3 if len(id3) else None


def _stars(name: str, text: str) -> int | None:
    """1–5 stars from a rating field's text, None for unrated or unreadable.
    FMPS is a fraction; a RATING up to 5 is stars, above it a 0–100 scale."""
    try:
        value = float(text)
    except ValueError:
        return None
    if value <= 0:
        return None
    if name.lower() == "fmps_rating":
        value *= 5
    elif value > 5:
        value /= 20
    return min(5, max(1, int(value + 0.5)))   # half a star rounds up


def _popm_byte(stars: int) -> int:
    # parsing imports this module, so its star table is fetched at call time.
    from planner.music.parsing import stars_popm
    return stars_popm(stars)


def _named(fields: list) -> list:
    """(name, frame class, values) for Vorbis-style NAME=values fields, the
    name matched in lower case."""
    # Neither tag type keeps a stable order: sort the names _VORBIS knows first,
    # in its order, so 'bpm' beats 'tempo' and 'date' beats 'year' every time.
    rank = {k: i for i, k in enumerate(_VORBIS)}
    fields = sorted(fields, key=lambda kv: rank.get(kv[0].lower(), len(rank)))
    out = []
    for name, values in fields:
        k = name.lower()
        frame = (POPM if k in _RATING else
                 _VORBIS.get(k, COMM if k in _VORBIS_COMMENT else TXXX))
        out.append((name, frame, values))
    return out


def _pairs(tags):
    """(name, frame class, values) for each field, or None for a tag type
    that is neither Vorbis comments, an APEv2 tag nor iTunes atoms."""
    if isinstance(tags, VCommentDict):
        return _named(list(tags.as_dict().items()))
    if isinstance(tags, APEv2):
        return _named([(k, list(v)) for k, v in tags.items()
                       if isinstance(v, APETextValue)])
    if isinstance(tags, MP4Tags):
        out = []
        for k, v in tags.items():
            if k in _MP4:
                out.append((k, _MP4[k], v))
            elif k == _MP4_COMMENT:
                out.append((k, COMM, v))
            elif k.startswith(_MP4_FREEFORM):
                name = k[len(_MP4_FREEFORM):]
                out.append((name, POPM if name.lower() in _RATING else TXXX, v))
        return out
    return None
