# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Dancesport Playlist Planner GUI.

One spec, two flavors (same split as requirements.txt vs requirements-full.txt):

  LITE (default, ~0.7 GB):
      .venv\\Scripts\\pyinstaller.exe dancesport.spec --noconfirm
      → dist\\DanceSport-Planner-Player\\DanceSport-Planner-Player.exe
      Core app only; the Demucs / OpenL3 buttons show a pip hint.

  FULL (~4 GB, adds the torch stack → 🎙️ Demucs vocals):
      set DANCESPORT_BUILD=full  (PowerShell: $env:DANCESPORT_BUILD='full')
      .venv\\Scripts\\pyinstaller.exe dancesport.spec --noconfirm
      → dist\\DanceSport-Planner-Player-Full\\DanceSport-Planner-Player-Full.exe

  Or simply:  build_exe.bat  /  build_exe.bat full

macOS (same spec, run it ON a Mac — PyInstaller cannot cross-build):
      ./build_app.sh          → dist/DanceSport-Planner-Player.app
      ./build_app.sh full     → dist/DanceSport-Planner-Player-Full.app
      ./build_app.sh lite dmg → plus a DanceSport-Planner-Player.dmg to hand around
  The .app is built for the architecture of the Mac that builds it (no
  universal2: llvmlite/numba/soundfile have no universal wheels), and it keeps
  its data in ~/Library/Application Support/DanceSport-Planner-Player rather than inside
  the bundle — see planner.config._in_app_bundle.

OpenL3 stays excluded from BOTH flavors: it needs tensorflow next to torch
(a second multi-GB ML framework in one bundle, fragile under PyInstaller) and
its weights download at import time. Use a venv install for OpenL3.

