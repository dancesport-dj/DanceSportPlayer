"""Levels: master volume, the ducks, loudness (LUFS) and silence skipping.

Split off player/window/main_player.py — everything that decides HOW LOUD the desk is and
where a track really starts, as a MainWindow mixin. The sound card itself (which
one, held or handed back, the OS's own sounds) is player/audio/audio_device.py.
"""
import logging

from planner import i18n

from PySide6.QtCore import (
    QTimer,
)
from pathlib import Path
from shared.audio.playback import (
    _TARGET_LUFS,
    _TRUE_PEAK_CEILING,
    audible_played_secs,
)
from shared.stores import (  # auto-resolved
    save_settings,
)
from shared.audio.audio_probes import LoudnessWorker, SilenceWorker, find_ffmpeg  # auto-resolved
from player.audio.mix import (
    _ANNOUNCE_DUCK,  # noqa: F401 — re-exported: the level arithmetic moved out
    _DESK_DUCK,  # noqa: F401
    _DUCK_DOWN_MS,  # noqa: F401
    _DUCK_UP_MS,  # noqa: F401
    desk_duck_level,
    desk_duck_pct,
    fade_in_secs,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.audio")

# 🔇 Only stretches at least this silent-long are skipped in playback. Only the
# edges of a track are skipped at all, so a musical break (a Paso Doble stop
# pose!) is safe by position; the floor matches the probe's own 2 s minimum,
# which catches a short silent intro like Ella Vos - Temporary (3.8 s).
_SILENCE_SKIP_MIN = 2.0

# 📊 A title nobody measured yet: hold its start until its loudness is known,
# but never longer than this — a silent floor is worse than a levelled one.
# Past the cap the title starts anyway and the gain is ramped in on the fly
# (player.audio.mix decides how long that swell takes).
_LUFS_WAIT_MS = 1000


class AudioLevelMixin(MainWindowHost):
    """Master volume, ducking, loudness levelling and silence skipping."""

    def _apply_volume(self):
        """Push what the mix says each output should be at, right now."""
        if self._player and self._audio_out is not None:
            self._audio_out.setVolume(self._mix.deck())
        if self._cart_voices is not None:
            self._cart_voices.set_level(self._mix.cartwall())

    def _set_desk_duck(self, on: bool):
        """🔉 The duck button on the player card / preview overlay: everything
        audible down and back. A factor of its own, so it survives a fade-out
        ramp or an announcement happening at the same time — and the filler
        music picks it up on its next tick."""
        self._mix.set_desk_duck(on, desk_duck_level(self._settings))
        self._apply_volume()
        if self._big_player:
            self._big_player.set_ducked(on)
        if self._preview:
            self._preview.set_ducked(on)
        if self._presenter is not None:
            self._presenter.set_ducked(on)
        log.info("🔉 Desk duck %s\n"
                 "factor: %.2f", "on" if on else "off", self._mix.desk)

    def apply_duck_level(self):
        """🔉 The duck level from ⚙ Settings: every duck button names it, and
        a duck that is on right now moves to it. One that is off stays off."""
        pct = desk_duck_pct(self._settings)
        for w in (self._big_player, self._preview, self._presenter):
            if w is not None:
                w.set_duck_level(pct)
        if self._mix.desk != 1.0:
            self._set_desk_duck(True)

    def _set_duck_reason(self, reason: str, on: bool):
        """Ref-counted duck: the announcer and the 🎛 cartwall both pull the
        music down, and whichever of them ends first must not lift it back up
        over the other. `player.audio.mix` keeps the reasons; this starts the ramp."""
        self._mix.duck_reason(reason, on)
        if not self._ramp_timer.isActive():
            self._ramp_timer.start()

    def _on_announcer_speaking(self, on: bool):
        """Pull the music down under a spoken announcement and let it back up
        afterwards — without a break there is no silence to speak into.

        Ramped, not stepped: a hard level change on running music clicks, and
        the ear reads the click as the music itself being damaged. Down fast
        (the first word must not be buried), back up slowly.

        Called before the first clip plays, so it is also where the device is
        taken back: the clip player is none of the deck's players."""
        if on:
            self._audio_device.ensure()
        self._set_duck_reason("announce", on)

    def _step_volume_ramp(self):
        """One ramp step of the announcement duck and of a loudness gain that
        arrived after the title had already started."""
        if self._mix.step() and self._big_player:
            self._big_player.set_gain(self._mix.heard_gain())   # the dB readout, once
        if self._mix.settled:
            self._ramp_timer.stop()
        self._apply_volume()
        if self._filler.active:
            self._update_pause_music_volume()

    def _set_base_volume(self, v: float):
        """Volume slider (preview overlay or big player card) → user's base
        volume factor. Keeps the other slider in sync and persists the level.
        The card's dB follows too: how much of a boost is heard depends on it."""
        self._mix.set_base(v)
        self._apply_volume()
        if self._big_player:
            self._big_player.set_volume_value(self._mix.base)
            self._big_player.set_gain(self._mix.heard_gain())
        self._vol_save_timer.start()

    def _set_cart_volume(self, v: float):
        """🎛 The cartwall's own fader (its slider, a controller fader, the desk
        keys) → the pads' level, apart from the music. Persisted the same way."""
        self._mix.set_cart(v)
        self._apply_volume()
        if self._cartwall is not None:
            self._cartwall.set_level(self._mix.cart)
        self._vol_save_timer.start()

    def _save_master_volume(self):
        self._settings["master_volume"] = round(self._mix.base, 3)
        self._settings["cartwall_volume"] = round(self._mix.cart, 3)
        save_settings(self._settings)

    def _loudness_gain(self, path: Path) -> float:
        """Per-track equalization factor: pull the track's measured EBU R128
        loudness towards the common target, clamped to −12…+9 dB so a broken
        measurement can never blast or mute a song. Where the true peak is on
        record, no gain takes it past −1 dBTP."""
        if not self._pv("loudness") or not self._library.cache:
            return 1.0
        try:
            lufs = self._library.cache.get_lufs(path)
            tp = self._library.cache.get_tp(path)
        except Exception:
            return 1.0
        if lufs is None:
            return 1.0
        gain_db = max(-12.0, min(9.0, _TARGET_LUFS - lufs))
        if tp is not None:
            gain_db = min(gain_db, _TRUE_PEAK_CEILING - tp)
        return 10 ** (gain_db / 20)

    def _refresh_loudness_gain(self):
        """Take the 🔊 Equalize volume box as it stands NOW for the loaded track.

        The gain is otherwise fixed when a track loads, so ticking the box during
        a song only reached the NEXT title. Every resume re-asks: pause, press
        play, and the setting is in force — and a level that changes exactly when
        the music comes back is the one the hall does not hear jump."""
        if self._playback.path is None:
            return
        gain = self._loudness_gain(self._playback.path)
        if not self._mix.snap_gain(gain):
            return
        self._apply_volume()
        if self._big_player:
            self._big_player.set_gain(self._mix.heard_gain())

    def _ensure_silences(self, path: Path):
        """Arm the 🔇 stillness skip for the (about to be) playing track: use
        the session dict or the DB cache if we can, else probe with ffmpeg in
        the background and arm once the spans land (the song plays meanwhile)."""
        if self._silences.get(str(path)) is not None:
            return      # spans known (None: one probe failed, try again)
        if self._library.cache:
            stored = self._library.cache.get_silences(path)
            if stored is not None:
                self._silences[str(path)] = [list(s) for s in stored]
                return
        running = self._silence_worker
        if running is not None and running.isRunning():
            if running.path == path:
                return   # already being probed
            # A title skipped a few seconds in: its probe gives way, or the
            # one the hall hears now would play unskipped. It is probed again
            # the next time it is loaded.
            running.cancel()
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return
        # Not cached — this title costs an ffmpeg decode in the background while
        # it plays. ⚙ Settings → 🔇 Probe silences does the whole library up front.
        log.info("🔇 Silence probe started (background)\nfile: %s", path.name)
        w = SilenceWorker(path, ffmpeg, parent=self)
        w.done.connect(self._on_silences)
        w.error.connect(self._on_silence_error)
        self._silence_worker = w
        w.start()

    def _on_silences(self, path_str: str, spans: list):
        self._silences[path_str] = [list(s) for s in spans]
        if self._library.cache:   # persist, so the next session arms instantly
            self._library.cache.put_silences(Path(path_str), spans)
            self._library.cache.save()
        if self._playback.path is not None and str(self._playback.path) == path_str:
            # The probe ran while this very track plays — the countdown was
            # still aimed at the end of the file until now.
            self._sync_big_player_limit()
        # The ⏱ cells were painted before this answer existed: a row that should
        # read red (or no longer should) only learns it here.
        for table in self._deckset.all_tables:
            table.refresh_paths([Path(path_str)])
        if spans:
            log.info("🔇 Silence probed\n"
                     "file: %s\n"
                     "spans: %s", Path(path_str).name,
                     ", ".join(f"{s:.1f}–{e:.1f}s" for s, e in spans))

    def _on_silence_error(self, path_str: str, _msg: str):
        # One failure may pass (the file locked for a moment, a virus scan):
        # the title is probed again on its next load. A second one is
        # remembered, so a file ffmpeg cannot read isn't re-probed every play.
        # None marks the first failure; every reader takes it as "no spans".
        self._silences[path_str] = [] if path_str in self._silences else None

    def _await_loudness(self, path: Path, start: bool) -> bool:
        """Measure a track's EBU R128 loudness before the hall hears it, if
        nobody ever did.

        Without this, a title added after the last ⚙ Settings → 📊 Analyze
        loudness run played at its own level while everything around it was
        equalized — the one song in the round that is too loud or too quiet.
        Starting it and correcting the level a second later is the worse of the
        two: the floor hears the mistake, not the fix. So a title that is about
        to be PLAYED waits for its measurement (≈1 s, capped at _LUFS_WAIT_MS);
        a title that is only cued measures in the background and is levelled
        long before it is heard.

        Returns True when the caller must stand down — the load re-enters
        through `_resume_after_loudness` once the number is in.
        """
        self._lufs_pending = None   # any new load supersedes an older wait
        if not self._pv("loudness") or not self._library.cache:
            return False
        if str(path) in self._lufs_failed:
            return False    # measured once, ffmpeg said no — never wait again
        try:
            if self._library.cache.get_lufs(path) is not None:
                return False
        except Exception:
            return False
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return False
        running = self._lufs_worker
        if running is not None and running.isRunning():
            if running.path == path:
                return False    # already being measured — don't measure twice
            running.cancel()    # a skipped title's decode gives way, as above
        log.info("📊 Loudness measurement started (background)\n"
                 "file: %s\n"
                 "playback waits: %s", path.name, "yes" if start else "no")
        w = LoudnessWorker(path, ffmpeg, parent=self)
        w.done.connect(self._on_track_lufs)
        w.error.connect(self._on_track_lufs_error)
        self._lufs_worker = w
        if start:
            self._lufs_pending = path
            self._lufs_token = self._playback.token
            QTimer.singleShot(_LUFS_WAIT_MS, self,
                              lambda: self._resume_after_loudness(path))
        w.start()
        return start

    def _resume_after_loudness(self, path: Path):
        """Play the title that was held back — either because its measurement
        landed or because it took too long to keep waiting for."""
        if self._lufs_pending is None or self._lufs_pending != path:
            return          # superseded by a newer load, or already resumed
        if self._lufs_token != self._playback.token:
            # ⏹ (or any other stop) came in during the wait: every stop path
            # bumps the token, and the operator's stop must win.
            self._lufs_pending = None
            return
        self._lufs_pending = None
        self._load_track(path, True)

    def _on_track_lufs(self, path_str: str, lufs: float, tp: float | None = None):
        """A measurement landed: store it, then either start the title that was
        waiting for it or — if that title is already running because the wait
        timed out — ramp its gain to where it should have started."""
        if self._library.cache:
            self._library.cache.put_lufs(Path(path_str), lufs, tp)
            self._library.cache.save()
        log.info("📊 Loudness measured\n"
                 "file: %s\n"
                 "lufs: %.1f", Path(path_str).name, lufs)
        if self._lufs_pending is not None and str(self._lufs_pending) == path_str:
            self._resume_after_loudness(self._lufs_pending)
            return
        if self._playback.path is None or str(self._playback.path) != path_str:
            return
        if self._mix.ramp_gain_to(self._loudness_gain(self._playback.path)):
            self._ramp_timer.start()

    def _on_track_lufs_error(self, path_str: str, msg: str):
        """ffmpeg couldn't measure the file — remember that, so no later play
        of it waits for a number that will never come."""
        self._lufs_failed.add(path_str)
        log.warning("📊 Loudness measurement failed\n"
                    "file: %s\n"
                    "reason: %s", Path(path_str).name, msg)
        if self._lufs_pending is not None and str(self._lufs_pending) == path_str:
            self._resume_after_loudness(self._lufs_pending)

    def _heard_secs(self) -> float:
        """Music the floor has heard of this title (see audible_played_secs)."""
        if self._player is None:
            return 0.0
        return audible_played_secs(self._player.position(), self._playback.offset_ms,
                                   self._player.playbackRate())

    def _arm_fade_in(self, path: Path):
        """🌅 A title being loaded starts at silence when the fade-in is on.
        Not one a 🔀 crossfade brings in (that has its own ramp), and not in
        the floating overlay: a pre-listen starts at full level."""
        xf = self._between.xfade
        if (fade_in_secs(self._settings) <= 0 or not self._is_playing_mode()
                or (xf.state == "fading" and path == xf.incoming)):
            self._playback.fade_in_from = None
            self._playback.fade_in_secs = 0.0
            return
        self._playback.fade_in_from = 0.0
        self._playback.fade_in_secs = fade_in_secs(self._settings)
        self._mix.fade_in = 0.0

    def _step_fade_in(self):
        """🌅 One tick of the fade-in, counted in music heard: a pause holds
        it, and a running 🔀 crossfade owns the level until it ends."""
        start = self._playback.fade_in_from
        if start is None or self._between.xfade.state is not None:
            return
        secs = fade_in_secs(self._settings)
        level = (1.0 if secs <= 0
                 else max(0.0, min(1.0, (self._heard_secs() - start) / secs)))
        if level >= 1.0:
            self._playback.fade_in_from = None
        self._mix.fade_in = level
        self._apply_volume()

    def _maybe_skip_silence(self) -> bool:
        """Playhead inside a ≥2 s silent stretch at the EDGES of the track:
        jump past a silent intro, end the song when the stretch runs to the
        end of the file (dead air after the last note). Silence in the middle
        is left alone — it may be a deliberate break the dancers know.
        Returns True when this tick skipped."""
        path = self._playback.path
        if path is None:
            return False
        spans = self._silences.get(str(path))
        if not spans or self._player is None:
            return False
        pos = self._player.position() / 1000.0
        for start, end in spans:
            if end - start < _SILENCE_SKIP_MIN:
                continue
            # 0.3 s in before acting (never clip the last note's release);
            # the 0.7 s tail guard keeps a just-landed seek from re-firing.
            if not (start + 0.3 <= pos < end - 0.7):
                continue
            dur = self._track_duration(path)
            if dur > 0 and end >= dur - 1.5:            # trailing silence
                log.info("🔇 Trailing silence from %.1fs — ending playback\n"
                         "file: %s", start, path.name)
                self.statusBar().showMessage(
                    i18n.t("🔇 Only stillness left from %s — song ended.")
                    % f"{int(start) // 60}:{int(start) % 60:02d}", 4000)
                self._on_timed_end("trailing silence")
            elif start <= 0.5:                          # silent intro
                log.info("🔇 Skipping %.1fs of leading silence\n"
                         "file: %s", end - start, path.name)
                self.statusBar().showMessage(
                    i18n.t("🔇 Skipped %ss of leading silence.") % f"{end - start:.0f}", 4000)
                target_ms = int(end * 1000) - 200
                # Don't let the skipped dead air eat into the play length.
                self._playback.offset_ms += max(0, target_ms - int(pos * 1000))
                self._player.setPosition(target_ms)
                if self._playback.fade_in_from is not None:
                    # 🌅 …nor into the fade-in: it starts over with the music.
                    self._playback.fade_in_from = self._heard_secs()
                    self._mix.fade_in = 0.0
                self._sync_big_player_limit()   # the ⏳ cut moved back with it
            else:
                continue   # mid-track stillness — play it as recorded
            return True
        return False
