"""🔌 A drive that comes or goes is noticed without anybody pressing ▶.

Every few seconds a thread of its own reads the drive list and checks the
files every deck, wishlist and 🎛 pad points at — a stick that sleeps or a
network share that hangs holds up only that thread, never the music. Back on
the GUI thread, the rows whose file went or came back are painted again (red
❗ or white), the wall re-marks its pads, and a toast says what most likely
happened. Nothing stops and nothing is asked: the running title plays on.
"""
import contextlib
import logging
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from planner.music.drives import DriveWatch, drive_of, missing_among, mounted_drives, warning
from planner.music.paths import resolve_file
from shared.widgets import WARN_TOAST_MS, show_toast

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.drives")

DRIVE_CHECK_MS = 10_000
# Windows says when a volume comes or goes (a stick in or out, a letter
# remapped): looked at this long after, once the drive has settled.
DEVICE_SETTLE_MS = 1500
_WM_DEVICECHANGE = 0x0219
_DBT_VOLUME_EVENTS = (0x8000, 0x8004)   # DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE


class _DriveHub(QObject):
    """Carries one look from the probe thread onto the GUI thread, and
    holds the watch's state so the window keeps only this one name."""
    looked = Signal(object, object, object, object)  # drives, checked, missing, found
    probe: threading.Thread | None = None
    device_filter: QAbstractNativeEventFilter | None = None

    def __init__(self, parent):
        super().__init__(parent)
        self.watch = DriveWatch()
        self.timer = QTimer(self)
        self.soon = QTimer(self)        # a look right after Windows' notice
        self.soon.setSingleShot(True)
        self.soon.setInterval(DEVICE_SETTLE_MS)


class _DeviceFilter(QAbstractNativeEventFilter):
    """Hears WM_DEVICECHANGE, which Windows sends every top-level window when
    a volume arrives or leaves. Several windows hear it, so the look it
    starts is a single-shot timer: the copies fold into one."""

    def __init__(self, on_change, fields):
        super().__init__()
        self._on_change = on_change
        self._fields = fields      # (hwnd, message id, wParam) out of a MSG

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            got = self._fields(message)
            if (got is not None and got[1] == _WM_DEVICECHANGE
                    and got[2] in _DBT_VOLUME_EVENTS):
                with contextlib.suppress(RuntimeError):   # the window is gone
                    self._on_change()
        return False, 0


def _look(hub, track_paths, pad_paths, settings):
    """The probe thread. A title or pad counts as there when `resolve_file`
    finds it — on its own drive, the same path on another one, or 🧭's copy:
    that is what plays, so a stick back as G: is no loss."""
    drives = mounted_drives()
    checked = set(track_paths) | set(pad_paths)
    found = {}      # not at its own path, but played from this one

    def exists(p):
        hit = resolve_file(p, settings)
        if hit is not None and str(hit) != str(Path(p)):
            found[p] = str(hit)
        return hit is not None
    missing = missing_among(checked, exists=exists)
    with contextlib.suppress(RuntimeError):  # the window closed while it looked
        hub.looked.emit(drives, checked, missing, found)


class DriveWatchMixin(MainWindowHost):
    """🔌 The periodic look at drives and files."""

    def _init_drive_watch(self):
        hub = self._drive_hub = _DriveHub(self)
        hub.looked.connect(self._on_drives_looked)
        hub.timer.setInterval(DRIVE_CHECK_MS)
        hub.timer.timeout.connect(self._drive_tick)
        hub.timer.start()
        hub.soon.timeout.connect(self._drive_tick)
        app = QApplication.instance()
        if sys.platform == "win32" and app is not None:
            try:
                from shared.taskbar_win32 import msg_fields
            except (ImportError, OSError, AttributeError):   # pragma: no cover
                return
            hub.device_filter = _DeviceFilter(hub.soon.start, msg_fields)
            app.installNativeEventFilter(hub.device_filter)

    def _drive_watch_shutdown(self):
        hub = getattr(self, "_drive_hub", None)
        if hub is not None:
            hub.timer.stop()
            hub.soon.stop()
            app = QApplication.instance()
            if hub.device_filter is not None and app is not None:
                app.removeNativeEventFilter(hub.device_filter)
                hub.device_filter = None

    def _drive_tick(self):
        hub = self._drive_hub
        if hub.probe is not None and hub.probe.is_alive():
            return      # the last look still hangs on a slow drive
        tracks = {m.path_str for table in self._deckset.all_tables
                  for _r, m in table._row_meta.numbered() if m.path_str}
        wall = getattr(self, "_cartwall", None)
        pads = ({pad.path for page in wall.pages() for pad in page.pads.values()}
                if wall is not None else set())
        hub.probe = threading.Thread(target=_look, name="drive-probe",
                                     args=(hub, tracks, pads, dict(self._settings)),
                                     daemon=True)
        hub.probe.start()

    def _on_drives_looked(self, drives, checked, missing, found):
        change = self._drive_hub.watch.step(drives, checked, missing, found)
        if change is None:
            return
        for drive in sorted(change.gone_drives):
            log.info("🔌 Drive gone\n"
                     "drive: %s", drive)
        for drive in sorted(change.new_drives):
            log.info("🔌 Drive connected\n"
                     "drive: %s", drive)
        changed = change.paths()
        if not changed:
            return
        for table in self._deckset.all_tables:
            table.refresh_paths(changed)
        wall = getattr(self, "_cartwall", None)
        if wall is not None:
            wall.refresh_missing()
        log.warning("🔌 Titles changed on disk\n"
                    "gone: %d\n"
                    "back: %d\n"
                    "on another drive: %d\n"
                    "drives: %s", len(change.missing), len(change.back),
                    len(change.rehomed),
                    ", ".join(sorted({drive_of(p) for p in changed} - {""})) or "-")
        text = warning(change)
        if text:
            self.statusBar().showMessage(text)
            # Titles back is good news: the plain toast, not the red one.
            show_toast(self, text, WARN_TOAST_MS,
                       error=bool(change.missing or change.rehomed))
