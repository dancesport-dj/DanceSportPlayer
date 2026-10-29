"""The play values both sides read: the 🎉 party / 🏆 tournament sets and the
play-length ladder.

No Qt. The ▶ player applies these values and ⚙ Settings edits them, so they
live below both: gui/ never imports player/ (tests/app/test_layering.py).
"""
import contextlib

# 🎉 What a party needs, as opposed to a tournament heat: every title to its
# own end, one after the other, with nothing in between — and all of them at
# the same level, since a party set spans decades of mastering. Nothing spoken:
# without a pause the announcement would land on top of the music. A
# double-click plays at once: someone asks for a song and it runs. The 🔀
# crossfade stands ready at 4 s, the length UltraMixer starts on, but is off:
# Marcel's party runs title after title, each faded within its length.
# `fade_inside`: the fade-out ends AT the play length (1:45 is silent at 1:45);
# off, the title plays its full length and fades after it.
PARTY_SET = {"secs": 0, "fade": 3.0, "fade_inside": True, "advance": True,
              "pause_off": True,
              "loudness": True, "announce": False, "dblclick": True,
              "xfade": 4.0, "xfade_on": False, "xfade_curve": "equal"}

# 🔀 The crossfade has a switch of its own, and its seconds stay where they are
# while it is off — so switching it on comes up on a length worth hearing, not
# on the 0.5 s a spin box above an "off" would step to. 4 s is that length.
XFADE_DEFAULT_SECS = 4.0
XFADE_MIN_SECS = 0.5
XFADE_MAX_SECS = 10.0
# The shapes a crossfade can take, by the name a set stores
# (shared.audio.playback.crossfade_levels draws and ramps them). Equal power first:
# two unrelated songs add in power, so it is the one without a dip.
XFADE_CURVES = ("equal", "linear", "scurve")

# 🏆 …and what a competition heat needs: the TSO play length — 1:45, and a
# 3 s ramp AFTER it (Marcel found 1.5 s too abrupt on the floor; the full
# length is danced, then faded) —
# and every title started by the operator: no advancing, no pause running on by
# itself, no voice, and a double-click that only CUES the title — the music
# starts when the couples stand, on ⏯. The Paso Doble has values of its own
# in this set, see `_TOURNAMENT_PD`.
TOURNAMENT_SET = {"secs": 105, "fade": 3, "fade_inside": False,
                   "advance": False,
                   "pause_off": True, "loudness": True, "announce": False,
                   "dblclick": False, "xfade": XFADE_DEFAULT_SECS,
                   "xfade_on": False, "xfade_curve": "equal"}

# Both sets are only defaults: ⚙ Settings → 🎛 Play sets writes the user's own
# values under these keys, one dict per set.
_SET_KEYS = {"party": ("party_set", PARTY_SET),
             "tournament": ("tournament_set", TOURNAMENT_SET)}
# …and the 🏆 set's per-dance lengths, see `dance_secs_of`. Shipped as Marcel
# plays a heat: 1:30 for the Waltzes, the Quickstep and the Jive, 1:37 for the
# rest. The Paso Doble plays in full (0) — Marcel: "default tournent set for
# paso is full"; the set's 1:45 would cut it before its music ends.
DANCE_SECS_KEY = "tournament_dance_secs"
_DANCE_SECS = {"LW": 90, "TG": 97, "WW": 90, "SF": 97, "QS": 90,
               "SA": 97, "CC": 97, "RB": 97, "PD": 0, "JI": 90}
# …and, on top of those, a dance's length in one kind of round — a final
# Waltz at 2:00 where the Vorrunde ran 1:30. Marcel: equal per dance within
# a round, may change between rounds, "but must not": so nothing is shipped,
# and a (round, dance) without one runs on the dance's length. See
# `round_dance_secs_of` and `round_kind`.
ROUND_DANCE_SECS_KEY = "tournament_round_dance_secs"
ROUND_KINDS = ("first", "inter", "semi", "final")
# …and the Paso Doble's pick per kind of round: 0 = full, 1 or 2 = after that
# highlight. Marcel: "highlight3 = full for finals and 2 vor vorrunde" — a 3rd
# highlight is the music's end, so it is no pick of its own. See
# `round_pd_n_of`.
ROUND_PD_KEY = "tournament_round_pd_n"
ROUND_PD_PICKS = (0, 1, 2)

