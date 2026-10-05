"""Light / dark theming and the accent colour, derived from the app's own colours.

The app was written light: 157 different colours live in inline stylesheets and
QColor constants spread over gui/ and player/, and 90 of them appear exactly
once. Hand-authoring a dark twin for each would be a large diff AND a design
job, and the meaning already sits in the light value — amber is popularity, red
is a warning, the blue-gray band is a round header.

So the dark theme is not a second palette. It is a transform of the light one,
and the role of a colour decides what happens to it:

* a `color:` value is INK. Its lightness is flipped into the light half and then
  raised until it really clears `_AA_TARGET` against `_INK_REF` — the lightest
  ground any dark pane is allowed to have. Measured, not assumed.
* a `background:` value is GROUND. It flips into the dark half, capped at
  `_GROUND_CAP`, which is exactly `_INK_REF`'s lightness.
* a `border:` value is a LINE and flips like a ground.

Those two rules give an invariant worth having: no ground is lighter than the
ground every ink was tested against, so every ink clears AA on every ground.
`tests/gui/test_theme.py` asserts it over the pairs the app really uses.

Hue and chroma survive the flip (Oklab, so "same hue, other lightness" means
what it says), which is why a themed warning stays recognisably red.

Two further properties make the transform safe to apply blindly:

* **Light mode is the identity.** Nothing is rewritten unless the theme is dark
  or the accent has been changed, so the default look is bit-for-bit today's.
* **It leaves what is already right alone.** The ▶ player panel is dark already;
  its colours pass the guards untouched instead of being flipped into mush.

Because of that, the whole app is themed from one hook on `setStyleSheet`
(`install_stylesheet_hook`) rather than by editing every call site.
"""
import logging
import math
import re

from PySide6.QtGui import QColor, QPalette

log = logging.getLogger("dancesport.gui.theme")

# The blue the app is built around, and the family of tints derived from it.
# Only these are re-hued when the user picks another accent — a red warning or a
# green "proven" mark carries meaning and must stay the colour it is.
ACCENT_DEFAULT = "#1565c0"
_ACCENT_FAMILY = (
    "#1565c0",  # the accent itself
    "#4a82d2",  # slider groove fill
    "#3a4a68",  # hovered dark button
    "#2a3346",  # dark button ground
    "#d6e6fa",  # hover tint on light
    "#e3ecfb",  # selected row
    "#dbe6f4",  # header band
    "#b9d4f2",  # focus ring
    "#1d4f86",  # pressed
    "#2c3e60",  # card title ink
    "#cfe0f5",  # ink on the dark player
    "#eef3fb",  # brightest ink on dark
    # The ▶ player panel is built out of the accent too — it is the one place
    # where the blue is the whole surface and not a highlight on it.
    "#1d2330",  # the panel itself
    "#10141d",  # its border
    "#8fa3c4",  # dim text and the fader's marks
    "#6e87ad",  # dimmer still: the next-up line, the clock
    "#9aa6c0",  # a drop zone's dashed edge
    "#dde4f0",  # the overlay's hovered button
    "#f3f6fc",  # the light card the overlay is
    # The window furniture in `app_palette`. Near-twins of the tints above but
    # not equal to them (#4682d2 is not #4a82d2), so they have to be named or a
    # picked accent leaves every selected row sitting in the old blue.
    "#4682d2",  # QPalette.Highlight — the selection band
    "#1e64c8",  # QPalette.Link
)

# The list above cannot be the whole answer. There are 64 colours at the
# accent's hue spread over gui/ and player/ — the takt meter's scale, the
# cartwall, the tournament tree, the deck headers — and a picked accent that
# recolours some of them and leaves the rest blue looks broken rather than
# restrained. So membership is also a rule: at the accent's hue, and blue
# enough that it reads as blue.
#
# The chroma floor is what keeps the app's greys grey. A near-neutral like
# icons' #33383f sits at the accent's hue too, by a hair, and driving it to the
# picked colour would tint the body text. Below the floor the recolour would be
# invisible anyway, so only the curated list applies there — that is exactly
# what it is for.
_ACCENT_HUE_WINDOW = 30.0   # degrees either side, in Oklab
_ACCENT_MIN_CHROMA = 0.045  # below this a colour is a grey with a hint of blue

