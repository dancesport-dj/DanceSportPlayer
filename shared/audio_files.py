"""What counts as an audio file, and the folder the music pickers open in.

The browse folder is module state: the desk seeds it from the settings at
startup and every picker, on either side, reads and updates the same one.
"""
import logging
from pathlib import Path

from PySide6.QtCore import QStandardPaths

import planner.config

log = logging.getLogger("dancesport.gui")


# Extensions the app treats as "a track". Also the allowlist for handing a path
# to the OS' open verb: an imported .m3u may name ANY path and nothing on that
# route checks the suffix, so without this a foreign playlist can point a row at
# a script and the double-click that means "preview this song" runs it.
# TableDragDropMixin uses the same tuple for external drops.
_AUDIO_EXTS = (".mp3", ".m4a", ".m4b", ".flac", ".wav", ".ogg",
               ".oga", ".opus", ".aac", ".wma", ".aiff", ".aif")


# Folder the "click to browse" file dialog opens in (first one that exists);
# falls back to the OS standard Music folder.
def _resolve_browse_dir() -> str:
    candidates = [Path(r"F:\my music"), planner.config.MUSIC_DIR]
    std = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation)
    if std:
        candidates.append(Path(std))
    for p in candidates:
        if p and p.exists():
            return str(p)
    return std or ""

_MUSIC_BROWSE_DIR = _resolve_browse_dir()

# Where the user picked last. The computed folder above is only the FIRST
# start: on a machine that never had F:\my music (every Mac) it lands in
# ~/Music, and a picker that opens there every time makes the operator walk
# the same five folders on every add. Set from settings["open_dir"] at
# startup and persisted through `saver` on every pick.
_last_browse_dir = ""
_browse_dir_saver = None


def set_browse_dir(folder: str, saver=None) -> None:
    """Seed the remembered folder (settings) and say how to persist a new one."""
    global _last_browse_dir, _browse_dir_saver
    _last_browse_dir = str(folder or "")
    _browse_dir_saver = saver


def music_browse_dir() -> str:
    """Folder the music / playlist pickers open in: the last one the user
    picked from, while it is still there."""
    if _last_browse_dir and Path(_last_browse_dir).is_dir():
        return _last_browse_dir
    return _MUSIC_BROWSE_DIR


def remember_browse_dir(path) -> None:
    """Keep the folder a picker just took a file from, for the next one."""
    global _last_browse_dir
    if not path:
        return
    p = Path(path)
    folder = str(p if p.is_dir() else p.parent)
    if folder == _last_browse_dir:
        return
    _last_browse_dir = folder
    if _browse_dir_saver is not None:
        try:
            _browse_dir_saver(folder)
        except Exception as exc:
            log.debug("📂 Could not store the browse folder %s: %s", folder, exc)
