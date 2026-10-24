"""📦 Venue pack: the desk of one PC carried to another in one file.

Home is where the playlists are built; the venue laptop is where they are
played. A pack carries what the desk is made of — the settings, the decks of
the autosave, the 🎛 cartwall with its pads and keys — and, when asked, the
music those name, so the laptop needs nothing else.

It is a zip: the JSON documents deflated, the music stored (an MP3 does not
shrink), and a manifest saying which original path became which file inside.

An import is not written over the live files. Closing the window writes the
autosave and the settings one last time, so whatever replaced them while the
app ran would be gone after the restart that is meant to load it. The import is
staged next to them instead and applied at the next start, before anything
reads them — with a copy of what it replaces kept aside.
"""
import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePath, PureWindowsPath

from planner.config import write_json_atomic
from planner.music.paths import PathRemapper, home_search_roots

log = logging.getLogger("dancesport.venue_pack")

FORMAT = "danceplaylist-venue"
VERSION = 1
MANIFEST = "manifest.json"
SUFFIX = ".dpvenue"
STAGE_DIR = "venue_import"
BACKUP_PREFIX = "before-venue-import-"
SETTINGS_FILE = "gui_settings.json"
# The only documents a pack may bring: the names come from the pack itself,
# and the app folder also holds the AI key and the planner config.
PACK_FILES = (SETTINGS_FILE, "autosave_playlist.json", "cartwall.json")

# Tracks: the same list shared/audio/audio_files.py plays.
AUDIO_EXTS = (".mp3", ".m4a", ".m4b", ".flac", ".wav", ".ogg",
              ".oga", ".opus", ".aac", ".wma", ".aiff", ".aif")

# Who may reach this desk from a phone: the remote PIN and whether the remote
# and the guest page are on. A pack never carries them, and one that does
# (written before they were left out) cannot switch them on here.
ACCESS_KEYS = ("remote_pin", "remote_mode", "remote_port",
               "guest_mode", "guest_port")

# Settings that describe THIS machine — its folders, its screens, its audio
# backend — and stay as they are when another machine's settings come in.
MACHINE_KEYS = ("library_dir", "global_dir", "save_dir", "playlist_dir",
                "reference_path", "remap_paths", "open_dir", "import_dir",
                "ai_claude_config_dir", "presenter_screen",
                "presenter_screen_name", "media_backend") + ACCESS_KEYS


class VenuePackError(Exception):
    """The file is not a venue pack this version can read."""


class VenuePackCancelled(Exception):
    """The operator cancelled; nothing half-done is left behind."""


@dataclass
class PackResult:
    tracks: int = 0
    missing: list[str] = field(default_factory=list)


@dataclass
class Pack:
    docs: dict
    music: dict          # original path -> name inside the zip
    created: str = ""


# ── Paths inside the documents ───────────────────────────────────────────────

def _is_track(s) -> bool:
    if not isinstance(s, str) or not s.lower().endswith(AUDIO_EXTS):
        return False
    return PureWindowsPath(s).is_absolute() or s.startswith("/")


def _walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk(v)
    else:
        yield obj


def track_paths(*docs) -> list[str]:
    """Every absolute audio path the documents name, once, in order of first
    appearance — as values and as keys (per-title sections are keyed by path)."""
    seen: dict[str, None] = {}
    for doc in docs:
        for s in _walk(doc):
            if _is_track(s):
                seen.setdefault(s, None)
    return list(seen)


