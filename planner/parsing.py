"""Filename / tag parsing & detection helpers for the planner.

Extracted from dancesport_planner.py (logical split): the pure (mostly
filename-in, value-out) helpers that the scan and the competition importer
depend on — BPM/dance/year/Christmas detection, ID3 comment & class-tag reading,
title cleaning and tempo-fit formatting. Pinned by test_parsing.py.
"""
import re
import logging
import unicodedata
from pathlib import Path

try:
    from mutagen.id3 import ID3
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

from planner.models import (
    DANCE_PATTERNS, GENRE_TO_DANCE, TEMPO_RANGES, fold_text,
)

log = logging.getLogger("dancesport.parsing")


def _norm(p: str) -> str:
    return p.lower().replace('\\', '/')


def _stem_key(name: str) -> str:
    """Match key for playlist co-occurrence: the bare filename (no folder, no
    extension), lower-cased. Matching by filename rather than full path means a
    track still matches even if the M3U points at a different drive/folder than
    the current library — giving 'likely' matches instead of exact-path-only.
    """
    return Path(name).stem.lower().strip()


# Dance code glued directly to a BPM number, e.g. 'WW58', 'LW29', 'QS50'
# (the space-separated 'LW 29' form is handled by _clean_title).
_DANCE_BPM_PREFIX = re.compile(
    r'^(?:lw|tg|ta|ww|vw|sf|qs|qu|cc|sa|sb|rb|ru|pd|ji|jv)\d{1,3}[\s_\-]*',
    re.IGNORECASE)


def _title_key(name: str) -> str:
    """Match key derived from a filename's *title* (dance codes, BPM markers and
    punctuation stripped, alphanumeric-normalised). Lets a renamed file match an
    old playlist entry whose filename approximated the song title. Returns '' if
    nothing meaningful remains (callers must ignore empty keys)."""
    stem = _DANCE_BPM_PREFIX.sub('', Path(name).stem)
    key = _norm_title(_clean_title(stem))
    return key if len(key) >= 3 else ''


# Decorations that mark the SAME song re-encoded for a different DJ / tempo and so
# should NOT make two copies look like different titles:
#   • a trailing "DJ <whatever>" tag                         → 'Upside Down DJ Ice'
#   • a parenthetical/bracket dance(+bpm) code               → 'Upside Down (JI43)'
#   • a glued dance+bpm token anywhere                       → 'Upside Down JI43'
_DANCE_CODES_RE = r'lw|tg|ta|ww|vw|sf|qs|qu|cc|sa|sb|rb|ru|pd|ji|jv'


_DJ_TAG = re.compile(r'(?<=\S)\s+\bdj\b.*$', re.IGNORECASE)
# A word of three letters or more — what a title has and a 'S50' / '1-01SB' prefix hasn't.
_TITLE_WORD = re.compile(r'[^\W\d_]{3,}')


_PAREN_CODE = re.compile(
    rf'[\(\[]\s*(?:{_DANCE_CODES_RE})\s*\d{{0,3}}\s*[\)\]]', re.IGNORECASE)


_GLUED_CODE = re.compile(
    rf'\b(?:{_DANCE_CODES_RE})\s?\d{{1,3}}\b', re.IGNORECASE)


# Full dance NAMES (German + English) used as a DJ-style filename prefix, e.g.
# 'jive(43) - Bim Bam' or 'Samba - Foo'. Only stripped when at the very start AND
# followed by a tag separator (paren / digit / dash / colon) so real titles that
# merely begin with a dance word ('Jive Bunny') are left intact.
_DANCE_WORDS_RE = (
    r'langsamer\s+walzer|wiener\s+walzer|slow\s*fox(?:trott?)?|quick\s*step|'
    r'cha[\s-]*cha(?:[\s-]*cha)?|paso\s*doble|disco\s*fox|'
    r'walzer|waltz|tango|foxtrott?|quickstep|samba|rumba|rhumba|jive|salsa|'
    r'discofox|wcs'
)


_LEAD_DANCE_PREFIX = re.compile(
    rf'^\s*(?:{_DANCE_WORDS_RE})\s*(?=[\(\[\)\]\-_|:]|\d)', re.IGNORECASE)


# A bare parenthetical / bracketed number with no dance code, e.g. '(43)' or '[50]'.
_BARE_PAREN_NUM = re.compile(r'[\(\[]\s*\d{1,3}\s*[\)\]]')


# Leading track-number / index prefixes glued to the front of a title, possibly
# several in a row: '08 ', '2-14 ', '08 1-16 ', '03. '. Common in this library
# ('08 1-16 El Sonador' vs the playlist's '1-16 El Sonador'). Only stripped when real
# title text follows (the caller's >=3-char guard / raw fallback protects number-titles).
_LEAD_TRACK_NUM = re.compile(r'^\s*(?:\d+[\s._\-]+)+')

# Trailing 'cut' tournament-edit marker, stripped only in the dedup key (see
# `_song_title_key`), not in `_clean_title`'s displayed title.
_CUT_TRIM_RE = re.compile(r'[\s_(\[]+cut\b[\s)\]]*$', re.IGNORECASE)


