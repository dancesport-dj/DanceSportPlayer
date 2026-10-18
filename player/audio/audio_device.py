"""The sound card: which one we play into, whether we hold it, and the OS's own
sounds on it.

Split off player/window/main_audio.py as an object of its own rather than one more
MainWindow mixin: it owns its state (released? idle since when? which device?
the system-sound mute) and gets everything else it looks at handed in, so it is
built and tested without a window.
"""
import logging
import time
from typing import TYPE_CHECKING, Callable

from planner import i18n
from shared.audio.playback import (_AUDIO_IDLE_S, OUTPUT_SOURCES, SYSTEM_DEFAULT,
                                   device_id, match_output)
from shared.stores import save_settings
from player.audio.mix import OutputMix
from player.audio.system_sounds import SystemSoundGuard

try:
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
except ImportError:
    pass

if TYPE_CHECKING:
    from player.audio.announce import DanceAnnouncer
    from player.audio.cart_voices import CartVoices

log = logging.getLogger("dancesport.gui.audio")


class AudioDevice:
    """🔊 Put every source on its output, 🔇 hand the card back while nothing
    plays and 🔕 keep the OS's own sounds off the PA.

    `player` is None when Qt Multimedia is missing; only the system-sound half
    works then. The settings, the cartwall's voice pool and the announcer are
    read through getters: the window replaces its settings dict when a dialog
    saves, and the wall builds its pool after this exists. `devices` is
    QMediaDevices unless a test hands in its own list; `warn` tells the
    operator that a chosen output is not there. `cue` is the 🎧 pre-listen
    player (player.audio.cue_player), None without Qt Multimedia."""

    def __init__(self, player, audio_out, pause_player, pause_out, *,
                 mix: OutputMix,
                 settings: Callable[[], dict],
                 cart_voices: Callable[[], "CartVoices | None"],
                 is_playing_mode: Callable[[], bool],
                 apply_volume: Callable[[], None],
                 system_sounds: SystemSoundGuard,
                 announcer: Callable[[], "DanceAnnouncer | None"] = lambda: None,
                 devices=None,
                 warn: Callable[[str], None] | None = None,
                 cue=None):
        self._player = player
        self.cue = cue
        self._audio_out = audio_out
        self._pause_player = pause_player
        self._pause_out = pause_out
        self._mix = mix
        self._settings = settings
        self._cart_voices = cart_voices
        self._is_playing_mode = is_playing_mode
        self._apply_volume = apply_volume
        self._system_sounds = system_sounds
        self._announcer = announcer
        self._warn = warn
        self.released = False
        self.idle_since: float | None = None
        self.out_id = None
        # Source → id of the device it was last put on, and the chosen outputs
        # already reported missing (said once, until they are back).
        self._applied: dict[str, bytes] = {}
        self._missing: set[str] = set()
        if player is not None:
            self._devices = devices or QMediaDevices
            dev = self._devices.defaultAudioOutput()
            self.out_id = None if dev is None or dev.isNull() else dev.id()
            # Both outputs were built on the default: only a choice moves them.
            for source, out in (("music", audio_out), ("filler", pause_out)):
                if out is not None:
                    self._applied[source] = device_id(out.device())
            self.sync()

    def on_outputs_changed(self):
        """A device came or went, or the default switched → put every source
        back on its output: the ones following the default move with it, a
        chosen card that was missing is taken back once it is there again."""
        if not self._player:
            return
        dev = self._devices.defaultAudioOutput()
        if dev is not None and not dev.isNull():
            if dev.id() == self.out_id:
                # The list changed around a default that stayed put. On the
                # record anyway: a stutter at the same second points here.
                log.info("🔊 Audio outputs changed\n"
                         "default: %s (kept)\n"
                         "outputs: %d", dev.description(),
                         len(self._devices.audioOutputs()))
            else:
                self.out_id = dev.id()
                log.info("🔊 Default audio device changed → %s", dev.description())
        self.sync()

    def watch_default(self):
        """Poll for a change of DEFAULT output — Qt has no signal for it.

        `audioOutputsChanged` fires when a device appears or disappears, which
        misses the case the operator hits at the desk: two headsets both plugged
        in, and the output switched in the Windows flyout. The device list never
        changes, so the music keeps going into the one nobody is wearing.

        The same tick applies a changed output choice from ⚙ Settings."""
        if not self._player:
            return
        dev = self._devices.defaultAudioOutput()
        if dev is not None and not dev.isNull() and dev.id() != self.out_id:
            self.on_outputs_changed()
        else:
            self.sync()

    # ── 🔊 One output per source ──────────────────────────────────────────────

    def _choice(self, source: str) -> dict:
        return ((self._settings() or {}).get("audio_outputs") or {}).get(source) or {}

    def _chosen_device(self, want: str, name: str | None = None):
        """The plugged-in device with id `want` (hex) — or, renumbered by
        Windows under a new id, the one called `name` (`match_output`) — or
        None."""
        devs = {device_id(dev).hex(): dev for dev in self._devices.audioOutputs()}
        hit = match_output([(i, d.description()) for i, d in devs.items()],
                           want, name)
        return devs.get(hit) if hit else None

    def _lookup(self, source: str):
        """What target() answers, without a word about a missing card."""
        want = self._choice(source).get("id")
        if not want:
            return (self._lookup("music") if source != "music"
                    else self._devices.defaultAudioOutput())
        if want == SYSTEM_DEFAULT:
            return self._devices.defaultAudioOutput()
        return (self._chosen_device(want, self._choice(source).get("name"))
                or self._devices.defaultAudioOutput())

    def target(self, source: str):
        """The device `source` should play on: its chosen output while that is
        plugged in, else what it follows — the music the system default, every
        other source the music."""
        choice = self._choice(source)
        want = choice.get("id")
        if not want:
            return (self.target("music") if source != "music"
                    else self._devices.defaultAudioOutput())
        if want == SYSTEM_DEFAULT:
            return self._devices.defaultAudioOutput()
        dev = self._chosen_device(want, choice.get("name"))
        if dev is not None:
            self._missing.discard(want)
            return dev
        if want not in self._missing:
            self._missing.add(want)
            name = choice.get("name") or want
            log.warning("🔈 Chosen audio output not connected\n"
                        "source: %s\n"
                        "output: %s\n"
                        "playing on: the system default", source, name)
            if self._warn is not None:
                self._warn(i18n.t("🔈 %s is not connected — playing on the "
                                  "system default until it is back.") % name)
        return self._devices.defaultAudioOutput()

    def cue_device(self):
        """🎧 The pre-listen output, or None when none is chosen (pre-listen
        is off — it follows nothing). A chosen card that is not plugged in
        falls back to the system default, as its warning says."""
        choice = ((self._settings() or {}).get("audio_outputs") or {}).get("cue") or {}
        if not choice.get("id"):
            return None
        return self.target("cue")

    def unplugged(self) -> list[tuple[str, str]]:
        """(source, name) of every chosen output that is not plugged in now,
        🎧 pre-listen included — for 🚦 Ready?, so it warns nothing."""
        if not self._player:
            return []
        out = []
        for source in (*OUTPUT_SOURCES, "cue"):
            choice = self._choice(source)
            want = choice.get("id")
            if (want and want != SYSTEM_DEFAULT
                    and self._chosen_device(want, choice.get("name")) is None):
                out.append((source, choice.get("name") or want))
        return out

    def music_card(self) -> str | None:
        """🔊 The name of the card chosen for the music while it is plugged
        in, for the status bar's badge — None on the system default, with
        nothing chosen, or while the card is missing. A look: it warns
        nothing and moves nothing."""
        if not self._player:
            return None
        choice = self._choice("music")
        want = choice.get("id")
        if not want or want == SYSTEM_DEFAULT:
            return None
        dev = self._chosen_device(want, choice.get("name"))
        return None if dev is None else dev.description()

    def cue_on_music(self) -> bool:
        """Whether a 🎧 pre-listen would be refused right now: its output, or
        the default it falls back to, is the one the music plays on."""
        if not self._player or not self._choice("cue").get("id"):
            return False
        cue, music = self._lookup("cue"), self._lookup("music")
        if cue is None or music is None:
            return False
        return device_id(cue) == device_id(music)

    def missing(self, source: str) -> bool:
        """Whether `source`'s chosen output was not plugged in when last
        looked up by target()."""
        choice = ((self._settings() or {}).get("audio_outputs") or {}).get(source) or {}
        return choice.get("id") in self._missing

    def _sink(self, source: str):
        """What takes a device for `source`, or None while it does not exist
        (the wall's pool and the announcer are built after this)."""
        if source == "music":
            return self._audio_out.setDevice
        if source == "filler":
            return None if self._pause_out is None else self._pause_out.setDevice
        owner = self._cart_voices() if source == "cartwall" else self._announcer()
        return None if owner is None else owner.set_device

    def sync(self):
        """Put every source on its target, touching only those that moved:
        moving an output re-opens the card."""
        if not self._player:
            return
        for source in OUTPUT_SOURCES:
            dev = self.target(source)
            if dev is None or dev.isNull():
                continue
            key = device_id(dev)
            if self._applied.get(source) == key:
                continue
            sink = self._sink(source)
            if sink is None:
                continue
            sink(dev)
            self._applied[source] = key
            log.info("🔊 Audio output set\n"
                     "source: %s\n"
                     "output: %s", source, dev.description())

    def swap_deck(self, player, audio_out):
        """🔀 A crossfade made the other player the deck: the music is that
        one's output now, and it goes on the music's device."""
        self._player, self._audio_out = player, audio_out
        self._applied.pop("music", None)
        self.sync()

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
        mode switch; `player.audio.system_sounds` does the muting."""
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
