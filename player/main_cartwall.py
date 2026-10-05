"""🎛 Cartwall wiring: the dock, the toolbar toggle and cartwall.json.

Only wiring lives here. Every Qt event handler belongs to the widgets in
player.cartwall — QMainWindow comes first in MainWindow's bases, so anything Qt
delivers by virtual dispatch would never reach a mixin method.
"""
import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from planner import cartwall as pc
from planner import i18n
from player.cartwall import CartVoices, CartwallWidget
from shared.stores import load_cartwall_file, save_cartwall_file, save_settings

log = logging.getLogger("dancesport.gui.cartwall")

CART_DOCK = "cartwall_dock"     # objectName — QMainWindow.restoreState needs one


class CartwallMixin:
    """The 🎛 sample-pad wall: pads that fire over the running deck music."""

    def _build_cartwall(self):
        """Create the wall, its dock and its audio pool, and load the saved wall."""
        self._cartwall = CartwallWidget()
        self._cartwall.padClicked.connect(self._on_pad_clicked)
        self._cartwall.changed.connect(self._save_cartwall)
        self._cartwall.stopAll.connect(self._on_cart_stop_all)
        self._cartwall.padRefreshed.connect(self._on_cart_pad_refreshed)
        self._cartwall.previewVolume.connect(self._on_cart_preview_volume)
        self._cartwall.previewFire.connect(self._on_cart_preview_fire)
        self._cartwall.fadeChanged.connect(self._on_cart_wall_fade)

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
            self._cart_voices.padFading.connect(self._cartwall.set_fading)
            self._cart_voices.padTick.connect(self._on_cart_tick)
            self._cart_voices.activeChanged.connect(self._on_cart_active)
            self._cart_voices.duckChanged.connect(self._on_cart_duck_changed)
            self._cart_voices.wantsDevice.connect(self._audio_device.ensure)
            self._cartwall.padsMoved.connect(self._cart_voices.rekey)
            self._apply_volume()      # push the desk level into the fresh pool
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
        if self._cart_voices.is_playing(key):
            self._cart_voices.stop(key)
            return
        # Checked on the tap, not on a timer: a stick that came up as a different
        # drive letter must say so instead of firing silence.
        if not os.path.isfile(pad.path):
            self._cartwall.refresh_missing()
            self.statusBar().showMessage(i18n.t("⚠️ Sample not found: %s") % pad.path)
            log.warning("🎛 Pad file is gone\n"
                        "path: %s", pad.path)
            return
        if self._cart_voices.fire(key, pad):
            self._cartwall.set_playing(key, True)
        else:
            self.statusBar().showMessage(
                "🎛 No free pad voice — every voice holds a looping pad.")

    def _on_cart_pad_stopped(self, key):
        self._cartwall.set_playing(key, False)

    def _on_cart_stop_all(self):
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
            if pad is not None and os.path.isfile(pad.path):
                if self._cart_voices.fire(key, pad):
                    self._cartwall.set_playing(key, True)
        elif self._cart_voices.is_playing(key):
            self._cart_voices.stop(key)

    def _on_cart_wall_fade(self, ms: int):
        if self._cart_voices is not None:
            self._cart_voices.set_wall_fade(ms)

    def _on_cart_active(self, count: int):
        self._cartwall.set_active(count)

    def _on_cart_duck_changed(self, on: bool):
        self._set_duck_reason("cartwall", on)

    def _on_cart_tick(self, rows):
        for key, ms_left, frac in rows:
            self._cartwall.set_remaining(key, ms_left, frac)

    def _cartwall_shutdown(self):
        """Release every sample file before the widgets go — a looping bed can
        hold a handle open for an hour, and WMF keeps it until told otherwise."""
        if getattr(self, "_cart_voices", None) is not None:
            self._cart_voices.shutdown()

    # ── persistence ──────────────────────────────────────────────────────────
    def _load_cartwall(self):
        doc = pc.load_doc(load_cartwall_file())
        self._cart_file_foreign = not doc.ok
        if not doc.ok:
            log.warning("🎛 cartwall.json is not a wall this build understands\n"
                        "action: starting empty, and NOT overwriting the file")
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
