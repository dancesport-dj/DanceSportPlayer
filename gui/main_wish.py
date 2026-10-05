"""⭐ The wishlists: their own grid, their headers, their counts.

Split off gui/main_decks.py as a MainWindow mixin. A wishlist is a flat list of
candidates, not a draw — it has its own layout beside the decks, its own
drag-to-swap header and its own housekeeping against the planned playlists.
"""
import logging

from PySide6.QtCore import (
    QMimeData,
    Qt,
)
from PySide6.QtGui import (
    QDrag,
)
from PySide6.QtWidgets import (
    QApplication,
)
from planner.models import ALLOW_REPEAT
from planner.planned import is_planned
from planner.suggester import PlaylistSuggester
from shared.widgets import (
    _show_toast,
)
from shared.stores import (  # auto-resolved
    save_settings,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from planner import i18n

log = logging.getLogger("dancesport.gui.wish")


class WishlistMixin:
    """⭐ Wishlist layout, headers, counts and housekeeping."""

    def _reset_wishlist_name(self, table: PlaylistTable):
        """Reset a wishlist's header title back to its default (called when it's
        emptied). `_set_deck_name` refreshes the header and autosaves the session.
        An empty wishlist is no file any more either (📂 on its header)."""
        table._m3u_path = None
        default_name = self.deck(table).default_name
        if default_name:
            self._set_deck_name(table, default_name)

    def _wish_header_press(self, e, table: PlaylistTable):
        """Record the press origin (so a real drag can be told apart from a click),
        then fall through to the normal header click (focus / right-click menu)."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._wish_drag_origin = (e.position().toPoint()
                                      if hasattr(e, "position") else e.pos())
        else:
            self._wish_drag_origin = None
        self._on_header_press(e, table)

    def _wish_header_move(self, e, table: PlaylistTable):
        """Start a wishlist-swap drag once the cursor leaves the click threshold."""
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        origin = getattr(self, "_wish_drag_origin", None)
        pos = e.position().toPoint() if hasattr(e, "position") else e.pos()
        if origin is None or (pos - origin).manhattanLength() < QApplication.startDragDistance():
            return
        self._wish_drag_origin = None
        drag = QDrag(self.deck(table).header)
        mime = QMimeData()
        mime.setData(self._WISH_REORDER_MIME,
                     str(self._wishlists.index(table)).encode("ascii"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def _wish_header_drag_enter(self, e):
        """Accept only another wishlist header being dragged over."""
        if e.mimeData().hasFormat(self._WISH_REORDER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def _wish_header_drop(self, e, table: PlaylistTable):
        """Drop a dragged wishlist header onto this one → swap the two wishlists."""
        md = e.mimeData()
        if not md.hasFormat(self._WISH_REORDER_MIME):
            e.ignore()
            return
        try:
            src_idx = int(bytes(md.data(self._WISH_REORDER_MIME)).decode("ascii"))
        except ValueError:
            e.ignore()
            return
        if not (0 <= src_idx < len(self._wishlists)) or self._wishlists[src_idx] is table:
            e.ignore()
            return
        e.acceptProposedAction()
        self._swap_wishlists(self._wishlists[src_idx], table)

    def _swap_wishlists(self, a: PlaylistTable, b: PlaylistTable):
        """Exchange two wishlists' tracks and names — the user-visible effect of
        dragging one wishlist onto another to switch their positions."""
        a_entries = a._row_meta.entries()
        b_entries = b._row_meta.entries()
        a_name = self.deck(a).name
        b_name = self.deck(b).name
        a.load_wishlist(b_entries, a._play_cb, a._suggester)
        b.load_wishlist(a_entries, b._play_cb, b._suggester)
        a._m3u_path, b._m3u_path = b._m3u_path, a._m3u_path
        if a_name is not None and b_name is not None:
            self._set_deck_name(a, b_name)
            self._set_deck_name(b, a_name)
        self._update_wish_counts()
        self._autosave_playlist()
        self.statusBar().showMessage(i18n.t("⭐ Swapped %s ⇄ %s") % (a_name, b_name))

    def _wire_wishlist(self, table: PlaylistTable):
        """Lazily attach playback / similar-track drop support to a wishlist."""
        if table._suggester is not None:
            return
        sug = self._suggester or (PlaylistSuggester(self._lib) if self._lib else None)
        if sug is not None:
            table.load_wishlist([], play_cb=self._play_or_stop, suggester=sug)

    def _wish_label(self) -> str:
        """Cycle-button caption for the current wishlist state (count, or 2×2 at grid)."""
        if getattr(self, "_wish_grid", False):
            return "4 wishlists (2×2)"   # no ⭐: the button's icon paints it
        return self._WISH_LABELS[self._wish_state]

    def _rebuild_wish_layout(self):
        """Wire the wishlist splitter for the current shape: a single row of boxes, or
        — only with 4 wishlists and grid mode on — a 2×2 stack (wish 1/3 left, 2/4
        right, mirroring the deck grid). Reparents the 4 boxes between _wish_split and
        its two column splitters."""
        boxes = (self._wish_box, self._wish_box2, self._wish_box3, self._wish_box4)
        grid = bool(getattr(self, "_wish_grid", False)) and self._wish_state == 4
        for w in (*boxes, self._wish_col1, self._wish_col2):
            w.setParent(None)
        if grid:
            self._wish_col1.addWidget(self._wish_box)
            self._wish_col1.addWidget(self._wish_box3)
            self._wish_col2.addWidget(self._wish_box2)
            self._wish_col2.addWidget(self._wish_box4)
            self._wish_col1.setSizes([500, 500])
            self._wish_col2.setSizes([500, 500])
            self._wish_split.addWidget(self._wish_col1)
            self._wish_split.addWidget(self._wish_col2)
            self._wish_split.setSizes([500, 500])
        else:
            for b in boxes:
                self._wish_split.addWidget(b)
        self._wish_grid_active = grid

    def _wish_grid_on(self) -> bool:
        return bool(getattr(self, "_wish_grid_active", False))

    def _wish_col_pair(self, table) -> tuple:
        """The two wishlists sharing a column in 2×2 mode (left 1&3, right 2&4)."""
        if table in (self._wishlist, self._wishlist3):
            return (self._wishlist, self._wishlist3)
        return (self._wishlist2, self._wishlist4)

    def _wish_col_folded(self, table) -> bool:
        """True when every visible wishlist in this one's 2×2 column is folded."""
        vis = [t for t in self._wish_col_pair(table) if self._box_shown(t)]
        return bool(vis) and all(self.deck(t).folded for t in vis)

    def _wish_is_top(self, table) -> bool:
        """In 2×2 mode the upper wishlists (1, 2) are 'top'; a row reads all as top."""
        if self._wish_grid_on():
            return table in (self._wishlist, self._wishlist2)
        return True

    def _wish_is_left(self, table) -> bool:
        return table in (self._wishlist, self._wishlist3)

    def _wish_split_for(self, table):
        """The splitter a wishlist's box actually lives in (its column in 2×2 mode)."""
        if self._wish_grid_on():
            return (self._wish_col1 if table in (self._wishlist, self._wishlist3)
                    else self._wish_col2)
        return self._wish_split

    def _wish_fold_group(self, table) -> tuple:
        """The fold-neighbour group: the 2×2 column pair, else all wishlists in a row."""
        return self._wish_col_pair(table) if self._wish_grid_on() else tuple(self._wishlists)

    def _update_wish_area(self):
        """The wishlist area follows the cycle (_wish_state): 0 off · 1..4 show that many
        wishlists. State 0 hides it entirely (even with multiple decks); state 1 hides the
        single wishlist only in the ONE-deck view, where that deck should own the height
        (the old auto-reveal) — in the no-playlist view it shows, since that view exists so
        the wishlist / Eintanzen / library panes take over; states 2-4 always show that
        many. With 4 wishlists and _wish_grid on they stack 2×2 instead of in a row."""
        state = self._wish_state
        show_area = state >= 1 and (self._deck_count != 1 or state >= 2)
        self._wish_split.setVisible(show_area)
        boxes = (self._wish_box, self._wish_box2, self._wish_box3, self._wish_box4)
        for i, box in enumerate(boxes):
            box.setVisible(show_area and i < state)
        if show_area:
            for i, wl in enumerate(self._wishlists):
                if i < state:
                    self._wire_wishlist(wl)
            if self._wish_grid_on():
                # 2×2: two equal columns, each two equal rows.
                self._wish_split.setSizes([500, 500])
                self._wish_col1.setSizes([500, 500])
                self._wish_col2.setSizes([500, 500])
            else:
                # Replay the user's remembered drag for this wish-state if there is one;
                # otherwise fall back to the default ratio. Wishlists 1 & 2 are the primary
                # lists (std / lat) and get ~2.5× the width of the scratch lists 3 & 4 — Qt
                # scales these weights proportionally, so 2 shown is a clean 50:50, 3 is
                # ~42:42:17, and 4 is ~36:36:14:14. Hidden boxes get 0; folded wishlists are
                # re-clamped right after by _sync_wish_fold_constraints.
                remembered = self._wish_sizes.get(state)
                if remembered and len(remembered) == len(boxes):
                    sizes = [remembered[i] if i < state else 0 for i in range(len(boxes))]
                else:
                    weights = (1000, 1000, 400, 400)
                    sizes = [weights[i] if i < state else 0 for i in range(len(boxes))]
                self._wish_split.setSizes(sizes)
        # Which wishlists count as "all folded" depends on visibility.
        self._sync_wish_fold_constraints()

    def _on_wish_split_moved(self, *_):
        """User dragged a wishlist divider → remember this layout for the current
        wish-state so _update_wish_area replays it instead of the default ratio.
        (setSizes() doesn't re-emit splitterMoved, so our own resizes don't recurse.)
        The 2×2 grid keeps equal panes and isn't remembered here."""
        if self._wish_grid_on():
            return
        if self._wish_state >= 1:
            self._wish_sizes[self._wish_state] = self._wish_split.sizes()

    def _set_wish_state(self, state: int, grid: bool = False):
        """Apply a wishlist-area state (0 off · 1..4 wishlists; grid stacks 4 as 2×2):
        rewire the splitter shape, update the cycle button label, persist, and re-render.
        Single source of truth used by the cycle button and the restore path."""
        self._wish_state = state if state in (0, 1, 2, 3, 4) else 1
        self._wish_grid = bool(grid) and self._wish_state == 4
        self._dual_wish_btn.setProperty("countText", str(self._wish_state))
        self._set_toolbar_btn_text(self._dual_wish_btn, self._wish_label())
        self._settings["wish_state"] = self._wish_state
        self._settings["wish_grid"] = self._wish_grid
        save_settings(self._settings)
        self._rebuild_wish_layout()
        self._update_wish_area()

    def _cycle_wish_view(self, back: bool = False):
        """⭐ button: cycle off → 1 → 2 → 3 → 4 → 4 stacked 2×2 → off (the 'off' state
        disables wishlists completely, even with multiple decks). A right click
        (`back`) walks the same ring the other way."""
        if back:
            if self._wish_state == 4 and self._wish_grid:
                self._set_wish_state(4)
            elif self._wish_state == 0:
                self._set_wish_state(4, grid=True)
            else:
                self._set_wish_state(
                    {4: 3, 3: 2, 2: 1, 1: 0}.get(self._wish_state, 1))
        elif self._wish_state == 4 and not self._wish_grid:
            self._set_wish_state(4, grid=True)
        elif self._wish_state == 4 and self._wish_grid:
            self._set_wish_state(0)
        else:
            self._set_wish_state({0: 1, 1: 2, 2: 3, 3: 4}.get(self._wish_state, 1))
        if self._wish_grid:
            msg = "⭐ 4 wishlists stacked 2×2"
        else:
            msg = {0: "⭐ Wishlists disabled",
                   1: "⭐ Single wishlist",
                   2: "⭐ 2 wishlists shown",
                   3: "⭐ 3 wishlists shown",
                   4: "⭐ 4 wishlists shown"}[self._wish_state]
        self.statusBar().showMessage(msg)

    def _clean_wishlist_against_playlists(self, wishlist: PlaylistTable,
                                          announce: bool = True) -> int:
        """Remove from `wishlist` every track that's already in an open playlist deck —
        matched by full path OR content fingerprint (so renamed copies count too).
        ALLOW_REPEAT dances (PD) are kept: they may play again in another round,
        so the wishlist copy stays useful. Returns how many tracks were removed."""
        if wishlist is None or not getattr(wishlist, "_flat_mode", False):
            return 0
        paths, fps = self._deck_dedup_index()
        # hashed on demand
        fingerprint = self._cache.fingerprint if self._cache is not None else None
        rows = []
        if paths or fps:
            for r, m in wishlist._row_meta.numbered():
                e = m.entry
                if (getattr(e, "dance", None) or "") in ALLOW_REPEAT:
                    continue
                if is_planned(getattr(e, "path", None), paths, fps, fingerprint):
                    rows.append(r)
        n = len(rows)
        if n:
            wishlist._remove_rows(rows)
            if announce:
                _show_toast(self, i18n.t("🧹  Removed %d track(s) already in a playlist") % n)
        elif announce:
            _show_toast(self, "✅  No wishlist tracks are in an open playlist")
        return n

    def _update_wish_counts(self):
        """Refresh the title-count badge under each wishlist (total · fresh).
        Piggybacks the deck Σ-total badges — both refresh on the same events."""
        self._update_deck_totals()
        for d in self._deck_of.values():
            lbl = d.count_lbl
            if lbl is None:
                continue
            entries = d.table.wishlist_entries()
            n = len(entries)
            if not n:
                lbl.setText(i18n.t("🎵 0 titles"))
                continue
            fresh = sum(1 for e in entries if not getattr(e, "popularity", 0))
            # Translated BEFORE the count goes in: an f-string exists at no
            # call site, so the catalog — keyed by the English string — could
            # never reach it and the bar stayed English in German mode.
            txt = i18n.t("🎵 %d title" if n == 1 else "🎵 %d titles") % n
            if fresh:
                txt += i18n.t("  ·  ✦ %d new") % fresh
            lbl.setText(txt)

    def current_wishlist_paths(self) -> set:
        """Set of file paths currently in any wishlist (for wishlist-scoped search)."""
        paths = set()
        for wl in getattr(self, "_wishlists", []):
            for e in wl.wishlist_entries():
                if e is not None and e.path:
                    paths.add(str(e.path))
        return paths
