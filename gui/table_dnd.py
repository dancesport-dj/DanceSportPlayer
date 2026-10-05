"""PlaylistTable drag & drop: external drops, dance-header drag, internal move/swap.

Mixin of PlaylistTable — extracted 1:1 from gui/playlist_table.py in the
big-module split; behaviour unchanged."""
import logging

import re
from PySide6.QtCore import (
    QMimeData,
    QTimer,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QDrag,
)
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)
from pathlib import Path
from planner import i18n
from planner.models import ALLOW_REPEAT, MusicEntry
from planner.terms import dance_name
from gui.common import (
    _C_ROW_EVEN,
    _C_ROW_ODD,
)
from shared.columns import (
    _COL_TITLE,
)
from shared.audio_files import (
    _AUDIO_EXTS,
)
from shared.widgets import (
    _show_toast,
)

log = logging.getLogger("dancesport.gui.playlist_table")

# `PlaylistTable` is late-bound into this module by gui.playlist_table after
# the class is defined (a top-level import would be circular): the methods
# here isinstance-check drag sources against it at call time.
PlaylistTable = None


class TableDragDropMixin:
    """Drag & drop concern: accept external tracks/playlists, start drags,
    reorder dances by header drag, move/swap tracks between slots."""

    # ── Drag & Drop ──────────────────────────────────────────────────────────

    # ── Dance-header drag: reorder whole dances ─────────────────────────────────
    # Dance HEADER rows aren't Qt-draggable (not selectable), so the drag is
    # hand-started: press is remembered here, the move threshold launches it.

    def mousePressEvent(self, event):
        self._hdr_press = None
        if (event.button() == Qt.MouseButton.LeftButton
                and not self._flat_mode and self._playlist):
            pos = event.position().toPoint()
            row = self.rowAt(pos.y())
            if row in self._dance_hdr_rows:
                self._hdr_press = (row, pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._hdr_press is not None
                and event.buttons() & Qt.MouseButton.LeftButton):
            row, origin = self._hdr_press
            if ((event.position().toPoint() - origin).manhattanLength()
                    >= QApplication.startDragDistance()):
                dance = self._dance_hdr_dance.get(row)
                self._hdr_press = None
                if dance:
                    self._start_dance_drag(dance)
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._hdr_press = None
        super().mouseReleaseEvent(event)

    def _start_dance_drag(self, dance: str):
        """Drag a dance HEADER to reorder whole dances: the payload is the dance
        code (internal-only mime), the drop target is another dance section."""
        self._dance_drag = dance
        mime = QMimeData()
        mime.setData("application/x-dancesport-dance", dance.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            self._dance_drag = None
            self._stop_autoscroll()
            self._hide_drop_line()

    def startDrag(self, _supported_actions):
        """Build a file-URI drag compatible with external Windows applications (VLC, etc.)."""
        rows = {idx.row() for idx in self.selectedIndexes()}
        # Fallback: if nothing is selected use the current (last-clicked) index
        if not rows:
            cur = self.currentIndex()
            if cur.isValid():
                rows = {cur.row()}

        paths = []
        song_rows = []
        for r in sorted(rows):
            if r < len(self._row_meta) and self._row_meta[r]:
                m = self._row_meta[r]
                entry = m.entry
                # Any row with a real entry is draggable out (file-URI drag) — this
                # includes flat Wishlist rows and Theme-mode rows, which carry
                # theme=True. Round/dance HEADERS are stored as None and skipped
                # above. The theme flag only gates internal slot-to-slot moves
                # (see _internal_drag_src), not dragging a track out of the table.
                if entry:
                    paths.append(entry.path)
                    song_rows.append(r)
        if not paths:
            return

        # Remember the dragged song rows so an internal drop onto another slot can
        # move/swap the track between rounds (see dropEvent). Cleared after exec.
        self._drag_src_rows = song_rows

        mime = QMimeData()
        # setUrls → Qt translates to CF_HDROP (Windows shell drag format)
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        # Plain-text fallback: some external apps (UltraMixer et al.) probe
        # text/plain before/instead of CF_HDROP.
        mime.setText("\n".join(str(p) for p in paths))

        drag = QDrag(self)
        drag.setMimeData(mime)
        # Offer Copy/Move/Link like an Explorer drag — some external apps only
        # accept the drop if their preferred action is among the ones offered,
        # even though we still default to Copy (never MOVE the real MP3 out of
        # the library). Internal slot-to-slot moves are handled manually in
        # dropEvent (keyed off e.source() is self), so no special-casing needed.
        try:
            drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
                      | Qt.DropAction.LinkAction, Qt.DropAction.CopyAction)
        finally:
            self._drag_src_rows = []
            self._stop_autoscroll()
            self._hide_drop_line()

    # ── Accept a track dropped from Similar-Tracks / Explorer / VLC (replace a song) ──

    # Shared with _open_in_default_player so the drop gate and the open gate can
    # never drift apart.
    _AUDIO_DROP_EXTS = _AUDIO_EXTS

    # Windows / UNC / forward-slash path ending in an audio extension. Used to dig a
    # real file path out of opaque drag payloads (e.g. UltraMixer's Java-serialized
    # PlayListFile object, which carries no file:// URL or plain-text path).
    _RAW_PATH_RE = re.compile(
        r"((?:[A-Za-z]:[\\/]|\\\\)[^\x00\r\n\t\"<>|]+?"
        r"\.(?:mp3|m4a|m4b|flac|wav|ogg|oga|opus|aac|wma|aiff|aif))",
        re.IGNORECASE,
    )

    def _path_from_raw_mime(self, md) -> Path | None:
        """Last resort: scan every drag payload's raw bytes for an embedded audio
        file path (covers players that drop a serialized object, not a URL)."""
        if md is None:
            return None
        for fmt in md.formats():
            try:
                raw = bytes(md.data(fmt))
            except Exception:
                continue
            for enc in ("utf-8", "latin-1", "utf-16-le"):
                text = raw.decode(enc, "ignore")
                for m in self._RAW_PATH_RE.finditer(text):
                    p = self._coerce_audio_path(m.group(1))
                    if p is not None:
                        return p
        return None

    def _coerce_audio_path(self, raw: str) -> Path | None:
        """Turn a dragged string (a bare path, a quoted path or a file:// URL — as
        VLC and other players hand off) into a real local audio file path, or None."""
        if not raw:
            return None
        s = raw.strip().strip('"').strip("'")
        if not s:
            return None
        if s.lower().startswith("file:"):
            u = QUrl(s)
            if u.isLocalFile():
                s = u.toLocalFile()
        p = Path(s)
        if p.suffix.lower() in self._AUDIO_DROP_EXTS and p.is_file():
            return p
        return None

    def _droppable_path(self, e) -> Path | None:
        """Local audio-file path carried by a drag, from any source.

        Explorer hands off file URLs (CF_HDROP); VLC and some players instead pass
        a file:// URL or the raw path as text — so we check urls() first, then fall
        back to the text payload (one path per line)."""
        md = e.mimeData()
        if not md:
            return None
        if md.hasUrls():
            for url in md.urls():
                p = (self._coerce_audio_path(url.toLocalFile())
                     if url.isLocalFile()
                     else self._coerce_audio_path(url.toString()))
                if p is not None:
                    return p
        if md.hasText():
            for line in md.text().splitlines():
                p = self._coerce_audio_path(line)
                if p is not None:
                    return p
        # Players that drop a serialized object (UltraMixer, some DJ apps) carry the
        # path only inside raw bytes — dig it out as a last resort.
        return self._path_from_raw_mime(md)

    def _has_droppable(self, e) -> bool:
        """True if a drag carries something a DECK can take: an audio file, or a
        folder of them. Cheap enough for the per-pixel dragMove check — the folder
        is counted here, never walked (see `_wishlist_droppables`)."""
        if self._droppable_path(e) is not None:
            return True
        return any(p.is_dir() for p in self._wishlist_droppables(e, expand_dirs=False))

    def _dropped_m3u(self, e) -> Path | None:
        """If a drop carries exactly ONE .m3u/.m3u8 playlist file (from Explorer), return
        it — else None. Used to IMPORT a playlist file dropped onto a deck, the way the
        📂 Import M3U button loads it into the focused deck."""
        m3us = self._dropped_m3us(e)
        return m3us[0] if len(m3us) == 1 else None

    def _dropped_m3us(self, e) -> list[Path]:
        """The playlist files of a drop that carries nothing else, else []."""
        if isinstance(e.source(), PlaylistTable):
            return []   # internal drag (deck / wishlist rows) is never a file import
        # expand_dirs=False: a dropped FOLDER stays itself here, so a folder that
        # happens to hold a single .m3u doesn't get read as "import this playlist,
        # replacing the deck" — it means its music, like every other folder drop.
        files = self._wishlist_droppables(e, expand_dirs=False)
        if files and all(f.suffix.lower() in (".m3u", ".m3u8") for f in files):
            return files
        return []

    def _confirm_m3u_replaces(self, m3u: Path) -> bool:
        """Ask before an .m3u dropped onto a list that already holds tracks wipes
        it: importing a playlist file REPLACES the list, it never appends to it,
        and a file dragged in from Explorer is an easy thing to do by accident.
        Nothing to lose on an empty list, so nothing to ask."""
        songs = self._row_meta.song_count()
        if not songs:
            return True
        name = self.host.deck_name()
        ans = QMessageBox.question(
            self, "Import M3U",
            i18n.t("%s already holds %d track(s).\n\nImporting %s REPLACES them — the list is "
                   "loaded fresh from the file, the tracks in it now are dropped.\n\nImport anyway?")
            % (f"“{name}”" if name else i18n.t("This list"), songs, m3u.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    def _event_row(self, e) -> int:
        """Row under the cursor for a drag event (Qt5/Qt6 position API safe)."""
        return self.rowAt(self._event_y(e))

    def _event_y(self, e) -> int:
        """Vertical pixel of a drag event in the viewport (Qt5/Qt6 safe)."""
        return e.position().toPoint().y() if hasattr(e, "position") else e.pos().y()

    def _dynamic_drop_row(self, e) -> int:
        """Target row for a dynamic-mode drop. Like _event_row, but a drop that lands
        in a GAP between rows or in the empty area below the grid snaps to the nearest
        VISIBLE row, so it still resolves to the round the cursor is over instead of
        falling through to the first round (the old 'dropped here, landed in Vorrunde'
        bug). -1 only when the grid is completely empty."""
        row = self._event_row(e)
        if row >= 0:
            return row
        y = self._event_y(e)
        best, best_d = -1, None
        for r in range(self.rowCount()):
            if self.isRowHidden(r):
                continue
            center = self.rowViewportPosition(r) + self.rowHeight(r) / 2
            d = abs(y - center)
            if best_d is None or d < best_d:
                best, best_d = r, d
        return best

    def _deck_adds_on_drop(self) -> bool:
        """True for a playlist DECK in a player-only install: a dropped title is
        ADDED to the list at the place it was dropped, never swapped in for the
        one under the cursor. Replacing a slot is planning work — the operator
        running the evening drags a song in because it should also be played,
        and losing the title that was there is never what they meant. The flat
        wishlists and the ETDS party list already insert; they keep their own
        paths below."""
        return not self._flat_mode and not self._warmup and self.player_only()

    def plays_flat(self) -> bool:
        """True for a deck that is — or that the next load should make — the flat
        running order of a player-only install (see `load_player_list`)."""
        return bool(self._player_list or self._deck_adds_on_drop())

    def become_player_list(self):
        """Turn this deck into the flat running order, keeping the order it is
        already showing — which for a competition grid IS its playing order.

        A draw that was planned before the install was switched to player mode
        still renders as a round/heat grid, and in that grid a title can only
        move into another slot of its own dance. There is nobody planning here,
        so the grid is only in the way: re-render it as the running order and
        every row can be dragged wherever the evening needs it. The rounds it was
        drawn into are the one thing worth keeping — they head the ─── strips."""
        entries = self._row_meta.entries()
        sections: dict = {}
        for m in self._row_meta.songs():
            if m.round_name:
                sections.setdefault(m.path_str, m.round_name)
        # A deck that was never generated has no play callback yet — the same
        # wiring the dynamic drop relies on.
        if self._play_cb is None:
            self.host.ensure_deck_ready()
        label = self.host.deck_name()
        self.load_player_list(entries, label, self._play_cb, self._suggester,
                              sections=sections)

    def _supports_row_reorder(self) -> bool:
        """True for lists whose own rows may be freely reordered by an internal
        drag (drop into the red-line gap): the flat wishlists AND the warm-up
        ("Eintanzen") list. Playlist decks instead swap within a dance only."""
        return self._flat_mode or self._warmup

    def _internal_drag_src(self) -> int | None:
        """First still-valid song row of an in-flight internal drag, or None."""
        for r in self._drag_src_rows:
            if 0 <= r < len(self._row_meta):
                m = self._row_meta[r]
                if m and not m.theme and m.entry is not None:
                    return r
        return None

    def _resolve_internal_drop(self, row: int, src: int | None) -> int:
        """Target slot for an internal slot-to-slot drag, from the row the cursor
        is over. Taking that row as-is makes every round boundary a dead zone: the
        round and dance HEADER rows carry no meta, so a track aimed at the start of
        the next round has nothing to land on and the drop is silently refused.
        Resolve a header row to the first slot of the DRAGGED track's dance inside
        the round it belongs to. A real song row of another dance is left alone —
        that's a wrong-dance aim, not a boundary."""
        if src is None or self._internal_drop_ok(src, row):
            return row
        if 0 <= row < len(self._row_meta) and self._row_meta[row] is not None:
            return row
        rname = self._round_of_row(row)
        if rname is None:
            return row
        dance = self._row_meta[src].dance
        for r, m in enumerate(self._row_meta):
            if (m and not m.theme and not m.backup
                    and m.round_name == rname and m.dance == dance):
                return r
        return row

    def _internal_drop_ok(self, src: int | None, row: int) -> bool:
        """True if the dragged track (row `src`) may drop onto slot `row`:
        a real same-dance heat slot in another (or the same) position."""
        if src is None or not (0 <= row < len(self._row_meta)) or row == src:
            return False
        m = self._row_meta[row]
        return (m is not None and not m.theme and not m.backup
                and m.dance == self._row_meta[src].dance)

    def dragEnterEvent(self, e):
        if e.source() is self:
            # Dance-header drag: reorder whole dance sections within this deck.
            if self._dance_drag:
                e.setDropAction(Qt.DropAction.MoveAction)
                e.accept()
                return
            # Wishlist / warm-up list: reorder its own rows by drag-and-drop.
            # (CopyAction keeps us inside startDrag's offered actions; the reorder
            # itself is manual.)
            if self._supports_row_reorder() and self._drag_src_rows:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
                return
            # Internal slot-to-slot move (e.g. a track from one round to another).
            if self._internal_drag_src() is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
            else:
                e.ignore()
            return
        if self._flat_mode:
            # Wishlist: accept audio + .m3u + whole folders from anywhere — Explorer,
            # another deck, or the OTHER wishlist (drag-and-drop between wishlists).
            if self._wishlist_droppables(e, expand_dirs=False):
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
            else:
                e.ignore()
            return
        # A single .m3u dropped onto a deck = import it into this deck; several
        # go into the free decks, one each.
        if self._dropped_m3us(e):
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            return
        # External track drop (Similar-Tracks / file managers) onto a real song row.
        if not self._has_droppable(e):
            e.ignore()
            return
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()

    def _drag_y(self, e) -> int:
        return e.position().toPoint().y() if hasattr(e, "position") else e.pos().y()

    def _drop_index(self, e) -> int:
        """Flat (Wishlist) insert position for a drop: the row GAP under the cursor.
        Cursor in a row's upper half → insert before it, lower half → after it;
        below the last row → append. Returns an index in 0..rowCount."""
        y   = self._drag_y(e)
        row = self.rowAt(y)
        if row < 0:
            return self.rowCount()
        mid = self.rowViewportPosition(row) + self.rowHeight(row) / 2
        return row if y < mid else row + 1

    def _show_drop_line(self, idx: int):
        """Place the red drop-indicator line at insert gap `idx` (0..rowCount)."""
        n = self.rowCount()
        if idx >= n:
            y = (self.rowViewportPosition(n - 1) + self.rowHeight(n - 1)) if n else 0
        else:
            y = self.rowViewportPosition(idx)
        self._drop_line.setGeometry(0, max(0, y - 1), self.viewport().width(), 3)
        self._drop_line.raise_()
        self._drop_line.show()
        self._drop_row_hl.hide()

    def _show_drop_row(self, row: int):
        """Highlight the whole deck row `row` a drop would replace/land on."""
        if not (0 <= row < self.rowCount()):
            self._hide_drop_line()
            return
        y = self.rowViewportPosition(row)
        self._drop_row_hl.setGeometry(0, y, self.viewport().width(), self.rowHeight(row))
        self._drop_row_hl.raise_()
        self._drop_row_hl.show()
        self._drop_line.hide()

    def _hide_drop_line(self):
        """Clear any drop marker (the gap line AND the row highlight)."""
        self._drop_line.hide()
        self._drop_row_hl.hide()

    def _drop_ctrl(self, e) -> bool:
        """True if Ctrl is held during a drop (forces copy instead of move)."""
        try:
            mods = e.modifiers()
        except Exception:
            mods = QApplication.keyboardModifiers()
        return bool(mods & Qt.KeyboardModifier.ControlModifier)

    def _drop_shift(self, e) -> bool:
        """True if Shift is held during a drop. On the warm-up / ETDS party list
        that means "replace the title under the cursor" instead of the default
        "insert the wish at this spot"."""
        try:
            mods = e.modifiers()
        except Exception:
            mods = QApplication.keyboardModifiers()
        return bool(mods & Qt.KeyboardModifier.ShiftModifier)

    def _warmup_replace_drop(self, e, row: int) -> bool:
        """True when a drop onto the warm-up list should REPLACE row `row`: Shift
        held and the cursor actually on a song row (a ─── header has nothing to
        replace, so that stays an insert)."""
        m = self._row_meta[row] if 0 <= row < len(self._row_meta) else None
        return (self._drop_shift(e) and m is not None
                and m.entry is not None)

    # Edge auto-scroll speed (px per 40 ms tick): gentle just inside the margin so
    # the user can ease onto the exact drop point, ramping up only at the very edge.
    _AUTOSCROLL_MIN_PX = 1
    _AUTOSCROLL_MAX_PX = 14

    def _update_drag_autoscroll(self, e):
        """Scroll the table while a drag is held near its top/bottom edge so slots
        that are off-screen (e.g. a later round) can be reached. Speed scales with
        how far into the edge margin the cursor is, so it crawls near the boundary
        and only races at the very edge — fine control over where it lands."""
        y      = self._drag_y(e)
        h      = self.viewport().height()
        margin = 40
        if y < margin:
            self._autoscroll_dir = -1
            depth = (margin - y) / margin
        elif y > h - margin:
            self._autoscroll_dir = 1
            depth = (y - (h - margin)) / margin
        else:
            self._autoscroll_dir = 0
            depth = 0.0
        # Ease-in (depth²) from MIN to MAX so the first part of the margin is slow.
        depth = max(0.0, min(1.0, depth))
        self._autoscroll_speed = int(round(
            self._AUTOSCROLL_MIN_PX
            + depth * depth * (self._AUTOSCROLL_MAX_PX - self._AUTOSCROLL_MIN_PX)))
        if self._autoscroll_dir and not self._autoscroll_timer.isActive():
            self._autoscroll_timer.start()
        elif not self._autoscroll_dir:
            self._autoscroll_timer.stop()

    def _drag_autoscroll(self):
        if not self._autoscroll_dir:
            self._autoscroll_timer.stop()
            return
        sb = self.verticalScrollBar()
        step = max(1, getattr(self, "_autoscroll_speed", self._AUTOSCROLL_MIN_PX))
        sb.setValue(sb.value() + self._autoscroll_dir * step)

    def _stop_autoscroll(self):
        self._autoscroll_dir = 0
        self._autoscroll_timer.stop()

    def dragLeaveEvent(self, e):
        self._stop_autoscroll()
        self._hide_drop_line()
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e):
        self._update_drag_autoscroll(e)
        row = self._event_row(e)
        if e.source() is self:
            if self._dance_drag:
                # Highlight the dance section the dragged dance would move to.
                tgt = self._dance_at_row(row)
                if tgt is not None and tgt != self._dance_drag:
                    hdr = (row if row in self._dance_hdr_rows
                           else self._row_dance_hdr.get(row, -1))
                    if hdr is not None and hdr >= 0:
                        self._show_drop_row(hdr)
                    e.setDropAction(Qt.DropAction.MoveAction)
                    e.accept()
                else:
                    self._hide_drop_line()
                    e.ignore()
                return
            if self._supports_row_reorder() and self._drag_src_rows:
                e.setDropAction(Qt.DropAction.CopyAction)   # reorder within this list
                if self._drop_ctrl(e):
                    # Ctrl held → SWAP with the target track (deck-style row
                    # highlight) instead of moving to a gap.
                    self._show_drop_row(row)
                else:
                    self._show_drop_line(self._drop_index(e))
                e.accept()
                return
            src = self._internal_drag_src()
            # _dynamic_drop_row: empty space below the grid snaps to the nearest
            # visible row instead of falling through as "no row".
            tgt = self._resolve_internal_drop(self._dynamic_drop_row(e), src)
            if self._internal_drop_ok(src, tgt):
                e.setDropAction(Qt.DropAction.CopyAction)
                self._show_drop_row(tgt)   # the RESOLVED slot, not the cursor row
                e.accept()
            else:
                self._hide_drop_line()
                e.ignore()
            return
        if self._flat_mode:
            # Wishlist: accept audio files, .m3u playlists AND whole folders, dropped
            # anywhere — they're inserted at the cursor's gap (shown by the red line).
            if self._wishlist_droppables(e, expand_dirs=False):
                e.setDropAction(Qt.DropAction.CopyAction)
                self._show_drop_line(self._drop_index(e))
                e.accept()
            else:
                self._hide_drop_line()
                e.ignore()
            return
        # A single .m3u dropped onto a deck imports the whole playlist into it;
        # several go into the free decks, one each.
        if self._dropped_m3us(e):
            e.setDropAction(Qt.DropAction.CopyAction)
            self._hide_drop_line()
            e.accept()
            return
        if not self._flat_mode and (self._dynamic or not self._row_meta
                                    or self._deck_adds_on_drop()):
            # Dynamic deck — or an EMPTY deck that this first drop turns dynamic,
            # or any deck of a player-only install. Drops BUILD the grid
            # (auto-fill rounds / extend heats) instead of replacing one slot,
            # so accept anywhere on the table.
            if self._can_dynamic_drop(e):
                e.setDropAction(Qt.DropAction.CopyAction)
                snap = self._dynamic_drop_row(e)
                if 0 <= snap < len(self._row_meta) and self._row_meta[snap]:
                    self._show_drop_row(snap)
                else:
                    self._hide_drop_line()
                e.accept()
            else:
                self._hide_drop_line()
                e.ignore()
            return
        if self._warmup:
            # Eintanzen / ETDS party list: a wish dragged in is INSERTED at the gap
            # under the cursor (red line) — the ─── rounds re-cut around it. Shift
            # replaces the title under the cursor instead.
            if (not self._wishlist_droppables(e, expand_dirs=False)
                    and self._droppable_path(e) is None):
                self._hide_drop_line()
                e.ignore()
                return
            e.setDropAction(Qt.DropAction.CopyAction)
            if self._warmup_replace_drop(e, row):
                self._show_drop_row(row)
            else:
                self._show_drop_line(self._drop_index(e))
            e.accept()
            return
        # Accept onto any heat slot — filled OR empty ("⚠ No song found") — but never
        # onto headers (meta is None) or flat theme rows.
        m = self._row_meta[row] if 0 <= row < len(self._row_meta) else None
        ok = (self._has_droppable(e) and m is not None and not m.theme)
        if ok:
            e.setDropAction(Qt.DropAction.CopyAction)
            self._show_drop_row(row)
            e.accept()
        else:
            self._hide_drop_line()
            e.ignore()

    def dropEvent(self, e):
        self._stop_autoscroll()
        self._hide_drop_line()
        row = self._event_row(e)
        src_tbl = e.source()
        if src_tbl is self:
            # Dance-header drag: move the whole dance to the target section.
            if self._dance_drag:
                tgt = self._dance_at_row(row)
                if tgt is not None and tgt != self._dance_drag:
                    e.setDropAction(Qt.DropAction.MoveAction)
                    e.accept()
                    self._reorder_dance(self._dance_drag, tgt)
                else:
                    e.ignore()
                return
            # Wishlist / warm-up list: reorder its own rows. Ctrl held → SWAP the
            # dragged track with the one under the cursor; otherwise move it to the
            # gap shown by the red line. The reorder re-fills ONLY the rows that
            # actually changed (see _apply_song_reorder), so the scroll position
            # holds at the drop point and there's no full-table rebuild. It's still
            # deferred to the next event-loop tick (QTimer.singleShot(0)) so the
            # drag gesture ends immediately before the autosave/disk-write runs.
            if self._supports_row_reorder() and self._drag_src_rows:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
                src_rows = list(self._drag_src_rows)   # cleared after drag.exec()
                drop_idx = self._drop_index(e)
                ctrl     = self._drop_ctrl(e)
                tgt_row  = row

                def _do():
                    self._drag_src_rows = src_rows      # restore for the helpers
                    try:
                        if ctrl:
                            self._swap_reorder(tgt_row)
                        elif self._warmup:
                            self._reorder_warmup(drop_idx)
                        else:
                            self._reorder_flat(drop_idx)
                    finally:
                        self._drag_src_rows = []
                QTimer.singleShot(0, _do)
                return
            src = self._internal_drag_src()
            # _dynamic_drop_row: empty space below the grid snaps to the nearest
            # visible row instead of falling through as "no row".
            tgt = self._resolve_internal_drop(self._dynamic_drop_row(e), src)
            if self._internal_drop_ok(src, tgt):
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
                # Multiple selected song rows → move the whole block, keeping each
                # track's heat offset from the anchor (single row keeps the old path).
                heats = self._row_meta.heat_rows()
                movable = [r for r in self._drag_src_rows if r in heats]
                if len(movable) > 1:
                    self._move_rows_block(movable, tgt)
                else:
                    self._move_or_swap_rows(src, tgt)
            else:
                e.ignore()
            return
        if self._flat_mode:
            # Wishlist: insert every dropped audio file at the cursor gap; expand
            # any dropped .m3u in place. The red drop line marked the spot.
            files = self._wishlist_droppables(e)
            if not files:
                e.ignore()
                return
            # A .m3u dropped onto an EMPTY wishlist names it after the file (keeping
            # the ⭐ Wishlist prefix): "⭐  Wishlist: <m3u name>".
            was_empty = self.rowCount() == 0
            m3u_drop = next((f for f in files
                             if f.suffix.lower() in (".m3u", ".m3u8")), None)
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            added = self._insert_drop_files(files, self._drop_index(e))
            if was_empty and added and m3u_drop is not None:
                self.host.name_after_playlist(m3u_drop.stem)
            ctrl = self._drop_ctrl(e)
            from_deck = (isinstance(src_tbl, PlaylistTable) and src_tbl is not self
                         and not src_tbl._flat_mode)
            from_wishlist = (isinstance(src_tbl, PlaylistTable) and src_tbl is not self
                             and src_tbl._flat_mode)
            # Both wishlist → wishlist AND deck → wishlist are a MOVE unless Ctrl is held
            # (then a copy). A deck source has its dragged slots emptied so the track is
            # taken OUT of the playlist and lands in the wishlist ("dragged back").
            moved = False
            if added and not ctrl:
                if from_wishlist:
                    moved = src_tbl._remove_rows(src_tbl._drag_src_rows, select_after=True)
                elif from_deck:
                    moved = src_tbl._clear_slots_at(set(src_tbl._drag_src_rows), select_after=True)
            # Auto-clean: a wishlist shouldn't hold tracks already in an open playlist, so
            # re-run the check on every add (user-requested). Skip it for a deck → wishlist
            # drop — that's a deliberate placement, and running it here would instantly
            # remove the very track just dragged in (it's, or just was, in that playlist).
            cleaned = 0
            if not from_deck:
                cleaned = self.host.clean_wishlist_against_playlists(announce=False)
            # Duplicates are auto-filtered by _append_entry, so `added` only counts
            # genuinely new tracks; tell the user when everything was a dup.
            if added:
                msg = (i18n.t("⭐  Moved %d track(s) to the wishlist") if moved
                       else i18n.t("⭐  Added %d track(s) to the wishlist")) % added
                if cleaned:
                    msg += i18n.t("  ·  🧹 %d already in a playlist removed") % cleaned
                _show_toast(self, msg)
            elif cleaned:
                _show_toast(self, i18n.t("🧹  Removed %d track(s) already in a playlist")
                            % cleaned)
            else:
                _show_toast(self, "⭐  Already in the wishlist — nothing added")
            return
        # Several .m3u at once (the 🏆 tab's marked playlists) go into the free
        # decks, one each — what 📂 Import M3U does with several picked files.
        m3us = self._dropped_m3us(e)
        if len(m3us) > 1 and self.host.warmup_table() is not self:
            fan_out = self.host.import_m3u_multi_loader()
            if fan_out is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
                fan_out([str(p) for p in m3us])
                return
        # A single .m3u dropped onto a deck = IMPORT it into this deck (like 📂 Import),
        # detecting rounds / heats / dances — not a track-by-track append.
        m3u = self._dropped_m3u(e)
        if m3u is not None:
            host = self.host
            if host.warmup_table() is self:
                # The Eintanzen panel keeps a flat list — load the .m3u as one, not
                # as a round/heat import. It is recognised by BEING the panel, not
                # by `_warmup`: that flag is only raised once a list has been
                # loaded (an empty panel fell through to the deck import, which has
                # no grid here and left it blank) and it is raised on a player
                # deck too, which has its own loader below. Asked before
                # `plays_flat()`, true of a panel already holding a running order —
                # else the second file dropped on it would arrive as a deck and
                # lose the 🤸 title.
                load = host.warmup_m3u_loader()
            elif self.plays_flat():
                # Player-only install: the deck IS the running order, so the file
                # is one flat list — there is no draw in it to rebuild.
                load = host.player_list_m3u_loader()
            else:
                load = None
            load = load or host.import_m3u_loader()
            if load is not None:
                if not self._confirm_m3u_replaces(m3u):
                    e.ignore()
                    return
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
                load(self, m3u)
                return
        if self._deck_adds_on_drop():
            # A deck of a player-only install: make it the flat running order —
            # empty or still showing a planned grid — then let the insert path
            # below place the dropped track where it was dropped.
            self.become_player_list()
        elif (not self._flat_mode and not self._player_list
              and (self._dynamic or not self._row_meta)):
            # Dynamic deck, or an empty one going dynamic now: build/extend the grid.
            # A deck in free order is never one of them — emptied out, its next drop
            # would otherwise silently hand it a grid back.
            if not self._can_dynamic_drop(e):
                e.ignore()
                return
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            pre_planned = self._planned_keys()
            self._dynamic_drop(e, self._dynamic_drop_row(e), replace=self._drop_ctrl(e))
            # dragging from another deck / wishlist is a MOVE
            self._move_from_drag_source(e, pre_planned=pre_planned)
            return
        # Static deck / warm-up: collect EVERY dropped track.
        paths = [p for p in self._wishlist_droppables(e)
                 if p.suffix.lower() not in (".m3u", ".m3u8")]
        if not paths:
            path = self._droppable_path(e)
            paths = [path] if path is not None else []
        if self._warmup and not self._warmup_replace_drop(e, row):
            # ETDS party list: people wish for a song mid-evening — ADD it where it
            # was dropped and let the rounds re-cut around it. Shift+drop is the
            # way to overwrite a planned title instead.
            if not paths:
                e.ignore()
                return
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            pre_planned = self._planned_keys()
            added = self._insert_warmup_files(paths, self._drop_index(e))
            if added:
                self._move_from_drag_source(e, pre_planned=pre_planned)
                _show_toast(self, (i18n.t("➕  Added %d track(s)") if self._player_list
                                   else i18n.t("➕  Added %d track(s) — rounds re-cut"))
                            % added)
            else:
                _show_toast(self, "Already in the list — nothing added")
            return
        if not paths or not (0 <= row < len(self._row_meta)):
            e.ignore()
            return
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()
        pre_planned = self._planned_keys()
        placed_rows = [row] if self._replace_row_with_path(row, paths[0]) else []
        if len(paths) > 1:
            placed_rows += self._fill_empty_slots_with(paths[1:], row + 1)
            skipped = len(paths) - len(placed_rows)
            if placed_rows:
                msg = i18n.t("🎯  Placed %d track(s)") % len(placed_rows)
                if skipped:
                    msg += i18n.t("  (%d skipped — no free slot)") % skipped
                _show_toast(self, msg)
        if placed_rows:
            # dragging from another deck / wishlist is a MOVE
            self._move_from_drag_source(e, pre_planned=pre_planned)
            # Instant Check-Music on the landed rows — AFTER the queued
            # _fill_song_row repaints, so the red marks paint over the final bg.
            QTimer.singleShot(0, lambda: self._mark_drop_issues(placed_rows))

    def _fill_empty_slots_with(self, paths: list[Path], start_row: int) -> list[int]:
        """Static deck multi-drop: place each extra track into the first EMPTY heat
        slot of its own dance, scanning from `start_row` downward and wrapping to
        the top. Tracks with no free slot are skipped. Returns the filled rows."""
        placed: list[int] = []
        n = len(self._row_meta)
        order = list(range(max(0, start_row), n)) + list(range(0, max(0, start_row)))
        # Resolved in one pass so a folder's worth of tracks gets the progress
        # dialog rather than reading tags silently in the placement loop.
        for p, ent in zip(paths, self._entries_for_paths(paths)):
            dance = getattr(ent, "dance", None) if ent else None
            for r in order:
                m = self._row_meta[r]
                if (m and not m.theme and not m.backup
                        and m.entry is None
                        and (dance is None or m.dance == dance)):
                    if self._replace_row_with_path(r, p):
                        placed.append(r)
                    break
        return placed

    def _mark_drop_issues(self, rows: list[int]) -> None:
        """Instant Check-Music after a slot drop: re-evaluate the deck's live
        issue marks (probing the dropped files' silences on the way) and toast
        the problems of the rows that just landed. Offending rows stay RED
        until the issue is resolved (refresh_issue_marks re-runs on every grid
        edit)."""
        issues = self.refresh_issue_marks(probe_rows=set(rows))
        msgs: list[str] = []
        for r in rows:
            for msg in issues.get(r, ()):
                if msg not in msgs:   # the 🧩 spread message spans several rows
                    msgs.append(msg)
        if len(msgs) > 6:
            msgs = msgs[:6] + [i18n.t("… plus %d more") % (len(msgs) - 6)]
        if msgs:
            _show_toast(self, "⚠  " + "\n".join(msgs), msec=4200)

    def _entry_for(self, path: Path) -> MusicEntry | None:
        """The entry for a dropped file: the library's own if it knows the path,
        otherwise one built from the file (VLC, Explorer, a foreign .m3u).
        None when the library isn't ready or the file can't be read as audio."""
        lib = self._suggester.lib if self._suggester else None
        if lib is None:
            return None
        return lib.entry_for(path, self._cache)

    def _replace_row_with_path(self, row: int, path: Path) -> bool:
        """Replace the song in `row` with a dropped track. Returns True if the slot was
        actually replaced (so a wishlist source can then MOVE the track out).

        The track may come from the Similar-Tracks window (already in the library)
        or be dragged in from outside it (VLC / Windows Explorer) — in which case a
        fresh entry is built from the file's tags/filename."""
        try:
            meta = self._row_meta[row]
            if not meta or (meta.theme and not meta.warmup):
                return False   # header / theme row — but a warm-up / heat slot IS fillable
            new_entry = self._entry_for(path)
            if new_entry is None:
                QMessageBox.information(
                    self, "Replace",
                    i18n.t("Couldn't read “%s” as an audio track.") % Path(path).name
                )
                return False

            # Genre/dance guard: if the dropped track's detected dance doesn't match
            # this slot's dance, confirm before replacing (a slot keeps its dance —
            # this just catches accidental drops of the wrong dance). Skipped when the
            # dropped file's dance can't be determined.
            slot_dance = meta.dance
            drop_dance = getattr(new_entry, "dance", None)
            if drop_dance and slot_dance and drop_dance != slot_dance:
                a = dance_name(drop_dance, drop_dance)
                b = dance_name(slot_dance, slot_dance)
                ans = QMessageBox.question(
                    self, "Different dance",
                    i18n.t("“%s” looks like a %s track, but this slot is %s.\n\nReplace anyway?")
                    % (new_entry.title, a, b),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return False

            # Don't allow a song that's already planned elsewhere in this list — the
            # same audio counts, whichever drive or folder the copy lies in.
            if meta.dance not in ALLOW_REPEAT and self._holds_same_audio(
                    new_entry, [m.entry for r, m in self._row_meta.numbered() if r != row]):
                QMessageBox.information(
                    self, "Already planned",
                    i18n.t("“%s” is already used in this playlist.") % new_entry.title
                )
                return False

            # Recompute the timbral similarity to the round anchor so ≈ / hover-% match.
            # When dropping onto the anchor (first) song, anchor on the next song instead
            # so the score reflects the rest of the round, not the song being replaced.
            if self._use_timbre and self._suggester:
                new_entry.sim_score = self._suggester.anchor_similarity(
                    new_entry, meta.round_name,
                    anchor=self._effective_anchor(meta.round_name, {row}))
            else:
                new_entry.sim_score = None

            if row == self._current_play_row:
                self._current_play_row = -1
                if self._play_cb:
                    self._play_cb(None)

            meta.entry = new_entry
            if self._playlist is not None and meta.round_name is not None:
                self._playlist[meta.round_name][meta.h_idx][meta.d_idx] = new_entry

            bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD
            QTimer.singleShot(0, lambda: (self._fill_song_row(row, meta, bg),
                                          self._notify_changed()))
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Replace Error", str(exc))
            return False

    # ── Dance-header drag: reorder whole dance sections ─────────────────────────

    def _dance_at_row(self, row: int) -> str | None:
        """Dance code a drag at `row` targets: the dance header itself or any
        song/backup row of a dance section. None on round headers / empty space."""
        if row in self._dance_hdr_rows:
            return self._dance_hdr_dance.get(row)
        if 0 <= row < len(self._row_meta):
            m = self._row_meta[row]
            if m and not m.theme:
                return m.dance
        return None

    def _reorder_dance(self, src: str, dst: str):
        """Move dance `src` to dance `dst`'s position — EVERY heat in EVERY round
        is permuted (the dance order is one per deck). Dragging down lands after
        the target, dragging up before it, like an ordinary list reorder."""
        old = list(self._dynamic_dances) if self._dynamic else list(self._loaded_dances)
        if src not in old or dst not in old or src == dst or not self._playlist:
            return
        new = [d for d in old if d != src]
        pos = new.index(dst) + (1 if old.index(src) < old.index(dst) else 0)
        new.insert(pos, src)
        perm = [old.index(d) for d in new]
        for heats in self._playlist.values():
            for i, h in enumerate(heats):
                heats[i] = [(h[p] if p < len(h) else None) for p in perm]
        if self._dynamic_backups:
            npos = {i: new.index(d) for i, d in enumerate(old)}
            self._dynamic_backups = {
                (rn, hi, npos.get(di, di)): entries
                for (rn, hi, di), entries in self._dynamic_backups.items()
            }
        log.info("🔀 Dance reordered\n"
                 "dance: %s\n"
                 "order: %s", src, " ".join(new))
        if self._dynamic:
            self._dynamic_dances = new
            self._rebuild_dynamic()
            return
        scroll = self.verticalScrollBar().value()
        rounds = list(self._loaded_rounds)
        pools = ([self._round_pools_by_name.get(rc.name, []) for rc in rounds]
                 if self._round_pools_by_name else None)
        self.load(self._playlist, new, rounds, self._dance_class,
                  play_cb=self._play_cb, suggester=self._suggester,
                  use_timbre=self._use_timbre, style=self._style,
                  round_pools=pools,
                  round_skip_dances=self._round_skip_dances or None,
                  round_ctx=self._round_ctx or None)
        self._restore_scroll(scroll)

    # ── Internal drag: move/swap a track between slots (e.g. across rounds) ─────

    def _move_or_swap_rows(self, src: int, dst: int):
        """Move the track in row `src` into slot `dst` (e.g. from one round to
        another). Same-dance only. If `dst` already holds a song the two are
        swapped so every heat slot stays filled; if `dst` is empty, `src` becomes
        empty. Playback follows the moved song so it isn't interrupted."""
        try:
            if src == dst:
                return
            sm = self._row_meta[src] if 0 <= src < len(self._row_meta) else None
            dm = self._row_meta[dst] if 0 <= dst < len(self._row_meta) else None
            if not sm or not dm or sm.theme or dm.theme:
                return
            src_entry = sm.entry
            if src_entry is None:
                return
            dst_entry = dm.entry

            # A dance slot may only hold a track of that dance.
            if sm.dance != dm.dance:
                a = dance_name(sm.dance, sm.dance)
                b = dance_name(dm.dance, dm.dance)
                QMessageBox.information(
                    self, "Move track",
                    i18n.t("A %s track can only move into another %s slot — not a %s slot.") % (a, a, b)
                )
                return

            # Swap (or move into an empty slot) in the row meta + live playlist grid.
            # A playing song takes its id along, so its marker follows it and the
            # audio keeps playing uninterrupted (no restart).
            self._row_meta.swap(src, dst)
            if self._playlist is not None:
                if sm.round_name is not None:
                    self._playlist[sm.round_name][sm.h_idx][sm.d_idx] = dst_entry
                if dm.round_name is not None:
                    self._playlist[dm.round_name][dm.h_idx][dm.d_idx] = src_entry

            # Recompute each moved song's timbral similarity vs its NEW round's anchor
            # so the ≈ flag / hover-% reflect the round it now lives in.
            if self._use_timbre and self._suggester:
                src_entry.sim_score = self._suggester.anchor_similarity(
                    src_entry, dm.round_name,
                    anchor=self._effective_anchor(dm.round_name, {dst}))
                if dst_entry is not None:
                    dst_entry.sim_score = self._suggester.anchor_similarity(
                        dst_entry, sm.round_name,
                        anchor=self._effective_anchor(sm.round_name, {src}))

            bg_s = _C_ROW_EVEN if sm.h_idx % 2 == 0 else _C_ROW_ODD
            bg_d = _C_ROW_EVEN if dm.h_idx % 2 == 0 else _C_ROW_ODD

            def _after():
                self._fill_song_row(src, sm, bg_s)
                self._fill_song_row(dst, dm, bg_d)
                # A fresh fill says ▶: the ■ goes back on the playing song's row.
                if self._current_play_row in (src, dst):
                    self.sync_play_glyph()
                self.setCurrentCell(dst, _COL_TITLE)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _after)
        except Exception as exc:
            QMessageBox.critical(self, "Move Error", str(exc))

    def _slot_row(self, round_name, dance, d_idx, h_idx) -> int | None:
        """Row index of a real (non-backup) song slot identified by its grid
        coordinates, or None if that heat/dance doesn't exist in the round."""
        for r, m in enumerate(self._row_meta):
            if (m and not m.theme and not m.backup
                    and m.round_name == round_name and m.dance == dance
                    and m.d_idx == d_idx and m.h_idx == h_idx):
                return r
        return None

    def _move_rows_block(self, src_rows, dst: int):
        """Move/swap SEVERAL selected song rows at once from one round into another.
        The first selected row is the anchor: it lands on the drop slot `dst`, the
        rest keep their heat offset relative to it (so a whole block of heats shifts
        together). Each track swaps with whatever sits in its destination slot —
        same-dance only, like the single-row move."""
        try:
            heats = self._row_meta.heat_rows()
            srcs = sorted(r for r in src_rows if r in heats)
            if not srcs:
                return
            anchor = srcs[0]
            am = self._row_meta[anchor]
            dm0 = self._row_meta[dst] if 0 <= dst < len(self._row_meta) else None
            if not dm0 or dm0.dance != am.dance:
                # Anchor and drop slot disagree on dance → defer to the single-row
                # path, which shows the "can only move into the same dance" notice.
                self._move_or_swap_rows(anchor, dst)
                return
            base_h    = am.h_idx
            dst_round = dm0.round_name
            dst_h     = dm0.h_idx
            src_set   = set(srcs)
            # Resolve every (src, dst) pair against the CURRENT grid before mutating.
            # Skip targets that are themselves dragged rows or already taken so the
            # whole batch stays a set of disjoint swaps (no track is lost/duplicated).
            plan = []
            taken = set()
            for s in srcs:
                sm = self._row_meta[s]
                tgt = self._slot_row(dst_round, sm.dance, sm.d_idx,
                                     dst_h + (sm.h_idx - base_h))
                if tgt is None or tgt == s or tgt in src_set or tgt in taken:
                    continue
                taken.add(tgt)
                plan.append((s, tgt, sm.entry, self._row_meta[tgt].entry))
            if not plan:
                return

            # A playing song takes its id along, so its marker follows it; any
            # other keeps its row and its ■ marker.
            affected = []
            for s, t, se, te in plan:
                sm, dm = self._row_meta[s], self._row_meta[t]
                self._row_meta.swap(s, t)
                if self._playlist is not None:
                    if sm.round_name is not None:
                        self._playlist[sm.round_name][sm.h_idx][sm.d_idx] = te
                    if dm.round_name is not None:
                        self._playlist[dm.round_name][dm.h_idx][dm.d_idx] = se
                if self._use_timbre and self._suggester:
                    if se is not None:
                        se.sim_score = self._suggester.anchor_similarity(
                            se, dm.round_name,
                            anchor=self._effective_anchor(dm.round_name, {t}))
                    if te is not None:
                        te.sim_score = self._suggester.anchor_similarity(
                            te, sm.round_name,
                            anchor=self._effective_anchor(sm.round_name, {s}))
                affected += [s, t]

            anchor_dst = plan[0][1]

            def _after():
                for r in affected:
                    m = self._row_meta[r]
                    bg = _C_ROW_EVEN if m.h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, m, bg)
                # A fresh fill says ▶: the ■ goes back on the playing song's row.
                if self._current_play_row in affected:
                    self.sync_play_glyph()
                self.setCurrentCell(anchor_dst, _COL_TITLE)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _after)
        except Exception as exc:
            QMessageBox.critical(self, "Move Error", str(exc))

