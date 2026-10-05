"""Transport and desk icons in the SF-Symbols style of the iPad app, painted
instead of shipped: no image files to install, and every glyph is sharp at
whatever size the presenter screen scales it to.

Everything is built on one shared geometry so a row of them reads as a set:

* the same optical box (`_BOX`) for every glyph, so nothing sits higher, wider
  or further left than its neighbour;
* the same corner radius (`_R`), applied by stroking the filled path with a
  round-join pen — Apple's transport glyphs have soft tips, and hard points are
  what make a hand-drawn set look hand-drawn;
* the same stroke weight (`_W`) for the outlined ones.

Coordinates are fractions of the icon size, so a glyph is identical at 16 px
and at 200 px.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap,
)

# The box every glyph is drawn into: symmetric side margins, and a height that
# leaves the same air above and below. Transport arrows fill it; the round
# glyphs use the full square, as SF's ".circle" variants do.
_BOX = (0.085, 0.205, 0.915, 0.795)   # left, top, right, bottom
_R = 0.052       # corner radius — the tips of every arrow
_W = 0.085       # stroke weight of the outlined glyphs


def _canvas(px: int):
    """A transparent square pixmap and an antialiased painter on it."""
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    return pm, p


def _soft(p: QPainter, path: QPainterPath, color: str, px: int, r: float = _R):
    """Fill a path AND stroke it with a round-join pen of the same colour: the
    outline grows the shape by r and rounds every corner in one pass, which is
    how the tips of these arrows get their radius."""
    pen = QPen(QColor(color))
    pen.setWidthF(2 * r * px)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(QColor(color))
    p.drawPath(path)


def _triangle(px: int, x0: float, x1: float, top: float, bot: float,
              r: float = _R) -> QPainterPath:
    """A triangle pointing from the flat edge at x0 towards the tip at x1,
    already pulled in by r so that _soft() grows it back to exactly [x0, x1].

    The tip is inset further than the flat edge: it is a sharp corner, and a
    round join eats more of a sharp corner than of a blunt one.
    """
    d = 1 if x1 > x0 else -1
    flat = x0 + d * r
    tip = x1 - d * 2.1 * r
    path = QPainterPath(QPointF(flat * px, (top + r) * px))
    path.lineTo(flat * px, (bot - r) * px)
    path.lineTo(tip * px, (top + bot) / 2 * px)
    path.closeSubpath()
    return path


def _bar(px: int, x: float, w: float, top: float, bot: float,
         r: float = _R) -> QPainterPath:
    """A rounded upright bar — the ⏭ end-stop and the ⏸ strokes."""
    path = QPainterPath()
    path.addRoundedRect(QRectF(x * px, top * px, w * px, (bot - top) * px),
                        r * px, r * px)
    return path


def _pair(px: int, color: str, x0: float, x1: float, back: bool = False):
    """The two chevrons of ⏪ / ⏩, centred in _BOX with a hairline between
    them — a set of transport buttons only looks machined if forward and
    backward are exact mirrors."""
    left, top, right, bot = _BOX
    mid = (left + right) / 2
    gap = 0.012
    pm, p = _canvas(px)
    if back:
        for a, b in ((mid - gap, left), (right, mid + gap)):
            _soft(p, _triangle(px, a, b, top, bot), color, px)
    else:
        for a, b in ((left, mid - gap), (mid + gap, right)):
            _soft(p, _triangle(px, a, b, top, bot), color, px)
    p.end()
    return pm


def backward(px: int, color: str) -> QPixmap:
    """'backward.fill' — the previous title."""
    return _pair(px, color, *_BOX[::2], back=True)


def forward(px: int, color: str) -> QPixmap:
    """'forward.fill' — the next title."""
    return _pair(px, color, *_BOX[::2])


def forward_end(px: int, color: str) -> QPixmap:
    """'forward.end.fill' — the ⏭ of the up-next header: two chevrons run into
    the end-stop, so they get the room the bar takes."""
    left, top, right, bot = _BOX
    bar_w = 0.105
    stop = right - bar_w
    mid = (left + stop) / 2
    gap = 0.012
    pm, p = _canvas(px)
    for a, b in ((left, mid - gap), (mid + gap, stop - 0.022)):
        _soft(p, _triangle(px, a, b, top, bot), color, px)
    _soft(p, _bar(px, stop, bar_w, top, bot, 0.035), color, px, 0.0)
    p.end()
    return pm


def _knockout(p: QPainter, px: int, color: str):
    """Start a filled disc that the glyph is then punched out of — SF's
    '.circle.fill' look, and transparent rather than black, so it sits on any
    background."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    # Half a pixel of air: an ellipse drawn out to the very edge has its
    # antialiased rim clipped at top, bottom and both sides, which puts four
    # flat spots on what has to read as a perfect circle.
    p.drawEllipse(QRectF(0.5, 0.5, px - 1, px - 1))
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)


