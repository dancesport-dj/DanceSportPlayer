"""🎉 Does a loaded party list still obey the rules it was built from?

`planner/warmup.py` builds an ETDS party list under a set of rules — sections
alternate, a round is three distinct dances, the Wiener Walzer and the Paso
Doble are held back, the Samba never runs twice — and then the list is edited.
Titles get dragged in from a deck, swapped, deleted; an imported .m3u from last
year is opened as a party list and was never built by the generator at all.
Nothing re-checks any of it, so the rules quietly stop holding and the first
one to notice is the floor.

This is the other direction: take the list as it stands and say which rules it
breaks. Pure — no Qt, no database — so the rules are testable on hand-built
lists, the way planner/checks.py is.

Two things it deliberately does NOT do:

* It never rewrites the list. A party list is the operator's, and a finding is
  a sentence, not a repair. 🔀 Shuffle is what rebuilds one.
* It does not cut the rounds its own way. `warmup_rounds()` is what the list
  view already draws its section headers from, so the check counts the rounds
  the operator can actually see. A rule that disagreed with the headers would
  be unreadable — and it is `warmup_rounds` starting a fresh round at a
  repeated dance that turns "the Rumba twice in one round" into the short
  round reported below.

A finding carries segments in the shape planner/checks.py uses —
(text, target) pairs, target being a row index into the list or None — so the
report can render a jump link straight back into the offending title.
"""

from dataclasses import dataclass

from planner import i18n
from planner.checks import entry_takt, title_cluster_map
from planner.models import TEMPO_RANGES
from planner.terms import dance_name
from planner.parsing import _song_title_key
from planner.warmup import (
    _WARMUP_BALLROOM,
    _WARMUP_LATIN,
    warmup_code,
    warmup_rounds,
)

# A party title that runs past this is a floor-clearer: the dancers have had
# the dance twice over by then. The generator never picks on length, so this
# only ever bites on hand-added titles — which is exactly who it is for.
LONG_TRACK_SECS = 300

# The two gates `build_warmup_playlist` opens on a played-title count, restated
# here so the check and the builder cannot drift apart unnoticed.
LATE_WW_AFTER = 12
LATE_PD_AFTER = 40

# Latin rounds the Paso Doble sits out between appearances.
PD_ROUND_GAP = 3

# The two competition sections; a Social round is neither.
_SECTIONS = ("Standardrunde", "Lateinrunde")

# The section labels `warmup_rounds` names its rounds with are German, and
# they are what the list view shows; a sentence about them needs the plain
# phrase instead ("3 Latin rounds", not "3 Lateinruden").
#
# The WHOLE phrase, not the bare word: "Latin" on its own is the style name
# the combos are read back by with `currentText()`, and a catalog entry for
# that word would rewrite those too.
_SECTION_WORD = {"Standardrunde": "Standard rounds",
                 "Lateinrunde": "Latin rounds",
                 "Socialrunde": "Social rounds"}

# The first round of each section is fixed in the builder.
_OPENERS = {"Standardrunde": ("LW", "TG", "QS"),
            "Lateinrunde": ("CC", "RB", "JI")}

# Every covered dance plays within this many rounds of its section: the
# builder forces one that sat out two rounds into the next. So this many
# rounds running without it is a hole.
_COVERAGE_ROUNDS = 3

# Categories, in the order the report shows them.
ROUNDS = "Rounds"
SPACING = "Spacing"
DUPLICATES = "Duplicates"
TAKT = "Takt"
LENGTH = "Length"


@dataclass(frozen=True)
class PartyFinding:
    """One broken rule.

    `segments` is [(text, row or None), …]; `rows` is every row it points at,
    so a caller that only wants to highlight need not walk the segments."""

    category: str
    segments: tuple = ()
    rows: tuple = ()

    @property
    def text(self) -> str:
        return "".join(t for t, _ in self.segments)


