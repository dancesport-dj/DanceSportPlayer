"""PlaylistTable keyboard shortcuts and the row actions they share with the menu.

Mixin of PlaylistTable — extracted 1:1 from gui/table/playlist_table.py in the
big-module split; behaviour unchanged. The right-click menu itself is a mixin
of its own, in gui/table/table_menu.py."""
import logging
import time

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QColor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QInputDialog,
    QMessageBox,
)
from pathlib import Path
from planner.models import DANCE_NAMES, MusicEntry
from planner.terms import dance_name, genre_name
from planner import i18n
from planner.generate.warmup import _WARMUP_ORDER, warmup_code
from gui.common import (
    BusyDialog,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _unreadable_playlist,
    display_title,
)
from shared.columns import (
    _COL_ALBUM,
    _COL_ARTIST,
    _COL_BPM,
    _COL_CLASS,
    _COL_COMMENT,
    _COL_CUSTOM,
    _COL_DANCE,
    _COL_FILE,
    _COL_LEN,
    _COL_POP,
    _COL_RATING,
    _COL_TITLE,
)
from shared.widgets import (
    _show_toast,
)
from planner.playlist.playlist_text import PlaylistEncodingError, read_playlist_text
from gui.decks.playlist_entries import playlist_paths
from typing import TYPE_CHECKING
from gui.table.table_menu import TableMenuMixin

if TYPE_CHECKING:
    from gui.window.hosts import PlaylistTableHost
    from gui.decks.running_order import Row
else:
    PlaylistTableHost = object

log = logging.getLogger("dancesport.gui.playlist_table")

# `PlaylistTable` is late-bound into this module by gui.table.playlist_table after
# the class is defined (a top-level import would be circular): the methods
# here isinstance-check drag sources against it at call time.
PlaylistTable = None

def _dance_sort_key(e):
    """Sort key for the dance-column sort: Standard, then Latin, then the social
    dances (Discofox, Salsa, …) in running order, then any other genre —
    alphabetically by name, then by title.

    A social track carries no competition dance; its genre sits in `other_genre`,
    so the code comes from `warmup_code`. Keyed on `e.dance` alone, every social
    track shared one blank rank and the dances came out mixed, sorted by title."""
    code = warmup_code(e) or ""
    rank = _WARMUP_ORDER.get(code, len(_WARMUP_ORDER))
    name = DANCE_NAMES.get(code) or getattr(e, "other_genre", None) or code
    return (rank, name.lower(), (e.title or "").lower())


