"""Re-rolling titles in a playlist table: ↺ one song, a whole dance or a
round, the warm-up's and the party list's swaps, and the strategy, pool and
timbre settings a re-roll draws with.

Mixin of PlaylistTable, split off gui/table/playlist_table.py.
"""
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMessageBox

from planner import i18n
from planner.generate.warmup import warmup_swap_partner
from planner.models import ALLOW_REPEAT
from planner.terms import dance_name
from shared.columns import _COL_TITLE
from shared.widgets import _show_toast
from gui.common import _C_ROW_EVEN, _C_ROW_ODD

if TYPE_CHECKING:
    from gui.window.hosts import PlaylistTableHost
else:
    PlaylistTableHost = object

log = logging.getLogger("dancesport.gui.playlist_table")


class TableRegenMixin(PlaylistTableHost):
    """Re-rolling a song, a dance or a round, and what a re-roll draws from."""

    def _effective_anchor(self, round_name: str | None, exclude_rows: set):
        """Audio features to use as the round's timbral anchor for a regen/replace.

        The anchor is normally the round's FIRST song. But when that song is the one
        being re-rolled/replaced (its row is in `exclude_rows`), anchoring on it would
        just match the song we're removing — so fall back to the next song in the round
        (in display order) that still has features. Returns None when timbre is off or
        no surviving song in the round has features."""
        if not round_name or not self._use_timbre:
            return None
        for r, m in self._row_meta.numbered():
            if m.theme or m.round_name != round_name or r in exclude_rows:
                continue
            if m.entry.features is not None:
                return m.entry.features
        return None

    def _round_cls_style(self, round_name: str | None) -> tuple[str, str | None]:
        """Class + style a ↺ re-roll must respect — the round's own competition
        on a stacked 📅 day-plan deck, the deck's otherwise."""
        ctx = self._round_ctx.get(round_name or "") or {}
        return (ctx.get("cls") or self._dance_class,
                ctx.get("style") or self._style)

    def _regen(self, row: int):
        try:
            if row >= len(self._row_meta) or not self._row_meta[row]:
                return
            meta = self._row_meta[row]
            if meta.warmup and self._party_swap():
                self._swap_from_list_end(row)
                return
            if meta.warmup:
                self._regen_warmup(row)
                return
            if meta.theme:
                return   # theme rows have no round/tier context to regenerate from
            if self._is_row_pinned(row):
                _show_toast(self, i18n.t("📌  Pinned — unpin the title to re-roll it"))
                return
            suggester = self._suggester
            if not suggester or not self._playlist:
                return

            dance = meta.dance
            tier  = meta.tier

            # Build exclusion set: every current entry AND any library copy of it
            # (same filename / fingerprint), so a re-roll can't return a duplicate of
            # a song already planned here. This slot's own song is only the
            # fallback when no alternative exists: left in the draw, it came back
            # about once in as many ↺ as the dance has titles.
            planned = self._row_meta.entries()
            exclude = self._exclude_with_dupes(planned)
            current = meta.entry

            r_cls, r_style = self._round_cls_style(meta.round_name)

            def pick():
                return suggester.regenerate(
                    dance, r_cls, tier, exclude,
                    prefer_fresh=meta.prefer_fresh,
                    round_name=meta.round_name,
                    use_timbre=self._use_timbre,
                    strategy=meta.strategy or None,
                    style=r_style,
                    candidates=self._round_pools_by_name.get(meta.round_name),
                    anchor=self._effective_anchor(meta.round_name, {row}),
                )
            new_entry = pick()
            if not new_entry and current and dance not in ALLOW_REPEAT:
                exclude.discard(str(current.path))
                new_entry = pick()
            if not new_entry:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            # If this row was playing, remember it so we can auto-play the new pick
            # in its place once the row is redrawn. Drop the play-row marker now (the
            # widget it points at is about to be replaced); playback switches in _after.
            was_playing = (row == self._current_play_row)
            if was_playing:
                self._current_play_row = -1

            # Update metadata + live playlist
            meta.entry = new_entry
            self._playlist[meta.round_name][meta.h_idx][meta.d_idx] = new_entry

            # Defer row redraw so it happens after the clicked signal returns.
            # Replacing a cell widget while inside its signal handler can crash.
            bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD

            def _after():
                self._fill_song_row(row, meta, bg)
                # If the replaced song was playing, immediately play the new one in
                # its place instead of leaving playback stopped.
                if was_playing and self._play_cb:
                    self._on_play_click(row, new_entry.path)
                # Keep the row selected AND the keyboard focus on the table so the
                # Space / Ctrl+R / Ctrl+N shortcuts keep firing after a re-roll.
                self.setCurrentCell(row, _COL_TITLE)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _after)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def _party_swap(self) -> bool:
        """Does ↺ swap within this list instead of re-rolling from the library?
        True on the ETDS party list: an Eintanzen list without a style (a
        per-class warm-up always has one) that is not a running order."""
        return self._warmup and not self._player_list and not self._warmup_style

    def _swap_from_list_end(self, row: int):
        """↺ on the party list: swap the title on `row` with one of the same
        dance from the end of the list (see warmup_swap_partner)."""
        song_rows = self._row_meta.song_rows()
        if row not in song_rows:
            return
        k = warmup_swap_partner(self._row_meta.entries(), song_rows.index(row))
        if k is None:
            dance = self._row_meta[row].dance
            _show_toast(self, i18n.t("↺  No other %s near the end of the list")
                        % dance_name(dance, dance))
            return
        partner = song_rows[k]
        # Deferred: the ↺ button that fired this is one of the widgets redrawn.
        QTimer.singleShot(0, lambda: self._swap_song_rows(row, partner))

    def _swap_song_rows(self, a: int, b: int):
        """Swap the titles on two song rows in place and redraw just those two.
        The playing title keeps playing; its marker moves with it."""
        ma, mb = self._row_meta.at(a), self._row_meta.at(b)
        if ma is None or mb is None or ma.entry is None or mb.entry is None:
            return
        self._row_meta.swap(a, b)
        song_rows = self._row_meta.song_rows()
        for r, m in ((a, ma), (b, mb)):
            for c in range(self.columnCount()):
                self._played_saved.pop((r, c), None)
            bg = _C_ROW_EVEN if song_rows.index(r) % 2 == 0 else _C_ROW_ODD
            self._fill_song_row(r, m, bg)
            if r == self._current_play_row:
                self.sync_play_glyph()
        self._update_play_row_hl()
        self.setCurrentCell(a, _COL_TITLE)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        log.info("⇅ Titles swapped\n"
                 "row %d: %s\n"
                 "row %d: %s", a, ma.entry.title, b, mb.entry.title)
        self._notify_changed()

    def _regen_warmup(self, row: int):
        """Re-roll one warm-up row: pick a fresh timbre-matched, TSO-conform track
        of the same dance for this class (excluding tracks already in the list)."""
        meta = self._row_meta[row]
        if not self._suggester:
            return
        dance = meta.dance or ""
        # Exclude tracks already in THIS list AND any track planned in the open
        # playlist decks, so a re-roll never picks music used elsewhere.
        exclude = self._row_meta.paths()
        try:
            exclude |= self.host.planned_paths()
        except Exception as exc:
            log.debug("♻️ Deck dedup index unavailable — re-roll may reuse a planned track: %s", exc)
        current = meta.entry
        new_entry = self._suggester.regenerate_warmup(
            dance, self._warmup_style, self._warmup_class, exclude,
            anchor_entry=current, relax=self._warmup_relax,
        )
        if not new_entry:
            QMessageBox.information(self, "Regenerate",
                                    "No alternative Practice track found.")
            return
        was_playing = (row == self._current_play_row)
        if was_playing:
            self._current_play_row = -1
        meta.entry = new_entry
        bg = _C_ROW_EVEN if row % 2 == 0 else _C_ROW_ODD

        def _after():
            self._fill_song_row(row, meta, bg)
            if was_playing and self._play_cb:
                self._on_play_click(row, new_entry.path)
            self.setCurrentCell(row, _COL_TITLE)
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self._notify_changed()
        QTimer.singleShot(0, _after)

    def _regen_dance(self, round_name: str, d_idx: int, dance: str):
        """Re-roll EVERY heat of one dance within one round.

        Same behaviour as the per-song ↺ (honours the round's strategy, BPM,
        class and timbre), but applied to the whole dance segment at once. Other
        dances and other rounds stay untouched; picks stay unique across the
        whole playlist (except ALLOW_REPEAT dances, e.g. PD)."""
        try:
            if not self._suggester or not self._playlist:
                return

            # Rows that hold this dance in this round.
            target_rows = [
                r for r, m in enumerate(self._row_meta)
                if m and not m.theme
                and m.round_name == round_name and m.d_idx == d_idx
                and not self._is_row_pinned(r)   # 📌 stays
            ]
            if not target_rows:
                return

            # Exclude every other current entry across the whole playlist (and any
            # library copy of it), but NOT the ones we're replacing, so other slots
            # stay unique and no duplicate of a planned song can be re-picked.
            replacing = set(target_rows)
            keep = [m.entry for r, m in self._row_meta.numbered()
                    if r not in replacing]
            exclude = self._exclude_with_dupes(keep)

            # Anchor on the first surviving song NOT in this dance segment, so re-rolling
            # the anchor dance (e.g. the first one) matches the rest of the round.
            seg_anchor = self._effective_anchor(round_name, replacing)

            # Remember which row (if any) in this segment was playing so we can
            # auto-play its replacement once the rows are redrawn.
            playing_row = -1
            picked_any = False
            r_cls, r_style = self._round_cls_style(round_name)
            for r in target_rows:
                meta = self._row_meta[r]
                new_entry = self._suggester.regenerate(
                    dance, r_cls, meta.tier, exclude,
                    prefer_fresh=meta.prefer_fresh,
                    round_name=meta.round_name,
                    use_timbre=self._use_timbre,
                    strategy=meta.strategy or None,
                    style=r_style,
                    candidates=self._round_pools_by_name.get(meta.round_name),
                    anchor=seg_anchor,
                )
                if not new_entry:
                    continue
                picked_any = True
                # Keep heats within this dance unique (PD may repeat) — exclude the
                # pick AND its library copies so a later heat can't grab a duplicate.
                if dance not in ALLOW_REPEAT:
                    exclude |= self._exclude_with_dupes([new_entry])

                # Drop the play-row marker if this row was playing — its widget is
                # about to be replaced; playback switches to the new pick in _redraw.
                if r == self._current_play_row:
                    playing_row = r
                    self._current_play_row = -1

                meta.entry = new_entry
                self._playlist[meta.round_name][meta.h_idx][meta.d_idx] = new_entry

            if not picked_any:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            # Defer redraw so widgets aren't replaced inside the clicked handler.
            def _redraw():
                for r in target_rows:
                    meta = self._row_meta[r]
                    bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, meta, bg)
                # If a song in this segment was playing, play its replacement now.
                if playing_row >= 0 and self._play_cb:
                    new_entry = self._row_meta[playing_row].entry
                    if new_entry is not None:
                        self._on_play_click(playing_row, new_entry.path)
                # Keep keyboard focus on the table so shortcuts keep working.
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _redraw)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def _regen_round(self, round_name: str):
        """Re-roll EVERY dance / heat of one whole round at once.

        Like the per-dance ↺ but applied to the entire round: each dance is
        re-rolled from its own pool (honouring the round's strategy, BPM, class
        and timbre), picks stay unique across the whole playlist (except
        ALLOW_REPEAT dances, e.g. PD). Other rounds stay untouched."""
        try:
            if not self._suggester or not self._playlist:
                return

            # Group this round's song rows by dance, preserving display order.
            rows_by_dance: dict[int, list[int]] = {}
            for r, m in enumerate(self._row_meta):
                if (m and not m.theme
                        and m.round_name == round_name
                        and not self._is_row_pinned(r)):   # 📌 stays
                    rows_by_dance.setdefault(m.d_idx, []).append(r)
            if not rows_by_dance:
                return

            all_rows = [r for rows in rows_by_dance.values() for r in rows]
            playing_row = -1
            picked_any  = False

            # Re-roll dance by dance. `exclude` is rebuilt per dance so that
            # already-replaced dances (with their new picks) and untouched
            # rounds keep every slot unique.
            for d_idx in sorted(rows_by_dance):
                seg_rows = rows_by_dance[d_idx]
                dance    = self._row_meta[seg_rows[0]].dance

                replacing = set(seg_rows)
                keep = [m.entry for r, m in self._row_meta.numbered()
                        if r not in replacing]
                exclude = self._exclude_with_dupes(keep)

                seg_anchor = self._effective_anchor(round_name, replacing)

                r_cls, r_style = self._round_cls_style(round_name)
                for r in seg_rows:
                    meta = self._row_meta[r]
                    new_entry = self._suggester.regenerate(
                        dance, r_cls, meta.tier, exclude,
                        prefer_fresh=meta.prefer_fresh,
                        round_name=round_name,
                        use_timbre=self._use_timbre,
                        strategy=meta.strategy or None,
                        style=r_style,
                        candidates=self._round_pools_by_name.get(round_name),
                        anchor=seg_anchor,
                    )
                    if not new_entry:
                        continue
                    picked_any = True
                    if dance not in ALLOW_REPEAT:
                        exclude |= self._exclude_with_dupes([new_entry])

                    if r == self._current_play_row:
                        playing_row = r
                        self._current_play_row = -1

                    meta.entry = new_entry
                    self._playlist[round_name][meta.h_idx][meta.d_idx] = new_entry

            if not picked_any:
                QMessageBox.information(self, "Regenerate", "No alternative song found.")
                return

            def _redraw():
                for r in all_rows:
                    meta = self._row_meta[r]
                    bg = _C_ROW_EVEN if meta.h_idx % 2 == 0 else _C_ROW_ODD
                    self._fill_song_row(r, meta, bg)
                if playing_row >= 0 and self._play_cb:
                    new_entry = self._row_meta[playing_row].entry
                    if new_entry is not None:
                        self._on_play_click(playing_row, new_entry.path)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                self._notify_changed()
            QTimer.singleShot(0, _redraw)

        except Exception as exc:
            QMessageBox.critical(self, "Regenerate Error", str(exc))

    def update_strategy(self, round_name: str, strategy: str, prefer_fresh: bool):
        """Update the stored strategy for every row of a round WITHOUT re-rolling.

        Lets the ↺ buttons (per-song / per-dance) draw from the newly selected
        strategy's pool while the already-generated grid stays untouched."""
        for m in self._row_meta:
            if m and m.round_name == round_name:
                m.strategy     = strategy or ""
                m.prefer_fresh = prefer_fresh

    def set_round_pool(self, round_name: str, pool):
        """Update the candidate pool a round's ↺ buttons draw from (Past
        Competitions 🎯 scope), without re-rolling the grid. `pool=None` means
        the full library (🎯 unticked)."""
        self._round_pools_by_name[round_name] = pool

    def set_use_timbre(self, on: bool):
        """Toggle timbre-similarity scoring for the ↺ buttons live, without
        re-rolling the grid (anchors stay cached on the suggester)."""
        self._use_timbre = on