def _song_title_key(name: str) -> str:
    """Aggressively normalise a track title so re-encoded copies of the SAME song
    collapse together — e.g. 'Upside Down DJ Ice' and 'Upside Down (JI43)' both
    become 'upside down'. Strips a trailing DJ tag, parenthetical/glued dance+bpm
    codes, then reuses `_clean_title`/`_norm_title`. Falls back to the plain
    normalised title if nothing meaningful survives (so distinct songs whose whole
    title looks like a tag, e.g. 'DJ Got Us Fallin In Love', stay distinct).
    Used by the Similar-window 'hide duplicate copies' filter."""
    raw = Path(name).stem
    s = _PAREN_CODE.sub(' ', raw)
    dj = _DJ_TAG.search(s)
    # Only a TRAILING tag: in 'S50  DJ Eiffel. Dancando Na Rua' the DJ is the artist
    # in front of the title, and cutting there would leave just the tempo code.
    if dj and _TITLE_WORD.search(s[:dj.start()]):
        s = s[:dj.start()]
    s = _GLUED_CODE.sub(' ', s)
    s = _LEAD_DANCE_PREFIX.sub(' ', s)   # strip a leading 'Jive(.. / Samba - / Tango:' tag
    s = _BARE_PAREN_NUM.sub(' ', s)      # strip a leftover bare '(43)' / '[50]'
    s = _LEAD_TRACK_NUM.sub(' ', s)      # strip leading track-number(s): '08 1-16 ', '2-14 '
    s = s.strip(' -_|')                  # drop separators the prefix-strip left behind
    cleaned = _clean_title(s)
    # A trailing 'cut' tournament-edit marker, however separated ('… cut', '… (cut)';
    # the '_cut' form is already gone via _clean_title). Stripped only here in the
    # dedup KEY (not in _clean_title) so the displayed title 'The Final Cut' stays
    # intact while a 'Creepin cut' copy still collapses onto 'Creepin'. End-anchored.
    cleaned = _CUT_TRIM_RE.sub('', cleaned)
    key = _norm_title(cleaned)
    return key if len(key) >= 3 else _norm_title(_clean_title(raw))


_DASH_SPLIT_RE = re.compile(r'\s+-\s+')


def _song_title_keys(name: str) -> list[str]:
    """Candidate dedup keys for a track: the full title key, PLUS — when the name has
    a spaced ' - ' (the DJ-export Artist–Title delimiter) — a key for each side. A
    bare 'Rhythm' then shares the 'rhythm' candidate of 'Casey … - Rhythm' WITHOUT the
    full 'Higher - Faster' ever collapsing to 'faster' (its full key stays too). The
    caller treats a match on ANY shared candidate as the same song — recall over
    precision, so a possible duplicate is mentioned rather than missed. Order: full
    key first, then the dash parts; de-duplicated, empties dropped."""
    keys: list[str] = []
    full = _song_title_key(name)
    if full:
        keys.append(full)
    stem = Path(name).stem
    if _DASH_SPLIT_RE.search(stem):
        for part in _DASH_SPLIT_RE.split(stem):
            k = _song_title_key(part)
            if k and k not in keys:
                keys.append(k)
    return keys


# A remix, cover or other version of a song: the word, a bracket that holds it
# ('(DJ Maksy Viennese Waltz Remix)', '[Salsa Version]') and a dash part that
# holds it ('Adele - Rolling in the deep - rumba remix - (Dj Mitya)').
_VERSION_WORDS = r'remix|rmx|mix|edit|version|bootleg|rework|mashup|cover|remake'
_VERSION_WORD_RE = re.compile(rf'\b(?:{_VERSION_WORDS})\b', re.IGNORECASE)
_VERSION_GROUP_RE = re.compile(
    rf'[\(\[][^\(\)\[\]]*\b(?:{_VERSION_WORDS})\b[^\(\)\[\]]*[\)\]]', re.IGNORECASE)
_VERSION_DASH_RE = re.compile(
    rf'\s+-\s+[^-]*\b(?:{_VERSION_WORDS})\b[^-]*?(?=\s+-\s+|$)', re.IGNORECASE)
_DANCE_WORD_KEY_RE = re.compile(rf'(?:{_DANCE_WORDS_RE})', re.IGNORECASE)


def is_version(name: str) -> bool:
    """True when a file name marks a remix, cover, edit or other version."""
    return bool(_VERSION_WORD_RE.search(Path(name).stem))


def version_base_keys(name: str) -> list[str]:
    """For a version of a song ('Willow (DJ Maksy Viennese Waltz Remix)'), the
    `_song_title_keys` of the song without the version part — [] for a name
    that is no version, or whose version word is the whole title ('Party Mix
    I'). A key that is only a dance word ('Samba - … (New Mix)') is dropped."""
    stem = Path(name).stem
    base = _VERSION_DASH_RE.sub(' ', _VERSION_GROUP_RE.sub(' ', stem))
    if base.strip() == stem.strip():
        return []
    return [k for k in _song_title_keys(base + '.mp3')
            if not _DANCE_WORD_KEY_RE.fullmatch(k)]


# ── Class suitability from COMM tag ───────────────────────────────────────────
_CLASS_CODES = {'D', 'C', 'B', 'A', 'S'}


_INSTR_WORDS = {'instr', 'instrumental'}

# Songs-DB writes a class floor, 'ab C' = class C and every class above it.
_CLASS_ORDER = ('D', 'C', 'B', 'A', 'S')
_AB_CLASS_RE = re.compile(r'ab\s+([dcbas])', re.IGNORECASE)


def _ab_classes(part: str) -> list[str] | None:
    """'ab C' → ['C', 'B', 'A', 'S']; None when `part` is no class floor."""
    m = _AB_CLASS_RE.fullmatch(part.strip())
    if not m:
        return None
    return list(_CLASS_ORDER[_CLASS_ORDER.index(m.group(1).upper()):])

# Filename/title marker for instrumentals: '(Instr.)', '… Instrumental', '(inst)'.
# Word-bounded so 'instant'/'einst' never match.
_TITLE_INSTR_RE = re.compile(r'\b(?:instr\w*|inst)\b', re.IGNORECASE)


