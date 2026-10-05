"""Manual tap-tempo measurement: tap along to a track's beat by hand and read
its live tempo back, next to a target and the % it is off by — a TopTurnier-
style cross-check independent of the app's own BPM analysis or its automatic
TSO tempo-pitching.
"""
import time

import planner.models

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from shared.icons import button as icon_button

_INK = "#cfe0f5"
_DIM = "#8fa3c4"
_GOOD = "#7fd4a0"
_ACCENT = "#4a82d2"
_GAIN = "#d8b35c"    # same as the tempo fader's own pitch readout
_BAD = "#e53935"     # same red as the end-of-track warning

_KORREKTUR_WARN_PCT = 2.5
# A gap this many times the running mean interval is a pause in the tapping,
# not a bar: the reading starts over from the tap after it.
_PAUSE_FACTOR = 2.5


class TapTempoMeter:
    """Tracks Takt taps since the last reset and derives one tempo reading
    averaged over the whole tapped span — settles to a stable number rather
    than jittering with every single interval."""

    def __init__(self):
        self._taps: list[float] = []

    def reset(self):
        self._taps = []

    def tap(self, now: float) -> float | None:
        if len(self._taps) >= 2:
            mean = (self._taps[-1] - self._taps[0]) / (len(self._taps) - 1)
            if now - self._taps[-1] > _PAUSE_FACTOR * mean:
                self._taps = []
        self._taps.append(now)
        return self.takte_per_minute()

    def takte_per_minute(self) -> float | None:
        if len(self._taps) < 2:
            return None
        span = self._taps[-1] - self._taps[0]
        return 60.0 * (len(self._taps) - 1) / span if span > 0 else None


def default_sollwert(dance: str | None) -> float | None:
    """Midpoint of the dance's TEMPO_RANGES band, or None if the dance is
    unknown/absent. The class key doesn't matter — every class holds the same
    range (see planner.models.TEMPO_RANGES)."""
    if not dance:
        return None
    rng = planner.models.TEMPO_RANGES.get(dance, {}).get("S")
    if not rng:
        return None
    lo, hi = rng
    return (lo + hi) / 2.0


