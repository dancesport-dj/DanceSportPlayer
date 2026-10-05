"""⏸ Between the rounds: the pause, its filler music and the spoken next dance.

Split off player/main_player.py as a MainWindow mixin. Nothing here plays a heat —
this is the time in between, which the hall still hears.
"""
import logging

import time
from PySide6.QtCore import (
    QTimer,
    QUrl,
)
from pathlib import Path

from player.announce import announce_secs
from planner import i18n
try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.pause")

# Speak the next dance this many seconds before the pause ends — late enough
# that the couples are already on the floor. Shorter pauses announce at once.
# A FLOOR, not the whole answer: a long announcement ("Nächster Tanz: West
# Coast Swing, Heat 5" runs past six seconds) starts earlier than this, see
# `_announce_lead`.
_ANNOUNCE_LEAD = 5.0
# …and the music waits this long after the last word. The hall should hear the
# call end, not have the next title come in on its tail.
_ANNOUNCE_TAIL = 1.2
# ⏳ …but the held-back start waits only this long. There the tail is not
# covered by anything: the pause has filler music running underneath, where
# 1.2s is inaudible, while a held start is silence from the last word to the
# first bar — and 1.2s of silence in a hall is a hole, not a breath. Nudge
# this, not _ANNOUNCE_TAIL, if the call and the music sit too close.
# 0.35 was the first nudge and the hall still heard it as a wait, so it is
# 0.20 now: a breath, not a beat.
_START_TAIL = 0.20
# ⏳ How often the held-back start looks to see whether the voice is done.
# Granularity, so it is added to _START_TAIL on top: kept well under it.
_ANNOUNCE_POLL_MS = 25


def _live_target(nxt):
    """An armed (table, row, path) advance, with the row re-found by its path.

    The row number was right when the advance was armed; a re-render during
    the pause (a reorder, a regen, a heat added above) moves the title while
    the number stays. The title is what was meant, so it is looked up again —
    the nearest copy when the list holds it twice. None once it is gone."""
    if nxt is None:
        return None
    t, row, path = nxt
    want = str(path)
    meta = t._row_meta.at(row)
    if meta is not None and meta.path_str == want:
        return nxt
    rows = [r for r, m in t._row_meta.numbered() if m.path_str == want]
    if not rows:
        return None
    return t, min(rows, key=lambda r: abs(r - row)), path