# The TSO pitch, per set: on for a heat, where every title of a round is pitched
# to the dance's mean tempo, and off for a party, where the next song is a
# different dance at whatever tempo it was recorded at. Kept out of the dicts
# above because the toggle sits on the player card and not on the panel, so it
# cannot ride along in `apply_play_set` — it IS stored in the same set, though.
_SET_TSO = {"party": False, "tournament": True}

# ❓ …and whether a double-click on another title asks before it stops the one
# playing: on in both, a stray click cuts the floor at a party as at a heat.
# Kept out of the dicts above like the TSO pitch: Marcel wants no switch for it
# on the panel, so `apply_play_set` has no place for it. Stored in the same set.
_SET_ASK = {"party": True, "tournament": True}

# 🐂 …and the Paso Doble of a heat: no stop at the highlight — Marcel: "it can
# be buggy", and a heat stopped in the wrong bar is danced twice — after the
# 2nd once switched on, and no 'Start after' wait, the chairman's call being
# the wait. Kept out of `_TOURNAMENT_SET` like the TSO pitch, for the same
# reason: `apply_play_set` has no place for them, the panel's 🐂 row owns
# them. Stored in the same set.
TOURNAMENT_PD = {"pd_stop": False, "pd_n": 2, "pd_delay": 0}
# 🎉 …and the Paso Doble of a party: Marcel: "there we normally only want
# playing paso till second highlight and wait 3 seconds before starting" —
# the couples take their position. Later: "set start after default to 1s".
PARTY_PD = {"pd_stop": True, "pd_n": 2, "pd_delay": 1}
_SET_PD = {"party": PARTY_PD, "tournament": TOURNAMENT_PD}
# The ranges of the panel's own spin boxes (player.widgets.play_mode_setup).
_PD_RANGES = {"pd_n": (1, 3), "pd_delay": (0, 60)}


def play_set_of(settings: dict, which: str) -> dict:
    """The configured values of the 🎉 party / 🏆 tournament set.

    Per FIELD fallback, not per dict: a settings file written before a field
    joined the set still yields a complete set instead of an empty one, and a
    hand-edited value of the wrong type cannot break the button.
    """
    key, default = _SET_KEYS[which]
    stored = settings.get(key)
    stored = upgrade_xfade(stored) if isinstance(stored, dict) else {}
    out = dict(default)
    for k, fallback in default.items():
        v = stored.get(k, fallback)
        try:
            if k == "secs":
                out[k] = int(v)
            elif k == "fade":
                # Clamped to the spin box's own range: a hand-edited 99 would
                # otherwise ramp a whole heat down to nothing.
                out[k] = max(0.0, min(10.0, float(v)))
            elif k == "xfade":
                out[k] = max(XFADE_MIN_SECS, min(XFADE_MAX_SECS, float(v)))
            elif k == "xfade_curve":
                out[k] = v if v in XFADE_CURVES else fallback
            else:
                out[k] = bool(v)
        except (TypeError, ValueError):
            out[k] = fallback
    return out


def upgrade_xfade(vals: dict) -> dict:
    """🔀 Play values saved before the crossfade had its own switch, brought
    onto it — a copy, the argument is left alone.

    Back then 0 s WAS off: such a value becomes the switch off over the
    default length, any other one the switch on over that length. Values that
    already carry the switch, or no crossfade at all, come back unchanged."""
    if "xfade" not in vals or "xfade_on" in vals:
        return dict(vals)
    out = dict(vals)
    try:
        secs = float(vals["xfade"] or 0)
    except (TypeError, ValueError):
        secs = 0.0
    out["xfade_on"] = secs > 0
    if secs <= 0:
        out["xfade"] = XFADE_DEFAULT_SECS
    return out


def same_play_values(a: dict, b: dict) -> bool:
    """Whether two sets of play values play the same. The crossfade's seconds
    and curve do not count while its switch is off — nothing of them is heard."""
    def heard(vals: dict) -> dict:
        vals = dict(vals)
        if not vals.get("xfade_on", False):
            vals.pop("xfade", None)
            vals.pop("xfade_curve", None)
        return vals
    return heard(a) == heard(b)


