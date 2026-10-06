"""The 🎨 looks: designs to pick beyond the classic light and dark.

The classic themes (shared/theme.py) keep Qt's Fusion furniture and colour it.
A look restyles the furniture itself — buttons, fields, tabs, headers,
scrollbars, menus, the deck title strips — after one design:

* platform looks — Windows 11, macOS, GNOME, each light and dark;
* Desk looks — console, carbon, neon, studio: the feel of a mixing desk;
* modern looks — graphite, midnight, aurora, paper and two high-contrast
  ones, picked for readability first.

Every look is selectable on every system. Each one is a `Look`: one `Tokens`
colour set, hand-picked so dark is designed rather than derived, plus the
shape of its buttons, tabs and focus mark. The app's own inline stylesheets
(the round bands, the ▶ player card, …) still go through shared/theme.py's
transform; the accent it re-hues them to is the look's.
"""
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QFont

# A sheet that starts with this is final for its look: shared/theme.py's
# transform leaves it alone instead of shading the colours a second time.
LOOK_MARK = "/* look */"

# The pre-rendered pictures the ⚙ Settings tab shows, one per theme key
# (tools/theme_previews.py renders them from the real main window).
PREVIEW_DIR = Path(__file__).resolve().parents[1] / "assets" / "themes"


@dataclass(frozen=True)
class Tokens:
    window: str          # the dialog / main-window ground
    base: str            # lists, tables, text fields
    alt_base: str        # every other table row
    surface: str         # a button's face
    surface_hover: str
    surface_pressed: str
    border: str          # hairlines: frames, grid, separators
    border_strong: str   # a control's outline, a scrollbar handle
    text: str
    text_dim: str        # disabled text, placeholders
    accent: str          # filled: the default button, a checked toggle
    on_accent: str       # text on that fill
    accent_ink: str      # the accent as text: links, focus rings
    selection: str       # the selected row's band
    on_selection: str
    header: str          # table header, menu bar
    tooltip: str
    radius: int
    # Set, a button / header face is a vertical gradient from this down to
    # `surface` / `header` — the machined look of a mixing desk. Empty = flat.
    surface_top: str = ""
    header_top: str = ""


# How a button is drawn:
#   outline — a face with a frame (Windows 11, macOS)
#   flat    — a grey face, no frame (GNOME)
#   key     — a top-lit gradient key in a dark slot (desk looks)
#   glow    — flat and dark; a pressed toggle glows with an accent rim
#   tonal   — a soft filled face, no frame, generous corners
#   pill    — fully rounded ends
#   bold    — a 2 px frame, for the high-contrast looks
BUTTON_STYLES = ("outline", "flat", "key", "glow", "tonal", "pill", "bold")


@dataclass(frozen=True)
class Look:
    key: str
    group: str           # "platform" | "desk" | "modern"
    caption: str         # English; the catalog has the German
    blurb: str
    dark: bool
    tokens: Tokens
    fonts: tuple
    buttons: str         # one of BUTTON_STYLES
    tabs: str = "underline"   # "underline" | "segment" | "key" | "pill"
    focus: str = "ring"       # "ring" | "underline" (Windows 11)
    # The group whose finer details the look shares: desk looks draw faders
    # and dim headers, platform looks keep the system's own checkboxes. Empty
    # = its own group; a look of your own keeps the family it was copied from.
    family: str = ""


TAB_STYLES = ("underline", "segment", "key", "pill")
FOCUS_STYLES = ("ring", "underline")


GROUPS = (
    ("platform", "Platform looks"),
    ("desk", "Desk looks"),
    ("modern", "Modern looks"),
)

_SEGOE = ("Segoe UI Variable Text", "Segoe UI")
# Bahnschrift is Windows' DIN: the lettering of mixing desks and meters.
_DIN = ("Bahnschrift", "Segoe UI")
# Qt on macOS already starts with the system font; listing it keeps a
# preview rendered elsewhere honest about what it stands in for.
_MAC = (".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue")
_GNOME = ("Adwaita Sans", "Cantarell", "Inter", "Noto Sans")

