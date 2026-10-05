"""★ The rating column: five stars drawn in a cell, set with one click.

Shared by the decks and the 📚 library. The cell's item carries the stars
under `RATING_ROLE` (0 = unrated); a click on the n-th star asks for n stars,
a click on the star the rating already ends on takes it back to none. What a
rating is stored as (the DB edit layer, see planner.tag_edits) is the
window's business — the delegate only says which cell wants how many.
"""
from collections.abc import Callable

from PySide6.QtCore import QEvent, QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

RATING_ROLE = Qt.ItemDataRole.UserRole + 41
STARS = 5
_C_STAR_ON = QColor(215, 150, 0)      # amber, the Pop column's family
_C_STAR_OFF = QColor(0, 0, 0, 38)     # faint: the cell reads empty but clickable


def stars_of(index: QModelIndex) -> int:
    try:
        return max(0, min(STARS, int(index.data(RATING_ROLE) or 0)))
    except (TypeError, ValueError):
        return 0


def star_rects(rect: QRect, fm: QFontMetrics) -> list[QRect]:
    """Where each of the five stars sits in `rect`, centred, left to right."""
    w = fm.horizontalAdvance("★")
    left = rect.left() + max(0, (rect.width() - w * STARS) // 2)
    return [QRect(left + i * w, rect.top(), w, rect.height()) for i in range(STARS)]


def star_at(rect: QRect, fm: QFontMetrics, x: int) -> int:
    """The star (1–5) a click at `x` lands on: left of the first counts as
    the first, right of the last as the last, so the whole cell is a target."""
    rects = star_rects(rect, fm)
    for n, r in enumerate(rects, 1):
        if x < r.right() + 1:
            return n
    return STARS


def clicked_rating(current: int, star: int) -> int:
    """Clicking the star the rating ends on clears it; any other sets it."""
    return 0 if star == current else star


class StarDelegate(QStyledItemDelegate):
    """Paints RATING_ROLE as stars and reports clicks as `on_rate(index, stars)`."""

    def __init__(self, on_rate: Callable[[QModelIndex, int], None], parent=None):
        super().__init__(parent)
        self._on_rate = on_rate

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        if index.data(RATING_ROLE) is None:
            return                                   # a header row or a gap, not a track
        n = stars_of(index)
        painter.save()
        painter.setFont(opt.font)
        for i, r in enumerate(star_rects(option.rect, opt.fontMetrics)):
            painter.setPen(_C_STAR_ON if i < n else _C_STAR_OFF)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "★")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if (event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and index.data(RATING_ROLE) is not None
                and option.rect.contains(event.position().toPoint())):
            star = star_at(option.rect, option.fontMetrics, int(event.position().x()))
            self._on_rate(index, clicked_rating(stars_of(index), star))
            return True
        return super().editorEvent(event, model, option, index)