def crossfade_curve(vals: dict) -> str:
    """🔀 The shape of the crossfade of these play values — equal power where
    they were saved before there was a choice."""
    curve = vals.get("xfade_curve")
    return curve if curve in XFADE_CURVES else XFADE_CURVES[0]


def crossfade_secs(vals: dict) -> float:
    """🔀 How long the crossfade of these play values is, 0 = none: switched
    off, or values from before the crossfade that do not have one."""
    if not vals.get("xfade_on", False):
        return 0.0
    try:
        return max(0.0, min(XFADE_MAX_SECS, float(vals.get("xfade", 0) or 0)))
    except (TypeError, ValueError):
        return 0.0


# Bumped when a set's default changes in a way a saved set has to follow.
PLAY_SETS_VERSION = 3
_OLD_TOURNAMENT_FADE = 1.5
_OLD_TOURNAMENT_SECS = 100


def migrate_play_sets(s: dict) -> dict:
    """Bring play sets saved under older defaults up to date, in place.

    v2 raised the 🏆 tournament fade-out from 1.5 s to 3 s, v3 its play
    length from 1:40 to 1:45. ⚙ Settings saves a set whole, so a stored old
    default is that default as often as a choice — it is lifted; any other
    stored value was chosen and stays. Runs once: an old value picked after
    the update is kept."""
    version = int(s.get("play_sets_version") or 1)
    if version >= PLAY_SETS_VERSION:
        return s
    stored = s.get("tournament_set")
    if isinstance(stored, dict):
        for since, key, old in ((2, "fade", _OLD_TOURNAMENT_FADE),
                                (3, "secs", _OLD_TOURNAMENT_SECS)):
            with contextlib.suppress(TypeError, ValueError):
                if version < since and float(stored.get(key, 0)) == old:
                    stored[key] = TOURNAMENT_SET[key]
    s["play_sets_version"] = PLAY_SETS_VERSION
    return s


def dance_secs_of(settings: dict) -> dict[str, int]:
    """🏆 The tournament set's own play length per dance — a Viennese Waltz
    cut at 1:30, a Waltz at 1:37 — keyed by dance code, 0 = full.

    A dance not in it runs on the set's one length. Kept beside the set's dict,
    not in it: `apply_play_set` takes that dict as keywords, and a list's own
    values never carry these — they only count while a list stands on the set.
    A hand-edited entry that is not a length is dropped, not guessed at.
    Nothing stored (or no list at all) is the shipped lengths; a list emptied
    in ⚙ Settings stays empty."""
    stored = settings.get(DANCE_SECS_KEY)
    if not isinstance(stored, dict):
        return dict(_DANCE_SECS)
    out: dict[str, int] = {}
    for dance, v in stored.items():
        try:
            secs = int(v)
        except (TypeError, ValueError):
            continue
        out[str(dance)] = (0 if secs <= 0
                           else max(LEN_TYPED_MIN, min(LEN_TYPED_MAX, secs)))
    return out


def round_kind(name: str) -> str | None:
    """Which of `ROUND_KINDS` the round `name` is, or None for a round that
    is no tournament round (a party list's 'Standardrunde 1', a dance code).
    Every Zwischenrunde is one kind: the per-round lengths are a column per
    kind, not per numbered round. A day plan's stacked deck names its rounds
    '<competition> — <round>' (planner.models._DAY_COMP_SEP): only the part
    after the dash is the round."""
    low = (name or "").rsplit(" — ", 1)[-1].strip().lower()
    if "semi" in low or "halbfinal" in low:
        return "semi"
    if "zwischenrunde" in low or "viertelfinal" in low:
        return "inter"
    if low in ("finale", "final", "endrunde"):
        return "final"
    if low == "vorrunde":
        return "first"
    return None