def _finding(category, *segments) -> PartyFinding:
    segs = tuple(segments)
    rows = tuple(dict.fromkeys(t for _text, t in segs if t is not None))
    return PartyFinding(category, segs, rows)


def _name(dance) -> str:
    return dance_name(dance or "", dance or "?")


def _rounds(section: str) -> str:
    """"Standard rounds": how a sentence names a section's rounds."""
    return i18n.t(_SECTION_WORD.get(section, ""))


def _title(entry) -> str:
    title = getattr(entry, "title", "")
    path = getattr(entry, "path", None)
    return title or (path.stem if path else "?")


def _at(row) -> tuple:
    """The segment that becomes a jump link. Rows are 1-based on screen."""
    return (i18n.t("row %d") % (row + 1), row)


def _row_list(rows) -> list:
    """'row 3, row 17.' as link segments."""
    segs: list = []
    for i, row in enumerate(rows):
        if i:
            segs.append((", ", None))
        segs.append(_at(row))
    segs.append((".", None))
    return segs


def _base(round_name: str) -> str:
    """'Lateinrunde 3' → 'Lateinrunde'; the unnamed round stays ''."""
    head, _sep, tail = round_name.rpartition(" ")
    return head if head and tail.isdigit() else round_name


def _rounds_with_rows(entries) -> list:
    """`warmup_rounds` again, but carrying each title's row index.

    It hands back the entries themselves and the report needs to jump to a
    row, so the rows are counted off the round lengths rather than looked up:
    a party list may legitimately hold the same entry twice, and that is one
    of the things being checked."""
    out, cursor = [], 0
    for name, songs in warmup_rounds(entries):
        out.append((name, songs, list(range(cursor, cursor + len(songs)))))
        cursor += len(songs)
    return out


# ── The rules ────────────────────────────────────────────────────────────────

def round_findings(rounds) -> list:
    """Three distinct dances per round, the openers, and the Samba spacing."""
    out = []
    history: dict = {}          # section → the dance codes of its past rounds
    for index, (name, songs, rows) in enumerate(rounds):
        section = _base(name)
        codes = [warmup_code(e) for e in songs]
        past = history.setdefault(section, [])

        # A short round. The builder shrinks one only when every dance of the
        # section is ruled out — and a dance repeated by hand shows up here
        # too, because `warmup_rounds` cuts a fresh round at the repeat. The
        # last round of an evening is allowed to run out mid-round.
        #
        # Competition rounds only. A social interlude is ONE title, or two, by
        # design — "two rounds in three hold a single title", so the socials
        # stay the breather between the rounds instead of becoming a block of
        # their own (see `_warmup_mode_round`). Reporting those as rounds of 1
        # was reporting the builder working.
        if (section in _SECTIONS
                and len(songs) < 3 and index < len(rounds) - 1):
            out.append(_finding(
                ROUNDS,
                (i18n.t("“%s” is %d title long, not 3 — from "
                        if len(songs) == 1 else
                        "“%s” is %d titles long, not 3 — from ")
                 % (name or i18n.t("a round"), len(songs)), None),
                _at(rows[0]),
                (".", None)))

        # The Samba never two rounds running.
        if past and "SA" in past[-1] and "SA" in codes:
            out.append(_finding(
                ROUNDS,
                (i18n.t("the Samba plays two %s running, the second at ")
                 % _rounds(section), None),
                _at(rows[codes.index("SA")]),
                (".", None)))


        # The first round of a section has fixed openers.
        openers = _OPENERS.get(section)
        if openers and not past and set(codes) != set(openers):
            out.append(_finding(
                ROUNDS,
                (i18n.t("“%s” opens the section with %s, not %s "
                        "— from ")
                 % (name,
                    ", ".join(_name(c) for c in codes if c)
                    or i18n.t("nothing"),
                    ", ".join(_name(c) for c in openers)), None),
                _at(rows[0]),
                (".", None)))

        past.append([c for c in codes if c])
    return out


