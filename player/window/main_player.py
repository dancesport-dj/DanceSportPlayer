"""Playing mode: the player card, the play sets and the running clock.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
`PlayerControlMixin` is composed of smaller ones — levels (player.window.main_audio),
the 🐂 PD stop (player.window.main_pd), the ⏸ pause (player.window.main_pause), the
🖥 presenter screen (player.window.main_presenter), the per-list play values
(player.window.main_play_values) and loading a title (player.window.main_load) — so
MainWindow keeps importing this one name.
"""
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
)
from PySide6.QtWidgets import (
    QMessageBox,
)

from planner import i18n, terms
from planner.music.paths import resolve_file
from planner.playing import play_counts, play_log
from planner.playing.celebration import (
    celebrate_dip_pct,
    celebrate_down_secs,
    celebrate_hold_secs,
    celebrate_level,
    celebrate_mode,
    celebrate_pct,
    celebrate_up_secs,
    celebrates,
)
from planner.playlist.checks import trailing_silence_secs
from planner.terms import dance_name
from player.audio.mix import hand_fade_secs
from player.audio.tso import round_strip, round_takte, tso_band_of, tso_target
from player.widgets.player_parts import (  # auto-resolved
    set_time_format,
    takt_text,
)
from player.widgets.quit_fade import QuitFadeDialog
from player.widgets.taskbar import (
    TaskbarPlayer,
)
from player.window.main_audio import (
    ANNOUNCE_DUCK,  # noqa: F401 — re-exported: tests patch it here
    DESK_DUCK,  # noqa: F401
    DUCK_DOWN_MS,  # noqa: F401
    DUCK_UP_MS,  # noqa: F401
    AudioLevelMixin,
)
from player.window.main_load import TrackLoadMixin
from player.window.main_pause import PauseMusicMixin, live_target
from player.window.main_pd import PdStopMixin
from player.window.main_play_values import PlayValuesMixin
from player.window.main_presenter import PresenterMixin
from player.window.main_resume import ResumeSessionMixin
from player.window.main_xfade import CrossfadeMixin
from shared.audio.playback import (
    audible_played_secs,
    device_id,
    keep_display_awake,
)
from shared.columns import (
    _COL_TITLE,
    COL_REGEN,
)
from shared.stores import (  # auto-resolved
    player_layout_of,
    save_settings,
)
from shared.widgets import (
    show_toast,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

# The desk's table, named in annotations only: the evening is handed one
# and never builds one, so it must not import the desk at runtime.
if TYPE_CHECKING:
    from gui.table.playlist_table import PlaylistTable

log = logging.getLogger("dancesport.gui.player")

# 🧊 How long the position may stand still while the player says it plays
# before _watch_stall steps in.
_STALL_MS = 5000
# ✕ during music: how long past the last fade's end the window waits, so the
# ramp's final step has landed before the players go.
_QUIT_FADE_MARGIN_MS = 200

class PlayerControlMixin(TrackLoadMixin, PlayValuesMixin, PresenterMixin,
                         AudioLevelMixin, PdStopMixin, PauseMusicMixin,
                         CrossfadeMixin, ResumeSessionMixin):
    """Playing mode itself: the player card, the decks it plays and the clock.

    Levels, the Paso Doble stop, the 🖥 presenter screen, the per-list play
    values and loading a title are their own modules; MainWindow still gets
    all of it from this one name.
    """

    # A stop or a 🛑 hold left the output where the fade took it; the next start
    # puts the level back (see _on_playback_state).
    _level_owed = False

    def _is_playing_mode(self) -> bool:
        return self._left_stack.currentWidget() is self._play_scroll

    # ── 🎧 Pre-listen ─────────────────────────────────────────────────────────

    def _cue_player(self):
        """The 🎧 pre-listen player (AudioDevice owns it), or None."""
        return getattr(getattr(self, "_audio_device", None), "cue", None)

    def _cue_wanted(self) -> bool:
        """A title heard from a pane or a preview window goes to the
        pre-listen player — in either mode — once a pre-listen output is
        chosen ("Same as the music" chooses none)."""
        choice = (self._settings.get("audio_outputs") or {}).get("cue") or {}
        return self._cue_player() is not None and bool(choice.get("id"))

    def _show_cue_view(self, table, row: int, title: str):
        """🎧 The pre-listen's mini player under the row that started it —
        if it does play that title (a refused one doesn't)."""
        cue = self._cue_player()
        if (cue is None or cue.path is None or cue.path.stem != title
                or row < 0 or not self._settings.get("preview_player", True)):
            return
        cue.view.show_for(table, row, title)

    def _cue_skip(self, step: int):
        """⏮/⏭ of the pre-listen's mini player: the event plan's column or
        the library pane — never a deck, which is the hall's music."""
        compare = getattr(self, "_event_compare", None)
        if compare is not None and compare.skip_prehear(step):
            return
        self._lib_browser.skip(step)

    def _prehear_seek(self, delta_ms: int):
        """Ctrl+←/→ where a title is pre-listened (library and 🏆 panes,
        Similar, event plan): the 🎧 title while it plays, else the player
        the preview went to — the deck's, without a pre-listen output."""
        cue = self._cue_player()
        if cue is not None and cue.path is not None:
            cue.seek(delta_ms)
        else:
            self._seek(delta_ms)

    def _prehear(self, path: Path | None, always: bool = False):
        """Play (None: stop) a title from the library pane, the 🏆 pane, the
        Similar window or the event plan. With a pre-listen output it goes
        there and the music keeps running; else on the deck's player, as it
        always did — unless `always`: the two panes keep to the pre-listen
        player and its mini player even then, on the music's output, so
        the main player and its card stay with the deck."""
        cue = self._cue_player()
        if cue is not None and always and not self._cue_wanted():
            if path is None:
                cue.stop()
            else:
                cue.play(path, self._audio_device.target("music"),
                         self._audio_device.pair("music"))
            return
        if cue is None or not self._cue_wanted():
            if cue is not None:
                cue.stop()
            self._play_or_stop(path)
            return
        if path is None:
            cue.stop()
            return
        dev = self._audio_device.cue_device()
        if dev is None:
            return   # not reached: _cue_wanted means an output is chosen
        music = self._audio_device.target("music")
        pair = self._audio_device.pair("cue")
        # 🔀 Another channel pair of the music's card is not the music's.
        if (music is None or (device_id(dev), pair)
                != (device_id(music), self._audio_device.pair("music"))
                or self._audio_device.single_output()):
            # With one output there is no other to choose: it is the default.
            cue.play(path, dev, pair)
            return
        # The music's own output: the preview would go out on the PA.
        if self._audio_device.missing("cue"):
            refused = i18n.t("🎧 The pre-listen output is not connected, and "
                             "the system default is the music's own output.")
        else:
            refused = i18n.t("🎧 Pre-listen refused — its output is the one "
                             "the music plays on. Choose another in ⚙ Settings.")
        cue.stop()
        self._reset_aux_play_markers()
        show_toast(self, refused, 4000, error=True)
        log.warning("%s\n"
                    "title: %s", refused, Path(path).stem)

    def prehear_path(self) -> Path | None:
        """What a preview window's ▶ is heard on right now: the pre-listen
        title while pre-listen is on, else the deck's (see deck_path)."""
        cue = self._cue_player()
        if cue is not None and self._cue_wanted():
            return cue.path
        return self.deck_path()

    # ── ▶ Playing mode, its clock and what plays next ────────────────────────

    def _apply_player_layout(self):
        """Dock the master player where the settings ask for it: at the head of
        the ▶ panel on the left, or as a wide strip above the decks. It is the
        SAME card either way — moved, never rebuilt, so a running title, the
        tempo and the fade all carry across untouched."""
        if not self._big_player:
            return
        wide = player_layout_of(self._settings) == "wide"
        if wide == self._big_player.is_wide():
            return
        self._big_player.setParent(None)   # …out of whichever layout holds it
        self._big_player.set_wide(wide)
        if wide:
            # The panel rides in the strip's middle: the mode is then one band
            # across the top and the decks get the side column's width back.
            self._play_scroll.takeWidget()
            self._play_panel.set_wide(True)
            self._big_player.set_extra_widget(self._play_panel)
            self._right_col.insertWidget(1, self._big_player)   # under the toolbar
            # Above the decks it would otherwise stand there in Planning mode
            # too, where the mini overlay is the player — so it comes and goes
            # with the mode (see _set_play_mode).
            self._big_player.setVisible(self._mode_play_btn.isChecked())
        else:
            self._big_player.set_extra_widget(None)
            self._play_panel.set_wide(False)
            self._play_scroll.setWidget(self._play_panel)
            self._play_panel.set_player_widget(self._big_player)
            self._big_player.setVisible(True)
        self._dock_mode_row()

    def _dock_mode_row(self):
        """Put the 📝/▶ switch where the mode it switches out of can be seen.

        Everywhere but the wide strip that is the head of the left column. In
        the strip the left column is gone while Playing runs, so the switch
        goes into the strip with everything else — and comes back the moment
        Planning needs the column again."""
        playing = self._mode_play_btn.isChecked()
        in_strip = playing and bool(
            self._big_player) and self._big_player.is_wide()
        self._left_box.setVisible(not in_strip)
        if in_strip and self._big_player is not None:
            self._big_player.set_lead_widget(self._mode_row_w)
        else:
            if self._big_player:
                self._big_player.set_lead_widget(None)
            if self._left_col.indexOf(self._mode_row_w) < 0:
                self._left_col.insertWidget(0, self._mode_row_w)
            self._mode_row_w.setVisible(self._mode_switch_shown)

    def _set_play_mode(self, playing: bool):
        self._mode_plan_btn.setChecked(not playing)
        self._mode_play_btn.setChecked(playing)
        self._left_stack.setCurrentWidget(self._play_scroll if playing else self._cfg_scroll)
        if self._big_player and self._big_player.is_wide():
            self._big_player.setVisible(playing)
            self._dock_mode_row()
        for t in self._deckset.all_tables:
            t.set_play_highlight_enabled(playing)
            # No song swapping while a tournament runs — hide the ↺ column.
            t.setColumnHidden(COL_REGEN, playing)
            # Nothing advances outside playing mode, so the corner switch has
            # nothing to say there.
            t.set_advance_toggle_visible(playing)
        if playing:
            # The big player on the left covers everything the mini overlay
            # shows — don't display both.
            if self._preview:
                self._preview.hide()
        else:
            # Leaving Playing mode mid-fade: let the song run on at full volume.
            self._mix.fade = 1.0
            self._apply_volume()
            self._set_countdown("")
            # Back in Planning mode the overlay is the only player UI —
            # re-pop it for whatever is still playing.
            self._sync_preview_to_playback()
        self._settings["play_mode"] = "playing" if playing else "planning"
        save_settings(self._settings)
        self._audio_device.watch_system_sounds()

    def _save_play_settings(self):
        # The set values belong to the list on the panel. The copies below are
        # only what a fresh panel starts on before any list is shown.
        self._store_panel_into_list()
        self._settings["play_secs"] = self._play_panel.play_secs()
        self._settings["fade_secs"] = self._play_panel.fade_secs()
        self._settings["fade_inside"] = self._play_panel.fade_inside()
        # The seconds as set, also while the switch is off — like the pause's.
        self._settings["xfade_secs"] = self._play_panel.xfade_setting_secs()
        self._settings["xfade_on"] = self._play_panel.xfade_on()
        self._settings["xfade_curve"] = self._play_panel.xfade_curve()
        self._settings["timed_enabled"] = self._play_panel.timed_enabled()
        self._settings["auto_advance"] = self._play_panel.auto_advance()
        # The tick as shown, not the effective off of a switched-off
        # auto-advance — so it is still there when ⏭ comes back.
        self._settings["repeat_list"] = self._play_panel.repeat_setting_on()
        self._settings["stop_at_mode"] = self._play_panel.stop_at_mode()
        self._settings["closing_song"] = self._play_panel.closing_song()
        # The configured seconds, not the effective 0 of a switched-off pause —
        # so the number is still there when it's switched back on.
        self._settings["pause_secs"] = self._play_panel.pause_setting_secs()
        self._settings["pause_enabled"] = self._play_panel.pause_enabled()
        # ⏸♪ can only jump into a pause that is going to happen.
        if self._big_player:
            self._big_player.set_pause_available(
                self._engine_pause_available())
        self._settings["loudness_eq"] = self._play_panel.loudness_eq()
        self._settings["pd_highlight_stop"] = self._play_panel.pd_highlight_stop()
        self._settings["pd_highlight_n"] = self._play_panel.pd_highlight_n()
        self._settings["pd_start_delay"] = self._play_panel.pd_start_delay()
        self._settings["announce_next"] = self._play_panel.announce_next()
        # The waveform or the seek bar, never both: no choice left to keep.
        self._settings.pop("replace_seek_bar", None)
        self._settings.pop("hide_seek_bar", None)
        self._settings["dblclick_plays"] = self._play_panel.dblclick_plays()
        self._settings["remember_pos"] = self._play_panel.remember_pos()
        self._settings["presenter_screen"] = self._play_panel.presenter_screen()
        self._settings["presenter_screen_name"] = \
            self._play_panel.presenter_screen_name()
        self._settings["keep_awake"] = self._play_panel.keep_awake()
        self._refresh_wake_lock()
        save_settings(self._settings)
        # Toggling the PD options mid-song must re-arm (or disarm) the stop.
        if self._playback.dance == "PD" and self._playback.path is not None:
            if self._pd_highlight()[0]:
                self._ensure_pd_highlights(self._playback.path)
            else:
                self._pd_stop_at = None
        # Play length / timed toggle changed → refresh the ⏳ display too.
        self._sync_big_player_limit()

    def _stop_play_timer(self):
        """Halt the tick engine, cancel any pending auto-advance and restore
        full volume for the next song."""
        self._fade_timer.stop()
        self._drop_on_air()
        paused = self._between.pending is not None
        self._between.pending = None
        if paused and getattr(self, "_cart_voices", None) is not None:
            self._cart_follow_deck(None)   # 🎶 no Paso Doble is coming now
        self._pd_stop_at = None
        self._fade_now.cancel()
        self._set_fade_indicator(False)
        # The level goes back only when the next song starts (see
        # _on_playback_state): every caller stops the player now, and a full
        # level pushed before that stop lands is heard as a blip after a fade.
        self._mix.fade = 1.0
        self._level_owed = True
        self._set_countdown("")
        if self._big_player:
            self._big_player.set_pause_active(False)

    def _silence_stop_ms(self) -> int | None:
        """Where the 🔇 stillness skip will end the playing track, in ms of
        file time, or None — the probe found no dead air behind the last note
        (or hasn't run yet)."""
        if self._playback.path is None:
            return None
        spans = self._silences.get(str(self._playback.path))
        if not spans:
            return None
        start = trailing_silence_secs(self._track_duration(self._playback.path),
                                      spans)
        return None if start is None else int(start * 1000)

    def _sync_big_player_limit(self):
        """Tell the big player where playback will ACTUALLY end — ⏳ timed cut,
        🔇 dead air behind the last note, or 🐂 PD highlight stop — so it shows
        the adjusted track time next to the full length and counts down to it."""
        if not self._big_player:
            return
        fade_at = None      # 〰 where the timed cut's fade-out begins, file ms
        if self._celebrating():
            # 🥇 Past its cut the title plays on to the file's end: no cut and
            # no fade left to mark, the bar and the waveform span all of it.
            self._big_player.set_limit(None, "trophy", to_end=True)
            self._big_player.set_pd_marks(self._unarmed_pd_marks())
        elif self._pd_runs_to_its_highlight():
            # Auto-detection leaves None where a highlight wasn't found.
            hl = [t for t in (self._pd_highlights.get(str(self._playback.path))
                              or []) if t] \
                if self._playback.path is not None else []
            # A stop standing in for an undetected highlight isn't in that list
            # — draw it too, so the bar always shows what will actually fire.
            if (self._pd_stop_at is not None
                    and not any(abs(t - self._pd_stop_at) < 0.5 for t in hl)):
                hl = sorted(hl + [self._pd_stop_at])
            self._big_player.set_pd_marks(hl, self._pd_stop_at)
            if self._pd_stop_at is not None:
                self._big_player.set_limit(int(self._pd_stop_at * 1000), "highlight")
            else:
                # The stop is on but it lands on the song's own end (finale
                # highlight at the end) → keep the 🐂 sand clock, "plays through".
                self._big_player.set_limit(None, "highlight", to_end=True)
        elif (self._playback.path is not None
                and self._play_limit_secs() > 0):
            # Same arithmetic as the tick's cut, inverted: the play length is
            # wall-clock music, so in FILE time it stretches with the tempo rate
            # and sits after whatever silence was skipped.
            rate = (self._player.playbackRate()
                    if self._player else 1.0)
            end_ms = (self._play_end_secs() * max(0.01, rate) * 1000
                      + self._playback.offset_ms)
            # Dead air can fall BEFORE the cut — then the song ends there, and
            # the countdown has to say so. Whichever comes first wins.
            sil_ms = self._silence_stop_ms()
            if sil_ms is not None and sil_ms < end_ms:
                self._big_player.set_limit(sil_ms, "mute")
            elif self._celebration_due():
                # 🥇 …and after the cut it comes back up: say so beside it.
                self._big_player.set_limit(int(end_ms), then="trophy")
            else:
                self._big_player.set_limit(int(end_ms))
            # A PD played in full shows its highlights, nothing armed.
            self._big_player.set_pd_marks(self._unarmed_pd_marks())
            # The tick fades over the last `fade` wall-clock seconds.
            fade = float(self._pv("fade"))
            if fade > 0:
                fade_at = int(end_ms - fade * max(0.01, rate) * 1000)
        else:
            sil_ms = self._silence_stop_ms()
            if sil_ms is not None:
                self._big_player.set_limit(sil_ms, "mute")
            else:
                self._big_player.set_limit(None)
            self._big_player.set_pd_marks(self._unarmed_pd_marks())
        spans = (self._silences.get(str(self._playback.path))
                 if self._playback.path is not None else None)
        # ⏩ Where the title starts: what was skipped, and a pre-roll still
        # owed until the media is open. 🌅 Its fade-in runs on from there,
        # in music heard, so in file time it stretches with the tempo too.
        start_ms = self._playback.offset_ms + self._playback.pre_roll_ms
        fade_in_end = None
        if self._playback.fade_in_secs > 0:
            rate = self._player.playbackRate() if self._player else 1.0
            fade_in_end = int(start_ms + self._playback.fade_in_secs
                              * max(0.01, rate) * 1000)
        self._big_player.set_wave_overlay(spans or [], fade_at, start_ms,
                                          fade_in_end)

    def _next_song_to_advance(self) -> tuple[PlaylistTable, int, Path] | None:
        """(table, row, path) of the song AFTER the one currently playing, or
        None. Must be resolved BEFORE the play buttons are reset — afterwards
        no table remembers which row was active."""
        for t in self._deckset.all_tables:
            row = t._current_play_row
            if row < 0:
                continue
            if self._looping():
                m = t._row_meta.at(row)
                if m is not None and m.entry is not None:
                    return t, row, m.entry.path
            nrow, npath = t.next_song_row(row, +1)
            if nrow >= 0 and npath:
                return t, nrow, npath
            return self._list_starts_again(t)
        return None

    def _looping(self) -> bool:
        """🔁 on the player card: this title starts again instead of whatever
        would otherwise follow it."""
        return self._big_player is not None and self._big_player.loop_mode()

    def _list_starts_again(self, t) -> tuple[PlaylistTable, int, Path] | None:
        """The list has run out: with 🔁 on, its own first song is what comes
        next. Off — the tournament case — nothing does.

        Not `repeat_list()`: that ANDs the panel's auto-advance, and the deck
        this list is on may have an answer of its own."""
        if not (self._play_panel.repeat_setting_on() and self._deck_advance(t)):
            return None
        nrow, npath = t.next_song_row(-1, +1)
        if nrow < 0 or not npath:
            return None
        return t, nrow, npath

    def _refresh_next_up(self):
        """Put what comes AFTER the running song on the big player card — and
        warn one song early when the round ends here, instead of only flashing
        🏁 once it is already over."""
        if not self._big_player:
            return
        # ⏹ A planned stop at the end of this title is what comes next.
        stop = self._play_panel.stop_text()
        if stop and self._play_panel.stop_due(
                datetime.now() + timedelta(seconds=self._music_left() or 0)):
            self._big_player.set_next_up(i18n.t("⏹  Stops after this title"))
            return
        tail = f"  ·  {stop}" if stop else ""
        # During the auto-advance pause nothing is "playing", so no table can
        # resolve a follower — the armed advance IS the next song.
        nxt = self._next_song_to_advance() or live_target(self._between.pending)
        if nxt is None:
            self._big_player.set_next_up(stop)
            return
        t, nrow, npath = nxt
        if self._looping():
            # Nothing "comes after" a looping title — it comes again.
            self._big_player.set_next_up(f"🔁  {npath.stem}  ·  again{tail}")
            return
        row = t._current_play_row
        nmeta = t._row_meta.at(nrow)
        cur = t._row_meta.at(row)
        # Same reading as in _queue_auto_advance: a follower ABOVE the
        # running title is the list starting over, not a round ending.
        if (nmeta is not None and cur is not None
                and nrow > row and cur.round_name != nmeta.round_name):
            self._big_player.set_next_up(f"🏁  {terms.round_name(cur.round_name) or 'Round'} ends here")
            return
        code = nmeta.dance if nmeta is not None else ""
        dance = dance_name(code, code)
        self._big_player.set_next_up(
            (f"⏭  {dance}  ·  {npath.stem}" if dance else f"⏭  {npath.stem}") + tail)

    def _set_artwork_shown(self, on: bool):
        """🖼 in ⚙ Settings → cover on the player card."""
        if self._big_player:
            self._big_player.set_artwork_enabled(on)

    def _set_waveform_shown(self, on: bool):
        """〰 in ⚙ Settings → waveform in place of the card's seek bar."""
        if self._big_player:
            self._big_player.set_waveform_enabled(on)

    def _set_vol_buttons_shown(self, on: bool):
        """− / + in ⚙ Settings → beside the card's volume slider and the
        cartwall's (built later at start, which applies it itself)."""
        if self._big_player:
            self._big_player.set_vol_buttons_shown(on)
        if getattr(self, "_cartwall", None) is not None:
            self._cartwall.set_vol_buttons_shown(on)

    def _set_button_scale(self, pct: int):
        """🔘 The button size in ⚙ Settings → the player card's ⏮ ⏯ ⏭, the ▶
        panel's switches and both mini players' ✕ ⏮ ⏭."""
        if self._big_player:
            self._big_player.set_button_scale(pct)
        self._play_panel.set_button_scale(pct)
        cue = self._cue_player()
        for view in (self._preview, getattr(cue, "view", None)):
            if view is not None:
                view.set_button_scale(pct)

    def _set_time_format(self, fmt: str | None):
        """⏱ in ⚙ Settings → how a title over an hour reads on the player and
        the mini player; the labels pick it up on their next tick."""
        set_time_format(fmt)

    def _playing_m3u(self) -> Path | None:
        """The .m3u the running deck was imported from, if it was — its own
        picture beats the cover of whatever CD the track came off."""
        for t in self._deckset.all_tables:
            if t._current_play_row >= 0:
                return getattr(t, "_m3u_path", None)
        return None

    def _focus_next_song(self):
        """Put the cursor on the song that comes next.

        With auto-advance off nothing starts by itself, so the operator has to
        find the next row and press play on it — the one moment they are busy
        watching the floor. Selecting it (and scrolling it into view) means the
        row is already under the finger, exactly as the 🏁 end-of-round case
        does. Nothing is played; the end cues it (see _cue_next_song).
        """
        nxt = self._next_song_to_advance()
        if nxt is None:
            return
        t, nrow, _npath = nxt
        t.setCurrentCell(nrow, _COL_TITLE)   # scrolls it into view by itself
        self._between.cue_next = nxt

    def _cue_next_song(self):
        """Load the title `_focus_next_song` picked — on the card, silent — so
        ⏯ starts it. Called once the end has released the old title: cued
        before that, the end would unload it again.

        🌙 After a planned stop with a closing song, that song plays first;
        the next title keeps waiting and is cued when the song ends."""
        closing, self._between.closing = self._between.closing, None
        if closing is not None:
            self._playback.closing = closing
            log.info("🌙 Closing song\n"
                     "file: %s", closing.name)
            self._play_or_stop(closing)
            return
        nxt = live_target(self._between.cue_next)
        self._between.cue_next = None
        if nxt is None:
            return
        t, nrow, npath = nxt
        self._play_or_stop(npath, start=False)
        t.cue_row(nrow, scroll=False)

    def _queue_auto_advance(self):
        """Arm the between-songs pause if Playing mode + auto-advance are on.

        Auto-advance as the PLAYING deck has it — every list carries its own
        answer (see `_deck_advance`)."""
        if self._closing_on_air():
            # 🌙 The closing song has ended: the title the stop put under the
            # cursor is still waiting — `_cue_next_song` cues it now.
            self._playback.closing = None
            return
        self._between.cue_next = None
        if not self._is_playing_mode():
            return
        advancing = self._playing_advance()
        # 🔁 holds the evening on ONE title. That is not the list walking on, so
        # it does not wait for the switch that walks it.
        if not self._looping() and not advancing:
            self._focus_next_song()
            return
        # ⏹ The planned stop. A 🔀 crossfade has already brought the next
        # title in: that end still counts, but it cannot stop anything.
        crossfading = self._between.xfade.state == "fading"
        if self._play_panel.stop_title_ended(datetime.now(), can_stop=not crossfading):
            self._set_countdown(i18n.t("⏹  Stopped as planned"))
            self._focus_next_song()
            closing = self._between.closing = self._closing_song_path()
            self.statusBar().showMessage(
                i18n.t("⏹ Stopped as planned — 🌙 the closing song plays, then ⏯ the next title.")
                if closing is not None else
                i18n.t("⏹ Stopped as planned — ⏯ plays the next title."), 8000)
            log.info("⏹ Stopped as planned\n"
                     "closing song: %s\n"
                     "next title cued, waiting for ⏯",
                     closing.name if closing is not None else "none")
            return
        nxt = self._next_song_to_advance()
        if nxt is None:
            return
        t, nrow, _npath = nxt
        row = t._current_play_row
        cur, nxt_meta = t._row_meta.at(row), t._row_meta.at(nrow)
        if cur is not None and nxt_meta is not None:
            cur_round = cur.round_name
            # `nrow > row` is what tells a round change from a 🔁 start-over:
            # the latter lands ABOVE the finished title and is the end of the
            # whole list, not the seam between two rounds.
            if nrow > row and cur_round != nxt_meta.round_name:
                # 🏁 The round is over — tournament flow: the couples change,
                # the operator starts the next round manually.
                rn = cur_round or i18n.t("Round")
                self._set_countdown(i18n.t("🏁  %s finished") % rn)
                self.statusBar().showMessage(
                    i18n.t("🏁 %s finished — auto-advance stopped.") % rn, 8000)
                # ⏯ on the big player picks up here with the next round.
                self._between.round_start = nxt
                # Point the operator at what comes next: focus + flash the
                # following round's header and its first song row.
                t.setCurrentCell(nrow, _COL_TITLE)
                hdr = t._row_round_hdr.get(nrow, -1)   # -1 = 🚫 no-grouping view
                flash = [hdr, nrow] if hdr >= 0 else [nrow]
                t.flash_rows(flash, QColor(187, 222, 251))
                return
        self._between.pending = nxt
        self._between.round_start = None
        self._between.announced = False   # one spoken cue per pause
        self._between.quiet_until = 0.0   # …and the quiet the hall gets after it
        # Both halves, not the seconds alone: 🔁 can reach this line with ⏭
        # auto-advance off, and the panel calls a pause impossible in that
        # state — so a gap here would be one the app says does not exist.
        # `pause_available()` asks the panel's switch; this deck's is what
        # counts.
        gap = self._engine_pause_secs() if advancing else 0
        self._between.advance_at = time.monotonic() + gap
        self._between.shown = gap > 0   # 🖥 worth showing
        if self._big_player:
            self._big_player.set_pause_active(True)   # show ⏱➕ extend
        # ⏩ Preload: hand the next file to the backend NOW, so the end of the
        # pause is a bare play() instead of a full open-and-probe of the file
        # (the WMF backend takes a noticeable moment for that).
        if self._player:
            url = self._source_url(nxt[2])
            if self._player.source() != url:   # 🔀 a crossfade opened it already
                self._player.setSource(url)
        # …and measure its loudness in the same breath, if nobody ever did: the
        # pause is exactly the room for that decode, so the advance itself never
        # has to hold the next title back to get its level right.
        self._await_loudness(Path(nxt[2]), False)
        if getattr(self, "_cart_voices", None) is not None:
            self._start_pause_pads()   # ▶ the wall's 🎶 queue fills the pause
            self._cart_follow_deck(None)   # 🎶 a Paso Doble next keeps the bed down
        self._fade_timer.start()

    def _set_countdown(self, text: str):
        """Show the countdown/status on the left Playing panel; mirror it onto
        the big-player card ONLY during the between-songs pause — nothing
        sounds then, and the card is where the desk looks. The 🐂 wait before
        a Paso Doble has its own place there (`set_wait`). In normal play the
        panel's sand clock + the card's adjusted-time line already cover it,
        so a card countdown would double the ⏳."""
        self._play_panel.set_countdown(text)
        if self._big_player:
            self._big_player.set_countdown(
                text if self._between.pending is not None else "")

    def _fire_pending_advance(self):
        """End the between-songs pause now and start the queued next song."""
        if self._between.pending is None:
            return
        nxt = live_target(self._between.pending)
        self._between.pending = None
        if self._big_player:
            self._big_player.set_pause_active(False)
        if nxt is None:
            # Its title was taken out of the deck during the pause — whatever
            # sits on the old row now is not what the hall was told comes next.
            self.statusBar().showMessage(
                "⏹ The next title was removed during the pause — nothing "
                "was started.", 8000)
            return
        t, nrow, npath = nxt
        t._on_play_click(nrow, npath)   # handles the ▶/■ markers + playback
        t.scroll_row_into_play_view(nrow)

    def _on_player_next(self):
        """⏭ on the big player: during a running auto-advance pause, skip the
        rest of the pause and start the next song; the wall's 🎶 beds dip
        under it on their own. A call still to come is kept: the pause only
        runs up to it (`_skip_to_call`). Outside a pause, just step the deck
        to the next row."""
        if self._between.pending is not None:
            if self._skip_to_call():
                return
            self._announcer.stop()   # the cue was for THIS pause, which is over
            self._fire_pending_advance()
            return
        if self._crossfade_skip():   # 🔀 fades into the next title instead
            return
        self._preview_skip(+1)

    def _set_fade_indicator(self, on: bool):
        """Blink the big player orange while a fade-out ramps the song down --
        a fade is otherwise a silent thing to watch happen."""
        if self._big_player:
            self._big_player.set_fading(on)

    def _fade_out_now(self):
        """🔉↓ on the big player: ramp the playing song to silence over the
        configured fade time, then end it like a timed cut. In planning mode
        too: the 📱 phone has the button whichever side the desk shows."""
        if (self._playback.path is None
                or self._player is None
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        if self._fade_now.running:
            # A second press must not restart the ramp: that put the volume
            # back to full. On a 🛑 ramp it only turns the hold into an end.
            self._fade_now.hold = False
            return
        if self._celebrating():
            # 🥇 A final's title playing on goes down over its own seconds,
            # all of them, from the level it plays at.
            level = max(0.01, self._mix.fade)
            self._fade_now.start(celebrate_down_secs(self._settings) / level,
                                 level=level)
        else:
            self._fade_now.start(hand_fade_secs(self._settings, self._pv("fade")),
                                 level=self._mix.fade)
        self._set_fade_indicator(True)
        self._fade_timer.start()   # make sure the tick is running to drive it

    def _fade_and_hold(self):
        """🛑 on the big player: ramp the song to silence over the fade time and
        PAUSE it there. Unlike 🔉↓ nothing ends and nothing advances — ⏯ picks
        the song back up at exactly the spot it went quiet. For an announcement
        or an incident on the floor, where the round must continue afterwards."""
        if (self._player is None or self._playback.path is None
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        if self._fade_now.running:
            return   # a fade is already running — don't restart the ramp
        self._fade_now.start(hand_fade_secs(self._settings, self._pv("fade")),
                             hold=True, level=self._mix.fade)
        log.info("🛑 Panic fade — holding playback in place\n"
                 "file: %s\n"
                 "fade: %.1fs", self._playback.path.name, self._fade_now.total)
        self._set_fade_indicator(True)
        self._fade_timer.start()

    def _mark_cued_row(self, path, scroll: bool = True) -> bool:
        """Point the playing-row marker at the deck row holding `path` (clearing
        every other deck's marker first), so ⏭ / ⏮ continue through that playlist
        after a track is cued on the big player by drag-drop. Returns True when a
        matching deck row was found; external (non-library) drops leave no marker.

        scroll=False marks the row without bringing it into view — for a cue the
        operator did not ask for, which must not pull the deck away from the spot
        they are working in."""
        target = str(path)
        hit_table = None
        hit_row = -1
        for t in self._deckset.all_tables:
            for r, m in t._row_meta.numbered():
                if str(getattr(m.entry, "path", "")) == target:
                    hit_table, hit_row = t, r
                    break
            if hit_table is not None:
                break
        # One playing deck at a time: clear stale markers on every other deck.
        for t in self._deckset.all_tables:
            if t is not hit_table and t._current_play_row >= 0:
                t.on_playback_stopped()
        if hit_table is None:
            return False
        hit_table.cue_row(hit_row, scroll)
        return True

    def _on_player_drop(self, path_str: str):
        """A track dropped onto the big-player card → cue it (load + show) but
        don't auto-start; the user presses ⏯ to play. If the track came from a
        deck, mark that deck row as current so ⏭ / ⏮ keep walking the playlist."""
        if not path_str:
            return
        p = Path(path_str)
        if resolve_file(p, self._settings) is None:
            self.statusBar().showMessage(i18n.t("Can't cue — file not found: %s") % p.name,
                                         5000)
            return
        self._play_or_stop(p, start=False)
        from_deck = self._mark_cued_row(p)
        msg = (i18n.t("⏸ Cued %s — press ⏯ to play. — ⏭ walks the playlist") if from_deck
               else i18n.t("⏸ Cued %s — press ⏯ to play."))
        self.statusBar().showMessage(msg % p.name, 4000)

    def _on_play_tick(self):
        """200 ms heartbeat while a song is playing: drives the countdown, the
        fade-out ramp over the last N seconds, and the stop at play length."""
        if not self._player:
            return
        # Between-songs pause: count down, then fire the queued next song.
        if self._between.pending is not None:
            self._between_tick(self._player, self._between.pending)
            return
        # 🔇 Stillness skip — in EVERY mode (preview too): jump over silent
        # stretches, end the song when only dead air is left. Deliberate fades
        # (🔉↓) keep priority — no skipping mid-fade.
        if (self._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
                and not self._fade_now.running
                and self._maybe_skip_silence()):
            return
        if (self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        if self._watch_stall():
            return
        self._step_fade_in()
        # Manual "fade out now" (🔉↓): ramp to silence, then end like a timed
        # cut. Takes priority over the normal timed/PD logic below. On either
        # side of the desk: the 📱 phone sends it whichever one is showing.
        if self._fade_now.running:
            hold = self._fade_now.hold
            remaining = self._fade_now.remaining()
            if remaining <= 0:
                self._fade_now.cancel()
                self._set_fade_indicator(False)
                if hold:
                    # 🛑 Panic: stay on this song at this position. ⏯ resumes at
                    # the normal level — pushed when it runs again, not here:
                    # the pause lands late and the buffer would play it loud.
                    self._fade_now.hold = False
                    self._player.pause()
                    # 🔀 A fading title holds now, not when the pause lands:
                    # its next ramp step would push the whole level below.
                    self._xfade_follow(QMediaPlayer.PlaybackState.PausedState)
                    self._mix.fade = 1.0
                    self._level_owed = True
                    self._set_countdown("🛑  held")
                    return
                self._on_timed_end("fade-out finished")
                return
            self._mix.fade = self._fade_now.level(remaining)
            self._apply_volume()
            self._set_countdown(f"{'🛑' if hold else '🔉↓'}  {remaining:.0f} s")
            return
        if not self._is_playing_mode():
            return
        if self._closing_tick():
            return
        self._note_on_air()
        # Grey the track once it has truly been heard for >10 s (any dance):
        # not silence skipped over, nor the ground a ↩ resume jumped past.
        if (not self._played_marked
                and self._playback.path is not None
                and audible_played_secs(self._player.position(),
                                        self._playback.offset_ms,
                                        self._player.playbackRate())
                >= self._PLAYED_AFTER_MS / 1000):
            self._played_marked = True
            self._mark_path_played(self._playback.path)
            self._log_play(self._playback.path)
            self._note_session()   # ▶ for picking the evening up after a crash
        # ⏹ An "At …" stop set to fade: the time has come, so the title on air
        # fades out now — its end is then the planned stop. Not while a
        # crossfade has the next title coming in already.
        if (self._between.xfade.state != "fading"
                and self._play_panel.stop_fade_due(
                    datetime.now(),
                    audible_played_secs(self._player.position(),
                                        self._playback.offset_ms,
                                        self._player.playbackRate()))):
            self._fade_out_now()
            return
        if self._celebration_tick():
            return
        # 🔀 Near the end of a title the list walks straight on from, the next
        # one comes in under it. The tick goes on below: until the tail player
        # takes over, the running title keeps its own fade and cut.
        self._maybe_crossfade()
        if self._pd_runs_to_its_highlight():
            self._pd_tick(self._player)
            return
        if not self._play_limit_secs() > 0:
            if self._mix.fade != 1.0:   # toggled off mid-fade → ramp back up
                self._mix.fade = 1.0
                self._apply_volume()
            self._set_countdown("")
            return
        limit = self._play_end_secs()
        fade = float(self._pv("fade"))
        # Wall-clock music heard so far: skipped silence doesn't count and the
        # tempo fader is divided out, so "1:45" is 1:45 on the floor.
        played = audible_played_secs(self._player.position(),
                                     self._playback.offset_ms,
                                     self._player.playbackRate())
        remaining = limit - played
        if remaining <= 0:
            # 🥇 …unless a title of the final comes back up instead.
            if not self._begin_celebration():
                self._on_timed_end("play length reached")
            return
        x = min(1.0, remaining / fade) if fade > 0 else 1.0
        # 🥇 A title that comes back up is faded only down to its dip.
        floor = self._cut_fade_floor() if x < 1.0 else 0.0
        self._mix.fade = floor + (1.0 - floor) * x
        self._apply_volume()
        r = int(remaining + 0.999)
        self._set_countdown(f"⏳  {r // 60}:{r % 60:02d}")

    def _celebration_due(self) -> bool:
        """🥇 Does the title playing come back up after its play-length fade?
        Only under ✋ Manual: under ⏭ Auto the ⏸ pause and its music follow
        each title, so it ends as always."""
        mode = celebrate_mode(self._settings)
        if (mode == "off" or self._playback.path is None
                or self._player is None or self._looping()
                or self._playing_advance()):
            return False
        t, row = self._playing_row()
        if t is None or t._row_meta.at(row) is None:
            return False
        # By `round_at`: an imported running order names its rounds in the
        # ─── strips, not on the rows.
        rnd = t.round_at(row)
        nrow, _npath = t.next_song_row(row, +1)
        last = nrow < 0 or t._row_meta.at(nrow) is None or t.round_at(nrow) != rnd
        return celebrates(mode, rnd, last)

    def _cut_fade_floor(self) -> float:
        """🥇 How low the play-length fade takes the title playing (0…1): to
        its dip, where it comes back up afterwards, else all the way."""
        if not self._celebration_due():
            return 0.0
        return celebrate_dip_pct(self._settings) / 100.0

    def _begin_celebration(self) -> bool:
        """🥇 The play length has faded a title out: does it come back up?

        True = it plays on right here until 🔉↓ fades it, the next title
        starts or its file ends."""
        if not self._celebration_due():
            return False
        path = self._playback.path
        self._playback.celebrate = (self._playback.token, time.monotonic())
        log.info("🥇 The final's title plays on\n"
                 "file: %s", path.name if path else "?")
        self._sync_big_player_limit()   # the card runs on to the file's end
        return True

    def _closing_song_path(self) -> Path | None:
        """🌙 The closing song set on the ▶ panel, if its file is there."""
        raw = self._play_panel.closing_song()
        if not raw:
            return None
        if resolve_file(raw, self._settings) is None:
            log.warning("🌙 Closing song not found\n"
                        "file: %s", raw)
            self.statusBar().showMessage(
                i18n.t("🌙 Closing song not found: %s") % Path(raw).name, 8000)
            return None
        return Path(raw)

    def _closing_on_air(self) -> bool:
        """🌙 The closing song is the deck's title."""
        c = self._playback.closing
        return c is not None and c == self._playback.path

    def _closing_tick(self) -> bool:
        """🌙 One tick of the closing song: at the music's level, the
        countdown running to its file's end. True while it plays — no play
        length, no "played" mark, no stop rule applies to it."""
        player = self._player
        if not self._closing_on_air() or player is None:
            return False
        if self._mix.fade != 1.0:
            self._mix.fade = 1.0
            self._apply_volume()
        left = max(0, player.duration() - player.position()) / 1000.0
        r = int(left / max(0.01, player.playbackRate()) + 0.999)
        self._set_countdown(f"🌙  {r // 60}:{r % 60:02d}")
        return True

    def _celebrating(self) -> bool:
        """🥇 A title of the final is playing on after its fade."""
        c = self._playback.celebrate
        return c is not None and c[0] == self._playback.token

    def _celebration_tick(self) -> bool:
        """🥇 One tick of a final's title playing on: it comes back up to its
        level and stays there, the countdown runs to its file's end. True
        while one runs — it owns the level, no play length applies."""
        c, player = self._playback.celebrate, self._player
        if c is None or c[0] != self._playback.token or player is None:
            return False
        self._mix.fade = celebrate_level(
            time.monotonic() - c[1],
            celebrate_up_secs(self._settings), celebrate_pct(self._settings),
            celebrate_dip_pct(self._settings),
            celebrate_hold_secs(self._settings))
        self._apply_volume()
        left = max(0, player.duration() - player.position()) / 1000.0
        r = int(left / max(0.01, player.playbackRate()) + 0.999)
        self._set_countdown(f"🥇  {r // 60}:{r % 60:02d}")
        return True

    def _watch_stall(self) -> bool:
        """Playing, but the position has not moved for _STALL_MS — a decoder
        hang, the output device gone. The title is reloaded where it stood and
        the operator told; a second stall of the same title gives it up like
        one that would not play (→ the next title of a running round). True
        when it stepped in."""
        player = self._player
        if player is None:
            return False
        pb = self._playback
        token, pos, now = pb.token, player.position(), time.monotonic()
        seen_token, seen_pos, since = pb.stall_seen
        if token != seen_token or pos != seen_pos:
            pb.stall_seen = (token, pos, now)
            return False
        path = pb.path
        if 1000 * (now - since) < _STALL_MS or path is None:
            return False
        pb.stall_seen = (None, 0, 0.0)
        if pb.stall_reloaded == token:
            log.error("🧊 Playback stalled again — giving up\n"
                      "file: %s", path)
            self._playback_failed(path, i18n.t("stalled"),
                                  i18n.t("⚠ Could not play: %s") % path.name)
            return True
        pb.stall_reloaded = token
        at = f"{pos // 60_000}:{pos // 1000 % 60:02d}"
        log.warning("🧊 Playback stalled — reloading\n"
                    "file: %s\n"
                    "at: %s", path, at)
        show_toast(self, i18n.t("⚠ Playback stalled — “%s” reloaded at %s.")
                    % (path.stem, at), error=True)
        player.stop()
        player.setSource(QUrl())
        # ↩ The seek waits for the media (see _on_media_status), which books it
        # as skipped ground. This ground was heard: the ⏳ play length goes on.
        pb.offset_ms -= pos
        self._resume_seek_ms = pos
        player.setSource(self._source_url(path))
        player.play()
        return True

    def _between_tick(self, player, pending):
        """⏸ The pause between two songs: its countdown, fade and advance."""
        # The deck the pause is running for, not the panel: its own switch
        # is what armed this, so its own switch is what can call it off —
        # unless 🔁 armed it, which never asked that switch (see
        # _queue_auto_advance).
        if (not self._is_playing_mode()
                or not (self._deck_advance(pending[0]) or self._looping())):
            self._stop_play_timer()   # turned off during the pause → cancel
            player.setSource(QUrl())   # release the preloaded file
            self._set_fade_indicator(False)   # no ⏭ ramp runs on into nothing
            return
        # 🔉 The quit fade: the wall's beds go down, no next title follows.
        if self._fade_now.quitting:
            return
        remaining = self._between.advance_at - time.monotonic()
        if remaining > 0:
            if remaining <= self._announce_lead():
                self._maybe_announce_next()
            r = int(remaining + 0.999)
            self._set_countdown(f"⏸  {r} s")
            return
        if self._hold_for_announcement():
            return
        self._fire_pending_advance()

    def _pd_tick(self, player):
        """🐂 A Paso Doble danced to its highlights: no fade, only the stop."""
        # Under the 🐂 stop a Paso Doble is never faded and never cut at
        # the play length — it is danced to its highlights. Only the armed
        # highlight stop (or the natural end) may end it.
        if self._mix.fade != 1.0:
            self._mix.fade = 1.0
            self._apply_volume()
        if self._pd_stop_at is not None:
            pos = player.position() / 1000.0
            # The mark is a fixed musical spot in the file, so the STOP is
            # compared against the raw position — but how long until the gong
            # is wall-clock, hence the tempo rate on the countdown only.
            remaining = self._pd_stop_at - pos
            if remaining <= 0:
                if self._pd_verify_stop:
                    # ✔ Just left edit mode: pause ON the mark so it can be
                    # checked by ear instead of advancing to the next title.
                    self._pd_verify_stop = False
                    player.pause()
                    self._set_countdown("🎯  stop reached — ⏯ to go on")
                    return
                self._on_timed_end("PD highlight stop")
                return
            remaining /= max(0.01, player.playbackRate())
            r = int(remaining + 0.999)
            tag = ("🎯" if (self._library.cache and self._playback.path
                            and self._library.cache.is_pd_manual(self._playback.path))
                   else "🐂")
            self._set_countdown(f"{tag}  {r // 60}:{r % 60:02d}")
        elif (self._pd_worker is not None
                and self._pd_worker.isRunning()):
            self._set_countdown("🐂  detecting highlights…")
        else:
            self._set_countdown("🐂  plays to the end")

    def _mark_path_played(self, path: Path):
        """Grey this track in every deck that holds a copy of it."""
        for t in self._deckset.all_tables:
            t.mark_path_played(str(path))

    def _log_play(self, path: Path):
        """📜 Put a title heard in playing mode into the play log — called at
        the same point it greys, so once per play. Pre-listening in planning
        mode is not a play; a desk without a database logs nothing."""
        if self._library.cache is None or self._player is None or not self._is_playing_mode():
            return
        deck = next((t for t in self._deckset.all_tables if t._current_play_row >= 0), None)
        meta = deck._row_meta[deck._current_play_row] if deck else None
        ent = meta.entry if meta else None
        if ent is None or Path(ent.path) != Path(path):
            # Played from a dialog or a file: no row knows more than the name.
            deck, ent = None, None
        heard = audible_played_secs(self._player.position(), self._playback.offset_ms,
                                    self._player.playbackRate())
        started = datetime.now() - timedelta(seconds=heard)
        try:
            play_log.record(
                started, path,
                (ent.tag_artist or "") if ent else "",
                ent.title if ent else Path(path).stem,
                self._playback.dance, self.deck(deck).title if deck else "",
                ent.duration if ent else 0, composer=play_log.composer_of(path))
        except sqlite3.Error as exc:
            log.warning("📜 Play not logged\n"
                        "file: %s\n"
                        "error: %s", path, exc)
        else:
            play_counts.bump(path, started)
            self._refresh_play_counts()

    def _refresh_play_counts(self):
        """🔁 Every list's Plays column, after a play or a reset."""
        for t in self._deckset.all_tables:
            t.refresh_play_counts()
        self._lib_browser.refresh_play_counts()
        self._tourney_tree.refresh_play_counts()

    def _load_play_counts(self):
        """🔁 Count the last day's plays off the log, once the database is there."""
        try:
            play_counts.load()
        except sqlite3.Error as exc:
            log.warning("🔁 Play counts not read\n"
                        "error: %s", exc)
            return
        self._refresh_play_counts()

    def _reset_play_counts(self):
        """🔁 The header menu's reset: every counter back to zero. The play
        log, the report for the music rights society, stays as it is."""
        try:
            play_counts.reset()
        except sqlite3.Error as exc:
            log.warning("🔁 Play counter reset not saved\n"
                        "error: %s", exc)
        self._refresh_play_counts()

    def _equalize_heat_tempo(self, auto: bool = False) -> bool:
        """TSO button on the player: pitch the playing title to the average
        tempo of its dance in the current round, clamped to the TSO range.
        auto=True (TSO toggle on / each new track) stays silent on the
        'nothing playing' cases so it doesn't nag between titles.

        Returns whether a tempo was actually set — `_load_track` pitches before
        it starts the music and needs to know whether to try again afterwards.
        """
        if not self._big_player or self._playback.path is None:
            if not auto:
                self.statusBar().showMessage(
                    terms.rules_name(i18n.t(
                        "Play a title first — then TSO sets its heat tempo."),
                        short=True), 4000)
            return False
        # The deck that is actually playing (the one with a marked ▶/■ row).
        deck = next((t for t in self._deckset.all_tables
                     if t._current_play_row >= 0), None)
        if deck is None or not (0 <= deck._current_play_row < len(deck._row_meta)):
            if not auto:
                self.statusBar().showMessage("No playing row found.", 4000)
            return False
        meta = deck._row_meta[deck._current_play_row]
        ent = meta.entry
        if ent is None or not getattr(ent, "bpm", 0):
            if not auto:
                self.statusBar().showMessage(
                    "This title has no detected tempo — can't equalize.", 5000)
            return False
        dance = ent.dance
        row = deck._current_play_row
        hdr = round_strip(deck, row)
        counts, danced_at, target = tso_target(
            round_takte(deck, row, dance), dance, ent.bpm,
            tso_band_of(self._settings, dance))
        played_at = self._big_player.set_tempo_to_target(target)
        if played_at is None:
            if not auto:
                self.statusBar().showMessage(
                    "The fader can't reach that tempo for this title.", 5000)
            return False
        takte = "+".join(f"T{b}×{n}" for b, n in sorted(counts.items()))
        # What the button read the round as. A target nobody expected is always
        # a disagreement about WHICH titles it counted — a takt that never made
        # it into a filename, a title the round header does not cover — and the
        # status line is gone in six seconds.
        # The strip heads a running order with the round it could work out —
        # the row itself has no name for it, and "round: —" was what gave the
        # whole-deck count away the first time.
        hdr_item = deck.item(hdr, 0) if hdr is not None and hdr >= 0 else None
        heading = (hdr_item.text().strip(" ─") if hdr_item else "")
        log.info("🎚 TSO pitched a title\n"
                 "dance: %s\n"
                 "round: %s\n"
                 "takte: %s\n"
                 "danced at: T%s\n"
                 "target: T%s\n"
                 "playing: T%s → T%s (%s)",
                 dance, meta.round_name or heading or "—", takte or "—",
                 takt_text(danced_at),
                 takt_text(target), ent.bpm, takt_text(played_at),
                 ent.title or ent.path.name)
        src = (i18n.t("the %s %s of this round") % (takte, dance_name(dance, dance))
               if len(counts) > 1 else i18n.t("this %s") % dance_name(dance, dance))
        self.statusBar().showMessage(
            terms.rules_name(i18n.t("🎚 TSO tempo: %s %s → T%s (target T%s from %s)"),
                             short=True)
            % (dance, ent.bpm, takt_text(played_at), takt_text(target), src), 6000)
        return True

    def _on_timed_end(self, reason: str = "play length"):
        """Play length reached — stop the song like a natural end.

        `reason` is only for the log: four different rules end a title this way
        and, from the hall, all four look identical — the music stops. When one
        of them fires where it should not have, the breadcrumb is what tells
        them apart afterwards."""
        log.info("⏹ Song ended\n"
                 "reason: %s\n"
                 "file: %s\n"
                 "position: %d / %d ms",
                 reason,
                 self._playback.path.name if self._playback.path else "?",
                 self._player.position() if self._player else -1,
                 self._player.duration() if self._player else -1)
        if reason != "crossfade":
            # 🔀 Any other end ends a running crossfade too — a 🔉↓ that ran
            # out took the fading title down with it.
            self._end_crossfade()
        self._stop_play_timer()
        self._queue_auto_advance()   # before the buttons reset (needs the active row)
        self._playback.token += 1
        if self._player:
            self._player.stop()
            if self._between.pending is None:
                # Release the file; with an armed advance the NEXT source is
                # already preloaded (see _queue_auto_advance) — keep it.
                self._player.setSource(QUrl())
        for t in self._deckset.all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()
        if self._preview:
            self._preview.hide()
        if self._between.pending is not None:
            self._show_pause_status()
        else:
            self._now_playing.setText("No song selected")
            if self._big_player:
                self._big_player.set_now("")
        self._cue_next_song()

    def _stop_if_playing_from(self, table):
        """A new playlist landed in the deck the music is coming from — stop it.

        Only when the running title is GONE from the deck. A re-render reloads
        the same deck with the same tracks (a drop, a sort, a grid turning into
        a running order) and must never cut the floor off mid-song. A genuinely
        new list is the other case: the player would keep working through a
        playlist nobody can see any more, and its next auto-advance would land
        on whatever row now sits at that index. Loading into ANOTHER deck is
        left alone — planning the next round while the floor dances is normal.
        """
        if not self._player:
            return

        def holds(path) -> bool:
            target = str(path)
            return any(m and m.entry is not None and str(m.entry.path) == target
                       for m in table._row_meta)

        # ⏯ after a finished round would start a title this deck no longer has.
        nrs = self._between.round_start
        if nrs is not None and nrs[0] is table and not holds(nrs[2]):
            self._between.round_start = None
        # During the between-songs pause no row runs, but the armed advance
        # names the deck the evening is coming from.
        pending = self._between.pending
        pausing_into = (pending is not None and pending[0] is table
                        and not holds(pending[2]))
        if not pausing_into:
            if self._playback.path is None:
                return
            if table._current_play_row < 0 and not table._play_dropped:
                return      # the music is coming from some other deck or pane
            if holds(self._playback.path):
                return      # same track, re-rendered — it keeps playing
        log.info("⏹ The playing title left its deck\n"
                 "cause: a new list, or its heat / round removed\n"
                 "was playing: %s",
                 self._playback.path.name if self._playback.path else "-")
        self._between.pending = None    # …and the pause it would have run into
        self._announcer.stop()
        self._play_or_stop(None)        # stop, release the file, clear the card
        self._on_stop_btn()             # …and every deck's ▶/■ back to idle
        self.statusBar().showMessage(
            "⏹ The playing title is no longer in its deck — the music was "
            "stopped.", 8000)

    def _cue_first_track(self, table):
        """A playlist landed in a deck — put its first title on the player.

        An empty player card next to a full deck is a dead control: you cannot
        press ⏯, the artwork is blank, and nothing says which track is next. So
        the first title is CUED (start=False — loaded, shown, silent) as soon as
        a deck has one.

        Only ever when nothing is loaded at all. Anything else would be a deck
        load reaching into a running tournament, and generating a playlist while
        the floor is dancing is a normal thing to do.
        """
        if not self._player or self._playback.path is not None:
            return
        path = table.first_track_path()
        if path is not None:
            self._play_or_stop(path, start=False)
            # …and say on the deck WHICH title that is: the same marker a drop
            # onto the card leaves. Without it the first title of the session
            # sits on the player with no row highlighted, and ⏭ has nowhere to
            # walk on from. No scroll to it: `loaded` also fires for an edit —
            # the loaded title dragged out to another deck empties the player
            # — and the deck must stay where the operator was dragging from.
            self._mark_cued_row(path, scroll=False)
            row = table._current_play_row
            if row >= 0 and not table.selectionModel().hasSelection():
                # …and pick it, like a click on its ▶ does — never over what
                # the operator selected. No scroll: the decks run autoScroll off.
                table.setCurrentCell(row, _COL_TITLE)

    def _preview_skip(self, step: int):
        """⏮/⏭ on the preview overlay / big player: play the previous / next
        song row of whichever table is currently playing (headers are skipped).
        Falls back to the event plan's column, then the library pane, when the
        preview started there."""
        # Whatever is being said belongs to the title we are leaving. Fast
        # skipping used to stack one announcement per step and read them all
        # out over the music that finally stayed.
        self._announcer.stop()
        for t in self._deckset.all_tables:
            row = t._current_play_row
            if row < 0:
                continue
            nrow, npath = t.next_song_row(row, step)
            if nrow >= 0:
                t._on_play_click(nrow, npath)   # handles ▶/■ markers + playback
                t.scroll_row_into_play_view(nrow)
            return
        compare = getattr(self, "_event_compare", None)
        if compare is not None and compare.skip_prehear(step):
            return
        self._lib_browser.skip(step)

    def _on_playback_state(self, state):
        """(Re)starting via ⏯/▶ in the big player must restart the tick engine
        (countdown, fade ramp, PD highlight stop) if a stop had halted it — and
        the running row's ■/▶ follows the player, whoever pressed pause."""
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._xfade_follow(state)   # 🔀 a fading title pauses and runs with it
        self._refresh_wake_lock()
        if playing or state == QMediaPlayer.PlaybackState.PausedState:
            # StoppedState is deliberately skipped: it also fires on every track
            # switch, and the stop paths clear the row markers themselves.
            for t in self._deckset.all_tables:
                t.sync_play_glyph(playing)
        if state == QMediaPlayer.PlaybackState.PausedState:
            # 🔉↓ A fade's clock is wall time: paused, it would run out, and
            # the first tick after ⏯ would cut the title with no ramp at all.
            self._fade_now.freeze()
        if not playing:
            return
        self._fade_now.thaw()
        # 🧊 The stall watch measures from now: the time stood still while
        # paused or held, and the first tick would take it for a stall.
        self._playback.stall_seen = (None, 0, 0.0)
        self._cued = False   # it runs — however it was started
        # ↩ The mark is spent only now. Double-clicking a title merely loads it
        # — the playhead is parked on the mark and the badge has to survive
        # that, or looking at a title would cost the place in it.
        if self._playback.path is not None and self._is_playing_mode():
            self._clear_resume(self._playback.path)
        if self._level_owed:
            self._level_owed = False
            self._apply_volume()
        self._refresh_loudness_gain()
        if not self._fade_timer.isActive():
            self._fade_timer.start()
        if (self._playback.dance == "PD" and self._playback.path is not None
                and self._pd_highlight()[0]
                and self._pd_stop_at is None):
            self._ensure_pd_highlights(self._playback.path)

    def _on_stop_btn(self):
        """Stop button in the player bar — also resets every deck's play buttons."""
        self._stop_play_timer()
        self._end_crossfade()   # ⏹ is silence: the tail too
        # ⏹ means silence: a load the ⏭ rate limit still holds back must not
        # start after it, and a spoken call must not run on over it.
        self._pending_load = None
        self._load_timer.stop()
        self._announcer.stop()
        if self._player:
            self._playback.token += 1
            self._player.stop()
            self._player.setSource(QUrl())   # release the file (see _play_or_stop)
        for t in self._deckset.all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()
        if self._preview:
            self._preview.hide()
        self._now_playing.setText("No song selected")
        if self._big_player:
            self._big_player.set_now("")

    def _seek(self, delta_ms: int):
        """Seek the player by delta_ms (clamped to [0, duration]). Used by the
        Ctrl+←/→ shortcuts in the playlist table."""
        if not self._player:
            return
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def _seek_preloaded(self):
        """A title opened ahead — by the pause before a dance or a 🔀
        crossfade — had its LoadedMedia before the load asked for the ↩
        resume seek; do what that status would have done, now."""
        if self._player is None:
            return
        status = self._player.mediaStatus()
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,
                      QMediaPlayer.MediaStatus.BufferedMedia):
            self._on_media_status(status)

    def _on_media_status(self, status):
        """Reset play buttons when a song finishes playing naturally."""
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._playback.path:
            # A file back on disk opens again — rows drawn while it was gone
            # still carry its red ❗, and a title that failed earlier its red row.
            failed = self._playback.failed.pop(str(self._playback.path), None)
            for t in self._deckset.all_tables:
                t.refresh_found(self._playback.path)
                if failed is not None:
                    t.refresh_issue_marks()
            # 🐂 Armed while loading from the scanned length; now the file's own
            # length is known, which decides whether the highlight is the finale.
            if self._playback.dance == "PD" and self._pd_highlight()[0]:
                self._arm_pd_stop(self._playback.path)
        if (not self._playback.ready_logged and self._playback.play_t0 is not None
                and status in (QMediaPlayer.MediaStatus.LoadedMedia,
                               QMediaPlayer.MediaStatus.BufferedMedia)):
            # ⏱ Click → decodable media: everything after our own blocking work.
            self._playback.ready_logged = True
            log.info("⏱ Media ready\n"
                     "file: %s\n"
                     "total: %.0f ms",
                     self._playback.path.name if self._playback.path else "?",
                     1000 * (time.perf_counter() - self._playback.play_t0))
        if (self._resume_seek_ms is not None and self._player is not None
                and status in (QMediaPlayer.MediaStatus.LoadedMedia,
                               QMediaPlayer.MediaStatus.BufferedMedia)):
            # ↩ The media is open at last, so the position will hold. The ⏳ cut
            # is told to ignore what was skipped, exactly as the 🔇 silence skip
            # does — otherwise a title resumed past its play length stops the
            # instant it starts.
            ms = self._resume_seek_ms
            self._resume_seek_ms = None
            self._playback.offset_ms += ms
            self._player.setPosition(ms)
            self._sync_big_player_limit()   # the ⏳ marker moves on with it
            self.statusBar().showMessage(
                i18n.t("↩ Picked up at %s.") % f"{ms // 60_000}:{ms // 1000 % 60:02d}", 4000)
        if (self._playback.pre_roll_ms and self._player is not None
                and status in (QMediaPlayer.MediaStatus.LoadedMedia,
                               QMediaPlayer.MediaStatus.BufferedMedia)):
            # ⏩ The pre-roll: the same seek, and the ⏳ cut ignores it the same.
            ms = self._playback.pre_roll_ms
            self._playback.pre_roll_ms = 0
            self._playback.offset_ms += ms
            self._player.setPosition(ms)
            self._sync_big_player_limit()
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._is_playing_mode():
                # ↩ Heard out — no mark. Only in the big player: the overlay is
                # a pre-listen and never touches a mark, not even by running a
                # title to its end.
                self._clear_resume(self._playback.path)
            self._stop_play_timer()
            if self._play_panel.pd_editing():
                # ✏️ Hand-marking: the title ran out while it was being edited.
                # Nothing advances and nothing is unloaded — the track stays on
                # the card and in the player, so the scrubber can go straight
                # back to the crash and 🎯 keeps working on it.
                self._now_playing.setText(
                    i18n.t("⏸  editing: %s") % self._playback.path.stem[:70]
                    if self._playback.path is not None else "⏸  editing")
                self.statusBar().showMessage(
                    "✏️ Title ended — still loaded for editing; scrub back and "
                    "⏯ to listen.", 6000)
                for t in self._deckset.all_tables:
                    t.on_playback_stopped()
                self._reset_aux_play_markers()
                return
            self._queue_auto_advance()   # song shorter than the play length
            if self._between.pending is not None:
                self._show_pause_status()
            else:
                # Let go of the file: the backend holds it open as long as it
                # is the source, so the title just heard could not be renamed
                # or retagged. An armed advance has preloaded the next one.
                if self._player:
                    self._player.setSource(QUrl())
                self._now_playing.setText("No song selected")
                if self._big_player:
                    self._big_player.set_now("")
            if self._preview:
                self._preview.hide()
            for t in self._deckset.all_tables:
                t.on_playback_stopped()
            self._reset_aux_play_markers()
            self._cue_next_song()

    # ── ⏯ Playing or stopped, and the ⏯ tap ──────────────────────────────────

    def _is_player_running(self) -> bool:
        """Whether music is coming out right now — the ⏯ glyph follows it."""
        return bool(self._player) and (
            self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

    def _may_quit(self) -> bool:
        """Closing stops the music on the floor: with it playing, ask first.

        Paused or stopped closes at once, and so does a window that never got
        a player."""
        player = getattr(self, "_player", None)
        if (player is None
                or player.playbackState() != QMediaPlayer.PlaybackState.PlayingState):
            return True
        answer = QMessageBox.question(
            self, i18n.t("Music is playing"),
            i18n.t("Music is playing. Quit anyway and stop it?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes

    def _quit_after_fade(self) -> bool:
        """✕ with music sounding: fade it out first (`_fade_out_to_quit`) and
        close once it is silent. True while the close waits; the window then
        closes itself, and that close — or a second ✕ meanwhile — goes at once."""
        if self._fade_now.quitting:
            return False
        ms = self._fade_out_to_quit()
        if ms <= 0:
            return False
        self._fade_now.quitting = True
        log.info("🔉 Fading out before quitting\n"
                 "fade: %.1fs", ms / 1000)
        QTimer.singleShot(ms + _QUIT_FADE_MARGIN_MS, self, self.close)
        self._show_quit_fade(ms)
        return True

    def _show_quit_fade(self, ms: int):
        """The window saying the app is closing — a child of this one, so
        it goes with it."""
        QuitFadeDialog(self, ms)

    def _fade_out_to_quit(self) -> int:
        """Marcel: "if i close the window and a music from cartwall or main
        player is still playing fade it out with the configured intervall".
        The title over its list's fade time, HELD at silence — a fade ending
        like a timed cut would start the next title on the way out — and every
        sounding pad over its own fade or the wall's. Returns how long the
        longest runs, in ms; 0 when nothing sounds."""
        ms = 0
        if (self._player is not None and self._playback.path is not None
                and self._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState):
            if not self._fade_now.running:
                self._fade_now.start(
                    hand_fade_secs(self._settings, self._pv("fade")),
                    level=self._mix.fade)
                self._set_fade_indicator(True)
                self._fade_timer.start()
            self._fade_now.hold = True
            ms = round(self._fade_now.remaining() * 1000)
        voices = getattr(self, "_cart_voices", None)
        if voices is not None:
            self._cartwall.end_queue_run()   # a faded pad hands nothing on
            ms = max(ms, voices.stop_all())
        return ms

    def _is_player_stopped(self) -> bool:
        """Stopped, not paused — a cued title the deck row shows as ▶."""
        return bool(self._player) and (
            self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState)

    def _resume_tap(self) -> bool:
        """⏯ while the player stands still — from the card, the Space key, the
        presenter or the taskbar, they all come through here.

        Two things can be waiting for it: a Paso Doble held back after the call
        (the couples are in position early — start it now) and a 🏁 round-end
        stop (start the next round). And a title that is only cued: it starts
        the way ▶ on its row would — announced, pitched, held — not with a bare
        play(). Returns True when the tap was handled; False leaves the big
        player to restart whatever is loaded."""
        return (self._skip_pd_hold() or self._start_next_round()
                or self._start_cued())

    def _start_cued(self) -> bool:
        """⏯ on a title that was loaded but never started."""
        if not (self._cued and self._playback.path is not None
                and self._is_player_stopped()):
            return False
        # Not through its row's ▶, so say which list now plays, as that does.
        table, _row = self._playing_row()
        self._on_list_play(table)
        self._play_or_stop(self._playback.path)
        return True

    # ── ☀ Keeping the screen awake ────────────────────────────────────────────

    def _wake_lock_wanted(self) -> bool:
        """Whether the screen has to stay on right now: music on the speakers,
        or the presenter screen standing in front of the hall."""
        return bool(self._play_panel.keep_awake()
                    and (self._is_player_running() or self._presenter is not None))

    def _refresh_wake_lock(self):
        """Put the machine's idle timers where the current state wants them.

        Called from every edge that can change the answer — playback state, the
        presenter opening or closing, the setting itself. Only the CHANGES go to
        the OS: a track switch passes through Stopped for a moment, and that is
        no reason to hand the timeout back and take it again."""
        want = self._wake_lock_wanted()
        if want == self._awake_held:
            return
        if keep_display_awake(want) or not want:
            self._awake_held = want


    def _init_taskbar(self):
        """🪟 Hook the window's taskbar button up as a third control surface.

        Same three actions as the presenter's transport and the big player's,
        deliberately: the desk that reaches for the taskbar has the window
        covered by something else, and ⏮ ⏯ ⏭ is the whole job then. A no-op
        anywhere but Windows, and on Windows too if the shell says no."""
        self._taskbar = TaskbarPlayer(self)
        if not self._taskbar.attach(self):
            self._taskbar = None
            return
        self._taskbar.prevClicked.connect(lambda: self._preview_skip(-1))
        self._taskbar.playPauseClicked.connect(self._presenter_play_pause)
        self._taskbar.nextClicked.connect(self._on_player_next)
        if self._player:
            # State changes only. positionChanged fires ten times a second, and
            # nothing up there moves that fast — the ⏯ glyph is all that follows
            # the player.
            self._player.playbackStateChanged.connect(self._on_taskbar_state)

    def _on_taskbar_state(self, state):
        if self._taskbar is None:
            return
        self._taskbar.set_playing(
            state == QMediaPlayer.PlaybackState.PlayingState)
        self._sync_taskbar_title()

    def _sync_taskbar_title(self):
        """The title as the caption over the hover thumbnail.

        The thumbnail itself is only a small photograph of the window, and the
        player card's own text is not readable at that size — cropping the
        thumbnail down to the card was tried and the shell did not honour it,
        so the name above the picture is where the title lives.

        Whatever is LOADED, not only what is sounding: hovering the taskbar
        between two heats used to give back nothing but the window title, which
        reads exactly like a caption that is broken. ⏸ says it is not running.

        Called when a song is loaded and on state changes — once per song, so
        it costs nothing on the tick."""
        if self._taskbar is None:
            return
        if self._playback.path is None:
            self._taskbar.set_title("")     # nothing loaded: the window's name
            return
        dance = dance_name(self._playback.dance, self._playback.dance)
        stem = self._playback.path.stem
        playing = (self._player is not None
                   and self._player.playbackState()
                   == QMediaPlayer.PlaybackState.PlayingState)
        self._taskbar.set_title(("" if playing else "⏸  ")
                                + (f"{stem}  ·  {dance}" if dance else stem))

    def _taskbar_shutdown(self):
        if self._taskbar is not None:
            self._taskbar.shutdown()
            self._taskbar = None
