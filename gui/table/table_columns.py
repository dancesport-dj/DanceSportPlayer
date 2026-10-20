"""A playlist table's columns: which are shown, their widths, the column
menu, short or full dance names, and the Nb. gutter that numbers the titles.
The title column takes the width nobody claimed.

Mixin of PlaylistTable, split off gui/table/playlist_table.py.
"""
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMenu

from planner.terms import dance_name
from shared.columns import (
    _COL_ALBUM,
    _COL_DANCE,
    _COL_LEN,
    _COL_PLAY,
    _COL_RATING,
    _COL_REGEN,
    _COL_TITLE,
    _N_COLS,
)
from gui.common import DANCE_SHORT, add_custom_mapping_action

if TYPE_CHECKING:
    from gui.window.hosts import PlaylistTableHost
else:
    PlaylistTableHost = object


class TableColumnsMixin(PlaylistTableHost):
    """Shown and hidden columns, their widths and menu, and the Nb. gutter."""

    # Readable names for the three columns whose caption is a glyph — a tick list
    # reading "▶ / ⏱ / ↺" says nothing about what would disappear.
    _COL_MENU_NAMES = {_COL_PLAY: "▶  Play", _COL_LEN: "⏱  Length",
                       _COL_RATING: "★  Rating", _COL_REGEN: "↺  Regenerate"}

    # Whole captions, not the bare noun: the noun on its own cannot be a
    # catalog key, and glueing one into a sentence is how the German would go
    # wrong the first time a kind is added whose article is not "jeder".
    _KIND_HEADS = {"wishlist": "Columns in every wishlist",
                   "party": "Columns in every party list"}

    # The left-to-right order a list starts with. The column numbers stay what
    # they are (saved ticks and widths use them); only the header shows Album
    # beside Title, so a ticked-on Album reads Artist · Title · Album.
    _DEFAULT_ORDER = [c for c in range(_N_COLS) if c != _COL_ALBUM]
    _DEFAULT_ORDER.insert(_DEFAULT_ORDER.index(_COL_TITLE) + 1, _COL_ALBUM)

    def column_order(self) -> list[int]:
        """The column numbers from left to right, as the header shows them."""
        hh = self.horizontalHeader()
        return [hh.logicalIndex(v) for v in range(hh.count())]

    def set_column_order(self, order):
        """Show the columns in a saved order. One that does not name every
        column exactly once (saved before a column was added) is ignored.
        JSON may hand the numbers back as strings."""
        try:
            order = [int(c) for c in order]
        except (TypeError, ValueError):
            return
        if sorted(order) != list(range(_N_COLS)):
            return
        hh = self.horizontalHeader()
        hh.blockSignals(True)       # our own doing, not a drag: don't re-save
        try:
            for visual, logical in enumerate(order):
                cur = hh.visualIndex(logical)
                if cur != visual:
                    hh.moveSection(cur, visual)
            self._pin_edge_columns()
        finally:
            hh.blockSignals(False)

    def _pin_edge_columns(self):
        """Dance stays first and ↺ last: a round's header row spans every
        column up to ↺, writes its name in Dance and keeps ↺ for its own
        regenerate button."""
        hh = self.horizontalHeader()
        if hh.visualIndex(_COL_DANCE) != 0:
            hh.moveSection(hh.visualIndex(_COL_DANCE), 0)
        if hh.visualIndex(_COL_REGEN) != _N_COLS - 1:
            hh.moveSection(hh.visualIndex(_COL_REGEN), _N_COLS - 1)

    def _on_section_moved(self, *_args):
        """A header was dragged to a new place: hold the edges, then tell the
        window, which keeps the order for every list of this kind."""
        hh = self.horizontalHeader()
        hh.blockSignals(True)
        try:
            self._pin_edge_columns()
        finally:
            hh.blockSignals(False)
        if self._order_cb:
            self._order_cb(self.list_kind, self.column_order())

    def set_column_order_callback(self, cb):
        """`cb(kind, order)` when the user has dragged a column elsewhere."""
        self._order_cb = cb

    def _fill_title_column(self):
        """Give Title whatever width the other columns leave over.

        What `Stretch` used to do, minus the part that made Title the one column
        the user could not drag. Runs on a table resize and after a neighbour is
        dragged, so there is never an empty gap on the right."""
        if self._filling or self.isColumnHidden(_COL_TITLE):
            return
        others = sum(self.columnWidth(c) for c in range(_N_COLS)
                     if c != _COL_TITLE and not self.isColumnHidden(c))
        want = self.viewport().width() - others
        self._filling = True
        try:
            self.setColumnWidth(
                _COL_TITLE, max(self.horizontalHeader().minimumSectionSize(), want))
        finally:
            self._filling = False

    def _on_section_resized(self, idx: int, _old: int, _new: int):
        """A dragged column takes its width from Title, not from the window."""
        if idx == _COL_TITLE or self._filling:
            return
        self._fill_title_column()
        # A drag arrives a pixel at a time; save once when it comes to rest.
        self._width_timer.start()

    def _notify_widths(self):
        if self._widths_cb:
            self._widths_cb(self.list_kind, self.column_widths())

    def _notify_dance_names(self):
        if self._dance_cb:
            self._dance_cb(self.list_kind, self._short_dances)

    def set_dance_names_callback(self, cb):
        """`cb(kind, short)` when the Dance column is switched between the full
        name and the short code."""
        self._dance_cb = cb

    def _dance_label(self, dance: str) -> str:
        """What the Dance column says for a dance code: the full name, or the
        Σ line's short one when the user has asked for it."""
        if self._short_dances:
            return DANCE_SHORT.get(dance, dance)
        return dance_name(dance, dance)

    def short_dances(self) -> bool:
        return self._short_dances

    def set_short_dances(self, on: bool):
        """Write the Dance column short ("LW", "SB") or in full. Rewrites the
        rows that are already there; the dance HEADER rows keep the full name,
        they span the table and have the room."""
        on = bool(on)
        if on == self._short_dances:
            return
        self._short_dances = on
        for row, meta in enumerate(self._row_meta):
            # A header row carries no dance of its own, and a stacked backup's
            # Dance cell is deliberately blank.
            if meta is None or meta.backup:
                continue
            item = self.item(row, _COL_DANCE)
            if item is not None:
                item.setText(self._dance_label(meta.dance))

    def set_columns_callback(self, cb):
        """`cb(kind, hidden_columns)` whenever a tick changes — the window saves it
        and applies it to every other list of the same kind."""
        self._columns_cb = cb

    def set_rating_callback(self, cb):
        """`cb(entry, stars)` when a ★ is clicked — 0 stars = take the rating back."""
        self._rating_cb = cb

    def _on_star_clicked(self, index, stars: int):
        entry = self._row_meta.entry_at(index.row())
        if entry is not None and self._rating_cb is not None:
            self._rating_cb(entry, stars)

    def set_widths_callback(self, cb):
        """`cb(kind, widths)` when the user has finished dragging a handle."""
        self._widths_cb = cb

    def column_widths(self) -> dict[int, int]:
        """Every column's width except Title's, which is the leftover and is
        recomputed on each resize. A hidden column reports the width it had, not
        the 0 Qt gives a hidden section."""
        return {c: (self._col_width.get(c, 0) if self.isColumnHidden(c)
                    else self.columnWidth(c))
                for c in range(_N_COLS) if c != _COL_TITLE}

    def set_column_widths(self, widths):
        """Apply saved widths. JSON has no integer keys, so string ones count."""
        self._filling = True          # our own doing, not a drag: don't re-save
        try:
            for key, w in (widths or {}).items():
                c, w = int(key), int(w)
                if c == _COL_TITLE or not 0 <= c < _N_COLS or w <= 0:
                    continue
                if self.isColumnHidden(c):
                    self._col_width[c] = w
                else:
                    self.setColumnWidth(c, w)
        finally:
            self._filling = False
        self._fill_title_column()

    def hidden_columns(self) -> list[int]:
        return [c for c in range(_N_COLS) if self.isColumnHidden(c)]

    def set_hidden_columns(self, cols):
        """Show exactly the columns not in `cols`. Title is never put away — a row
        without it cannot be told from any other."""
        want = {int(c) for c in cols if int(c) != _COL_TITLE}
        for c in range(_N_COLS):
            hidden = self.isColumnHidden(c)
            if c in want and not hidden:
                self._col_width[c] = self.columnWidth(c)
                self.setColumnHidden(c, True)
            elif hidden and c not in want:
                self.setColumnHidden(c, False)
                w = self._col_width.pop(c, 0)
                if w:
                    self.setColumnWidth(c, w)
        self._fill_title_column()

    def build_column_menu(self) -> QMenu:
        """The right-click tick list of the header."""
        menu = QMenu(self)
        head = menu.addAction(self._KIND_HEADS.get(
            self.list_kind, "Columns in every playlist"))
        head.setEnabled(False)
        menu.addSeparator()
        for c in range(_N_COLS):
            if c == _COL_TITLE:
                continue
            item = self.horizontalHeaderItem(c)
            act = menu.addAction(self._COL_MENU_NAMES.get(
                c, item.text() if item else str(c)))
            act.setCheckable(True)
            act.setChecked(not self.isColumnHidden(c))
            act.setData(c)
            act.triggered.connect(lambda on, col=c: self._toggle_column(col, on))
        menu.addSeparator()
        # Not a column but the same kind of choice: how much room the Dance
        # column needs. Carries no data(), which is how a column tick is told
        # apart from it.
        short = menu.addAction("Short dance names  (LW, SB)")
        short.setCheckable(True)
        short.setChecked(self._short_dances)
        short.triggered.connect(self._toggle_short_dances)
        add_custom_mapping_action(menu, self)
        return menu

    def _toggle_short_dances(self, on: bool):
        self.set_short_dances(on)
        self._notify_dance_names()

    def _toggle_column(self, col: int, on: bool):
        hidden = set(self.hidden_columns())
        if on:
            hidden.discard(col)
        else:
            hidden.add(col)
        self.set_hidden_columns(sorted(hidden))
        if self._columns_cb:
            self._columns_cb(self.list_kind, self.hidden_columns())

    def _show_column_menu(self, pos: QPoint):
        self.build_column_menu().exec(self.horizontalHeader().mapToGlobal(pos))

    def set_numbered(self, on: bool):
        """Show or hide the Nb. column of the 🔢 Numbers view."""
        self._numbered = on
        vh = self.verticalHeader()
        fm = self._nb_label.fontMetrics()
        vh.setFixedWidth(max(fm.horizontalAdvance("Nb."), fm.horizontalAdvance("999")) + 14)
        vh.setVisible(on)
        self._nb_label.setVisible(on)
        self.updateGeometries()

    def updateGeometries(self):
        super().updateGeometries()
        if getattr(self, "_nb_label", None) is not None:
            f = self.frameWidth()
            self._nb_label.setGeometry(f, f, self.verticalHeader().width(),
                                       self.horizontalHeader().height())

    def song_number_label(self, row: int) -> str:
        """The Nb. text of a table row: the title's place in the list, counted
        from 1, or blank for a header / empty slot."""
        songs = self._row_meta.song_rows()
        try:
            return str(songs.index(row) + 1)
        except ValueError:
            return ""
