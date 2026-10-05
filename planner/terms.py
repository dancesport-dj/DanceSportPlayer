"""Dance and round names as the screen shows them.

The data speaks German. DANCE_NAMES, the tournament rounds (Vorrunde …
Finale) and the Standardrunde / Lateinrunde / Socialrunde sections of a party
list are what the .m3u files carry and what the app reads back, so they stay
German wherever they are stored, exported or announced. Only the screen gets
them through here: in English as English terms, unless ⚙ Settings asks for
the German words ("german_dance_terms"); a German screen keeps them as they
are. That setting also decides the language of what the hall sees and hears
(`hall_language`): the presenter screen and the recorded announcements are
German with it, so German dance names never sit in an English frame.

Not part of `i18n.t()`: those keys are English chrome translated into German,
these are German data translated into English, and a song or round that
happens to be named "Finale" must not be rewritten in every label of the app.
Like the language, the setting is read once at start-up.
"""
import re

from planner import i18n
from planner.models import DANCE_NAMES

DANCE_NAMES_EN = {
    'LW': 'Slow Waltz', 'TG': 'Tango', 'WW': 'Viennese Waltz',
    'SF': 'Slowfox', 'QS': 'Quickstep', 'CC': 'ChaCha',
    'SA': 'Samba', 'RB': 'Rumba', 'PD': 'Paso Doble', 'JI': 'Jive',
    'TANGOARG': 'Argentine Tango',
}

# A dance written short, for where the full name doesn't fit: the code itself,
# except where the operator knows the dance by another abbreviation — Samba is
# SB on the desk and Jive JV, not SA / JI — and the social dances, which have
# no two-letter code of their own. The Σ song-count line has always read this
# way; the Dance column can be switched to it per kind of list, and the player
# card's subtitle uses it. The same in every language.
DANCE_SHORT = {"SA": "SB", "JI": "JV",
               "DISCOFOX": "DF", "SALSA": "SL", "BACHATA": "BC",
               "WCS": "WCS", "KIZOMBA": "KZ", "FORRO": "FR",
               "TANGOARG": "TA"}

# The German genre labels of the non-competition tracks
# (models.OTHER_GENRE_LABELS). They are stored as `other_genre` and matched on
# as they are, so only the screen gets them in English.
_GENRE_EN = {"Einleitung": "Intro", "Einmarsch": "Entrance", "Marsch": "March",
             "Fanfare/Tusch": "Fanfare", "Weihnachten": "Christmas",
             "Sonstiges": "Other"}

_SECTION_EN = {"standard": "Standard round", "latein": "Latin round",
               "social": "Social round"}
# The WDSF words. The rounds count on: the first intermediate round is Round 2.
_ROUND_EN = {"vorrunde": "Round 1", "zwischenrunde": "Round 2",
             "hoffnungsrunde": "Redance",
             "semifinale": "Semi-Final", "halbfinale": "Semi-Final",
             "viertelfinale": "Quarter-Final", "finale": "Final",
             "endrunde": "Final"}
_SECTION_RE = re.compile(r"(?i)^(standard|latein|social)runde(\s+\d+)?$")
_NTH_RE = re.compile(r"(?i)^(\d+)\.\s*zwischenrunde$")
_RUNDE_RE = re.compile(r"(?i)^runde\s+(\d+)$")

# Off until `apply_settings` has run: start-up calls it before the first
# window, and until then the names pass untouched, as the data has them.
_english_terms = False
# Whether ⚙ Settings asked for the German words. Kept apart from the flag
# above, which is also off before the settings are read.
_german_kept = False


def apply_settings(settings: dict) -> None:
    global _english_terms, _german_kept
    _german_kept = bool((settings or {}).get("german_dance_terms"))
    _english_terms = not _german_kept


def hall_language() -> str:
    """The language of the presenter screen and the announcements: German
    when the German dance terms were asked for, the screen's own otherwise."""
    return "de" if _german_kept else i18n.active_language()


def english() -> bool:
    """Whether the screen names dances and rounds in English."""
    return _english_terms and i18n.active_language() == "en"


def dance_name(code, default=None):
    """`DANCE_NAMES.get(code, default)`, in English on an English screen."""
    if english() and code in DANCE_NAMES_EN:
        return DANCE_NAMES_EN[code]
    return DANCE_NAMES.get(code, genre_name(default))


def genre_name(label):
    """A track's genre label (`other_genre`) for the screen: the German ones in
    English on an English screen, anything else untouched."""
    if english() and label in _GENRE_EN:
        return _GENRE_EN[label]
    return label


def round_name(name):
    """A round or section label for the screen. A bare dance code (a running
    order whose rounds could not be derived) is named as its dance; anything
    the app did not name itself passes untouched."""
    if not isinstance(name, str) or not name:
        return name
    if name in DANCE_NAMES:
        return dance_name(name)
    if not english():
        return name
    key = name.strip()
    if m := _SECTION_RE.match(key):
        return _SECTION_EN[m.group(1).lower()] + (m.group(2) or "")
    if m := _NTH_RE.match(key):
        return f"Round {int(m.group(1)) + 1}"
    if m := _RUNDE_RE.match(key):
        return f"Round {m.group(1)}"
    return _ROUND_EN.get(key.lower(), name)