# ── Transform tuning ─────────────────────────────────────────────────────────
# Oklab lightness, 0 = black, 1 = white.
_FLOOR = 0.20           # darkest ground: white lands here (~#161616)
_CEIL = 0.94            # lightest ink
_GROUND_SPREAD = 1.55   # grounds bunch up near white; fan them back apart
_GROUND_CAP = 0.34      # no dark pane DERIVED from a light one may be lighter
_ALREADY_DARK = 0.45    # ...but a colour this dark was already a dark pane
_CHROMA = 0.92          # saturated colours read hotter on dark; pull back a bit
_AA_TARGET = 4.6        # WCAG AA for body text is 4.5; keep rounding room
# ...and a colour this saturated behind something is a FILL, not a pane: a
# filled slider, the selection band, a badge. Measured on the app's own colours,
# the two kinds do not overlap — the most coloured real pane is the round
# header's #c8d2f0 at chroma 0.043, the least coloured real fill the desk
# toggle's #5f9e72 at 0.093.
_FILL_CHROMA = 0.07

# A colour capped at exactly `_GROUND_CAP` comes back out of 8-bit sRGB at an
# Oklab lightness a ten-thousandth ABOVE it. Idempotence no longer rests on
# this — `_ALREADY_DARK` catches such a colour far earlier — but a test
# asserting that derived grounds land at or below the cap still needs the
# rounding slack, and that is all this is now.
_GROUND_EPS = 0.005

_THEMES = ("light", "dark")

_active_theme = "light"
_active_accent = ACCENT_DEFAULT


# ── sRGB ↔ Oklab ─────────────────────────────────────────────────────────────

def _srgb_to_linear(value: float) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> int:
    c = 12.92 * value if value <= 0.0031308 else 1.055 * (value ** (1 / 2.4)) - 0.055
    return max(0, min(255, round(c * 255)))


def hex_to_rgb(text: str) -> tuple[int, int, int]:
    h = text.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(v) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def from_oklab(lab: tuple[float, float, float]) -> tuple[int, int, int]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(v) for v in (r, g, bb))


def _with_lightness(lab: tuple[float, float, float], L: float) -> str:
    return rgb_to_hex(from_oklab((L, lab[1], lab[2])))


def contrast_ratio(one: str, two: str) -> float:
    """WCAG relative-luminance contrast between two hex colours (1.0 … 21.0)."""
    def lum(text):
        r, g, b = (_srgb_to_linear(v) for v in hex_to_rgb(text))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = lum(one), lum(two)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# The neutral sitting exactly at the ground cap: the lightest pane a dark theme
# builds, and therefore the ground every ink has to prove itself against.
_INK_REF = _with_lightness((0.0, 0.0, 0.0), _GROUND_CAP)


def ink_reference() -> str:
    """The ground dark-mode inks are guaranteed readable on (for the tests)."""
    return _INK_REF


def ground_cap() -> float:
    return _GROUND_CAP


def ground_tolerance() -> float:
    """How far past the cap 8-bit rounding may land a ground (for the tests)."""
    return _GROUND_EPS


# ── The transform ────────────────────────────────────────────────────────────

def _role_of(prop: str) -> str:
    """Which role a CSS property gives its colour.

    The property name is the role, so nothing has to be guessed: `color:#aaa` is
    faint TEXT and must stay readable, while the same `#aaa` behind `border:`
    is a hairline and may go dark. Inferring the role from the colour itself got
    exactly these two cases wrong."""
    p = prop.lower()
    if "background" in p:
        return "ground"
    if "border" in p or "gridline" in p or "outline" in p:
        return "line"
    return "ink"


