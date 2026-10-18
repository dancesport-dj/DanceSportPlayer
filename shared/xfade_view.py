"""🔀 The crossfade drawn the way UltraMixer draws it: the outgoing title's
level falling in red, the incoming one's rising in green, the length below —
and the button its curve is picked with, each curve drawn in its menu.

The curves are `shared.audio.playback.crossfade_levels`, the same ones the player
ramps with — the picture is the fade, not an illustration of one. The box spans
the longest crossfade (10 s), so a short one is a steep cross in the middle and
a long one a slow one across the whole box. In shared/ because both the Playing
panel and the settings' play sets show it.

While a crossfade comes, runs and has just run, a marker walks the box on the
same time axis: in at the left edge the lead before the ramp, on the ramp
while it runs, out at the right edge the lead after it.
"""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from planner import i18n
from planner.playing.play_sets import XFADE_CURVES
from shared.audio.playback import crossfade_levels

_OUT = QColor("#e53935")
_IN = QColor("#43a047")
_BOX = QColor("#1e1f24")
_FRAME = QColor("#4a4d57")
_TEXT = QColor("#f2f2f2")
_OFF = QColor("#9e9e9e")
_MARK = QColor("#ffd54f")
_POINTS = 48
_SPAN_SECS = 10.0    # what the full width of the box stands for
_LABEL_H = 13        # the strip under the curves the length is written in
_ICON = QSize(30, 20)


def lead_secs(secs: float) -> float:
    """How many seconds the box shows either side of a `secs` long ramp."""
    return (_SPAN_SECS - min(max(0.0, secs), _SPAN_SECS)) / 2


def _curve_path(area: QRectF, which: int, curve: str, start: float,
                width: float) -> QPainterPath:
    """The out (0) or in (1) level across `area`, full level at the top: flat
    before and after the ramp, which runs from `start` and is `width` wide."""
    path = QPainterPath()
    path.moveTo(area.left(), area.bottom() - crossfade_levels(0, curve)[which] * area.height())
    for i in range(_POINTS + 1):
        t = i / _POINTS
        level = crossfade_levels(t, curve)[which]
        path.lineTo(QPointF(start + t * width, area.bottom() - level * area.height()))
    path.lineTo(area.right(), area.bottom() - crossfade_levels(1, curve)[which] * area.height())
    return path


