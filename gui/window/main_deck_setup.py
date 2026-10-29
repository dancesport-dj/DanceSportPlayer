"""The deck area's builders: the playlist, wishlist and day decks, the toolbar
above them, the deck grids and the wishlists, warm-up panel and library pane
below them.

Extracted from dancesport_gui.py as a MainWindow mixin.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import planner.config
import planner.playlist.m3u
from gui.common import DEFAULT_HIDDEN_COLUMNS
from gui.dialogs import TOURNAMENTS, deck_name, wishlist_name
from gui.library_browser import LibraryBrowser
from gui.library_load_bar import NEEDS_LIBRARY
from gui.table.playlist_table import PlaylistTable
from gui.tournament_tree import TournamentTree
from planner import i18n
from planner.models import MusicEntry
from shared.appearance.icons import counted_emoji

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object


class _ToolbarRow(QWidget):
    """The toolbar strip, which reports when its OWN width changes.

    It sits in the right pane of the main splitter, not in the window, so the
    two widths come apart whenever the config panel folds or the divider is
    dragged — and the window, which is all `resizeEvent` hears, never moves.
    Reporting from here rather than through the app-wide filter on qApp keeps
    the callback tied to this widget's lifetime: Resize is far too common an
    event to be dereferencing a torn-down window's attributes on.
    """

    def __init__(self, on_resize):
        super().__init__()
        self._on_resize = on_resize

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()


class DeckSetupMixin(MainWindowHost):
    """Builds the deck area: decks, toolbar, grids and lower panes."""

    def _setup_decks(self):
        """The playlist, wishlist and day decks, and the columns each kind shows."""
        # Right: two playlist decks + wishlist + player bar
        right = QWidget()
        rl = QVBoxLayout(right)
        # …kept: the wide player docks into it above the decks.
        self._right_col = rl
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        # Three tables: two full playlist decks side-by-side + a flat wishlist below.
        # Controls (Generate / Save / ↺ / play / collapse) act on the focused deck.
        self._deckset.tableA = PlaylistTable()
        self._deckset.tableB = PlaylistTable()
        self._deckset.tableC = PlaylistTable()
        self._deckset.tableD = PlaylistTable()
        # Decks E–H back the 8-playlist mode: a second 2×2 grid shown on its own tab
        # ("Group E–H") so eight playlists never crowd the screen at once.
        self._deckset.tableE = PlaylistTable()
        self._deckset.tableF = PlaylistTable()
        self._deckset.tableG = PlaylistTable()
        self._deckset.tableH = PlaylistTable()
        self._deckset.wishlist = PlaylistTable()
        self._deckset.wishlist2 = PlaylistTable()
        self._deckset.wishlist3 = PlaylistTable()
        self._deckset.wishlist4 = PlaylistTable()
        self._deckset.wishlist._flat_mode = True
        self._deckset.wishlist2._flat_mode = True
        self._deckset.wishlist3._flat_mode = True
        self._deckset.wishlist4._flat_mode = True
        # Dedicated warm-up (Eintanzen) list — its own panel between the decks and the
        # wishlist area, never clobbering a playlist. Holds a single warm-up list with
        # ↺ timbre re-roll + drag-drop replace; hidden until a warm-up is generated.
        self._deckset.warmup_table = PlaylistTable()
        # Up to eight full playlist decks (generation targets); 1/2/4/8 shown via _dual_btn
        # (8 = two tabs of four).
        self._deckset.decks = [self._deckset.tableA, self._deckset.tableB, self._deckset.tableC, self._deckset.tableD,
                               self._deckset.tableE, self._deckset.tableF, self._deckset.tableG, self._deckset.tableH]
        # Eight dedicated 📅 day decks on the third tab ("Tournament day", two
        # sub-tabs of four). Filled only by the 📅 Day-plan planner, so decks A–H
        # always stay normal working playlists; the tab shows while they hold a plan.
        self._deckset.day_decks = [PlaylistTable() for _ in range(8)]
        self._deckset.wishlists = [self._deckset.wishlist, self._deckset.wishlist2,
                                   self._deckset.wishlist3, self._deckset.wishlist4]
        self._deckset.all_tables = (self._deckset.decks + self._deckset.day_decks
                                    + self._deckset.wishlists + [self._deckset.warmup_table])
        self._deckset.table = self._deckset.tableA                   # the focused/active deck
        self._deckset.deck_count = 1                              # visible deck count: 1, 2, 4 or 8
        # One Deck per table, holding everything this window keeps about it
        # (see gui.decks.deck); reached through self.deck(table), never directly.
        self._deckset.deck_of = {}
        self.deck(self._deckset.tableA).ctx = self._boot_ctx

        self._wire_deck_tables()

        # Which columns each KIND of list shows (header right-click). A wishlist
        # has no use for Heat and ↺, a deck does — and there are four wishlists
        # and sixteen decks, so the tick belongs to the kind, not to the table
        # the user happened to right-click. Saved in gui_settings.json.
        saved_cols = self._settings.get("hidden_columns") or {}
        saved_widths = self._settings.get("column_widths") or {}
        saved_short = self._settings.get("short_dances") or {}
        saved_order = self._settings.get("column_order") or {}
        for kind, tables in (("playlist", self._deckset.decks + self._deckset.day_decks),
                             ("wishlist", self._deckset.wishlists),
                             ("party", [self._deckset.warmup_table])):
            # A saved empty list is a decision (Heat ticked back on), not an
            # absent setting — only the missing key falls back to the default.
            hidden = ([int(c) for c in saved_cols[kind]] if kind in saved_cols
                      else DEFAULT_HIDDEN_COLUMNS.get(kind, []))
            widths = saved_widths.get(kind) or {}
            short = bool(saved_short.get(kind, False))
            order = saved_order.get(kind)
            for t in tables:
                t.list_kind = kind
                t.set_short_dances(short)
                if order:
                    t.set_column_order(order)
                if hidden:
                    t.set_hidden_columns(hidden)
                if widths:
                    # After the hiding: a width for a column that is put away is
                    # kept for when it comes back, not a reason to show it.
                    t.set_column_widths(widths)
        return right, rl, saved_cols, saved_widths

    def _wire_deck_tables(self):
        """Every table's callbacks and signals into this window."""
        for t in self._deckset.all_tables:
            t._seek_cb = self._seek   # Ctrl+←/→ seeks ∓30 s
            t._short_secs_cb = lambda dance, rnd="", t=t: self._configured_play_secs(t, dance, rnd)   # orange ⏱ on short tracks
            # 🏆 The panel's length follows the picked row's dance.
            t.currentCellChanged.connect(lambda *_a: self._sync_dance_len())
            t._play_secs_cb = self._track_play_secs   # ⏱ tooltip: real play time
            t._edge_silence_cb = self._track_edge_silence   # red ⏱ past 5 s
            t.set_change_callback(self._autosave_playlist)
            t.focused.connect(self._on_table_focused)
            t.playRequested.connect(self._on_deck_play)
            t.saveRequested.connect(self._on_table_save_requested)
            t.saveToTournamentsRequested.connect(
                lambda t: self._on_table_save_requested(t, file_in_tree=True))
            t.cleared.connect(self._on_table_cleared)
            # Order matters: the stop clears the playing title, which is what
            # then lets the cue put the new list's first track on the player.
            t.loaded.connect(self._stop_if_playing_from)
            t.loaded.connect(self._cue_first_track)
            t.dynamicChanged.connect(self._on_deck_dynamic_changed)
            t.set_columns_callback(self._on_columns_changed)
            t.set_widths_callback(self._on_column_widths_changed)
            t.set_column_order_callback(self._on_column_order_changed)
            t.set_dance_names_callback(self._on_dance_names_changed)
            t.set_rating_callback(self._set_entry_rating)
            t.set_play_counts_callback(self._reset_play_counts)
            # ⏭/✋ in the deck's bottom-right corner — THIS deck's auto-advance
            # answer, within reach while a round runs. The panel's switch is
            # what it falls back to (see _deck_advance).
            t.set_advance_toggle(lambda t=t: self._deck_advance(t),
                                 lambda on, t=t: self._set_deck_advance(t, on))
            t.setToolTip(
                "Space: play / stop the selected song\n"
                "Ctrl + ← / → : seek 30 s back / forward\n"
                "Click a round / dance header to collapse or expand it")
        for t in self._deckset.decks + self._deckset.day_decks:
            # Empty deck → first drop turns dynamic; capacity comes from the Rounds field.
            t._capacity_provider = self._current_capacity

    def _setup_deck_toolbar(self, rl):
        """The toolbar above the decks: collapse, view cycles, actions."""
        # Collapse / expand + dual-view toggle toolbar above the decks.
        coll_bar = QHBoxLayout()
        coll_bar.setContentsMargins(0, 0, 0, 0)
        coll_bar.setSpacing(4)
        (btn_save_all, btn_bundle, btn_clear_all, btn_day, btn_warmup,
         btn_print) = self._make_action_buttons()
        self._make_view_buttons()
        for b in (self._collapse_btn, self._fold_decks_btn,
                  btn_save_all, btn_bundle, self._save_state_btn, btn_clear_all,
                  self._check_btn, btn_day, btn_warmup,
                  btn_print, self._dual_btn, self._compact_btn, self._dual_wish_btn,
                  self._warmup_toggle_btn, self._lib_btn, self._cart_btn):
            b.setFixedHeight(24)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # The 🤸 Eintanzen / ETDS party list is a playlist like any other here —
        # it has rounds and dance headers to collapse, and being left out of the
        # ⊟ / ⊞ pair made the buttons look broken whenever it was the only list
        # on screen (the no-playlist view).
        self._collapse_btn.clicked.connect(self._toggle_collapse_all)
        self._fold_decks_btn.clicked.connect(self._toggle_fold_all_decks)
        # A lambda: `clicked` passes its `checked` flag to any slot that takes
        # an argument, and _save_all_playlists(decks=…) took it for the decks.
        btn_save_all.clicked.connect(lambda: self._save_all_playlists())
        btn_bundle.clicked.connect(self._export_bundle)
        btn_day.clicked.connect(self._plan_tournament_day)
        self._save_state_btn.clicked.connect(self._save_state_now)
        btn_clear_all.clicked.connect(self._clear_all_playlists)
        self._check_btn.clicked.connect(self._show_check_menu)
        btn_warmup.clicked.connect(self._generate_warmup)
        btn_print.clicked.connect(self._print_running_order)
        # Left click steps the ring forward, right click back. A QPushButton has
        # no right-click signal of its own, so the context-menu request is it —
        # neither button carries a menu, and a right click never fires clicked().
        self._dual_btn.clicked.connect(lambda: self._cycle_deck_view())
        self._dual_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._dual_btn.customContextMenuRequested.connect(
            lambda _pos: self._cycle_deck_view(back=True))
        self._compact_btn.clicked.connect(self._cycle_compact)
        self._dual_wish_btn.clicked.connect(lambda: self._cycle_wish_view())
        self._dual_wish_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._dual_wish_btn.customContextMenuRequested.connect(
            lambda _pos: self._cycle_wish_view(back=True))
        self._warmup_toggle_btn.toggled.connect(self._on_warmup_toggle)
        self._lib_btn.toggled.connect(self._on_library_pane_toggled)
        self._cart_btn.toggled.connect(self._on_cartwall_toggled)
        coll_bar.addWidget(self._collapse_btn)
        coll_bar.addWidget(self._fold_decks_btn)
        coll_bar.addWidget(btn_save_all)
        coll_bar.addWidget(btn_bundle)
        coll_bar.addWidget(self._save_state_btn)
        coll_bar.addWidget(btn_clear_all)
        coll_bar.addWidget(self._check_btn)
        coll_bar.addWidget(btn_day)
        coll_bar.addWidget(btn_warmup)
        coll_bar.addWidget(btn_print)
        coll_bar.addStretch(1)
        coll_bar.addWidget(self._dual_btn)
        coll_bar.addWidget(self._compact_btn)
        coll_bar.addWidget(self._dual_wish_btn)
        coll_bar.addWidget(self._warmup_toggle_btn)
        coll_bar.addWidget(self._lib_btn)
        coll_bar.addWidget(self._cart_btn)
        help_btn = self._make_help_button()
        coll_bar.addWidget(help_btn)
        # Responsive toolbar, two compaction stages: when the row is too narrow to
        # hold every full label (e.g. 1920×1200 at 200 % scale = 960 px effective),
        # first the view buttons collapse to their leading icon; if that still
        # doesn't fit (small displays), EVERY button collapses to its icon — the
        # full label is kept as the tooltip, so nothing gets truncated mid-word.
        self._toolbar_btns = [
            self._collapse_btn, self._fold_decks_btn,
            btn_save_all, btn_bundle, self._save_state_btn, btn_clear_all,
            self._check_btn, btn_day, btn_warmup,
            btn_print, self._dual_btn, self._compact_btn, self._dual_wish_btn,
            self._warmup_toggle_btn, self._lib_btn, self._cart_btn,
        ]
        self._toolbar_icon_btns = [
            self._collapse_btn, self._fold_decks_btn, btn_print,
        ]
        # Toolbar actions that exist only for the planning side: they generate,
        # curate or check a playlist. Hidden in a player-only install
        # (_apply_app_mode); everything else here also serves a tournament.
        # 🚦 Check stays: its menu shrinks to Ready? instead (_check_menu).
        self._planner_btns = [btn_bundle, btn_day, btn_warmup]
        # Hidden by the player-only BUILD rather than by player mode: 🖨 Print
        # renders through Qt6Pdf, which that build does not ship (see
        # dancesport.spec). In every other build it stays, player mode included.
        self._player_build_hidden = [btn_print] if planner.config.player_build() else []
        self._install_toolbar_row(coll_bar, rl)

    def _install_toolbar_row(self, coll_bar, rl):
        """The toolbar row itself, set up to compact its buttons."""
        self._toolbar_compact = 0
        self._toolbar_full_width = 0
        self._toolbar_l1_width = 0
        self._toolbar_l2_width = 0
        for b in self._toolbar_btns:
            self._register_toolbar_btn(b)
        # 🗜 carries a state-dependent caption — set it only now, so the button is
        # registered and the label goes through the compaction-aware setter.
        self._apply_compact_label()
        self._toolbar_widget = _ToolbarRow(self._update_toolbar_compact)
        self._toolbar_widget.setLayout(coll_bar)
        # Buttons report their full-text width as their MINIMUM, which would pin the
        # whole window to a ~3000 px minimum width and stop it being resized narrower
        # (so the icon-compaction below could never trigger). An Ignored horizontal
        # policy lets the bar shrink with the window; resizeEvent then compacts it.
        self._toolbar_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        rl.addWidget(self._toolbar_widget)

    def _make_action_buttons(self):
        """The toolbar's action buttons, from ⊟ Collapse to 🖨 Print."""
        # One button per job, not two: each says what the NEXT click does.
        self._collapse_btn = QPushButton("⊟  Collapse all")
        self._collapse_btn.setToolTip(
            "Collapse every round and dance header of every playlist —\n"
            "click again to open them all.")
        self._fold_decks_btn = QPushButton("▴  Fold decks")
        self._fold_decks_btn.setToolTip(
            "Fold every visible playlist deck and wishlist to its header tab —\n"
            "click again to open them all.\n"
            "Click a single tab (or its arrow) to open just that one.")
        btn_save_all = QPushButton("💾  Save all")
        btn_save_all.setToolTip(
            "Export every non-empty playlist deck to its own .m3u in the\n"
            "playlist folder at once (wishlists are not included).\n"
            "Each file is named after its deck title.")
        btn_bundle = QPushButton("🧳  USB export")
        btn_bundle.setToolTip(
            "Export playlists as a self-contained venue bundle — asks first\n"
            "whether to take all open decks, only the 📅 tournament day, or\n"
            "saved .m3u files dragged in, with the ⭐ wishlists if ticked.\n"
            "One sub-folder per playlist holding its tracks copied in numbered\n"
            "play order (0_0_1 - Title WW29.mp3) plus the playlist's .m3u — each\n"
            "folder plays in order even without the M3U, from any drive,\n"
            "laptop or UltraMixer at the venue (no path fixing needed there).\n"
            "Also offers the 📦 venue pack: this desk in one file for another PC.")
        self._save_state_btn = QPushButton("📌  Save state")
        self._save_state_btn.setToolTip(
            "Save the whole working session right now — every deck, wishlist and the\n"
            "window layout — so it comes back exactly on the next launch.  (Ctrl+Shift+S)\n"
            "(This also happens automatically on every edit and on close.)")
        btn_clear_all = QPushButton("🧹  Clear all")
        btn_clear_all.setToolTip(
            "Empty every playlist deck (wishlists are kept).\n"
            "Tip: Del on a deck's title clears just that one playlist;\n"
            "Del on a wishlist's title clears that wishlist.")
        # One button for every check, its tools in a menu like ❔'s.
        self._check_btn = QPushButton("🚦  Check ▾")
        self._check_btn.setToolTip(
            "🚦 Ready? — the pre-flight before the event, one traffic light per\n"
            "check: missing files, loudness, silence probe, Paso Doble highlights,\n"
            "duplicates and the music check, each with its fix.\n"
            "The menu also opens 🔁 Check duplicates, 🎵 Check music and\n"
            "🧭 Fix paths on their own.")
        btn_day = QPushButton("📅  Day plan")
        btn_day.setToolTip(
            "Plan a whole tournament day: define the day's competitions\n"
            "(style, age, class, round pattern) and generate them all at once\n"
            "into the 📅 Tournament-day tab — eight dedicated day decks in two\n"
            "sub-tabs, separate from the normal playlists; more than 8\n"
            "competitions stack several per deck. All share one no-repeat\n"
            "pool, so a song never appears in two of the day's competitions\n"
            "(Paso excepted). Exports write one M3U per competition.")
        btn_warmup = QPushButton("🤸  Practice / Party")
        self._warmup_gen_btn = btn_warmup   # caption follows the app mode
        btn_warmup.setToolTip(
            "Build a practice playlist into the focused deck:\n"
            "• Practice for a tournament class — the class's dances round-robin\n"
            "  (e.g. Latin S: SA, CC, RB, PD, JI …), TSO-conform, popular + fresh.\n"
            "• Party — alternating 3-dance rounds across all dances.\n"
            "Draw from your ⭐ Favorites (unused tracks), the open wishlists\n"
            "or a chosen .m3u file.")
        # 📚 Both draw from the library: greyed out while its scan still runs.
        for btn in (btn_day, btn_warmup):
            btn.setProperty(NEEDS_LIBRARY, True)
        btn_print = QPushButton("🖨  Print")
        btn_print.setToolTip(
            "Export the focused playlist as a printable PDF\n"
            "(rounds, heats, titles, lengths) into the playlist folder.")
        return (btn_save_all, btn_bundle, btn_clear_all, btn_day, btn_warmup,
                btn_print)

    def _make_view_buttons(self):
        """The view cycles and pane toggles: ⧉ 🗜 ⭐ 🤸 📚 🎛."""
        # The ⧉ / ⭐ of the two cycle buttons is painted rather than typed, so a
        # count badge can sit in its corner once the toolbar compacts the caption
        # away. 'countEmoji' marks such a button, 'countText' is the number —
        # both the badge and what the caption shrinks to.
        self._dual_btn = QPushButton("1 playlist")
        self._dual_btn.setProperty("countEmoji", "⧉")
        self._dual_btn.setProperty("countText", "1")
        self._dual_btn.setIcon(counted_emoji("⧉", None, 16))
        self._dual_btn.setIconSize(QSize(16, 16))
        # A player build stops the ring at four (_max_decks), so its tooltip may
        # not promise a view that install will never reach.
        eight = self._max_decks() >= 8
        tip = [i18n.t("Cycle 1 → 2 → 4 → 8 → no playlists (and back).") if eight else
               i18n.t("Cycle 1 → 2 → 4 → no playlists (and back)."),
               i18n.t("Right click walks the cycle backwards.")]
        if eight:
            tip.append(i18n.t("8 splits into two tabs of four (Group A–D / Group E–H)."))
        tip += [i18n.t("No-playlist hides every deck so the Practice / wishlist / "
                       "library panes take over."),
                i18n.t("Two or more decks also reveal the wishlist below."),
                i18n.t("Generate / Save / ↺ / play act on whichever deck has focus.")]
        self._dual_btn.setToolTip("\n".join(tip))
        # Header view, cycled in four steps: full → 🗜 compact (no per-dance header
        # rows, the Dance column still names each row) → 🚫 no grouping at all (no
        # round / ─── section headers either — a party list as one flat run) →
        # 🔢 numbers (no grouping, plus an Nb. column counting the titles).
        self._compact_btn = QPushButton("🗜  Compact")
        self._compact_btn.setCheckable(True)
        self._compact_state = int(self._settings.get("compact", 0) or 0)
        if self._compact_state not in (0, 1, 2, 3):
            self._compact_state = 0
        self._compact_btn.setToolTip(
            "Cycle the playlist headers: full → 🗜 Compact (per-dance header rows\n"
            "hidden, each round lists its songs directly) → 🚫 No groups (round and\n"
            "─── section headers dropped too, so the list — a Practice / party\n"
            "list above all — is one flat run of songs) → 🔢 Numbers (no groups,\n"
            "plus an Nb. column up front counting the titles).")
        for t in self._deckset.all_tables:
            # Honoured when the tables render during restore. The wishlists are
            # in here too: flat lists have no headers to drop, but their titles
            # get numbered like everything else.
            t._compact = self._compact_state >= 1
            t._nogroup = self._compact_state >= 2
            t.set_numbered(self._compact_state >= 3)
        # Wishlist area cycle button: off → 1 → 2 → 3 → 4 wishlists → 4 stacked 2×2.
        self._wish_state = int(self._settings.get("wish_state", 1))
        if self._wish_state not in (0, 1, 2, 3, 4):
            self._wish_state = 1
        # 2×2 grid only applies with 4 wishlists; ignore a stale flag at other counts.
        self._wish_grid = bool(self._settings.get("wish_grid", False)) and self._wish_state == 4
        self._wish_grid_active = False   # what the splitters are actually wired as
        self._dual_wish_btn = QPushButton(self._wish_label())
        self._dual_wish_btn.setProperty("countEmoji", "⭐")
        self._dual_wish_btn.setProperty("countText", str(self._wish_state))
        self._dual_wish_btn.setIcon(counted_emoji("⭐", None, 16))
        self._dual_wish_btn.setIconSize(QSize(16, 16))
        self._dual_wish_btn.setToolTip(
            "Cycle the wishlist area: off → 1 → 2 → 3 → 4 → 4 stacked 2×2.\n"
            "Right click walks it backwards.\n"
            "Off hides it entirely, even with multiple decks.\n"
            "Double-click any deck/wishlist title to rename it.")
        self._warmup_toggle_btn = QPushButton("🤸  Practice / Party ▾")
        self._warmup_toggle_btn.setCheckable(True)
        # The two 🤸 buttons would be identical at icon size — keep the toggle's ▾
        # (a fixed icon caption, so a mode-driven relabel cannot drop it again).
        self._warmup_toggle_btn.setProperty("iconTextFixed", "🤸▾")
        self._lib_btn = QPushButton("📚  Library")
        self._lib_btn.setCheckable(True)
        self._lib_btn.setChecked(bool(self._settings.get("library_pane", True)))
        self._lib_btn.setToolTip(
            "Show / hide the library browser under the wishlists:\n"
            "filter the whole competition library and drag tracks\n"
            "straight into a deck or wishlist.")
        # Off by default: most tournaments never need sample pads.
        self._cartwall_shown = bool(self._settings.get("cartwall_pane", False))
        self._cart_btn = QPushButton("🎛  Cartwall")
        self._cart_btn.setCheckable(True)
        self._cart_btn.setChecked(self._cartwall_shown)
        self._cart_btn.setToolTip(
            "Show / hide the 🎛 sample-pad wall:\n"
            "drop Tusch, applause or a background bed onto a pad and tap it —\n"
            "it plays on top of the running music instead of replacing it.\n"
            "Drag its title bar to dock it left / right / below, or float it.")

    def _make_help_button(self):
        """❔ Shortcuts, manual and about, at the end of the toolbar."""
        help_btn = QPushButton("❔")
        help_btn.setFixedSize(24, 24)
        help_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        help_btn.setToolTip("Shortcuts (F1), manual and about this app")
        help_btn.clicked.connect(self._show_help_menu)
        self._help_btn = help_btn
        return help_btn

    def _setup_deck_grids(self):
        """The deck headers, the 2×2 grids and the tab widget that holds them."""
        # Decks side-by-side (top) + wishlists (bottom), each under its own header.
        self._rename_edit = None   # active inline header editor (one at a time)
        self._rename_finish = None # teardown callback for the active inline editor
        self._warmup_folded = False                              # Eintanzen panel compacted?
        self._warmup_closed = False                              # Eintanzen panel hidden?
        # Fixed A/B/C/D badge per deck, rendered before the (possibly renamed) title so
        # each playlist stays visually identifiable even after the user renames it.
        for t, letter in zip(self._deckset.decks,
                             ("🅰", "🅱", "🅲", "🅳", "🅴", "🅵", "🅶", "🅷"), strict=True):
            self.deck(t).letter = letter
        # Day decks carry outline (squared) letters so they never get confused
        # with the normal decks' filled 🅰–🅷 badges.
        for t, letter in zip(self._deckset.day_decks,
                             ("🄰", "🄱", "🄲", "🄳", "🄴", "🄵", "🄶", "🄷"), strict=True):
            self.deck(t).letter = letter
        deckA_box = self._make_deck_box(self._deckset.tableA, deck_name(1))
        self._grid.deckB_box = self._make_deck_box(self._deckset.tableB, deck_name(2))
        self._grid.deckC_box = self._make_deck_box(self._deckset.tableC, deck_name(3))
        self._grid.deckD_box = self._make_deck_box(self._deckset.tableD, deck_name(4))
        self._grid.deckE_box = self._make_deck_box(self._deckset.tableE, deck_name(5))
        self._grid.deckF_box = self._make_deck_box(self._deckset.tableF, deck_name(6))
        self._grid.deckG_box = self._make_deck_box(self._deckset.tableG, deck_name(7))
        self._grid.deckH_box = self._make_deck_box(self._deckset.tableH, deck_name(8))
        self._grid.day_boxes = [self._make_deck_box(t, f"📅 Competition {i + 1}")
                                for i, t in enumerate(self._deckset.day_decks)]
        self._grid.wish_box = self._make_deck_box(self._deckset.wishlist, wishlist_name(1))
        self._grid.wish_box2 = self._make_deck_box(self._deckset.wishlist2, wishlist_name(2))
        self._grid.wish_box3 = self._make_deck_box(self._deckset.wishlist3, wishlist_name(3))
        self._grid.wish_box4 = self._make_deck_box(self._deckset.wishlist4, wishlist_name(4))
        self._grid.warmup_box = self._make_deck_box(self._deckset.warmup_table,
                                               self._warmup_title(""))

        self._build_deck_grids(deckA_box)

        self._build_day_grids()

        # All grids live in a tab widget. In 1/2/4-deck modes the tab bar is hidden
        # and only the first page shows, so the deck area looks like a plain panel;
        # 8-deck mode reveals "Group E–H", a loaded day plan reveals "📅 Tournament day".
        self._grid.deck_tabs = QTabWidget()
        self._grid.deck_tabs.setDocumentMode(True)
        self._grid.deck_tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._grid.deck_tabs.addTab(self._grid.decks_split, "Group A–D")
        self._grid.deck_tabs.addTab(self._grid.decks_split2, "Group E–H")
        self._grid.deck_tabs.addTab(self._grid.day_tabs, "📅 Tournament day")
        # The 📅 tab only shows when its view is switched on (_apply_deck_view).
        self._grid.deck_tabs.setTabVisible(self._grid.day_page(), False)
        # ✕ on the 📅 tab closes the whole tournament-day view (clears the day
        # decks after a confirm); double-click on the tab renames it to the
        # competition name, e.g. "DanceComp 2026" (handled in eventFilter).
        self._day_tab_title = ""
        # Keeps the (empty) 📅 tab on screen after 🧹 Clear — only ✕ retires it.
        self._day_tab_keep = False
        day_close = QToolButton()
        day_close.setText("✕")
        day_close.setAutoRaise(True)
        day_close.setToolTip("Close the tournament day — clears all 📅 day decks")
        day_close.clicked.connect(self._close_day_plan)
        self._grid.deck_tabs.tabBar().setTabButton(
            self._grid.day_page(), QTabBar.ButtonPosition.RightSide, day_close)
        # A QTabWidget normally draws a pane border + margin around its pages; strip
        # both so a single-tab (≤4-deck) view is visually identical to the old layout.
        self._grid.deck_tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; margin: 0; } "
            "QTabWidget::tab-bar { left: 0; }")
        self._grid.deck_tabs.currentChanged.connect(self._on_deck_tab_changed)
        # Accept drag-hover on the tab bar: dragging a track onto a tab flips the
        # 8-deck view to that group's 4 decks so it can be dropped there (handled
        # in eventFilter). The tab bar itself takes no drop — it's just a switcher.
        self._grid.deck_tabs.tabBar().setAcceptDrops(True)
        # 🎛 Sample pads that fire OVER the deck music (Tusch, applause, a bed
        # under the Siegerehrung). Its own dock, not a tab — the wall is used
        # while watching the running heat, not instead of it.
        self._build_cartwall()

    def _build_deck_grids(self, deckA_box):
        """The two 2×2 grids of decks A–D and E–H."""
        # 2×2 grid of decks as two COLUMNS side by side: A above C (left) and
        # B above D (right). Built column-wise (not row-wise) so folding a deck
        # to a tab frees VERTICAL space for the other deck in the same column.
        # Single/Two-deck views use the top decks only.
        self._grid.decks_col1 = QSplitter(Qt.Orientation.Vertical)
        self._grid.decks_col1.addWidget(deckA_box)
        self._grid.decks_col1.addWidget(self._grid.deckC_box)
        self._grid.decks_col1.setSizes([500, 500])
        self._grid.decks_col2 = QSplitter(Qt.Orientation.Vertical)
        self._grid.decks_col2.addWidget(self._grid.deckB_box)
        self._grid.decks_col2.addWidget(self._grid.deckD_box)
        self._grid.decks_col2.setSizes([500, 500])
        self._grid.decks_split = QSplitter(Qt.Orientation.Horizontal)
        self._grid.decks_split.addWidget(self._grid.decks_col1)
        self._grid.decks_split.addWidget(self._grid.decks_col2)
        self._grid.decks_split.setSizes([500, 500])
        # One shared row divider for the whole 2×2 grid: dragging the 🅰/🅲
        # handle also moves the 🅱/🅳 handle and vice-versa, so all four decks keep
        # the same row heights (setSizes doesn't re-emit splitterMoved → no loop).
        self._grid.decks_col1.splitterMoved.connect(
            lambda *_: self._grid.decks_col2.setSizes(self._grid.decks_col1.sizes()))
        self._grid.decks_col2.splitterMoved.connect(
            lambda *_: self._grid.decks_col1.setSizes(self._grid.decks_col2.sizes()))

        # Second 2×2 grid (decks E–H), shown on the "Group E–H" tab in 8-deck mode.
        # Built exactly like the first grid: 🅴 above 🅶 (left), 🅵 above 🅷 (right).
        self._grid.decks_col3 = QSplitter(Qt.Orientation.Vertical)
        self._grid.decks_col3.addWidget(self._grid.deckE_box)
        self._grid.decks_col3.addWidget(self._grid.deckG_box)
        self._grid.decks_col3.setSizes([500, 500])
        self._grid.decks_col4 = QSplitter(Qt.Orientation.Vertical)
        self._grid.decks_col4.addWidget(self._grid.deckF_box)
        self._grid.decks_col4.addWidget(self._grid.deckH_box)
        self._grid.decks_col4.setSizes([500, 500])
        self._grid.decks_split2 = QSplitter(Qt.Orientation.Horizontal)
        self._grid.decks_split2.addWidget(self._grid.decks_col3)
        self._grid.decks_split2.addWidget(self._grid.decks_col4)
        self._grid.decks_split2.setSizes([500, 500])
        self._grid.decks_col3.splitterMoved.connect(
            lambda *_: self._grid.decks_col4.setSizes(self._grid.decks_col3.sizes()))
        self._grid.decks_col4.splitterMoved.connect(
            lambda *_: self._grid.decks_col3.setSizes(self._grid.decks_col4.sizes()))

    def _build_day_grids(self):
        """The 📅 day decks' two 2×2 grids and the sub-tabs holding them."""
        # Two more 2×2 grids for the 📅 day decks, mirroring the normal groups:
        # day 🄰 above 🄲 (left) and 🄱 above 🄳 (right), same for 🄴–🄷. They live
        # in their own sub-tab widget on the "📅 Tournament day" page.
        self._grid.day_col1 = QSplitter(Qt.Orientation.Vertical)
        self._grid.day_col1.addWidget(self._grid.day_boxes[0])
        self._grid.day_col1.addWidget(self._grid.day_boxes[2])
        self._grid.day_col1.setSizes([500, 500])
        self._grid.day_col2 = QSplitter(Qt.Orientation.Vertical)
        self._grid.day_col2.addWidget(self._grid.day_boxes[1])
        self._grid.day_col2.addWidget(self._grid.day_boxes[3])
        self._grid.day_col2.setSizes([500, 500])
        self._grid.day_split = QSplitter(Qt.Orientation.Horizontal)
        self._grid.day_split.addWidget(self._grid.day_col1)
        self._grid.day_split.addWidget(self._grid.day_col2)
        self._grid.day_split.setSizes([500, 500])
        self._grid.day_col1.splitterMoved.connect(
            lambda *_: self._grid.day_col2.setSizes(self._grid.day_col1.sizes()))
        self._grid.day_col2.splitterMoved.connect(
            lambda *_: self._grid.day_col1.setSizes(self._grid.day_col2.sizes()))
        self._grid.day_col3 = QSplitter(Qt.Orientation.Vertical)
        self._grid.day_col3.addWidget(self._grid.day_boxes[4])
        self._grid.day_col3.addWidget(self._grid.day_boxes[6])
        self._grid.day_col3.setSizes([500, 500])
        self._grid.day_col4 = QSplitter(Qt.Orientation.Vertical)
        self._grid.day_col4.addWidget(self._grid.day_boxes[5])
        self._grid.day_col4.addWidget(self._grid.day_boxes[7])
        self._grid.day_col4.setSizes([500, 500])
        self._grid.day_split2 = QSplitter(Qt.Orientation.Horizontal)
        self._grid.day_split2.addWidget(self._grid.day_col3)
        self._grid.day_split2.addWidget(self._grid.day_col4)
        self._grid.day_split2.setSizes([500, 500])
        self._grid.day_col3.splitterMoved.connect(
            lambda *_: self._grid.day_col4.setSizes(self._grid.day_col3.sizes()))
        self._grid.day_col4.splitterMoved.connect(
            lambda *_: self._grid.day_col3.setSizes(self._grid.day_col4.sizes()))
        self._grid.day_tabs = QTabWidget()
        self._grid.day_tabs.setDocumentMode(True)
        self._grid.day_tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._grid.day_tabs.addTab(self._grid.day_split, "Group A–D")
        self._grid.day_tabs.addTab(self._grid.day_split2, "Group E–H")
        self._grid.day_tabs.currentChanged.connect(self._on_day_tab_changed)
        # Drag-hover flips the day sub-tab too (handled in eventFilter).
        self._grid.day_tabs.tabBar().setAcceptDrops(True)
        # 🧹 in the day page's tab row: empty all day playlists (with confirm) —
        # unlike the tab's ✕ this reads as "clear", and the tab name is kept.
        day_clear = QToolButton()
        day_clear.setText("🧹")
        day_clear.setAutoRaise(True)
        day_clear.setToolTip("Clear all tournament-day playlists")
        day_clear.clicked.connect(self._clear_day_plan)
        self._grid.day_tabs.setCornerWidget(day_clear, Qt.Corner.TopRightCorner)

    def _setup_lower_panes(self, rl, saved_cols, saved_widths):
        """Wishlists, warm-up panel and library pane below the decks."""
        # The wishlist area is a horizontal splitter. In the default row layout it holds
        # the 4 wishlist boxes directly; in 2×2 grid mode (4 wishlists only) it instead
        # holds two vertical column splitters — wish 1/3 left, wish 2/4 right, mirroring
        # the deck grid. _rebuild_wish_layout reparents the boxes between the two shapes.
        self._grid.wish_col1 = QSplitter(Qt.Orientation.Vertical)
        self._grid.wish_col2 = QSplitter(Qt.Orientation.Vertical)
        # One shared row divider for the 2×2 grid (drag either handle, both move).
        self._grid.wish_col1.splitterMoved.connect(
            lambda *_: self._grid.wish_col2.setSizes(self._grid.wish_col1.sizes()))
        self._grid.wish_col2.splitterMoved.connect(
            lambda *_: self._grid.wish_col1.setSizes(self._grid.wish_col2.sizes()))
        self._grid.wish_split = QSplitter(Qt.Orientation.Horizontal)
        self._rebuild_wish_layout()
        # Remember the user's manual divider drags per wish-state (2 vs 3 vs 4 visible
        # wishlists each keep their own layout); _update_wish_area replays these instead
        # of snapping back to the default ratio. Persisted across sessions in _save_layout.
        self._wish_sizes: dict[int, list[int]] = {}
        self._grid.wish_split.splitterMoved.connect(self._on_wish_split_moved)

        self._grid.right_split = QSplitter(Qt.Orientation.Vertical)
        self._grid.right_split.addWidget(self._grid.deck_tabs)
        # Warm-up (Eintanzen) panel sits ABOVE the wishlist, BELOW the playlists;
        # hidden until a warm-up is generated (or restored from autosave).
        self._grid.right_split.addWidget(self._grid.warmup_box)
        self._grid.warmup_box.setVisible(False)
        self._grid.right_split.addWidget(self._grid.wish_split)
        # Library browser docked under the wishlists — foldable to its header,
        # fully hideable via the 📚 toolbar toggle.
        self._lib_browser = LibraryBrowser()
        self._lib_browser.setProperty(NEEDS_LIBRARY, True)   # empty until the scan is done
        self._lib_browser.playRequested.connect(self._on_lib_play)
        self._lib_browser.unplannedToggled.connect(self._on_lib_unplanned_toggled)
        self._lib_browser.wholeLibraryWanted.connect(self._show_whole_library)
        self._lib_browser.wholeLibraryDropped.connect(self._stop_whole_wait)
        self._lib_browser.wholeRescanWanted.connect(self._rescan_repository)
        self._lib_browser.foldToggled.connect(self._on_lib_fold_toggled)
        self._lib_browser.columnOrderChanged.connect(self._on_lib_columns_reordered)
        self._lib_browser.columnWidthsChanged.connect(self._on_lib_column_widths)
        self._lib_browser.columnsChanged.connect(self._on_lib_columns_hidden)
        self._lib_browser.danceNamesChanged.connect(self._on_lib_dance_names)
        self._lib_browser.playCountsResetWanted.connect(self._reset_play_counts)
        self._lib_browser._table.seek_cb = self._prehear_seek   # Ctrl+←/→ seeks ∓30 s
        saved_widths = self._settings.get("library_col_widths")
        if isinstance(saved_widths, dict):
            self._lib_browser.apply_column_widths(saved_widths)
        saved_cols = self._settings.get("library_columns")
        if isinstance(saved_cols, list):
            self._lib_browser.apply_column_order([int(c) for c in saved_cols])
        saved_hidden = self._settings.get("library_hidden_columns")
        if isinstance(saved_hidden, list):
            self._lib_browser.set_hidden_columns([int(c) for c in saved_hidden])
        self._lib_browser.set_short_dances(
            bool(self._settings.get("library_short_dances")))
        # 🏆 The tournament tree shares the pane as a second tab: both are ways
        # of finding music to drag onto a deck, and the desk has the vertical
        # space for one of them, not two.
        self._tourney_tree = TournamentTree(TOURNAMENTS)
        self._tourney_tree.setProperty(NEEDS_LIBRARY, True)
        self._tourney_tree.playRequested.connect(
            lambda path, row: self._on_lib_play(path, row, self._tourney_tree))
        self._tourney_tree.loadRequested.connect(self._load_tournament_m3u)
        self._tourney_tree.playCountsResetWanted.connect(self._reset_play_counts)
        self._tourney_tree._table.seek_cb = self._prehear_seek   # Ctrl+←/→ seeks ∓30 s
        # A tournament list may point outside the library (an older copy of the
        # collection, a stick) — those tracks are read off the file itself.
        def _external_entry(p: Path) -> MusicEntry | None:
            lib, cache = self._library.lib, self._library.cache
            return lib.make_external_entry(p, cache) if lib and cache else None
        self._tourney_tree.resolve_entry = _external_entry
        self._lib_tabs = QTabWidget()
        self._lib_tabs.setDocumentMode(True)
        self._lib_tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; margin: 0; } "
            "QTabWidget::tab-bar { left: 0; }")
        self._lib_tabs.addTab(self._lib_browser, "📚  Library")
        self._lib_tabs.addTab(self._tourney_tree, "🏆  Tournaments")
        self._lib_tabs.currentChanged.connect(self._on_lib_tab_changed)
        self._grid.right_split.addWidget(self._lib_tabs)
        self._grid.right_split.setStretchFactor(0, 1)
        self._grid.right_split.setSizes([560, 200, 160, 160])
        self._lib_tabs.setVisible(bool(self._settings.get("library_pane", True)))
        if self._settings.get("library_folded"):
            self._lib_browser.set_folded(True)
        # The ▾ in the tab bar's corner folds the pane as a whole — built last
        # so its restore has the final say over the browser's own fold above.
        self._build_lib_pane_fold_btn()
        # Folded tabs ARE the minimized representation — never let a splitter
        # collapse a pane to 0px on top of that (the tabs would vanish with no
        # way to unfold them).
        for s in (self._grid.decks_col1, self._grid.decks_col2, self._grid.decks_split,
                  self._grid.decks_col3, self._grid.decks_col4, self._grid.decks_split2,
                  self._grid.wish_col1, self._grid.wish_col2,
                  self._grid.wish_split, self._grid.right_split):
            s.setChildrenCollapsible(False)
        rl.addWidget(self._grid.right_split, stretch=1)

        # Single-playlist view by default; _dual_btn reveals decks 2–4 / wishlists.
        self._grid.wish_box2.setVisible(False)
        self._grid.wish_box3.setVisible(False)
        self._grid.wish_box4.setVisible(False)
        self._apply_deck_view()   # hides decks B/C/D for _deck_count == 1
        self._focused_table = self._deckset.tableA   # Ctrl+S target, updated on focus
        # The list whose own play values the panel shows and edits.
        self._panel_table = self._focused_table
        self._set_active_table(self._deckset.tableA)