def title_marks_instrumental(text: str) -> bool:
    """True when a filename/title carries an 'instrumental' marker."""
    return bool(_TITLE_INSTR_RE.search(text))


# iTunes / UltraMixer / ReplayGain etc. write technical data into their OWN COMM
# frames (desc='iTunNORM', 'iTunPGAP', …). They must never shadow the real comment.
_COMMENT_JUNK_DESC = ('itun', 'ultramixer', 'replaygain', 'cddb')


# "No tags handed in: read them from the file." None can't say this - it is
# a real answer (the file has no ID3 tag).
_UNREAD = object()


def _id3_of(path: Path, tags=_UNREAD):
    """`tags` when handed in, else the file's own ID3 tag; None when it has none."""
    if tags is not _UNREAD:
        return tags
    try:
        return ID3(path)
    except Exception:
        return None


def _read_tags_once(path: Path) -> tuple:
    """(ID3 tag or None, duration in whole seconds) from ONE parse of the file.

    For the scan's slow path, which wants every tag field and the length: the
    helpers below each opened the file on their own, five parses a track. An
    MP3's tag comes out of `MutagenFile` as exactly what `ID3(path)` reads;
    anything else (no audio frame found, another format) asks `ID3` itself,
    so every answer stays what it was."""
    if not HAS_MUTAGEN:
        return None, 0
    try:
        audio = MutagenFile(path)
    except Exception:
        audio = None
    secs = 0
    if audio is not None and audio.info is not None:
        secs = int(round(audio.info.length))
    if audio is not None and type(audio.tags) is ID3:
        return audio.tags, secs
    return _id3_of(path), secs


def _read_id3v1_comment(path: Path) -> str | None:
    """The raw ID3v1 'comment' field from the last 128 bytes ('TAG' magic). Some older
    files carry the class tag only here, so it's used as a last-resort fallback."""
    try:
        with open(path, 'rb') as f:
            f.seek(-128, 2)
            tag = f.read(128)
    except Exception:
        return None
    if len(tag) != 128 or tag[:3] != b'TAG':
        return None
    comment = tag[97:127]                       # 30-byte comment field
    if comment[28] == 0 and comment[29] != 0:   # ID3v1.1 keeps a track no. in byte 29
        comment = comment[:28]
    try:
        return comment.decode('latin-1').strip('\x00').strip() or None
    except Exception:
        return None


def _get_comment_tag(path: Path, tags=_UNREAD) -> str | None:
    """Return the most relevant comment for class-tag parsing.

    Skips iTunes / UltraMixer technical COMM frames (iTunNORM, iTunPGAP, …) that would
    otherwise shadow a real class tag like 'D;C;B;vocal_f'. Among the remaining comments
    it PREFERS one that actually carries class codes, searched in priority order:
    standard COMM (empty desc) → iTunes' ID3v1-comment frame → any other comment → the
    raw ID3v1 tail. So if the modern comment lacks codes, the OLD comment is used."""
    if not HAS_MUTAGEN:
        return None
    candidates: list[tuple[int, str]] = []   # (priority, text)
    tags = _id3_of(path, tags)
    if tags is not None:
        for key, frame in tags.items():
            if not key.startswith('COMM') or not getattr(frame, 'text', None):
                continue
            txt = frame.text[0].strip()
            if not txt:
                continue
            desc = (getattr(frame, 'desc', '') or '').lower()
            if any(j in desc for j in _COMMENT_JUNK_DESC):
                continue
            prio = 0 if desc == '' else (1 if 'id3v1' in desc else 2)
            candidates.append((prio, txt))
    v1 = _read_id3v1_comment(path)              # old ID3v1 tail → lowest priority
    if v1:
        candidates.append((3, v1))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    # Prefer the highest-priority comment that actually carries class codes; fall back
    # to the standard (highest-priority) comment when none of them do.
    for _prio, txt in candidates:
        classes, _ = _parse_class_tag(txt)
        if classes:
            return txt
    return candidates[0][1]


# Everything in a comment that is NOT a class code or an instr marker is a free
# marker the user typed: 'vocal_f', 'classic', 'eintanzen', 'langes Vorspiel', …
# ~2800 of 3855 library files carry one, so they are worth keeping — but the same
# field also collects three kinds of noise, which these drop:
#   • the tempo, as a bare number ('29', 'qs-50')  → already in `bpm`
#   • a bare dance code ('rb', 'ww')                → already in `dance`
#   • converter / shop provenance ('www.mediahuman.com', 'made with suno',
#     'converted by convert2mp3.net', 'Erscheinungsdatum 2016')
#   • a release date or an artist credit ('1975 Riccardo Cocciante')
#   • the iTunes gapless blob ('00000000 000002a0 00000768 …'), which lands in
#     the comment field of files that went through iTunes
_TAG_NOISE_RE = re.compile(
    r"""^(?:
          \d+(?:[.,]\d+)?                              # 29, 30.5
        | (?:lw|lwt|tg|ta|ww|vw|sf|sfx|qs|qu|cc|ch|sa|sb|rb|ru|pd|ps|ji|jv)
          [\s\-]?\d*                                   # rb, QS-50
        | (?:www\.|https?://).*                        # www.mediahuman.com
        | (?:converted\s+by|made\s+with)\b.*
        | erscheinung\w*datum\b.*                     # 'erscheinungadatum' too
        | (?:19|20)\d{2}\b.*                          # 1975 Riccardo Cocciante
        | [0-9a-f]{6,}(?:\s+[0-9a-f]{4,})+            # 00000000 000002a0 …
      )$""",
    # DOTALL: the junk is sometimes several lines in one comment field, and a
    # trailing line must not save it from the filter.
    re.IGNORECASE | re.VERBOSE | re.DOTALL)