_LOOKS = (
    # ── Platform ─────────────────────────────────────────────────────────────
    Look("win11_light", "platform", "Windows 11 · Light",
         "Fluent: 4 px corners, Segoe UI Variable, the Windows blue and an "
         "accent line under the active field.",
         False, Tokens(
             window="#f3f3f3", base="#ffffff", alt_base="#f9f9f9",
             surface="#fbfbfb", surface_hover="#f6f6f6", surface_pressed="#f0f0f0",
             border="#e5e5e5", border_strong="#c8c8c8",
             text="#1b1b1b", text_dim="#6e6e6e",
             accent="#005fb8", on_accent="#ffffff", accent_ink="#005fb8",
             selection="#d6e8f8", on_selection="#1b1b1b",
             header="#f9f9f9", tooltip="#f9f9f9", radius=4),
         _SEGOE, "outline", focus="underline"),
    Look("win11_dark", "platform", "Windows 11 · Dark",
         "Fluent in dark: the Windows 11 dark greys with the light blue accent.",
         True, Tokens(
             window="#202020", base="#272727", alt_base="#2c2c2c",
             surface="#2d2d2d", surface_hover="#323232", surface_pressed="#292929",
             border="#3a3a3a", border_strong="#505050",
             text="#ffffff", text_dim="#a8a8a8",
             accent="#60cdff", on_accent="#000000", accent_ink="#60cdff",
             selection="#1f4a66", on_selection="#ffffff",
             header="#2b2b2b", tooltip="#2b2b2b", radius=4),
         _SEGOE, "outline", focus="underline"),
    Look("macos_light", "platform", "macOS · Light",
         "Aqua as of Sonoma: 6 px corners, a solid blue selection with white "
         "text and an accent ring around the active field.",
         False, Tokens(
             window="#ececec", base="#ffffff", alt_base="#f4f5f5",
             surface="#ffffff", surface_hover="#f7f7f7", surface_pressed="#e4e4e4",
             border="#dcdcdc", border_strong="#c2c2c2",
             text="#262626", text_dim="#767676",
             accent="#007aff", on_accent="#ffffff", accent_ink="#0068da",
             selection="#0063e1", on_selection="#ffffff",
             header="#fafafa", tooltip="#fdfdfd", radius=6),
         _MAC, "outline", tabs="segment"),
    Look("macos_dark", "platform", "macOS · Dark",
         "Aqua in dark mode: charcoal panes, grey keys, the bright system blue.",
         True, Tokens(
             window="#282828", base="#1e1e1e", alt_base="#262626",
             surface="#4a4a4a", surface_hover="#555555", surface_pressed="#616161",
             border="#383838", border_strong="#555555",
             text="#e6e6e6", text_dim="#9a9a9a",
             accent="#0a84ff", on_accent="#ffffff", accent_ink="#3b9bff",
             selection="#0058d0", on_selection="#ffffff",
             header="#2a2a2a", tooltip="#323232", radius=6),
         _MAC, "outline", tabs="segment"),
    Look("gnome_light", "platform", "Linux GNOME · Light",
         "Adwaita: 6 px corners, flat grey buttons without a frame, the GNOME blue.",
         False, Tokens(
             window="#fafafb", base="#ffffff", alt_base="#f6f6f7",
             surface="#e8e8e9", surface_hover="#dfdfe0", surface_pressed="#cdcdce",
             border="#dededf", border_strong="#c0c0c1",
             text="#313134", text_dim="#737378",
             accent="#3584e4", on_accent="#ffffff", accent_ink="#1c71d8",
             selection="#d4e5fa", on_selection="#313134",
             header="#ebebed", tooltip="#ffffff", radius=6),
         _GNOME, "flat"),
    Look("gnome_dark", "platform", "Linux GNOME · Dark",
         "Adwaita dark: soft charcoal, flat buttons, the GNOME blue.",
         True, Tokens(
             window="#222226", base="#1d1d20", alt_base="#262629",
             surface="#36363a", surface_hover="#404044", surface_pressed="#4e4e52",
             border="#36363a", border_strong="#4f4f53",
             text="#ffffff", text_dim="#a2a2a6",
             accent="#3584e4", on_accent="#ffffff", accent_ink="#78aeed",
             selection="#26405f", on_selection="#ffffff",
             header="#2e2e32", tooltip="#2e2e32", radius=6),
         _GNOME, "flat"),
    # ── Desk looks ───────────────────────────────────────────────────────────
    Look("console", "desk", "Console",
         "Graphite, keys lit from above like a mixing desk, a pressed key "
         "glows blue. Lettering in Bahnschrift.",
         True, Tokens(
             window="#1d1e21", base="#141518", alt_base="#18191c",
             surface="#2a2c30", surface_hover="#34373c", surface_pressed="#1f2023",
             border="#0c0d0e", border_strong="#45484e",
             text="#e3e5e8", text_dim="#959aa2",
             accent="#1e9bff", on_accent="#03111d", accent_ink="#4cb3ff",
             selection="#1b4f80", on_selection="#ffffff",
             header="#222427", tooltip="#2a2c30", radius=3,
             surface_top="#3a3d42", header_top="#303337"),
         _DIN, "key", tabs="key"),
    Look("carbon", "desk", "Carbon",
         "Jet black with metal gradients and orange as the light: harder and "
         "higher in contrast, like a hardware controller in a dark hall.",
         True, Tokens(
             window="#121212", base="#0b0b0b", alt_base="#111111",
             surface="#1e1e1f", surface_hover="#2c2c2e", surface_pressed="#101010",
             border="#000000", border_strong="#3c3c3e",
             text="#ececec", text_dim="#9a9a9a",
             accent="#ff8a1c", on_accent="#160b00", accent_ink="#ffa040",
             selection="#5a3410", on_selection="#ffffff",
             header="#161616", tooltip="#1e1e1f", radius=2,
             surface_top="#3a3a3c", header_top="#2b2b2c"),
         _DIN, "key", tabs="key"),
    Look("neon", "desk", "Neon",
         "Flat night blue with cyan as the light: whatever is on gets a "
         "glowing rim instead of a fill. Rounder corners.",
         True, Tokens(
             window="#0c0e15", base="#0f121b", alt_base="#131725",
             surface="#161b29", surface_hover="#1d2436", surface_pressed="#10141f",
             border="#1f2638", border_strong="#2c3654",
             text="#dfe6ff", text_dim="#8a94b8",
             accent="#00d9ff", on_accent="#001318", accent_ink="#3fe3ff",
             selection="#0f3d52", on_selection="#ffffff",
             header="#121624", tooltip="#161b29", radius=6),
         _SEGOE, "glow"),
    Look("studio", "desk", "Studio",
         "The bright desk: brushed aluminium, keys lit from above, orange as "
         "the accent. For daylight and bright halls.",
         False, Tokens(
             window="#e3e5e8", base="#f7f8f9", alt_base="#eef0f2",
             surface="#e4e7ea", surface_hover="#eff1f3", surface_pressed="#d3d7dc",
             border="#c7cbd1", border_strong="#a7adb5",
             text="#1d2024", text_dim="#5f656e",
             accent="#e86c00", on_accent="#ffffff", accent_ink="#b85200",
             selection="#ffdcb8", on_selection="#1d2024",
             header="#d6d9de", tooltip="#fdfdfe", radius=3,
             surface_top="#fdfdfe", header_top="#f3f4f6"),
         _DIN, "key", tabs="key"),
    # ── Modern, readability first ────────────────────────────────────────────
    Look("graphite", "modern", "Graphite",
         "Calm neutral dark: near-white text on graphite, soft filled buttons "
         "with round corners, a clear blue. Easy on the eyes for a long evening.",
         True, Tokens(
             window="#1e1f22", base="#18191b", alt_base="#1d1e21",
             surface="#2c2e33", surface_hover="#363940", surface_pressed="#26282c",
             border="#2f3136", border_strong="#4a4d55",
             text="#f1f2f4", text_dim="#a9aeb7",
             accent="#2f6fe0", on_accent="#ffffff", accent_ink="#6ea8fe",
             selection="#24456f", on_selection="#ffffff",
             header="#232428", tooltip="#2c2e33", radius=8),
         _SEGOE, "tonal", tabs="pill"),
    Look("midnight", "modern", "Midnight",
         "Deep navy with a teal accent and pill-shaped buttons: modern and "
         "quiet, the text stays crisp against the dark blue.",
         True, Tokens(
             window="#0f1724", base="#0b1220", alt_base="#101a2a",
             surface="#1a2638", surface_hover="#23324b", surface_pressed="#152031",
             border="#1e2a3d", border_strong="#3a4b66",
             text="#e9eef7", text_dim="#a3b0c4",
             accent="#2dd4bf", on_accent="#04201c", accent_ink="#5eead4",
             selection="#134e4a", on_selection="#ffffff",
             header="#121c2c", tooltip="#1a2638", radius=12),
         _SEGOE, "pill", tabs="pill"),
    Look("aurora", "modern", "Aurora",
         "Dark with a violet accent: soft filled buttons, warm dark greys, "
         "light lavender for links and focus.",
         True, Tokens(
             window="#18161f", base="#131119", alt_base="#18151f",
             surface="#28232f", surface_hover="#322c3c", surface_pressed="#201c28",
             border="#2b2735", border_strong="#4a4259",
             text="#f0edf7", text_dim="#aea7bd",
             accent="#7c4dff", on_accent="#ffffff", accent_ink="#c4b5fd",
             selection="#3d2f66", on_selection="#ffffff",
             header="#1d1a25", tooltip="#28232f", radius=8),
         _SEGOE, "tonal", tabs="pill"),
    Look("paper", "modern", "Paper",
         "Clean and bright: white panes, nearly black text, soft grey buttons "
         "with round corners and a strong blue. Crisp in daylight.",
         False, Tokens(
             window="#f4f5f7", base="#ffffff", alt_base="#f6f7f9",
             surface="#e8ebef", surface_hover="#dde2e8", surface_pressed="#d0d6de",
             border="#dde1e6", border_strong="#b4bcc6",
             text="#111418", text_dim="#525b66",
             accent="#2457d6", on_accent="#ffffff", accent_ink="#1f4fc4",
             selection="#d8e4ff", on_selection="#111418",
             header="#eef0f3", tooltip="#ffffff", radius=8),
         _SEGOE, "tonal", tabs="pill"),
    Look("contrast_dark", "modern", "High contrast · Dark",
         "Black and white with a yellow accent, 2 px frames and a yellow "
         "selection: readable from across the hall and in bright stage light.",
         True, Tokens(
             window="#000000", base="#000000", alt_base="#141414",
             surface="#1a1a1a", surface_hover="#2e2e2e", surface_pressed="#3a3a3a",
             border="#6b6b6b", border_strong="#d6d6d6",
             text="#ffffff", text_dim="#d4d4d4",
             accent="#ffd60a", on_accent="#000000", accent_ink="#ffd60a",
             selection="#ffd60a", on_selection="#000000",
             header="#161616", tooltip="#000000", radius=4),
         _SEGOE, "bold"),
    Look("contrast_light", "modern", "High contrast · Light",
         "Black on white with a deep blue accent and 2 px frames: the most "
         "readable light look, also on a weak projector or laptop screen.",
         False, Tokens(
             window="#ffffff", base="#ffffff", alt_base="#f0f0f0",
             surface="#ffffff", surface_hover="#e6edfc", surface_pressed="#d2ddf8",
             border="#8c8c8c", border_strong="#1a1a1a",
             text="#000000", text_dim="#3b3b3b",
             accent="#0037b3", on_accent="#ffffff", accent_ink="#0037b3",
             selection="#0037b3", on_selection="#ffffff",
             header="#ebebeb", tooltip="#ffffff", radius=4),
         _SEGOE, "bold"),
)

