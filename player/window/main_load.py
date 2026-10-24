"""Loading a title onto the player: the load itself, the mini player that pops
up under its row, the ↩ place a title was left at, and what happens when a
title won't play.

↩ One player serves every deck, so stepping away from a half-heard title is
the normal way to lose your place in it. self._resume
(player.audio.resume_marks) keeps the place, in memory, for as long as the
app runs; the methods here wire it to the switch, the player and the row
badges.

Extracted from player/window/main_player.py as a MainWindow mixin.
"""
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QMessageBox

import planner.generate.warmup
from planner import i18n, terms
from planner.terms import dance_name
from shared.audio.playback import pre_roll_secs
from shared.stores import ON_AIR, save_settings
from shared.widgets import _show_toast
from player.audio.on_air_note import NOTE
from player.window.main_pause import _live_target

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object
try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.player")


# Shortest gap between two loads handed to the media backend. Below this a fast
# ⏭ burst is coalesced to its last target — long enough to spare Windows Media
# Foundation a teardown per keypress, short enough that a single press still
# feels immediate.
_LOAD_MIN_GAP_MS = 250.0


class TrackLoadMixin(MainWindowHost):
    """Loading a title, the ↩ resume marks, the mini player and the failover."""

    def deck_path(self) -> Path | None:
        """The title the player is on, or about to load: a load held back by
        the rate limit or by the loudness wait already counts. A preview
        window asks before it stops the shared player."""
        if self._pending_load is not None:
            return self._pending_load[0]
        if self._lufs_pending is not None:
            return self._lufs_pending
        return self._playback.path

    def _play_or_stop(self, path: Path | None, start: bool = True):
        """Play the given path, or stop if path is None.

        start=False cues the track (loads the source + shows it on the card) but
        leaves it stopped, so the user presses ⏯ to begin — used for drag-drop
        onto the player, which must not auto-start playback.

        Loads are rate-limited (see _LOAD_MIN_GAP_MS): a single press still hits
        the backend immediately, but hammering ⏭ only moves the target and one
        load follows when the burst settles. Stopping is never delayed.
        """
        if not self._player:
            return
        gap_left = _LOAD_MIN_GAP_MS - 1000.0 * (time.monotonic() - self._last_load_at)
        if path is not None and gap_left > 0:
            # A newer title supersedes one still waiting for its loudness:
            # that wait would otherwise start the old title when its level
            # lands, before this one loads.
            self._lufs_pending = None
            self._pending_load = (path, start)
            self._load_timer.start(int(gap_left))
            return
        self._pending_load = None
        self._load_timer.stop()
        self._load_track(path, start)

    def _flush_pending_load(self):
        """The skip burst is over — load whatever the last press landed on."""
        pending = self._pending_load
        self._pending_load = None
        if pending is not None:
            self._load_track(*pending)

    def _load_track(self, path: Path | None, start: bool = True):
        """The real work of `_play_or_stop` — everything that touches the media
        backend. Only ever entered through the rate limit above."""
        if not self._player:
            return
        self._last_load_at = time.monotonic()
        t0 = time.perf_counter()
        self._playback.token += 1
        self._cued = path is not None and not start   # ⏯ starts it (_start_cued)
        if path != self._playback.path and self._play_panel.pd_editing():
            # A new title cancels hand-marking — otherwise its highlight stop
            # would stay suspended on a track nobody is editing any more.
            self._play_panel.set_pd_edit(False)
            self._pd_verify_stop = False
        self._remember_stop_point()   # ↩ before the stop takes the position away
        self._player.stop()
        self._stop_play_timer()
        self._crossfade_takes(path)   # 🔀 its incoming title, or the end of it
        if path is not None and self._await_loudness(path, start):
            return      # …re-enters here the moment the level is known
        if path is None:
            self._unload_track(self._player)
        else:
            ent = self._adopt_track(path)
            if self._playback.dance == "PD" and self._pd_highlight()[0]:
                self._ensure_pd_highlights(path)
            self._ensure_silences(path)   # arm the 🔇 stillness skip
            self._arm_fade_in(path)
            self._mix.load_gain(self._loudness_gain(path))
            self._apply_volume()
            url = QUrl.fromLocalFile(str(path))
            if self._player.source() != url:
                # Errors the backend queued before this source belong to the
                # title it replaces. The timer is posted first, so it runs
                # after all of them and before anything about the new title.
                QTimer.singleShot(0, lambda t=self._playback.token:
                                  self._end_stale_errors(t))
                self._player.setSource(url)
                self._playback.stale_error_token = self._playback.token
            else:
                self._seek_preloaded()
            pitched = self._pitch_before_play(ent, start)
            # 🐂 A Paso Doble may be held back a few seconds after the dance is
            # called, so the couples stand before the first bar. Everything up
            # to here has happened — the file is open, pitched and levelled;
            # only the play() waits.
            hold = self._pd_start_hold() if start else 0.0
            # ⏳ The other way round: the dance is called into silence and the
            # music follows the voice. Asked BEFORE the play(), because that is
            # the play() it holds back.
            waiting = bool(start and not hold
                           and self._announce_start_first(ent))
            if start and not hold and not waiting:
                self._player.play()
            if self._big_player:
                # Qt may drop a rate set while the player was idle — re-assert.
                # Free when the early set stuck: apply_tempo skips a no-op.
                self._big_player.apply_tempo()
            if start and not hold and not waiting:
                self._fade_timer.start()
                # After play(): the announcement ducks what is running, so the
                # music has to be on its way already.
                self._maybe_announce_start(ent)
            self._now_playing.setText(
                (f"▶  {path.stem[:80]}") if start else (i18n.t("⏸  cued: %s") % path.stem[:74]))
            self._show_big_now(path, ent, start, pitched)
            self._sync_big_player_limit()
            self._refresh_next_up()
            self._show_preview(path)
            self._arm_start(path, start, hold, waiting)
            # ⏱ What the GUI thread spent before the backend took over. The
            # matching "media ready" line comes from _on_media_status, so a slow
            # start can be blamed on us or on the decoder without guessing.
            self._play_t0 = t0
            self._play_ready_logged = False
            log.info("⏱ Play requested\n"
                     "file: %s\n"
                     "blocking: %.0f ms", path.name, 1000 * (time.perf_counter() - t0))
        self._preview_src = None

    def _unload_track(self, player):
        """Nothing on the deck: drop the source and every display of a title."""
        # Clear the source too: the Windows (WMF) backend keeps the file open
        # otherwise, and a stale source can wedge the NEXT load.
        player.setSource(QUrl())
        self._now_playing.setText("No song selected")
        if self._big_player:
            self._big_player.set_now("")
            self._big_player.set_artwork(None)
            self._big_player.set_waveform_track(None)
            self._big_player.set_current_dance(None)
        self._playback.dance = ""
        self._playback.path = None
        self._played_marked = False
        self._playback.offset_ms = 0
        self._sync_dance_len()        # 🏆 the panel's length: the picked row's again
        self._sync_taskbar_title()    # 🪟 nothing loaded → the window's name
        if self._preview:
            self._preview.hide()

    def _adopt_track(self, path):
        """`path` becomes the deck's title; returns its library entry."""
        # 🕘 What is on the deck right now becomes the last played — but
        # only when something else really takes over: a restart of the same
        # file must not make a title its own predecessor.
        if self._playback.path is not None and self._playback.path != path:
            self._last_played = (
                dance_name(self._playback.dance, self._playback.dance),
                self._playback.path.stem)
        self._between.round_start = None   # a song starts — round-end resume done
        ent = self._resolve_entry(str(path))
        # warmup_code, not .dance: a social title (Discofox, Salsa, …) has
        # no competition code, and with an empty dance it was never
        # announced and showed a blank dance on the card.
        # 🐂 The row it was started from names it first: a grid slot keeps its
        # dance whatever the title is tagged, and a path the library does not
        # hold verbatim (a Mac copy) comes back named by its file name alone —
        # a Paso Doble row then played no Paso Doble, and the stop never ran.
        self._playback.dance = self._row_dance(path) or (
            (planner.generate.warmup.warmup_code(ent) or "") if ent is not None else "")
        self._playback.path = path
        self._played_marked = False   # fresh track — re-arm the 10 s rule
        self._playback.offset_ms = 0      # …and no silence skipped on it yet
        self._sync_dance_len()        # 🏆 this dance's own length, where it has one
        # ↩ Seeking here would be thrown away — the media is not open yet.
        # `_on_media_status` performs it the moment it is.
        self._resume_seek_ms = self._resume_mark_for(path)
        self._playback.pre_roll_ms = self._pre_roll_ms_for(path)   # ⏩ …or this
        self._refresh_resume_marks(path)   # the row badges follow the deck
        # 🪟 The taskbar caption names the title, and a new one has to reach
        # it here: the state change alone does not fire between two songs
        # of a heat, and the caption would keep naming the previous one.
        self._sync_taskbar_title()
        return ent

    def _row_dance(self, path) -> str:
        """The dance of the deck row playing `path`, or "" — no row is marked,
        or the marked one still holds the title before (a drop onto the card
        cues without marking one)."""
        table, row = self._playing_row()
        meta = table._row_meta.at(row) if table is not None else None
        if meta is None or meta.path_str != str(path):
            return ""
        return meta.dance

    def _pitch_before_play(self, ent, start):
        """Takt, fader and TSO pitch into the stopped track; True once pitched."""
        # Everything that moves the playback RATE happens here, while the
        # track is still stopped: a rate change makes the backend re-init
        # its resampler, and doing that after play() is a hole you hear at
        # the top of every title. Set into silence and there is nothing to
        # cut. The takt is needed first — TSO pitches against it.
        pitched = False
        if self._big_player:
            self._big_player.set_takt(
                ent.bpm if ent is not None and getattr(ent, "bpm", 0) else None)
            self._big_player.set_current_dance(self._playback.dance or None)
            self._big_player.on_new_track()   # zero the fader if armed…
            self._big_player.apply_tempo()    # …then push the resulting rate
            if start and self._big_player.tso_mode() and self._is_playing_mode():
                pitched = self._equalize_heat_tempo(auto=True)
        return pitched

    def _show_big_now(self, path, ent, start, pitched):
        """The big player's now line, cover, waveform and gain for `path`."""
        if self._big_player:
            meas = (float(getattr(getattr(ent, "features", None), "bpm", 0) or 0)
                    if ent is not None else 0.0)
            bits = [b for b in (
                terms.DANCE_SHORT.get(self._playback.dance, self._playback.dance),
                f"T{ent.bpm}" if ent is not None and getattr(ent, "bpm", 0) else "",
                f"🥁 {meas:.0f} bpm" if meas > 0 else "",
            ) if b]
            self._big_player.set_now(path.stem, "  ·  ".join(bits))
            self._big_player.set_artwork(path, self._playing_m3u())
            self._big_player.set_waveform_track(path)
            self._big_player.set_gain(self._mix.heard_gain())
            # Second try for the TSO pitch: the deck only knows which row is
            # playing once it has told us, so on some paths the early one
            # above found nothing to pitch against. Costs a gap — but a
            # wrongly pitched heat costs more.
            if (not pitched and start and self._big_player.tso_mode()
                    and self._is_playing_mode()):
                self._equalize_heat_tempo(auto=True)

    def _arm_start(self, path, start, hold, waiting):
        """🐂 The PD hold, ⏳ the wait for the call, or the load watchdog."""
        if start and hold:
            # …the wait counts down on the left panel, speaks the call if
            # the announcement is on, and starts the music (with its own
            # watchdog) when it is over.
            self._hold_pd_start(hold, path)
        elif start and waiting:
            # …and this one waits for the voice that has just started,
            # silently: the hall is listening to the call.
            self._wait_for_announcement(path)
        elif start:
            # Watchdog: if the backend silently hangs in Loading/Stalled (it
            # happens on rapid source switches), retry the load once, then give
            # up cleanly instead of showing a forever-"playing" dead player.
            # Tied to the window: it goes when the window does.
            token = self._playback.token
            QTimer.singleShot(2000, self, lambda: self._check_playback(token, path))

    def _check_playback(self, token: int, path: Path, retried: bool = False):
        """Watchdog for `_play_or_stop`: verify playback really started; one
        retry, then a clean stop + status message. Stale tokens no-op."""
        if not self._player or token != self._playback.token:
            return
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            return   # playing — or deliberately paused by the user
        status = self._player.mediaStatus()
        if status in (QMediaPlayer.MediaStatus.EndOfMedia,
                      QMediaPlayer.MediaStatus.NoMedia):
            return   # finished or stopped meanwhile — nothing to rescue
        if not retried:
            log.warning("🔁 Playback stuck (status %s) — reloading\n"
                        "file: %s", status, path)
            self._player.stop()
            self._player.setSource(QUrl())
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self._player.play()
            QTimer.singleShot(2500, self, lambda: self._check_playback(token, path, True))
            return
        log.error("🔇 Playback did not start (status %s)\nfile: %s", status, path)
        self._playback_failed(path, i18n.t("did not start"),
                              i18n.t("⚠ Could not play: %s") % path.name)

    def _reset_playback_ui(self, message: str):
        """Stop the player and put every play button / the status line back to
        idle — shared by the playback-error handler and the watchdog."""
        self._playback.token += 1
        self._stop_play_timer()
        if self._player:
            self._player.stop()
            self._player.setSource(QUrl())
        for t in self._deckset.all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()
        if self._preview:
            self._preview.hide()
        self._now_playing.setText("No song selected")
        if self._big_player:
            self._big_player.set_now("")
        self.statusBar().showMessage(message, 8000)

    def _end_stale_errors(self, token: int):
        """Every error queued before the load's setSource has been seen."""
        if self._playback.stale_error_token == token:
            self._playback.stale_error_token = None

    def _on_player_error(self, _error, error_string: str):
        """A decode/backend failure used to leave the UI 'playing' silently —
        surface it and reset, so a broken file never looks like a stuck app."""
        if self._playback.stale_error_token is not None:
            # Raised for the previous title: the source now names the next
            # one, which would be marked failed and skipped for nothing.
            log.info("🔇 Previous title's playback error ignored\n"
                     "error: %s", error_string or "unknown")
            return
        src = self._player.source().toLocalFile() if self._player else ""
        log.error("🔇 Playback error\n"
                  "error: %s\n"
                  "file: %s", error_string or "unknown", src)
        reason = error_string or i18n.t("unknown error")
        self._playback_failed(Path(src) if src else None, reason,
                              i18n.t("⚠ Playback failed: %s") % reason)
        # A row checks for its file only when it is filled: one deleted or
        # renamed since then still looks fine. Repaint its rows (→ red ❗) and
        # say so where it is seen — the status line alone went unnoticed.
        if src and not Path(src).exists():
            for t in self._deckset.all_tables:
                t.refresh_paths([Path(src)])
            _show_toast(self, i18n.t("⚠ File not found on disk:\n%s") % Path(src))

    def _playback_failed(self, path: Path | None, reason: str, message: str):
        """A title would not play: remember it, put the UI back to idle and,
        when the evening runs by itself, start the next title instead of
        leaving the floor without music.

        The next title is looked up BEFORE the reset — afterwards no table
        remembers which row was playing."""
        nxt = self._failover_target() if path is not None else None
        if path is not None:
            self._playback.failed[str(path)] = reason
        self._reset_playback_ui(message)
        if path is None:
            return
        for t in self._deckset.all_tables:
            t.refresh_issue_marks()      # → its rows turn red, reason in the tooltip
        if nxt is None:
            return
        log.warning("⏭ Skipped a title that would not play\n"
                    "failed: %s\n"
                    "next: %s", path.name, Path(nxt[2]).name)
        _show_toast(self, i18n.t("⚠ “%s” would not play — skipped to the next title.")
                    % path.stem)
        # Not from inside the backend's own error signal: start it once that
        # has returned.
        QTimer.singleShot(0, lambda: self._start_failover(nxt))

    def _failover_target(self):
        """The title a failed one hands over to: the next one of its round,
        when Playing mode runs with ⏭ auto-advance. None at the end of a round
        (the operator starts the next round, as after a title that ends
        normally) and under 🔁, which would only hand the title to itself."""
        if (not self._is_playing_mode() or self._looping()
                or not self._playing_advance()):
            return None
        nxt = self._next_song_to_advance()
        if nxt is None:
            return None
        t, nrow, _npath = nxt
        row = t._current_play_row
        if row is None or nrow <= row:
            return None
        cur, nmeta = t._row_meta.at(row), t._row_meta.at(nrow)
        if cur is None or nmeta is None or cur.round_name != nmeta.round_name:
            return None
        return nxt

    def _start_failover(self, nxt):
        """Start the title a failed one handed over to, if it is still there."""
        nxt = _live_target(nxt)
        if nxt is None:
            return
        t, nrow, npath = nxt
        t._on_play_click(nrow, npath)
        t.scroll_row_into_play_view(nrow)

    def _show_preview(self, path: Path):
        """Pop the UltraMixer-style mini player under the row whose ▶ was clicked.
        Skipped when disabled in ⚙ Settings, in Playing mode (the big player
        already shows everything) or when playback didn't start from a deck
        (e.g. the Similar-Tracks dialog — its own window covers the decks)."""
        if (not self._preview or not self._settings.get("preview_player", True)
                or self._is_playing_mode()):
            return
        src = self._preview_src
        if src is None or src._current_play_row < 0:
            # Playback isn't anchored to a deck row (Similar-Tracks dialog, library
            # pane…). The overlay's slider stays wired to the shared player, so a
            # leftover overlay would keep ticking on the new track while its title
            # is frozen on the old one — hide it instead of leaving it stale.
            # One that already names this title isn't stale: the library pane
            # opens it itself, before a rate-limited load has caught up.
            if (self._preview.isVisible()
                    and self._preview.title() != path.stem):
                self._preview.hide()
            return
        self._preview.show_for(src, src._current_play_row, path.stem)

    def _sync_preview_to_playback(self):
        """Pop the overlay for the song that's already playing — used when the
        preview player gets re-enabled in ⚙ Settings mid-playback."""
        if (not self._preview or not self._settings.get("preview_player", True)
                or self._is_playing_mode()
                or not self._player
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        for t in self._deckset.all_tables:
            row = t._current_play_row
            if 0 <= row < len(t._row_meta) and t._row_meta[row]:
                entry = t._row_meta[row].entry
                if entry is not None:
                    self._preview.show_for(t, row, entry.path.stem)
                return

    def _disable_preview(self):
        """⚙ menu on the overlay: turn the preview player off and persist it."""
        self._settings["preview_player"] = False
        save_settings(self._settings)
        if self._preview:
            self._preview.hide()
        cue = self._cue_player()
        if cue is not None:
            cue.view.hide()   # the pre-listen plays on, without its mini player
        self.statusBar().showMessage(
            "Preview player disabled — re-enable it in ⚙ Settings.")

    def remember_pos(self) -> bool:
        """Whether the ↩ switch on the Playing panel is on."""
        return bool(self._settings.get("remember_pos", False))

    def _set_remember_pos(self, on: bool):
        """The ↩ switch moved. Switching it off drops every mark: a tick left
        on a bar by a switch that is now off is a promise nothing will keep."""
        if not on and self._resume.clear_all():
            self._refresh_resume_marks()

    def _resume_mark_for(self, path: Path) -> int | None:
        """Where `path` should be picked up again, or None.

        Only the big player spends a mark. The floating overlay is a pre-listen
        — a title tried there starts at its top and keeps the place it holds in
        the big player, so hearing a snippet while planning never costs the spot
        the set was actually left at.
        """
        if not self.remember_pos() or not self._is_playing_mode():
            return None
        return self._resume.get(path)

    def _pre_roll_ms_for(self, path: Path) -> int:
        """⏩ How far into `path` the big player starts it, or 0. A ↩ mark
        wins, a title a 🔀 crossfade brings in is running already, and the
        floating overlay's pre-listen starts at the top."""
        xf = self._between.xfade
        if (self._resume_seek_ms is not None or not self._is_playing_mode()
                or (xf.state == "fading" and path == xf.incoming)):
            return 0
        return 1000 * pre_roll_secs(self._settings)

    def _note_resume(self, path: Path, pos_ms: int, dur_ms: int):
        """Keep (or drop) the mark for `path` at `pos_ms` (ResumeMarks.note
        decides which) and repaint the badges."""
        self._resume.note(path, pos_ms, dur_ms)
        self._refresh_resume_marks(path)

    def _clear_resume(self, path: Path | None):
        """Forget where `path` stood — it has just been heard to the end."""
        if path is not None and self._resume.clear(path):
            self._refresh_resume_marks(path)

    def _on_back_to_start(self):
        """⏮ 0:00 on the card: the title starts over, so the ↩ mark of where
        it stopped before goes — the next load would pick it up there again.
        A pick-up still waiting for the media would undo the rewind, too."""
        self._resume_seek_ms = None
        self._clear_resume(self._playback.path)

    def _remember_stop_point(self):
        """Note where the running title stands, just before it is stopped.

        Only while it really is on the player: `_load_track` is re-entered once
        a track's loudness is known, and by then the deck is stopped and
        position() reads 0 — recording that would wipe the mark instead of
        setting it.
        """
        if not self.remember_pos() or self._player is None:
            return
        if not self._is_playing_mode():
            # Only the big player keeps a place. The floating overlay is for a
            # quick listen while planning — every row tried there would leave a
            # badge behind, and none of them is a title anyone comes back to.
            return
        path = self._playback.path
        if path is None:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            return
        self._note_resume(path, self._player.position(), self._player.duration())

    def _refresh_resume_marks(self, path: Path | None = None):
        """Repaint the ↩ badges on the deck rows.

        Only the rows carry a mark: the seek bar would draw its tick exactly
        where the playhead already stands, since a picked-up title starts there.

        `path` only says which title moved — every deck gets the whole dict and
        repaints the rows whose badge actually changed.
        """
        for t in self._deckset.all_tables:
            t.set_resume_marks(self._resume.at)

    # ── 🆘 Picking up after a crash ───────────────────────────────────────────

    def _note_on_air(self):
        """Say on disk which title is playing on which row — once a title, in
        the background (NOTE). A crash leaves the note behind for the next
        start (_offer_crash_resume); every stop takes it away (_drop_on_air)."""
        table, row = self._playing_row()
        if table is None or self._playback.path is None:
            return
        on_air = (self._deckset.all_tables.index(table), row, str(self._playback.path))
        if on_air == self._playback.on_air:
            return
        self._playback.on_air = on_air
        NOTE.write(dict(zip(("table", "row", "path"), on_air, strict=True)))

    def _drop_on_air(self):
        """The title stopped on purpose: there is nothing to pick up."""
        if self._playback.on_air is not None:
            self._playback.on_air = None
            NOTE.remove()

    def _on_air_row(self, note) -> tuple | None:
        """(table, row, path) of the note's title, or None when its deck no
        longer holds it. A row that moved is found by its file."""
        try:
            table = self._deckset.all_tables[int(note["table"])]
            row, path = int(note["row"]), Path(note["path"])
        except (TypeError, KeyError, ValueError, IndexError):
            return None
        rows = [r for r, m in table._row_meta.numbered()
                if str(getattr(m.entry, "path", "")) == str(path)]
        if not rows:
            return None
        return table, (row if row in rows else rows[0]), path

    def _offer_crash_resume(self):
        """The last run did not end while a title was on air: ask whether to
        cue it again on its row, from its start. Not modal — the library scan
        goes on behind the question.

        ▶ The titles the evening had played (ResumeSessionMixin) come in the
        same question; with no title on air, after a restart or a crash
        between titles, they are asked about on their own."""
        note = ON_AIR.read()
        ON_AIR.remove()
        hit = self._on_air_row(note) if isinstance(note, dict) else None
        evening = self._evening_to_offer()
        if hit is None:
            if evening is not None:
                self._offer_evening(evening)
            return
        table, row, path = hit
        log.warning("🆘 The last run ended while a title was playing\n"
                    "file: %s", path)
        text = i18n.t("The last session ended while “%s” was playing.\n\n"
                      "Cue it again?") % path.stem
        if evening is not None:
            text += "\n" + i18n.t("The %d titles played this evening grey out again.") % (
                len(evening.played))
        box = QMessageBox(
            QMessageBox.Icon.Question, i18n.t("Pick up after a crash?"), text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        box.buttonClicked.connect(
            lambda b: self._crash_answered(
                box.standardButton(b) == QMessageBox.StandardButton.Yes,
                table, row, path, evening))
        box.open()

    def _crash_answered(self, yes: bool, table, row: int, path: Path, evening):
        if yes:
            self._resume_on_air(table, row, path)
        if evening is not None:
            self._evening_answered(evening, yes)

    def _resume_on_air(self, table, row: int, path: Path):
        """Cue `path` on its row in Playing mode; ⏯ starts it."""
        self._set_play_mode(True)
        self._load_track(path, False)   # straight to the load, past the rate limit
        for t in self._deckset.all_tables:
            if t is not table and t._current_play_row >= 0:
                t.on_playback_stopped()
        table.cue_row(row)
