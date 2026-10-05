"""The sound card: which one we play into, whether we hold it, and the OS's own
sounds on it.

Split off player/main_audio.py as an object of its own rather than one more
MainWindow mixin: it owns its state (released? idle since when? which device?
the system-sound mute) and gets everything else it looks at handed in, so it is
built and tested without a window.
"""
import logging
import time
from typing import Callable

from shared.playback import _AUDIO_IDLE_S
from shared.stores import save_settings
from player.mix import OutputMix
from player.system_sounds import SystemSoundGuard

try:
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
except ImportError:
    pass

log = logging.getLogger("dancesport.gui.audio")


class AudioDevice:
    """🔊 Follow the default output, 🔇 hand it back while nothing plays and
    🔕 keep the OS's own sounds off the PA.

    `player` is None when Qt Multimedia is missing; only the system-sound half
    works then. The settings and the cartwall's voice pool are read through
    getters: the window replaces its settings dict when a dialog saves, and the
    wall builds its pool after this exists."""

    def __init__(self, player, audio_out, pause_player, pause_out, *,
                 mix: OutputMix,
                 settings: Callable[[], dict],
                 cart_voices: Callable[[], object],
                 is_playing_mode: Callable[[], bool],
                 apply_volume: Callable[[], None],
                 system_sounds: SystemSoundGuard):
        self._player = player
        self._audio_out = audio_out
        self._pause_player = pause_player
        self._pause_out = pause_out
        self._mix = mix
        self._settings = settings
        self._cart_voices = cart_voices
        self._is_playing_mode = is_playing_mode
        self._apply_volume = apply_volume
        self._system_sounds = system_sounds
        self.released = False
        self.idle_since: float | None = None
        self.out_id = None
        if player is not None:
            dev = QMediaDevices.defaultAudioOutput()
            self.out_id = None if dev is None or dev.isNull() else dev.id()

    def on_outputs_changed(self):
        """Windows audio device switched → re-point both players at the new system
        default so playback follows the active device instead of staying stuck on
        the device that was default when the outputs were created."""
        if not self._player:
            return
        dev = QMediaDevices.defaultAudioOutput()
        if dev is None or dev.isNull():
            return
        if dev.id() == self.out_id:
            return   # the list changed around a default that stayed put
        self.out_id = dev.id()
        self._audio_out.setDevice(dev)
        if self._pause_out is not None:
            self._pause_out.setDevice(dev)
        voices = self._cart_voices()
        if voices is not None:
            voices.set_device(dev)
        log.info("🔊 Audio device changed → %s", dev.description())

    def watch_default(self):
        """Poll for a change of DEFAULT output — Qt has no signal for it.

        `audioOutputsChanged` fires when a device appears or disappears, which
        misses the case the operator hits at the desk: two headsets both plugged
        in, and the output switched in the Windows flyout. The device list never
        changes, so the music keeps going into the one nobody is wearing."""
        if not self._player:
            return
        dev = QMediaDevices.defaultAudioOutput()
        if dev is not None and not dev.isNull() and dev.id() != self.out_id:
            self.on_outputs_changed()

    # ── 🔇 Handing the sound device back while nothing plays ─────────────────

    def busy(self) -> bool:
        """True while anything of ours is — or is about to be — audible: the
        deck (playing OR paused; a pause is resumed, not ended), the filler
        music, a cartwall pad, an announcement being spoken."""
        if self._player is None:
            return True
        stopped = QMediaPlayer.PlaybackState.StoppedState
        if self._player.playbackState() != stopped:
            return True
        if (self._pause_player is not None
                and self._pause_player.playbackState() != stopped):
            return True
        voices = self._cart_voices()
        if voices is not None and voices.playing_keys():
            return True
        return "announce" in self._mix.duck_reasons

    def watch_idle(self):
        """Hand the sound card back once everything has been silent for
        `_AUDIO_IDLE_S`. Rides the same 2 s tick as the default-device poll.

        An onboard output un-mutes its analogue stage the moment an app opens
        it, and the PA carries that hiss all evening — it starts with the app
        and stops when the app closes, playing or not. Nothing in the audio
        path can filter it out: it is added AFTER the converter, downstream of
        every sample we produce. Not holding the device open is the only cure,
        which is why this is a device question and not a volume one."""
        if self._player is None:
            return
        if not (self._settings() or {}).get("release_audio_idle"):
            self.idle_since = None
            if self.released:
                self.ensure()   # switched off mid-evening
            return
        if self.busy():
            self.idle_since = None
            return
        now = time.monotonic()
        if self.idle_since is None:
            self.idle_since = now
        elif now - self.idle_since >= _AUDIO_IDLE_S:
            self.release()

    def release(self):
        """Let go of the output — every player at once, because one of them
        holding it is enough to keep the hiss on the PA."""
        if self.released or self._player is None:
            return
        self.released = True
        self._player.setAudioOutput(None)
        if self._pause_player is not None:
            self._pause_player.setAudioOutput(None)
        voices = self._cart_voices()
        if voices is not None:
            voices.release_outputs()
        log.info("🔇 Sound device handed back\n"
                 "after: %.0f s of silence", _AUDIO_IDLE_S)

    def ensure(self):
        """Take the device back before anything can be heard.

        Hung on the players' own playbackStateChanged rather than on the
        thirteen places that call play(): a title that starts silently because
        one path forgot to ask is the one failure this feature must not have."""
        if not self.released or self._player is None:
            return
        self.released = False
        self._player.setAudioOutput(self._audio_out)
        if self._pause_player is not None and self._pause_out is not None:
            self._pause_player.setAudioOutput(self._pause_out)
        voices = self._cart_voices()
        if voices is not None:
            voices.restore_outputs()
        self._apply_volume()
        self.idle_since = None
        log.info("🔊 Sound device taken back for the next title")

    def on_playback_state(self, state):
        """Whatever starts a title — a deck row, ⏯, the presenter, the filler —
        the device is back before its first sample is due."""
        if state != QMediaPlayer.PlaybackState.StoppedState:
            self.ensure()
        self.watch_system_sounds()

    # ── 🔕 The OS's own sounds off the PA ─────────────────────────────────────

    def watch_system_sounds(self):
        """Mute the System Sounds session all through Playing mode — the gaps
        between dances go out over the PA too — and whenever anything of ours
        is audible in planning. Rides the 2 s tick, the playback signal and the
        mode switch; `player.system_sounds` does the muting."""
        want = (bool(self._settings().get("mute_system_sounds", True))
                and (self._is_playing_mode() or self.busy()))
        self.hold_system_sounds(want)

    def hold_system_sounds(self, on: bool):
        if self._system_sounds.hold(on):
            # The OS keeps the change after we are gone: a crash must be able
            # to find out on the next start what is still to be put back.
            settings = self._settings()
            record = self._system_sounds.record
            if record is None:
                settings.pop("system_sounds_muted", None)
            else:
                settings["system_sounds_muted"] = record
            save_settings(settings)
