"""Planning an event from its own history — the lists of earlier editions.

A recurring event keeps one folder per edition under PLAYLIST_DIR
('DanceConvention 2025', 'DanceConvention 2024', 'WiDaFe 2014' … 'Widafe 2025').
The folder name without its dates and years is the event's series; the lists
inside are the competitions it held, named after the class
('HGR_S_STD.m3u', 'MAS_I_S_STD.m3u', 'JACK_AND_JILL.m3u').

No Qt here: the AI event dialog and its tests build on these functions.
"""
import logging
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from pathlib import Path

from planner import i18n, llm
from planner.competition import (
    CompetitionSpec,
    _is_superseded_playlist,
    _round_stages_in_name,
    comp_categories,
    competition_matches_file,
    is_side_list,
)
from planner.config import PLAYLIST_DIR
from planner.models import ALLOW_REPEAT, DEFAULT_DANCES, RoundConfig, rounds_from_pattern
from planner.parsing import _song_title_keys, is_version, version_base_keys
from planner.playlist_text import read_playlist_text
from planner.scoring import class_popularity, effective_popularity
from planner.similarity import SoundAlike
from planner.sound import sound_codes
from planner.warmup import class_warmup_pool

log = logging.getLogger("dancesport.event")

_DATE_RE = re.compile(r'\d{1,2}[._]\d{1,2}(?:[._]\d{2,4})?')
_YEAR_RE = re.compile(r'(?<!\d)(?:19|20)\d{2}(?!\d)')


def event_series(folder_name: str) -> str:
    """'DanceConvention 2025' → 'danceconvention'. Dates, years and the words
    that only join them ('u.', '-') go; case and spacing do not count."""
    name = _DATE_RE.sub(' ', folder_name)
    name = _YEAR_RE.sub(' ', name)
    words = [w for w in re.split(r'[^0-9A-Za-zÄÖÜäöüß&]+', name.lower())
             if w and w not in ('u', 'und')]
    series = ' '.join(words)
    for pattern, merged, _name in _MERGED_SERIES:
        if pattern.search(series):
            return merged
    return series


# Events whose folders are named more than one way (Marcel, 2026-09-27):
# (pattern on the series, the series, the name the event list shows).
_MERGED_SERIES = (
    (re.compile(r'^dc$'), 'dancecomp', 'DanceComp'),        # 'dC2013'; 'DC HGR' is a class
    (re.compile(r'\betds\b'), 'etds', 'ETDS'),              # wherever it is held
    (re.compile(r'ball\b'), 'ball', 'Ball'),                # Boston-Club, Recklinghausen, Galaball
    (re.compile(r'\brangliste'), 'rangliste bc', 'Ranglisten BC'),
)
_MERGED_NAMES = {merged: name for _p, merged, name in _MERGED_SERIES}


def edition_year(folder_name: str) -> int:
    """The year an edition folder names, 0 if it names none."""
    years = [int(y) for y in _YEAR_RE.findall(folder_name)]
    if not years:
        short = re.findall(r'\d{1,2}[._]\d{1,2}[._](\d{2})(?!\d)', folder_name)
        years = [2000 + int(y) for y in short]
    return max(years, default=0)


def past_editions(series: str, *, root: Path | None = None,
                  before_year: int | None = None) -> list[Path]:
    """Every edition folder of `series` directly under `root`, newest first.
    `before_year` leaves out the edition being planned (and anything later)."""
    root = PLAYLIST_DIR if root is None else root
    if not root.is_dir():
        return []
    found = []
    for d in root.iterdir():
        if not d.is_dir() or event_series(d.name) != series:
            continue
        year = edition_year(d.name)
        if before_year is not None and year >= before_year:
            continue
        found.append((year, d.name, d))
    found.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [d for _y, _n, d in found]


def event_series_list(root: Path | None = None) -> list[tuple[str, str, int]]:
    """Every series under `root` as (series, name, editions), by name. The name
    is the newest edition's folder name without its dates and year; a folder
    that names no year is no edition."""
    root = PLAYLIST_DIR if root is None else root
    if not root.is_dir():
        return []
    newest: dict[str, tuple[int, str]] = {}
    count: dict[str, int] = defaultdict(int)
    for d in root.iterdir():
        year = edition_year(d.name) if d.is_dir() else 0
        series = event_series(d.name) if year else ""
        if not series:
            continue
        count[series] += 1
        if (year, d.name) > newest.get(series, (0, "")):
            newest[series] = (year, d.name)
    out = []
    for series, (_year, folder) in newest.items():
        name = _MERGED_NAMES.get(series) or _YEAR_RE.sub(' ', _DATE_RE.sub(' ', folder))
        out.append((series, ' '.join(name.split()), count[series]))
    out.sort(key=lambda t: t[1].lower())
    return out


def edition_lists(spec: CompetitionSpec, edition: Path) -> list[Path]:
    """The lists of one edition that were this competition."""
    out = []
    for m3u in sorted(edition.rglob("*.m3u")):
        if _is_superseded_playlist(m3u) or is_side_list(m3u.stem):
            continue
        if competition_matches_file(spec, m3u):
            out.append(m3u)
    return out


def _read_entries(m3u: Path, resolve) -> list:
    try:
        lines = read_playlist_text(m3u)[0].splitlines()
    except Exception:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            e = resolve(line)
            if e is not None:
                out.append(e)
    return out


def _slice_per_dance(entries, spec: CompetitionSpec, n_rounds: int) -> list[dict]:
    """A plain list, cut round by round from the back — per dance, so a spare
    title only moves its own dance. Earlier titles than the rounds need fall
    into the first round."""
    rounds: list[dict] = [defaultdict(list) for _ in range(n_rounds)]
    by_dance: dict[str, list] = defaultdict(list)
    for e in entries:
        if e.dance in spec.dances:
            by_dance[e.dance].append(e)
    for dance, titles in by_dance.items():
        end = len(titles)
        for r in range(n_rounds - 1, -1, -1):
            take = spec.heats[r] if r > 0 else end
            start = max(0, end - take)
            rounds[r][dance].extend(titles[start:end])
            end = start
            if end <= 0:
                break
    return rounds