LOOKS = {look.key: look for look in _LOOKS}


def get(key: str) -> Look | None:
    return LOOKS.get(key)


def family(look: Look) -> str:
    return look.family or look.group


def mix(one: str, two: str, share: float) -> str:
    """`share` of `one` over `two`, in sRGB — what an alpha fill looks like."""
    a, b = QColor(one), QColor(two)
    return QColor(round(a.red() * share + b.red() * (1 - share)),
                  round(a.green() * share + b.green() * (1 - share)),
                  round(a.blue() * share + b.blue() * (1 - share))).name()


def font(look: Look, base: QFont) -> QFont:
    """The app font for this look, at the size the platform already chose."""
    out = QFont(base)
    out.setFamilies(list(look.fonts) + [base.family()])
    return out


def preview_path(key: str) -> Path:
    return PREVIEW_DIR / f"{key}.png"


def shared_colors(look: Look) -> dict[str, str]:
    """The colours tables PAINT with (gui/common.py's `_C_*`), for this look.

    Only the furniture is replaced: row grounds, the round and dance bands,
    the number gutter. Inks that carry meaning — popularity amber, a warning
    red, the new-title blue — keep going through the theme transform."""
    t = look.tokens
    dark = look.dark
    green = "#5fb760" if dark else "#2e8b3a"
    return {
        "_C_ROW_EVEN": t.base,
        "_C_ROW_ODD": t.alt_base,
        "_C_ROUND_BG": mix(t.accent, t.base, 0.22 if dark else 0.13),
        "_C_ROUND_FG": t.accent_ink,
        "_C_DANCE_BG": mix(green, t.base, 0.16 if dark else 0.09),
        "_C_DANCE_FG": green,
        "_C_DEFAULT": t.text,
        "_NumberHeader._BG": t.header,
        "_NumberHeader._FG": t.text_dim,
        "_NumberHeader._LINE": t.border,
    }


