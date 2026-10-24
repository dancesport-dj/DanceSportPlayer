"""🏆 Event: a whole day planned from its history — asking for the plan, the
side-by-side comparison of its variants, and laying the chosen one onto the
decks.

Extracted from gui/window/main_generate.py as a MainWindow mixin.
"""
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMessageBox

from planner import i18n
from planner.event import event_plan
from planner.generate.suggester import PlaylistSuggester
from planner.music.similarity import SoundAlike
from shared.widgets import _show_toast
from gui.dialogs import AiTranscriptDialog
from gui.dialogs.event_compare import EventCompareDialog
from gui.workers import EventPlanWorker

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object


def _spread_over_decks(decks: list, items: list) -> list[tuple]:
    """(deck, items) pairs: one item per deck, or contiguous chunks of several
    when there are more items than decks — the day's order stays readable."""
    n_decks = min(len(decks), len(items))
    base, rem = divmod(len(items), n_decks)
    sizes = [base + 1] * rem + [base] * (n_decks - rem)
    it = iter(items)
    return [(deck, [next(it) for _ in range(size)])
            # Fewer sizes than decks when there are fewer items: the rest stay empty.
            for deck, size in zip(decks, sizes, strict=False)]


class EventPlanMixin(MainWindowHost):
    """🏆 Event plans: the run, the comparison and the decks it fills."""

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
            EventPlanWorker(self._library.lib, ev["specs"], editions,
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
        from planner.music import embeddings as ae
        store = self._embedding_store()
        chroma = (lambda e: store.recorded(e.path, ae.MODEL_CHROMA)) if store else None
        return SoundAlike(self._library.lib, chroma=chroma)

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
                play_cb=self._prehear, seek_cb=self._prehear_seek)
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
        if self._cue_wanted():
            # 🎧 Pre-listening: the decks play on, their ■ stays.
            self._reset_aux_play_markers(keep=self._event_compare)
            self._show_cue_view(table, row, title)
            return
        for t in self._deckset.all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers(keep=self._event_compare)
        if (self._preview and self._settings.get("preview_player", True)
                and not self._is_playing_mode()):
            self._preview.show_for(table, row, title)

    def _rehome_preview(self):
        """The event plan's tables are about to be deleted — the mini player
        sitting in one of their viewports would be deleted with them."""
        dlg = getattr(self, "_event_compare", None)
        cue = self._cue_player()
        for view in (self._preview, cue.view if cue is not None else None):
            if view and dlg is not None and dlg.isAncestorOf(view):
                view.hide()
                view.setParent(None)

    def _apply_event_plan(self, profiles: list[str]):
        """📅 The event plan into the day decks, each competition as its tab
        chose (`profiles[i]`): a deck per competition, several sharing one
        when there are more than eight."""
        old_day = [t for t in self._deckset.day_decks
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
                  "age": c.spec.label, "suggester": PlaylistSuggester(self._library.lib)}
                 for c in (self._event_result.variants[p][i]
                           for i, p in enumerate(profiles))]
        self._stash_active_replay()   # keep any worked competition grid first
        self._replay_label = None
        self._replay_active = False
        self._clear_replay_sources()
        use_timbre = self._cfg.get_config()[-1]
        assign = _spread_over_decks(self._deckset.day_decks, parts)
        for deck, deck_parts in assign:
            self._load_day_deck(deck, deck_parts, use_timbre)
        ev = self._event_opts["event"]
        if ev["series_name"]:
            self._set_day_tab_title(f"{ev['series_name']} {ev['year']}")
        self._apply_deck_view()   # reveal the 📅 Tournament-day tab
        self._grid.deck_tabs.setCurrentWidget(self._grid.day_tabs)
        self._grid.day_tabs.setCurrentWidget(self._grid.day_split)
        self._set_active_table(assign[0][0])
        self._cfg.save_btn.setEnabled(True)
        self._autosave_playlist()
        names = {i18n.t(event_plan.PROFILE_NAMES.get(p, p)) for p in profiles}
        _show_toast(self, i18n.t("🏆  %s: %d competitions into %d deck(s)")
                    % (" + ".join(sorted(names)), len(parts), len(assign)))
