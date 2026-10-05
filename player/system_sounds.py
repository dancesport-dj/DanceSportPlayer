"""🔕 The operating system's own sounds stay off the PA while the evening runs.

The music and the OS share the one sound card, so an error ding or a
notification chime goes out over the hall's speakers at full volume. Each
platform has one switch for exactly those sounds, our own QMessageBox beeps
included, that leaves the music alone:

- Windows: the "System Sounds" session of the volume mixer, per output device.
- macOS: the alert volume (System Settings → Sound → Alert volume).
- Linux: GNOME's event sounds (org.gnome.desktop.sound event-sounds), which
  libcanberra honours for every GTK app; other desktops have no common switch
  and are left alone.

The change outlives the app: the OS keeps it until someone puts it back. So a
backend only ever undoes what it changed itself (a switch the operator had
already turned off stays off), and `record` is what the caller persists so a
crash that skips `hold(False)` is repaired on the next start by
`restore_leftover`.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys

log = logging.getLogger("dancesport.gui.audio")

_CMD_TIMEOUT_S = 3


def _run(*cmd: str) -> str | None:
    """stdout of a short helper command, or None if it is missing or failed."""
    try:
        done = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=_CMD_TIMEOUT_S, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


class WindowsBackend:
    """Mutes every active output device's System Sounds session — all of them,
    not just the default: the music follows a default switched mid-evening.

    Devices are kept by endpoint id, which survives unplugging, and `refresh`
    runs on every tick while muted, so the PA's interface plugged in (or back
    in) mid-evening is muted too. The record is the list of ids WE muted: a
    crash repair lifts only those, never a device muted by hand."""

    def __init__(self, win32=None):
        if win32 is None:
            from player import system_sounds_win32 as win32
        self._w = win32
        self._ours: set[str] = set()   # muted by us — lifted on restore
        self._left: set[str] = set()   # muted by hand — never touched

    def _volumes(self):
        try:
            return self._w.system_sound_volumes()
        except OSError as e:
            log.warning("🔕 System sounds could not be reached\n"
                        "error: %s", e)
            return None

    def mute(self):
        """Mute every device not seen before; the record, or None."""
        w = self._w
        for dev_id, vol in self._volumes() or ():
            try:
                if dev_id in self._ours or dev_id in self._left:
                    continue   # decided when it was first seen
                if w.get_mute(vol):
                    self._left.add(dev_id)   # muted by hand — not ours to lift
                    continue
                w.set_mute(vol, True)
                self._ours.add(dev_id)
            except OSError:
                continue
            finally:
                w.release(vol)
        return sorted(self._ours) or None

    refresh = mute

    def restore(self, record):
        """Lift our own mutes. A record from before the ids were kept is a
        bare count: then every device is unmuted, as it was back then."""
        w = self._w
        ours = set(record) if isinstance(record, list) else None
        self._ours, self._left = set(), set()
        for dev_id, vol in self._volumes() or ():
            try:
                if ours is None or dev_id in ours:
                    w.set_mute(vol, False)
            except OSError:   # device unplugged meanwhile — nothing to lift
                pass
            finally:
                w.release(vol)


class MacBackend:
    """The alert volume: every NSBeep and system alert sound, nothing else.
    Set through Standard Additions, which needs no automation permission."""

    def mute(self):
        out = _run("osascript", "-e", "alert volume of (get volume settings)")
        try:
            before = int(out)
        except (TypeError, ValueError):
            return None
        if before == 0:
            return None   # already silent — not ours to raise later
        if _run("osascript", "-e", "set volume alert volume 0") is None:
            return None
        return before

    def restore(self, record):
        level = record if isinstance(record, int) and 0 < record <= 100 else 100
        _run("osascript", "-e", f"set volume alert volume {level}")


class LinuxBackend:
    """GNOME's event-sounds switch. No gsettings or no GNOME schema: nothing
    to do, and nothing breaks."""

    _KEY = ("org.gnome.desktop.sound", "event-sounds")

    def mute(self):
        if _run("gsettings", "get", *self._KEY) != "true":
            return None
        if _run("gsettings", "set", *self._KEY, "false") is None:
            return None
        return True

    def restore(self, _record):
        _run("gsettings", "set", *self._KEY, "true")


def default_backend():
    # The test suite sets this (tests/__init__.py): a test window entering
    # Playing mode must not mute the sounds of the machine running it.
    if os.environ.get("DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS"):
        return None
    if sys.platform == "win32":
        try:
            return WindowsBackend()
        except (ImportError, OSError):   # pragma: no cover - no Core Audio
            return None
    if sys.platform == "darwin":
        return MacBackend() if shutil.which("osascript") else None
    if sys.platform.startswith("linux"):
        return LinuxBackend() if shutil.which("gsettings") else None
    return None


class SystemSoundGuard:
    """Turns the platform's system sounds off and back on again."""

    def __init__(self, backend=None):
        self._backend = backend if backend is not None else default_backend()
        self.active = False
        # What the backend has to put back, or None when it changed nothing.
        # JSON-safe: the caller stores it in the settings for the crash repair.
        self.record = None

    def hold(self, on: bool) -> bool:
        """Silence (True) or restore (False). True when the state changed —
        the caller persists `record` then."""
        if self._backend is None:
            return False
        if on == self.active:
            # Muted already: a backend that works per device mutes the ones
            # plugged in since.
            if on and hasattr(self._backend, "refresh"):
                record = self._backend.refresh()
                if record != self.record:
                    self.record = record
                    log.info("🔕 System sounds muted on a new device\n"
                             "changed: %s", record)
                    return True
            return False
        if on:
            self.record = self._backend.mute()
            log.info("🔕 System sounds muted\n"
                     "changed: %s", self.record)
        else:
            if self.record is not None:
                self._backend.restore(self.record)
                log.info("🔔 System sounds back")
            self.record = None
        self.active = on
        return True

    def restore_leftover(self, record):
        """Put back what a run that crashed while muted left behind."""
        if self._backend is None or record is None:
            return
        self._backend.restore(record)
        log.info("🔔 System sounds restored after an unclean exit")
