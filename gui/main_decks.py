"""Deck layout, folding, tabs, inline rename and wishlist wiring.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import logging

import re
from pathlib import Path
from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from planner.config import player_build
from planner.m3u import grid_from_running_order
from planner.terms import dance_name
from planner.planned import is_planned
from planner.suggester import PlaylistSuggester
from gui.common import (
    DANCE_SHORT,
    _fmt_track_secs,
    reveal_in_explorer,
)
from gui.deck import Deck, DeckContext
from gui.dialogs import (  # auto-resolved
    app_mode_of,
    warmup_name,
)
from shared.stores import (
    save_settings,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.session_env import ALL_DECK_KEYS, WISH_KEYS
from planner import i18n
from planner.warmup import _WARMUP_ORDER, warmup_code
from gui.main_fold import FoldMixin
from gui.main_wish import WishlistMixin

log = logging.getLogger("dancesport.gui.decks")


def dance_counts_line(entries) -> str:
    """Songs per dance in running order — "LW 3 · TG 3 · DF 2 · other 1".
    Social dances go by their short code; a track of no known dance counts as
    "other"."""
    counts: dict = {}
    for e in entries:
        code = warmup_code(e)
        counts[code] = counts.get(code, 0) + 1
    order = sorted(counts, key=lambda c: (c is None, _WARMUP_ORDER.get(c, 99), c or ""))
    return " · ".join(
        f"{i18n.t('other') if c is None else DANCE_SHORT.get(c, c)}"
        f" {counts[c]}" for c in order)


class _TotalBadge(QLabel):
    """The Σ badge under a playlist; a click opens / closes its per-dance line."""
    clicked = Signal()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            ev.accept()
            return
        super().mousePressEvent(ev)


class DeckLayoutMixin(FoldMixin, WishlistMixin):
    """The decks themselves: their boxes, tabs, names, modes and totals, and the
    🎼 library pane that sits under them.

    What grew around them lives next door still: 📐 folding (gui.main_fold) and
    ⭐ the wishlists (gui.main_wish). MainWindow keeps importing this one name.
    """

    def deck(self, table: PlaylistTable) -> Deck:
        """Everything this window keeps about `table`, made on first ask.

        Decks come into existence as their box is built, and the wishlists and
        the Eintanzen panel are asked about before that — hence on first ask
        rather than up front."""
        d = self._deck_of.get(table)
        if d is None:
            d = self._deck_of[table] = Deck(table)
        return d

    def _deck_header_text(self, table: PlaylistTable, active: bool) -> str:
        """Header label: fixed 🅰/🅱/🅲/🅳 deck badge + ● focus dot + (renamed) title.
        Wishlists carry no letter."""
        name = self.deck(table).name
        letter = self.deck(table).letter
        if self.deck(table).folded:
            # Folded to a tab: in a sideways-collapsed strip only the fixed badge
            # fits (the strip is width-clamped to the header's size hint), but a
            # full-width tab has room — keep the title there.
            if self._folded_tab_is_sideways(table):
                return letter or name[:1]
            return (letter + "  " + name) if letter else name
        dot = "●  " if active else ""
        if not letter:
            return dot + name
        return letter + "  " + dot + name

    def _is_deck(self, table: PlaylistTable) -> bool:
        """True for any full playlist deck — the normal decks A–H AND the 📅 day
        decks (wishlists and the Eintanzen panel are not decks)."""
        return table in self._decks or table in self._day_decks

    # ── Deck grid geometry (2×2 grids: A/C·B/D on tab 1, E/G·F/H on tab 2, and
    #    two more of 📅 day decks on the Tournament-day tab's sub-tabs) ──
    def _deck_columns(self):
        """Every deck column as (column_splitter, (top_deck, bottom_deck), grid_splitter).
        All grids are listed; callers scope to what's visible via `_box_shown`."""
        d = self._day_decks
        return (
            (self._decks_col1, (self._tableA, self._tableC), self._decks_split),
            (self._decks_col2, (self._tableB, self._tableD), self._decks_split),
            (self._decks_col3, (self._tableE, self._tableG), self._decks_split2),
            (self._decks_col4, (self._tableF, self._tableH), self._decks_split2),
            (self._day_col1, (d[0], d[2]), self._day_split),
            (self._day_col2, (d[1], d[3]), self._day_split),
            (self._day_col3, (d[4], d[6]), self._day_split2),
            (self._day_col4, (d[5], d[7]), self._day_split2),
        )

    def _deck_col_pair(self, table: PlaylistTable):
        """The (top, bottom) deck pair sharing `table`'s column."""
        for _col, pair, _grid in self._deck_columns():
            if table in pair:
                return pair
        return (self._tableA, self._tableC)

    def _deck_col_split(self, table: PlaylistTable):
        """The vertical column splitter holding `table`."""
        for col, pair, _grid in self._deck_columns():
            if table in pair:
                return col
        return self._decks_col1

    def _deck_is_top(self, table: PlaylistTable) -> bool:
        """True for the upper deck of its column (folds up / expands down).
        Pure identity check — safe to call before the column splitters exist."""
        d = self._day_decks
        return table in (self._tableA, self._tableB, self._tableE, self._tableF,
                         d[0], d[1], d[4], d[5])

    def _deck_is_left(self, table: PlaylistTable) -> bool:
        """True for the left column of its grid (sideways tab expands right ▸)."""
        d = self._day_decks
        return table in (self._tableA, self._tableC, self._tableE, self._tableG,
                         d[0], d[2], d[4], d[6])

    def _deck_tab_index(self, table: PlaylistTable) -> int:
        """Which top-level tab page (0 = Group A–D, 1 = Group E–H,
        2 = 📅 Tournament day) holds this deck."""
        if table in self._day_decks:
            return 2
        return 1 if table in (self._tableE, self._tableF,
                              self._tableG, self._tableH) else 0

    def _day_tab_index(self, table: PlaylistTable) -> int:
        """Which 📅 sub-tab (0 = Group A–D, 1 = Group E–H) holds this day deck."""
        return 1 if table in self._day_decks[4:] else 0

    def _day_plan_active(self) -> bool:
        """True while any 📅 day deck holds tracks — drives the visibility of the
        Tournament-day tab (its decks are only ever filled by the day planner)."""
        return any(t.rowCount() > 0 for t in self._day_decks)

    def _set_day_tab_title(self, title: str):
        """Label the 📅 top-level tab: the competition/event name when the user
        renamed it (persisted in the autosave env), the generic default otherwise."""
        self._day_tab_title = (title or "").strip()
        self._deck_tabs.setTabText(
            2, f"📅 {self._day_tab_title}" if self._day_tab_title
            else "📅 Tournament day")

    def _rename_day_tab(self):
        """Double-click on the 📅 tab: rename it to the competition name,
        e.g. "DanceComp 2026" (empty input restores the default label)."""
        title, ok = QInputDialog.getText(
            self, "Rename tournament day",
            "Competition name (empty = default):",
            text=getattr(self, "_day_tab_title", ""))
        if not ok:
            return
        self._set_day_tab_title(title)
        self._autosave_playlist()

    def _close_day_plan(self):
        """✕ on the 📅 tab: clear every day deck and retire the whole tab view
        (confirmed first while any day deck still holds tracks)."""
        filled = [t for t in self._day_decks if t.rowCount() > 0]
        if filled:
            n = len(filled)
            ans = QMessageBox.question(
                self, "Close tournament day",
                (i18n.t("Close the tournament-day view? This clears %d day playlist.")
                 if n == 1 else
                 i18n.t("Close the tournament-day view? This clears %d day playlists."))
                % n,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        for t in self._day_decks:
            self._blank_deck(t)
        self._set_day_tab_title("")
        self._day_tab_keep = False
        self._apply_deck_view()
        self._autosave_playlist()
        self.statusBar().showMessage("📅 Tournament day closed.")

    def _clear_day_plan(self):
        """🧹 on the 📅 tab: empty every day playlist (confirmed first). The tab
        stays open with its name kept — only ✕ Close retires it."""
        filled = [t for t in self._day_decks if t.rowCount() > 0]
        if not filled:
            return
        n = len(filled)
        ans = QMessageBox.question(
            self, "Clear tournament day",
            (i18n.t("Clear the %d day playlist?") if n == 1
             else i18n.t("Clear all %d day playlists?")) % n,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        for t in self._day_decks:
            self._blank_deck(t)
        self._day_tab_keep = True
        self._apply_deck_view()
        self._autosave_playlist()
        self.statusBar().showMessage("🧹 Tournament-day playlists cleared.")

    def _group_tab_menu(self, page: int, global_pos):
        """Right-click on a Group A–D / E–H tab: save that page's decks as .m3u
        files, or clear them."""
        decks = [t for t in self._decks if self._deck_tab_index(t) == page]
        filled = any(t.rowCount() > 0 for t in decks)
        menu = QMenu(self)
        save = menu.addAction("💾  Save all playlists as M3U")
        save.setEnabled(filled)
        clear = menu.addAction("🧹  Clear all playlists")
        clear.setEnabled(filled)
        menu.addSeparator()
        new_day = self._add_new_day_action(menu)
        act = menu.exec(global_pos)
        if act is save:
            self._save_all_playlists(decks=decks)
        elif act is clear:
            self._clear_group_tab(page)
        elif act is new_day:
            self._new_day_tab()

    def _add_new_day_action(self, menu: QMenu):
        """📅 New tournament day… — greyed out while the one 📅 tab is shown."""
        act = menu.addAction("📅  New tournament day…")
        act.setEnabled(not self._deck_tabs.isTabVisible(2))
        return act

    def _tab_strip_menu(self, global_pos):
        """Right-click on the tab strip beside the tabs: open a 📅 tab."""
        menu = QMenu(self)
        new_day = self._add_new_day_action(menu)
        if menu.exec(global_pos) is new_day:
            self._new_day_tab()

    def _new_day_tab(self):
        """Open the 📅 tab empty under a competition name typed by hand, for a
        day put together without the day planner. It stays open like after
        🧹 Clear until ✕ retires it."""
        title, ok = QInputDialog.getText(
            self, "New tournament day", "Competition name:")
        if not ok or not title.strip():
            return
        self._set_day_tab_title(title)
        self._day_tab_keep = True
        self._apply_deck_view()
        self._deck_tabs.setCurrentIndex(2)
        self._autosave_playlist()

    def _clear_group_tab(self, page: int):
        """Empty every deck on one Group tab page (confirmed first) — the other
        page, the 📅 day decks and the wishlists stay untouched."""
        decks = [t for t in self._decks if self._deck_tab_index(t) == page]
        filled = [t for t in decks if t.rowCount() > 0]
        if not filled:
            return
        n = len(filled)
        ans = QMessageBox.question(
            self, "Clear playlists",
            (i18n.t("Clear the %d playlist on “%s”?") if n == 1
             else i18n.t("Clear all %d playlists on “%s”?"))
            % (n, self._deck_tabs.tabText(page)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        for t in filled:
            self._blank_deck(t)
        self._autosave_playlist()
        self.statusBar().showMessage(
            i18n.t("🧹 %s playlists cleared.") % self._deck_tabs.tabText(page))

    def _day_tab_menu(self, global_pos):
        """Right-click on the 📅 tab: save every competition as its own M3U
        (and file them in 🏆 Tournaments), or reach the clear / rename / close
        actions without the ✕ / double-click gestures."""
        menu = QMenu(self)
        save = menu.addAction("💾  Save all competition M3Us")
        save.setEnabled(self._day_plan_active())
        file_in = menu.addAction("🏆  Save all and add to Tournaments")
        file_in.setEnabled(self._day_plan_active())
        clear = menu.addAction("🧹  Clear all playlists")
        clear.setEnabled(self._day_plan_active())
        rename = menu.addAction("✏️  Rename tab…")
        close = menu.addAction("✕  Close tournament day")
        act = menu.exec(global_pos)
        if act is save:
            self._save_day_plan_m3us()
        elif act is file_in:
            self._save_day_plan_m3us(file_in_tree=True)
        elif act is clear:
            self._clear_day_plan()
        elif act is rename:
            self._rename_day_tab()
        elif act is close:
            self._close_day_plan()

    def _ensure_deck_tab_visible(self, table: PlaylistTable):
        """Bring the tab page holding `table` to the front (whenever that tab is
        shown — 8-deck mode or an active 📅 day plan; day decks also front
        their sub-tab)."""
        if self._is_deck(table):
            idx = self._deck_tab_index(table)
            if self._deck_tabs.isTabVisible(idx):
                self._deck_tabs.setCurrentIndex(idx)
                if table in self._day_decks:
                    self._day_tabs.setCurrentIndex(self._day_tab_index(table))

    def _on_deck_tab_changed(self, index: int):
        """Focus the first open deck on the page the user switched to, so
        Generate / Save / ↺ target a deck you can actually see."""
        if getattr(self, "_restoring", False):
            return
        if index == 2:
            self._on_day_tab_changed(self._day_tabs.currentIndex())
            return
        for t in self._decks:
            if self._deck_tab_index(t) == index and not self.deck(t).folded:
                self._set_active_table(t)
                break

    def _on_day_tab_changed(self, index: int):
        """Focus the first open 📅 day deck on the sub-tab the user switched to."""
        if getattr(self, "_restoring", False):
            return
        decks = self._day_decks[:4] if index == 0 else self._day_decks[4:]
        for t in decks:
            if not self.deck(t).folded:
                self._set_active_table(t)
                break

    def _make_deck_box(self, table: PlaylistTable, title: str) -> QWidget:
        """A titled container (header label + table) used for each deck/wishlist.
        Click the header to focus the deck; double-click it to rename."""
        box = QWidget()
        self.deck(table).box = box
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        hdr = QLabel()
        hdr.setStyleSheet(self._DECK_HDR_IDLE)
        hdr.setToolTip("Click to focus · right-click or double-click to rename")
        hdr.mouseDoubleClickEvent = lambda _e, t=table: self._begin_inline_rename(t)
        if table in self._wishlists:
            # Wishlist headers can be dragged onto one another to swap the two
            # wishlists' position (their tracks + name trade places). Works in the
            # 2-up row and the 2×2 grid alike, since it just swaps content.
            hdr.setAcceptDrops(True)
            hdr.mousePressEvent = lambda e, t=table: self._wish_header_press(e, t)
            hdr.mouseMoveEvent = lambda e, t=table: self._wish_header_move(e, t)
            hdr.dragEnterEvent = self._wish_header_drag_enter
            hdr.dragMoveEvent = self._wish_header_drag_enter
            hdr.dropEvent = lambda e, t=table: self._wish_header_drop(e, t)
        else:
            hdr.mousePressEvent = lambda e, t=table: self._on_header_press(e, t)
        self.deck(table).header        = hdr
        self.deck(table).name          = title
        self.deck(table).default_name  = title
        hdr.setText(self._deck_header_text(table, False))
        # Per-deck mode button, cycling 🔒 static → 🔓 dynamic → ✋ free order
        # (decks only; the flat wishlist has none).
        hb = QHBoxLayout()
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(3)
        if self._is_deck(table):
            # Parented to the box straight away: _refresh_mode_btn below calls
            # setVisible(), and on a widget that has no parent yet that means
            # "show a top-level WINDOW" — sixteen 44×19 windows flashing across
            # the desktop before the loading splash even appears.
            mode_btn = QToolButton(box)
            mode_btn.setText("🔒")
            mode_btn.setAutoRaise(True)
            mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            mode_btn.clicked.connect(lambda _=False, t=table: self._cycle_deck_mode(t))
            self.deck(table).mode_btn = mode_btn
            self._refresh_mode_btn(table)   # glyph + tooltip for the current mode
            hb.addWidget(mode_btn)
        # Fold-to-tab toggle (decks AND wishlists): collapse to the header strip so
        # the other open playlists dynamically get the space. The stand-alone warm-up
        # panel has no fold (it's a single full-width list).
        hb.addWidget(hdr, stretch=1)
        if self._is_deck(table) or table in self._wishlists:
            fold_btn = QToolButton()
            fold_btn.setAutoRaise(True)
            fold_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            fold_btn.clicked.connect(lambda _=False, t=table: self._toggle_deck_fold(t))
            self.deck(table).fold_btn = fold_btn
            self._refresh_fold_btn(table)   # arrow + tooltip for the open state
            hb.addWidget(fold_btn)
        # The stand-alone warm-up (Eintanzen) panel gets a compact toggle (fold to a
        # header tab), the twin of the decks' fold. Showing / hiding it entirely is
        # the 🤸 Eintanzen toolbar toggle (mirrors the ⭐ wishlist toggle).
        if table is self._warmup_table:
            # 🔀 only on the ETDS party list: the same titles in a fresh order.
            self._warmup_shuffle_btn = QToolButton()
            self._warmup_shuffle_btn.setText("🔀")
            self._warmup_shuffle_btn.setAutoRaise(True)
            self._warmup_shuffle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._warmup_shuffle_btn.setToolTip(
                "Shuffle — put the same titles in a fresh order,\n"
                "as if the party list were built again from scratch.")
            self._warmup_shuffle_btn.clicked.connect(
                lambda _=False: self._shuffle_warmup())
            hb.addWidget(self._warmup_shuffle_btn)
            # 🩺 the rules the list was built from, read back off the list as
            # it now stands — it gets edited after the build, and nothing else
            # re-checks it. A check-up, not a tick: ✓ read as "this list is
            # fine" when the button is what goes looking.
            self._warmup_check_btn = QToolButton()
            self._warmup_check_btn.setText("🩺")
            self._warmup_check_btn.setAutoRaise(True)
            self._warmup_check_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._warmup_check_btn.setToolTip(
                "Check the party list — rounds, the late WW / PD rules,\n"
                "duplicates, takt and over-long titles.")
            self._warmup_check_btn.clicked.connect(
                lambda _=False: self._check_party_list())
            hb.addWidget(self._warmup_check_btn)
            # Connected after the window's own cleared handler, so it sees the
            # list already wiped.
            table.loaded.connect(self._sync_warmup_shuffle_btn)
            table.cleared.connect(self._sync_warmup_shuffle_btn)
            self._sync_warmup_shuffle_btn()
            self._warmup_fold_btn = QToolButton()
            self._warmup_fold_btn.setText("▾")
            self._warmup_fold_btn.setAutoRaise(True)
            self._warmup_fold_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._warmup_fold_btn.setToolTip(
                i18n.t("Compact the %s panel to its header tab —\n"
                       "click the tab (or this arrow) to open it again.")
                % self._warmup_default_name())
            self._warmup_fold_btn.clicked.connect(
                lambda _=False: self._toggle_warmup_fold())
            hb.addWidget(self._warmup_fold_btn)
        v.addLayout(hb)
        v.addWidget(table, stretch=1)
        # The bar under the table: the song counter filling it, the ⏭/✋
        # auto-advance switch on the right. The switch used to float in the
        # table's own bottom-right corner, where it covered the last rows and
        # ended up across the middle of the list once the rows scrolled under
        # it; down here it is next to the count and covers nothing.
        badge = None
        # Σ total play time badge below each deck (the whole playlist) — the
        # Eintanzen / party panel is a playlist too, so it gets one as well.
        if self._is_deck(table) or table is self._warmup_table:
            tot = _TotalBadge("")
            tot.setStyleSheet(
                "color:#2c4a73; background:#eef3fb; border:1px solid #c9d6ea; "
                "border-radius:4px; padding:2px 6px; font-size:11px;")
            tot.setToolTip("Total play time of this playlist\n"
                           "(↳ backup rows not counted — they only play as stand-ins)\n"
                           "Click ▸ for the songs per dance")
            tot.setCursor(Qt.CursorShape.PointingHandCursor)
            tot.clicked.connect(self._toggle_totals_by_dance)
            tot.setVisible(False)
            self.deck(table).total_lbl = tot
            badge = tot
        # Title-count badge below each wishlist (like the "✦new" fresh indicator).
        if table in self._wishlists:
            cnt = QLabel("")
            cnt.setStyleSheet(
                "color:#7a5b00; background:#fff8e6; border:1px solid #e6d28a; "
                "border-radius:4px; padding:2px 6px; font-size:11px;")
            cnt.setToolTip("Number of titles in this wishlist")
            self.deck(table).count_lbl = cnt
            badge = cnt
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        # The badge takes the width instead of a spacer, so its highlight runs
        # the length of the bar the way it did before the switch moved down
        # here — no stripe of bare background between the count and the switch.
        if badge is not None:
            rl.addWidget(badge, 1)
        # No alignment flag, so the switch is given the whole height of the bar
        # and grows with it: opened to its per-dance line the Σ badge is two
        # rows tall, and a one-row switch pinned to the top of it read as a
        # button dropped beside a badge rather than the other half of one strip.
        # The width is still its own — the badge above takes the stretch.
        switch = table.advance_toggle()
        switch.setSizePolicy(QSizePolicy.Policy.Fixed,
                             QSizePolicy.Policy.Ignored)
        rl.addWidget(switch, 0)
        self.deck(table).badge_row = row
        v.addWidget(row)
        # Zero-stretch spacer: invisible while the table is shown, but when the
        # playlist is folded it soaks up any leftover height so the header tab
        # stays pinned to the TOP of the box instead of floating centered.
        v.addStretch(0)
        return box

    def _set_deck_name(self, table: PlaylistTable, name: str):
        """Set a deck/wishlist header title and refresh its label (keeps focus mark)."""
        name = (name or "").strip()
        if not name:
            return
        # Strip any legacy leading deck emoji (🅰/🅱/3️⃣/4️⃣) from old autosaves so the
        # fixed A/B/C/D badge isn't doubled up.
        if self.deck(table).letter:
            name = re.sub(r"^(?:🅰|🅱|🅲|🅳|3️⃣|4️⃣)️?\s*", "", name).strip() or name
        self.deck(table).name = name
        hdr = self.deck(table).header
        if hdr is not None:
            active = self.deck(table).active
            hdr.setText(self._deck_header_text(table, active))
        # The title is part of the saved session. Generate/Import set it AFTER the
        # content autosave already ran, so persist it here too (skipped mid-restore).
        if not getattr(self, "_restoring", False):
            self._autosave_playlist()

    def _warmup_default_name(self) -> str:
        """What an unnamed 🤸 panel is called here — see gui.dialogs.warmup_name."""
        return warmup_name(app_mode_of(self._settings))

    def _warmup_title(self, label: str) -> str:
        """Eintanzen panel title with its 🤸 logo pinned in front of the name
        (and never doubled up if the label already carries one)."""
        label = (label or self._warmup_default_name()).strip()
        while label.startswith(self._WARMUP_LOGO):
            label = label[len(self._WARMUP_LOGO):].strip()
        return f"{self._WARMUP_LOGO}  {label}" if label else self._WARMUP_LOGO

    def _favorites_deck_name(self, age: str, cls: str, style: str) -> str:
        """Deck title for a Favorites playlist — the export name without the date."""
        parts = [p for p in (age, cls, style) if p]
        return " · ".join(parts) if parts else "Playlist"

    # ── Dynamic mode (per-deck drag-to-build) ───────────────────────────────────
    def _current_capacity(self) -> list[int]:
        """Per-round heat capacity from the '6-3-2-1' Rounds field (default 6-3-2-1)."""
        raw = self._cfg.rounds_edit.text().strip()
        try:
            caps = [int(p) for p in re.split(r"[-,\s]+", raw) if p]
        except ValueError:
            caps = []
        caps = [c for c in caps if c > 0]
        return caps or [6, 3, 2, 1]

    # The three ways a deck can take a drag, in the order the button cycles them.
    _DECK_MODES = ("static", "dynamic", "free")
    _DECK_MODE_GLYPH = {"static": "🔒", "dynamic": "🔓", "free": "✋"}
    _DECK_MODE_TIP = {
        "static": ("Static deck — drops replace a single slot.\n"
                   "Click to switch to Dynamic: drag songs in to\n"
                   "build rounds & heats automatically."),
        "dynamic": ("Dynamic deck — drag songs in to build rounds & heats.\n"
                    "Click to switch to Free order: one running order,\n"
                    "every row draggable anywhere (like the party list)."),
        "free": ("Free order — one running order, drag any row anywhere\n"
                 "and a dropped song lands where you drop it.\n"
                 "Click to go back to a planned Static grid."),
    }
    _DECK_MODE_MSG = {
        "static": "🔒 Static mode — a drop now replaces a single slot",
        "dynamic": ("🔓 Dynamic mode — drag songs from the wishlist or another "
                    "deck to build rounds & heats"),
        "free": ("✋ Free order — every row can be dragged anywhere, and a "
                 "dropped song lands where you drop it"),
    }

    def _deck_own_mode(self, table: PlaylistTable) -> str:
        """The mode the deck itself is in, ignoring what the install implies.

        This is the one that gets SAVED: a deck that is only free because nobody
        plans here must not come back free in an install that does."""
        if getattr(table, "_player_list", False):
            return "free"
        return "dynamic" if table._dynamic else "static"

    def _deck_mode(self, table: PlaylistTable) -> str:
        """Which of the three drag modes a deck is in right now.

        A player-only install plans nothing, so its decks are the free running
        order from the start — an empty one included, before it has been handed
        a single track (`plays_flat`)."""
        if table.plays_flat():
            return "free"
        return self._deck_own_mode(table)

    def _cycle_deck_mode(self, table: PlaylistTable):
        """The mode button: static → dynamic → free order → static again."""
        cur = self._deck_mode(table)
        nxt = self._DECK_MODES[(self._DECK_MODES.index(cur) + 1) % len(self._DECK_MODES)]
        self._set_deck_mode(table, nxt)

    def _set_deck_mode(self, table: PlaylistTable, mode: str):
        """Put one deck into 'static', 'dynamic' or 'free' mode.

        Static ⇄ dynamic keep the grid as it is. Free order throws it away for a
        flat running order — the way back builds a fresh grid out of that list
        (see `_regrid_deck`), which is what makes the third state a state and not
        a one-way door."""
        if not self._is_deck(table) or mode not in self._DECK_MODES:
            return
        cur = self._deck_mode(table)
        if cur == mode:
            self._refresh_mode_btn(table)
            return
        extra = ""
        if mode == "free":
            table.become_player_list()
        elif cur == "free":
            unknown = self._regrid_deck(table, dynamic=(mode == "dynamic"))
            if unknown is None:
                self._refresh_mode_btn(table)
                return
            if unknown:
                extra = (i18n.t(" — %d track(s) of no known dance left out")
                         % unknown)
        elif mode == "dynamic":
            table._enter_dynamic(self._current_capacity())
        else:
            table._dynamic = False
        self._refresh_mode_btn(table)
        self._autosave_playlist()
        self.statusBar().showMessage(i18n.t(self._DECK_MODE_MSG[mode]) + extra)

    def _restore_deck_modes(self, modes: dict):
        """Put the decks that came back EMPTY into the mode they were left in.

        A deck with tracks restores its mode along with them (the saved state
        says `player_list` or `dynamic`); an empty one has no saved state at
        all, so its 🔒/🔓/✋ toggle needs replaying by hand. Only empty decks,
        which is also what keeps this off `_set_deck_mode`: the trip back from
        free order re-builds a grid and can ask a question, and startup is no
        place for either.

        A player-only install replays NOTHING: nobody plans there, `_deck_mode`
        already calls every deck free, and putting one back into dynamic would
        leave it contradicting that — free on the button, dynamic underneath,
        with no toggle on screen to get out of it again. The saved mode is left
        in the file for the install that does plan; an empty deck's dynamic flag
        is not worth carrying, which is why `_blank_deck` drops it too."""
        player_only = app_mode_of(self._settings) == "player"
        for key, table in zip(ALL_DECK_KEYS, self._decks + self._day_decks):
            mode = modes.get(key)
            if mode not in self._DECK_MODES or table._row_meta or player_only:
                continue
            if mode == "free":
                table.become_player_list()
            elif mode == "dynamic":
                table._enter_dynamic(self._current_capacity())
            self._refresh_mode_btn(table)

    def _restore_list_play(self, list_play: dict, legacy_advance: dict):
        """Give every list back the play values it was left with.

        `list_play` holds each list's whole set; a file written before that
        only knew a ⏭/✋ answer per list (`deck_advance`), which seeds the list
        the usual way and then takes that answer. A list in neither keeps
        nothing, so it is seeded on first use like a fresh one."""
        for key, table in zip(ALL_DECK_KEYS + WISH_KEYS + ("warmup",),
                              self._decks + self._day_decks
                              + self._wishlists + [self._warmup_table]):
            if isinstance(list_play.get(key), dict):
                table._play_vals = None
                self._list_vals(table).update(list_play[key])
            elif key in legacy_advance:
                self._list_vals(table)["advance"] = bool(legacy_advance[key])
            else:
                continue
            table.refresh_advance_toggle()
        # The panel shows its list — show that list's restored values.
        panel_list = self._panel_list()
        if panel_list is not None and panel_list._play_vals is not None:
            self._panel_table = None
            self._bind_panel(panel_list)

    def _regrid_deck(self, table: PlaylistTable, dynamic: bool) -> int | None:
        """Read a deck's free running order back into a round/heat grid.

        Free mode holds no grid at all (the flat load drops it), so the way back
        is to work one out of the list AS IT STANDS — including whatever was
        dragged around while it was free. The rounds its ─── strips are headed
        with become the rounds of the grid, so what comes back is what was on
        screen. Returns how many tracks had no detectable dance (they have no
        column to sit in and are left out), or None when nothing danceable is
        left at all — the deck then stays free rather than going blank."""
        entries = table._row_meta.entries()
        # The rounds as the STRIPS read them, not the raw map behind them: a song
        # dropped in while the list was free belongs to no round of its own and
        # is shown inside the one it landed in — that is where it goes back, too.
        # With no rounds known at all the strips name DANCES, which would cut a
        # round per dance: leave the rounds to the import heuristic instead.
        labels = (table._player_section_labels(entries)
                  if getattr(table, "_player_sections", None) else None)
        res = grid_from_running_order(entries, labels)
        if not res["playlist"] or not res["dances"]:
            QMessageBox.information(
                self, "Free order",
                "None of these tracks says which dance it is, so there is no "
                "grid to build from them — the list stays a free running order.")
            return None
        # A grid has a column per dance and nowhere else to put a track, so
        # everything it cannot place falls out of the deck. That is a deletion,
        # and a deletion gets ASKED for — the old status-bar line said it after
        # the fact and scrolled away, which is how a list comes back short and
        # nobody knows why. Counted off the grid, so a track lost for any other
        # reason is in the number too.
        lost = len(entries) - int(res["total"])
        if lost > 0:
            go = QMessageBox.question(
                self, "Free order",
                i18n.t("%d of these %d tracks say nothing about which "
                       "dance they are. A grid has no column to put them in, so "
                       "building one leaves them out of the deck.\n\n"
                       "Build the grid without them?") % (lost, len(entries)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if go != QMessageBox.StandardButton.Yes:
                log.info("🧩 Grid declined — the list stays free\n"
                         "deck: %s\n"
                         "would have lost: %s", self.deck(table).name, lost)
                return None
        latin = {'CC', 'SA', 'RB', 'PD', 'JI'}
        dances = res["dances"]
        style = ("Latin" if sum(d in latin for d in dances) >= len(dances) / 2
                 else "Standard")
        log.info("🧩 Running order re-built as a grid\n"
                 "deck: %s\n"
                 "rounds: %s\n"
                 "dropped: %s", self.deck(table).name,
                 len(res["rounds"]), lost)
        table.load(
            res["playlist"], dances, res["rounds"],
            table._dance_class or "S",
            play_cb=table._play_cb,
            suggester=table._suggester,
            use_timbre=bool(table._use_timbre),
            style=style,
            dynamic=dynamic,
            capacity=[int(getattr(r, "heats", 0) or 0) for r in res["rounds"]],
            backups=res["backups"],
        )
        return lost

    def _toggle_deck_dynamic(self, table: PlaylistTable, on: bool):
        """Flip one deck between static and dynamic mode (keeps its current grid)."""
        self._set_deck_mode(table, "dynamic" if on else "static")

    def _refresh_mode_btn(self, table: PlaylistTable):
        """Sync a deck's mode button to its current mode."""
        btn = self.deck(table).mode_btn
        if btn is None:
            return
        # A player-only install never plans a round, so there is nothing to
        # choose between: its decks always take a drop as an addition. Folding
        # is checked here too, so this stays the ONE place that decides whether
        # the button shows — an unfold that set it visible by itself brought the
        # toggle back in an install that hides it.
        btn.setVisible(not table.player_only() and not self.deck(table).folded)
        mode = self._deck_mode(table)
        btn.setText(self._DECK_MODE_GLYPH[mode])
        btn.setToolTip(self._DECK_MODE_TIP[mode])

    def _warmup_has_content(self) -> bool:
        """True when the Eintanzen panel holds a warm-up list (something to show)."""
        t = self._warmup_table
        return bool(getattr(t, "_warmup", False) and t._row_meta)

    def _decks_to_player_lists(self) -> int:
        """Re-render every deck that still shows a planned grid as the running
        order it has to be in a player-only install. Returns how many changed.

        Switching the app mode needs no restart, so a draw planned a moment ago
        is still on screen — with its slots, where a title can only be moved into
        another slot of its own dance. Nobody is planning any more, so the same
        songs, in the same order, become one list that can be dragged freely."""
        changed = 0
        for t in self._decks + self._day_decks:
            if t.plays_flat() and not t._player_list and t._row_meta:
                t.become_player_list()
                changed += 1
        if changed:
            log.info("🎧 Decks re-rendered as running orders\n"
                     "decks: %s", changed)
            self._autosave_playlist()
        return changed

    def _ensure_empty_warmup(self):
        """Arm the Eintanzen panel as an empty warm-up list so it can be shown and
        accept a dropped Eintanzen .m3u even when nothing was generated yet."""
        if self._warmup_has_content():
            return
        label = self._warmup_title(self._warmup_default_name())
        self._warmup_table.load_warmup(
            [], label, style="", dance_class="S", relax=True,
            play_cb=self._play_or_stop,
            suggester=PlaylistSuggester(self._lib) if self._lib else None,
        )
        self._set_deck_name(self._warmup_table, label)

    def _on_warmup_toggle(self, on: bool):
        """🤸 Eintanzen toolbar toggle: show / hide the warm-up panel. When nothing
        was built yet, opening arms an empty panel ready to receive a dropped
        Eintanzen .m3u (mirror of the ⭐ wishlist toggle)."""
        if on:
            self._ensure_empty_warmup()
        self._warmup_closed = not on
        self._warmup_box.setVisible(on)
        if not on and self._focused_table is self._warmup_table:
            self._set_active_table(self._tableA)
        self._autosave_playlist()
        name = self._warmup_default_name()
        if on:
            self.statusBar().showMessage(
                i18n.t("🤸 %s panel shown — drop an .m3u here "
                       "or build one with 🤸 %s.") % (name, name))
        else:
            self.statusBar().showMessage(i18n.t("🤸 %s panel hidden") % name)

    def _sync_warmup_toggle(self):
        """Reconcile the 🤸 Eintanzen toolbar toggle with the panel's state: always
        clickable (opens an empty panel on demand), checked when it's shown."""
        btn = getattr(self, "_warmup_toggle_btn", None)
        if btn is None:
            return
        btn.setEnabled(True)
        btn.blockSignals(True)
        btn.setChecked(self._warmup_has_content() and not self._warmup_closed)
        btn.blockSignals(False)

    def _on_deck_dynamic_changed(self, table: PlaylistTable):
        """A deck flipped mode on its own (e.g. an empty deck's first drop)."""
        self._refresh_mode_btn(table)
        self._autosave_playlist()

    def _ensure_deck_ready(self, table: PlaylistTable):
        """Wire a never-generated deck with a suggester / play callback / cache so a
        dynamic drop onto an empty deck can resolve and render tracks."""
        if self._lib is None:
            return
        if table._suggester is None:
            table._suggester = self._suggester or PlaylistSuggester(self._lib)
        if table._play_cb is None:
            table._play_cb = self._play_or_stop
        if table._cache is None:
            table._cache = self._cache

    def _on_header_press(self, e, table: PlaylistTable):
        """Left-click focuses the deck (and clears its row selection, so a following
        Del wipes the whole playlist); right-click opens rename + 💾 save + the
        static⇄dynamic toggle (decks), or rename + 📂 Show in Explorer + 💾 save +
        fold (wishlists)."""
        if e.button() == Qt.MouseButton.RightButton:
            if self._is_deck(table):
                is_folded = self.deck(table).folded
                menu = QMenu(self)
                ren = menu.addAction("✏  Rename")
                ren.setEnabled(not is_folded)
                # The playlist's own file, like the song rows offer theirs.
                m3u = table._m3u_path
                reveal = menu.addAction("📂  Show in Explorer" if m3u else
                                        "📂  Show in Explorer (not saved as a file yet)")
                reveal.setEnabled(m3u is not None)
                save_acts = self._add_header_save_actions(menu, table)
                mode_acts = {}
                if not table.player_only():   # nothing to switch where nobody plans
                    menu.addSeparator()
                    cur_mode = self._deck_mode(table)
                    for mode, label in (
                            ("static", "🔒  Static — a drop replaces one slot"),
                            ("dynamic", "🔓  Dynamic — drops build rounds & heats"),
                            ("free", "✋  Free order — drag any row anywhere")):
                        act = menu.addAction(label)
                        act.setCheckable(True)
                        act.setChecked(mode == cur_mode)
                        act.setEnabled(not is_folded)
                        mode_acts[act] = mode
                fold_btn = self.deck(table).fold_btn
                # Under a 🎨 look the arrow is the button's icon, not its text.
                fold_arrow = ((fold_btn.property("lookGlyph") or fold_btn.text())
                              if fold_btn is not None else "▾")
                fold = menu.addAction(
                    f"{fold_arrow}  " + i18n.t("Unfold this playlist" if is_folded
                                               else "Fold to a tab"))
                menu.addSeparator()
                clear = menu.addAction("🧹  Empty this playlist")
                clear.setEnabled(table.rowCount() > 0)
                # With 1–4 playlists there is no tab bar to right-click.
                new_day = self._add_new_day_action(menu)
                gp = (e.globalPosition().toPoint() if hasattr(e, "globalPosition")
                      else e.globalPos())
                chosen = menu.exec(gp)
                if chosen is ren:
                    self._begin_inline_rename(table)
                elif chosen is reveal and m3u is not None:
                    reveal_in_explorer(m3u, self)
                elif chosen in save_acts:
                    save_acts[chosen]()
                elif chosen in mode_acts:
                    self._set_deck_mode(table, mode_acts[chosen])
                elif chosen is fold:
                    self._toggle_deck_fold(table, not is_folded)
                elif chosen is clear:
                    table._clear_entire()
                elif chosen is new_day:
                    self._new_day_tab()
            elif table is self._warmup_table:
                if self._warmup_folded:
                    self._toggle_warmup_fold(False)
                else:
                    self._begin_inline_rename(table)
            else:
                # A wishlist: rename, its file and the fold — the deck menu minus the
                # planning modes.
                is_folded = self.deck(table).folded
                menu = QMenu(self)
                ren = menu.addAction("✏  Rename")
                ren.setEnabled(not is_folded)
                m3u = table._m3u_path
                reveal = menu.addAction("📂  Show in Explorer" if m3u else
                                        "📂  Show in Explorer (not saved as a file yet)")
                reveal.setEnabled(m3u is not None)
                save_acts = self._add_header_save_actions(menu, table)
                fold = menu.addAction("Unfold this wishlist" if is_folded
                                      else "Fold to a tab")
                gp = (e.globalPosition().toPoint() if hasattr(e, "globalPosition")
                      else e.globalPos())
                chosen = menu.exec(gp)
                if chosen is ren:
                    self._begin_inline_rename(table)
                elif chosen is reveal and m3u is not None:
                    reveal_in_explorer(m3u, self)
                elif chosen in save_acts:
                    save_acts[chosen]()
                elif chosen is fold:
                    self._toggle_deck_fold(table, not is_folded)
        else:
            # Clicking a folded tab re-opens the deck.
            if table is self._warmup_table:
                if self._warmup_folded:
                    self._toggle_warmup_fold(False)
            elif self.deck(table).folded:
                self._toggle_deck_fold(table, False)
            table.clearSelection()
            table.setFocus(Qt.FocusReason.MouseFocusReason)

    def _add_header_save_actions(self, menu: QMenu, table: PlaylistTable) -> dict:
        """💾 Save as M3U… (and 🏆 filing, where a Tournaments tree is kept) in a
        header menu, as a song row offers them: {action: what it runs}."""
        has_songs = table._row_meta.has_songs()
        save = menu.addAction("💾  Save as M3U…")
        save.setEnabled(has_songs)
        acts = {save: lambda: self._on_table_save_requested(table)}
        if getattr(self, "_tourney_tree", None) is not None:
            tree = menu.addAction("🏆  Save and add to Tournaments…")
            tree.setEnabled(has_songs)
            acts[tree] = lambda: self._on_table_save_requested(table, file_in_tree=True)
        return acts

    _WISH_REORDER_MIME = "application/x-wishlist-reorder"

    def _begin_inline_rename(self, table: PlaylistTable):
        """Edit a deck/wishlist title in place (tab-style) — no dialog. The header
        label is swapped for a QLineEdit; Enter / focus-out commits, Esc cancels."""
        hdr = self.deck(table).header
        if hdr is None or self.deck(table).folded:
            return   # no in-place rename inside a folded tab strip
        # Tear down any rename still open (commit it). A stale edit that never got
        # focus-out would otherwise block EVERY future rename — the "can't rename"
        # symptom — so never silently bail on a dangling editor.
        if getattr(self, "_rename_edit", None) is not None:
            self._commit_inline_rename()
        box = hdr.parentWidget()
        lyt = box.layout() if box else None
        if lyt is None:
            return
        # Deck headers sit in a nested HBox (mode toggle + label); indexOf on the
        # outer VBox returns -1 there, which used to append the editor at the
        # BOTTOM of the deck box — find the layout that actually holds the label.
        idx = lyt.indexOf(hdr)
        if idx < 0:
            for i in range(lyt.count()):
                sub = lyt.itemAt(i).layout()
                if sub is not None and sub.indexOf(hdr) >= 0:
                    lyt = sub
                    idx = sub.indexOf(hdr)
                    break
        if idx < 0:
            return
        edit = QLineEdit(self.deck(table).name)
        edit.setStyleSheet(self._DECK_HDR_IDLE)
        hdr.setVisible(False)
        lyt.insertWidget(idx, edit)
        self._rename_edit = edit
        edit.selectAll()
        edit.setFocus(Qt.FocusReason.MouseFocusReason)

        def _finish(commit: bool):
            if self._rename_edit is not edit:
                return   # already torn down (guards the editingFinished/Esc race)
            self._rename_edit = None
            self._rename_finish = None
            if commit:
                txt = edit.text().strip()
                if txt:
                    self._set_deck_name(table, txt)   # autosaves the new title
            lyt.removeWidget(edit)
            edit.deleteLater()
            hdr.setVisible(True)

        def _key(e, _orig=edit.keyPressEvent):
            if e.key() == Qt.Key.Key_Escape:
                _finish(False)
                return
            _orig(e)

        # Expose the active editor's teardown so a re-entrant rename can flush it.
        self._rename_finish = _finish
        edit.keyPressEvent      = _key
        edit.returnPressed.connect(lambda: _finish(True))
        edit.editingFinished.connect(lambda: _finish(True))

    def _commit_inline_rename(self):
        """Flush the in-progress inline rename (if any), committing its text."""
        finish = getattr(self, "_rename_finish", None)
        if finish is not None:
            finish(True)

    def _on_table_focused(self, table: PlaylistTable):
        self._focused_table = table  # Ctrl+S target (deck OR wishlist)
        self._set_active_table(table)
        self._bind_panel(table)   # the play panel shows THIS list's values

    def _set_active_table(self, table: PlaylistTable):
        """Mark `table` as focused. Decks (not the wishlist) also become the target
        of Generate / Save / ↺, with their generation context swapped in."""
        # Highlight whichever of the tables has focus.
        for d in self._deck_of.values():
            if d.header is None:
                continue
            active = d.active = (d.table is table)
            d.header.setStyleSheet(self._DECK_HDR_ACTIVE if active else self._DECK_HDR_IDLE)
            d.header.setText(self._deck_header_text(d.table, active))
        # Generation target only ever a full deck; Save/Import follow the focused
        # table, so a focused wishlist enables the Save button for itself.
        if self._is_deck(table):
            deck = self.deck(table)
            fresh = deck.ctx is None
            if fresh:
                # Empty / never-generated deck → KEEP the user's last combo selection
                # on screen (mode/style/age/class/dances stay put) so e.g. a
                # Past-Competitions schedule is ready for the next competition
                # without re-picking the mode. Only the per-deck CONTENT starts empty
                # so nothing leaks in from the deck we just left. (Clearing a deck
                # still resets the combos — that's _blank_deck.)
                deck.ctx = self._focused_ctx().carried_over(self._cfg.get_mode())
            self._table = table
            self._ensure_deck_tab_visible(table)   # 8-mode: front its tab page
            if not fresh:
                self._show_deck_ctx(table)         # this deck's context on the combos
            self._cfg.save_btn.setEnabled(bool(table._row_meta))
        elif table in self._wishlists or table is self._warmup_table:
            self._cfg.save_btn.setEnabled(bool(table._row_meta))

    def _focused_ctx(self) -> DeckContext:
        """The focused deck's generation context: what `self._style` and the
        other DeckFields read and write. Before the decks exist, the one deck
        A starts with; a deck focused without ever being generated starts
        from the defaults."""
        if getattr(self, "_deck_of", None) is None:
            return self._boot_ctx
        deck = self.deck(self._table)
        if deck.ctx is None:
            deck.ctx = DeckContext()
        return deck.ctx

    def _show_deck_ctx(self, table: PlaylistTable):
        """Put the focused deck's generation context on the combos."""
        # The grid is the source of truth for which dances this deck holds. Re-sync
        # `_dances` from the table's actual columns so the checkboxes can't drift to a
        # stale subset (e.g. an imported 5-dance Latin deck showing only CC+PD because
        # `_dances` got clobbered by an edit/generate elsewhere).
        deck_dances = table.current_dances()
        if deck_dances:
            self._dances = deck_dances
        # Mirror the restored context into the visible combos so the controls follow
        # the focused deck. Drive the mode combo from _ui_mode so a Past-Competitions
        # deck comes back as "Past Competitions", not the engine's "Favorites".
        self._cfg.apply_config(
            mode=getattr(self, "_ui_mode", None) or getattr(self, "_mode", None),
            style=getattr(self, "_style", None),
            age=getattr(self, "_age", None),
            cls=getattr(self, "_dance_class", None),
            dances=getattr(self, "_dances", None),
            replay_idx=getattr(self, "_active_replay_idx", None),
        )

    def _max_decks(self) -> int:
        """Most decks the view will show. A player build stops at four: a venue
        runs one competition at a time, and eight decks only exist so a planner
        can lay several out side by side. Every path that raises the deck count
        — the ⧉ ring, a reveal, an import, a restored layout — comes through
        _apply_deck_view, which clamps to this."""
        return 4 if player_build() else 8

    def _apply_deck_view(self):
        """Show exactly `_deck_count` decks (1 → A · 2 → A,B · 4 → A,B,C,D · 8 → two
        tabs of four) and keep the wishlist area in sync. If the active deck got
        hidden, refocus deck A."""
        n = min(self._deck_count, self._max_decks())
        self._deck_count = n   # a restored 8-deck layout lands here in a player build
        # No-playlist view: hide the whole deck-tab area so the Eintanzen /
        # wishlist / library panes below take over the space.
        self._deck_tabs.setVisible(n >= 1)
        if n == 0:
            self._dual_btn.setProperty("countText", "0")
            self._set_toolbar_btn_text(self._dual_btn, "No playlist")
            self._update_wish_area()
            return
        eight = (n == 8)
        g1 = min(n, 4)   # decks shown on the first grid (tab "Group A–D")
        self._decks_col2.setVisible(g1 >= 2)   # right column (decks B+D)
        self._deckC_box.setVisible(g1 >= 4)    # bottom decks only at 4+
        self._deckD_box.setVisible(g1 >= 4)
        # Second grid (E–H) is a full 2×2; it shows on its own tab in 8-mode. The
        # 📅 Tournament-day tab (its own eight day decks in two sub-tabs) shows
        # whenever a day plan is loaded, independent of the deck-count view.
        for b in (self._deckE_box, self._deckF_box, self._deckG_box, self._deckH_box):
            b.setVisible(True)
        day = self._day_plan_active() or getattr(self, "_day_tab_keep", False)
        self._deck_tabs.setTabVisible(0, True)
        self._deck_tabs.setTabVisible(1, eight)
        self._deck_tabs.setTabVisible(2, day)
        self._deck_tabs.tabBar().setVisible(eight or day)
        if not self._deck_tabs.isTabVisible(self._deck_tabs.currentIndex()):
            self._deck_tabs.setCurrentIndex(0)
        self._dual_btn.setProperty("countText", str(n))
        self._set_toolbar_btn_text(
            self._dual_btn,
            (i18n.t("%d playlist") if n == 1 else i18n.t("%d playlists")) % n)
        self._update_wish_area()
        # Single-playlist view must never end up as a lone folded tab.
        if n == 1 and self.deck(self._tableA).folded:
            self._toggle_deck_fold(self._tableA, False)
        # Which decks count as "whole column folded" depends on visibility.
        self._sync_col_fold_constraints()
        if self._table is not None and not self._box_shown(self._table):
            self._set_active_table(self._tableA)

    def _cycle_deck_view(self, back: bool = False):
        """Cycle the deck view 1 → 2 → 4 → 8 → 0 (no playlists) → 1, stopping at
        4 where that is the cap (_max_decks).

        A right click (`back`) walks the same ring the other way: one view too
        far then costs one click back instead of four more forward."""
        ring = ({1: 2, 2: 4, 4: 8, 8: 0, 0: 1} if self._max_decks() >= 8
                else {1: 2, 2: 4, 4: 0, 0: 1})
        if back:
            ring = {nxt: cur for cur, nxt in ring.items()}
        self._deck_count = ring.get(self._deck_count, 1)
        self._apply_deck_view()
        msg = {0: "No-playlist view — decks hidden; only Eintanzen / wishlist / library show",
               1: "Single-playlist view",
               2: "🎚️ Two-playlist view — focus a deck; its controls drive Generate / Save / ↺",
               4: "🎚️ Four-playlist view — focus a deck to drive Generate / Save / ↺",
               8: "🎚️ Eight-playlist view — two tabs (Group A–D / E–H); focus a deck to drive Generate / Save / ↺"}
        self.statusBar().showMessage(msg[self._deck_count])
        self._autosave_playlist()

    def _reveal_deck(self, table) -> None:
        """Bring one deck on screen: widen the deck view if it is hidden, front
        its tab, unfold it and make it the active deck.

        A run that fills a deck the current view hides looks exactly like a run
        that did nothing — the 'No playlist' view (`_deck_count == 0`) swallows
        the whole grid. Whatever the view was, the deck that was just filled
        comes forward."""
        if not self._is_deck(table):
            return
        if not self._box_shown(table):
            # Day decks live on the 📅 tab (shown while they hold tracks) and
            # need no deck-count at all; a normal deck may need a wider view
            # first. Either way the page holding it comes to the front.
            if table not in self._day_decks:
                idx = self._decks.index(table)
                want = 8 if idx >= 4 else 4 if idx >= 2 else 2 if idx >= 1 else 1
                want = min(want, self._max_decks())
                if want > self._deck_count:
                    self._deck_count = want
                    self._apply_deck_view()
            self._ensure_deck_tab_visible(table)
        if self.deck(table).folded:   # deck folded to a slim tab strip
            self._toggle_deck_fold(table, folded=False)
        self._set_active_table(table)

    def _cycle_compact(self):
        """🗜 toolbar button: full headers → compact → no grouping → numbers → full."""
        self._set_compact_state((self._compact_state + 1) % 4)

    def _set_compact_state(self, state: int):
        """Apply a header view (0 full · 1 🗜 compact · 2 🚫 no grouping ·
        3 🔢 numbers) to every list on the desk, then persist it.

        The wishlists included: they are flat, so steps 0-2 have no headers to
        drop there, but 🔢 numbers their titles like any other list."""
        self._compact_state = state
        for t in self._all_tables:
            t.set_grouping(state)
        self._apply_compact_label()
        self._settings["compact"] = state
        save_settings(self._settings)
        self.statusBar().showMessage(
            {0: "🗜 Full view — round and dance headers shown",
             1: "🗜 Compact view — dance headers hidden",
             2: "🚫 No grouping — flat song list, no round headers",
             3: "🔢 Numbers — flat song list, every title numbered"}[state])

    def _apply_compact_label(self):
        """Caption + pressed look of the 🗜 button for the current state."""
        self._compact_btn.setChecked(self._compact_state > 0)
        self._set_toolbar_btn_text(
            self._compact_btn,
            {2: "🚫  No groups", 3: "🔢  Numbers"}.get(self._compact_state,
                                                      "🗜  Compact"))

    def _on_deck_play(self, source: PlaylistTable):
        """One shared player: when a deck starts a song, clear the others' ■ markers."""
        self._preview_src = source   # anchor for the preview overlay in _play_or_stop
        for t in self._all_tables:
            if t is not source:
                t.on_playback_stopped()
        self._reset_aux_play_markers()
        self._on_list_play(source)   # its own TSO / pause, never re-applied

    def release_play_markers(self):
        """A preview window (Similar tracks) takes the shared player over: every
        deck's ■ and the panes' markers go back to ▶, as when another deck
        starts — the row that was running is no longer what plays."""
        for t in self._all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()

    def _reset_aux_play_markers(self, keep=None):
        """Clear the ▶/■ toggle of the library pane, the tournament pane, the
        event plan and the BPM-check dialog — the shared player stopped or
        another widget took it over. `keep` is the pane that just STARTED
        playing, if any."""
        for pane in (getattr(self, "_lib_browser", None),
                     getattr(self, "_tourney_tree", None),
                     getattr(self, "_event_compare", None)):
            if pane is not None and pane is not keep:
                pane.on_playback_stopped()
        dlg = getattr(self, "_bpm_dlg", None)
        if dlg is not None:
            try:
                dlg.reset_play_marker()
            except RuntimeError:   # dialog already deleted
                self._bpm_dlg = None

    # ----- duplicate detection / resolution -----------------------------------
    def _visible_deck_tables(self) -> list[PlaylistTable]:
        """The deck tables currently shown (matches the 1 / 2 / 4 / 8 deck view).
        In 8-mode all eight count, even those on the inactive tab page; an active
        📅 day plan adds the eight day decks the same way."""
        tables = [self._tableA]
        if self._deck_count >= 2:
            tables.append(self._tableB)
        if self._deck_count >= 4:
            tables += [self._tableC, self._tableD]
        if self._deck_count >= 8:
            tables += [self._tableE, self._tableF, self._tableG, self._tableH]
        if self._day_plan_active():
            tables += self._day_decks
        return tables

    def _checkable_deck_tables(self) -> list[PlaylistTable]:
        """Every deck that currently HOLDS tracks — across all tabs / view modes,
        not just the on-screen ones. This is what the Music check scans, so an
        'open' playlist sitting on the inactive 8-mode tab still gets checked."""
        return [t for t in self._decks + self._day_decks if t._row_meta.has_songs()]

    def _update_deck_totals(self):
        """Refresh the Σ total-play-time badge under each deck (whole playlist)
        and under the Eintanzen / party panel."""
        by_dance = bool(self._settings.get("totals_by_dance"))
        for d in self._deck_of.values():
            lbl = d.total_lbl
            if lbl is None:
                continue
            table = d.table
            entries = table._row_meta.heat_entries()
            n = len(entries)
            secs = sum(int(getattr(e, "duration", 0) or 0) for e in entries)
            if n:
                # Two whole keys rather than a word glued onto a number: the
                # plural is not an "s" in every language.
                count = (i18n.t("Σ  %d song") if n == 1
                         else i18n.t("Σ  %d songs")) % n
                lbl.setText(f"{'▾' if by_dance else '▸'}  " + count
                            + (f"  ·  ~{_fmt_track_secs(secs)}" if secs else "")
                            + (f"\n{dance_counts_line(entries)}" if by_dance else ""))
            else:
                lbl.setText("")
            folded = (self._warmup_folded if table is self._warmup_table
                      else self.deck(table).folded)
            lbl.setVisible(bool(n) and not folded)

    def _toggle_totals_by_dance(self):
        """▸ / ▾ on a Σ badge: show or hide the songs per dance — under every
        playlist at once, remembered across restarts."""
        self._settings["totals_by_dance"] = not self._settings.get("totals_by_dance")
        save_settings(self._settings)
        self._update_deck_totals()

    # ── 🎼 The library pane below the decks ─────────────────────────────────────
    def _on_library_pane_toggled(self, on: bool):
        """📚 toolbar toggle: show / hide the library browser entirely."""
        self._lib_tabs.setVisible(on)
        self._settings["library_pane"] = on
        save_settings(self._settings)
        self.statusBar().showMessage(
            "📚 Library browser shown" if on else "📚 Library browser hidden")

    def show_library_filtered(self, dance: str = "", cls: str = "",
                              plays: str = "", added: str = ""):
        """Reveal the 📚 library pane on ONE filtered view — 📊 the gap
        dashboard sends the user here to browse a thin dance × class."""
        if not self._lib_btn.isChecked():
            self._lib_btn.setChecked(True)   # fires _on_library_pane_toggled
        self._lib_tabs.setCurrentWidget(self._lib_browser)
        self._lib_browser.focus_filter(dance=dance, cls=cls, plays=plays,
                                       added=added)
        self.statusBar().showMessage(
            i18n.t("📚 Library filtered: %s")
            % (dance_name(dance, dance) or i18n.t("all dances"))
            + (i18n.t(" · class %s") % cls if cls else "")
            + (i18n.t(" · never played") if plays == "never" else ""))

    def _on_lib_columns_reordered(self, order: list):
        self._settings["library_columns"] = list(order)
        save_settings(self._settings)

    def _on_lib_column_widths(self, widths: dict):
        # JSON keys are strings; store them that way for a clean round-trip.
        self._settings["library_col_widths"] = {str(k): int(v)
                                                 for k, v in widths.items()}
        save_settings(self._settings)

    def _on_lib_columns_hidden(self, hidden: list):
        # One pane, so one setting — unlike the decks, which keep theirs per
        # kind of list.
        self._settings["library_hidden_columns"] = [int(c) for c in hidden]
        save_settings(self._settings)

    def _on_lib_dance_names(self, short: bool):
        self._settings["library_short_dances"] = bool(short)
        save_settings(self._settings)

    def _on_columns_changed(self, kind: str, hidden: list):
        """A column was ticked off (or back on) in a header's right-click menu.

        It is a setting for the KIND of list, so every other deck / wishlist /
        party list gets the same treatment — the user sees one wishlist at a
        time and would otherwise have to repeat the tick four times."""
        cols = [int(c) for c in hidden]
        self._settings.setdefault("hidden_columns", {})[kind] = cols
        save_settings(self._settings)
        for t in self._all_tables:
            if t.list_kind == kind and t.hidden_columns() != cols:
                t.set_hidden_columns(cols)

    def _on_column_widths_changed(self, kind: str, widths: dict):
        """A handle was dragged to rest in one list of this kind — keep it, and
        give the others the same width. JSON keys are strings; store them that
        way for a clean round-trip, like library_col_widths."""
        cols = {str(k): int(v) for k, v in widths.items() if int(v) > 0}
        self._settings.setdefault("column_widths", {})[kind] = cols
        save_settings(self._settings)
        for t in self._all_tables:
            if t.list_kind == kind and t.column_widths() != widths:
                t.set_column_widths(cols)

    def _on_dance_names_changed(self, kind: str, short: bool):
        """The Dance column of this kind of list was switched between
        "Langsamer Walzer" and "LW" — the other lists of the kind follow."""
        short = bool(short)
        self._settings.setdefault("short_dances", {})[kind] = short
        save_settings(self._settings)
        for t in self._all_tables:
            if t.list_kind == kind:
                t.set_short_dances(short)

    def _on_tempo_reset_mode(self, on: bool):
        self._settings["tempo_reset_per_track"] = bool(on)
        save_settings(self._settings)

    def _on_tso_mode(self, on: bool):
        """TSO toggle flipped: persist it, and when switched ON pitch the title
        playing right now to the heat mean straight away (don't wait for the
        next track)."""
        self._settings["tso_equalize"] = bool(on)
        save_settings(self._settings)
        # …and it is the value of the list the card is serving.
        t = getattr(self, "_tso_list", None) or self._engine_list()
        if t is not None:
            self._list_vals(t)["tso"] = bool(on)
            self._autosave_playlist()
        if on:
            self._equalize_heat_tempo(auto=True)

    def _on_lib_tab_changed(self, index: int):
        """The fold clamps the whole pane, so a folded library would leave the
        🏆 tab a sliver — switching tabs unfolds it."""
        if index and self._lib_browser.is_folded():
            self._lib_browser.set_folded(False)

    def _on_lib_play(self, path: Path | None, row: int, pane=None):
        """▶ / double-click in the library — or the tournament — pane: preview
        via the shared player, with the mini overlay anchored to the clicked
        row. `pane` is which of the two asked for it."""
        pane = pane if pane is not None else self._lib_browser
        for t in self._all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers(keep=pane)
        self._play_or_stop(path)
        if (path is not None and row >= 0 and self._preview
                and self._settings.get("preview_player", True)
                and not self._is_playing_mode()):
            self._preview.show_for(pane._table, row, Path(path).stem)

    def _on_lib_unplanned_toggled(self, on: bool):
        """🆕 filter switched in the library pane — feed it the planned set."""
        if on:
            self._refresh_library_planned_filter()

    def _refresh_library_planned_filter(self):
        """Build the set of library paths already used in the open decks and hand it
        to the library browser. Matches by full path AND by content fingerprint, so a
        renamed/relocated copy of a planned track is hidden too."""
        if getattr(self, "_lib_browser", None) is None:
            return
        if not self._lib_browser.unplanned_active():
            return
        paths, fps = self._deck_dedup_index()
        planned = set(paths)
        fingerprint = (self._cache.recorded_fingerprint
                       if self._cache is not None else None)
        if self._lib is not None:
            for e in self._lib.entries:
                p = getattr(e, "path", None)
                # `paths` is lowercased; the browser looks up `str(path)` as is.
                if is_planned(p, paths, fps, fingerprint):
                    planned.add(str(p))
        self._lib_browser.set_planned_paths(planned)
