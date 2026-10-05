"""Data models & dance configuration for the Dancesport Playlist Planner.

Extracted from dancesport_planner.py (logical split): the static dance/style
tables, the RoundConfig / MusicEntry dataclasses, the ScanCancelled signal and
the Playlist type alias. Pure data; safe to import from any planner leaf module.
"""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from planner.db import AudioFeatures


# ── Dance Configuration ────────────────────────────────────────────────────────
DANCE_NAMES = {
    'LW': 'Langsamer Walzer', 'TG': 'Tango',    'WW': 'Wiener Walzer',
    'SF': 'Slowfox',          'QS': 'Quickstep', 'CC': 'Cha-Cha',
    'SA': 'Samba',            'RB': 'Rumba',     'PD': 'Paso Doble',
    'JI': 'Jive',
    # 'Others' (social / non-tournament) dance codes – see OTHERS_DANCES
    'SALSA': 'Salsa',   'DISCOFOX': 'Discofox', 'BACHATA': 'Bachata',
    'WCS': 'West Coast Swing', 'KIZOMBA': 'Kizomba', 'FORRO': 'Forró',
    'TANGOARG': 'Tango Argentino',
}


DANCE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('LW', re.compile(r'\b(LW|Slow[-_\s]?Waltz|Langsamer[-_\s]?Walzer|LWT)\b', re.IGNORECASE)),
    ('TG', re.compile(r'\b(TG|TA|Tango)\b',                                     re.IGNORECASE)),
    ('WW', re.compile(r'\b(WW|VW|Viennese|Wiener[-_\s]?Walzer|VienneseWaltz)\b',re.IGNORECASE)),
    ('SF', re.compile(r'\b(SF|SFX|Slowfox|Slow[-_\s]?Fox|Foxtrot)\b',           re.IGNORECASE)),
    ('QS', re.compile(r'\b(QS|Qs|QU|Quickstep)\b',                              re.IGNORECASE)),
    ('CC', re.compile(r'\b(CC|CH|CHA|Cha[-_\s]?Cha)\b',                         re.IGNORECASE)),
    ('SA', re.compile(r'\b(SA|SB|Samba)\b',                                     re.IGNORECASE)),
    ('RB', re.compile(r'\b(RB|RU|Rumba)\b',                                     re.IGNORECASE)),
    ('PD', re.compile(r'\b(PD|PS|Paso[-_\s]?Doble|Pasodoble)\b',                re.IGNORECASE)),
    ('JI', re.compile(r'\b(JI|JV|Jive)\b',                                      re.IGNORECASE)),
]


# Map ID3 TCON genre tag values → dance codes (case-insensitive lookup)
GENRE_TO_DANCE: dict[str, str] = {
    'lw': 'LW', 'lwt': 'LW', 'slow waltz': 'LW', 'langsamer walzer': 'LW',
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
    'df':            'Discofox',
    'bw':            'Boogie Woogie',
    'sl':            'Salsa',
    'bc':            'Bachata',
    'bac':           'Bachata',
    'wcs':           'West Coast Swing',
    'kz':            'Kizomba',
    'background':    'Background',
    'special':       'Special',
    'jingle':        'Jingle',
    'einleitung':    'Einleitung',
    'einmarsch':     'Einmarsch',
    'marsch':        'Marsch',
    'fanfare/tusch': 'Fanfare/Tusch',
    'tango arg.':    'Tango Argentino',
    'forro':         'Forró',   # genre lookups are accent-folded ('Forró' → 'forro')
    'xmas':          'Weihnachten',
    'misc':          'Sonstiges',
    'test':          'Test',
}