def round_dance_secs_of(settings: dict) -> dict[str, dict[str, int]]:
    """🏆 The per-round overrides of `dance_secs_of`: round kind → dance code
    → seconds, 0 = full. Read like `dance_secs_of`: an entry that is not a
    length, or a round that is not one of `ROUND_KINDS`, is dropped; nothing
    stored is no override at all."""
    stored = settings.get(ROUND_DANCE_SECS_KEY)
    if not isinstance(stored, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for kind in ROUND_KINDS:
        # Only a dict: dance_secs_of reads anything else as the shipped lengths.
        if isinstance(stored.get(kind), dict):
            lens = dance_secs_of({DANCE_SECS_KEY: stored[kind]})
            if lens:
                out[kind] = lens
    return out


def round_pd_n_of(settings: dict) -> dict[str, int]:
    """🐂 The Paso Doble's pick per kind of round: round kind → 0 (full) or
    the highlight it stops after. Anything else stored is dropped; a round
    without a pick follows the 🏆 set's highlight stop."""
    stored = settings.get(ROUND_PD_KEY)
    if not isinstance(stored, dict):
        return {}
    out: dict[str, int] = {}
    for kind in ROUND_KINDS:
        try:
            n = int(stored[kind])
        except (KeyError, TypeError, ValueError):
            continue
        if n in ROUND_PD_PICKS:
            out[kind] = n
    return out


def tso_of(settings: dict, which: str) -> bool:
    """Where the play set wants the TSO pitch — ⚙ Settings → 🎛 Play sets.

    Read apart from `play_set_of` because the panel's `apply_play_set` has no
    place for it: the toggle lives on the player card.
    """
    stored = settings.get(_SET_KEYS[which][0])
    stored = stored if isinstance(stored, dict) else {}
    return bool(stored.get("tso", _SET_TSO[which]))


def dblclick_ask_of(settings: dict, which: str) -> bool:
    """❓ Whether the set asks before a double-click stops the playing title —
    ⚙ Settings → 🎛 Play sets. Read apart from `play_set_of`, like `tso_of`."""
    stored = settings.get(_SET_KEYS[which][0])
    stored = stored if isinstance(stored, dict) else {}
    return bool(stored.get("dblclick_ask", _SET_ASK[which]))


def pd_of(settings: dict, which: str = "tournament") -> dict:
    """🐂 The 🏆 tournament / 🎉 party set's Paso Doble: `pd_stop` at a
    highlight, after the `pd_n`th, and `pd_delay` seconds of 'Start after' —
    ⚙ Settings → 🎛 Play sets. Per field, like `play_set_of`: a value of the
    wrong type falls back to the default, one out of range is pulled into the
    panel's."""
    stored = settings.get(_SET_KEYS[which][0])
    stored = stored if isinstance(stored, dict) else {}
    out = dict(_SET_PD[which])
    out["pd_stop"] = bool(stored.get("pd_stop", out["pd_stop"]))
    for k, (lo, hi) in _PD_RANGES.items():
        with contextlib.suppress(TypeError, ValueError):
            out[k] = max(lo, min(hi, int(stored.get(k, out[k]))))
    return out


# Play-length ladder: 15 s rungs up to 2:30, then 0 = "full" (no cut).
LEN_STEP = 15
LEN_MAX = 150
# Typed lengths are NOT held to the ladder — 1:37 is a legitimate answer to
# "how long is this heat". Only the outer bounds still apply: below 5 s the
# fade-out would be longer than the song, and past 20 min no title survives
# anyway, so anything longer is what "full" is for.
LEN_TYPED_MIN = 5
LEN_TYPED_MAX = 20 * 60


def parse_play_length(text: str) -> int | None:
    """Seconds out of a typed play length, or None if it is not one.

    Takes "1:37", "97", "2:00" and — because that is what the label itself
    shows in the off position — "full" (German: "komplett"), which is 0.
    Returns None rather than guessing at anything else, so a slip leaves the
    length untouched."""
    text = (text or "").strip().lower()
    if not text:
        return None
    if text in ("full", "komplett", "voll", "0"):
        return 0
    if ":" in text:
        mins, _, secs = text.partition(":")
        if not mins.strip().isdigit() or not secs.strip().isdigit():
            return None
        total = int(mins) * 60 + int(secs)
    elif text.isdigit():
        total = int(text)
    else:
        return None
    return max(LEN_TYPED_MIN, min(LEN_TYPED_MAX, total))
