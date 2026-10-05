"""Let an LLM build a playlist out of the library.

Two backends, tried in order:

  1. `claude -p` — the Claude Code CLI on the user's own subscription, no API
     key needed. Which login it uses is decided by CLAUDE_CONFIG_DIR.
  2. OpenRouter — the key/model already configured for the 🤖 AI-suggestions
     dialog (planner.ai).

The model never sees or writes file paths: every track it is shown carries a
NUMBER — its position in the candidate pool — and it answers with numbers. A
hallucinated title therefore can never reach a playlist; an unknown number is
simply dropped.

The library is too big to show whole, so a run takes two turns:

  1. SEARCH — the model sees a per-dance summary (how many tracks, what tempi,
     how many proven / fresh / unplanned) and asks for the subsets it wants.
  2. PICK   — it gets only those rows and answers with its picks.

The numbering is the same in both turns: it is the position in the full pool,
never the position in whatever subset was sent.
"""
import json
import logging
import os
import random
import re
import shutil
import subprocess
import tempfile
import time

from planner.models import ALLOW_REPEAT, DANCE_NAMES, TEMPO_RANGES, is_non_turnier
from planner.parsing import _norm_title
from planner.scoring import HIGHER_CLASSES, class_focused, effective_popularity
from planner.sound import code_text, sound_codes
from planner.warmup import class_warmup_pool, warmup_code
from planner import ai
from planner.planned import path_key

log = logging.getLogger("dancesport.llm")


# The claude CLI's alias for the latest Opus, so a new one is taken without a
# code change (Marcel: "use latest opus model not a specific one").
# Overridable via the gui_settings.json key 'ai_model'.
CLAUDE_MODEL = "opus"


# Safety bound on the pool itself. The real library is ~3600 tracks, of which a
# competition pool is a fraction, so this never bites — it only stops a
# pathological library from building an endless summary.
MAX_CANDIDATES = 6000


# What a search round may cost. `_QUERY_LIMIT` rows unless the model says
# otherwise, `_QUERY_MAX` however loudly it asks, `_ROWS_MAX` over all its
# queries together — roughly 8k tokens, which every backend takes comfortably.
_QUERY_LIMIT = 60
_QUERY_MAX = 200
_ROWS_MAX = 600

# How much of the played-together appendix is worth its room: at most this many
# rows get a line, each naming at most `_PAIRS_PER_ROW` partners, and a pair has
# to share at least `_PAIRS_MIN_SHARED` past playlists to count at all. One
# shared list is a coincidence — two is a habit.
_PAIR_ROWS = 150
_PAIRS_PER_ROW = 4
_PAIRS_MIN_SHARED = 2

# How much of a per-pick reason is kept. Long enough for a real sentence, short
# enough that a model that decides to write an essay cannot flood the window.
_WHY_MAX = 200


# From how many plays a track counts as "proven" in the summary (the same
# threshold the round strategies use to separate proven from fresh).
_PROVEN_PLAYS = 3
_MARKERS_SHOWN = 25


# The editable half of the prompt: what the user considers a good playlist. Shown
# in the dialog, saved to gui_settings.json, resettable to exactly this text.
DEFAULT_RULES = """\
You are the music director of a dancesport event. Build the playlist a good DJ
would build:

• Tempo first. Every track must sit inside the TSO range given for its dance.
  Prefer the middle of the range; an edge tempo only when nothing better fits.
• Never use the same track twice — Paso Doble is the only exception, there are
  simply too few usable pieces.
• Keep one heat coherent: no jump from a 1930s big band to a 2020s electro
  cover inside the same heat.
• Spread artists, eras and arrangements over the whole event. The same artist
  should not come back within a round.
• The later the round, the stronger the track. Save the crowd-pleasers and the
  well-known recordings for the final. The "fin" and "sem" columns say which
  tracks a past final and semifinal really used — build those two rounds out of
  them, each from its own column, and leave the high-"pop" titles that have
  never been in either to the preliminaries.
• Every Paso Doble must have the classic "España cañí" highlight structure.
• Lean on proven tracks (a high play count) but mix in a few fresh ones, so the
  event does not sound exactly like last year's.
• Watch the energy curve: open friendly, build through the round, do not put
  the two most driving tracks back to back.
"""


# The half the user does NOT edit — how the answer has to come back.
_OUTPUT_CONTRACT = """\
Answer with ONE JSON object and nothing else. No prose, no markdown fence.

{"playlist": [{"n": <catalog number>, "round": "<round name>", "heat": <int>,
               "why": "<why THIS track, in a few words>"}],
 "notes": "<two sentences on what you went for>"}

Rules for the answer:
• "n" must be a number from the rows you were shown. Never invent a track,
  and never guess a number you did not see.
• List the tracks in playing order.
• Leave out "round" and "heat" when no round structure was requested.
• Do not repeat a number (Paso Doble excepted).
• "why" is read afterwards by the person running the event, so give the real
  reason — the tempo, the play history, how it sounds, what it follows — not a
  rewording of the title. One short clause is enough.
"""


# ── Backend 1: the claude CLI ────────────────────────────────────────────────
# Where the installers put it when PATH does not carry it — a GUI started from
# the Explorer inherits a much smaller PATH than the user's own terminal.
_CLAUDE_BIN_FALLBACKS = (
    "~/.local/bin/claude.exe",     # native installer, Windows
    "~/.local/bin/claude",         # native installer, macOS / Linux
    "~/AppData/Roaming/npm/claude.cmd",
    "~/.claude/local/claude",      # `claude migrate-installer` target
    "/usr/local/bin/claude",
)


def resolve_claude_bin() -> str | None:
    """Absolute path to the claude CLI, or None. CLAUDE_BIN wins over PATH."""
    override = os.environ.get("CLAUDE_BIN", "").strip()
    if override and os.path.isfile(override):
        return override
    found = shutil.which("claude")
    if found:
        return found
    for candidate in _CLAUDE_BIN_FALLBACKS:
        path = os.path.expanduser(candidate)
        if os.path.isfile(path):
            return path
    return None


def claude_available() -> bool:
    return resolve_claude_bin() is not None


# What makes a directory a claude login rather than any other dotfolder.
_CLAUDE_CONFIG_MARKERS = (".credentials.json", "settings.json", "projects")


def claude_config_dirs(home: str = "") -> list[str]:
    """Every `claude` login on this machine: ~/.claude and the profiles beside
    it (~/.claude-profil1, …), plain ~/.claude first.

    A shell that exports CLAUDE_CONFIG_DIR picks one of these; a GUI started
    from the desktop has no such variable and would silently take ~/.claude,
    which may well be the logged-out one."""
    home = home or os.path.expanduser("~")
    try:
        names = sorted(os.listdir(home))
    except OSError:
        return []
    found = []
    for name in names:
        if not name.startswith(".claude"):
            continue
        path = os.path.join(home, name)
        if not os.path.isdir(path):
            continue
        if any(os.path.exists(os.path.join(path, m))
               for m in _CLAUDE_CONFIG_MARKERS):
            found.append(path)
    found.sort(key=lambda p: os.path.basename(p) != ".claude")
    return found