def is_marker_noise(text: str) -> bool:
    """True for a comment fragment that is not a marker at all — a tempo, a bare
    dance code, converter provenance, a release date or an artist credit, or the
    hex blob iTunes leaves behind."""
    return bool(_TAG_NOISE_RE.match(text.strip().lower()))


def parse_comment_markers(comment: str) -> list[str]:
    """The free markers of a comment, lower-cased, in the order they were typed.

    Class codes, instr words and the noise above are left out — those are already
    carried by `classes_ok` / `is_instrumental` / `bpm` / `dance`."""
    out: list[str] = []
    for part in (p.strip() for p in comment.split(';')):
        if not part or part.upper() in _CLASS_CODES or _ab_classes(part):
            continue
        low = part.lower()
        if low in _INSTR_WORDS or is_marker_noise(low) or low in out:
            continue
        out.append(low)
    return out


def _parse_class_tag(comment: str) -> tuple[list[str] | None, bool]:
    """Parse a comment like 'B;A;S;instr' or 'C;B;A;S;vocal_f;classic'.

    Returns (classes_ok, is_instrumental):
      classes_ok     – list of class codes the song is suited for, or None if
                       the comment contains no class codes at all
      is_instrumental – True when the comment contains 'instr' / 'instrumental'
    """
    parts = [p.strip() for p in comment.split(';') if p.strip()]
    classes: list[str] = []
    for p in parts:
        for code in _ab_classes(p) or ([p.upper()] if p.upper() in _CLASS_CODES else []):
            if code not in classes:
                classes.append(code)
    is_instr  = any(p.lower() in _INSTR_WORDS for p in parts)
    return (classes if classes else None), is_instr


# ── Filename Helpers ───────────────────────────────────────────────────────────
# Matches dance codes directly concatenated with BPM, e.g. (RB24), SF29, QS51
_CODE_BPM_PAT = re.compile(
    r'\b(LW|LWT|TG|TA|WW|VW|SF|SFX|QS|QU|CC|CH|SA|SB|RB|RU|PD|PS|JI|JV)\d{2,3}\b',
    re.IGNORECASE,
)


_CODE_ALIAS: dict[str, str] = {
    'LWT':'LW','TA':'TG','VW':'WW','SFX':'SF','QU':'QS',
    'CH':'CC','SB':'SA','RU':'RB','PS':'PD','JV':'JI',
}


def _detect_dance(name: str) -> str | None:
    for code, pat in DANCE_PATTERNS:
        if pat.search(name):
            return code
    # Fallback: dance code glued directly to BPM digits, e.g. (RB24), SF29
    m = _CODE_BPM_PAT.search(name)
    if m:
        raw = m.group(1).upper()
        return _CODE_ALIAS.get(raw, raw)
    return None


# Quality / round words appended to a dance folder's name ("Samba gut",
# "Samba nicht so gut", "Samba sehr gut") or forming their own subfolders
# inside it ("nicht gut", "vorrunden", "endrunden"). Stripped from the tail
# of a folder name so the dance name underneath still matches.
_FOLDER_QUALIFIER_WORDS = frozenset((
    'gut', 'sehr', 'nicht', 'so', 'schlecht',
    'vorrunde', 'vorrunden', 'endrunde', 'endrunden',
))


def _strip_folder_qualifiers(folded: str) -> str:
    words = folded.split()
    while words and words[-1] in _FOLDER_QUALIFIER_WORDS:
        words.pop()
    return ' '.join(words)


def dance_from_folders(path: Path) -> str | None:
    """Fallback dance detection from the FOLDER structure, for libraries organised
    like  my music/standard/LW/…  instead of tagged files or coded filenames.

    Each parent folder name (deepest first, so the most specific wins) is matched
    whole against the known dance codes and names (GENRE_TO_DANCE — 'LW', 'Samba',
    'Langsamer Walzer', …), accent-folded. A trailing quality/round qualifier is
    stripped before a second try, so 'Samba gut' / 'Samba nicht so gut' match too;
    pure qualifier subfolders ('nicht gut', 'vorrunden', 'endrunden') match
    nothing themselves and the walk simply continues to their dance parent.
    Only consulted when neither the genre tag nor the filename yielded a dance.
    Returns the dance code, or None."""
    for part in reversed(Path(path).parts[:-1]):
        folded = fold_text(part.strip())
        code = GENRE_TO_DANCE.get(folded)
        if code is None:
            code = GENRE_TO_DANCE.get(_strip_folder_qualifiers(folded))
        if code:
            return code
    return None


# Age-class tokens as they appear in playlist names → the GUI age-combo label.
# Order matters: longer / more specific patterns are tried first.
_AGE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Senioren V",   re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)[\s._-]*(?:5|v)\b', re.I)),
    ("Senioren IV",  re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)[\s._-]*(?:4|iv)\b', re.I)),
    ("Senioren III", re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)[\s._-]*(?:3|iii)\b', re.I)),
    ("Senioren II",  re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)[\s._-]*(?:2|ii)\b', re.I)),
    ("Senioren I",   re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)[\s._-]*(?:1|i)\b', re.I)),
    ("Senioren I",   re.compile(r'\b(?:sen(?:ioren)?|mas(?:ters)?)\b', re.I)),   # bare → I
    ("Hauptgruppe",  re.compile(r'\b(?:hauptgruppe|hgr|hauptgr|hg)\b', re.I)),
    ("Jugend",       re.compile(r'\b(?:jugend|jgd|jug)\b', re.I)),
    ("Junioren",     re.compile(r'\b(?:junioren|jun|jr|u21|u16|u14|u12)\b', re.I)),
    ("Kinder",       re.compile(r'\b(?:kinder|kin|kd|u10|u8)\b', re.I)),
]


