"""Keyboard help for a list of rows that each hold a choice combo.

Tab walks the combos, the row holding the focus is outlined, and a letter picks
the choice for it and moves on to the next row.

The outline is a transparent child widget that paints a frame, not a stylesheet:
setting a stylesheet on a row while the dialog opens inside a drag-and-drop
handler crashed the app (access violation in Qt6Widgets).
"""
from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QComboBox, QWidget


class _Outline(QWidget):
    """A highlight frame laid over its parent row; mouse clicks go through it."""

    def __init__(self, row: QWidget):
        super().__init__(row)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

    def paintEvent(self, _ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().highlight().color(), 2))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 3, 3)


class RowKeys(QObject):
    """`keys`: {Qt.Key: item data} for every combo given to `add`."""

    def __init__(self, parent: QObject, keys: dict):
        super().__init__(parent)
        self._keys = keys
        self._rows: dict = {}
        self._outlines: dict = {}

    def add(self, combo: QComboBox, row: QWidget):
        """Outline `row` while `combo` has the focus."""
        self._rows[combo] = row
        self._outlines[row] = _Outline(row)
        combo.installEventFilter(self)
        row.installEventFilter(self)

    def eventFilter(self, obj, ev):
        outline = self._outlines.get(obj)
        if outline is not None:                      # a row
            if ev.type() == QEvent.Type.Resize:
                outline.setGeometry(obj.rect())
            return super().eventFilter(obj, ev)
        row = self._rows.get(obj)
        if row is not None:
            kind = ev.type()
            if kind == QEvent.Type.FocusIn:
                shown = self._outlines[row]
                shown.setGeometry(row.rect())
                shown.raise_()
                shown.show()                  # a scroll area brings the focus into view
            elif kind == QEvent.Type.FocusOut:
                self._outlines[row].hide()
            elif kind == QEvent.Type.KeyPress and ev.key() in self._keys:
                idx = obj.findData(self._keys[ev.key()])
                if idx >= 0:
                    obj.setCurrentIndex(idx)
                    # setCurrentIndex stays silent; the owner listens to
                    # `activated` (a Replace… opens its picker from there).
                    obj.activated.emit(idx)
                    obj.focusNextChild()          # on to the next row
                return True
        return super().eventFilter(obj, ev)
