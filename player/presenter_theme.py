"""🎨 The palettes the 🖥 presenter screen can wear.

The screen was built in one look — the iPad app's black hall display — and its
colours sat in module constants. A wedding is not that hall: the same screen
standing next to the cake wants ivory and warm brown, not pure black and SF
orange. So the colours move into a named theme, the screen reads them from
there, and picking another one is a combo on the play panel.

A theme is data, not code: the same nine colours plus the font the hero line is
set in. Adding one is adding an entry to `THEMES`.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("dancesport.gui.presenter")


@dataclass(frozen=True)
class Theme:
    """One presenter palette. Every colour is a CSS colour string."""
    key: str
    label: str          # what the combo shows
    bg: str             # the whole screen
    hero: str           # the running dance, and the queue rows behind the next
    sub: str            # titles, headers, elapsed time
    div: str            # hairlines between queue rows, and the foot hint
    past: str           # the title the evening has already spent
    up: str             # the dance that comes next — the accent
    left: str           # remaining time
    end: str            # …and the colour it blinks in over the last seconds
    track: str          # the progress bar's unfilled track
    fill: str           # …and its fill
    # The face the hero line is set in, best first — an empty tuple keeps the
    # system font. A chain, not one name: a theme may ask for a font that is
    # only installed on the machine it was made for.
    hero_families: tuple = ()
    # Images stacked above the timetable page's heading, top first, each
    # centred: a theme's mark. Paths are relative to the repo root, so they
    # survive being packaged. An empty tuple means the page has no mark.
    logo: tuple = ()


THEMES = {
    # The screen as it was built: the iPad app's "Now dancing" view.
    "default": Theme(
        key="default", label="Default (schwarz)",
        bg="#000000", hero="#ffffff", sub="#8e8e93", div="#3a3a3c",
        past="#6e6e73", up="#ff9f0a", left="#ffffff", end="#ff3b30",
        track="rgba(255,255,255,0.20)", fill="#ffffff"),
    # Light: a wedding's own print style, so the screen in the hall and
    # the menu card on the table are one set. Taken from the shared constants
    # the print pieces are generated from (hochzeit/build/tischplan_layout.py):
    #   GOLD #C9A84C · DARK #555555 · GREY #777777 · LINE #CCCCCC
    #   SOFT #F2F0E6 · PALE #DBDBDB · Cantarell
    # Light on purpose — this screen stands in a lit room, not a dark hall, and
    # black on a beamer in daylight is a grey rectangle anyway. The greys are
    # used as the ramp they already are: DARK reads, GREY is secondary, LINE is
    # what the evening has spent, PALE is the hairlines.
    # The one colour not in that palette is `end`: print has no alarm tone, and
    # gold blinking on gold says nothing, so the last seconds take a muted
    # brick red that sits with the gold instead of the default's SF scarlet.
    # Cantarell ships Regular only (the print scripts fake bold by overprinting)
    # — on screen Qt synthesises the weight, which is what the hero line wants.
    "light": Theme(
        key="light", label="Light (gold)",
        bg="#f2f0e6", hero="#555555", sub="#777777", div="#dbdbdb",
        past="#cccccc", up="#c9a84c", left="#555555", end="#b03a2e",
        track="rgba(85,85,85,0.15)", fill="#c9a84c",
        hero_families=("Cantarell", "Georgia")),
}

# Where a theme's `logo` paths are resolved from — this file's own repo, not the
# working directory, so the screen finds its mark whatever folder it was started
# from (the app icon had exactly this bug once) and after packaging.
ASSET_ROOT = Path(__file__).resolve().parents[1]


def logo_paths(theme: Theme) -> list:
    """The theme's marks as absolute paths, dropping any that isn't on disk —
    a missing image costs the heading its crown, never the screen."""
    out = []
    for rel in theme.logo:
        p = ASSET_ROOT / rel
        if p.is_file():
            out.append(p)
        else:
            log.warning("🎨 Theme mark missing\n"
                        "theme: %s\n"
                        "file: %s", theme.key, p)
    return out

DEFAULT_KEY = "default"


def theme_for(key) -> Theme:
    """The named theme, or the default one for anything unknown — a settings
    file naming a theme that no longer exists must not cost the screen."""
    return THEMES.get(str(key or ""), THEMES[DEFAULT_KEY])


def theme_choices() -> list[tuple[str, str]]:
    """(key, label) per theme, in the order the combo should offer them."""
    return [(t.key, t.label) for t in THEMES.values()]