def event_round_history(lib, spec: CompetitionSpec,
                        editions: list[Path]) -> list[dict[str, list]]:
    """What the given editions played for `spec`, per round of `spec.heats`.

    One {dance: [(entry, source), …]} per round, the editions in the order
    given (newest first from `past_editions`), each title with the
    'Edition / list' it came from. Round-tagged lists (VR/ZR/ER in the name)
    are aligned from the final upward; plain ones are cut per dance from the
    back. Dances the competition does not dance are left out."""
    n_rounds = len(spec.heats)
    out: list[dict[str, list]] = [defaultdict(list) for _ in range(n_rounds)]
    resolve = lib.line_resolver()
    for edition in editions:
        tagged: dict[int, list] = defaultdict(list)
        for m3u in edition_lists(spec, edition):
            entries = _read_entries(m3u, resolve)
            source = f"{edition.name} / {m3u.stem}"
            stages = _round_stages_in_name(m3u.stem)
            if stages:
                for st in stages:
                    tagged[st].extend((e, source) for e in entries)
                continue
            for r, per_dance in enumerate(_slice_per_dance(entries, spec, n_rounds)):
                for dance, titles in per_dance.items():
                    out[r][dance].extend((e, source) for e in titles)
        present = sorted(tagged, reverse=True)          # final-most first
        for rank, st in enumerate(present):
            r = max(0, n_rounds - 1 - rank)
            for e, source in tagged[st]:
                if e.dance in spec.dances:
                    out[r][e.dance].append((e, source))
    return [dict(r) for r in out]


# ── Three variants of a day ───────────────────────────────────────────────────
# Every slot of a competition comes from one of four sources, the tiers:
#   event — what this event played for this competition in earlier years
#   class — what other events played for the same competition class
#   new   — titles that came into the archive lately and were never played
#           at the class, the ones that sound most like those first
#   rare  — titles the class has hardly heard (RARE_MAX_PLAYS), the new ones
#           among them, in the same order
# and, only when all of them run dry, from the rest of the class-valid library.
TIERS = ("event", "class", "new", "rare")

# How much of each tier a variant aims for. "Like last year" takes all of last
# year it can and fills only the slots last year did not have — the reference
# the others are compared with. It offers a replacement for each of its titles
# but puts none in. "Last year, renewed" starts the same, then swaps some of
# last year's titles for new ones that sound like them (RENEW_SHARE) and
# offers a replacement for each title it kept.
PROFILES: dict[str, dict[str, float]] = {
    "like_last_year": {"event": 1.0, "class": 0.0, "new": 0.0, "rare": 0.0},
    "last_year_renewed": {"event": 1.0, "class": 0.0, "new": 0.0, "rare": 0.0},
    "proven_fresh": {"event": 0.5, "class": 0.3, "new": 0.2, "rare": 0.0},
    "variety": {"event": 0.25, "class": 0.45, "new": 0.3, "rare": 0.0},
}
PROFILE_ORDER = ("like_last_year", "last_year_renewed", "proven_fresh", "variety")
PROFILE_NAMES = {"like_last_year": "Like last year",
                 "last_year_renewed": "Last year, renewed",
                 "proven_fresh": "Proven + fresh",
                 "variety": "Variety"}
SUGGESTS_REPLACEMENTS = {"like_last_year", "last_year_renewed"}
# These swap up to this share of a competition's event titles for a new title
# that sounds like that very one (its `anchor`) — the ones the class played
# least first, so the favourites stay. Marcel: keep Grade and Gratitude and
# replace the second waltz from last year.
RENEWS = {"last_year_renewed"}
RENEW_SHARE = 0.30


def profile_quota(profile: str, new_share: float | None = None,
                  rare_share: float | None = None) -> dict[str, float]:
    """The tier shares of a profile, with `new_share` of new and `rare_share`
    of rarely played titles if given — event and class share the rest in the
    profile's proportion. A profile that takes no new titles ("like last
    year") stays as it is."""
    quota = PROFILES[profile]
    if quota["new"] <= 0:
        return dict(quota)
    new = quota["new"] if new_share is None else new_share
    rare = quota["rare"] if rare_share is None else rare_share
    rest = quota["event"] + quota["class"]
    return {"event": (1 - new - rare) * quota["event"] / rest,
            "class": (1 - new - rare) * quota["class"] / rest,
            "new": new, "rare": rare}

# A later heat of a round chooses among this many free titles of its tier the
# one that sounds most like the first heat's title of the dance.
HEAT_LIKE_WINDOW = 10

# A new title that sounds at least this much like an event or class title is
# that title's stand-in (its `anchor`) — "like last year" offers it first.
NEW_MIN_SIM = 0.80
# Event and class titles per dance whose timbre neighbours are looked up.
NEW_ANCHORS = 12
# A new title came into the archive (the file's creation time, `added`) at
# most this long ago. Marcel: new is new in the archive, 12–18 months — a
# title that has sat there since the 2020 copy is not new just because no
# list of the class has it yet.
NEW_MAX_AGE_DAYS = 548
# A rarely played title, of any age, was played at most this often at the
# class — Marcel: 0–2 times, and the new titles belong to it too.
RARE_MAX_PLAYS = 2

_STD_DANCES = set(DEFAULT_DANCES['Standard']['S'])


@dataclass
class Pick:
    entry: object
    tier: str    # one of TIERS, or 'library'
    source: str  # 'Edition / list', the class lists, or what it sounds like
    anchor: object = None                # a new title: the title it sounds like
    suggestion: "Pick | None" = None     # a replacement offered, not applied
    why: str = ""                        # the AI's reason, when it chose this
    like_heat: str = ""                  # a later heat: what it sounds like in the first
    replaces: "Pick | None" = None       # the title of last year it stands in for


@dataclass
class EventCandidates:
    """Everything one competition may draw from, gathered once for all variants."""
    spec: CompetitionSpec
    rounds: list[RoundConfig]
    event: list[dict[str, list[Pick]]]   # per round: dance → picks
    klass: list[dict[str, list[Pick]]]   # per round: dance → picks
    new: dict[str, list[Pick]]           # dance → picks, most similar first
    library: dict[str, list[Pick]]       # dance → picks, most played first
    own: set[str]                        # paths in this competition's event history
    rare: dict[str, list[Pick]] = field(default_factory=dict)   # like `new`
    sound: object = None                 # the `SoundAlike` a round's heats match by


@dataclass
class RefusedSwap:
    """A title the AI wanted in a slot and did not get, kept for the last word."""
    round: str
    heat: int      # index into the round's heats
    dance: int     # index into the competition's dances
    pick: Pick     # the title, with the AI's why
    reason: str    # why it did not go in


