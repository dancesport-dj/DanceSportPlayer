"""The Playing-mode panel shown in place of the ConfigPanel during a tournament.

Extracted from dancesport_gui.py (view split).
"""
import logging

from planner.play_sets import (
    _LEN_MAX,
    _LEN_STEP,
    _LEN_TYPED_MAX,
    _LEN_TYPED_MIN,
    parse_play_length,
)

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
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from shared.widgets import (
    _hsep,
)
from player.presenter import (  # auto-resolved
    screen_choices,
)
from player.presenter_theme import DEFAULT_KEY, theme_choices
from planner import i18n
from planner.playlist_text import PlaylistEncodingError, read_playlist_text

log = logging.getLogger("dancesport.gui.play_mode")

# The wide strip's skin — the BigPlayerWidget's own dark chrome, so the panel
# riding in it reads as part of the same machine instead of a light board
# screwed to its side. Kept here rather than imported: the player card sets it
# on itself with an #BigPlayer id rule, and a panel is not that widget.
_STRIP_QSS = (
    # The panel itself must not paint: a widget with a style sheet fills its
    # background from the palette, and the palette here is the window's light
    # grey — which is exactly the pale board this skin exists to get rid of.
    "#PlayModePanel { background:transparent; }"
    "QLabel { color:#dfe8f6; background:transparent; }"
    "QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {"
    " background:#2a3346; color:#e6edf8; border:1px solid #3a4a68;"
    " border-radius:4px; padding:1px 3px; }"
    "QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {"
    " color:#7c8699; background:#232a39; }"
    "QComboBox QAbstractItemView { background:#232a39; color:#e6edf8;"
    " selection-background-color:#1565c0; }"
    "QPushButton { background:#2a3346; color:#cfe0f5; border:1px solid #3a4a68;"
    " border-radius:5px; padding:2px 8px; }"
    "QPushButton:hover { background:#3a4a68; }"
    "QPushButton:pressed { background:#1565c0; }"
    "QToolButton { color:#cfe0f5; background:#2a3346; border:none;"
    " border-radius:4px; padding:2px 5px; }"
    "QToolButton:hover { background:#3a4a68; }")


def _row_box(lyt) -> QWidget:
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


class _Rows(QWidget):
    """A group of rows that stands as a column or lies down as a line.

    Down the side panel a group is a little stack; in the strip over the decks
    the same group has to be one line high — the strip is worth having only as
    long as it is no deeper than the player beside it. A widget keeps one
    layout for life, so the rows live in an inner body that is thrown away and
    re-laid instead."""

    def __init__(self, rows=(), parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
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
        self.layout().replaceWidget(old, body)
        # A widget built parentless starts hidden, and a group already on
        # screen has no show() left to come and reveal it.
        body.show()
        old.setParent(None)
        old.deleteLater()


class _FlowLayout(QLayout):
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


class _Toggle(QAbstractButton):
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

    def settle(self):
        """Put the knob where the state says, with no slide."""
        self._anim.stop()
        self.setSlide(1.0 if self.isChecked() else 0.0)

    # ── drawing ──────────────────────────────────────────────────────────────
    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(self._text_left() + fm.horizontalAdvance(self.text()) + 4,
                     max(self._TRACK_H, fm.height()) + 8)

    def minimumSizeHint(self) -> QSize:
        # The pill must never be squeezed away -- the caption elides instead.
        fm = QFontMetrics(self.font())
        return QSize(self._text_left() + fm.averageCharWidth() * 6,
                     max(self._TRACK_H, fm.height()) + 8)

    def _text_left(self) -> int:
        return self._TRACK_W + self._GAP

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
        room = max(0, self.width() - self._text_left())
        fm = QFontMetrics(self.font())
        pt.drawText(QRectF(self._text_left(), 0, room, self.height()),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, room))


class _InlineEdit(QLineEdit):
    """A field that sits over the play-length readout while it is being typed.

    Only exists for Esc: a QLineEdit swallows it silently, and abandoning a
    half-typed length has to be possible without committing something."""

    escaped = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            return
        super().keyPressEvent(event)


