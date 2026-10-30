"""Data models & dance configuration for the Dancesport Playlist Planner.

Extracted from dancesport_planner.py (logical split): the static dance/style
tables, the RoundConfig / MusicEntry dataclasses, the ScanCancelled signal and
the Playlist type alias. Pure data; safe to import from any planner leaf module.
"""
import os
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from planner.dances import TEMPO_RANGES  # noqa: F401  (re-exported)
from planner.music.analysis import AudioFeatures

# ── Dance Configuration ────────────────────────────────────────────────────────
DANCE_NAMES = {
    'LW': 'Langsamer Walzer', 'TG': 'Tango', 'WW': 'Wiener Walzer',
    'SF': 'Slowfox', 'QS': 'Quickstep', 'CC': 'Cha-Cha',
    'SA': 'Samba', 'RB': 'Rumba', 'PD': 'Paso Doble',
    'JI': 'Jive',
    # 'Others' (social / non-tournament) dance codes – see OTHERS_DANCES
    'SALSA': 'Salsa', 'DISCOFOX': 'Discofox', 'BACHATA': 'Bachata',
    'WCS': 'West Coast Swing', 'KIZOMBA': 'Kizomba', 'FORRO': 'Forró',
    'TANGOARG': 'Tango Argentino',
    # Boogie Woogie and Line Dance are social dances with a code of their own,
    # but they don't sit in the ETDS warm-up rotation (WARMUP_MODE): an evening
    # plays them as they come, not in alternating rounds.
    'BW': 'Boogie Woogie', 'LD': 'Line Dance',
}


DANCE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('LW', re.compile(r'\b(LW|Slow[-_\s]?Waltz|Langsamer[-_\s]?Walzer|LWT)\b', re.IGNORECASE)),
    ('TG', re.compile(r'\b(TG|TA|Tango)\b', re.IGNORECASE)),
    ('WW', re.compile(r'\b(WW|VW|Viennese|Wiener[-_\s]?Walzer|VienneseWaltz)\b', re.IGNORECASE)),
    ('SF', re.compile(r'\b(SF|SFX|Slowfox|Slow[-_\s]?Fox|Foxtrot)\b', re.IGNORECASE)),
    ('QS', re.compile(r'\b(QS|Qs|QU|Quickstep)\b', re.IGNORECASE)),
    ('CC', re.compile(r'\b(CC|CH|CHA|Cha[-_\s]?Cha)\b', re.IGNORECASE)),
    ('SA', re.compile(r'\b(SA|SB|Samba)\b', re.IGNORECASE)),
    ('RB', re.compile(r'\b(RB|RU|Rumba)\b', re.IGNORECASE)),
    ('PD', re.compile(r'\b(PD|PS|Paso[-_\s]?Doble|Pasodoble)\b', re.IGNORECASE)),
    ('JI', re.compile(r'\b(JI|JV|Jive)\b', re.IGNORECASE)),
]


# Map ID3 TCON genre tag values → dance codes (case-insensitive lookup)
GENRE_TO_DANCE: dict[str, str] = {
    'lw': 'LW', 'lwt': 'LW', 'sw': 'LW', 'slow waltz': 'LW', 'langsamer walzer': 'LW',
    'tg': 'TG', 'ta': 'TG', 'tango': 'TG',
    'ww': 'WW', 'vw': 'WW', 'viennese waltz': 'WW', 'wiener walzer': 'WW',
    'sf': 'SF', 'sfx': 'SF', 'slowfox': 'SF', 'slow fox': 'SF', 'foxtrot': 'SF',
    'qs': 'QS', 'qu': 'QS', 'quickstep': 'QS',
    'cc': 'CC', 'cha': 'CC', 'cha-cha': 'CC', 'cha cha': 'CC',
    'sa': 'SA', 'sb': 'SA', 'samba': 'SA',
    'rb': 'RB', 'ru': 'RB', 'rumba': 'RB',
    'pd': 'PD', 'ps': 'PD', 'paso doble': 'PD', 'pasodoble': 'PD', 'paso': 'PD',
    'ji': 'JI', 'jv': 'JI', 'jive': 'JI',
    # Christmas / seasonal variants  (e.g. Weihn.Ji, Weihn.Qs, WW/Weihn.)
    'weihn.lw': 'LW', 'weihn.tg': 'TG', 'ww/weihn.': 'WW',
    'weihn.sf': 'SF', 'weihn.qs': 'QS', 'weihn.qs;qs;qu': 'QS',
    'weihn.ji': 'JI',
    # Compound tags
    'tg;show': 'TG',
}


