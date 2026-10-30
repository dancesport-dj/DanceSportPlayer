"""☰ A playlist table's right-click menu, and the windows it opens.

Split off gui/table/table_actions.py: the menu's title, structure
and list sections, and what they open — similar tracks, a round's history
and the titles planned for it before.
"""
from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from gui.common import reveal_in_explorer
from gui.dialogs import SimilarTracksDialog
from planner import i18n
from planner.models import MusicEntry
from planner.music.parsing import song_title_key
from planner.terms import dance_name
from shared.widgets import show_toast

if TYPE_CHECKING:
    from gui.window.hosts import PlaylistTableHost
else:
    PlaylistTableHost = object


def _source_stem(label: str) -> str:
    """The playlist stem of a past-competition source label ("parentdir / stem"),
    which carries the class and category the history is scored by."""
    return label.split(" / ", 1)[-1]


def clean_deck_label(n_other: int) -> str:
    """The 🧹 action's wording for however many OTHER playlists are in view:
    one of them is "the other playlist", more are counted."""
    return ("🧹  Remove titles the other playlist has" if n_other == 1
            else f"🧹  Remove titles the other {n_other} playlists have")


class TableMenuMixin(PlaylistTableHost):
    """The right-click menu of PlaylistTable (mixin)."""

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

        # Each section adds its actions and files what each one does in
        # `handlers`; the chosen one runs once the menu has closed.
        menu = QMenu(self)
        handlers: dict = {}
        self._menu_title(menu, handlers, row, entry, pb_dance, pb_round)
        self._menu_structure(menu, handlers, row, entry)
        self._menu_list(menu, handlers)
        if menu.isEmpty():
            return

        handler = handlers.get(menu.exec(event.globalPos()))
        if handler is not None:
            handler()

    def _menu_title(self, menu, handlers, row, entry, pb_dance, pb_round):
        """Context menu: what can be done with the title under the mouse."""
        host = self.host
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
            handlers[a] = lambda: self._show_planned_before(pb_dance, pb_round)
            return a
        planned_act = None

        if entry:
            if not menu.isEmpty():
                menu.addSeparator()
            if planning:
                self._add_similar_actions(menu, handlers, entry, pb_dance, pb_round)
                if pb_round and pb_dance:
                    planned_act = _mk_planned()
            self._add_file_actions(menu, handlers, entry)
            # Stars, classes, markers — for the selection when the click is
            # inside it, like "Remove this title".
            edit_rows = self._title_rows_for(row)
            edit_act = menu.addAction(
                i18n.t("🏷  Edit tags of %d tracks…") % len(edit_rows)
                if len(edit_rows) > 1 else i18n.t("🏷  Edit tags…"))
            edit_act.setEnabled(bool(entry.path))
            handlers[edit_act] = lambda: host.edit_entry_tags(
                [self._row_meta[r].entry for r in sorted(edit_rows)])
            # Mark / unmark "for potential replace", with Reset-all directly
            # below it.
            if self._marks_allowed():
                menu.addSeparator()
                is_marked = bool(entry.path and str(entry.path) in self._marked_paths)
                mark_act = menu.addAction("🔁  Unmark (potential replace)\tCtrl+M"
                                          if is_marked
                                          else "🔁  Mark for potential replace\tCtrl+M")
                handlers[mark_act] = lambda: self._toggle_mark(
                    {ix.row() for ix in self.selectedIndexes()} or {row})
                if self._marked_paths:
                    reset_marks_act = menu.addAction("🔁  Reset all replacement marks")
                    handlers[reset_marks_act] = self._reset_all_marks
            # 📌 Pin: a slot of a round keeps its title through ↻ / ↺.
            pin_meta = self._row_meta[row] if 0 <= row < len(self._row_meta) else None
            if pin_meta and pin_meta.round_name and not pin_meta.theme and entry.path:
                menu.addSeparator()
                pin_act = menu.addAction(
                    i18n.t("📌  Unpin") if str(entry.path) in self._pinned_paths
                    else i18n.t("📌  Pin — keep this title when the round is re-rolled"))
                handlers[pin_act] = lambda: self._toggle_pin(
                    {ix.row() for ix in self.selectedIndexes()} or {row})
            if self._flat_mode:
                menu.addSeparator()
                remove_act = menu.addAction("🗑  Remove from wishlist")
                # The same removal as the Delete key: played rows re-grey and
                # the play frame moves where the rows now sit. Opened inside a
                # selection, the whole selection goes, like a deck's 🗑.
                handlers[remove_act] = lambda: self._remove_rows(edit_rows)
            # Eintanzen list: two selected titles of one dance change places.
            if self._two_songs_selected():
                menu.addSeparator()
                swap_act = menu.addAction("⇅  Swap these two titles\tAlt+S")
                handlers[swap_act] = self._swap_selected

        # Empty slot (no entry, so no "Find similar" above): still offer it, on top.
        if planning and planned_act is None and pb_round and pb_dance:
            _mk_planned()

    def _menu_structure(self, menu, handlers, row, entry):
        """Context menu: grow or shrink the rounds, heats and slots of a deck."""
        def _remove_titles(title_rows):
            if self._confirm_delete("Remove song",
                                    self._remove_songs_prompt(len(title_rows))):
                self._clear_slots_at(title_rows)

        # ── Dynamic-mode structure editing ─────────────────────────────────────
        # Two coherent groups so the menu reads logically: first GROW (➕ Add),
        # then SHRINK (🗑 Remove), each ordered smallest→largest scope
        # (heat→round for adds; title→heat for removes).
        dance_here = round_here = None
        if self._dynamic:
            rmeta = (self._row_meta[row]
                     if 0 <= row < len(self._row_meta) else None)
            # Round-level actions work from a round/dance HEADER row too (resolved via
            # _round_of_row); heat-level ones (remove THIS heat) need an actual slot row.
            round_name = self._round_of_row(row)
            on_round = bool(round_name and round_name in (self._playlist or {}))
            on_heat_row = bool(rmeta and rmeta.round_name
                               and not rmeta.backup)
            is_backup_row = bool(rmeta and rmeta.backup)
            # The single dance under the cursor — from a slot row's meta or a dance
            # header — so just that dance can be pulled out of this one round.
            if rmeta and rmeta.dance and rmeta.round_name:
                dance_here, round_here = rmeta.dance, rmeta.round_name
            elif row in self._dance_hdr_dance:
                dance_here = self._dance_hdr_dance[row]
                round_here = self._row_round_name.get(row)

            # GROW: add a heat to this round, then a whole new round. "Create new
            # round" stays available even on empty space.
            if not menu.isEmpty():
                menu.addSeparator()
            if on_round:
                add_heat_act = menu.addAction("➕  Add a heat to this round")
                handlers[add_heat_act] = lambda: self._add_dynamic_heat(row)
            new_round_act = menu.addAction(
                i18n.t("➕  Insert new round after %s") % round_name if on_round
                else "➕  Create new round")
            handlers[new_round_act] = lambda: self._insert_dynamic_round(row)

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
                    handlers[remove_title_act] = lambda: _remove_titles(title_rows)
                if is_backup_row:
                    backup_act = menu.addAction("🗑  Remove this backup\tCtrl+Del")
                    handlers[backup_act] = lambda: self._remove_dynamic_backup(row)
                elif on_heat_row:
                    heat_act = menu.addAction("🗑  Remove this heat (all dances)\tCtrl+Del")
                    handlers[heat_act] = lambda: self._remove_dynamic_heat(row)
                    # An EMPTY slot (no song): offer a surgical clear that lifts a stacked
                    # backup up into it, or drops a lone dead slot — every other option
                    # here would also wipe the heat or the backup beneath it.
                    self._add_empty_slot_action(menu, handlers, row, rmeta)
                if dance_here and round_here and round_here in (self._playlist or {}):
                    dn = dance_name(dance_here, dance_here)
                    remove_dance_act = menu.addAction(
                        i18n.t("🗑  Remove %s from this round "
                               "(keep other dances)") % dn)
                    remove_dance_all_act = menu.addAction(
                        i18n.t("🗑  Remove %s from all rounds and heats") % dn)
                    handlers[remove_dance_act] = (
                        lambda: self._remove_dance_from_round(round_here, dance_here))
                    handlers[remove_dance_all_act] = (
                        lambda: self._remove_dance_everywhere(dance_here))
                if on_round:
                    remove_round_act = menu.addAction("🗑  Remove this round (all heats)")
                    handlers[remove_round_act] = lambda: self._remove_dynamic_round(row)

        # The same "take this title out" a dynamic deck has, for the other two
        # kinds of deck. Del does it too, but Del is not discoverable and on a
        # Mac laptop there is only ⌫ — so the menu has to carry it as well.
        elif entry is not None and not self._flat_mode:
            menu.addSeparator()
            title_rows = self._title_rows_for(row)
            remove_title_act = menu.addAction(
                self._remove_titles_caption(len(title_rows)))
            handlers[remove_title_act] = lambda: _remove_titles(title_rows)

    def _add_similar_actions(self, menu, handlers, entry, pb_dance, pb_round):
        """🔎 ⭐ 🌱 Find similar: anywhere, in the wishlist, never played."""
        host = self.host
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
        if entry.features is not None:
            slot = (pb_dance, pb_round)
            handlers[act] = lambda: self._show_similar(entry, slot=slot)
            handlers[act_wl] = lambda: self._show_similar(
                entry, wishlist_only=True, slot=slot)
            handlers[act_fresh] = lambda: self._show_similar(
                entry, fresh_only=True, slot=slot)

    def _add_file_actions(self, menu, handlers, entry):
        """📋 📂 🎵 🏷 Copy, show, check speed and re-read the file."""
        host = self.host
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
        if entry.path:
            def _copy_path():
                QApplication.clipboard().setText(str(entry.path))
                show_toast(self, "📋  Path copied to clipboard")
            handlers[copy_act] = _copy_path
            handlers[reveal_act] = lambda: reveal_in_explorer(entry.path, self)
            handlers[speed_act] = lambda: host.check_track_speed(entry)
            handlers[retag_act] = lambda: host.rescan_entry_tags(entry)

    def _add_empty_slot_action(self, menu, handlers, row, rmeta):
        """⬆ lift a backup into an empty slot, or 🗑 drop a lone dead one."""
        if rmeta is not None and rmeta.entry is None and rmeta.dance:
            _key = (rmeta.round_name, rmeta.h_idx, rmeta.d_idx)
            _di = (self._dynamic_dances.index(rmeta.dance)
                   if rmeta.dance in self._dynamic_dances else -1)
            _filled = _di >= 0 and any(
                _di < len(h) and h[_di] is not None
                for h in (self._playlist or {}).get(rmeta.round_name, []))
            empty_slot_act = None
            if self._dynamic_backups.get(_key):
                empty_slot_act = menu.addAction(
                    "⬆  Move backup up into this empty slot")
            elif not _filled:
                empty_slot_act = menu.addAction("🗑  Remove this empty slot")
            if empty_slot_act is not None:
                handlers[empty_slot_act] = (
                    lambda: self._remove_empty_dynamic_slot(row))

    def _menu_list(self, menu, handlers):
        """Context menu: actions on the whole list — mode, save, import, clean up."""
        host = self.host
        # Static ⇄ dynamic mode toggle (decks only, not the flat wishlist — and
        # not in a player-only install, where a deck always adds a dropped title).
        if not self._flat_mode and not self.player_only():
            if not menu.isEmpty():
                menu.addSeparator()
            mode_act = menu.addAction(
                "🔒  Back to a planned grid" if self._player_list else
                "🔒  Switch to static mode" if self._dynamic else
                "🔓  Switch to dynamic mode")
            handlers[mode_act] = lambda: host.set_deck_mode(
                "static" if (self._dynamic or self._player_list) else "dynamic")

        # Save the whole list as an .m3u — always available (even on a header row).
        save_act = None
        if self._row_meta.has_songs():
            if not menu.isEmpty():
                menu.addSeparator()
            save_act = menu.addAction("💾  Save as M3U…")
            handlers[save_act] = lambda: self.saveRequested.emit(self)
            if host.has_tournaments():
                tree_act = menu.addAction("🏆  Save and add to Tournaments…")
                handlers[tree_act] = lambda: self.saveToTournamentsRequested.emit(self)

        # Import an .m3u INTO this table (deck: full rounds/heats detection;
        # wishlist: tracks are appended flat).
        if save_act is None and not menu.isEmpty():
            menu.addSeparator()
        import_act = menu.addAction("📂  Import M3U…")
        handlers[import_act] = host.import_m3u_into

        # Wishlist: drop every track that's already sitting in an open playlist deck.
        clean_pl_act = None
        if self._flat_mode and self.rowCount() > 0:
            if not menu.isEmpty():
                menu.addSeparator()
            clean_pl_act = menu.addAction("🧹  Remove tracks already in a playlist")
            handlers[clean_pl_act] = host.clean_wishlist_against_playlists

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
                clean_deck_act = menu.addAction(clean_deck_label(n_other))
                handlers[clean_deck_act] = host.clean_deck_against_others

        # Any list: the same audio twice in THIS list (a C: and an F: copy, say).
        if self._row_meta.has_songs():
            if clean_pl_act is None and clean_deck_act is None and not menu.isEmpty():
                menu.addSeparator()
            dedupe_act = menu.addAction("♊  Remove duplicate titles in this list")
            handlers[dedupe_act] = self._remove_duplicate_titles

        # Find a title in THIS list and jump to it (re-run to step to the next match).
        if self._row_meta.has_songs():
            if not menu.isEmpty():
                menu.addSeparator()
            search_act = menu.addAction("🔍  Find a title or genre in this list…\tCtrl+F")
            handlers[search_act] = self._search_title

        # Empty the whole list (blank it again) — clearer than Del-on-header / Ctrl+A.
        if self.rowCount() > 0:
            if not menu.isEmpty():
                menu.addSeparator()
            clear_act = menu.addAction("🧹  Empty this wishlist" if self._flat_mode
                                       else "🧹  Empty this playlist")
            handlers[clear_act] = self._clear_entire

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
        dlg = SimilarTracksDialog(entry, results, self,
                                  play_cb=self.host.preview_cb() or self._play_cb,
                                  lib=lib, cache=self._cache,
                                  seek_cb=self.host.preview_seek_cb() or self._seek_cb,
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
        from planner.event.competition import category_compatible, class_compatible, comp_categories, comp_type_tokens
        lib = self._suggester.lib if self._suggester else None
        if lib is None or not self._playlist:
            return None
        rounds_in_order = list(self._playlist.keys())
        if round_name not in rounds_in_order:
            return None
        round_idx = rounds_in_order.index(round_name)
        schedule_heats = [len(self._playlist[r]) for r in rounds_in_order]
        num_dances = len(self.current_dances()) or 1
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            _all, round_pools, _n, round_sources = lib.past_competition_round_pools(
                None, schedule_heats, num_dances)
        finally:
            QApplication.restoreOverrideCursor()
        pool = round_pools[round_idx] if 0 <= round_idx < len(round_pools) else []
        sources = round_sources[round_idx] if 0 <= round_idx < len(round_sources) else {}

        # This deck's competition identity: start class (WDSF ⇒ S) + distinctive type
        # tokens (WDSF / category / level), parsed from its name and configured class.
        deck_name = self.host.deck_name()
        deck_types = comp_type_tokens(deck_name)
        deck_class = "S" if "WDSF" in deck_types else (self._dance_class or None)
        deck_cats = comp_categories(deck_name)

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
        keys = {song_title_key(p) for p in paths} - {""}
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
        from planner.event.competition import comp_class, slot_history_score
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
            None, results, self, play_cb=self.host.preview_cb() or self._play_cb,
            seek_cb=self.host.preview_seek_cb() or self._seek_cb, history_title=f"📜  Planned before · {dn} · {round_name}")
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