def shade(color: str, role: str = "ink") -> str:
    """One light colour → its colour in the active theme."""
    out = _reaccent(color)
    if _active_theme != "dark":
        return out
    return _darkify(out, role)


def _darkify(color: str, role: str) -> str:
    L, a, b = to_oklab(hex_to_rgb(color))
    lab = (0.0, a * _CHROMA, b * _CHROMA)
    if role in ("ground", "line"):
        if math.hypot(a, b) >= _FILL_CHROMA:
            # Not a pane at all — a FILL. A colour this saturated behind
            # something is a figure on the page (a filled slider, the selection
            # band, an active header), and the rule below is written for the
            # pale pane a figure sits ON. Deriving it down turned the ▶
            # player's volume bar into #003281, 1.33:1 against the card it sits
            # on, where the light theme had 2.74:1. It keeps the lightness it
            # was designed with, which is also what keeps its white text
            # readable — brightening it further would cost that.
            return color
        if L <= _ALREADY_DARK:
            # Already a dark pane — leave it EXACTLY. The cap below is a target
            # for grounds being derived from light ones, not a ceiling every
            # dark surface must be squeezed under: the ▶ player's hovered
            # button sits at L 0.41, and pulling it down to the cap left it a
            # fifth of a step from the button underneath it, killing the hover.
            return color
        return _with_lightness(lab, min(_GROUND_CAP, _FLOOR + _GROUND_SPREAD * (1.0 - L)))
    if contrast_ratio(color, _INK_REF) >= _AA_TARGET:
        return color                # already bright enough for a dark pane
    base = _FLOOR + (_CEIL - _FLOOR) * (1.0 - L)
    out = _with_lightness(lab, base)
    if contrast_ratio(out, _INK_REF) >= _AA_TARGET:
        return out
    lo, hi = base, 1.0              # lift until the contrast is really there
    for _ in range(26):
        mid = (lo + hi) / 2
        if contrast_ratio(_with_lightness(lab, mid), _INK_REF) >= _AA_TARGET:
            hi = mid
        else:
            lo = mid
    return _with_lightness(lab, hi)


def in_accent_family(color: str) -> bool:
    """Whether a colour is the accent's rather than its own.

    Named on the list, or close enough to the accent's hue and blue enough to
    read as blue. Anything else — a red warning, a green proven mark, the
    popularity amber, and every grey in the app — keeps the colour it has,
    because for those the colour IS the meaning."""
    if color.lower() in _ACCENT_FAMILY:
        return True
    _, a, b = to_oklab(hex_to_rgb(color))
    chroma = (a ** 2 + b ** 2) ** 0.5
    if chroma < _ACCENT_MIN_CHROMA:
        return False
    _, base_a, base_b = to_oklab(hex_to_rgb(ACCENT_DEFAULT))
    hue = math.degrees(math.atan2(b, a))
    base_hue = math.degrees(math.atan2(base_b, base_a))
    delta = abs(hue - base_hue) % 360
    return min(delta, 360 - delta) <= _ACCENT_HUE_WINDOW


def _reaccent(color: str) -> str:
    """Swing an accent-family colour onto the chosen accent's hue.

    Lightness is kept, so the family keeps its own light/dark structure — the
    hover tint stays a tint and the pressed shade stays darker — while hue and
    chroma come from the accent. Colours outside the family are returned as they
    are: their colour IS their meaning."""
    if _active_accent.lower() == ACCENT_DEFAULT:
        return color
    if not in_accent_family(color):
        return color
    L, a, b = to_oklab(hex_to_rgb(color))
    base_L, base_a, base_b = to_oklab(hex_to_rgb(ACCENT_DEFAULT))
    acc_L, acc_a, acc_b = to_oklab(hex_to_rgb(_active_accent))
    base_c = (base_a ** 2 + base_b ** 2) ** 0.5
    acc_c = (acc_a ** 2 + acc_b ** 2) ** 0.5
    own_c = (a ** 2 + b ** 2) ** 0.5
    if base_c <= 1e-6 or acc_c <= 1e-6:
        return rgb_to_hex(from_oklab((L, 0.0, 0.0)))
    scale = (own_c / base_c) * acc_c
    return rgb_to_hex(from_oklab((L, acc_a / acc_c * scale, acc_b / acc_c * scale)))


