"""🔍 The find bar: the in-list search, floating at the top right of the list.

It stands over the column titles, so it hides no row, and the list stays usable
behind it. The list does the searching (`_find_step` in `table_actions.py`); the
bar only holds the two fields and says which way to go.
"""

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLineEdit, QToolButton

from gui.common import platform_keys
from planner import i18n
from shared.appearance.icons import icon


class FindBar(QFrame):
    """A title field, a genre field, back and forward like a PDF reader."""

    stepped = Signal(int)      # +1 forward, -1 back
    dismissed = Signal()
    edited = Signal()          # a field changed: tint the matches, no jump

    GAP = 20      # to the right edge of the list: clear of the scrollbar and the X
    WIDE = 480    # room for both fields; a narrower list gets what it has

    def __init__(self, table):
        super().__init__(table)
        self.setObjectName("findBar")
        self.setStyleSheet("#findBar { background: palette(window);"
                           " border: 1px solid palette(mid); border-radius: 4px; }")
        shadow = QGraphicsDropShadowEffect(self)     # lifts the bar off the list
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)
        lyt = QHBoxLayout(self)
        lyt.setContentsMargins(4, 2, 2, 2)
        lyt.setSpacing(2)
        self._title = self._field(lyt, platform_keys(i18n.t("Find title (Ctrl+F)")),
                                  "A word of the title, the tag title or the file name")
        self._genre = self._field(lyt, i18n.t("Genre / dance"),
                                  "Highlights every row of the list whose dance or genre matches -\n"
                                  "leave empty to search titles only.")
        self._title.textChanged.connect(lambda _t: self.edited.emit())
        self._genre.textChanged.connect(lambda _t: self.edited.emit())
        self._title.installEventFilter(self)
        self._genre.installEventFilter(self)
        self._prev = self._button(lyt, "caret_up", "Previous match (Shift+Enter)",
                                  lambda: self.stepped.emit(-1))
        self._next = self._button(lyt, "caret_down", "Next match (Enter)",
                                  lambda: self.stepped.emit(1))
        self._close = self._button(lyt, "close", "Close (Esc)", self.dismiss)
        # A click on a button that takes no focus hands it up to the first parent
        # that does: stop that here, or an arrow would pull the cursor into the list.
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocusProxy(self._title)

    @staticmethod
    def _field(lyt, placeholder: str, tip: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setToolTip(tip)
        edit.setClearButtonEnabled(True)
        lyt.addWidget(edit, 1)
        return edit

    @staticmethod
    def _button(lyt, name: str, tip: str, slot) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(icon(name))
        btn.setIconSize(QSize(14, 14))
        btn.setAutoRaise(True)
        btn.setToolTip(tip)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # the cursor stays in the field
        btn.clicked.connect(slot)
        lyt.addWidget(btn)
        return btn

    def title(self) -> str:
        return self._title.text().strip()

    def genre(self) -> str:
        return self._genre.text().strip()

    def open(self) -> None:
        """Show the bar with the last search marked, ready to type over."""
        self.place()
        self.show()
        self.raise_()
        self._title.setFocus()
        self._title.selectAll()

    def place(self) -> None:
        """Top right of the list, over the column titles."""
        table = self.parentWidget()
        if table is None:
            return
        width = min(self.WIDE, table.width() - 2 * self.GAP)
        self.setGeometry(table.width() - width - self.GAP, 0, width,
                         self.sizeHint().height())

    def clearFields(self) -> None:
        """Empty both fields and put the cursor back in the title."""
        self._genre.clear()
        self._title.clear()
        self._title.setFocus()

    def dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()

    def eventFilter(self, obj, e):
        """Tab / Shift+Tab swap between the two fields; the list behind the bar
        must not take the key."""
        if (obj in (self._title, self._genre) and e.type() == QEvent.Type.KeyPress
                and e.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab)):
            target = self._genre if obj is self._title else self._title
            target.setFocus()
            target.selectAll()
            return True
        if (obj in (self._title, self._genre) and e.type() == QEvent.Type.KeyPress
                and e.matches(QKeySequence.StandardKey.Cut)):
            obj.clear()          # Ctrl+X empties the whole field, not just a selection
            return True
        return super().eventFilter(obj, e)

    def event(self, e):
        # Esc is the bar's while it has the cursor, not a window shortcut's.
        if e.type() == QEvent.Type.ShortcutOverride and e.key() == Qt.Key.Key_Escape:
            e.accept()
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        """What the fields leave over. All of it stays here: behind the bar, Enter
        would start the selected title of the list."""
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            shift = e.modifiers() & Qt.KeyboardModifier.ShiftModifier
            self.stepped.emit(-1 if shift else 1)
        elif e.key() == Qt.Key.Key_Escape:
            self.dismiss()
        elif e.matches(QKeySequence.StandardKey.Find):
            self.dismiss()      # Ctrl+F again closes it
        e.accept()