def remap(obj, mapping: dict):
    """A copy of `obj` with every string found in `mapping` replaced —
    values and dict keys alike."""
    if isinstance(obj, dict):
        return {mapping.get(k, k) if isinstance(k, str) else k: remap(v, mapping)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [remap(v, mapping) for v in obj]
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def _exists(path: str) -> bool:
    try:
        return Path(path).is_file()
    except OSError:
        return False


def relink(docs: dict, settings: dict) -> tuple[dict, int]:
    """`docs` with every track this machine lacks re-rooted to the copy its own
    folders hold — the 🧭 Fix paths search: Reference path, search folders, the
    library and, away from Windows, the home folder. A path is only rewritten
    to a file that exists. Returns the documents and how many paths moved."""
    roots = [settings.get("reference_path") or ""]
    roots += settings.get("remap_paths") or []
    roots += [settings.get("library_dir") or "", settings.get("global_dir") or ""]
    remapper = PathRemapper([*roots, *home_search_roots()])
    mapping = {}
    if remapper:
        for t in track_paths(*docs.values()):
            if not _exists(t):
                hit = remapper.remap(t)
                if hit is not None:
                    mapping[t] = str(hit)
    if not mapping:
        return docs, 0
    return {name: remap(obj, mapping) for name, obj in docs.items()}, len(mapping)


def merge_settings(local: dict, imported: dict) -> dict:
    """The imported settings, with this machine's own keys kept as they are."""
    out = {k: v for k, v in imported.items() if k not in MACHINE_KEYS}
    for k, v in local.items():
        if k in MACHINE_KEYS or k not in out:
            out[k] = v
    return out


# ── Writing ──────────────────────────────────────────────────────────────────

def _arcname(path: str, taken: set) -> str:
    """music/<folder>/<file>: the folder kept, since a dance can be told by it."""
    p = PureWindowsPath(path) if "\\" in path else PurePath(path)
    folder = p.parent.name or "music"
    stem, ext = PurePath(p.name).stem, PurePath(p.name).suffix
    name, n = f"music/{folder}/{p.name}", 2
    while name.lower() in taken:
        name = f"music/{folder}/{stem} ({n}){ext}"
        n += 1
    taken.add(name.lower())
    return name


def write_pack(dest: Path, docs: dict, include_music: bool,
               progress=None, cancelled=None) -> PackResult:
    """Write `docs` (file name -> JSON object) and, if asked, their music to
    `dest`. The file appears only when complete; cancelling removes it."""
    dest = Path(dest)
    if isinstance(docs.get(SETTINGS_FILE), dict):
        docs = {**docs, SETTINGS_FILE: {k: v for k, v in docs[SETTINGS_FILE].items()
                                        if k not in ACCESS_KEYS}}
    res = PackResult()
    music: dict[str, str] = {}
    tracks = track_paths(*docs.values()) if include_music else []
    present: list[str] = []
    for t in tracks:
        (present if Path(t).is_file() else res.missing).append(t)
    manifest = {"format": FORMAT, "version": VERSION,
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "files": sorted(docs), "music": music,
                "missing": res.missing}
    fd, tmp = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp",
                               dir=dest.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for name, obj in docs.items():
                z.writestr(name, json.dumps(obj, indent=2, ensure_ascii=False))
            taken: set[str] = set()
            for i, t in enumerate(present, 1):
                if cancelled and cancelled():
                    raise VenuePackCancelled()
                arc = _arcname(t, taken)
                z.write(t, arc, compress_type=zipfile.ZIP_STORED)
                music[t] = arc
                res.tracks += 1
                if progress:
                    progress(i, len(present))
            if cancelled and cancelled():
                raise VenuePackCancelled()
            z.writestr(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False))
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    log.info("📦 Venue pack written\n"
             "file: %s\n"
             "tracks: %d\n"
             "missing: %d", dest, res.tracks, len(res.missing))
    return res


# ── Reading ──────────────────────────────────────────────────────────────────

def _manifest(z: zipfile.ZipFile) -> dict:
    try:
        m = json.loads(z.read(MANIFEST).decode("utf-8"))
    except (KeyError, ValueError) as exc:
        raise VenuePackError("no venue pack manifest") from exc
    if not isinstance(m, dict) or m.get("format") != FORMAT:
        raise VenuePackError("not a venue pack")
    if not isinstance(m.get("version"), int) or m["version"] > VERSION:
        raise VenuePackError("made by a newer version of the app")
    return m


def read_pack(src: Path) -> Pack:
    """The documents and the music index of a pack; VenuePackError if it is not one."""
    try:
        with zipfile.ZipFile(src) as z:
            m = _manifest(z)
            docs = {}
            for name in m.get("files", []):
                if name not in PACK_FILES:
                    log.warning("⚠️ Venue pack entry ignored\n"
                                "file: %s", name)
                    continue
                try:
                    docs[name] = json.loads(z.read(name).decode("utf-8"))
                except (KeyError, ValueError) as exc:
                    raise VenuePackError(f"damaged entry: {name}") from exc
                if name == SETTINGS_FILE and not isinstance(docs[name], dict):
                    raise VenuePackError(f"damaged entry: {name}")
    except (zipfile.BadZipFile, OSError) as exc:
        raise VenuePackError(str(exc)) from exc
    return Pack(docs=docs, music=dict(m.get("music") or {}),
                created=str(m.get("created", "")))


def _crc32(path: Path) -> int | None:
    crc = 0
    try:
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                crc = zlib.crc32(chunk, crc)
    except OSError:
        return None
    return crc


def _landing(target: Path, info: zipfile.ZipInfo) -> Path:
    """Where a packed track goes: a copy already there (same size and CRC) is
    reused, and a different file under that name is left alone — the track
    takes "name (2)" instead."""
    stem, ext, n = target.stem, target.suffix, 2
    cand = target
    while cand.is_file():
        if (cand.stat().st_size == info.file_size
                and _crc32(cand) == info.CRC):
            return cand
        cand = target.with_name(f"{stem} ({n}){ext}")
        n += 1
    return cand