@dataclass
class PlannedCompetition:
    spec: CompetitionSpec
    rounds: list[RoundConfig]
    grid: dict[str, list[list[Pick | None]]]   # round → heats → one pick per dance
    notes: str = ""                            # what the AI changed, in a sentence
    refused: list[RefusedSwap] = field(default_factory=list)

    def playlist(self) -> dict[str, list[list]]:
        """The grid as the {round: [[entry per dance] per heat]} a deck loads."""
        return {name: [[p.entry if p else None for p in heat] for heat in heats]
                for name, heats in self.grid.items()}


def _dance_style(spec: CompetitionSpec, dance: str) -> str:
    """The style a dance is checked in — a mixed programme (J&J) per dance."""
    if spec.style:
        return spec.style
    return 'Standard' if dance in _STD_DANCES else 'Latin'


def _dedup(picks: list[Pick]) -> list[Pick]:
    seen: set[str] = set()
    out = []
    for p in picks:
        path = str(p.entry.path)
        if path not in seen:
            seen.add(path)
            out.append(p)
    return out


_VIEW_TEXT = {"timbre": "timbre top %d %%", "groove": "groove top %d %%",
              "melody": "melody top %d %%"}


def sounds_alike_text(views: dict) -> str:
    """'timbre top 3 %, groove top 10 %, …' — where a title sits among its
    dance in each view of `SoundAlike`."""
    return ", ".join(i18n.t(_VIEW_TEXT[v]) % max(1, round((1 - s) * 100))
                     for v, s in views.items() if v in _VIEW_TEXT)


def _sounds_like(similar, source: str, anchor, e, sim: float) -> str:
    views = similar.views(anchor, e) if hasattr(similar, "views") else {}
    if views:
        return (i18n.t("%s, sounds like %s (%s)")
                % (source, anchor.title, sounds_alike_text(views)))
    return i18n.t("%s, sounds like %s (%d%%)") % (source, anchor.title, round(sim * 100))


def _original_index(entries) -> tuple[dict, dict]:
    """The library's songs that are no version, by full song key and by the
    keys of their dash parts — what `_original_of` looks a version up in."""
    full: dict[str, list] = {}
    parts: dict[str, list] = {}
    for e in entries:
        if is_version(e.path.name):
            continue
        keys = _song_title_keys(e.path.name)
        if keys:
            full.setdefault(keys[0], []).append(e)
            for k in keys[1:]:
                parts.setdefault(k, []).append(e)
    return full, parts


def _original_of(e, index: tuple[dict, dict], cls):
    """The song a remix or cover `e` is a version of, the one played most at
    the class — None when `e` is no version or its song is not in the
    library. Marcel: a remix keeps its own plays, it is only pointed out.
    Full keys match full keys and dash parts, a dash part only a full key:
    two dash parts alike are mostly the same artist, not the same song."""
    base = version_base_keys(e.path.name)
    if not base:
        return None
    full, parts = index
    found = (full.get(base[0], []) + parts.get(base[0], [])
             + [o for k in base[1:] for o in full.get(k, [])])
    return max((o for o in found if o is not e),
               key=lambda o: class_popularity(o, cls), default=None)


def gather_candidates(lib, spec: CompetitionSpec, editions: list[Path], *,
                      similar=None, use_class: bool = True) -> EventCandidates:
    """The event, class, new, rare and library candidates of one competition.

    Event titles are trusted as they were played. Class, new, rare and library
    titles must fit the class (tempo, class tag, style folder). A new title
    came into the archive within NEW_MAX_AGE_DAYS and was never played at this
    class; a rare one, new or not, was played there at most RARE_MAX_PLAYS
    times, on none of the lists gathered here. Both are sorted by how much
    they sound like the event or class titles of their dance (`similar`, by
    default timbre and groove agreeing — `SoundAlike`), and a remix or cover among them
    says whose version it is (`_original_of`). Without
    `use_class` the other events' lists of the class are left out."""
    similar = similar or SoundAlike(lib)
    cls = spec.dance_class
    dances = spec.dances
    fits = {d: class_warmup_pool(lib.entries, _dance_style(spec, d), d, cls)
             for d in dances}
    valid = {d: {str(e.path) for e in fits[d]} for d in dances}

    history = event_round_history(lib, spec, editions)
    event = [{d: _dedup([Pick(e, "event", src) for e, src in rnd.get(d, [])])
              for d in dances} for rnd in history]
    own = {str(p.entry.path) for rnd in event for picks in rnd.values()
           for p in picks}

    def most_played(entries):
        return sorted(entries, key=lambda e: effective_popularity(e, cls),
                      reverse=True)

    if use_class:
        _all, pools, _n, sources = lib.past_competition_round_pools(
            spec, spec.heats, len(dances))
    else:
        pools = [[] for _ in spec.heats]
    klass = []
    for r, pool in enumerate(pools):
        per: dict[str, list[Pick]] = {d: [] for d in dances}
        for e in most_played(pool):
            path = str(e.path)
            if e.dance in per and path not in own and path in valid[e.dance]:
                labels = dict.fromkeys(sources[r].get(id(e), []))
                per[e.dance].append(Pick(e, "class", ", ".join(labels)))
        klass.append(per)

    new: dict[str, list[Pick]] = {}
    rare: dict[str, list[Pick]] = {}
    library: dict[str, list[Pick]] = {}
    since = time.time() - NEW_MAX_AGE_DAYS * 86400
    originals = _original_index(lib.entries)
    for d in dances:
        known = _dedup([p for rnd in reversed(event) for p in rnd[d]]
                       + [p for rnd in reversed(klass) for p in rnd[d]])
        known_paths = {str(p.entry.path) for p in known}
        # Another copy of a song already played is neither new nor rare.
        known_songs = {k for p in known for k in _song_title_keys(p.entry.path.name)}
        tiers: dict[str, set[str]] = {}     # path → {"new", "rare"}
        for e in fits[d]:
            path = str(e.path)
            if (path in own or path in known_paths
                    or known_songs.intersection(_song_title_keys(e.path.name))):
                continue
            plays = class_popularity(e, cls)
            if plays <= RARE_MAX_PLAYS:
                tiers[path] = {"rare"}
                if plays == 0 and e.added is not None and e.added >= since:
                    tiers[path].add("new")
        best: dict[str, tuple] = {str(e.path): (0.0, e, None)
                                  for e in fits[d] if str(e.path) in tiers}
        for a in known[:NEW_ANCHORS]:
            for sim, e in similar(a.entry, n=len(fits[d]) + 1, same_dance=True):
                path = str(e.path)
                if path in tiers and sim > best[path][0]:
                    best[path] = (sim, e, a.entry)
        new[d], rare[d] = [], []
        for sim, e, anchor in sorted(best.values(), key=lambda t: t[0], reverse=True):
            for tier in sorted(tiers[str(e.path)]):
                if tier == "new":
                    source = (i18n.t("in the archive since %s")
                              % time.strftime("%m/%Y", time.localtime(e.added)))
                else:
                    plays = class_popularity(e, cls)
                    source = (i18n.t("played %d× at the class") % plays if plays
                              else i18n.t("never played at the class"))
                if anchor is not None:
                    source = _sounds_like(similar, source, anchor, e, sim)
                song = _original_of(e, originals, cls)
                if song is not None:
                    name = f"{song.title} ({song.dance})" if song.dance else song.title
                    song_plays = class_popularity(song, cls)
                    source += ", " + (
                        i18n.t("a version of %s, played %d× at the class")
                        % (name, song_plays) if song_plays
                        else i18n.t("a version of %s, never played at the class")
                        % name)
                (new if tier == "new" else rare)[d].append(
                    Pick(e, tier, source, anchor if sim >= NEW_MIN_SIM else None))
        library[d] = [Pick(e, "library", "")
                      for e in most_played(class_warmup_pool(
                          lib.entries, _dance_style(spec, d), d, cls))
                      if str(e.path) not in own]

    rounds = rounds_from_pattern("-".join(str(h) for h in spec.heats))
    return EventCandidates(spec, rounds, event, klass, new, library, own, rare,
                           similar if hasattr(similar, "agreement") else None)