# Style tokens (filename) → the GUI style-combo label.
_STYLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Latin",    re.compile(r'\b(?:latin|latein|lat)\b', re.I)),
    ("Standard", re.compile(r'\b(?:standard|std|stt|st)\b', re.I)),
]


# Start-class token (filename) → the GUI class-combo letter. Matches an explicit
# "Kl./Klasse/Startklasse X" or the app's own  Age_X_Style  middle field, or a
# bare standalone D/C/B/A/S letter. Style abbreviations (STD/LAT) are stripped first.
_CLASS_EXPLICIT = re.compile(
    r'\b(?:start)?kl(?:asse)?[\s._-]*([sabcd])\b', re.I)


_CLASS_BARE     = re.compile(r'(?<![A-Za-z])([SABCD])(?![A-Za-z])')


_SPACED_SEP_RE = re.compile(r'[._\-]+')
_STYLE_WORDS_RE = re.compile(r'\b(?:latin|latein|lat|standard|std)\b', re.I)


def detect_playlist_meta(name: str) -> dict[str, str | None]:
    """Best-effort age class / start class / dance style from a playlist file name.

    Recognises this app's own  `Age_Class_Style`  export naming plus common
    German tournament conventions (HGR, Sen II, Jun, Kl. A, STD/LAT …). Returns a
    dict with keys 'age', 'cls', 'style' — each None when nothing matched, so the
    caller can keep its existing default for that field."""
    stem = name or ""
    # Strip only a known playlist extension — Path.stem would also truncate at any
    # internal '.' (e.g. "Jugend Kl. D Latein"), losing the class/style tokens.
    low = stem.lower()
    for ext in (".m3u8", ".m3u"):
        if low.endswith(ext):
            stem = stem[:-len(ext)]
            break
    # Spaced-out copy so word boundaries work across _ . - separators too.
    spaced = _SPACED_SEP_RE.sub(' ', stem)

    age = None
    for label, pat in _AGE_PATTERNS:
        if pat.search(spaced):
            age = label
            break

    style = None
    for label, pat in _STYLE_PATTERNS:
        if pat.search(spaced):
            style = label
            break

    cls = None
    m = _CLASS_EXPLICIT.search(spaced)
    if m:
        cls = m.group(1).upper()
    else:
        # Drop style words first so their letters can't masquerade as a class.
        cleaned = _STYLE_WORDS_RE.sub(' ', spaced)
        hits = _CLASS_BARE.findall(cleaned)
        if len(hits) == 1:        # a single unambiguous letter
            cls = hits[0].upper()

    return {"age": age, "cls": cls, "style": style}


# Glued class tokens `detect_playlist_meta` can't see (it needs word boundaries):
#   'DLAT_2' / 'senCLAT' / 'SEN4SSTD'  – class letter fused to the style word
#   'LAT_HGR_c' / 'hgr2CLAT' / 'sen3s' – class letter right after the age group
# Both require tight context (group word / style word adjacent), so a stray letter
# in a normal word can't masquerade as a class.
_CLS_GLUED = (
    re.compile(r'\b(?:hgr|sen)\s*\d?\s*[_\- ]?([dcbas])(?=$|[_\-. ]|lat|std)', re.I),
    re.compile(r'(?:^|[_\-. ])([dcbas])(?:lat|std)', re.I),
)


def _playlist_class_of(m3u: Path) -> str | None:
    """Start class an M3U was run as, parsed from its FILE name — falling back to
    the parent folder name (tournament lists are often organized as
    'HGR S Lat\\Finale.m3u'). None when neither carries a recognizable class."""
    for name in (m3u.name, m3u.parent.name):
        cls = detect_playlist_meta(name)["cls"]
        if cls:
            return cls
        for pat in _CLS_GLUED:
            m = pat.search(name)
            if m:
                return m.group(1).upper()
    return None


def _get_raw_genre_tag(path: Path, tags=_UNREAD) -> str | None:
    """Return the raw TCON genre string from the MP3 ID3 tag, or None."""
    if not HAS_MUTAGEN:
        return None
    tags = _id3_of(path, tags)
    if tags is None:
        return None
    try:
        if 'TCON' in tags:
            return str(tags['TCON']).strip()
    except Exception:
        pass
    return None


def _read_duration(path: Path) -> int:
    """Track length in whole seconds from the audio header (0 = unknown).

    Uses mutagen's generic File so it works for any format in the library;
    the MPEG header parse is cheap (no frame decoding)."""
    if not HAS_MUTAGEN:
        return 0
    try:
        audio = MutagenFile(path)
        if audio is not None and audio.info is not None:
            return int(round(audio.info.length))
    except Exception:
        pass
    return 0


# POPM (Popularimeter) ratings, 0–255. Windows Explorer / Media Player write the
# stars as 1/64/128/196/255 under this e-mail; other programs use their own e-mail
# (Songs-DB: 'no@email') and the same scale, so any POPM counts.
_WMP_POPM_EMAIL = 'Windows Media Player 9 Series'
_STARS_POPM = {1: 1, 2: 64, 3: 128, 4: 196, 5: 255}


def stars_popm(stars: int) -> int:
    """1–5 stars → the POPM byte Windows writes for them."""
    return _STARS_POPM[stars]


