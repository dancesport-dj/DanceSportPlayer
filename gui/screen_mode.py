"""📐 Screen: Auto / Normal / Compact (⚙ Settings → 🎨 Look).

Compact is the shape for a 13″ laptop: the hints fold to one line, an empty
wishlist starts folded, the rows sit tighter. Auto picks it when the screen's
free height is short. Decided when the window is built, and under Auto
again when it moves to a screen of another size (_on_screen_changed).
"""

SCREEN_MODES = ("auto", "normal", "compact")
# (key, caption), shared by ⚙ Look and the first-start question.
SCREEN_MODE_CHOICES = (("auto", "Auto"), ("normal", "Normal"),
                       ("compact", "Compact"))
# 1366×768 and 1280×800 leave about 730-760 px under the taskbar; a 1080p
# screen at 150 % leaves about 680. A 1080p screen at 100 % leaves ~1040.
COMPACT_BELOW = 800

# Set by apply_settings: at window build, and on a screen change under Auto.
_compact = False


def screen_mode_of(settings: dict) -> str:
    """The saved choice, falling back to "auto"."""
    want = (settings or {}).get("screen_mode", "auto")
    return want if isinstance(want, str) and want in SCREEN_MODES else "auto"


def is_compact(settings: dict, free_height: int) -> bool:
    """Whether the window is built compact on a screen with this much
    free height (logical px)."""
    mode = screen_mode_of(settings)
    if mode == "auto":
        return free_height < COMPACT_BELOW
    return mode == "compact"


def apply_settings(settings: dict, free_height: int) -> None:
    """Set the shape for this screen: the window's panels read `compact()`
    when they are built, and again when the window re-shapes them."""
    global _compact
    _compact = is_compact(settings, free_height)


def compact() -> bool:
    return _compact
