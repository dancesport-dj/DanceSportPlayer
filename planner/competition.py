"""Competition-schedule parsing & playlist matching for 'Past Competitions' mode.

Extracted from dancesport_planner.py (logical split): the superseded-playlist
filter (so old/dumped lists never feed popularity), round-stage detection and
the CompetitionSpec parser that maps a pasted schedule onto stored M3U files.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from planner.config import PLAYLIST_DIR
from planner.models import DEFAULT_DANCES
from planner.parsing import _CODE_ALIAS


# ── Superseded-playlist filter ───────────────────────────────────────────────────
# Old / replaced playlists are parked in folders named "alt" / "alte" / "old"
# (German "alt" = old), in dated archive dirs like "07.8.2011alt", or saved as
# files with an "_alt" suffix. They must NOT feed popularity / replay learning.
#
# "alt" / "alte" / "alter" counts only as a word of its own (see `_starts_word` /
# `_ends_word`): alt, alte, alter stand, ..._alt, ...2011alt, STDalt, _alteListe —
# not the letters inside Walter, Altenkirchen or Abschlussveranstaltung. "old" is
# matched as a whole segment only.
_OLD_MARKER_RE = re.compile(r'alt(?:er|e)?', re.IGNORECASE)


def _starts_word(seg: str, i: int) -> bool:
    """Does the marker at seg[i] begin a word of its own? At the start, after a
    separator or digit, as a camelCase hump (neuAlle, latRest) or glued to an
    acronym (STDalt) — not inside an ordinary word (Walter, Ballett, Halle)."""
    if i == 0 or not seg[i - 1].isalpha():
        return True
    if seg[i].isupper() and seg[i - 1].islower():
        return True
    # Both letters: " H".isupper() is True, which would make " Halle" an acronym.
    return (seg[i].islower() and i >= 2
            and seg[i - 2].isupper() and seg[i - 1].isupper())


def _ends_word(seg: str, j: int) -> bool:
    """Does the marker ending before seg[j] end a word (alteListe counts as two)?"""
    return (j == len(seg) or not seg[j].isalpha()
            or (seg[j].isupper() and seg[j - 1].islower()))


def _has_old_marker(seg: str) -> bool:
    return any(_starts_word(seg, m.start()) and _ends_word(seg, m.end())
               for m in _OLD_MARKER_RE.finditer(seg))


# Stem tokens (separator-split) that mark a working "holding bin" rather than a
# played event set: new / unsorted dumps, a generic "liste", an "all" collection
# (LAT_ALL / liste_all), or a "ball" social set. Matched per token so words like
# Galaball / Ballhaus / Neustadt survive.
_HOLDING_BIN_TOKENS = {'neu', 'neue', 'new', 'neustd', 'neulat', 'liste', 'all', 'ball'}


# Lowercase words that name a dance or a style. A playlist whose stem is made up
# ONLY of these (plus numbers / separators) is a per-dance / per-style collection
# dump ("Jive", "Jive_2", "LAT_Jive", "Tango Standard") — not a played event set —
# so it must not feed popularity. Mixed names ("Jive Hits 2018") keep their non-
# dance token and survive.
_DANCE_WORDS = {
    'lw', 'tg', 'ta', 'ww', 'vw', 'sf', 'sfx', 'qs', 'qu', 'cc', 'cha',
    'sa', 'sb', 'rb', 'ru', 'pd', 'ps', 'ji', 'jv',
    'jive', 'tango', 'rumba', 'samba', 'quickstep', 'slowfox', 'foxtrot',
    'paso', 'doble', 'pasodoble', 'walzer', 'langsamer', 'wiener', 'viennese',
    'waltz', 'slow', 'fox', 'chacha', 'rhumba',
    'std', 'standard', 'lat', 'latein', 'latin', 'others', 'social',
}


def _is_superseded_playlist(m3u: Path) -> bool:
    """True if `m3u` (relative to PLAYLIST_DIR) is an old / replaced / auto-dumped
    playlist that must NOT feed popularity / replay learning.

    Excluded when:
      • any directory segment or the filename stem is an "old" marker
        (alt/alte/old/…_alt/…2011alt) — see `_has_old_marker`; or
      • the filename is a software dump / combined collection: stem starts with
        "Export" (ExportM3U / ExportUnused / ExportParty / …), or contains the
        "all songs" token "alle" (alle / alleSTD / ALLE_LAT / neuAlleLAT / …),
        or a merge token "zusammen" / "merged" (musik_zusammen_einfach /
        latein_merged_pre_6 / …). "alle" and "rest" count as words only
        (`_starts_word`), so Halle, Ballett and Bukarest survive; or
      • the filename is a working "holding bin" rather than a played set: a token
        "neu" / "neue" / "new" (newly-added, not yet placed), "(un)sortiert" /
        "zu_sortieren" (to be sorted), a generic "liste", an "all" collection
        (LAT_ALL / liste_all), a "ball" social set, or a "reserve" list, e.g.
        neu_r / zu_sortieren / unsortiert_LAT / liste_all / Ball_2019 / Reserve_STD.
        Matched per token so city names like Neuss / Neustadt / Neujahr and words
        like Galaball / Ballhaus survive; or
      • the file is a working draft rather than a played set: its stem or one of
        its folders carries a working marker (Standard_filter_final, gesamt.m3u,
        standard_pre_4, Vorsortierungen/LW_pre.m3u) — see `_has_working_marker`.
        These pools hold the whole pre-selection, so counting them would mark a
        few hundred never-danced titles as played; or
      • the stem is named ONLY after dances / styles (per-dance collection dump):
        "Jive", "Jive_2", "LAT_Jive", "Tango Standard" — see `_DANCE_WORDS`.
        Mixed names like "Jive Hits 2018" keep a non-dance token and survive.
        These bins would otherwise inflate popularity and wrongly mark genuinely
        fresh (never-played) songs as 'proven'.
    """
    try:
        rel = m3u.relative_to(PLAYLIST_DIR)
    except ValueError:
        rel = m3u
    for part in list(rel.parent.parts) + [rel.stem]:
        seg = part.strip()
        if seg.lower() == 'old' or _has_old_marker(seg):
            return True
    stem = rel.stem.strip()
    name = stem.lower()
    if name.startswith('export'):
        return True
    if 'zusammen' in name or 'merged' in name:
        return True
    if "komplett" in name or any(_starts_word(stem, m.start())
                                 for m in re.finditer(r'alll?e', stem, re.IGNORECASE)):
        return True
    # A "rest" list — but not a name that merely ends in -rest (Bukarest, Forrest).
    if any(_starts_word(stem, m.start()) or not _ends_word(stem, m.end())
           for m in re.finditer(r'rest', stem, re.IGNORECASE)):
        return True
    if _has_working_marker(name) or is_working_collection_path(m3u):
        return True
    tokens = re.split(r'[_\s\-.]+', name)
    if any(t in _HOLDING_BIN_TOKENS
           or t.startswith(('sortier', 'unsortier', 'reserve', 'vorsort'))
           for t in tokens):
        return True
    # Per-dance / per-style collection dumps named ONLY after dances/styles.
    alpha = [t for t in tokens if t and not t.isdigit()]
    if alpha and all(t in _DANCE_WORDS for t in alpha):
        return True
    return False


# Canonical category id → all filename / label tokens that mean it. SEN and MAS are
# the SAME category (renamed); WO = World Open; RIS = Rising Stars.
_COMP_CATEGORY_SYNONYMS: dict[str, set[str]] = {
    'SEN': {'SEN', 'MAS', 'SENIOR', 'SENIOREN', 'MASTER', 'MASTERS'},
    'HGR':    {'HGR', 'HG', 'HAUPTGRUPPE', 'ADULT'},
    'U21':    {'U21'},
    'RIS':    {'RIS', 'RISING', 'RISINGSTARS'},
    'WO':     {'WO', 'WORLD', 'WORLDOPEN'},
    'YOUTH':  {'YOUTH', 'JUGEND', 'JGD', 'JUG', 'TEEN', 'TEENS'},
    'JUN':    {'JUN', 'JUNIOR', 'JUNIOREN'},
    'KIN':    {'KIN', 'KINDER', 'KIDS', 'BAMBINI', 'BAMBINIS'},
    'JJ':     {'JJ', 'JNJ'},
}


_COMP_TOKEN_TO_CAT: dict[str, str] = {
    tok: cat for cat, toks in _COMP_CATEGORY_SYNONYMS.items() for tok in toks
}


_COMP_STYLE_TOKENS: dict[str, str] = {
    'STD': 'Standard', 'STANDARD': 'Standard',
    'LAT': 'Latin', 'LATEIN': 'Latin',
}


_ROMAN_LEVELS = {'I', 'II', 'III', 'IV', 'V'}


# 'J & J', 'J&J', 'Jack and Jill', 'JACK_AND_JILL' — all one category token.
_JJ_RE = re.compile(
    r'\bJ\s*(?:&|\+|and|und|n)\s*J\b|jack[\s_\-]*(?:&|and|und|n)?[\s_\-]*jill',
    re.IGNORECASE)


def _comp_tokens(text: str) -> list[str]:
    """Uppercase alphanumeric tokens of a label / filename stem, split on any
    non-alphanumeric run, so 'MAS_I_A_LAT' → ['MAS','I','A','LAT'] while 'U21'
    stays one token. Every spelling of Jack and Jill becomes 'JJ'."""
    text = _JJ_RE.sub(' JJ ', text)
    return [t.upper() for t in re.split(r'[^A-Za-z0-9]+', text) if t]


def is_side_list(stem: str) -> bool:
    """A warm-up, party or Christmas list kept beside the competition lists."""
    name = stem.lower()
    return any(w in name for w in
               ('eintanzen', 'party', 'weihn', 'christmas', 'xmas'))


_COMP_CLASS_LETTERS = ('S', 'A', 'B', 'C', 'D')


def comp_class(stem: str) -> str | None:
    """Start class (S/A/B/C/D) named in a competition filename/label, or None.

    WDSF competitions are danced at S level, so a 'WDSF' token reads as 'S'. Handles
    both separated ('SEN I A LAT' → 'A') and glued ('CLAT', 'DSTD' → 'C'/'D') forms."""
    toks = _comp_tokens(stem)
    if 'WDSF' in toks:
        return 'S'
    for t in toks:
        if t in _COMP_CLASS_LETTERS:
            return t
        if len(t) > 1 and t[0] in _COMP_CLASS_LETTERS and t[1:] in _COMP_STYLE_TOKENS:
            return t[0]               # glued class+style: CLAT / DSTD / ASTD
    return None


def comp_type_tokens(text: str) -> set[str]:
    """Distinctive identity tokens of a competition label/filename — canonical
    category (SEN/HGR/JUN…), roman level (I/II…) and 'WDSF'. Used to spot an EXACT
    competition-type match; style and class letters are intentionally excluded."""
    out: set[str] = set()
    for t in _comp_tokens(text):
        if t in _COMP_TOKEN_TO_CAT:
            out.add(_COMP_TOKEN_TO_CAT[t])
        elif t in _ROMAN_LEVELS:
            out.add(t)
        elif t == 'WDSF':
            out.add('WDSF')
    return out


def slot_history_score(file_stem: str, deck_class: str | None,
                       deck_type_tokens: set[str]) -> int:
    """Relevance of a past list (`file_stem`) to a deck's competition, for ranking
    'find planned before' results: a concrete type match (WDSF=WDSF, SEN I=SEN I)
    ranks top, then same start class (S=S, A=A; WDSF counts as S), then another class.
    A competition with no class named (open / championship) is danced at A/S level, so
    it's treated as the deck's own class when that is A or S, else as S. Higher = more
    relevant."""
    fc = comp_class(file_stem)
    if fc is None:
        fc = deck_class if deck_class in ('A', 'S') else 'S'
    cls = 2 if fc == deck_class else 1
    bonus = 1 if (deck_type_tokens and (deck_type_tokens & comp_type_tokens(file_stem))) else 0
    return cls * 10 + bonus


# Name fragments that mark a working / intermediate list (filter passes, reduced
# pools, (pre)sorting drafts, 'Selektionen' staging folders) rather than an actual
# per-competition plan. They often still carry a style or 'final' token (or sit under
# a real-looking stem), so they slip past the positive checks below — we test them
# against both the stem AND every parent folder name. ('fertig' = finished lists is
# intentionally NOT here — those are real plans.)
_WORKING_LIST_PREFIXES = ('FILTER', 'REDUZIERT', 'GRUNDSORT', 'DURCHGANG',
                          'VORSORT', 'SORTIER', 'SELEKTION', 'GESAMT')

# 'pre' as its own token, numbered or not: standard_pre_4, LW_pre, gesamt_standard_pre.
# Only the whole token counts — a 'Preis'/'Premiere' in an event name is not a draft.
_PRE_TOKEN_RE = re.compile(r'PRE\d*$')


def _has_working_marker(text: str) -> bool:
    return any(t.startswith(_WORKING_LIST_PREFIXES) or _PRE_TOKEN_RE.match(t)
               for t in _comp_tokens(text))


def is_working_collection_path(m3u_path: Path) -> bool:
    """True when the file sits in a working / pre-sorting folder (Vorsortierungen,
    fertig, Selektionen…). Its parent folders — not just its stem — mark it as a
    non-final draft, so it stays out of the 'find planned before' history even when
    the stem itself reads like a real competition."""
    return any(_has_working_marker(part) for part in m3u_path.parent.parts)


def is_competition_file(stem: str) -> bool:
    """True when a filename looks like a real tournament list — it names a start
    class, a category (SEN/HGR/JUN…), a style (STD/LAT), 'WDSF' or a round stage
    (VR/SEMI/ER). Filters arbitrary party / theme / single-track playlists, and
    working drafts (filter passes, reduced/sorting lists), out of the 'find planned
    before' history look-up (otherwise every random .m3u leaks in)."""
    if _has_working_marker(stem):
        return False
    if comp_class(stem) is not None:
        return True
    toks = _comp_tokens(stem)
    if any(t in _COMP_TOKEN_TO_CAT for t in toks):
        return True
    if any(t in _COMP_STYLE_TOKENS for t in toks):
        return True
    return bool(_round_stages_in_name(stem))