def popm_stars(tags) -> int | None:
    """1–5 stars from the file's POPM frames, or None when it is unrated.

    The Windows frame wins when there are several; otherwise the highest rating.
    The bands follow Windows' own reading of a raw byte (1–31 = ★, 32–95 = ★★, …)."""
    if tags is None:
        return None
    try:
        frames = tags.getall('POPM')
    except Exception:
        return None
    rated = [f for f in frames if getattr(f, 'rating', 0)]
    if not rated:
        return None
    wmp = [f for f in rated if f.email == _WMP_POPM_EMAIL]
    raw = (wmp or [max(rated, key=lambda f: f.rating)])[0].rating
    return 1 if raw < 32 else 2 if raw < 96 else 3 if raw < 160 else 4 if raw < 224 else 5


def _get_title_artist_tags(path: Path, tags=_UNREAD) -> tuple[str | None, str | None, str | None]:
    """Return (ID3 title TIT2, artist TPE1, album TALB) for the file, or (None, None, None)."""
    if not HAS_MUTAGEN:
        return None, None, None
    tags = _id3_of(path, tags)
    if tags is None:
        return None, None, None
    try:
        title = str(tags['TIT2']).strip() if 'TIT2' in tags else None
        artist = str(tags['TPE1']).strip() if 'TPE1' in tags else None
        album = str(tags['TALB']).strip() if 'TALB' in tags else None
        return (title or None), (artist or None), (album or None)
    except Exception:
        return None, None, None


def _get_tag_bpm(path: Path) -> float | None:
    """Return the ID3 BPM frame (TBPM) as a float, or None. This is the BPM written
    into the file's metadata (typically beats/min, as DJ tools store it) — distinct
    from the tempo encoded in the file NAME and from a measured tempo."""
    if not HAS_MUTAGEN:
        return None
    try:
        tags = ID3(path)
        if 'TBPM' in tags:
            val = str(tags['TBPM']).strip()
            return float(val) if val else None
    except Exception:
        return None
    return None


_YEAR_PAT = re.compile(r'\b(19[3-9]\d|20[0-4]\d)\b')


def _detect_year(name: str, path: Path, tags=_UNREAD) -> int | None:
    """Best-effort release year: ID3 year tag first, then a 4-digit year in the filename."""
    tags = _id3_of(path, tags) if HAS_MUTAGEN else None
    if tags is not None:
        try:
            for key in ('TDRC', 'TYER', 'TDOR', 'TORY', 'TDRL'):
                if key in tags:
                    m = _YEAR_PAT.search(str(tags[key]))
                    if m:
                        return int(m.group(1))
        except Exception:
            pass
    m = _YEAR_PAT.search(name)
    return int(m.group(1)) if m else None


_XMAS_NAME_PAT = re.compile(
    r'christmas|weihnacht|jingle.bell|silent.night|santa|rudolph|frosty|'
    r'sleigh|advent|heilige.nacht|stille.nacht|oh.tannenbaum|navidad|noel|'
    r'feliz.natal|buon.natale|kerst',
    re.IGNORECASE,
)


def _is_christmas(filename_stem: str, genre_tag: str) -> bool:
    """Return True for Christmas/seasonal songs that should not appear in playlists."""
    genre_l = genre_tag.lower()
    if 'weihn' in genre_l or genre_l == 'xmas':
        return True
    return bool(_XMAS_NAME_PAT.search(filename_stem))


# Dance abbreviations (codes) and full dance names used to ANCHOR a tempo number in a
# filename. SW = Slow Waltz, WA = Walzer, JV = Jive (all map to a valid bars/min).
_DANCE_CODE_RE = r'LW|TG|TA|WW|VW|WV|SF|QS|QU|CC|SA|SB|RB|RU|PD|JI|SW|WA|JV'


# Full names (DE + EN), longest/multi-word variants first so e.g. 'slow foxtrot' wins over
# 'fox'. '[\s-]*' between words so 'slow-foxtrot' / 'cha-cha' parse like spaced forms.
_DANCE_NAME_RE = (
    r'slow[\s-]*fox(?:trot)?|slowfox|langsamer?[\s-]*foxtrott?|'
    r'slow[\s-]*walt?z|slowwalt?z|langsamer?[\s-]*walzer|langs\.?[\s-]*walzer|'
    r'viennese[\s-]*waltz|wiener[\s-]*walzer|'
    r'quick[\s-]*step|paso[\s-]*doble|pasodoble|'
    r'cha[\s-]*cha(?:[\s-]*cha)?|chacha|'
    r'tango|samba|rumba|jive'
)