# Tempo ranges (bars per minute) – same for all age classes and all start classes.
# Songs outside this range but within BELOW_TEMPO_EXT are still allowed, marked *.
TEMPO_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    'LW': {'D': (28,30),'C': (28,30),'B': (28,30),'A': (28,30),'S': (28,30)},
    'TG': {'D': (31,33),'C': (31,33),'B': (31,33),'A': (31,33),'S': (31,33)},
    'WW': {'D': (58,60),'C': (58,60),'B': (58,60),'A': (58,60),'S': (58,60)},
    'SF': {'D': (28,30),'C': (28,30),'B': (28,30),'A': (28,30),'S': (28,30)},
    'QS': {'D': (50,52),'C': (50,52),'B': (50,52),'A': (50,52),'S': (50,52)},
    'CC': {'D': (30,32),'C': (30,32),'B': (30,32),'A': (30,32),'S': (30,32)},
    'SA': {'D': (50,52),'C': (50,52),'B': (50,52),'A': (50,52),'S': (50,52)},
    'RB': {'D': (24,26),'C': (24,26),'B': (24,26),'A': (24,26),'S': (24,26)},
    'PD': {'D': (58,60),'C': (58,60),'B': (58,60),'A': (58,60),'S': (58,60)},
    'JI': {'D': (41,43),'C': (41,43),'B': (41,43),'A': (41,43),'S': (41,43)},
}


# 🎚 Where inside its TSO band the 🎚 button pitches a heat — ⚙ Settings →
# 🎛 Play sets, one choice per dance.
TSO_BANDS = ("mean", "lower", "middle", "upper")


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


def tso_band_target(lo: float, hi: float, mean: float, band: str) -> float:
    """The tempo the 🎚 TSO button pitches every title of a heat to.

    'mean' is what the button has always done: keep the heat's own average and
    only pull it into the TSO band, so a round recorded at 25 is danced at 25.
    The three fixed points put the whole dance on one takt instead — the bottom
    of the band, its middle, or the top. Worth setting on the slow dances: one
    takt out of 24 is twice the pitch shift one takt out of 50 is, and it is
    heard on the voice.
    """
    if band == "lower":
        return float(lo)
    if band == "middle":
        return (lo + hi) / 2
    if band == "upper":
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


def best_style_for_dances(dances):
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
    'Latin':    ('lateincd',),
}


_RESERVED_STYLE_FOLDERS = {f for fs in STYLE_FOLDERS.values() for f in fs}


# Folder names (case-insensitive) whose tracks are never used in any pool — junk,
# duplicates or non-danceable material that would otherwise slip into 'Others'.
# Tracks under these folders are skipped at scan time (never enter the library).
_EXCLUDED_FOLDERS = {'sox', 'unbearbeitet'}