# Non-competition genres shown in the library overview but never used for playlists.
# Keys are lowercase raw genre tag values.
OTHER_GENRE_LABELS: dict[str, str] = {
    'df': 'Discofox',
    'bw': 'Boogie Woogie',
    'ld': 'Line Dance',
    'sl': 'Salsa',
    'bc': 'Bachata',
    'bac': 'Bachata',
    'wcs': 'West Coast Swing',
    'kz': 'Kizomba',
    'background': 'Background',
    'special': 'Special',
    'jingle': 'Jingle',
    'einleitung': 'Einleitung',
    'einmarsch': 'Einmarsch',
    'marsch': 'Marsch',
    'fanfare/tusch': 'Fanfare/Tusch',
    'tango arg.': 'Tango Argentino',
    'forro': 'Forró',   # genre lookups are accent-folded ('Forró' → 'forro')
    'xmas': 'Weihnachten',
    'misc': 'Sonstiges',
    'test': 'Test',
}


# 🎚 Where inside its TSO band the 🎚 button pitches a heat — ⚙ Settings →
# 🎛 Play sets, one choice per dance.
class TsoBand(StrEnum):
    """Which takt of its TSO band a dance is pitched to.

    A StrEnum, not a bare `str`: the four spellings are stored in the settings
    file, are the combos' item data and are compared by hand in `tso_band_of`
    and `tso_band_target`. Keeping them equal to those spellings leaves a
    saved setting and the combos' data untouched."""
    MEAN = "mean"
    LOWER = "lower"
    MIDDLE = "middle"
    UPPER = "upper"

    @classmethod
    def of(cls, value: object) -> TsoBand:
        """A band from a value read off the settings file. A hand-edited one
        can hold a spelling this version does not know; the mean is what the
        button did before the setting existed."""
        try:
            return cls(str(value))
        except ValueError:
            return cls.MEAN


TSO_BANDS = tuple(TsoBand)


def takt_counts(bpms) -> dict[int, int]:
    """How many titles of a round sit on each whole takt.

    A round is danced at ONE tempo, and which one it asks for is read off the
    takte its titles are recorded at — a measured tenth counts towards the takt
    it is nearest, a title without a tempo counts for nothing."""
    counts: dict[int, int] = {}
    for b in bpms:
        if b:
            takt = int(b + 0.5)
            counts[takt] = counts.get(takt, 0) + 1
    return counts


# 🎚 A whole takt is only worth pitching where the step stays near the ~2% a
# floor does not feel: it is 3.4% at T29, already 3.6% at T28, 4.2% at T24.
MAX_WHOLE_TAKT_PITCH = 0.035


def _leading_takt(counts: dict[int, int]) -> int | None:
    """The takt more titles of the round sit on than on any other, None on a
    tie."""
    most = max(counts.values())
    lead = [takt for takt, n in counts.items() if n == most]
    return lead[0] if len(lead) == 1 else None


def round_takt_target(counts: dict[int, int], lo: float | None = None,
                      hi: float | None = None) -> float:
    """The one takt a round is danced at, from `takt_counts`.

    Where the takt MOST of the round is on sits ONE takt from the rest and
    that step is cheap enough (`MAX_WHOLE_TAKT_PITCH`), the round joins it:
    T50+T51+T51 Sambas are danced at 51, T30+T31+T31 Cha-Chas at 31. It works
    downwards just as well — nine T50 Sambas against three T51 are danced at
    50, the three braking 2% — but not where the step costs more than the
    thumb rule: T24+T25+T25 Rumbas would each have to give 4.2% for one.

    Everything else meets in the middle of the buckets, every title moving:
    a takt TWO steps off the majority is too far to join, so T50+T52+T52
    Quicksteps are danced at 51 and T58+T58+T60 Viennese at 59; T58+T59+T60
    Paso Dobles have no majority at all and meet at 59; T28+T29+T29 Slow Foxes
    cannot afford the takt and meet at 28.5. Titles recorded OUTSIDE the TSO
    band (a T27 Slow Fox) are left out of that middle — they are pulled into
    the band on their own and should not drag the round down after them.

    How many titles a bucket holds only decides which takt leads: the middle
    is of the TAKTE, not of the titles. Averaging the titles let the copies
    vote — five T25 against one T24 came out at 24.7, which is neither takt
    and no middle either.
    """
    if not counts:
        return 0.0
    lead = _leading_takt(counts)
    if lead is not None and lead > 1:
        others = [takt for takt in counts if takt != lead]
        if (others and set(others) <= {lead - 1, lead + 1}
                and 1 / min(others) <= MAX_WHOLE_TAKT_PITCH):
            return float(lead)
    takte = [takt for takt in counts
             if (lo is None or takt >= lo) and (hi is None or takt <= hi)]
    takte = takte or list(counts)
    return sum(takte) / len(takte)