# ── Rewriting stylesheets ────────────────────────────────────────────────────

# A hex literal. Three or six digits, and not the start of a longer word — an ID
# selector like `#BigPlayer` must never be mistaken for a colour.
_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])")

# One `property: value` pair. The value stops at the end of the declaration, so
# a whole `qlineargradient(...)` with its stops comes along as one value and
# every colour in it is treated as the property's role.
_DECL_RE = re.compile(r"([-a-zA-Z]+)\s*:\s*([^;{}]*)")


def qss(sheet: str) -> str:
    """Rewrite every colour in a stylesheet (or an inline HTML `style=`) for the
    active theme. The identity function in light mode with the default accent,
    so the untouched app keeps exactly the look it has."""
    if not sheet or (_active_theme != "dark" and _active_accent.lower() == ACCENT_DEFAULT):
        return sheet

    def fix_decl(match: re.Match) -> str:
        prop, value = match.group(1), match.group(2)
        if "#" not in value:
            return match.group(0)
        role = _role_of(prop)
        fixed = _HEX_RE.sub(lambda m: shade(m.group(0), role), value)
        return match.group(0).replace(value, fixed) if fixed != value else match.group(0)

    return _DECL_RE.sub(fix_decl, sheet)


def qcolor(color: str, role: str = "ink") -> QColor:
    return QColor(shade(color, role))


# ── Active theme ─────────────────────────────────────────────────────────────

def theme_of(settings: dict) -> str:
    """The theme named in the settings, falling back to light."""
    want = str((settings or {}).get("theme") or "").strip().lower()
    return want if want in _THEMES else "light"


def accent_of(settings: dict) -> str:
    """The accent named in the settings, falling back to the app's blue."""
    want = str((settings or {}).get("accent_color") or "").strip().lower()
    if re.fullmatch(r"#(?:[0-9a-f]{6}|[0-9a-f]{3})", want):
        return rgb_to_hex(hex_to_rgb(want))
    return ACCENT_DEFAULT


def set_active(theme: str = "light", accent: str = ACCENT_DEFAULT) -> None:
    global _active_theme, _active_accent
    _active_theme = theme if theme in _THEMES else "light"
    _active_accent = accent if re.fullmatch(
        r"#(?:[0-9a-f]{6}|[0-9a-f]{3})", (accent or "").lower()) else ACCENT_DEFAULT
    _active_accent = _active_accent.lower()


def apply_settings(settings: dict) -> None:
    set_active(theme_of(settings), accent_of(settings))


def active_theme() -> str:
    return _active_theme


def active_accent() -> str:
    return _active_accent


def is_dark() -> bool:
    return _active_theme == "dark"


# ── Wiring it into the app ───────────────────────────────────────────────────

_hook_installed = False
_raw_set_stylesheet = None


def set_stylesheet_unthemed(widget, sheet: str) -> None:
    """Set a stylesheet the theme must NOT touch.

    For the one case where a colour is the content rather than the styling: the
    accent swatch in ⚙ Settings has to show exactly the colour that was picked.
    Going through `QWidget.setStyleSheet` would not help — after the hook that
    name IS the wrapper — so the original is kept here when it is replaced."""
    from PySide6.QtWidgets import QWidget

    original = _raw_set_stylesheet or QWidget.setStyleSheet
    original(widget, sheet)


