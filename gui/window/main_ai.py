"""🤖 A playlist written by an AI model: asking for it, the running log, and
loading what comes back onto a deck; plus the AI suggest dialog.

Extracted from gui/window/main_generate.py as a MainWindow mixin.
"""
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMessageBox

from gui.dialogs import AiPlaylistDialog, AiSuggestDialog, AiTranscriptDialog
from gui.workers import AiPlaylistWorker
from planner import i18n
from planner.event import event_plan
from planner.generate import llm
from planner.generate.suggester import PlaylistSuggester
from shared.stores import save_settings

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.generate")


class AiPlaylistMixin(MainWindowHost):
    """🤖 AI playlists: the request, its log and the picks it returns."""

    def _generate_ai_playlist(self):
        """🤖: let an LLM assemble the playlist instead of the scoring algorithm.

        The model first sees a per-dance summary of the TSO-conform candidates
        and asks for the slices it wants, then answers with the numbers it picked
        off those rows — it can never name a track that isn't in the library. Competition mode reuses the left panel's style / class / dances
        / rounds; flat mode just asks for N tracks in playing order; wish mode hands
        it the titles the user named and lets it find them."""
        if not self._library.lib or not self._library.lib.entries:
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

        self._remember_ai_options(opts)

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
                self._library.lib.entries, style, cls, dances)
            task = llm.competition_task(style, age, cls, dances, rounds,
                                                opts["brief"])
            ctx: dict[str, Any] = dict(mode="competition", style=style, age=age, dance_class=cls,
                       dances=dances, rounds=rounds, use_timbre=use_timbre)
        elif opts["mode"] == "wishes":
            if not opts["wishes"]:
                QMessageBox.information(
                    self, "AI playlist",
                    "The wish list is empty — write the titles you want, one\n"
                    "per line or a column per dance.")
                return
            cls = None
            candidates = llm.flat_candidates(self._library.lib.entries)
            task = llm.wish_task(opts["wishes"], opts["brief"])
            # A wish list is a flat list that the user, not the model, ordered.
            ctx = dict(mode="flat", label="\U0001f4dd Wish list")
        else:
            cls = None
            candidates = llm.flat_candidates(self._library.lib.entries)
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

        self._start_ai_run(opts, task, candidates, cls, used_paths, ctx)

    def _start_ai_run(self, opts, task, candidates, cls, used_paths, ctx):
        """💬 The transcript window and the worker that asks the model."""
        ctx["candidates"] = candidates
        # The deck this run belongs to, pinned NOW: `self._table` follows the
        # focus and a run takes minutes, so a click on another deck while the
        # model thinks must not send the answer into that deck's playlist.
        ctx["table"] = self._deckset.table
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
            dance_class=cls, used_paths=used_paths, lib=self._library.lib)
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

    def _remember_ai_options(self, opts):
        """The dialog's answers into the settings, for the next run."""
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
        if table is not None and table is not self._deckset.table:
            self._reveal_deck(table)

    def _on_ai_playlist_done(self, picks, notes: str, backend: str):
        ctx = getattr(self, "_ai_ctx", None) or {}
        candidates = ctx.get("candidates") or []
        self._suggester = PlaylistSuggester(self._library.lib)

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
            self._style = ctx["style"]
            self._age = ctx["age"]
            self._dance_class = ctx["dance_class"]
            self._dances = dances
            self._playlist = grid
            self._mode = "Favorites"
            self._ui_mode = "Favorites"
            self._theme_entries = []
            self._deckset.table.load(
                grid, dances, rounds, ctx["dance_class"],
                play_cb=self._play_or_stop,
                suggester=self._suggester,
                use_timbre=ctx["use_timbre"],
                style=ctx["style"],
            )
            self._set_deck_name(
                self._deckset.table,
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
            self._mode = "Theme"
            self._ui_mode = "Theme"
            self._playlist = None
            self._theme_entries = entries
            self._theme_label = label
            self._set_deck_name(self._deckset.table, label)
            self._deckset.table.load_theme(entries, label,
                                   play_cb=self._play_or_stop,
                                   suggester=self._suggester)
            # A flat list is a running order, not a draw — so hand the deck over
            # in ✋ free order: every row can be dragged anywhere, and a title
            # dropped in is ADDED where it lands instead of replacing what was
            # there. A theme grid would only allow a move within the same dance.
            self._deckset.table.become_player_list()
            self._refresh_mode_btn(self._deckset.table)
            head = i18n.t("🤖 %d tracks by %s") % (len(entries), backend)

        self._cfg.save_btn.setEnabled(True)
        # The transcript window is not modal and the deck view may be hiding
        # the very deck this just filled — bring the playlist forward, and the
        # main window with it, so a finished run is visibly finished.
        self._reveal_deck(self._deckset.table)
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

    def _open_ai_dialog(self):
        if not self._library.lib:
            return
        # Seed with the first selected dance (Favorites) or the chosen theme
        dance = self._dances[0] if self._dances else None
        theme = None
        if self._cfg.get_mode() == "Theme":
            _, theme, _ = self._cfg.get_theme_config()
            dance = None
        AiSuggestDialog(
            self._library.lib, self, play_cb=self._play_or_stop,
            dance=dance, theme=theme,
        ).exec()