def tso_band_target(lo: float, hi: float, mean: float,
                    band: TsoBand | str) -> float:
    """The tempo the 🎚 TSO button pitches every title of a heat to.

    `TsoBand.MEAN` is what the button has always done: keep the heat's own
    average and only pull it into the TSO band, so a round recorded at 25 is
    danced at 25. The three fixed points put the whole dance on one takt
    instead — the bottom of the band, its middle, or the top. Worth setting on
    the slow dances: one takt out of 24 is twice the pitch shift one takt out
    of 50 is, and it is heard on the voice.
    """
    band = TsoBand.of(band)
    if band == TsoBand.LOWER:
        return float(lo)
    if band == TsoBand.MIDDLE:
        return (lo + hi) / 2
    if band == TsoBand.UPPER:
        return float(hi)
    return min(max(mean, lo), hi)


# D-class: 4 dances; C and above: 5 dances
DEFAULT_DANCES: dict[str, dict[str, list[str]]] = {
    'Standard': {
        'D': ['LW','TG','SF','QS'],
        'C': ['LW','TG','WW','SF','QS'], 'B': ['LW','TG','WW','SF','QS'],
        'A': ['LW','TG','WW','SF','QS'], 'S': ['LW','TG','WW','SF','QS'],
    },
    'Latin': {
        'D': ['SA','CC','RB','JI'],
        'C': ['SA','CC','RB','PD','JI'], 'B': ['SA','CC','RB','PD','JI'],
        'A': ['SA','CC','RB','PD','JI'], 'S': ['SA','CC','RB','PD','JI'],
    },
    # 'Others' – social dances. No real class distinction, so every class offers
    # the same dances (the class combo just doesn't constrain them).
    'Others': {
        cls: ['SALSA','DISCOFOX','BACHATA','WCS','KIZOMBA','FORRO','TANGOARG']
        for cls in ('D','C','B','A','S')
    },
}


DANCE_STYLES = ('Standard', 'Latin', 'Others')


def style_covers_dances(style: str, dances) -> bool:
    """True when every dance code fits `style`'s widest (S-class) checkbox list, i.e.
    the panel can actually show + check all of them under that style."""
    sset = set(DEFAULT_DANCES.get(style, {}).get("S", []))
    return all(d in sset for d in (dances or []))


def best_style_for_dances(dances) -> str | None:
    """Pick the style whose S-class dance set covers the most of `dances` — used to
    keep the panel's style in step with a deck's actual dances when they disagree."""
    best, score = None, -1
    for st in DANCE_STYLES:
        sset = set(DEFAULT_DANCES.get(st, {}).get("S", []))
        n = sum(1 for d in (dances or []) if d in sset)
        if n > score:
            best, score = st, n
    return best


# Which top-level library folder(s) each competition style draws from. A track
# only enters a style's pool when it lives under the matching folder, so a
# CC-detected track sitting in a social-dance folder (discofox / salsa / …) can
# never pollute a Standard or Latin competition pool. Matched case-insensitively
# against the file's path segments. 'Others' is the complement (everything NOT
# under a Standard/Latin folder).
STYLE_FOLDERS: dict[str, tuple[str, ...]] = {
    'Standard': ('standardcd',),
    'Latin': ('lateincd',),
}


RESERVED_STYLE_FOLDERS = {f for fs in STYLE_FOLDERS.values() for f in fs}


# Folder names (case-insensitive) whose tracks are never used in any pool — junk,
# duplicates or non-danceable material that would otherwise slip into 'Others'.
# Tracks under these folders are skipped at scan time (never enter the library).
EXCLUDED_FOLDERS = {'sox', 'unbearbeitet'}