def _svg_file(name: str, body: str, size: int) -> str:
    """A small SVG a stylesheet can name by path.

    QSS draws no shapes of its own — a combo's arrow, a check box's tick
    want an image. Written once per colour into the temp folder; nothing to
    bundle with the app."""
    folder = Path(tempfile.gettempdir()) / "danceplaylist_theme"
    path = folder / f"{name}.svg"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
            f'height="{size}" viewBox="0 0 {size} {size}">{body}</svg>',
            encoding="utf-8")
    return path.as_posix()


def _chevron(color: str, up: bool = False) -> str:
    d = "M1.5 6.5 L5 3 L8.5 6.5" if up else "M1.5 3.5 L5 7 L8.5 3.5"
    return _svg_file(
        f"chevron_{'up_' if up else ''}{color.lstrip('#')}",
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round"/>', 10)


def _tick(color: str) -> str:
    return _svg_file(
        f"tick_{color.lstrip('#')}",
        f'<path d="M2.5 6.2 L5 8.6 L9.6 3.6" fill="none" stroke="{color}" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>', 12)


def _face(top: str, bottom: str) -> str:
    """A control's face: a top-lit vertical gradient, or flat when `top` is empty."""
    if not top:
        return bottom
    return (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {top}, stop:1 {bottom})")


def _on(look: Look) -> str:
    """The declarations of something switched on: a checked toggle, the
    default button, the focused deck's title strip."""
    t = look.tokens
    if look.buttons == "glow":
        return (f"background: {mix(t.accent, t.base, 0.14)}; color: {t.accent_ink}; "
                f"border: 1px solid {t.accent};")
    if look.buttons == "key":
        lit = mix("#ffffff", t.accent, 0.28)
        return (f"background: {_face(lit, t.accent)}; color: {t.on_accent}; "
                f"border: 1px solid {mix(t.accent, '#000000', 0.7)};")
    width = 2 if look.buttons == "bold" else 1
    return (f"background: {t.accent}; color: {t.on_accent}; "
            f"border: {width}px solid {t.accent};")


def _button(look: Look) -> tuple[str, str, int]:
    """(frame declarations, face, corner radius) of an ordinary button."""
    t = look.tokens
    style = look.buttons
    if style == "key":
        frame = (f"border: 1px solid {t.border}; border-top-color: {t.border_strong};"
                 if look.dark else f"border: 1px solid {t.border_strong};")
        return frame, _face(t.surface_top, t.surface), t.radius
    if style in ("flat", "tonal"):
        return "border: 1px solid transparent;", t.surface, t.radius
    if style == "glow":
        return f"border: 1px solid {t.border_strong};", t.surface, t.radius
    if style == "pill":
        return f"border: 1px solid {t.border_strong};", t.surface, 11
    if style == "bold":
        return f"border: 2px solid {t.border_strong};", t.surface, t.radius
    return f"border: 1px solid {t.border_strong};", t.surface, t.radius


def _tabs(look: Look, face: str) -> str:
    t = look.tokens
    if look.tabs == "segment":
        return f"background: {t.surface}; border: 1px solid {t.border_strong};"
    if look.tabs == "key":
        return (f"background: {face}; color: {t.accent_ink}; "
                f"border: 1px solid {t.border}; border-bottom: 2px solid {t.accent};")
    if look.tabs == "pill":
        return (f"background: {mix(t.accent, t.window, 0.18)}; "
                f"color: {t.accent_ink}; border: 1px solid transparent;")
    return (f"background: transparent; color: {t.text}; "
            f"border-bottom: 2px solid {t.accent_ink};")


def _fader(t: Tokens) -> str:
    """A slider as a mixer fader: a slim dark slot and a square cap."""
    return f"""
QSlider::groove:horizontal {{
    height: 4px; background: {t.border}; border: 1px solid {t.border_strong};
    border-radius: 1px;
}}
QSlider::handle:horizontal {{
    width: 10px; margin: -7px 0; border-radius: 2px;
    background: {_face(t.surface_top or mix('#ffffff', t.surface, 0.15), t.surface)};
    border: 1px solid {t.border}; border-top-color: {t.border_strong};
}}"""


def _checks(t: Tokens) -> str:
    """Check boxes every look can see: a framed slot that lights up when on."""
    return f"""
QCheckBox::indicator, QGroupBox::indicator {{
    width: 13px; height: 13px; border-radius: 3px;
    border: 1px solid {t.border_strong}; background: {t.base};
}}
QCheckBox::indicator:hover {{ border-color: {t.accent_ink}; }}
QCheckBox::indicator:checked, QGroupBox::indicator:checked {{
    background: {t.accent}; border-color: {t.accent};
    image: url({_tick(t.on_accent)});
}}
QCheckBox::indicator:disabled {{ background: {t.window}; border-color: {t.border}; }}"""


def stylesheet(look: Look) -> str:
    """The app-wide stylesheet: the shape of every standard control."""
    t = look.tokens
    r = t.radius
    frame, face, button_r = _button(look)
    face_hover = (_face(mix("#ffffff", t.surface_top, 0.06), t.surface_hover)
                  if look.buttons == "key" else t.surface_hover)
    on = _on(look)
    ring = 2 if look.buttons == "bold" else 1
    focus = (f"border-bottom: 2px solid {t.accent_ink}; padding-bottom: 2px;"
             if look.focus == "underline" else
             f"border: {ring}px solid {t.accent_ink};")
    dim_headers = family(look) == "desk"
    return f"""
QMainWindow, QDialog {{ background: {t.window}; }}
QToolTip {{
    background: {t.tooltip}; color: {t.text};
    border: 1px solid {t.border_strong}; border-radius: {r}px; padding: 4px 6px;
}}

QPushButton {{
    background: {face}; {frame}
    border-radius: {button_r}px; padding: 3px 8px;
}}
QPushButton:hover {{ background: {face_hover}; }}
QPushButton:pressed {{ background: {t.surface_pressed}; }}
QPushButton:disabled {{ color: {t.text_dim}; }}
QPushButton:default, QPushButton:checked {{ {on} }}
QPushButton:default:hover, QPushButton:checked:hover {{ border-color: {t.accent_ink}; }}

QToolButton {{
    background: transparent; border: 1px solid transparent;
    border-radius: {min(button_r, 8)}px; padding: 0;
}}
QToolButton:hover {{ background: {t.surface_hover}; border-color: {t.border}; }}
QToolButton:pressed {{ background: {t.surface_pressed}; }}
QToolButton:checked {{
    background: {mix(t.accent, t.window, 0.18)}; border-color: {mix(t.accent, t.window, 0.4)};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {{
    background: {t.base}; border: {ring}px solid {t.border_strong};
    border-radius: {r}px; padding: 3px 6px;
    selection-background-color: {t.accent}; selection-color: {t.on_accent};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ {focus} }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {t.text_dim}; }}
QComboBox {{ padding-right: 22px; }}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right;
    width: 20px; border: none;
}}
QComboBox::down-arrow {{ image: url({_chevron(t.text_dim)}); width: 10px; height: 10px; }}
QComboBox::down-arrow:on {{ image: url({_chevron(t.accent_ink)}); }}
QAbstractSpinBox {{ padding-right: 18px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border; width: 16px; border: none; background: transparent;
}}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
    background: {t.surface_hover};
}}
QAbstractSpinBox::up-arrow {{ image: url({_chevron(t.text_dim, True)}); width: 8px; height: 8px; }}
QAbstractSpinBox::down-arrow {{ image: url({_chevron(t.text_dim)}); width: 8px; height: 8px; }}
QComboBox QAbstractItemView {{
    background: {t.base}; border: 1px solid {t.border_strong};
    selection-background-color: {t.selection}; selection-color: {t.on_selection};
    outline: none;
}}

QTabWidget::pane {{ border: 1px solid {t.border}; border-radius: {r}px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {t.text_dim};
    border: 1px solid transparent; border-radius: {r}px;
    padding: 5px 12px; margin: 2px 1px;
}}
QTabBar::tab:hover {{ color: {t.text}; background: {t.surface_hover}; }}
QTabBar::tab:selected {{ color: {t.text}; {_tabs(look, face)} }}

QHeaderView {{ background: {t.header}; border: none; }}
QHeaderView::section {{
    background: {_face(t.header_top, t.header)};
    color: {t.text_dim if dim_headers else t.text};
    border: none; border-right: 1px solid {t.border};
    border-bottom: 1px solid {t.border_strong};
    padding: 4px 6px; font-weight: 600;
}}
QHeaderView::section:hover {{ background: {t.surface_hover}; }}
QTableCornerButton::section {{ background: {t.header}; border: none; }}

QAbstractItemView {{
    background: {t.base}; alternate-background-color: {t.alt_base};
    border: 1px solid {t.border}; gridline-color: {t.border};
    selection-background-color: {t.selection}; selection-color: {t.on_selection};
}}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle {{
    background: {t.border_strong}; border-radius: 4px; border: 2px solid transparent;
    background-clip: padding;
}}
QScrollBar::handle:vertical {{ min-height: 28px; }}
QScrollBar::handle:horizontal {{ min-width: 28px; }}
QScrollBar::handle:hover {{ background: {t.text_dim}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QMenuBar {{ background: {t.window}; }}
QMenuBar::item {{ padding: 4px 10px; border-radius: {r}px; }}
QMenuBar::item:selected {{ background: {t.surface_hover}; }}
QMenu {{
    background: {t.base}; border: 1px solid {t.border_strong};
    border-radius: {r + 2}px; padding: 4px;
}}
QMenu::item {{ padding: 5px 24px 5px 22px; border-radius: {r}px; }}
QMenu::item:selected {{ background: {t.selection}; color: {t.on_selection}; }}
QMenu::item:disabled {{ color: {t.text_dim}; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 6px; }}

QGroupBox {{
    border: 1px solid {t.border}; border-radius: {r + 2}px;
    margin-top: 14px; padding-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 10px; padding: 0 4px; font-weight: 600;
}}

QProgressBar {{
    background: {t.surface}; border: 1px solid {t.border};
    border-radius: {r}px; text-align: center; min-height: 14px;
}}
QProgressBar::chunk {{
    background: {_face(t.surface_top and mix('#ffffff', t.accent, 0.28), t.accent)};
    border-radius: {max(r - 1, 2)}px;
}}

QSlider::groove:horizontal {{ height: 4px; background: {t.border_strong}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 14px; margin: -6px 0; border-radius: 8px;
    background: {t.base}; border: 1px solid {t.border_strong};
}}{_fader(t) if family(look) == "desk" else ""}{_checks(t) if family(look) != "platform" else ""}

QSplitter::handle {{ background: {t.window}; }}
QStatusBar {{ background: {t.window}; color: {t.text_dim}; }}
QStatusBar::item {{ border: none; }}
"""


def parts(look: Look) -> dict[str, str]:
    """Inline sheets for the app's own furniture: the deck title strip (idle /
    focused) and the Planning ⇄ Playing switch. Each starts with LOOK_MARK,
    so the theme transform hands it through unchanged."""
    t = look.tokens
    strip = ("border-radius:%dpx; padding:2px 8px; font-size:11px; font-weight:bold;"
             % min(t.radius, 6))
    on = _on(look).replace(": ", ":")
    _frame, face, _r = _button(look)
    return {
        "deck_idle": (f"{LOOK_MARK} background:{_face(t.header_top, t.header)};"
                      f" color:{t.text_dim}; border:1px solid {t.border}; {strip}"),
        "deck_active": f"{LOOK_MARK} {on} {strip}",
        "mode_btn": (f"{LOOK_MARK} QPushButton{{border:1px solid {t.border};"
                     f" border-radius:0; background:{face}; color:{t.text_dim};"
                     f" font-weight:bold;}}"
                     f"QPushButton:checked{{{on}}}"),
    }
