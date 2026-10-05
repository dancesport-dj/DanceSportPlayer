"""📥 Restoring a saved state: an autosave env back into the decks.

Split off gui/main_persist.py as a MainWindow mixin — the reading half of the
serialize/restore pair, one deck kind at a time (grid, favorites, running order,
theme list).
"""
from dataclasses import replace
from pathlib import Path

from planner import i18n
from planner.models import MusicEntry, RoundConfig
from planner.suggester import PlaylistSuggester
from gui.dialogs import (  # auto-resolved
    keep_autosave_copy,
    load_autosave,
    save_autosave,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.session_env import (
    ALL_DECK_KEYS,
    WISH_KEYS,
    SessionEnv,
)

class RestoreMixin:
    """📥 Putting a saved environment back into the decks."""

    def _restore_env(self, data: dict, *, deck_modes: bool = False,
                     wish_default: bool = False):
        """Put one saved env back on the desk: sixteen decks, the 📅 tab title,
        four wishlists, the Eintanzen panel, every custom title, the deck view
        and the wishlist view.

        Both readers of an env run this — the startup restore and every
        undo/redo — and they used to be two copies of it that had already
        drifted apart. They really differ only in what a MISSING piece of the
        env means. At startup the file is all there is, so an env that says
        nothing about the wishlist view leaves the view alone, and the
        🔒/🔓/✋ toggle of a deck that came back empty is replayed by hand
        (`deck_modes`). An undo step is the whole truth about one moment, so a
        missing wishlist view there means "one wishlist" (`wish_default`), not
        "keep whatever is on screen"."""
        for key, table in zip(ALL_DECK_KEYS, self._decks + self._day_decks):
            if data.get(key):
                self._restore_into_deck(table, data[key])
        if deck_modes:
            self._restore_deck_modes(data.get("deck_modes") or {})
            self._restore_list_play(data.get("list_play") or {},
                                    data.get("deck_advance") or {})
        self._set_day_tab_title(data.get("day_tab") or "")
        self._day_tab_keep = bool(data.get("day_tab_keep"))

        for key, tbl in zip(WISH_KEYS, self._wishlists):
            ents = [e for e in (self._resolve_entry(p)
                                for p in (data.get(key) or [])) if e]
            if ents:
                tbl.load_wishlist(ents, play_cb=self._play_or_stop,
                                  suggester=PlaylistSuggester(self._lib))
        self._restore_warmup_state(data.get("warmup"))

        names = data.get("names") or {}
        for key, table in zip(ALL_DECK_KEYS + WISH_KEYS,
                              self._decks + self._day_decks + self._wishlists):
            if names.get(key):
                self._set_deck_name(table, names[key])
        files = data.get("m3u_paths") or {}
        for key, table in zip(ALL_DECK_KEYS + WISH_KEYS,
                              self._decks + self._day_decks + self._wishlists):
            table._m3u_path = Path(files[key]) if files.get(key) else None

        self._deck_count = self._env_deck_count(data)
        self._apply_deck_view()
        if "wish_state" in data:
            self._set_wish_state(int(data.get("wish_state") or 0),
                                 grid=bool(data.get("wish_grid")))
        elif data.get("dual_wish") or data.get("wishlist2"):
            # Legacy snapshot: the boolean flag, or a 2nd wishlist's tracks.
            self._set_wish_state(2, grid=bool(data.get("wish_grid")))
        elif wish_default:
            self._set_wish_state(1, grid=bool(data.get("wish_grid")))
        self._set_active_table(self._tableA)

    @staticmethod
    def _env_deck_count(data: dict) -> int:
        """How many decks the view showed. Trust a valid saved count; only INFER
        it from content for legacy files that lack one — decks E–H can still hold
        tracks after the view was cycled back down to 4, so content alone must
        not force the count up."""
        count = data.get("deck_count")
        if count in (0, 1, 2, 4, 8):
            return count
        count = 2 if (data.get("dual") or data.get("deck_b")
                      or data.get("wishlist")) else 1
        if data.get("deck_c") or data.get("deck_d"):
            count = 4
        if any(data.get(k) for k in ("deck_e", "deck_f", "deck_g", "deck_h")):
            count = 8
        return count

    def _apply_env(self, data: dict):
        """Restore a full snapshot built by _build_env: wipe every deck + wishlist,
        then rebuild from the snapshot. Guarded so the rebuild's edit hooks don't
        feed back into the undo timeline."""
        self._restoring = True
        try:
            for table in self._decks + self._day_decks:
                self._blank_deck(table)
            for wl in self._wishlists:
                wl.load_wishlist([], play_cb=self._play_or_stop, suggester=None)
            self._restore_env(data, wish_default=True)
        except Exception as exc:
            self.statusBar().showMessage(i18n.t("Could not apply snapshot: %s") % exc)
        finally:
            self._restoring = False
        self._update_wish_counts()
        save_autosave(data)

    def _resolve_entry(self, path: str) -> MusicEntry | None:
        """Find a saved path in the library, else rebuild it as an external entry,
        else None (file gone)."""
        if not self._lib:
            return None
        return self._lib.entry_for(path, self._cache, require_file=True)

    def _resolve_paths(self, paths: list[str], progress_cb=None) -> list:
        """`_resolve_entry` over a flat list, reporting as it goes and dropping
        what no longer exists (see `_playlist_from_grid` for why it is slow)."""
        out = []
        total = len(paths)
        for i, p in enumerate(paths, 1):
            e = self._resolve_entry(p)
            if e is not None:
                out.append(e)
            if progress_cb:
                progress_cb(i, total, Path(p).name)
        return out

    def _restore_playlist(self):
        """Reload the autosaved decks + wishlist from the last session, if any."""
        # A new session starts with a clean slate: nothing counts as already
        # played, even though the decks themselves are restored.
        for t in self._all_tables:
            t.reset_played_marks()
        data = load_autosave()
        if not data or not self._lib:
            return
        # Guard the whole restore: each table.load() fires the change-callback
        # autosave, which would otherwise re-save the file with the still-default
        # deck names (applied only at the end) and clobber the real titles.
        self._restoring = True
        failed = None
        try:
            if data.get("version") == 1:
                # Legacy single-playlist file → restore into deck A.
                self._restore_into_deck(self._tableA, data)
                # Front the primary deck's context again (a deck B restore
                # leaves the globals stale) — _restore_env does this itself.
                self._set_active_table(self._tableA)
            else:
                self._restore_env(data, deck_modes=True)
        except Exception as exc:
            failed = exc
        finally:
            self._restoring = False
        # Whatever did not come back would be gone from the file with the first
        # edit, so the file as it was is kept aside first.
        lost = SessionEnv(data).all_paths() - SessionEnv(self._build_env()).all_paths()
        if failed is not None or lost:
            kept = keep_autosave_copy()
            why = (i18n.t("Could not restore saved playlist: %s") % failed if failed is not None
                   else i18n.t("⚠  %d saved track(s) not found — is the music drive plugged in?")
                   % sum(lost.values()))
            self.statusBar().showMessage(
                why + (" " + i18n.t("The saved session is kept as %s.") % kept.name if kept else ""))

    def _restore_into_deck(self, table: PlaylistTable, data: dict):
        """Restore one serialized grid into a specific deck; what it restores
        lands in that deck's own context."""
        if self.deck(table).ctx is None:
            # The restore sets what the file holds; the rest starts as the
            # focused deck has it, as the combos did when restores swapped them.
            self.deck(table).ctx = replace(self._focused_ctx())
        prev = self._table
        self._table = table
        try:
            if data.get("player_list"):
                self._restore_player_list(data)
            elif data.get("mode") == "Theme":
                self._restore_theme(data)
            else:
                self._restore_favorites(data)
                # A draw saved while the install still planned: it renders as a
                # grid, where a title can only move within its own dance. Here it
                # is the running order — same songs, same order, free to drag.
                if table.plays_flat():
                    table.become_player_list()
            self._refresh_mode_btn(table)
        finally:
            self._table = prev

    def _restore_favorites(self, data: dict):
        dances      = data.get("dances") or []
        rounds_data = data.get("rounds") or []
        if not dances or not rounds_data:
            return
        dance_class = data.get("dance_class", "S")
        style       = data.get("style", "Latin")
        use_timbre  = bool(data.get("use_timbre", True))
        n_dances    = len(dances)

        rounds = [RoundConfig(name=r["name"], heats=int(r.get("heats", 1)),
                              tier=r.get("tier", "early"),
                              prefer_fresh=bool(r.get("prefer_fresh", False)),
                              strategy=r.get("strategy", "") or "")
                  for r in rounds_data]

        playlist = self._playlist_from_grid(rounds_data, n_dances)

        # Dynamic-mode state + stacked final-round backups.
        dynamic  = bool(data.get("dynamic"))
        capacity = data.get("dynamic_capacity") or []
        backups: dict[tuple[str, int, int], list[MusicEntry]] = {}
        for r in rounds_data:
            for key, paths in (r.get("backups") or {}).items():
                try:
                    h, d = (int(x) for x in str(key).split("/"))
                except ValueError:
                    continue
                for p in paths:
                    ent = self._resolve_entry(p)
                    if ent is not None:
                        backups.setdefault((r["name"], h, d), []).append(ent)

        round_skip_dances: dict[str, set] = {}
        for r in rounds_data:
            skipped = r.get("skip_dances") or []
            if skipped:
                round_skip_dances[r["name"]] = set(skipped)

        round_ctx = {r["name"]: r["ctx"] for r in rounds_data if r.get("ctx")}

        suggester = PlaylistSuggester(self._lib)
        self._suggester     = suggester
        self._playlist      = playlist
        self._mode          = "Favorites"
        self._ui_mode       = data.get("ui_mode", "Favorites")
        self._theme_entries = []
        self._style         = style
        self._dance_class   = dance_class
        self._dances        = dances
        self._age           = data.get("age", self._age)

        self._table.load(
            playlist, dances, rounds, dance_class,
            play_cb=self._play_or_stop, suggester=suggester,
            use_timbre=use_timbre, style=style,
            dynamic=dynamic, capacity=capacity, backups=backups,
            round_skip_dances=round_skip_dances,
            round_ctx=round_ctx,
            marked={str(p) for p in (data.get("marked") or [])},
        )
        self._cfg.save_btn.setEnabled(True)
        total = sum(1 for hl in playlist.values()
                    for h in hl for e in h if e is not None)
        self.statusBar().showMessage(
            i18n.t("↩  Restored your in-progress playlist — %d songs (%s, %s)")
            % (total, style, dance_class)
        )

    def _restore_player_list(self, data: dict):
        """Bring a player-only install's flat running order back into its deck —
        same tracks, same order, still freely re-orderable."""
        entries = [e for e in (self._resolve_entry(p)
                               for p in (data.get("theme_entries") or [])) if e]
        if not entries:
            return
        suggester = PlaylistSuggester(self._lib)
        self._suggester = suggester
        self._playlist  = None
        # Set before the load, not after: the rows read the mark set as they are
        # filled, so this way they come back orange in one pass with no re-render.
        self._table._marked_paths = {str(p) for p in (data.get("marked") or [])}
        self._table.load_player_list(
            entries, data.get("theme_label") or "",
            play_cb=self._play_or_stop, suggester=suggester,
            sections=data.get("player_sections") or None,
        )
        self.statusBar().showMessage(
            i18n.t("↩  Restored your running order — %d tracks") % len(entries))

    def _restore_theme(self, data: dict):
        entries = []
        for p in (data.get("theme_entries") or []):
            e = self._resolve_entry(p)
            if e is not None:
                entries.append(e)
        if not entries:
            return
        suggester = PlaylistSuggester(self._lib)
        self._suggester     = suggester
        self._mode          = "Theme"
        self._ui_mode       = "Theme"
        self._theme_entries = entries
        self._theme_label   = data.get("theme_label", "")
        self._playlist      = None
        self._style         = data.get("style", self._style)
        self._dance_class   = data.get("dance_class", self._dance_class)

        self._table.load_theme(
            entries, self._theme_label or "Theme",
            play_cb=self._play_or_stop, suggester=suggester,
        )
        self._cfg.save_btn.setEnabled(True)
        self.statusBar().showMessage(
            i18n.t("↩  Restored your themed playlist — %d tracks") % len(entries)
        )

    def _restore_warmup_state(self, state: dict | None):
        """Re-load the Eintanzen panel from `_warmup_state()`; reveal it when filled,
        hide it otherwise."""
        state = state or {}
        entries = [e for e in (self._resolve_entry(p) for p in state.get("paths", [])) if e]
        if not entries:
            self._warmup_table._warmup = False
            self._warmup_table.setRowCount(0)
            self._warmup_table._row_meta.clear()
            self._warmup_folded = False
            self._warmup_closed = False
            self._warmup_box.setVisible(False)
            self._sync_warmup_toggle()
            return
        label = self._warmup_title(state.get("label") or "")
        if state.get("player_list"):
            self._warmup_table.load_player_list(
                entries, label, play_cb=self._play_or_stop,
                suggester=PlaylistSuggester(self._lib),
                sections=state.get("player_sections") or None)
        else:
            self._warmup_table.load_warmup(
                entries, label, state.get("style", "") or "",
                state.get("dance_class", "S"), bool(state.get("relax", True)),
                play_cb=self._play_or_stop, suggester=PlaylistSuggester(self._lib))
        self._set_deck_name(self._warmup_table, label)
        self._warmup_closed = bool(state.get("closed", False))
        self._warmup_box.setVisible(not self._warmup_closed)
        if not self._warmup_closed:
            self._toggle_warmup_fold(bool(state.get("folded", False)))
        self._sync_warmup_toggle()