def comp_categories(text: str) -> set[str]:
    """Canonical age/grade categories named in a label/filename (SEN/HGR/JUN/KIN/
    YOUTH…). Empty when the list names none (an open / uncategorised list)."""
    return {_COMP_TOKEN_TO_CAT[t] for t in _comp_tokens(text) if t in _COMP_TOKEN_TO_CAT}


_YOUTH_CATS = frozenset({'KIN', 'JUN', 'YOUTH', 'U21'})


def category_compatible(file_stem: str, deck_cats: set[str]) -> bool:
    """Whether a past list's age category fits a deck. An open list (no category)
    always fits. A YOUTH list (kids / teens / juniors / U21) fits only a deck that
    names the SAME youth category — so youth lists never leak into an adult or
    generically-named deck. Adult/other lists fit unless the deck names a different
    category."""
    fcats = comp_categories(file_stem)
    if not fcats:
        return True
    if fcats & _YOUTH_CATS:
        return bool(fcats & deck_cats)
    if not deck_cats:
        return True
    return bool(fcats & deck_cats)


_TOP_CLASSES = frozenset({'S', 'A'})


def class_compatible(file_stem: str, deck_class: str | None) -> bool:
    """Whether a past list's start class fits a deck of `deck_class`. WDSF and
    unclassed-open lists count as top (S/A) level. Same class always fits; the two
    open/top classes S and A are mutually compatible; everything else must match
    exactly. `deck_class=None` (unknown) keeps every list."""
    if deck_class is None:
        return True
    fc = comp_class(file_stem) or 'S'    # unclassed/open competition → A/S top level
    if fc == deck_class:
        return True
    return fc in _TOP_CLASSES and deck_class in _TOP_CLASSES