class CrossfadeView(QWidget):
    """A small dark box with the two level curves of the crossfade. Around
    one, a marker walks across the box with a dot on each curve."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secs = 0.0
        self._curve = XFADE_CURVES[0]
        self._progress: float | None = None
        self.setFixedSize(self.sizeHint())

    def sizeHint(self) -> QSize:
        return QSize(112, 44)

    def secs(self) -> float:
        return self._secs

    def set_curve(self, curve: str):
        self._curve = curve
        self.update()

    def progress(self) -> float | None:
        return self._progress

    def set_progress(self, t: float | None):
        """Where the marker stands, in ramp lengths: 0 where the ramp starts,
        1 where it ends, below 0 before it and above 1 after it, as far as the
        box reaches. None hides it."""
        if t is not None:
            lead = lead_secs(self._secs) / self._secs if self._secs > 0 else 0.0
            t = min(1.0 + lead, max(-lead, float(t)))
        if t != self._progress:
            self._progress = t
            self.update()

    def set_secs(self, secs: float):
        self._secs = max(0.0, float(secs))
        self.setToolTip(
            i18n.t("🔀 The last %s s of a title and the first %s s of the "
                   "next play together:\nred the one going out, green the "
                   "one coming in.") % (f"{self._secs:g}", f"{self._secs:g}")
            if self._secs > 0 else
            i18n.t("🔀 No crossfade: one title ends, then the next starts."))
        self.update()

    def _span(self, area: QRectF) -> tuple[float, float]:
        """Where the ramp starts and how wide it is: in the middle, as wide as
        the crossfade is long."""
        frac = min(1.0, self._secs / _SPAN_SECS)
        return area.left() + (1.0 - frac) / 2 * area.width(), frac * area.width()

    def _ramp(self, area: QRectF, which: int) -> QPainterPath:
        """One level curve."""
        return _curve_path(area, which, self._curve, *self._span(area))

    def _paint_marker(self, p: QPainter, area: QRectF):
        """Where the crossfade stands: a line down the box and the two levels
        on it, flat either side of the ramp."""
        start, width = self._span(area)
        t = self._progress or 0.0
        # On a whole pixel, so the 2 px line stays crisp instead of smearing.
        x = float(round(min(area.right(), max(area.left(), start + t * width))))
        p.setPen(QPen(_MARK, 2))
        p.drawLine(QPointF(x, area.top() - 2), QPointF(x, area.bottom() + 2))
        p.setPen(Qt.PenStyle.NoPen)
        levels = crossfade_levels(min(1.0, max(0.0, t)), self._curve)
        for level, colour in zip(levels, (_OUT, _IN), strict=True):
            p.setBrush(colour.lighter(140))
            p.drawEllipse(QPointF(x, area.bottom() - level * area.height()), 3.0, 3.0)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(_FRAME, 1))
        p.setBrush(_BOX)
        p.drawRoundedRect(box, 4, 4)
        area = box.adjusted(6, 5, -6, -5 - _LABEL_H)
        on = self._secs > 0
        if on:
            outs, ins = self._ramp(area, 0), self._ramp(area, 1)
        else:
            # A hard cut: the old title at full level to the middle, gone,
            # and the new one there at once. The red drop and the green rise
            # stand side by side; on one x the green hid the red.
            mid = area.center().x()
            drop, rise = mid - 2, mid + 2
            outs, ins = QPainterPath(), QPainterPath()
            outs.moveTo(area.left(), area.top())
            outs.lineTo(drop, area.top())
            outs.lineTo(drop, area.bottom())
            ins.moveTo(rise, area.bottom())
            ins.lineTo(rise, area.top())
            ins.lineTo(area.right(), area.top())
        p.setBrush(Qt.BrushStyle.NoBrush)
        for path, colour in ((outs, _OUT), (ins, _IN)):
            p.setPen(QPen(colour if on else colour.darker(130), 2))
            p.drawPath(path)
        if on and self._progress is not None:
            self._paint_marker(p, area)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(max(7.0, font.pointSizeF() * 0.85))
        p.setFont(font)
        p.setPen(_TEXT if on else _OFF)
        label = QRectF(box.left(), area.bottom() + 2, box.width(), _LABEL_H)
        p.drawText(label, Qt.AlignmentFlag.AlignCenter,
                   # In the locale's digits, as the spin box beside it writes them.
                   self.locale().toString(self._secs, "f", 1) + " s" if on
                   else i18n.t("off"))
        p.end()


# What each curve is called and what it does, for its button.
_CURVE_TEXT = {
    "equal": ("equal power",
              "🔀 Equal power: the two titles add up to one steady level\n"
              "all the way across — right for two unrelated songs."),
    "linear": ("linear",
               "🔀 Linear: two straight lines, the way a plain mixer fader\n"
               "does it — a little quieter in the middle."),
    "scurve": ("S-curve",
               "🔀 S-curve: steady like equal power, but slow off both ends —\n"
               "the new title is barely there at first, the old one lingers."),
}


def _curve_icon(curve: str) -> QIcon:
    """The curve drawn small on the dark box: red out, green in, the ramp
    across the whole width."""
    pix = QPixmap(_ICON)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    box = QRectF(0.5, 0.5, _ICON.width() - 1, _ICON.height() - 1)
    p.setPen(QPen(_FRAME, 1))
    p.setBrush(_BOX)
    p.drawRoundedRect(box, 3, 3)
    area = box.adjusted(3, 3, -3, -3)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for which, colour in ((0, _OUT), (1, _IN)):
        p.setPen(QPen(colour, 1.6))
        p.drawPath(_curve_path(area, which, curve, area.left(), area.width()))
    p.end()
    return QIcon(pix)


class CrossfadeCurveButton(QToolButton):
    """🔀 The crossfade's curve: the button shows the one in use, its menu all
    of them, each drawn and named. One button and not a row of three: the
    Playing panel's column is as wide as its widest row, and three buttons
    made the crossfade that row. `curveChanged` carries the name the sets
    store."""

    curveChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(_ICON)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # Space belongs to the transport, as on the panel's switches.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        group = QActionGroup(self)
        group.setExclusive(True)
        self._actions: dict[str, QAction] = {}
        for curve in XFADE_CURVES:
            act = menu.addAction(_curve_icon(curve), i18n.t(_CURVE_TEXT[curve][0]))
            act.setCheckable(True)
            act.setToolTip(i18n.t(_CURVE_TEXT[curve][1]))
            group.addAction(act)
            self._actions[curve] = act
        self.setMenu(menu)
        self._curve = XFADE_CURVES[0]
        self._actions[self._curve].setChecked(True)
        self._show()
        group.triggered.connect(self._on_picked)

    def curve(self) -> str:
        return self._curve

    def curve_name(self) -> str:
        """The curve as a person calls it, for a toast."""
        return i18n.t(_CURVE_TEXT[self._curve][0])

    def set_curve(self, curve: str):
        """Put the button on `curve`; an unknown name is equal power."""
        if curve not in self._actions:
            curve = XFADE_CURVES[0]
        self._actions[curve].setChecked(True)
        if curve != self._curve:
            self._curve = curve
            self._show()
            self.curveChanged.emit(curve)

    def _on_picked(self, act: QAction):
        self.set_curve(next(c for c, a in self._actions.items() if a is act))

    def _show(self):
        self.setIcon(_curve_icon(self._curve))
        self.setToolTip(i18n.t(_CURVE_TEXT[self._curve][1]))
