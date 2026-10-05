"""Playing mode: the player card, the play sets and the running clock.

Extracted from dancesport_gui.py (controller split) as a MainWindow mixin.
`PlayerControlMixin` is composed of three smaller ones — levels (player.main_audio),
the 🐂 PD stop (player.main_pd) and the ⏸ pause (player.main_pause) — so MainWindow
keeps importing this one name.
"""
import logging

import planner.models
import planner.warmup

import time
from typing import TYPE_CHECKING
from datetime import datetime
from PySide6.QtCore import (
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
)
from PySide6.QtWidgets import (
    QDialog,
)
from pathlib import Path
from planner import i18n
from planner import terms
from planner.terms import dance_name
from planner.checks import trailing_silence_secs
from planner.play_sets import play_set_of, tso_of
from player.tso import round_strip, round_takte, tso_band_of, tso_target
from shared.columns import (
    _COL_REGEN,
    _COL_TITLE,
)
from shared.playback import (
    audible_played_secs,
    keep_display_awake,
)
from shared.widgets import (
    _show_toast,
)
from shared.stores import (  # auto-resolved
    player_layout_of,
    save_settings,
)
from player.player import (  # auto-resolved
    _takt_text,
)
from player.main_audio import (
    AudioLevelMixin,
    _ANNOUNCE_DUCK,  # noqa: F401 — re-exported: tests patch it here
    _DESK_DUCK,  # noqa: F401
    _DUCK_DOWN_MS,  # noqa: F401
    _DUCK_UP_MS,  # noqa: F401
)
from player.main_pause import PauseMusicMixin, _live_target
from player.main_pd import PdStopMixin
from player.presenter import (  # auto-resolved
    PAUSE_TEXT,
    PresenterWindow,
)
from player.taskbar import (
    TaskbarPlayer,
)
from player.timetable import load_timetable, save_timetable
try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

# The desk's table, named in annotations only: the evening is handed one
# and never builds one, so it must not import the desk at runtime.
if TYPE_CHECKING:
    from gui.playlist_table import PlaylistTable

log = logging.getLogger("dancesport.gui.player")

# Shortest gap between two loads handed to the media backend. Below this a fast
# ⏭ burst is coalesced to its last target — long enough to spare Windows Media
# Foundation a teardown per keypress, short enough that a single press still
# feels immediate.
_LOAD_MIN_GAP_MS = 250.0

# ⭐ A wishlist takes neither set: it holds requests and background music, so
# each title plays to its own end and nothing starts by itself — the next one
# is picked by hand. No voice and no TSO pitch either: these are songs, not a
# heat. A double-click plays at once, the way a request is answered.
_WISHLIST_VALS = {"secs": 0, "fade": 3.0, "advance": False, "pause_off": True,
                  "loudness": True, "announce": False, "dblclick": True,
                  "tso": False}

# 🖥 From this many seconds left, the presenter screen blinks the remaining
# time red — long enough for the floor to finish the figure they are in.
_ENDING_AT = 12.0


def _mmss(secs: float) -> str:
    """Seconds as 01:39 — zero-padded, so the clock doesn't jump in width."""
    s = max(0, int(secs))
    return f"{s // 60:02d}:{s % 60:02d}"