# ── Round-stage detection in playlist filenames ──────────────────────────────────
# Some past lists encode the round in the FILENAME (one round per file, or several
# concatenated): VR=Vorrunde, ZR/1ZR/2ZR…=Zwischenrunde(n), SEMI/HF=Halbfinale,
# ER/Finale=Endrunde. We map each to a canonical "stage value" — higher = closer to
# the final — so 'final↔final, semi↔semi' alignment can sort rounds bottom-up.
_ROUND_STAGE_RE = re.compile(
    r'^(?:(\d+)\s*)?'
    r'(VR|VOR|VORR|VORRUNDE|'
    r'ZR|ZW|ZWR|ZWISCHEN|ZWISCHENRUNDE|'
    r'SEMI|HF|HALBF|HALBFINALE|SEMIFINAL|'
    r'ER|ENDR|ENDRUNDE|FINALE|FINAL|FIN)'
    r'(\d+)?$',
    re.IGNORECASE,
)


def _round_stage_value(token: str) -> int | None:
    """Canonical stage value for one filename token, or None if it is not a round
    marker. 0=Vorrunde, 10·n=n-th Zwischenrunde, 50=Halbfinale, 60=Endrunde."""
    m = _ROUND_STAGE_RE.match(token)
    if not m:
        return None
    num  = m.group(1) or m.group(3)
    base = m.group(2).upper()
    if base in ('VR', 'VOR', 'VORR', 'VORRUNDE'):
        return 0
    if base in ('ZR', 'ZW', 'ZWR', 'ZWISCHEN', 'ZWISCHENRUNDE'):
        n = int(num) if num else 1
        return 10 * max(1, n)          # ZR/1ZR=10, 2ZR=20, 3ZR=30 …
    if base in ('SEMI', 'HF', 'HALBF', 'HALBFINALE', 'SEMIFINAL', 'SEMIFINALE'):
        return 50
    return 60                          # ER / ENDR / FINALE / FINAL / FIN