# Which competition chooses first where two of the same day want a title.
# Marcel: S before A before B…, HGR S first, then Jug A, then SEN I S and on
# with age — younger groups first, so HGR A is third. One class step weighs as
# much as one senior age step; the youth's top class (A) counts as S.
_CLASS_STEP = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
_YOUTH_GROUPS = ("U21", "YOUTH", "JUN", "KIN")
_SENIOR_RE = re.compile(r'\b(?:SEN|MAS)[A-Z]*[\s_]*(IV|V|I{1,3})\b', re.IGNORECASE)
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


def competition_rank(spec: CompetitionSpec) -> tuple:
    """Sort key: the competition that matters most first. J&J comes last.
    Tolerates the schedule's 'SENI I S' spelling of SEN I S."""
    cats = comp_categories(spec.label)
    if "JJ" in cats:
        return (1, 0, 0)
    step = _CLASS_STEP.get(spec.dance_class, len(_CLASS_STEP))
    senior = _SENIOR_RE.search(spec.label)
    if senior:
        age, group = _ROMAN[senior.group(1).upper()], 1 + len(_YOUTH_GROUPS)
    elif "HGR" in cats and re.search(r'\bII\b', spec.label):
        age, group = 0.5, 0                       # HGR II: between HGR and SEN I
    elif youth := [g for g in _YOUTH_GROUPS if g in cats]:
        age, group, step = 0, 1 + _YOUTH_GROUPS.index(youth[0]), max(step - 1, 0)
    else:
        age, group = 0, 0                         # HGR, or no group named
    return (0, step + age, group)


