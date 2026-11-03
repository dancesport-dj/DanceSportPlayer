"""Chromaprint fingerprints of a track, read through the `fpcalc` tool.

The bundled ffmpeg has no chromaprint muxer, so the fingerprint comes from the
small `fpcalc` program of the Chromaprint project (LGPL). Where it is, and how
one track is fingerprinted. The matching itself is `planner.music.chroma_match`.

No Qt and no librosa, like the rest of the probes the player build keeps.
"""
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from planner.config import INSTALL_DIR
from planner.music.chroma_match import Chroma, parse_raw

log = logging.getLogger("dancesport.chroma")

# The audio fpcalc reads. Its own default; a copy cut short or re-encoded still
# lines up over this, and the fingerprint stays about 4 KB.
LENGTH_SECS = 120
TIMEOUT_SECS = 120

# Next to the app / .exe, where a deployed build keeps it, then an unpacked
# chromaprint release in the dev tree.
_BUNDLED_FPCALC = (
    INSTALL_DIR / "fpcalc.exe",
    INSTALL_DIR / "fpcalc",
    *sorted(Path(__file__).parents[2].glob("chromaprint-fpcalc-*/fpcalc.exe"),
            reverse=True),
)
# After PATH, the package-manager prefixes a GUI launch does not have on PATH.
_FPCALC_CANDIDATES = (
    Path("/opt/homebrew/bin/fpcalc"),
    Path("/usr/local/bin/fpcalc"),
    Path("/opt/local/bin/fpcalc"),
    Path("/home/linuxbrew/.linuxbrew/bin/fpcalc"),
    Path.home() / ".linuxbrew" / "bin" / "fpcalc",
)


def find_fpcalc() -> str | None:
    """The bundled fpcalc, else fpcalc on PATH, else the usual Homebrew /
    MacPorts prefixes, else None. On PATH never one in the current folder:
    Windows' lookup tries that first, so a planted fpcalc.exe in a music folder
    would run on every fingerprint."""
    for cand in _BUNDLED_FPCALC:
        if cand.is_file():
            return str(cand)
    exe = shutil.which("fpcalc")
    if exe and Path(exe).resolve().parent != Path.cwd().resolve():
        return exe
    for cand in _FPCALC_CANDIDATES:
        if cand.is_file():
            return str(cand)
    return None


def parse_output(text: str) -> Chroma | None:
    """The DURATION= and FINGERPRINT= lines of `fpcalc -raw`, or None when the
    output holds no fingerprint."""
    duration = 0.0
    words = None
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key == "DURATION":
            try:
                duration = float(value)
            except ValueError:
                duration = 0.0
        elif key == "FINGERPRINT":
            try:
                words = parse_raw(value)
            except ValueError:
                return None
    if words is None or not len(words):
        return None
    return Chroma(duration, words)


def fingerprint_file(fpcalc: str, path, on_proc=None) -> Chroma | None:
    """Fingerprint one track, or None when fpcalc cannot read it.

    `on_proc` is handed the Popen as soon as it exists, so a worker can kill it
    when the pass is cancelled. A path that is no file on disk is never given to
    fpcalc: it would read a `http://…` line of an imported playlist as a URL."""
    try:
        if not Path(path).is_file():
            return None
    except OSError:
        return None
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    args = [fpcalc, "-raw", "-length", str(LENGTH_SECS), os.path.abspath(path)]
    try:
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", creationflags=flags)
    except OSError as exc:
        log.warning("🎼 fpcalc did not start\nfile: %s\nerror: %s", path, exc)
        return None
    if on_proc is not None:
        on_proc(proc)
    try:
        out, _err = proc.communicate(timeout=TIMEOUT_SECS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        log.warning("🎼 fpcalc timed out\nfile: %s", path)
        return None
    if proc.returncode != 0:
        return None
    return parse_output(out)
