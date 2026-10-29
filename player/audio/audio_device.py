"""The sound card: which one we play into, whether we hold it, and the OS's own
sounds on it.

Split off player/window/main_audio.py as an object of its own rather than one more
MainWindow mixin: it owns its state (released? idle since when? which device?
the system-sound mute) and gets everything else it looks at handed in, so it is
built and tested without a window.
"""
import contextlib
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer

from planner import i18n
from player.audio.mix import OutputMix
from player.audio.system_sounds import SystemSoundGuard
from shared.audio.playback import (
    AUDIO_IDLE_S,
    OUTPUT_SOURCES,
    SYSTEM_DEFAULT,
    choice_pair,
    device_id,
    match_output,
    pair_label,
)
from shared.stores import save_settings

with contextlib.suppress(ImportError):
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer

if TYPE_CHECKING:
    from player.audio.announce import DanceAnnouncer
    from player.audio.cart_voices import CartVoices
    from player.audio.pair_route import PairRoute

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
    player (player.audio.cue_player), None without Qt Multimedia.
    The music's players get theirs from `make_route`, each the first time
    the music is put on a pair; until then they run Qt's own path."""

    def __init__(self, player, audio_out, *,
                 mix: OutputMix,
                 settings: Callable[[], dict],
                 cart_voices: Callable[[], CartVoices | None],
                 is_playing_mode: Callable[[], bool],
                 apply_volume: Callable[[], None],
                 system_sounds: SystemSoundGuard,
                 announcer: Callable[[], DanceAnnouncer | None] = lambda: None,
                 devices=None,
                 warn: Callable[[str], None] | None = None,
                 cue=None,
                 spare_deck: Callable[[], tuple] = lambda: (None, None),
                 make_route: Callable[[object, object], PairRoute] | None = None):
        self._player = player
        self._make_route = make_route
        # id(player) → the route of a music player (the deck, the spare deck).
        self._routes: dict[int, PairRoute] = {}
        self.cue = cue
        self._audio_out = audio_out
        self._mix = mix
        self._settings = settings
        self._cart_voices = cart_voices
        self._is_playing_mode = is_playing_mode
        self._apply_volume = apply_volume
        self._system_sounds = system_sounds
        self._system_sounds_unsaved = False
        self._announcer = announcer
        self._spare_deck = spare_deck
        self._warn = warn
        self.released = False
        self.idle_since: float | None = None
        self.out_id = None
        # Source → (device id, channel pair) it was last put on, and the chosen
        # outputs already reported missing (said once, until they are back).
        self._applied: dict[str, tuple[bytes, int]] = {}
        self._missing: set[str] = set()
        if player is not None:
            self._devices = devices or QMediaDevices
            # 🔇 Started by the silence that starts the idle clock: one look
            # when the window is over, no poll. It goes with the deck's player,
            # so it never looks at a window that is gone.
            self._idle_timer = QTimer(player if isinstance(player, QObject) else None)
            self._idle_timer.setSingleShot(True)
            self._idle_timer.timeout.connect(self.watch_idle)
            dev = self._devices.defaultAudioOutput()
            self.out_id = None if dev is None or dev.isNull() else dev.id()
            # The output was built on the default: only a choice moves it.
            if audio_out is not None:
                self._applied["music"] = (device_id(audio_out.device()), 0)
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
        # 🔕 While muted, a backend that mutes per device mutes the one
        # plugged in just now.
        if self._system_sounds.active:
            self.hold_system_sounds(True)

    def watch_default(self):
        """Poll for a change of DEFAULT output, off Windows only.

        The case the operator hits at the desk: two headsets both plugged in,
        and the output switched in the system's sound menu. On Windows
        `audioOutputsChanged` fires for that too (measured 2026-10-27, Qt
        6.11), so nothing polls there. macOS and Linux are unverified."""
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

    def pair(self, source: str) -> int:
        """🔀 The channel pair `source` plays on, 0 for the whole device. A
        source following the music is on the music's pair; one following the
        system default, or whose chosen card is missing (the default it
        falls back to is not that card), is on all of it."""
        choice = self._choice(source)
        want = choice.get("id")
        if not want and source != "music":
            return self.pair("music")
        if (not want or want == SYSTEM_DEFAULT
                or self._chosen_device(want, choice.get("name")) is None):
            return 0
        return choice_pair(choice)

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

    def single_output(self) -> bool:
        """Whether this machine has one audio output at most — then there is
        no other card for 🎧 pre-listen, and the music's is its default."""
        return len(self._devices.audioOutputs()) <= 1

    def cue_on_music(self) -> bool:
        """Whether a 🎧 pre-listen would be refused right now: its output, or
        the default it falls back to, is the one the music plays on — and
        another one exists to choose."""
        if (not self._player or not self._choice("cue").get("id")
                or self.single_output()):
            return False
        cue, music = self._lookup("cue"), self._lookup("music")
        if cue is None or music is None:
            return False
        return ((device_id(cue), self.pair("cue"))
                == (device_id(music), self.pair("music")))

    def cue_shares_music(self) -> bool:
        """Whether 🎧 pre-listen is left on "Same as the music" while another
        output exists to choose: then every preview is heard where the music
        is, 📚 and 🏆 on the pre-listen player, the rest on the deck's."""
        return (bool(self._player) and not self._choice("cue").get("id")
                and not self.single_output())

    def missing(self, source: str) -> bool:
        """Whether `source`'s chosen output was not plugged in when last
        looked up by target()."""
        choice = ((self._settings() or {}).get("audio_outputs") or {}).get(source) or {}
        return choice.get("id") in self._missing

    def _route(self, player, out, pair: int) -> PairRoute | None:
        """🔀 A music player's route, built the first time it is put on a
        channel pair; None for one that never was."""
        route = self._routes.get(id(player))
        if route is None and pair:
            if self._make_route is None:
                from player.audio.pair_route import PairRoute
                self._make_route = PairRoute
            route = self._routes[id(player)] = self._make_route(player, out)
        return route

    def _hold(self, player, out, on: bool):
        """Take a music player's card (`on`) or let go of it."""
        route = self._routes.get(id(player))
        if route is None:
            player.setAudioOutput(out if on else None)
        elif on:
            route.restore()
        else:
            route.release()

    def _sink(self, source: str, pair: int):
        """What takes a device and channel pair for `source`, or None while
        it does not exist (the wall's pool and the announcer are built after
        this)."""
        if source == "music":
            route = self._route(self._player, self._audio_out, pair)
            if route is not None:
                return route.set_device
            return lambda dev, _pair: self._audio_out.setDevice(dev)
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
            pair = self.pair(source)
            key = (device_id(dev), pair)
            if self._applied.get(source) == key:
                continue
            sink = self._sink(source, pair)
            if sink is None:
                continue
            sink(dev, pair)
            self._applied[source] = key
            log.info("🔊 Audio output set\n"
                     "source: %s\n"
                     "output: %s\n"
                     "channels: %s", source, dev.description(),
                     pair_label(pair) if pair else "the whole device")

    def swap_deck(self, player, audio_out):
        """🔀 A crossfade made the other player the deck: the music is that
        one's output now, and it goes on the music's device."""
        self._player, self._audio_out = player, audio_out
        self._applied.pop("music", None)
        self.sync()

    # ── 🔇 Handing the sound device back while nothing plays ─────────────────

    def busy(self) -> bool:
        """True while anything of ours is — or is about to be — audible: the
        deck (playing OR paused; a pause is resumed, not ended), a cartwall
        pad, an announcement being spoken."""
        if self._player is None:
            return True
        stopped = QMediaPlayer.PlaybackState.StoppedState
        if self._player.playbackState() != stopped:
            return True
        voices = self._cart_voices()
        if voices is not None and voices.playing_keys():
            return True
        return "announce" in self._mix.duck_reasons

    def watch_idle(self):
        """Hand the sound card back once everything has been silent for
        `_AUDIO_IDLE_S`. Called whenever something starts or stops being
        audible (see `on_activity`); the silence that starts the clock sets
        `_idle_timer` to look again when the window is over.

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
            self._idle_timer.stop()
            if self.released:
                self.ensure()   # switched off mid-evening
            return
        if self.busy():
            self.idle_since = None
            self._idle_timer.stop()
            return
        now = time.monotonic()
        if self.idle_since is None:
            self.idle_since = now
        left = AUDIO_IDLE_S - (now - self.idle_since)
        if left <= 0:
            self.release()
        else:
            # A coarse timer may fire a little early: then it looks again.
            self._idle_timer.start(int(left * 1000) + 1)

    def release(self):
        """Let go of the output — every player at once, because one of them
        holding it is enough to keep the hiss on the PA."""
        if self.released or self._player is None:
            return
        self.released = True
        self._hold(self._player, self._audio_out, False)
        voices = self._cart_voices()
        if voices is not None:
            voices.release_outputs()
        # Both built on first use — and from then on holding the card too.
        spare, spare_out = self._spare_deck()
        if spare is not None:
            self._hold(spare, spare_out, False)
        announcer = self._announcer()
        if announcer is not None:
            announcer.release_outputs()
        log.info("🔇 Sound device handed back\n"
                 "after: %.0f s of silence", AUDIO_IDLE_S)

    def ensure(self):
        """Take the device back before anything can be heard.

        Hung on the players' own playbackStateChanged rather than on the
        thirteen places that call play(): a title that starts silently because
        one path forgot to ask is the one failure this feature must not have."""
        if not self.released or self._player is None:
            return
        self.released = False
        self._hold(self._player, self._audio_out, True)
        voices = self._cart_voices()
        if voices is not None:
            voices.restore_outputs()
        spare, spare_out = self._spare_deck()
        if spare is not None and spare_out is not None:
            self._hold(spare, spare_out, True)
        announcer = self._announcer()
        if announcer is not None:
            announcer.restore_outputs()
        self._apply_volume()
        self.idle_since = None
        log.info("🔊 Sound device taken back for the next title")

    def on_playback_state(self, state):
        """Whatever starts a title — a deck row, ⏯, the presenter —
        the device is back before its first sample is due."""
        if state != QMediaPlayer.PlaybackState.StoppedState:
            self.ensure()
        self.on_activity()

    def on_activity(self):
        """🔇🔕 Something started or stopped being audible — a player, a pad,
        an announcement — or ⚙ Settings was saved: the idle clock and the
        system-sound mute look again. They have no poll of their own."""
        self.watch_system_sounds()
        self.watch_idle()

    # ── 🔕 The OS's own sounds off the PA ─────────────────────────────────────

    def watch_system_sounds(self):
        """Mute the System Sounds session all through Playing mode — the gaps
        between dances go out over the PA too — and whenever anything of ours
        is audible in planning. Called from `on_activity` and the mode
        switch; `player.audio.system_sounds` does the muting."""
        want = (bool(self._settings().get("mute_system_sounds", True))
                and (self._is_playing_mode() or self.busy()))
        self.hold_system_sounds(want)

    def hold_system_sounds(self, on: bool):
        if self._system_sounds_unsaved:
            on = False
        if self._system_sounds.hold(on):
            # The OS keeps the change after we are gone: a crash must be able
            # to find out on the next start what is still to be put back.
            settings = self._settings()
            record = self._system_sounds.record
            if record is None:
                settings.pop("system_sounds_muted", None)
            else:
                settings["system_sounds_muted"] = record
            if not save_settings(settings) and record is not None:
                # Nothing on disk says what to put back, so a crash would
                # leave the OS muted for good: lift it, and stay off.
                log.warning("🔕 System Sounds left unmuted\n"
                            "reason: the settings could not be saved")
                self._system_sounds_unsaved = True
                self._system_sounds.hold(False)
                settings.pop("system_sounds_muted", None)