def plan_variant(cands_list: list[EventCandidates],
                 profile: str, *,
                 new_share: float | None = None,
                 rare_share: float | None = None) -> list[PlannedCompetition]:
    """One variant of the whole day, the competitions in the order given.
    They choose by `competition_rank`: the most important takes its titles
    first, whatever time of the day it runs.

    Slots fill final first, heat by heat, dance by dance. Each takes the tier
    furthest behind its share in `PROFILES[profile]` that still has a free
    title — the same round first, then the dance's other rounds — and falls
    back to the other tiers, then the library, when none has. A later heat
    of a round takes, among the tier's next `HEAT_LIKE_WINDOW` free titles,
    the one that sounds most like the first heat's (`EventCandidates.sound`);
    the event's own titles stay as they were played. No title plays
    twice in the day (Paso Doble only not twice in a round), and a title in
    one competition's event history is not given to another as a class, new
    or library title. A profile of RENEWS then swaps up to RENEW_SHARE of the
    event titles, the least played at the class first, for a new title that
    sounds like that very one; the new one `replaces` it. In a profile of
    SUGGESTS_REPLACEMENTS every event title left carries a `suggestion`:
    preferably a new title that sounds like it, else a class title — each
    offered once and played nowhere else that day.
    `new_share` and `rare_share` override the profile's share of new and
    rarely played titles (`profile_quota`)."""
    quota = profile_quota(profile, new_share, rare_share)
    active = [t for t in TIERS if quota[t] > 0]
    fallback = [t for t in TIERS if t not in active]
    order = sorted(range(len(cands_list)),
                   key=lambda i: (competition_rank(cands_list[i].spec), i))
    reserved: dict[str, int] = {}
    for i in order:
        for path in cands_list[i].own:
            reserved.setdefault(path, i)

    used_day: set[str] = set()
    placed: set[str] = set()     # every path in a grid today, Paso Doble too
    offered: set[str] = set()    # every path suggested as a replacement
    out: list[PlannedCompetition | None] = [None] * len(cands_list)
    for i in order:
        c = cands_list[i]
        dances = c.spec.dances
        n = len(c.rounds)
        grid = {rc.name: [[None] * len(dances) for _ in range(rc.heats)]
                for rc in c.rounds}
        counts = dict.fromkeys(TIERS, 0)
        used_round: list[set[str]] = [set() for _ in range(n)]

        def free(p: Pick, r: int) -> bool:
            path = str(p.entry.path)
            if path in used_round[r]:
                return False
            if p.entry.dance not in ALLOW_REPEAT and path in used_day:
                return False
            if path in offered:
                return False
            return p.tier == "event" or reserved.get(path, i) == i

        def replacement(pick: Pick, r: int, d: str) -> Pick | None:
            own_sound = [p for p in c.new.get(d, []) if p.anchor is pick.entry]
            order = sorted(range(n), key=lambda x: (abs(x - r), -x))
            for p in (own_sound + c.new.get(d, [])
                      + [p for x in order for p in c.klass[x].get(d, [])]):
                if free(p, r) and str(p.entry.path) not in placed:
                    return p
            return None

        def candidate(tier: str, r: int, d: str, anchor=None) -> Pick | None:
            if tier in ("event", "class"):
                per_round = c.event if tier == "event" else c.klass
                order = sorted(range(n), key=lambda x: (abs(x - r), -x))
                pools = [per_round[x].get(d, []) for x in order]
            else:
                pools = [{"new": c.new, "rare": c.rare}.get(tier, c.library).get(d, [])]
            window = 1 if anchor is None or c.sound is None or tier == "event"                 else HEAT_LIKE_WINDOW
            found = []
            for pool in pools:
                for p in pool:
                    if free(p, r):
                        found.append(p)
                        if len(found) >= window:
                            break
                if len(found) >= window:
                    break
            if len(found) <= 1:
                return found[0] if found else None
            best = max(found, key=lambda p: c.sound.agreement(anchor.entry, p.entry))
            views = (c.sound.views(anchor.entry, best.entry)
                     if hasattr(c.sound, "views") else {})
            return replace(best, like_heat=(
                i18n.t("sounds like '%s' of the first heat (%s)")
                % (anchor.entry.title, sounds_alike_text(views)) if views
                else i18n.t("sounds like '%s' of the first heat") % anchor.entry.title))

        k = 0
        for r in range(n - 1, -1, -1):
            rc = c.rounds[r]
            for h in range(rc.heats):
                for j, d in enumerate(dances):
                    k += 1
                    behind = sorted(active, key=lambda t: (
                        -(quota[t] * k - counts[t]), TIERS.index(t)))
                    anchor = grid[rc.name][0][j] if h else None
                    pick = None
                    for t in behind + fallback:
                        pick = candidate(t, r, d, anchor)
                        if pick is not None:
                            counts[t] += 1
                            break
                    if pick is None:
                        pick = candidate("library", r, d)
                    if pick is None:
                        continue
                    path = str(pick.entry.path)
                    used_round[r].add(path)
                    placed.add(path)
                    if pick.entry.dance not in ALLOW_REPEAT:
                        used_day.add(path)
                    grid[rc.name][h][j] = pick

        if profile in RENEWS:
            cls = c.spec.dance_class
            kept = [(r, heat, j, pick) for r in range(n - 1, -1, -1)
                    for heat in grid[c.rounds[r].name]
                    for j, pick in enumerate(heat)
                    if pick is not None and pick.tier == "event"]
            budget = int(RENEW_SHARE * len(kept))
            for r, heat, j, pick in sorted(
                    kept, key=lambda s: class_popularity(s[3].entry, cls)):
                if budget <= 0:
                    break
                twin = next((p for p in c.new.get(dances[j], [])
                             if p.anchor is pick.entry and free(p, r)
                             and str(p.entry.path) not in placed), None)
                if twin is None:
                    continue
                path = str(twin.entry.path)
                used_round[r].add(path)
                placed.add(path)
                if twin.entry.dance not in ALLOW_REPEAT:
                    used_day.add(path)
                heat[j] = replace(twin, replaces=pick)
                budget -= 1

        if profile in SUGGESTS_REPLACEMENTS:
            for r in range(n - 1, -1, -1):          # the final's first
                for heat in grid[c.rounds[r].name]:
                    for j, pick in enumerate(heat):
                        if pick is None or pick.tier != "event":
                            continue
                        alt = replacement(pick, r, dances[j])
                        if alt is not None:
                            offered.add(str(alt.entry.path))
                            heat[j] = replace(pick, suggestion=alt)
        out[i] = PlannedCompetition(c.spec, c.rounds, grid)
    return out


# ── The AI pass: a second opinion on every competition ──────────────────────
# What each variant is for, in the words the model gets.
PROFILE_INTENTS = {
    "like_last_year": "last year's lists as they were — the reference the "
                      "others are compared with. Its titles stay; a swap "
                      "here is only offered next to one as a replacement.",
    "last_year_renewed": "last year's lists with the titles the class played "
                         "least swapped for new titles that sound like them. "
                         "Its titles stay; a swap here is only offered next "
                         "to one as a replacement.",
    "proven_fresh": "mostly this event's and this class's proven titles, "
                    "with about a fifth new titles that sound like them.",
    "variety": "the most change: a quarter from this event's history, the "
               "rest from other events' lists of the class and new titles.",
}

# How much of the class, rare and library tiers the model sees, per dance (and
# per round for the class lists). Event and new titles are few and all go in.
AI_CLASS_ROWS = 15
AI_RARE_ROWS = 10
AI_LIBRARY_ROWS = 10


def _grid_picks(comp: PlannedCompetition):
    """(round index, heat, dance index, pick) for every filled slot."""
    for r, rc in enumerate(comp.rounds):
        for h, heat in enumerate(comp.grid[rc.name]):
            for j, p in enumerate(heat):
                if p is not None:
                    yield r, h, j, p


def _catalogue(c: EventCandidates, drafts: list[PlannedCompetition]) -> list[Pick]:
    """The rows one competition's question offers: every title its drafts
    hold or suggest, then its candidates tier by tier — each title once."""
    picks = []
    for comp in drafts:
        for *_slot, p in _grid_picks(comp):
            picks.append(p)
            if p.suggestion is not None:
                picks.append(p.suggestion)
    for rnd in reversed(c.event):
        for d in c.spec.dances:
            picks += rnd.get(d, [])
    for rnd in reversed(c.klass):
        for d in c.spec.dances:
            picks += rnd.get(d, [])[:AI_CLASS_ROWS]
    for d in c.spec.dances:
        picks += c.new.get(d, [])
    for d in c.spec.dances:
        picks += c.rare.get(d, [])[:AI_RARE_ROWS]
    for d in c.spec.dances:
        picks += c.library.get(d, [])[:AI_LIBRARY_ROWS]
    return _dedup(picks)


def _draft_slots(comp: PlannedCompetition, numbers: dict[str, int]) -> list[tuple]:
    """The draft slot by slot in playing order, as `llm.event_task` takes it."""
    out = []
    for rc in comp.rounds:
        for h, heat in enumerate(comp.grid[rc.name]):
            for j, p in enumerate(heat):
                d = comp.spec.dances[j]
                if p is None:
                    out.append((rc.name, h + 1, d, None, "", "", None))
                    continue
                sug = (numbers.get(str(p.suggestion.entry.path))
                       if p.suggestion is not None else None)
                out.append((rc.name, h + 1, d, numbers[str(p.entry.path)],
                            p.tier, p.source, sug))
    return out


def _provenance(pool: list[Pick]) -> str:
    lines = ["Where each row comes from (n · tier · source):"]
    for n, p in enumerate(pool, 1):
        lines.append(f"{n:4d} · {p.tier} · {(p.source or 'the library')[:100]}")
    return "\n".join(lines)