class PauseMusicMixin:
    """⏸ The pause between rounds: filler music and the spoken next dance."""

    def _heat_of(self, table, row) -> int | None:
        """The heat number a row sits in, or None when there is none to call.

        A generated round grid states its heat outright (h_idx). Every other
        list — a normal running order, a party set, an imported .m3u — has no
        grid, so the heat is read off the ORDER instead: three Sambas in the
        Vorrunde are heats 1, 2 and 3, and the count restarts with the next
        round strip. None when the operator didn't ask for the heat at all.
        """
        if table is None or not self._play_panel.announce_heat():
            return None
        if not (0 <= row < len(table._row_meta)):
            return None
        meta = table._row_meta[row]
        if not meta:
            return None
        if meta.round_name:
            return int(meta.h_idx) + 1
        return self._heat_by_order(table, row, meta)

    def _heat_by_order(self, table, row, meta) -> int | None:
        """How often this dance has come up in this section, this row included.

        The section is the ─── strip the row hangs under (the round, where the
        list knows its rounds; the whole list where it doesn't), so a Vorrunde
        and a Finale each count their heats from one.
        """
        dance = meta.dance or ""
        if not dance:
            return None
        section = table._row_round_hdr.get(row, -1)
        return sum(1 for r in range(row + 1)
                   for m in (table._row_meta[r],)
                   if m and (m.dance or "") == dance
                   and table._row_round_hdr.get(r, -1) == section) or None

    def _announce_dance_of(self, nxt) -> tuple[str, int | None, int | None]:
        """(dance code, takt, heat) of a (table, row, path) advance target."""
        nxt = _live_target(nxt)
        if nxt is None:
            return "", None, None
        t, nrow, _npath = nxt
        meta = t._row_meta[nrow] if 0 <= nrow < len(t._row_meta) else None
        if not meta:
            return "", None, None
        ent = meta.entry
        return (meta.dance or "", getattr(ent, "bpm", None) or None,
                self._heat_of(t, nrow))

    def _announce_lead(self) -> float:
        """How far before the end of the pause the voice has to start.

        Measured from the clips that will actually play, plus the quiet the
        hall gets afterwards. `_ANNOUNCE_LEAD` stays the floor: a short call
        keeps the settled timing, a long one simply starts earlier instead of
        running into the music.

        Falls back to the floor whenever the length cannot be known — the takt
        is read by the synthesiser, whose speed is the system's.
        """
        if self._between.pending is None:
            return _ANNOUNCE_LEAD
        code, takt, heat = self._announce_dance_of(self._between.pending)
        secs = announce_secs(code,
                             takt if self._play_panel.announce_takt() else None,
                             heat=heat)
        return max(_ANNOUNCE_LEAD, secs + _ANNOUNCE_TAIL) if secs \
            else _ANNOUNCE_LEAD

    def _hold_for_announcement(self) -> bool:
        """The pause has run out but the voice has not — True to keep waiting.

        The lead above is an estimate; this is the measurement behind it. A
        clip that ran longer than its trim said, a synthesiser nobody can time
        beforehand, an announcement that only started late — either way the
        next title must not come in over the last word.

        It cannot hold the evening: the announcer gives `speaking` up after its
        own 8 s watchdog even when the engine never reports back.
        """
        if self._between.pending is None:
            return False
        now = time.monotonic()
        if self._announcer.speaking:
            self._between.quiet_until = now + _ANNOUNCE_TAIL
        if now >= self._between.quiet_until:
            return False
        self._set_countdown("🔈  announcing…")
        return True

    def _maybe_announce_next(self):
        """Speak the coming dance once per pause, shortly before it ends."""
        if (self._between.announced or self._between.pending is None
                or not self._pv("announce")
                # ✋ Manual under THIS deck stops its announcement too — 🔁 can
                # reach a pause with the switch off, so it is asked here again.
                or not self._deck_advance(self._between.pending[0])):
            return
        self._between.announced = True   # set first: a dead engine must not retry per tick
        code, takt, heat = self._announce_dance_of(self._between.pending)
        if not code:
            return
        self._announcer.speak(code,
                              takt if self._play_panel.announce_takt() else None,
                              heat=heat)

    def _playing_row(self):
        """(deck, row) of the row that is actually playing (the one with a
        marked ▶), or (None, -1)."""
        t = next((t for t in self._all_tables if t._current_play_row >= 0), None)
        return (t, t._current_play_row) if t is not None else (None, -1)

    def _wants_start_call(self) -> bool:
        """Whether this start names its dance at all.

        Playing mode (a preview while planning is an audition), 🔈 on, and the
        list in play on ⏭ Auto — ✋ Manual means the hall has its own announcer.
        And no pause: with one the call goes INTO the pause, which is a gap of
        its own, timed by `_announce_lead`."""
        return bool(self._is_playing_mode()
                    and self._pv("announce")
                    and self._playing_advance()
                    and not self._engine_pause_secs() > 0
                    and self._playback.dance)

    def _speak_start_call(self, ent) -> bool:
        """Name the dance that is starting ("Langsamer Walzer", not "Nächster
        Tanz: …"). False when nothing was said."""
        takt = getattr(ent, "bpm", None) or None
        return self._announcer.speak(
            self._playback.dance, takt if self._play_panel.announce_takt() else None,
            now=True, heat=self._heat_of(*self._playing_row()))

    def _announce_start_first(self, ent) -> bool:
        """⏳ Call the dance into silence and hold the music for it.

        Without a pause the call has no gap of its own, so by default it runs
        over the first bars with the music ducked under it — in the hall that
        is the dance being named and the dance being played at the same time.
        This is the other answer: the voice first, the music after it.

        True when the call was actually made and the music is now waiting. A
        call that could not be made (no clips, no speech engine) holds nothing
        back — a title that never starts is worse than one announced over."""
        if not self._play_panel.announce_wait() or not self._wants_start_call():
            return False
        return bool(self._speak_start_call(ent))

    def _wait_for_announcement(self, path):
        """Hold the music until the call is over, then start it.

        Nothing counts down and nothing is on the speakers: what the hall gets
        is the dance named, a breath, and the music — which is the whole point
        of asking for it. The wait is measured, not estimated, the same way the
        pause measures it in `_hold_for_announcement`."""
        self._between.quiet_until = time.monotonic() + _START_TAIL
        self._poll_announcement(self._playback.token, path)

    def _poll_announcement(self, token: int, path):
        """Is the voice done? Start the music; else look again in a moment.

        It cannot hold the evening: the announcer gives `speaking` up after its
        own watchdog even when the engine never reports back."""
        if token != self._playback.token:
            return          # ■, or the next title took the player meanwhile
        now = time.monotonic()
        if self._announcer.speaking:
            self._between.quiet_until = now + _START_TAIL
        if now < self._between.quiet_until:
            QTimer.singleShot(_ANNOUNCE_POLL_MS,
                              lambda: self._poll_announcement(token, path))
            return
        self._release_held_start(token, path)

    def _maybe_announce_start(self, ent):
        """No break configured → no pause to announce into, so name the dance
        over the first bars of the music instead (the music ducks under it).

        Not under ⏳: there the call was made before the music started, by
        `_announce_start_first`, and naming it again would be the call arriving
        after the thing it announced."""
        if self._play_panel.announce_wait() or not self._wants_start_call():
            return
        self._speak_start_call(ent)

    def _announce_test(self):
        """🔈 Test in the play panel — hear voice and level before the round."""
        takt = 29 if self._play_panel.announce_takt() else None
        heat = 3 if self._play_panel.announce_heat() else None
        if not self._announcer.speak("LW", takt, heat=heat):
            self.statusBar().showMessage(
                "🔈 No speech engine available on this system.", 6000)

    def _on_to_pause(self):
        """⏸♪ on the big player: end the playing song right now and jump into
        the between-songs pause (filler music + countdown), exactly as a timed
        play-length end would. Needs Playing mode + auto-advance + a next song;
        otherwise it just stops the song."""
        if self._between.pending is not None:
            return   # already in the pause
        if not self._is_playing_mode() or self._playback.path is None:
            return
        self._on_timed_end()
        if self._between.pending is None:
            self.statusBar().showMessage(
                "No pause started — enable auto-advance and have a next song "
                "queued.", 5000)

    def _extend_pause(self):
        """⏱➕: lengthen the running auto-advance pause by one more pause
        length, so a heat change that runs long doesn't cut to the next song
        too soon. The preloaded filler keeps rotating meanwhile."""
        if self._between.pending is None:
            self.statusBar().showMessage(
                "No auto-advance pause is running to extend.", 4000)
            return
        extra = max(4, self._engine_pause_secs())
        self._between.advance_at += extra
        self._between.shown = True   # 🖥 held by hand — now the hall should see it
        # Keep the fade-out ramp proportional to the (now longer) pause.
        self._filler.total += extra
        r = int(self._between.advance_at - time.monotonic() + 0.999)
        self._set_countdown(f"⏸  {r} s")
        self.statusBar().showMessage(
            i18n.t("⏱ Auto-advance pause extended by %ss.") % extra, 3000)

    def _start_next_round(self) -> bool:
        """⏯ on the big player after a 🏁 round-end stop: start the next
        round's first song. Returns True when the tap was handled."""
        nxt = _live_target(self._between.round_start)
        self._between.round_start = None
        if nxt is None:
            return False    # its title left the deck: ⏯ does what it always does
        t, nrow, npath = nxt
        t._on_play_click(nrow, npath)
        t.scroll_row_into_play_view(nrow)
        return True

    def _start_pause_music(self):
        """Start the optional filler for the between-songs pause (silent — the
        tick fades it in). The current title resumes where the last pause left
        off; when it ends, _on_pause_media_status rotates to the next one.
        Very short pauses skip it (no room for an audible fade in + out)."""
        paths = self._play_panel.pause_music()
        secs = self._engine_pause_secs()
        if not paths or not self._pause_player or secs < 4:
            return
        path = self._filler.load(paths)
        if path is None:
            log.warning("🎵 Pause music not found\n"
                        "files: %s", "\n".join(paths))
            return
        url = QUrl.fromLocalFile(path)
        if self._pause_player.source() != url:
            self._pause_player.setSource(url)
        self._filler.total = float(secs)
        self._pause_out.setVolume(0.0)
        self._pause_player.play()
        self._filler.active = True

    def _on_pause_media_status(self, status):
        """A filler title ran out mid-pause → rotate to the next one (a single
        title restarts from the top) and update the big-player status."""
        if (status != QMediaPlayer.MediaStatus.EndOfMedia
                or not self._pause_player or not self._filler.titles):
            return
        path = self._filler.rotate()
        url = QUrl.fromLocalFile(path)
        if self._pause_player.source() != url:
            self._pause_player.setSource(url)
        else:
            self._pause_player.setPosition(0)
        if self._between.pending is not None:   # pause still running
            self._pause_player.play()
            self._filler.active = True
            self._show_pause_status()

    def _show_pause_status(self):
        """Pause display: with filler music the title line carries the filler
        (walking text if too long) and 'Auto-advance' moves to the subtitle
        row; the card's seek bar/⏯ control the FILLER player meanwhile."""
        if self._filler.active and self._filler.titles:
            stem = Path(self._filler.current).stem
            self._now_playing.setText(i18n.t("⏸ Auto-advance…  🎵 %s") % stem)
            if self._big_player and self._pause_player:
                self._big_player.set_now(
                    "", subtitle="Auto-advance…", status=stem,
                    sub_icon="pause_circle")
                self._big_player.set_player(self._pause_player)
        else:
            self._now_playing.setText("⏸  Auto-advance…")
            if self._big_player:
                self._big_player.set_now("", status="Auto-advance…",
                                         sub_icon="pause_circle")
        self._refresh_next_up()   # set_now("") cleared it — the pause needs it most

    def _update_pause_music(self, remaining: float):
        """Fade ramp of the filler: in over the first seconds of the pause,
        out over the last ones; follows the user's base volume in between."""
        if (not self._pause_player
                or self._pause_player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        self._mix.filler_fade = self._filler.fade(remaining)
        self._update_pause_music_volume()

    def _update_pause_music_volume(self):
        """The filler's level: its own fade ramp × the shared announcement duck.

        Split out of the 200 ms fade tick because the duck ramps in 25 ms steps
        — stepping the filler only every fifth of a second would leave the very
        artefact the ramp exists to avoid."""
        if self._pause_out is None:
            return
        self._pause_out.setVolume(
            self._mix.filler(self._play_panel.pause_music_vol() / 100.0))

    def _stop_pause_music(self):
        """Silence the filler, keeping its position for the next pause."""
        self._filler.active = False
        if self._big_player and self._player:
            self._big_player.set_player(self._player)   # card back to main
        if (self._pause_player
                and self._pause_player.playbackState()
                != QMediaPlayer.PlaybackState.StoppedState):
            self._pause_player.pause()
            self._pause_out.setVolume(0.0)