The app keeps its database + JSON files NEXT TO the .exe (planner.config._app_dir
switches to the executable's folder when frozen), so audio_features.db,
gui_settings.json, the caches and the playlists\\ output all live in the dist
folder and persist across runs. Copy an existing audio_features.db into that
folder to reuse already-analysed features. Model weights (htdemucs) are
still downloaded on first use into the user's cache, not bundled.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all

FLAVOR = os.environ.get("DANCESPORT_BUILD", "lite").strip().lower()
FULL = FLAVOR == "full"
PLAYER = FLAVOR == "player"
MACOS = sys.platform == "darwin"
app_name = ("DanceSport-Planner-Player-Full" if FULL else
            "DanceSport-Player" if PLAYER else "DanceSport-Planner-Player")
# What Finder, the Dock and the permission prompts show: the name the app gives
# itself (gui.dialogs.app_title). The bundle id below stays the old one, so a Mac
# keeps the permissions it already granted.
display_name = "DanceSport Player" if PLAYER else "DanceSport Planner & Player"
_flavor_caption = ("FULL (Demucs)" if FULL else
                   "PLAYER (no analysis stack)" if PLAYER else "LITE")
# Plain ASCII — PyInstaller prints this through a cp1252 Windows console.
print(f"Building the {_flavor_caption} flavor -> "
      f"dist{os.sep}{app_name}{'.app' if MACOS else ''}")

datas = []
binaries = []
hiddenimports = []

# Packages whose data files / dynamic submodules PyInstaller can't fully infer.
# librosa (+ its numba/sklearn/scipy/soundfile stack) is the important one.
collect_pkgs = [] if PLAYER else [
    "librosa",
    "numba",
    "llvmlite",
    "scipy",
    "soundfile",
    "audioread",
    "soxr",
    "pooch",
    "lazy_loader",
    "joblib",
    "msgpack",
    "decorator",
]
if FULL:
    # demucs ships the remote-model listing its weight download reads. torch
    # itself is handled by the pyinstaller-hooks-contrib torch hook.
    collect_pkgs += ["demucs"]

for _pkg in collect_pkgs:
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    # A package's own test suite is never run from the .exe. scipy alone brings
    # ~20 MB of test fixtures along.
    hiddenimports += [_m for _m in _h if ".tests" not in _m]

# Read-only app resources that the code loads relative to its own folder.
datas += [("icon.ico", "."), ("icon.png", ".")]
# The pictures ⚙ Settings shows for each theme (shared/looks.py PREVIEW_DIR,
# rendered by tools/theme_previews.py).
datas += [(os.path.join(SPECPATH, "assets", "themes", "*.png"),
           os.path.join("assets", "themes"))]
# The manual as a PDF, English and German, for the app to open from its ❔
# menu. Built by tools/build_manual_pdf and not in git; a build without one
# has no manual in that language.
for _dest in (os.path.join("docs", "manual"), os.path.join("docs", "manual", "de")):
    _manual = os.path.join(SPECPATH, _dest, "manual.pdf")
    if os.path.isfile(_manual):
        datas += [(_manual, _dest)]
        print(f"Manual: {_dest}/manual.pdf bundled")
    else:
        print(f"NOTE: no {_dest}/manual.pdf, the build has no manual there "
              "(py -m tools.build_manual_pdf)")
# The licence texts: the app's own MIT licence, the icons' (Icons8, Bootstrap,
# Twemoji), every bundled library's and the ElevenLabs voices'. MIT, CC-BY and
# the voices' terms want the notice in every copy, the .app included.
for _licence in ("LICENSE", "ICONS-LICENSE.txt", "THIRD_PARTY_LICENSES.md",
                 "speech/LICENSE-AUDIO.md"):
    datas += [(os.path.join(SPECPATH, _licence), "licenses")]
# A presenter theme's mark, resolved by player/presenter_theme.py relative to
# the repo root — so it has to land in the bundle under the same folder name.
# The wedding marks are a couple's names and stay out of git: a clone has none,
# and the theme then simply shows no mark.
_marks = os.path.join(SPECPATH, "assets", "hochzeit")
if os.path.isdir(_marks):
    datas += [(os.path.join(_marks, "*.png"), os.path.join("assets", "hochzeit"))]
# The recorded dance announcements, one folder per language and voice. Missing
# ones only cost the hall the German clip or the announcement, so an
# incomplete set still builds. A folder without a clip in it is skipped too:
# PyInstaller fails on a pattern that matches nothing.
for _language in ("german", "english"):
    for _gender in ("female", "male"):
        _clips = os.path.join(SPECPATH, "speech", "announcements",
                              _language, _gender)
        if os.path.isdir(_clips) and any(n.endswith(".mp3")
                                         for n in os.listdir(_clips)):
            datas += [(os.path.join(_clips, "*.mp3"),
                       os.path.join("speech", "announcements",
                                    _language, _gender))]

# Finder wants .icns and refuses an .ico. Ship an icon.icns next to this spec
# for a crisp Dock icon (`sips -s format icns icon.png --out icon.icns`);
# without one PyInstaller converts the PNG itself when Pillow is installed.
if MACOS:
    app_icon = "icon.icns" if os.path.exists(os.path.join(SPECPATH, "icon.icns")) \
               else "icon.png"
else:
    app_icon = "icon.ico"

# Build-flavor marker: lets the app know which flavor it is at runtime
# (planner.config.build_flavor), so the GUI can hide the heavy AI features
# the lite exe doesn't bundle instead of showing dead "not installed" hints.
_flavor_file = os.path.join(SPECPATH, "build_flavor.txt")
with open(_flavor_file, "w", encoding="utf-8") as _f:
    _f.write("full" if FULL else "player" if PLAYER else "lite")
datas += [(_flavor_file, ".")]

# Which release this is (planner.version): the tag CI builds from, else
# VERSION in the code. The app shows it in the title bar and 🐞 error reports carry it, so
# a report names the build it came from. Into the build folder, like the DSN.
sys.path.insert(0, SPECPATH)
from planner.version import VERSION_FILE, build_version, numbers  # noqa: E402
VERSION = build_version()
VERSION_NUMBERS = ".".join(map(str, numbers(VERSION)))
os.makedirs(workpath, exist_ok=True)
_version_file = os.path.join(workpath, VERSION_FILE)
with open(_version_file, "w", encoding="utf-8") as _f:
    _f.write(VERSION)
datas += [(_version_file, ".")]
print(f"Version: {VERSION}")

# The same on the .exe itself (Properties → Details), where Windows wants
# numbers: 1.2.0 is file version 1.2.0.0, the full text is the product version.
exe_version_info = None
if sys.platform == "win32":
    _n = numbers(VERSION) + (0,)
    exe_version_info = os.path.join(workpath, "exe_version_info.txt")
    with open(exe_version_info, "w", encoding="utf-8") as _f:
        _f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={_n}, prodvers={_n}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('ProductName', {display_name!r}),
      StringStruct('FileDescription', {display_name!r}),
      StringStruct('ProductVersion', {VERSION!r}),
      StringStruct('FileVersion', {VERSION!r}),
      StringStruct('OriginalFilename', {app_name + '.exe'!r}),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ])