class TaktMeterOverlay(QFrame):
    """Small floating card: Reset / Takt buttons, a live Taktzahl readout, an
    editable Sollwert target and the resulting Notwendige Taktkorrektur — all
    display-only, no effect on playback."""

    closeRequested = Signal()
    applyRequested = Signal(float)   # the Notwendige Taktkorrektur, in percent

    _TAP_QSS = (
        f"QPushButton {{ font-weight:bold; background:{_ACCENT};"
        " border:1px solid #6a9de0; }"
        "QPushButton:hover { background:#5a92dc; }")
    _TAP_FLASH_QSS = (
        f"QPushButton {{ font-weight:bold; background:{_GOOD};"
        f" border:1px solid {_GOOD}; color:#10241a; }}")

    def __init__(self):
        super().__init__(None)   # reparented into the anchor's window on show_near()
        self._meter = TapTempoMeter()
        self._dance: str | None = None
        self._sollwert_auto = True
        self._pct = 0.0
        self._drag_off: QPoint | None = None
        self._user_pos: QPoint | None = None
        self._anchor: QWidget | None = None
        self._last_press: tuple | None = None
        self._tap_flash = QTimer(self)
        self._tap_flash.setSingleShot(True)
        self._tap_flash.setInterval(150)
        self._tap_flash.timeout.connect(self._end_tap_flash)
        self.setObjectName("TaktMeterOverlay")
        self.setStyleSheet(
            "#TaktMeterOverlay { background:#2c3752;"
            " border:2px solid %(accent)s; border-radius:6px; }"
            "QLabel { color:%(ink)s; font-size:11px; background:transparent; }"
            "QPushButton, QToolButton { color:%(ink)s; background:#3d4b6e;"
            " border:1px solid #55668f; border-radius:4px; padding:3px 8px; }"
            "QPushButton:hover, QToolButton:hover { background:#4f5f88; }"
            "QPushButton:pressed, QToolButton:pressed { background:%(accent)s; }"
            "QPushButton:disabled, QToolButton:disabled { color:%(dim)s;"
            " background:#333d54; border-color:#333d54; }"
            "QDoubleSpinBox { background:#3d4b6e; color:%(ink)s;"
            " border:1px solid #55668f; border-radius:4px; padding:1px 3px; }"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {"
            " background:#55668f; width:16px; border-left:1px solid #6a7cab; }"
            "QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {"
            " background:%(accent)s; }"
            "QDoubleSpinBox::up-arrow { width:0; height:0; margin:3px;"
            " border-left:4px solid transparent; border-right:4px solid transparent;"
            " border-bottom:5px solid %(ink)s; }"
            "QDoubleSpinBox::down-arrow { width:0; height:0; margin:3px;"
            " border-left:4px solid transparent; border-right:4px solid transparent;"
            " border-top:5px solid %(ink)s; }"
            % {"ink": _INK, "dim": _DIM, "accent": _ACCENT}
        )

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(8, 6, 8, 8)
        lyt.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(4)
        title = QLabel("♪ Takt meter")
        title.setStyleSheet("font-weight:bold; color:#eef3fb;")
        title.setCursor(Qt.CursorShape.OpenHandCursor)
        title.setToolTip("Drag here to move")
        self._title = title
        top.addWidget(title, stretch=1)
        close_btn = QToolButton()
        icon_button(close_btn, "close", 11, _INK)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.closeRequested.emit)
        top.addWidget(close_btn)
        lyt.addLayout(top)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset)
        btn_row.addWidget(reset_btn)
        self._tap_btn = QPushButton("♪ Takt")
        self._tap_btn.setStyleSheet(self._TAP_QSS)
        self._tap_btn.clicked.connect(self._on_tap)
        btn_row.addWidget(self._tap_btn, stretch=1)
        lyt.addLayout(btn_row)

        taktzahl_row = QHBoxLayout()
        taktzahl_row.addWidget(QLabel("Takt count:"))
        self._taktzahl_lbl = QLabel("—")
        self._taktzahl_lbl.setStyleSheet(f"font-weight:bold; color:{_INK};")
        taktzahl_row.addWidget(self._taktzahl_lbl)
        taktzahl_row.addStretch(1)
        lyt.addLayout(taktzahl_row)

        sollwert_row = QHBoxLayout()
        sollwert_row.addWidget(QLabel("Target:"))
        self._sollwert_spin = QDoubleSpinBox()
        self._sollwert_spin.setRange(0, 99.9)
        self._sollwert_spin.setDecimals(1)
        self._sollwert_spin.setSuffix(" Takt/min")
        self._sollwert_spin.valueChanged.connect(self._on_sollwert_edited)
        sollwert_row.addWidget(self._sollwert_spin)
        sollwert_row.addStretch(1)
        lyt.addLayout(sollwert_row)

        korrektur_row = QHBoxLayout()
        korrektur_row.addWidget(QLabel("Correction needed:"))
        self._korrektur_lbl = QLabel("0.0%")
        self._korrektur_lbl.setStyleSheet(f"color:{_DIM};")
        korrektur_row.addWidget(self._korrektur_lbl)
        korrektur_row.addStretch(1)
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setToolTip(
            "Apply this correction to the tempo fader.")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        korrektur_row.addWidget(self._apply_btn)
        lyt.addLayout(korrektur_row)

        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ── Tapping ──

    def _on_tap(self):
        self._meter.tap(time.monotonic())
        self._refresh()
        self._tap_btn.setStyleSheet(self._TAP_FLASH_QSS)
        self._tap_flash.start()

    def _end_tap_flash(self):
        self._tap_btn.setStyleSheet(self._TAP_QSS)

    def reset(self):
        """Throw the tapped span away so the next tap starts a fresh reading.

        The Reset button, but also what closing the card and loading a new
        title do: a span of taps only ever describes the title it was tapped
        on, at the fader position it was tapped at."""
        self._meter.reset()
        self._refresh()

    def _refresh(self):
        takt = self._meter.takte_per_minute()
        self._taktzahl_lbl.setText(f"{takt:.1f} Takte / Minute" if takt else "—")  # i18n: data
        sollwert = self._sollwert_spin.value()
        has_correction = bool(takt and sollwert)
        pct = (sollwert / takt - 1.0) * 100.0 if has_correction else 0.0
        self._pct = pct
        significant = abs(pct) >= 0.05
        self._korrektur_lbl.setText(f"{pct:+.1f}%" if significant else "0.0%")
        if significant:
            color = _BAD if abs(pct) > _KORREKTUR_WARN_PCT else _GAIN
            self._korrektur_lbl.setStyleSheet(f"font-weight:bold; color:{color};")
        else:
            self._korrektur_lbl.setStyleSheet(f"color:{_DIM};")
        self._apply_btn.setEnabled(has_correction and significant)

    def _on_apply(self):
        self.applyRequested.emit(self._pct)
        # The fader just moved, so the taps just measured describe a rate
        # that no longer plays — keeping them would let a second measurement
        # average itself against a stale span and read wrong.
        self.reset()

    # ── Sollwert ──

    def _on_sollwert_edited(self, _value: float):
        self._sollwert_auto = False
        self._refresh()

    def set_dance(self, dance: str | None):
        self._dance = dance
        if self._sollwert_auto:
            val = default_sollwert(dance)
            if val is not None:
                self._sollwert_spin.blockSignals(True)
                self._sollwert_spin.setValue(val)
                self._sollwert_spin.blockSignals(False)
        self._refresh()

    # ── Placement (same drag/anchor pattern as PreviewOverlay) ──

    def show_near(self, anchor: QWidget):
        """First open: appears to the right of `anchor`, top-aligned with it.
        A later open reuses wherever the user last dragged it to instead."""
        self._anchor = anchor
        par = anchor.window()
        if self.parentWidget() is not par:
            self.setParent(par)
        self.adjustSize()
        if self._user_pos is not None:
            self.move(self._clamped(self._user_pos, par))
        else:
            top_right = par.mapFromGlobal(anchor.mapToGlobal(
                QPoint(anchor.width() + 4, 0)))
            self.move(self._clamped(top_right, par))
        self.show()
        self.raise_()

    def _clamped(self, p: QPoint, par: QWidget) -> QPoint:
        return QPoint(
            max(2, min(p.x(), max(2, par.width() - self.width() - 2))),
            max(2, min(p.y(), max(2, par.height() - self.height() - 2))))

    # ── Click-away dismissal ──

    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def hideEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        # Closing the card ends the measurement — whether by the ✕, the toggle
        # or a click outside. Whatever was tapped belongs to the title that was
        # playing then, so the next open starts from nothing rather than
        # averaging new taps against a span from minutes ago.
        self.reset()
        super().hideEvent(event)

    def eventFilter(self, _obj, event):
        """A press anywhere outside the card closes it. Two exemptions: the
        card itself, and the anchor button — that one toggles the card off by
        itself, and closing here first would leave the toggle free to reopen
        it on the very same click. The hit test runs on screen coordinates
        because one press reaches this filter repeatedly as it propagates up
        the widget chain; `_last_press` keeps those repeats to one close."""
        if (event.type() == QEvent.Type.MouseButtonPress
                and self.isVisible()
                and isinstance(event, QMouseEvent)):
            press = (event.timestamp(), event.globalPosition().toPoint())
            if press != self._last_press:
                self._last_press = press
                if not (self._covers(self, press[1])
                        or self._covers(self._anchor, press[1])):
                    self.closeRequested.emit()
        return False

    @staticmethod
    def _covers(w: QWidget | None, global_pos: QPoint) -> bool:
        if w is None or not w.isVisible():
            return False
        return w.rect().contains(w.mapFromGlobal(global_pos))

    # ── Dragging ──

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if (event.button() == Qt.MouseButton.LeftButton
                and pos.y() <= self._title.geometry().bottom() + 2):
            self._drag_off = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_off is not None and self.parentWidget() is not None:
            self.move(self._clamped(
                self.pos() + event.position().toPoint() - self._drag_off,
                self.parentWidget()))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_off is not None:
            self._drag_off = None
            self._user_pos = self.pos()
            self.unsetCursor()
        event.accept()
