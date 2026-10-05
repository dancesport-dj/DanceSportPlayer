"""PlaylistTable context menu + keyboard shortcuts.

Mixin of PlaylistTable — extracted 1:1 from gui/playlist_table.py in the
big-module split; behaviour unchanged."""
import logging
import time
from dataclasses import replace

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
    QMenu,
    QMessageBox,
)
from pathlib import Path
from planner.models import DANCE_NAMES, MusicEntry
from planner.terms import dance_name, genre_name
from planner.parsing import _song_title_key
from planner import i18n
from planner.warmup import _WARMUP_ORDER, warmup_code
from gui.common import (
    BusyDialog,
    _C_ROW_EVEN,
    _C_ROW_ODD,
    _unreadable_playlist,
    reveal_in_explorer,
)
from shared.columns import (
    _COL_ARTIST,
    _COL_BPM,
    _COL_CLASS,
    _COL_CUSTOM,
    _COL_DANCE,
    _COL_LEN,
    _COL_POP,
    _COL_RATING,
    _COL_TITLE,
)
from shared.widgets import (
    _show_toast,
)
from planner.playlist_text import PlaylistEncodingError, read_playlist_text
from gui.playlist_entries import playlist_paths
from gui.dialogs import (  # auto-resolved
    SimilarTracksDialog,
)

log = logging.getLogger("dancesport.gui.playlist_table")

# `PlaylistTable` is late-bound into this module by gui.playlist_table after
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


def _source_stem(label: str) -> str:
    """The playlist stem of a past-competition source label ("parentdir / stem"),
    which carries the class and category the history is scored by."""
    return label.split(" / ", 1)[-1]


def _clean_deck_label(n_other: int) -> str:
    """The 🧹 action's wording for however many OTHER playlists are in view:
    one of them is "the other playlist", more are counted."""
    return ("🧹  Remove titles the other playlist has" if n_other == 1
            else f"🧹  Remove titles the other {n_other} playlists have")


