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
from dataclasses import dataclass, field
from pathlib import Path, PurePath, PureWindowsPath

from planner.config import write_json_atomic

log = logging.getLogger("dancesport.venue_pack")

FORMAT = "danceplaylist-venue"
VERSION = 1
MANIFEST = "manifest.json"
SUFFIX = ".dpvenue"
STAGE_DIR = "venue_import"
BACKUP_PREFIX = "before-venue-import-"
SETTINGS_FILE = "gui_settings.json"

# Tracks: the same list shared/audio_files.py plays.
AUDIO_EXTS = (".mp3", ".m4a", ".m4b", ".flac", ".wav", ".ogg",
              ".oga", ".opus", ".aac", ".wma", ".aiff", ".aif")

# Settings that describe THIS machine — its folders, its screens, its audio
# backend — and stay as they are when another machine's settings come in.
MACHINE_KEYS = ("library_dir", "global_dir", "save_dir", "playlist_dir",
                "reference_path", "remap_paths", "open_dir", "import_dir",
                "ai_claude_config_dir", "presenter_screen",
                "presenter_screen_name", "media_backend")


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
    seen = {}
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
    res = PackResult()
    music = {}
    tracks = track_paths(*docs.values()) if include_music else []
    present = []
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
            taken = set()
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
                try:
                    docs[name] = json.loads(z.read(name).decode("utf-8"))
                except (KeyError, ValueError) as exc:
                    raise VenuePackError(f"damaged entry: {name}") from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise VenuePackError(str(exc)) from exc
    return Pack(docs=docs, music=dict(m.get("music") or {}),
                created=str(m.get("created", "")))


def extract_music(src: Path, dest_dir: Path, progress=None, cancelled=None) -> dict:
    """Unpack the music under `dest_dir`; original path -> new path. A file
    already there with the same size is taken as the same file, so importing a
    pack twice copies nothing twice. Cancelling removes what this call wrote."""
    dest_dir = Path(dest_dir)
    mapping, written = {}, []
    try:
        with zipfile.ZipFile(src) as z:
            music = _manifest(z).get("music") or {}
            for i, (orig, arc) in enumerate(music.items(), 1):
                if cancelled and cancelled():
                    raise VenuePackCancelled()
                rel = PurePath(arc)
                if rel.is_absolute() or ".." in rel.parts:
                    continue                    # never write outside dest_dir
                target = dest_dir.joinpath(*rel.parts[1:])
                info = z.getinfo(arc)
                if not (target.is_file() and target.stat().st_size == info.file_size):
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
    settings are merged so this machine keeps its own folders. Returns the
    file names replaced ([] when nothing was staged)."""
    state_dir = Path(state_dir)
    stage = state_dir / STAGE_DIR
    if not stage.is_dir():
        return []
    staged = sorted(p for p in stage.iterdir() if p.suffix == ".json")
    backup = state_dir / (BACKUP_PREFIX + time.strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(exist_ok=True)
    applied = []
    for src in staged:
        live = state_dir / src.name
        try:
            obj = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("⚠️ Venue import entry skipped\n"
                        "file: %s\n"
                        "error: %s", src.name, exc)
            continue
        if live.exists():
            shutil.copy2(live, backup / src.name)
            if src.name == SETTINGS_FILE:
                try:
                    local = json.loads(live.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    local = {}
                obj = merge_settings(local if isinstance(local, dict) else {}, obj)
        elif src.name == SETTINGS_FILE:
            obj = merge_settings({}, obj)
        write_json_atomic(live, obj)
        applied.append(src.name)
    shutil.rmtree(stage, ignore_errors=True)
    log.info("📥 Venue pack applied\n"
             "files: %s\n"
             "backup: %s", ", ".join(applied) or "none", backup.name)
    return applied
