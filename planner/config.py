#!/usr/bin/env python3
"""Path configuration for the Dancesport Playlist Planner.

Extracted from dancesport_planner.py (light split): holds every filesystem
location the planner, the DB layer and the GUI share, including the
env-var / planner_config.json override mechanism.
"""

import json
import logging
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

log = logging.getLogger("dancesport.config")


def _app_dir() -> Path:
    """The folder the app itself lives in — its code and the files shipped with it.

    When running as a normal script that's the folder this package sits in.
    When frozen
    into an .exe by PyInstaller, `__file__` points inside the temporary unpack
    dir, so instead we use the folder the .exe itself sits in — that's where a
    deployed build keeps ffmpeg.exe and build_flavor.txt."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def restore_system_library_path(environ=os.environ, *, frozen=None,
                                platform=sys.platform) -> None:
    """Give the programs we start the system's libraries back (Linux build).

    PyInstaller's bootloader points LD_LIBRARY_PATH at the bundled libraries
    and keeps the old value as LD_LIBRARY_PATH_ORIG, but only when there was
    one. Children inherit it, so gsettings or a system ffmpeg would load the
    bundle's older glib or Qt's trimmed FFmpeg and fail. The app itself is not
    affected: the loader read the variable once, when the process started."""
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if not frozen or not platform.startswith("linux"):
        return
    orig = environ.get("LD_LIBRARY_PATH_ORIG")
    if orig is None:
        environ.pop("LD_LIBRARY_PATH", None)
    else:
        environ["LD_LIBRARY_PATH"] = orig


def _is_writable(folder: Path) -> bool:
    """Can we really create a file in here? Probe it — don't ask `os.access`.

    On Windows `os.access(W_OK)` only reports the read-only *attribute* and
    happily says yes for a folder whose ACLs deny writes (`C:\\Program Files`).
    Creating a file and deleting it again is the only honest answer, and it
    costs one stat's worth of time once per process."""
    probe = folder / f".write_probe_{os.getpid()}"
    try:
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def _in_app_bundle(folder: Path) -> bool:
    """Is this folder inside a macOS .app? Then it is off limits even if writable.

    A bundle dragged into /Applications by an admin user IS writable, so the
    probe below would happily put the database in Contents/MacOS — where it
    breaks the code signature and where the next version replaces the whole
    bundle, database and all. A .app is a read-only artefact by convention."""
    parts = folder.parts
    return ("Contents" in parts and any(p.endswith(".app") for p in parts))


# The per-user data folder's name, and the one it had before the app was renamed.
DATA_FOLDER_NAME = "DanceSport-Planner-Player"
_OLD_DATA_FOLDER_NAME = "DancePlaylist"


def _user_data_dir() -> Path:
    """The per-user spot for app data on this OS, when the app folder is read-only."""
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(root) / DATA_FOLDER_NAME


def _move_old_data_dir(new: Path) -> Path:
    """Carry the user folder over from the app's old name; return the one to use.

    The old folder is renamed whole — the same disk, so nothing is copied — and
    only while the new one does not exist yet. If the rename fails (another
    copy of the app still has the database open) the old folder stays in use:
    starting empty beside the user's real data would look like data loss."""
    old = new.with_name(_OLD_DATA_FOLDER_NAME)
    if new.exists() or not old.is_dir():
        return new
    try:
        old.rename(new)
    except OSError as exc:
        log.error("🗂️ Could not move the data folder to the new app name\n"
                  "old: %s\n"
                  "new: %s\n"
                  "error: %s\n"
                  "keeps using the old folder", old, new, exc)
        return old
    log.warning("🗂️ Data folder moved to the new app name\n"
                "old: %s\n"
                "new: %s", old, new)
    return new


def _data_dir(install_dir: Path) -> Path:
    """Where everything the app WRITES goes: DB, caches, JSON state, playlists, logs.

    Next to the app whenever that folder takes writes — that is the normal case
    here and it keeps the portable-folder property: copy the folder to a stick
    and the whole configuration travels with it, no migration, nothing hidden
    in a user profile.

    It falls back to the per-user location only where writing next to the app
    is not allowed or not done: inside a macOS .app bundle (see
    `_in_app_bundle`), or under a folder that refuses writes such as
    `C:\\Program Files`. Without this the app would come up and then fail on
    every single save."""
    bundled = _in_app_bundle(install_dir)
    if not bundled and _is_writable(install_dir):
        return install_dir
    fallback = _move_old_data_dir(_user_data_dir())
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.error("🗂️ No writable data folder\n"
                  "app folder: %s (unusable)\n"
                  "fallback: %s\n"
                  "error: %s", install_dir, fallback, exc)
        return install_dir
    log.warning("🔒 Data goes to the user folder\n"
                "app folder: %s\n"
                "reason: %s\n"
                "data folder: %s", install_dir,
                "inside a .app bundle" if bundled else "not writable", fallback)
    return fallback


# ── Paths ──────────────────────────────────────────────────────────────────────
# App-local files (caches, DB, output) live next to this script — unless it sits
# somewhere unwritable, see _data_dir. The user-specific directories (music
# library, learned playlists, output) can be overridden without editing code —
# precedence:
#   1. environment variable (DANCEPLAYLIST_MUSIC_DIR / _PLAYLIST_DIR / _OUTPUT_DIR)
#   2. planner_config.json in the data dir (keys: music_dir, playlist_dir, output_dir)
#   3. built-in default
INSTALL_DIR = _app_dir()      # read-only side: shipped files (ffmpeg, build marker)
_BASE_DIR = _data_dir(INSTALL_DIR)
APP_DIR = _BASE_DIR   # public alias for the GUI / other modules
PATH_CONFIG_FILE = _BASE_DIR / "planner_config.json"


