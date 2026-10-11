"""🎛 Hardware controller, desk side: open the device, read it, obey it.

A MIDI controller (Korg nanoKONTROL2, a Traktor in MIDI mode, …) or a HID one
(a Traktor in its native mode) drives the very actions the 📱 phone remote
does, through the same `_on_remote_command`, plus the music volume. Which
knob does what is the profile in the settings (planner.controller); the
🎛 Controller window picks the device, loads a profile and learns bindings.

Reading happens on the MIDI backend's or the HID reader's thread; every
reading crosses to the GUI thread through `_ControllerHub.control` before
anything is done with it. A device that is not plugged in at launch is looked for every few
seconds, so the controller can come out of the bag after the app is up.
"""
import logging

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from planner import cartwall as pc
from planner import controller as pctl
from shared import hid_input, midi_input
from shared.stores import save_settings

log = logging.getLogger("dancesport.gui.controller")

_RETRY_MS = 3000


class _ControllerHub(QObject):
    """Carries readings from the input thread onto the GUI thread, and tells
    the 🎛 window news."""

    control = Signal(str, float)        # control, value 0…1
    changed = Signal()                  # connected, disconnected, new profile


def controller_devices(all_hid: bool = False) -> list[tuple[str, str, str]]:
    """(kind, id, name) for every input plugged in now — MIDI first."""
    out = [("midi", name, name) for name in midi_input.list_inputs() if name]
    out += [("hid", ident, f"{name} (HID)")
            for ident, name in hid_input.list_devices(all_hid)]
    return out


class ControllerMixin:
    """🎛 A hardware controller — none unless one is chosen."""

    def _init_controller(self):
        self._ctl_hub = _ControllerHub()
        self._ctl_hub.control.connect(self._on_controller_control)
        self._ctl_input = None
        self._ctl_error = ""
        self._ctl_last_report = {}
        self._ctl_listener = None
        cfg = self.controller_config()
        self._ctl_map = pctl.ControllerMap(cfg["bindings"])
        self._ctl_retry = QTimer(self)
        self._ctl_retry.setInterval(_RETRY_MS)
        self._ctl_retry.timeout.connect(self._connect_controller)
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
        from player.controller_dialog import ControllerDialog
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

    def set_controller_listener(self, listener):
        """Learn: every reading goes to `listener(control, value)` instead of
        the desk while one is set. None hands them back to the desk."""
        self._ctl_listener = listener

    def _connect_controller(self):
        cfg = self.controller_config()
        if self._ctl_input is not None or not cfg["device"]:
            self._ctl_retry.stop()
            return
        hub = self._ctl_hub
        try:
            if cfg["kind"] == "hid":
                self._ctl_last_report = {}
                self._ctl_input = hid_input.HidInput(cfg["device"], self._on_hid_report)
            else:
                self._ctl_input = midi_input.MidiInput(
                    cfg["device"],
                    lambda s, a, b: self._emit_midi(hub, s, a, b))
        except OSError as exc:
            if self._ctl_error != str(exc):
                log.info("🎛 Controller not connected\n"
                         "device: %s\n"
                         "reason: %s", cfg["device"], exc)
            self._ctl_error = str(exc)
            if not self._ctl_retry.isActive():
                self._ctl_retry.start()
            hub.changed.emit()
            return
        self._ctl_error = ""
        self._ctl_retry.stop()
        log.info("🎛 Controller connected\n"
                 "device: %s\n"
                 "profile: %s\n"
                 "bindings: %d", cfg["device"], cfg["profile"] or "-",
                 len(cfg["bindings"]))
        hub.changed.emit()

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
        elif action == "duck":
            self._set_desk_duck(self._mix.desk == 1.0)
        elif action.startswith("pad:"):
            self._fire_controller_pad(int(action[4:]) - 1)
        else:
            self._on_remote_command(action, None)

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
