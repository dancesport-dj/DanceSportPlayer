"""💡 The generate hints under the decks.

Normal: every hint, wrapped. 📐 Compact: one line, the first hint and how
many more ("+3 more ▾"); the whole list in the tooltip and on a click.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel

from planner import i18n
from shared.plain_text import PLAIN, plain_tip

_SEP = "   "


class HintsLabel(QLabel):

    def __init__(self, compact: bool = False, parent=None):
        super().__init__(parent)
        self._compact = compact
        self._hints: list[str] = []
        self._open = False
        self.setTextFormat(PLAIN)    # the model's notes are no markup (7.C)
        self.setWordWrap(True)
        self.setStyleSheet(
            "background:#fff8e6; color:#7a5b00; border:1px solid #e6d28a;"
            "border-radius:4px; padding:4px 8px; font-size:11px;")
        self.setVisible(False)

    def set_hints(self, hints: list[str]):
        """Show these notes; none hides the bar. A new list starts folded."""
        self._hints = list(hints)
        self._open = False
        if not self._hints:
            self.clear()
            self.setToolTip("")
            self.setVisible(False)
            return
        self._render()
        self.setVisible(True)

    def set_compact(self, compact: bool):
        """📐 Follow the screen shape: one folded line, or every hint."""
        self._compact = compact
        self._open = False
        if self._hints:
            self._render()

    def _folds(self) -> bool:
        return self._compact and len(self._hints) > 1

    def _render(self):
        folded = self._folds() and not self._open
        self.setWordWrap(not folded)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self._folds()
                       else Qt.CursorShape.ArrowCursor)
        self.setToolTip(plain_tip("\n".join(self._hints) if self._folds() else ""))
        if not folded:
            text = _SEP.join(self._hints)
            self.setText(text + "   ▴" if self._folds() else text)
            return
        more = _SEP + i18n.t("+%d more ▾") % (len(self._hints) - 1)
        fm = self.fontMetrics()
        room = self.contentsRect().width() - 20 - fm.horizontalAdvance(more)
        first = fm.elidedText(self._hints[0], Qt.TextElideMode.ElideRight,
                              max(room, 40))
        self.setText(first + more)

    def minimumSizeHint(self) -> QSize:
        # Folded it cannot wrap: it gives way instead of widening the window.
        hint = super().minimumSizeHint()
        if self._folds() and not self._open:
            return QSize(0, hint.height())
        return hint

    def mousePressEvent(self, event):
        if self._folds() and event.button() == Qt.MouseButton.LeftButton:
            self._open = not self._open
            self._render()
            self.updateGeometry()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._folds() and not self._open:
            self._render()
