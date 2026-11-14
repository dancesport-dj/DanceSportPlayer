"""🎛 The cartwall's audio pool: the voices its pads sound on.

CartVoices owns its own QMediaPlayer instances, so a pad layers over the
running title instead of replacing it. The wall and its pads are in
player.widgets.cartwall.
"""

import logging
import os
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, QUrl, Signal

from planner.playing import cartwall as pc
from player.audio.mix import CART_DUCK
from shared.audio.playback import (
    crossfade_levels,
    prime_disconnect_notify,
    quiet_ffmpeg_log,
)

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

    from player.audio.pair_route import PairRoute
    HAS_MULTIMEDIA = True
else:
    try:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

        from player.audio.pair_route import PairRoute
        HAS_MULTIMEDIA = True
    except ImportError:                               # pragma: no cover
        QAudioOutput = QMediaPlayer = PairRoute = None
        HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.cartwall")


# How many pads can sound at once. Eight rather than a handful because a looping
# background bed occupies a voice for a whole Siegerehrung and the one-shots have
# to layer on top of it. Measured before it was built: ten concurrent WMF media
# sessions (these eight plus the deck and the filler) survive 200 retriggers and
# 80 source swaps on this machine without a single errorOccurred.
_VOICES = 8

_STEAL_FADE_MS = 120    # a voice being taken over for a different pad
_RAMP_MS = 25           # a level change coarser than this is an audible click
_TICK_MS = 100          # countdown refresh — a 3 s sting needs the digit to move
FIRE_GAP_MS = 120      # ignore a re-tap this soon: that is a double-click
# 🔈 A pad that pulls the OTHER PADS down (CartPad.duck_pads): they go down fast
# and come back over a second, like the main duck's defaults.
_MIN_CROSSOVER_MS = 100  # a loop crossover shorter than this is a plain restart
# 🔇 Dead air at the edges of a looping pad's file, like the main player's
# silence skip: a stretch this long counts, the music is taken to stop this
# long after the stretch begins and to start this long before it ends.
_SILENCE_MIN_S = 1.5
_SILENCE_EDGE_S = 0.5    # a leading stretch must start this close to 0
_SILENCE_END_SLACK_S = 1.5   # a trailing one must end this close to the end
_SILENCE_RELEASE_MS = 300
_SILENCE_LEAD_MS = 200
# 🔇 A pad that skips its lead-in (CartPad.skip_silence) starts this long
# before its music, so the attack is not clipped. Not _SILENCE_LEAD_MS: of
# a 300 ms gap that would skip a third.
_LEAD_PREROLL_MS = 25
_LEAD_EDGE_S = 0.05     # the lead-in must start this close to 0
# …and it ends this long after its music stops, so the decay is not cut.
_TAIL_RELEASE_MS = 25
_PAD_DUCK_DOWN_MS = 150
_PAD_DUCK_UP_MS = 1000

# 🎶 A background pad under a running title: down fast, by default as fast as a
# pad pulls the music (player.audio.mix._CART_DUCK), all the way down: under a
# title the bed is silent, not quieter. When the music stops it waits a moment
# for the title switch, then fades in, by default over seconds. All of it is
# set under ⚙ Settings ▸ 🎛 Cartwall (planner.playing.cartwall.background_*_ms).


# ─────────────────────────────────────────────────────────────────────────────
# The audio pool
# ─────────────────────────────────────────────────────────────────────────────
class _Voice:
    """One player of the pool, plus what it is currently doing."""

    def __init__(self, player, out, route: PairRoute):
        self.player = player
        self.out = out
        self.route = route       # 🔀 its way to the card, a channel pair or all of it
        # key and pad are set and cleared together: a voice with a pad is busy.
        self.key = None          # (page, row, col) while it is playing
        self.pad: pc.CartPad | None = None
        self.fade = 1.0
        self.fade_step = 0.0     # > 0 while fading out
        self.rise = 1.0          # a fired 🎶 pad coming up from silence
        self.rise_step = 0.0     # > 0 while it does
        # A loop crossover shapes both ramps like the main player's crossfade
        # (equal power) instead of two straight lines: the new round rises on
        # `rise`, the old one falls on `fade`.
        self.blend_in = False
        self.blend_out = False
        self.then: tuple[object, pc.CartPad] | None = None  # (key, pad) to start once the fade finishes
        self.then_manual = False  # was `then` tapped by hand (it ducks only then)
        self.manual = False      # tapped by hand: only such a pad ducks the music
        self.tail = False        # a loop's finished round, fading out under the next one
        self.tail_of = None      # …and the pad cell it belongs to: a stop takes it too
        self.dip = 1.0           # a loop fading itself down before it restarts
        self.dip_step = 0.0      # > 0 while it does; the pad stays the pad
        self.held = False        # a 🎶 pad paused under a title, to carry on later
        self.started = 0.0      # monotonic, for "steal the oldest"
        self.released = 0.0      # monotonic, for "least recently used"

    @property
    def busy(self) -> bool:
        return self.key is not None