# Non-tournament library CATEGORIES (a soft exclude, unlike _EXCLUDED_FOLDERS):
# tracks in these folders STILL load into the library — searchable and browsable
# in the library view, fine for parties — but are kept OUT of playlist GENERATION
# pools, exactly like the per-file is_xmas flag. Each category id maps to a display
# label and the folder names that belong to it (matched case-insensitively as exact
# path segments). The library browser offers these as a "category" filter.
LIBRARY_CATEGORIES: dict[str, tuple[str, tuple[str, ...]]] = {
    'seasonal': ('🎄 Seasonal / Christmas',
                 ('christmas', 'weihnachten', 'xmas')),
    'anthems': ('🎺 Anthems',
                ('hymnen', 'hymnen wdsf')),
    'background': ('🎶 Background / non-dance',
                   # 'special' is the umbrella these live under: openings,
                   # fanfares, award and Ausmarsch music. It used to be a HARD
                   # skip, so its ~130 loose files never reached the library at
                   # all — now they load, browsable, still out of generation.
                   ('special', 'musikbett', 'hintergrundmusik',
                    'background dancecomp 2025', 'happy bithday dances')),
    'wrong_tempo': ('⏱️ Wrong tempo / not tournament',
                    ('nicht turnier', 'nicht tso turniertempo',
                     'gut aber kein turnier', 'gut aber nicht turnier',
                     'unangepasst', 'unagepasste versionen', 'unsicher')),
    'duplicates': ('👥 Duplicates / raw versions',
                   ('doppelte musikdatein', 'doppeltvlt', 'orig', 'original',
                    'originale', 'converted', 'einpegelung', 'sample', 'samples')),
    # Not a folder either: entrance and award music, by the words and folders
    # set in ⚙ Settings → 📁 Paths (is_ceremony below).
    'ceremony': ('🏅 Background: entrance & awards', ()),
    # Not a folder: a competition title whose comment carries no class tag
    # (library_category below). No folder names, so it never matches a path.
    'no_class': ('🏷 No class', ()),
}

# Whether the MAIN library uses class tags at all. Without any, 'no_class' would
# take every title out of generation, so the category only applies once one
# title carries a class. Set by whoever owns the main library (the window's
# library load, the CLI scan) and by an in-app tag edit — never by a plain
# MusicLibrary load: the whole-repo index is a library too.
_class_tags_in_use = False


def note_class_tag_use(entries) -> None:
    global _class_tags_in_use
    _class_tags_in_use = any(getattr(e, 'classes_ok', None) for e in entries)


# Whether 'no_class' titles also stay out of GENERATION. Off by default: the
# category is there to find them in the library pane; leaving them out of the
# playlists is the user's call (⚙ Settings → General, 'exclude_no_class').
_exclude_no_class = False


def set_no_class_exclusion(on) -> None:
    global _exclude_no_class
    _exclude_no_class = bool(on)


# 🙈 Folders the operator hid (⚙ Settings → 📁 Paths, 'hidden_folders'): titles
# below them stay out of every library, like _EXCLUDED_FOLDERS but by path.
_hidden_folders: tuple[str, ...] = ()


def _path_key(path) -> str:
    return os.path.normcase(os.path.normpath(str(path).strip()))


def set_hidden_folders(folders) -> None:
    global _hidden_folders
    keys = (_path_key(f) for f in folders or () if str(f).strip())
    _hidden_folders = tuple(k if k.endswith(os.sep) else k + os.sep for k in keys)


def is_hidden_path(path) -> bool:
    if not _hidden_folders:
        return False
    return _path_key(path).startswith(_hidden_folders)

# 🏅 Entrance (Einmarsch) and award (Siegerehrung) music, ⚙ Settings → 📁 Paths:
# one of these words in the file or folder name, the title or the comment tag,
# or a title below one of the folders named there ('ceremony_words',
# 'ceremony_folders').
CEREMONY_WORDS = ('Einmarsch', 'Siegerehrung', 'Entrance', 'Award', 'Ceremony')
_ceremony_words: tuple[str, ...] = tuple(w.lower() for w in CEREMONY_WORDS)
_ceremony_folders: tuple[str, ...] = ()


def ceremony_words_of(settings: dict) -> list[str]:
    """The 🏅 words as set, the built-in ones while none were ever saved."""
    words = (settings or {}).get('ceremony_words')
    return list(CEREMONY_WORDS) if words is None else [str(w) for w in words]


def set_ceremony_match(words, folders) -> None:
    global _ceremony_words, _ceremony_folders
    _ceremony_words = tuple(fold_text(str(w).strip()) for w in words or ()
                            if str(w).strip())
    keys = (_path_key(f) for f in folders or () if str(f).strip())
    _ceremony_folders = tuple(k if k.endswith(os.sep) else k + os.sep for k in keys)