# Compiled once (not per `_detect_bpm` call — the same 13-pattern list used to be
# rebuilt from source strings and recompiled on every call, which is most of every
# library scan's regex time).
_BPM_PATTERNS = [re.compile(pat, re.IGNORECASE) for pat in [
    # Glued UPPERCASE 'T' tempo marker, e.g. '...CattailsT28', 'Diosa marinaT32'
    # — no word boundary before the T, so the '\b'-anchored pattern below misses it.
    # (?-i:...) forces an uppercase T so it never fires on a lowercase 't' in a word.
    r'(?-i:[A-Z]{0,3}T)(\d{2,3})(?:\D|$)',
    r'\b(?:[A-Z]{0,3}[Tt])(\d{2,3})(?:[^0-9]|$)',
    # Parenthetical "(<dance name> <bpm>)" — the name may be MULTIPLE words, so
    # '(Slow Waltz 29)' / '(Paso Doble 60)' parse like '(Samba 50)' / '(LW 29)'.
    r'\(\s*[A-Za-z][A-Za-z.\s]*?\s+(\d{2,3})\s*\)',
    # Parenthetical with a '-' separator and/or a trailing 'TM'/'T_M'/'bpm'
    # tournament-tempo marker, e.g. '(Langsamer Walzer 29 TM)', '(Tango - 33 T_M)',
    # '(Samba 51 TM)' — anchored to a known dance name so a catalog number can't slip in.
    r'\(\s*(?:' + _DANCE_NAME_RE + r')[A-Za-z._\s-]*?(\d{2,3})\s*(?:T[\s_]?M|bpm)?\s*\)',
    # Bare parenthetical tempo, e.g. 'viennese waltz(58)' — the dance word sits
    # OUTSIDE the parens so the number stands alone inside them.
    r'\(\s*(\d{2,3})\s*\)',
    # Bracketed takt with a trailing 'TM'/'T_M'/'bpm' marker, e.g. '[31 TM]'
    # (the dance name sits in a separate '(Slow Waltz)' group). The marker is
    # REQUIRED — a bare '[31]' is a track number, not a takt.
    r'\[\s*(\d{2,3})\s*(?:T[\s_]?M|bpm)\s*\]',
    r'(\d{2,3})[\s-]*bpm',
    # Dance CODE + optional '-'/space separator + number, tolerating a glued suffix
    # after the number (the trailing '(?!\d)' replaces a '\b' that fails when a letter
    # is fused on), e.g. '[TG-32]', 'WW-59', 'Rb 25gepitched', 'sb51andV', 'sw29', 'WA29'.
    # No leading '\b' on purpose, so a code fused onto a word ('…ChernyeWW58') still parses.
    # '_' is allowed as a separator too, e.g. 'PD_58' / 'JI_42' (the '(?!\d)' still
    # blocks a 4-digit year like 'RB_2024' from reading as a takt).
    r'(?:' + _DANCE_CODE_RE + r')[\s_-]*(\d{2,3})(?!\d)',
    # Parenthetical NUMBER + dance code (the reverse order), e.g. '(29 SF)',
    # '(58VW)' glued, and '(29W)' where a lone 'W' = Walzer. Kept inside parens on
    # purpose: a bare 'NN CODE' at a name's start is a TRACK NUMBER + dance folder
    # code ('63 RU El Reloj', '16 LW …'), NOT a takt, so it must not match here.
    r'\(\s*(\d{2,3})[\s-]*(?:' + _DANCE_CODE_RE + r'|W)\s*\)',
    # 'CH' is the ChaCha code but too common a letter pair to drop into the
    # boundary-less alternation above (it would let 'March 31' read as bpm 31).
    # Anchor it to a word start so only 'CH31' / 'CH 31' / 'CH-31' parse.
    r'\bCH[\s-]*(\d{2,3})(?!\d)',
    # Lone single-letter dance codes glued to a takt: 'W29' (Walzer/Slow Waltz),
    # 'Q50' (Quickstep), 'J43' (Jive). Forced UPPERCASE + word-anchored + glued
    # (no separator) so a lowercase letter inside a word, or a spaced 'W 29'
    # coincidence, can't fire — single letters are far too common to allow loosely.
    # 'DJ50' is safe: there's no word boundary before the 'J' in 'DJ'.
    r'\b(?-i:[WQJLR])(\d{2,3})(?!\d)',
    # Full dance NAME + number (glued or separated), e.g. 'Tango32', 'Samba50',
    # 'ChaCha 30', 'Rumba 25', 'slow-foxtrot-28'.
    r'\b(?:' + _DANCE_NAME_RE + r')[\s-]*(\d{2,3})(?!\d)',
    # Pitched-edit takt: '…_cut_pitch_24.5', '…pitch 27' — these are tempo-shifted
    # versions whose trailing number is the resulting takt. Anchored to 'pitch' so a
    # bare decimal can't slip in; the integer part is kept (.5 truncates harmlessly).
    r'pitch[\s_-]*(\d{2,3})',
]]


def _detect_bpm(name: str) -> int | None:
    for pat in _BPM_PATTERNS:
        for m in pat.finditer(name):
            bpm = int(m.group(1))
            # Floor at 15 (not 20) so slow 'Nicht TSO Turniertempo' versions — e.g. a
            # Rumba at 19 bars/min — are PARSED, hence get tempo-filtered out, instead of
            # reading as bpm=None and slipping past the in-tempo filter as 'unknown'.
            # finditer (not search): skip an out-of-range first hit and keep looking, so
            # e.g. a track-number 'WW 10 … vw59' yields 59, not None.
            if 15 <= bpm <= 70:
                return bpm
    return None


def _detect_bpm_tagged(stem: str, tag_title: str | None) -> int | None:
    """BPM from the filename, falling back to the ID3 title tag when the file
    name carries no readable tempo. Covers files whose name was truncated (e.g.
    '...(RB 2.mp3') while the full '(RB 25)' survives in the title tag."""
    bpm = _detect_bpm(stem)
    if bpm is None and tag_title:
        bpm = _detect_bpm(tag_title)
    return bpm


# Compiled once — `_clean_title` runs on every filename during a scan, and re.sub()
# with a raw pattern string still pays a cache-lookup on every call even when the
# compiled pattern itself is cached.
_CT_LEAD_NUM = re.compile(r'^\d+(?:[.\-_]\d+)*[.\-_\s]+')
_CT_LEAD_CODE = re.compile(r'^(?:' + _DANCE_CODE_RE + r')\s+', re.IGNORECASE)
_CT_GLUED_T_UPPER = re.compile(r'(?-i:[A-Z]{0,3}T)\d{2,3}\w*')
_CT_GLUED_T = re.compile(r'\b[A-Z]{0,3}[Tt]\d{2,3}\w*')
_CT_PAREN_TEMPO = re.compile(
    r'\(\s*[A-Za-z][A-Za-z.\s-]*?\s+\d{2,3}\s*(?:T[\s_]?M|bpm)?\s*\)', re.IGNORECASE)