# The round glyphs are painted this many times too large and scaled back down:
# their rim IS the shape, and plain antialiasing at button size facets it.
_SS = 4


def _shrink(pm: QPixmap, px: int) -> QPixmap:
    """Supersampled → button size, in the screen's own pixels: hand Qt a 1×
    pixmap on a 125 % display and it stretches the disc by a fraction of a
    pixel, which is precisely what stops it looking round."""
    scr = QGuiApplication.primaryScreen()
    dpr = scr.devicePixelRatio() if scr is not None else 1.0
    side = max(1, round(px * dpr))
    out = pm.scaled(side, side, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
    out.setDevicePixelRatio(dpr)
    return out


def play_circle(px: int, color: str) -> QPixmap:
    """'play.circle.fill' — the centre of the transport, while paused.

    The triangle is nudged right of the true centre: its mass sits at a third
    of its width, so a geometrically centred play arrow always looks like it
    has slipped to the left."""
    big = px * _SS
    pm, p = _canvas(big)
    _knockout(p, big, color)
    _soft(p, _triangle(big, 0.355, 0.735, 0.275, 0.725, 0.045), color, big, 0.045)
    p.end()
    return _shrink(pm, px)


def pause_circle(px: int, color: str) -> QPixmap:
    """'pause.circle.fill' — the same button while something is playing."""
    big = px * _SS
    pm, p = _canvas(big)
    _knockout(p, big, color)
    for x in (0.355, 0.545):
        _soft(p, _bar(big, x, 0.10, 0.29, 0.71, 0.04), color, big, 0.0)
    p.end()
    return _shrink(pm, px)


def pause(px: int, color: str) -> QPixmap:
    """'pause.fill' — the between-songs break, on the presenter's hero line.

    The bare pair of bars, not the transport's '.circle.fill' variant: the
    break is a state of the screen, and a disc down there would read as a
    button the hall could press. Same box, same soft corners as the row of
    icons in the foot, so it belongs to the same set."""
    top, bot = _BOX[1], _BOX[3]
    w = 0.26
    gap = 0.23
    x0 = (1.0 - (2 * w + gap)) / 2   # centred in the square, not in _BOX
    pm, p = _canvas(px)
    for x in (x0, x0 + w + gap):
        _soft(p, _bar(px, x, w, top, bot, 0.06), color, px, 0.0)
    p.end()
    return pm


def play(px: int, color: str) -> QPixmap:
    """'play.fill' — the bare triangle, for the taskbar's ⏯ button.

    Not the '.circle.fill' the big transport wears: up there it stands between
    the bare chevrons of ⏮ and ⏭, and a disc among them would read as the odd
    one out. Nudged right of centre for the same reason play_circle is."""
    top, bot = _BOX[1], _BOX[3]
    pm, p = _canvas(px)
    _soft(p, _triangle(px, 0.275, 0.775, top, bot), color, px)
    p.end()
    return pm


def cup(px: int, color: str) -> QPixmap:
    """'cup.and.saucer.fill' — over to the break music.

    Body, handle and saucer are one closed silhouette rather than three loose
    pieces: the handle grows out of the wall instead of hovering beside it, and
    the saucer tapers like a saucer instead of being a bar under the cup."""
    col = QColor(color)
    pm, p = _canvas(px)

    # Handle first, so the body covers where it meets the wall.
    pen = QPen(col)
    pen.setWidthF(0.075 * px)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(0.545 * px, 0.275 * px, 0.30 * px, 0.26 * px),
              -80 * 16, 190 * 16)

    # Cup: straight rim, walls tapering to a rounded base.
    body = QPainterPath(QPointF(0.145 * px, 0.235 * px))
    body.lineTo(0.655 * px, 0.235 * px)
    body.lineTo(0.605 * px, 0.545 * px)
    body.quadTo(0.585 * px, 0.665 * px, 0.475 * px, 0.665 * px)
    body.lineTo(0.325 * px, 0.665 * px)
    body.quadTo(0.215 * px, 0.665 * px, 0.195 * px, 0.545 * px)
    body.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(col)
    p.drawPath(body)

    # Saucer: wider than the cup, thinner at the rim than under the foot.
    saucer = QPainterPath(QPointF(0.06 * px, 0.735 * px))
    saucer.lineTo(0.94 * px, 0.735 * px)
    saucer.quadTo(0.88 * px, 0.855 * px, 0.735 * px, 0.855 * px)
    saucer.lineTo(0.265 * px, 0.855 * px)
    saucer.quadTo(0.12 * px, 0.855 * px, 0.06 * px, 0.735 * px)
    saucer.closeSubpath()
    p.drawPath(saucer)
    p.end()
    return pm


