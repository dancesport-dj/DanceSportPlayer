"""🖥 The presenter screen: opening it, what it shows of the running title and
the ones to come, its timetable, its theme and the monitor it stands on.

Extracted from player/window/main_player.py as a MainWindow mixin.
"""
import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog

from planner import i18n
from planner.terms import dance_name
from player.audio.mix import desk_duck_pct
from shared.audio.playback import audible_played_secs
from shared.stores import save_settings
from shared.widgets import _show_toast
from player.presenter.presenter import PAUSE_TEXT, PresenterWindow
from player.presenter.timetable import load_timetable, save_timetable
from player.window.main_pause import _live_target

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
    from gui.table.playlist_table import PlaylistTable
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.player")


# 🖥 From this many seconds left, the presenter screen blinks the remaining
# time red — long enough for the floor to finish the figure they are in.
_ENDING_AT = 12.0


def _mmss(secs: float) -> str:
    """Seconds as 01:39 — zero-padded, so the clock doesn't jump in width."""
    s = max(0, int(secs))
    return f"{s // 60:02d}:{s % 60:02d}"


class PresenterMixin(MainWindowHost):
    """🖥 The presenter screen and what it shows."""

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
            self._presenter.set_theme(self._settings.get("presenter_theme", ""))
            self._presenter.timetableRequested.connect(self._edit_timetable)
            self._presenter.set_timetable(load_timetable())
            self._presenter.set_now_offset(self._now_offset)
            self._presenter.set_ducked(self._mix.desk != 1.0)
            self._presenter.set_duck_level(desk_duck_pct(self._settings))
            guests = getattr(self, "_guests", None)
            if guests is not None:   # 📨 open guest requests show their code
                guests.sync_presenter()
        self._presenter.show_on_screen(self._play_panel.presenter_screen())
        self._refresh_wake_lock()

    def _presenter_play_pause(self):
        if self._big_player:
            self._big_player.toggle_play()

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
        from player.presenter.timetable_dialog import TimetableDialog
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
        """Another palette picked in ⚙ Settings → 🎨 Look: repaint an open
        presenter screen in it. The settings dialog has saved it already."""
        if self._presenter is not None:
            self._presenter.set_theme(key)

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
        """(dance, title) of the next `count` songs after the running one."""
        return [(self._row_dance_name(table, row), path.stem)
                for table, row, path in self._upcoming_rows(count)]

    def _upcoming_rows(self, count: int) -> list:
        """(table, row, path) of the next `count` songs after the running one.
        During the auto-advance pause nothing is playing, so no table can
        resolve a follower — the armed advance is then the first entry."""
        out: list = []
        table = None
        for t in self._deckset.all_tables:
            if t._current_play_row >= 0:
                table, row = t, t._current_play_row
                break
        if table is None:
            nxt = _live_target(self._between.pending)
            if nxt is None:
                return out
            table, row, path = nxt
            if self._pause_on_screen():
                out.append((table, row, path))
            # …and without a visible pause the hero line already shows it, so
            # the queue starts behind it instead of naming it twice.
        while len(out) < count:
            row, path = table.next_song_row(row, +1)
            if row < 0 or path is None:
                break
            out.append((table, row, path))
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
        span = self._presenter_span()
        if span is None:
            return "", "", False, 0.0
        _rate, played, left = span
        total = played + left
        return (f"▶  {_mmss(played)}", f"−  {_mmss(left)}", left <= _ENDING_AT,
                played / total if total > 0 else 0.0)

    def _presenter_span(self) -> tuple[float, float, float] | None:
        """(rate, played, left) in floor seconds of the title the presenter's
        bar runs against, or None when no title is up."""
        if self._player is None or self._playback.path is None:
            return None
        rate = max(0.01, self._player.playbackRate())
        pos = self._player.position() / 1000.0
        played = audible_played_secs(self._player.position(),
                                     self._playback.offset_ms, rate)
        left = None
        if self._pd_runs_to_its_highlight():
            if self._pd_stop_at is not None:
                left = (self._pd_stop_at - pos) / rate
        elif self._play_limit_secs() > 0:
            left = self._play_end_secs() - played
        if left is None:
            dur = self._player.duration() / 1000.0
            left = (dur - pos) / rate if dur > 0 else 0.0
        return rate, played, max(0.0, left)

    def _seek_fraction(self, fraction: float):
        """📱 Seek to a point on the presenter's bar: 0 is where the music
        started (after a 🔇 skipped intro), 1 is where the title ends — the
        play length, a 🐂 highlight stop, or the file's own end."""
        if self._between.pending is not None:
            return
        span = self._presenter_span()
        if span is None or self._player is None:
            return
        rate, played, left = span
        heard = max(0.0, min(1.0, fraction)) * (played + left)
        self._player.setPosition(int(round(self._playback.offset_ms + heard * rate * 1000)))

    def _presenter_state(self) -> tuple[str, str, tuple[str, str, bool, float],
                                        list[tuple[str, str]], tuple[str, str]]:
        """What the presenter screen shows: (dance, title, times, next songs,
        last played)."""
        if self._pause_on_screen():
            now = (PAUSE_TEXT, "")
        elif (target := _live_target(self._between.pending)) is not None:
            # No pause configured — show what is about to start instead of the
            # break mark: the advance fires within a refresh or two, and a ⏸
            # blinking on and off between every two titles reads as a fault.
            table, row, path = target
            now = (self._row_dance_name(table, row), path.stem)
        elif self._playback.path is not None:
            now = (dance_name(self._playback.dance, self._playback.dance),
                   self._playback.path.stem)
        else:
            now = ("", "")
        return (now[0], now[1], self._presenter_times(),
                self._presenter_upcoming(3), self._presenter_last())
