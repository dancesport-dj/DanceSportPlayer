"""Which release a build is, so an error report names the build it came from.

The number is VERSION below. A release tag overrides it: CI passes the tag
in DANCEPLAYLIST_VERSION, so the app in a GitHub release says what the
release is named. The tag's v is dropped: the app says 1.2.0, never v1.2.0.
dancesport.spec writes the result into the bundle as build_version.txt, and
the running app reads it back. A source run is "dev".

No Qt and no planner.config in here: the spec imports this module, and
planner.config resolves the data folders on import.
"""
import os
import re
import sys
from pathlib import Path

# The release this code is, for a build without a tag.
VERSION = "1.1.1"
VERSION_ENV = "DANCEPLAYLIST_VERSION"
VERSION_FILE = "build_version.txt"
DEV = "dev"


def build_version() -> str:
    """For the spec: the version to bake in. The release tag CI builds from
    without its v, else VERSION."""
    return os.environ.get(VERSION_ENV, "").strip().removeprefix("v") or VERSION


def numbers(version: str) -> tuple[int, int, int]:
    """(major, minor, patch) of a version like 1.2.0, for the places that take
    numbers only (the .exe's file version, the macOS bundle version); a
    version without them is 0.0.0. It takes a dot, so "dev" or a commit hash
    like 728c49b is no version 728."""
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version.strip())
    if not m:
        return (0, 0, 0)
    return tuple(int(part or 0) for part in m.groups())


def app_version() -> str:
    """The version of this run: what the build baked in, or "dev" from source."""
    if not getattr(sys, "frozen", False):
        return DEV
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    try:
        value = (bundle / VERSION_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return DEV
    return value or DEV
