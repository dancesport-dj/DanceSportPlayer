"""The Playing-mode panel's small parts: a row as a movable widget, a column
of rows, a wrapping flow layout, the on/off switch and the Esc-aware inline
editor.

Split off player/widgets/play_mode_panel.py, which keeps the panel itself.
"""
from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


def row_box(lyt) -> QWidget:
    """A row of controls as one widget.

    A layout cannot be handed from one parent to another; a widget can. The
    panel's groups have to be movable — down a side column, or dealt across
    the wide strip — so every row that would sit loose in the panel's layout
    is wrapped here first. Margins back to nothing: on a widget of its own a
    layout would otherwise take the style's padding and the row would drift
    away from the ones above and below it."""
    w = QWidget()
    lyt.setContentsMargins(0, 0, 0, 0)
    w.setLayout(lyt)
    return w


class Rows(QWidget):
    """A group of rows that stands as a column or lies down as a line.

    Down the side panel a group is a little stack; in the strip over the decks
    the same group has to be one line high — the strip is worth having only as
    long as it is no deeper than the player beside it. A widget keeps one
    layout for life, so the rows live in an inner body that is thrown away and
    re-laid instead."""

    def __init__(self, rows=(), parent=None):
        super().__init__(parent)
        outer = self._outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._rows = []
        self._wide = False
        self._body = QWidget(self)
        outer.addWidget(self._body)
        self._build()

    def add(self, w: QWidget):
        self._rows.append(w)
        self._build()

    def set_wide(self, on: bool):
        on = bool(on)
        if on != self._wide:
            self._wide = on
            self._build()

    def _build(self):
        body = QWidget(self)
        lyt = QHBoxLayout(body) if self._wide else QVBoxLayout(body)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(8 if self._wide else 6)
        for w in self._rows:
            lyt.addWidget(w)
        old, self._body = self._body, body
        self._outer.replaceWidget(old, body)
        # A widget built parentless starts hidden, and a group already on
        # screen has no show() left to come and reveal it.
        body.show()
        old.setParent(None)
        old.deleteLater()