def is_ceremony(entry) -> bool:
    if _ceremony_folders and _path_key(entry.path).startswith(_ceremony_folders):
        return True
    if not _ceremony_words:
        return False
    text = _folded_names(str(entry.path), entry.title, getattr(entry, 'tag_title', None),
                         getattr(entry, 'tag_comment', None))
    return any(w in text for w in _ceremony_words)


@lru_cache(maxsize=65536)
def _folded_names(*names) -> str:
    """The names to look for 🏅 words in, folded once: every generation pool
    asks each title again."""
    return fold_text(' '.join(filter(None, names)))


# Flat lookup: lowercased folder name → category id.
_FOLDER_CATEGORY = {f: cid for cid, (_lbl, folders) in LIBRARY_CATEGORIES.items()
                    for f in folders}

# A comment marker naming a category puts the title in it, whatever folder it
# lies in. The names are the filter's own, English and German — not the folder
# words: 'special' and 'original' already mark tournament covers.
_MARKER_CATEGORY = {
    'seasonal': 'seasonal', 'christmas': 'seasonal',
    'saison': 'seasonal', 'weihnachten': 'seasonal',
    'anthems': 'anthems', 'hymnen': 'anthems',
    'background': 'background', 'non-dance': 'background',
    'hintergrund': 'background', 'kein tanz': 'background',
    'wrong tempo': 'wrong_tempo', 'not tournament': 'wrong_tempo',
    'falsches tempo': 'wrong_tempo', 'kein turnier': 'wrong_tempo',
    'duplicates': 'duplicates', 'raw versions': 'duplicates',
    'doppelte': 'duplicates', 'rohfassungen': 'duplicates',
}


def folder_category_of_parts(parts) -> str:
    """Soft category id implied by a sequence of folder segments ('' = none).
    The deepest matching segment wins. Used by the scanner to let category
    folders (anthems / background / seasonal …) survive the special/christmas
    hard-skip so they load browsable, and shared by library_category below."""
    for part in reversed(parts):
        cid = _FOLDER_CATEGORY.get(part.lower())
        if cid:
            return cid
    return ''


def library_category(entry) -> str:
    """Non-tournament category id of a library entry ('' = a normal tournament
    track). A comment marker naming a category comes first (_MARKER_CATEGORY),
    then 🏅 entrance and award music (is_ceremony), then the deepest
    matching folder segment of the path; a christmas
    track flagged per-file (is_xmas) counts as 'seasonal' even outside a christmas
    folder. A competition title without a class tag is 'no_class' while the
    library uses class tags (note_class_tag_use); social dances have no
    classes and never are. Drives the browser filter and, through
    is_non_turnier, the generation soft-exclude."""
    for marker in getattr(entry, 'comment_tags', None) or ():
        cid = _MARKER_CATEGORY.get(marker)
        if cid:
            return cid
    if is_ceremony(entry):
        return 'ceremony'
    cid = folder_category_of_parts(entry.path.parts[:-1])
    if cid:
        return cid
    if getattr(entry, 'is_xmas', False):
        return 'seasonal'
    if (_class_tags_in_use and entry.dance in TEMPO_RANGES
            and not getattr(entry, 'classes_ok', None)):
        return 'no_class'
    return ''


def is_non_turnier(entry) -> bool:
    """True → keep this entry out of GENERATION pools (it still lives in the
    library and stays browsable). Mirrors the is_xmas soft exclude. A
    'no_class' title only when set_no_class_exclusion asked for it."""
    cid = library_category(entry)
    if cid == 'no_class':
        return _exclude_no_class
    return bool(cid)


# 'Others' dance code → keyword fragments that identify it in a path / filename.
# Dedicated folders (salsa/, discofox/, …) match exactly; longer keywords also
# match as a substring so tracks inside mixed-compilation folders
# (e.g. SalsaDiscofoxTangoArgBachataCD) get classified by their filename.
OTHERS_DANCES: dict[str, dict[str, tuple[str, ...]]] = {
    'SALSA': {'keys': ('salsa',)},
    'DISCOFOX': {'keys': ('discofox', 'disco fox', 'df')},
    'BACHATA': {'keys': ('bachata',)},
    'WCS': {'keys': ('wcs', 'westcoast', 'west coast')},
    'KIZOMBA': {'keys': ('kizomba',)},
    'FORRO': {'keys': ('forro',)},   # matching is accent-folded (Forro with any accent)
    'TANGOARG': {'keys': ('argtango', 'tangoarg', 'tango arg', 'argentino')},
    'BW': {'keys': ('boogie woogie', 'boogie', 'bw')},
    'LD': {'keys': ('line dance', 'linedance', 'ld')},
}