def section_findings(rounds) -> list:
    """Standard and Latin take turns; two of the same in a row is a list that
    was edited rather than built."""
    out, previous = [], None
    for name, _songs, rows in rounds:
        section = _base(name)
        if section not in _SECTIONS:
            continue                    # a Social round may fall anywhere
        if section == previous:
            out.append(_finding(
                ROUNDS,
                (i18n.t("two %s run back to back — “%s” "
                        "starts at ") % (_rounds(section), name), None),
                _at(rows[0]),
                (i18n.t(", with no round of the other section between "
                        "them."), None)))
        previous = section
    return out


def coverage_findings(rounds, *, late_ww=True) -> list:
    """Every dance the builder covers is promised within three of its rounds,
    so three rounds of its section running without it are a hole — reported
    once per hole, from its first row. A hole as long as the whole section is
    the dance never playing at all, and says so.

    This is the rule, not variety: a dance playing three rounds running costs
    no other dance its turn — four Standard dances on three slots leave one
    out per round — so it is not a finding.

    Two dances are outside that promise, and for the same reason — a weight of
    0.025 and 0.05 has no business in every third round: the Paso is placed on
    its own percentage instead, and the Wiener Walzer joins the coverage set
    only once "late WW" is off. Measured over 200 generated evenings, holding
    the WW to the promise reported 4 of them, all correctly built."""
    out = []
    for section, dances in (("Standardrunde", _WARMUP_BALLROOM),
                            ("Lateinrunde", _WARMUP_LATIN)):
        mine = [(songs, rows) for name, songs, rows in rounds
                if _base(name) == section]
        played = [{warmup_code(e) for e in songs} for songs, _rows in mine]
        for dance in dances:
            if dance == "PD" or (dance == "WW" and late_ww):
                continue
            start = None
            for i, codes in enumerate(played + [{dance}]):   # sentinel ends it
                if dance not in codes:
                    start = i if start is None else start
                    continue
                if start is not None and i - start >= _COVERAGE_ROUNDS:
                    out.append(_gap_finding(dance, section, i - start,
                                            len(mine), mine[start][1][0]))
                start = None
    return out


def _gap_finding(dance, section, length, total, row) -> PartyFinding:
    if length == total:
        return _finding(
            ROUNDS,
            (i18n.t("the %s never plays — %d %s and not one of them.")
             % (_name(dance), total, _rounds(section)), None))
    return _finding(
        ROUNDS,
        (i18n.t("the %s sits out %d %s running, from ")
         % (_name(dance), length, _rounds(section)), None),
        _at(row),
        (".", None))


def spacing_findings(rounds, *, late_ww=True, late_pd=True) -> list:
    """The two held-back dances: when they may first appear, and how far apart
    the Pasos have to sit."""
    out = []
    played = 0
    latin_rounds = 0
    last_pd_round = None
    for name, songs, rows in rounds:
        if _base(name) == "Lateinrunde":
            latin_rounds += 1
        for entry, row in zip(songs, rows):
            code = warmup_code(entry)
            if code == "WW" and late_ww and played < LATE_WW_AFTER:
                out.append(_finding(
                    SPACING,
                    (i18n.t("the Wiener Walzer opens the evening at "),
                     None),
                    _at(row),
                    (i18n.t(" — “late WW” holds it back until "
                            "%d titles have played.")
                     % LATE_WW_AFTER, None)))
            elif code == "PD":
                if late_pd and played < LATE_PD_AFTER:
                    out.append(_finding(
                        SPACING,
                        (i18n.t("a Paso Doble plays at "), None),
                        _at(row),
                        (i18n.t(" — “late PD” holds the first "
                                "one back until %d titles have played.")
                         % LATE_PD_AFTER, None)))
                gap = latin_rounds - (last_pd_round or 0)
                if last_pd_round is not None and gap < PD_ROUND_GAP:
                    out.append(_finding(
                        SPACING,
                        (i18n.t("two Paso Dobles sit %d Latin round "
                                "apart, the second at " if gap == 1 else
                                "two Paso Dobles sit %d Latin rounds "
                                "apart, the second at ") % gap, None),
                        _at(row),
                        (i18n.t(" — the rule is %d.")
                         % PD_ROUND_GAP, None)))
                last_pd_round = latin_rounds
            played += 1
    return out