def install_stylesheet_hook() -> None:
    """Route every `setStyleSheet` through `qss`.

    160 inline stylesheets carry the app's colours. Rewriting them at the call
    sites would be a 330-colour diff across files this feature has no other
    reason to touch — and would miss the next one somebody writes. One hook on
    QWidget (and QApplication, which is not a QWidget) themes all of them,
    including the dialogs built long after start-up."""
    global _hook_installed, _raw_set_stylesheet
    if _hook_installed:
        return
    from PySide6.QtWidgets import QApplication, QWidget

    _raw_set_stylesheet = QWidget.setStyleSheet
    for cls in (QWidget, QApplication):
        original = cls.setStyleSheet

        def themed(self, sheet, _original=original):
            return _original(self, qss(sheet))

        cls.setStyleSheet = themed
    _hook_installed = True
    log.debug("🎨 Stylesheet hook installed (theme=%s accent=%s)",
              _active_theme, _active_accent)


# The title bar is not Qt's to paint — Windows draws it, and it follows the
# SYSTEM theme unless a window says otherwise. So a dark app under a light
# Windows keeps a white caption bar over every window, which is what gives the
# "dark mode, except the top 30 pixels" look.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20      # ...and 19 before Windows 10 20H1
_frame_watcher = None


def apply_window_frame(widget) -> bool:
    """Ask Windows for a dark title bar on this window.

    Returns whether it was applied, so the caller can tell "light theme" from
    "this platform has no such thing". Anything that goes wrong here is
    cosmetic by definition, so it is logged and swallowed rather than allowed
    to take a window down with it."""
    import sys

    if not is_dark() or not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        hwnd = int(widget.winId())
        on = ctypes.c_int(1)
        dwm = ctypes.windll.dwmapi
        for attribute in (_DWMWA_USE_IMMERSIVE_DARK_MODE, 19):
            if dwm.DwmSetWindowAttribute(hwnd, attribute,
                                         ctypes.byref(on),
                                         ctypes.sizeof(on)) == 0:
                return True
    except Exception as exc:                        # noqa: BLE001 — cosmetic
        log.debug("🎨 Dark title bar not available: %s", exc)
    return False


def install_titlebar_hook() -> None:
    """Give every window a dark title bar, including the ones not built yet.

    On Show rather than up front: the native window — and so the handle DWM
    needs — does not exist until then, and dialogs are created all through the
    session. `QDialog.exec()` shows the window from C++ without passing through
    any Python `show()`, so an event filter on the application is what catches
    all of them."""
    global _frame_watcher
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QApplication, QWidget

    if _frame_watcher is not None or not is_dark():
        return

    class _FrameWatcher(QObject):
        def eventFilter(self, obj, event):
            if (event.type() == QEvent.Type.Show
                    and isinstance(obj, QWidget) and obj.isWindow()):
                apply_window_frame(obj)
            return False

    app = QApplication.instance()
    if app is None:
        return
    _frame_watcher = _FrameWatcher(app)
    app.installEventFilter(_frame_watcher)
    log.debug("🎨 Title-bar hook installed")


# The QColor constants tables paint rows with directly. Role comes from the
# name: a _BG/_ROW_* is a ground, a _FG is ink.
_SHARED_COLORS = (
    ("gui.common", "_C_ROUND_BG", "ground"),
    ("gui.common", "_C_ROUND_FG", "ink"),
    ("gui.common", "_C_DANCE_BG", "ground"),
    ("gui.common", "_C_DANCE_FG", "ink"),
    ("gui.common", "_C_ROW_EVEN", "ground"),
    ("gui.common", "_C_ROW_ODD", "ground"),
    ("gui.common", "_C_POP_FG", "ink"),
    ("gui.common", "_C_NEW_FG", "ink"),
    ("gui.common", "_C_SIM_FG", "ink"),
    ("gui.common", "_C_WARN_FG", "ink"),
    ("gui.common", "_C_LEN_WARN_FG", "ink"),
    ("gui.common", "_C_DEFAULT", "ink"),
    ("gui.playlist_table", "_C_MARK_BG", "ground"),
    ("gui.playlist_table", "_C_MARK_FG", "ink"),
    ("gui.playlist_table", "_C_ISSUE_BG", "ground"),
    ("gui.tournament_tree", "_C_MISS_BG", "ground"),
    # Class attributes rather than module constants — the resolver walks a
    # dotted path either way, they were simply never listed.
    ("gui.dialogs", "LibraryGapsDialog._C_BAD", "ground"),
    ("gui.dialogs", "LibraryGapsDialog._C_WARN", "ground"),
    # Widgets that PAINT themselves. A stylesheet cannot reach a QPainter, so
    # these would otherwise keep their light-theme colours on a dark page —
    # the Nb. gutter as a white stripe down the table, the desk switches as a
    # column of bright pills.
    ("gui.playlist_table", "_NumberHeader._BG", "ground"),
    ("gui.playlist_table", "_NumberHeader._FG", "ink"),
    ("gui.playlist_table", "_NumberHeader._LINE", "line"),
    ("player.play_mode_panel", "_Toggle._OFF_TRACK", "ground"),
    ("player.play_mode_panel", "_Toggle._DISABLED_TEXT", "ink"),
)


