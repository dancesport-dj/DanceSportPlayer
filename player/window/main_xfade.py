"""🔀 Crossfade: the next title comes in under the end of the last one.

Split off player/window/main_player.py as a MainWindow mixin. Two players take
turns as the deck. When a crossfade starts, the one playing the outgoing title
becomes the tail and carries its last seconds out without being touched, and
the other one becomes the deck and walks on to the next title exactly as an
ordinary advance does, only coming in from silence. Nothing that is heard ever
changes player, so there is no switch to hear. (A tail that reopened the
outgoing file and took over from the deck was tried first: a seek is never
sample-exact, and the jump between the two was audible.)

Everything that follows the deck by name moves with the swap: the window's
handlers, the player card, the preview overlay and the output device.

A crossfade only happens where the list would have walked on with no gap
anyway: ⏭ auto-advance on, no pause, the next title in the same round, no 🔁,
no 🐂 Paso Doble run to its highlight and no 🔉↓ fade by hand. A heat — advance
off, or a pause — keeps its gap.
"""
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, QUrl

from planner.playing.play_sets import crossfade_curve, crossfade_secs
from shared.xfade_view import lead_secs
from shared.audio.playback import (
    audible_played_secs,
    crossfade_levels,
    prime_disconnect_notify,
)

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object
try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.xfade")

# The ramp is stepped as often as the other level ramps (see player.audio.mix).
_STEP_MS = 25
# ⏩ How long before the ramp the spare player opens the incoming title: the
# WMF backend takes a noticeable moment for that, which must not fall into
# the ramp.
_PRELOAD_SECS = 10.0


