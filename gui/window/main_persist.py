"""Serialize / restore playlist state, autosave, undo-redo, layout.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import contextlib
import json
import logging
import os

from PySide6.QtCore import (
    QSettings,
    Qt,
)
from PySide6.QtWidgets import (
    QMessageBox,
)

from gui.common import (
    CART_DOCK_SHARE,
)
from gui.decks.deck_snapshot import playlist_from_grid, serialize_deck
from gui.dialogs import (  # auto-resolved
    AUTOSAVE_VERSION,
    save_autosave,
)
from gui.table.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.window.main_export import ExportMixin
from gui.window.main_restore import RestoreMixin
from gui.window.main_undo import UndoMixin
from gui.window.session_env import (
    ALL_DECK_KEYS,
    DAY_KEYS,
    WISH_KEYS,
    SessionEnv,
)
from planner import i18n
from planner.generate.suggester import PlaylistSuggester
from planner.store import state_dir
from shared.widgets import (
    show_toast,
)

log = logging.getLogger("dancesport.gui.persist")


def layout_settings() -> QSettings:
    """The store for the window size, every divider and the 🎛 dock.

    The registry, unless DANCEPLAYLIST_STATE_DIR redirects the app's state:
    then an INI file beside the rest of it. Without that, every test window
    that closed wrote its offscreen layout over the operator's real one."""
    if os.environ.get("DANCEPLAYLIST_STATE_DIR"):
        return QSettings(str(state_dir() / "layout.ini"),
                         QSettings.Format.IniFormat)
    return QSettings("danceplaylist_ai", "planner")


