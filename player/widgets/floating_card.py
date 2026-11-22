"""A small card that floats over the main window next to the button that
opened it: ♪ Takt meter, 🎚 EQ.

First open: to the right of the anchor, top-aligned with it. Dragged by its
title (`self._title`, set by the subclass); a later open comes back where it
was dragged to. A press anywhere outside closes it (`closeRequested`), except
on the anchor itself and while a popup (a combo's list) or a modal dialog of
the card's own is open: those are other windows, and a press in them belongs
to the card.
"""
from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QFrame, QWidget

# The cards' dark look, one for all of them.
INK = "#cfe0f5"
DIM = "#8fa3c4"
ACCENT = "#4a82d2"
# Every card sets objectName "FloatingCard" so this frame rule finds it.
CARD_QSS = (
    "#FloatingCard { background:#2c3752;"
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
    % {"ink": INK, "dim": DIM, "accent": ACCENT}
)


class FloatingCard(QFrame):

    closeRequested = Signal()

    def __init__(self):
        super().__init__(None)   # reparented into the anchor's window on show_near()
        self.setObjectName("FloatingCard")
        self._drag_off: QPoint | None = None
        self._user_pos: QPoint | None = None
        self._anchor: QWidget | None = None
        self._last_press: tuple | None = None
        self._title: QWidget | None = None

    # ── Placement ──

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

    def refit(self) -> None:
        """Grow or shrink to what the content needs now and stay inside the
        window. A child widget's layout can't resize it by itself, so rows
        shown later (the EQ's ⚙ Advanced) were squeezed over the others."""
        self.adjustSize()
        par = self.parentWidget()
        if par is not None:
            self.move(self._clamped(self.pos(), par))

    def anchor(self) -> QWidget | None:
        return self._anchor

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
        super().hideEvent(event)

    def eventFilter(self, _obj, event):
        """A press anywhere outside the card closes it. Exemptions: the card
        itself, the anchor button (that one toggles the card off by itself, and
        closing here first would leave the toggle free to reopen it on the very
        same click), and a press while a popup or a modal dialog is up. The hit
        test runs on screen coordinates because one press reaches this filter
        repeatedly as it propagates up the widget chain; `_last_press` keeps
        those repeats to one close."""
        if (event.type() == QEvent.Type.MouseButtonPress
                and self.isVisible()
                and isinstance(event, QMouseEvent)):
            press = (event.timestamp(), event.globalPosition().toPoint())
            if press != self._last_press:
                self._last_press = press
                if not (self._covers(self, press[1])
                        or self._covers(self._anchor, press[1])
                        or QApplication.activePopupWidget() is not None
                        or QApplication.activeModalWidget() is not None):
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
        if (event.button() == Qt.MouseButton.LeftButton and self._title is not None
                and pos.y() <= self._title.geometry().bottom() + 2):
            self._drag_off = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        par = self.parentWidget()
        if self._drag_off is not None and par is not None:
            self.move(self._clamped(
                self.pos() + event.position().toPoint() - self._drag_off, par))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_off is not None:
            self._drag_off = None
            self._user_pos = self.pos()
            self.unsetCursor()
        event.accept()
