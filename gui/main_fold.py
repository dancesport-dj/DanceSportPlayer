"""📐 Folding: a deck, a wishlist or the whole column shrunk to a tab.

Split off gui/main_decks.py as a MainWindow mixin. Screen space is the scarce
thing at the desk, so every box can fold to its title — which means the splitter
constraints have to be re-clamped in the same order the splitters nest.
"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from shared.stores import (  # auto-resolved
    save_settings,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from planner import i18n

log = logging.getLogger("dancesport.gui.fold")


class FoldMixin:
    """📐 Folding boxes to tabs, and the splitter clamps that go with it."""

    # ── Fold a deck/wishlist to a tab (header-only strip) ─────────────────────────
    def _box_shown(self, table: PlaylistTable) -> bool:
        """True if this playlist's box is shown by the current view — also catches
        boxes hidden only via an ancestor (col2 / the wishlist area)."""
        b = self.deck(table).box
        if b is None:
            return False
        root = getattr(self, "_right_split", None)
        if root is None:   # during construction: only explicit hides exist yet
            return not b.isHidden()
        return b.isVisibleTo(root)

    def _all_decks_folded(self) -> bool:
        """True if every deck shown by the current view is folded to a tab."""
        vis = [t for t in (*self._decks, *self._day_decks) if self._box_shown(t)]
        return bool(vis) and all(self.deck(t).folded for t in vis)

    def _folded_tab_is_sideways(self, table: PlaylistTable) -> bool:
        """True when this folded playlist lives in a SIDEWAYS-collapsed strip
        (width-clamped slim column), where only the badge fits the tab. A
        full-width tab (vertical fold / whole section collapsed) returns False."""
        if table in self._wishlists:
            if self._wish_grid_on():
                # Sideways (badge-only) tab only inside a fully-folded column.
                return not self._wish_all_folded() and self._wish_col_folded(table)
            return not self._wish_all_folded()
        if self._all_decks_folded():
            return False
        pair = self._deck_col_pair(table)
        vis = [t for t in pair if self._box_shown(t)]
        return bool(vis) and all(self.deck(t).folded for t in vis)

    def _refresh_deck_header(self, table: PlaylistTable):
        """Re-render a deck/wishlist header label for the current fold state."""
        hdr = self.deck(table).header
        if hdr is None:
            return
        active = self.deck(table).active
        hdr.setText(self._deck_header_text(table, active))

    def _toggle_deck_fold(self, table: PlaylistTable, folded: bool | None = None):
        """Fold a deck/wishlist to a slim header tab (or unfold it) so the remaining
        open playlists dynamically get its space — without changing the view."""
        if not self._is_deck(table) and table not in self._wishlists:
            return
        box = self.deck(table).box
        hdr = self.deck(table).header
        if box is None or hdr is None:
            return
        if folded is None:
            folded = not self.deck(table).folded
        if bool(self.deck(table).folded) == bool(folded):
            return
        self._commit_inline_rename()   # never fold a header mid-rename
        is_wish = table in self._wishlists
        if is_wish:
            group = self._wish_fold_group(table)
            split = self._wish_split_for(table)
            section_was_collapsed = self._wish_all_folded()
        else:
            group = self._deck_col_pair(table)
            split = self._deck_col_split(table)
            section_was_collapsed = self._all_decks_folded()
        vis = [t for t in group if self._box_shown(t)]
        group_was_all_folded = bool(vis) and all(self.deck(t).folded for t in vis)
        self.deck(table).folded = bool(folded)
        table.setVisible(not folded)
        # Through _refresh_mode_btn, not setVisible: a player-only install hides
        # the toggle for good, and unfolding must not hand it back.
        self._refresh_mode_btn(table)
        cnt = self.deck(table).count_lbl
        if cnt is not None:
            cnt.setVisible(not folded)
        tot = self.deck(table).total_lbl
        if tot is not None:
            tot.setVisible(not folded and bool(tot.text()))
        # The bar the badge and the ⏭/✋ switch share. Hidden whole, so a folded
        # deck does not keep a switch under its header tab; the two inside keep
        # their own rules (the badge follows its text, the switch playing mode).
        badge_row = self.deck(table).badge_row
        if badge_row is not None:
            badge_row.setVisible(not folded)
        active = self.deck(table).active
        hdr.setText(self._deck_header_text(table, active))
        hdr.setToolTip(i18n.t("%s — folded.  Click to unfold.")
                       % self.deck(table).name
                       if folded else
                       "Click to focus · right-click or double-click to rename")
        if folded and table is self._table:
            # A folded deck shouldn't stay the Generate/Save/↺ target.
            for t in (*self._decks, *self._day_decks):
                if not self.deck(t).folded and self._box_shown(t):
                    self._set_active_table(t)
                    break
        if is_wish:
            self._sync_wish_fold_constraints()
        else:
            self._sync_col_fold_constraints(group_was_all_folded)
        for s in (self._decks_col1, self._decks_col2, self._decks_split,
                  self._decks_col3, self._decks_col4, self._decks_split2,
                  self._day_col1, self._day_col2, self._day_split,
                  self._day_col3, self._day_col4, self._day_split2,
                  self._wish_col1, self._wish_col2,
                  self._wish_split, self._right_split):
            # QSplitter re-derives its own max size from its children on a
            # DEFERRED event — force it now so the setSizes below aren't
            # clamped by the pre-fold constraints.
            s.refresh()
        if folded:
            section_now = self._wish_all_folded() if is_wish else self._all_decks_folded()
            if section_now and not section_was_collapsed:
                # The section just collapsed to tab rows: pin its pane to the
                # strip's own height and hand the rest to the other half right
                # away — the max clamps alone don't make the parent splitter
                # redistribute synchronously, and zeroing the pane instead
                # would make its tabs vanish (the splitter drops it to its
                # minimum, not to the strip height).
                sizes = self._right_split.sizes()
                rt = sizes[0] + sizes[1]
                if rt > 0:
                    strip = (self._wish_split if is_wish
                             else self._deck_tabs).sizeHint().height()
                    strip = min(strip, rt)
                    # Panes beyond decks+wishlists (library browser) keep theirs.
                    self._right_split.setSizes(
                        ([rt - strip, strip] if is_wish
                         else [strip, rt - strip]) + sizes[2:])
        if not folded:
            # Give the freshly unfolded playlist its half of the pair back.
            total = sum(split.sizes())
            if total > 0:
                split.setSizes([total // 2, total - total // 2])
            # If its whole section (decks / wishlist area) was collapsed to tab
            # height, give the section its share of the window back too.
            if section_was_collapsed:
                sizes = self._right_split.sizes()
                rt = sizes[0] + sizes[1]
                if rt > 0:
                    self._right_split.setSizes(
                        [int(rt * 0.75), rt - int(rt * 0.75)] + sizes[2:])

    def _sync_col_fold_constraints(self, rebalance: bool = False):
        """Reconcile the fold clamps of both deck columns with the current state.

        A folded deck normally carries only a HEIGHT clamp — its column partner
        gets the vertical space. When every visible deck of ONE column is folded
        the clamps flip to width clamps: QSplitter derives its own max size from
        its children, so a fully height-clamped column would clamp the parent
        splitter and squash the OTHER column; collapsing it sideways hands its
        width to the open column instead. And when ALL visible decks are folded
        the width clamps would do the same to the WISHLIST area below (the chain
        _decks_split → _right_split would pin the window width), so then every
        box goes back to height clamps and the whole deck section collapses to
        full-width tab rows — the wishlists get the vertical space."""
        all_decks_folded = self._all_decks_folded()
        for col, pair, _grid in self._deck_columns():
            vis = [t for t in pair if self._box_shown(t)]
            col_folded = bool(vis) and all(self.deck(t).folded for t in vis)
            for t in pair:
                b = self.deck(t).box
                if b is None:
                    continue
                # Tab text depends on the strip orientation (badge-only when
                # sideways) and feeds the width clamp below — refresh it first.
                self._refresh_deck_header(t)
                if col_folded and not all_decks_folded:
                    b.setMaximumHeight(16777215)
                    b.layout().activate()
                    b.setMaximumWidth(b.sizeHint().width() + 8)
                else:
                    b.setMaximumWidth(16777215)
                    if self.deck(t).folded:
                        b.layout().activate()
                        b.setMaximumHeight(b.sizeHint().height() + 4)
                    else:
                        b.setMaximumHeight(16777215)
            if col_folded and not all_decks_folded:
                # Stack the tabs at the top of the collapsed strip instead of
                # leaving the lower one floating at mid-height.
                total = sum(col.sizes())
                if total > 0 and vis:
                    top = self.deck(pair[0]).box.sizeHint().height() + 4
                    col.setSizes([min(top, total), max(total - top, 0)])
            for t in pair:
                self._refresh_fold_btn(t)   # arrows depend on the column state
        if rebalance:
            # Rebalance each grid's two columns (the hidden grids are inert).
            for grid, right_col in ((self._decks_split, self._decks_col2),
                                    (self._decks_split2, self._decks_col4),
                                    (self._day_split, self._day_col2),
                                    (self._day_split2, self._day_col4)):
                vt = sum(grid.sizes())
                if vt > 0 and right_col.isVisible():
                    grid.setSizes([vt // 2, vt - vt // 2])

    def _wish_all_folded(self) -> bool:
        """True if every wishlist shown right now is folded to a tab."""
        vis = [t for t in self._wishlists if self._box_shown(t)]
        return bool(vis) and all(self.deck(t).folded for t in vis)

    def _sync_wish_fold_constraints(self):
        """Reconcile the fold clamps of the wishlist pair (mirror of the deck
        columns, one orientation down: the wishlists sit SIDE BY SIDE, so a
        folded one collapses sideways for its open neighbour — width clamp —
        and only when every visible wishlist is folded do the clamps flip to
        height, collapsing the whole wishlist area so the decks above get the
        vertical space)."""
        all_folded = self._wish_all_folded()
        if self._wish_grid_on():
            # 2×2: wishlists stack vertically within each column, so folding behaves
            # exactly like a deck column — a folded one clamps HEIGHT (its column
            # partner gets the room); a whole folded column clamps WIDTH for the open
            # column; all folded falls back to height so the area collapses to tabs.
            for pair in ((self._wishlist, self._wishlist3),
                         (self._wishlist2, self._wishlist4)):
                vis = [t for t in pair if self._box_shown(t)]
                col_folded = bool(vis) and all(self.deck(t).folded for t in vis)
                for t in pair:
                    b = self.deck(t).box
                    if b is None:
                        continue
                    self._refresh_deck_header(t)
                    if col_folded and not all_folded:
                        b.setMaximumHeight(16777215)
                        b.layout().activate()
                        b.setMaximumWidth(b.sizeHint().width() + 8)
                    else:
                        b.setMaximumWidth(16777215)
                        if self.deck(t).folded:
                            b.layout().activate()
                            b.setMaximumHeight(b.sizeHint().height() + 4)
                        else:
                            b.setMaximumHeight(16777215)
                    self._refresh_fold_btn(t)
            return
        for t in self._wishlists:
            b = self.deck(t).box
            if b is None:
                continue
            # Tab text depends on the strip orientation (badge-only when
            # sideways) and feeds the width clamp below — refresh it first.
            self._refresh_deck_header(t)
            if all_folded:
                b.setMaximumWidth(16777215)
                b.layout().activate()
                b.setMaximumHeight(b.sizeHint().height() + 4)
            elif self.deck(t).folded:
                b.setMaximumHeight(16777215)
                b.layout().activate()
                b.setMaximumWidth(b.sizeHint().width() + 8)
            else:
                b.setMaximumWidth(16777215)
                b.setMaximumHeight(16777215)
            self._refresh_fold_btn(t)

    def _toggle_collapse_all(self):
        """⊟ / ⊞ in one button: collapse the round and dance headers of every
        playlist, and open them all again on the next click. The caption says
        what that next click does.

        Its own flag rather than a reading of the tables: an empty deck has no
        headers to collapse, and a state read off one would never flip back.

        The 🤸 Eintanzen / ETDS party list is a playlist like any other here: it
        has rounds and dance headers to collapse, and leaving it out made the
        button look broken in the no-playlist view, where it is the only list."""
        collapse = not getattr(self, "_all_collapsed", False)
        self._all_collapsed = collapse
        tables = [*self._decks, *self._day_decks, self._warmup_table]
        for t in tables:
            (t.collapse_all if collapse else t.expand_all)()
        self._set_toolbar_btn_text(
            self._collapse_btn, "⊞  Expand all" if collapse else "⊟  Collapse all")

    def _toggle_fold_all_decks(self):
        """▴ / ▾ in one button: fold every visible playlist to its header tab,
        or open them all again once any of them is folded — so a single deck
        folded by hand is opened by the same click that would fold the rest."""
        vis = [t for t in (*self._decks, *self._day_decks, *self._wishlists)
               if self._box_shown(t)]
        folded_now = (any(self.deck(t).folded for t in vis)
                      or self._warmup_folded)
        self._fold_all_decks(not folded_now)

    def _fold_all_decks(self, folded: bool):
        """Fold or unfold every VISIBLE playlist at once (toolbar twin of ⊟/⊞)
        — decks, wishlists AND the 🤸 Eintanzen / party list, so one click
        collapses / restores the whole layout. The warm-up panel is not a deck
        (it is one full-width box in the right splitter) and so has its own
        fold; without this line the buttons did nothing at all in the
        no-playlist view, where that panel is all there is."""
        for t in (*self._decks, *self._day_decks, *self._wishlists):
            if self._box_shown(t):
                self._toggle_deck_fold(t, folded)
        self._toggle_warmup_fold(folded)   # no-ops while the panel is hidden
        self._set_toolbar_btn_text(
            self._fold_decks_btn,
            "▾  Unfold decks" if folded else "▴  Fold decks")
        self.statusBar().showMessage(
            "▴ All playlists folded to tabs — click a tab to open one"
            if folded else "▾ All playlists unfolded")

    def _refresh_fold_btn(self, table: PlaylistTable):
        """Point the fold arrow where the playlist edge will move when clicked:
        an open TOP deck folds upwards (▴) and its tab expands back down (▾),
        a BOTTOM deck folds down (▾) and expands back up (▴); a tab in a fully
        collapsed column strip expands sideways (▸/◂) toward the middle, and a
        tab in a fully collapsed section (all decks / all wishlists) expands
        back down (▾). Wishlists mirror the decks one orientation down."""
        btn = self.deck(table).fold_btn
        if btn is None:
            return
        if not self.deck(table).folded:
            if table in self._wishlists:
                top = self._wish_is_top(table)
            else:
                top = self._deck_is_top(table)
            btn.setText("▴" if top else "▾")
            btn.setToolTip("Fold this playlist to a tab —\n"
                           "the other open playlists get its space.")
            return
        btn.setToolTip("Unfold this playlist")
        if table in self._wishlists:
            if self._wish_all_folded():
                btn.setText("▾")   # whole area expands back down
            elif self._wish_grid_on():
                if self._wish_col_folded(table):
                    btn.setText("▸" if self._wish_is_left(table) else "◂")
                else:
                    btn.setText("▾" if self._wish_is_top(table) else "▴")
            else:
                btn.setText("▸" if table is self._wishlist else "◂")
            return
        if self._all_decks_folded():
            btn.setText("▾")       # whole deck section expands back down
            return
        pair = self._deck_col_pair(table)
        vis = [t for t in pair if self._box_shown(t)]
        if bool(vis) and all(self.deck(t).folded for t in vis):
            btn.setText("▸" if self._deck_is_left(table) else "◂")
        else:
            btn.setText("▾" if self._deck_is_top(table) else "▴")

    def _toggle_warmup_fold(self, folded: bool | None = None):
        """Compact the stand-alone Eintanzen panel to its header strip (or open it
        again), handing the freed vertical height to the decks. Mirrors the deck /
        wishlist fold, but the warm-up panel is one full-width box in the right
        splitter, so the bookkeeping is far simpler."""
        box = self._warmup_box
        if not box.isVisibleTo(self._right_split):   # as _box_shown, ancestors included
            return
        if folded is None:
            folded = not self._warmup_folded
        folded = bool(folded)
        changed = (folded != self._warmup_folded)
        self._commit_inline_rename()   # never fold a header mid-rename
        self._warmup_folded = folded
        self._warmup_table.setVisible(not folded)
        # Σ badge goes with the table (before the height clamp below reads sizeHint).
        tot = self.deck(self._warmup_table).total_lbl
        if tot is not None:
            tot.setVisible(not folded and bool(tot.text()))
        name = self._warmup_default_name()
        btn = getattr(self, "_warmup_fold_btn", None)
        if btn is not None:
            btn.setText("▸" if folded else "▾")
            btn.setToolTip(i18n.t("Open the %s panel.") % name if folded else
                           i18n.t("Compact the %s panel to its header tab —\n"
                                  "click the tab (or this arrow) to open it "
                                  "again.") % name)
        hdr = self.deck(self._warmup_table).header
        if hdr is not None:
            hdr.setToolTip(i18n.t("%s — folded.  Click to open.") % name
                           if folded else
                           "Click to focus · right-click or double-click to rename")
        # Clamp the box to its header height when folded so the splitter actually
        # shrinks it (the deferred max-size recalc must be forced before setSizes).
        box.layout().activate()
        box.setMaximumHeight(box.sizeHint().height() + 4 if folded else 16777215)
        self._right_split.refresh()
        idx = self._right_split.indexOf(box)
        sizes = self._right_split.sizes()
        if changed and idx > 0 and len(sizes) > idx and sum(sizes) > 0:
            if folded:
                strip = box.sizeHint().height() + 4
                freed = max(0, sizes[idx] - strip)
                sizes[idx] = strip
                sizes[0] += freed         # hand the height to the decks above
            else:
                want = max(140, int(sum(sizes) * 0.2))
                grow = min(max(0, want - sizes[idx]), max(0, sizes[0] - 200))
                sizes[idx] += grow
                sizes[0]   -= grow
            self._right_split.setSizes(sizes)
        self._autosave_playlist()

    def _folded_lib_height(self) -> int:
        """What the library pane shrinks to when folded: its header strip plus
        the tab bar it hangs under."""
        return (self._lib_browser._hdr.sizeHint().height()
                + self._lib_tabs.tabBar().sizeHint().height() + 8)

    def _on_lib_fold_toggled(self, folded: bool):
        self._settings["library_folded"] = folded
        save_settings(self._settings)
        # Redistribute the vertical space right away: the max-height clamp on
        # the pane alone doesn't make the splitter shrink it to the header
        # strip — the freed space must be handed to the decks explicitly.
        # The library shares its pane with the 🏆 tournament tree, so the clamp
        # has to sit on the TAB widget — the browser's own max height would let
        # the splitter keep the space around it.
        self._lib_tabs.setMaximumHeight(
            self._folded_lib_height() if folded else 16777215)
        self._hand_lib_pane_height(folded, self._folded_lib_height())

    def _hand_lib_pane_height(self, folded: bool, folded_height: int):
        """Give the library pane `folded_height` (or a quarter of the splitter
        when opening) and share what is left among the panes above it."""
        sizes = self._right_split.sizes()
        if len(sizes) < 2:
            return
        total = sum(sizes)
        if total <= 0:
            return
        if folded:
            lib = min(folded_height, total)
        else:
            lib = max(140, int(total * 0.25))
        rest = total - lib
        # The library pane is the LAST child; scale every other pane (decks /
        # warm-up / wishlist) to fill the remaining height, keeping their ratios.
        head = sizes[:-1]
        head_sum = sum(head)
        if head_sum > 0:
            new_head = [round(s * rest / head_sum) for s in head]
            new_head[0] += rest - sum(new_head)   # absorb rounding into the decks
        else:
            new_head = [rest] + [0] * (len(head) - 1)
        self._right_split.setSizes(new_head + [lib])

    # ── Fold the WHOLE pane — both tabs — from the tab bar's corner ──────────────

    def _folded_lib_pane_height(self) -> int:
        """What the whole pane shrinks to: the tab bar, and nothing under it.
        The corner arrow rides that bar, which is what keeps it clickable — so
        the clamp has to clear the arrow too, not just the tabs, or the one
        control that opens the pane again is the one the fold cuts off."""
        bar = self._lib_tabs.tabBar().sizeHint().height()
        btn = getattr(self, "_lib_pane_fold_btn", None)
        if btn is not None:
            bar = max(bar, btn.sizeHint().height())
        return bar + 6

    def _build_lib_pane_fold_btn(self):
        """Hang the fold arrow in the tab bar's top-right corner.

        The 📚 browser has a ▾ of its own, but it sits INSIDE that tab: it is
        gone as soon as 🏆 Tournaments is picked, and it only ever folds the
        browser. This one belongs to the bar both tabs hang under, so it
        collapses the pane as a whole — and survives doing it, which is the
        only way back short of the toolbar button."""
        self._lib_pane_folded = False
        # The tab bar draws a base line across its whole width. On the left the
        # tabs sit on top of it, so it never showed; the corner is bare, so the
        # arrow ended up with a stray line hanging over it. The tabs carry their
        # own outline in document mode and look the same without the base.
        self._lib_tabs.tabBar().setDrawBase(False)
        btn = QToolButton()
        btn.setAutoRaise(True)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda: self._toggle_lib_pane_fold())
        self._lib_pane_fold_btn = btn
        self._lib_tabs.setCornerWidget(btn, Qt.Corner.TopRightCorner)
        # Picking a tab on a collapsed pane means "show me that one", not
        # "switch the tab I cannot see".
        self._lib_tabs.tabBarClicked.connect(
            lambda _i: self._lib_pane_folded
            and self._toggle_lib_pane_fold(False))
        if self._settings.get("library_pane_folded"):
            self._toggle_lib_pane_fold(True, save=False)
        else:
            self._refresh_lib_pane_fold_btn()

    def _refresh_lib_pane_fold_btn(self):
        """The arrow points where the pane's edge will go when clicked."""
        folded = self._lib_pane_folded
        self._lib_pane_fold_btn.setText("▴" if folded else "▾")
        self._lib_pane_fold_btn.setToolTip(
            "Open the library pane back up" if folded
            else "Collapse the whole pane —\n"
                 "📚 Library and 🏆 Tournaments together")

    def _toggle_lib_pane_fold(self, folded: bool = None, save: bool = True):
        """Collapse the library pane to its tab bar, or give it its height back."""
        if folded is None:
            folded = not self._lib_pane_folded
        self._lib_pane_folded = folded
        self._lib_tabs.setMaximumHeight(
            self._folded_lib_pane_height() if folded else 16777215)
        self._refresh_lib_pane_fold_btn()
        self._settings["library_pane_folded"] = folded
        if save:
            save_settings(self._settings)
        self._hand_lib_pane_height(folded, self._folded_lib_pane_height())
        self.statusBar().showMessage(
            "📚 Library pane collapsed — the arrow in the tab bar opens it"
            if folded else "📚 Library pane open")
