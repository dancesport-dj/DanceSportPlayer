"""🎛 Hardware controller, desk side: open the device, read it, obey it.

A MIDI controller (Korg nanoKONTROL2, a Traktor in MIDI mode, …) or a HID one
(a Traktor in its native mode) drives the very actions the 📱 phone remote
does, through the same `_on_remote_command`, plus the music volume. Which
knob does what is the profile in the settings (planner.playing.controller); the
🎛 Controller window picks the device, loads a profile and learns bindings.

Reading happens on the MIDI backend's or the HID reader's thread; every
reading crosses to the GUI thread through `_ControllerHub.control` before
anything is done with it. A device that is not plugged in at launch is looked for every few
seconds, so the controller can come out of the bag after the app is up.
"""
import logging
import threading
from functools import partial

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QPushButton

from planner.playing import cartwall as pc
from planner.playing import controller as pctl
from shared.controllers import hid_input, midi_input
from shared.stores import save_settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.controller")

_RETRY_MS = 3000


class _ControllerHub(QObject):
    """Carries readings from the input thread onto the GUI thread, and tells
    the 🎛 window news."""

    control = Signal(str, float)        # control, value 0…1
    changed = Signal()                  # connected, disconnected, new profile
    found = Signal(str, bool)           # the tick's look: device, in the list?
    opened = Signal(str, object, str)   # a HID re-plug: device, HidInput or None, why
    badge: QPushButton | None = None    # the status bar's 🎛 pill (MainWindow)
    probe: threading.Thread | None = None  # the thread taking that look


def _look_for(hub, kind: str, device: str, on_report=None):
    """The probe thread: is `device` in the system's list? A slow driver
    holds up only this thread, never the GUI thread the fades and cuts of
    the music run on. A HID device that is back is opened here too, with
    `on_report` — enumerating and opening it takes about 250 ms."""
    if kind == "hid":
        found = any(ident == device for ident, _name in hid_input.list_devices(True))
        if found and on_report is not None:
            try:
                dev, why = hid_input.HidInput(device, on_report), ""
            except OSError as exc:
                dev, why = None, str(exc)
            try:
                hub.opened.emit(device, dev, why)
            except RuntimeError:    # the window closed while it opened
                if dev is not None:
                    dev.close()
            return
    else:
        found = device in midi_input.list_inputs()
    try:
        hub.found.emit(device, found)
    except RuntimeError:    # the window closed while it looked
        pass


def controller_devices(all_hid: bool = False) -> list[tuple[str, str, str]]:
    """(kind, id, name) for every input plugged in now — MIDI first."""
    out = [("midi", name, name) for name in midi_input.list_inputs() if name]
    out += [("hid", ident, f"{name} (HID)")
            for ident, name in hid_input.list_devices(all_hid)]
    return out


