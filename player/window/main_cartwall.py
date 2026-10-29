"""🎛 Cartwall wiring: the dock, the toolbar toggle and cartwall.json.

Only wiring lives here. Every Qt event handler belongs to the widgets in
player.widgets.cartwall — QMainWindow comes first in MainWindow's bases, so anything Qt
delivers by virtual dispatch would never reach a mixin method.
"""
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from planner import i18n
from planner.music.paths import resolve_file
from planner.playing import cartwall as pc
from player.audio.cart_voices import CartVoices
from player.audio.mix import cart_duck_level
from player.widgets.cartwall import CartwallWidget
from player.window.main_pause import live_target
from shared.stores import load_cartwall_file, save_cartwall_file, save_settings

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object
try:
    from PySide6.QtMultimedia import QMediaPlayer
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

log = logging.getLogger("dancesport.gui.cartwall")

CART_DOCK = "cartwall_dock"     # objectName — QMainWindow.restoreState needs one


def paso_comes_next(between) -> bool:
    """The armed auto-advance (`between.pending`) starts a Paso Doble."""
    nxt = live_target(between.pending) if between is not None else None
    if nxt is None:
        return False
    meta = nxt[0]._row_meta.at(nxt[1])
    return meta is not None and meta.dance == "PD"


class CartwallMixin(MainWindowHost):
    """The 🎛 sample-pad wall: pads that fire over the running deck music."""

    def _build_cartwall(self):
        """Create the wall, its dock and its audio pool, and load the saved wall."""
        self._cartwall = CartwallWidget()
        self._cartwall.keysRequested.connect(
            lambda: self.open_desk_keys_window(over=self._cartwall, tab=1))
        self._cartwall.settingsRequested.connect(
            lambda: self._open_settings(open_cartwall=True))
        self._cartwall.padClicked.connect(self._on_pad_clicked)
        self._cartwall.changed.connect(self._save_cartwall)
        self._cartwall.stopAll.connect(self._on_cart_stop_all)
        self._cartwall.padRefreshed.connect(self._on_cart_pad_refreshed)
        self._cartwall.previewVolume.connect(self._on_cart_preview_volume)
        self._cartwall.previewFire.connect(self._on_cart_preview_fire)
        self._cartwall.fadeChanged.connect(self._on_cart_wall_fade)
        self._cartwall.set_level(self._mix.cart)
        self._cartwall.levelChanged.connect(self._set_cart_volume)
        self._cartwall.muteChanged.connect(self._set_cart_muted)
        self._cartwall.set_vol_buttons_shown(
            self._settings.get("vol_buttons", True) is not False)

        # A dock rather than a tab: the wall has to sit BESIDE the playlists —
        # you fire a Tusch while looking at the running heat, not instead of it.
        # Dockable to any edge, floatable onto a second screen, and the splitter
        # between it and the decks resizes it.
        self._cart_dock = QDockWidget("🎛  Cartwall", self)
        self._cart_dock.setObjectName(CART_DOCK)
        self._cart_dock.setWidget(self._cartwall)
        self._cart_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._cart_dock)
        self._wire_cart_dock()
        self._cart_dock.setVisible(self._cartwall_shown)

        if self._player is not None:
            self._cart_voices = CartVoices(self)
            self._cart_voices.padStopped.connect(self._on_cart_pad_stopped)
            self._cart_voices.padEnded.connect(self._on_cart_pad_ended)
            self._cart_voices.padFading.connect(self._cartwall.set_fading)
            self._cart_voices.padHeld.connect(self._cartwall.set_held)
            self._cart_voices.padTick.connect(self._on_cart_tick)
            self._cart_voices.activeChanged.connect(self._on_cart_active)
            self._cart_voices.activeChanged.connect(self._audio_device.on_activity)
            self._cart_voices.duckChanged.connect(self._on_cart_duck_changed)
            self._cart_voices.wantsDevice.connect(self._audio_device.ensure)
            self._audio_device.sync()   # 🔊 the wall's own output, if one is chosen
            self._cartwall.padsMoved.connect(self._cart_voices.rekey)
            self._cartwall.padSeekRequested.connect(self._cart_voices.seek)
            self._apply_volume()      # push the desk level into the fresh pool
            self.apply_cart_settings()
        self._load_cartwall()

    # ── the dock and the toolbar toggle ──────────────────────────────────────
    def _wire_cart_dock(self):
        """Everything the dock and the wall have to tell each other."""
        self._cart_dock.visibilityChanged.connect(self._on_cart_dock_visibility)
        self._cart_dock.dockLocationChanged.connect(self._on_cart_dock_moved)
        # Dragged out or put back — by the title bar or by 📌, both arrive here,
        # so the button is never left standing on a wall that is already docked.
        self._cart_dock.topLevelChanged.connect(self._cartwall.set_floating)
        self._cartwall.dockRequested.connect(self._on_cart_dock_back)
        self._cartwall.set_floating(self._cart_dock.isFloating())

    def _on_cart_dock_back(self):
        """📌 on the wall: snap the floating wall back into the main window.

        Qt puts it back at the edge it last sat at. The window is raised with
        it — the wall may have been floating on a second screen, and the main
        window behind everything else there."""
        if not self._cart_dock.isFloating():
            return
        self._cart_dock.setFloating(False)
        self.raise_()
        self.statusBar().showMessage("📌 Cartwall docked")
        log.info("📌 Cartwall snapped back\n"
                 "area: %s", self.dockWidgetArea(self._cart_dock).name)

    def _on_cartwall_toggled(self, on: bool):
        self._cartwall_shown = bool(on)
        self._settings["cartwall_pane"] = self._cartwall_shown
        save_settings(self._settings)
        self._cart_dock.setVisible(self._cartwall_shown)
        if on:
            self._cartwall.refresh_missing()
        self.statusBar().showMessage(
            "🎛 Cartwall shown" if on else "🎛 Cartwall hidden")

    def _on_cart_dock_visibility(self, visible: bool):
        """Closing the dock with its own ✕ has to leave the toolbar toggle telling
        the truth. Ignored while the window is not up yet or is minimised — Qt
        calls every dock invisible then, and neither is the user closing one."""
        if (not self.isVisible() or self.isMinimized()
                or visible == self._cart_btn.isChecked()):
            return
        self._cart_btn.setChecked(visible)      # runs _on_cartwall_toggled

    def _on_cart_dock_moved(self, area):
        """A side edge gives the wall height and no width, a top or bottom edge
        the other way round — so the wall turns to match. pc.transpose carries
        the pads along, so dragging it back restores the wall exactly."""
        side = area in (Qt.DockWidgetArea.LeftDockWidgetArea,
                        Qt.DockWidgetArea.RightDockWidgetArea)
        # Not an edit: the startup dock restore lands here too, and a file this
        # build could not read must survive it.
        self._cart_turning = True
        try:
            self._cartwall.set_portrait(side)
        finally:
            self._cart_turning = False
        log.info("🎛 Cartwall re-docked\n"
                 "area: %s\n"
                 "grid: %d × %d", area.name, *self._cartwall.grid())

    # ── firing ───────────────────────────────────────────────────────────────
    def _on_pad_clicked(self, key):
        """Tap = fire, tap the same pad again = fade it out."""
        pad = self._cartwall.pad_at(key)
        if pad is None:
            return
        if self._cart_voices is None:
            self.statusBar().showMessage(
                "🔇 No audio backend — the cartwall cannot play here.")
            return
        run = self._cartwall.queue_run()
        if self._cart_voices.is_playing(key):
            if run is not None and run[0] == key:
                self._cartwall.end_queue_run()   # stopping the run's pad stops the run
            self._cart_voices.stop(key)
            return
        if pad.queue:
            # ▶ A queued pad starts the queue from itself; a run already going
            # is replaced, so the pad it was playing ends without handing on.
            self._cart_run_from(key, pad)
            return
        if pad.stops_others:
            self._cartwall.end_queue_run()       # it takes the floor from the run too
        # Checked on the tap, not on a timer: a stick that came up as a different
        # drive letter must say so instead of firing silence.
        found = resolve_file(pad.path, self._settings)
        if found is None:
            self._cartwall.refresh_missing()
            self.statusBar().showMessage(i18n.t("⚠️ Sample not found: %s") % pad.path)
            log.warning("🎛 Pad file is gone\n"
                        "path: %s", pad.path)
            return
        # The copy found fires; the pad keeps its own path for when the stick
        # comes back under its old letter.
        fired = self._cart_voices.fire(key, replace(pad, path=str(found)))
        if fired:
            self._cartwall.set_playing(key, True)
        elif fired is False:   # None: a double-click's second half
            self.statusBar().showMessage(
                "🎛 No free pad voice — every voice holds a looping pad.")

    def _cart_run_from(self, key, pad, *, tapped=True):
        """▶ Play the queue on from this pad: the first one, counting from it,
        whose file is there. Its own 🔁 is not heard — a looping pad would
        hold the queue up for good — and every other flag is."""
        voices = self._cart_voices
        if voices is None:
            return
        for _ in range(len(pc.queued(self._cartwall.pages()))):
            found = resolve_file(pad.path, self._settings)
            if found is not None:
                fired = voices.fire(
                    key, replace(pad, path=str(found), loop=False), tapped=tapped)
                if fired:
                    self._cartwall.set_playing(key, True)
                    self._cartwall.set_queue_run(key, pad.queue)
                elif fired is False:
                    self._cartwall.end_queue_run()
                    self.statusBar().showMessage(
                        "🎛 No free pad voice — every voice holds a looping pad.")
                return
            self.statusBar().showMessage(
                i18n.t("⚠️ Sample not found, skipped: %s") % pad.path)
            log.warning("🎛 Queued pad file is gone\n"
                        "path: %s", pad.path)
            hit = pc.queue_next(self._cartwall.pages(), pad.queue)
            if hit is None:
                break
            page, (row, col), pad = hit
            key = (page, row, col)
        self._cartwall.end_queue_run()
        self._cartwall.refresh_missing()
        self.statusBar().showMessage(
            i18n.t("⚠️ Queue stopped: none of its samples were found"))

    def _start_pause_pads(self):
        """⏸ A pause between two titles: the ▶ queue plays from its first 🎶
        background pad, unless a run is going already. Only a background pad
        steps back by itself when the next title starts."""
        if self._cart_voices is None or self._cartwall.queue_run() is not None:
            return
        for page, (row, col), pad in pc.queued(self._cartwall.pages()):
            if pad.background:
                self._cart_run_from((page, row, col), pad, tapped=False)
                return

    def _on_cart_pad_ended(self, key):
        """A pad ran out on its own. If it was the run's, the next one plays."""
        run = self._cartwall.queue_run()
        if run is None or run[0] != key:
            return
        hit = pc.queue_next(self._cartwall.pages(), run[1])
        if hit is None:
            self._cartwall.end_queue_run()
            return
        page, (row, col), pad = hit
        self._cart_run_from((page, row, col), pad, tapped=False)

    def _on_cart_pad_stopped(self, key):
        self._cartwall.set_playing(key, False)

    def _on_cart_stop_all(self):
        self._cartwall.end_queue_run()
        if self._cart_voices is not None:
            self._cart_voices.stop_all()

    def _on_cart_pad_refreshed(self, key, pad):
        """Volume / loop changed in the pad dialog — apply it to a live voice at
        once, so dragging the slider on a running bed is audible."""
        if self._cart_voices is not None:
            self._cart_voices.refresh_pad(key, pad)

    def _on_cart_preview_volume(self, key, level: float):
        """The pad dialog's volume slider, applied to the running voice as it
        moves — you cannot pick a level for a bed without hearing it under the
        music. Nothing is stored: Cancel leaves the pad's trim alone."""
        if self._cart_voices is not None:
            self._cart_voices.preview_volume(key, level)

    def _on_cart_preview_fire(self, key, on: bool):
        """▶ in the pad dialog. It goes through the normal fire path, so a pad
        that is already running is left alone and the duck behaves as usual."""
        if self._cart_voices is None:
            self.statusBar().showMessage(
                "🔇 No audio backend — the cartwall cannot play here.")
            return
        if on:
            pad = self._cartwall.pad_at(key)
            found = resolve_file(pad.path, self._settings) if pad is not None else None
            if (pad is not None and found is not None
                    and self._cart_voices.fire(key, replace(pad, path=str(found)))):
                self._cartwall.set_playing(key, True)
        elif self._cart_voices.is_playing(key):
            self._cart_voices.stop(key)

    def _on_cart_wall_fade(self, ms: int):
        if self._cart_voices is not None:
            self._cart_voices.set_wall_fade(ms)

    def apply_cart_settings(self):
        """⚙ Settings ▸ 🎛 Cartwall, as far as the wall's audio follows it:
        how far a pad ducks the music, whether a starting title pauses 🎶
        background pads or only mutes them, and how fast they dip and come back."""
        self._mix.set_cart_duck(cart_duck_level(self._settings))
        if "cartwall" in self._mix.duck_reasons:
            self._set_duck_reason("cartwall", True)   # a pad ducking now moves to it
        pauses = pc.background_pauses(self._settings)
        voices = getattr(self, "_cart_voices", None)
        if voices is not None:
            voices.set_background_pauses(pauses)
            voices.set_background_fade_in(pc.background_fade_in_ms(self._settings))
            voices.set_background_fade_out(pc.background_fade_out_ms(self._settings))
            voices.set_background_fire_fade(pc.background_fire_fade_ms(self._settings))
            voices.set_background_hold(pc.background_hold_ms(self._settings))
        wall = getattr(self, "_cartwall", None)
        if wall is not None:
            wall.set_background_pauses(pauses)   # the pad dialog's 🎶 wording
            wall.set_background_volume(pc.background_volume(self._settings))
            wall.refresh_missing()   # the search folders may have changed

    def _file_check_for_wall(self):
        """A pad is red only when 🧭's search finds its file nowhere either.
        The settings are read on every check, so a changed search folder
        counts from the next refresh on."""
        self._cartwall.set_file_check(
            lambda p: resolve_file(p, self._settings) is not None)

    def cart_wall_settings(self) -> dict:
        """The wall's fade-out and colour, for ⚙ Settings ▸ 🎛 Cartwall:
        they are kept in cartwall.json, not with the settings."""
        wall = getattr(self, "_cartwall", None)
        if wall is None:
            return {}
        return {"cart_fade_ms": wall.fade_ms(),
                "cart_wall_colour": wall.default_colour()}

    def apply_cart_wall(self, vals: dict):
        """…and back onto the wall, which saves them in its file."""
        wall = getattr(self, "_cartwall", None)
        if wall is None:
            return
        if "cart_fade_ms" in vals:
            wall.set_fade_ms(vals["cart_fade_ms"])
        if "cart_wall_colour" in vals:
            wall.set_default_colour(vals["cart_wall_colour"])

    def _on_cart_active(self, count: int):
        self._cartwall.set_active(count)

    def _on_cart_duck_changed(self, on: bool):
        self._set_duck_reason("cartwall", on)

    def _cart_follow_deck(self, state):
        """🎶 Hung on the deck's playbackStateChanged (see _deck_slots), so it
        moves to the other player when a crossfade swaps them — and on the
        pause music's: that is music too, and a background pad gives way to
        it the same way. Whichever of the two changed, both are asked.

        🐂 Also called when a Paso Doble's wait starts and ends: the deck is
        stopped through it, but the couples are walking on to the call, so
        the bed stays down unless ⚙ Settings ▸ 🎛 Cartwall lets it back.
        So does a title waiting for the bed to fade out (bed_wait): it is
        on its way down for that title."""
        voices = getattr(self, "_cart_voices", None)
        if voices is None:
            return
        # 🐂 …and so is the auto-advance pause running into a Paso Doble with
        # no 'Start after': the bed rose in it and the PD started over it.
        # Likewise a Paso Doble cued for ⏯ with ⏭ Auto off. With a wait the
        # bed may come up in between — the wait dips it out again.
        playback = getattr(self, "_playback", None)
        settings = getattr(self, "_settings", {})
        before_pd = (paso_comes_next(getattr(self, "_between", None))
                     or (getattr(self, "_cued", False) and playback is not None
                         and playback.dance == "PD"))
        pd_wait = ((getattr(self, "_pd_hold", None) is not None
                    and pc.background_quiet_in_pd_wait(settings))
                   or (before_pd and pc.background_quiet_before_pd(settings)))
        bed_wait = playback is not None and playback.bed_wait is not None
        playing = QMediaPlayer.PlaybackState.PlayingState
        player = getattr(self, "_player", None)
        voices.set_music_playing(
            pd_wait or bed_wait or state == playing
            or (player is not None and player.playbackState() == playing))

    def _on_cart_tick(self, rows):
        for key, ms_left, frac in rows:
            self._cartwall.set_remaining(key, ms_left, frac)

    def _cartwall_shutdown(self):
        """Release every sample file before the widgets go — a looping bed can
        hold a handle open for an hour, and WMF keeps it until told otherwise."""
        voices = getattr(self, "_cart_voices", None)
        if voices is not None:
            voices.shutdown()

    # ── persistence ──────────────────────────────────────────────────────────
    def _load_cartwall(self):
        doc = pc.load_doc(load_cartwall_file())
        self._cart_file_foreign = not doc.ok
        if not doc.ok:
            log.warning("🎛 cartwall.json is not a wall this build understands\n"
                        "action: starting empty, and NOT overwriting the file")
        self._file_check_for_wall()
        self._cartwall.set_wall(doc.grid, doc.pages, doc.page, doc.colour,
                                doc.fade_ms, doc.slot_keys)
        log.info("🎛 Cartwall loaded\n"
                 "grid: %d × %d\n"
                 "pages: %d\n"
                 "pads: %d", doc.grid[0], doc.grid[1], len(doc.pages),
                 pc.pad_count(doc.pages))

    def _save_cartwall(self, *, edit: bool = True):
        """Write the wall — except over a file this build could not read, which
        stays untouched until the user chooses to start over by editing the
        wall. Neither 📌 (`edit=False`) nor the wall turning to fit its dock
        edge is that choice."""
        if getattr(self, "_cart_file_foreign", False):
            if not edit or getattr(self, "_cart_turning", False):
                return
            self._cart_file_foreign = False
        save_cartwall_file(pc.dump_doc(self._cartwall.grid(),
                                       self._cartwall.pages(),
                                       self._cartwall.current_page(),
                                       self._cartwall.default_colour(),
                                       self._cartwall.fade_ms(),
                                       self._cartwall.slot_keys()))
