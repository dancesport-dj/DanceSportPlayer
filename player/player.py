"""The big bottom player bar, the hover preview overlay and a click-seek slider.

Extracted from dancesport_gui.py (view split): BigPlayerWidget, PreviewOverlay,
_ClickSlider and the small format helpers used alongside them.
"""
import logging
import shiboken6

import math
import time
from typing import TYPE_CHECKING
from PySide6.QtCore import (
    QPoint,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pathlib import Path
from collections.abc import Callable
from player.artwork import cover
from shared.icons import (
    WARN,
    button as icon_button,
    html as icon_html,
    icon,
    pixmap as icon_pixmap,
)
from planner import i18n

# The desk's table, named in annotations only: the evening is handed one
# and never builds one, so it must not import the desk at runtime.
if TYPE_CHECKING:
    from gui.playlist_table import PlaylistTable

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.player")

# Edge length of the 🖼 cover on the player card — as tall as the title block
# next to it, so switching it on doesn't grow the card.
_ART_PX = 76

# Icon colours. The overlay is a light card in the app's blue, the big player a
# dark one — an icon carries its own colour, so it has to be told which world
# it is in (a QSS `color:` no longer reaches it).
_OVERLAY_INK = "#1565c0"
_CARD_INK = "#cfe0f5"
_CARD_FADE = "#d8a0a0"     # fade this song out
_CARD_PAUSE = "#9fc3f0"    # over to the pause music
_CARD_EXTEND = "#7fd4a0"   # give the pause more time
_CARD_CUE = "#f0c674"      # back to 0:00
_CARD_PANIC = "#e58080"    # fade to silence and hold
_CARD_DIM = "#8fa3c4"      # the fader's own small marks
_CARD_GAIN = "#d8b35c"     # the R128 equalization readout

# One − / + click on the tempo fader, in the slider's own 0.1 % units — the
# finest step the fader has. A takt is hit by tenths, not halves, and the far
# side of the range is reached by holding the button rather than by clicking.
_TEMPO_STEP = 1


def _fmt_ms(ms: int) -> str:
    """Milliseconds → mm:ss for the preview-overlay time labels."""
    s = max(0, int(ms) // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def _round_half_up(x: float) -> int:
    """Round half UP, so a takt of 24.5 shows as T25. Python's built-in round()
    uses banker's rounding (round(24.5) == 24), which would read T24 here."""
    return math.floor(x + 0.5)


def _takt_text(x: float) -> str:
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


class _ClickSlider(_NoWheelSlider):
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


class _TempoSlider(_ClickSlider):
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


class PreviewOverlay(QFrame):
    """Small floating player shown right below the row whose ▶ was clicked:
    title, seek bar, restart / ±10 s skip, elapsed + remaining time and a
    volume slider. Drag anywhere on its background to move it — the chosen
    spot is reused the next time it pops up. The ⚙ menu can disable the
    overlay (re-enable in ⚙ Settings → 'Preview player')."""

    closeRequested = Signal()    # ✕ clicked → MainWindow stops playback
    disableRequested = Signal()  # ⚙ → Disable → MainWindow persists the setting
    prevRequested = Signal()     # ⏮ → MainWindow plays the previous song row
    nextRequested = Signal()     # ⏭ → MainWindow plays the next song row
    duckToggled = Signal(bool)   # 🔉 → MainWindow pulls everything down (_DESK_DUCK)

    def __init__(self, player: QMediaPlayer, audio_out: QAudioOutput,
                 get_vol: Callable[[], float] | None = None,
                 set_vol: Callable[[float], None] | None = None):
        super().__init__(None)   # reparented into a deck's viewport on show_for()
        self._player = player
        self._audio_out = audio_out
        # MainWindow routes the slider through its base-volume factor so the
        # fade-out / loudness gains stay multiplied in; without callables the
        # slider drives the audio output directly (standalone use).
        self._get_vol = get_vol or audio_out.volume
        self._set_vol = set_vol or audio_out.setVolume
        self._dragging = False
        self._full_title = ""
        self._ducked = False
        self._drag_off: QPoint | None = None   # press point while moving the overlay
        self._user_pos: QPoint | None = None   # sticky position after a manual drag
        self._anchor: QPoint | None = None     # where it must stay while shown
        self.setObjectName("PreviewOverlay")
        # Light card in the app's palette (row blue-gray + undo-button blues).
        self.setStyleSheet(
            "#PreviewOverlay { background:#f3f6fc;"
            " border:1px solid #9aa6c0; border-radius:6px; }"
            "QLabel { color:#333; font-size:10px; background:transparent; }"
            "QToolButton { color:#1565c0; background:transparent; border:none;"
            " font-size:11px; font-weight:bold; padding:0px 3px; border-radius:3px; }"
            "QToolButton:hover { background:#d6e6fa; }"
            "QSlider::groove:horizontal { height:5px; border-radius:2px;"
            " background:#dde4f0; }"
            "QSlider::sub-page:horizontal { background:#4a82d2; border-radius:2px; }"
            "QSlider::handle:horizontal { width:9px; margin:-3px 0;"
            " border-radius:4px; background:#1565c0; }"
            # Seek bar: same slim look as the volume slider, but the widget is
            # taller — the whole 18 px strip is click/drag-sensitive.
            "QSlider#seek { min-height:18px; }"
        )

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(6, 3, 6, 4)
        lyt.setSpacing(1)

        # ── Row 1: ✕ | title | ⚙ ──
        top = QHBoxLayout()
        top.setSpacing(4)
        close_btn = QToolButton()
        icon_button(close_btn, "close", 11, _OVERLAY_INK)
        close_btn.setToolTip("Close the preview and stop playback  (Ctrl+X)")
        close_btn.clicked.connect(self.closeRequested.emit)
        top.addWidget(close_btn)
        self._title = QLabel("")
        # A title comes from an ID3 tag or an .m3u line, i.e. from whoever made
        # the file. Under the AutoText default Qt would parse markup in it and
        # its resource loader would fetch an <img src>, including over UNC.
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._title.setStyleSheet("font-weight:bold; color:#2c3e60;")
        self._title.setToolTip("Drag here to move the preview player")
        self._title.setCursor(Qt.CursorShape.OpenHandCursor)
        top.addWidget(self._title, stretch=1)
        gear_btn = QToolButton()
        icon_button(gear_btn, "gear", 12, _OVERLAY_INK)
        gear_btn.setToolTip("Preview-player options")
        gear_btn.clicked.connect(lambda: self._gear_menu(gear_btn))
        top.addWidget(gear_btn)
        lyt.addLayout(top)

        # ── Row 2: seek slider | ⏮ ◀◀ ▶▶ | times | 🔊 volume ──
        bot = QHBoxLayout()
        bot.setSpacing(4)
        self._slider = _ClickSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("seek")
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.clickJumped.connect(self._player.setPosition)   # click = seek
        bot.addWidget(self._slider, stretch=1)

        for name, tip, cb in (
                ("prev", "Previous title", self.prevRequested.emit),
                ("rewind", "Back 10 s", lambda: self._skip(-10_000)),
                ("forward", "Forward 10 s", lambda: self._skip(+10_000)),
                ("next", "Next title", self.nextRequested.emit)):
            b = QToolButton()
            icon_button(b, name, 12, _OVERLAY_INK)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            bot.addWidget(b)

        self._time_lbl = QLabel("00:00  -00:00")
        self._time_lbl.setStyleSheet(
            "font-family:Consolas,monospace; font-size:10px; color:#555;")
        bot.addWidget(self._time_lbl)

        self._duck_btn = QToolButton()
        icon_button(self._duck_btn, "volume", 12, _OVERLAY_INK)
        self._duck_btn.setCheckable(True)   # stays pressed while ducked
        self._duck_btn.setToolTip("Duck to 20 % / back to full")
        self._duck_btn.clicked.connect(self._toggle_duck)
        bot.addWidget(self._duck_btn)
        self._vol = _ClickSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setFixedWidth(50)
        self._vol.setToolTip("Volume")
        self._vol.valueChanged.connect(lambda v: self._set_vol(v / 100.0))
        bot.addWidget(self._vol)
        lyt.addLayout(bot)

        # The decks own Space / Ctrl+←→ shortcuts — never steal keyboard focus.
        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)

    # ── Placement ──

    def show_for(self, table: PlaylistTable, row: int, title: str):
        """Float the overlay inside `table`'s viewport, just below `row`
        (above it when the row sits at the bottom edge). After the user has
        dragged it somewhere, that spot is reused instead."""
        vp = table.viewport()
        if self.parentWidget() is not vp:
            self.setParent(vp)
        self._full_title = title
        self.resize(min(380, max(260, vp.width() - 12)), self.sizeHint().height())
        self._elide_title()
        self._vol.blockSignals(True)
        self._vol.setValue(round(self._get_vol() * 100))
        self._vol.blockSignals(False)
        self.set_ducked(self._ducked)
        if self._user_pos is not None:
            self.move(self._clamped(self._user_pos))
        else:
            y = table.rowViewportPosition(row) + table.rowHeight(row) + 2
            if y + self.height() > vp.height() - 2:
                y = table.rowViewportPosition(row) - self.height() - 2
            self.move(self._clamped(QPoint(6, y)))
        self._anchor = self.pos()
        self.show()
        self.raise_()

    def _clamped(self, p: QPoint) -> QPoint:
        """Keep the overlay fully inside its parent viewport."""
        vp = self.parentWidget()
        if not vp:
            return p
        return QPoint(
            max(2, min(p.x(), max(2, vp.width() - self.width() - 2))),
            max(2, min(p.y(), max(2, vp.height() - self.height() - 2))))

    # ── Drag-to-move (also swallows clicks so they don't hit the table below) ──
    # Only the TITLE BAR starts a move — the slider row is left alone so a
    # slightly-missed seek can never fling the overlay around.

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if (event.button() == Qt.MouseButton.LeftButton
                and pos.y() <= self._title.geometry().bottom() + 2):
            self._drag_off = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_off is not None:
            self.move(self._clamped(
                self.pos() + event.position().toPoint() - self._drag_off))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_off is not None:
            self._drag_off = None
            self._user_pos = self._anchor = self.pos()   # spot for the next show
            self.unsetCursor()
        event.accept()

    def moveEvent(self, event):
        """Stay where it was put when the list scrolls underneath.

        A scroll area scrolls by MOVING its viewport's children, so one turn of
        the wheel over a long library list used to carry the overlay off the top
        edge — it looked like the player had vanished mid-song. Only a drag may
        move it; anything else is put straight back."""
        super().moveEvent(event)
        if (self._drag_off is None and self._anchor is not None
                and self.pos() != self._anchor):
            self.move(self._anchor)

    def mouseDoubleClickEvent(self, event):
        event.accept()   # don't let double-clicks reach the table either

    def _elide_title(self):
        fm = self._title.fontMetrics()
        avail = max(40, self.width() - 90)
        self._title.setText(fm.elidedText(self._full_title, Qt.TextElideMode.ElideRight, avail))

    # ── Player feedback ──

    def _on_duration(self, dur: int):
        self._slider.setRange(0, max(0, dur))
        self._update_time(self._player.position())

    def _on_position(self, pos: int):
        if not self._dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(pos)
            self._slider.blockSignals(False)
            self._update_time(pos)

    def _update_time(self, pos: int):
        dur = self._slider.maximum()   # kept in sync by durationChanged
        self._time_lbl.setText(f"{_fmt_ms(pos)}  -{_fmt_ms(dur - pos)}")

    # ── Controls ──

    def _on_slider_pressed(self):
        self._dragging = True

    def _on_slider_moved(self, value: int):
        self._update_time(value)   # live readout while scrubbing

    def _on_slider_released(self):
        self._dragging = False
        self._player.setPosition(self._slider.value())

    def _skip(self, delta_ms: int):
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def _toggle_duck(self):
        """🔉 Down to a fifth for a word over the music. MainWindow owns the
        factor, so this overlay and the big card always agree — and the button
        follows that answer, not the click, so the two never drift apart."""
        self.duckToggled.emit(not self._ducked)
        self._duck_btn.setChecked(self._ducked)

    def set_ducked(self, on: bool):
        self._ducked = bool(on)
        self._duck_btn.setIcon(icon("volume_low" if self._ducked else "volume",
                                    12, _OVERLAY_INK))
        self._duck_btn.setChecked(self._ducked)

    def _gear_menu(self, anchor: QToolButton):
        menu = QMenu(self)
        act = menu.addAction(icon("blocked"),
                             "Disable preview player  (re-enable in Settings)")
        act.triggered.connect(self.disableRequested.emit)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


def _block(layout) -> QWidget:
    """A row of the player card, wrapped in a widget of its own so `set_wide`
    can move it: a layout is re-parented only through a widget."""
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w


class BigPlayerWidget(QFrame):
    """UltraMixer-style master player docked on top of the Playing-mode panel:
    big readable title + elapsed/remaining time, full-width seek bar and large
    transport buttons — everything sized for a quick glance from a standing
    position at the tournament desk. Drives the shared QMediaPlayer."""

    prevRequested = Signal()   # ⏮ → previous song row of the active deck
    nextRequested = Signal()   # ⏭ → next song row of the active deck
    tempoResetModeChanged = Signal(bool)   # ↺ checkbox → MainWindow persists it
    tsoModeChanged = Signal(bool)          # TSO toggle → auto-equalize the heat tempo
    tempoApplied = Signal()                # rate changed → the ⏳ limit moves with it
    extendPauseRequested = Signal()        # ⏱➕ → lengthen the running auto-advance pause
    toPauseRequested = Signal()            # ⏸♪ → end this song now, jump to the pause music
    fadeOutRequested = Signal()            # 🔉↓ → fade the playing song out now
    panicRequested = Signal()              # 🛑 → fade to silence and HOLD (no advance)
    duckToggled = Signal(bool)             # 🔉 → _DESK_DUCK on everything audible
    fileDropped = Signal(str)              # a track dropped onto the card → play it

    def __init__(self, player: QMediaPlayer, audio_out=None,
                 get_vol: Callable[[], float] | None = None,
                 set_vol: Callable[[float], None] | None = None,
                 parent=None):
        super().__init__(parent)
        self._player = player
        # Volume goes through MainWindow's base-volume factor so the fade-out
        # ramp and the loudness gain stay multiplied in (same wiring as the
        # preview overlay); the 🔉 duck is a factor of its own over there, so
        # the card and the overlay always show the same state.
        self._audio_out = audio_out
        self._get_vol = get_vol or (audio_out.volume if audio_out else (lambda: 1.0))
        self._set_vol = set_vol or (audio_out.setVolume if audio_out else (lambda _v: None))
        self._tempo_player = player   # the fader always targets the MAIN player
        self._ducked = False
        self._dragging = False
        self._full_title = ""
        self._dur = 0   # the track's real duration (slider max may be a limit)
        # Set by MainWindow: after a 🏁 round-end stop the ⏯ button starts
        # the next round's first song (returns True when it handled the tap).
        self.resume_cb: Callable[[], bool] | None = None
        # Walking text for titles wider than the card (started by _elide_title).
        self._marquee_pos = 0
        self._marquee = QTimer(self)
        self._marquee.setInterval(300)
        self._marquee.timeout.connect(self._marquee_step)
        self.setObjectName("BigPlayer")
        _common_qss = (
            "QLabel { background:transparent; }"
            "QToolButton { color:#cfe0f5; background:#2a3346; border:none;"
            " font-size:14px; padding:3px 5px; border-radius:5px; }"
            "QToolButton:hover { background:#3a4a68; }"
            "QToolButton:pressed { background:#1565c0; }"
            "QSlider::groove:horizontal { height:6px; border-radius:3px;"
            " background:#2a3346; }"
            "QSlider::sub-page:horizontal { background:#4a82d2; border-radius:3px; }"
            "QSlider::handle:horizontal { width:12px; margin:-4px 0;"
            " border-radius:6px; background:#9fc3f0; }"
            "QSlider#seek { min-height:20px; }")
        # Normal vs end-of-track warning skins (the card flashes red while a
        # song is in its last seconds — see _flash_step / _update_time).
        # Both skins use the SAME 2px border width so toggling them never
        # reflows the card's content (only the colour changes when flashing).
        self._base_qss = (
            "#BigPlayer { background:#1d2330; border:2px solid #10141d;"
            " border-radius:8px; }" + _common_qss)
        self._flash_qss = (
            "#BigPlayer { background:#3a1d22; border:2px solid #e53935;"
            " border-radius:8px; }" + _common_qss)
        # A deliberate fade (🔉↓ / 🛑) blinks the same beat in ORANGE: the song
        # is on its way out because the operator said so, which reads
        # differently from a song running into its own end.
        self._fade_qss = (
            "#BigPlayer { background:#3a2a17; border:2px solid #fb8c00;"
            " border-radius:8px; }" + _common_qss)
        # The seek bar joins the warning but does NOT blink with the card: it
        # stays steadily red for the whole final stretch, so the played portion
        # keeps reading as a progress bar. Set on the slider itself (its own
        # sheet outranks the card's), which also keeps _flash_step from
        # toggling it and leaves the volume slider blue.
        self._seek_end_qss = (
            "QSlider::sub-page:horizontal { background:#e53935;"
            " border-radius:3px; }"
            "QSlider::handle:horizontal { width:12px; margin:-4px 0;"
            " border-radius:6px; background:#ff8a80; }")
        self.setStyleSheet(self._base_qss)
        # End-of-track flash: blinks the card red over the last seconds.
        self._END_FLASH_MS = 10_000   # warn over the final 10 s of playback
        self._flash_on = False
        self._fading = False          # a fade-out is ramping the song down
        self._flash = QTimer(self)
        self._flash.setInterval(450)
        self._flash.timeout.connect(self._flash_step)

        # The blocks below stand in a body of their own, so the whole
        # arrangement can be swapped for the wide one (see set_wide) without
        # the frame, its skins or its wiring noticing.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._wide = False
        self._extra = None            # guest in the wide strip's middle
        self._lead = None             # …and in its bottom-right corner
        self._body = QWidget()
        outer.addWidget(self._body)

        # 🖼 Cover next to the title block — off unless the operator asks for it
        # (see set_artwork_enabled); the text column keeps the rest of the width.
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        self._art_on = False
        self._art_track: Path | None = None
        self._art_list: Path | None = None
        self._art = QLabel()
        self._art.setFixedSize(_ART_PX, _ART_PX)
        self._art.setVisible(False)
        head_row.addWidget(self._art, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        head_row.addLayout(text_col, 1)
        self._head_box = _block(head_row)

        self._title = QLabel("")
        # Track metadata is foreign input — never let Qt read markup in it (see
        # the preview overlay's title above).
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setStyleSheet("font-size:13px; font-weight:bold; color:#eef3fb;")
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_col.addWidget(self._title)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        self._sub = QLabel("")
        self._sub.setTextFormat(Qt.TextFormat.PlainText)
        self._sub.setStyleSheet("font-size:11px; color:#8fa3c4;")
        # Ignored width: a plain QLabel won't shrink below its text width, so a
        # long subtitle (dance · takt · 🥁 bpm) used to spill under the fade-out
        # / aux buttons. Let it yield space and elide instead (see _elide_sub).
        self._sub.setSizePolicy(QSizePolicy.Policy.Ignored,
                                QSizePolicy.Policy.Preferred)
        self._full_sub = ""
        # State glyph in front of the subtitle (the auto-advance pause). It has
        # to be its own label: _elide_sub pushes the subtitle through plain-text
        # elision, which would chew up an inline <img>.
        self._sub_icon = QLabel()
        self._sub_icon.setVisible(False)
        sub_row.addWidget(self._sub_icon)
        sub_row.addWidget(self._sub, stretch=1)
        # Pause-only countdown mirror (⏸ N s) — shown on the card ONLY while the
        # between-songs pause runs. During normal play the panel already shows
        # the sand clock and the card shows the adjusted time, so mirroring it
        # here too would just double the ⏳.
        self._countdown_lbl = QLabel("")
        self._countdown_lbl.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#d8b35c;"
            "font-family:Consolas,monospace;")
        sub_row.addWidget(self._countdown_lbl)
        # R128 equalization feedback: how far this track's volume was pulled —
        # back at the right end of the subtitle row.
        self._gain_icon = QLabel()
        self._gain_icon.setPixmap(icon_pixmap("volume", 11, _CARD_GAIN))
        self._gain_icon.setVisible(False)
        sub_row.addWidget(self._gain_icon)
        self._gain_lbl = QLabel("")
        self._gain_lbl.setStyleSheet(f"font-size:11px; color:{_CARD_GAIN};")
        self._gain_lbl.setToolTip(
            "Volume adjustment of this track by Equalize volume (R128)")
        sub_row.addWidget(self._gain_lbl)
        text_col.addLayout(sub_row)

        # What comes after this title — the operator's cue to get ready, and the
        # early warning that this is the round's last song. Elided like the
        # subtitle so a long title can't widen the card.
        self._next_lbl = QLabel("")
        self._next_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self._next_lbl.setStyleSheet("font-size:11px; color:#6e87ad;")
        self._next_lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                                     QSizePolicy.Policy.Preferred)
        self._full_next = ""
        text_col.addWidget(self._next_lbl)

        # Context aux buttons — fade-out / jump-to-pause / extend-pause. Created
        # here but placed in their OWN row BELOW the transport buttons (see
        # aux_row further down); shown only while a song plays / a pause runs.
        self._fade_btn = QToolButton()
        icon_button(self._fade_btn, "fade_out", 16, _CARD_FADE)
        self._fade_btn.setFixedHeight(28)
        self._fade_btn.setMinimumWidth(52)
        self._fade_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._fade_btn.setToolTip(
            "Fade this song out now (over the configured fade time), then end "
            "it\n— for a quick, clean finish on the floor.")
        self._fade_btn.clicked.connect(self.fadeOutRequested.emit)
        self._fade_btn.setVisible(False)
        self._topause_btn = QToolButton()
        icon_button(self._topause_btn, "break_music", 16, _CARD_PAUSE)
        self._topause_btn.setFixedHeight(28)
        self._topause_btn.setMinimumWidth(52)
        self._topause_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._topause_btn.setToolTip(
            "Jump straight to the pause music — end this song now and start\n"
            "the between-songs pause (e.g. the dancers are already leaving).")
        self._topause_btn.clicked.connect(self.toPauseRequested.emit)
        self._topause_btn.setVisible(False)
        self._extend_btn = QToolButton()
        icon_button(self._extend_btn, "extend", 16, _CARD_EXTEND)
        self._extend_btn.setFixedHeight(28)
        self._extend_btn.setMinimumWidth(52)
        self._extend_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._extend_btn.setToolTip(
            "Extend the auto-advance pause (add another pause length) —\n"
            "use it when the heat change is taking longer than planned.")
        self._extend_btn.clicked.connect(self.extendPauseRequested.emit)
        self._extend_btn.setVisible(False)
        # Card state for the context-dependent aux buttons (play vs. pause).
        self._is_paused = False
        self._has_song = False

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self._elapsed = QLabel("00:00")
        self._elapsed.setStyleSheet(
            "font-size:32px; font-weight:bold; color:#7fd4a0;"
            "font-family:Consolas,monospace;")
        time_row.addWidget(self._elapsed)
        time_row.addStretch(1)
        right_col = QVBoxLayout()
        right_col.setSpacing(0)
        self._remaining = QLabel("-00:00")
        self._remaining.setStyleSheet(
            "font-size:20px; color:#6e87ad; font-family:Consolas,monospace;")
        self._remaining.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        right_col.addWidget(self._remaining)
        # Where playback will ACTUALLY end (⏳ timed cut / 🐂 PD highlight
        # stop) next to the track's full length.
        self._limit_ms: int | None = None
        self._limit_glyph = "hourglass"
        # True when a stop is armed but resolves to the track's natural end (a PD
        # whose finale highlight sits at the end) — the card still shows a 🐂
        # marker so the operator sees the highlight-stop is on and the song plays
        # through, instead of the sand clock just vanishing.
        self._limit_to_end = False
        self._limit_lbl = QLabel("")
        self._limit_lbl.setStyleSheet(
            "font-size:11px; color:#d8b35c; font-family:Consolas,monospace;")
        self._limit_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._limit_lbl.setToolTip(
            "Adjusted play length (timed play / Paso Doble highlight stop)\n"
            "next to the track's full length")
        right_col.addWidget(self._limit_lbl)
        time_row.addLayout(right_col)
        self._time_box = _block(time_row)

        self._slider = _ClickSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("seek")
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_released)
        # Late-bound: the card can be retargeted to the pause-music player.
        self._slider.clickJumped.connect(
            lambda ms: self._player.setPosition(ms))

        btns = QHBoxLayout()
        btns.setSpacing(4)
        btns.addStretch(1)
        self._cue_btn = QToolButton()
        icon_button(self._cue_btn, "cue_start", 16, _CARD_CUE)
        self._cue_btn.setToolTip("Jump back to the start (0:00) of this track")
        self._cue_btn.clicked.connect(self._seek_to_start)
        btns.addWidget(self._cue_btn)
        self._pause_btn = None
        # The primary controls (prev / play-pause / next) are enlarged so the
        # operator can hit them at a glance; the fine controls stay smaller.
        primary = {"prev", "play_circle", "next"}
        for name, tip, cb in (
                ("prev", "Previous title", self.prevRequested.emit),
                ("rewind", "Back 10 s", lambda: self._skip(-10_000)),
                ("play_circle", "Pause / resume", self._toggle_pause),
                ("forward", "Forward 10 s", lambda: self._skip(+10_000)),
                ("next", "Next title", self.nextRequested.emit)):
            b = QToolButton()
            big = name in primary
            icon_button(b, name, 24 if big else 16, _CARD_INK)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            if big:
                b.setStyleSheet("QToolButton { padding:5px 7px; }")
            btns.addWidget(b)
            if name == "play_circle":
                self._pause_btn = b
        # 🔁 Hold the evening on THIS title: it starts over every time it ends.
        # A state, not an action, so it stays pressed and lights up — next to ⏭
        # because it is the answer to the same question, "what comes now".
        self._loop_btn = QToolButton()
        icon_button(self._loop_btn, "regen", 16, _CARD_INK)
        self._loop_btn.setCheckable(True)
        self._loop_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._loop_btn.setToolTip(
            "Endless repeat of THIS title (toggle):\n"
            "while on, the running title starts again every time it ends —\n"
            "for the moment the floor is still full or the speech runs long.\n\n"
            "It holds the evening on one title, so it beats the 🏁 end of a\n"
            "round and works with ⏭ auto-advance off too. Switch it off and\n"
            "the list carries on where it stands.")
        self._loop_btn.setStyleSheet(
            "QToolButton:checked { background:#1565c0; }")
        btns.addWidget(self._loop_btn)
        btns.addStretch(1)
        self._btn_box = _block(btns)

        # Aux controls row — fade-out / jump-to-pause / extend-pause — sitting
        # in their own row right BELOW the transport buttons (the operator's
        # "end this song" / "manage the pause" actions, kept clear of the main
        # play controls). Visibility is toggled per play / pause state.
        aux_row = QHBoxLayout()
        aux_row.setSpacing(6)
        aux_row.addStretch(1)
        aux_row.addWidget(self._fade_btn)
        aux_row.addWidget(self._topause_btn)
        aux_row.addWidget(self._extend_btn)
        aux_row.addStretch(1)
        self._aux_box = _block(aux_row)

        # ── Master volume — the ONLY volume control in Playing mode (the
        # preview overlay, which owns the other one, is hidden here). Full width
        # on purpose: it has to be hittable at a glance from a standing desk.
        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        self._panic_btn = QToolButton()
        icon_button(self._panic_btn, "panic", 16, _CARD_PANIC)
        self._panic_btn.setFixedHeight(28)
        self._panic_btn.setMinimumWidth(40)
        self._panic_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._panic_btn.setToolTip(
            "Fade the music out and HOLD it there (over the fade time).\n"
            "Nothing ends and nothing advances — ⏯ resumes at exactly the\n"
            "spot it went quiet. For an announcement or an incident on the floor.")
        self._panic_btn.clicked.connect(self.panicRequested.emit)
        vol_row.addWidget(self._panic_btn)
        self._duck_btn = QToolButton()
        icon_button(self._duck_btn, "volume", 16, _CARD_INK)
        self._duck_btn.setFixedHeight(28)
        self._duck_btn.setMinimumWidth(40)
        self._duck_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._duck_btn.setCheckable(True)   # stays pressed while ducked
        self._duck_btn.setStyleSheet(
            "QToolButton:checked { background:#d98f3a; border:1px solid #b06f20;"
            " border-radius:4px; }")
        self._duck_btn.setToolTip(
            "Duck to 20 % / back to full — the filler music comes down too")
        self._duck_btn.clicked.connect(self.toggle_duck)
        vol_row.addWidget(self._duck_btn)
        self._vol = _ClickSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(round(self._get_vol() * 100))
        self._vol.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._vol.setToolTip("Master volume")
        self._vol.valueChanged.connect(self._on_vol_changed)
        vol_row.addWidget(self._vol, stretch=1)
        self._vol_lbl = QLabel("")
        self._vol_lbl.setFixedWidth(34)
        self._vol_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                                   | Qt.AlignmentFlag.AlignVCenter)
        self._vol_lbl.setStyleSheet(
            "font-size:11px; color:#8fa3c4; font-family:Consolas,monospace;")
        vol_row.addWidget(self._vol_lbl)
        self._vol_box = _block(vol_row)
        self._refresh_vol_lbl()

        # ── Tempo fader: ±16% time-stretch, pitch preserved (the Qt ffmpeg
        # backend keeps the key — verified with a 440 Hz sine at rate 1.16).
        self._takt: int | None = None
        self._current_dance: str | None = None
        self._takt_overlay = None   # lazy: player.takt_meter.TaktMeterOverlay
        tempo_box = QVBoxLayout()
        tempo_box.setSpacing(2)
        # Top row: just the icon + the slider, so the fader spans the whole
        # card width and is easy to nudge precisely.
        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)
        tempo_icon = QLabel()
        tempo_icon.setPixmap(icon_pixmap("sliders", 12, _CARD_DIM))
        slider_row.addWidget(tempo_icon)
        self._tempo = _TempoSlider(Qt.Orientation.Horizontal)
        self._tempo.setRange(-160, 160)   # 0.1 % steps
        self._tempo.setValue(0)
        self._tempo.setToolTip(
            "Tempo −16 % … +16 % without changing the pitch (time stretch) —\n"
            "e.g. to pull a track onto the takt the tournament needs.\n"
            "Stays set across tracks; a double-click on the fader (or the\n"
            "button below) resets it.")
        self._tempo.resetRequested.connect(self.reset_tempo)
        # Every setPlaybackRate makes the backend re-init its resampler, which
        # is the short audible gap. So while the user is dragging we only move
        # the label and apply the rate ONCE, when the handle is released.
        # Wheel / keyboard changes (no drag) fall back to a debounce timer.
        self._tempo_apply = QTimer(self)
        self._tempo_apply.setSingleShot(True)
        self._tempo_apply.setInterval(220)
        self._tempo_apply.timeout.connect(self.apply_tempo)
        self._tempo.valueChanged.connect(self._on_tempo)
        self._tempo.sliderReleased.connect(self._on_tempo_released)
        # − / + around the fader: walk the tempo instead of hunting for it with
        # the handle, which on a 32 %-wide fader is a coarse instrument. Held,
        # they glide — the one control in this app where auto-repeat is the
        # point, not the hazard. The rate still lands once, when the stepping
        # stops: a programmatic setValue is no drag, so _on_tempo debounces it
        # exactly like a wheel notch and a glide costs one gap, not thirty.
        minus = self._tempo_step_btn("−", -_TEMPO_STEP, i18n.t("slower"))
        plus = self._tempo_step_btn("+", +_TEMPO_STEP, i18n.t("faster"))
        slider_row.addWidget(minus)
        slider_row.addWidget(self._tempo, stretch=1)
        slider_row.addWidget(plus)
        tempo_box.addLayout(slider_row)
        # Bottom row: the percentage / takt readout on the left, the reset and
        # the per-title auto-reset toggle on the right.
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        self._tempo_lbl = QLabel("±0.0%")
        self._tempo_lbl.setStyleSheet(
            "font-size:11px; color:#8fa3c4; font-family:Consolas,monospace;")
        info_row.addWidget(self._tempo_lbl)
        info_row.addStretch(1)
        self._tso_btn = QToolButton()
        self._tso_btn.setText("TSO")
        self._tso_btn.setCheckable(True)
        self._tso_btn.setStyleSheet(
            "QToolButton { font-size:11px; font-weight:bold; color:#7fd4a0; }"
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._tso_btn.setToolTip(
            "Auto-equalize the heat tempo (toggle):\n"
            "while on, every title is pitched to the average tempo of its\n"
            "dance in this round, kept inside the TSO range (e.g. a Rumba\n"
            "at 23 → T24, a Paso Doble at 57 → T58).")
        self._tso_btn.toggled.connect(self.tsoModeChanged.emit)
        self._tso_btn.toggled.connect(self._sync_tempo_pin)
        info_row.addWidget(self._tso_btn)
        tempo_reset = QToolButton()
        tempo_reset.setText("0")
        tempo_reset.setToolTip(
            "Reset the tempo to ±0 % (or double-click the fader)")
        tempo_reset.clicked.connect(self.reset_tempo)
        info_row.addWidget(tempo_reset)
        # A checkable button (not a QCheckBox — its white indicator clashed with
        # the dark card); it lights up in the accent colour while armed. Pinned
        # is the exception, so the signal carries the reset flag, not the pin.
        self._tempo_pin = QToolButton()
        icon_button(self._tempo_pin, "pin", 12, _CARD_INK)
        self._tempo_pin.setCheckable(True)
        self._tempo_pin.setToolTip(
            "📌 Pin the tempo: the fader stays where you left it when the next\n"
            "title starts.\n"
            "Off: every new title begins at ±0 %.\n"
            "Switching TSO on takes the pin off — TSO pitches each title itself.")
        self._tempo_pin.setStyleSheet(
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._tempo_pin.toggled.connect(
            lambda on: self.tempoResetModeChanged.emit(not on))
        info_row.addWidget(self._tempo_pin)
        self._takt_btn = QToolButton()
        self._takt_btn.setText("♪")
        self._takt_btn.setCheckable(True)
        self._takt_btn.setStyleSheet(
            "QToolButton:checked { background:#1565c0; color:#ffffff; }")
        self._takt_btn.setToolTip(
            "Tap along to the beat to measure this track's live tempo by hand,\n"
            "against a target for its dance (Sollwert) — display only, does not\n"
            "touch the fader.")
        self._takt_btn.toggled.connect(self._toggle_takt_overlay)
        info_row.addWidget(self._takt_btn)
        tempo_box.addLayout(info_row)
        self._tempo_box = _block(tempo_box)

        # The decks own Space / Ctrl+←→ shortcuts — never steal keyboard focus.
        self._relayout()
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Drop a track from a deck / the library onto the card to play it.
        self.setAcceptDrops(True)

        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)
        player.playbackStateChanged.connect(self._on_state)
        self.set_now("")

    def set_wide(self, on: bool):
        """Lay the card out along the width instead of down a panel — the wide
        strip that stands above the decks."""
        on = bool(on)
        if on != self._wide:
            self._wide = on
            self._relayout()

    def set_lead_widget(self, w):
        """Take something into the strip's bottom-right corner.

        The 📝/▶ mode switch stands there while the strip is Playing mode.
        Beside the transport it was 240 px of the player's own column, and
        that column sets how much width is left for the mode panel — the
        panel paid for it a whole line deep. In the corner it costs the strip
        one short row under a panel that is now a row shorter. Ignored while
        the card stands in a panel: there the switch is above it anyway."""
        if w is not self._lead:
            self._lead = w
            self._relayout()

    def set_extra_widget(self, w):
        """Let somebody else have the strip's empty middle.

        Wide, the card holds its own two ends and leaves a monitor's worth of
        nothing between them. That is where the Playing-mode panel goes, so
        the whole of the mode stands in one band and the decks get the side
        panel's width back. Ignored while the card stands in a panel — there
        it is the guest, not the host."""
        if w is not self._extra:
            self._extra = w
            self._relayout()

    def is_wide(self) -> bool:
        return self._wide

    def _corner_row(self):
        """The bottom line of the strip's right-hand end — whatever was handed
        over as the lead widget, pushed into the corner."""
        foot = QHBoxLayout()
        foot.addStretch(1)
        if self._lead is not None:
            foot.addWidget(self._lead, 0, Qt.AlignmentFlag.AlignBottom)
        return foot

    def _relayout(self):
        """Put the blocks into a fresh body in the current arrangement. They are
        re-parented by being added, so the body they leave behind goes out
        empty — nothing of the card is rebuilt, only where it stands."""
        body = QWidget()
        lyt = QVBoxLayout(body)
        pad = 6 if self._wide else 8
        lyt.setContentsMargins(10, pad, 10, pad)
        lyt.setSpacing(4)
        if self._wide:
            # Split down the middle: on the left everything the operator SEES
            # and HITS while a song runs — what is playing, how long it still
            # has, the transport and the seek bar under it, all in one column
            # the eye never has to leave. The settings that are dialled in
            # between songs — the faders, the fade-out, the tempo switches —
            # stand out of that way on the right.
            row = QHBoxLayout()
            row.setSpacing(16)
            left = QVBoxLayout()
            left.setSpacing(4)
            left.addWidget(self._head_box)
            # Clock and transport share a row: stacked they would push the
            # strip a third deeper, and every pixel here is one the playlists
            # under it lose. Both sit hard against the left edge — the play
            # button belongs next to the clock it drives, not drifting off
            # towards the middle of the screen because there was room.
            clock = QHBoxLayout()
            clock.setSpacing(10)
            clock.addWidget(self._time_box, 0)
            clock.addWidget(self._btn_box, 0)
            clock.addStretch(1)
            left.addLayout(clock)
            right = QVBoxLayout()
            right.setSpacing(4)
            right.addWidget(self._aux_box)
            right.addWidget(self._vol_box)
            right.addWidget(self._tempo_box)
            right.addStretch(1)
            # Nothing of the card is stretched to fill. Alone, it keeps to
            # the two edges — player left, its own settings right — and the
            # monitor's spare width falls between them. With a guest the card
            # closes up on the left instead and the guest takes the whole
            # right: a light panel wants an edge to sit against, not a hole in
            # the middle of the dark.
            if self._extra is not None:
                # The seek bar runs under BOTH of the player's columns. Left
                # to the first one it would be as narrow as the transport
                # above it — and a scrub bar is only as fine as it is long.
                player = QVBoxLayout()
                player.setSpacing(4)
                top = QHBoxLayout()
                top.setSpacing(16)
                top.addLayout(left, 0)
                top.addLayout(right, 0)
                player.addLayout(top)
                player.addWidget(self._slider)
                # The strip is as deep as its deepest guest; the player itself
                # stays the height it is and keeps to the top rather than
                # being pulled apart to fill it.
                player.addStretch(1)
                row.addLayout(player, 0)
                # The guest and the mode switch share the right-hand end: the
                # panel takes all the height it wants and the switch sits in
                # the corner under it, hard against both edges of the card.
                far = QVBoxLayout()
                far.setSpacing(4)
                far.addWidget(self._extra, 1)
                far.addLayout(self._corner_row())
                row.addLayout(far, 1)
            else:
                left.addWidget(self._slider)
                left.addStretch(1)
                row.addLayout(left, 0)
                row.addStretch(1)
                right.addLayout(self._corner_row())
                row.addLayout(right, 0)
            lyt.addLayout(row)
        else:
            for w in (self._head_box, self._time_box, self._slider,
                      self._btn_box, self._aux_box, self._vol_box,
                      self._tempo_box):
                lyt.addWidget(w)
        # Wide, the card asks for ~840 px. Reported as a minimum that would
        # pin the whole window to it and stop it being resized narrower (same
        # reason the deck toolbar yields its width) — so let it shrink and
        # let the blocks elide instead.
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored if self._wide
            else QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred)
        old, self._body = self._body, body
        self.layout().replaceWidget(old, body)
        old.setParent(None)
        old.deleteLater()
        # New body, same rule: the decks own Space / Ctrl+←→, so nothing in
        # the card ever takes the keyboard.
        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ── Fed by MainWindow on every play/stop ──

    def set_player(self, player: QMediaPlayer):
        """Retarget the card (seek bar, times, ⏯) to another QMediaPlayer —
        used for the pause-music filler while the between-songs pause runs,
        so the slider drags the FILLER and not the preloaded next song."""
        if player is self._player:
            return
        # Another player, another timeline — the 🐂 marks of the song that was
        # on the bar mean nothing on the filler (or back again).
        self.set_pd_marks([])
        old = self._player
        old.durationChanged.disconnect(self._on_duration)
        old.positionChanged.disconnect(self._on_position)
        old.playbackStateChanged.disconnect(self._on_state)
        self._player = player
        player.durationChanged.connect(self._on_duration)
        player.positionChanged.connect(self._on_position)
        player.playbackStateChanged.connect(self._on_state)
        self._on_duration(player.duration())
        self._on_position(player.position())
        self._on_state(player.playbackState())

    def set_now(self, title: str, subtitle: str = "", status: str = "",
                sub_icon: str = ""):
        """Show the playing song; title '' → idle, displaying `status` (e.g.
        the auto-advance pause) or 'No song selected'. `sub_icon` is a shared.icons
        name painted in front of the subtitle (the pause state)."""
        self._full_title = title or status or "No song selected"
        self._marquee_pos = 0
        # A real title means a song is playing → offer ⏸♪ jump-to-pause; an
        # empty title is idle or the pause filler (status set), so hide it.
        self._has_song = bool(title)
        self._refresh_aux_buttons()
        if title:
            self._title.setStyleSheet(
                "font-size:13px; font-weight:bold; color:#eef3fb;")
            # The idle branch below zeroed the length. A 🔁 title reloads the
            # SAME file, which sends no new durationChanged — so ask for it,
            # or the seek bar stays 0 long and every drag lands on 0.
            self._on_duration(self._player.duration())
        else:
            self._title.setStyleSheet(
                "font-size:13px; font-style:italic; color:#6e87ad;")
            self._slider.setRange(0, 0)
            self._elapsed.setText("00:00")
            self._remaining.setText("-00:00")
            self._gain_lbl.setText("")
            self._gain_icon.setVisible(False)
            self._dur = 0
            self._limit_ms = None
            self._limit_to_end = False
            self._limit_lbl.setText("")
            self._takt = None
            self._refresh_tempo_lbl()
            self._stop_end_flash()
            self.set_next_up("")   # nothing running → nothing "next"
            self.set_pd_marks([])
        if sub_icon:
            self._sub_icon.setPixmap(icon_pixmap(sub_icon, 12, "#8fa3c4"))
        self._sub_icon.setVisible(bool(sub_icon))
        self._full_sub = subtitle
        self._elide_sub()
        # The fade-out / aux buttons may have just (un)hidden, so the subtitle's
        # width changes only after the layout settles — re-elide on the next tick.
        QTimer.singleShot(0, self._elide_sub)
        self._elide_title()

    def set_pause_available(self, on: bool):
        """⏸♪ only works when there IS a between-songs pause to jump into.

        With 'Pause between songs' unticked the button would end the song and
        then report that nothing happened — greyed out it says so before the
        press instead of after it."""
        self._topause_btn.setEnabled(bool(on))
        self._topause_btn.setToolTip(
            "Jump straight to the pause music — end this song now and start\n"
            "the between-songs pause (e.g. the dancers are already leaving)."
            if on else
            "No pause to jump to — tick 'Pause between songs' (and ⏭\n"
            "auto-advance) in the Playing-mode panel first.")

    def set_artwork_enabled(self, on: bool):
        """🖼 Show the cover next to the title, or give the width back."""
        self._art_on = bool(on)
        self._art.setVisible(self._art_on)
        self._refresh_artwork()

    def set_artwork(self, track: Path | None, playlist: Path | None = None):
        """The track now playing and the playlist it came from — the picture is
        the playlist's if it has one, the track's own cover otherwise."""
        self._art_track = track
        self._art_list = playlist
        self._refresh_artwork()

    def _refresh_artwork(self):
        if not self._art_on:
            return
        if self._art_track is None:
            self._art.clear()
            return
        self._art.setPixmap(cover(self._art_track, self._art_list, _ART_PX))

    def set_gain(self, factor: float):
        """Show the R128 equalization gain of the playing track (1.0 → none)."""
        if abs(factor - 1.0) < 0.005:
            self._gain_lbl.setText("")
            self._gain_icon.setVisible(False)
            return
        db = 20 * math.log10(factor) if factor > 0 else 0.0
        self._gain_lbl.setText(f"{db:+.1f} dB")
        self._gain_icon.setVisible(True)

    def set_takt(self, takt: int | None):
        """Filename takt (bars/min) of the playing track — lets the tempo
        label show the resulting takt next to the percentage."""
        self._takt = takt
        self._refresh_tempo_lbl()

    def set_current_dance(self, dance: str | None):
        """Playing track's dance code — feeds the ♪ Takt overlay's Sollwert
        default. A no-op until that overlay has been opened at least once."""
        self._current_dance = dance
        if self._takt_overlay is not None:
            self._takt_overlay.set_dance(dance)

    def _toggle_takt_overlay(self, on: bool):
        if on:
            if self._takt_overlay is None:
                from player.takt_meter import TaktMeterOverlay
                self._takt_overlay = TaktMeterOverlay()
                self._takt_overlay.closeRequested.connect(
                    lambda: self._takt_btn.setChecked(False))
                self._takt_overlay.applyRequested.connect(
                    self.apply_takt_correction)
                self._takt_overlay.set_dance(self._current_dance)
            self._takt_overlay.show_near(self._takt_btn)
        elif self._takt_overlay is not None:
            self._takt_overlay.hide()

    def set_countdown(self, text: str):
        """Mirror the auto-advance pause countdown onto the card (MainWindow
        only feeds it while a pause is running — see _set_countdown)."""
        self._countdown_lbl.setText(text or "")

    def set_pause_active(self, on: bool):
        """Between-songs pause on/off: swaps the card's context buttons
        (⏸♪ jump-to-pause while playing ↔ ⏱➕ extend while paused) and clears
        the pause countdown when the pause ends."""
        self._is_paused = bool(on)
        if not self._is_paused:
            self._countdown_lbl.setText("")
        self._refresh_aux_buttons()

    def _refresh_aux_buttons(self):
        playing = self._has_song and not self._is_paused
        self._extend_btn.setVisible(self._is_paused)
        self._topause_btn.setVisible(playing)
        self._fade_btn.setVisible(playing)
        # …and the row with them: an empty block still costs the layout its
        # spacing, which is a gap in the card with nothing in it.
        self._aux_box.setVisible(playing or self._is_paused)

    # ── Drag a track onto the card to play it ──

    @staticmethod
    def _dropped_path(md) -> str:
        """Pull a local file path out of a drop's mime data (deck/library drags
        set both file URLs and a plain-text path fallback)."""
        for u in md.urls():
            if u.isLocalFile():
                return u.toLocalFile()
        if md.hasText():
            first = md.text().strip().splitlines()
            if first:
                return first[0].strip()
        return ""

    def dragEnterEvent(self, event):
        if self._dropped_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._dropped_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        path = self._dropped_path(event.mimeData())
        if path:
            event.acceptProposedAction()
            self.fileDropped.emit(path)
        else:
            super().dropEvent(event)

    def set_tempo_reset_on_track(self, on: bool):
        """Restore the reset-per-title preference (no signal) — the 📌 pin is
        its opposite: pinned means the tempo is NOT reset."""
        self._tempo_pin.blockSignals(True)
        self._tempo_pin.setChecked(not bool(on))
        self._tempo_pin.blockSignals(False)
        self._sync_tempo_pin()

    def tempo_reset_on_track(self) -> bool:
        return not self._tempo_pin.isChecked()

    def _sync_tempo_pin(self):
        """TSO owns the pitch while it runs, so the pin has nothing to hold: it
        comes off — and stays off and greyed out — until TSO is switched off."""
        on = self._tso_btn.isChecked()
        if on and self._tempo_pin.isChecked():
            self._tempo_pin.setChecked(False)   # the preference follows the pin
        self._tempo_pin.setEnabled(not on)

    def set_tso_mode(self, on: bool):
        """Restore the TSO auto-equalize toggle (no signal)."""
        self._tso_btn.blockSignals(True)
        self._tso_btn.setChecked(bool(on))
        self._tso_btn.blockSignals(False)
        self._sync_tempo_pin()

    def tso_mode(self) -> bool:
        return self._tso_btn.isChecked()

    def set_loop_mode(self, on: bool):
        """Put the 🔁 button where the caller wants it (the keyboard and the
        taskbar reach the loop through here, as they do the rest)."""
        self._loop_btn.setChecked(bool(on))

    def loop_mode(self) -> bool:
        """Whether the running title starts again instead of the next one.

        Deliberately not persisted anywhere: it is a decision about THIS
        moment, and an app that came back from a restart still looping one
        title would be a trap."""
        return self._loop_btn.isChecked()

    def on_new_track(self):
        """A new title is about to play — zero the fader if the user asked for
        it, so the next track starts at its natural tempo, and end any ♪ Takt
        measurement that is still standing: those taps were tapped along to the
        title that just went, and averaging the next ones against them would
        read a tempo neither track has."""
        if self.tempo_reset_on_track() and self._tempo.value() != 0:
            self._tempo.setValue(0)   # apply_tempo() right after pushes rate 1.0
        if self._takt_overlay is not None:
            self._takt_overlay.reset()

    def set_tempo_to_target(self, target_bpm: float) -> float | None:
        """Move the fader so the playing title (its takt = self._takt) is pitched
        to target_bpm, clamped to the fader's ±16 % range. Returns the takt the
        title now actually plays at — a half takt is a real answer here, so it
        is not rounded — or None when no takt / target is known."""
        if not self._takt or target_bpm <= 0:
            return None
        pct = (target_bpm / self._takt - 1.0) * 100.0
        val = max(-160, min(160, round(pct * 10)))   # fader steps are 0.1 %
        self._tempo.setValue(val)
        self.apply_tempo()   # apply at once — this is a deliberate, single set
        return self._takt * (1.0 + val / 1000.0)

    def apply_takt_correction(self, pct: float):
        """Push the fader by the ♪ Takt overlay's measured correction. The
        current fader position already contributed to the tapped tempo, so
        the correction compounds onto it rather than replacing it."""
        current_rate = 1.0 + self._tempo.value() / 1000.0
        new_rate = current_rate * (1.0 + pct / 100.0)
        val = max(-160, min(160, round((new_rate - 1.0) * 1000)))
        self._tempo.setValue(val)
        self.apply_tempo()   # apply at once — this is a deliberate, single set

    def _tempo_step_btn(self, text: str, delta: int, word: str) -> QToolButton:
        """One of the − / + buttons beside the tempo fader."""
        b = QToolButton()
        b.setText(text)
        # The step and its percent sign travel together as one value: a literal
        # %% in a catalog key would be the only one in the catalog, and the
        # number is a number in every language anyway.
        b.setToolTip(i18n.t("Tempo %s %s — hold to glide")
                     % (f"{_TEMPO_STEP / 10:.1f} %", word))
        b.setAutoRepeat(True)
        b.setAutoRepeatDelay(400)
        b.setAutoRepeatInterval(110)
        b.setStyleSheet(
            "QToolButton { font-size:14px; font-weight:bold; padding:0 5px; }")
        b.clicked.connect(lambda _checked=False, d=delta: self._nudge_tempo(d))
        return b

    def _nudge_tempo(self, delta: int):
        """Step the fader by one − / + click. setValue clamps to the range, so
        holding a button at either end simply stops there."""
        self._tempo.setValue(self._tempo.value() + delta)

    def _on_tempo(self, _value: int):
        self._refresh_tempo_lbl()   # readout follows the fader instantly
        # While the handle is held, hold off. Applying the rate as the fader
        # moves was tried and is worse: every setPlaybackRate re-inits the
        # backend's resampler, so the music breaks up under the thumb for the
        # whole length of the drag. The readout is what follows live; the sound
        # changes once, when the handle is let go. Only non-drag changes
        # (wheel / arrow keys / the − + buttons) go through the timer.
        if self._tempo.isSliderDown():
            self._tempo_apply.stop()
        else:
            # A click on the groove jumps the fader there but may still turn into
            # a double-click reset — hold the rate change until that is ruled
            # out, so the reset isn't preceded by a gap at a tempo nobody asked
            # for. Wheel / arrow keys keep the short debounce.
            self._tempo_apply.start(
                QApplication.doubleClickInterval() + 60
                if self._tempo.click_pending() else 220)

    def _on_tempo_released(self):
        self._tempo_apply.stop()
        if self._tempo.click_pending():
            # Let go this fast and it was a click, not a drag — and a click can
            # still become the double-click reset. Same hold-off as above: wait
            # it out rather than pitch the song to a value about to be undone.
            self._tempo_apply.start(QApplication.doubleClickInterval() + 60)
            return
        self.apply_tempo()   # one rate change per drag, so one short gap at most

    def reset_tempo(self):
        """Back to the track's natural tempo — the 0 button and a double-click
        on the fader. Applied at once, not debounced: this is a deliberate
        single set, usually made because the pitch is audibly wrong."""
        self._tempo_apply.stop()
        self._tempo.setValue(0)
        self.apply_tempo()

    def apply_tempo(self):
        """Push the fader's rate to the MAIN player — debounced after fader
        moves and re-asserted when a track starts (a rate set while idle can
        be dropped). If the backend hiccups and halts on the rate change,
        kick playback straight back on."""
        p = self._tempo_player
        target = 1.0 + self._tempo.value() / 1000.0
        # The ffmpeg backend re-inits its resampler on every setPlaybackRate,
        # which is the audible gap. Skip the call when the rate is already what
        # we want, so the _on_state re-assert and idle kicks don't hiccup the
        # sound for no reason.
        if abs(p.playbackRate() - target) < 0.0005:
            return
        was_playing = (p.playbackState()
                       == QMediaPlayer.PlaybackState.PlayingState)
        # The rate change is the one thing we do to a RUNNING track that makes
        # the backend tear its session down and build it again — the gap the
        # comment above warns about. If a title falls silent shortly after it
        # started, this line says whether we asked for that.
        log.info("🎛 Playback rate change\n"
                 "from: %.4f\n"
                 "to: %.4f\n"
                 "playing: %s\n"
                 "position: %d ms", p.playbackRate(), target, was_playing,
                 p.position())
        p.setPlaybackRate(target)
        if was_playing and (p.playbackState()
                            != QMediaPlayer.PlaybackState.PlayingState):
            p.play()
        # The timed cut is wall-clock, so the file position it lands on moves
        # with the rate — MainWindow re-computes the ⏳ limit from here.
        self.tempoApplied.emit()

    # ── Master volume ──

    def _on_vol_changed(self, v: int):
        self._set_vol(v / 100.0)
        self._refresh_vol_lbl()

    def _refresh_vol_lbl(self):
        self._vol_lbl.setText("duck" if self._ducked else f"{self._vol.value()}%")
        self._vol_lbl.setStyleSheet(
            "font-size:11px; font-family:Consolas,monospace;"
            + ("color:#d98f3a;" if self._ducked else "color:#8fa3c4;"))

    def toggle_duck(self):
        """🔉 Ask for a fifth of the volume (or full again). Ducking beats
        muting at the desk: a word over the music doesn't need a hole in the
        round."""
        self.duckToggled.emit(not self._ducked)
        self._duck_btn.setChecked(self._ducked)

    def set_ducked(self, on: bool):
        """The state MainWindow settled on — it owns the volume factor, and
        the filler music on its own output follows the same one. The button
        follows this, never the click, so card and overlay can't disagree."""
        self._ducked = bool(on)
        self._duck_btn.setIcon(icon("volume_low" if self._ducked else "volume",
                                    16, _CARD_INK))
        self._duck_btn.setChecked(self._ducked)
        self._refresh_vol_lbl()

    def set_volume_value(self, vol: float):
        """Show a volume set elsewhere (settings restore, preview overlay slider)
        without echoing it back through _set_vol."""
        self._vol.blockSignals(True)
        self._vol.setValue(max(0, min(100, round(vol * 100))))
        self._vol.blockSignals(False)
        self._refresh_vol_lbl()

    def _refresh_tempo_lbl(self):
        v = self._tempo.value()
        txt = f"{v / 10.0:+.1f}%" if v else "±0.0%"
        if self._takt:
            txt += f" → T{_takt_text(self._takt * (1.0 + v / 1000.0))}"
        self._tempo_lbl.setText(txt)
        self._tempo_lbl.setStyleSheet(
            "font-size:11px; font-family:Consolas,monospace;"
            + ("color:#d8b35c;" if v else "color:#8fa3c4;"))

    def set_limit(self, ms: int | None, glyph: str = "hourglass",
                  to_end: bool = False):
        """Adjusted end of playback in ms (timed cut / PD highlight stop); None →
        playback runs to the track's natural end. `glyph` is a shared.icons name
        (the sand clock for a timed cut, the highlight marker for a PD stop);
        `to_end=True` keeps it visible (as `glyph ⟶ full`) for a stop that
        resolves to the very end — e.g. a PD whose finale highlight is the
        song's own ending."""
        self._limit_ms = int(ms) if ms else None
        self._limit_glyph = glyph
        self._limit_to_end = bool(to_end) and self._limit_ms is None
        self._apply_range()
        self._update_time(self._player.position())
        self._refresh_limit()

    def _end_ms(self) -> int:
        """Where playback ACTUALLY ends: the armed limit, else the track end."""
        if self._limit_ms and 0 < self._limit_ms < self._dur:
            return self._limit_ms
        return self._dur

    def _apply_range(self):
        # The seek bar (and with it the -remaining readout) runs to the
        # actual end of playback, not the file's full length.
        self._slider.setRange(0, self._end_ms())

    def _refresh_limit(self):
        if self._limit_ms and 0 < self._limit_ms < self._dur:
            self._limit_lbl.setText(
                f"{icon_html(self._limit_glyph, 11, WARN)} {_fmt_ms(self._limit_ms)}"
                f" / {_fmt_ms(self._dur)}")
        elif self._limit_to_end and self._dur > 0:
            # Stop armed but it lands on the track's own end → "plays through".
            self._limit_lbl.setText(f"{icon_html(self._limit_glyph, 11, WARN)} "
                                    f"⟶ {_fmt_ms(self._dur)}")
        else:
            self._limit_lbl.setText("")

    def set_pd_marks(self, marks_secs, armed_secs=None):
        """Draw the Paso Doble highlights on the seek bar. Highlights beyond
        the armed stop fall outside the bar's range and simply aren't shown."""
        self._slider.set_marks([int(s * 1000) for s in (marks_secs or [])],
                               int(armed_secs * 1000) if armed_secs else None)

    def set_next_up(self, text: str):
        """Show what plays after this title (⏭ …) or that the round ends here."""
        self._full_next = text or ""
        self._elide_next()

    def _elide_next(self):
        if not self._labels_alive():
            return
        fm = self._next_lbl.fontMetrics()
        avail = max(20, self._next_lbl.width())
        self._next_lbl.setText(
            fm.elidedText(self._full_next, Qt.TextElideMode.ElideRight, avail))

    def _labels_alive(self):
        """False once Qt has begun deleting this row's children. A window being
        torn down still resizes the row, and set_now_playing leaves a queued
        re-elide behind — both can land after the labels are gone, and eliding a
        destroyed label raises out of the event handler."""
        return all(shiboken6.isValid(lbl)
                   for lbl in (self._title, self._sub, self._next_lbl))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide_title()
        self._elide_sub()
        self._elide_next()

    def _elide_sub(self):
        """Elide the subtitle (dance · takt · 🥁 bpm) to the label's width so it
        can't spill under the fade-out / aux buttons at the row's right edge."""
        if not self._labels_alive():
            return
        fm = self._sub.fontMetrics()
        avail = max(20, self._sub.width())
        self._sub.setText(
            fm.elidedText(self._full_sub, Qt.TextElideMode.ElideRight, avail))

    def _elide_title(self):
        if not self._labels_alive():
            return
        fm = self._title.fontMetrics()
        avail = max(40, self.width() - 28)
        if fm.horizontalAdvance(self._full_title) <= avail:
            self._marquee.stop()
            self._title.setText(self._full_title)
            return
        # Too wide → walking text so the whole title can be read.
        if not self._marquee.isActive():
            self._marquee.start()
        self._marquee_step()

    def _marquee_step(self):
        s = self._full_title + "   •   "
        pos = self._marquee_pos % len(s)
        self._marquee_pos = pos + 1
        fm = self._title.fontMetrics()
        avail = max(40, self.width() - 28)
        self._title.setText(fm.elidedText(
            s[pos:] + s[:pos], Qt.TextElideMode.ElideRight, avail))

    # ── Player feedback ──

    def _on_duration(self, dur: int):
        self._dur = max(0, dur)
        self._apply_range()   # duration arrives async, after set_limit
        self._update_time(self._player.position())
        self._refresh_limit()

    def _on_position(self, pos: int):
        if not self._dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(pos)
            self._slider.blockSignals(False)
            self._update_time(pos)

    def _on_state(self, state):
        if self._pause_btn:
            halted = state != QMediaPlayer.PlaybackState.PlayingState
            self._pause_btn.setIcon(icon(
                "play_circle" if halted else "pause_circle", 24, _CARD_INK))
        if state != QMediaPlayer.PlaybackState.PlayingState:
            self._stop_end_flash()   # never keep blinking once playback halts
        if (state == QMediaPlayer.PlaybackState.PlayingState
                and self._player is self._tempo_player):
            # A rate set while idle may have been dropped — re-assert it, but
            # only when it differs (apply_tempo's play() kick could otherwise
            # ping-pong with this handler on a flaky rate change).
            target = 1.0 + self._tempo.value() / 1000.0
            if abs(self._player.playbackRate() - target) > 0.0005:
                self.apply_tempo()

    def _update_time(self, pos: int):
        dur = self._slider.maximum()
        remaining = max(0, dur - pos)
        self._elapsed.setText(_fmt_ms(pos))
        self._remaining.setText(f"-{_fmt_ms(remaining)}")
        self._update_end_flash(remaining, dur)

    def _update_end_flash(self, remaining: int, dur: int):
        """Blink the card red while the song is in its final seconds, so the
        end is unmissable at a glance from the desk. Only flashes while a track
        is actually playing toward its (possibly limited) end."""
        playing = (self._player.playbackState()
                   == QMediaPlayer.PlaybackState.PlayingState)
        # Only the main player warns — not the pause-music filler the card is
        # temporarily retargeted to between songs.
        warn = (playing and self._player is self._tempo_player
                and dur > 0 and 0 < remaining <= self._END_FLASH_MS)
        if warn:
            if not self._flash.isActive():
                self._flash.start()
                self._flash_step()
            # Not tied to starting the beat: a fade started first has the timer
            # running already, and the seek bar would then stay blue through
            # the final stretch it is supposed to mark.
            if self._slider.styleSheet() != self._seek_end_qss:
                self._slider.setStyleSheet(self._seek_end_qss)
        elif not warn and self._flash.isActive() and not self._fading:
            self._stop_end_flash()

    def set_fading(self, on: bool):
        """Blink the card ORANGE while a fade-out ramps the song down.

        🔉↓ and 🛑 work silently: the volume slides away over several seconds
        and nothing on the desk says it is happening. This is the same beat as
        the red end-of-track warning in the colour of a deliberate act — and it
        wins over the red while both are true, because the fade is the thing
        the operator just asked for."""
        on = bool(on)
        if on == self._fading:
            return
        self._fading = on
        if on:
            self._flash_on = False
            self._flash.start()
            self._flash_step()
        else:
            # Back to normal; the red end warning restarts itself on the next
            # position tick if the song is still running into its end.
            self._stop_end_flash()

    def _flash_step(self):
        self._flash_on = not self._flash_on
        skin = self._fade_qss if self._fading else self._flash_qss
        self.setStyleSheet(skin if self._flash_on else self._base_qss)

    def _stop_end_flash(self):
        self._flash.stop()
        self._flash_on = False
        self._fading = False
        self.setStyleSheet(self._base_qss)
        self._slider.setStyleSheet("")   # seek bar back to blue

    # ── Controls ──

    def _on_slider_pressed(self):
        self._dragging = True

    def _on_slider_moved(self, value: int):
        self._update_time(value)

    def _on_slider_released(self):
        self._dragging = False
        self._player.setPosition(self._slider.value())

    def _skip(self, delta_ms: int):
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def _toggle_pause(self):
        st = self._player.playbackState()
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif st == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        elif self.resume_cb and self.resume_cb():
            pass   # 🏁 round-end stop → started the next round's first song
        elif not self._player.source().isEmpty():
            # Stopped but a track is still loaded → (re)start it from 0:00.
            self._player.play()

    def toggle_play(self):
        """Public play/pause toggle (Space key) — same as clicking ⏯."""
        self._toggle_pause()

    def _seek_to_start(self):
        """Rewind the playhead to 0:00, leaving play/pause state untouched."""
        if not self._player.source().isEmpty():
            self._player.setPosition(0)