class CartVoices(QObject):
    """The pads' own audio pipeline — independent of the deck and the filler.

    Voices are built once and never destroyed. A voice keeps its last file as
    its source even while idle, so tapping the same Tusch for the fortieth time
    is a setPosition(0) and not a media-session rebuild.
    """

    activeChanged = Signal(int)     # how many pads are audible
    duckChanged = Signal(bool)      # is any *ducking* pad live right now
    padStopped = Signal(object)     # the (page, row, col) that stopped
    # …because it ran out on its own: not stopped, faded, stolen or broken.
    # The ▶ queue's cue for the next pad.
    padEnded = Signal(object)
    # A pad is over, for whatever reason: the pad and the seconds it was heard.
    # Feeds the play log.
    padPlayed = Signal(object, float)
    padFading = Signal(object, bool)  # key, is it on its way out right now
    padHeld = Signal(object, bool)    # key, is it a 🎶 pad paused under a title
    padTick = Signal(list)          # [(key, ms_left, frac), …]
    wantsDevice = Signal()          # a pad is about to fire — 🔇 device back
    wantsSilences = Signal(str)     # a looping pad's file, whose dead air nobody probed
    wantsEdges = Signal(str)        # a 🔇 pad's file, whose lead-in and tail nobody probed

    def __init__(self, parent=None, voices=_VOICES, factory=None):
        super().__init__(parent)
        self._make = factory or self._build_player
        self._pool: list[_Voice] = []
        for _ in range(voices):
            player, out = self._make()
            voice = _Voice(player, out, PairRoute(player, out, self))
            out.setVolume(0.0)
            player.mediaStatusChanged.connect(
                lambda status, v=voice: self._on_status(v, status))
            player.errorOccurred.connect(
                lambda err, msg, v=voice: self._on_error(v, err, msg))
            self._pool.append(voice)
        self._level = 1.0        # master × desk, pushed in by _apply_volume
        self._bed_duck = 1.0     # 🔈 the music's duck, heard by 🎶 pads only
        self._muted = False
        self._loop_mode = pc.LOOP_MODES[0]   # 🔁 how a looping pad meets its file end
        # 🔈 How far a duck_pads pad pulls the other pads: the level they are
        # at while it plays, the factor now, and where it is headed.
        self._pad_duck_level = CART_DUCK
        self._pad_duck = 1.0
        self._pad_duck_target = 1.0
        self._pad_duck_step = 0.0
        self._pad_duck_ramp = QTimer(self)
        self._pad_duck_ramp.setInterval(_RAMP_MS)
        self._pad_duck_ramp.timeout.connect(self._step_pad_duck)
        self._wall_fade = pc.DEFAULT_FADE_MS   # what a pad follows by default
        self._wall_cross = pc.DEFAULT_CROSS_MS   # …and for a loop crossover
        self._silences: dict[str, list[tuple[float, float]]] = {}   # file → dead air, s
        self._silences_asked: set[str] = set()
        self._leads: dict[str, int] = {}   # file → where its music starts, ms
        self._ends: dict[str, int] = {}    # file → where its music stops, ms
        self._edges_asked: set[str] = set()
        self._bg_pauses = False  # a starting title pauses 🎶 pads instead of muting them
        self._bg_up_ms = pc.DEFAULT_BG_FADE_IN_MS  # 🎶 pads coming back once the music stops
        self._bg_down_ms = pc.DEFAULT_BG_FADE_OUT_MS  # …and dipping when a title starts
        self._bg_fire_ms = pc.DEFAULT_BG_FIRE_FADE_MS  # …and coming up when fired
        self._last_fire: dict[object, float] = {}
        self._active = 0
        self._ducking = False
        self._ramp = QTimer(self)
        self._ramp.setInterval(_RAMP_MS)
        self._ramp.timeout.connect(self._step_fades)
        self._tick = QTimer(self)
        self._tick.setInterval(_TICK_MS)
        self._tick.timeout.connect(self._emit_tick)
        # Followed even with no background pad running, so one fired under a
        # title starts low instead of blaring for the length of the dip. 1.0 is up,
        # 0.0 is all the way down.
        self._bg = 1.0
        self._bg_target = 1.0
        self._music_paused = False   # the music is down because it is paused
        self._bg_ramp = QTimer(self)
        self._bg_ramp.setInterval(_RAMP_MS)
        self._bg_ramp.timeout.connect(self._step_background)
        self._bg_hold = QTimer(self)
        self._bg_hold.setSingleShot(True)
        self._bg_hold.setInterval(pc.DEFAULT_BG_HOLD_MS)
        self._bg_hold.timeout.connect(self._lift_background)

    @staticmethod
    def _build_player():
        quiet_ffmpeg_log()
        player = QMediaPlayer()
        out = QAudioOutput()
        player.setAudioOutput(out)
        prime_disconnect_notify(player, out)
        return player, out

    # ── firing and stopping ──────────────────────────────────────────────────
    def seek(self, key, frac: float) -> None:
        """Jump a running pad to `frac` (0…1) of its file — the spot a drag
        across the pad let go of. A pad that is not sounding is left alone."""
        voice = self._voice_for(key)
        if voice is None or not voice.busy:
            return
        total = voice.player.duration()
        if total > 0:
            voice.player.setPosition(int(total * max(0.0, min(1.0, frac))))

    def is_playing(self, key) -> bool:
        """True only while the pad is really running — a pad that is fading out
        counts as free, so tapping it again re-fires instead of doing nothing."""
        voice = self._voice_for(key)
        return voice is not None and voice.fade_step <= 0

    def fire(self, key, pad: pc.CartPad, *, tapped: bool = True) -> bool | None:
        """Start `pad` on a voice. True: it plays (or will, once a stolen
        voice has faded); False: no voice was free; None: the second half of
        a double-click, ignored — the first half's outcome stands.
        `tapped=False` is a start nobody clicked (the ▶ queue moving on),
        which no double-click guard may swallow."""
        # The desk first: it holds the released flag for ALL players, and a wall
        # that quietly re-attached only its own voices would leave that flag set
        # — the deck's output would then never be handed back again.
        self.wantsDevice.emit()
        self.restore_outputs()
        now = time.monotonic()
        if tapped and now - self._last_fire.get(key, 0.0) < FIRE_GAP_MS / 1000.0:
            return None         # a double-click is one tap
        self._last_fire[key] = now
        if pad.stops_others:
            self._stop_others(key)
        if pad.background and tapped and self._music_paused:
            # The music is only paused, not playing: a bed the operator taps
            # by hand is wanted now, and the pause must not keep it silent.
            self._bg_hold.stop()
            self._lift_background()

        reviving = self._voice_for(key)
        if reviving is not None:
            # It was fading out and the operator changed their mind.
            reviving.fade = 1.0
            reviving.fade_step = 0.0
            reviving.then = None
            reviving.pad = pad
            reviving.manual = tapped
            reviving.started = now
            reviving.player.setPosition(self._first_ms(pad))
            reviving.player.play()
            self._set_held(reviving, False)
            self._arm_rise(reviving, pad)
            if pad.background and self._bg <= 0.0 and self._bg_target <= 0.0:
                self._hold_background()
            self._apply(reviving)
            self.padFading.emit(key, False)   # stop the blink: it is back
            self._sync()
            return True

        url = QUrl.fromLocalFile(str(pad.path))
        voice = self._pick(url)
        if voice is None:
            log.warning("🎛 No free cartwall voice\n"
                        "pad: %s\n"
                        "reason: every voice holds a looping pad", pad.path)
            return False
        if voice.busy:
            # Taken over: let the old one down gently, start the new one on it
            # when the ramp gets there.
            voice.then = (key, pad)
            voice.then_manual = tapped
            self._start_fade(voice, _STEAL_FADE_MS)
            return True
        self._start(voice, key, pad, url, manual=tapped)
        return True

    def set_silences(self, path, spans) -> None:
        """🔇 The silent stretches [[start, end], …] (seconds) of a pad's file,
        from the probe the main player uses. A looping pad's crossover goes
        from its last audible point into the first one of the next round."""
        self._silences[str(path)] = [(float(s), float(e)) for s, e in spans]

    def _audible(self, pad: pc.CartPad, total_ms: int) -> tuple[int, int]:
        """Where the music of a pad's file starts and stops, in ms: the whole file
        unless a silent stretch of at least 1.5 s sits at its start or runs to
        its end. Silence in the middle is a break the dancers know."""
        lead, end = 0, total_ms
        for start, stop in self._silences.get(str(pad.path), ()):
            if stop - start < _SILENCE_MIN_S:
                continue
            if stop >= total_ms / 1000.0 - _SILENCE_END_SLACK_S:
                end = min(end, int(start * 1000) + _SILENCE_RELEASE_MS)
            elif start <= _SILENCE_EDGE_S:
                lead = max(lead, int(stop * 1000) - _SILENCE_LEAD_MS)
        return (lead, end) if end > lead else (0, total_ms)

    def ask_edges(self, path) -> None:
        """🔇 A pad that skips its silence wants to know where the music of
        `path` starts and stops. Asked once per file: the window probes it
        (wantsEdges) and answers with set_edges."""
        path = str(path)
        if path in self._leads or path in self._edges_asked:
            return
        self._edges_asked.add(path)
        self.wantsEdges.emit(path)

    def set_edges(self, path, spans) -> None:
        """The silent stretches at the top and the end of a pad's file,
        [[start, end], …] in seconds (shared.audio.audio_probes.
        detect_edge_silence), or []. A stretch from the very top is the
        lead-in, any other the tail. Kept apart from set_silences: a loop's
        crossover counts only long dead air."""
        lead = 0
        end = None
        for start, stop in spans:
            if float(start) <= _LEAD_EDGE_S:
                lead = max(lead, int(float(stop) * 1000) - _LEAD_PREROLL_MS)
            else:
                end = int(float(start) * 1000) + _TAIL_RELEASE_MS
        self._leads[str(path)] = lead
        if end is not None and end > lead:
            self._ends[str(path)] = end
        else:
            self._ends.pop(str(path), None)

    def _first_ms(self, pad: pc.CartPad) -> int:
        """Where a pad's first round starts: past its lead-in when it asks."""
        if not pad.skip_silence:
            return 0
        return self._leads.get(str(pad.path), 0)

    def _last_ms(self, pad: pc.CartPad, total_ms: int) -> int:
        """Where a pad's music stops, in every loop mode and for a one-shot:
        at its last audible point (`_audible`), or before a skipped tail if
        that is earlier."""
        end = self._audible(pad, total_ms)[1]
        tail = self._ends.get(str(pad.path)) if pad.skip_silence else None
        return min(end, tail) if tail is not None else end

    def _past_tail(self, voice: _Voice) -> bool:
        """🔇 Has a pad that skips its tail reached it? The file plays on in
        silence, so the pad ends (or goes round) here instead of at EndOfMedia."""
        pad = voice.pad
        if (pad is None or not pad.skip_silence or voice.tail or voice.held
                or voice.dip_step > 0):
            return False
        tail = self._ends.get(str(pad.path))
        return tail is not None and voice.player.position() >= tail

    def _round_ms(self, pad: pc.CartPad, total_ms: int) -> int:
        """Where a loop's next round starts, in every loop mode: at the first
        audible point (`_audible`), or past a skipped lead-in if that is later."""
        return max(self._audible(pad, total_ms)[0], self._first_ms(pad))

    def set_wall_cross(self, ms: int) -> None:
        """The crossover length a looping pad follows unless it has its own."""
        self._wall_cross = max(0, min(pc.MAX_CROSS_MS, int(ms)))

    def set_wall_fade(self, ms: int) -> None:
        """The wall-wide fade-out. Pads with a fade of their own ignore it."""
        self._wall_fade = max(0, min(pc.MAX_FADE_MS, int(ms)))

    def stop(self, key) -> None:
        voice = self._voice_for(key)
        if voice is not None and voice.pad is not None and voice.fade_step <= 0:
            self._start_fade(voice, pc.fade_for(voice.pad, self._wall_fade))
        for tail in self._tails(lambda of: of == key):
            self._cut_tail(tail, self._tail_fade(tail))

    def stop_all(self) -> int:
        """Fade every pad out. Returns the longest fade started, in ms."""
        longest = 0
        for voice in self._pool:
            # A voice already on its steal ramp keeps fading, but the pad that
            # was waiting for it must not start any more.
            voice.then = None
            if voice.pad is not None and voice.fade_step <= 0:
                span = pc.fade_for(voice.pad, self._wall_fade)
                longest = max(longest, span)
                self._start_fade(voice, span)
        for tail in self._tails(lambda _of: True):
            self._cut_tail(tail, self._tail_fade(tail))
        return longest

    def cut_all(self) -> None:
        """⏹ Every pad silent now: the status bar's red stop. No fade, not even
        a pad's own, and nothing passed by — a voice already fading, a loop's
        tail, a bed held under the title. A pad waiting for a voice is dropped
        first, or it would start on the voice this frees."""
        for voice in self._pool:
            voice.then = None
            voice.then_manual = False
        for voice in self._pool:
            if voice.pad is not None:
                self._finish_fade(voice, "stop all sound")

    def _stop_others(self, key) -> None:
        """A ■ pad takes the floor: every other pad fades out, and one still
        waiting for a voice is not started any more."""
        for voice in self._pool:
            if voice.then is not None and voice.then[0] != key:
                voice.then = None
            if voice.key != key and voice.pad is not None and voice.fade_step <= 0:
                self._start_fade(voice, pc.fade_for(voice.pad, self._wall_fade))
        for tail in self._tails(lambda of: of != key):
            self._cut_tail(tail, self._tail_fade(tail))

    def _tail_fade(self, tail: _Voice) -> int:
        """The fade a stop gives a 🔁 tail: its pad's own, else the wall's."""
        return pc.fade_for(tail.pad, self._wall_fade) if tail.pad is not None else 0

    def _tails(self, belongs) -> list[_Voice]:
        """🔁 The loop rounds still fading out under their next one whose pad
        cell `belongs(cell)` accepts. They have no key, so the stops above
        would pass them by and leave up to a crossover's length sounding."""
        return [v for v in self._pool
                if v.tail and v.pad is not None and belongs(v.tail_of)]

    def _cut_tail(self, voice: _Voice, span_ms: int) -> None:
        """A stop reaches a tail: a hard cut ends it now, a fade makes it go
        no later than the fade does. Never later than its own crossover."""
        if span_ms <= 0:
            self._finish_fade(voice, "stopped during the loop crossover")
            return
        voice.fade_step = max(voice.fade_step, voice.fade * _RAMP_MS / float(span_ms))
    def playing_keys(self) -> list[object]:
        return [v.key for v in self._pool if v.busy]

    def rekey(self, moved: dict) -> None:
        """The wall was turned or reshaped: {old cell: new cell}. A sounding
        pad keeps its voice, it only answers to the cell it now sits in — or a
        tap there would start a second copy instead of stopping it."""
        for voice in self._pool:
            if voice.key is not None:
                voice.key = moved.get(voice.key, voice.key)
            if voice.tail_of is not None:
                voice.tail_of = moved.get(voice.tail_of, voice.tail_of)
            if voice.then is not None:
                key, pad = voice.then
                voice.then = (moved.get(key, key), pad)
        self._last_fire = {moved.get(k, k): t for k, t in self._last_fire.items()}

    # ── levels ───────────────────────────────────────────────────────────────
    def set_level(self, level: float) -> None:
        """The desk's master × duck-button product, pushed in from _apply_volume."""
        self._level = max(0.0, min(1.0, level))
        for voice in self._pool:
            if voice.busy:
                self._apply(voice)

    def set_bed_duck(self, duck: float) -> None:
        """🔈 The duck the music takes under a spoken call (or a ducking pad),
        pushed in from _apply_volume. The 🎶 background pads are the pause
        music now, so they take it too; a one-shot pad does not."""
        self._bed_duck = max(0.0, min(1.0, duck))
        for voice in self._pool:
            if voice.busy and voice.pad is not None and voice.pad.background:
                self._apply(voice)

    def set_pad_duck_level(self, level: float) -> None:
        """🔈 The level the other pads are pulled to under a `duck_pads` pad;
        a duck that is on moves to it."""
        self._pad_duck_level = max(0.0, min(1.0, level))
        self._sync()

    def _aim_pad_duck(self, target: float) -> None:
        # The pace is set once per new target, from the way still to go: every
        # move takes its direction's span. Taken from the depth setting, a
        # depth turned to 100 % mid-duck gave a step of 0 and the duck stuck.
        if target != self._pad_duck_target:
            span = _PAD_DUCK_DOWN_MS if target < self._pad_duck else _PAD_DUCK_UP_MS
            self._pad_duck_step = _RAMP_MS * abs(target - self._pad_duck) / span
        self._pad_duck_target = target
        if self._pad_duck != target and not self._pad_duck_ramp.isActive():
            self._pad_duck_ramp.start()

    def _step_pad_duck(self) -> None:
        down = self._pad_duck_target < self._pad_duck
        step = self._pad_duck_step
        if abs(self._pad_duck_target - self._pad_duck) <= step:
            self._pad_duck = self._pad_duck_target
            self._pad_duck_ramp.stop()
        else:
            self._pad_duck += -step if down else step
        for voice in self._pool:
            if voice.busy:
                self._apply(voice)

    def set_muted(self, muted: bool) -> None:
        """🔇 silences the wall without losing where anything is — the point of
        having it next to ⏹, which cannot bring a bed back mid-track."""
        self._muted = bool(muted)
        for voice in self._pool:
            if voice.busy:
                self._apply(voice)
        self._sync()   # a muted wall is not heard, so it cannot duck the music

    def muted(self) -> bool:
        return self._muted

    def set_loop_mode(self, mode: str) -> None:
        """🔁 How a looping pad meets the end of its file: "crossover" blends
        into its next round, "fade" dips to silence and restarts, "hard" wraps
        at once. Anything else is the default."""
        self._loop_mode = mode if mode in pc.LOOP_MODES else pc.LOOP_MODES[0]

    def set_background_pauses(self, pauses: bool) -> None:
        """🎶 Whether a starting title pauses the background pads (True) or
        only dips them to silence, still running, until the music stops (False)."""
        self._bg_pauses = bool(pauses)

    def set_background_fade_in(self, ms: int) -> None:
        """🎶 How long the background pads take to come back up once the music
        stops; 0 = at once. A swell already under way carries on at the new pace."""
        self._bg_up_ms = max(0, min(pc.MAX_FADE_MS, int(ms)))

    def set_background_fade_out(self, ms: int) -> None:
        """🎶 How long the background pads take to dip to silence when a title
        starts; 0 = at once."""
        self._bg_down_ms = max(0, min(pc.MAX_FADE_MS, int(ms)))

    def set_background_fire_fade(self, ms: int) -> None:
        """🎶 How long a background pad takes to come up from silence when it
        is fired; 0 = full volume at once. Only the next fire follows it."""
        self._bg_fire_ms = max(0, min(pc.MAX_FADE_MS, int(ms)))

    def set_background_hold(self, ms: int) -> None:
        """🎶 How long the music has to stay stopped before the background
        pads come back; 0 = straight away."""
        self._bg_hold.setInterval(max(0, min(pc.MAX_FADE_MS, int(ms))))

    def set_music_playing(self, playing: bool, paused: bool = False) -> None:
        """The deck started or stopped: 🎶 background pads dip or come back.
        Set to pause, they hold once they are down (see _hold_background).
        `paused`: the deck is only paused, its title waits. The beds stay down
        as for playing music, but a bed tapped by hand still sounds."""
        self._music_paused = playing and paused
        if playing:
            self._bg_hold.stop()
            self._aim_background(0.0)
        elif self._bg_target < 1.0 and not self._bg_hold.isActive():
            self._bg_hold.start()

    def background_down_in_ms(self) -> int:
        """How long the 🎶 background pads heard now still need to dip to
        silence at the fade-out pace; 0 when none is (no bed, already down,
        held, or the wall muted). A starting title waits that long unless
        the operator lets it overlap (see pc.background_overlaps)."""
        if self._muted or self._level <= 0.0 or self._bg <= 0.0:
            return 0
        if not any(v.busy and v.pad is not None and v.pad.background
                   and v.fade_step <= 0 and not v.held for v in self._pool):
            return 0
        return round(self._bg * self._bg_down_ms)

    def _lift_background(self) -> None:
        # Whatever the setting says now: a bed held under the title never
        # comes back otherwise.
        for voice in self._pool:
            if voice.held:
                self._set_held(voice, False)
                voice.player.play()
        self._aim_background(1.0)

    def _hold_background(self) -> None:
        """Set to pause: the background pads are silent now, so stop them where
        they are — on the dip, never before it, or the bed cuts off audibly."""
        if not self._bg_pauses:
            return
        for voice in self._pool:
            if (voice.busy and voice.pad is not None and voice.pad.background
                    and voice.fade_step <= 0 and not voice.held):
                self._set_held(voice, True)
                voice.player.pause()

    def _aim_background(self, target: float) -> None:
        self._bg_target = target
        if self._bg != target and not self._bg_ramp.isActive():
            self._bg_ramp.start()

    def _step_background(self) -> None:
        span = self._bg_down_ms if self._bg_target < self._bg else self._bg_up_ms
        step = _RAMP_MS / span if span > 0 else 1.0
        if abs(self._bg_target - self._bg) <= step:
            self._bg = self._bg_target
            self._bg_ramp.stop()
        else:
            self._bg += step if self._bg_target > self._bg else -step
        for voice in self._pool:
            if voice.busy and voice.pad is not None and voice.pad.background:
                self._apply(voice)
        if self._bg <= 0.0:
            self._hold_background()

    def preview_volume(self, key, volume: float) -> None:
        """The pad dialog's slider, heard while it is dragged. The stored pad is
        untouched — Cancel has to leave the wall exactly as it was."""
        voice = self._voice_for(key)
        if voice is not None and voice.pad is not None:
            voice.pad = replace(voice.pad, volume=max(0.0, min(1.0, volume)))
            self._apply(voice)

    def refresh_pad(self, key, pad: pc.CartPad) -> None:
        """Settings changed while the pad runs — a volume drag has to be audible
        at once, not on the next tap."""
        voice = self._voice_for(key)
        if voice is not None:
            # The dialog's pad carries the stored path; the voice keeps the
            # resolved one it was fired with, which the edge tables are keyed by (D.B).
            voice.pad = (replace(pad, path=voice.pad.path)
                         if voice.pad is not None else pad)
            self._apply(voice)
            self._sync()

    def set_device(self, device, pair: int = 0) -> None:
        for voice in self._pool:
            voice.route.set_device(device, pair)

    def release_outputs(self) -> None:
        """🔇 Idle audio release: let go of the sound device (see
        player.audio.audio_device.AudioDevice.release). A voice pool is built at start-up and
        then holds the card for the whole evening, so the wall has to let go too
        or the hiss stays. Only ever called with every voice silent."""
        for voice in self._pool:
            voice.route.release()

    def restore_outputs(self) -> None:
        """Take the device back before a pad is heard. Called from `fire` — the
        one door every tap goes through."""
        for voice in self._pool:
            voice.route.restore()

    def shutdown(self) -> None:
        """The one place sources ARE cleared: WMF keeps the file open, and a
        looping bed can hold one for an hour."""
        self._ramp.stop()
        self._tick.stop()
        self._bg_ramp.stop()
        self._bg_hold.stop()
        self._pad_duck_ramp.stop()
        for voice in self._pool:
            voice.key = None
            voice.pad = None
            voice.then = None
            voice.player.stop()
            voice.player.setSource(QUrl())

    # ── internals ────────────────────────────────────────────────────────────
    def _voice_for(self, key) -> _Voice | None:
        for voice in self._pool:
            if voice.key == key:
                return voice
        return None

    def _idle_for(self, url) -> _Voice | None:
        """A free voice, cheapest first: one that already holds `url`, an unused
        one, the least recently used one. None when every voice is taken."""
        idle = [v for v in self._pool if not v.busy and v.fade_step <= 0]
        for voice in idle:
            if voice.player.source() == url:
                return voice
        for voice in idle:
            if voice.player.source().isEmpty():
                return voice
        return min(idle, key=lambda v: v.released) if idle else None

    def _pick(self, url) -> _Voice | None:
        """A voice for this file, cheapest first: one that already holds it, an
        unused one, the least recently used one — and only then take one over."""
        idle = self._idle_for(url)
        if idle is not None:
            return idle
        # Everything is busy. Never take a looping bed out from under the
        # operator — that is the one sound they expect to keep running.
        busy = [v for v in self._pool
                if v.pad is not None and v.fade_step <= 0 and not v.pad.loop]
        if busy:
            return min(busy, key=lambda v: v.started)
        # …or on its way out: after ⏹ all every voice fades for up to the wall
        # fade, and a tap in those seconds must still sound. The quietest one,
        # but never one already promised to another pad.
        fading = [v for v in self._pool
                  if v.busy and v.fade_step > 0 and v.then is None]
        return min(fading, key=lambda v: v.fade) if fading else None

    def _start(self, voice: _Voice, key, pad: pc.CartPad, url, *,
               manual: bool = True) -> None:
        if voice.player.source() != url:
            voice.player.setSource(url)
        voice.key = key
        voice.pad = pad
        voice.manual = manual
        voice.fade = 1.0
        voice.fade_step = 0.0
        voice.started = time.monotonic()
        path = str(pad.path)
        if pad.loop and path not in self._silences_asked:
            self._silences_asked.add(path)
            if path not in self._silences:
                self.wantsSilences.emit(path)
        if pad.skip_silence:
            self.ask_edges(path)   # normally asked when the wall loaded
        log.info("🎛 Pad started\n"
                 "file: %s\n"
                 "pad: %s\n"
                 "loop: %s\n"
                 "background: %s\n"
                 "duck: %s",
                 os.path.basename(str(pad.path)), key, pad.loop, pad.background,
                 pad.duck)
        self._arm_rise(voice, pad)
        self._apply(voice)
        voice.player.setPosition(self._first_ms(pad))
        voice.player.play()
        if pad.background and self._bg <= 0.0 and self._bg_target <= 0.0:
            self._hold_background()   # fired under a title: it waits for the break
        if not self._tick.isActive():
            self._tick.start()
        self._sync()

    def _arm_rise(self, voice: _Voice, pad: pc.CartPad) -> None:
        """A 🎶 pad fired with a fade-in set starts silent and comes up on the
        fade ramp; every other pad starts at its level."""
        if pad.background and self._bg_fire_ms > 0:
            voice.rise = 0.0
            voice.rise_step = _RAMP_MS / float(self._bg_fire_ms)
            if not self._ramp.isActive():
                self._ramp.start()
        else:
            voice.rise = 1.0
            voice.rise_step = 0.0

    def _start_fade(self, voice: _Voice, span_ms: int) -> None:
        if span_ms <= 0:
            # A hard cut, because this pad asked for one. It clicks — that is the
            # user's call to make per pad, which is why it is not the default.
            self._finish_fade(voice)
            return
        voice.rise_step = 0.0   # a bed still coming up goes down from where it got
        if voice.blend_in:       # as heard, not as the ramp counts
            voice.rise = crossfade_levels(voice.rise)[1]
            voice.blend_in = False
        voice.fade *= voice.dip   # …and so does a loop already dipping
        voice.dip = 1.0
        voice.dip_step = 0.0
        voice.fade_step = max(0.001, _RAMP_MS / float(span_ms))
        if voice.key is not None:
            self.padFading.emit(voice.key, True)
        if not self._ramp.isActive():
            self._ramp.start()

    def _step_fades(self) -> None:
        fading = False
        for voice in self._pool:
            # A held bed's dip waits, and so may the timer: _set_held starts
            # it again when the hold lifts.
            if voice.dip_step > 0 and not voice.held:
                fading = True
                voice.dip -= voice.dip_step
                if voice.dip <= 0:
                    self._restart_loop(voice)
                else:
                    self._apply(voice)
            if voice.rise_step > 0:
                voice.rise = min(1.0, voice.rise + voice.rise_step)
                if voice.rise >= 1.0:
                    voice.rise_step = 0.0
                    voice.blend_in = False
                else:
                    fading = True
                if voice.fade_step <= 0:
                    self._apply(voice)
            if voice.fade_step <= 0:
                continue
            voice.fade -= voice.fade_step
            if voice.fade <= 0:
                voice.fade = 0.0
                voice.fade_step = 0.0
                self._finish_fade(voice)
            else:
                self._apply(voice)
                fading = True
        if not fading:
            self._ramp.stop()

    def _restart_loop(self, voice: _Voice) -> None:
        """A loop's next round: from where its music starts, at its own
        level. The pad keeps its key, so the wall hears nothing of it."""
        voice.dip = 1.0
        voice.dip_step = 0.0
        voice.player.setPosition(
            self._round_ms(voice.pad, voice.player.duration()) if voice.pad else 0)
        voice.player.play()
        self._apply(voice)

    def _finish_fade(self, voice: _Voice, reason: str = "faded out") -> None:
        follow = voice.then
        follow_manual = voice.then_manual
        voice.then = None
        voice.then_manual = False
        self._release(voice, reason)
        if follow is not None:
            key, pad = follow
            self._start(voice, key, pad, QUrl.fromLocalFile(str(pad.path)),
                        manual=follow_manual)

    def _release(self, voice: _Voice, reason: str = "faded out") -> None:
        """Silence and rewind, but KEEP the source. The deck clears its source
        because a different title follows and WMF holds the handle; a cart voice
        is pinned to its sample on purpose, so the next tap costs nothing.
        `reason` is only for the log: why this pad ended."""
        key = voice.key
        pad = voice.pad
        if key is not None and pad is not None:
            # A loop restarts its position, so it is timed on the clock instead.
            heard = (time.monotonic() - voice.started if pad.loop
                     else voice.player.position() / 1000.0)
            log.info("🎛 Pad ended\n"
                     "file: %s\n"
                     "pad: %s\n"
                     "reason: %s\n"
                     "position: %d / %d ms",
                     os.path.basename(str(pad.path)), key, reason,
                     voice.player.position(), voice.player.duration())
        voice.player.pause()
        voice.player.setPosition(0)
        voice.out.setVolume(0.0)
        self._set_held(voice, False)
        voice.key = None
        voice.pad = None
        voice.manual = False
        voice.tail = False
        voice.tail_of = None
        voice.dip = 1.0
        voice.dip_step = 0.0
        voice.fade = 1.0
        voice.fade_step = 0.0
        voice.rise = 1.0
        voice.rise_step = 0.0
        voice.blend_in = voice.blend_out = False
        voice.released = time.monotonic()
        if key is not None:
            self.padStopped.emit(key)
            if pad is not None:
                self.padPlayed.emit(pad, heard)
        self._sync()

    def _set_held(self, voice: _Voice, held: bool) -> None:
        if voice.held != held:
            voice.held = held
            if not held and voice.dip_step > 0 and not self._ramp.isActive():
                self._ramp.start()
            if voice.key is not None:
                self.padHeld.emit(voice.key, held)

    def _apply(self, voice: _Voice) -> None:
        if voice.pad is None:
            return
        fade = (crossfade_levels(1.0 - voice.fade)[0] if voice.blend_out
                else voice.fade)
        rise = crossfade_levels(voice.rise)[1] if voice.blend_in else voice.rise
        vol = self._level * voice.pad.volume * fade * rise * voice.dip
        if voice.pad.background:
            vol *= self._bg * self._bed_duck
        if not self._pulls_pads(voice):
            vol *= self._pad_duck
        if self._muted:
            vol = 0.0
        voice.out.setVolume(max(0.0, min(1.0, vol)))

    def _on_error(self, voice: _Voice, err, msg: str) -> None:
        log.warning("🎛 Cartwall voice error\n"
                    "error: %s\n"
                    "detail: %s", err, msg)
        if voice.busy:
            self._finish_fade(voice, "error")   # it will not play: free the voice (and duck)

    def _on_status(self, voice: _Voice, status) -> None:
        if voice.pad is None:
            return
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            # A file that cannot be decoded never reaches EndOfMedia, so it
            # would hold its voice and the duck for good. Not even a loop
            # pad retries it.
            self._finish_fade(voice, "error: invalid media")
            return
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        self._at_end(voice, "end of file")

    def _at_end(self, voice: _Voice, reason: str) -> None:
        """A pad's round is over: at the end of its file, or 🔇 where its
        music stops (`_past_tail`)."""
        if voice.tail:
            self._finish_fade(voice, "loop crossover")   # its round is over
            return
        if voice.pad is not None and voice.pad.loop:
            # Endless repeat by starting the file over. NOT
            # setLoops(Infinite) — this codebase moved off that API on this
            # backend.
            self._restart_loop(voice)
            return
        # It ended where it was meant to: no fade — but a pad that stole this
        # voice mid-ramp is still waiting for it.
        key = voice.key
        natural = voice.fade_step <= 0 and voice.then is None
        self._finish_fade(voice, reason)
        if natural:
            self.padEnded.emit(key)   # after the release: the voice is free again

    def _maybe_crossover(self, voice: _Voice) -> None:
        """🔁 A looping pad near the end of its file hands the next round to a
        second voice, which comes up from the top while this one fades out —
        over the pad's own crossover length or the setting's, never more than
        a third of the music (dead air at the file's edges is not counted, see
        `_audible`). A length of 0, a too-short file or no free voice keep
        the plain restart at the end (see _on_status)."""
        pad = voice.pad
        if self._loop_mode == "hard":
            return
        if (not voice.busy or pad is None or not pad.loop or voice.held
                or voice.fade_step > 0 or voice.dip_step > 0
                or voice.then is not None):
            return
        total = voice.player.duration()
        lead, end = self._audible(pad, total)[0], self._last_ms(pad, total)
        span = min(pc.cross_for(pad, self._wall_cross), (end - lead) // 3)
        left = end - voice.player.position()
        if total <= 0 or span < _MIN_CROSSOVER_MS or left > span + _TICK_MS:
            return
        # A tick that came late leaves less than the span: blend in what is
        # left, or the new round is not at full when the old one runs out.
        over = max(_RAMP_MS, min(span, left))
        if self._loop_mode == "fade":
            log.info("🔁 Loop fade out and restart\n"
                     "file: %s\n"
                     "pad: %s\n"
                     "over: %d ms",
                     os.path.basename(str(pad.path)), voice.key, over)
            voice.dip_step = _RAMP_MS / float(over)
            if not self._ramp.isActive():
                self._ramp.start()
            return
        url = voice.player.source()
        nxt = self._idle_for(url)
        if nxt is None:
            return
        log.info("🔁 Loop crossover\n"
                 "file: %s\n"
                 "pad: %s\n"
                 "over: %d ms",
                 os.path.basename(str(pad.path)), voice.key, over)
        nxt.key, nxt.pad, nxt.manual = voice.key, pad, voice.manual
        nxt.started = voice.started
        nxt.fade = 1.0
        nxt.fade_step = 0.0
        nxt.rise = 0.0
        nxt.rise_step = _RAMP_MS / float(over)
        nxt.blend_in = True
        if nxt.player.source() != url:
            nxt.player.setSource(url)
        self._apply(nxt)
        nxt.player.setPosition(self._round_ms(pad, total))
        nxt.player.play()
        # The old round is no longer the pad: it keeps sounding, but without
        # the key (the wall hears nothing of it) and without the tap (it does
        # not duck), and lets go on its own.
        voice.tail_of = voice.key
        voice.key = None
        voice.manual = False
        voice.tail = True
        self._start_fade(voice, over)
        voice.blend_out = True
        if not self._ramp.isActive():
            self._ramp.start()
        self._sync()

    def _emit_tick(self) -> None:
        for voice in self._pool:
            if voice.busy and self._past_tail(voice):
                self._at_end(voice, "end of its music")
        for voice in self._pool:
            self._maybe_crossover(voice)
        rows = []
        for voice in self._pool:
            if not voice.busy:
                continue
            total = voice.player.duration()
            if total > 0 and voice.pad is not None and voice.pad.skip_silence:
                total = self._last_ms(voice.pad, total)   # 🔇 down to where the music stops
            pos = voice.player.position()
            left = max(0, total - pos) if total > 0 else -1
            frac = min(1.0, pos / total) if total > 0 else 0.0
            rows.append((voice.key, left, frac))
        if rows:
            self.padTick.emit(rows)
        else:
            self._tick.stop()

    @staticmethod
    def _pulls_pads(voice: _Voice) -> bool:
        """Is this voice a pad the operator tapped that pulls the other pads
        down? It is not pulled down itself."""
        return (voice.pad is not None and voice.pad.duck_pads
                and not voice.pad.background and voice.manual)

    def _sync(self) -> None:
        active = sum(1 for v in self._pool if v.busy)
        # 🔈 Only a pad the operator tapped ducks: the queue moving on or a pad
        # filling a pause starts under the music without pulling it down. A muted
        # wall makes no sound to duck for.
        ducking = not self._muted and any(
            v.pad is not None and v.pad.duck and not v.pad.background and v.manual
            for v in self._pool)
        # …and the same for a pad that pulls the OTHER PADS down.
        pulling = not self._muted and any(self._pulls_pads(v) for v in self._pool)
        self._aim_pad_duck(self._pad_duck_level if pulling else 1.0)
        if active != self._active:
            self._active = active
            self.activeChanged.emit(active)
        if ducking != self._ducking:
            self._ducking = ducking
            self.duckChanged.emit(ducking)