def duplicate_findings(entries) -> list:
    """The same title twice in one evening, exactly or near enough."""
    out = []

    by_path: dict = {}
    for row, entry in enumerate(entries):
        path = str(getattr(entry, "path", "") or "")
        if path:
            by_path.setdefault(path, []).append(row)
    exact = {row for rows in by_path.values() if len(rows) > 1 for row in rows}
    for rows in sorted(by_path.values()):
        if len(rows) > 1:
            out.append(_finding(DUPLICATES,
                                (i18n.t("“%s” plays %d times, "
                                        "at ")
                                 % (_title(entries[rows[0]]), len(rows)), None),
                                *_row_list(rows)))

    # Near-duplicates: two different files of the same song. Only worth saying
    # when they are the same dance — a Jive "Beautiful" and a Slow Waltz
    # "Beautiful" are two songs that happen to share a name.
    keys = [_song_title_key(_title(e)) for e in entries]
    clusters = title_cluster_map(keys)
    grouped: dict = {}
    for row, key in enumerate(keys):
        if row not in exact and clusters.get(key):
            grouped.setdefault(clusters[key], []).append(row)
    for rows in sorted(grouped.values()):
        if len(rows) < 2 or len({warmup_code(entries[r]) for r in rows}) > 1:
            continue
        out.append(_finding(DUPLICATES,
                            (i18n.t("“%s” and “%s” "
                                    "look like the same song, at ")
                             % (_title(entries[rows[0]]),
                                _title(entries[rows[1]])), None),
                            *_row_list(rows)))
    return out


def takt_findings(entries, beats_per_bar: dict) -> list:
    """Every title inside its dance's official tempo band."""
    out = []
    for row, entry in enumerate(entries):
        band = TEMPO_RANGES.get(getattr(entry, "dance", None) or "", {}).get("S")
        takt = entry_takt(entry, beats_per_bar) if band else 0
        if not takt:
            continue                    # a social dance, or simply unmeasured
        low, high = band
        if low <= takt <= high:
            continue
        out.append(_finding(
            TAKT,
            (i18n.t("“%s” is a %s at T%d, outside T%d–T%d "
                    "— ")
             % (_title(entry), _name(entry.dance), takt, low, high), None),
            _at(row),
            (".", None)))
    return out


def length_findings(entries, *, long_secs: int = LONG_TRACK_SECS) -> list:
    """A title long enough to empty the floor on its own."""
    out = []
    for row, entry in enumerate(entries):
        secs = int(getattr(entry, "duration", 0) or 0)
        if secs <= long_secs:
            continue
        out.append(_finding(
            LENGTH,
            (i18n.t("“%s” runs %d:%02d, past %d:%02d — ")
             % (_title(entry), secs // 60, secs % 60,
                long_secs // 60, long_secs % 60), None),
            _at(row),
            (".", None)))
    return out


def party_findings(entries, *, beats_per_bar: dict | None = None,
                   late_ww: bool = True, late_pd: bool = True,
                   long_secs: int = LONG_TRACK_SECS) -> list:
    """Every rule the loaded party list breaks, in report order.

    An empty result means it reads like something the generator would have
    built. `late_ww` / `late_pd` mirror the two switches it was built under —
    checking against a gate the operator turned off would be inventing a rule
    they declined."""
    entries = list(entries)
    if not entries:
        return []
    rounds = _rounds_with_rows(entries)
    return (round_findings(rounds)
            + section_findings(rounds)
            + coverage_findings(rounds, late_ww=late_ww)
            + spacing_findings(rounds, late_ww=late_ww, late_pd=late_pd)
            + duplicate_findings(entries)
            + takt_findings(entries, beats_per_bar or {})
            + length_findings(entries, long_secs=long_secs))
