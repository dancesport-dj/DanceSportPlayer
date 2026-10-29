"""🥇 The final plays on: after the play length has faded a title of the final
out, it comes back up as background music while the couples celebrate.

Marcel: off, the last dance of the final, or every dance of the final. It only
follows the play-length fade — 🔉↓, 🛑 and ⏹ stay real fades — and only under
✋ Manual: the title plays on until 🔉↓ fades it, the next title starts or its
file ends. Under ⏭ Auto the ⏸ pause and its music follow each title, so it
ends as always.

The settings and the rule live here, without players or widgets, so the
⚙ Settings dialog and the player read one set of defaults.
"""
from planner.playing.play_sets import round_kind

CELEBRATE_MODES = ("off", "last", "all")
CELEBRATE_PCT = 60   # 🥇 how loud it comes back, % of the music's level
CELEBRATE_PCT_MIN = 5
CELEBRATE_DIP_PCT = 5   # 🥇 how low the play-length fade takes it first
CELEBRATE_HOLD_SECS = 2.0   # …how long it stays there
CELEBRATE_UP_SECS = 3.0   # …over how long it comes up
CELEBRATE_DOWN_SECS = 3.0   # …and goes down again at its end
CELEBRATE_MAX_SECS = 10.0


def celebrate_mode(settings: dict) -> str:
    """🥇 "off", "last" (the final's last dance) or "all" (its every dance)."""
    mode = settings.get("celebrate_mode", "off")
    return mode if mode in CELEBRATE_MODES else "off"


def celebrate_pct(settings: dict) -> int:
    """🥇 How loud the title comes back, % of the music's level."""
    try:
        pct = int(settings.get("celebrate_pct", CELEBRATE_PCT))
    except (TypeError, ValueError):
        return CELEBRATE_PCT
    return max(CELEBRATE_PCT_MIN, min(100, pct))


def celebrate_dip_pct(settings: dict) -> int:
    """🥇 How low the play-length fade takes the title before it comes back
    up, % of the music's level: 0 = all the way down. Never above the level
    it comes back at: a dip lies below where it rises to."""
    try:
        dip = int(settings.get("celebrate_dip_pct", CELEBRATE_DIP_PCT))
    except (TypeError, ValueError):
        return CELEBRATE_DIP_PCT
    return max(0, min(celebrate_pct(settings), dip))


def _secs(settings: dict, key: str, default: float) -> float:
    try:
        secs = float(settings.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(0.0, min(CELEBRATE_MAX_SECS, secs))


def celebrate_up_secs(settings: dict) -> float:
    """🥇 How long it comes up; 0 = at once."""
    return _secs(settings, "celebrate_up_secs", CELEBRATE_UP_SECS)


def celebrate_hold_secs(settings: dict) -> float:
    """🥇 How long it stays at its dip before it comes up; 0 = not at all."""
    return _secs(settings, "celebrate_hold_secs", CELEBRATE_HOLD_SECS)


def celebrate_down_secs(settings: dict) -> float:
    """🥇 How long it goes down at its end; 0 = it stops at once."""
    return _secs(settings, "celebrate_down_secs", CELEBRATE_DOWN_SECS)


def celebrates(mode: str, round_name: str, last_of_round: bool) -> bool:
    """Whether a title of round `round_name` plays on after its fade."""
    if mode not in ("last", "all") or round_kind(round_name) != "final":
        return False
    return mode == "all" or last_of_round


def celebrate_level(elapsed: float, up_secs: float, pct: int,
                    dip: int = 0, hold_secs: float = 0.0) -> float:
    """The level (0…1) `elapsed` seconds into the coming up from `dip`,
    which it stays at for the first `hold_secs`."""
    elapsed -= hold_secs
    if elapsed < 0:
        return dip / 100.0
    rise = min(1.0, max(0.0, elapsed / up_secs)) if up_secs > 0 else 1.0
    return (dip + rise * (pct - dip)) / 100.0