def fold_text(s: str) -> str:
    """Accent-insensitive lowercase: 'Forró' → 'forro' — regardless of whether
    the source uses a precomposed ó (NFC) or o + combining accent (NFD, common
    on files that passed through macOS)."""
    return ''.join(ch for ch in unicodedata.normalize('NFKD', s.lower())
                   if not unicodedata.combining(ch))


ROUND_NAMES: dict[int, list[str]] = {
    1: ['Finale'],
    2: ['Vorrunde', 'Finale'],
    3: ['Vorrunde', 'Zwischenrunde', 'Finale'],
    4: ['Vorrunde', '1. Zwischenrunde', 'Semifinale', 'Finale'],
    5: ['Vorrunde', '1. Zwischenrunde', '2. Zwischenrunde', 'Semifinale', 'Finale'],
    6: ['Vorrunde', '1. Zwischenrunde', '2. Zwischenrunde', '3. Zwischenrunde', 'Semifinale', 'Finale'],
    7: ['Vorrunde', '1. Zwischenrunde', '2. Zwischenrunde', '3. Zwischenrunde', '4. Zwischenrunde', 'Semifinale', 'Finale'],
}


def default_round_name(i: int) -> str:
    """The name of round `i`, counted 0-based, where `ROUND_NAMES` names no
    round for the count — a list of eight rounds, or a warm-up that is no
    competition at all. The deck, the CLI and the m3u import all fall back to
    these, and the name goes into the playlist, so it has to be written once."""
    return f"Runde {i + 1}"


def round_names(n: int) -> list[str]:
    """The names of `n` rounds: the standard progression where there is one
    for that count, plainly numbered past it."""
    names = ROUND_NAMES.get(n)
    return list(names) if names else [default_round_name(i) for i in range(n)]


# Paso Doble is allowed to repeat across rounds (limited library)
ALLOW_REPEAT = {'PD'}


# Dances where songs slightly below the standard minimum tempo are allowed.
# They are included in suggestions but marked with * (need on-the-fly pitch-up).
# Value = how many BPM below the minimum are still acceptable.
#   TG: min is 31 → T30 included with *
#   JI: min is 42 → T41 included with *
# (RB/PD dropped: their TSO windows themselves moved down to 24-26 / 58-60,
#  no extra margin.)
BELOW_TEMPO_EXT: dict[str, int] = {'TG': 1, 'JI': 1}


# ── Theme Mode ─────────────────────────────────────────────────────────────────
# Mood grouping by dance, used to filter theme playlists ('slow' vs 'fast').
SLOW_DANCES = {'LW', 'WW', 'SF', 'RB'}


FAST_DANCES = {'TG', 'QS', 'CC', 'SA', 'PD', 'JI'}


# ── Data Classes ───────────────────────────────────────────────────────────────
class RoundTier(StrEnum):
    """Where a round sits in the ladder, back from the final.

    A StrEnum, not a bare `str`: it compares equal to the plain spelling, so a
    saved session, an .m3u header or a test's `tier="final"` still match, and
    `json.dump` writes it back out as that string."""
    EARLY = "early"
    PRE_SEMI = "pre_semi"
    SEMI = "semi"
    FINAL = "final"

    @classmethod
    def of(cls, value: object) -> RoundTier:
        """A tier from a value read off disk. A session saved by an older
        version can hold "" or a spelling this one dropped, and the round
        still needs a tier — the earliest is the safe reading."""
        try:
            return cls(str(value))
        except ValueError:
            return cls.EARLY


def tier_by_position(i: int, n: int) -> RoundTier:
    """The tier of round `i` of `n`, counted back from the final — the one
    ladder `rounds_from_pattern`, the m3u import and the dynamic deck all lay
    down, so a '6-3-2-1' pattern and a six-round import agree."""
    if i == n - 1:
        return RoundTier.FINAL
    if i == n - 2:
        return RoundTier.SEMI
    if i == n - 3:
        return RoundTier.PRE_SEMI
    return RoundTier.EARLY