""")

# 🐞 Where opt-in error reports go (shared.error_reports). Not in the source:
# the repository is public. CI passes it from a secret, a local build takes it
# from the git-ignored .env; a build with neither ships no address, and the app
# then offers no reports at all. Written into the build folder, not next to
# this spec, so the address never lands in the working tree.
ERROR_DSN = os.environ.get("DANCEPLAYLIST_ERROR_DSN", "").strip()
if not ERROR_DSN and os.path.exists(os.path.join(SPECPATH, ".env")):
    # Same reading as shared.error_reports.envFileValue, without importing
    # the app (planner.config resolves data folders on import).
    with open(os.path.join(SPECPATH, ".env"), encoding="utf-8") as _f:
        for _line in _f.read().splitlines():
            _name, _sep, _value = _line.partition("=")
            if _sep and _name.strip() == "DANCEPLAYLIST_ERROR_DSN":
                ERROR_DSN = _value.strip().strip("\"'")
if ERROR_DSN:
    os.makedirs(workpath, exist_ok=True)
    _dsn_file = os.path.join(workpath, "error_report_dsn.txt")
    with open(_dsn_file, "w", encoding="utf-8") as _f:
        _f.write(ERROR_DSN)
    datas += [(_dsn_file, ".")]

# The optional AI modules are imported lazily; keep the modules so the buttons
# exist, their heavy backends are flavor-gated (below). A player build shows
# none of those buttons, so it does not need the module pulled in by name —
# the GUI modules that import it at module scope still bring it along, and it
# imports fine with nothing behind it.
if not PLAYER:
    hiddenimports += ["planner.embeddings"]

# planner.i18n loads a language's catalog by name (importlib), which PyInstaller
# cannot follow — without this every build falls back to English. One module per
# language in planner.i18n.LANGUAGES, English excepted (it has no catalog).
hiddenimports += ["planner.lang_de"]

# Never pull these in — OpenL3/tensorflow in both flavors (see docstring), plus
# general build hygiene. (PyInstaller follows even the lazy function-level
# imports in planner.vocals/planner.embeddings, so the optional backends must be
# excluded explicitly in the lite flavor.)
excludes = [
    "tensorflow", "tensorboard", "keras", "openl3", "jax", "flax", "clang",
    "torchvision", "timm",
    # Only the dropped CLAP search used it; torch still reaches for it, so it
    # has to be kept out of the full flavor by name.
    "transformers",
    "skimage", "matplotlib", "IPython", "notebook", "pytest",
    # 28 MB nobody imports: librosa reaches for sklearn only in decompose() and
    # segment(), and the app calls neither (load, get_duration, beat, feature,
    # onset, util.localmax). joblib is NOT in here — librosa.beat needs it.
    "sklearn",
]
if not sys.platform.startswith("linux"):
    # Only the Linux wake lock speaks D-Bus (shared.playback._awake_linux);
    # its import is inside a function, which PyInstaller follows anyway.
    excludes += ["PySide6.QtDBus"]
if PLAYER:
    # The player build runs prepared playlists and never analyses anything, so
    # the entire librosa stack goes — 215 MB of the 483 MB lite build, and by
    # far the biggest single win here. Nothing breaks: every import of these is
    # either try/except-guarded (planner.db's HAS_NUMPY / HAS_LIBROSA,
    # planner.similarity) or inside a function that this build never reaches,
    # so the similarity subsystem simply reports itself unavailable.
    #
    # numpy STAYS. The three features a player build must keep are loudness
    # (ffmpeg ebur128), tempo/pitch (Qt's own media backend) and the Paso Doble
    # highlight detection — and that last one computes its RMS envelope with
    # numpy after decoding through ffmpeg (shared.audio_probes._rms_envelope).
    excludes += ["librosa", "numba", "llvmlite", "scipy", "soundfile", "soxr",
                 "audioread", "pooch", "lazy_loader", "joblib", "msgpack",
                 "decorator"]
    # No AI backends and no OpenRouter UI in this build, so nothing left here
    # speaks TLS. Dropping the module drops OpenSSL's two DLLs with it (~13 MB);
    # hashlib falls back to its built-in digests without _hashlib.
    # The one exception is the 🐞 error reports: they go out over HTTPS.
    if not ERROR_DSN:
        excludes += ["ssl", "_ssl"]
if not FULL:
    # The torch stack only exists in the full flavor. (sympy is a torch
    # dependency, so it must stay IN when FULL.)
    excludes += ["torch", "torchaudio", "demucs", "sympy"]
    # Demucs pulls its weights through huggingface_hub, which lands on hf_xet
    # (9 MB) + PIL (13 MB, via a TYPE_CHECKING import) + safetensors. The lite
    # flavor hides the 🎙 vocals button outright, so none of it can ever run,
    # and planner.vocals imports torch inside a function — it still imports fine
    # without any of them.
    excludes += ["huggingface_hub", "hf_xet", "safetensors", "PIL"]

a = Analysis(
    ["dancesport_gui.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# ── Trimming what the app provably never opens ───────────────────────────────
# Qt's software OpenGL renderer (Mesa llvmpipe) is a 20 MB fallback for machines
# with no GL driver — it is loaded by Qt Quick / QOpenGLWidget, and this app is
# QtWidgets throughout (the raster engine).
_DROP_BINARIES = {"opengl32sw.dll"}

# The player build is QtWidgets and audio only, so three more groups of Qt go.
# The av*/swresample DLLs are NOT among them — that is Qt's own media backend,
# i.e. playback, the tempo fader and the pitch-preserving time stretch.
if PLAYER:
    _DROP_BINARIES |= {
        # PDF rendering, reached only by the printed running order — a control
        # the player build hides (dancesport_gui._player_build_hidden).
        "qt6pdf.dll",
        # Qt Quick / QML: pulled in for QML video output. This app has no video
        # and draws every widget through the raster engine.
        "qt6quick.dll", "qt6qml.dll", "qt6qmlmodels.dll", "qt6qmlmeta.dll",
    }
    if not ERROR_DSN:
        # OpenSSL, matching the "ssl" exclude above.
        _DROP_BINARIES |= {"libcrypto-3.dll", "libcrypto-3-x64.dll",
                           "libssl-3.dll", "libssl-3-x64.dll"}

# The languages the announcements are made in. Qt ships 124 .qm files, ~7 MB,
# for the text of its own dialogs; every other language is dead weight in a
# German tournament hall.
_KEEP_LANGS = ("_de.qm", "_en.qm")


def _keep_binary(dest):
    return os.path.basename(dest).lower() not in _DROP_BINARIES


def _keep_data(dest):
    parts = dest.replace("\\", "/").lower().split("/")
    if "tests" in parts:          # scipy/numpy test fixtures, ~20 MB
        return False
    if dest.endswith(".qm"):
        return dest.endswith(_KEEP_LANGS)
    return True


a.binaries = [entry for entry in a.binaries if _keep_binary(entry[0])]
a.datas = [entry for entry in a.datas if _keep_data(entry[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
    version=exe_version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

if MACOS:
    # Wrap the one-folder build into a real .app so it can be double-clicked and
    # dragged to /Applications. The usage strings are the text macOS shows in
    # its permission prompts — without them the app is KILLED instead of asked
    # about. Removable volumes is the one that matters here: the music library
    # and the 🧳 venue bundle both live on a stick. Desktop / Downloads /
    # Network volumes take the same NS…UsageDescription form if a library ends
    # up there.
    app = BUNDLE(
        coll,
        name=f"{app_name}.app",
        icon=app_icon,
        bundle_identifier="de.marcelkb.danceplaylist",
        info_plist={
            "CFBundleName": app_name,
            "CFBundleDisplayName": display_name,
            # Numbers only, as macOS wants them; the full text is in the app.
            "CFBundleShortVersionString": VERSION_NUMBERS,
            "CFBundleVersion": VERSION_NUMBERS,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSRemovableVolumesUsageDescription":
                f"{display_name} reads your music from external drives and writes "
                "the venue bundle to a USB stick.",
            "NSDocumentsFolderUsageDescription":
                f"{display_name} reads your music library and writes the generated "
                "playlists.",
        },
    )