def sliders(px: int, color: str) -> QPixmap:
    """'slider.horizontal.3' — switches the presenter's controls on.

    Three tracks with a knob on each: the knob is a filled pill sitting in a
    gap cut out of its track, the way a real fader looks, not a dot printed on
    top of a line."""
    pm, p = _canvas(px)
    col = QColor(color)
    left, right = 0.075, 0.925
    kw, kh = 0.135, 0.235       # knob size
    for y, knob in ((0.235, 0.66), (0.5, 0.335), (0.765, 0.60)):
        pen = QPen(col)
        pen.setWidthF(_W * px)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawLine(QPointF(left * px, y * px), QPointF(right * px, y * px))
        # Clear a slot, then set the knob into it.
        p.setPen(Qt.PenStyle.NoPen)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.setBrush(Qt.GlobalColor.black)
        slot = QRectF((knob - kw / 2 - 0.045) * px, (y - kh / 2 - 0.03) * px,
                      (kw + 0.09) * px, (kh + 0.06) * px)
        p.drawRoundedRect(slot, 0.07 * px, 0.07 * px)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.setBrush(col)
        p.drawRoundedRect(
            QRectF((knob - kw / 2) * px, (y - kh / 2) * px, kw * px, kh * px),
            kw / 2 * px, kw / 2 * px)
    p.end()
    return pm


def _speaker_body(p: QPainter, px: int, color: str):
    """The cone every speaker glyph starts with: a slab at the back and a
    trapezoid flaring forward, as one closed shape."""
    path = QPainterPath(QPointF(0.10 * px, 0.395 * px))
    path.lineTo(0.245 * px, 0.395 * px)
    path.lineTo(0.435 * px, 0.215 * px)
    path.lineTo(0.435 * px, 0.785 * px)
    path.lineTo(0.245 * px, 0.605 * px)
    path.lineTo(0.10 * px, 0.605 * px)
    path.closeSubpath()
    _soft(p, path, color, px, 0.035)


def _waves(p: QPainter, px: int, color: str, arcs):
    """`arcs` of (radius, span) drawn as the sound coming off the cone."""
    pen = QPen(QColor(color))
    pen.setWidthF(_W * px)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for r, span in arcs:
        p.drawArc(QRectF((0.50 - r) * px, (0.5 - r) * px, 2 * r * px, 2 * r * px),
                  -span * 8, span * 16)


def speaker(px: int, color: str) -> QPixmap:
    """'speaker.wave.2.fill' — full volume."""
    pm, p = _canvas(px)
    _speaker_body(p, px, color)
    _waves(p, px, color, ((0.20, 100), (0.33, 100)))
    p.end()
    return pm


def speaker_low(px: int, color: str) -> QPixmap:
    """'speaker.wave.1.fill' — ducked: the same cone, one wave short."""
    pm, p = _canvas(px)
    _speaker_body(p, px, color)
    _waves(p, px, color, ((0.20, 100),))
    p.end()
    return pm


def xmark_circle(px: int, color: str) -> QPixmap:
    """'xmark.circle' — closes the screen, like the iPad app's dismiss."""
    pm, p = _canvas(px)
    pen = QPen(QColor(color))
    pen.setWidthF(_W * px)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    inset = pen.widthF() / 2
    p.drawEllipse(QRectF(inset, inset, px - 2 * inset, px - 2 * inset))
    for x0, x1 in ((0.345, 0.655), (0.655, 0.345)):
        p.drawLine(QPointF(x0 * px, 0.345 * px), QPointF(x1 * px, 0.655 * px))
    p.end()
    return pm
