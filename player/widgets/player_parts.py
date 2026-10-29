"""The player cards' small parts: their colours and sizes, the time and takt
formats, the click-to-seek and tempo sliders, and a card row as a movable
widget.

Split off player/widgets/player.py, which keeps the big player card and the
preview overlay.
"""
import math
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QSlider, QStyle, QWidget

# Edge length of the 🖼 cover on the player card — as tall as the title block
# next to it, so switching it on doesn't grow the card.
ART_PX = 76

# Icon colours. The overlay is a light card in the app's blue, the big player a
# dark one — an icon carries its own colour, so it has to be told which world
# it is in (a QSS `color:` no longer reaches it).
OVERLAY_INK = "#1565c0"
CARD_INK = "#cfe0f5"
CARD_FADE = "#d8a0a0"     # fade this song out
CARD_PAUSE = "#9fc3f0"    # over to the pause music
CARD_EXTEND = "#7fd4a0"   # give the pause more time
CARD_CUE = "#f0c674"      # back to 0:00
CARD_PANIC = "#e58080"    # fade to silence and hold
CARD_DIM = "#8fa3c4"      # the fader's own small marks
CARD_GAIN = "#d8b35c"     # the R128 equalization readout

# The card's gold countdown: the pause's own, and the 🐂 wait's, which reads
# on from the 11 px words before it ("PD T60 in 5 s") in their font.
COUNTDOWN_CSS = ("font-size:13px; font-weight:bold; color:#d8b35c;"
                  "font-family:Consolas,monospace;")
WAIT_COUNT_CSS = "font-size:11px; font-weight:bold; color:#d8b35c;"

# One − / + click on the tempo fader, in the slider's own 0.1 % units — the
# finest step the fader has. A takt is hit by tenths, not halves, and the far
# side of the range is reached by holding the button rather than by clicking.
TEMPO_STEP = 1

# One − / + click on the music volume, in per cent. Held, the buttons glide:
# half to full in under three seconds. A figure already known is typed.
VOL_STEP = 2


# ⏱ How a title over an hour reads: "hours" → 1:04:00, "minutes" → 64:00.
# ⚙ Settings → 🔊 Sound & player; one switch for every player time label.
_time_format = "hours"


def set_time_format(fmt: str | None):
    global _time_format
    _time_format = "minutes" if fmt == "minutes" else "hours"


def fmt_ms(ms: int) -> str:
    """Milliseconds → mm:ss for the player's time labels — h:mm:ss from an
    hour on, unless ⚙ Settings asks for minutes past 59."""
    s = max(0, int(ms) // 1000)
    if s >= 3600 and _time_format == "hours":
        return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
    return f"{s // 60:02d}:{s % 60:02d}"


def _round_half_up(x: float) -> int:
    """Round half UP, so a takt of 24.5 shows as T25. Python's built-in round()
    uses banker's rounding (round(24.5) == 24), which would read T24 here."""
    return math.floor(x + 0.5)


def takt_text(x: float) -> str:
    """A takt for the readout: whole where the pitch lands whole, one decimal
    where it does not.

    A heat of a T24 and a T25 title is equalized to their mean, 24.5 — and
    printed as a whole takt that read "T25" on both, which is what a Rumba
    pitched to a hard 25 would say too. The half takt is the answer to "what
    is this heat danced at", so it has to be on the label.
    """
    return f"{_round_half_up(x * 10) / 10:g}"


class _NoWheelSlider(QSlider):
    """A slider the mouse wheel cannot touch.

    Qt lets a wheel notch over a slider move it, without a click, without focus
    — so a roll of the wheel meant for the list behind it lands on the volume,
    the tempo or the seek bar of a song playing to a hall. Ignoring the event
    instead of eating it passes the scroll on to whatever is scrollable above
    (the playing column is inside a scroll area); the fader still takes the
    click and the drag it was aimed at."""

    def wheelEvent(self, event):
        event.ignore()


class ClickSlider(_NoWheelSlider):
    """Slider that jumps straight to the clicked spot (no page-stepping). The
    handle lands under the cursor, so the same press continues as a drag."""

    clickJumped = Signal(int)   # value the user clicked to (fires before drag)

    def set_marks(self, marks, armed=None):
        """Positions (slider values) to draw on the groove — the Paso Doble
        highlights. `armed` is the one that will stop the song; it is drawn
        wider and brighter so it stands out from the others."""
        self._marks = [int(m) for m in (marks or [])]
        self._armed_mark = int(armed) if armed else None
        self.update()

    def _x_for(self, value: int) -> int:
        return QStyle.sliderPositionFromValue(
            self.minimum(), self.maximum(), value, max(1, self.width()))

    def paintEvent(self, event):
        super().paintEvent(event)
        marks = getattr(self, "_marks", None)
        if not marks or self.maximum() <= self.minimum():
            return
        armed = getattr(self, "_armed_mark", None)
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        h = self.height()
        for m in marks or ():
            if not (self.minimum() <= m <= self.maximum()):
                continue
            hot = armed is not None and m == armed
            w = 3 if hot else 2
            p.setBrush(QColor("#ff9800") if hot else QColor("#b0762a"))
            p.drawRoundedRect(self._x_for(m) - w // 2, (h - 10) // 2, w, 10, 1, 1)
        p.end()

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton
                and self.maximum() > self.minimum()):
            val = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                round(event.position().x()), max(1, self.width()))
            self.setValue(val)
            self.clickJumped.emit(val)
        super().mousePressEvent(event)


class TempoSlider(ClickSlider):
    """The ±16 % fader. A click lands the handle on the spot you hit — Qt's own
    page-stepping moves it by exactly 1 %, which turns "put it at +4" into four
    clicks. A double-click anywhere on it snaps back to ±0 % — the same as the
    0 button, but reachable without aiming at a small target while a song
    runs."""

    resetRequested = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._press_at = 0.0

    def mousePressEvent(self, event):
        self._press_at = time.monotonic()
        super().mousePressEvent(event)

    def click_pending(self) -> bool:
        """True while the value change a click just caused could still turn out
        to be the first half of a double-click reset."""
        return ((time.monotonic() - self._press_at) * 1000
                < QApplication.doubleClickInterval())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resetRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def block(layout) -> QWidget:
    """A row of the player card, wrapped in a widget of its own so `set_wide`
    can move it: a layout is re-parented only through a widget."""
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
