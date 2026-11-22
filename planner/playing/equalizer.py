"""🎚 The equalizer settings: one room EQ per output source.

Kept under the settings key "equalizer", one entry per source named as in
"audio_outputs" (music, announcer, cue) plus the operator's own presets:

    {"music": {"on": True, "bypass": False, "advanced": False,
               "preset": "boomy_hall",
               "bands": [{"kind": "lowcut", "freq": 30, "gain": 0, "q": 0.707, "on": True},
                         ...five in all...]},
     "announcer": {...}, "cue": {...},
     "presets": {"My hall": [-2.0, -3.0, 1.0, 0.0]}}

The EQ corrects a room and its speakers, not a title, so it belongs to the
venue: it is not a machine key and travels in the 🧳 venue pack. The filter
itself is player.audio.eq; nothing here needs numpy or Qt.

Five bands, always in this order: a low cut, a low shelf, a low-mid peak, a
presence peak, a high shelf. Without "advanced" only the gains and the low
cut (on/off and its cut-off, LOW_CUT_CHOICES) are the operator's; the other
frequencies and every width stay at the defaults.
"""
import math

SOURCES = ("music", "announcer", "cue")
MAX_GAIN_DB = 12.0
_BUTTERWORTH_Q = round(1 / math.sqrt(2), 3)

# (kind, freq Hz, q, on) per band and source; every gain starts at 0 (flat).
_DEFAULT_BANDS = {
    "music": (("lowcut", 30, _BUTTERWORTH_Q, True), ("lowshelf", 100, 0.707, True),
              ("peak", 250, 1.0, True), ("peak", 2500, 1.0, True),
              ("highshelf", 10000, 0.707, True)),
    # The announcement clips already carry a baked speech EQ (tools/audio/
    # announce_eq.py): this only adapts them to the room. No low shelf for a voice.
    "announcer": (("lowcut", 100, _BUTTERWORTH_Q, True), ("lowshelf", 100, 0.707, False),
                  ("peak", 250, 1.0, True), ("peak", 3000, 1.0, True),
                  ("highshelf", 8000, 0.707, True)),
    "cue": (("lowcut", 30, _BUTTERWORTH_Q, True), ("lowshelf", 100, 0.707, True),
            ("peak", 250, 1.0, True), ("peak", 2500, 1.0, True),
            ("highshelf", 10000, 0.707, True)),
}

# The cut-offs the low cut offers without "Advanced", in Hz.
LOW_CUT_CHOICES = (30, 60, 80, 100, 150)

# Built-in presets: the gains of the four bands after the low cut, in dB.
PRESETS = {
    "flat": (0.0, 0.0, 0.0, 0.0),
    "boomy_hall": (-3.0, -3.0, 1.0, 1.0),
    "small_room": (-2.0, -1.0, 0.0, 1.0),
    "weak_speakers": (3.0, 0.0, 1.0, 2.0),
    "speech_clarity": (0.0, -3.0, 3.0, 1.0),
}
# What the EQ card and ⚙ Settings call them (run through i18n there).
PRESET_CAPTIONS = {
    "flat": "Flat",
    "boomy_hall": "Boomy hall",
    "small_room": "Small room",
    "weak_speakers": "Weak speakers",
    "speech_clarity": "Speech clarity",
}
# The key that says the operator has accepted the app making the music's
# tempo itself while its EQ is on (shared.audio.eq_question, "Don't ask again").
PITCH_OK_KEY = "eq_pitch_ok"


