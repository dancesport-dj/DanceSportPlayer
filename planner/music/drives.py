#!/usr/bin/env python3
"""🔌 Which drives are there, and which titles went with one.

A USB stick pulled mid-evening takes its titles along without a word: the
rows stay white until somebody presses ▶ on one. The window looks every few
seconds (see gui/window/main_drives.py); this module is the part of that look
that needs no Qt — the drive list, the file check and what changed since the
last look.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from planner import i18n

_VOLUMES = Path("/Volumes")


def mounted_drives() -> frozenset[str]:
    """The drives this PC has right now: `F:` on Windows, `/Volumes/STICK` on
    a Mac. Reading the list touches no drive, so a sleeping disk stays asleep."""
    try:
        if sys.platform == "win32":
            return frozenset(d.rstrip("\\/").upper() for d in os.listdrives())
        if _VOLUMES.is_dir():
            return frozenset(str(p) for p in _VOLUMES.iterdir())
    except OSError:
        pass
    return frozenset()


def local_drives() -> frozenset[str]:
    """`mounted_drives` without the ones a look can hang on: on Windows only
    removable, fixed and RAM drives — a network drive that is gone can hold
    a file check for seconds, and a CD drive spins up."""
    found = mounted_drives()
    if sys.platform != "win32":
        return found
    import ctypes
    get_type = ctypes.windll.kernel32.GetDriveTypeW
    # 2 removable (a stick), 3 fixed (a USB disk too), 6 RAM disk.
    return frozenset(d for d in found if get_type(d + "\\") in (2, 3, 6))


def on_other_drives(path) -> list[str]:
    """The same path on every other local drive, in drive order: a stick
    that came back as G: instead of F:, or another stick on F: with the same
    folders on a second one. Empty for a path that is not on a drive."""
    drive = drive_of(path)
    if not drive:
        return []
    rest = str(path)[len(drive):]
    return [other + rest for other in sorted(local_drives()) if other != drive]


def drive_of(path) -> str:
    """The drive a path lives on, in `mounted_drives` spelling, or "" for one
    that is not on a drive of its own (a network share, the Mac's system disk)."""
    text = str(path)
    if sys.platform == "win32":
        drive = Path(text).drive.upper()
        return drive if len(drive) == 2 else ""
    parts = Path(text).parts
    if len(parts) > 2 and Path(*parts[:2]) == _VOLUMES:
        return str(Path(*parts[:3]))
    return ""


def missing_among(paths, exists=os.path.exists) -> set[str]:
    """Which of `paths` are not there. A drive that errors counts as gone."""
    gone = set()
    for p in paths:
        try:
            if not exists(p):
                gone.add(p)
        except (OSError, ValueError):
            gone.add(p)
    return gone


@dataclass
class DriveChange:
    """What one look found different from the one before it."""
    gone_drives: set[str] = field(default_factory=set)
    new_drives: set[str] = field(default_factory=set)
    missing: set[str] = field(default_factory=set)   # there last time, gone now
    back: set[str] = field(default_factory=set)      # gone last time, there now
    # Newly playing from another drive (a remapped letter): stored → found.
    rehomed: dict[str, str] = field(default_factory=dict)
    # Playing from another drive last time, and no longer.
    settled: set[str] = field(default_factory=set)

    def paths(self) -> set[str]:
        """Every title whose row has to be painted again."""
        return self.missing | self.back | set(self.rehomed) | self.settled


class DriveWatch:
    """Remembers the last look and tells what changed since.

    A title only counts as newly missing when the last look saw it there:
    a playlist restored with a few gone files, or a title dropped in from a
    stick that is gone again, was never on the floor, and is red already."""

    def __init__(self):
        self.drives: frozenset[str] | None = None
        self.checked: set[str] = set()
        self.gone: set[str] = set()
        self.elsewhere: set[str] = set()

    def step(self, drives, checked, missing, found=None) -> DriveChange | None:
        """Feed one look; the change, or None when nothing changed (always
        None for the first look, which only sets the baseline). `found` maps
        a title that is not at its own path to the file that plays instead."""
        drives, checked, missing = frozenset(drives), set(checked), set(missing)
        # Only a copy on ANOTHER drive is a remap; a 🧭 search folder on the
        # title's own drive is the old "moved" case and says nothing new.
        elsewhere = {p: f for p, f in (found or {}).items()
                     if drive_of(p) and drive_of(f) and drive_of(f) != drive_of(p)}
        first = self.drives is None
        change = DriveChange(
            gone_drives=set(self.drives or ()) - drives,
            new_drives=set(drives - (self.drives or drives)),
            missing=(missing & self.checked) - self.gone,
            back=(self.gone & checked) - missing,
            rehomed={p: f for p, f in elsewhere.items()
                     if p in self.checked and p not in self.elsewhere},
            settled=(self.elsewhere & checked) - set(elsewhere) - missing)
        self.drives, self.checked, self.gone = drives, checked, missing
        self.elsewhere = set(elsewhere)
        if first or not (change.gone_drives or change.new_drives
                         or change.paths()):
            return None
        return change


def warning(change: DriveChange) -> str:
    """The note the window shows, with the likely cause first; "" when no
    title is touched (a drive nothing plays from came or went)."""
    if change.missing:
        drives = sorted({drive_of(p) for p in change.missing} & change.gone_drives)
        if drives:
            return (i18n.t("🔌 Drive %s is gone: USB stick unplugged? "
                           "%d titles can't play until it is back.")
                    % (", ".join(drives), len(change.missing)))
        return (i18n.t("⚠️ %d titles are gone from disk: moved, renamed or deleted?")
                % len(change.missing))
    if change.rehomed:
        old = sorted({drive_of(p) for p in change.rehomed})
        new = sorted({drive_of(f) for f in change.rehomed.values()})
        return (i18n.t("🔌 %d titles are no longer on %s: found on %s, "
                       "they play from there.")
                % (len(change.rehomed), ", ".join(old), ", ".join(new)))
    if change.back:
        return i18n.t("🔌 %d titles are back and can play again.") % len(change.back)
    return ""
