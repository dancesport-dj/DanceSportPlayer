"""The play values both sides read: the 🎉 party / 🏆 tournament sets and the
play-length ladder.

No Qt. The ▶ player applies these values and ⚙ Settings edits them, so they
live below both: gui/ never imports player/ (tests/app/test_layering.py).
"""

# 🎉 What a party needs, as opposed to a tournament heat: every title to its
# own end, one after the other, with nothing in between — and all of them at
# the same level, since a party set spans decades of mastering. Nothing spoken:
# without a pause the announcement would land on top of the music. A
# double-click plays at once: someone asks for a song and it runs.
_PARTY_SET = {"secs": 0, "fade": 3.0, "advance": True, "pause_off": True,
              "loudness": True, "announce": False, "dblclick": True}

# 🏆 …and what a competition heat needs: the TSO play length — 1:40, and a
# 3 s ramp (Marcel found 1.5 s too abrupt on the floor) —
# and every title started by the operator: no advancing, no pause running on by
# itself, no voice, and a double-click that only CUES the title — the music
# starts when the couples stand, on ⏯. The Paso Doble highlight stop is
# deliberately NOT part of either set.
_TOURNAMENT_SET = {"secs": 100, "fade": 3.0, "advance": False,
                   "pause_off": True, "loudness": True, "announce": False,
                   "dblclick": False}

# Both sets are only defaults: ⚙ Settings → 🎛 Play sets writes the user's own
# values under these keys, one dict per set.
_SET_KEYS = {"party": ("party_set", _PARTY_SET),
             "tournament": ("tournament_set", _TOURNAMENT_SET)}

# The TSO pitch, per set: on for a heat, where every title of a round is pitched
# to the dance's mean tempo, and off for a party, where the next song is a
# different dance at whatever tempo it was recorded at. Kept out of the dicts
# above because the toggle sits on the player card and not on the panel, so it
# cannot ride along in `apply_play_set` — it IS stored in the same set, though.
_SET_TSO = {"party": False, "tournament": True}


def play_set_of(settings: dict, which: str) -> dict:
    """The configured values of the 🎉 party / 🏆 tournament set.

    Per FIELD fallback, not per dict: a settings file written before a field
    joined the set still yields a complete set instead of an empty one, and a
    hand-edited value of the wrong type cannot break the button.
    """
    key, default = _SET_KEYS[which]
    stored = settings.get(key)
    stored = stored if isinstance(stored, dict) else {}
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
            else:
                out[k] = bool(v)
        except (TypeError, ValueError):
            out[k] = fallback
    return out


# Bumped when a set's default changes in a way a saved set has to follow.
PLAY_SETS_VERSION = 2
_OLD_TOURNAMENT_FADE = 1.5


def migrate_play_sets(s: dict) -> dict:
    """Bring play sets saved under older defaults up to date, in place.

    v2 raised the 🏆 tournament fade-out from 1.5 s to 3 s. ⚙ Settings saves a
    set whole, so a stored 1.5 is the old default as often as a choice — it
    is lifted to 3; any other stored value was chosen and stays. Runs once:
    a 1.5 picked after the update is kept."""
    if int(s.get("play_sets_version") or 1) >= PLAY_SETS_VERSION:
        return s
    stored = s.get("tournament_set")
    if isinstance(stored, dict):
        try:
            if float(stored.get("fade")) == _OLD_TOURNAMENT_FADE:
                stored["fade"] = _TOURNAMENT_SET["fade"]
        except (TypeError, ValueError):
            pass
    s["play_sets_version"] = PLAY_SETS_VERSION
    return s


def tso_of(settings: dict, which: str) -> bool:
    """Where the play set wants the TSO pitch — ⚙ Settings → 🎛 Play sets.

    Read apart from `play_set_of` because the panel's `apply_play_set` has no
    place for it: the toggle lives on the player card.
    """
    stored = settings.get(_SET_KEYS[which][0])
    stored = stored if isinstance(stored, dict) else {}
    return bool(stored.get("tso", _SET_TSO[which]))


# Play-length ladder: 15 s rungs up to 2:30, then 0 = "full" (no cut).
_LEN_STEP = 15
_LEN_MAX = 150
# Typed lengths are NOT held to the ladder — 1:37 is a legitimate answer to
# "how long is this heat". Only the outer bounds still apply: below 5 s the
# fade-out would be longer than the song, and past 20 min no title survives
# anyway, so anything longer is what "full" is for.
_LEN_TYPED_MIN = 5
_LEN_TYPED_MAX = 20 * 60


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
    return max(_LEN_TYPED_MIN, min(_LEN_TYPED_MAX, total))
