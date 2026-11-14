"""🎧 Audio output profiles: named sets of the "audio_outputs" setting.

A tournament puts the music on the PA card and pre-listen on the headphones;
preparing the evening puts everything on the headphones. A profile is one such
set under a name. "audio_outputs" stays what the rest of the app reads — it
always mirrors the active profile — so nothing else has to know profiles exist,
and a settings file without profiles behaves exactly as before.

    "audio_profiles": name → {"outputs": {source → choice}, "private": bool}
    "audio_profile":  the active name

Two profiles always exist and cannot be deleted: "Main" (the hall) and
"Rehearsal" (everything on the headphones). Rehearsal is private by
definition, Main never is; further profiles are hall profiles you name
yourself. A private profile is a rehearsal: the hall hears nothing of it. The
active profile is kept across a restart like any setting; entering Playing mode
on a rehearsal one warns (see AudioDevice.rehearsal_profile).

Qt-free: plain functions over the settings dict.
"""
import copy

OUTPUTS_KEY = "audio_outputs"
PROFILES_KEY = "audio_profiles"
ACTIVE_KEY = "audio_profile"

MAIN = "Main"
REHEARSAL = "Rehearsal"
BUILTIN = (MAIN, REHEARSAL)
_CUE = "cue"       # the 🎧 pre-listen source of "audio_outputs"
_MUSIC = "music"


def _stored(settings: dict) -> dict:
    """The well-formed profiles of a settings dict, in stored order. A hand-
    edited file with a profile that is not a dict loses only that profile."""
    raw = settings.get(PROFILES_KEY)
    if not isinstance(raw, dict):
        return {}
    return {name: prof for name, prof in raw.items()
            if isinstance(name, str) and isinstance(prof, dict)}


def is_builtin(name: str | None) -> bool:
    return name in BUILTIN


def profile_names(settings: dict) -> list[str]:
    """The built-ins first, then the profiles you made, in stored order."""
    stored = _stored(settings)
    return ([n for n in BUILTIN if n in stored]
            + [n for n in stored if n not in BUILTIN])


def active_profile(settings: dict) -> str | None:
    """The active profile's name, None when none is active (or it is gone)."""
    name = settings.get(ACTIVE_KEY)
    return name if name in _stored(settings) else None


def is_private(settings: dict, name: str | None = None) -> bool:
    """Whether `name` (default: the active profile) is a rehearsal. Rehearsal
    always is and Main never is, whatever a hand-edited file says."""
    name = name if name is not None else active_profile(settings)
    if name in BUILTIN:
        return name == REHEARSAL
    prof = _stored(settings).get(name)
    return bool(prof) and prof.get("private") is True


def _outputs_of(prof: dict) -> dict:
    outputs = prof.get("outputs")
    return copy.deepcopy(outputs) if isinstance(outputs, dict) else {}


def ensure_builtin(settings: dict) -> bool:
    """Make sure Main and Rehearsal exist; True when something was added (the
    caller then saves). Main starts as the outputs in force, and becomes the
    active profile when none is — unless a private profile of your own is the
    active one: its outputs are the headphones, so Main then starts as the
    first hall profile's (empty when there is none). Rehearsal starts with the
    music, and so every source that follows it, on the pre-listen output —
    empty when there is none, which is the system default until it is saved
    from Settings. A stored active name no profile has (a hand-edited file)
    falls back to Main, and Main's outputs come into force with it, so the
    profile shown is the one that plays. Existing profiles are never touched."""
    stored = _stored(settings)
    outputs = settings.get(OUTPUTS_KEY)
    outputs = outputs if isinstance(outputs, dict) else {}
    added = False
    if MAIN not in stored:
        main_outputs = outputs
        if is_private(settings):
            hall = next((prof for name, prof in stored.items()
                         if not is_private(settings, name)), None)
            main_outputs = _outputs_of(hall) if hall else {}
        stored[MAIN] = {"outputs": copy.deepcopy(main_outputs), "private": False}
        added = True
    if settings.get(ACTIVE_KEY) not in stored:
        settings[ACTIVE_KEY] = MAIN
        settings[OUTPUTS_KEY] = _outputs_of(stored[MAIN])
        added = True
    if REHEARSAL not in stored:
        cue = outputs.get(_CUE)
        stored[REHEARSAL] = {"outputs": ({_MUSIC: copy.deepcopy(cue)}
                                         if isinstance(cue, dict) and cue else {}),
                             "private": True}
        added = True
    if added:
        settings[PROFILES_KEY] = stored
    return added


def save_profile(settings: dict, name: str, outputs: dict, private: bool = False) -> bool:
    """Store a copy of `outputs` as profile `name` (replacing one of that name)
    and make it the active one. False for a blank name. `private` only counts
    for a profile of your own: Rehearsal is always private, Main never."""
    name = (name or "").strip()
    if not name:
        return False
    if name in BUILTIN:
        private = name == REHEARSAL
    stored = _stored(settings)
    stored[name] = {"outputs": copy.deepcopy(outputs), "private": bool(private)}
    settings[PROFILES_KEY] = stored
    settings[ACTIVE_KEY] = name
    settings[OUTPUTS_KEY] = copy.deepcopy(outputs)
    return True


def switch_profile(settings: dict, name: str) -> bool:
    """Make `name` the active profile and put its outputs where the app reads
    them. False, with nothing changed, for a name that does not exist."""
    prof = _stored(settings).get(name)
    if prof is None:
        return False
    settings[ACTIVE_KEY] = name
    settings[OUTPUTS_KEY] = _outputs_of(prof)
    return True


def delete_profile(settings: dict, name: str) -> bool:
    """Drop profile `name`; False when nothing went (no such profile, or one of
    the built-ins). The outputs in force stay as they are; only the link to the
    deleted profile goes."""
    if name in BUILTIN:
        return False
    stored = _stored(settings)
    if stored.pop(name, None) is None:
        return False
    settings[PROFILES_KEY] = stored
    if settings.get(ACTIVE_KEY) == name:
        settings.pop(ACTIVE_KEY, None)
    return True


def clear_active(settings: dict) -> None:
    """Unlink the active profile; every profile and the outputs in force stay."""
    settings.pop(ACTIVE_KEY, None)