def _round_index(comp: PlannedCompetition, name: str) -> int | None:
    return next((r for r, rc in enumerate(comp.rounds)
                 if rc.name.lower() == name.lower()), None)


def _swap_refused(swap: dict, i: int, comp: PlannedCompetition,
                  pool: list[Pick], cands_list: list[EventCandidates],
                  suggests: bool) -> str:
    """Why a swap cannot go in on its own — '' when it can. The rules of the
    day are checked once all of an answer's swaps are in (`_day_conflict`),
    so two titles may trade places."""
    dances = comp.spec.dances
    r = _round_index(comp, swap["round"])
    if r is None:
        return f"no round {swap['round']!r}"
    rc = comp.rounds[r]
    if swap["dance"] not in dances:
        return f"no dance {swap['dance']!r}"
    if not 1 <= swap["heat"] <= rc.heats:
        return f"no heat {swap['heat']} in {rc.name}"
    if not 1 <= swap["n"] <= len(pool):
        return f"#{swap['n']} was not shown"
    cand = pool[swap["n"] - 1]
    if llm.pool_dance(cand.entry) != swap["dance"]:
        return f"#{swap['n']} is not a {swap['dance']}"
    path = str(cand.entry.path)
    slot = comp.grid[rc.name][swap["heat"] - 1][dances.index(swap["dance"])]
    if slot is not None and str(slot.entry.path) == path:
        return f"#{swap['n']} is already in that slot"
    if suggests and slot is None:
        return "nothing there to offer a replacement for"
    if path not in cands_list[i].own and any(
            path in c.own for k, c in enumerate(cands_list) if k != i):
        return f"#{swap['n']} belongs to another competition's history"
    return ""


def _wanted(swap: dict, comp: PlannedCompetition,
            pool: list[Pick]) -> RefusedSwap | None:
    """The swap as a slot and a real title of its dance, or None when it
    names no such thing — then there is nothing to show of it."""
    r = _round_index(comp, swap["round"])
    if (r is None or swap["dance"] not in comp.spec.dances
            or not 1 <= swap["heat"] <= comp.rounds[r].heats
            or not 1 <= swap["n"] <= len(pool)):
        return None
    cand = pool[swap["n"] - 1]
    j = comp.spec.dances.index(swap["dance"])
    slot = comp.grid[comp.rounds[r].name][swap["heat"] - 1][j]
    if (llm.pool_dance(cand.entry) != swap["dance"]
            or slot is not None and str(slot.entry.path) == str(cand.entry.path)):
        return None
    return RefusedSwap(comp.rounds[r].name, swap["heat"] - 1, j,
                       replace(cand, suggestion=None, replaces=None,
                               why=swap["why"]), "")


def _keep_refused(comp: PlannedCompetition, lost: RefusedSwap) -> None:
    """Keep a lost swap once — a second look may propose it again."""
    same = (lost.round, lost.heat, lost.dance, str(lost.pick.entry.path))
    if all((x.round, x.heat, x.dance, str(x.pick.entry.path)) != same
           for x in comp.refused):
        comp.refused.append(lost)


def _day_conflict(comps: list[PlannedCompetition], key: tuple,
                  suggests: bool) -> str:
    """Why the title a swap put into slot `key` (competition, round, heat,
    dance) breaks its variant's day — '' when it does not. The rules are
    plan_variant's: no title twice (Paso Doble only not twice in a round), and
    a title offered as a replacement is played and offered nowhere else."""
    i, r, h, j = key
    slot = comps[i].grid[comps[i].rounds[r].name][h][j]
    mine = slot.suggestion if suggests else slot
    path = str(mine.entry.path)
    for k, other in enumerate(comps):
        for r2, h2, j2, p in _grid_picks(other):
            here = (k, r2, h2, j2) == key
            if (p.suggestion is not None and not (here and suggests)
                    and str(p.suggestion.entry.path) == path):
                return "is offered for another slot"
            if here and not suggests or str(p.entry.path) != path:
                continue
            if suggests or mine.entry.dance not in ALLOW_REPEAT:
                return "already plays that day"
            if (k, r2) == (i, r):
                return "already plays in that round"
    return ""


def _question(c: EventCandidates, i: int,
              out: dict[str, list[PlannedCompetition]],
              rules: str) -> tuple[list[Pick], str, str]:
    """(catalogue, system, user) — the question for competition `i`."""
    pool = _catalogue(c, [comps[i] for comps in out.values()])
    numbers = {str(p.entry.path): n for n, p in enumerate(pool, 1)}
    entries = [p.entry for p in pool]
    elsewhere = {str(p.entry.path) for comps in out.values()
                 for k, comp in enumerate(comps) if k != i
                 for *_slot, p in _grid_picks(comp)}
    lost = []
    for v, comps in out.items():
        for x in comps[i].refused:
            n = numbers.get(str(x.pick.entry.path))
            lost.append(f"{v} {x.round} heat {x.heat + 1} {c.spec.dances[x.dance]}: "
                        f"{f'#{n} ' if n else ''}{x.pick.entry.title} — {x.reason}")
    task = llm.event_task(
        c.spec.label, c.spec.style, c.spec.dance_class, c.spec.dances, c.rounds,
        {v: _draft_slots(comps[i], numbers) for v, comps in out.items()},
        {v: PROFILE_INTENTS.get(v, "") for v in out}, lost)
    rows = llm.catalog_rows(
        entries, range(1, len(entries) + 1), dance_class=c.spec.dance_class,
        used_paths=elsewhere,
        sound=sound_codes(entries, dance_of=llm.pool_dance))
    system, user = llm.build_event_prompt(rules, task,
                                          rows + "\n\n" + _provenance(pool))
    return pool, system, user