def _round_stages_in_name(stem: str) -> list[int]:
    """Distinct round-stage values found in a filename stem, in appearance order
    (earliest round first). Empty when the file carries no round marker (i.e. a
    plain per-class list holding every round, to be sectioned bottom-up instead)."""
    out: list[int] = []
    for t in re.split(r'[^A-Za-z0-9]+', stem):
        v = _round_stage_value(t)
        if v is not None and v not in out:
            out.append(v)
    return out


@dataclass
class CompetitionSpec:
    label: str  # human label incl. style, e.g. 'U21 STD'
    style: str | None  # 'Standard' | 'Latin'; None = a mixed programme (J&J)
    dance_class: str  # D/C/B/A/S named in the label; 'S' when it names none
    dances: list[str]  # competition dances, in running order
    heats: list[int]  # heats per round (the trailing 4-4-3-2-1)
    couples: int | None = None  # parsed (NN), informational only
    # Couples per round when the line names its rounds ('VR ZR ER 24-12-6');
    # `heats` is then derived from these.
    couples_per_round: list[int] | None = None


# Every competition dance a bracketed list '(LW; TG; CC; RB)' may name.
_STD_DANCES = set(DEFAULT_DANCES['Standard']['S'])
_LAT_DANCES = set(DEFAULT_DANCES['Latin']['S'])