class FlowLayout(QLayout):
    """Controls set like words in a paragraph: along the line until the edge,
    then on to the next one.

    What the strip has plenty of is width and nothing at all of height, and
    how much of either the panel needs depends on how wide the window is
    opened. Columns have to be dealt in advance and are wrong at every other
    size; a flow finds its own breaks — three lines on a laptop, two across a
    desk monitor — and asks for exactly the height that takes."""

    def __init__(self, parent=None, hspace=18, vspace=6):
        super().__init__(parent)
        self._items = []
        self._h = hspace
        self._v = vspace

    # ── the plumbing QLayout requires ────────────────────────────────────
    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    # ── how tall it comes out at a given width ───────────────────────────
    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._lay(QRect(0, 0, width, 0), place=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._lay(rect, place=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _lay(self, rect: QRect, place: bool) -> int:
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line = eff.x(), eff.y(), 0
        for item in self._items:
            if item.isEmpty():          # a group the settings switched off
                continue
            hint = item.sizeHint()
            # Nothing is ever laid wider than the strip it is in: a row that
            # asks for more than the whole width would otherwise be drawn off
            # the right edge and its last control simply cut in half.
            wide = min(hint.width(), eff.width())
            if x + wide > eff.right() + 1 and line > 0:
                x = eff.x()
                y += line + self._v
                line = 0
            if place:
                item.setGeometry(QRect(QPoint(x, y), QSize(wide, hint.height())))
            x += wide + self._h
            line = max(line, hint.height())
        return y + line - rect.y() + m.bottom()


class Toggle(QAbstractButton):
    """A sliding on/off switch, the kind a phone uses.

    The desk is read at a glance, from a metre away, between two heats, and a
    tick box is four pixels of state. A filled button was worse: on shouted and
    off did not look like a switch at all. A pill with a knob says which of two
    positions it is in even with the colour ignored — the colour is a fraction
    of the area, so a column of them does not compete with the player.

    Same API as the tick box it replaces: isChecked / setChecked / toggled.
    """

    _TRACK_W = 36
    _TRACK_H = 20
    _GAP = 8                        # pill to caption
    _SLIDE_MS = 130

    _OFF_TRACK = QColor("#ccd1d8")
    _ON_TRACK = QColor("#5f9e72")   # muted, not a traffic light
    _RIM = QColor(0, 0, 0, 38)
    _KNOB = QColor("#ffffff")
    _KNOB_OFF_RIM = QColor(0, 0, 0, 46)
    _DISABLED_TEXT = QColor("#a6abb2")

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        # Space on a focused switch would toggle it — the desk's space bar
        # belongs to the transport, not to whatever was clicked last.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._slide = 0.0           # 0 = knob left/off, 1 = knob right/on
        self._ink = None            # caption colour; None = the palette's
        self._anim = QPropertyAnimation(self, b"slide", self)
        self._anim.setDuration(self._SLIDE_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._slide_to)

    # ── the knob's position, animated ────────────────────────────────────────
    def getSlide(self) -> float:
        return self._slide

    def setSlide(self, value: float):
        self._slide = float(value)
        self.update()

    slide = Property(float, getSlide, setSlide)

    def _slide_to(self, on: bool):
        if not self.isVisible():
            # Stored settings are applied while the panel is still being built.
            # There is nothing to watch slide there, and a switch that animates
            # itself on the way onto the screen looks like someone flipped it.
            self.settle()
            return
        self._anim.stop()
        self._anim.setStartValue(self._slide)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def set_ink(self, color: QColor | None):
        """Paint the caption in this colour from now on.

        The caption is painted, not styled, so a dark skin cannot reach it
        through a style sheet — and a palette set by hand is thrown away again
        the next time one is applied to an ancestor."""
        self._ink = color
        self.update()

    def set_scale(self, pct: int):
        """🔘 The pill at the button size from ⚙ Settings → Look."""
        self._TRACK_W = round(type(self)._TRACK_W * pct / 100)
        self._TRACK_H = round(type(self)._TRACK_H * pct / 100)
        self.updateGeometry()
        self.update()

    def settle(self):
        """Put the knob where the state says, with no slide."""
        self._anim.stop()
        self.setSlide(1.0 if self.isChecked() else 0.0)

    # ── drawing ──────────────────────────────────────────────────────────────
    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(self.text_left() + fm.horizontalAdvance(self.text()) + 4,
                     max(self._TRACK_H, fm.height()) + 8)

    def minimumSizeHint(self) -> QSize:
        # The pill must never be squeezed away -- the caption elides instead.
        fm = QFontMetrics(self.font())
        return QSize(self.text_left() + fm.averageCharWidth() * 6,
                     max(self._TRACK_H, fm.height()) + 8)

    def text_left(self) -> int:
        return self._TRACK_W + self._GAP

    def word_left(self) -> int:
        """Where the caption's first word starts, past its leading icon."""
        text = self.text()
        lead = next((i for i, ch in enumerate(text) if ch.isalnum()), 0)
        return self.text_left() + QFontMetrics(self.font()).horizontalAdvance(text[:lead])

    def paintEvent(self, _event):
        pt = QPainter(self)
        pt.setRenderHint(QPainter.RenderHint.Antialiasing)
        live = self.isEnabled()
        top = (self.height() - self._TRACK_H) / 2

        track_col = QColor(self._ON_TRACK if self.isChecked() else self._OFF_TRACK)
        if not live:
            track_col.setAlpha(105)
        pt.setPen(QPen(self._RIM))
        pt.setBrush(track_col)
        pt.drawRoundedRect(QRectF(0.5, top + 0.5, self._TRACK_W - 1,
                                  self._TRACK_H - 1),
                           (self._TRACK_H - 1) / 2, (self._TRACK_H - 1) / 2)

        d = self._TRACK_H - 6
        x = 3 + self._slide * (self._TRACK_W - d - 6)
        pt.setPen(QPen(self._KNOB_OFF_RIM))
        pt.setBrush(self._KNOB if live else QColor("#eef0f2"))
        pt.drawEllipse(QRectF(x, top + 3, d, d))

        pt.setPen((self._ink or self.palette().windowText().color()) if live
                  else self._DISABLED_TEXT)
        room = max(0, self.width() - self.text_left())
        fm = QFontMetrics(self.font())
        pt.drawText(QRectF(self.text_left(), 0, room, self.height()),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, room))


class InlineEdit(QLineEdit):
    """A field that sits over the play-length readout while it is being typed.

    Only exists for Esc: a QLineEdit swallows it silently, and abandoning a
    half-typed length has to be possible without committing something."""

    escaped = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            return
        super().keyPressEvent(event)