class CrossfadeMixin(MainWindowHost):
    """The second player and the two ramps of a crossfade. Their state is
    `self._between.xfade` (player.audio.between_dances.Crossfade), not loose fields
    on the window."""

    def _xfade_secs(self) -> float:
        """The playing list's crossfade length, 0 = off. A list saved before
        the crossfade existed has no value for it — off."""
        return crossfade_secs(self._xfade_vals())

    def _xfade_vals(self) -> dict:
        """The play values of the list the crossfade would run on."""
        t = self._engine_list()
        return self._play_panel.play_set() if t is None else self._list_vals(t)

    def _music_left(self) -> float | None:
        """Wall-clock seconds until the running title ends on its own: the
        ⏳ cut, the 🔇 dead air behind the last note or the file's end,
        whichever comes first. None while the length is not known yet."""
        if self._player is None:
            return None
        rate = max(0.01, self._player.playbackRate())
        pos = self._player.position()
        end = self._silence_stop_ms()   # 0 is dead air from the first sample
        if end is None:
            end = self._player.duration()
            if end <= 0:
                return None
        left = (end - pos) / 1000.0 / rate
        limit = self._play_end_secs()
        if limit > 0:
            played = audible_played_secs(pos, self._playback.offset_ms, rate)
            left = min(left, limit - played)
        return left

    def _crossfade_target(self):
        """(table, row, path) the crossfade would bring in, or None where the
        list would not walk straight on: no next title, or the 🏁 end of a
        round, which waits for the operator."""
        nxt = self._next_song_to_advance()
        if nxt is None:
            return None
        t, nrow, _npath = nxt
        row = t._current_play_row
        cur, nm = t._row_meta.at(row), t._row_meta.at(nrow)
        if (cur is not None and nm is not None and nrow > row
                and cur.round_name != nm.round_name):
            return None
        return nxt

    def _crossfade_due(self, left: float | None) -> bool:
        """Whether the tick should start a crossfade now, `left` seconds before
        the running title ends."""
        secs = self._xfade_secs()
        if secs <= 0 or left is None or left > secs or left <= 0.2:
            return False
        return self._crossfade_coming()

    def _crossfade_coming(self) -> bool:
        """Whether the end of the running title will crossfade: the list
        walks straight on from it, with nothing in the way."""
        if (self._between.xfade.state is not None
                or not self._is_playing_mode() or not self._playing_advance()
                or self._engine_pause_secs() > 0 or self._looping()
                or self._fade_now.running or self._pd_runs_to_its_highlight()
                or self._play_panel.pd_editing()):
            return False
        # ⏹ Never fade into a planned stop: that title is the last one.
        end = datetime.now() + timedelta(seconds=self._music_left() or 0)
        if self._play_panel.stop_due(end):
            return False
        return self._crossfade_target() is not None

    def _maybe_crossfade(self):
        """Every play tick: start a crossfade when it is due, and walk the
        picture's marker in before it and out after it."""
        xf = self._between.xfade
        if xf.state is not None:
            return   # the ramp steps the marker itself
        secs = self._xfade_secs() if self._is_playing_mode() else 0.0
        left = self._music_left() if secs > 0 else None
        if left is not None and self._crossfade_due(left):
            self._start_crossfade(left)
            return
        mark = None
        if xf.after_until is not None:
            now = time.monotonic()
            if now < xf.after_until:
                mark = (now - xf.t0) / xf.length
            else:
                xf.after_until = None
        elif (left is not None and left <= secs + _PRELOAD_SECS
                and self._crossfade_coming()):
            self._preload_incoming()
            if left <= secs + lead_secs(secs):
                mark = (secs - left) / secs
        self._show_mark(mark)

    def _preload_incoming(self):
        """⏩ Hand the title the crossfade will bring in to the spare player
        now, so the swap is a bare play() instead of a file open — the head
        start the pause before a dance gives too (see _queue_auto_advance).
        A ⏭ or 📱 jump to another title simply loads that one at the swap."""
        nxt = self._crossfade_target()
        spare = self._spare_deck()
        if nxt is None or spare is None:
            return
        url = QUrl.fromLocalFile(str(nxt[2]))
        if spare.source() != url:
            spare.setSource(url)

    def _show_mark(self, t: float | None):
        """Put the picture's marker at `t` ramp lengths, None = away."""
        xf = self._between.xfade
        if t != xf.mark:
            xf.mark = t
            self._play_panel.xfade_view.set_progress(t)

    def _spare_deck(self):
        """The second player, built on first use — most evenings never fade."""
        xf = self._between.xfade
        if xf.player is None and HAS_MULTIMEDIA:
            xf.player = QMediaPlayer(self)
            xf.out = QAudioOutput(self)
            xf.player.setAudioOutput(xf.out)
            prime_disconnect_notify(xf.player, xf.out)
            xf.timer = QTimer(self)
            xf.timer.setInterval(_STEP_MS)
            xf.timer.timeout.connect(self._step_crossfade)
        return xf.player

    def _skip_target(self):
        """The path ⏭ would load: the title after the playing row, or None
        past the end of the list."""
        for t in self._deckset.all_tables:
            row = t._current_play_row
            if row < 0:
                continue
            nrow, npath = t.next_song_row(row, +1)
            return npath if nrow >= 0 else None
        return None

    def _crossfade_skip(self) -> bool:
        """⏭ with the crossfade on: fade into the next title instead of
        cutting — even into the next round, the operator asked for it. False
        where ⏭ stays a plain cut: crossfade off, planning, a pause between
        dances, the deck not playing, a 🔉↓ fade by hand, a crossfade already
        running, or no next title."""
        secs = self._xfade_secs()
        if (secs <= 0 or self._between.xfade.state is not None
                or not self._is_playing_mode() or self._engine_pause_secs() > 0
                or self._fade_now.running or self._player is None
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState
                or self._skip_target() is None):
            return False
        self._remember_stop_point()   # as a plain ⏭ keeps it, before the swap
        return self._start_crossfade(secs, skip=True)

    def _crossfade_jump(self, table, row: int, path) -> bool:
        """📱 A next title tapped on the phone: the running one fades out while
        the tapped one comes in — over the crossfade's length, or over the
        fade-out time where the crossfade is off. Unlike ⏭ not held back by a
        pause between dances: the operator asked for this title now. False
        where nothing is there to fade out: planning, the deck not playing, a
        🔉↓ fade by hand or a crossfade already running."""
        if (self._between.xfade.state is not None or not self._is_playing_mode()
                or self._fade_now.running or self._player is None
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return False
        secs = self._xfade_secs() or float(self._pv("fade"))
        self._remember_stop_point()   # as a plain ⏭ keeps it, before the swap
        return self._start_crossfade(secs, jump=(table, row, path))

    def _start_crossfade(self, left: float, skip: bool = False,
                         jump: tuple | None = None) -> bool:
        """Hand the running title to the tail and bring the next one in: the
        list's next title, for a ⏭ the row after the playing one, or the
        `jump` (table, row, path) tapped on the phone."""
        xf = self._between.xfade
        spare = self._spare_deck()
        if jump is not None:
            incoming = jump[2]
        elif skip:
            incoming = self._skip_target()
        else:
            nxt = self._crossfade_target()
            incoming = nxt[2] if nxt is not None else None
        if (spare is None or xf.out is None or self._player is None
                or incoming is None):
            return False
        xf.length = max(0.5, left)
        # Kept for the whole fade: a curve picked meanwhile is the next one's.
        xf.curve = crossfade_curve(self._xfade_vals())
        xf.incoming = incoming
        log.info("🔀 Crossfade starting\n"
                 "out: %s\n"
                 "in: %s\n"
                 "length: %.1fs\n"
                 "by: %s",
                 self._playback.path.name if self._playback.path else "?",
                 Path(incoming).name, xf.length,
                 "📱" if jump is not None else "⏭" if skip else "the list")
        self._hand_over(skip, jump)
        return True

    def _hand_over(self, skip: bool = False, jump: tuple | None = None):
        """The tail carries the old title out where it is; the other player,
        now the deck, walks on to the next one exactly as an advance with no
        pause does — or, for a ⏭, exactly as ⏭ does, and for a title tapped
        on the phone as a click on its ▶."""
        xf = self._between.xfade
        xf.state = "fading"
        xf.t0 = time.monotonic()
        # The level it plays at already: the tail goes on without a step.
        self._mix.tail_gain = self._mix.gain * self._mix.fade
        self._swap_decks()
        if jump is not None:
            table, row, path = jump
            table._on_play_click(row, path)
            table.scroll_row_into_play_view(row)
        elif skip:
            self._preview_skip(+1)
        else:
            self._on_timed_end("crossfade")
            self._fire_pending_advance()   # no pause: start it now, from silence
        if xf.timer is not None:
            xf.timer.start()

    def _deck_slots(self) -> list[tuple[str, object]]:
        """(signal, handler) of everything the window hangs on the deck."""
        slots: list[tuple[str, object]] = [
            ("mediaStatusChanged", self._on_media_status),
            ("errorOccurred", self._on_player_error),
            ("playbackStateChanged", self._audio_device.on_playback_state),
            ("playbackStateChanged", self._on_playback_state),
            ("playbackStateChanged", self._cart_follow_deck)]
        if self._taskbar is not None:
            slots.append(("playbackStateChanged", self._on_taskbar_state))
        return slots

    def _swap_decks(self):
        """The spare player becomes the deck and the deck the tail — and all
        that follows the deck moves over: the handlers, the card, the overlay
        and the output's device."""
        xf = self._between.xfade
        old, new = self._player, xf.player
        if old is None or new is None or xf.out is None:
            return
        for name, slot in self._deck_slots():
            getattr(old, name).disconnect(slot)
            getattr(new, name).connect(slot)
        self._player, xf.player = new, old
        self._audio_out, xf.out = xf.out, self._audio_out
        self._audio_device.swap_deck(new, self._audio_out)
        if self._big_player is not None:
            self._big_player.set_deck(new)
        if self._preview is not None:
            self._preview.set_player(new)

    def _xfade_follow(self, state):
        """⏯ on the deck holds the fading title too, and the ramps with it;
        ▶ picks both up where they stood. Whoever paused the deck — the card,
        Space, the phone, the taskbar, a 🛑 hold."""
        xf = self._between.xfade
        if xf.state != "fading" or xf.player is None:
            return
        if (state == QMediaPlayer.PlaybackState.PausedState
                and xf.paused_at is None):
            xf.paused_at = time.monotonic()
            xf.player.pause()
            if xf.timer is not None:
                xf.timer.stop()
            log.info("🔀 Crossfade held with the deck")
        elif (state == QMediaPlayer.PlaybackState.PlayingState
                and xf.paused_at is not None):
            xf.t0 += time.monotonic() - xf.paused_at
            xf.paused_at = None
            xf.player.play()
            if xf.timer is not None:
                xf.timer.start()
            log.info("🔀 Crossfade goes on")

    def _crossfade_takes(self, path):
        """A title is being loaded. The crossfade's own incoming title starts
        from where the in-ramp stands (silence, or later when its loudness
        held it back); any other load — ⏹, ⏭, a click — ends the crossfade."""
        xf = self._between.xfade
        if xf.state == "fading" and path is not None and path == xf.incoming:
            self._mix.fade_in = self._xfade_levels()[1]
            return
        self._end_crossfade()

    def _xfade_levels(self) -> tuple[float, float]:
        """(out, in) as the ramps stand right now."""
        xf = self._between.xfade
        return crossfade_levels((time.monotonic() - xf.t0) / xf.length,
                                xf.curve)

    def _step_crossfade(self):
        """One ramp step: the tail down, the new title up."""
        xf = self._between.xfade
        if xf.state != "fading":
            self._end_crossfade()
            return
        out, inc = self._xfade_levels()
        self._show_mark((time.monotonic() - xf.t0) / xf.length)
        self._mix.fade_in = inc
        self._apply_volume()
        if xf.out is not None:
            xf.out.setVolume(self._mix.tail(out))
        if out <= 0.0001:
            self._end_crossfade()
            # Ran its course: the marker walks on to the right edge.
            xf.after_until = xf.t0 + xf.length + lead_secs(xf.length)
            self._show_mark((time.monotonic() - xf.t0) / xf.length)
            # 🔈 The dance the crossfade brought in, named now that it plays
            # alone — its start call was held off the mix. Not a 🐂 Paso
            # Doble on its start wait: that wait has called it already (or
            # left it to the hall), and a mixed evening would say it again
            # in the other voice.
            if self._wants_start_call() and not self._pd_start_hold() > 0:
                self._speak_start_call()

    def _end_crossfade(self):
        """Stop the tail and put the deck's level back to whole. The tail's
        player stays, as the spare for the next crossfade."""
        xf = self._between.xfade
        was = xf.state is not None or self._mix.fade_in != 1.0
        xf.state = None
        xf.after_until = None
        xf.incoming = None
        xf.paused_at = None
        if xf.timer is not None:
            xf.timer.stop()
        if xf.player is not None:
            xf.player.stop()
            xf.player.setSource(QUrl())
        if self._mix.fade_in != 1.0:
            self._mix.fade_in = 1.0
            self._apply_volume()
        # Also before and after one: a stop ends the ticks that would.
        self._show_mark(None)
        if was:
            log.debug("🔀 Crossfade over")