def sync_shared_colors() -> None:
    """Re-shade the shared QColor constants in place.

    Every module binds these by value (`from gui.common import _C_ROW_ODD`), so
    rebinding the name in the defining module would not reach them. QColor is
    mutable, so the object each importer already holds is edited instead — which
    is also why this has to run before the first table is painted."""
    import importlib

    for module_name, attr, role in _SHARED_COLORS:
        try:
            color = importlib.import_module(module_name)
            for part in attr.split("."):    # "_Toggle._OFF_TRACK" — a widget
                color = getattr(color, part)  # that paints its own colours
        except (ImportError, AttributeError):
            log.debug("🎨 %s.%s not present, skipped", module_name, attr)
            continue
        fixed = QColor(shade(color.name(), role))
        color.setRgb(fixed.red(), fixed.green(), fixed.blue(), color.alpha())


def app_palette() -> QPalette:
    """The Fusion palette for the active theme.

    The light values are the ones `run_gui` has always set; the dark ones are
    those same values put through the transform, so the window furniture matches
    the panes rather than being a second set of colours to keep in step."""
    roles = (
        ("Window", "#f0f2f5", "ground"),
        ("WindowText", "#141414", "ink"),
        ("Base", "#ffffff", "ground"),
        ("AlternateBase", "#f5f7fc", "ground"),
        ("Text", "#141414", "ink"),
        ("ButtonText", "#141414", "ink"),
        ("Button", "#e1e4eb", "ground"),
        ("Link", "#1e64c8", "ink"),
        ("Highlight", "#4682d2", "ground"),
        ("HighlightedText", "#ffffff", "ink"),
        ("ToolTipBase", "#ffffdc", "ground"),
        ("ToolTipText", "#141414", "ink"),
    )
    pal = QPalette()
    R = QPalette.ColorRole
    for name, color, role in roles:
        pal.setColor(getattr(R, name), QColor(shade(color, role)))
    if is_dark():
        # Highlighted text is the one pair the transform cannot help with: both
        # halves are picked for the light theme and would flip together.
        pal.setColor(R.HighlightedText, QColor("#ffffff"))
        pal.setColor(R.ToolTipBase, QColor(shade("#ffffdc", "ground")))
        # The bevel roles. Fusion draws every frame edge, group-box outline,
        # sunken panel and scrollbar groove out of these, and they are the one
        # group nothing above sets — so a default palette's light-theme values
        # came through, and the ⚙ Settings separators were pure white rules
        # across a dark dialog. Qt derives them from the button colour when a
        # palette is built from one; this does the same derivation by hand,
        # with Qt's own factors, on the button colour we just shaded.
        button = pal.color(R.Button)
        for name, factor in (("Light", 150), ("Midlight", 125)):
            pal.setColor(getattr(R, name), button.lighter(factor))
        for name, factor in (("Mid", 150), ("Dark", 200)):
            pal.setColor(getattr(R, name), button.darker(factor))
        pal.setColor(R.Shadow, QColor("#000000"))
    return pal
