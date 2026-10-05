"""The app's icons: one designed set, painted at whatever size and colour the
widget asks for.

Emoji were what every button used to wear. They are somebody else's artwork,
they land at a different size, weight and colour on every machine, and a row of
them never reads as a set. These come from Bootstrap Icons (MIT — see
ICONS-LICENSE.txt): one grid, one stroke weight, monochrome, so a toolbar looks
machined instead of assembled.

Use `icon(name)` for anything that takes a QIcon, `pixmap(name, px, colour)`
when a raw QPixmap is wanted (the presenter screen paints its own big ones).
Both are cached per (name, size, colour) — a table repainting its play column
must not re-rasterise an SVG per row.

    btn.setIcon(icon("play"))
    btn.setIconSize(QSize(16, 16))

`INK` is the default colour: a near-black that matches the app's text without
the harshness of pure black. Pass a colour for anything tinted — the presenter's
white-on-black, a red warning, an amber duck.
"""

from functools import lru_cache

from PySide6.QtCore import QBuffer, QIODevice, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from shared import theme
from shared.iconset import SVG

INK = "#33383f"          # default: the app's text colour
INK_LIGHT = "#f5f5f7"    # on a dark card (player, presenter)
ACCENT = "#1565c0"       # the app's blue — links, active tools
DANGER = "#c0392b"       # destructive actions
WARN = "#d98f3a"         # the duck, warnings
# An emoji carried its own colour, and that colour is half of what made it
# findable in a row of twenty. These are the few that keep one — used where the
# colour MEANS something (a gold wishlist, a red erase), never as decoration.
GOLD = "#d99e0b"         # wishlist, favourites, the trophy
GREEN = "#2e7d32"        # Eintanzen / practice
TEAL = "#00838f"         # the tournament day, the venue bundle
PURPLE = "#7b1fa2"       # party mode

_DEFAULT_PX = 16


def _disc_ink(fill: str) -> str:
    """The readable colour for a character sitting on a filled `fill` disc.

    The discs were white-on-blue, which only holds while the disc is dark. A
    picked accent can be any lightness, so the letter is chosen against the
    disc it actually lands on instead of assumed."""
    return "#ffffff" if theme.contrast_ratio(fill, "#ffffff") >= 3.0 else "#141414"


def names() -> list:
    """Every icon there is — the check a call site's typo trips over."""
    return sorted(SVG)


@lru_cache(maxsize=512)
def pixmap(name: str, px: int = _DEFAULT_PX, color: str = INK) -> QPixmap:
    """The icon as a transparent QPixmap of px × px, painted in `color`.

    An icon carries its colour in the pixels, so the theme's stylesheet hook
    never sees it — the shading has to happen here instead. Doing it inside the
    painter rather than on the constants above is what makes it complete: the
    colour is caught whether it arrived as an argument, as a literal, or as the
    `color=INK` default, which was bound when this function was defined and no
    amount of rebinding INK would ever reach. In light mode with the default
    accent it is the identity, and the cache key stays the colour as asked for
    — the theme is fixed for as long as the app runs."""
    try:
        view_box, body = SVG[name]
    except KeyError:
        raise KeyError(f"no icon named {name!r} — see shared.icons.names()") from None
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
           f'fill="{theme.shade(color, "ink")}">{body}</svg>')
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(doc.encode("utf-8")).render(p, QRectF(0, 0, px, px))
    p.end()
    return pm


@lru_cache(maxsize=512)
def icon(name: str, px: int = _DEFAULT_PX, color: str = INK) -> QIcon:
    """The icon as a QIcon — for buttons, menu actions, tabs and table cells.

    Rendered at 2× as well, so it stays sharp on a high-dpi screen and when a
    style hands the button a bigger icon size than it was asked for.
    """
    ic = QIcon(pixmap(name, px, color))
    ic.addPixmap(pixmap(name, px * 2, color))
    return ic


@lru_cache(maxsize=256)
def html(name: str, px: int = _DEFAULT_PX, color: str = INK) -> str:
    """The icon as an `<img>` tag for a rich-text QLabel.

    For the badge labels that used to start with an emoji and are one string,
    not a widget — a second QLabel just to carry the glyph would be worse.
    """
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap(name, px, color).save(buf, "PNG")
    data = bytes(buf.data().toBase64()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}" width="{px}" height="{px}">'


@lru_cache(maxsize=64)
def letter_pixmap(ch: str, px: int = _DEFAULT_PX, color: str = ACCENT) -> QPixmap:
    """A filled disc with a letter on it — the A–H deck badges.

    Bootstrap has no lettered circles (its `a-circle` / `b-circle` slots simply
    do not exist), and the boxed 🅰–🅷 emoji render as whatever tile the system
    emoji font decides on. Painted here it is one shape in the UI font, at the
    size the header asks for, and it sits in a row of real icons without
    looking like a stray character.
    """
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    disc = theme.shade(color, "ink")
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(disc))
    p.drawEllipse(QRectF(0, 0, px, px))
    font = p.font()
    font.setBold(True)
    font.setPixelSize(max(7, round(px * 0.66)))
    p.setFont(font)
    p.setPen(QColor(_disc_ink(disc)))
    p.drawText(QRectF(0, 0, px, px), int(Qt.AlignmentFlag.AlignCenter), ch)
    p.end()
    return pm


def _stamp_count(p: QPainter, big: int, count, badge: str):
    """Draw the count disc into the bottom-right corner of a `big`² pixmap."""
    d = round(big * 0.58)            # badge diameter
    rect = QRectF(big - d, big - d, d, d)
    disc = theme.shade(badge, "ink")
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(disc))
    p.drawEllipse(rect)
    font = p.font()
    font.setBold(True)
    font.setPixelSize(max(7, round(d * 0.74)))
    p.setFont(font)
    p.setPen(QColor(_disc_ink(disc)))
    p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), str(count))


@lru_cache(maxsize=64)
def counted_emoji(ch: str, count, px: int = _DEFAULT_PX,
                  badge: str = ACCENT) -> QIcon:
    """The emoji `ch` with a small count disc in its bottom-right corner.

    For the two cycle buttons in the toolbar: they keep the character they have
    always worn (⧉ decks, ⭐ wishlists) and the badge says how many are open —
    which the caption alone cannot do, since compaction drops the caption.
    `count` may be any short string; 0 is drawn, not hidden.

    `count=None` draws the bare emoji, full size: while the button still shows
    its caption the number is already there in words, and a badge on top of it
    would say the same thing twice.
    """
    big = px * 2
    pm = QPixmap(big, big)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # Badged: the glyph is inset, so the disc has an empty corner to sit in.
    span = big * (0.86 if count is not None else 1.0)
    font = p.font()
    font.setPixelSize(round(span * 0.9))
    p.setFont(font)
    p.setPen(QColor(theme.shade(INK, "ink")))
    p.drawText(QRectF(0, 0, span, span), int(Qt.AlignmentFlag.AlignCenter), ch)
    if count is not None:
        _stamp_count(p, big, count, badge)
    p.end()
    return QIcon(pm)


def button(btn, name: str, px: int = _DEFAULT_PX, color: str = INK):
    """Give a QToolButton / QPushButton its icon at a matching size.

    A convenience over setIcon + setIconSize, because Qt's default icon size
    (16 px, or whatever the style says) is nearly always not the one wanted.
    Returns the button, so it can be used inline.
    """
    btn.setIcon(icon(name, px, color))
    btn.setIconSize(QSize(px, px))
    return btn