class TableActionsMixin:
    """User-action concern: the right-click context menu (find similar,
    replace, mark, …) and every keyboard shortcut of the grid."""

    # ── Context menu: find similar tracks ──────────────────────────────────────

    def contextMenuEvent(self, event):
        row = self.rowAt(event.pos().y())
        entry = None
        if 0 <= row < len(self._row_meta) and self._row_meta[row]:
            entry = self._row_meta[row].entry

        # A deck slot (filled OR empty) carries its dance + round in the meta — used by
        # "Find planned before" to look up what history used at this dance + tier.
        pb_dance = pb_round = None
        if not self._flat_mode and 0 <= row < len(self._row_meta) and self._row_meta[row]:
            m = self._row_meta[row]
            if m.round_name and m.dance:
                pb_dance, pb_round = m.dance, m.round_name

        menu = QMenu(self)
        act = act_wl = act_fresh = copy_act = reveal_act = remove_act = speed_act = None
        retag_act = edit_act = None
        edit_rows: set = set()
        mark_act = reset_marks_act = None
        swap_act = None

        # ── Playback, right where the mouse already is: end the music, or let
        # the current title go and start the next one. ─────────────────────────
        stop_act = skip_act = None
        host = self.host
        if host.can_stop_and_skip():
            running = host.music_running()
            stop_act = menu.addAction("⏹  Stop the music")
            skip_act = menu.addAction("⏭  Skip to the next title")
            stop_act.setEnabled(running)
            skip_act.setEnabled(running)

        # Both lookups are planning work — searching the library for a better
        # track, or for what an earlier tournament used in this slot. A
        # player-only install runs a finished playlist and has no use for
        # either, so they stay off its menu entirely.
        planning = not host.player_only()

        # "Find planned before": history picks for this slot's dance + round tier. Works
        # on an empty slot too (no entry needed). Added right below "Find similar".
        def _mk_planned():
            a = menu.addAction("📜  Find planned before")
            if not (self._suggester is not None and self._suggester.lib is not None):
                a.setEnabled(False)
                a.setText("📜  Find planned before (load library first)")
            return a
        planned_act = None

        if entry:
            if not menu.isEmpty():
                menu.addSeparator()
            if planning:
                act = menu.addAction("🔎  Find similar tracks")
                act_wl = menu.addAction("⭐  Find similar (in my wishlist only)")
                # Same search, but only over music the floor has not heard from
                # you — the quickest way to swap a worn title for a fresh one.
                act_fresh = menu.addAction("🌱  Find similar (never played)")
                wl_empty = not host.wishlist_paths()
                if entry.features is None:
                    act.setEnabled(False)
                    act.setText("🔎  Find similar (run Audio Analysis first)")
                    act_wl.setEnabled(False)
                    act_wl.setText(
                        "⭐  Find similar in wishlist (run Audio Analysis first)")
                    act_fresh.setEnabled(False)
                    act_fresh.setText(
                        "🌱  Find similar, never played (run Audio Analysis first)")
                elif wl_empty:
                    act_wl.setEnabled(False)
                    act_wl.setText("⭐  Find similar in wishlist (wishlist is empty)")
                if pb_round and pb_dance:
                    planned_act = _mk_planned()
            copy_act = menu.addAction("📋  Copy file path")
            reveal_act = menu.addAction("📂  Show in Explorer")
            if not entry.path:
                copy_act.setEnabled(False)
                copy_act.setText("📋  Copy file path (unavailable)")
                reveal_act.setEnabled(False)
                reveal_act.setText("📂  Show in Explorer (unavailable)")
            speed_act = menu.addAction("🎵  Check music speed")
            retag_act = menu.addAction("🏷  Re-read MP3 tags")
            if not entry.path:
                speed_act.setEnabled(False)
                speed_act.setText("🎵  Check music speed (unavailable)")
                retag_act.setEnabled(False)
                retag_act.setText("🏷  Re-read MP3 tags (unavailable)")
            # Stars, classes, markers — for the selection when the click is
            # inside it, like "Remove this title".
            edit_rows = self._title_rows_for(row)
            edit_act = menu.addAction(
                i18n.t("🏷  Edit tags of %d tracks…") % len(edit_rows)
                if len(edit_rows) > 1 else i18n.t("🏷  Edit tags…"))
            edit_act.setEnabled(bool(entry.path))
            # Mark / unmark "for potential replace", with Reset-all directly
            # below it.
            if self._marks_allowed():
                menu.addSeparator()
                is_marked = bool(entry.path and str(entry.path) in self._marked_paths)
                mark_act = menu.addAction("🔁  Unmark (potential replace)\tCtrl+M"
                                          if is_marked
                                          else "🔁  Mark for potential replace\tCtrl+M")
                if self._marked_paths:
                    reset_marks_act = menu.addAction("🔁  Reset all replacement marks")
            if self._flat_mode:
                menu.addSeparator()
                remove_act = menu.addAction("🗑  Remove from wishlist")
            # Eintanzen list: two selected titles of one dance change places.
            if self._two_songs_selected():
                menu.addSeparator()
                swap_act = menu.addAction("⇅  Swap these two titles\tAlt+S")

        # Empty slot (no entry, so no "Find similar" above): still offer it, on top.
        if planning and planned_act is None and pb_round and pb_dance:
            planned_act = _mk_planned()

        # ── Dynamic-mode structure editing ─────────────────────────────────────
        # Two coherent groups so the menu reads logically: first GROW (➕ Add),
        # then SHRINK (🗑 Remove), each ordered smallest→largest scope
        # (heat→round for adds; title→heat for removes).
        remove_title_act = heat_act = backup_act = remove_round_act = None
        empty_slot_act = None
        add_heat_act = new_round_act = remove_dance_act = None
        remove_dance_all_act = None
        dance_here = round_here = None
        title_rows: set = set()
        if self._dynamic:
            rmeta = (self._row_meta[row]
                     if 0 <= row < len(self._row_meta) else None)
            # Round-level actions work from a round/dance HEADER row too (resolved via
            # _round_of_row); heat-level ones (remove THIS heat) need an actual slot row.
            round_name    = self._round_of_row(row)
            on_round      = bool(round_name and round_name in (self._playlist or {}))
            on_heat_row   = bool(rmeta and rmeta.round_name
                                 and not rmeta.backup)
            is_backup_row = bool(rmeta and rmeta.backup)
            # The single dance under the cursor — from a slot row's meta or a dance
            # header — so just that dance can be pulled out of this one round.
            if rmeta and rmeta.dance and rmeta.round_name:
                dance_here, round_here = rmeta.dance, rmeta.round_name
            elif row in self._dance_hdr_dance:
                dance_here = self._dance_hdr_dance[row]
                round_here = self._row_round_name.get(row)
            can_remove_dance = bool(dance_here and round_here
                                    and round_here in (self._playlist or {}))

            # GROW: add a heat to this round, then a whole new round. "Create new
            # round" stays available even on empty space.
            if not menu.isEmpty():
                menu.addSeparator()
            if on_round:
                add_heat_act = menu.addAction("➕  Add a heat to this round")
            new_round_act = menu.addAction(
                i18n.t("➕  Insert new round after %s") % round_name if on_round
                else "➕  Create new round")

            # SHRINK: remove just the track(s) keeping the slot, then the whole
            # heat / a single stacked backup.
            want_title = bool(entry and not self._flat_mode)
            if want_title:
                title_rows = self._title_rows_for(row)
            if want_title or on_round:
                menu.addSeparator()
                if want_title:
                    remove_title_act = menu.addAction(
                        self._remove_titles_caption(len(title_rows)))
                if is_backup_row:
                    backup_act = menu.addAction("🗑  Remove this backup\tCtrl+Del")
                elif on_heat_row:
                    heat_act = menu.addAction("🗑  Remove this heat (all dances)\tCtrl+Del")
                    # An EMPTY slot (no song): offer a surgical clear that lifts a stacked
                    # backup up into it, or drops a lone dead slot — every other option
                    # here would also wipe the heat or the backup beneath it.
                    if rmeta.entry is None and rmeta.dance:
                        _key = (rmeta.round_name, rmeta.h_idx, rmeta.d_idx)
                        _di = (self._dynamic_dances.index(rmeta.dance)
                               if rmeta.dance in self._dynamic_dances else -1)
                        _filled = _di >= 0 and any(
                            _di < len(h) and h[_di] is not None
                            for h in (self._playlist or {}).get(rmeta.round_name, []))
                        if self._dynamic_backups.get(_key):
                            empty_slot_act = menu.addAction(
                                "⬆  Move backup up into this empty slot")
                        elif not _filled:
                            empty_slot_act = menu.addAction("🗑  Remove this empty slot")
                if can_remove_dance:
                    dn = dance_name(dance_here, dance_here)
                    remove_dance_act = menu.addAction(
                        i18n.t("🗑  Remove %s from this round "
                               "(keep other dances)") % dn)
                    remove_dance_all_act = menu.addAction(
                        i18n.t("🗑  Remove %s from all rounds and heats") % dn)
                if on_round:
                    remove_round_act = menu.addAction("🗑  Remove this round (all heats)")

        # The same "take this title out" a dynamic deck has, for the other two
        # kinds of deck. Del does it too, but Del is not discoverable and on a
        # Mac laptop there is only ⌫ — so the menu has to carry it as well.
        elif entry is not None and not self._flat_mode:
            menu.addSeparator()
            title_rows = self._title_rows_for(row)
            remove_title_act = menu.addAction(
                self._remove_titles_caption(len(title_rows)))

        # Static ⇄ dynamic mode toggle (decks only, not the flat wishlist — and
        # not in a player-only install, where a deck always adds a dropped title).
        mode_act = None
        if not self._flat_mode and not self.player_only():
            if not menu.isEmpty():
                menu.addSeparator()
            mode_act = menu.addAction(
                "🔒  Back to a planned grid" if self._player_list else
                "🔒  Switch to static mode" if self._dynamic else
                "🔓  Switch to dynamic mode")

        # Save the whole list as an .m3u — always available (even on a header row).
        save_act = tree_act = None
        if self._row_meta.has_songs():
            if not menu.isEmpty():
                menu.addSeparator()
            save_act = menu.addAction("💾  Save as M3U…")
            if host.has_tournaments():
                tree_act = menu.addAction("🏆  Save and add to Tournaments…")

        # Import an .m3u INTO this table (deck: full rounds/heats detection;
        # wishlist: tracks are appended flat).
        if save_act is None and not menu.isEmpty():
            menu.addSeparator()
        import_act = menu.addAction("📂  Import M3U…")

        # Wishlist: drop every track that's already sitting in an open playlist deck.
        clean_pl_act = None
        if self._flat_mode and self.rowCount() > 0:
            if not menu.isEmpty():
                menu.addSeparator()
            clean_pl_act = menu.addAction("🧹  Remove tracks already in a playlist")

        # Deck: the same thing the other way round — drop what the OTHER open
        # playlists already plan, so a title runs once in the evening. The
        # playlists it is measured against are the ones in view: two decks on
        # screen means the other one, eight means the other seven.
        clean_deck_act = None
        if (not self._flat_mode and self._row_meta.has_songs()
                and host.can_clean_decks()):
            n_other = sum(1 for t in host.visible_deck_tables()
                          if t is not self and t._row_meta.has_songs())
            if n_other:
                if not menu.isEmpty():
                    menu.addSeparator()
                clean_deck_act = menu.addAction(_clean_deck_label(n_other))

        # Any list: the same audio twice in THIS list (a C: and an F: copy, say).
        dedupe_act = None
        if self._row_meta.has_songs():
            if clean_pl_act is None and clean_deck_act is None and not menu.isEmpty():
                menu.addSeparator()
            dedupe_act = menu.addAction("♊  Remove duplicate titles in this list")

        # Find a title in THIS list and jump to it (re-run to step to the next match).
        search_act = None
        if self._row_meta.has_songs():
            if not menu.isEmpty():
                menu.addSeparator()
            search_act = menu.addAction("🔍  Find a title in this list…\tCtrl+F")

        # Empty the whole list (blank it again) — clearer than Del-on-header / Ctrl+A.
        clear_act = None
        if self.rowCount() > 0:
            if not menu.isEmpty():
                menu.addSeparator()
            clear_act = menu.addAction("🧹  Empty this wishlist" if self._flat_mode
                                       else "🧹  Empty this playlist")
        if menu.isEmpty():
            return

        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if stop_act is not None and chosen is stop_act:
            host.stop_music()
        elif skip_act is not None and chosen is skip_act:
            host.skip_to_next()
        elif save_act is not None and chosen is save_act:
            self.saveRequested.emit(self)
        elif tree_act is not None and chosen is tree_act:
            self.saveToTournamentsRequested.emit(self)
        elif chosen is import_act:
            host.import_m3u_into()
        elif clean_pl_act is not None and chosen is clean_pl_act:
            host.clean_wishlist_against_playlists()
        elif clean_deck_act is not None and chosen is clean_deck_act:
            host.clean_deck_against_others()
        elif dedupe_act is not None and chosen is dedupe_act:
            self._remove_duplicate_titles()
        elif swap_act is not None and chosen is swap_act:
            self._swap_selected()
        elif mark_act is not None and chosen is mark_act:
            sel = {ix.row() for ix in self.selectedIndexes()}
            self._toggle_mark(sel or {row})
        elif reset_marks_act is not None and chosen is reset_marks_act:
            self._reset_all_marks()
        elif search_act is not None and chosen is search_act:
            self._search_title()
        elif clear_act is not None and chosen is clear_act:
            self._clear_entire()
        elif remove_title_act is not None and chosen is remove_title_act:
            if self._confirm_delete("Remove song",
                                    self._remove_songs_prompt(len(title_rows))):
                self._clear_slots_at(title_rows)
        elif heat_act is not None and chosen is heat_act:
            self._remove_dynamic_heat(row)
        elif remove_round_act is not None and chosen is remove_round_act:
            self._remove_dynamic_round(row)
        elif add_heat_act is not None and chosen is add_heat_act:
            self._add_dynamic_heat(row)
        elif backup_act is not None and chosen is backup_act:
            self._remove_dynamic_backup(row)
        elif empty_slot_act is not None and chosen is empty_slot_act:
            self._remove_empty_dynamic_slot(row)
        elif new_round_act is not None and chosen is new_round_act:
            self._insert_dynamic_round(row)
        elif remove_dance_act is not None and chosen is remove_dance_act:
            self._remove_dance_from_round(round_here, dance_here)
        elif remove_dance_all_act is not None and chosen is remove_dance_all_act:
            self._remove_dance_everywhere(dance_here)
        elif mode_act is not None and chosen is mode_act:
            host.set_deck_mode("static" if (self._dynamic or self._player_list)
                               else "dynamic")
        elif remove_act is not None and chosen is remove_act:
            if row == self._current_play_row and self._play_cb:
                self._play_cb(None)
                self._current_play_row = -1
            self.removeRow(row)
            del self._row_meta[row]
            self._notify_changed()
        elif copy_act is not None and chosen is copy_act and entry.path:
            QApplication.clipboard().setText(str(entry.path))
            _show_toast(self, "📋  Path copied to clipboard")
        elif reveal_act is not None and chosen is reveal_act and entry.path:
            reveal_in_explorer(entry.path, self)
        elif speed_act is not None and chosen is speed_act and entry.path:
            host.check_track_speed(entry)
        elif retag_act is not None and chosen is retag_act and entry.path:
            host.rescan_entry_tags(entry)
        elif edit_act is not None and chosen is edit_act:
            host.edit_entry_tags([self._row_meta[r].entry for r in sorted(edit_rows)])
        elif planned_act is not None and chosen is planned_act:
            self._show_planned_before(pb_dance, pb_round)
        elif act is not None and chosen is act and entry.features is not None:
            self._show_similar(entry, slot=(pb_dance, pb_round))
        elif act_wl is not None and chosen is act_wl and entry.features is not None:
            self._show_similar(entry, wishlist_only=True, slot=(pb_dance, pb_round))
        elif act_fresh is not None and chosen is act_fresh and entry.features is not None:
            self._show_similar(entry, fresh_only=True, slot=(pb_dance, pb_round))

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

    def _show_similar(self, entry: MusicEntry, wishlist_only: bool = False,
                      fresh_only: bool = False, slot=(None, None)):
        """`slot` is the clicked row's (dance, round): with both set, the window
        offers 📜 narrowing to what past competitions played in that round."""
        lib = self._suggester.lib if self._suggester else None
        if lib is None:
            return
        results = lib.similar_tracks(entry, n=100, same_dance=True, min_display=0.5)
        if not results:
            QMessageBox.information(
                self, "Similar Tracks",
                "No similar tracks found (audio features may be missing)."
            )
            return
        # Non-modal (show, not exec) so its rows can be dragged onto a playlist row
        # to replace the song there. Keep a reference so it isn't garbage-collected.
        wl_paths = self.host.wishlist_paths()
        dance, round_name = slot
        history_cb = ((lambda: self._round_history_keys(dance, round_name))
                      if dance and round_name else None)
        dlg = SimilarTracksDialog(entry, results, self, play_cb=self._play_cb,
                                  lib=lib, cache=self._cache, seek_cb=self._seek_cb,
                                  wishlist_paths=wl_paths, wishlist_only=wishlist_only,
                                  fresh_only=fresh_only, round_history_cb=history_cb,
                                  round_name=round_name)
        dlg.setModal(False)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Drop references to dialogs whose underlying C++ object was already deleted
        # (WA_DeleteOnClose) — touching .isVisible() on those raises RuntimeError.
        def _alive(d) -> bool:
            try:
                return d is not None and d.isVisible()
            except RuntimeError:
                return False
        self._similar_dlgs = [d for d in getattr(self, "_similar_dlgs", []) if _alive(d)]
        self._similar_dlgs.append(dlg)
        dlg.show()
        dlg.raise_()

    def _round_history(self, dance: str, round_name: str):
        """What past competitions played for `dance` in this deck's `round_name`
        tier (final↔final, round 2↔round 2, any heat), from lists of a class and
        age category compatible with this deck.

        Returns (matched, labels_of, deck_class, deck_types): the library entries,
        each one's source-list labels by id(entry), and this deck's identity the
        callers rank by. None when the deck has no such round or no library."""
        from planner.competition import (comp_type_tokens, comp_categories,
                                         class_compatible, category_compatible)
        lib = self._suggester.lib if self._suggester else None
        if lib is None or not self._playlist:
            return None
        rounds_in_order = list(self._playlist.keys())
        if round_name not in rounds_in_order:
            return None
        round_idx      = rounds_in_order.index(round_name)
        schedule_heats = [len(self._playlist[r]) for r in rounds_in_order]
        num_dances     = len(self.current_dances()) or 1
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            _all, round_pools, _n, round_sources = lib.past_competition_round_pools(
                None, schedule_heats, num_dances)
        finally:
            QApplication.restoreOverrideCursor()
        pool    = round_pools[round_idx]   if 0 <= round_idx < len(round_pools)   else []
        sources = round_sources[round_idx] if 0 <= round_idx < len(round_sources) else {}

        # This deck's competition identity: start class (WDSF ⇒ S) + distinctive type
        # tokens (WDSF / category / level), parsed from its name and configured class.
        deck_name  = self.host.deck_name()
        deck_types = comp_type_tokens(deck_name)
        deck_class = "S" if "WDSF" in deck_types else (self._dance_class or None)
        deck_cats  = comp_categories(deck_name)

        # Keep only this-dance tracks whose source lists FOR THIS ROUND include a
        # competition of a compatible class AND age category, with just that subset
        # of lists. Kept here, not on the entry: `e` is the library's shared object,
        # its replay_sources is the tooltip of the same song in every deck.
        matched = []
        labels_of: dict[int, list[str]] = {}
        for e in pool:
            if e.dance != dance:
                continue
            labels = [lab for lab in sources.get(id(e), [])
                      if class_compatible(_source_stem(lab), deck_class)
                      and category_compatible(_source_stem(lab), deck_cats)]
            if not labels:
                continue
            labels_of[id(e)] = labels
            matched.append(e)
        return matched, labels_of, deck_class, deck_types

    def _round_history_keys(self, dance: str, round_name: str):
        """(paths, title keys) of what past competitions played for `dance` in
        this round — the Similar window's 📜 filter. The title keys let another
        copy of the same song count too."""
        hist = self._round_history(dance, round_name)
        matched = hist[0] if hist else []
        paths = {str(e.path) for e in matched if e.path}
        keys = {_song_title_key(p) for p in paths} - {""}
        return paths, keys

    def _show_planned_before(self, dance: str, round_name: str):
        """List tracks history used for `dance` at this round's tier (final↔final,
        semi↔semi…), drawn only from real tournament lists of a compatible class.

        A track is kept only if some past list placed it in THIS round (not merely
        somewhere in the file) AND that list's class fits this deck (same class, or
        both top S/A; WDSF and open count as S/A — others are hidden). `replay_sources`
        is narrowed to exactly that subset. Results are RANKED by how well the list's
        competition matches this deck: a concrete type match (WDSF=WDSF, SEN I=SEN I)
        first, then same start class. Reuses the Similar-Tracks window in 'history' mode."""
        from planner.competition import comp_class, slot_history_score
        hist = self._round_history(dance, round_name)
        if hist is None:
            return
        matched, labels_of, deck_class, deck_types = hist
        dn = dance_name(dance, dance)
        if not matched:
            QMessageBox.information(
                self, "Find planned before",
                i18n.t("No past competition plans found for %s in %s.") % (dn, round_name))
            return

        def _stems_of(e):
            return [_source_stem(s) for s in labels_of[id(e)]]

        def _score(e):
            return max((slot_history_score(s, deck_class, deck_types)
                        for s in _stems_of(e)), default=0)

        def _best_class(e):
            # Class letter of the highest-scoring source list (for the 'Class' column).
            best, cls = -1, ""
            for s in _stems_of(e):
                sc = slot_history_score(s, deck_class, deck_types)
                if sc > best:
                    # Unclassed lists are assumed A/S level (see slot_history_score).
                    best, cls = sc, (comp_class(s) or "A/S")
            return cls

        # Concrete matches on top; ties broken by overall play popularity, then title.
        matched.sort(key=lambda e: (_score(e), e.popularity or 0,
                                    (e.title or "").lower()), reverse=True)
        # The window's tooltips show the narrowed lists on a copy of each entry.
        results = [(_best_class(e), replace(e, replay_sources=labels_of[id(e)]))
                   for e in matched]
        dlg = SimilarTracksDialog(
            None, results, self, play_cb=self._play_cb, seek_cb=self._seek_cb,
            history_title=f"📜  Planned before · {dn} · {round_name}")
        dlg.setModal(False)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        def _alive(d) -> bool:
            try:
                return d is not None and d.isVisible()
            except RuntimeError:
                return False
        self._similar_dlgs = [d for d in getattr(self, "_similar_dlgs", []) if _alive(d)]
        self._similar_dlgs.append(dlg)
        dlg.show()
        dlg.raise_()

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

    def _row_base_bg(self, row: int, meta: dict | None) -> QColor:
        """The row's normal (unmarked) background — heat-parity alternating colour."""
        parity = meta.h_idx if meta and meta.h_idx is not None else row
        return _C_ROW_EVEN if parity % 2 == 0 else _C_ROW_ODD

    def _refill_row(self, row: int, meta: dict):
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
        """Space: play/stop the selected song.  Ctrl+←/→: seek ∓30 s.
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
        if key == Qt.Key.Key_Space and mods == Qt.KeyboardModifier.NoModifier:
            row, path = self._selected_song_row()
            if row >= 0:
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
        for pos, (r, e) in enumerate(zip(song_rows, final_entries)):
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
                [tp for tp, _ in todo])):
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

    def _reload_warmup(self, entries: list[MusicEntry] | None = None):
        """Re-render the warm-up / ETDS party list (default: from its current
        tracks) — the ─── headers are derived during the load, so any change of
        order or of the grouping view has to go through here.

        Keeps the current scroll offset, like `_rebuild_dynamic`: the rebuild
        throws every row away and the bar would fall back to the top, leaving the
        operator to scroll their place back after each edit.

        An edit that only adds or drops tracks doesn't get that far — see
        `_warmup_edit_in_place`, which moves the rows under it instead of
        building the list again."""
        if entries is None:
            entries = self._row_meta.entries()
        placed = self._row_meta.placements()
        scroll = self.verticalScrollBar().value()
        # The greyed-out played rows are remembered by (row, column), and the
        # edit moves rows: give every one of them its own colour back FIRST,
        # while those numbers still mean the rows they were taken from.
        self._ungrey_played_rows()
        if not self._warmup_edit_in_place(entries):
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
        _COL_TITLE: lambda e: (e.title or "").lower(),
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
        self.statusBar_message(
            f"↕ {what} sorted by {self.horizontalHeaderItem(col).text()} {arrow}")

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
        from gui.duplicate_titles_dialog import DuplicateTitlesDialog

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

