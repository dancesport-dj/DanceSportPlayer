"""Small widgets and helpers the desk and the evening both put on screen: the
flow layout, the app icon, the separator line, the play-button glyph, the
toast and the double-click-to-type readout of a slider.
"""
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFrame,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QScrollBar,
    QSlider,
    QWidget,
)


class FlowLayout(QLayout):
    """A row of controls that breaks onto a second row instead of clipping.

    Qt ships no flow layout, and two panes need one: the cartwall's header has
    to survive a dock the user has dragged down to two pads wide, and the 🏆
    slot board wraps a folder's playlists across whatever width it is given.
    """

    def __init__(self, parent=None, spacing: int = 6):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    # QLayout's pure-virtual half
    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._lay_out(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._lay_out(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """One control wide — the whole point is that the rest wrap."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _lay_out(self, rect: QRect, apply: bool) -> int:
        x, y, line_h = rect.x(), rect.y(), 0
        space = self.spacing()
        line: list = []
        for item in self._items:
            if item.isEmpty():
                continue    # a hidden control takes no room, nor its spacing
            hint = item.sizeHint()
            # On a line narrower than its wish, a control that can shrink does.
            hint.setWidth(max(item.minimumSize().width(), min(hint.width(), rect.width())))
            if x + hint.width() > rect.right() + 1 and line_h > 0:
                self._centre_line(line, line_h, apply)
                self._fill_line(line, rect.right() + 1 - (x - space), apply)
                x = rect.x()
                y += line_h + space
                line_h = 0
                line = []
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            line.append(item)
            x += hint.width() + space
            line_h = max(line_h, hint.height())
        self._centre_line(line, line_h, apply)
        self._fill_line(line, rect.right() + 1 - (x - space), apply)
        return y + line_h - rect.y()

    @staticmethod
    def _centre_line(line: list, line_h: int, apply: bool) -> None:
        """A line's controls share one middle, as in a QHBoxLayout: a button
        beside a taller fader sits level with it, not on its top edge."""
        if not apply:
            return
        for item in line:
            box = item.geometry()
            box.moveTop(box.y() + (line_h - box.height()) // 2)
            item.setGeometry(box)

    @staticmethod
    def _fill_line(line: list, leftover: int, apply: bool) -> None:
        """Hand what is left of a finished line to the controls that want it.

        Wrapping alone would leave a search box sitting at its size hint with
        empty space beside it; a control whose size policy says Expanding gets
        that space, exactly as it would in a QHBoxLayout with a stretch.
        """
        if not apply or leftover <= 0:
            return
        greedy = [i for i in line
                  if i.expandingDirections() & Qt.Orientation.Horizontal]
        if not greedy:
            return
        share = leftover // len(greedy)
        shift = 0
        for item in line:
            box = item.geometry()
            box.moveLeft(box.x() + shift)
            if item in greedy:
                box.setWidth(box.width() + share)
                shift += share
            item.setGeometry(box)


# Resolve the bundled app icon relative to THIS file so it loads no matter what
# the working directory is when the GUI is launched (a bare "icon.png" failed
# whenever the app was started from another folder → blank taskbar icon).
# Prefer the multi-size .ico: Windows' taskbar wants 16/24/32/48 px frames, which
# a single big PNG doesn't carry, so a PNG-only QIcon shows up blank in the bar.
_ICON_DIR = Path(__file__).resolve().parents[1]
ICON_ICO = _ICON_DIR / "icon.ico"
_ICON_PNG = _ICON_DIR / "icon.png"
_ICON_PATH = ICON_ICO if ICON_ICO.exists() else _ICON_PNG


def app_icon() -> QIcon:
    """The app/window/taskbar icon — the .ico (all sizes) plus the PNG as a
    high-res fallback frame, so every context (taskbar, title bar, Alt-Tab) has
    a crisp size to pick from."""
    icon = QIcon()
    if ICON_ICO.exists():
        icon.addFile(str(ICON_ICO))
    if _ICON_PNG.exists():
        icon.addFile(str(_ICON_PNG))
    if icon.isNull():
        icon = QIcon(str(_ICON_PATH))
    return icon


def hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    return f


class _WheelGuard(QObject):
    """See guard_wheel: an unfocused input hands the wheel to the page."""

    def eventFilter(self, obj, event):
        if event.type() != QEvent.Type.Wheel or obj.hasFocus():
            return False
        area = obj.parentWidget()
        while area is not None and not isinstance(area, QAbstractScrollArea):
            area = area.parentWidget()
        if area is not None:
            QApplication.sendEvent(area.verticalScrollBar(), event)
        return True


def guard_wheel(root: QWidget):
    """Every spin box, combo and slider under `root` takes the wheel only once
    it has been clicked into; until then the wheel scrolls the page around it.

    Qt steps an input on any wheel notch over it, focus or not, so scrolling a
    long page changes whatever input passes under the pointer. The same rule
    as the player's ClickWheelSpinBox, for pages built from plain Qt inputs."""
    guard = _WheelGuard(root)
    for w in root.findChildren(QWidget):
        if (isinstance(w, (QAbstractSpinBox, QComboBox, QAbstractSlider))
                and not isinstance(w, QScrollBar)):
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            w.installEventFilter(guard)


def set_play_glyph(btn, playing: bool):
    """The ▶ / ■ toggle of a row's play button — the same two characters, in the
    same ink, as always."""
    btn.setText("■" if playing else "▶")
    btn.setStyleSheet("padding: 0;")
    return btn


# A toast that says something is wrong (a drive gone, a file not found) and
# names a path: it has to stay up long enough to be read.
WARN_TOAST_MS = 8000
# A toast that reports an error or a refusal — something that could not be
# done — sits on the mute red, so it is not read as one more "done".
ERROR_TOAST_BG = "#d9534f"
_TOAST_CSS = ("background:%s; color:white; padding:7px 14px;"
              "border-radius:6px; font-size:12px;")


def show_toast(anchor: QWidget, text: str, msec: int = 1500,
               error: bool = False) -> None:
    """Show a short, self-dismissing toast message over `anchor`'s window —
    in red with `error`.

    One toast at a time per window. Mark a track and unmark it again and the
    second message arrives well inside the 1.5 s the first one lives — as two
    separate labels at the same spot they were drawn over each other, into a
    smudge of both texts. The window keeps one label and reuses it: the new
    message replaces the old one and restarts its clock."""
    win = anchor.window()
    lbl = getattr(win, "_toast_lbl", None)
    timer = getattr(win, "_toast_timer", None)
    if lbl is None or timer is None:
        lbl = QLabel(win)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Titles, file names and guests' wishes: never markup.
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        # Both parented to the window, so they go when it does.
        timer = QTimer(win)
        timer.setSingleShot(True)
        timer.timeout.connect(lbl.hide)
        # Kept on the window itself, which QWidget does not declare.
        keep = cast(Any, win)
        keep._toast_lbl = lbl
        keep._toast_timer = timer
    # The label is shared: each message sets its own colour.
    lbl.setStyleSheet(_TOAST_CSS % (ERROR_TOAST_BG if error else "#323232"))
    lbl.setText(text)
    lbl.adjustSize()
    rect = win.rect()
    x = (rect.width() - lbl.width()) // 2
    y = rect.height() - lbl.height() - 24
    lbl.move(max(0, x), max(0, y))
    lbl.show()
    lbl.raise_()
    timer.start(msec)


class ClickableLabel(QLabel):
    """A QLabel that reports a double-click — Qt's does not."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()


class TypedValue(ClickableLabel):
    """A slider's readout that a double-click turns into a field.

    A slider is the right control for a level judged by ear and the wrong one
    for a number that is already known: 25 % and 1.5 s are quicker typed than
    aimed at, and a pad that has to match another one has to hit the figure
    exactly, not nearly."""

    def __init__(self, slider: QSlider, per_unit: int = 1, parent=None):
        super().__init__("", parent)
        self._slider = slider
        # Slider steps per typed unit: 1000 for a fade typed in seconds, 1 for
        # a volume typed in per cent.
        self._per_unit = per_unit
        self._edit = None       # built on first use
        self.setToolTip("Double-click to type a value")
        self.double_clicked.connect(self._open)

    def _open(self) -> None:
        """Put the field over the readout. Made once and then reused."""
        if not self._slider.isEnabled():
            return          # a pad following the wall's fade: nothing to set
        if self._edit is None:
            self._edit = QLineEdit(self)
            self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._edit.installEventFilter(self)
            self._edit.editingFinished.connect(self._commit)
        self._edit.setGeometry(self.rect())
        # The bare number, not the caption: "1.5 s (wall)" is what the reader
        # wants and "1.5" is what the typist wants to start from.
        self._edit.setText(f"{self._slider.value() / self._per_unit:g}")
        self._edit.show()
        self._edit.selectAll()
        self._edit.setFocus()

    def eventFilter(self, obj, event):
        """Both keys have to be caught here.

        Esc, because a QLineEdit swallows it without telling anyone. Enter,
        because a QLineEdit does the opposite — it commits and then hands the
        key on, and the next thing in line is the dialog's Ok button: typing a
        value and pressing Enter would shut the whole settings window."""
        edit = self._edit
        if edit is not None and obj is edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                edit.hide()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._commit()
                return True
        return super().eventFilter(obj, event)

    def _commit(self) -> None:
        """Enter, or the focus moving on. Nonsense is refused rather than
        guessed at, so a half-typed value leaves the slider where it was."""
        edit = self._edit
        if edit is None or edit.isHidden():
            return          # editingFinished comes again on the focus-out
        # The unit may be typed along with the number, and a German keyboard
        # puts a comma where float() wants a point.
        text = edit.text().strip().rstrip("s%dB ").replace(",", ".")
        edit.hide()
        try:
            typed = float(text)
            value = int(round(typed * self._per_unit))
        except (ValueError, OverflowError):    # "inf", "1e999", "nan"
            return
        # setValue clamps: 999 s of fade is not a fade, it is a stuck pad.
        self._slider.setValue(value)
