"""Theme-mode definitions for the planner.

Extracted from dancesport_planner.py (logical split): the built-in THEMES table
and the loaders that merge user overrides from themes.json.
"""
import logging

from planner.store import USER_THEMES

log = logging.getLogger("dancesport.themes")


# Built-in themes. A track matches a theme when it satisfies ALL present keys:
#   dances      – allowed dance codes (omit → any competition dance)
#   year_range  – inclusive (lo, hi); tracks without a known year are excluded
#   mood        – 'slow' | 'fast' (uses SLOW_DANCES / FAST_DANCES)
#   min_pop     – minimum popularity (proven-ness)
# A track can also be force-included via themes.json → "track_themes".
THEMES: dict[str, dict] = {
    'Hochzeit':  {'label': 'Hochzeit (Wedding)', 'dances': ['LW', 'WW', 'SF', 'RB', 'CC'],
                  'mood': 'slow', 'min_pop': 1},
    'Party':     {'label': 'Party',              'dances': ['CC', 'SA', 'JI', 'QS', 'TG']},
    'Galaball':  {'label': 'Galaball / Ballnacht', 'min_pop': 1},
    '80er':      {'label': '80er',   'year_range': (1980, 1989)},
    '90er':      {'label': '90er',   'year_range': (1990, 1999)},
    '2000er':    {'label': '2000er', 'year_range': (2000, 2009)},
    '2010er':    {'label': '2010er', 'year_range': (2010, 2019)},
}


def load_user_themes() -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Load custom theme specs and per-track theme overrides from themes.json.

    Expected JSON shape (all keys optional):
      {
        "custom_themes": { "Schlager": {"min_pop": 1, "mood": "slow"} },
        "track_themes":  { "songfilename stem": ["Hochzeit", "90er"] }
      }
    Returns (custom_themes, track_themes) with track stems lower-cased.
    """
    custom: dict[str, dict] = {}
    track:  dict[str, list[str]] = {}
    data = USER_THEMES.read({})
    try:
        # The store answers for the file; this answers for its shape — it is
        # meant to be hand-edited, so anything can be in there.
        custom = data.get('custom_themes', {}) or {}
        for stem, names in (data.get('track_themes', {}) or {}).items():
            track[stem.lower()] = list(names)
    except Exception as exc:
        log.warning("⚠️ Malformed themes file\n"
                    "error: %s\n"
                    "instead: using built-in themes only", exc)
    return custom, track


def all_themes() -> dict[str, dict]:
    """Built-in themes merged with user-defined custom themes (themes.json wins)."""
    custom, _ = load_user_themes()
    merged = dict(THEMES)
    merged.update(custom)
    return merged