class PersistenceMixin(ExportMixin, UndoMixin, RestoreMixin):
    """Serializing the desk: what a deck IS, as a dict, the autosave of it, and
    🪟 the window geometry QSettings remembers alongside.

    The rest went next door: 💾 export (gui.window.main_export), ↶ undo
    (gui.window.main_undo) and 📥 restore (gui.window.main_restore). MainWindow keeps
    importing this one name.
    """

    def _clear_all_playlists(self):
        """🧹 Clear-all: empty every playlist deck after one confirm. Wishlists are
        left untouched (clear those individually with Del on their header)."""
        decks = [t for t in self._deckset.decks + self._deckset.day_decks if t.rowCount() > 0]
        if not decks:
            self.statusBar().showMessage("Nothing to clear — all playlists are empty.")
            return
        n = len(decks)
        ans = QMessageBox.question(
            self, "Clear all playlists",
            (i18n.t("Empty %d playlist? This can't be undone.") if n == 1
             else i18n.t("Empty %d playlists? This can't be undone.")) % n,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        for t in self._deckset.decks + self._deckset.day_decks:
            self._blank_deck(t)
        self._apply_deck_view()   # clearing the day plan also retires the 📅 tab
        self._autosave_playlist()
        self.statusBar().showMessage("🧹 Cleared all playlists.")

    def _stash_active_replay(self):
        """Stash the currently shown replay grid (if any) before another mode's
        generation replaces it, then forget which competition was active."""
        if self._active_replay_idx is not None:
            self._stash_replay_work(self._active_replay_idx)
        self._active_replay_idx = None

    def _stash_replay_work(self, idx: int):
        """Snapshot the working grid for competition `idx` so it can be restored."""
        grid = self._serialize_playlist_state()
        if not grid or grid.get("mode") != "Favorites":
            return   # nothing worth keeping (empty grid / theme)
        self._replay_work[idx] = {
            "grid": grid,
            "rounds": self._replay_rounds,
            "pools": self._replay_pools,
            "use_timbre": self._replay_use_timbre,
            "label": self._replay_label,
            "dances": self._dances,
            "dance_class": self._dance_class,
            "style": self._style,
            "age": self._age,
        }

    def _restore_replay_work(self, idx: int):
        """Re-show the previously worked grid for competition `idx`."""
        work = self._replay_work.get(idx)
        if not work:
            return
        dances = work["dances"]
        rounds = work["rounds"]
        playlist = self._playlist_from_grid(work["grid"].get("rounds") or [], len(dances))

        self._suggester = PlaylistSuggester(self._library.lib)
        self._playlist = playlist
        self._mode = "Favorites"
        self._ui_mode = "Past Competitions"
        self._theme_entries = []
        self._replay_active = True
        self._replay_rounds = rounds
        self._replay_pools = work["pools"]
        self._replay_use_timbre = work["use_timbre"]
        self._replay_label = work["label"]
        self._dances = dances
        self._dance_class = work["dance_class"]
        self._style = work["style"]
        self._age = work["age"]

        self._deckset.table.load(
            playlist, dances, rounds, self._dance_class,
            play_cb=self._play_or_stop, suggester=self._suggester,
            use_timbre=self._replay_use_timbre, style=self._style,
            round_pools=self._effective_replay_pools(),
        )
        self._cfg.save_btn.setEnabled(True)
        total = sum(1 for hl in playlist.values()
                    for h in hl for e in h if e is not None)
        self.statusBar().showMessage(
            i18n.t("↩  Restored your worked playlist for “%s” — %d songs")
            % (work.get('age') or i18n.t("this competition"), total)
        )

    def _playlist_from_grid(self, rounds_data: list, n_dances: int,
                            progress_cb=None) -> dict:
        """The saved grid rebuilt against this window's library (see
        deck_snapshot.playlist_from_grid)."""
        return playlist_from_grid(rounds_data, n_dances, self._resolve_entry,
                                  progress_cb)

    def _deck_meta(self, table: PlaylistTable) -> dict:
        """Generation context (mode/style/class/age/theme) for a deck."""
        ctx = self._focused_ctx() if table is self._deckset.table else self.deck(table).ctx
        if ctx is None:   # never generated, never focused
            return {"mode": "Favorites", "ui_mode": "Favorites", "style": "Latin",
                    "dance_class": "S", "age": "", "theme_label": ""}
        return {"mode": ctx.mode, "ui_mode": ctx.ui_mode, "style": ctx.style,
                "dance_class": ctx.dance_class, "age": ctx.age,
                "theme_label": ctx.theme_label}

    def _serialize_playlist_state(self, table: PlaylistTable | None = None) -> dict | None:
        """A deck's snapshot with its generation context (see
        deck_snapshot.serialize_deck); the focused deck by default."""
        table = table or self._deckset.table
        return serialize_deck(table, self._deck_meta(table))

    def _warmup_state(self) -> dict:
        """Serialize the dedicated Eintanzen panel: its track paths + the warm-up
        params needed to re-roll. Empty dict when no warm-up list is loaded.

        A running order dropped onto the panel keeps its rounds here too, or the
        next start would cut the strips as a warm-up list again."""
        t = self._deckset.warmup_table
        if not getattr(t, "_warmup", False) or not t._row_meta:
            return {}
        return {
            "paths": [str(e.path) for e in t.wishlist_entries()],
            "player_list": bool(getattr(t, "_player_list", False)),
            "player_sections": dict(getattr(t, "_player_sections", {}) or {}),
            "style": getattr(t, "_warmup_style", "") or "",
            "dance_class": getattr(t, "_warmup_class", "") or "S",
            "relax": bool(getattr(t, "_warmup_relax", True)),
            "label": getattr(t, "_warmup_label", "") or self._warmup_default_name(),
            "folded": bool(getattr(self, "_warmup_folded", False)),
            "closed": bool(getattr(self, "_warmup_closed", False)),
        }

    def _build_env(self) -> dict | None:
        """Snapshot the entire UI state (all decks + wishlists + names + view).

        Returns the serializable env dict, or None if nothing could be built.
        """
        try:
            env = {
                "version": AUTOSAVE_VERSION,
                "deck_count": self._deckset.deck_count,
                "dual": self._deckset.deck_count > 1,   # legacy flag (back-compat)
                "dual_wish": self._wish_state == 2,   # legacy flag (back-compat)
                "wish_state": self._wish_state,
                "wish_grid": bool(getattr(self, "_wish_grid", False)),
                "deck_a": self._serialize_playlist_state(self._deckset.tableA),
                "deck_b": self._serialize_playlist_state(self._deckset.tableB),
                "deck_c": self._serialize_playlist_state(self._deckset.tableC),
                "deck_d": self._serialize_playlist_state(self._deckset.tableD),
                "deck_e": self._serialize_playlist_state(self._deckset.tableE),
                "deck_f": self._serialize_playlist_state(self._deckset.tableF),
                "deck_g": self._serialize_playlist_state(self._deckset.tableG),
                "deck_h": self._serialize_playlist_state(self._deckset.tableH),
                "wishlist": [str(e.path) for e in self._deckset.wishlist.wishlist_entries()],
                "wishlist2": [str(e.path) for e in self._deckset.wishlist2.wishlist_entries()],
                "wishlist3": [str(e.path) for e in self._deckset.wishlist3.wishlist_entries()],
                "wishlist4": [str(e.path) for e in self._deckset.wishlist4.wishlist_entries()],
                "names": {
                    "deck_a": self.deck(self._deckset.tableA).name,
                    "deck_b": self.deck(self._deckset.tableB).name,
                    "deck_c": self.deck(self._deckset.tableC).name,
                    "deck_d": self.deck(self._deckset.tableD).name,
                    "deck_e": self.deck(self._deckset.tableE).name,
                    "deck_f": self.deck(self._deckset.tableF).name,
                    "deck_g": self.deck(self._deckset.tableG).name,
                    "deck_h": self.deck(self._deckset.tableH).name,
                    "wishlist": self.deck(self._deckset.wishlist).name,
                    "wishlist2": self.deck(self._deckset.wishlist2).name,
                    "wishlist3": self.deck(self._deckset.wishlist3).name,
                    "wishlist4": self.deck(self._deckset.wishlist4).name,
                },
                # Dedicated Eintanzen panel (paths + re-roll params), separate from
                # the decks and the wishlists.
                "warmup": self._warmup_state(),
                # Custom 📅 tab label (competition name), "" = default.
                "day_tab": getattr(self, "_day_tab_title", ""),
                # The 📅 tab stays open with no tracks in it (opened by hand
                # under a competition name, or 🧹 cleared) until ✕ closes it.
                "day_tab_keep": bool(getattr(self, "_day_tab_keep", False)),
            }
            # The eight 📅 day decks (day_a … day_h) — v4 additions.
            for key, t in zip(DAY_KEYS, self._deckset.day_decks, strict=True):
                env[key] = self._serialize_playlist_state(t)
                env["names"][key] = self.deck(t).name
            # The 🔒/🔓/✋ toggle of every deck. A deck WITH tracks carries its
            # mode inside its own state above; an empty one has no state at all
            # to carry it, so the mode it was left in would be back to 🔒 static
            # at the next start.
            env["deck_modes"] = {
                key: self._deck_own_mode(t)
                for key, t in zip(ALL_DECK_KEYS,
                                  self._deckset.decks + self._deckset.day_decks, strict=True)}
            # The play values of every list that has been given some (see
            # `_list_vals`) — the 🤸 panel too, under its own key. A list not
            # listed is seeded afresh on its first use after the restart.
            env["list_play"] = {
                key: dict(t._play_vals)
                for key, t in zip(ALL_DECK_KEYS + WISH_KEYS + ("warmup",),
                                  self._deckset.decks + self._deckset.day_decks
                                  + self._deckset.wishlists + [self._deckset.warmup_table], strict=True)
                if t._play_vals is not None}
            # The .m3u each deck / wishlist was loaded from or last saved to (📂 on
            # its header).
            env["m3u_paths"] = {
                key: str(t._m3u_path)
                for key, t in zip(ALL_DECK_KEYS + WISH_KEYS,
                                  self._deckset.decks + self._deckset.day_decks + self._deckset.wishlists, strict=True)
                if t._m3u_path is not None}
            return env
        except Exception as exc:
            # Loud: every edit autosaves through here, so a silent None stopped
            # the autosave for the rest of the evening without a word.
            log.exception("⚠️ Session snapshot failed — the session is not saved")
            self.statusBar().showMessage(
                i18n.t("⚠  Session not saved — the snapshot failed: %r") % (exc,))
            return None

    def _autosave_playlist(self):
        """Persist both decks + the wishlist (called after every grid edit)."""
        self._update_wish_counts()
        self._sync_loudness_available()   # playlist content changed → re-gate 🔊
        # Keep the library's 🆕 Unplanned filter in sync with deck contents.
        self._refresh_library_planned_filter()
        # While an undo/redo restore is in flight, don't snapshot the half-applied
        # state — _apply_env saves the authoritative snapshot itself.
        if getattr(self, "_restoring", False):
            return
        env = self._build_env()
        if env is None:
            return
        modes = env.get("deck_modes") or {}
        before = self._undo_timeline.current
        if (SessionEnv(env).holds_tracks()
                # …or the desk was just emptied (🧹, Del on a header): the last
                # state held tracks, and the restart must not bring them back.
                # An empty start or a failed restore never held any.
                or (before is not None and SessionEnv(before).holds_tracks())
                # …or nothing is loaded yet but a deck has been switched out of
                # 🔒 static: that toggle is the only thing worth saving then.
                or any(m != "static" for m in modes.values())
                # …or an empty 📅 tab under a name typed by hand.
                or env.get("day_tab_keep")):
            save_autosave(env)
        self._push_undo(env)

    def _save_state_now(self):
        """📌 toolbar button: persist the whole working session right now — every
        deck/wishlist plus the window layout — instead of relying on the implicit
        save-on-edit / save-on-close."""
        self._autosave_playlist()
        self._save_layout()
        # The wall writes itself on every edit already; 📌 covers it too so the
        # button means what it says — nothing in the session is left unwritten.
        self._save_cartwall(edit=False)
        msg = "📌 Session saved — decks, wishlists, 🎛 cartwall and layout."
        self.statusBar().showMessage(msg)
        show_toast(self, msg)

    def save_on_quit(self):
        """Persist the working playlist + window layout one last time before quitting.

        Called from MainWindow.closeEvent, NOT named closeEvent itself: QMainWindow
        comes first in MainWindow's bases, so QWidget.closeEvent would shadow a
        mixin one and nothing here would ever run."""
        self._autosave_playlist()
        self._save_layout()
        # A fader moved in the last 600 ms is still waiting on its save, and
        # the quit ends the process before that timer would run.
        if self._vol_save_timer.isActive():
            self._vol_save_timer.stop()
            self._save_master_volume()

    # ── Window / splitter layout persistence ────────────────────────────────────
    def _layout_settings(self) -> QSettings:
        return layout_settings()

    def _restore_layout(self):
        """Bring back the window size + every divider position from the last session
        (config-panel width, deck column widths, wishlist height, …)."""
        s = self._layout_settings()
        geo = s.value("win/geometry")
        if geo is not None:
            try:
                self.restoreGeometry(geo)
            except Exception as exc:
                log.debug("📐 Stored window geometry rejected: %s", exc)
            # A session that ended in fullscreen comes back fullscreen, past
            # set_fullscreen: start the clock it would have started.
            if self.windowState() & Qt.WindowState.WindowFullScreen:
                self.set_fullscreen(True)
        # Dock layout — which edge the 🎛 cartwall sits on, how wide it is, and
        # whether it was left floating. It also restores dock VISIBILITY, so the
        # toolbar toggle re-asserts its own setting right after.
        st = s.value("win/state")
        if st is not None:
            try:
                self.restoreState(st)
            except Exception as exc:
                log.debug("📐 Stored dock state rejected: %s", exc)
        else:
            # No saved layout: the wall may be dragged narrow, so Qt would open it
            # at that floor next to a hungry central widget. Hand it a quarter
            # of the window instead.
            self.resizeDocks([self._cart_dock], [round(self.width() * CART_DOCK_SHARE)],
                             Qt.Orientation.Horizontal)
        self._cart_dock.setVisible(self._cartwall_shown)
        # Deck view + 2nd-wishlist toggle decide which dividers are even visible, so
        # restore them BEFORE the splitter handle positions.
        dc = s.value("layout/deck_count")
        try:
            dc = int(dc)
        except (TypeError, ValueError):
            dc = None
        if dc in (0, 1, 2, 4, 8):
            self._deckset.deck_count = dc
        ws = s.value("layout/wish_state")
        if ws is not None:
            with contextlib.suppress(TypeError, ValueError):
                self._wish_state = (int(ws) if int(ws) in (0, 1, 2, 3, 4)
                                    else self._wish_state)
        else:   # legacy layout key: dual_wish bool → 2 wishlists
            dw = s.value("layout/dual_wish")
            if dw is not None and not isinstance(dw, bool):
                dw = str(dw).lower() in ("1", "true", "yes")
            if dw:
                self._wish_state = 2
        wg = s.value("layout/wish_grid")
        if wg is not None and not isinstance(wg, bool):
            wg = str(wg).lower() in ("1", "true", "yes")
        self._wish_grid = bool(wg) and self._wish_state == 4
        self._rebuild_wish_layout()
        self._set_toolbar_btn_text(self._dual_wish_btn, self._wish_label())
        # Remembered wishlist divider layouts (keyed by visible count) — load BEFORE
        # _apply_deck_view so _update_wish_area replays them instead of the default ratio.
        raw = s.value("layout/wish_sizes")
        if raw:
            try:
                self._wish_sizes = {int(k): [int(x) for x in v]
                                    for k, v in json.loads(raw).items()}
            except Exception as exc:
                log.debug("📐 Stored wishlist divider layout unreadable: %s", exc)
        self._apply_deck_view()
        for name, sp in self._persist_splitters.items():
            st = s.value(f"split/{name}")
            if st is not None:
                try:
                    sp.restoreState(st)
                except Exception as exc:
                    log.debug("📐 Stored splitter state for %s rejected: %s", name, exc)
        # Re-fold the decks that were folded to a tab last session (AFTER the
        # splitter states, so the fold clamps win over the restored pane sizes).
        fv = s.value("layout/folded")
        if fv:
            keys = {"a": self._deckset.tableA, "b": self._deckset.tableB,
                    "c": self._deckset.tableC, "d": self._deckset.tableD,
                    "e": self._deckset.tableE, "f": self._deckset.tableF,
                    "g": self._deckset.tableG, "h": self._deckset.tableH,
                    "w1": self._deckset.wishlist, "w2": self._deckset.wishlist2,
                    "w3": self._deckset.wishlist3, "w4": self._deckset.wishlist4}
            for k in str(fv).split(","):
                t = keys.get(k.strip())
                if t is not None:
                    self._toggle_deck_fold(t, True)

    def _save_layout(self):
        """Persist the window size + divider positions so the next launch matches."""
        s = self._layout_settings()
        try:
            s.setValue("win/geometry", self.saveGeometry())
            s.setValue("win/state", self.saveState())
            s.setValue("layout/deck_count", int(self._deckset.deck_count))
            s.setValue("layout/wish_state", int(self._wish_state))
            s.setValue("layout/wish_grid", bool(getattr(self, "_wish_grid", False)))
            s.setValue("layout/folded", ",".join(
                k for k, t in (("a", self._deckset.tableA), ("b", self._deckset.tableB),
                               ("c", self._deckset.tableC), ("d", self._deckset.tableD),
                               ("e", self._deckset.tableE), ("f", self._deckset.tableF),
                               ("g", self._deckset.tableG), ("h", self._deckset.tableH),
                               ("w1", self._deckset.wishlist), ("w2", self._deckset.wishlist2),
                               ("w3", self._deckset.wishlist3), ("w4", self._deckset.wishlist4))
                if self.deck(t).folded))
            for name, sp in self._persist_splitters.items():
                s.setValue(f"split/{name}", sp.saveState())
            # Per-wish-state divider layouts the user dragged (keyed by visible count).
            s.setValue("layout/wish_sizes", json.dumps(self._wish_sizes))
        except Exception as exc:
            log.warning("📐 Layout not saved — it will not come back next session: %s", exc)
