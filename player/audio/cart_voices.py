"""🎛 The cartwall's audio pool: the voices its pads sound on.

CartVoices owns its own QMediaPlayer instances, so a pad layers over the
running title instead of replacing it. The wall and its pads are in
player.widgets.cartwall.
"""

import logging
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QObject, QTimer, QUrl, Signal)

from planner.playing import cartwall as pc
from shared.audio.playback import prime_disconnect_notify, quiet_ffmpeg_log

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_MULTIMEDIA = True
else:
    try:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        HAS_MULTIMEDIA = True
    except ImportError:                               # pragma: no cover
        QAudioOutput = QMediaPlayer = None
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
_FIRE_GAP_MS = 120      # ignore a re-tap this soon: that is a double-click


# ─────────────────────────────────────────────────────────────────────────────
# The audio pool
# ─────────────────────────────────────────────────────────────────────────────
class _Voice:
    """One player of the pool, plus what it is currently doing."""

    def __init__(self, player, out):
        self.player = player
        self.out = out
        # key and pad are set and cleared together: a voice with a pad is busy.
        self.key = None          # (page, row, col) while it is playing
        self.pad: pc.CartPad | None = None
        self.fade = 1.0
        self.fade_step = 0.0     # > 0 while fading out
        self.then: tuple[object, pc.CartPad] | None = None  # (key, pad) to start once the fade finishes
        self.started = 0.0       # monotonic, for "steal the oldest"
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
    padFading = Signal(object, bool)  # key, is it on its way out right now
    padTick = Signal(list)          # [(key, ms_left, frac), …]
    wantsDevice = Signal()          # a pad is about to fire — 🔇 device back

    def __init__(self, parent=None, voices=_VOICES, factory=None):
        super().__init__(parent)
        self._make = factory or self._build_player
        self._pool: list[_Voice] = []
        for _ in range(voices):
            player, out = self._make()
            voice = _Voice(player, out)
            out.setVolume(0.0)
            player.mediaStatusChanged.connect(
                lambda status, v=voice: self._on_status(v, status))
            player.errorOccurred.connect(
                lambda err, msg, v=voice: self._on_error(v, err, msg))
            self._pool.append(voice)
        self._level = 1.0        # master × desk, pushed in by _apply_volume
        self._muted = False
        self._wall_fade = pc.DEFAULT_FADE_MS   # what a pad follows by default
        self._last_fire: dict[object, float] = {}
        self._active = 0
        self._ducking = False
        self._ramp = QTimer(self)
        self._ramp.setInterval(_RAMP_MS)
        self._ramp.timeout.connect(self._step_fades)
        self._tick = QTimer(self)
        self._tick.setInterval(_TICK_MS)
        self._tick.timeout.connect(self._emit_tick)

    @staticmethod
    def _build_player():
        quiet_ffmpeg_log()
        player = QMediaPlayer()
        out = QAudioOutput()
        player.setAudioOutput(out)
        prime_disconnect_notify(player, out)
        return player, out

    # ── firing and stopping ──────────────────────────────────────────────────
    def is_playing(self, key) -> bool:
        """True only while the pad is really running — a pad that is fading out
        counts as free, so tapping it again re-fires instead of doing nothing."""
        voice = self._voice_for(key)
        return voice is not None and voice.fade_step <= 0

    def fire(self, key, pad: pc.CartPad) -> bool:
        # The desk first: it holds the released flag for ALL players, and a wall
        # that quietly re-attached only its own voices would leave that flag set
        # — the deck's output would then never be handed back again.
        self.wantsDevice.emit()
        self.restore_outputs()
        now = time.monotonic()
        if now - self._last_fire.get(key, 0.0) < _FIRE_GAP_MS / 1000.0:
            return False        # a double-click is one tap
        self._last_fire[key] = now

        reviving = self._voice_for(key)
        if reviving is not None:
            # It was fading out and the operator changed their mind.
            reviving.fade = 1.0
            reviving.fade_step = 0.0
            reviving.then = None
            reviving.pad = pad
            reviving.started = now
            reviving.player.setPosition(0)
            reviving.player.play()
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
            self._start_fade(voice, _STEAL_FADE_MS)
            return True
        self._start(voice, key, pad, url)
        return True

    def set_wall_fade(self, ms: int) -> None:
        """The wall-wide fade-out. Pads with a fade of their own ignore it."""
        self._wall_fade = max(0, min(pc.MAX_FADE_MS, int(ms)))

    def stop(self, key) -> None:
        voice = self._voice_for(key)
        if voice is not None and voice.pad is not None and voice.fade_step <= 0:
            self._start_fade(voice, pc.fade_for(voice.pad, self._wall_fade))

    def stop_all(self) -> None:
        for voice in self._pool:
            # A voice already on its steal ramp keeps fading, but the pad that
            # was waiting for it must not start any more.
            voice.then = None
            if voice.pad is not None and voice.fade_step <= 0:
                self._start_fade(voice, pc.fade_for(voice.pad, self._wall_fade))

    def playing_keys(self) -> list[object]:
        return [v.key for v in self._pool if v.busy]

    def rekey(self, moved: dict) -> None:
        """The wall was turned or reshaped: {old cell: new cell}. A sounding
        pad keeps its voice, it only answers to the cell it now sits in — or a
        tap there would start a second copy instead of stopping it."""
        for voice in self._pool:
            if voice.key is not None:
                voice.key = moved.get(voice.key, voice.key)
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

    def set_muted(self, muted: bool) -> None:
        """🔇 silences the wall without losing where anything is — the point of
        having it next to ⏹, which cannot bring a bed back mid-track."""
        self._muted = bool(muted)
        for voice in self._pool:
            if voice.busy:
                self._apply(voice)

    def muted(self) -> bool:
        return self._muted

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
            voice.pad = pad
            self._apply(voice)
            self._sync()

    def set_device(self, device) -> None:
        for voice in self._pool:
            voice.out.setDevice(device)

    def release_outputs(self) -> None:
        """🔇 Idle audio release: let go of the sound device (see
        player.audio.audio_device.AudioDevice.release). A voice pool is built at start-up and
        then holds the card for the whole evening, so the wall has to let go too
        or the hiss stays. Only ever called with every voice silent."""
        for voice in self._pool:
            voice.player.setAudioOutput(None)

    def restore_outputs(self) -> None:
        """Take the device back before a pad is heard. Called from `fire` — the
        one door every tap goes through."""
        for voice in self._pool:
            if voice.player.audioOutput() is None:
                voice.player.setAudioOutput(voice.out)

    def shutdown(self) -> None:
        """The one place sources ARE cleared: WMF keeps the file open, and a
        looping bed can hold one for an hour."""
        self._ramp.stop()
        self._tick.stop()
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

    def _pick(self, url) -> _Voice | None:
        """A voice for this file, cheapest first: one that already holds it, an
        unused one, the least recently used one — and only then take one over."""
        idle = [v for v in self._pool if not v.busy and v.fade_step <= 0]
        for voice in idle:
            if voice.player.source() == url:
                return voice
        for voice in idle:
            if voice.player.source().isEmpty():
                return voice
        if idle:
            return min(idle, key=lambda v: v.released)
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

    def _start(self, voice: _Voice, key, pad: pc.CartPad, url) -> None:
        if voice.player.source() != url:
            voice.player.setSource(url)
        voice.key = key
        voice.pad = pad
        voice.fade = 1.0
        voice.fade_step = 0.0
        voice.started = time.monotonic()
        self._apply(voice)
        voice.player.setPosition(0)
        voice.player.play()
        if not self._tick.isActive():
            self._tick.start()
        self._sync()

    def _start_fade(self, voice: _Voice, span_ms: int) -> None:
        if span_ms <= 0:
            # A hard cut, because this pad asked for one. It clicks — that is the
            # user's call to make per pad, which is why it is not the default.
            self._finish_fade(voice)
            return
        voice.fade_step = max(0.001, _RAMP_MS / float(span_ms))
        if voice.key is not None:
            self.padFading.emit(voice.key, True)
        if not self._ramp.isActive():
            self._ramp.start()

    def _step_fades(self) -> None:
        fading = False
        for voice in self._pool:
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

    def _finish_fade(self, voice: _Voice) -> None:
        follow = voice.then
        voice.then = None
        self._release(voice)
        if follow is not None:
            key, pad = follow
            self._start(voice, key, pad, QUrl.fromLocalFile(str(pad.path)))

    def _release(self, voice: _Voice) -> None:
        """Silence and rewind, but KEEP the source. The deck clears its source
        because a different title follows and WMF holds the handle; a cart voice
        is pinned to its sample on purpose, so the next tap costs nothing."""
        key = voice.key
        voice.player.pause()
        voice.player.setPosition(0)
        voice.out.setVolume(0.0)
        voice.key = None
        voice.pad = None
        voice.fade = 1.0
        voice.fade_step = 0.0
        voice.released = time.monotonic()
        if key is not None:
            self.padStopped.emit(key)
        self._sync()

    def _apply(self, voice: _Voice) -> None:
        if voice.pad is None:
            return
        vol = self._level * voice.pad.volume * voice.fade
        if self._muted:
            vol = 0.0
        voice.out.setVolume(max(0.0, min(1.0, vol)))

    def _on_error(self, voice: _Voice, err, msg: str) -> None:
        log.warning("🎛 Cartwall voice error\n"
                    "error: %s\n"
                    "detail: %s", err, msg)
        if voice.busy:
            self._finish_fade(voice)   # it will not play: free the voice (and duck)

    def _on_status(self, voice: _Voice, status) -> None:
        if voice.pad is None:
            return
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            # A file that cannot be decoded never reaches EndOfMedia, so it
            # would hold its voice and the duck for good. Not even a loop
            # pad retries it.
            self._finish_fade(voice)
            return
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if voice.pad.loop:
            # Endless repeat the way the pause music already does it. NOT
            # setLoops(Infinite) — this codebase moved off that API on this
            # backend (see the filler-player comment in dancesport_gui).
            voice.player.setPosition(0)
            voice.player.play()
            return
        # It ended where it was meant to: no fade — but a pad that stole this
        # voice mid-ramp is still waiting for it.
        self._finish_fade(voice)

    def _emit_tick(self) -> None:
        rows = []
        for voice in self._pool:
            if not voice.busy:
                continue
            total = voice.player.duration()
            pos = voice.player.position()
            left = max(0, total - pos) if total > 0 else -1
            frac = (pos / total) if total > 0 else 0.0
            rows.append((voice.key, left, frac))
        if rows:
            self.padTick.emit(rows)
        else:
            self._tick.stop()

    def _sync(self) -> None:
        active = sum(1 for v in self._pool if v.busy)
        ducking = any(v.pad is not None and v.pad.duck for v in self._pool)
        if active != self._active:
            self._active = active
            self.activeChanged.emit(active)
        if ducking != self._ducking:
            self._ducking = ducking
            self.duckChanged.emit(ducking)