class PlayerControlMixin(AudioLevelMixin, PdStopMixin, PauseMusicMixin):
    """Playing mode itself: the player card, the decks it plays, the 🖥 presenter
    screen and the clock.

    Levels and the Paso Doble stop are their own modules; MainWindow still gets
    all of it from this one name.
    """

    # A stop or a 🛑 hold left the output where the fade took it; the next start
    # puts the level back (see _on_playback_state).
    _level_owed = False

    def _is_playing_mode(self) -> bool:
        return self._left_stack.currentIndex() == 1

    # ── Every list its own play values ───────────────────────────────────────
    #
    # One player, several lists: the 🤸 party list runs full length and
    # hands-free while the tournament deck beside it cuts at 1:30 and is started
    # title by title. So the values a play set covers belong to the LIST — the
    # panel shows (and edits) those of the list last clicked, and playback runs
    # on those of the list that is playing, which need not be the same one.

    def _panel_list(self):
        """The list whose values the play panel shows and edits. None on a desk
        with no lists, where the panel's own values are the only ones."""
        return getattr(self, "_panel_table", None)

    def _card_tso(self) -> bool:
        """The TSO pitch as the player card has it — it is not on the panel."""
        card = getattr(self, "_big_player", None)
        if card is not None:
            return bool(card.tso_mode())
        return bool(getattr(self, "_settings", {}).get("tso_equalize", True))

    def _list_vals(self, table) -> dict:
        """The play values ONE list runs with: `play_set()`'s keys plus `tso`.

        A list is given them the first time anything asks, and never again
        behind the operator's back: the set of its kind — 🎉 party for the 🤸
        list, 🏆 tournament for every deck, the fixed `_WISHLIST_VALS` for a ⭐
        wishlist — or, for the list the panel was already standing on
        (start-up, a desk no list was ever bound to), what the panel shows.
        After that only a hand changes them: the panel while it shows this
        list, the ⏭/✋ in the list's corner, or 🎉/🏆."""
        if table._play_vals is None:
            panel_list = self._panel_list()
            if panel_list is None or table is panel_list:
                vals = self._play_panel.play_set()
                vals["tso"] = self._card_tso()
            elif any(table is t for t in getattr(self, "_wishlists", ())):
                vals = dict(_WISHLIST_VALS)
            else:
                settings = getattr(self, "_settings", {})
                kind = ("party" if table is getattr(self, "_warmup_table", None)
                        else "tournament")
                vals = play_set_of(settings, kind)
                vals["tso"] = tso_of(settings, kind)
            table._play_vals = vals
        return table._play_vals

    def _engine_list(self):
        """The list playback runs on: the one playing, else the one on the
        panel — which is then what the next ▶ will most likely start."""
        t, _row = self._playing_row()
        return t if t is not None else self._panel_list()

    def _pv(self, key: str):
        """One play value as playback has to obey it right now."""
        t = self._engine_list()
        if t is None:
            return self._play_panel.play_set()[key]
        return self._list_vals(t)[key]

    def _play_limit_secs(self) -> int:
        """Seconds per title for the playing list, 0 = to the track's own end."""
        return int(self._pv("secs"))

    def _engine_pause_secs(self) -> int:
        """The between-titles pause for the playing list: the panel's seconds
        (they are global), 0 where this list has the pause switched off."""
        return 0 if self._pv("pause_off") else self._play_panel.pause_setting_secs()

    def _engine_pause_available(self) -> bool:
        """Whether a pause can happen at all — only a list that walks on has
        a gap to put one in."""
        return bool(self._playing_advance() and not self._pv("pause_off"))

    def _configured_play_secs(self, table=None) -> int:
        """Play length a deck's ⏱ column flags short tracks against (0 = off)
        — that deck's own, where it is given."""
        if table is not None:
            return int(self._list_vals(table)["secs"])
        return self._play_limit_secs()

    def _bind_panel(self, table) -> None:
        """A list was clicked: the panel now shows ITS values, and edits there
        go into it. Nothing is written into the list by the switch itself."""
        if table is None or table is self._panel_list():
            return
        vals = self._list_vals(table)
        self._panel_table = table
        self._binding_panel = True
        try:
            changed = self._play_panel.apply_play_set(
                **{k: v for k, v in vals.items() if k != "tso"})
        finally:
            self._binding_panel = False
        # The TSO toggle sits on the player card, which serves the list that
        # is playing — it follows the click only while nothing plays.
        if self._playing_row()[0] is None:
            if bool(vals["tso"]) != self._card_tso():
                changed.append(i18n.t("TSO tempo equalize → on") if vals["tso"]
                               else i18n.t("TSO tempo equalize → off"))
            self._sync_card_tso(vals["tso"], table)
        self._refresh_set_lights()
        # Other values on the panel get the toast 🎉/🏆 get. Not while the
        # window is not up: start-up binds the panel too, and nobody clicked.
        if changed and self.isVisible():
            _show_toast(self, self._list_set_head(table)
                        + "\n" + "\n".join(changed), 4000)

    def _list_set_head(self, table) -> str:
        """The toast's first line for a list the panel switched to: the set
        it stands on, or that it has values of its own."""
        name = self.deck(table).title
        if self._on_play_set("party"):
            return i18n.t("🎉  Party set — %s") % name
        if self._on_play_set("tournament"):
            return i18n.t("🏆  Tournament set — %s") % name
        return i18n.t("🎚  Own settings — %s") % name

    def _sync_card_tso(self, want: bool, table=None) -> None:
        """Move the card's TSO toggle for `table`. Its signal stores the value
        into a list — this one, named here because while a title is only just
        starting the playing row is not marked yet."""
        card = getattr(self, "_big_player", None)
        if card is None or bool(want) == card.tso_mode():
            return
        self._tso_list = table
        try:
            card.set_tso_mode(bool(want))
        finally:
            self._tso_list = None

    def _store_panel_into_list(self) -> None:
        """The panel moved (by hand or by 🎉/🏆): write it into its list."""
        t = self._panel_list()
        if t is None or getattr(self, "_binding_panel", False):
            return
        vals = self._list_vals(t)
        new = self._play_panel.play_set()
        if any(vals.get(k) != v for k, v in new.items()):
            vals.update(new)
            self._autosave_playlist()

    def _deck_advance(self, table) -> bool:
        """⏭ Auto / ✋ Manual as it stands for ONE list."""
        if table is None:
            return self._play_panel.auto_advance()
        return bool(self._list_vals(table)["advance"])

    def _playing_advance(self) -> bool:
        """…for the list the evening is on right now (see `_engine_list`)."""
        return self._deck_advance(self._engine_list())

    def _set_deck_advance(self, table, on: bool):
        """⏭/✋ in a list's corner was clicked: it is that list's own value, so
        the panel follows only when it is showing this very list."""
        self._list_vals(table)["advance"] = bool(on)
        if table is self._panel_list():
            self._play_panel.advance_check.setChecked(bool(on))
        table.refresh_advance_toggle()
        self._autosave_playlist()

    def _wire_advance_switch(self):
        """Repaint the corner switch when the panel's ⏭ moves — it is the same
        value whenever the panel shows that list."""
        self._play_panel.advance_check.toggled.connect(
            lambda _: self._refresh_advance_toggles())

    def _refresh_advance_toggles(self):
        """Repaint the corner switch on every list."""
        # getattr: the panel exists before the decks do, and a play set applied
        # during start-up flips this switch before there is anything to repaint.
        for t in getattr(self, "_all_tables", ()):
            t.refresh_advance_toggle()

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
        if in_strip:
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
        self._left_stack.setCurrentIndex(1 if playing else 0)
        if self._big_player and self._big_player.is_wide():
            self._big_player.setVisible(playing)
            self._dock_mode_row()
        for t in self._all_tables:
            t.set_play_highlight_enabled(playing)
            # No song swapping while a tournament runs — hide the ↺ column.
            t.setColumnHidden(_COL_REGEN, playing)
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
        self._settings["timed_enabled"] = self._play_panel.timed_enabled()
        self._settings["auto_advance"] = self._play_panel.auto_advance()
        # The tick as shown, not the effective off of a switched-off
        # auto-advance — so it is still there when ⏭ comes back.
        self._settings["repeat_list"] = self._play_panel.repeat_setting_on()
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
        self._settings["pause_music"] = self._play_panel.pause_music()
        self._settings["pause_music_vol"] = self._play_panel.pause_music_vol()
        self._settings["announce_next"] = self._play_panel.announce_next()
        self._settings["announce_wait"] = self._play_panel.announce_wait()
        self._settings["announce_takt"] = self._play_panel.announce_takt()
        self._settings["announce_heat"] = self._play_panel.announce_heat()
        self._settings["announce_voice"] = self._play_panel.announce_voice()
        # Live: the next announcement is made in the voice the panel shows now,
        # not in the one the app started with.
        self._announcer.set_voice(self._settings["announce_voice"])
        self._settings["show_artwork"] = self._play_panel.show_artwork()
        self._settings["dblclick_plays"] = self._play_panel.dblclick_plays()
        self._settings["remember_pos"] = self._play_panel.remember_pos()
        self._settings["presenter_screen"] = self._play_panel.presenter_screen()
        self._settings["presenter_screen_name"] = \
            self._play_panel.presenter_screen_name()
        self._settings["presenter_theme"] = self._play_panel.presenter_theme()
        self._settings["keep_awake"] = self._play_panel.keep_awake()
        self._refresh_wake_lock()
        save_settings(self._settings)
        # Toggling the PD options mid-song must re-arm (or disarm) the stop.
        if self._playback.dance == "PD" and self._playback.path is not None:
            if self._play_panel.pd_highlight_stop():
                self._ensure_pd_highlights(self._playback.path)
            else:
                self._pd_stop_at = None
        # Play length / timed toggle changed → refresh the ⏳ display too.
        self._sync_big_player_limit()

    def _stop_play_timer(self):
        """Halt the tick engine, cancel any pending auto-advance and restore
        full volume for the next song."""
        self._fade_timer.stop()
        self._between.pending = None
        self._pd_stop_at = None
        self._fade_now_end = None
        self._between.fade_end = None
        self._set_fade_indicator(False)
        self._stop_pause_music()
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
        if self._pd_runs_to_its_highlight():
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
            end_ms = (self._play_limit_secs() * max(0.01, rate) * 1000
                      + self._playback.offset_ms)
            # Dead air can fall BEFORE the cut — then the song ends there, and
            # the countdown has to say so. Whichever comes first wins.
            sil_ms = self._silence_stop_ms()
            if sil_ms is not None and sil_ms < end_ms:
                self._big_player.set_limit(sil_ms, "mute")
            else:
                self._big_player.set_limit(int(end_ms))
            self._big_player.set_pd_marks([])   # not a PD — no marks on the bar
        else:
            sil_ms = self._silence_stop_ms()
            if sil_ms is not None:
                self._big_player.set_limit(sil_ms, "mute")
            else:
                self._big_player.set_limit(None)
            self._big_player.set_pd_marks([])

    def _next_song_to_advance(self) -> tuple[PlaylistTable, int, Path] | None:
        """(table, row, path) of the song AFTER the one currently playing, or
        None. Must be resolved BEFORE the play buttons are reset — afterwards
        no table remembers which row was active."""
        for t in self._all_tables:
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
        # During the auto-advance pause nothing is "playing", so no table can
        # resolve a follower — the armed advance IS the next song.
        nxt = self._next_song_to_advance() or _live_target(self._between.pending)
        if nxt is None:
            self._big_player.set_next_up("")
            return
        t, nrow, npath = nxt
        if self._looping():
            # Nothing "comes after" a looping title — it comes again.
            self._big_player.set_next_up(f"🔁  {npath.stem}  ·  again")
            return
        row = t._current_play_row
        nmeta = t._row_meta.at(nrow)
        cur = t._row_meta.at(row)
        if nmeta is not None and cur is not None:
            # Same reading as in _queue_auto_advance: a follower ABOVE the
            # running title is the list starting over, not a round ending.
            if nrow > row and cur.round_name != nmeta.round_name:
                self._big_player.set_next_up(f"🏁  {terms.round_name(cur.round_name) or 'Round'} ends here")
                return
        code = nmeta.dance if nmeta is not None else ""
        dance = dance_name(code, code)
        self._big_player.set_next_up(
            f"⏭  {dance}  ·  {npath.stem}" if dance else f"⏭  {npath.stem}")

    # ── 🎉 Party play set ─────────────────────────────────────────────────────

    def _set_party_tso(self, want) -> list[str]:
        """Put the TSO pitch where the set wants it, for the list on the panel
        (None = leave alone, for a set saved before TSO joined it). Reports
        like the panel does.

        TSO pitches every title to the heat's mean tempo — right for a round of
        Quicksteps, wrong for a party, where the next song is a different dance
        at whatever tempo it was recorded. The toggle itself sits on the player
        card and serves the list that plays, so it only moves when that is the
        list the set was applied to."""
        if want is None:
            return []
        t = self._panel_list()
        was = self._list_vals(t)["tso"] if t is not None else self._card_tso()
        if t is not None:
            self._list_vals(t)["tso"] = bool(want)
        if t is None or t is self._engine_list():
            if self._big_player is None:
                return []
            self._sync_card_tso(want, t)
            self._settings["tso_equalize"] = bool(want)
        if bool(was) == bool(want):
            return []
        return [i18n.t("TSO tempo equalize → on") if want
                else i18n.t("TSO tempo equalize → off")]

    def _on_play_set(self, which: str) -> bool:
        """Is the panel standing on the 🎉 party / 🏆 tournament set right now?

        The TSO pitch is not part of the answer: its toggle sits on the player
        card, so neither `play_set()` nor `play_set_of` carries it."""
        return self._play_panel.play_set() == play_set_of(self._settings, which)

    def _refresh_set_lights(self) -> None:
        """Light the button of the set the panel is standing ON — every time a
        control moves, whoever moved it.

        Both tooltips have always promised exactly this ("lit gold while the
        panel stands on those values"), but the lights used to be set when a
        set was applied and then left alone, so they went on reporting the last
        button pressed while the values underneath them were nudged by hand.
        Both dark is an answer too: the panel is on the operator's own values.
        """
        party = self._on_play_set("party")
        self._play_panel.set_party_on(party)
        if not party:
            self._play_panel.set_tournament_on(self._on_play_set("tournament"))

    def _set_party_mode(self, on: bool) -> None:
        """🎉 clicked: put the list on the panel on the party settings (full
        length, auto-advance, no pause, equalized volume, TSO off) — or, when
        the lit button is clicked off, on the 🏆 tournament set — and say so.

        Only a hand does this, and only to the list on the panel. Switching
        lists used to re-apply the set of the list's kind on every title, which
        undid a play length nudged between two heats (1:55 came back as 1:40
        after one party song); a list now keeps what it was given."""
        which = "party" if on else "tournament"
        changed = self._play_panel.apply_play_set(
            **play_set_of(self._settings, which))
        changed += self._set_party_tso(tso_of(self._settings, which))
        head = (i18n.t("🎉  Party set applied") if on
                else i18n.t("🏆  Tournament set back"))
        self._refresh_set_lights()
        self._save_play_settings()
        _show_toast(self, head + "\n" + ("\n".join(changed) if changed
                                         else i18n.t("nothing to change")), 4000)
        log.info("🎉 Party set %s\n"
                 "changed: %s", "on" if on else "off", changed or "—")

    def _apply_tournament_set(self):
        """🏆 button: put the list on the panel on the competition values and
        say so.

        Pressing it always applies — it is a way back, not a toggle you can
        switch off. The gold light only reports where the panel stands.

        🐂 The Paso Doble highlight stop goes off with it: the detection is not
        good enough yet to cut a competition Paso Doble on, and a heat stopped
        in the wrong bar is danced twice. Switch it back by hand for a demo.
        """
        changed = self._play_panel.apply_play_set(
            **play_set_of(self._settings, "tournament"))
        changed += self._set_party_tso(tso_of(self._settings, "tournament"))
        changed += self._play_panel.set_pd_highlight_stop(False)
        self._refresh_set_lights()
        self._save_play_settings()
        _show_toast(self, i18n.t("🏆  Tournament set applied") + "\n"
                    + ("\n".join(changed) if changed
                       else i18n.t("nothing to change")), 4000)
        log.info("🏆 Tournament set applied\n"
                 "changed: %s", changed or "—")

    def _on_list_play(self, table) -> None:
        """A title started from `table`: playback now runs on that list's own
        values. Nothing is applied TO the list — it keeps what it was given —
        but the player card serves the list that plays, so its TSO toggle and
        its ⏸♪ button take this list's answers."""
        if table is None:
            return
        vals = self._list_vals(table)
        for t in self._all_tables:
            t.set_advance_live(t is table)
        self._sync_card_tso(vals["tso"], table)
        if self._big_player is not None:
            self._big_player.set_pause_available(
                bool(vals["advance"] and not vals["pause_off"]))

    def _set_artwork_shown(self, on: bool):
        """🖼 checkbox on the Playing panel → cover on the player card."""
        if self._big_player:
            self._big_player.set_artwork_enabled(on)

    def _playing_m3u(self) -> Path | None:
        """The .m3u the running deck was imported from, if it was — its own
        picture beats the cover of whatever CD the track came off."""
        for t in self._all_tables:
            if t._current_play_row >= 0:
                return getattr(t, "_m3u_path", None)
        return None

    def _focus_next_song(self):
        """Put the cursor on the song that comes next.

        With auto-advance off nothing starts by itself, so the operator has to
        find the next row and press play on it — the one moment they are busy
        watching the floor. Selecting it (and scrolling it into view) means the
        row is already under the finger, exactly as the 🏁 end-of-round case
        does. It only moves the selection; nothing is played.
        """
        nxt = self._next_song_to_advance()
        if nxt is None:
            return
        t, nrow, _npath = nxt
        t.setCurrentCell(nrow, _COL_TITLE)   # scrolls it into view by itself

    def _queue_auto_advance(self):
        """Arm the between-songs pause if Playing mode + auto-advance are on.

        Auto-advance as the PLAYING deck has it — every list carries its own
        answer (see `_deck_advance`)."""
        if not self._is_playing_mode():
            return
        advancing = self._playing_advance()
        # 🔁 holds the evening on ONE title. That is not the list walking on, so
        # it does not wait for the switch that walks it.
        if not self._looping() and not advancing:
            self._focus_next_song()
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
        self._between.held = False   # set while the operator ⏯-pauses the filler
        self._between.fade_end = None   # set while ⏭ fades the filler out to skip
        if self._big_player:
            self._big_player.set_pause_active(True)   # show ⏱➕ extend
        # ⏩ Preload: hand the next file to the backend NOW, so the end of the
        # pause is a bare play() instead of a full open-and-probe of the file
        # (the WMF backend takes a noticeable moment for that).
        if self._player:
            self._player.setSource(QUrl.fromLocalFile(str(nxt[2])))
        # …and measure its loudness in the same breath, if nobody ever did: the
        # pause is exactly the room for that decode, so the advance itself never
        # has to hold the next title back to get its level right.
        self._await_loudness(Path(nxt[2]), False)
        self._start_pause_music()
        self._fade_timer.start()

    def _set_countdown(self, text: str):
        """Show the countdown/status on the left Playing panel; mirror it onto
        the big-player card ONLY during the between-songs pause. In normal play
        the panel's sand clock + the card's adjusted-time line already cover it,
        so a card countdown would double the ⏳."""
        self._play_panel.set_countdown(text)
        if self._big_player:
            self._big_player.set_countdown(
                text if self._between.pending is not None else "")

    def _fire_pending_advance(self):
        """End the between-songs pause now and start the queued next song."""
        if self._between.pending is None:
            return
        nxt = _live_target(self._between.pending)
        self._between.pending = None
        self._stop_pause_music()
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
        rest of the pause and start the next song; while the filler music is
        playing, fade it out over the configured fade time first so it doesn't
        cut off mid-track. Outside a pause, just step the deck to the next row."""
        if self._between.pending is not None:
            self._announcer.stop()   # the cue was for THIS pause, which is over
            if (self._filler.active and self._pause_player is not None
                    and self._pause_player.playbackState()
                    == QMediaPlayer.PlaybackState.PlayingState):
                self._start_pause_skip_fade()
            else:
                self._fire_pending_advance()   # no audible filler → advance now
            return
        self._preview_skip(+1)

    def _start_pause_skip_fade(self):
        """⏭ during the filler music: ramp it to silence over the fade time and
        then fire the queued next song (driven by _on_play_tick), instead of
        cutting the filler dead."""
        if self._between.fade_end is not None:
            return   # already fading
        self._between.held = False   # take it out of a ⏯-hold if it was paused
        self._pause_fade_total = max(0.5, float(self._pv("fade")))
        self._pause_fade_from = self._pause_out.volume()
        self._between.fade_end = time.monotonic() + self._pause_fade_total
        self._fade_timer.start()   # ensure the tick is running to drive the ramp

    def _set_fade_indicator(self, on: bool):
        """Blink the big player orange while a fade-out ramps the song down --
        a fade is otherwise a silent thing to watch happen."""
        if self._big_player:
            self._big_player.set_fading(on)

    def _fade_out_now(self):
        """🔉↓ on the big player: ramp the playing song to silence over the
        configured fade time, then end it like a timed cut."""
        if (not self._is_playing_mode() or self._playback.path is None
                or self._player is None
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        self._fade_now_hold = False
        self._fade_now_total = max(0.5, float(self._pv("fade")))
        self._fade_now_end = time.monotonic() + self._fade_now_total
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
        if self._fade_now_end is not None:
            return   # a fade is already running — don't restart the ramp
        self._fade_now_hold = True
        self._fade_now_total = max(0.5, float(self._pv("fade")))
        self._fade_now_end = time.monotonic() + self._fade_now_total
        log.info("🛑 Panic fade — holding playback in place\n"
                 "file: %s\n"
                 "fade: %.1fs", self._playback.path.name, self._fade_now_total)
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
        for t in self._all_tables:
            for r, m in t._row_meta.numbered():
                if str(getattr(m.entry, "path", "")) == target:
                    hit_table, hit_row = t, r
                    break
            if hit_table is not None:
                break
        # One playing deck at a time: clear stale markers on every other deck.
        for t in self._all_tables:
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
        if not p.is_file():
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
            # The deck the pause is running for, not the panel: its own switch
            # is what armed this, so its own switch is what can call it off.
            if (not self._is_playing_mode()
                    or not self._deck_advance(self._between.pending[0])):
                self._stop_play_timer()   # turned off during the pause → cancel
                self._player.setSource(QUrl())   # release the preloaded file
                return
            # ⏭ skip: fade the filler to silence over the fade time, then advance.
            if self._between.fade_end is not None:
                remaining = self._between.fade_end - time.monotonic()
                if remaining <= 0:
                    self._between.fade_end = None
                    self._fire_pending_advance()
                    return
                f = remaining / self._pause_fade_total
                self._pause_out.setVolume(max(0.0, min(1.0, self._pause_fade_from * f)))
                self._set_countdown(f"🔉↓  {int(remaining + 0.999)} s")
                return
            # Operator ⏯-paused the filler on the big player → hold the countdown
            # where it is (pin the deadline to "now") until they press play again.
            held = (self._filler.active and self._pause_player is not None
                    and self._pause_player.playbackState()
                    == QMediaPlayer.PlaybackState.PausedState)
            if held:
                if not self._between.held:
                    self._between.held = True
                    self._between.hold_remaining = self._between.advance_at - time.monotonic()
                self._between.advance_at = time.monotonic() + self._between.hold_remaining
                r = int(self._between.hold_remaining + 0.999)
                self._set_countdown(i18n.t("⏸  %d s  (paused)") % r)
                return
            self._between.held = False
            remaining = self._between.advance_at - time.monotonic()
            if remaining > 0:
                if remaining <= self._announce_lead():
                    self._maybe_announce_next()
                self._update_pause_music(remaining)
                r = int(remaining + 0.999)
                self._set_countdown(f"⏸  {r} s")
                return
            if self._hold_for_announcement():
                return
            self._fire_pending_advance()
            return
        # 🔇 Stillness skip — in EVERY mode (preview too): jump over silent
        # stretches, end the song when only dead air is left. Deliberate fades
        # (🔉↓) keep priority — no skipping mid-fade.
        if (self._player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
                and self._fade_now_end is None
                and self._maybe_skip_silence()):
            return
        if (not self._is_playing_mode()
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        # Manual "fade out now" (🔉↓): ramp to silence, then end like a timed
        # cut. Takes priority over the normal timed/PD logic below.
        if self._fade_now_end is not None:
            hold = self._fade_now_hold
            remaining = self._fade_now_end - time.monotonic()
            if remaining <= 0:
                self._fade_now_end = None
                self._set_fade_indicator(False)
                if hold:
                    # 🛑 Panic: stay on this song at this position. ⏯ resumes at
                    # the normal level — pushed when it runs again, not here:
                    # the pause lands late and the buffer would play it loud.
                    self._fade_now_hold = False
                    self._player.pause()
                    self._mix.fade = 1.0
                    self._level_owed = True
                    self._set_countdown("🛑  held")
                    return
                self._on_timed_end("fade-out finished")
                return
            self._mix.fade = (max(0.0, remaining / self._fade_now_total)
                              if self._fade_now_total > 0 else 0.0)
            self._apply_volume()
            self._set_countdown(f"{'🛑' if hold else '🔉↓'}  {remaining:.0f} s")
            return
        # Grey the track once it has truly been heard for >10 s (any dance).
        if (not self._played_marked
                and self._playback.path is not None
                and self._player.position() >= self._PLAYED_AFTER_MS):
            self._played_marked = True
            self._mark_path_played(self._playback.path)
        if self._pd_runs_to_its_highlight():
            # Under the 🐂 stop a Paso Doble is never faded and never cut at
            # the play length — it is danced to its highlights. Only the armed
            # highlight stop (or the natural end) may end it.
            if self._mix.fade != 1.0:
                self._mix.fade = 1.0
                self._apply_volume()
            if self._pd_stop_at is not None:
                pos = self._player.position() / 1000.0
                # The mark is a fixed musical spot in the file, so the STOP is
                # compared against the raw position — but how long until the gong
                # is wall-clock, hence the tempo rate on the countdown only.
                remaining = self._pd_stop_at - pos
                if remaining <= 0:
                    if self._pd_verify_stop:
                        # ✔ Just left edit mode: pause ON the mark so it can be
                        # checked by ear instead of advancing to the next title.
                        self._pd_verify_stop = False
                        self._player.pause()
                        self._set_countdown("🎯  stop reached — ⏯ to go on")
                        return
                    self._on_timed_end("PD highlight stop")
                    return
                remaining /= max(0.01, self._player.playbackRate())
                r = int(remaining + 0.999)
                tag = ("🎯" if (self._cache and self._playback.path
                                and self._cache.is_pd_manual(self._playback.path))
                       else "🐂")
                self._set_countdown(f"{tag}  {r // 60}:{r % 60:02d}")
            elif (self._pd_worker is not None
                    and self._pd_worker.isRunning()):
                self._set_countdown("🐂  detecting highlights…")
            else:
                self._set_countdown("🐂  plays to the end")
            return
        if not self._play_limit_secs() > 0:
            if self._mix.fade != 1.0:   # toggled off mid-fade → ramp back up
                self._mix.fade = 1.0
                self._apply_volume()
            self._set_countdown("")
            return
        limit = self._play_limit_secs()
        fade = float(self._pv("fade"))
        # Wall-clock music heard so far: skipped silence doesn't count and the
        # tempo fader is divided out, so "1:45" is 1:45 on the floor.
        played = audible_played_secs(self._player.position(),
                                     self._playback.offset_ms,
                                     self._player.playbackRate())
        remaining = limit - played
        if remaining <= 0:
            self._on_timed_end("play length reached")
            return
        self._mix.fade = min(1.0, remaining / fade) if fade > 0 else 1.0
        self._apply_volume()
        r = int(remaining + 0.999)
        self._set_countdown(f"⏳  {r // 60}:{r % 60:02d}")

    def _mark_path_played(self, path: Path):
        """Grey this track in every deck that holds a copy of it."""
        for t in self._all_tables:
            t.mark_path_played(str(path))

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
                    "Play a title first — then TSO sets its heat tempo.", 4000)
            return False
        # The deck that is actually playing (the one with a marked ▶/■ row).
        deck = next((t for t in self._all_tables
                     if t._current_play_row >= 0), None)
        if deck is None or not (0 <= deck._current_play_row < len(deck._row_meta)):
            if not auto:
                self.statusBar().showMessage("No playing row found.", 4000)
            return False
        meta = deck._row_meta[deck._current_play_row] or {}
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
                 _takt_text(danced_at),
                 _takt_text(target), ent.bpm, _takt_text(played_at),
                 ent.title or ent.path.name)
        src = (i18n.t("the %s %s of this round") % (takte, dance_name(dance, dance))
               if len(counts) > 1 else i18n.t("this %s") % dance_name(dance, dance))
        self.statusBar().showMessage(
            i18n.t("🎚 TSO tempo: %s %s → T%s (target T%s from %s)")
            % (dance, ent.bpm, _takt_text(played_at), _takt_text(target), src), 6000)
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
        self._stop_play_timer()
        self._queue_auto_advance()   # before the buttons reset (needs the active row)
        self._playback.token += 1
        if self._player:
            self._player.stop()
            if self._between.pending is None:
                # Release the file; with an armed advance the NEXT source is
                # already preloaded (see _queue_auto_advance) — keep it.
                self._player.setSource(QUrl())
        for t in self._all_tables:
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
        self._stop_pause_music()
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

    def deck_path(self) -> Path | None:
        """The title the player is on, or about to load: a load held back by
        the rate limit or by the loudness wait already counts. A preview
        window asks before it stops the shared player."""
        if self._pending_load is not None:
            return self._pending_load[0]
        if self._lufs_pending is not None:
            return self._lufs_pending
        return self._playback.path

    def _play_or_stop(self, path: Path | None, start: bool = True):
        """Play the given path, or stop if path is None.

        start=False cues the track (loads the source + shows it on the card) but
        leaves it stopped, so the user presses ⏯ to begin — used for drag-drop
        onto the player, which must not auto-start playback.

        Loads are rate-limited (see _LOAD_MIN_GAP_MS): a single press still hits
        the backend immediately, but hammering ⏭ only moves the target and one
        load follows when the burst settles. Stopping is never delayed.
        """
        if not self._player:
            return
        gap_left = _LOAD_MIN_GAP_MS - 1000.0 * (time.monotonic() - self._last_load_at)
        if path is not None and gap_left > 0:
            self._pending_load = (path, start)
            self._load_timer.start(int(gap_left))
            return
        self._pending_load = None
        self._load_timer.stop()
        self._load_track(path, start)

    def _flush_pending_load(self):
        """The skip burst is over — load whatever the last press landed on."""
        pending = self._pending_load
        self._pending_load = None
        if pending is not None:
            self._load_track(*pending)

    def _load_track(self, path: Path | None, start: bool = True):
        """The real work of `_play_or_stop` — everything that touches the media
        backend. Only ever entered through the rate limit above."""
        if not self._player:
            return
        self._last_load_at = time.monotonic()
        t0 = time.perf_counter()
        self._playback.token += 1
        self._cued = path is not None and not start   # ⏯ starts it (_start_cued)
        if path != self._playback.path and self._play_panel.pd_editing():
            # A new title cancels hand-marking — otherwise its highlight stop
            # would stay suspended on a track nobody is editing any more.
            self._play_panel.set_pd_edit(False)
            self._pd_verify_stop = False
        self._remember_stop_point()   # ↩ before the stop takes the position away
        self._player.stop()
        self._stop_play_timer()
        if path is not None and self._await_loudness(path, start):
            return      # …re-enters here the moment the level is known
        if path is None:
            # Clear the source too: the Windows (WMF) backend keeps the file open
            # otherwise, and a stale source can wedge the NEXT load.
            self._player.setSource(QUrl())
            self._now_playing.setText("No song selected")
            if self._big_player:
                self._big_player.set_now("")
                self._big_player.set_artwork(None)
                self._big_player.set_current_dance(None)
            self._playback.dance = ""
            self._playback.path = None
            self._played_marked = False
            self._playback.offset_ms = 0
            self._sync_taskbar_title()    # 🪟 nothing loaded → the window's name
            if self._preview:
                self._preview.hide()
        else:
            # 🕘 What is on the deck right now becomes the last played — but
            # only when something else really takes over: a restart of the same
            # file must not make a title its own predecessor.
            if self._playback.path is not None and self._playback.path != path:
                self._last_played = (
                    dance_name(self._playback.dance, self._playback.dance),
                    self._playback.path.stem)
            self._between.round_start = None   # a song starts — round-end resume done
            ent = self._resolve_entry(str(path))
            # warmup_code, not .dance: a social title (Discofox, Salsa, …) has
            # no competition code, and with an empty dance it was never
            # announced and showed a blank dance on the card.
            self._playback.dance = (planner.warmup.warmup_code(ent) or "") if ent is not None else ""
            self._playback.path = path
            self._played_marked = False   # fresh track — re-arm the 10 s rule
            self._playback.offset_ms = 0      # …and no silence skipped on it yet
            # ↩ Seeking here would be thrown away — the media is not open yet.
            # `_on_media_status` performs it the moment it is.
            self._resume_seek_ms = self._resume_mark_for(path)
            self._refresh_resume_marks(path)   # the row badges follow the deck
            # 🪟 The taskbar caption names the title, and a new one has to reach
            # it here: the state change alone does not fire between two songs
            # of a heat, and the caption would keep naming the previous one.
            self._sync_taskbar_title()
            if self._playback.dance == "PD" and self._play_panel.pd_highlight_stop():
                self._ensure_pd_highlights(path)
            self._ensure_silences(path)   # arm the 🔇 stillness skip
            self._mix.load_gain(self._loudness_gain(path))
            self._apply_volume()
            url = QUrl.fromLocalFile(str(path))
            if self._player.source() != url:
                self._player.setSource(url)
            # Everything that moves the playback RATE happens here, while the
            # track is still stopped: a rate change makes the backend re-init
            # its resampler, and doing that after play() is a hole you hear at
            # the top of every title. Set into silence and there is nothing to
            # cut. The takt is needed first — TSO pitches against it.
            pitched = False
            if self._big_player:
                self._big_player.set_takt(
                    ent.bpm if ent is not None and getattr(ent, "bpm", 0) else None)
                self._big_player.set_current_dance(self._playback.dance or None)
                self._big_player.on_new_track()   # zero the fader if armed…
                self._big_player.apply_tempo()    # …then push the resulting rate
                if start and self._big_player.tso_mode() and self._is_playing_mode():
                    pitched = self._equalize_heat_tempo(auto=True)
            # 🐂 A Paso Doble may be held back a few seconds after the dance is
            # called, so the couples stand before the first bar. Everything up
            # to here has happened — the file is open, pitched and levelled;
            # only the play() waits.
            hold = self._pd_start_hold() if start else 0.0
            # ⏳ The other way round: the dance is called into silence and the
            # music follows the voice. Asked BEFORE the play(), because that is
            # the play() it holds back.
            waiting = bool(start and not hold
                           and self._announce_start_first(ent))
            if start and not hold and not waiting:
                self._player.play()
            if self._big_player:
                # Qt may drop a rate set while the player was idle — re-assert.
                # Free when the early set stuck: apply_tempo skips a no-op.
                self._big_player.apply_tempo()
            if start and not hold and not waiting:
                self._fade_timer.start()
                # After play(): the announcement ducks what is running, so the
                # music has to be on its way already.
                self._maybe_announce_start(ent)
            self._now_playing.setText(
                (f"▶  {path.stem[:80]}") if start else (i18n.t("⏸  cued: %s") % path.stem[:74]))
            if self._big_player:
                meas = (float(getattr(getattr(ent, "features", None), "bpm", 0) or 0)
                        if ent is not None else 0.0)
                bits = [b for b in (
                    terms.DANCE_SHORT.get(self._playback.dance, self._playback.dance),
                    f"T{ent.bpm}" if ent is not None and getattr(ent, "bpm", 0) else "",
                    f"🥁 {meas:.0f} bpm" if meas > 0 else "",
                ) if b]
                self._big_player.set_now(path.stem, "  ·  ".join(bits))
                self._big_player.set_artwork(path, self._playing_m3u())
                self._big_player.set_gain(self._mix.gain)
                # Second try for the TSO pitch: the deck only knows which row is
                # playing once it has told us, so on some paths the early one
                # above found nothing to pitch against. Costs a gap — but a
                # wrongly pitched heat costs more.
                if (not pitched and start and self._big_player.tso_mode()
                        and self._is_playing_mode()):
                    self._equalize_heat_tempo(auto=True)
            self._sync_big_player_limit()
            self._refresh_next_up()
            self._show_preview(path)
            if start and hold:
                # …the wait counts down on the left panel, speaks the call if
                # the announcement is on, and starts the music (with its own
                # watchdog) when it is over.
                self._hold_pd_start(hold, path, ent)
            elif start and waiting:
                # …and this one waits for the voice that has just started,
                # silently: the hall is listening to the call.
                self._wait_for_announcement(path)
            elif start:
                # Watchdog: if the backend silently hangs in Loading/Stalled (it
                # happens on rapid source switches), retry the load once, then give
                # up cleanly instead of showing a forever-"playing" dead player.
                token = self._playback.token
                QTimer.singleShot(2000, lambda: self._check_playback(token, path))
            # ⏱ What the GUI thread spent before the backend took over. The
            # matching "media ready" line comes from _on_media_status, so a slow
            # start can be blamed on us or on the decoder without guessing.
            self._play_t0 = t0
            self._play_ready_logged = False
            log.info("⏱ Play requested\n"
                     "file: %s\n"
                     "blocking: %.0f ms", path.name, 1000 * (time.perf_counter() - t0))
        self._preview_src = None

    def _check_playback(self, token: int, path: Path, retried: bool = False):
        """Watchdog for `_play_or_stop`: verify playback really started; one
        retry, then a clean stop + status message. Stale tokens no-op."""
        if not self._player or token != self._playback.token:
            return
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            return   # playing — or deliberately paused by the user
        status = self._player.mediaStatus()
        if status in (QMediaPlayer.MediaStatus.EndOfMedia,
                      QMediaPlayer.MediaStatus.NoMedia):
            return   # finished or stopped meanwhile — nothing to rescue
        if not retried:
            log.warning("🔁 Playback stuck (status %s) — reloading\n"
                        "file: %s", status, path)
            self._player.stop()
            self._player.setSource(QUrl())
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self._player.play()
            QTimer.singleShot(2500, lambda: self._check_playback(token, path, True))
            return
        log.error("🔇 Playback did not start (status %s)\nfile: %s", status, path)
        self._reset_playback_ui(i18n.t("⚠ Could not play: %s") % path.name)

    def _reset_playback_ui(self, message: str):
        """Stop the player and put every play button / the status line back to
        idle — shared by the playback-error handler and the watchdog."""
        self._playback.token += 1
        self._stop_play_timer()
        if self._player:
            self._player.stop()
            self._player.setSource(QUrl())
        for t in self._all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()
        if self._preview:
            self._preview.hide()
        self._now_playing.setText("No song selected")
        if self._big_player:
            self._big_player.set_now("")
        self.statusBar().showMessage(message, 8000)

    def _on_player_error(self, _error, error_string: str):
        """A decode/backend failure used to leave the UI 'playing' silently —
        surface it and reset, so a broken file never looks like a stuck app."""
        src = self._player.source().toLocalFile() if self._player else ""
        log.error("🔇 Playback error\n"
                  "error: %s\n"
                  "file: %s", error_string or "unknown", src)
        self._reset_playback_ui(
            i18n.t("⚠ Playback failed: %s") % (error_string or i18n.t("unknown error")))

    def _show_preview(self, path: Path):
        """Pop the UltraMixer-style mini player under the row whose ▶ was clicked.
        Skipped when disabled in ⚙ Settings, in Playing mode (the big player
        already shows everything) or when playback didn't start from a deck
        (e.g. the Similar-Tracks dialog — its own window covers the decks)."""
        if (not self._preview or not self._settings.get("preview_player", True)
                or self._is_playing_mode()):
            return
        src = self._preview_src
        if src is None or src._current_play_row < 0:
            # Playback isn't anchored to a deck row (Similar-Tracks dialog, library
            # pane…). The overlay's slider stays wired to the shared player, so a
            # leftover overlay would keep ticking on the new track while its title
            # is frozen on the old one — hide it instead of leaving it stale.
            if self._preview.isVisible():
                self._preview.hide()
            return
        self._preview.show_for(src, src._current_play_row, path.stem)

    def _sync_preview_to_playback(self):
        """Pop the overlay for the song that's already playing — used when the
        preview player gets re-enabled in ⚙ Settings mid-playback."""
        if (not self._preview or not self._settings.get("preview_player", True)
                or self._is_playing_mode()
                or not self._player
                or self._player.playbackState()
                != QMediaPlayer.PlaybackState.PlayingState):
            return
        for t in self._all_tables:
            row = t._current_play_row
            if 0 <= row < len(t._row_meta) and t._row_meta[row]:
                entry = t._row_meta[row].entry
                if entry is not None:
                    self._preview.show_for(t, row, entry.path.stem)
                return

    def _preview_skip(self, step: int):
        """⏮/⏭ on the preview overlay / big player: play the previous / next
        song row of whichever table is currently playing (headers are skipped).
        Falls back to the event plan's column, then the library pane, when the
        preview started there."""
        # Whatever is being said belongs to the title we are leaving. Fast
        # skipping used to stack one announcement per step and read them all
        # out over the music that finally stayed.
        self._announcer.stop()
        for t in self._all_tables:
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

    def _disable_preview(self):
        """⚙ menu on the overlay: turn the preview player off and persist it."""
        self._settings["preview_player"] = False
        save_settings(self._settings)
        if self._preview:
            self._preview.hide()
        self.statusBar().showMessage(
            "Preview player disabled — re-enable it in ⚙ Settings.")

    def _on_playback_state(self, state):
        """(Re)starting via ⏯/▶ in the big player must restart the tick engine
        (countdown, fade ramp, PD highlight stop) if a stop had halted it — and
        the running row's ■/▶ follows the player, whoever pressed pause."""
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_wake_lock()
        if playing or state == QMediaPlayer.PlaybackState.PausedState:
            # StoppedState is deliberately skipped: it also fires on every track
            # switch, and the stop paths clear the row markers themselves.
            for t in self._all_tables:
                t.sync_play_glyph(playing)
        if not playing:
            return
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
                and self._play_panel.pd_highlight_stop()
                and self._pd_stop_at is None):
            self._ensure_pd_highlights(self._playback.path)

    def _on_stop_btn(self):
        """Stop button in the player bar — also resets every deck's play buttons."""
        self._stop_play_timer()
        # ⏹ means silence: a load the ⏭ rate limit still holds back must not
        # start after it, and a spoken call must not run on over it.
        self._pending_load = None
        self._load_timer.stop()
        self._announcer.stop()
        if self._player:
            self._playback.token += 1
            self._player.stop()
            self._player.setSource(QUrl())   # release the file (see _play_or_stop)
        for t in self._all_tables:
            t.on_playback_stopped()
        self._reset_aux_play_markers()
        if self._preview:
            self._preview.hide()
        self._now_playing.setText("No song selected")
        if self._big_player:
            self._big_player.set_now("")

    # ── ↩ Where a title was left ─────────────────────────────────────────────
    # One player serves every deck, so stepping away from a half-heard title is
    # the normal way to lose your place in it. These keep the place, in memory,
    # for as long as the app runs.

    # Both windows are the 10 s the rest of the player already counts in
    # (`_PLAYED_AFTER_MS`, the point a title counts as heard).
    _RESUME_MIN_MS = 10_000    # the first seconds are not a place to come back to
    _RESUME_TAIL_MS = 10_000   # stopped this near the end, a title is finished

    def remember_pos(self) -> bool:
        """Whether the ↩ switch on the Playing panel is on."""
        return bool(self._settings.get("remember_pos", False))

    def _set_remember_pos(self, on: bool):
        """The ↩ switch moved. Switching it off drops every mark: a tick left
        on a bar by a switch that is now off is a promise nothing will keep."""
        if not on and self._resume_pos:
            self._resume_pos.clear()
            self._refresh_resume_marks()

    def _resume_mark_for(self, path: Path) -> int | None:
        """Where `path` should be picked up again, or None.

        Only the big player spends a mark. The floating overlay is a pre-listen
        — a title tried there starts at its top and keeps the place it holds in
        the big player, so hearing a snippet while planning never costs the spot
        the set was actually left at.
        """
        if not self.remember_pos() or not self._is_playing_mode():
            return None
        return self._resume_pos.get(str(path))

    def _note_resume(self, path: Path, pos_ms: int, dur_ms: int):
        """Keep (or drop) the mark for `path` at `pos_ms`.

        Two guards decide whether there is anything worth coming back to: the
        opening seconds are not a place anyone wants back, and a title stopped
        on its last note is one that finished — resuming there would play the
        run-out and call it a title.
        """
        key = str(path)
        done = dur_ms > 0 and pos_ms >= dur_ms - self._RESUME_TAIL_MS
        if pos_ms < self._RESUME_MIN_MS or done:
            self._resume_pos.pop(key, None)
        else:
            self._resume_pos[key] = int(pos_ms)
        self._refresh_resume_marks(path)

    def _clear_resume(self, path: Path | None):
        """Forget where `path` stood — it has just been heard to the end."""
        if path is not None and self._resume_pos.pop(str(path), None) is not None:
            self._refresh_resume_marks(path)

    def _remember_stop_point(self):
        """Note where the running title stands, just before it is stopped.

        Only while it really is on the player: `_load_track` is re-entered once
        a track's loudness is known, and by then the deck is stopped and
        position() reads 0 — recording that would wipe the mark instead of
        setting it.
        """
        if not self.remember_pos() or self._player is None:
            return
        if not self._is_playing_mode():
            # Only the big player keeps a place. The floating overlay is for a
            # quick listen while planning — every row tried there would leave a
            # badge behind, and none of them is a title anyone comes back to.
            return
        path = self._playback.path
        if path is None:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            return
        self._note_resume(path, self._player.position(), self._player.duration())

    def _refresh_resume_marks(self, path: Path | None = None):
        """Repaint the ↩ badges on the deck rows.

        Only the rows carry a mark: the seek bar would draw its tick exactly
        where the playhead already stands, since a picked-up title starts there.

        `path` only says which title moved — every deck gets the whole dict and
        repaints the rows whose badge actually changed.
        """
        for t in self._all_tables:
            t.set_resume_marks(self._resume_pos)

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

    def _on_media_status(self, status):
        """Reset play buttons when a song finishes playing naturally."""
        if (not self._play_ready_logged and self._play_t0 is not None
                and status in (QMediaPlayer.MediaStatus.LoadedMedia,
                               QMediaPlayer.MediaStatus.BufferedMedia)):
            # ⏱ Click → decodable media: everything after our own blocking work.
            self._play_ready_logged = True
            log.info("⏱ Media ready\n"
                     "file: %s\n"
                     "total: %.0f ms",
                     self._playback.path.name if self._playback.path else "?",
                     1000 * (time.perf_counter() - self._play_t0))
        if (self._resume_seek_ms is not None
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
            self.statusBar().showMessage(
                i18n.t("↩ Picked up at %s.") % f"{ms // 60_000}:{ms // 1000 % 60:02d}", 4000)
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
                for t in self._all_tables:
                    t.on_playback_stopped()
                self._reset_aux_play_markers()
                return
            self._queue_auto_advance()   # song shorter than the play length
            if self._between.pending is not None:
                self._show_pause_status()
            else:
                self._now_playing.setText("No song selected")
                if self._big_player:
                    self._big_player.set_now("")
            if self._preview:
                self._preview.hide()
            for t in self._all_tables:
                t.on_playback_stopped()
            self._reset_aux_play_markers()

    # ── 🖥 Presenter screen ───────────────────────────────────────────────────

    def _toggle_presenter(self, on: bool):
        """🖥 Presenter: open (or close) the hall-sized second screen showing
        the running title, its dance and what comes next."""
        self._presenter_lost = None     # a hand on the toggle decides from here
        if not on:
            if self._presenter is not None:
                self._presenter.close()
            return
        if self._presenter is None:
            self._presenter = PresenterWindow(self._presenter_state, self)
            self._presenter.closed.connect(self._on_presenter_closed)
            # 🎛 The optional transport on the screen itself, for the desk that
            # drives the presenter machine — same actions as the player card.
            self._presenter.playing_cb = self._is_player_running
            self._presenter.prevRequested.connect(lambda: self._preview_skip(-1))
            self._presenter.playPauseRequested.connect(self._presenter_play_pause)
            self._presenter.nextRequested.connect(self._on_player_next)
            self._presenter.breakRequested.connect(self._on_to_pause)
            self._presenter.duckToggled.connect(self._set_desk_duck)
            self._presenter.controlsToggled.connect(self._on_presenter_controls)
            self._presenter.lastToggled.connect(self._on_presenter_last)
            self._presenter.set_controls_shown(
                bool(self._settings.get("presenter_controls", False)))
            self._presenter.set_last_played_shown(
                bool(self._settings.get("presenter_last_played", False)))
            self._presenter.set_theme(self._play_panel.presenter_theme())
            self._presenter.timetableRequested.connect(self._edit_timetable)
            self._presenter.set_timetable(load_timetable())
            self._presenter.set_now_offset(self._now_offset)
            self._presenter.set_ducked(self._mix.desk != 1.0)
        self._presenter.show_on_screen(self._play_panel.presenter_screen())
        self._refresh_wake_lock()

    def _is_player_running(self) -> bool:
        """Whether music is coming out right now — the ⏯ glyph follows it."""
        return bool(self._player) and (
            self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

    def _is_player_stopped(self) -> bool:
        """Stopped, not paused — a cued title the deck row shows as ▶."""
        return bool(self._player) and (
            self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState)

    def _presenter_play_pause(self):
        if self._big_player:
            self._big_player.toggle_play()

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

    def _on_presenter_last(self, on: bool):
        """🕘 The last-played line was switched on the screen itself — remember
        it, the way the transport is remembered."""
        self._settings["presenter_last_played"] = bool(on)
        save_settings(self._settings)

    def _on_presenter_controls(self, on: bool):
        self._settings["presenter_controls"] = bool(on)
        save_settings(self._settings)

    def _on_presenter_closed(self):
        """The window can also go away via Esc or its ✕ — un-press the button."""
        self._presenter = None
        self._play_panel.set_presenter_on(False)
        self._refresh_wake_lock()

    def _edit_timetable(self):
        """🕒 Type the evening's running order. Saved to its own JSON file and
        pushed straight onto an open presenter screen — on the night there is
        no time to close and reopen it."""
        from player.timetable_dialog import TimetableDialog
        dlg = TimetableDialog(load_timetable(), self,
                              now_offset=self._now_offset)
        dlg.changed.connect(lambda: self._preview_timetable(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            # Everything typed went onto the screen as it was typed, so a
            # cancelled draft has to be taken off it again.
            self._preview_timetable(None)
            return
        table = dlg.timetable()
        save_timetable(table)
        # The clock the page runs on is not part of the programme and is not
        # saved with it — it belongs to this one evening.
        self._now_offset = dlg.now_offset()
        if self._presenter is not None:
            self._presenter.set_timetable(table)
            self._presenter.set_now_offset(self._now_offset)
        shifted = ""
        if self._now_offset is not None:
            at = datetime.now() + self._now_offset
            shifted = i18n.t(", running at %s") % at.strftime("%H:%M")
        _show_toast(self, i18n.t("🕒  Timetable saved — %d entries") % len(table.entries)
                    + (i18n.t(", fading every %ss") % table.rotate_secs
                       if table.rotate else "") + shifted)

    def _preview_timetable(self, dlg):
        """Put a half-typed programme on the presenter screen while the dialog
        is still open — the hall is the only place it can really be judged, and
        walking back to the desk to save between every line is not a thing
        anybody does on the night. `dlg` None puts the saved one back."""
        if self._presenter is None:
            return
        if dlg is None:
            self._presenter.set_timetable(load_timetable())
            self._presenter.set_now_offset(self._now_offset)
        else:
            self._presenter.set_timetable(dlg.timetable())
            self._presenter.set_now_offset(dlg.now_offset())

    def _theme_presenter(self, key: str):
        """Another palette picked: repaint an open presenter screen in it, and
        remember the choice for the next time it's opened."""
        if self._presenter is not None:
            self._presenter.set_theme(key)
        self._save_play_settings()

    def _move_presenter(self, index: int):
        """Another monitor picked: move an open presenter screen over, and
        remember the choice for the next time it's opened."""
        if self._presenter is not None:
            self._presenter.show_on_screen(index)
        self._save_play_settings()

    def _on_screen_removed(self, screen):
        """A monitor went away. A presenter standing on it is closed rather
        than left to Windows, which drops a full-screen window onto the desk's
        own screen — over the controls, mid-heat. It comes back with that
        monitor (`_on_screen_added`): a knocked cable is not a decision."""
        if self._presenter is None:
            return
        on = self._presenter.screen()
        if on is None or on.name() != screen.name():
            return
        self._play_panel.set_presenter_on(False)   # → _toggle_presenter closes it
        self._presenter_lost = screen.name()
        log.warning("🖥 The presenter's screen was disconnected\n"
                    "screen: %s", screen.name())
        self.statusBar().showMessage(
            "🖥 The presenter's screen was disconnected — it opens again when "
            "the screen is back.", 8000)

    def _on_screen_added(self, screen):
        """The monitor a presenter was closed for is back: put it up again."""
        if not self._presenter_lost or screen.name() != self._presenter_lost:
            return
        self._presenter_lost = None
        if self._presenter is not None:
            return      # opened again by hand in the meantime
        self._play_panel._fill_screens()   # the panel's own refill may come later
        self._play_panel.set_presenter_on(True)

    @staticmethod
    def _row_dance_name(table: PlaylistTable, row: int) -> str:
        """Spelled-out dance of a grid row ('LW' → 'Langsamer Walzer')."""
        meta = table._row_meta.at(row)
        code = meta.dance if meta is not None else ""
        return dance_name(code, code)

    def _pause_on_screen(self) -> bool:
        """Whether the running auto-advance pause is one the hall should see.

        With the ⏸ switch off the "pause" is zero seconds long — the presenter
        would flash its ⏸ mark for one refresh between two titles, which reads
        as a fault rather than as a break. Extending it by hand (⏱➕) makes it
        a real one, so `_between.shown` is what the desk decided, not the clock."""
        return self._between.pending is not None and self._between.shown

    def _presenter_upcoming(self, count: int) -> list[tuple[str, str]]:
        """(dance, title) of the next `count` songs after the running one.
        During the auto-advance pause nothing is playing, so no table can
        resolve a follower — the armed advance is then the first entry."""
        out: list[tuple[str, str]] = []
        table = None
        for t in self._all_tables:
            if t._current_play_row >= 0:
                table, row = t, t._current_play_row
                break
        if table is None:
            nxt = _live_target(self._between.pending)
            if nxt is None:
                return out
            table, row, path = nxt
            if self._pause_on_screen():
                out.append((self._row_dance_name(table, row), path.stem))
            # …and without a visible pause the hero line already shows it, so
            # the queue starts behind it instead of naming it twice.
        while len(out) < count:
            row, path = table.next_song_row(row, +1)
            if row < 0 or path is None:
                break
            out.append((self._row_dance_name(table, row), path.stem))
        return out

    def _presenter_last(self) -> tuple[str, str]:
        """(dance, title) of what was played before what the hero line shows.

        While a title runs that is the one remembered from the handover. When
        nothing is sounding — a break, or the moment between two songs where
        the hero already names the one about to start — the title that just
        ended is the last played, and that one is still the loaded one."""
        if self._pause_on_screen() or self._between.pending is not None:
            if self._playback.path is not None:
                return (dance_name(self._playback.dance, self._playback.dance),
                        self._playback.path.stem)
        return self._last_played or ("", "")

    def _presenter_times(self) -> tuple[str, str, bool, float]:
        """(played, left, ending, fraction) of the running title — '▶ 01:39' /
        '− 00:38', the flag that makes the presenter blink the last seconds red,
        and how far the progress bar has run. 'left' counts down to whatever
        ends the title: the play length, a 🐂 highlight stop, or the track's own
        end."""
        if self._between.pending is not None:
            if not self._between.shown:
                # A zero-length pause: the next title is already loading, and
                # the old one's position would be all the player could report.
                return "", "", False, 0.0
            left = max(0.0, self._between.advance_at - time.monotonic())
            return "", f"−  {_mmss(left)}", False, 0.0
        if self._player is None or self._playback.path is None:
            return "", "", False, 0.0
        rate = max(0.01, self._player.playbackRate())
        pos = self._player.position() / 1000.0
        played = audible_played_secs(self._player.position(),
                                     self._playback.offset_ms, rate)
        left = None
        if self._pd_runs_to_its_highlight():
            if self._pd_stop_at is not None:
                left = (self._pd_stop_at - pos) / rate
        elif self._play_limit_secs() > 0:
            left = self._play_limit_secs() - played
        if left is None:
            dur = self._player.duration() / 1000.0
            left = (dur - pos) / rate if dur > 0 else 0.0
        left = max(0.0, left)
        total = played + left
        return (f"▶  {_mmss(played)}", f"−  {_mmss(left)}", left <= _ENDING_AT,
                played / total if total > 0 else 0.0)

    def _presenter_state(self) -> tuple[str, str, tuple[str, str, bool, float],
                                        list[tuple[str, str]], tuple[str, str]]:
        """What the presenter screen shows: (dance, title, times, next songs,
        last played)."""
        if self._pause_on_screen():
            now = (PAUSE_TEXT, "")
        elif _live_target(self._between.pending) is not None:
            # No pause configured — show what is about to start instead of the
            # break mark: the advance fires within a refresh or two, and a ⏸
            # blinking on and off between every two titles reads as a fault.
            table, row, path = _live_target(self._between.pending)
            now = (self._row_dance_name(table, row), path.stem)
        elif self._playback.path is not None:
            now = (dance_name(self._playback.dance, self._playback.dance),
                   self._playback.path.stem)
        else:
            now = ("", "")
        return (now[0], now[1], self._presenter_times(),
                self._presenter_upcoming(3), self._presenter_last())