# Non-tournament library CATEGORIES (a soft exclude, unlike _EXCLUDED_FOLDERS):
# tracks in these folders STILL load into the library — searchable and browsable
# in the library view, fine for parties — but are kept OUT of playlist GENERATION
# pools, exactly like the per-file is_xmas flag. Each category id maps to a display
# label and the folder names that belong to it (matched case-insensitively as exact
# path segments). The library browser offers these as a "category" filter.
LIBRARY_CATEGORIES: dict[str, tuple[str, tuple[str, ...]]] = {
    'seasonal':    ('🎄 Seasonal / Christmas',
                    ('christmas', 'weihnachten', 'xmas')),
    'anthems':     ('🎺 Anthems',
                    ('hymnen', 'hymnen wdsf')),
    'background':  ('🎶 Background / non-dance',
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
    'duplicates':  ('👥 Duplicates / raw versions',
                    ('doppelte musikdatein', 'doppeltvlt', 'orig', 'original',
                     'originale', 'converted', 'einpegelung', 'sample', 'samples')),
}

# Flat lookup: lowercased folder name → category id.
_FOLDER_CATEGORY = {f: cid for cid, (_lbl, folders) in LIBRARY_CATEGORIES.items()
                    for f in folders}


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
    track). The deepest matching folder segment of the path wins; a christmas
    track flagged per-file (is_xmas) counts as 'seasonal' even outside a christmas
    folder. Drives both the generation soft-exclude and the browser filter."""
    cid = folder_category_of_parts(entry.path.parts[:-1])
    if cid:
        return cid
    if getattr(entry, 'is_xmas', False):
        return 'seasonal'
    return ''


def is_non_turnier(entry) -> bool:
    """True → keep this entry out of GENERATION pools (it still lives in the
    library and stays browsable). Mirrors the is_xmas soft exclude."""
    return bool(library_category(entry))


# 'Others' dance code → keyword fragments that identify it in a path / filename.
# Dedicated folders (salsa/, discofox/, …) match exactly; longer keywords also
# match as a substring so tracks inside mixed-compilation folders
# (e.g. SalsaDiscofoxTangoArgBachataCD) get classified by their filename.
OTHERS_DANCES: dict[str, dict[str, tuple[str, ...]]] = {
    'SALSA':    {'keys': ('salsa',)},
    'DISCOFOX': {'keys': ('discofox', 'disco fox', 'df')},
    'BACHATA':  {'keys': ('bachata',)},
    'WCS':      {'keys': ('wcs', 'westcoast', 'west coast')},
    'KIZOMBA':  {'keys': ('kizomba',)},
    'FORRO':    {'keys': ('forro',)},   # matching is accent-folded (Forro with any accent)
    'TANGOARG': {'keys': ('argtango', 'tangoarg', 'tango arg', 'argentino')},
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


# Paso Doble is allowed to repeat across rounds (limited library)
ALLOW_REPEAT = {'PD'}


# Dances where songs slightly below the standard minimum tempo are allowed.
# They are included in suggestions but marked with * (need on-the-fly pitch-up).
# Value = how many BPM below the minimum are still acceptable.
#   TG: min is 31 → T30 included with *
#   JI: min is 41 → T40 included with *
# (RB/PD dropped: their TSO windows themselves moved down to 24-26 / 58-60,
#  no extra margin.)
BELOW_TEMPO_EXT: dict[str, int] = {'TG': 1, 'JI': 1}


# ── Theme Mode ─────────────────────────────────────────────────────────────────
# Mood grouping by dance, used to filter theme playlists ('slow' vs 'fast').
SLOW_DANCES = {'LW', 'WW', 'SF', 'RB'}


FAST_DANCES = {'TG', 'QS', 'CC', 'SA', 'PD', 'JI'}


# ── Data Classes ───────────────────────────────────────────────────────────────
@dataclass
class RoundConfig:
    name: str
    heats: int
    tier: str  # 'early' | 'pre_semi' | 'semi' | 'final'
    prefer_fresh: bool = False  # legacy: True = prefer unused; False = prefer proven
    strategy: str = ""  # one of STRATEGIES; "" → derive from tier/prefer_fresh


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
    names = ROUND_NAMES.get(n, [f"Runde {i + 1}" for i in range(n)])
    cfgs = []
    for i, (name, heats) in enumerate(zip(names, counts)):
        tier = (
            "final"    if i == n - 1 else
            "semi"     if i == n - 2 else
            "pre_semi" if i == n - 3 else
            "early"
        )
        cfgs.append(RoundConfig(
            name=name, heats=heats, tier=tier,
            prefer_fresh=(tier == "pre_semi"),
        ))
    return cfgs


@dataclass
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
    custom: str | None = None  # the free Custom field (planner.custom_field)
    tag_edits: dict | None = None  # file values of fields an in-app tag edit overrides
    tag_title: str | None = None  # ID3 TIT2 title (for renamed-file playlist matching)
    tag_artist: str | None = None  # ID3 TPE1 artist (for renamed-file playlist matching)
    tag_album: str | None = None  # ID3 TALB album (shown in hover info)
    is_instrumental: bool = False  # True when COMM tag or filename marks 'instr'
    audio_instr_prob: float | None = None  # learned from audio (planner.vocals), None = unknown
    vocal_share: float | None = None  # measured Demucs vocal-stem energy share, None = not measured
    sim_score: float | None = None  # timbral similarity to round anchor (set at pick-time)
    is_xmas: bool = False  # True → Christmas song, excluded from playlists
    features: AudioFeatures | None = None
    replay_sources: list[str] | None = None  # 'Past Competitions': relevant M3Us (parent/stem)
    class_plays: dict[str, int] | None = None  # start class → distinct playlists played in
    final_plays: int = 0  # of those playlists, how many played it in the FINAL round
    semi_plays: int = 0   # …and how many in the SEMIFINAL — the other round that matters
    added: float | None = None  # file creation time (unix) — when it entered the library
    last_played: int | None = None  # newest year among the playlists it appears in


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
    for r, comp in zip(rounds_data, comps):
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
        cur["rounds"].append({"name": plain, "tier": r.get("tier", "early"),
                              "heats": int(r.get("heats", 1)), "grid": grid})
    return groups