class ControllerMixin(MainWindowHost):
    """🎛 A hardware controller — none unless one is chosen."""

    def _init_controller(self):
        self._ctl_hub = _ControllerHub()
        self._ctl_hub.control.connect(self._on_controller_control)
        self._ctl_hub.found.connect(self._on_controller_found)
        self._ctl_hub.opened.connect(self._on_controller_opened)
        self._ctl_input = None
        self._ctl_error = ""
        self._ctl_last_report = {}
        self._ctl_listener = None
        cfg = self.controller_config()
        self._ctl_map = pctl.ControllerMap(cfg["bindings"])
        # Ticks while a device is chosen: retries it while it is missing,
        # watches for an unplug while it is connected.
        self._ctl_retry = QTimer(self)
        self._ctl_retry.setInterval(_RETRY_MS)
        self._ctl_retry.timeout.connect(self._controller_tick)
        self._connect_controller()

    def controller_hub(self) -> _ControllerHub:
        return self._ctl_hub

    def controller_config(self) -> dict:
        """The saved choice: {"kind", "device", "profile", "bindings"}."""
        raw = self._settings.get("controller")
        raw = raw if isinstance(raw, dict) else {}
        return {"kind": raw.get("kind") if raw.get("kind") in ("midi", "hid") else "",
                "device": str(raw.get("device") or ""),
                "profile": str(raw.get("profile") or ""),
                "bindings": pctl.clean_bindings(raw.get("bindings"))}

    def set_controller_config(self, cfg: dict):
        """Save a new choice and reconnect to it."""
        cfg = {"kind": cfg.get("kind", ""), "device": cfg.get("device", ""),
               "profile": cfg.get("profile", ""),
               "bindings": pctl.clean_bindings(cfg.get("bindings"))}
        self._settings["controller"] = cfg
        save_settings(self._settings)
        self._ctl_map = pctl.ControllerMap(cfg["bindings"])
        self._disconnect_controller()
        self._connect_controller()

    def controller_status(self) -> tuple[bool, str]:
        """(connected, what to show) for the 🎛 window."""
        if self._ctl_input is not None:
            return True, self.controller_config()["device"]
        return False, self._ctl_error

    def open_controller_window(self, over=None):
        """🎛 The controller's window: device, profile, learn.

        `over` is a modal dialog it is opened from (⚙ Settings): the window is
        then that dialog's own, as with the 📱 remote's window."""
        from player.dialogs.controller_dialog import ControllerDialog
        if over is not None:
            dlg = ControllerDialog(self, parent=over)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.show()
            return dlg
        dlg = getattr(self, "_controller_dlg", None)
        if dlg is None:
            dlg = ControllerDialog(self, parent=self)
            self._controller_dlg = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def _sync_controller_badge(self):
        """🎛 A green pill at the right of the status bar while the
        controller is connected — like the 📱 Remote one, so the desk sees the
        nanoKONTROL2 is there to be used. A click opens its window."""
        hub = self._ctl_hub
        if hub.badge is None:
            badge = QPushButton()
            badge.setToolTip("The hardware controller is connected — "
                             "click for its window.")
            badge.setStyleSheet("background:#2e7d32; color:white; font-weight:bold; "
                                "border:none; border-radius:8px; padding:1px 8px; "
                                "margin:2px 4px;")
            badge.setCursor(Qt.CursorShape.PointingHandCursor)
            badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            badge.clicked.connect(lambda: self.open_controller_window())
            # First of the permanent widgets: the ⛶ clock keeps the far right.
            self.statusBar().insertPermanentWidget(0, badge)
            hub.badge = badge
        connected, device = self.controller_status()
        # i18n: data — the device's own name
        hub.badge.setText(f"🎛 {device}")
        hub.badge.setVisible(connected)

    def set_controller_listener(self, listener):
        """Learn: every reading goes to `listener(control, value)` instead of
        the desk while one is set. None hands them back to the desk."""
        self._ctl_listener = listener

    def _connect_controller(self):
        cfg = self.controller_config()
        if not cfg["device"]:
            self._ctl_retry.stop()
            return
        if self._ctl_input is not None:
            return
        hub = self._ctl_hub
        try:
            if cfg["kind"] == "hid":
                self._ctl_last_report = {}
                dev = hid_input.HidInput(cfg["device"], self._on_hid_report)
            else:
                dev = midi_input.MidiInput(
                    cfg["device"],
                    lambda s, a, b: self._emit_midi(hub, s, a, b))
        except OSError as exc:
            self._controller_failed(cfg["device"], str(exc))
            return
        self._controller_adopt(dev)

    def _controller_failed(self, device: str, why: str):
        if self._ctl_error != why:
            log.info("🎛 Controller not connected\n"
                     "device: %s\n"
                     "reason: %s", device, why)
        self._ctl_error = why
        if not self._ctl_retry.isActive():
            self._ctl_retry.start()
        self._ctl_hub.changed.emit()

    def _controller_adopt(self, dev):
        cfg = self.controller_config()
        self._ctl_input = dev
        self._ctl_error = ""
        self._ctl_retry.start()
        log.info("🎛 Controller connected\n"
                 "device: %s\n"
                 "profile: %s\n"
                 "bindings: %d", cfg["device"], cfg["profile"] or "-",
                 len(cfg["bindings"]))
        self._ctl_hub.changed.emit()

    def _on_controller_opened(self, device: str, dev, why: str):
        """A HID device the probe thread opened on its re-plug (dev None:
        it is in the list but would not open, `why`)."""
        cfg = self.controller_config()
        if (device != cfg["device"] or not self._ctl_retry.isActive()
                or self._ctl_input is not None):
            if dev is not None:     # another device chosen meanwhile, or shut down
                dev.close()
            return
        if dev is None:
            self._controller_failed(device, why)
        else:
            self._controller_adopt(dev)

    def _controller_tick(self):
        """No backend tells of a USB unplug (winmm only reports data), so
        the system's device list is read: a connected device that has left
        it is let go, a missing one is opened once it is back. The list is
        read on a thread of its own, which also opens a HID device that is
        back; the GUI thread opens only a MIDI one, and closes."""
        hub = self._ctl_hub
        if hub.probe is not None and hub.probe.is_alive():
            return
        cfg = self.controller_config()
        if cfg["kind"] == "hid" and self._ctl_input is not None:
            # Its reader ends on the read error an unplug brings: free to ask.
            # (Only a HidInput has `alive`; the kind says this is one.)
            self._on_controller_found(cfg["device"], getattr(self._ctl_input, "alive", True))
            return
        on_report = None
        if cfg["kind"] == "hid":
            # Missing: the probe opens it once it is back, so the reader
            # starts from a clean slate.
            self._ctl_last_report = {}
            on_report = self._on_hid_report
        hub.probe = threading.Thread(target=_look_for, name="controller-probe",
                                     args=(hub, cfg["kind"], cfg["device"], on_report),
                                     daemon=True)
        hub.probe.start()

    def _on_controller_found(self, device: str, found: bool):
        cfg = self.controller_config()
        if device != cfg["device"] or not self._ctl_retry.isActive():
            return      # another device chosen meanwhile, or shut down
        if found:
            self._connect_controller()
            return
        if self._ctl_input is not None:
            log.info("🎛 Controller unplugged\n"
                     "device: %s", device)
            self._disconnect_controller()
            self._ctl_retry.start()
        if not self._ctl_error:     # keep the reason the last open gave
            self._ctl_error = f"Controller not found: {device}"
            self._ctl_hub.changed.emit()

    def _disconnect_controller(self):
        dev, self._ctl_input = self._ctl_input, None
        if dev is not None:
            dev.close()
            log.info("🎛 Controller disconnected\n"
                     "device: %s", dev.name)
        self._ctl_retry.stop()
        self._ctl_hub.changed.emit()

    def _controller_shutdown(self):
        self._ctl_listener = None
        self._disconnect_controller()

    @staticmethod
    def _emit_midi(hub, status, data1, data2):
        """The MIDI backend's thread: name the control and cross to the GUI thread."""
        hit = pctl.midi_control(status, data1, data2)
        if hit is not None:
            hub.control.emit(*hit)

    def _on_hid_report(self, report: bytes):
        """The HID reader's thread: diff against the last report of that id."""
        if not report:
            return
        prev = self._ctl_last_report.get(report[0])
        self._ctl_last_report[report[0]] = report
        if prev is None:            # the first report is the resting state
            return
        for control, value in pctl.hid_controls(prev, report):
            self._ctl_hub.control.emit(control, value)

    def _on_controller_control(self, control: str, value: float):
        if self._ctl_listener is not None:
            self._ctl_listener(control, value)
            return
        for action, val in self._ctl_map.feed(control, value):
            log.info("🎛 Controller: %s\n"
                     "control: %s", action, control)
            self._run_controller_action(action, val)

    def _run_controller_action(self, action: str, value: float):
        """One bound action — the phone remote's switch wherever it has one."""
        if action == "volume":
            self._set_base_volume(value)
        elif action in ("vol_up", "vol_down"):
            step = pctl.VOLUME_STEP if action == "vol_up" else -pctl.VOLUME_STEP
            self._set_base_volume(self._mix.base + step)
        elif action.startswith("tempo"):
            player = self._big_player
            if player is None:
                return
            if action == "tempo":
                player.set_tempo_from_knob(pctl.knob_offset(value))
            elif action == "tempo_reset":
                player.reset_tempo()
            else:
                player.step_tempo(action == "tempo_up")
        elif action == "duck":
            self._set_desk_duck(self._mix.desk == 1.0)
        elif action.startswith("pad:"):
            self._fire_controller_pad(int(action[4:]) - 1)
        else:
            self._on_remote_command(action, None)

    # ── ⌨ Desk keys ──────────────────────────────────────────────────────────

    def _init_desk_keys(self):
        """One shortcut per KEY_ACTION, on all its keys, from anywhere in the window: the
        keyboard's way into what the 📱 phone and the 🎛 controller run, and
        so a Stream Deck's or a macro keypad's.

        Auto-repeat OFF, which QShortcut has ON by default: held a moment too
        long, a key repeats at the system rate and every repeat of ⏭ throws
        another title away. Only the volume and tempo steps are meant to glide."""
        self._desk_keys = {}
        for action in pctl.KEY_ACTIONS:
            sc = QShortcut(self)
            sc.setAutoRepeat(action in ("vol_up", "vol_down", "tempo_up", "tempo_down"))
            sc.activated.connect(partial(self._on_desk_key, action))
            self._desk_keys[action] = sc
        self._apply_desk_keys()

    def _apply_desk_keys(self):
        for action, keys in pctl.desk_keys(self._settings.get("desk_keys")).items():
            self._desk_keys[action].setKeys([QKeySequence(k) for k in keys])

    def set_desk_keys(self, keys: dict):
        """Save new desk keys (only those off the defaults) and put them on."""
        keys = pctl.desk_keys(keys)
        self._settings["desk_keys"] = {
            a: k for a, k in keys.items() if k != [pctl.KEY_DEFAULTS.get(a, "")]}
        save_settings(self._settings)
        self._apply_desk_keys()
        log.info("⌨ Desk keys saved\n"
                 "bound: %d", sum(len(k) for k in keys.values()))

    def open_desk_keys_window(self, over=None, tab=0):
        """⌨ The Keys window — desk keys and the 🎛 wall's in one — modal over
        ⚙ Settings, the F1 sheet or the wall. `tab` 1 opens on the wall's."""
        from player.dialogs.desk_keys_dialog import KeysDialog
        wall = self._cartwall
        dlg = KeysDialog(pctl.desk_keys(self._settings.get("desk_keys")),
                         (wall.grid(), wall.pages(), wall.slot_keys()),
                         parent=over if over is not None else self, tab=tab)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_desk_keys(dlg.desk_keys())
            wall.apply_keys(dlg.pad_keys(), dlg.slot_keys())
        dlg.deleteLater()

    def _on_desk_key(self, action: str):
        log.info("⌨ Desk key: %s", action)
        self._run_controller_action(action, 1.0)

    def _fire_controller_pad(self, slot: int):
        """Pad n is the n-th cell of the cartwall page on screen, row by row —
        the same place Ctrl+n fires, so a hole on the page stays a hole."""
        wall = self._cartwall
        if wall is None:
            return
        cells = list(pc.cells_in_order(wall.grid()))
        page = wall.current_page()
        pages = wall.pages()
        if not (0 <= slot < len(cells) and 0 <= page < len(pages)):
            return
        if cells[slot] in pages[page].pads:
            wall.play_pad((page, *cells[slot]))