class TableActionsMixin(TableMenuMixin):
    """User-action concern: every keyboard shortcut of the grid and the row
    actions (replace, mark, remove, …) the right-click menu shares with it."""

    _space_at = 0.0   # when Space last played/stopped — a quick second tap is the same press

    # ── Selection ──────────────────────────────────────────────────────────────

    def _selected_song_rows(self) -> list[int]:
        """The selected rows that hold a title, top to bottom."""
        selected = {ix.row() for ix in self.selectedIndexes()}
        return [r for r in self._row_meta.song_rows() if r in selected]

    def _two_songs_selected(self) -> bool:
        """Exactly two titles selected on an Eintanzen list — what ⇅ Swap needs.
        A running order is left out: its strips follow the tracks' paths."""
        return (self._warmup and not self._player_list
                and len(self._selected_song_rows()) == 2)

    def _swappable_pair(self) -> tuple[int, int] | None:
        """The two selected rows when ⇅ Swap may change their places: both
        hold the same dance, so every round keeps its dances. None otherwise."""
        if not self._two_songs_selected():
            return None
        a, b = self._selected_song_rows()
        code = warmup_code(self._row_meta[a].entry)
        if not code or code != warmup_code(self._row_meta[b].entry):
            return None
        return a, b

    def _swap_selected(self):
        """⇅ Swap (context menu, Alt+S): the two selected titles change places.
        Anything but two titles of one dance gets a dialog that says why not."""
        if not self._two_songs_selected():
            QMessageBox.information(
                self, "Swap titles",
                "Select exactly two titles of the same dance to swap them.")
            return
        pair = self._swappable_pair()
        if pair is None:
            a, b = (self._row_meta[r].entry for r in self._selected_song_rows())

            def label(e):
                name = dance_name(warmup_code(e) or "") or genre_name(e.other_genre) or "?"
                return f"„{e.title}“ ({name})"

            QMessageBox.warning(
                self, "Swap titles",
                i18n.t("%s and %s are different dances.\n\n"
                       "Only titles of the same dance can swap places, so every round "
                       "keeps its dances.") % (label(a), label(b)))
            return
        self._swap_song_rows(*pair)

    def _search_title(self):
        """Prompt for text and jump to the next song row whose title (tag title or
        filename too) contains it, wrapping around. The query is remembered and the
        search starts just AFTER the current row, so re-running with the same term
        steps through every match in turn."""
        text, ok = QInputDialog.getText(
            self, "Find in list", "Find title:",
            text=getattr(self, "_last_search", ""))
        if not ok:
            return
        term = text.strip().lower()
        if not term:
            return
        self._last_search = text.strip()
        n = len(self._row_meta)
        cur = self.currentRow()
        order = list(range(cur + 1, n)) + list(range(0, cur + 1))
        for r in order:
            m = self._row_meta[r] if 0 <= r < n else None
            ent = m.entry if m else None
            if ent is None:
                continue
            hay = " ".join(filter(None, [
                ent.title or "",
                getattr(ent, "tag_title", "") or "",
                Path(ent.path).name if getattr(ent, "path", None) else "",
            ])).lower()
            if term in hay:
                self._focus_row(r)
                return
        _show_toast(self, i18n.t("🔍  No title matching “%s”") % self._last_search)

    def _focus_row(self, row: int, focus: bool = True):
        """Select, centre-scroll and focus `row` so a found / targeted song stands out.

        `focus=False` leaves the keyboard focus where it is: a re-render that puts
        the selection back on the same song must not pull focus over from whatever
        deck the user was working in."""
        item = self.item(row, _COL_TITLE)
        if item is not None:
            self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.clearSelection()
        self.setCurrentCell(row, _COL_TITLE)
        self.selectRow(row)
        if focus:
            self.setFocus()

    # ── Keyboard shortcuts ─────────────────────────────────────────────────────

    def _selected_song_row(self) -> tuple[int, Path | None]:
        """Return (row, path) of the first selected row that holds a real song,
        or (-1, None) if the selection is a header/empty row."""
        rows: list[int] = []
        sm = self.selectionModel()
        if sm:
            rows = [idx.row() for idx in sm.selectedRows()]
        if not rows and self.currentRow() >= 0:
            rows = [self.currentRow()]
        for r in rows:
            if 0 <= r < len(self._row_meta) and self._row_meta[r]:
                entry = self._row_meta[r].entry
                if entry is not None:
                    return r, entry.path
        return -1, None

    def _marks_allowed(self) -> bool:
        """May this deck carry 🔁 "potential replace" marks?

        Both modes that let the operator rearrange the list themselves: the
        dynamic grid and the free running order. Noting "this one should go" is
        the same job in either — you are looking at the evening as it will be
        played and flagging what to come back to. A static grid is excluded
        because it is planned output, not a working list.
        """
        return bool(self._dynamic or self.plays_flat())

    def _is_row_marked(self, row: int) -> bool:
        """True when this row's song is flagged 'for potential replace'."""
        if 0 <= row < len(self._row_meta) and self._row_meta[row]:
            e = self._row_meta[row].entry
            return bool(e is not None and getattr(e, "path", None)
                        and str(e.path) in self._marked_paths)
        return False

    def _is_row_pinned(self, row: int) -> bool:
        """True when this row's title is 📌 pinned (sits out the re-rolls)."""
        if 0 <= row < len(self._row_meta) and self._row_meta[row]:
            e = self._row_meta[row].entry
            return bool(e is not None and getattr(e, "path", None)
                        and str(e.path) in self._pinned_paths)
        return False

    def _toggle_pin(self, rows) -> bool:
        """📌 Pin or unpin the titles in `rows` (slots of a round only), keyed by
        path like the 🔁 marks. If any of them is unpinned, pin them all;
        otherwise unpin them all."""
        paths = []
        for r in rows:
            if 0 <= r < len(self._row_meta) and self._row_meta[r]:
                m = self._row_meta[r]
                if (m.entry is not None and getattr(m.entry, "path", None)
                        and m.round_name and not m.theme):
                    paths.append(str(m.entry.path))
        if not paths:
            return False
        pinning = any(p not in self._pinned_paths for p in paths)
        if pinning:
            self._pinned_paths.update(paths)
        else:
            self._pinned_paths.difference_update(paths)
        affected = set(paths)
        for r in range(min(self.rowCount(), len(self._row_meta))):
            m = self._row_meta[r]
            if m and m.entry is not None and str(getattr(m.entry, "path", "")) in affected:
                self._refill_row(r, m)
        n = len(affected)
        if pinning:
            _show_toast(self, (i18n.t("📌  Pinned %d title — the round's ↻ keeps it") if n == 1
                               else i18n.t("📌  Pinned %d titles — the round's ↻ keeps them")) % n)
        else:
            _show_toast(self, (i18n.t("📌  Unpinned %d title") if n == 1
                               else i18n.t("📌  Unpinned %d titles")) % n)
        self._notify_changed()
        return True

    def _row_base_bg(self, row: int, meta: Row | None) -> QColor:
        """The row's normal (unmarked) background — heat-parity alternating colour."""
        parity = meta.h_idx if meta and meta.h_idx is not None else row
        return _C_ROW_EVEN if parity % 2 == 0 else _C_ROW_ODD

    def _refill_row(self, row: int, meta: Row):
        """Re-render one song row (picks up its current mark state), restoring the ■
        marker if it's the row that's currently playing (a fresh fill resets it to ▶)."""
        self._fill_song_row(row, meta, self._row_base_bg(row, meta))
        if row == self._current_play_row:
            self.sync_play_glyph()

    def _toggle_mark(self, rows) -> bool:
        """Toggle the 'potential replace' mark on the songs in `rows`. Marks are keyed
        by file path (so they survive re-renders and span every slot a track sits in).
        If any targeted song is unmarked, mark them all; otherwise unmark them all."""
        paths = []
        for r in rows:
            if 0 <= r < len(self._row_meta) and self._row_meta[r]:
                e = self._row_meta[r].entry
                if e is not None and getattr(e, "path", None):
                    paths.append(str(e.path))
        if not paths:
            return False
        marking = any(p not in self._marked_paths for p in paths)
        if marking:
            self._marked_paths.update(paths)
        else:
            for p in paths:
                self._marked_paths.discard(p)
        affected = set(paths)
        for r in range(min(self.rowCount(), len(self._row_meta))):
            m = self._row_meta[r]
            if m and m.entry is not None and str(getattr(m.entry, "path", "")) in affected:
                self._refill_row(r, m)
        n = len(affected)
        if marking:
            _show_toast(self, (i18n.t("🔁  Marked %d track for replace") if n == 1
                               else i18n.t("🔁  Marked %d tracks for replace")) % n)
        else:
            _show_toast(self, (i18n.t("🔁  Unmarked %d track") if n == 1
                               else i18n.t("🔁  Unmarked %d tracks")) % n)
        return True

    def _reset_all_marks(self):
        """Clear every 'potential replace' mark in this playlist."""
        if not self._marked_paths:
            return
        cleared = self._marked_paths
        self._marked_paths = set()
        for r in range(min(self.rowCount(), len(self._row_meta))):
            m = self._row_meta[r]
            if m and m.entry is not None and str(getattr(m.entry, "path", "")) in cleared:
                self._refill_row(r, m)
        _show_toast(self, "🔁  Cleared all replacement marks")

    def keyPressEvent(self, event):
        """Space / Enter: play/stop the selected song.  Ctrl+←/→: seek ∓30 s.
        Ctrl+F: find a title in this list.
        Ctrl+R / Ctrl+N: re-roll (regenerate) the selected song.
        Alt+S: swap the two selected titles (Eintanzen list).
        Ctrl+M / Ctrl+1: mark/unmark for potential replace (dynamic + free order).
        Ctrl+Del: remove the whole heat (dynamic decks)."""
        key  = event.key()
        mods = event.modifiers()
        # A held key repeats at the system rate, and every action below is either a
        # toggle or throws something away: held Space plays/stops/plays, a held
        # Ctrl+R re-rolls the same song over and over, a held Del keeps clearing.
        # Only the ∓30 s seek is meant to repeat — holding it to run through a song
        # is the point. Everything else goes to the base class, which is what makes
        # a held arrow key still scroll the list.
        if event.isAutoRepeat() and not (
                key in (Qt.Key.Key_Left, Qt.Key.Key_Right)
                and (mods & Qt.KeyboardModifier.ControlModifier)):
            super().keyPressEvent(event)
            return
        if (key == Qt.Key.Key_F and (mods & Qt.KeyboardModifier.ControlModifier)
                and self._row_meta.has_songs()):
            self._search_title()
            event.accept()
            return
        # Enter too: in Playing mode the window keeps Space for the player's
        # play / pause in the list playing, and Enter still starts the selection.
        if ((key == Qt.Key.Key_Space and mods == Qt.KeyboardModifier.NoModifier)
                or (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                    and mods in (Qt.KeyboardModifier.NoModifier,
                                 Qt.KeyboardModifier.KeypadModifier))):
            row, path = self._selected_song_row()
            if row >= 0:
                # A double tap is one press: the second would stop the title
                # the first just started (still loading, so it looked idle).
                now = time.monotonic()
                if now - self._space_at >= QApplication.doubleClickInterval() / 1000:
                    self._space_at = now
                    self._on_play_click(row, path)
                event.accept()
                return
        elif (key in (Qt.Key.Key_R, Qt.Key.Key_N)
              and (mods & Qt.KeyboardModifier.ControlModifier)):
            row, _ = self._selected_song_row()
            if row >= 0:
                self._regen(row)
                event.accept()
                return
        elif (key == Qt.Key.Key_S and mods == Qt.KeyboardModifier.AltModifier
              and self._warmup and not self._player_list):
            self._swap_selected()
            event.accept()
            return
        elif (key in (Qt.Key.Key_Left, Qt.Key.Key_Right)
              and (mods & Qt.KeyboardModifier.ControlModifier)):
            if self._seek_cb:
                self._seek_cb(-30000 if key == Qt.Key.Key_Left else 30000)
                event.accept()
                return
        elif (key in (Qt.Key.Key_M, Qt.Key.Key_1)
              and (mods & Qt.KeyboardModifier.ControlModifier)
              and self._marks_allowed()):
            # Ctrl+M / Ctrl+1: toggle the orange "potential replace" mark on the
            # selected song row(s). Same combo again unmarks.
            rows = {ix.row() for ix in self.selectedIndexes()}
            if not rows and self.currentRow() >= 0:
                rows = {self.currentRow()}
            if self._toggle_mark(rows):
                event.accept()
                return
        elif (key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
              and (mods & Qt.KeyboardModifier.ControlModifier)
              and self._dynamic):
            if self._remove_heat_under_cursor():
                event.accept()
                return
        elif (key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
              and mods == Qt.KeyboardModifier.NoModifier):
            has_sel = bool(self.selectedIndexes())
            # Selecting EVERY song (e.g. Ctrl+A) then Del = empty the whole list,
            # same as Del on the header — wiping it back to blank (after a confirm).
            if has_sel and self._all_songs_selected():
                if self._clear_entire():
                    event.accept()
                    return
            elif self._flat_mode:
                # Wishlist: Del on selected rows removes them; Del with nothing
                # selected (header focused) clears the WHOLE wishlist (after a confirm).
                if (self._remove_selected_rows() if has_sel else self._clear_entire()):
                    event.accept()
                    return
            else:
                # Deck: Del on selected rows empties those heat slots (slot stays as
                # "⚠ No song found"); Del with nothing selected (header focused) wipes
                # the ENTIRE playlist back to a blank/white table (after a confirm).
                if (self._clear_selected_slots() if has_sel else self._clear_entire()):
                    event.accept()
                    return
        super().keyPressEvent(event)

    def _remove_heat_under_cursor(self) -> bool:
        """True when Ctrl+Del took something away."""
        # Ctrl+Del: remove the whole heat under the cursor (dynamic decks only —
        # static strategies have a fixed heat grid). On a '↳ backup N' row only
        # that backup goes.
        row = self.currentRow()
        if 0 <= row < len(self._row_meta):
            m = self._row_meta[row]
            if m and m.round_name:
                if m.backup:
                    self._remove_dynamic_backup(row)
                else:
                    self._remove_dynamic_heat(row)
                return True
        return False

    def _all_songs_selected(self) -> bool:
        """True when every song (entry-bearing row) in the list is currently selected
        — so Del should empty the whole list, not just clear those slots. False when
        the list holds no songs at all (nothing to empty)."""
        song_rows = set(self._row_meta.song_rows())
        if not song_rows:
            return False
        sel = {ix.row() for ix in self.selectedIndexes()}
        return song_rows <= sel

    def _remove_selected_rows(self) -> bool:
        """Wishlist helper: drop every selected song row. Returns True if any went."""
        return self._remove_rows({ix.row() for ix in self.selectedIndexes()})

    def _clear_entire(self) -> bool:
        """Del on the header (nothing selected) clears the WHOLE table after a confirm.
        A wishlist is emptied here; a competition deck is wiped back to a blank/white
        table via the `cleared` signal (MainWindow resets the deck's context too).
        Returns True when the key is handled (including a cancelled confirm); False
        when there's nothing to clear."""
        if self.rowCount() == 0:
            return False
        name = self.host.deck_name()
        named = f" “{name}”" if name else ""
        if self._flat_mode:
            ans = QMessageBox.question(
                self, "Clear wishlist",
                i18n.t("Remove all %d track(s) from wishlist%s?") % (len(self._row_meta), named),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return True   # cancelled, but still consume the key
            if self._current_play_row >= 0 and self._play_cb:
                self._play_cb(None)
            self._render_flat_entries([])
            # Emptying a wishlist drops its custom name back to the default (an empty
            # wishlist named after the playlist it once held would be misleading).
            self.host.reset_wishlist_name()
            return True
        # Competition deck → blank it completely ("white again"); MainWindow does the
        # actual reset (rows + per-deck context + Save button) via the cleared signal.
        ans = QMessageBox.question(
            self, "Clear playlist",
            i18n.t("Remove the entire playlist%s? The table will be blank again.") % named,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return True
        self.cleared.emit(self)
        return True

    def _remove_rows(self, rows, select_after: bool = False) -> bool:
        """Wishlist helper: drop the given row indices. Returns True if any went.
        select_after → after the removal, select the spot the (first) removed row
        held, so moving a track OUT leaves the source's cursor where it was."""
        rows = sorted({r for r in rows if 0 <= r < len(self._row_meta)}, reverse=True)
        if not rows:
            return False
        gap = rows[-1]   # smallest removed index = the place the track was
        # Only stop playback when the playing row is itself removed; a playing track
        # that survives keeps its ■ marker — its id renumbers with its row.
        if self._current_play_row in rows and self._play_cb:
            self._play_cb(None)
        for r in rows:
            self.removeRow(r)
            del self._row_meta[r]
        self._notify_changed()
        if select_after and self.rowCount():
            self._focus_rows([min(gap, self.rowCount() - 1)])
        # Removing the last track from a wishlist drops its custom name back to the
        # default — same rationale as clearing it outright (see `_clear_entire`).
        if self._flat_mode and self.rowCount() == 0:
            self.host.reset_wishlist_name()
        return True

    def _apply_song_reorder(self, final_entries, select=None) -> bool:
        """Re-order a reorderable list (wishlist / warm-up) IN PLACE: only the song
        rows whose track actually changed get re-filled — unchanged rows keep their
        widgets, so the table is never torn down. That means the scroll position
        survives the drop (no jump back to the top) and there's no per-row widget
        churn (no lag). `final_entries` is the new order of the song entries (the
        ■ marker follows the playing one by its id); `select` is the list of
        entries to (re)select + focus afterwards so the dropped track stays
        highlighted where it landed. Returns True if the order actually changed."""
        song_rows = self._row_meta.song_rows()
        if len(song_rows) != len(final_entries):
            return False
        cur = [self._row_meta[r].entry for r in song_rows]
        if final_entries == cur:
            return False   # dropped back where it already was → no-op
        sel_paths   = {str(e.path) for e in select if e is not None} if select else set()
        select_rows = []
        # The grey of an already-played row is remembered by (row, column), and
        # the tracks are about to change rows: give every row its own colour
        # back while those numbers still mean the rows they were taken from.
        self._ungrey_played_rows()
        placed = self._row_meta.placements()
        for pos, (r, e) in enumerate(zip(song_rows, final_entries, strict=True)):
            m = self._row_meta[r]
            if m.entry is not e:
                m.entry = e
                # A social track has no .dance — in a warm-up list its genre
                # names the dance, exactly as both render paths there read it.
                # (The flat wishlist leaves those blank and keeps doing so.)
                code = (warmup_code(e) if self._warmup else None) if e else None
                m.dance = (code or e.dance or "") if e is not None else ""
                # Warm-up song rows count parity from 0 (header sits above them);
                # the flat wishlist counts it straight from the table row.
                parity = pos if self._warmup else r
                bg = _C_ROW_EVEN if parity % 2 == 0 else _C_ROW_ODD
                self._fill_song_row(r, m, bg)
            if e is not None and str(e.path) in sel_paths:
                select_rows.append(r)
        self._row_meta.adopt(placed)
        self._follow_play_row()
        # …and grey the played ones again, on the rows they now sit on — the
        # running one, which keeps its own colours, has just been found.
        self._grey_played_rows()
        self._focus_rows(select_rows)
        self._notify_changed()
        return True

    def _focus_rows(self, rows) -> None:
        """Select the given rows and scroll the first into view (without jumping the
        viewport when it's already visible). Used to keep a just-dropped track
        highlighted where it landed."""
        rows = [r for r in rows if 0 <= r < self.rowCount()]
        if not rows:
            return
        self.clearSelection()
        first = self.item(rows[0], _COL_TITLE)
        if first is not None:
            self.setCurrentItem(first)        # current → first dropped row
        for r in rows:
            self.selectRow(r)                 # extend to the rest of the moved block
        if first is not None:
            self.scrollToItem(first, QAbstractItemView.ScrollHint.EnsureVisible)

    def _restore_scroll(self, offset: int) -> None:
        """Put the viewport back at `offset` after a re-render threw every row
        away — so an edit in the middle of a long list doesn't send the operator
        scrolling their place back.

        The scrollbar's range is only recomputed during the view's delayed
        layout. Asked before that runs, it still reports the old range — or none
        at all, and the offset is clamped away to the top."""
        self.executeDelayedItemsLayout()
        self.updateGeometries()
        bar = self.verticalScrollBar()
        bar.setValue(min(offset, bar.maximum()))

    def _reorder_flat(self, drop_index: int) -> bool:
        """Wishlist helper: move the dragged rows (`_drag_src_rows`) to the insert
        gap `drop_index` (0..rowCount, as returned by `_drop_index`). Returns True
        if the order actually changed."""
        src = sorted({r for r in self._drag_src_rows if 0 <= r < len(self._row_meta)})
        if not src:
            return False
        cur = self._row_meta.entries()
        if len(cur) != len(self._row_meta):
            return False   # safety: flat rows map 1:1 to entries
        moved     = [cur[r] for r in src]
        src_set   = set(src)
        remaining = [e for i, e in enumerate(cur) if i not in src_set]
        # Translate the drop gap into the shrunken (post-removal) list: every
        # dragged row before the gap shifts it one place left.
        before    = sum(1 for r in src if r < drop_index)
        insert_at = max(0, min(drop_index - before, len(remaining)))
        final     = remaining[:insert_at] + moved + remaining[insert_at:]
        return self._apply_song_reorder(final, select=moved)

    def _reorder_warmup(self, drop_index: int) -> bool:
        """Warm-up ("Eintanzen") helper: move the dragged song rows to the insert
        gap `drop_index` (table-row index, as returned by `_drop_index`), keeping
        the ═══ header pinned at the top and every row's warm-up tag intact. The
        list is rebuilt via `load_warmup` so ↺ re-roll keeps working afterwards.
        Returns True if the order actually changed."""
        # Song rows = rows with a real entry (the ═══ header span carries None).
        song_rows = self._row_meta.song_rows()
        if not song_rows:
            return False
        src_set = {r for r in self._drag_src_rows if r in set(song_rows)}
        if not src_set:
            return False
        entries  = [self._row_meta[r].entry for r in song_rows]
        pos_of   = {r: i for i, r in enumerate(song_rows)}
        src_idx  = sorted(pos_of[r] for r in src_set)
        moved    = [entries[i] for i in src_idx]
        keep     = [e for i, e in enumerate(entries) if i not in set(src_idx)]
        # Translate the table-row gap into the entries list, then account for the
        # dragged rows that sat before it (each shifts the gap one place left).
        gap       = self._song_pos_at(drop_index)
        before    = sum(1 for i in src_idx if i < gap)
        insert_at = max(0, min(gap - before, len(keep)))
        final     = keep[:insert_at] + moved + keep[insert_at:]
        return self._apply_song_reorder(final, select=moved)

    def _swap_reorder(self, dst_row: int) -> bool:
        """Ctrl-drag within a reorderable list (wishlist / warm-up): SWAP the dragged
        track with the one at `dst_row` — both keep their slots, only the titles
        exchange — instead of moving the dragged track to a gap. Mirrors a playlist
        deck's in-place replace. Returns True if a swap happened."""
        src = self._internal_drag_src()           # first valid dragged song row
        if src is None or not (0 <= dst_row < len(self._row_meta)) or dst_row == src:
            return False
        dm = self._row_meta[dst_row]
        if dm is None or dm.entry is None or dm.theme:
            return False
        song_rows = self._row_meta.song_rows()
        entries = self._row_meta.entries()
        si = song_rows.index(src)
        di = song_rows.index(dst_row)
        dragged = entries[si]                  # the track being dropped onto dst_row
        entries[si], entries[di] = entries[di], entries[si]
        return self._apply_song_reorder(entries, select=[dragged])

    def _m3u_track_paths(self, path: Path) -> list[Path]:
        """The track paths an .m3u/.m3u8 names, in file order. Reading the file is
        all that happens here — resolving those paths to entries is the slow part
        and belongs to `_entries_for_paths`, which can put a progress bar on it.
        A file that can't be decoded reads as empty, and a toast says why."""
        try:
            lines = read_playlist_text(path)[0].splitlines()
        except OSError:
            return []
        except PlaylistEncodingError as exc:
            _unreadable_playlist(self, path, exc)
            return []
        return playlist_paths(lines)

    # A drop gets a progress dialog only once it has been running this long. Two
    # or three tracks resolve instantly, and a window flashing up for them is
    # worse than none at all. What this is for is a dropped FOLDER: every track
    # in it that isn't already in the library has its tags read here, and a few
    # hundred of those look exactly like a hung app without it.
    _DROP_PROGRESS_AFTER = 0.5

    def _entries_for_paths(self, paths: list[Path]) -> list[MusicEntry | None]:
        """Resolve audio paths to MusicEntries — one result per input path, None
        where the file couldn't be read, so a caller can pair them up by zip() and
        still tell WHICH path failed.

        Cancelling the progress dialog stops the resolve where it stands and the
        list comes back SHORT: zip() then simply yields the ones that were done,
        and the tracks already found are kept rather than thrown away."""
        out: list[MusicEntry | None] = []
        total = len(paths)
        dlg = None
        cancelled: list[bool] = []
        t0 = last = time.monotonic()
        try:
            for i, p in enumerate(paths, 1):
                out.append(self._entry_for(p))
                now = time.monotonic()
                if dlg is None:
                    # Nothing to report to on the last file — the dialog would
                    # appear and close in the same breath.
                    if i == total or now - t0 < self._DROP_PROGRESS_AFTER:
                        continue
                    dlg = BusyDialog(self.host.dialog_parent(),
                                     i18n.t("➕  Adding %s tracks…") % f"{total:,}",
                                     cancelable=True)
                    dlg.cancel_requested.connect(lambda: cancelled.append(True))
                    dlg.show_after(0)   # already past the delay — up on the next tick
                    last = 0.0          # …which the forced repaint below pumps
                if now - last >= 0.08:
                    # Repainting per file would cost more than the reads do.
                    last = now
                    dlg.set_progress(i, total, p.name, (now - t0) / i * (total - i))
                    QApplication.processEvents()
                if cancelled:
                    break
        finally:
            if dlg is not None:
                dlg.finish()
        return out

    def _resolve_drop_entries(self, files: list[Path]) -> list[MusicEntry]:
        """Resolve dropped paths to MusicEntries (expanding .m3u playlists), keeping
        drop order. Unreadable single files surface a message; m3u lines are silent."""
        # Flattened first so the whole drop — a folder of three hundred included —
        # is ONE pass under one progress dialog, instead of a stutter per playlist.
        todo: list[tuple[Path, bool]] = []   # (path, came out of an .m3u)
        for p in files:
            if p.suffix.lower() in (".m3u", ".m3u8"):
                todo += [(tp, True) for tp in self._m3u_track_paths(p)]
            else:
                todo.append((p, False))
        out: list[MusicEntry] = []
        unreadable: list[Path] = []
        for (p, from_m3u), ent in zip(todo, self._entries_for_paths(
                [tp for tp, _ in todo]), strict=True):
            if ent is not None:
                out.append(ent)
            elif not from_m3u:
                unreadable.append(p)
        if unreadable:
            # One message for the lot: a folder can hold a hundred files that
            # aren't music, and a hundred modal boxes is not a report.
            names = [p.name for p in unreadable[:8]]
            if len(unreadable) > 8:
                names.append(i18n.t("… plus %d more") % (len(unreadable) - 8))
            QMessageBox.information(
                self, "Wishlist",
                i18n.t("Couldn't read as an audio track:") + "\n\n" + "\n".join(names)
            )
        return out

    def _not_yet_held(self, cur: list, new_entries: list) -> list:
        """The `new_entries` whose audio is neither in `cur` nor earlier in the batch
        — a copy of a held title on another drive is the same title (`_audio_keys`)."""
        seen: set = set()
        for e in cur:
            seen |= self._audio_keys(e)
        out: list[MusicEntry] = []
        for ent in new_entries:
            keys = self._audio_keys(ent)
            if keys & seen:
                continue
            seen |= keys
            out.append(ent)
        return out

    def _insert_drop_files(self, files: list[Path], at: int) -> int:
        """Insert dropped files into the flat Wishlist at gap `at` (0..rowCount),
        skipping tracks already present. Returns how many NEW tracks were inserted."""
        new_entries = self._resolve_drop_entries(files)
        if not new_entries:
            return 0
        cur  = self._row_meta.entries()
        to_add = self._not_yet_held(cur, new_entries)
        if not to_add:
            return 0
        at = max(0, min(at, len(cur)))
        final   = cur[:at] + to_add + cur[at:]
        self._render_flat_entries(final)
        # The rebuild resets the scroll to the top — bring the just-dropped rows back
        # into view and select them so the focus stays where the user dropped them.
        self._focus_rows(range(at, at + len(to_add)))
        return len(to_add)

    def _song_pos_at(self, at: int) -> int:
        """Table-row gap `at` → position in the SONG list: the ─── round headers
        sitting between the songs don't count. Measuring from the first song row
        instead drifts one place per header the gap sits below — with a warm-up
        list carrying a header per round that's most of the list."""
        return sum(1 for r in self._row_meta.song_rows() if r < at)

    def _insert_warmup_files(self, files: list[Path], at: int) -> int:
        """Insert dropped tracks into the warm-up / ETDS party list at the table-row
        gap `at` (as returned by `_drop_index`), then re-render.

        The ─── round headers are derived from the track ORDER, so a wish dropped
        into the middle re-cuts the rounds around it — that IS the point: during a
        party the floor decides, not the plan. Tracks already in the list are
        skipped. Returns how many were inserted."""
        new_entries = self._resolve_drop_entries(files)
        if not new_entries:
            return 0
        cur = self._row_meta.entries()
        to_add = self._not_yet_held(cur, new_entries)
        if not to_add:
            return 0
        idx = self._song_pos_at(at)
        self._reload_warmup(cur[:idx] + to_add + cur[idx:])
        # Show the wishes where they landed.
        self._focus_rows([r for r, m in self._row_meta.numbered()
                          if any(m.entry is en for en in to_add)])
        return len(to_add)

    def _reload_warmup(self, entries: list[MusicEntry] | None = None,
                       rebuild: bool = False):
        """Re-render the warm-up / ETDS party list (default: from its current
        tracks) — the ─── headers are derived during the load, so any change of
        order or of the grouping view has to go through here.

        Keeps the current scroll offset, like `_rebuild_dynamic`: the rebuild
        throws every row away and the bar would fall back to the top, leaving the
        operator to scroll their place back after each edit.

        An edit that only adds or drops tracks doesn't get that far — see
        `_warmup_edit_in_place`, which moves the rows under it instead of
        building the list again. `rebuild` skips that: a 🏷 re-tag changes the
        dance of a title already in the list, which no row move shows."""
        if entries is None:
            entries = self._row_meta.entries()
        placed = self._row_meta.placements()
        scroll = self.verticalScrollBar().value()
        # The greyed-out played rows are remembered by (row, column), and the
        # edit moves rows: give every one of them its own colour back FIRST,
        # while those numbers still mean the rows they were taken from.
        self._ungrey_played_rows()
        if rebuild or not self._warmup_edit_in_place(entries):
            self.load_warmup(entries, self._warmup_label, self._warmup_style,
                             self._warmup_class, self._warmup_relax,
                             self._play_cb, self._suggester,
                             running_order=self._player_list)
        self._restore_scroll(scroll)
        # A rebuild dropped every row widget, and an in-place edit moved the rows
        # under the change — either way the ■ marker goes back on the track that
        # is still playing.
        self._row_meta.adopt(placed)
        self._follow_play_row()
        # …and grey the played ones again, now that the rows — and the running
        # one, which keeps its own colours — sit where they finally sit.
        self._grey_played_rows()

    # Columns that can be sorted, each with a sort key over a MusicEntry.
    # (Heat / ▶ / ↺ carry no orderable value, so clicking them does nothing.)
    _FLAT_SORT_KEYS = {
        _COL_DANCE: _dance_sort_key,
        _COL_TITLE: lambda e: display_title(e).lower(),
        _COL_ARTIST: lambda e: ((getattr(e, "tag_artist", None) or "").lower(),
                                (e.title or "").lower()),
        _COL_BPM:   lambda e: (e.bpm if e.bpm is not None else -1, (e.title or "").lower()),
        _COL_LEN:   lambda e: (getattr(e, "duration", 0) or 0, (e.title or "").lower()),
        _COL_POP:   lambda e: (e.popularity or 0, (e.title or "").lower()),
        _COL_CLASS: lambda e: (",".join(e.classes_ok) if getattr(e, "classes_ok", None)
                               else "", (e.title or "").lower()),
        _COL_RATING: lambda e: (getattr(e, "rating", None) or 0, (e.title or "").lower()),
        _COL_CUSTOM: lambda e: ((getattr(e, "custom", None) or "").lower(),
                                (e.title or "").lower()),
        _COL_FILE: lambda e: (e.title or "").lower(),
        _COL_ALBUM: lambda e: ((getattr(e, "tag_album", None) or "").lower(),
                               (e.title or "").lower()),
        _COL_COMMENT: lambda e: ((getattr(e, "tag_comment", None) or "").lower(),
                                 (e.title or "").lower()),
    }

    def _sortable_as_list(self) -> bool:
        """True where the rows are a plain list the user owns the order of: the
        Wishlist, and a deck in ✋ free order. A static or dynamic deck says no —
        there the row order IS the round/heat plan, not a view of it."""
        return bool(self._flat_mode or self._player_list)

    def _on_header_section_double_clicked(self, col: int):
        """Sort the list by the double-clicked column (no-op on a planned deck)."""
        if not self._sortable_as_list():
            return
        self._sort_flat_by_column(col)

    def _sort_flat_by_column(self, col: int):
        keyfn = self._FLAT_SORT_KEYS.get(col)
        if keyfn is None:
            return
        entries = self._row_meta.entries()
        if len(entries) < 2:
            return
        # Sorting the same column again flips ascending ↔ descending.
        if col == self._flat_sort_col:
            self._flat_sort_desc = not self._flat_sort_desc
        else:
            self._flat_sort_col = col
            self._flat_sort_desc = False
        try:
            entries.sort(key=keyfn, reverse=self._flat_sort_desc)
        except Exception:
            return
        if self._flat_mode:
            self._render_flat_entries(entries)
        else:
            # A running order carries ─── headers derived from the order itself,
            # so its rebuild has to go the load_warmup way.
            self._reload_warmup(entries)
        arrow = "▼" if self._flat_sort_desc else "▲"
        what = "Wishlist" if self._flat_mode else (self._warmup_label or "List")
        hdr = self.horizontalHeaderItem(col)
        self.statusBar_message(
            f"↕ {what} sorted by {hdr.text() if hdr is not None else ''} {arrow}")

    def statusBar_message(self, msg: str):
        """Surface a short status note via the main window's status bar, if reachable."""
        self.host.show_status(msg)

    def _render_flat_entries(self, entries):
        """Rebuild the flat (wishlist) table from an ordered entry list, keeping
        play_cb/suggester intact and the ■ marker on the playing track, wherever
        it lands. The scroll offset is kept too — see `_restore_scroll`."""
        placed = self._row_meta.placements()
        scroll = self.verticalScrollBar().value()
        self._row_meta.clear()
        self.setRowCount(0)
        for e in entries:
            self._append_entry(e, notify=False)
        self._restore_scroll(scroll)
        self._row_meta.adopt(placed)
        self._follow_play_row()
        self._notify_changed()

    def _confirm_delete(self, title: str, text: str) -> bool:
        """Yes/No guard for a destructive deck edit (slot / heat / round). Returns
        True only when the user confirms; defaults to No so an accidental Enter
        cancels."""
        ans = QMessageBox.question(
            self, title, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _title_rows_for(self, row: int) -> set:
        """Which rows a "remove this title" acts on.

        Right-clicking inside a selection means the selection; right-clicking
        outside one means only the row under the mouse. Shared by the context
        menu of every deck so the two cannot disagree about it."""
        sel = {ix.row() for ix in self.selectedIndexes()}
        if row in sel:
            rows = {r for r in sel
                    if 0 <= r < len(self._row_meta) and self._row_meta[r]
                    and not self._row_meta[r].theme
                    and self._row_meta[r].entry is not None}
            if rows:
                return rows
        return {row}

    def _remove_titles_caption(self, n: int) -> str:
        """The menu entry that takes n titles out of this list. Same f-string
        problem as the prompt below, same answer."""
        if self._player_list:
            # Free order: the row itself goes, nothing stays behind.
            return (i18n.t("🗑  Remove %d selected titles") % n
                    if n > 1
                    else i18n.t("🗑  Remove this title"))
        return (i18n.t("🗑  Remove %d selected titles (keep slots)") % n if n > 1
                else i18n.t("🗑  Remove this title (keep slot)"))

    def _remove_songs_prompt(self, n: int) -> str:
        """What the confirm asks before n songs are taken out. A planned grid
        keeps the empty slot; a free running order does not, and saying so is
        the difference between "it vanished" and "I meant that".

        Translated here rather than left to the hook: an f-string arrives at
        QMessageBox already assembled and matches no catalog key."""
        if self._player_list:
            return (i18n.t("Remove %d songs from the running order?") % n
                    if n > 1
                    else i18n.t("Remove this song from the running order?"))
        return (i18n.t("Remove %d songs from their slots? The slots stay empty.") % n
                if n > 1
                else i18n.t("Remove this song from its slot? The slot stays empty."))

    def _clear_selected_slots(self) -> bool:
        """Deck helper: empty every selected heat slot — the track is removed but the
        slot stays in the grid (renders "⚠ No song found"), ready for a new pick or
        drop. Header / theme rows are skipped. Asks for confirmation first. Returns
        True if the key was handled (incl. a cancelled confirm), False if nothing
        was eligible to clear."""
        # A stacked '↳ backup N' row counts: _clear_slots_at drops it from the
        # overlay rather than emptying the slot under it.
        songs = {r for r, m in self._row_meta.numbered() if not m.theme}
        eligible = {ix.row() for ix in self.selectedIndexes()} & songs
        if not eligible:
            return False
        if not self._confirm_delete("Remove song",
                                    self._remove_songs_prompt(len(eligible))):
            return True   # cancelled, but still consume the key
        self._clear_slots_at(eligible)
        return True

    def _remove_duplicate_titles(self, on_load: bool = False) -> int:
        """♊ Take out every track whose title this list already holds further up.

        The same recording can sit in the library twice — the C: and the F: copy,
        a copy with edited tags — and an .m3u written from both carries it twice.
        Of identical audio the last copy stays and the earlier ones go — later in
        the rounds the list tends to carry the better title. Another file of the
        same title (a tournament '_cut', a re-encode: same cleaned title in the
        same dance, `_title_key`) is a different recording, so the user picks per
        title which file to keep (`_ask_which_duplicates`), or keeps them all.
        Removed tracks go the way a Del would take them (a wishlist row or a
        running-order row is removed, a deck slot is emptied). Asks first.
        `on_load` is the check right after a list arrived: a clean list then says
        nothing. Returns how many tracks were removed."""
        dups = self._duplicate_rows()
        if not dups:
            if not on_load:
                _show_toast(self, "✅  No duplicate titles in this list")
            return 0
        copies: dict[int, list[int]] = {}       # first row -> every row of that audio
        for r, first, same in dups:
            if same:
                copies.setdefault(first, [first]).append(r)
        last = {row: g[-1] for g in copies.values() for row in g}
        identical = [(row, g[-1]) for g in copies.values() for row in g[:-1]]
        by_title: dict[int, set[int]] = {}      # a title's files, each by its copy that stays
        for r, first, same in dups:
            if not same:
                by_title.setdefault(first, {last.get(first, first)}).add(last.get(r, r))
        name = self.host.deck_name()
        if by_title:
            rows = self._ask_which_duplicates(
                identical, [sorted(g) for g in by_title.values()])
            if rows is None:
                return 0
        else:
            n = len(identical)
            lines = [f"•  {self._row_meta[r].entry.title}" for r, _first in identical[:8]]
            if n > 8:
                lines.append(i18n.t("… and %d more") % (n - 8))
            where = f"“{name}”" if name else i18n.t("This list")
            if not self._confirm_delete(
                    "Duplicate titles",
                    (i18n.t("%s holds %d title twice — the same audio, e.g. a copy of the file on another drive:\n\n%s\n\nRemove the earlier copy? The last one stays.") if n == 1
                     else i18n.t("%s holds %d titles twice — the same audio, e.g. a copy of the file on another drive:\n\n%s\n\nRemove the earlier copies? The last one stays."))
                    % (where, n, "\n".join(lines))):
                return 0
            rows = {r for r, _first in identical}
        if not rows:
            _show_toast(self, "✅  Kept all titles")
            return 0
        n = len(rows)
        if self._flat_mode:
            self._remove_rows(rows)
        elif self._warmup:
            self._drop_running_order_rows(rows)
        else:
            self._clear_slots_at(rows)
        log.info("♊ Duplicate titles removed\n"
                 "list: %s\n"
                 "removed: %d\n"
                 "trigger: %s", name or "?", n, "load" if on_load else "menu")
        _show_toast(self, (i18n.t("🧹  Removed %d duplicate title") if n == 1
                           else i18n.t("🧹  Removed %d duplicate titles")) % n)
        return n

    def _ask_which_duplicates(self, identical, groups) -> set[int] | None:
        """Show `DuplicateTitlesDialog`: `identical` (row, first row) pairs go for
        sure, each group (rows of one title) keeps the file the user picks.
        Returns every row to remove, or None when cancelled."""
        from gui.dialogs.duplicate_titles_dialog import DuplicateTitlesDialog

        def entry(r):
            return self._row_meta[r].entry
        dlg = DuplicateTitlesDialog(
            self,
            identical=[(entry(r), entry(first)) for r, first in identical],
            groups=[[(r, entry(r)) for r in g] for g in groups],
            play_cb=self._play_cb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return {r for r, _first in identical} | dlg.removed_rows()

    def _clear_slots_at(self, row_set, select_after: bool = False) -> bool:
        """Empty the given heat slots (static: slot stays as "⚠ No song found"; dynamic:
        a '↳ backup N' row drops from the overlay; free order: the row goes altogether).
        Shared by the Del key (selection) and the deck→wishlist MOVE (dragged rows).
        Returns True if anything was cleared. select_after → leave the source's cursor
        on the (first) emptied slot, so moving a track OUT keeps the selection where it
        was."""
        if self._player_list:
            return self._drop_running_order_rows(row_set, select_after)
        rows = sorted({r for r in row_set if 0 <= r < len(self._row_meta)})
        cleared = False
        dropped_backup = False
        for r in rows:
            if not (0 <= r < len(self._row_meta)):
                continue
            m = self._row_meta[r]
            if not m or m.theme or m.entry is None:
                continue
            if r == self._current_play_row and self._play_cb:
                self._play_cb(None)
                self._current_play_row = -1
            # A '↳ backup N' row lives in the backups overlay, NOT a grid slot — its
            # h_idx/d_idx point at the PRIMARY slot, so the grid-clear below would wipe
            # the wrong track and leave the backup dangling (it would reappear on the
            # next rebuild). Drop it from the overlay and re-render once at the end.
            if m.backup:
                if self._discard_backup_entry(m):
                    dropped_backup = True
                    cleared = True
                continue
            m.entry = None
            if self._playlist is not None and m.round_name is not None:
                self._playlist[m.round_name][m.h_idx][m.d_idx] = None
            bg = _C_ROW_EVEN if m.h_idx % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(r, m, bg)
            cleared = True
        if dropped_backup:
            self._rebuild_dynamic()
        elif cleared:
            self._notify_changed()
        if select_after and cleared and rows and self.rowCount():
            self._focus_rows([min(rows[0], self.rowCount() - 1)])
        return cleared

    def _drop_running_order_rows(self, row_set, select_after: bool = False) -> bool:
        """Free order: take the given tracks OUT of the list instead of emptying
        a slot under them.

        There is no grid behind a running order — a title sits where it was
        dropped and the ─── strips are cut from the order itself. An emptied slot
        would be a hole nothing can fill: no pick plans into it, and a dropped
        song lands where it was dropped rather than in the gap. So the row goes,
        and the strips re-cut around what is left."""
        rows = set()
        for r in row_set:
            m = self._row_meta.at(r)
            if m is not None and m.filled:
                rows.add(r)
        if not rows:
            return False
        if self._current_play_row in rows and self._play_cb:
            self._play_cb(None)
            self._current_play_row = -1
        self._reload_warmup([m.entry for r, m in self._row_meta.numbered()
                             if r not in rows])
        if select_after and self.rowCount():
            self._focus_rows([min(min(rows), self.rowCount() - 1)])
        return True

