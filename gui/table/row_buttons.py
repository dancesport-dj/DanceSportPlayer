"""▶ / ↺ A deck row's buttons, painted by a delegate instead of cell widgets.

Every song row used to carry two QPushButton cell widgets. A start restores
~460 rows, and building, polishing and placing those ~930 widgets was ~0.85 s
of the ~1.2 s the fill took (measured 2026-10-09). The cell now holds a plain
item: the glyph under BUTTON_ROLE, the look under LOOK_ROLE, the tooltip as
the item's own. `RowButtonDelegate` paints a push button there and reports a
click as `on_click(row, col)`, with the row read off the index at click time,
so a row inserted or removed above never makes it play the wrong title.

The button is drawn through a hidden template QPushButton per look, so the
app's stylesheet (hover, pressed, disabled, a 🎨 look's own buttons) and the
theme hook apply to it exactly as they did to the widgets.
"""
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QPersistentModelIndex, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPalette, QSinglePointEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QStyledItemDelegate,
)

BUTTON_ROLE = Qt.ItemDataRole.UserRole + 42   # the glyph; None = no button in this cell
LOOK_ROLE = Qt.ItemDataRole.UserRole + 43     # one of LOOKS
PATH_ROLE = Qt.ItemDataRole.UserRole + 44     # the play button's track

# The size the widgets had (setFixedSize), centered in the cell.
BUTTON_SIZE = QSize(26, 20)

# look → the sheet its template button carries (what each widget used to set).
LOOKS = {
    "plain": "padding: 0;",
    "off": "padding: 0;",
    "missing": "padding: 0; color: #c81e1e; font-weight: bold;",
}


def button_rect(cell: QRect) -> QRect:
    r = QRect(QPoint(0, 0), BUTTON_SIZE)
    r.moveCenter(cell.center())
    return r


class RowButtonDelegate(QStyledItemDelegate):
    """Paints BUTTON_ROLE cells as push buttons and reports their clicks.

    The cell around the button paints like the empty cell it used to be: no
    text and no background of its own, only the selection, orange on a row
    `is_marked` names (as the table's default delegate draws it). A cell
    without a button (a flat list's ❗ item) paints as the plain item it is."""

    _SEL_MARKED = QColor(232, 126, 14)

    def __init__(self, view: QAbstractItemView, on_click: Callable[[int, int], None],
                 is_marked: Callable[[int], bool] = lambda _row: False):
        super().__init__(view)
        self._view = view
        self._on_click = on_click
        self._is_marked = is_marked
        self._templates: dict[str, QPushButton] = {}
        self._pressed: QPersistentModelIndex | None = None
        self._down = False
        self._hover: QPersistentModelIndex | None = None
        view.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        view.viewport().installEventFilter(self)

    def _template(self, look: str) -> QPushButton:
        btn = self._templates.get(look)
        if btn is None:
            btn = QPushButton(self._view)
            btn.hide()
            btn.setStyleSheet(LOOKS.get(look, LOOKS["plain"]))
            btn.setEnabled(look != "off")
            btn.ensurePolished()
            self._templates[look] = btn
        return btn

    # ── Painting ──────────────────────────────────────────────────────────────

    def paint(self, painter, option, index):
        glyph = index.data(BUTTON_ROLE)
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if glyph is not None:
            opt.text = ""                      # the cell itself paints as an empty one
        if opt.state & QStyle.StateFlag.State_Selected and self._is_marked(index.row()):
            opt.palette.setColor(QPalette.ColorRole.Highlight, self._SEL_MARKED)
        style = opt.widget.style() if opt.widget else self._view.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        if glyph is None:
            return
        look = index.data(LOOK_ROLE) or "plain"
        btn = self._template(look)
        b = QStyleOptionButton()
        b.initFrom(btn)
        b.rect = button_rect(option.rect)
        b.text = glyph
        b.state = QStyle.StateFlag.State_Raised
        if look != "off":
            b.state |= QStyle.StateFlag.State_Enabled
            if self._same(self._hover, index):
                b.state |= QStyle.StateFlag.State_MouseOver
            if self._down and self._same(self._pressed, index):
                b.state |= QStyle.StateFlag.State_Sunken
        painter.save()
        painter.setFont(btn.font())
        btn.style().drawControl(QStyle.ControlElement.CE_PushButton, b, painter, btn)
        painter.restore()

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def _button_at(self, pos: QPoint):
        """The index whose button is under `pos`, else None."""
        index = self._view.indexAt(pos)
        if not index.isValid() or index.data(BUTTON_ROLE) is None:
            return None
        if not button_rect(self._view.visualRect(index)).contains(pos):
            return None
        return index

    def _repaint(self, pidx: QPersistentModelIndex | None):
        if pidx is not None and pidx.isValid():
            index = self._view.model().index(pidx.row(), pidx.column())
            self._view.viewport().update(self._view.visualRect(index))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(event, QSinglePointEvent):  # hover and mouse events only
            return False
        et = event.type()
        if et in (QEvent.Type.HoverMove, QEvent.Type.HoverEnter, QEvent.Type.HoverLeave):
            index = (self._button_at(event.position().toPoint())
                     if et != QEvent.Type.HoverLeave else None)
            if not self._same(self._hover, index):
                self._repaint(self._hover)
                self._hover = QPersistentModelIndex(index) if index is not None else None
                self._repaint(self._hover)
            return False
        if et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            index = self._button_at(event.position().toPoint())
            if index is None:
                return False
            # A disabled button swallows the click too, as the widget did:
            # no selection, no drag, no double-click "play this row".
            if index.data(LOOK_ROLE) != "off":
                self._pressed = QPersistentModelIndex(index)
                self._down = True
                self._repaint(self._pressed)
            return True
        if self._pressed is None:
            return False
        if et == QEvent.Type.MouseMove:
            down = self._same(self._pressed, self._button_at(event.position().toPoint()))
            if down != self._down:
                self._down = down
                self._repaint(self._pressed)
            return True
        if et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            pressed, self._pressed = self._pressed, None
            hit = self._same(pressed, self._button_at(event.position().toPoint()))
            self._down = False
            self._repaint(pressed)
            if hit:
                self._on_click(pressed.row(), pressed.column())
            return True
        return False

    @staticmethod
    def _same(pidx: QPersistentModelIndex | None, index) -> bool:
        if pidx is None or index is None:
            return pidx is None and index is None
        return pidx.isValid() and pidx.row() == index.row() and pidx.column() == index.column()