class Strategy(StrEnum):
    """Which songs a round may draw from — see `planner.generate.scoring`.

    The five pool strategies were spelled `'proven'` / `'top_proven'` /
    `'fresh'` / `'mixed'` / `'all'` by hand wherever one was compared, defaulted
    or read back off a saved deck. A StrEnum keeps every one of those spellings
    working (it compares equal to it, hashes to it and `json.dump`s back out as
    it), so a restored session, an .m3u header and the combo's item data all
    stay as they were.

    `DEFAULT` is the empty string and means "no strategy chosen": the round
    takes its tier's natural pick (`resolve_strategy`). It is falsy, so the
    `rc.strategy or None` reads that used to spot that case still spot it."""
    DEFAULT = ""
    PROVEN = "proven"
    TOP_PROVEN = "top_proven"
    FRESH = "fresh"
    MIXED = "mixed"
    ALL = "all"

    @classmethod
    def of(cls, value: object) -> Strategy:
        """A strategy from a value that came from outside — a restored deck, a
        combo's item data. A deck saved by an older version can hold "" or a
        spelling this one dropped; no strategy chosen is the safe reading."""
        try:
            return cls(str(value))
        except ValueError:
            return cls.DEFAULT


@dataclass(slots=True)
class RoundConfig:
    name: str
    heats: int
    tier: RoundTier
    prefer_fresh: bool = False  # legacy: True = prefer unused; False = prefer proven
    strategy: Strategy = Strategy.DEFAULT  # DEFAULT → derive from tier/prefer_fresh


def rounds_from_pattern(raw: str) -> list[RoundConfig]:
    """Parse a heat-count pattern like ``6-3-2-1`` (also comma / space separated)
    into named RoundConfigs with tiers assigned back-to-front (final, semi,
    pre_semi, early…). Empty list when the pattern is invalid."""
    parts = re.split(r"[-,\s]+", (raw or "").strip())
    try:
        counts = [int(p) for p in parts if p]
        if not counts or not all(1 <= c <= 30 for c in counts):
            return []
    except ValueError:
        return []
    n = len(counts)
    names = round_names(n)
    cfgs = []
    for i, (name, heats) in enumerate(zip(names, counts, strict=True)):
        tier = tier_by_position(i, n)
        cfgs.append(RoundConfig(
            name=name, heats=heats, tier=tier,
            prefer_fresh=(tier == RoundTier.PRE_SEMI),
        ))
    return cfgs


@dataclass(slots=True)
class MusicEntry:
    path: Path
    title: str
    dance: str | None = None
    bpm: int | None = None  # from filename
    year: int | None = None  # from ID3 year tag (TDRC/TYER) or filename
    duration: int = 0
    popularity: int = 0
    source_info: str = ""  # M3U files this song appeared in
    cluster: str = ""  # parent folder (for coarse similarity)
    other_genre: str | None = None  # display label when dance is a non-competition genre
    classes_ok: list[str] | None = None  # class codes from COMM tag, e.g. ['B','A','S']
    comment_tags: list[str] | None = None  # free COMM markers, e.g. ['vocal_f','classic']
    rating: int | None = None  # 1–5 stars (POPM), None = unrated
    custom: str | None = None  # the free Custom field (planner.music.custom_field)
    tag_edits: dict | None = None  # file values of fields an in-app tag edit overrides
    tag_title: str | None = None  # ID3 TIT2 title (for renamed-file playlist matching)
    tag_artist: str | None = None  # ID3 TPE1 artist (for renamed-file playlist matching)
    tag_album: str | None = None  # ID3 TALB album (shown in hover info)
    tag_comment: str | None = None  # the COMM text as written ('vocal AS'), '' = none
    tag_bpm: float | None = None  # ID3 TBPM as written (usually beats/min), None = no tag
    tag_genre: str | None = None  # raw ID3 TCON text - the Dance column's last fallback
    is_instrumental: bool = False  # True when COMM tag or filename marks 'instr'
    audio_instr_prob: float | None = None  # learned from audio (planner.music.vocals), None = unknown
    vocal_share: float | None = None  # measured Demucs vocal-stem energy share, None = not measured
    is_xmas: bool = False  # True → Christmas song, excluded from playlists
    features: AudioFeatures | None = None
    replay_sources: list[str] | None = None  # 'Past Competitions': relevant M3Us (parent/stem)
    class_plays: dict[str, int] | None = None  # start class → distinct playlists played in
    final_plays: int = 0  # of those playlists, how many played it in the FINAL round
    semi_plays: int = 0   # …and how many in the SEMIFINAL — the other round that matters
    added: float | None = None  # file creation time (unix) — when it entered the library
    last_played: int | None = None  # newest year among the playlists it appears in

    def __post_init__(self):
        # The scan caches mark "probed, the header gives no length" as -1 so
        # the file is not probed again; an entry has no length to show.
        if self.duration and self.duration < 0:
            self.duration = 0


class ScanCancelled(Exception):
    """Raised by scan()/analysis when the caller's should_cancel predicate fires."""


