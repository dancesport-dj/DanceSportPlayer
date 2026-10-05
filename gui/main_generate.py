"""Playlist generation: rounds, replay, themes, warm-up, strategy.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
"""
import logging
import time

import planner.m3u
import planner.models
import planner.warmup

from planner import i18n
from planner.planned import path_key
from planner.warmup import reshuffle_warmup
from planner.models import is_non_turnier
from planner.terms import dance_name
from planner.planned import is_planned

from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
)
from collections import Counter
from pathlib import Path
from planner.models import ALLOW_REPEAT, MusicEntry
from planner.scoring import STRATEGY_LABELS
from planner.suggester import PlaylistSuggester, generate_hints, source_gap_hint
from gui.common import (
    BusyDialog,
    _sanitize_filename,
)
from shared.widgets import (
    _show_toast,
)
from planner.playlist_text import PlaylistEncodingError, read_playlist_text
from gui.dialogs import (  # auto-resolved
    AiPlaylistDialog,
    AiSuggestDialog,
    AiTranscriptDialog,
    LibraryGapsDialog,
    TournamentDayDialog,
)
from shared.stores import (
    save_settings,
)
from gui.playlist_table import (  # auto-resolved
    PlaylistTable,
)
from gui.workers import (  # auto-resolved
    AiPlaylistWorker,
    EventPlanWorker,
    WarmupBuilder,
)
from gui.warmup_dialog import ask_warmup_options
from gui.playlist_entries import playlist_paths, resolve_playlist_entries
from gui.event_compare import EventCompareDialog

from planner import event_plan, llm
from planner.similarity import SoundAlike

log =logging.getLogger("dancesport.gui.generate")


def _spread_over_decks(decks: list, items: list) -> list[tuple]:
    """(deck, items) pairs: one item per deck, or contiguous chunks of several
    when there are more items than decks — the day's order stays readable."""
    n_decks = min(len(decks), len(items))
    base, rem = divmod(len(items), n_decks)
    sizes = [base + 1] * rem + [base] * (n_decks - rem)
    it = iter(items)
    return [(deck, [next(it) for _ in range(size)])
            for deck, size in zip(decks, sizes)]