def _apply_answer(out: dict[str, list[PlannedCompetition]], i: int,
                  cands_list: list[EventCandidates], pool: list[Pick],
                  answer: dict) -> tuple[int, list[str]]:
    """Put one competition's swaps in. Returns (applied, why the rest not)."""
    c = cands_list[i]
    swapped: dict[tuple, tuple] = {}   # (variant, slot) → (pick before, swap)
    refused = []
    for swap in answer["swaps"]:
        v = swap["variant"]
        comps = out.get(v)
        suggests = v in SUGGESTS_REPLACEMENTS
        if comps is None:
            reason = "no such variant"
        elif sum(w == v for w, _key in swapped) >= llm.EVENT_MAX_SWAPS:
            reason = "too many swaps"
        else:
            reason = _swap_refused(swap, i, comps[i], pool, cands_list, suggests)
        if not reason:
            r = _round_index(comps[i], swap["round"])
            key = (i, r, swap["heat"] - 1, c.spec.dances.index(swap["dance"]))
            if (v, key) in swapped:
                reason = "that slot is swapped already"
        if reason:
            refused.append(f"{v} {swap['round']} {swap['heat']} "
                           f"{swap['dance']}: {reason}")
            if comps is not None and (lost := _wanted(swap, comps[i], pool)):
                _keep_refused(comps[i], replace(lost, reason=reason))
            continue
        row = comps[i].grid[c.rounds[r].name][key[2]]
        before = row[key[3]]
        chosen = replace(pool[swap["n"] - 1], suggestion=None, replaces=None,
                         why=swap["why"])
        row[key[3]] = replace(before, suggestion=chosen) if suggests else chosen
        swapped[(v, key)] = (before, swap)
    # The day's rules on the answer as a whole: the latest swap that breaks
    # them is undone until none does, so half a trade comes out whole.
    while True:
        bad = next(((v, key, why) for v, key in reversed(list(swapped))
                    if (why := _day_conflict(out[v], key,
                                             v in SUGGESTS_REPLACEMENTS))),
                   None)
        if bad is None:
            break
        v, key, why = bad
        before, swap = swapped.pop((v, key))
        out[v][i].grid[c.rounds[key[1]].name][key[2]][key[3]] = before
        refused.append(f"{v} {swap['round']} {swap['heat']} "
                       f"{swap['dance']}: #{swap['n']} {why}")
        _keep_refused(out[v][i], replace(_wanted(swap, out[v][i], pool), reason=why))
    for v, text in answer["notes"].items():
        if v in out:
            out[v][i].notes = text
    return len(swapped), refused


@dataclass
class RefineResult:
    """The variants after the AI pass, and what it could not check."""
    variants: dict[str, list[PlannedCompetition]]
    failed: list[int] = field(default_factory=list)    # asked; the plan stands
    pending: list[int] = field(default_factory=list)   # held back by a rate limit
    limit: str = ""                   # what the backend said about the limit
    reset_at: float | None = None     # when it lifts (epoch s), if it said
    second_round: list[int] = field(default_factory=list)  # lost a swap this time


# How many competitions are asked at once: a whole event day. One question
# took 506 s on the real 2026 plan, so asking them in turn costs the sum.
AI_PARALLEL = 8


def refine_with_ai(variants: dict[str, list[PlannedCompetition]],
                   cands_list: list[EventCandidates], *, rules: str = "",
                   ask=None, model: str = "", config_dir: str = "",
                   timeout: int = 1200, on_step=None, cancel=None,
                   only: list[int] | None = None) -> RefineResult:
    """The variants with the AI's swaps applied, one question per competition.

    The model sees every variant's draft of the competition and a numbered
    catalogue of its candidates, and answers with swaps (`llm.parse_swaps`).
    A swap that breaks a rule of the day is dropped; in a SUGGESTS_REPLACEMENTS
    variant it becomes the slot's `suggestion` instead of replacing the title.

    All questions go out at once, so no answer sees the others. They are
    applied by `competition_rank`: where two want the same title, the more
    important competition gets it and binds the rest. A competition
    whose question fails keeps its drafts — the computed plan always stands.
    One held back by a rate limit is listed in `pending`: hand the result's
    variants back with `only=pending` once the limit has lifted. One that lost
    a swap is listed in `second_round`: asked again with `only=second_round`,
    its question names what did not go in. The variants handed in are not
    changed.

    `ask(system, user) -> (text, backend)` is `llm._ask` unless given."""
    if ask is None:
        def ask(system, user):
            return llm._ask(system, user, model=model or llm.CLAUDE_MODEL,
                            config_dir=config_dir, timeout=timeout,
                            on_step=on_step, cancel=cancel)
    rules = rules or llm.DEFAULT_RULES
    out = {v: [replace(c, grid={name: [list(h) for h in heats]
                                for name, heats in c.grid.items()},
                       refused=list(c.refused))
               for c in comps]
           for v, comps in variants.items()}
    todo = list(range(len(cands_list))) if only is None else sorted(only)
    result = RefineResult(out)
    if not todo:
        return result

    questions = {}
    for i in todo:
        questions[i] = _question(cands_list[i], i, out, rules)
        _pool, system, user = questions[i]
        llm._step(on_step, "sent", f"{cands_list[i].spec.label} — the drafts to check",
                  system + "\n\n" + user)
    replies: dict[int, tuple | Exception] = {}
    with ThreadPoolExecutor(max_workers=min(len(todo), AI_PARALLEL)) as executor:
        asked = {executor.submit(ask, q[1], q[2]): i for i, q in questions.items()}
        for fut in as_completed(asked):
            i = asked[fut]
            label = cands_list[i].spec.label
            try:
                raw, backend = fut.result()
                llm._step(on_step, "received", f"{label} — its swaps — {backend}", raw)
                replies[i] = (llm.parse_swaps(raw), backend)
            except llm.Cancelled:
                raise
            except Exception as exc:
                replies[i] = exc

    for i in sorted(todo, key=lambda i: (competition_rank(cands_list[i].spec), i)):
        label = cands_list[i].spec.label
        reply = replies[i]
        if isinstance(reply, Exception):
            if llm.is_rate_limited(reply):
                result.pending.append(i)
                result.limit = result.limit or str(reply)
                result.reset_at = result.reset_at or llm.rate_limit_reset(str(reply))
                what = "held back by a rate limit, ask again later"
            else:
                result.failed.append(i)
                what = "the plan stands"
            log.warning("🤖 event refine failed, %s\n"
                        "competition: %s\n"
                        "error: %s", what, label, reply)
            llm._step(on_step, "note", f"{label} — {what}", str(reply))
            continue
        answer, backend = reply
        kept = sum(len(comps[i].refused) for comps in out.values())
        applied, refused = _apply_answer(out, i, cands_list, questions[i][0], answer)
        if sum(len(comps[i].refused) for comps in out.values()) > kept:
            result.second_round.append(i)
        if refused:
            llm._step(on_step, "note", f"{label} — swaps not applied",
                      "\n".join(refused))
        log.info("🤖 event refine via %s\n"
                 "competition: %s\n"
                 "rows shown: %d\n"
                 "swaps applied: %d\n"
                 "swaps refused: %d",
                 backend, label, len(questions[i][0]), applied, len(refused))
    return result