_CT_PAREN_NUM = re.compile(r'\(\s*\d{2,3}\s*\)')
_CT_BPM_SUFFIX = re.compile(r'\d{2,3}[\s-]*bpm\b', re.IGNORECASE)
_CT_CODE_NUM = re.compile(
    r'\b(?:' + _DANCE_CODE_RE + r')[\s-]*\d{2,3}[a-z]*\b', re.IGNORECASE)
_CT_NAME_NUM = re.compile(
    r'\b(?:' + _DANCE_NAME_RE + r')[\s-]*\d{2,3}[a-z]*\b', re.IGNORECASE)
_CT_EDIT_MARKERS = re.compile(
    r'(_cut|_gepitched.*|normalisiert|andV|dpit|andereVersion|pitch|downpitch|tempoangepasst)',
    re.IGNORECASE)
_CT_EMPTY_BRACKETS = re.compile(r'[(\[]\s*[)\]]')
_CT_MULTI_WS = re.compile(r'[\s_]{2,}')


def _clean_title(name: str) -> str:
    # Leading track number, incl. a disc-track token like '1-11' / '02-01' / '3.07'
    # (numbers joined by . - _ ). Space-joined numbers are NOT swallowed, so a title
    # such as '05 1 2 3 4' keeps its '1 2 3 4' after the '05' track number goes.
    name = _CT_LEAD_NUM.sub('', name)
    name = _CT_LEAD_CODE.sub('', name)
    name = _CT_GLUED_T_UPPER.sub('', name)
    name = _CT_GLUED_T.sub('', name)
    # Parenthetical tempo tag, incl. a '-' separator and trailing 'TM'/'T_M'/'bpm'.
    name = _CT_PAREN_TEMPO.sub('', name)
    name = _CT_PAREN_NUM.sub('', name)
    name = _CT_BPM_SUFFIX.sub('', name)
    # Inline 'CODE[-/ ]NN' / 'Name NN' tempo tags (with any glued pitch suffix).
    name = _CT_CODE_NUM.sub('', name)
    name = _CT_NAME_NUM.sub('', name)
    name = _CT_EDIT_MARKERS.sub('', name)
    # Drop now-empty brackets left behind after stripping a glued tempo tag, e.g. '()' / '[]'.
    name = _CT_EMPTY_BRACKETS.sub('', name)
    name = _CT_MULTI_WS.sub(' ', name)
    return name.strip(' -_|')


_TRAILING_COPY_NUM_RE = re.compile(r'\s+\d{1,2}$')
_TAG_AFTER_BRACKET_RE = re.compile(r'[)\]]\s*\d{1,2}$')
_ALL_DIGITS_WS_RE = re.compile(r'[\d\s]+')
# A store-download slug: no spaces, at least one '_' or '-' between word parts.
_SLUG_STEM_RE = re.compile(r'[^\s_-]+(?:[_-]+[^\s_-]+)+')


def _title_for(stem: str, tag_title: str | None = None) -> str:
    """Display title for a track. Starts from the cleaned filename, then resolves a
    trailing bare copy index that the cleaner leaves behind (e.g. '16-Timber (Sf29) 1'
    → 'Timber 1'): if in the original filename that number sat right after a ()/[]
    tempo tag it's a copy index and dropped; otherwise the ID3 title tag is preferred
    when it carries a real (non-numeric) title.

    A slug filename (no spaces, words glued by '_' or '-', as store downloads come)
    was never named by hand, so a spaced ID3 title wins over it."""
    t = _clean_title(stem)
    if _SLUG_STEM_RE.fullmatch(stem.strip()):
        tt = _clean_title(tag_title or '')
        if ' ' in tt and not _ALL_DIGITS_WS_RE.fullmatch(tt):
            return tt
    if _TRAILING_COPY_NUM_RE.search(t):
        if _TAG_AFTER_BRACKET_RE.search(stem):
            stripped = _TRAILING_COPY_NUM_RE.sub('', t).strip()
            if stripped:
                return stripped
        tt = _clean_title(tag_title or '')
        if tt and not _ALL_DIGITS_WS_RE.fullmatch(tt):
            return tt
    return t


def _tempo_lo(dance: str, dance_class: str) -> int:
    """Return the standard minimum BPM for this dance + class."""
    lo, _ = TEMPO_RANGES.get(dance, {}).get(dance_class, (20, 70))
    return lo


def _fmt_bpm(bpm: int | None, dance: str, dance_class: str) -> str:
    """Format BPM tag; adds * if below the class minimum (needs pitching)."""
    if bpm is None:
        return " [?BPM]"
    star = "*" if bpm < _tempo_lo(dance, dance_class) else ""
    return f" [T{bpm}{star}]"


def _bpm_fit(bpm: int | None, lo: int, hi: int) -> float:
    if bpm is None:
        return 0.4
    if lo <= bpm <= hi:
        ideal = (lo + hi) / 2
        return 1.0 - abs(bpm - ideal) / max(1, hi - lo)
    return 0.0


_NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')


def _norm_title(s: str) -> str:
    # Transliterate accents to ASCII first (é→e, ó→o, ñ→n…) so a title tagged
    # 'Ai Que Dó' and a filename 'Ai Que Do' normalise to the SAME key — otherwise
    # the accented char was dropped wholesale ('dó'→'d') and the two never matched.
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return _NON_ALNUM_RE.sub(' ', s).strip()