def _num(value, default: float, lo: float, hi: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return default if not math.isfinite(x) else max(lo, min(hi, x))


def default_eq(source: str) -> dict:
    """A source's EQ as it starts: off, flat."""
    return {"on": False, "bypass": False, "advanced": False, "preset": "flat",
            "bands": [{"kind": kind, "freq": float(freq), "gain": 0.0, "q": q, "on": on}
                      for kind, freq, q, on in _DEFAULT_BANDS[source]]}


def eq_of(settings: dict, source: str) -> dict:
    """`source`'s EQ from the settings, every field there and in range. A band
    list of the wrong length or a band of the wrong kind falls back to the
    defaults; without "advanced" the frequencies (but the low cut's) and the
    widths are the defaults."""
    out = default_eq(source)
    root = settings.get("equalizer")
    stored = root.get(source) if isinstance(root, dict) else None
    if not isinstance(stored, dict):
        return out
    for key in ("on", "bypass", "advanced"):
        out[key] = stored.get(key) is True
    preset = stored.get("preset")
    out["preset"] = preset if isinstance(preset, str) and preset else ""
    bands = stored.get("bands")
    if not isinstance(bands, list) or len(bands) != len(out["bands"]):
        return out
    for band, saved in zip(out["bands"], bands, strict=True):
        if not isinstance(saved, dict) or saved.get("kind") != band["kind"]:
            continue
        band["gain"] = _num(saved.get("gain"), 0.0, -MAX_GAIN_DB, MAX_GAIN_DB)
        # The low cut's switch and cut-off are picked without "Advanced".
        if band["kind"] == "lowcut" or out["advanced"]:
            band["on"] = saved.get("on", band["on"]) is True
            band["freq"] = _num(saved.get("freq"), band["freq"], 20.0, 20000.0)
        if out["advanced"]:
            band["q"] = _num(saved.get("q"), band["q"], 0.3, 6.0)
    return out


def with_eq(settings: dict, source: str, cfg: dict) -> dict:
    """The settings with `source`'s EQ replaced: a new dict, the rest of
    "equalizer" (the other sources, the presets) kept."""
    root = settings.get("equalizer")
    root = dict(root) if isinstance(root, dict) else {}
    root[source] = cfg
    return {**settings, "equalizer": root}


def user_presets(settings: dict) -> dict[str, tuple]:
    """The operator's own presets: name → four gains."""
    root = settings.get("equalizer")
    stored = root.get("presets") if isinstance(root, dict) else None
    out = {}
    for name, gains in (stored or {}).items() if isinstance(stored, dict) else ():
        if isinstance(name, str) and name and isinstance(gains, list) and len(gains) == 4:
            out[name] = tuple(_num(g, 0.0, -MAX_GAIN_DB, MAX_GAIN_DB) for g in gains)
    return out


def with_user_preset(settings: dict, name: str, gains) -> dict:
    """The settings with the operator's preset `name` saved (None = deleted)."""
    root = settings.get("equalizer")
    root = dict(root) if isinstance(root, dict) else {}
    presets = {k: list(v) for k, v in user_presets(settings).items()}
    if gains is None:
        presets.pop(name, None)
    else:
        presets[name] = [float(g) for g in gains]
    root["presets"] = presets
    return {**settings, "equalizer": root}


def apply_preset(cfg: dict, name: str, settings: dict) -> dict:
    """`cfg` with the gains of preset `name` (built-in or the operator's).
    The low cut and the frequencies stay; an unknown name changes nothing."""
    gains = PRESETS.get(name) or user_presets(settings).get(name)
    if gains is None:
        return cfg
    out = {**cfg, "preset": name, "bands": [dict(b) for b in cfg["bands"]]}
    for band, gain in zip(out["bands"][1:], gains, strict=True):
        band["gain"] = float(gain)
    return out


def tapped(cfg: dict) -> bool:
    """Whether the source's audio has to run through the EQ path at all. Also
    while bypassed: Bypass is an A/B compare inside that path, seamless; only
    "off" hands the player back to Qt's own output (and its pitch-kept tempo)."""
    return cfg.get("on") is True


def audible_bands(cfg: dict) -> list[tuple]:
    """(kind, freq, gain, q, on) per band as the filter takes them; none while
    bypassed or off, so the filter passes the sound through."""
    if not tapped(cfg) or cfg.get("bypass"):
        return []
    return [(b["kind"], b["freq"], b["gain"], b["q"], b["on"]) for b in cfg["bands"]]