# A Jack and Jill line that names no dances dances these; the table corrects them.
JJ_DANCES = ('LW', 'TG', 'CC', 'RB')

# Couples one heat takes when the schedule gives couples instead of heats.
MAX_COUPLES_PER_HEAT = 12


def _bracket_dances(text: str) -> list[str] | None:
    """The dances of a '(LW; TG; CC; RB)' group, or None if no bracket holds
    only dance codes (a '(50)' couples count is not one)."""
    for m in re.finditer(r'\(([^)]*)\)', text):
        toks = [t.upper() for t in re.split(r'[;,/\s]+', m.group(1)) if t]
        codes = [_CODE_ALIAS.get(t, t) for t in toks]
        if codes and all(c in _STD_DANCES | _LAT_DANCES for c in codes):
            return list(dict.fromkeys(codes))
    return None


def parse_competition_schedule(
        text: str, *, max_couples_per_heat: int = MAX_COUPLES_PER_HEAT,
) -> list[CompetitionSpec]:
    """Parse a free-form, multi-line schedule into one CompetitionSpec per line.

    Each line: optional day prefix ('Fr:'/'So:') and start time ('18:30'), a
    class label, a style token (STD/LAT, either side of the label) or the dances
    in brackets ('(LW; TG; CC; RB)', styles may mix), an optional couples count
    '(NN)' (kept but ignored for generation), and a trailing dash/space run of
    integers = heats per round. When named rounds stand before that run
    ('VR ZR ER 24-12-6') the integers are couples per round, and each round
    gets as many heats as `max_couples_per_heat` needs. Lines without a style
    or dances, or without round numbers, are skipped.
    """
    specs: list[CompetitionSpec] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r'^[A-Za-zÄÖÜäöü]{2,3}\s*:\s*', '', line).strip()  # drop 'Fr:'/'So:'
        line = re.sub(r'^\d{1,2}[:.]\d{2}(?:\s*Uhr)?\s+', '', line).strip()  # drop '18:30'
        if not line:
            continue
        couples = None
        m = re.search(r'\((\d+)\)', line)
        if m:
            couples = int(m.group(1))
        core = re.sub(r'\(\s*\d+\s*\)', ' ', line)   # remove the (NN) couples count

        bracket = _bracket_dances(core)
        core = re.sub(r'\([^)]*\)', ' ', core)      # the dance list is not label
        if bracket is None and 'JJ' in _comp_tokens(core):
            bracket = list(JJ_DANCES)               # 'J&J 3-2-1' names no dances

        style = None
        for t in _comp_tokens(core):
            if t in _COMP_STYLE_TOKENS:
                style = _COMP_STYLE_TOKENS[t]
                break
        if bracket and style is None:
            style = ('Standard' if set(bracket) <= _STD_DANCES else
                     'Latin' if set(bracket) <= _LAT_DANCES else None)
        elif style is None:
            continue   # not a competition line we can build a pool for

        # Trailing run of integers, then any named rounds in front of it.
        numbers: list[int] = []
        parts = re.split(r'[-,\s]+', core)
        i = len(parts) - 1
        while i >= 0:
            p = parts[i].strip()
            if p.isdigit():
                numbers.insert(0, int(p))
            elif p:
                break
            i -= 1
        named_rounds = 0
        while i >= 0 and (not parts[i].strip()
                          or _round_stage_value(parts[i].strip()) is not None):
            named_rounds += bool(parts[i].strip())
            i -= 1

        per_round = None
        if named_rounds:
            per_round = [n for n in numbers if n >= 1]
            heats = [-(-n // max(1, max_couples_per_heat)) for n in per_round]
        else:
            heats = [h for h in numbers if 1 <= h <= 30]
        if not heats:
            continue

        # Display label = core minus the trailing numbers and named rounds.
        if named_rounds:
            label = ' '.join(p for p in parts[:i + 1] if p.strip())
        else:
            label = re.sub(r'[\d\s\-,]+$', '', core).strip()
        label = re.sub(r'\s+', ' ', label).strip()

        dance_class = comp_class(label) or 'S'
        dances = bracket or list(DEFAULT_DANCES[style][dance_class])
        specs.append(CompetitionSpec(
            label=label,
            style=style,
            dance_class=dance_class,
            dances=dances,
            heats=heats,
            couples=couples,
            couples_per_round=per_round,
        ))
    return specs


def competition_matches_file(spec: CompetitionSpec, m3u_path: Path) -> bool:
    """True if a per-class M3U filename belongs to `spec` (style + category + level,
    and class when the line names one).

    Matching is whole-token so 'SEN I' never matches 'SEN II'. SEN/MAS collapse to
    one category, so a 'MAS_I_*_LAT.m3u' file satisfies a 'SEN I LAT' line. Files
    with no style token (per-dance round lists like 'LW_pre.m3u', or 'alle.m3u')
    never match — unless the spec has no style of its own (a mixed programme
    like Jack and Jill), which then goes by its category alone. A class named in
    the line takes lists of that class and above (S > A > B > C > D), so Jug A
    never draws from Jug B/C/D; a list naming no class is open, danced at S.
    """
    toks_list = _comp_tokens(m3u_path.stem)
    toks = set(toks_list)
    file_styles = {_COMP_STYLE_TOKENS[t] for t in toks if t in _COMP_STYLE_TOKENS}
    if spec.style is not None and spec.style not in file_styles:
        return False

    label_toks = _comp_tokens(spec.label)
    spec_cats = {_COMP_TOKEN_TO_CAT[t] for t in label_toks if t in _COMP_TOKEN_TO_CAT}
    # Categories in filename appearance order. A file that concatenates several
    # classes (e.g. '01_VR_JUGD_KINC_JUND') is treated as belonging to its FIRST
    # class only — we never split it, so only that first class may match it.
    ordered_cats: list[str] = []
    for t in toks_list:
        c = _COMP_TOKEN_TO_CAT.get(t)
        if c and c not in ordered_cats:
            ordered_cats.append(c)
    file_cats = {ordered_cats[0]} if len(ordered_cats) >= 2 else set(ordered_cats)
    if spec_cats:
        if not (spec_cats & file_cats):
            return False
    else:
        # Unknown category: require a non-style, non-level label token to be present.
        plain = {t for t in label_toks
                 if t not in _COMP_STYLE_TOKENS and t not in _ROMAN_LEVELS}
        if plain and not (plain & toks):
            return False
        if not plain and spec.style is None:
            return False   # nothing left to tell this programme's list apart

    spec_levels = {t for t in label_toks if t in _ROMAN_LEVELS}
    if spec_levels:
        file_levels = {t for t in toks if t in _ROMAN_LEVELS}
        if not (spec_levels & file_levels):
            return False

    spec_class = comp_class(spec.label)
    if spec_class is not None:
        file_class = comp_class(m3u_path.stem) or 'S'
        if _COMP_CLASS_LETTERS.index(file_class) > _COMP_CLASS_LETTERS.index(spec_class):
            return False
    return True
