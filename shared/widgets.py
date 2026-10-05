"""Small widgets and helpers the desk and the evening both put on screen: the
flow layout, the app icon, the separator line, the play-button glyph and the
toast.
"""
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QLabel, QLayout, QWidget


class FlowLayout(QLayout):
    """A row of controls that breaks onto a second row instead of clipping.

    Qt ships no flow layout, and two panes need one: the cartwall's header has
    to survive a dock the user has dragged down to two pads wide, and the 🏆
    slot board wraps a folder's playlists across whatever width it is given.
    """

    def __init__(self, parent=None, spacing: int = 6):
        super().__init__(parent)
        self._items: list[object] = []
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
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_h > 0:
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
        self._fill_line(line, rect.right() + 1 - (x - space), apply)
        return y + line_h - rect.y()

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
_ICON_DIR  = Path(__file__).resolve().parents[1]
_ICON_ICO  = _ICON_DIR / "icon.ico"
_ICON_PNG  = _ICON_DIR / "icon.png"
_ICON_PATH = _ICON_ICO if _ICON_ICO.exists() else _ICON_PNG


def _app_icon() -> QIcon:
    """The app/window/taskbar icon — the .ico (all sizes) plus the PNG as a
    high-res fallback frame, so every context (taskbar, title bar, Alt-Tab) has
    a crisp size to pick from."""
    icon = QIcon()
    if _ICON_ICO.exists():
        icon.addFile(str(_ICON_ICO))
    if _ICON_PNG.exists():
        icon.addFile(str(_ICON_PNG))
    if icon.isNull():
        icon = QIcon(str(_ICON_PATH))
    return icon


def _hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    return f


def set_play_glyph(btn, playing: bool):
    """The ▶ / ■ toggle of a row's play button — the same two characters, in the
    same ink, as always."""
    btn.setText("■" if playing else "▶")
    btn.setStyleSheet("padding: 0;")
    return btn


def _show_toast(anchor: QWidget, text: str, msec: int = 1500) -> None:
    """Show a short, self-dismissing toast message over `anchor`'s window.

    One toast at a time per window. Mark a track and unmark it again and the
    second message arrives well inside the 1.5 s the first one lives — as two
    separate labels at the same spot they were drawn over each other, into a
    smudge of both texts. The window keeps one label and reuses it: the new
    message replaces the old one and restarts its clock."""
    win = anchor.window()
    lbl = getattr(win, "_toast_lbl", None)
    if lbl is None:
        lbl = QLabel(win)
        lbl.setStyleSheet(
            "background:#323232; color:white; padding:7px 14px;"
            "border-radius:6px; font-size:12px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Both parented to the window, so they go when it does.
        timer = QTimer(win)
        timer.setSingleShot(True)
        timer.timeout.connect(lbl.hide)
        win._toast_lbl = lbl
        win._toast_timer = timer
    lbl.setText(text)
    lbl.adjustSize()
    rect = win.rect()
    x = (rect.width() - lbl.width()) // 2
    y = rect.height() - lbl.height() - 24
    lbl.move(max(0, x), max(0, y))
    lbl.show()
    lbl.raise_()
    win._toast_timer.start(msec)
