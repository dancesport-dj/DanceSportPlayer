"""🐂 The Paso Doble highlight stop: where the highlights are, and stopping on one.

Split off player/main_player.py as a MainWindow mixin. A PD is played to a
highlight — the crash the choreography lands on — not to a play length, so
where those sit is worth its own detection, its own hand-marking and its own
memory.
"""
import logging
import time

from pathlib import Path
from PySide6.QtCore import QTimer
from shared.audio_probes import PdHighlightWorker  # auto-resolved
from player.pd_stop import pd_stop_at
from planner import i18n

log = logging.getLogger("dancesport.gui.pd")

# 🐂 How often the wait after the call repaints its countdown.
_PD_HOLD_TICK_MS = 200
# 🎯 Hand-marking: a new mark this close to an existing one MOVES it (a second
# tap corrects the first) instead of stacking two marks on the same crash.
_PD_MARK_SNAP = 3.0


class PdStopMixin:
    """🐂 Paso Doble highlights: detect, hand-mark, remember, stop on one —
    and the wait between the call and the first bar."""

    def _pd_runs_to_its_highlight(self) -> bool:
        """Whether the playing title is a Paso Doble that ends on its own terms.

        Under the 🐂 stop a Paso Doble is never faded and ignores the play
        length — it is danced to its choreographed highlights, and only one of
        those (or the file's own end) may end it. With the stop switched off
        there is nothing musical left to end it, so it goes back to being an
        ordinary title: the play length cuts it and the fade takes it out, like
        every other dance.
        """
        return self._playback.dance == "PD" and self._play_panel.pd_highlight_stop()

    # ── The wait after the call ───────────────────────────────────────────────

    def _pd_start_hold(self) -> float:
        """Seconds this start has to wait, or 0 to start now.

        Only a Paso Doble, only in Playing mode: a preview while planning is an
        audition, and holding it back for five silent seconds would read as a
        player that isn't working.
        """
        if not self._is_playing_mode() or self._playback.dance != "PD":
            return 0.0
        return max(0.0, float(self._play_panel.pd_start_delay()))

    def _pd_call_wanted(self) -> bool:
        """Whether the app itself calls the dance at the head of the wait.

        The same switch as everywhere else — 🔈 Announce next dance. Off, the
        hall has its own announcer and the wait simply runs silently. ✋ Manual
        under the deck in play says the same thing for that list alone.

        Not when a pause has just announced it: `_maybe_announce_next` speaks
        into the last seconds of the pause, and the wait then does what it is
        there for — it follows that call. Two calls in a row would only say the
        same thing twice.
        """
        if not self._pv("announce") or not self._playing_advance():
            return False
        return not self._engine_pause_secs() > 0

    def _hold_pd_start(self, secs: float, path: Path, ent):
        """Call the Paso Doble (or let the hall's announcer do it) and start the
        music `secs` later.

        The couples walk on and take position on the call; a Paso Doble that
        starts on the word is danced from the wrong bar. The file is already
        loaded and pitched at this point — the wait costs nothing but silence,
        and the release is a bare play().
        """
        spoken = self._pd_call_wanted()
        if spoken:
            takt = getattr(ent, "bpm", None) or None
            # `now=True` — the bare "Paso Doble", not "Nächster Tanz: …". The
            # couples are already walking on when this is called; it is the
            # hall announcer's word for the dance that starts here, and the
            # seconds run from it.
            self._announcer.speak(
                "PD", takt if self._play_panel.announce_takt() else None,
                now=True, heat=self._heat_of(*self._playing_row()))
        self._pd_hold = (self._playback.token, path, time.monotonic() + secs)
        self._pd_hold_timer = QTimer()
        self._pd_hold_timer.setInterval(_PD_HOLD_TICK_MS)
        self._pd_hold_timer.timeout.connect(self._pd_hold_tick)
        self._pd_hold_timer.start()
        self._pd_hold_tick()          # paint the first second without a delay
        log.info("🐂 Paso Doble held back after the call\n"
                 "file: %s\n"
                 "wait: %d s\n"
                 "called by: %s", path.name, int(secs),
                 "the app" if spoken else "the hall")

    def _pd_hold_tick(self):
        """Count the wait down on the left Playing panel.

        Nothing is on the speakers while it runs — with the call left to the
        hall there is no sound at all — so the panel says what is coming and in
        how long, the way the between-songs pause does.
        """
        if self._pd_hold is None:
            return
        token, path, until = self._pd_hold
        if token != self._playback.token:
            self._end_pd_hold()       # a stop / the next title took the player
            return
        remaining = until - time.monotonic()
        if remaining > 0:
            r = int(remaining + 0.999)
            self._set_countdown(i18n.t("🐂  Paso Doble in %d s") % r)
            self._now_playing.setText(f"🐂  {r} s  —  {path.stem[:70]}")
            return
        self._end_pd_hold()
        self._release_held_start(token, path)

    def _skip_pd_hold(self) -> bool:
        """⏯ while the wait is counting: start the music now.

        The count is an estimate of how long the couples need; the operator
        watching them is the better judge. Tapping play cuts the rest of it —
        the same start the wait would have made, just earlier. Returns True
        when a wait was actually running — not for one that has already lost
        the player and only waits for its next tick to be dropped.
        """
        if self._pd_hold is None:
            return False
        token, path, _until = self._pd_hold
        self._end_pd_hold()
        if token != self._playback.token:
            return False
        log.info("🐂 Paso Doble wait cut short by ⏯\n"
                 "file: %s", path.name)
        self._release_held_start(token, path)
        return True

    def _end_pd_hold(self):
        """Drop the wait and its ticker — it has run out, or lost the player."""
        self._pd_hold = None
        if self._pd_hold_timer is not None:
            self._pd_hold_timer.stop()
            self._pd_hold_timer = None

    def _release_held_start(self, token: int, path: Path):
        """The wait is over — start the music, unless something else has taken
        the player since (a stop, the next title, another deck)."""
        if not self._player or token != self._playback.token:
            return
        if not self._is_player_running():
            self._player.play()      # …⏯ during the wait already started it
        self._fade_timer.start()
        # No `_maybe_announce_start` here: the dance has been called ALREADY —
        # at the head of the wait (or by the pause before it, or by the hall).
        # Naming it a second time over the first bars is the call arriving after
        # the music it was counted from.
        self._now_playing.setText(f"▶  {path.stem[:80]}")
        self._set_countdown("")
        QTimer.singleShot(2000, lambda: self._check_playback(token, path))

    # ── Highlights ────────────────────────────────────────────────────────────

    def _ensure_pd_highlights(self, path: Path):
        """Arm the highlight stop for a playing Paso Doble: use the session
        cache or the DB (filled by 🐂 Analyze PD highlights) if we can, else
        run the detection in the background and arm once the result lands
        (the song keeps playing meanwhile)."""
        if str(path) in self._pd_highlights:
            self._arm_pd_stop(path)
            return
        if self._cache:
            stored = self._cache.get_pd_highlights(path)
            if stored is not None:
                self._pd_highlights[str(path)] = list(stored)
                self._arm_pd_stop(path)
                return
        # Nothing known yet: arm the standard phrase positions now so the track
        # has a stop while the detection runs (re-armed for real when it lands).
        self._arm_pd_stop(path)
        if self._pd_worker is not None and self._pd_worker.isRunning():
            return   # a detection is already running — this one keeps the guess
        w = PdHighlightWorker(path, parent=self)
        w.done.connect(self._on_pd_highlights)
        w.error.connect(self._on_pd_error)
        self._pd_worker = w
        w.start()

    def _arm_pd_stop(self, path: Path):
        """Set the stop position from the highlights and the chosen highlight
        number — `pd_stop_at` has the policy."""
        if self._play_panel.pd_editing():
            # ✏️ Hand-marking: nothing cuts the title, so a later crash can be
            # reached, heard and marked — otherwise the mark just set becomes
            # the stop and the song ends the moment it's made.
            self._pd_stop_at = None
        elif not self._play_panel.pd_highlight_stop():
            self._pd_stop_at = None
        else:
            self._pd_stop_at = pd_stop_at(
                self._pd_highlights.get(str(path)) or [],
                self._play_panel.pd_highlight_n(),
                manual=bool(self._cache and self._cache.is_pd_manual(path)),
                duration=self._track_duration(path),
                takt=self._track_takt(path),
                name=path.name)
        self._sync_big_player_limit()

    def _track_duration(self, path: Path) -> float:
        """Best-effort track length in seconds: the player's reported duration
        when this is the loaded track, else the scanned entry's metadata."""
        ms = self._player.duration()
        if ms and ms > 0 and str(path) == str(self._playback.path):
            return ms / 1000.0
        ent = self._resolve_entry(str(path))
        return float(getattr(ent, "duration", 0) or 0)

    def _track_takt(self, path: Path) -> float:
        """The track's takt in bars per minute (0 = unknown). `MusicEntry.bpm`
        is bars, not beats — a Paso Doble at "T60" has bpm 60."""
        ent = self._resolve_entry(str(path))
        return float(getattr(ent, "bpm", 0) or 0)

    @staticmethod
    def _merge_pd_mark(marks: list[float], pos: float) -> list[float]:
        """The mark list after setting one at `pos`: a mark within _PD_MARK_SNAP
        seconds MOVES there (correcting an early/late tap instead of stacking a
        second mark on the same crash), a fourth mark replaces the nearest one,
        and the result stays sorted. Same rule as the iOS ruler."""
        out = list(marks)
        near = next((i for i, t in enumerate(out)
                     if abs(t - pos) <= _PD_MARK_SNAP), None)
        if near is not None:
            out[near] = pos
        elif len(out) < 3:
            out.append(pos)
        else:
            out[min(range(len(out)), key=lambda i: abs(out[i] - pos))] = pos
        return sorted(out)

    def _learn_pd_highlight(self):
        """🎯 Mark the current playhead as a Paso Doble highlight (flagged manual
        so 🐂 auto-detection never overwrites it). The first manual mark on a
        track replaces any auto guess; further marks add the 2nd / 3rd."""
        path = self._playback.path
        if self._playback.dance != "PD" or path is None or not self._cache:
            self.statusBar().showMessage(
                "🎯 Play a Paso Doble first, then click when a highlight hits.", 4000)
            return
        pos = self._player.position() / 1000.0
        if pos <= 0:
            return
        if self._cache.is_pd_manual(path):
            base = [t for t in (self._pd_highlights.get(str(path)) or [])
                    if t is not None]
        else:
            base = []   # first manual mark wipes the auto guess
        marks = self._merge_pd_mark(base, round(pos, 2))
        self._store_pd_marks(path, marks)
        mmss = f"{int(pos) // 60}:{int(pos) % 60:02d}"
        log.info("🎯 Manual Paso Doble highlight set\n"
                 "file: %s\n"
                 "highlights: %s", path.name,
                 ", ".join(f"{t:.1f}s" for t in marks))
        if self._play_panel.pd_editing():
            self.statusBar().showMessage(
                i18n.t("🎯 Highlight at %s — %d mark(s). ✔ Done editing arms the stop.")
                % (mmss, len(marks)), 4000)
        else:
            self.statusBar().showMessage(
                i18n.t("🎯 PD highlight %d marked at %s (stop set to #%s)")
                % (len(marks), mmss, self._play_panel.pd_highlight_n()), 4000)

    def _store_pd_marks(self, path: Path, marks: list[float]):
        """Persist a hand-edited mark list, re-arm the stop and refresh the
        chips. An empty list means 'forget it' — auto-detection takes over."""
        if marks:
            self._pd_highlights[str(path)] = marks
            self._cache.put_pd_highlights(path, marks, manual=True)
        else:
            self._pd_highlights.pop(str(path), None)
            self._cache.clear_pd_highlights(path)
        self._cache.save()
        self._arm_pd_stop(path)
        self._refresh_pd_chips()

    def _delete_pd_mark(self, secs: float):
        """✕ on a mark chip. Dropping the last one reverts the track to 🐂
        auto-detection rather than leaving it with no highlights at all."""
        path = self._playback.path
        if path is None or not self._cache:
            return
        marks = [t for t in (self._pd_highlights.get(str(path)) or [])
                 if t is not None and abs(t - secs) >= 0.05]
        self._store_pd_marks(path, marks)
        if not marks:
            self.statusBar().showMessage(
                "🎯 Last mark deleted — 🐂 auto-detection takes over again.", 4000)

    def _refresh_pd_chips(self):
        """Push the current track's marks onto the panel's chip row."""
        marks = [t for t in (self._pd_highlights.get(str(self._playback.path))
                             or []) if t is not None] \
            if self._playback.path is not None else []
        self._play_panel.set_pd_marks(marks)

    def _on_pd_edit_toggled(self, on: bool):
        """✏️ Edit highlights on/off. On: the stop is suspended (see
        _arm_pd_stop) and the whole title is reachable. Off: the stop is armed
        again and the next time it's reached playback PAUSES there instead of
        advancing, so the mark can be checked by ear."""
        self._pd_verify_stop = not on
        self._refresh_pd_chips()
        if on and self._player:
            # Hold the music the moment editing starts: the stop is suspended,
            # so otherwise the title would just run on through the hall while
            # the marks are being sorted out. ⏯ / the scrubber resume it.
            self._player.pause()
        if self._playback.path is not None and self._playback.dance == "PD":
            self._arm_pd_stop(self._playback.path)
        else:
            self._sync_big_player_limit()
        self.statusBar().showMessage(
            "✏️ Editing highlights — playback paused; scrub to a crash, ⏯ to "
            "listen, 🎯 sets a mark at the playhead." if on else
            "✔ Highlights armed — playback pauses at the stop once so you can "
            "check it.", 6000)

    def _clear_pd_highlight(self):
        """✖ Forget the current track's highlights (manual or auto) and let
        auto-detection take over again on the next play."""
        path = self._playback.path
        if path is None or not self._cache:
            return
        self._cache.clear_pd_highlights(path)
        self._cache.save()
        self._pd_highlights.pop(str(path), None)
        self._pd_stop_at = None
        self._refresh_pd_chips()
        self.statusBar().showMessage(
            "🎯 Highlights cleared — 🐂 auto-detection will run again.", 4000)
        if self._playback.dance == "PD" and self._play_panel.pd_highlight_stop():
            self._ensure_pd_highlights(path)
        self._sync_big_player_limit()

    def _on_pd_highlights(self, path_str: str, times: list):
        self._pd_highlights[path_str] = list(times)
        if self._cache:   # persist, so the next session arms instantly
            self._cache.put_pd_highlights(Path(path_str), times)
            self._cache.save()
        log.info("🐂 Paso Doble highlights detected\n"
                 "file: %s\n"
                 "highlights: %s", Path(path_str).name,
                 ", ".join("?" if t is None else f"{t:.1f}s" for t in times)
                 or "none")
        # Arm only if that very track is still the one playing.
        if (self._playback.path is not None
                and str(self._playback.path) == path_str
                and self._playback.dance == "PD"):
            self._arm_pd_stop(self._playback.path)

    def _on_pd_error(self, path_str: str, _msg: str):
        # Remember the failure so we don't re-analyze on every play.
        self._pd_highlights[path_str] = []