def extract_music(src: Path, dest_dir: Path, progress=None, cancelled=None) -> dict:
    """Unpack the music under `dest_dir`; original path -> new path. A file
    already there with the same content is taken as the same file, so importing
    a pack twice copies nothing twice; another file under the name is never
    overwritten (see `_landing`). Cancelling removes what this call wrote."""
    dest_dir = Path(dest_dir)
    mapping, written = {}, []
    try:
        with zipfile.ZipFile(src) as z:
            music = _manifest(z).get("music") or {}
            for i, (orig, arc) in enumerate(music.items(), 1):
                if cancelled and cancelled():
                    raise VenuePackCancelled()
                # The names come from the pack itself: a crafted one could
                # carry "C:" (drive-relative, joins outside dest_dir), ".." or
                # a .bat, so anything but a plain audio file name is skipped.
                parts = PurePath(arc).parts[1:]
                if (not parts or any(p in ("..", "") or ":" in p for p in parts)
                        or not parts[-1].lower().endswith(AUDIO_EXTS)):
                    continue
                target = dest_dir.joinpath(*parts)
                if not target.resolve().is_relative_to(dest_dir.resolve()):
                    continue                    # never write outside dest_dir
                info = z.getinfo(arc)
                target = _landing(target, info)
                if not target.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as fsrc, open(target, "wb") as fdst:
                        written.append(target)
                        shutil.copyfileobj(fsrc, fdst, 1 << 20)
                mapping[orig] = str(target)
                if progress:
                    progress(i, len(music))
    except BaseException:
        for t in written:
            t.unlink(missing_ok=True)
        raise
    return mapping


# ── Staged import, applied at the next start ─────────────────────────────────

def has_pending(state_dir: Path) -> bool:
    return (Path(state_dir) / STAGE_DIR).is_dir()


def stage_import(src: Path, state_dir: Path, music_dir: Path | None,
                 progress=None, cancelled=None) -> Pack:
    """Read the pack, unpack its music into `music_dir` (None: leave it), point
    the documents at it and park them for apply_pending()."""
    pack = read_pack(src)
    docs = pack.docs
    if music_dir is not None and pack.music:
        mapping = extract_music(src, music_dir, progress, cancelled)
        docs = {name: remap(obj, mapping) for name, obj in docs.items()}
    stage = Path(state_dir) / STAGE_DIR
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    for name, obj in docs.items():
        (stage / PurePath(name).name).write_text(
            json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return pack


def apply_pending(state_dir: Path) -> list[str]:
    """Put a staged import in place: the live files are copied aside first, the
    settings are merged so this machine keeps its own folders, and the tracks
    this machine lacks are looked up under those folders (`relink`). Returns
    the file names replaced ([] when nothing was staged)."""
    state_dir = Path(state_dir)
    stage = state_dir / STAGE_DIR
    if not stage.is_dir():
        return []
    docs = {}
    for src in sorted(p for p in stage.iterdir() if p.name in PACK_FILES):
        try:
            docs[src.name] = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("⚠️ Venue import entry skipped\n"
                        "file: %s\n"
                        "error: %s", src.name, exc)
    # Settings that are no object cannot be merged. Raised from here they
    # would leave the stage in place, and every start would fail on it again.
    if SETTINGS_FILE in docs and not isinstance(docs[SETTINGS_FILE], dict):
        log.warning("⚠️ Venue import entry skipped\n"
                    "file: %s\n"
                    "error: not a JSON object", SETTINGS_FILE)
        del docs[SETTINGS_FILE]
    live_settings = state_dir / SETTINGS_FILE
    try:
        local = json.loads(live_settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        local = {}
    local = local if isinstance(local, dict) else {}
    if SETTINGS_FILE in docs:
        docs[SETTINGS_FILE] = merge_settings(local, docs[SETTINGS_FILE])
    docs, relinked = relink(docs, docs.get(SETTINGS_FILE, local))
    backup = state_dir / (BACKUP_PREFIX + time.strftime("%Y%m%d-%H%M%S"))
    # All or nothing: every live file is copied aside before the first one is
    # replaced, and a failed write puts the ones already replaced back. The
    # stage stays, so the next start tries again (a file locked by a sync
    # client or a virus scanner usually is not locked for long).
    applied = []
    try:
        backup.mkdir(exist_ok=True)
        for name in docs:
            if (state_dir / name).exists():
                shutil.copy2(state_dir / name, backup / name)
        for name, obj in docs.items():
            write_json_atomic(state_dir / name, obj)
            applied.append(name)
    except OSError as exc:
        _roll_back(state_dir, backup, applied)
        log.warning("⚠️ Venue pack not applied, tried again next start\n"
                    "error: %s", exc)
        return []
    shutil.rmtree(stage, ignore_errors=True)
    log.info("📥 Venue pack applied\n"
             "files: %s\n"
             "paths relinked: %d\n"
             "backup: %s", ", ".join(applied) or "none", relinked, backup.name)
    return applied


def _roll_back(state_dir: Path, backup: Path, written: list[str]) -> None:
    """Put back the files a half-done apply_pending already replaced: the
    backed-up copy where there was one, else the new file goes again."""
    for name in written:
        try:
            if (backup / name).exists():
                shutil.copy2(backup / name, state_dir / name)
            else:
                (state_dir / name).unlink()
        except OSError as exc:
            log.error("🗄️ Venue import roll-back failed\n"
                      "file: %s\n"
                      "error: %s", name, exc)
    shutil.rmtree(backup, ignore_errors=True)