def default_claude_config_dir() -> str:
    """The login to offer when the user has not chosen one: whatever the
    environment already points at, else nothing (the CLI's own default)."""
    return os.environ.get("CLAUDE_CONFIG_DIR", "").strip()


class Cancelled(Exception):
    """The user stopped the run. Not a failure: no fallback, no retry, no sweep."""


def _raise_if_cancelled(cancel) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def call_claude_cli(prompt: str, model: str = CLAUDE_MODEL,
                    timeout: int = 600, config_dir: str = "",
                    cancel=None) -> str:
    """Run `claude -p` with the prompt on stdin and return its answer.

    `config_dir` pins CLAUDE_CONFIG_DIR — which login the CLI uses. Without it
    the CLI falls back to ~/.claude, which is a *different* profile than the one
    a shell with CLAUDE_CONFIG_DIR exported would use, and can be logged out.

    `cancel` (a threading.Event) set while the CLI thinks kills it within a
    second and raises Cancelled.
    """
    binary = resolve_claude_bin()
    if not binary:
        raise RuntimeError(
            "claude CLI not found — not on PATH and not at any of "
            + ", ".join(_CLAUDE_BIN_FALLBACKS)
            + ".\nSet the CLAUDE_BIN environment variable to its full path.")

    # CLAUDECODE must go or a nested invocation refuses to start.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir

    log.info("🤖 asking claude -p\n"
             "model: %s\n"
             "prompt: %d chars\n"
             "timeout: %ds", model, len(prompt), timeout)
    # The prompt carries library text someone else wrote (titles, ID3 comment
    # markers). The answer is plain text, so the CLI gets no tools, none of the
    # login's MCP servers, no transcript of it kept, and an empty folder to sit
    # in instead of the app's.
    cmd = [binary, "-p", "--output-format", "text", "--model", model,
           "--tools", "", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers": {}}', "--no-session-persistence"]
    with tempfile.TemporaryDirectory(prefix="dp_claude_") as cwd:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", env=env, cwd=cwd,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Waited on a second at a time so a stop gets through; the input goes
        # with the first wait only (communicate refuses it on a later one).
        deadline = time.monotonic() + timeout
        pending = prompt
        while True:
            try:
                stdout, stderr = proc.communicate(pending, timeout=1)
                break
            except subprocess.TimeoutExpired:
                pending = None
                stopped = cancel is not None and cancel.is_set()
                if stopped or time.monotonic() >= deadline:
                    proc.kill()
                    proc.communicate()
                    if stopped:
                        raise Cancelled() from None
                    raise subprocess.TimeoutExpired(cmd, timeout) from None
    if proc.returncode != 0:
        # The CLI explains itself on stdout, not stderr — a bad model, an expired
        # login and a hit usage limit all exit 1 with stderr empty.
        detail = ((stdout or "").strip() or (stderr or "").strip()
                  or "no output on either stream")
        raise RuntimeError(f"claude -p exited {proc.returncode}: {detail[:400]}")
    return stdout


# ── The pool the model picks from ────────────────────────────────
def competition_candidates(entries, style: str, dance_class: str,
                           dances: list[str], *, cap: int = MAX_CANDIDATES):
    """Every TSO-conform candidate per dance for a competition, most-played
    first. Nothing is sampled away: the model no longer reads this list, it
    queries it, so the pool may as well be complete."""
    per_dance = max(10, cap // max(1, len(dances)))
    out: list = []
    for dance in dances:
        pool = class_warmup_pool(entries, style, dance, dance_class)
        pool.sort(key=lambda e: -effective_popularity(e, dance_class))
        out.extend(pool[:per_dance])
    return out


def flat_candidates(entries, *, cap: int = MAX_CANDIDATES):
    """Candidates for a free-form list: everything danceable, junk categories
    (seasonal / duplicates / wrong tempo) left out."""
    by_dance: dict[str, list] = {}
    for e in entries:
        if getattr(e, "is_xmas", False) or is_non_turnier(e):
            continue
        code = warmup_code(e)
        if code:
            by_dance.setdefault(code, []).append(e)
    if not by_dance:
        return []
    per_dance = max(10, cap // len(by_dance))
    out: list = []
    for pool in by_dance.values():
        pool.sort(key=lambda e: -effective_popularity(e, None))
        out.extend(pool[:per_dance])
    return out


# ── One track, as the model sees it ──────────────────────────────
# The columns the library pane shows, minus what cannot help a choice. "tags"
# is what the ID3 comment carried: the start classes the track is cleared for,
# 'instr' when the comment (or the filename) marks it instrumental, and then the
# free markers the user typed (vocal_f, classic, eintanzen, …) — about three in
# four library files have one and they say things no other column does.
_ROW_HEADER = ("   n | dance | bpm | snd | pop | fin | sem | used | tags | year | "
               "artist – title")

# What 'fin' and 'sem' mean. Sent with every table — unlike 'snd' they cost no
# analysis, and without it the model reads the columns as a second play count.
_ROUND_LEGEND = (
    "fin / sem = of those past events, how many danced this track in their "
    "FINAL round and how many in their SEMIFINAL. Both are a different thing "
    "from 'pop': a title can lead the library on play count and still be heat "
    "music — played in every preliminary, never in an Endrunde. Those two "
    "rounds are the ones a DJ picks by hand, one track per dance, so a track "
    "that has been in them has been chosen for exactly that moment. Build the "
    "final from the 'fin' tracks and the semifinal from the 'sem' ones — "
    "keeping them apart, so the final is not handed what the semifinal just "
    "used — and leave the rest to the preliminaries."
)

# What the 'snd' digits mean. Only sent when the pool actually has analysed
# tracks in it — an unanalysed library would just be a column of dashes.
_ROW_LEGEND = (
    _ROUND_LEGEND + "\n"
    "snd = how this track sits among others of its own dance, measured from "
    "the audio:\n"
    "  first digit  energy (1 quiet … 5 loud)\n"
    "  second digit brightness (1 dark … 5 bright)\n"
    "  third digit  drive, how hard the beat pushes (1 soft … 5 hard)\n"
    "  '---' means that track has not been analysed."
)


def rules_to_remember(rules: str) -> str:
    """What to persist for the rule set the user has just run with.

    An UNTOUCHED default is remembered as "" — the dialog reads an empty setting
    as "use DEFAULT_RULES", so this version's wording never gets frozen into the
    settings file where a later change to the shipped rules could not reach it.
    That is not hypothetical: the rules said nothing about the "fin" / "sem"
    columns for a while because a saved copy from before them was shadowing the
    default. Anything the user actually typed comes back verbatim."""
    return "" if rules.strip() == DEFAULT_RULES.strip() else rules


def _used_set(used_paths) -> set:
    """The planned-paths index, case-folded — `_deck_dedup_index` lower-cases
    what it collects and a MusicEntry keeps the path as it was written."""
    return {path_key(p) for p in used_paths}


def _is_used(entry, used: set) -> bool:
    return path_key(entry.path) in used


def _pop_of(entry, dance_class) -> int:
    """The play count as the app ranks by it — weighted for the start class."""
    return int(round(effective_popularity(entry, dance_class)))


def _fin_of(entry) -> int:
    """How many of those past events danced this track in their FINAL round."""
    return int(getattr(entry, "final_plays", 0) or 0)


def _sem_of(entry) -> int:
    """…and how many in their SEMIFINAL."""
    return int(getattr(entry, "semi_plays", 0) or 0)


def entry_tags(entry) -> str:
    """The whole COMM comment in one cell: 'B,A,S+instr;vocal_f;classic'.

    The class codes come first, '+instr' rides on them, and the free markers
    follow after semicolons in the order they were typed. '*' means the comment
    carried no class codes; a bare '*' means it said nothing at all."""
    parts = list(getattr(entry, "classes_ok", None) or [])
    out = ",".join(parts) if parts else "*"
    if getattr(entry, "is_instrumental", False):
        out += "+instr"
    for marker in (getattr(entry, "comment_tags", None) or []):
        out += ";" + marker
    return out


def pool_dance(entry) -> str:
    """The dance code a track is grouped under everywhere in this module."""
    return entry.dance or warmup_code(entry) or "??"


def _row(n: int, entry, dance_class, used_paths, sound=None) -> str:
    bpm = entry.bpm if entry.bpm is not None else "?"
    year = entry.year if entry.year else "?"
    used = "yes" if _is_used(entry, used_paths) else "no"
    artist = (getattr(entry, "tag_artist", None) or "").strip()
    name = f"{artist} – {entry.title}" if artist else entry.title
    snd = code_text((sound or {}).get(str(entry.path)))
    return (f"{n:4d} | {pool_dance(entry)} | {bpm} | {snd} | "
            f"{_pop_of(entry, dance_class)} | {_fin_of(entry)} | "
            f"{_sem_of(entry)} | {used} | "
            f"{entry_tags(entry)} | {year} | {name[:70]}")


def catalog_rows(candidates, numbers, *, dance_class=None, used_paths=(),
                 sound=None) -> str:
    """The rows for `numbers` — 1-based positions in the FULL pool, which is the
    only handle the model ever gets on a track.

    `sound` is the {path: code} map from `planner.sound.sound_codes`; without it
    every row simply says '---' in the snd column."""
    used = _used_set(used_paths)
    lines = ([_ROW_LEGEND, "", _ROW_HEADER] if sound
             else [_ROUND_LEGEND, "", _ROW_HEADER])
    for n in numbers:
        lines.append(_row(n, candidates[n - 1], dance_class, used, sound))
    return "\n".join(lines)


def catalog_text(candidates, *, dance_class=None, used_paths=(), sound=None) -> str:
    """Every candidate, numbered by position — for a pool small enough that
    searching it would be silly."""
    return catalog_rows(candidates, range(1, len(candidates) + 1),
                        dance_class=dance_class, used_paths=used_paths,
                        sound=sound)


def played_together(numbers, candidates, playlists_of) -> str:
    """Which of the rows on the table have been played in the same events.

    The library knows, for every track, which of the ~2000 saved M3U playlists
    it turns up in — that is the same data 'Similar tracks → by playlist' ranks
    on. Two tracks that keep appearing in the same lists have worked together in
    a real room, which is knowledge no audio feature carries.

    Only pairs where BOTH rows were sent are listed, best overlap first, so the
    model can act on every number it reads. Empty string when nothing qualifies
    — the block is then left out of the prompt entirely.

    `playlists_of(entry) -> set[str]` is handed in (MusicLibrary.playlists_for)
    so this module stays free of the library.
    """
    if not playlists_of:
        return ""
    sets: dict[int, set] = {}
    for n in numbers:
        try:
            pls = playlists_of(candidates[n - 1])
        except Exception as exc:          # a broken index must not kill the run
            log.debug("🤝 no playlist history for row %d: %s", n, exc)
            continue
        if pls:
            sets[n] = pls

    rows = sorted(sets)
    partners: dict[int, list[tuple[float, int]]] = {}
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            shared = len(sets[a] & sets[b])
            if shared < _PAIRS_MIN_SHARED:
                continue
            score = shared / len(sets[a] | sets[b])
            partners.setdefault(a, []).append((score, b))
            partners.setdefault(b, []).append((score, a))
    if not partners:
        return ""

    # The rows with the most history first: if the budget cuts the block off,
    # what survives is the part with something to say.
    ranked = sorted(partners, key=lambda n: (-len(partners[n]), n))[:_PAIR_ROWS]
    lines = ["tracks you have played in the same events before — a row, then "
             "the rows it shares past playlists with, strongest first:"]
    for n in sorted(ranked):
        best = sorted(partners[n], key=lambda p: -p[0])[:_PAIRS_PER_ROW]
        lines.append(f"  {n} with " + ", ".join(str(b) for _, b in best))
    return "\n".join(lines)


# ── Step 1: what is in there ──────────────────────────────────
def library_summary(candidates, *, dance_class=None, used_paths=(),
                    sound=None) -> str:
    """One line per dance: how much there is and what shape it is in. This is
    all the model sees of the library before it decides what to ask for."""
    used = _used_set(used_paths)
    order: list[str] = []
    stats: dict[str, dict] = {}
    for e in candidates:
        code = e.dance or warmup_code(e) or "??"
        if code not in stats:
            order.append(code)
            stats[code] = {"n": 0, "bpm": [], "proven": 0, "finals": 0,
                       "semis": 0, "fresh": 0, "unused": 0}
        st = stats[code]
        st["n"] += 1
        if e.bpm is not None:
            st["bpm"].append(e.bpm)
        pop = _pop_of(e, dance_class)
        if pop >= _PROVEN_PLAYS:
            st["proven"] += 1
        elif pop == 0:
            st["fresh"] += 1
        if _fin_of(e):
            st["finals"] += 1
        if _sem_of(e):
            st["semis"] += 1
        if not _is_used(e, used):
            st["unused"] += 1

    lines = ["dance | pool | bpm   | proven | finalists | semifinalists | "
             "fresh | unplanned"]
    for code in order:
        st = stats[code]
        span = f"{min(st['bpm'])}-{max(st['bpm'])}" if st["bpm"] else "?"
        lines.append(f"{code:>5} | {st['n']:>4} | {span:>5} | {st['proven']:>6} | "
                     f"{st['finals']:>9} | {st['semis']:>13} | "
                     f"{st['fresh']:>5} | {st['unused']:>9}")
    lines.append("")
    lines.append("'finalists' / 'semifinalists' = tracks that a past event danced "
                 "in its FINAL or its SEMIFINAL round (the \"min_fin\" and "
                 "\"min_sem\" filters). Play count alone does not say that: the "
                 "most-played titles are often heat music.")
    markers = marker_counts(candidates)
    if markers:
        lines.append("")
        lines.append("comment markers in this pool (searchable with \"tag\"):")
        lines.append("  " + ", ".join(f"{name} ({n})" for name, n in markers))
    if sound:
        # Coverage matters: a half-analysed library would leave every "energy"
        # query quietly short, and the model should know that before it spends
        # a query on one.
        known = sum(1 for e in candidates if str(e.path) in sound)
        lines.append("")
        lines.append(
            f"sound analysis: {known} of {len(candidates)} tracks are analysed."
            " Each carries energy, brightness and drive, 1-5 among tracks of"
            " its own dance (searchable with \"energy\", \"bright\", \"drive\").")
    return "\n".join(lines)


def marker_counts(candidates, *, top: int = _MARKERS_SHOWN) -> list[tuple[str, int]]:
    """The most common free comment markers in a pool, commonest first.

    The model cannot guess that 'vocal_f' or 'eintanzen' exist, so step 1 is told
    which markers are actually in front of it — the long rare tail is cut off."""
    counts: dict[str, int] = {}
    for e in candidates:
        for marker in (getattr(e, "comment_tags", None) or []):
            counts[marker] = counts.get(marker, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top]


# ── Step 1: the queries that come back ───────────────────────────
_SEARCH_CONTRACT = f"""\
This is step 1 of 2. The library is far too big to show you whole, so tell me
what you want to see. Answer with ONE JSON object and nothing else:

{{"queries": [{{"dance": "LW", "min_pop": 3, "limit": 60}},
             {{"dance": "LW", "sort": "fresh", "limit": 20}}]}}

Query keys — "dance" is the only one you must give:
  dance    dance code from the summary, e.g. "LW"
  bpm      "28-30" or 29 — bars per minute, the tempo column
  min_pop  / max_pop   play count in past events (0 = never played)
  min_fin  how many past events danced it in their FINAL round (1 = only
           tracks that have been in a final)
  min_sem  the same for the SEMIFINAL — the other round that is picked by
           hand rather than filled
  unused   true → only tracks no open playlist has already taken
  class    only tracks the comment tag clears for this start class, e.g. "S"
  tag      one of the comment markers listed under the summary, e.g. "classic"
  instr    true → instrumentals only, false → exclude them
  focus    true → only tracks whose class tag is limited to the higher
           classes (no D and no C in it) — music chosen for that level,
           rather than music the lower classes also dance well to
  energy   "4-5" or 3 — how loud a track sits among its own dance, 1 quiet
           to 5 loud, measured from the audio
  bright   the same 1-5 scale for how much high end it carries, 1 dark
  drive    the same 1-5 scale for how hard the beat pushes, 1 soft
  search   substring of the artist or the title (accents and punctuation
           are ignored: "senorita" finds "Señorita", "dont stop" finds
           "Don't Stop")
  sort     "pop" (most played first, the default), "finals" (most finals
           first), "semis" (most semifinals first), "fresh" (least played
           first), "random"
  limit    rows for this query, at most {_QUERY_MAX} (default {_QUERY_LIMIT})

You get ONE search round and at most {_ROWS_MAX} rows over all queries
together, so spend them well: ask per dance, and pair a proven query with a
fresh or random one wherever you want room to surprise. You cannot pick a
track you did not ask to see.
"""


def parse_queries(text: str) -> list[dict]:
    """Pull the query list out of step 1. [] when there is nothing usable —
    the caller then falls back to a default sweep rather than failing."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        payload = json.loads(cleaned[start:end + 1])
    except ValueError:
        return []
    queries = payload.get("queries")
    if not isinstance(queries, list):
        return []
    return [q for q in queries if isinstance(q, dict)]


def _bpm_span(value):
    """'28-30' / 29 / '29' -> (lo, hi). None when it is not a tempo at all."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), float(value)
    text = str(value or "").strip()
    if not text:
        return None
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    try:
        return float(text), float(text)
    except ValueError:
        return None


def _bound(value):
    """A numeric query bound, or None when the model wrote something else."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_SOUND_KEYS = ("energy", "bright", "drive")


def _sound_ok(entry, query: dict, sound) -> bool:
    """The energy / bright / drive filters, read off the track's sound code.

    A query on a digit can only be answered for an analysed track, so the
    unanalysed ones drop out of such a query rather than slipping through."""
    wanted = [(i, _bpm_span(query[k]))          # same "1-2" or 3 shape as bpm
              for i, k in enumerate(_SOUND_KEYS) if k in query]
    wanted = [(i, span) for i, span in wanted if span]
    if not wanted:
        return True
    code = (sound or {}).get(str(entry.path))
    if not code:
        return False
    return all(span[0] <= code[i] <= span[1] for i, span in wanted)


def _search_key(s: str) -> str:
    """A title boiled down to what a half-remembered spelling of it can match.

    The normaliser folds accents and turns punctuation into spaces; dropping
    the spaces on top of that lets a wished "dont stop" find "Don't Stop" and
    "mas que nada" find "Mas Que Nada (Radio Edit)"."""
    return _norm_title(s).replace(" ", "")


def _matches(entry, query: dict, dance_class, used_paths, sound=None) -> bool:
    dance = str(query.get("dance") or "").strip().upper()
    if dance and (entry.dance or warmup_code(entry) or "") != dance:
        return False

    span = _bpm_span(query.get("bpm"))
    if span and (entry.bpm is None or not span[0] <= entry.bpm <= span[1]):
        return False

    pop = _pop_of(entry, dance_class)
    lo, hi = _bound(query.get("min_pop")), _bound(query.get("max_pop"))
    if lo is not None and pop < lo:
        return False
    if hi is not None and pop > hi:
        return False

    min_fin = _bound(query.get("min_fin"))
    if min_fin is not None and _fin_of(entry) < min_fin:
        return False
    min_sem = _bound(query.get("min_sem"))
    if min_sem is not None and _sem_of(entry) < min_sem:
        return False

    if query.get("unused") and _is_used(entry, used_paths):
        return False

    cls = str(query.get("class") or "").strip().upper()
    if cls:
        allowed = getattr(entry, "classes_ok", None)
        if allowed and cls not in allowed:
            return False

    if "instr" in query:
        if bool(query["instr"]) != bool(getattr(entry, "is_instrumental", False)):
            return False

    if query.get("focus") and not class_focused(entry):
        return False

    tag = str(query.get("tag") or "").strip().lower()
    if tag and tag not in (getattr(entry, "comment_tags", None) or []):
        return False

    needle = _search_key(str(query.get("search") or ""))
    if needle:
        hay = _search_key(f"{getattr(entry, 'tag_artist', '') or ''} "
                          f"{entry.title}")
        if needle not in hay:
            return False

    return _sound_ok(entry, query, sound)


def run_queries(queries: list[dict], candidates, *, dance_class=None,
                used_paths=(), rows_max: int = _ROWS_MAX,
                sound=None) -> list[int]:
    """The 1-based pool positions the queries select, in the order asked for.

    Every query keeps its own limit, a number already sent is never sent twice,
    and `rows_max` is the hard budget over all of them together."""
    used = _used_set(used_paths)
    picked: list[int] = []
    seen: set[int] = set()
    for query in queries:
        try:
            limit = int(query.get("limit") or _QUERY_LIMIT)
        except (TypeError, ValueError):
            limit = _QUERY_LIMIT
        limit = max(1, min(limit, _QUERY_MAX))

        hits = [i for i, e in enumerate(candidates, start=1)
                if i not in seen
                and _matches(e, query, dance_class, used, sound)]
        sort = str(query.get("sort") or "pop").strip().lower()
        if sort == "semis":
            hits.sort(key=lambda i: (-_sem_of(candidates[i - 1]),
                                     -_pop_of(candidates[i - 1], dance_class)))
        elif sort == "finals":
            hits.sort(key=lambda i: (-_fin_of(candidates[i - 1]),
                                     -_pop_of(candidates[i - 1], dance_class)))
        elif sort == "fresh":
            hits.sort(key=lambda i: _pop_of(candidates[i - 1], dance_class))
        elif sort == "random":
            random.shuffle(hits)
        else:
            hits.sort(key=lambda i: -_pop_of(candidates[i - 1], dance_class))

        for i in hits[:limit]:
            if len(picked) >= rows_max:
                return picked
            picked.append(i)
            seen.add(i)
    return picked


def default_queries(candidates, *, rows_max: int = _ROWS_MAX) -> list[dict]:
    """The sweep used when step 1 gives nothing usable: a proven and a fresh
    slice of every dance, so a failed search round still yields a playlist."""
    dances: list[str] = []
    for e in candidates:
        code = e.dance or warmup_code(e) or "??"
        if code not in dances:
            dances.append(code)
    if not dances:
        return []
    share = max(4, rows_max // (len(dances) * 2))
    out: list[dict] = []
    for code in dances:
        out.append({"dance": code, "sort": "pop", "limit": share})
        out.append({"dance": code, "sort": "fresh", "limit": max(2, share // 3)})
    return out


def _tempo_note(dances: list[str], dance_class: str) -> str:
    parts = []
    for d in dances:
        lo, hi = TEMPO_RANGES.get(d, {}).get(dance_class, (0, 0))
        if lo:
            parts.append(f"{DANCE_NAMES.get(d, d)} ({d}) {lo}-{hi}")
    return "TSO tempo (bars/minute) for this class: " + "; ".join(parts) if parts else ""


def build_prompt(rules: str, task: str, catalog: str) -> tuple[str, str]:
    """Step 2 — (system, user) for OpenRouter; the CLI gets them concatenated."""
    system = rules.strip() + "\n\n" + _OUTPUT_CONTRACT
    user = (f"{task.strip()}\n\nThe tracks you asked for — pick only from "
            f"these:\n{catalog}\n")
    return system, user


def build_search_prompt(rules: str, task: str, summary: str) -> tuple[str, str]:
    """Step 1 — the same rules, but what is wanted back is a set of queries."""
    system = rules.strip() + "\n\n" + _SEARCH_CONTRACT
    user = f"{task.strip()}\n\nWhat the library holds for this job:\n{summary}\n"
    return system, user


def competition_task(style: str, age: str, dance_class: str,
                     dances: list[str], rounds, brief: str) -> str:
    """The 'what to build' half for a competition: rounds, heats, dances."""
    lines = [f"Build the music for a {age} {dance_class}-class {style} competition.",
             "Rounds and how many songs of EVERY dance each one needs:"]
    for rc in rounds:
        lines.append(f"  • {rc.name}: {rc.heats} heat(s) × "
                     f"{len(dances)} dances = {rc.heats * len(dances)} songs")
    lines.append("Dance order inside every heat: "
                 + ", ".join(f"{DANCE_NAMES.get(d, d)} ({d})" for d in dances))
    total = sum(rc.heats for rc in rounds) * len(dances)
    lines.append(f"That is {total} songs in total. Fill every slot.")
    note = _tempo_note(dances, dance_class)
    if note:
        lines.append(note)
    if dance_class in HIGHER_CLASSES:
        # The tags column says which classes a track is cleared for. A tag that
        # names only the higher classes was written for this level; one that
        # also carries D and C is a title the lower classes dance well to and
        # this one only tolerably. Past plays at this level overrule the tag:
        # somebody put that track in a real B/A/S list on purpose.
        lines.append(
            f"This is a {dance_class}-class event: prefer tracks whose tags name"
            " only the higher classes (no D, no C) — the \"focus\" query key"
            " finds exactly those. Avoid the ones tagged D or C as well unless"
            " their pop count says they have been played at this level before;"
            " those were chosen deliberately and are fine.")
    if brief.strip():
        lines.append(f"\nExtra wishes for this event: {brief.strip()}")
    return "\n".join(lines)


def wish_task(wishes: str, brief: str = "") -> str:
    """The 'what to build' half for a list of titles the user pasted.

    The wishes come off a sheet of paper, not out of a database: shortened,
    mistyped, sometimes only half a title, with the dance in a code next to it
    and the important ones marked with an exclamation mark. The model's job is
    the lookup — find the library track each line means — and then the order."""
    lines = [
        "Build ONE flat playlist out of the wishes below, in the order they "
        "are written.",
        "",
        "The playlist IS the wish list: one track per wish and NOTHING else. "
        "Do not add a track to round the list out, to balance the dances, to "
        "fill a heat or to make it flow better — four wishes are a playlist of "
        "four tracks. The rules you were given say how to choose between the "
        "candidates for a wish; in this mode they never add one of their own.",
        "",
        "They are written the way the user found it easiest: one wish per "
        "line, a sentence describing what should be in the list, a whole "
        "sheet pasted in with a column per dance, or any mixture of those. "
        "Read them the way a colleague handed the same note would, and do not "
        "expect a fixed layout.",
        "",
        "What to look out for:",
        "  • A two-letter code beside a title names its dance, and in a table "
        "it can stand in the header row for the whole column "
        "(lw = Slow Waltz / Langsamer Walzer, t / ta = Tango, ww = Viennese "
        "Waltz / Wiener Walzer, sf = Slowfox, qs = Quickstep, sb / sa = Samba, "
        "cc = Cha Cha, rb / ru = Rumba, pd = Paso Doble, ji = Jive).",
        "  • The titles are SHORTENED and often misspelt — 'melacol?a lw' is "
        "the Slow Waltz called Melancolía. Work out what was meant.",
        "  • ! or !! after a title marks one the user especially wants. Those "
        "must be in the list; if one cannot be found at all, say so in "
        '"notes".',
        "  • A wish with no dance code takes the dance of its column, or of "
        "the sentence it stands in. If nothing says, the track itself does.",
        "  • Anything that is not a title is an instruction about the list — "
        "follow it.",
        "",
        "Use the \"search\" query key in step 1 to look each wished title up — "
        "a short, distinctive part of the title (no accents, no punctuation) "
        "finds it, and \"dance\" narrows it to the right dance. Ask for the "
        "wishes you are least sure about with a wider search rather than a "
        "narrower one.",
        "",
        "ONE query per wish, and put \"limit\": 8 on each of them. The row "
        "budget is shared: at 60 rows a wish the later wishes get nothing "
        "back, and a wish you never saw is a wish you cannot pick.",
        "",
        "Where a wish NAMES a track, pick the ONE catalog row that really is "
        "it. A track that merely sounds similar is not what was asked for — if "
        "a named wish is not in the library, leave it out and say so in "
        "\"notes\" instead of filling the gap with something else. Where a "
        "wish only DESCRIBES what is wanted, the choice is yours; say in "
        "\"why\" which wish that pick answers. Either way it stays one track "
        "per wish, and the playlist ends where the wishes end.",
        "",
        "The wishes:",
        wishes.strip(),
    ]
    if brief.strip():
        lines.append(f"\nWhat this list is for: {brief.strip()}")
    return "\n".join(lines)


# How many titles the model may swap per variant and competition. The drafts
# are already sound; this is a second opinion, not a rewrite.
EVENT_MAX_SWAPS = 6

# The contract for refining an event day: swaps against drafts it was shown.
_EVENT_CONTRACT = """\
Answer with ONE JSON object and nothing else. No prose, no markdown fence.

{"swaps": [{"variant": "<variant key>", "round": "<round name>",
            "heat": <heat number, 1 = first>, "dance": "<dance code>",
            "n": <catalogue number>, "why": "<why THIS track, in a few words>"}],
 "notes": {"<variant key>": "<one sentence on what you changed and why>"}}

Rules for the answer:
• A swap puts row "n" into exactly that slot of that variant's draft. Swap only
  where it clearly makes the slot better; an empty "swaps" list is a fine
  answer when the draft already holds up.
• "n" must be a number from the catalogue you were shown, and the row's dance
  must be the slot's dance. Never invent a track.
• A variant plays no title twice in the whole day (Paso Doble only not twice
  in a round). Do not swap in a title that variant already has in another
  slot, and leave the rows marked used=yes alone — another competition of the
  day has them.
• At most %d swaps per variant.
• For "like_last_year" and "last_year_renewed" last year's titles stay. A
  swap there is only OFFERED next to the title as a replacement, so name the
  one you would really offer in place of the "→ suggested" title.
• "why" is read by the person running the event: the real reason — tempo,
  play history, how it sounds, what it follows — in one short clause.
"""


def event_task(label: str, style: str | None, dance_class: str,
               dances: list[str], rounds, drafts: dict, intents: dict,
               lost: list[str] = ()) -> str:
    """The 'what to check' half for one competition of an event day.

    `drafts` is {variant: [(round, heat, dance, n, tier, source, suggested_n)]}
    in playing order; `intents` says in a sentence what each variant is for.
    `lost` lists the swaps an earlier look proposed that did not go in."""
    kind = f"{style} " if style else "mixed-style "
    lines = [f"An event day is planned in {len(drafts)} variants. Check the "
             f"{kind}competition \"{label}\" ({dance_class}-class) in each of "
             "them and swap titles where a better one is in the catalogue.",
             "Rounds and heats:"]
    for rc in rounds:
        lines.append(f"  • {rc.name}: {rc.heats} heat(s) × {len(dances)} dances")
    lines.append("Dance order inside every heat: "
                 + ", ".join(f"{DANCE_NAMES.get(d, d)} ({d})" for d in dances))
    note = _tempo_note(dances, dance_class)
    if note:
        lines.append(note)
    lines += ["",
              "Where a title comes from, its tier:",
              "  event   — this event played it for this competition in an "
              "earlier year",
              "  class   — other events played it for this class",
              "  new     — came into the archive in the last 18 months, never "
              "played at this class; its source says how much it sounds like "
              "one of those (timbre)",
              "  rare    — played at most twice at this class so far, new "
              "titles included; "
              "its source says how often and what it sounds like",
              "  library — the rest of the library that fits the class"]
    for variant, slots in drafts.items():
        lines += ["", f'Draft "{variant}" — {intents.get(variant, "")}']
        for rnd, heat, dance, n, tier, source, suggested in slots:
            if n is None:
                lines.append(f"  {rnd} heat {heat} {dance}: (empty)")
                continue
            line = f"  {rnd} heat {heat} {dance}: #{n} {tier}"
            if source:
                line += f" · {source[:80]}"
            if suggested is not None:
                line += f" → suggested #{suggested}"
            lines.append(line)
    if lost:
        lines += ["", "A second look. These swaps from your first answer did not "
                  "go in — mostly because a more important competition of the "
                  "day took the title first:"]
        lines += [f"  {x}" for x in lost]
        lines.append("Those titles stay out. Where the slot is still weak, find "
                     "another title for it; improve elsewhere only where it "
                     "clearly helps.")
    return "\n".join(lines)


def build_event_prompt(rules: str, task: str, catalog: str) -> tuple[str, str]:
    """(system, user) for the event refine — the rules, then the swap contract."""
    system = rules.strip() + "\n\n" + _EVENT_CONTRACT % EVENT_MAX_SWAPS
    user = (f"{task.strip()}\n\nThe catalogue — swap in only these rows:\n"
            f"{catalog}\n")
    return system, user


def flat_task(count: int, brief: str) -> str:
    lines = [f"Build ONE flat playlist of about {count} tracks, in playing order.",
             "No rounds, no heats — just the order they get played in."]
    if brief.strip():
        lines.append(f"\nWhat this list is for: {brief.strip()}")
    return "\n".join(lines)


# ── Reading the answer back ──────────────────────────────────────────────────
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _json_objects(text: str) -> list:
    """Every top-level JSON object in a reply, in order.

    Models do not always answer with exactly one object: one notices a mistake
    halfway ("Wait — that object is broken, here is the corrected answer") and
    writes a second one, or the object is followed by a sentence of commentary.
    Taking the first "{" up to the last "}" then chokes on the whole lot
    ("Extra data"), so each object is decoded on its own and whatever sits
    between them is skipped.
    """
    dec = json.JSONDecoder()
    found, i = [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return found
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            i += 1                      # not the start of an object after all
            continue
        if isinstance(obj, dict):
            found.append(obj)
        i = end


def parse_reply(text: str) -> dict:
    """Pull the JSON object out of the model's answer. Raises on nonsense."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    objects = _json_objects(cleaned)
    if not objects:
        raise RuntimeError(f"no JSON in the answer: {cleaned[:200]}")
    # More than one playlist means the model corrected itself: the LAST
    # complete answer is the one it stands by, the earlier one it disowned.
    playlists = [o for o in objects
                 if isinstance(o.get("playlist"), list) and o["playlist"]]
    payload = playlists[-1] if playlists else objects[-1]
    picks = payload.get("playlist") or []
    if not payload.get("notes"):
        payload = {**payload,
                   "notes": next((o["notes"] for o in reversed(objects)
                                  if o.get("notes")), "")}
    if not picks:
        # A cut-off answer: the wrapper never closed, so only the pick objects
        # inside it survived the decode. They are the useful half anyway.
        picks = [o for o in objects if "n" in o]
    if not picks:
        raise RuntimeError("the answer carried an empty playlist")
    out = []
    for item in picks:
        if isinstance(item, int):
            item = {"n": item}
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            continue
        heat = item.get("heat")
        out.append({
            "n": n,
            "round": str(item.get("round") or ""),
            "heat": int(heat) if isinstance(heat, (int, str)) and str(heat).isdigit() else 0,
            # Free text from a model: kept short, and never parsed for anything.
            "why": " ".join(str(item.get("why") or "").split())[:_WHY_MAX],
        })
    if not out:
        raise RuntimeError("the answer held no usable catalog numbers")
    return {"picks": out, "notes": str(payload.get("notes") or "")}


def parse_swaps(text: str) -> dict:
    """{"swaps": [...], "notes": {variant: str}} out of an event-refine answer.

    Swaps that miss a field are dropped here; whether one may be applied is the
    planner's business. Raises when the answer holds no JSON at all."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    objects = _json_objects(cleaned)
    if not objects:
        raise RuntimeError(f"no JSON in the answer: {cleaned[:200]}")
    # As with a playlist, the last complete answer is the one it stands by.
    answers = [o for o in objects if isinstance(o.get("swaps"), list)]
    payload = answers[-1] if answers else objects[-1]
    swaps = []
    for item in payload.get("swaps") or []:
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
            heat = int(item.get("heat") or 1)
        except (TypeError, ValueError):
            continue
        swaps.append({
            "variant": str(item.get("variant") or ""),
            "round": str(item.get("round") or ""),
            "heat": heat,
            "dance": str(item.get("dance") or "").upper(),
            "n": n,
            "why": " ".join(str(item.get("why") or "").split())[:_WHY_MAX],
        })
    notes = payload.get("notes")
    notes = ({str(k): " ".join(str(v).split())[:_WHY_MAX * 2]
              for k, v in notes.items()} if isinstance(notes, dict) else {})
    return {"swaps": swaps, "notes": notes}


def pick_reasons(picks, candidates, notes: str = "") -> str:
    """The model's own account of the playlist: its summary, then one line per
    track with the reason it gave for that track.

    This is what the transcript shows at the end of a run — the picks arrive as
    bare numbers everywhere else, and the reasoning behind them would otherwise
    be thrown away the moment the grid is filled.
    """
    lines: list[str] = []
    if notes.strip():
        lines.append(notes.strip())
    body: list[str] = []
    for p in picks:
        n = p.get("n")
        if not isinstance(n, int) or not 1 <= n <= len(candidates):
            continue
        e = candidates[n - 1]
        artist = (getattr(e, "tag_artist", None) or "").strip()
        name = f"{artist} – {e.title}" if artist else e.title
        where = ""
        if p.get("round"):
            where = f"{p['round']}" + (f" h{p['heat']}" if p.get("heat") else "")
            where = f" · {where}"
        body.append(f"{n:>4} · {pool_dance(e)}{where} · {name[:60]}")
        why = (p.get("why") or "").strip()
        if why:
            body.append(f"       {why}")
    if not body:
        return ""
    if lines:
        lines.append("")
    return "\n".join(lines + body)


def assemble_grid(picks, candidates, dances: list[str], rounds) -> dict:
    """Model answer → the round → heat → dance grid a deck loads (Playlist).

    A pick that names a round and heat lands there. Anything the model
    mislabelled — an unknown round name, a heat past the end — still gets the
    first free slot of its own dance, so a formatting slip costs no songs. A
    number outside the catalog is dropped: that is the whole point of handing
    out numbers instead of titles."""
    dance_idx = {d: i for i, d in enumerate(dances)}
    grid = {rc.name: [[None] * len(dances) for _ in range(rc.heats)]
            for rc in rounds}
    by_name = {rc.name.lower(): rc.name for rc in rounds}
    used: set[str] = set()
    leftovers = []

    for p in picks:
        n = p["n"]
        if not (1 <= n <= len(candidates)):
            continue
        e = candidates[n - 1]
        if e.dance not in dance_idx:
            continue
        if str(e.path) in used and e.dance not in ALLOW_REPEAT:
            continue
        di = dance_idx[e.dance]
        heats = grid.get(by_name.get(p["round"].strip().lower(), ""))
        h = p["heat"] - 1
        if heats is not None and 0 <= h < len(heats) and heats[h][di] is None:
            heats[h][di] = e
        else:
            leftovers.append(e)
            continue
        used.add(str(e.path))

    for e in leftovers:
        if str(e.path) in used and e.dance not in ALLOW_REPEAT:
            continue
        di = dance_idx[e.dance]
        for rc in rounds:
            placed = False
            for heat in grid[rc.name]:
                if heat[di] is None:
                    heat[di] = e
                    used.add(str(e.path))
                    placed = True
                    break
            if placed:
                break
    return grid


# How long to wait before asking a wobbling host again. Three tries on top of
# the first one: a 529 usually clears inside a minute, and a run that has
# already spent minutes building its prompt is worth two more.
_RETRY_WAITS = (10, 30, 60)

_TRANSIENT_RE = re.compile(
    r"""(?: http\s*(?:429|5\d\d)            # 'HTTP 529: overloaded'
        | overload
        | rate[\s_-]?limit
        | too\s+many\s+requests
        | temporarily\s+unavailable
        | (?:internal\s+)?server\s+error
        | bad\s+gateway | service\s+unavailable
        | connection\s+(?:reset|refused|aborted|error)
        | remote\s+end\s+closed | broken\s+pipe
        )""", re.IGNORECASE | re.VERBOSE)


def is_transient(exc: BaseException) -> bool:
    """True for a failure that is the host having a moment, not the request
    being wrong.

    A 429/5xx, an overload, a dropped socket: the same prompt may well go
    through a minute later. A bad key, a missing CLI, a hit usage limit or a
    malformed answer will fail exactly the same way, so those are NOT transient
    and must reach the fallback backend at once.

    Neither is a timeout: the host already had its whole timeout, and asking
    again three times over two backends and two turns kept a hung run going
    for hours. A 504 still is — that is the gateway answering.
    """
    reason = getattr(exc, "reason", None)            # URLError wraps the socket's
    if isinstance(exc, (subprocess.TimeoutExpired, TimeoutError)) \
            or isinstance(reason, TimeoutError):
        return False
    if isinstance(exc, OSError):
        # URLError, ConnectionReset, socket timeout — all OSError underneath.
        return True
    return bool(_TRANSIENT_RE.search(str(exc)))


# A limit that waiting lifts: the subscription's usage limit ('Claude AI usage
# limit reached|<epoch>', "You've hit your limit · resets 3pm") or an API's 429.
_RATE_LIMIT_RE = re.compile(
    r"usage\s+limit|hit\s+your\s+(?:\w+\s+)?limit|limit\s+reached"
    r"|rate[\s_-]?limit|too\s+many\s+requests|\b429\b", re.IGNORECASE)
_RESET_EPOCH_RE = re.compile(r"limit reached\|(\d{10})\b", re.IGNORECASE)


def is_rate_limited(exc: BaseException) -> bool:
    """True when asking again later — not now — would go through."""
    return bool(_RATE_LIMIT_RE.search(str(exc)))


def rate_limit_reset(text: str) -> float | None:
    """When the limit lifts (epoch seconds), if the message says so."""
    m = _RESET_EPOCH_RE.search(text or "")
    return float(m.group(1)) if m else None


def _try_backend(call, label: str, *, on_step=None, sleep=time.sleep,
                 cancel=None):
    """Run one backend, giving a server-side wobble 10s, 30s and 60s to pass.

    Every attempt but the last is followed by a transcript note, so a run that
    is quietly waiting out a 529 does not look like a run that has hung. A
    stop cuts the wait short, and an answer that lands after it is dropped.
    """
    for attempt, wait in enumerate(_RETRY_WAITS + (None,), start=1):
        _raise_if_cancelled(cancel)
        try:
            answer = call()
            _raise_if_cancelled(cancel)
            return answer
        except Exception as exc:
            if wait is None or not is_transient(exc):
                raise
            log.warning("🤖 %s wobbled, asking again in %ds\n"
                        "attempt: %d of %d\n"
                        "error: %s",
                        label, wait, attempt, len(_RETRY_WAITS) + 1, exc)
            _step(on_step, "note",
                  f"⏳ {label} — attempt {attempt} of {len(_RETRY_WAITS) + 1}",
                  f"{exc}\n\nServer-side hiccup. Asking again in {wait}s.")
            if cancel is not None:
                cancel.wait(wait)
            else:
                sleep(wait)


def _ask(system: str, user: str, *, model: str, config_dir: str,
         timeout: int, on_step=None, sleep=time.sleep,
         cancel=None) -> tuple[str, str]:
    """One question, whichever backend answers it. Returns (text, backend).

    Tier 1 is `claude -p`; anything that goes wrong there — CLI missing, login
    expired, a timeout — falls through to the OpenAI-compatible backend (that is
    OpenRouter unless the config names another host). Each tier gets the retries
    above first, so a passing 529 costs a wait, not the fallback. Only when BOTH
    fail does this raise, and the message then names both failures.
    """
    failures = []
    try:
        raw = _try_backend(
            lambda: call_claude_cli(system + "\n\n" + user, model=model,
                                    timeout=timeout, config_dir=config_dir,
                                    cancel=cancel),
            "claude -p", on_step=on_step, sleep=sleep, cancel=cancel)
        return raw, f"claude -p ({model})"
    except Cancelled:
        raise
    except Exception as exc:
        log.warning("🤖 claude -p failed: %s", exc)
        failures.append(f"claude -p — {exc}")

    cfg = ai.load_openrouter_config()
    base = cfg.get("base_url", "")
    host = ai.api_host(base)
    try:
        raw = _try_backend(
            lambda: ai.openrouter_chat(cfg["api_key"], cfg["model"],
                                               system, user, timeout=timeout,
                                               base_url=base),
            host, on_step=on_step, sleep=sleep, cancel=cancel)
        return raw, f"{host} ({cfg['model']})"
    except Cancelled:
        raise
    except Exception as exc:
        log.warning("🤖 %s failed: %s", host, exc)
        failures.append(f"{host} — {exc}")

    raise RuntimeError("Both backends failed.\n\n" + "\n\n".join(failures))


def _step(on_step, role: str, title: str, text: str) -> None:
    """Hand one line of the exchange to whoever is watching, if anyone is.

    `role` is 'sent' (we asked), 'received' (the model answered) or 'note'
    (what the program did in between, e.g. running the queries). A watcher that
    throws must not sink a run that is otherwise fine."""
    if on_step is None:
        return
    try:
        on_step(role, title, text)
    except Exception:
        log.exception("🤖 Transcript watcher failed")


def search_rows(rules: str, task: str, candidates, *, model: str = CLAUDE_MODEL,
                config_dir: str = "", timeout: int = 600, dance_class=None,
                used_paths=(), on_step=None, sound=None,
                cancel=None) -> list[int]:
    """Step 1: let the model say which slice of the library it wants to see.

    Returns the pool positions to show it. A search round that fails outright,
    or answers with nothing usable, falls back to `default_queries` instead of
    sinking the run — the picking turn is the one that matters, and it reports
    a dead backend on its own.
    """
    summary = library_summary(candidates, dance_class=dance_class,
                              used_paths=used_paths, sound=sound)
    system, user = build_search_prompt(rules, task, summary)
    _step(on_step, "sent", "1 · What the model is asked to search",
          system + "\n\n" + user)
    try:
        raw, backend = _ask(system, user, model=model, config_dir=config_dir,
                            timeout=timeout, on_step=on_step, cancel=cancel)
        _step(on_step, "received", f"1 · Its queries — {backend}", raw)
        queries = parse_queries(raw)
        log.info("🤖 search round via %s\n"
                 "queries: %d", backend, len(queries))
    except Cancelled:
        raise
    except Exception as exc:
        log.warning("🤖 search round failed, sweeping instead: %s", exc)
        _step(on_step, "note", "1 · The search round failed",
              f"{exc}\n\nSweeping the pool instead.")
        queries = []

    numbers = run_queries(queries, candidates, dance_class=dance_class,
                          used_paths=used_paths, sound=sound) if queries else []
    if not numbers:
        # No queries, or only queries that match nothing. Sweep the pool, or
        # step 2 would be handed an empty catalog and could pick nothing.
        numbers = run_queries(default_queries(candidates), candidates,
                              dance_class=dance_class, used_paths=used_paths,
                              sound=sound)
    log.info("🤖 search round done\n"
             "queries: %d\n"
             "rows: %d of %d in the pool", len(queries), len(numbers),
             len(candidates))
    _step(on_step, "note", "1 · What the queries found",
          f"{len(queries)} quer{'y' if len(queries) == 1 else 'ies'} → "
          f"{len(numbers)} of {len(candidates)} tracks in the pool.")
    return numbers


def ask_playlist(rules: str, task: str, candidates, *,
                 model: str = CLAUDE_MODEL, config_dir: str = "",
                 timeout: int = 600, dance_class=None, used_paths=(),
                 on_step=None, playlists_of=None,
                 cancel=None) -> tuple[list[dict], str, str]:
    """Ask for a playlist over `candidates`. Returns (picks, notes, backend).

    Two turns: the model searches the pool, then picks out of what came back.
    The numbers in `picks` are positions in `candidates`, not in the subset it
    was shown, so `assemble_grid` resolves them without knowing about the
    search at all.

    Both turns carry what the database knows about the sound of a track (the
    snd digits, see planner.sound) and, if `playlists_of` is given, which of
    the rows on the table have been played in the same events before.

    `on_step(role, title, text)` gets every prompt and every reply as they
    happen, so the window can show the exchange while it runs.
    """
    sound = sound_codes(candidates, dance_of=pool_dance)
    numbers = search_rows(rules, task, candidates, model=model,
                          config_dir=config_dir, timeout=timeout,
                          dance_class=dance_class, used_paths=used_paths,
                          on_step=on_step, sound=sound, cancel=cancel)
    rows = catalog_rows(candidates, numbers, dance_class=dance_class,
                        used_paths=used_paths, sound=sound)
    together = played_together(numbers, candidates, playlists_of)
    if together:
        rows += "\n\n" + together
    system, user = build_prompt(rules, task, rows)
    _step(on_step, "sent", "2 · The tracks it may pick from",
          system + "\n\n" + user)
    raw, backend = _ask(system, user, model=model, config_dir=config_dir,
                        timeout=timeout, on_step=on_step, cancel=cancel)
    _step(on_step, "received", f"2 · Its playlist — {backend}", raw)
    payload = parse_reply(raw)
    # Only the rows it was shown can be picked: any other number is one the
    # model made up, and it would pull a pool track it never saw into the deck.
    offered = set(numbers)
    picks = [p for p in payload["picks"] if p["n"] in offered]
    stray = [p["n"] for p in payload["picks"] if p["n"] not in offered]
    if stray:
        _step(on_step, "note", "Numbers it was never shown",
              "Dropped: " + ", ".join(map(str, stray)))
    if not picks:
        raise RuntimeError("the answer named none of the tracks it was shown")
    log.info("🤖 playlist via %s\n"
             "rows offered: %d\n"
             "picks: %d\n"
             "dropped, not offered: %d",
             backend, len(numbers), len(picks), len(stray))
    return picks, payload["notes"], backend