class PlayModePanel(QWidget):
    """Tournament-floor controls: timed play length with auto fade-out.

    Shown instead of the ConfigPanel when the user flips the left-side mode
    switch to ▶ Playing. Everything is built for quick on-the-fly adjustment:
    a big readable length display, a coarse slider plus −5/+5 s nudge buttons,
    and a live countdown of the song currently playing."""

    settingsChanged = Signal()           # any control changed → MainWindow persists
    pdLearnRequested = Signal()          # 🎯 button → mark current playhead as a highlight
    pdClearRequested = Signal()          # ✖ button → forget current track's highlights
    pdEditToggled = Signal(bool)         # ✏️ Edit highlights on/off (suspends the stop)
    pdMarkDeleteRequested = Signal(float)   # ✕ on a mark chip → drop that mark
    announceTestRequested = Signal()     # 🔈 Test → speak a sample announcement
    presenterToggled = Signal(bool)      # 🖥 Presenter screen on/off
    presenterScreenChanged = Signal(int)   # another monitor picked for it
    presenterThemeChanged = Signal(str)    # …and another palette for it
    timetableRequested = Signal()          # 🕒 edit the evening's running order
    partySetToggled = Signal(bool)       # 🎉 party play set on/off
    tournamentSetRequested = Signal()    # 🏆 back to the competition values
    artworkToggled = Signal(bool)        # 🖼 cover art on the player card on/off
    rememberToggled = Signal(bool)       # ↩ remembering where a title stopped on/off
    settingsRequested = Signal()         # ⚙ — only shown in a player-only install

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(640)
        self.setObjectName("PlayModePanel")   # see _STRIP_QSS
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(8, 8, 8, 8)
        lyt.setSpacing(6)

        self._title_row = QLabel("▶  Playing mode")
        self._title_row.setStyleSheet("font-weight:bold; font-size:14px;")
        lyt.addWidget(self._title_row)
        lyt.addWidget(_hsep())

        # ── Timed play: − / + around a big readout, stepping the length in
        # 15 s rungs up to 2:30 and then to "full" (no cut at all). One control
        # instead of a slider plus an on/off box: "full" IS the off position.
        self._secs = self._load_secs(settings)
        len_row = QHBoxLayout()
        len_row.setSpacing(6)
        self.len_minus = QPushButton("−")
        self.len_plus = QPushButton("+")
        for b in (self.len_minus, self.len_plus):
            b.setFixedSize(46, 46)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # Scoped by type: a bare style would size the tooltips too.
            b.setStyleSheet("QPushButton{font-size:22px; font-weight:bold;}")
        self.len_minus.setToolTip(i18n.t("Shorter by %s s") % _LEN_STEP)
        self.len_plus.setToolTip(
            i18n.t("Longer by %s s — past %s the title plays to its end")
            % (_LEN_STEP, f"{_LEN_MAX // 60}:{_LEN_MAX % 60:02d}"))
        self.len_minus.clicked.connect(lambda: self._step_len(-1))
        self.len_plus.clicked.connect(lambda: self._step_len(+1))
        len_row.addWidget(self.len_minus)
        # Big mm:ss display — readable from a standing position at the desk.
        # Styled by its name only: the tooltip is a QLabel too, and a bare
        # style would put the explanation on screen in 34 px bold.
        self.len_lbl = QLabel("")
        self.len_lbl.setObjectName("playLen")
        self.len_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.len_lbl.setStyleSheet(
            "QLabel#playLen{font-size:34px; font-weight:bold; color:#1565c0;"
            "font-family:Consolas,monospace;}")
        self.len_lbl.setToolTip(
            i18n.t("Play length per song: each song is stopped after this time,\n"
                   "ramping down over the fade time first. Steps of %s s\n"
                   "up to %s; one step further is\n"
                   "'full' — no cut, every title plays to its own end.\n\n"
                   "Double-click to type an exact length (e.g. 1:37).")
            % (_LEN_STEP, f"{_LEN_MAX // 60}:{_LEN_MAX % 60:02d}"))
        # The ladder covers the usual lengths in two taps; typing covers the
        # ones between its rungs, which −/+ can never reach.
        self.len_lbl.setCursor(Qt.CursorShape.IBeamCursor)
        self.len_lbl.mouseDoubleClickEvent = self._on_len_typed
        self._len_edit: _InlineEdit | None = None    # built on first use
        len_row.addWidget(self.len_lbl, stretch=1)
        len_row.addWidget(self.len_plus)
        lyt.addWidget(_row_box(len_row))

        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel("Fade-out:"))
        # Half seconds: at 3 s a fade is already gentle, and the difference
        # between 1.5 and 2 is audible on the floor — whole seconds are too
        # coarse a ladder down at the short end.
        self.fade_spin = QDoubleSpinBox()
        self.fade_spin.setRange(0, 10)
        self.fade_spin.setDecimals(1)
        self.fade_spin.setSingleStep(0.5)
        self.fade_spin.setSuffix(" s")
        self.fade_spin.setValue(float(settings.get("fade_secs", 3)))
        self.fade_spin.setToolTip("Volume ramps to 0 over the last N seconds,\n"
                                  "in steps of half a second")
        fade_row.addWidget(self.fade_spin)
        fade_row.addStretch(1)
        lyt.addWidget(_row_box(fade_row))

        lyt.addWidget(_hsep())

        # ── Paso Doble: stop after a highlight instead of the fade ──
        self.pd_check = _Toggle("🐂  Stop Paso Doble after highlight")
        self.pd_check.setToolTip(
            "A Paso Doble under this switch is never faded out and ignores\n"
            "the play length — it is danced to its choreographed highlights.\n"
            "the highlights (crescendo → dramatic drop) are auto-detected\n"
            "in the background and the music shuts off at once when the\n"
            "chosen one (its closing gong) hits. A highlight detection\n"
            "can't pin down falls back to the standard phrasing\n"
            "(1st ≈ 0:45, 2nd ≈ 1:15).\n\n"
            "Off, a Paso Doble is an ordinary title: the play length cuts it\n"
            "and the fade takes it out, like every other dance.")
        self.pd_check.setChecked(bool(settings.get("pd_highlight_stop", True)))
        lyt.addWidget(self.pd_check)

        # Everything in this box belongs to the switch: which highlight stops
        # the dance and the marking tools. With the switch off none of it does
        # anything, and the desk column is the one place in the app where a
        # screenful of dead controls costs a scroll mid-round. The wait after
        # the call is NOT in here — it is about how a PD starts, not how it
        # ends, and it applies just as much with the stop switched off.
        self.pd_sub_box = _Rows()
        lyt.addWidget(self.pd_sub_box)

        pd_row = QHBoxLayout()
        pd_row.addWidget(QLabel("Stop after highlight:"))
        self.pd_spin = QSpinBox()
        self.pd_spin.setRange(1, 3)
        self.pd_spin.setValue(max(1, min(3, int(settings.get("pd_highlight_n", 2)))))
        self.pd_spin.setToolTip(
            "Which highlight ends the Paso Doble — usually the 2nd,\n"
            "in rare cases the 3rd.")
        pd_row.addWidget(self.pd_spin)
        pd_row.addStretch(1)
        self.pd_sub_box.add(_row_box(pd_row))

        # Manual learning: click exactly when a highlight hits while the PD plays.
        pd_learn_row = QHBoxLayout()
        self.pd_learn_btn = QPushButton("🎯  Mark highlight now")
        self.pd_learn_btn.setFixedHeight(26)
        self.pd_learn_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_learn_btn.setToolTip(
            "While a Paso Doble plays, click exactly when a highlight (the\n"
            "dramatic gong / drop) hits to teach its position. Click again at\n"
            "the 2nd / 3rd highlight. Manually learned highlights are flagged\n"
            "in the database and are never overwritten by 🐂 auto-detection.")
        self.pd_learn_btn.clicked.connect(self.pdLearnRequested.emit)
        pd_learn_row.addWidget(self.pd_learn_btn, stretch=1)
        self.pd_clear_btn = QPushButton("✖")
        self.pd_clear_btn.setFixedHeight(26)
        self.pd_clear_btn.setFixedWidth(30)
        self.pd_clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_clear_btn.setToolTip(
            "Forget the current track's learned highlights\n"
            "(falls back to 🐂 auto-detection on the next play).")
        self.pd_clear_btn.clicked.connect(self.pdClearRequested.emit)
        pd_learn_row.addWidget(self.pd_clear_btn)
        self.pd_sub_box.add(_row_box(pd_learn_row))

        # ✏️ Edit mode: while it's on nothing cuts the Paso Doble, so a later
        # crash can actually be reached, heard and marked. Without it the very
        # mark you just set becomes the stop and the title ends on the spot.
        self.pd_edit_btn = QPushButton("✏️  Edit highlights")
        self.pd_edit_btn.setCheckable(True)
        self.pd_edit_btn.setFixedHeight(26)
        self.pd_edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pd_edit_btn.setToolTip(
            "Pause the music and suspend the highlight stop, so the whole Paso\n"
            "Doble is reachable while you set its marks: scrub to a crash, ⏯ to\n"
            "listen, hit 🎯, delete a wrong mark with its ✕. Marking within 3 s\n"
            "of an existing mark moves that one instead of adding a fourth.\n\n"
            "Leaving edit mode arms the stop again and PAUSES at it the next\n"
            "time it's reached, so you can hear whether the mark sits right.")
        self.pd_edit_btn.setStyleSheet(
            "QPushButton:checked { background:#ff9800; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.pd_edit_btn.toggled.connect(self._on_pd_edit)
        self.pd_sub_box.add(self.pd_edit_btn)

        # Mark chips, only while editing: "0:44 ✕  1:15 ✕  2:01 ✕".
        self.pd_marks_box = QWidget()
        self.pd_marks_lyt = QHBoxLayout(self.pd_marks_box)
        self.pd_marks_lyt.setContentsMargins(0, 0, 0, 0)
        self.pd_marks_lyt.setSpacing(4)
        self.pd_marks_box.setVisible(False)
        self.pd_sub_box.add(self.pd_marks_box)

        # The couples walk on and take position when the dance is called — a
        # Paso Doble that starts on the word is danced from the wrong bar.
        pd_call_row = QHBoxLayout()
        pd_call_row.addWidget(QLabel("Start after:"))
        self.pd_delay_spin = QSpinBox()
        self.pd_delay_spin.setRange(0, 60)
        self.pd_delay_spin.setSuffix(" s")
        self.pd_delay_spin.setValue(
            max(0, min(60, int(settings.get("pd_start_delay", 0)))))
        self.pd_delay_spin.setToolTip(
            "Hold a Paso Doble back this long before the music starts, so the\n"
            "couples reach their position after the dance is called. Applies\n"
            "to every way a PD is started — ▶, a double-click, auto-advance.\n"
            "0 s = start at once, like every other dance.\n\n"
            "With 🔈 Announce next dance on, the app makes the call and the\n"
            "seconds run from it; off, the hall's announcer does and the wait\n"
            "runs silently — counted down on this panel either way.")
        pd_call_row.addWidget(self.pd_delay_spin)
        pd_call_row.addStretch(1)
        lyt.addWidget(_row_box(pd_call_row))

        lyt.addWidget(_hsep())

        # ── Auto-advance: heat flow without touching the mouse ──
        self.advance_check = _Toggle("⏭  Auto-advance to next song")
        self.advance_check.setToolTip(
            "When a song ends (fade-out or natural end), pause for the\n"
            "configured time, then play the next song row of the deck —\n"
            "so a whole round runs through hands-free. Stops at the end\n"
            "of the round (🏁) — the next round is started manually.\n\n"
            "Switching it off stops 🔈 Announce next dance too: nothing\n"
            "should call a dance that nothing then plays. Switching it\n"
            "back on restores the announcement you had.\n\n"
            "Every playlist keeps its own answer: this is the one of the\n"
            "list last clicked, the same as the ⏭/✋ under that deck.")
        self.advance_check.setChecked(bool(settings.get("auto_advance", True)))
        lyt.addWidget(self.advance_check)

        # Hangs off auto-advance: without it the last title is followed by
        # nothing anyway, so there is no end to run past.
        self.repeat_check = _Toggle("🔁  Start again at the end")
        self.repeat_check.setToolTip(
            "When the LAST title of the list has finished, carry on with its\n"
            "first one instead of stopping — so a party keeps its music going\n"
            "without anybody at the desk.\n\n"
            "The 🏁 end of a round is untouched: that one happens between\n"
            "rounds, and still waits for the operator.\n\n"
            "Needs ⏭ auto-advance.")
        self.repeat_check.setChecked(bool(settings.get("repeat_list", False)))
        lyt.addWidget(self.repeat_check)

        pause_row = QHBoxLayout()
        # The caption IS the switch — unchecked, songs run back to back and the
        # configured time stays in the box for switching back.
        self.pause_check = _Toggle("Pause between songs:")
        self.pause_check.setToolTip(
            "Off: the next song starts the moment the current one ends, with\n"
            "no filler music and no announcement. The configured time is kept\n"
            "for switching back.\n\n"
            "Needs ⏭ auto-advance — without it the next song waits for the\n"
            "operator anyway, so there is no gap to fill.")
        self.pause_check.setChecked(bool(settings.get("pause_enabled", False)))
        self.pause_check.toggled.connect(self._on_pause_on)
        pause_row.addWidget(self.pause_check)
        self.pause_spin = QSpinBox()
        self.pause_spin.setRange(0, 120)
        self.pause_spin.setSuffix(" s")
        self.pause_spin.setValue(int(settings.get("pause_secs", 15)))
        self.pause_spin.setToolTip(
            "Time for the couples to change / catch breath before the next song")
        pause_row.addWidget(self.pause_spin)
        pause_row.addStretch(1)
        # Kept, because the whole row leaves the panel together with the 🔁
        # tick above it when there is no auto-advance to hang a pause on.
        self.pause_row_box = _row_box(pause_row)
        lyt.addWidget(self.pause_row_box)

        # Optional filler music during the pause, faded in and out. Stored as
        # a list of titles (rotated pause after pause); legacy settings hold
        # a single path string.
        raw = settings.get("pause_music", "") or []
        if isinstance(raw, str):
            raw = [raw] if raw else []
        self._pause_music = [str(p) for p in raw]
        # In their own boxes so the whole row greys out with the pause, labels
        # and all — Qt disables children with their parent.
        # Both boxes live in one folder so the pair disappears together when
        # there is no pause to fill.
        self.pause_sub_box = _Rows()
        lyt.addWidget(self.pause_sub_box)

        self.pause_music_box = QWidget()
        pm_row = QHBoxLayout(self.pause_music_box)
        pm_row.setContentsMargins(0, 0, 0, 0)
        pm_row.setSpacing(4)
        pm_row.addWidget(QLabel("Pause music:"))
        self.pause_music_lbl = QLabel("")
        self.pause_music_lbl.setStyleSheet("color:#555; font-style:italic;")
        self.pause_music_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        pm_row.addWidget(self.pause_music_lbl, stretch=1)
        pm_pick = QToolButton()
        pm_pick.setText("📂")
        pm_pick.setToolTip(
            "Choose one or more titles — or an .m3u playlist — that play\n"
            "softly during the pause between songs, faded in at the start\n"
            "and out before the next song. Several titles rotate: a title\n"
            "keeps playing pause after pause until it ends, then the next\n"
            "one takes over.")
        pm_pick.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pm_pick.clicked.connect(self._pick_pause_music)
        pm_row.addWidget(pm_pick)
        pm_clear = QToolButton()
        pm_clear.setText("✕")
        pm_clear.setToolTip("No pause music")
        pm_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pm_clear.clicked.connect(lambda: self._set_pause_music([]))
        pm_row.addWidget(pm_clear)
        self.pause_sub_box.add(self.pause_music_box)
        self._refresh_pause_music_lbl()

        # Filler plays quieter than the dance music — it's background, not
        # program. Percentage of the normal playback volume.
        self.pause_vol_box = QWidget()
        pv_row = QHBoxLayout(self.pause_vol_box)
        pv_row.setContentsMargins(0, 0, 0, 0)
        pv_row.addWidget(QLabel("Pause music volume:"))
        self.pause_vol_spin = QSpinBox()
        self.pause_vol_spin.setRange(10, 100)
        self.pause_vol_spin.setSingleStep(5)
        self.pause_vol_spin.setSuffix(" %")
        self.pause_vol_spin.setValue(
            max(10, min(100, int(settings.get("pause_music_vol", 10)))))
        self.pause_vol_spin.setToolTip(
            "How loud the pause music plays, relative to the normal\n"
            "playback volume — kept lower so it stays in the background.")
        pv_row.addWidget(self.pause_vol_spin)
        pv_row.addStretch(1)
        self.pause_sub_box.add(self.pause_vol_box)

        # Spoken cue for the couples, timed to land just before the pause ends.
        self.announce_check = _Toggle("🔈  Announce next dance")
        self.announce_check.setToolTip(
            "Say the next dance out loud shortly before the pause ends\n"
            "(\"Nächster Tanz: Langsamer Walzer\"). Without a pause the dance\n"
            "is named as the title starts instead (\"Langsamer Walzer\") —\n"
            "over the first bars or before them, whichever the pair below\n"
            "is set to.")
        self.announce_check.setChecked(bool(settings.get("announce_next", False)))
        # What ✋ Manual switched off, so ⏭ Auto can put it back. Deliberately
        # not persisted: a session that ends in Manual starts in Manual, and
        # there is nothing left to restore.
        self._announce_before_manual = False
        lyt.addWidget(self.announce_check)

        # Which voice, and the two "…with" extras: all of it is how the
        # announcement sounds, so none of it is worth a line when nothing is
        # announced.
        self.announce_sub_box = _Rows()
        lyt.addWidget(self.announce_sub_box)

        # Where the spoken dance sits against the first bar. Directly under
        # the switch that makes the call at all: it is a question about the
        # announcement, not about auto-advance, which is where it used to
        # sit. Only without a pause — with one the call runs in the pause and
        # the music already waits for its last word.
        when_col = QVBoxLayout()
        when_col.setSpacing(1)
        # Short on purpose: the panel is 250px wide at its narrowest and the
        # reasons are in the tooltips, which have all the room they want.
        self.announce_over_radio = QRadioButton("over the first bars")
        self.announce_wait_radio = QRadioButton("before the music starts")
        self.announce_over_radio.setToolTip(
            "The dance is named while the music is already running, ducked\n"
            "under the voice — the hall hears both at once and the title\n"
            "loses none of its first bars.\n\n"
            "Applies where a title names its dance as it starts: 🔈 Announce\n"
            "next dance on, and no pause between songs (a pause has a gap of\n"
            "its own for the call).")
        self.announce_wait_radio.setToolTip(
            "The dance is called into silence and the music follows when the\n"
            "voice is done — the hall hears WHICH dance before it starts, at\n"
            "the cost of a second or two of quiet.\n\n"
            "Applies where a title names its dance as it starts: 🔈 Announce\n"
            "next dance on, and no pause between songs (a pause has a gap of\n"
            "its own for the call).")
        for r in (self.announce_over_radio, self.announce_wait_radio):
            when_col.addWidget(r)
        self.announce_wait_radio.setChecked(
            bool(settings.get("announce_wait", False)))
        self.announce_over_radio.setChecked(
            not self.announce_wait_radio.isChecked())
        self.announce_wait_radio.toggled.connect(
            lambda _: self.settingsChanged.emit())
        self.announce_when_box = _row_box(when_col)
        self.announce_sub_box.add(self.announce_when_box)

        ann_row = QHBoxLayout()
        ann_row.setSpacing(4)
        self.announce_takt_check = _Toggle("…with takt")
        self.announce_takt_check.setToolTip(
            "Append the bars per minute (\"…, 29 Takt\") — useful in training,\n"
            "usually just noise on a tournament floor.\n\n"
            "Ticking this hands the WHOLE announcement to the Windows voice:\n"
            "the recordings have clips for the dances and the heats, none for\n"
            "a tempo, and two voices in one announcement sound like two\n"
            "announcers.")
        self.announce_takt_check.setChecked(bool(settings.get("announce_takt", False)))
        self.announce_takt_check.setEnabled(self.announce_check.isChecked())
        ann_row.addWidget(self.announce_takt_check, stretch=1)
        self.announce_heat_check = _Toggle("…with heat")
        self.announce_heat_check.setToolTip(
            "Append the heat number (\"…, Heat 3\") — the couples hear which\n"
            "heat they are about to dance.\n\n"
            "Only a round grid has heats: a theme list, the warm-up and a free\n"
            "running order are announced without one. Recorded for heats 1-8;\n"
            "beyond that the number is left out.")
        self.announce_heat_check.setChecked(bool(settings.get("announce_heat", False)))
        self.announce_heat_check.setEnabled(self.announce_check.isChecked())
        ann_row.addWidget(self.announce_heat_check, stretch=1)
        self.announce_test_btn = QPushButton("🔈  Test")
        self.announce_test_btn.setFixedHeight(26)
        self.announce_test_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.announce_test_btn.setToolTip(
            "Speak a sample announcement now — check voice and level\n"
            "before the round, not during it.")
        self.announce_test_btn.clicked.connect(self.announceTestRequested.emit)
        ann_row.addWidget(self.announce_test_btn)
        self.announce_sub_box.add(_row_box(ann_row))

        # Which of the recorded voices reads the announcement.
        voice_row = QHBoxLayout()
        voice_row.setSpacing(4)
        voice_row.addWidget(QLabel("Voice:"))
        self.announce_voice_combo = QComboBox()
        self.announce_voice_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.announce_voice_combo.setToolTip(
            "Which recorded voice announces the dance. “Mixed” alternates them\n"
            "— she, he, she, he — so an evening doesn't run on a single voice.\n\n"
            "A dance that was never recorded is not announced.")
        for label, key in (("Female", "female"), ("Male", "male"),
                           ("Mixed", "random")):
            self.announce_voice_combo.addItem(label, key)
        want = str(settings.get("announce_voice", "female"))
        self.announce_voice_combo.setCurrentIndex(
            max(0, self.announce_voice_combo.findData(want)))
        self.announce_voice_combo.setEnabled(self.announce_check.isChecked())
        voice_row.addWidget(self.announce_voice_combo, stretch=1)
        self.announce_sub_box.add(_row_box(voice_row))

        lyt.addWidget(_hsep())

        # ── Loudness equalization (EBU R128) ──
        self.loudness_check = _Toggle("🔊  Equalize volume (R128)")
        self.loudness_check.setToolTip(
            "Compensate loudness differences between tracks on playback:\n"
            "each song's measured EBU R128 loudness is pulled towards a common\n"
            "target, so quiet old recordings and loud modern masters play at\n"
            "a similar level. Needs 📊 Analyze loudness (⚙ Settings) first.")
        self.loudness_check.setChecked(bool(settings.get("loudness_eq", True)))
        # The box stays clickable so the user can always toggle their intent; whether
        # equalization is ACTUALLY applied is gated separately on `_loudness_available`
        # (set once measured loudness exists). Disabling it would trap a checked box.
        self._loudness_available = False
        lyt.addWidget(self.loudness_check)

        # ── 🖼 Cover art on the player card ──
        self.artwork_check = _Toggle("🖼  Show artwork")
        self.artwork_check.setToolTip(
            "Show a cover picture next to the title on the player.\n"
            "The playlist's own image is used when it has one (an #EXTIMG line\n"
            "in the .m3u or a cover file beside it), otherwise the track's\n"
            "embedded artwork, otherwise a plain ♪ tile.")
        self.artwork_check.setChecked(bool(settings.get("show_artwork", True)))
        lyt.addWidget(self.artwork_check)

        # ── ▶️ What a double-click on a title in the deck does ──
        self.dblclick_check = _Toggle("▶️  Double-click starts the title")
        self.dblclick_check.setToolTip(
            "On: a double-click in a deck puts the title on the speakers at\n"
            "once — what a party wants.\n"
            "Off: it is only CUED on the player (loaded, shown, silent) and ⏯\n"
            "starts it — what a heat wants, where the music begins when the\n"
            "couples are on the floor and not a moment earlier.\n\n"
            "Part of the play sets: 🏆 tournament switches it off, 🎉 party on.")
        self.dblclick_check.setChecked(bool(settings.get("dblclick_plays", False)))
        lyt.addWidget(self.dblclick_check)

        # ── ↩ Pick a title up where it was left ──
        self.remember_check = _Toggle("↩  Remember where a title stopped")
        self.remember_check.setToolTip(
            "There is one player for every deck, so leaving a title to hear\n"
            "another one loses your place in it. On: the spot a title stopped\n"
            "at is kept and it starts there again — marked by a tick on the\n"
            "seek bar and by ↩ mm:ss on its row.\n\n"
            "A title played to its end keeps no mark, and the marks are\n"
            "forgotten when the app closes.")
        self.remember_check.setChecked(bool(settings.get("remember_pos", False)))
        lyt.addWidget(self.remember_check)

        lyt.addWidget(_hsep())

        # ── 🏆 Tournament play set: the competition values in one press ──
        # Above the party button on purpose: it is the one you reach for when a
        # party list has just left the panel somewhere else, and the pair reads
        # as what it is — tournament above, party below.
        self.tournament_btn = QPushButton("🏆  Tournament set")
        self.tournament_btn.setCheckable(True)   # lit while the panel is on it
        self.tournament_btn.setFixedHeight(26)
        self.tournament_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tournament_btn.setToolTip(
            "Put the panel back on the competition values in one go: the\n"
            "configured play length, no pause between songs, no auto-advance\n"
            "and no spoken announcement — the settings a heat is run with.\n\n"
            "Lit gold while the panel stands on those values, the way 🎉 is lit\n"
            "purple during a party. Switches the 🎉 party set off. What exactly\n"
            "it sets is yours to change: ⚙ Settings → 🎛 Play sets.")
        self.tournament_btn.setStyleSheet(
            "QPushButton:checked { background:#b8860b; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.tournament_btn.clicked.connect(self.tournamentSetRequested.emit)
        lyt.addWidget(self.tournament_btn)

        # ── 🎉 Party play set: the settings a party needs at once ──
        self.party_btn = QPushButton("🎉  Party set")
        self.party_btn.setCheckable(True)
        self.party_btn.setFixedHeight(26)
        self.party_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.party_btn.setToolTip(
            "Switch the tournament settings over to party playing in one go:\n"
            "every title to its full length, auto-advance to the next one, no\n"
            "pause (so no break music) in between and no spoken announcement.\n\n"
            "Applied by itself as soon as you play from the 🤸 Eintanzen /\n"
            "party list, and switched back when a tournament deck takes over —\n"
            "a toast says what changed either way. What exactly it sets is\n"
            "yours to change: ⚙ Settings → 🎛 Play sets.")
        self.party_btn.setStyleSheet(
            "QPushButton:checked { background:#7b1fa2; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.party_btn.toggled.connect(self.partySetToggled.emit)
        lyt.addWidget(self.party_btn)

        # ── 🖥 Presenter screen: what's playing + what's next, hall-sized ──
        pres_row = QHBoxLayout()
        pres_row.setSpacing(4)
        self.presenter_btn = QPushButton("🖥  Presenter")
        self.presenter_btn.setCheckable(True)
        self.presenter_btn.setFixedHeight(26)
        self.presenter_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presenter_btn.setToolTip(
            "Open a second, full-screen window showing only the running title\n"
            "with its dance and the next three songs — big and plain, for a\n"
            "beamer or a monitor turned towards the floor. Pick the screen\n"
            "next to it; Esc (or this button) closes it again.")
        self.presenter_btn.setStyleSheet(
            "QPushButton:checked { background:#1565c0; color:white;"
            " font-weight:bold; border-radius:3px; }")
        self.presenter_btn.toggled.connect(self.presenterToggled.emit)
        pres_row.addWidget(self.presenter_btn, stretch=1)
        self.presenter_screen_combo = QComboBox()
        self.presenter_screen_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presenter_screen_combo.setToolTip(
            "Which monitor the presenter screen fills. Same screen as the app\n"
            "is fine too — double-click the presenter window to shrink it back\n"
            "out of full screen.")
        pres_row.addWidget(self.presenter_screen_combo)
        lyt.addWidget(_row_box(pres_row))

        # …and which palette it wears. A hall wants the black screen; a wedding
        # wants the creme one, and the switch has to be reachable on the night.
        theme_row = QHBoxLayout()
        theme_row.setSpacing(4)
        theme_lbl = QLabel("🎨  Theme")
        theme_lbl.setToolTip(
            "The colours of the presenter screen. 'Default' is the black hall\n"
            "display; 'Light' is creme paper with warm brown type and rose\n"
            "gold for the next dance — made for a lit room, where black on a\n"
            "beamer is just a grey rectangle. Applies straight away.")
        self.presenter_theme_combo = QComboBox()
        self.presenter_theme_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presenter_theme_combo.setToolTip(theme_lbl.toolTip())
        for key, label in theme_choices():
            self.presenter_theme_combo.addItem(label, key)
        want = str(settings.get("presenter_theme", DEFAULT_KEY))
        self.presenter_theme_combo.setCurrentIndex(
            max(0, self.presenter_theme_combo.findData(want)))
        self.presenter_theme_combo.currentIndexChanged.connect(
            lambda _i: self.presenterThemeChanged.emit(self.presenter_theme()))
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.presenter_theme_combo, stretch=1)
        self.timetable_btn = QPushButton("🕒")
        self.timetable_btn.setFixedSize(30, 24)
        self.timetable_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timetable_btn.setToolTip(
            "The evening's running order — when dinner is, when the opening\n"
            "dance is — as a second page on the presenter screen.\n\n"
            "Type it here; on the screen itself, T (or its 🕒 button) switches\n"
            "to it, and it can fade between the two pages by itself.")
        self.timetable_btn.clicked.connect(self.timetableRequested.emit)
        theme_row.addWidget(self.timetable_btn)
        lyt.addWidget(_row_box(theme_row))

        # The monitor the presenter is wanted on, by name. It outlives an
        # unplug: the combo falls back to what is there, and goes back to
        # this one as soon as it is connected again.
        self._screen_name = str(settings.get("presenter_screen_name", ""))
        self._fill_screens(int(settings.get("presenter_screen", 0)))
        self.presenter_screen_combo.currentIndexChanged.connect(
            self._on_screen_picked)
        self.presenter_screen_combo.currentIndexChanged.connect(
            self.presenterScreenChanged.emit)
        # A beamer usually gets plugged in AFTER the app is started — keep the
        # list in step with what's actually connected.
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(lambda _s: self._fill_screens())
            app.screenRemoved.connect(lambda _s: self._fill_screens())

        # ── ☀ Hold the screensaver off while the desk is working ──
        self.awake_check = _Toggle("☀  Keep the screen awake")
        self.awake_check.setToolTip(
            "Keep the screensaver and the display timeout off while music is\n"
            "playing or the presenter screen is open.\n\n"
            "The system counts idle time from the mouse and the keyboard,\n"
            "never from the speakers — so an hour of music with nobody touching\n"
            "the desk blanks the screen mid-heat, the beamer included. It goes\n"
            "back to its normal timeouts as soon as neither is running.")
        self.awake_check.setChecked(bool(settings.get("keep_awake", True)))
        lyt.addWidget(self.awake_check)

        lyt.addWidget(_hsep())

        # ── Live countdown of the current song ──
        self.countdown_lbl = QLabel("")
        self.countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_lbl.setStyleSheet(
            "font-size:22px; font-family:Consolas,monospace; color:#444;")
        self._countdown_text: str | None = None   # last set_countdown text
        lyt.addWidget(self.countdown_lbl)

        lyt.addStretch(1)

        # ── ⚙ Settings, in the corner the ConfigPanel keeps it ──
        # A player-only install never shows the planning panel, so its gear is
        # out of reach and the app mode could not be changed back. This one sits
        # in the same spot of the same left panel — the hand goes to the same
        # place. Hidden in every other mode: there the planning gear is the one.
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(26, 26)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_btn.setToolTip(
            "Settings — app mode, library paths & analysis")
        self.settings_btn.clicked.connect(self.settingsRequested)
        self._gear_box = QWidget()
        glyt = QVBoxLayout(self._gear_box)
        glyt.setContentsMargins(0, 0, 0, 0)
        glyt.setSpacing(4)
        glyt.addWidget(_hsep())
        gear_row = QHBoxLayout()
        gear_row.setContentsMargins(0, 0, 0, 0)
        gear_row.addStretch(1)
        gear_row.addWidget(self.settings_btn)
        glyt.addLayout(gear_row)
        self._gear_box.setVisible(False)
        lyt.addWidget(self._gear_box)

        self.fade_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.pd_check.toggled.connect(self._on_pd_on)
        self.pd_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.pd_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.pd_delay_spin.valueChanged.connect(
            lambda _: self.settingsChanged.emit())
        self.advance_check.toggled.connect(lambda _: self._sync_pause_row())
        self.advance_check.toggled.connect(lambda _: self.settingsChanged.emit())
        # `clicked`, not `toggled`: only a person switching to Manual means
        # "stop everything automatic". A play set or a restored setting sets
        # this box too, and those carry their own announce value.
        self.advance_check.clicked.connect(self._follow_advance_with_announce)
        self.repeat_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.pause_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.pause_vol_spin.valueChanged.connect(lambda _: self.settingsChanged.emit())
        self.announce_check.toggled.connect(self.announce_sub_box.setVisible)
        self.announce_check.toggled.connect(self.announce_takt_check.setEnabled)
        self.announce_check.toggled.connect(self.announce_heat_check.setEnabled)
        self.announce_check.toggled.connect(self.announce_voice_combo.setEnabled)
        self.announce_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.announce_takt_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.announce_heat_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.announce_voice_combo.currentIndexChanged.connect(
            lambda _: self.settingsChanged.emit())
        self.loudness_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.awake_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.artwork_check.toggled.connect(self.artworkToggled.emit)
        self.artwork_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.dblclick_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self.remember_check.toggled.connect(self.rememberToggled.emit)
        self.remember_check.toggled.connect(lambda _: self.settingsChanged.emit())
        self._refresh_len_lbl()
        self._sync_pause_row()
        self.pd_sub_box.setVisible(self.pd_check.isChecked())
        self.announce_sub_box.setVisible(self.announce_check.isChecked())
        self.set_voice_advanced_shown(
            bool(settings.get("announce_advanced", False)))

        # Everything above went straight into the panel's own layout, one
        # group under the next, because down a side panel that is the only
        # shape there is. Cut at the rules, those groups become blocks that
        # can just as well be dealt out side by side — which is what the wide
        # player strip does with them: it has width to spare and no height.
        self._sections = self._harvest_sections()
        self._wide = False
        self._parked = set()    # rows this shape has no place for
        self._body = QWidget()
        self.layout().addWidget(self._body)
        self._relayout()

    def _harvest_sections(self):
        """Take the panel apart at its ─── rules.

        Each run of controls between two of them is one group the eye already
        reads as a unit; kept whole, a group can be stacked or laid on its
        side without anything drifting away from its own label. What comes
        back is the rows themselves, not a box around them — the box belongs
        to a shape, and the panel has two: (rule above it, its rows, does it
        soak up spare height)."""
        lyt = self.layout()
        sections = []
        sep = None
        rows = []
        grow = False

        def _close():
            if rows:
                sections.append((sep, list(rows), grow))

        while lyt.count():
            item = lyt.takeAt(0)
            w = item.widget()
            if isinstance(w, QFrame) and w.frameShape() == QFrame.Shape.HLine:
                _close()
                sep = w
                rows, grow = [], False
            elif w is not None:
                # Parked on the panel while it has no body: a widget with no
                # parent at all is a window of its own on the desktop.
                w.setParent(self)
                rows.append(w)
            elif item.spacerItem() is not None:   # the stretch pinning ⚙ down
                grow = True
        _close()
        return sections

    def set_wide(self, on: bool):
        """Lay the panel out in columns instead of down one — how it stands
        when it rides in the wide player strip above the decks."""
        on = bool(on)
        if on != self._wide:
            self._wide = on
            self._relayout()

    def is_wide(self) -> bool:
        return self._wide

    def sizeHint(self) -> QSize:
        """Across the strip, how deep the panel is IS a question about width.

        The rows wrap, so every width has its own depth. Qt's hint is a single
        number — the depth at the panel's own preferred width — and the strip
        is hardly ever exactly that wide: short of it the bottom line of
        switches is cut off, past it the panel steals a row of playlists. A
        Mac gets the short end at every width, its fallback for a missing
        Consolas being wider than the font the number was measured with.

        Down the side nothing wraps, so there the plain hint is the answer.
        """
        hint = super().sizeHint()
        if not self._wide:
            return hint
        return QSize(hint.width(), self.heightForWidth(self.width()
                                                       or hint.width()))

    def _relayout(self):
        """Re-deal the rows into a fresh body. They are re-parented by being
        added, so nothing is rebuilt — only the shape they stand in."""
        # The sub-groups lie down with the panel: a Paso Doble block four rows
        # deep would set the height of the whole strip on its own.
        for group in self.findChildren(_Rows):
            group.set_wide(self._wide)
        # Built with its parent from the start: a parentless widget shown is a
        # window of its own on the desktop.
        body = QWidget(self)
        dealt = set()
        if self._wide:
            lyt = _FlowLayout(body)
            lyt.setContentsMargins(0, 0, 0, 0)
            # Row by row, not group by group. Kept whole, a group is one word
            # in the paragraph — but the widest of them is half the strip on
            # its own, so every line broke early and the panel came out a rung
            # deeper than the width called for. Loose rows pack tight; they
            # keep their reading order, so a group still reads as a group
            # wherever the line doesn't break through it.
            for sep, rows, _grow in self._sections:
                for w in rows:
                    if w in self._strip_drops():
                        continue
                    lyt.addWidget(w)
                    dealt.add(w)
                if sep is not None:
                    sep.setParent(self)     # rules divide columns, not lines
                    sep.hide()
        else:
            lyt = QVBoxLayout(body)
            lyt.setContentsMargins(0, 0, 0, 0)
            lyt.setSpacing(6)
            for sep, rows, grow in self._sections:
                if sep is not None:
                    # Into the layout first, shown second: a widget shown
                    # while it still hangs off the panel flashes where it used
                    # to be before the body takes it.
                    lyt.addWidget(sep)
                    sep.setVisible(True)
                for w in rows:
                    lyt.addWidget(w)
                    dealt.add(w)
                if grow:
                    lyt.addStretch(1)
        # Whatever this shape has no place for keeps the panel as its parent:
        # left in the old body it would be destroyed with it, and there would
        # be nothing to deal back on the way over.
        for w in self._all_rows():
            if w not in dealt:
                w.setParent(self)
                w.hide()
                self._parked.add(w)
            elif w in self._parked:
                w.show()
                self._parked.discard(w)
        # Down the side it is one column and wants its 250; across the strip
        # it takes the width it is given and answers with a height.
        self.setMinimumWidth(0 if self._wide else 250)
        self.setMaximumWidth(16777215 if self._wide else 640)
        pol = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred if self._wide
            else QSizePolicy.Policy.Expanding)
        # A layout reads the wrapping off the panel's own layout, but whoever
        # sizes it by the POLICY — a splitter, a scroll area — has to be told,
        # or it takes the hint's one number for the depth at every width.
        pol.setHeightForWidth(self._wide)
        self.setSizePolicy(pol)
        self.layout().setContentsMargins(*((10, 6, 10, 6) if self._wide
                                           else (8, 8, 8, 8)))
        old, self._body = self._body, body
        self.layout().replaceWidget(old, body)
        # A widget built parentless starts out hidden, and a panel that is
        # already on screen has no show() left to come and reveal it.
        body.show()
        old.setParent(None)
        old.deleteLater()
        self._apply_skin()

    def _apply_skin(self):
        """Down the side the panel is a panel — the window's own light grey.
        In the strip it is part of the player: a pale board bolted to the side
        of a black deck reads as two devices, and the operator's eye has to
        cross the seam every time. Dark, the strip is one machine.

        Only what a stylesheet cannot reach is set by hand: the readouts and
        the labels carry their own colours from the build."""
        self.setStyleSheet(_STRIP_QSS if self._wide else "")
        ink = "#7fb2f0" if self._wide else "#1565c0"
        self.len_lbl.setStyleSheet(
            "QLabel#playLen{font-size:34px; font-weight:bold;"
            f"font-family:Consolas,monospace; color:{ink};}}")
        self.pause_music_lbl.setStyleSheet(
            f"color:{'#9fb0c8' if self._wide else '#555'}; font-style:italic;")
        for pill in self.findChildren(_Toggle):
            pill.set_ink(QColor("#dfe8f6") if self._wide else None)

    def _all_rows(self):
        return [w for _sep, rows, _grow in self._sections for w in rows]

    def _strip_drops(self) -> set:
        """What the strip does not repeat.

        The heading names a mode the strip itself is announcing, and the
        countdown is the player's own clock a hand's width to the left —
        twice the same second, in two different fonts."""
        return {self._title_row, self.countdown_lbl}


    def set_voice_advanced_shown(self, on: bool):
        """Show or hide the fine print of the announcement: …with takt, …with
        heat and the 🔈 Test button (⚙ Settings → 'Advanced voice controls').

        Three controls that are set once and then never touched again, sitting
        in the busiest column of the desk. Hidden they are still ON — what they
        were set to keeps being announced; only the switches are out of the
        way.

        They sit inside the announcement's own folder, so with 🔈 off they are
        off the panel whatever this says."""
        for w in (self.announce_takt_check, self.announce_heat_check,
                  self.announce_test_btn):
            w.setVisible(bool(on))

    def set_settings_visible(self, on: bool):
        """Show the ⚙ gear — only a player-only install needs its own."""
        self._gear_box.setVisible(on)

    def set_player_widget(self, w: QWidget):
        """Dock the big master player on top of the panel (UltraMixer-style)."""
        self.layout().insertWidget(0, w)

    def _pick_pause_music(self):
        start = (str(Path(self._pause_music[0]).parent)
                 if self._pause_music else "")
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose pause music", start,
            "Audio / playlist (*.mp3 *.wav *.flac *.m4a *.ogg *.m3u *.m3u8);;"
            "All files (*)")
        if not paths:
            return
        files: list[str] = []
        for p in paths:
            if p.lower().endswith((".m3u", ".m3u8")):
                files.extend(self._read_m3u(p))
            else:
                files.append(p)
        if files:
            self._set_pause_music(files)

    @staticmethod
    def _read_m3u(path: str) -> list[str]:
        """Every non-comment line of the playlist is a file path; relative
        ones resolve against the playlist's own folder."""
        try:
            lines = read_playlist_text(path)[0].splitlines()
        except (OSError, PlaylistEncodingError) as exc:
            log.warning("🎵 Could not read pause playlist\n"
                        "file: %s\n"
                        "error: %s", path, exc)
            return []
        base = Path(path).parent
        out: list[str] = []
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            p = Path(ln)
            if not p.is_absolute():
                p = base / p
            out.append(str(p))
        return out

    def _set_pause_music(self, paths: list[str]):
        self._pause_music = list(paths)
        self._refresh_pause_music_lbl()
        self.settingsChanged.emit()

    def _refresh_pause_music_lbl(self):
        if self._pause_music:
            fm = self.pause_music_lbl.fontMetrics()
            first = Path(self._pause_music[0]).stem
            n = len(self._pause_music)
            text = first if n == 1 else f"{n} titles · {first}…"
            self.pause_music_lbl.setText(
                fm.elidedText(text, Qt.TextElideMode.ElideRight, 160))
            self.pause_music_lbl.setToolTip(
                "\n".join(Path(p).stem for p in self._pause_music))
        else:
            self.pause_music_lbl.setText("none")
            self.pause_music_lbl.setToolTip("")

    @staticmethod
    def _load_secs(settings: dict) -> int:
        """The stored play length, kept exactly as it was left.

        It used to snap to the nearest ladder rung — a migration for the
        pre-ladder free slider. It cannot any more: a length typed into the
        readout is deliberately off the ladder, and snapping would quietly
        turn 1:37 back into 1:30 on the next start. An unticked pre-ladder
        on/off box is still the modern 'full'."""
        if not settings.get("timed_enabled", True):
            return 0
        secs = int(settings.get("play_secs", 105))
        if secs <= 0:
            return 0
        return max(_LEN_TYPED_MIN, min(_LEN_TYPED_MAX, secs))

    def _step_len(self, direction: int):
        """One rung up or down. Up from 2:30 lands on 'full'; down from 'full'
        comes back to 2:30. Both ends stop there instead of wrapping around —
        a mis-tap must never jump from full length to 15 s."""
        if direction > 0:
            self._secs = (0 if self._secs == 0 or self._secs >= _LEN_MAX
                          else self._secs + _LEN_STEP)
        elif self._secs == 0:
            self._secs = _LEN_MAX
        else:
            self._secs = max(_LEN_STEP, self._secs - _LEN_STEP)
        self._refresh_len_lbl()
        self.settingsChanged.emit()

    def _on_len_typed(self, _event=None):
        """Double-click on the readout: type the length into the big blue
        digits themselves, rather than into a box on top of them.

        In place because the desk is already looking at that number, and a
        modal dialog over the panel mid-heat is one thing too many to dismiss.
        The editor is made once and then reused."""
        if self._len_edit is None:
            self._len_edit = _InlineEdit(self.len_lbl)
            self._len_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # The label's own type, so the digits do not jump on the switch.
            # Transparent, so the panel background shows through whatever the
            # theme has made it; the border is what says "this is editable".
            self._len_edit.setStyleSheet(
                "font-size:34px; font-weight:bold; color:#1565c0;"
                "font-family:Consolas,monospace; background:transparent;"
                "border:2px solid #1565c0; border-radius:6px;")
            self._len_edit.setToolTip("m:ss, seconds, or 'full' — "
                                      "Enter to keep, Esc to abandon")
            self._len_edit.editingFinished.connect(self._commit_len_typed)
            self._len_edit.escaped.connect(self._close_len_edit)
        self._len_edit.setGeometry(self.len_lbl.rect())
        self._len_edit.setText(self.len_lbl.text())
        # The editor is transparent so the panel's own background shows through
        # it — which means the label's digits would show through too, printed
        # underneath the ones being typed. Blank it for as long as it is open.
        self.len_lbl.setText("")
        self._len_edit.show()
        self._len_edit.selectAll()
        self._len_edit.setFocus()

    def _close_len_edit(self):
        """Put the editor away and the readout back. Also the Esc path."""
        self._len_edit.hide()
        self._refresh_len_lbl()

    def _commit_len_typed(self):
        """Enter, or the focus moving on to something else.

        Unparseable input is refused rather than guessed at, so an abandoned
        half-typed '1:' leaves the length exactly as it was."""
        # isHidden, not isVisible: the question is whether the editor is open,
        # and isVisible would also answer "no" for a panel that is merely on a
        # tab nobody is looking at.
        if self._len_edit.isHidden():
            return          # editingFinished comes again on the focus-out
        text = self._len_edit.text()
        self._close_len_edit()
        secs = parse_play_length(text)
        if secs is None:
            log.info("⏱️ Play length not understood\n"
                     "typed: %s\n"
                     "keeping: %s s", text, self._secs)
            return
        if secs == self._secs:
            return
        self._secs = secs
        self._refresh_len_lbl()
        self.settingsChanged.emit()

    def _on_pd_on(self, on: bool):
        """Fold the Paso Doble's fine print away with its switch.

        Edit mode goes with it: left running behind a hidden button it would
        keep the highlight stop suspended with nothing on screen saying so."""
        if not on and self.pd_edit_btn.isChecked():
            self.pd_edit_btn.setChecked(False)
        self.pd_sub_box.setVisible(on)

    def _on_pd_edit(self, on: bool):
        self.pd_edit_btn.setText("✔  Done editing" if on else "✏️  Edit highlights")
        self.pd_marks_box.setVisible(on)
        self.pdEditToggled.emit(on)

    def pd_editing(self) -> bool:
        return self.pd_edit_btn.isChecked()

    def set_pd_edit(self, on: bool):
        """Leave edit mode from the outside (a new title cancels it, so its
        highlight stop isn't left suspended)."""
        self.pd_edit_btn.setChecked(on)

    def set_pd_marks(self, marks: list[float]):
        """Rebuild the deletable mark chips. Only visible while editing."""
        while self.pd_marks_lyt.count():
            w = self.pd_marks_lyt.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for t in marks:
            chip = QToolButton()
            chip.setText(f"{int(t) // 60}:{int(t) % 60:02d}  ✕")
            chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chip.setToolTip(i18n.t("Delete the highlight at %s s") % f"{t:.1f}")
            chip.setStyleSheet(
                "QToolButton { background:#ffe0b2; border:1px solid #ff9800;"
                " border-radius:9px; padding:1px 6px; }")
            chip.clicked.connect(lambda _=False, v=float(t):
                                 self.pdMarkDeleteRequested.emit(v))
            self.pd_marks_lyt.addWidget(chip)
        if not marks:
            hint = QLabel("no marks — scrub to a crash and hit 🎯")
            hint.setStyleSheet("color:#777; font-style:italic; font-size:11px;")
            self.pd_marks_lyt.addWidget(hint)
        self.pd_marks_lyt.addStretch(1)

    def _fill_screens(self, select: int | None = None):
        """(Re)list the connected monitors. The wanted one is found by name
        wherever the list now has it; while it is unplugged the index stands
        in, clamped to what is there. `select` is that index from a setting
        written before names were kept."""
        combo = self.presenter_screen_combo
        want = combo.currentIndex() if select is None else select
        combo.blockSignals(True)
        combo.clear()
        for label, name in screen_choices():
            combo.addItem(label, name)
        n = combo.count()
        if n:
            found = combo.findData(self._screen_name) if self._screen_name else -1
            combo.setCurrentIndex(found if found >= 0 else max(0, min(n - 1, want)))
            if not self._screen_name:
                self._screen_name = str(combo.currentData() or "")
        combo.blockSignals(False)

    def _on_screen_picked(self, _index: int):
        self._screen_name = str(self.presenter_screen_combo.currentData() or "")

    def presenter_screen(self) -> int:
        return max(0, self.presenter_screen_combo.currentIndex())

    def presenter_screen_name(self) -> str:
        """The monitor picked for the presenter — also while it is unplugged."""
        return self._screen_name

    def presenter_theme(self) -> str:
        """The key of the palette the presenter screen is set to wear."""
        return str(self.presenter_theme_combo.currentData() or DEFAULT_KEY)

    def keep_awake(self) -> bool:
        """Whether the screensaver and the display timeout are held off while
        something is playing or the presenter screen is open."""
        return self.awake_check.isChecked()

    def set_presenter_on(self, on: bool):
        """Reflect the presenter window's real state (it can be closed with Esc
        or its window button, not only via the toggle)."""
        self.presenter_btn.setChecked(bool(on))

    # ── 🎉 Party play set ─────────────────────────────────────────────────────

    def play_set(self) -> dict:
        """The controls a play set overrides, as they stand now."""
        return {"secs": self._secs,
                "fade": self.fade_secs(),
                "advance": self.advance_check.isChecked(),
                "pause_off": not self.pause_check.isChecked(),
                "loudness": self.loudness_check.isChecked(),
                "announce": self.announce_check.isChecked(),
                "dblclick": self.dblclick_check.isChecked()}

    def apply_play_set(self, secs: int, advance: bool, pause_off: bool,
                       loudness: bool = None, announce: bool = None,
                       fade: float = None, dblclick: bool = None) -> list[str]:
        """Put them onto the given values and report what really changed,
        phrased for a toast ("play length → full"). `loudness`, `announce`,
        `fade` and `dblclick` are optional: a party set stored before they
        joined the set doesn't carry them, and must then leave those controls
        alone."""
        changed: list[str] = []
        if secs != self._secs:
            self._secs = secs
            self._refresh_len_lbl()
            changed.append(i18n.t("play length → %s")
                           % (i18n.t("full") if secs == 0
                              else "%d:%02d" % (secs // 60, secs % 60)))
        if fade is not None and float(fade) != self.fade_spin.value():
            self.fade_spin.setValue(float(fade))
            # :g so a whole second reads "3 s" and not "3.0 s".
            changed.append(i18n.t("fade-out → %s s") % ("%g" % float(fade)))
        if advance != self.advance_check.isChecked():
            self.advance_check.setChecked(advance)
            changed.append(i18n.t("auto-advance → on") if advance
                           else i18n.t("auto-advance → off"))
        if pause_off == self.pause_check.isChecked():
            self.pause_check.setChecked(not pause_off)
            changed.append(i18n.t("pause between songs → off (no break music)")
                           if pause_off else i18n.t("pause between songs → on"))
        if loudness is not None and loudness != self.loudness_check.isChecked():
            self.loudness_check.setChecked(loudness)
            changed.append(i18n.t("equalize volume → on") if loudness
                           else i18n.t("equalize volume → off"))
        if announce is not None and announce != self.announce_check.isChecked():
            self.announce_check.setChecked(announce)
            changed.append(i18n.t("announce next dance → on") if announce
                           else i18n.t("announce next dance → off"))
        if dblclick is not None and dblclick != self.dblclick_check.isChecked():
            self.dblclick_check.setChecked(dblclick)
            changed.append(i18n.t("double-click → starts the title") if dblclick
                           else i18n.t("double-click → cues it"))
        if changed:
            self.settingsChanged.emit()
        return changed

    def set_party_on(self, on: bool):
        """Reflect the party set's real state without re-firing the toggle."""
        self.party_btn.blockSignals(True)
        self.party_btn.setChecked(bool(on))
        self.party_btn.blockSignals(False)
        if on:
            self.set_tournament_on(False)   # the two sets are never both on

    def set_tournament_on(self, on: bool):
        """Light the 🏆 button while the panel stands on the tournament values.

        A click already toggles the button by itself, so this is also what puts
        it back on after someone presses it while it is lit.
        """
        self.tournament_btn.blockSignals(True)
        self.tournament_btn.setChecked(bool(on))
        self.tournament_btn.blockSignals(False)

    def tournament_on(self) -> bool:
        return self.tournament_btn.isChecked()

    def _on_pause_on(self, on: bool):
        """The pause was switched on or off: follow it in the row, and let the
        engine see a pause of 0 while it is off (the seconds stay stored)."""
        self._sync_pause_row()
        self.settingsChanged.emit()

    def _sync_pause_row(self):
        """Take off what cannot happen, grey out what merely has no effect.

        Without ⏭ auto-advance the operator starts every song by hand: there is
        no gap between two songs and no end to run past, so the pause row and
        the 🔁 tick are not dead options — they are no options at all, and they
        leave the panel entirely. With the pause itself switched off, its
        seconds and the filler music only grey out, because that switch is
        right there to click again. Nothing is forgotten either way — the
        values stay where they are and come back with the checkbox."""
        advancing = self.advance_check.isChecked()
        pausing = advancing and self.pause_check.isChecked()
        self.pause_row_box.setVisible(advancing)
        # Same reason, one line up: nothing runs on by itself without ⏭, so
        # neither can the list start over.
        self.repeat_check.setVisible(advancing)
        self.pause_spin.setEnabled(pausing)
        self.pause_music_box.setEnabled(pausing)
        self.pause_vol_box.setEnabled(pausing)
        # No pause means no gap to fill — take the filler controls off the
        # panel rather than leave two dead rows in the way.
        self.pause_sub_box.setVisible(pausing)

    def _refresh_len_lbl(self):
        secs = self._secs
        self.len_lbl.setText("full" if secs == 0
                             else f"{secs // 60}:{secs % 60:02d}")
        self.len_plus.setEnabled(secs != 0)

    # ── Values read by MainWindow's playback engine ──

    def play_secs(self) -> int:
        """Seconds per song, 0 = play to the track's own end (see
        `timed_enabled`, which every caller checks first)."""
        return self._secs

    def fade_secs(self) -> float:
        return self.fade_spin.value()

    def timed_enabled(self) -> bool:
        """'full' on the ladder is the off position — no cut, no fade-out."""
        return self._secs > 0

    def auto_advance(self) -> bool:
        return self.advance_check.isChecked()

    def _follow_advance_with_announce(self, advancing: bool):
        """✋ Manual means the operator starts every song themselves, so an
        announcement would call a dance nothing then plays. Off it goes, and
        ⏭ Auto puts back what was configured — not simply "on", so an evening
        run without announcements stays without them.

        A value switched on by hand in the meantime is left alone: what is
        remembered is what to restore, never what to enforce."""
        if advancing:
            if self._announce_before_manual:
                self.announce_check.setChecked(True)
            self._announce_before_manual = False
        else:
            self._announce_before_manual = self.announce_check.isChecked()
            self.announce_check.setChecked(False)

    def repeat_list(self) -> bool:
        """Whether the end of the list is followed by its own beginning.

        Its own tick is not enough — without ⏭ auto-advance nothing follows
        anything, and the tick then stays checked but off the panel (the rule
        `pause_available` follows for the same reason)."""
        return self.auto_advance() and self.repeat_check.isChecked()

    def repeat_setting_on(self) -> bool:
        """The tick as shown, kept across an auto-advance off/on toggle."""
        return self.repeat_check.isChecked()

    def pause_secs(self) -> int:
        """Pause between songs, 0 while the ⏭ off switch is engaged — the next
        song then starts as soon as the current one ends."""
        return self.pause_spin.value() if self.pause_check.isChecked() else 0

    def pause_enabled(self) -> bool:
        return self.pause_check.isChecked()

    def pause_available(self) -> bool:
        """Whether a between-songs pause can actually happen.

        Its own tick is not enough: without ⏭ auto-advance the operator starts
        every song by hand, so there is no gap for a pause to fill — and the
        tick box stays checked but off the panel in that state, which is why
        both halves have to be asked."""
        return self.auto_advance() and self.pause_check.isChecked()

    def pause_setting_secs(self) -> int:
        """The configured seconds as shown, kept across an off/on toggle."""
        return self.pause_spin.value()

    def announce_next(self) -> bool:
        return self.announce_check.isChecked()

    def announce_wait(self) -> bool:
        """Whether the music waits for the start call instead of coming in
        under it — the ⏳ half of the pair under ⏭."""
        return self.announce_wait_radio.isChecked()

    def announce_takt(self) -> bool:
        return self.announce_takt_check.isChecked()

    def announce_heat(self) -> bool:
        return self.announce_heat_check.isChecked()

    def announce_voice(self) -> str:
        """'female', 'male' or 'random' — which recorded voice to announce in."""
        return self.announce_voice_combo.currentData() or "female"

    def show_artwork(self) -> bool:
        return self.artwork_check.isChecked()

    def dblclick_plays(self) -> bool:
        """True where a double-click in a deck starts the title, False where it
        only cues it on the player."""
        return self.dblclick_check.isChecked()

    def remember_pos(self) -> bool:
        """True where the spot a title stopped at is kept and played from again.

        The marks themselves live only as long as the app does — this is the
        switch, not the marks."""
        return self.remember_check.isChecked()

    def loudness_eq(self) -> bool:
        """User's stored intent (persisted), independent of whether loudness
        data is available yet — so the preference survives a restart."""
        return self.loudness_check.isChecked()

    def loudness_active(self) -> bool:
        """Whether equalization should be applied right now. Per-track: active
        whenever the box is ticked — `_loudness_gain` then pulls each MEASURED
        track towards the target and leaves unmeasured tracks at unity (original
        volume), so the dB readout shows for any measured track being played."""
        return self.loudness_check.isChecked()

    def pd_highlight_stop(self) -> bool:
        return self.pd_check.isChecked()

    def set_pd_highlight_stop(self, on: bool) -> list[str]:
        """Switch the 🐂 stop and report it the way `apply_play_set` does — the
        🏆 tournament set switches it off, its detection being too unreliable to
        cut a competition Paso Doble on."""
        if bool(on) == self.pd_check.isChecked():
            return []
        self.pd_check.setChecked(bool(on))   # …which reports the change itself
        return [i18n.t("🐂 Paso Doble highlight stop → on") if on
                else i18n.t("🐂 Paso Doble highlight stop → off")]

    def pd_highlight_n(self) -> int:
        return self.pd_spin.value()

    def pd_start_delay(self) -> int:
        """Seconds a Paso Doble waits after the call before the music starts
        (0 = start at once)."""
        return self.pd_delay_spin.value()

    def pause_music(self) -> list[str]:
        return list(self._pause_music)

    def pause_music_vol(self) -> int:
        """Filler loudness in percent of the normal playback volume."""
        return self.pause_vol_spin.value()

    def set_loudness_available(self, available: bool, missing: int = 0):
        """Equalize-volume is only offerable when every playlist track has a
        measured loudness (`missing` = unanalyzed count, -1 = no data at all) —
        a partially equalized playlist would jump in level between songs."""
        # Per-track equalization: the box always works (measured tracks are pulled
        # to the target, unmeasured ones play untouched), so this only updates the
        # tooltip to flag how many open-playlist tracks aren't measured yet.
        self._loudness_available = available
        base = ("Compensate loudness differences between tracks on playback:\n"
                "each song's measured EBU R128 loudness is pulled towards a\n"
                "common target, so quiet old recordings and loud modern\n"
                "masters play at a similar level.")
        if available:
            self.loudness_check.setToolTip(base)
        elif missing < 0:
            self.loudness_check.setToolTip(
                i18n.t(base) + "\n\n" + i18n.t("ℹ No loudness measured yet — tracks play at their\n"
                                                 "original volume. Run 📊 Analyze loudness (⚙ Settings)\n"
                                                 "to equalize them."))
        else:
            self.loudness_check.setToolTip(
                i18n.t(base) + "\n\n"
                + (i18n.t("ℹ %d open-playlist track not measured yet — it plays at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize it too.") if missing == 1
                   else i18n.t("ℹ %d open-playlist tracks not measured yet — they play at original volume.\nRun 📊 Analyze loudness (⚙ Settings) to equalize them too.")) % missing)

    def set_countdown(self, text: str):
        # Fit-to-width: start at the full 22px clock font and only step down
        # as far as needed so longer statuses ("🐂 detecting highlights…",
        # "🏁 Hauptrunde finished") stay fully visible at maximum size.
        if text == self._countdown_text:
            return
        self._countdown_text = text
        if text:
            avail = max(self.countdown_lbl.width() - 8, 160)
            font = QFont("Consolas")
            size = 22
            while size > 11:
                font.setPixelSize(size)
                if QFontMetrics(font).horizontalAdvance(text) <= avail:
                    break
                size -= 1
            self.countdown_lbl.setStyleSheet(
                f"font-size:{size}px; font-family:Consolas,monospace;"
                " color:#444;")
        self.countdown_lbl.setText(text)