def build_flavor() -> str:
    """Which build this is: 'lite' / 'full' / 'player' for a frozen .exe (marker file
    `build_flavor.txt`, written by dancesport.spec and driven by build_exe.bat's
    DANCESPORT_BUILD), or 'dev' when running from source. The GUI hides optional
    heavy features (OpenL3/Demucs) in frozen builds that don't bundle them
    — in an exe a pip hint is useless.

    Read from beside the .exe first, where a hand-placed marker belongs, then
    from the bundle folder: the spec ships the file as data, and PyInstaller
    puts data in `_internal`, not next to the .exe. Looking only beside the exe
    found nothing and fell back to 'lite' — right for a lite build by accident,
    and wrong for every full one."""
    if not getattr(sys, "frozen", False):
        return "dev"
    for folder in (INSTALL_DIR, Path(getattr(sys, "_MEIPASS", INSTALL_DIR))):
        try:
            flavor = (folder / "build_flavor.txt").read_text(
                encoding="utf-8").strip().lower()
        except OSError:
            continue
        return flavor if flavor in ("lite", "full", "player") else "lite"
    return "lite"


def player_build() -> bool:
    """True in a player-only build: the .exe carries neither the librosa
    analysis stack nor the planning half of the UI, so the app mode is fixed
    to 'player' and the planner controls are hidden outright rather than
    offered and then failing."""
    return build_flavor() == "player"


def _load_path_config() -> dict:
    try:
        cfg = json.loads(PATH_CONFIG_FILE.read_text(encoding='utf-8'))
        if not isinstance(cfg, dict):
            raise ValueError("top-level value must be a JSON object")
        return cfg
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log.warning("⚠️ Ignoring invalid %s: %s", PATH_CONFIG_FILE.name, exc)
        return {}


_PATH_CFG = _load_path_config()


def _configured_dir(env_key: str, cfg_key: str, default: Path) -> Path:
    val = os.environ.get(env_key) or _PATH_CFG.get(cfg_key)
    return Path(val).expanduser() if val else default


def _default_music_dir() -> Path:
    """The library when nothing is configured — per OS, because a drive letter
    is not portable.

    `C:` and `F:` name volumes of the Windows PC; a Mac has neither, and a
    default that cannot exist there sends every later fallback down the wrong
    road. The same library sits under the home folder on the Mac:
    `/Users/<user>/Music/my music/tanzcds`."""
    if sys.platform == "win32":
        return Path.home() / "Documents" / "datein" / "my music" / "tanzcds"
    return Path.home() / "Music" / "my music" / "tanzcds"


def _default_playlist_dir() -> Path:
    """The learned-playlists folder when nothing is configured (see
    `_default_music_dir`). Dropbox syncs to `~/Dropbox` away from Windows."""
    if sys.platform == "win32":
        return Path(r"D:\Dropbox\Turniere")
    return Path.home() / "Dropbox" / "Turniere"


MUSIC_DIR = _configured_dir("DANCEPLAYLIST_MUSIC_DIR", "music_dir",
                            _default_music_dir())
PLAYLIST_DIR = _configured_dir("DANCEPLAYLIST_PLAYLIST_DIR", "playlist_dir",
                               _default_playlist_dir())
OUTPUT_DIR = _configured_dir("DANCEPLAYLIST_OUTPUT_DIR", "output_dir",
                             _BASE_DIR / "playlists")


def set_playlist_dir(path) -> None:
    """Repoint the learned-playlists dir at runtime (⚙ GUI setting).

    PLAYLIST_DIR was re-imported by name into the planner modules at import
    time, so their module globals are updated too — otherwise they would keep
    using the old binding."""
    global PLAYLIST_DIR
    PLAYLIST_DIR = Path(path).expanduser()
    for mod_name in ("planner.library", "planner.competition", "dancesport_planner"):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "PLAYLIST_DIR"):
            mod.PLAYLIST_DIR = PLAYLIST_DIR
CACHE_FILE = _BASE_DIR / "audio_features.json"
AUDIO_DB_FILE = _BASE_DIR / "audio_features.db"
SCAN_CACHE_FILE = _BASE_DIR / "scan_cache.json"
GLOBAL_SCAN_CACHE_FILE = _BASE_DIR / "global_scan_cache.json"

def write_json_atomic(path: Path, obj: Any) -> None:
    """Write JSON via a temp file + os.replace so a crash never corrupts the target.

    os.replace is atomic on Windows and POSIX: the target either keeps its old
    content or gets the complete new one — never a half-written file. The data
    is fsync'd first (the rename is journaled, the bytes are not: a power cut
    could otherwise swap in an empty file), and the temp file is unique per
    call, so two writers of one file never share it.
    """
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

@contextmanager
def replacing_text(path: Path, encoding: str = "utf-8"):
    """A text file handle whose content replaces `path` only once it is whole.

    For the writers that go line by line (the playlist exports): opening the
    target with 'w' truncated it the moment the save began, so anything that
    raised half-way left half a file where the whole old one had been. Written
    to a temp file next to it, synced, and swapped in with os.replace when the
    block ends cleanly; an exception leaves the old file and no temp behind.
    """
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            yield f
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

# The app's other JSON files — themes, OpenRouter credentials, settings,
# autosave — are stores in planner.store, resolved against APP_DIR when they
# are read rather than while this module imports.
