"""🎛 HID input from a DJ controller that does not speak MIDI — through hidapi.

Native Instruments' Traktor controllers (and others) talk HID unless switched
into a MIDI mode. HID has no notion of "button 3": a device sends a report of
raw bytes, and `planner.controller.hid_controls` turns the bytes that changed
into controls the 🎛 learn step can bind. hidapi (the `hid` module) is
optional; without it there are simply no HID devices.

Nothing Qt lives here. Reports are read on a thread of our own and handed to
the callback from that thread; the caller moves them onto the GUI thread.
"""
from __future__ import annotations

import logging
import threading

log = logging.getLogger("dancesport.hid")

try:
    import hid
except ImportError:   # pragma: no cover - hidapi not installed
    hid = None

# USB vendors of DJ controllers listed without "all HID devices" ticked:
# Native Instruments, Pioneer DJ, inMusic (Numark / Denon DJ), Hercules,
# Reloop, Korg, Allen & Heath, Behringer.
DJ_VENDORS = frozenset({0x17CC, 0x2B73, 0x08E4, 0x15E4, 0x06F8, 0x200C,
                        0x0944, 0x22F0, 0x1397})
_READ_SIZE = 256
_READ_TIMEOUT_MS = 200


def available() -> bool:
    return hid is not None


def device_id(vendor: int, product: int) -> str:
    return f"{vendor:04x}:{product:04x}"


def list_devices(all_devices: bool = False) -> list[tuple[str, str]]:
    """(id, name) per HID device plugged in now, one entry per device however
    many interfaces it has. DJ vendors only unless `all_devices`."""
    if hid is None:
        return []
    out, seen = [], set()
    for d in hid.enumerate():
        vid, pid = d.get("vendor_id", 0), d.get("product_id", 0)
        ident = device_id(vid, pid)
        if ident in seen or not (all_devices or vid in DJ_VENDORS):
            continue
        seen.add(ident)
        name = " ".join(s for s in (d.get("manufacturer_string") or "",
                                    d.get("product_string") or "")
                        if s.strip()) or ident
        out.append((ident, name.strip()))
    return out


def _path_for(ident: str):
    """The interface to read: the vendor-defined one (where controllers put
    their buttons), else the device's first."""
    first = None
    for d in hid.enumerate():
        if device_id(d.get("vendor_id", 0), d.get("product_id", 0)) != ident:
            continue
        if d.get("usage_page", 0) >= 0xFF00:
            return d["path"]
        first = first or d["path"]
    return first


class HidInput:
    """One open HID device. `on_report(bytes)` runs on the reader thread for
    every input report; `close()` stops it."""

    def __init__(self, ident: str, on_report):
        if hid is None:
            raise OSError("HID input needs the hidapi package")
        path = _path_for(ident)
        if path is None:
            raise OSError(f"HID device not found: {ident}")
        self.name = ident
        self._dev = hid.device()
        try:
            self._dev.open_path(path)
        except (OSError, IOError) as exc:
            raise OSError(f"could not open HID device {ident} — another "
                          f"program may hold it ({exc})") from exc
        self._on_report = on_report
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="hid-input",
                                        daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                data = self._dev.read(_READ_SIZE, _READ_TIMEOUT_MS)
            except (OSError, IOError, ValueError):
                log.warning("🎛 HID device %s stopped answering", self.name)
                break
            if data:
                try:
                    self._on_report(bytes(data))
                except Exception:
                    log.exception("🎛 HID report handler failed")

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        try:
            self._dev.close()
        except (OSError, IOError):
            pass