# ── What the window says about a run ────────────────────────────────────────
# A limit that did not say when it lifts is tried again after this long.
RETRY_UNKNOWN_S = 1800


def retry_delay(reset_at: float | None, now: float) -> int:
    """Seconds to wait before asking again: a minute past the reset if the
    limit named one, never less than a minute, else RETRY_UNKNOWN_S."""
    if reset_at is None:
        return RETRY_UNKNOWN_S
    return max(60, int(reset_at - now) + 60)


def describe_result(result: RefineResult, cands_list: list[EventCandidates]) -> str:
    """Every competition with its variants' filled slots and the AI's notes,
    and what the AI pass left open — for the transcript."""
    blocks = []
    for i, c in enumerate(cands_list):
        lines = [c.spec.label]
        refused = 0
        for v, comps in result.variants.items():
            comp = comps[i]
            picks = list(_grid_picks(comp))
            total = sum(rc.heats for rc in comp.rounds) * len(comp.spec.dances)
            line = f"  {i18n.t(PROFILE_NAMES.get(v, v))}: {len(picks)}/{total}"
            if comp.notes:
                line += f" — {comp.notes}"
            lines.append(line)
            refused += len(comp.refused)
        if refused:
            lines.append("  " + (i18n.t("1 swap not applied, kept for your choice")
                                 if refused == 1 else
                                 i18n.t("%d swaps not applied, kept for your choice")
                                 % refused))
        if i in result.failed:
            lines.append("  " + i18n.t("the AI could not check it — the plan stands"))
        if i in result.pending:
            lines.append("  " + i18n.t("held back by the AI's limit — ask again later"))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ── The last word: what the comparison window changes ───────────────────────
# A slot is addressed as (competition, round index, heat, dance index) — the
# key _day_conflict takes — within one variant's list of competitions.
ALT_ROWS = 8     # free titles offered per tier for a slot


def slot_pick(comps: list[PlannedCompetition], key: tuple) -> Pick | None:
    i, r, h, j = key
    return comps[i].grid[comps[i].rounds[r].name][h][j]


def slot_refused(comp: PlannedCompetition, key: tuple) -> list[RefusedSwap]:
    """The swaps the AI wanted in this slot and did not get."""
    _i, r, h, j = key
    name = comp.rounds[r].name
    return [x for x in comp.refused if (x.round, x.heat, x.dance) == (name, h, j)]


def slot_alternatives(c: EventCandidates, comps: list[PlannedCompetition],
                      key: tuple, *, limit: int = ALT_ROWS) -> dict[str, list[Pick]]:
    """Per tier, up to `limit` titles of the slot's dance that do not play in
    this variant's day yet (Paso Doble: not in the same round) — the event and
    class lists of the slot's round first, then the nearer rounds."""
    i, r, _h, j = key
    dance = c.spec.dances[j]
    taken = {str(p.entry.path) for comp in comps for _r, _h, _j, p in _grid_picks(comp)}
    in_round = {str(p.entry.path) for r2, _h, _j, p in _grid_picks(comps[i]) if r2 == r}
    near = sorted(range(len(c.rounds)), key=lambda x: (abs(x - r), -x))
    pools = {
        "event": [p for x in near for p in c.event[x].get(dance, [])],
        "class": [p for x in near for p in c.klass[x].get(dance, [])],
        "new": c.new.get(dance, []),
        "rare": c.rare.get(dance, []),
        "library": c.library.get(dance, []),
    }
    seen: set[str] = set()
    out: dict[str, list[Pick]] = {}
    for tier, pool in pools.items():
        free = []
        for p in pool:
            path = str(p.entry.path)
            busy = in_round if dance in ALLOW_REPEAT else taken
            if path in seen or path in busy:
                continue
            seen.add(path)
            free.append(p)
            if len(free) >= limit:
                break
        if free:
            out[tier] = free
    return out


def slot_conflict(comps: list[PlannedCompetition], key: tuple, pick: Pick) -> str:
    """Why `pick` in slot `key` would break the variant's day — '' when not."""
    i, r, h, j = key
    heat = comps[i].grid[comps[i].rounds[r].name][h]
    before = heat[j]
    heat[j] = replace(pick, suggestion=None)
    try:
        return _day_conflict(comps, key, False)
    finally:
        heat[j] = before


def put_slot(comps: list[PlannedCompetition], key: tuple, pick: Pick) -> None:
    """Put `pick` into the slot. The replacement offered for the title it
    replaces goes with it, and a refused swap for this title is settled; what
    it sounded like in its old round's first heat, and the title of last year
    it stood in for, stay behind."""
    i, r, h, j = key
    comp = comps[i]
    comp.grid[comp.rounds[r].name][h][j] = replace(pick, suggestion=None, like_heat="",
                                                   replaces=None)
    path = str(pick.entry.path)
    comp.refused = [x for x in comp.refused
                    if not (x in slot_refused(comp, key)
                            and str(x.pick.entry.path) == path)]


def _heat_of(comps: list[PlannedCompetition], key: tuple) -> list:
    i, r, h, _j = key
    return comps[i].grid[comps[i].rounds[r].name][h]


def swap_conflict(comps: list[PlannedCompetition], a: tuple, b: tuple) -> str:
    """Why swapping the titles of slots `a` and `b` breaks the variant's day —
    '' when not. The day keeps its titles, so only a Paso Doble landing twice
    in a round can."""
    heat_a, heat_b = _heat_of(comps, a), _heat_of(comps, b)
    pick_a, pick_b = heat_a[a[3]], heat_b[b[3]]
    heat_a[a[3]], heat_b[b[3]] = pick_b, pick_a
    try:
        return _day_conflict(comps, a, False) or _day_conflict(comps, b, False)
    finally:
        heat_a[a[3]], heat_b[b[3]] = pick_a, pick_b


def swap_slots(comps: list[PlannedCompetition], a: tuple, b: tuple) -> None:
    """Swap the titles of slots `a` and `b`, each with the replacement offered
    for it; a refused swap for a title into the slot it now fills is settled."""
    pick_a, pick_b = slot_pick(comps, a), slot_pick(comps, b)
    for key, pick in ((a, pick_b), (b, pick_a)):
        put_slot(comps, key, pick)
        _heat_of(comps, key)[key[3]] = replace(pick, like_heat="") if pick.like_heat else pick