# ── Playlist Suggester ─────────────────────────────────────────────────────────
# Type alias: round_name → list-of-heats → songs-per-dance
Playlist = dict[str, list[list[MusicEntry | None]]]


# ── Tournament-day deck stacking ────────────────────────────────────────────────
# A day with more competitions than free decks stacks several competitions into
# one deck: dance columns become the ordered union, round names get the
# competition label as prefix (visible in the grid headers), and per-round
# skip/context maps keep rendering, ↺ regeneration and export per-competition.

_DAY_COMP_SEP = " — "   # between competition label and round name


def merge_day_playlists(comps: list[dict]) -> tuple[
        Playlist, list[str], list[RoundConfig], dict[str, set], dict[str, dict]]:
    """Stack several generated competitions into ONE deck-loadable playlist.

    Each comp dict needs: label, playlist, dances, rounds, cls, style.
    Returns (merged_playlist, union_dances, merged_rounds, round_skip_dances,
    round_ctx) where round_ctx maps every merged round name to
    {"comp": label, "cls": ..., "style": ...} so regeneration and export can
    recover the competition each round belongs to."""
    union: list[str] = []
    for c in comps:
        for d in c["dances"]:
            if d not in union:
                union.append(d)

    merged: Playlist = {}
    rounds: list[RoundConfig] = []
    skip: dict[str, set] = {}
    ctx: dict[str, dict] = {}
    labels_seen: dict[str, int] = {}
    for c in comps:
        # Two identical competitions on one day (e.g. same class, two patterns)
        # would collide on label AND round names → number the later ones.
        n = labels_seen.get(c["label"], 0) + 1
        labels_seen[c["label"]] = n
        label = c["label"] if n == 1 else f"{c['label']} ({n})"
        idx = [union.index(d) for d in c["dances"]]
        absent = {d for d in union if d not in c["dances"]}
        for rc in c["rounds"]:
            name = f"{label}{_DAY_COMP_SEP}{rc.name}"
            rounds.append(RoundConfig(
                name=name, heats=rc.heats, tier=rc.tier,
                prefer_fresh=rc.prefer_fresh, strategy=rc.strategy))
            heats = c["playlist"].get(rc.name) or []
            new_heats = []
            for heat in heats:
                row: list[MusicEntry | None] = [None] * len(union)
                for i, e in enumerate(heat):
                    row[idx[i]] = e
                new_heats.append(row)
            merged[name] = new_heats
            if absent:
                skip[name] = set(absent)
            ctx[name] = {"comp": label, "cls": c["cls"], "style": c["style"]}
    return merged, union, rounds, skip, ctx


def split_day_rounds(rounds_data: list[dict], dances: list[str]) -> list[dict]:
    """Regroup a SERIALIZED stacked-deck grid into per-competition chunks.

    rounds_data is the "rounds" list of a serialized deck (name/heats/grid/
    skip_dances/ctx per round, grid d-indices into `dances`). Returns one dict
    per competition — {"comp", "cls", "dances", "rounds"} with round names
    stripped back to plain (Vorrunde/Finale/…) and grids re-indexed into the
    competition's own dance list — or [] when the deck holds at most one
    competition (export it as-is)."""
    comps = [((r.get("ctx") or {}).get("comp")) for r in rounds_data]
    if len({c for c in comps if c}) < 2:
        return []
    groups: list[dict] = []
    cur: dict | None = None
    remap: dict[int, int] = {}
    for r, comp in zip(rounds_data, comps, strict=True):
        rctx = r.get("ctx") or {}
        if cur is None or comp != cur["comp"]:
            skip = set(r.get("skip_dances") or [])
            comp_dances = [d for d in dances if d not in skip]
            remap = {i: comp_dances.index(d)
                     for i, d in enumerate(dances) if d not in skip}
            cur = {"comp": comp or "Playlist",
                   "cls": rctx.get("cls") or "",
                   "dances": comp_dances, "rounds": []}
            groups.append(cur)
        prefix = f"{cur['comp']}{_DAY_COMP_SEP}"
        name = r.get("name", "")
        plain = name[len(prefix):] if name.startswith(prefix) else name
        grid = {}
        for h, hcol in (r.get("grid") or {}).items():
            grid[h] = {str(remap[int(d)]): p for d, p in hcol.items()
                       if int(d) in remap}
        cur["rounds"].append({"name": plain,
                              "tier": RoundTier.of(r.get("tier")),
                              "heats": int(r.get("heats", 1)), "grid": grid})
    return groups