class GenerateMixin:
    """Playlist generation: rounds, replay, themes, warm-up and strategy."""

    def _on_schedule_parsed(self):
        """A fresh schedule was parsed — the old per-competition stashes no longer
        match the new competition list, so drop them."""
        self._replay_work.clear()
        self._active_replay_idx = None

    def _on_replay_competition_changed(self, idx: int):
        """Switch the visible grid to the picked competition's saved work (tab-like).

        The competition we're leaving is stashed first, so its edits survive; the
        one we're entering is restored if it was worked on before, otherwise the
        current grid stays put for the user to ⚡ Generate from history.
        """
        if self._cfg.get_mode() != "Past Competitions" or not self._lib:
            return
        if idx == self._active_replay_idx:
            return
        if self._active_replay_idx is not None:
            self._stash_replay_work(self._active_replay_idx)
        self._active_replay_idx = idx
        if idx in self._replay_work:
            self._restore_replay_work(idx)
        else:
            # Not generated yet → show an empty grid, not the previous competition's.
            self._clear_replay_grid()
            self.statusBar().showMessage(
                "🆕 This competition has no saved work yet — "
                "press ⚡ Generate from History to seed it"
            )

    def _clear_replay_grid(self):
        """Blank the table when switching to a competition with no saved work yet."""
        if self._table._current_play_row >= 0:
            self._play_or_stop(None)
        self._table.setRowCount(0)
        self._table._row_meta.clear()
        self._playlist = None
        self._replay_active = False
        self._cfg.save_btn.setEnabled(False)
        self._show_hints([])

    def _blank_deck(self, table: PlaylistTable):
        """Wipe one competition deck back to a blank/white table: clears the rows,
        drops its stored generation context, resets its title to the default, and
        (if it's the active deck) resets the ConfigPanel combos/toggles too."""
        # Flush any half-typed inline rename so it can't resurrect a stale title.
        self._commit_inline_rename()
        if table._current_play_row >= 0:
            self._play_or_stop(None)
        table.setRowCount(0)
        table._row_meta.clear()
        table._current_play_row = -1
        table._playlist = None
        # Wiping a deck also drops its dynamic mode back to the default (static).
        table._dynamic = False
        table._dynamic_capacity = []
        table._dynamic_dances = []
        table._dynamic_backups = {}
        table._round_ctx = {}
        table._round_skip_dances = {}
        # …and its 🔁 "potential replace" marks, so a later restore/refill can't
        # resurrect orange rows the wipe was supposed to clear.
        table._marked_paths = set()
        table._m3u_path = None   # an empty deck is no file any more
        # A blanked deck has no committed competition style — so the first track
        # dropped in defines it and the cross-style guard doesn't fire spuriously
        # against a stale "Latin"/"Standard" left over from the cleared list.
        table._style = ""
        self._refresh_mode_btn(table)
        if table is not self._table:   # the focused deck's context is reset below
            self.deck(table).ctx = None
        # Reset the deck's header title back to its default ("Playlist N").
        default_name = self.deck(table).default_name
        if default_name:
            self._set_deck_name(table, default_name)
        if table is self._table:
            self._playlist          = None
            self._mode              = "Favorites"
            self._ui_mode           = "Favorites"
            self._replay_active     = False
            self._active_replay_idx = None
            self._replay_label      = None
            self._age               = ""
            self._theme_entries     = []
            self._theme_label       = ""
            self._cfg.save_btn.setEnabled(False)
            self._show_hints([])
            self._cfg.reset_to_defaults()   # mode/style/age/class/dances/rounds

    def _on_table_cleared(self, table: PlaylistTable):
        """A deck's header got a Del → blank that deck (focus it first so the active
        context is the one being cleared)."""
        if self._is_deck(table) and table is not self._table:
            self._set_active_table(table)
        self._blank_deck(table)
        self._apply_deck_view()   # a cleared day-plan deck may retire the 📅 tab
        self._autosave_playlist()

    def _clear_replay_sources(self):
        """Drop stale 'Past Competitions' tooltip data from the shared entries."""
        if self._lib:
            for e in self._lib.entries:
                e.replay_sources = None

    def _source_library(self):
        """The library ⚡ Generate draws from, per the panel's source selector.

        Returns (library, source_label, problem). The default source is the whole
        Favorites library and carries an empty label; the other two hand back a
        RESTRICTED VIEW of it (`MusicLibrary.restricted_to`) holding only the
        tracks parked in the open ⭐ wishlists, or the ones in a chosen .m3u —
        so a dance that pool cannot cover stays blank instead of being filled
        from the whole library behind the user's back. `library` is None when the
        chosen source has nothing to give; `problem` then says why.
        """
        kind, path = self._cfg.get_source()
        if kind == "wishlists":
            entries, seen = [], set()
            for t in self._wishlists:
                for e in t.wishlist_entries():
                    if str(e.path) not in seen:
                        seen.add(str(e.path))
                        entries.append(e)
            if not entries:
                return None, "", ("Your open wishlists are empty — park some "
                                  "tracks there first, or switch the source "
                                  "back to the Favorites library.")
            return self._lib.restricted_to(entries), i18n.t("⭐ the open wishlists"), ""
        if kind == "m3u":
            if not path:
                return None, "", "Choose an .m3u file first."
            dlg, tick = self._m3u_progress(path)
            try:
                entries = self._entries_from_m3u_file(path, tick)
            finally:
                dlg.finish()
            if not entries:
                return None, "", f"No resolvable tracks in {Path(path).name}."
            return (self._lib.restricted_to(entries),
                    f"📂 {Path(path).name}", "")
        return self._lib, "", ""

    def _browse_source_m3u(self):
        """'Browse…' next to the .m3u source: pick the file the next ⚡ Generate
        draws from."""
        start = self._settings.get("playlist_dir", "") or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Generate from an .m3u playlist", start,
            "Playlists (*.m3u *.m3u8)")
        if path:
            self._cfg.set_source_m3u(path)

    def _generate(self):
        if not self._lib:
            return
        mode = self._cfg.get_mode()
        if mode == "Theme":
            self._generate_theme()
            return
        if mode == "Past Competitions":
            self._generate_replay()
            return
        self._stash_active_replay()   # keep any worked competition grid before we replace it
        self._replay_label = None
        self._replay_active = False
        self._clear_replay_sources()
        style, age, cls, dances, rounds, use_timbre = self._cfg.get_config()
        if not dances:
            QMessageBox.warning(self, "No Dances",
                                "Please select at least one dance.")
            return
        if not rounds:
            QMessageBox.warning(self, "No Rounds",
                                "Enter a valid round pattern (e.g. 6-3-2-1).")
            return

        pool_lib, source_label, problem = self._source_library()
        if pool_lib is None:
            QMessageBox.information(self, "Generate", problem)
            return

        self._style       = style
        self._age         = age
        self._dance_class = cls
        self._dances      = dances
        self._iteration  += 1

        self.statusBar().showMessage("Generating playlist…")
        self._cfg.generate_btn.setEnabled(False)
        QApplication.processEvents()   # flush UI so status bar + cursor update immediately

        try:
            self._suggester = PlaylistSuggester(pool_lib)
            self._playlist  = self._suggester.suggest(cls, rounds, dances,
                                                      use_timbre=use_timbre,
                                                      style=style)
        except Exception as exc:
            self._cfg.generate_btn.setEnabled(True)
            self.statusBar().showMessage(
                i18n.t("Error generating playlist: %s") % exc)
            QMessageBox.critical(self, "Generate Error", str(exc))
            return

        self._mode          = "Favorites"
        self._ui_mode       = "Favorites"
        self._theme_entries = []
        self._table.load(
            self._playlist, dances, rounds, cls,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
            use_timbre=use_timbre,
            style=style,
        )
        self._set_deck_name(self._table, self._favorites_deck_name(age, cls, style))
        self._reveal_deck(self._table)   # never fill a deck the view is hiding
        self._cfg.generate_btn.setEnabled(True)
        self._cfg.save_btn.setEnabled(True)

        hints = generate_hints(pool_lib, self._playlist, dances, cls, rounds)
        gaps = source_gap_hint(self._playlist, dances, source_label)
        self._show_hints(([gaps] if gaps else []) + hints)

        total = sum(rc.heats for rc in rounds) * len(dances)
        suffix = (i18n.t("  (iteration %d)") % self._iteration
                  if self._iteration > 1 else "")
        src = i18n.t(" — from %s") % source_label if source_label else ""
        self.statusBar().showMessage(
            i18n.t("Generated %d songs — %s, %s, %s")
            % (total, self._style, self._age, cls) + suffix + src
        )

    def _plan_tournament_day(self):
        """📅: generate several competitions in one go into the Tournament-day
        tab's own eight day decks (two sub-tabs of four), one deck per
        competition — fully separated from the normal working decks A–H. All
        competitions share one 'already played today' exclusion pool, so no
        song repeats anywhere across the day (Paso Doble excepted)."""
        if not self._lib:
            return
        day_decks = self._day_decks
        old_day = [t for t in day_decks
                   if self._serialize_playlist_state(t) is not None]
        free = [t for t in day_decks if self._serialize_playlist_state(t) is None]

        style, age, cls, _dances, _rounds, use_timbre = self._cfg.get_config()
        dlg = TournamentDayDialog(
            style=style or "Latin", age=age or "Hauptgruppe", cls=cls or "S",
            pattern=self._cfg.rounds_edit.text().strip() or "6-3-2-1",
            parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        comps = dlg.competitions()
        if not comps:
            return

        if old_day:
            ret = QMessageBox.question(
                self, "Replace day plan",
                "The Tournament-day tab still holds an earlier day plan.\n\n"
                "Replace it with the new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                for t in old_day:
                    self._blank_deck(t)
                free = [t for t in day_decks
                        if self._serialize_playlist_state(t) is None]
            elif not free:
                return

        # More competitions than free decks → stack several per deck (contiguous
        # chunks keep the day's order readable top-to-bottom).
        assign = _spread_over_decks(free, comps)
        targets = [deck for deck, _ in assign]
        self._stash_active_replay()   # keep any worked competition grid before we replace it
        self._replay_label = None
        self._replay_active = False
        self._clear_replay_sources()

        busy = BusyDialog(self, message="📅 Planning tournament day…")
        busy.show_after(250)

        used_today: set = set()   # paths played in ANY earlier competition today
        built = 0
        done = 0
        decks_used = 0
        skipped: list[str] = []
        for deck, comp_list in assign:
            parts: list[dict] = []
            for comp in comp_list:
                c_style, c_age, c_cls = comp["style"], comp["age"], comp["cls"]
                label = self._favorites_deck_name(c_age, c_cls, c_style)
                busy.set_progress(done, len(comps), label)
                QApplication.processEvents()
                done += 1

                dances = planner.models.DEFAULT_DANCES.get(c_style, {}).get(c_cls) or []
                rounds = planner.models.rounds_from_pattern(comp["pattern"])
                if not dances or not rounds:
                    skipped.append(label)
                    continue
                try:
                    suggester = PlaylistSuggester(self._lib)
                    playlist = suggester.suggest(
                        c_cls, rounds, dances,
                        use_timbre=use_timbre, style=c_style,
                        exclude=used_today,
                    )
                except Exception as exc:
                    log.warning("📅 Day plan: %s failed: %s", label, exc)
                    skipped.append(f"{label} — {exc}")
                    continue

                # Everything just planned is spent for the REST of the day (PD may repeat).
                for heats in playlist.values():
                    for heat in heats:
                        for e in heat:
                            if e is not None and e.dance not in ALLOW_REPEAT:
                                used_today.add(str(e.path))
                parts.append({"label": label, "playlist": playlist,
                              "dances": dances, "rounds": rounds,
                              "cls": c_cls, "style": c_style, "age": c_age,
                              "suggester": suggester})
                built += 1

            if not parts:
                continue
            decks_used += 1
            self._load_day_deck(deck, parts, use_timbre)

        busy.finish()

        if built:
            self._apply_deck_view()   # reveal the 📅 Tournament-day tab
            self._deck_tabs.setCurrentIndex(2)
            self._day_tabs.setCurrentIndex(0)
            self._set_active_table(targets[0])
            self._cfg.save_btn.setEnabled(True)
            self._autosave_playlist()
            self._show_hints([
                i18n.t("📅 Day plan: %d competition(s) generated — %d songs locked "
                       "for the day (Paso Doble may repeat)") % (built, len(used_today))
            ])
            _show_toast(self, i18n.t("📅  Planned %d competition(s) into %d deck(s)")
                        % (built, decks_used))
        if skipped:
            QMessageBox.warning(
                self, "Day plan",
                i18n.t("Skipped competition(s):") + "\n\n"
                + "\n".join(f"• {s}" for s in skipped))
        self.statusBar().showMessage(
            i18n.t("📅 Day plan: %d generated, %d skipped") % (built, len(skipped))
            if skipped else i18n.t("📅 Day plan: %d competition(s) generated") % built)

    def _load_day_deck(self, deck: PlaylistTable, parts: list[dict],
                       use_timbre: bool):
        """Load one 📅 day deck with its competition(s). Each part needs:
        label, playlist, dances, rounds, cls, style, age, suggester."""
        first = parts[0]
        self._set_active_table(deck)
        self._style = first["style"]
        self._age = first["age"]
        self._dance_class = first["cls"]
        self._mode = "Favorites"
        self._ui_mode = "Favorites"
        self._theme_entries = []
        if len(parts) == 1:
            self._dances = first["dances"]
            self._suggester = first["suggester"]
            self._playlist = first["playlist"]
            self._table.load(
                first["playlist"], first["dances"], first["rounds"],
                first["cls"],
                play_cb=self._play_or_stop,
                suggester=first["suggester"],
                use_timbre=use_timbre,
                style=first["style"],
            )
            deck_label = first["label"]
        else:
            # Several competitions share this deck: union dance columns,
            # competition-prefixed round headers, per-round skip/ctx so
            # rendering, ↺ and export stay per-competition.
            merged, union, mrounds, skips, rctx = planner.models.merge_day_playlists(parts)
            self._dances = union
            self._suggester = first["suggester"]
            self._playlist = merged
            self._table.load(
                merged, union, mrounds, first["cls"],
                play_cb=self._play_or_stop,
                suggester=first["suggester"],
                use_timbre=use_timbre,
                style=first["style"],
                round_skip_dances=skips,
                round_ctx=rctx,
            )
            deck_label = "  +  ".join(p["label"] for p in parts)
        # 📅 prefix marks the deck as part of the day plan (shared no-repeat
        # pool) — otherwise it would look like an ordinary generated playlist.
        # _sanitize_filename strips it again, so export names stay clean.
        self._set_deck_name(self._table, f"📅  {deck_label}")

    def _generate_replay(self):
        cfg = self._cfg.get_replay_config()
        if not cfg:
            QMessageBox.warning(
                self, "No Competition",
                "Paste a schedule and click 'Parse schedule', then pick a competition."
            )
            return
        spec, rounds, use_timbre = cfg
        if not rounds:
            QMessageBox.warning(self, "No Rounds",
                                "The selected competition has no valid heat counts.")
            return

        self.statusBar().showMessage(
            i18n.t("Seeding '%s' from past playlists…") % spec.label)
        self._cfg.generate_btn.setEnabled(False)
        QApplication.processEvents()

        self._clear_replay_sources()   # drop stale matches from any earlier competition
        try:
            schedule_heats = [rc.heats for rc in rounds]
            entries, round_pools, n_files, round_sources = self._lib.past_competition_round_pools(
                spec, schedule_heats, len(spec.dances)
            )
            # The hover tooltip lists every past list of THIS competition a
            # track came from, across all rounds.
            for e in entries:
                labels = {lab for rnd in round_sources for lab in rnd.get(id(e), ())}
                e.replay_sources = sorted(labels) or None
        except Exception as exc:
            self._cfg.generate_btn.setEnabled(True)
            self.statusBar().showMessage(
                i18n.t("Error reading past playlists: %s") % exc)
            QMessageBox.critical(self, "History Error", str(exc))
            return

        seeded = bool(entries)
        if not seeded:
            round_pools = None

        # One FULL-library suggester drives generation, the per-round pools, ↺ and
        # live strategy re-rolls. Candidates restrict each round to its history;
        # `_get_pool` falls back to the full library for a dance history never used.
        suggester = PlaylistSuggester(self._lib)

        # Live-regen context: a strategy-combo / 🎯-scope change re-rolls one round.
        self._suggester         = suggester
        self._replay_active     = True
        self._replay_rounds     = rounds
        self._replay_pools      = round_pools
        self._replay_use_timbre = use_timbre
        effective_pools         = self._effective_replay_pools()

        self._iteration += 1
        try:
            self._playlist = suggester.suggest(
                spec.dance_class, rounds, spec.dances,
                use_timbre=use_timbre, style=spec.style,
                round_pools=effective_pools,
            )
        except Exception as exc:
            self._cfg.generate_btn.setEnabled(True)
            self.statusBar().showMessage(
                i18n.t("Error generating playlist: %s") % exc)
            QMessageBox.critical(self, "Generate Error", str(exc))
            return

        self._mode          = "Favorites"
        self._ui_mode       = "Past Competitions"
        self._theme_entries = []
        self._style         = spec.style
        self._age           = spec.label
        self._dance_class   = spec.dance_class
        self._dances        = spec.dances
        self._replay_label  = _sanitize_filename(spec.label)
        # This competition is now the active 'tab'; switching the combo will stash it.
        self._active_replay_idx = self._cfg.replay_combo.currentIndex()
        self._replay_work.pop(self._active_replay_idx, None)   # fresh seed supersedes old work

        self._table.load(
            self._playlist, spec.dances, rounds, spec.dance_class,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
            use_timbre=use_timbre,
            style=spec.style,
            round_pools=effective_pools,
        )
        self._set_deck_name(self._table, spec.label)   # name the deck after the competition
        self._cfg.generate_btn.setEnabled(True)
        self._cfg.save_btn.setEnabled(True)

        hints = generate_hints(self._lib, self._playlist, spec.dances,
                               spec.dance_class, rounds)
        if seeded:
            per_round = ", ".join(
                f"{rc.name}:{len(round_pools[i]) if round_pools and i < len(round_pools) else 0}"
                for i, rc in enumerate(rounds)
            )
            hints.insert(0, i18n.t("🕑 Seeded from %d past “%s” list(s) — "
                                   "round pool sizes: %s") % (n_files, spec.label, per_round))
        else:
            hints.insert(0, i18n.t("⚠️ No past “%s” lists found — "
                                   "used the whole favorites library instead") % spec.label)
        self._show_hints(hints)

        total = sum(rc.heats for rc in rounds) * len(spec.dances)
        suffix = (i18n.t("  (iteration %d)") % self._iteration
                  if self._iteration > 1 else "")
        self.statusBar().showMessage(
            i18n.t("Generated %d songs — %s") % (total, spec.label) + suffix
        )

    def _effective_replay_pools(self):
        """Per-round candidate pools after applying each round's 🎯 scope toggle.

        Returns the history pool for rounds kept to THIS competition, and None
        (→ full library) for rounds the user opened up to all playlists. None when
        there is no history at all."""
        if not self._replay_pools:
            return None
        out = []
        for i, rc in enumerate(self._replay_rounds):
            pool = self._replay_pools[i] if i < len(self._replay_pools) else None
            out.append(pool if self._cfg.round_scope(rc.name) else None)
        return out

    def _on_timbre_toggled(self, on: bool):
        """Apply a 'Use Timbre Similarity' toggle live so the ↺ buttons (and the
        replay live re-roll) pick it up without a full regenerate."""
        self._replay_use_timbre = on
        if self._table is not None:
            self._table.set_use_timbre(on)
        self.statusBar().showMessage(
            "Timbre similarity on for ↺ regenerations" if on
            else "Timbre similarity off for ↺ regenerations"
        )

    def _on_strategy_changed(self, round_name: str, strategy: str):
        """Route a strategy-combo change to the handler for the active mode.

        Both handlers honour the shared 'Auto re-roll round on strategy change'
        checkbox: on → live re-roll that round; off → just remember the strategy
        so the ↺ buttons use it and the generated grid stays as-is."""
        if self._replay_active:
            self._on_replay_strategy_changed(round_name, strategy)
        else:
            self._on_favorites_strategy_changed(round_name, strategy)

    def _on_favorites_strategy_changed(self, round_name: str, strategy: str):
        """Apply a strategy-combo change in Favorites mode (no history pools)."""
        if self._mode != "Favorites" or not self._playlist or not self._suggester:
            return
        if round_name not in self._playlist:
            return
        rc = next((r for r in self._cfg._round_cfgs if r.name == round_name), None)
        if rc is None:
            return
        rc.strategy     = strategy or None
        rc.prefer_fresh = (strategy == "fresh")

        # Auto re-roll off → keep the grid, just store the strategy for the ↺ buttons.
        if not self._cfg.auto_reroll_check.isChecked():
            self._table.update_strategy(round_name, strategy or "", strategy == "fresh")
            label = i18n.t(STRATEGY_LABELS.get(strategy, strategy))
            self.statusBar().showMessage(
                i18n.t("%s: strategy set to %s — ↺ a song or dance to apply")
                % (round_name, label)
            )
            return

        # Hold every OTHER round's songs so the re-rolled round stays repeat-free.
        used: set    = set()
        pd_used: set = set()
        for rn, heats in self._playlist.items():
            if rn == round_name:
                continue
            for heat in heats:
                for e in heat:
                    if e is None:
                        continue
                    if e.dance in ALLOW_REPEAT:
                        pd_used.add(str(e.path))
                    else:
                        used.add(str(e.path))

        if self._table._current_play_row >= 0:
            self._play_or_stop(None)

        use_timbre = self._cfg.timbre_check.isChecked()
        try:
            self._playlist[round_name] = self._suggester.regenerate_round(
                rc, self._dances, self._dance_class, used, pd_used,
                use_timbre=use_timbre, style=self._style,
            )
        except Exception as exc:
            self.statusBar().showMessage(i18n.t("Re-roll failed: %s") % exc)
            return

        self._table.load(
            self._playlist, self._dances, self._cfg._round_cfgs, self._dance_class,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
            use_timbre=use_timbre,
            style=self._style,
        )
        label = i18n.t(STRATEGY_LABELS.get(strategy, strategy))
        self.statusBar().showMessage(
            i18n.t("↻ %s re-rolled — %s") % (round_name, label))

    def _on_replay_strategy_changed(self, round_name: str, strategy: str):
        """Live re-roll one round when its strategy combo changes (Past Competitions).

        Only the named round is replaced; the other rounds' songs are held in the
        exclusion set so nothing duplicates. The round draws from its own history
        pool (timbre-matched to the round anchor), falling back to the full library
        for any dance that history never used in that round.
        """
        if not self._replay_active or not self._playlist:
            return
        if round_name not in self._playlist or not self._suggester:
            return
        rc = next((r for r in self._replay_rounds if r.name == round_name), None)
        if rc is None:
            return
        rc.strategy     = strategy or None
        rc.prefer_fresh = (strategy == "fresh")

        names = list(self._playlist.keys())

        # Auto re-roll disabled → keep the generated grid, but update what the ↺
        # buttons draw from: the new strategy AND the current 🎯 scope (this
        # competition's history pool when ticked, full library when unticked).
        if not self._cfg.auto_reroll_check.isChecked():
            self._table.update_strategy(round_name, strategy or "", strategy == "fresh")
            try:
                ri = names.index(round_name)
            except ValueError:
                ri = -1
            pool = (self._replay_pools[ri]
                    if (self._replay_pools and 0 <= ri < len(self._replay_pools)
                        and self._cfg.round_scope(round_name)) else None)
            self._table.set_round_pool(round_name, pool)
            label = i18n.t(STRATEGY_LABELS.get(strategy, strategy))
            scope = (i18n.t("this comp") if self._cfg.round_scope(round_name)
                     else i18n.t("all playlists"))
            self.statusBar().showMessage(
                i18n.t("%s: %s · %s — ↺ a song or dance to apply")
                % (round_name, label, scope)
            )
            return
        try:
            ri = names.index(round_name)
        except ValueError:
            return
        # 🎯 ticked → this round's history pool; unticked → None (full library).
        pool = (self._replay_pools[ri]
                if (self._replay_pools and ri < len(self._replay_pools)
                    and self._cfg.round_scope(round_name)) else None)

        # Hold every OTHER round's songs so the re-rolled round stays repeat-free.
        used: set    = set()
        pd_used: set = set()
        for rn, heats in self._playlist.items():
            if rn == round_name:
                continue
            for heat in heats:
                for e in heat:
                    if e is None:
                        continue
                    if e.dance in ALLOW_REPEAT:
                        pd_used.add(str(e.path))
                    else:
                        used.add(str(e.path))

        # Stop playback if a row in this round is currently playing.
        if self._table._current_play_row >= 0:
            self._play_or_stop(None)

        try:
            self._playlist[round_name] = self._suggester.regenerate_round(
                rc, self._dances, self._dance_class, used, pd_used,
                use_timbre=self._replay_use_timbre, style=self._style,
                candidates=pool,
            )
        except Exception as exc:
            self.statusBar().showMessage(i18n.t("Re-roll failed: %s") % exc)
            return

        self._table.load(
            self._playlist, self._dances, self._replay_rounds, self._dance_class,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
            use_timbre=self._replay_use_timbre,
            style=self._style,
            round_pools=self._effective_replay_pools(),
        )
        scope = (i18n.t("this comp") if self._cfg.round_scope(round_name)
                 else i18n.t("all playlists"))
        label = i18n.t(STRATEGY_LABELS.get(strategy, strategy))
        self.statusBar().showMessage(
            i18n.t("↻ %s re-rolled — %s · %s") % (round_name, label, scope))

    def _generate_theme(self):
        self._stash_active_replay()   # keep any worked competition grid before we replace it
        self._replay_label = None
        self._replay_active = False
        self._clear_replay_sources()
        theme_key, theme_label, count = self._cfg.get_theme_config()
        if not theme_key:
            QMessageBox.warning(self, "No Theme", "Please select a theme.")
            return

        self.statusBar().showMessage(
            i18n.t("Building '%s' playlist…") % theme_label)
        self._cfg.generate_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            self._suggester = PlaylistSuggester(self._lib)
            entries = self._suggester.suggest_theme(theme_key, count=count)
        except Exception as exc:
            self._cfg.generate_btn.setEnabled(True)
            QMessageBox.critical(self, "Theme Error", str(exc))
            return

        self._cfg.generate_btn.setEnabled(True)
        if not entries:
            self._show_hints([])
            self._table.setRowCount(0)
            self._cfg.save_btn.setEnabled(False)
            QMessageBox.information(
                self, "No Matches",
                i18n.t("No tracks matched theme '%s'.") % theme_label + "\n\n"
                + i18n.t("Decade themes require year tags in your MP3s; you can also map\n"
                         "songs to themes in themes.json (track_themes).")
            )
            self.statusBar().showMessage(
                i18n.t("No tracks matched '%s'.") % theme_label)
            return

        self._mode          = "Theme"
        self._ui_mode       = "Theme"
        self._theme_entries = entries
        self._theme_label   = theme_label
        self._playlist      = None
        self._table.load_theme(
            entries, theme_label,
            play_cb=self._play_or_stop,
            suggester=self._suggester,
        )
        self._reveal_deck(self._table)   # never fill a deck the view is hiding
        self._cfg.save_btn.setEnabled(True)

        dance_mix = ", ".join(
            f"{dance_name(d, d)}×{sum(1 for e in entries if e.dance == d)}"
            for d in dict.fromkeys(e.dance for e in entries)
        )
        self._show_hints([i18n.t("🎯 %s: %d tracks  (%s)")
                          % (theme_label, len(entries), dance_mix)])
        self.statusBar().showMessage(
            i18n.t("Theme '%s' — %d tracks") % (theme_label, len(entries)))

    def _ask_warmup_options(self):
        """The 🤸 dialog for this window's library — see `ask_warmup_options`."""
        return ask_warmup_options(
            self, self._lib.entries if self._lib else [],
            self._settings.get("library_dir", "") or "")

    def _entries_from_m3u_file(self, path, progress_cb=None) -> list[MusicEntry]:
        """Resolve every track line of an .m3u to a library MusicEntry (built as
        an external entry when not in the library). Used by the warm-up generator's
        'from an .m3u file' source. Order preserved, duplicates dropped.

        `progress_cb(done, total, detail)` is called every few lines: a long list
        reads the tags of everything that isn't in the library, which takes
        seconds, and a window that simply stops looks broken."""
        lib = self._lib
        if lib is None:
            return []
        try:
            _, _, remapper = self._remap_index()
        except Exception:
            remapper = None
        try:
            lines = read_playlist_text(path)[0].splitlines()
        except OSError:
            return []
        except PlaylistEncodingError as exc:
            log.warning("⚠️ Party list not read\n"
                        "file: %s\n"
                        "reason: %s", path, exc)
            QMessageBox.warning(self, "Playlist not read", str(exc))
            return []
        # Count the TRACK lines, not the lines: an .m3u carries an #EXTINF
        # comment per track, so a 282-track party list has 565 of them — and a
        # progress bar counting those ran up past 500 and finished at 282, which
        # reads as half the file having been thrown away.
        return resolve_playlist_entries(playlist_paths(lines), lib, self._cache,
                                        remapper, progress_cb)

    def _generate_warmup(self):
        """🤸: build a per-class warm-up or an ETDS party playlist into the focused
        deck. Heavy lifting runs in a WarmupBuilder thread with a progress dialog so
        a big library never freezes the UI."""
        if not self._lib or not self._lib.entries:
            QMessageBox.information(
                self, "Eintanzen",
                "The library is still loading — try again in a moment.")
            return
        opts = self._ask_warmup_options()
        if opts is None:
            return

        # Resolve the candidate pool (whole library, minus already-planned, the
        # open wishlists, or a chosen .m3u).
        if opts["source"] == "m3u":
            src = self._entries_from_m3u_file(opts["m3u_path"])
            if not src:
                QMessageBox.information(
                    self, "Eintanzen",
                    "No resolvable tracks in that .m3u file.")
                return
        elif opts["source"] == "wishlists":
            src, seen = [], set()
            for t in self._wishlists:
                for e in t._row_meta.entries():
                    if str(e.path) not in seen:
                        seen.add(str(e.path))
                        src.append(e)
            if not src:
                QMessageBox.information(
                    self, "Eintanzen",
                    "Your open wishlists are empty — park some tracks there first.")
                return
        else:
            # The Favorites library (settings library_dir) — never the global
            # repository, which only ever feeds similarity search. Categorised
            # tracks (duplicates / wrong tempo / seasonal / background) live in
            # that folder but are not tournament music: `class_warmup_pool`
            # already drops them, the party build does not, so drop them here.
            src = [e for e in self._lib.entries
                   if not getattr(e, "is_xmas", False) and not is_non_turnier(e)]
            if opts["unused_only"]:
                planned_paths, planned_fps = self._deck_dedup_index()
                fingerprint = self._cache.known_fingerprint if self._cache else None
                src = [e for e in src
                       if not is_planned(e.path, planned_paths, planned_fps,
                                         fingerprint)]

        if opts["mode"] == "class":
            params = dict(style=opts["style"], dance_class=opts["dance_class"],
                          max_tracks=opts["max_tracks"],
                          fresh_ratio=opts["fresh_ratio"], relax=opts["relax"])
            label = f"Eintanzen {opts['style']} {opts['dance_class']}"
        else:
            params = dict(opts["etds"])
            label = "Party"

        self._warmup_label = label
        self._warmup_opts = opts
        self._busy = BusyDialog(self, i18n.t("🤸 Building %s…") % label)  # i18n: data
        busy = self._busy
        self._warmup_worker = WarmupBuilder(src, opts["mode"], params, self)
        w = self._warmup_worker
        w.progress.connect(lambda d, t: busy.set_progress(d, t))
        w.done.connect(self._on_warmup_done)
        w.error.connect(self._on_warmup_error)
        w.finished.connect(busy.finish)
        # i18n: data — the label is a name ("Eintanzen Latin D", "Party")
        self.statusBar().showMessage(i18n.t("Building %s…") % label)
        # Show promptly: the in-memory build often finishes under the usual
        # 300 ms threshold, so the party/warm-up dialog would otherwise never
        # appear at all.
        busy.show_after(0)
        w.start()

    def _on_warmup_error(self, msg: str):
        QMessageBox.critical(self, "Eintanzen Error", msg)
        self.statusBar().showMessage("Eintanzen failed.")

    def _on_warmup_done(self, entries):
        """Load the freshly built warm-up / party list into the dedicated Eintanzen
        panel (above the wishlist, below the playlists), renamed 'Eintanzen …'. Rows
        carry a 'warmup' tag so ↺ re-rolls a timbre match and drops can replace a
        slot. Never clobbers a playlist deck or a wishlist."""
        if not entries:
            QMessageBox.information(
                self, "Eintanzen",
                "No matching tracks for the chosen options — check the class, the "
                "source and that the library / .m3u actually has those dances.")
            self.statusBar().showMessage("Eintanzen: no matching tracks.")
            return

        opts        = getattr(self, "_warmup_opts", {}) or {}
        style       = opts.get("style", "Latin")
        dance_class = opts.get("dance_class", "S")
        relax       = bool(opts.get("relax", True))
        if opts.get("mode") == "class":
            list_label = self._warmup_title(f"Eintanzen {style} {dance_class}")
        else:
            list_label = self._warmup_title("Party")
            style = ""   # ETDS mixes styles → ↺ tries every style per dance

        target = self._warmup_table
        target.load_warmup(
            entries, list_label, style, dance_class, relax,
            play_cb=self._play_or_stop, suggester=PlaylistSuggester(self._lib),
        )
        self._set_deck_name(target, list_label)
        self._warmup_closed = False
        self._warmup_box.setVisible(True)   # reveal the panel now it has content
        self._toggle_warmup_fold(False)     # always open a freshly built list
        self._sync_warmup_toggle()          # enable + check the toolbar toggle
        self._set_active_table(target)      # Save / similar follow this list
        self._autosave_playlist()
        mix = Counter(planner.warmup.warmup_code(e) for e in entries)
        dance_mix = ", ".join(f"{dance_name(d, d)}×{n}"
                              for d, n in mix.most_common())
        how = (i18n.t("↺ swaps with a title from the end, drag-drop replaces")
               if opts.get("mode") != "class"
               else i18n.t("↺ / drag-drop to replace by timbre"))
        self._show_hints([i18n.t("🤸 %s: %d tracks  (%s)  — %s")
                          % (list_label, len(entries), dance_mix, how)])
        self.statusBar().showMessage(
            i18n.t("%s — %d tracks") % (list_label, len(entries)))

    def _sync_warmup_shuffle_btn(self, *_):
        """🔀 and ✓ show only while the panel holds an ETDS party list with
        titles. ✓ shares the gate: the rules it reads back are the ones that
        built THIS kind of list, and a competition running order dropped on the
        panel would break every one of them by design."""
        t = self._warmup_table
        on = bool(t._party_swap() and t._row_meta.song_rows())
        self._warmup_shuffle_btn.setVisible(on)
        self._warmup_check_btn.setVisible(on)

    def _shuffle_warmup(self):
        """🔀 Put the party list's titles in a fresh order, as a new build from
        scratch would. The late WW / PD rules follow this session's last ETDS
        build; the playing title keeps playing."""
        t = self._warmup_table
        entries = t._row_meta.entries()
        if not t._party_swap() or not entries:
            return
        etds = (getattr(self, "_warmup_opts", None) or {}).get("etds") or {}
        order = reshuffle_warmup(entries, late_ww=etds.get("late_ww", True),
                                 late_pd=etds.get("late_pd", True))
        t._reload_warmup(order)
        t._notify_changed()
        log.info("🔀 Party list shuffled\n"
                 "tracks: %d", len(order))
        self.statusBar().showMessage(
            i18n.t("🔀 %s shuffled — %d tracks")
            % (t._warmup_label or i18n.t("Party list"), len(order)))

    def _load_warmup_from_m3u(self, table, m3u_path):
        """Load an .m3u dropped onto the warm-up panel as a flat list (not a
        round/heat import). Tracks gain the 'warmup' tag so ↺ / drag-drop replace
        by timbre, exactly like a generated list.

        The panel is not choosy about what is dropped on it — a competition
        running order lands here as readily as an Eintanzen list, and it is then
        cut into the rounds it is actually played in (Vorrunde, Zwischenrunde,
        Finale) instead of the warm-up's 'new round wherever a dance repeats'.
        Either way the panel is named after the file, not called 'Eintanzen'
        something it isn't."""
        dlg, tick = self._m3u_progress(m3u_path)
        try:
            entries = self._entries_from_m3u_file(m3u_path, progress_cb=tick)
            if not entries:
                self.statusBar().showMessage(
                    i18n.t("🤸 Eintanzen: nothing loadable from %s")
                    % Path(m3u_path).name)
                return
            list_label = self._warmup_title(Path(m3u_path).stem)
            tick(len(entries), len(entries), "building the list…")
            # Competition rounds only: a warm-up list has its own cut in
            # `load_warmup`, which re-runs after every drop instead of holding on
            # to the rounds the file arrived with.
            sections = self._player_round_sections(m3u_path, entries, warmup=False)
            if sections:
                table.load_player_list(
                    entries, list_label, play_cb=self._play_or_stop,
                    suggester=PlaylistSuggester(self._lib), sections=sections)
            else:
                table.load_warmup(
                    entries, list_label, style="", dance_class="S", relax=True,
                    play_cb=self._play_or_stop, suggester=PlaylistSuggester(self._lib),
                )
            log.info("🤸 Eintanzen panel loaded\n"
                     "file: %s\n"
                     "tracks: %s\n"
                     "rounds: %s", Path(m3u_path).name, len(entries),
                     ", ".join(dict.fromkeys(sections.values()))
                     or "none — cut where a dance repeats")
        finally:
            dlg.finish()
        self._set_deck_name(table, list_label)
        self._warmup_closed = False
        self._warmup_box.setVisible(True)
        self._toggle_warmup_fold(False)
        self._sync_warmup_toggle()
        self._set_active_table(table)
        table._remove_duplicate_titles(on_load=True)
        self._autosave_playlist()
        self.statusBar().showMessage(
            i18n.t("%s — %d tracks") % (list_label, len(entries)))

    def _m3u_progress(self, m3u_path):
        """A progress dialog for reading an .m3u, plus the tick that drives it.

        Returns (dialog, tick). The dialog only appears when the read takes
        longer than a moment, so a short list never flashes one — and a long one
        never leaves the window frozen with nothing to look at."""
        dlg = BusyDialog(self, message=i18n.t("📂 Importing %s…") % Path(m3u_path).name)
        dlg.show_after(250)

        def tick(done: int, total: int, detail: str = ""):
            dlg.set_progress(done, total, detail)
            QApplication.processEvents()

        return dlg, tick

    def _player_round_sections(self, m3u_path, entries, *,
                               warmup: bool = True) -> dict:
        """Track path → the round it is played in, for the ─── strips of a running
        order. Read from the '# ══ Round ══' markers this app writes into its own
        exports, otherwise derived from the order itself (a new round each time the
        dances come round again, or the Standardrunde / Lateinrunde / Socialrunde
        of a warm-up list). Empty when neither yields named rounds — the list then
        heads its strips with the dance instead.

        `warmup=False` leaves the warm-up rounds out, for the panel that has its
        own cut for those."""
        marked = planner.m3u.m3u_marker_rounds(m3u_path)
        if len(set(marked.values())) > 1:
            return {str(e.path): marked[path_key(e.path)]
                    for e in entries if path_key(e.path) in marked}
        return {str(e.path): name
                for name, seg in planner.m3u.running_order_rounds(entries, warmup=warmup)
                for e in seg}

    def _load_player_list_from_m3u(self, table, m3u_path):
        """Load an .m3u into a DECK of a player-only install as its flat running
        order — the file is the order the evening is played in, not a draw to
        rebuild, and every later drop inserts straight into it."""
        dlg, tick = self._m3u_progress(m3u_path)
        try:
            entries = self._entries_from_m3u_file(m3u_path, progress_cb=tick)
            if not entries:
                self.statusBar().showMessage(
                    i18n.t("🎧 Nothing loadable from %s") % Path(m3u_path).name)
                return
            label = Path(m3u_path).stem
            # Building the rows is the other half of the wait on a long list.
            tick(len(entries), len(entries), "building the list…")
            sections = self._player_round_sections(m3u_path, entries)
            table.load_player_list(entries, label, play_cb=self._play_or_stop,
                                   suggester=PlaylistSuggester(self._lib),
                                   sections=sections)
            table._m3u_path = Path(m3u_path)
        finally:
            dlg.finish()
        self._set_deck_name(table, label)
        self._set_active_table(table)
        table._remove_duplicate_titles(on_load=True)
        self._autosave_playlist()
        log.info("🎧 Player list loaded\n"
                 "file: %s\n"
                 "tracks: %s\n"
                 "rounds: %s", Path(m3u_path).name, len(entries),
                 ", ".join(dict.fromkeys(sections.values())) or "none — grouped by dance")
        self.statusBar().showMessage(
            i18n.t("%s — %d tracks") % (label, len(entries)))

    def _generate_ai_playlist(self):
        """🤖: let an LLM assemble the playlist instead of the scoring algorithm.

        The model first sees a per-dance summary of the TSO-conform candidates
        and asks for the slices it wants, then answers with the numbers it picked
        off those rows — it can never name a track that isn't in the library. Competition mode reuses the left panel's style / class / dances
        / rounds; flat mode just asks for N tracks in playing order; wish mode hands
        it the titles the user named and lets it find them."""
        if not self._lib or not self._lib.entries:
            QMessageBox.information(
                self, "AI playlist",
                "The library is still loading — try again in a moment.")
            return

        dlg = AiPlaylistDialog(
            self._settings, self,
            event_plan_kept=getattr(self, "_event_result", None) is not None)
        code = dlg.exec()
        if code not in (QDialog.DialogCode.Accepted, AiPlaylistDialog.REOPEN_PLAN):
            return
        opts = dlg.values()

        # Remember rules / model / brief for the next run.
        self._settings["ai_rules"] = llm.rules_to_remember(opts["rules"])
        self._settings["ai_model"] = opts["model"]
        self._settings["ai_brief"] = opts["brief"]
        self._settings["ai_wishes"] = opts["wishes"]
        self._settings["ai_flat_count"] = opts["count"]
        self._settings["ai_claude_config_dir"] = opts["config_dir"]
        ev = opts["event"]
        self._settings["ai_event_schedule"] = ev["schedule"]
        self._settings["ai_event_series"] = ev["series_name"]
        self._settings["ai_event_new_share"] = round(ev["new_share"] * 100)
        self._settings["ai_event_rare_share"] = round(ev["rare_share"] * 100)
        self._settings["ai_event_variants"] = ev["variants"]
        self._settings["ai_event_variants_offered"] = list(event_plan.PROFILE_ORDER)
        self._settings["ai_event_use_event"] = ev["use_event"]
        self._settings["ai_event_use_class"] = ev["use_class"]
        self._settings["ai_event_ai_check"] = ev["ai_check"]
        save_settings(self._settings)

        if code == AiPlaylistDialog.REOPEN_PLAN:
            self._show_event_compare()
            return
        if opts["mode"] == "event":
            self._plan_event(opts)
            return
        if opts["mode"] == "competition":
            style, age, cls, dances, rounds, use_timbre = self._cfg.get_config()
            if not dances:
                QMessageBox.warning(self, "No Dances",
                                    "Please select at least one dance.")
                return
            if not rounds:
                QMessageBox.warning(self, "No Rounds",
                                    "Enter a valid round pattern (e.g. 6-3-2-1).")
                return
            candidates = llm.competition_candidates(
                self._lib.entries, style, cls, dances)
            task = llm.competition_task(style, age, cls, dances, rounds,
                                                opts["brief"])
            ctx = dict(mode="competition", style=style, age=age, dance_class=cls,
                       dances=dances, rounds=rounds, use_timbre=use_timbre)
        elif opts["mode"] == "wishes":
            if not opts["wishes"]:
                QMessageBox.information(
                    self, "AI playlist",
                    "The wish list is empty — write the titles you want, one\n"
                    "per line or a column per dance.")
                return
            cls = None
            candidates = llm.flat_candidates(self._lib.entries)
            task = llm.wish_task(opts["wishes"], opts["brief"])
            # A wish list is a flat list that the user, not the model, ordered.
            ctx = dict(mode="flat", label="\U0001f4dd Wish list")
        else:
            cls = None
            candidates = llm.flat_candidates(self._lib.entries)
            task = llm.flat_task(opts["count"], opts["brief"])
            ctx = dict(mode="flat", count=opts["count"])

        # What the open decks already hold. The model does not have to avoid it,
        # but it is told, so it can keep a second list off the same twenty songs.
        try:
            used_paths, _fps = self._deck_dedup_index()
        except Exception as exc:
            log.debug("🤖 Could not read the planned decks: %s", exc)
            used_paths = set()

        if not candidates:
            QMessageBox.information(
                self, "AI playlist",
                "No candidate tracks for those settings — check the dances, the\n"
                "start class and that the library actually holds those tempos.")
            return

        ctx["candidates"] = candidates
        # The deck this run belongs to, pinned NOW: `self._table` follows the
        # focus and a run takes minutes, so a click on another deck while the
        # model thinks must not send the answer into that deck's playlist.
        ctx["table"] = self._table
        self._ai_ctx = ctx
        # The exchange goes into a window of its own instead of behind a
        # spinner: two prompts, two replies and the query pass between them,
        # written down as they happen. It is not modal, so the button has to
        # be the thing that stops a second run starting on top of this one.
        previous = getattr(self, "_ai_log", None)
        if previous:                      # the last run's transcript, read or not
            previous.deleteLater()
        # Deliberately parentless: an owned window gets no taskbar button on
        # Windows, so minimising it during a long run loses it for good. This
        # reference is what keeps it alive, and closeEvent takes it down.
        self._ai_log = AiTranscriptDialog()
        self._ai_log.add_step(
            "note", "Pool",
            i18n.t("%d tracks are on the table, %d of them already in an open deck.")
            % (len(candidates), len(used_paths)) if used_paths
            else i18n.t("%d tracks are on the table.") % len(candidates))
        self._ai_log.show()
        self._cfg.ai_log_btn.setVisible(True)
        self._cfg.ai_playlist_btn.setEnabled(False)
        self._ai_worker = AiPlaylistWorker(
            opts["rules"], task, candidates, opts["model"],
            opts["config_dir"], self,
            dance_class=cls, used_paths=used_paths, lib=self._lib)
        w = self._ai_worker
        w.step.connect(self._ai_log.add_step)
        w.done.connect(self._on_ai_playlist_done)
        w.error.connect(self._on_ai_playlist_error)
        w.cancelled.connect(self._on_ai_playlist_cancelled)
        self._ai_log.stopRequested.connect(w.cancel)
        w.finished.connect(
            lambda: self._cfg.ai_playlist_btn.setEnabled(True))
        self.statusBar().showMessage("Asking the model for a playlist…")
        w.start()

    def _show_ai_log(self):
        """💬 — put the kept conversation back on screen. Closing its window
        only hides it; nothing but the next run throws it away."""
        log_dlg = getattr(self, "_ai_log", None)
        if not log_dlg:
            return
        log_dlg.show()
        log_dlg.setWindowState(
            log_dlg.windowState() & ~Qt.WindowState.WindowMinimized)
        log_dlg.raise_()
        log_dlg.activateWindow()

    def _on_ai_playlist_error(self, msg: str):
        log_dlg = getattr(self, "_ai_log", None)
        if log_dlg:
            log_dlg.add_step("note", "It failed", msg)
            log_dlg.finish("Failed — nothing was changed.")
        QMessageBox.critical(self, "AI playlist failed", msg)
        self.statusBar().showMessage("AI playlist failed.")

    def _on_ai_playlist_cancelled(self):
        log_dlg = getattr(self, "_ai_log", None)
        if log_dlg:
            log_dlg.finish("Stopped — nothing was changed.")
        self.statusBar().showMessage("AI playlist stopped.")

    def _back_to_ai_deck(self, ctx: dict):
        """Make the deck the run was started on the active one again.

        Called only once the answer is going to be written: a run that came
        back with nothing leaves the focus where the user put it. Going
        through `_reveal_deck` stashes the deck we are leaving and brings this
        deck's own generation context back, so everything after this writes to
        the deck that asked for the playlist."""
        table = ctx.get("table")
        if table is not None and table is not self._table:
            self._reveal_deck(table)

    def _on_ai_playlist_done(self, picks, notes: str, backend: str):
        ctx = getattr(self, "_ai_ctx", None) or {}
        candidates = ctx.get("candidates") or []
        self._suggester = PlaylistSuggester(self._lib)

        if ctx.get("mode") == "competition":
            dances, rounds = ctx["dances"], ctx["rounds"]
            grid = llm.assemble_grid(picks, candidates,
                                             dances, rounds)
            filled = sum(1 for heats in grid.values() for h in heats
                         for e in h if e is not None)
            if not filled:
                QMessageBox.information(
                    self, "AI playlist",
                    "The model answered, but none of its picks matched the\n"
                    "catalog. Try again — or lower the round count.")
                self._finish_ai_log("Nothing usable — the decks were left alone.")
                self.statusBar().showMessage("AI playlist: nothing usable.")
                return
            self._back_to_ai_deck(ctx)
            self._stash_active_replay()
            self._replay_label = None
            self._replay_active = False
            self._clear_replay_sources()
            self._style       = ctx["style"]
            self._age         = ctx["age"]
            self._dance_class = ctx["dance_class"]
            self._dances      = dances
            self._playlist    = grid
            self._mode        = "Favorites"
            self._ui_mode     = "Favorites"
            self._theme_entries = []
            self._table.load(
                grid, dances, rounds, ctx["dance_class"],
                play_cb=self._play_or_stop,
                suggester=self._suggester,
                use_timbre=ctx["use_timbre"],
                style=ctx["style"],
            )
            self._set_deck_name(
                self._table,
                self._favorites_deck_name(ctx["age"], ctx["dance_class"],
                                          ctx["style"]))
            total = sum(rc.heats for rc in rounds) * len(dances)
            head = i18n.t("🤖 %d/%d slots filled by %s") % (filled, total, backend)
        else:
            seen, entries = set(), []
            for p in picks:
                n = p["n"]
                if not (1 <= n <= len(candidates)):
                    continue
                e = candidates[n - 1]
                if str(e.path) in seen:
                    continue
                seen.add(str(e.path))
                entries.append(e)
            if not entries:
                QMessageBox.information(
                    self, "AI playlist",
                    "The model answered, but none of its picks matched the "
                    "catalog.")
                self._finish_ai_log("Nothing usable — the decks were left alone.")
                self.statusBar().showMessage("AI playlist: nothing usable.")
                return
            self._back_to_ai_deck(ctx)
            label = ctx.get("label") or "🤖 AI playlist"
            self._mode          = "Theme"
            self._ui_mode       = "Theme"
            self._playlist      = None
            self._theme_entries = entries
            self._theme_label   = label
            self._set_deck_name(self._table, label)
            self._table.load_theme(entries, label,
                                   play_cb=self._play_or_stop,
                                   suggester=self._suggester)
            # A flat list is a running order, not a draw — so hand the deck over
            # in ✋ free order: every row can be dragged anywhere, and a title
            # dropped in is ADDED where it lands instead of replacing what was
            # there. A theme grid would only allow a move within the same dance.
            self._table.become_player_list()
            self._refresh_mode_btn(self._table)
            head = i18n.t("🤖 %d tracks by %s") % (len(entries), backend)

        self._cfg.save_btn.setEnabled(True)
        # The transcript window is not modal and the deck view may be hiding
        # the very deck this just filled — bring the playlist forward, and the
        # main window with it, so a finished run is visibly finished.
        self._reveal_deck(self._table)
        self.raise_()
        self.activateWindow()
        self._show_hints([head] + ([notes] if notes else []))
        # The reasoning is the part that gets lost otherwise: everywhere else a
        # pick is just a number in a grid.
        why = llm.pick_reasons(picks, candidates, notes)
        if why and getattr(self, "_ai_log", None):
            self._ai_log.add_step("received", "Why these tracks", why)
        self._finish_ai_log(head)
        self.statusBar().showMessage(head)

    def _finish_ai_log(self, message: str):
        """Stop the transcript window's bar and say how the run ended. It stays
        open — reading back what was asked is the point of it."""
        log_dlg = getattr(self, "_ai_log", None)
        if log_dlg:
            log_dlg.finish(message)

    # ── 🏆 Event: a whole day planned from its history ──────────────────────

    def _plan_event(self, opts: dict):
        """Plan the pasted day's variants, the AI checking them if asked."""
        ev = opts["event"]
        if not ev["specs"]:
            QMessageBox.information(
                self, "Event plan",
                "No competition could be read from the schedule. Each line\n"
                "needs a class, a style (STD/LAT) or its dances in brackets,\n"
                "and the heats per round, e.g.  'HGR S STD 3-2-1'.")
            return
        if not ev["variants"]:
            QMessageBox.information(self, "Event plan",
                                    "Tick at least one variant to plan.")
            return
        editions = (event_plan.past_editions(ev["series"], before_year=ev["year"])
                    if ev["use_event"] and ev["series"] else [])
        if editions:
            history = ", ".join(d.name for d in editions)
        elif ev["use_event"]:
            history = i18n.t("no earlier edition found — the class lists carry the plan")
        else:
            history = i18n.t("not used")
        self._event_opts = opts
        self._event_run(
            EventPlanWorker(self._lib, ev["specs"], editions,
                            profiles=ev["variants"], use_class=ev["use_class"],
                            new_share=ev["new_share"], rare_share=ev["rare_share"],
                            ask_ai=ev["ai_check"],
                            rules=opts["rules"], model=opts["model"],
                            config_dir=opts["config_dir"],
                            similar=self._event_sound(), parent=self),
            i18n.t("%d competitions. Earlier editions: %s")
            % (len(ev["specs"]), history))

    def _event_sound(self) -> SoundAlike:
        """Timbre, groove and — where its index is built — the chroma cover
        match: a sound-alike must be close in all of them."""
        from planner import embeddings as ae
        store = self._embedding_store()
        chroma = (lambda e: store.recorded(e.path, ae.MODEL_CHROMA)) if store else None
        return SoundAlike(self._lib, chroma=chroma)

    def _continue_event_plan(self, only: list[int]):
        """Ask the AI again about `only`, starting from the plan as it stands."""
        timer = getattr(self, "_event_retry", None)
        worker = getattr(self, "_event_worker", None)
        if worker is not None and worker.isRunning():
            if timer is not None:           # still busy: try again shortly
                timer.start(5 * 60 * 1000)
            return
        if timer is not None:
            timer.stop()
        opts = self._event_opts
        self._event_run(
            EventPlanWorker(None, [], [], variants=self._event_result.variants,
                            cands_list=self._event_cands, only=only,
                            rules=opts["rules"], model=opts["model"],
                            config_dir=opts["config_dir"], parent=self),
            i18n.t("Asking again about: %s") % ", ".join(
                self._event_cands[i].spec.label for i in only))

    def _event_run(self, worker, intro: str):
        """Start an event worker with its own transcript window."""
        previous = getattr(self, "_ai_log", None)
        if previous:
            previous.deleteLater()
        self._ai_log = AiTranscriptDialog()
        self._ai_log.add_step("note", "Event", intro)
        self._ai_log.show()
        self._cfg.ai_log_btn.setVisible(True)
        self._cfg.ai_playlist_btn.setEnabled(False)
        self._event_worker = worker
        compare = getattr(self, "_event_compare", None)
        if compare is not None:             # no edits while the AI is asked
            compare.set_busy(True)
            worker.finished.connect(lambda: compare.set_busy(False))
        worker.step.connect(self._ai_log.add_step)
        worker.done.connect(self._on_event_plan_done)
        worker.error.connect(self._on_ai_playlist_error)
        worker.cancelled.connect(self._on_ai_playlist_cancelled)
        self._ai_log.stopRequested.connect(worker.cancel)
        worker.finished.connect(
            lambda: self._cfg.ai_playlist_btn.setEnabled(True))
        self.statusBar().showMessage("🏆 Planning the event…")
        worker.start()

    def _on_event_plan_done(self, result, cands_list):
        self._event_result = result
        self._event_cands = cands_list
        if getattr(self, "_ai_log", None):
            self._ai_log.add_step("note", "The plan",
                                  event_plan.describe_result(result, cands_list))
        head = i18n.t("🏆 %d competitions planned in %d variants") % (
            len(cands_list), len(result.variants))
        self._finish_ai_log(head)
        self.statusBar().showMessage(head)
        self._show_event_compare()
        if result.pending:
            self._offer_event_wait(result)

    def _offer_event_wait(self, result):
        """The AI's limit held competitions back: wait for it and go on."""
        delay = event_plan.retry_delay(result.reset_at, time.time())
        names = ", ".join(self._event_cands[i].spec.label for i in result.pending)
        ret = QMessageBox.question(
            self, "Event plan",
            i18n.t("The AI's limit held back: %s\n\n%s\n\n"
                   "Wait and ask again by itself in %d minutes?")
            % (names, result.limit, max(1, round(delay / 60))),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if ret != QMessageBox.StandardButton.Yes:
            return
        old = getattr(self, "_event_retry", None)
        if old is not None:                 # one waiting question at a time
            old.stop()
            old.deleteLater()
        timer = self._event_retry = QTimer(self)
        timer.setSingleShot(True)
        pending = list(result.pending)
        timer.timeout.connect(lambda: self._continue_event_plan(pending))
        timer.start(delay * 1000)
        self.statusBar().showMessage(
            i18n.t("🏆 Asking the AI again at %s")
            % time.strftime("%H:%M", time.localtime(time.time() + delay)))

    def _show_event_compare(self):
        """The kept plan side by side — opened once, then brought up to date."""
        dlg = getattr(self, "_event_compare", None)
        if dlg is None:
            dlg = self._event_compare = EventCompareDialog(
                self._event_result, self._event_cands, self,
                play_cb=self._play_or_stop, seek_cb=self._seek)
            dlg.continueRequested.connect(self._continue_event_plan)
            dlg.applyRequested.connect(self._apply_event_plan)
            dlg.prehearing.connect(self._on_event_prehear)
            dlg.tablesReplaced.connect(self._rehome_preview)
        else:
            dlg.set_result(self._event_result, self._event_cands)
        # show() and raise_() leave a minimized window down — the answer to
        # asking again would go into a window nobody sees.
        dlg.setWindowState(dlg.windowState() & ~Qt.WindowState.WindowMinimized)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_event_prehear(self, table, row: int, title: str):
        """A cell of the event plan plays: the decks' ▶/■ go back, and the
        mini player comes up below its row, as for the library pane."""
        for t in self._all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers(keep=self._event_compare)
        if (self._preview and self._settings.get("preview_player", True)
                and not self._is_playing_mode()):
            self._preview.show_for(table, row, title)

    def _rehome_preview(self):
        """The event plan's tables are about to be deleted — the mini player
        sitting in one of their viewports would be deleted with them."""
        dlg = getattr(self, "_event_compare", None)
        if self._preview and dlg is not None and dlg.isAncestorOf(self._preview):
            self._preview.hide()
            self._preview.setParent(None)

    def _apply_event_plan(self, profiles: list[str]):
        """📅 The event plan into the day decks, each competition as its tab
        chose (`profiles[i]`): a deck per competition, several sharing one
        when there are more than eight."""
        old_day = [t for t in self._day_decks
                   if self._serialize_playlist_state(t) is not None]
        if old_day:
            ret = QMessageBox.question(
                self, "Replace day plan",
                "The Tournament-day tab still holds an earlier day plan.\n\n"
                "Replace it with the new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
            for t in old_day:
                self._blank_deck(t)
        parts = [{"label": c.spec.label, "playlist": c.playlist(),
                  "dances": c.spec.dances, "rounds": c.rounds,
                  "cls": c.spec.dance_class, "style": c.spec.style,
                  "age": c.spec.label, "suggester": PlaylistSuggester(self._lib)}
                 for c in (self._event_result.variants[p][i]
                           for i, p in enumerate(profiles))]
        self._stash_active_replay()   # keep any worked competition grid first
        self._replay_label = None
        self._replay_active = False
        self._clear_replay_sources()
        use_timbre = self._cfg.get_config()[-1]
        assign = _spread_over_decks(self._day_decks, parts)
        for deck, deck_parts in assign:
            self._load_day_deck(deck, deck_parts, use_timbre)
        ev = self._event_opts["event"]
        if ev["series_name"]:
            self._set_day_tab_title(f"{ev['series_name']} {ev['year']}")
        self._apply_deck_view()   # reveal the 📅 Tournament-day tab
        self._deck_tabs.setCurrentIndex(2)
        self._day_tabs.setCurrentIndex(0)
        self._set_active_table(assign[0][0])
        self._cfg.save_btn.setEnabled(True)
        self._autosave_playlist()
        names = {i18n.t(event_plan.PROFILE_NAMES.get(p, p)) for p in profiles}
        _show_toast(self, i18n.t("🏆  %s: %d competitions into %d deck(s)")
                    % (" + ".join(sorted(names)), len(parts), len(assign)))

    def _show_hints(self, hints: list[str]):
        if hints:
            self._hints_lbl.setText("   ".join(hints))
            self._hints_lbl.setVisible(True)
        else:
            self._hints_lbl.clear()
            self._hints_lbl.setVisible(False)

    def _show_library_gaps(self):
        """📊 (Settings → 🎵 Checks): per dance × class pool statistics — where
        does the library run thin for a real competition?"""
        if not self._lib or not self._lib.entries:
            QMessageBox.information(
                self, "Library gaps",
                "The library is still loading — try again in a moment.")
            return
        dlg = LibraryGapsDialog(self._lib, self)
        dlg.exec()
        if not dlg.jump_to:
            return
        # 📚 "show these tracks": ⚙ Settings is still open on top of us, so close
        # it (keeping whatever was edited) and filter the pane once it is gone.
        dance, cls = dlg.jump_to
        settings_dlg = getattr(self, "_settings_dlg", None)
        if settings_dlg is not None:
            settings_dlg.accept()
        QTimer.singleShot(
            0, lambda: self.show_library_filtered(dance=dance, cls=cls,
                                                  plays="never"))

    def _open_ai_dialog(self):
        if not self._lib:
            return
        # Seed with the first selected dance (Favorites) or the chosen theme
        dance = self._dances[0] if self._dances else None
        theme = None
        if self._cfg.get_mode() == "Theme":
            _, theme, _ = self._cfg.get_theme_config()
            dance = None
        AiSuggestDialog(
            self._lib, self, play_cb=self._play_or_stop,
            dance=dance, theme=theme,
        ).exec()
