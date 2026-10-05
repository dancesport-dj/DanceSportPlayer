#!/bin/sh
# Build the macOS .app bundle — the counterpart of build_exe.bat.
#   ./build_app.sh            -> lite (dist/DanceSport-Planner-Player.app)
#   ./build_app.sh full       -> full (dist/DanceSport-Planner-Player-Full.app, + Demucs)
#   ./build_app.sh player     -> player (dist/DanceSport-Player.app, no analysis stack)
#   ./build_app.sh lite dmg   -> also dist/DanceSport-Planner-Player.dmg to hand around
#
# Run this ON a Mac: PyInstaller does not cross-build, so a .app can only be
# made on macOS. See dancesport.spec for what goes into the bundle.
set -e
cd "$(dirname "$0")"

case "$1" in
    full)   DANCESPORT_BUILD=full;   APP_NAME=DanceSport-Planner-Player-Full ;;
    player) DANCESPORT_BUILD=player; APP_NAME=DanceSport-Player ;;
    *)      DANCESPORT_BUILD=lite;   APP_NAME=DanceSport-Planner-Player ;;
esac
export DANCESPORT_BUILD

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

# PyInstaller bundles whatever it finds in this interpreter, so a venv missing a
# dependency still "builds" — it just yields an .app that dies on launch with
# "PySide6 not found". The fallback above makes that easy to hit: without a venv
# it lands on Apple's /usr/bin/python3 (3.9), too old for numpy>=2.4. Check first.
"$PY" - <<'EOF' || exit 1
import os
import sys

if sys.version_info < (3, 14):
    sys.exit(f"❌ Python {sys.version.split()[0]} is too old — the code needs 3.14+.\n"
             f"   interpreter: {sys.executable}\n"
             f"   fix: python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller pillow")

# PIL only converts icon.png for the Dock icon; the rest are the app itself.
# The player flavor is built without librosa on purpose (see BUILD.md), so
# demanding it here would refuse the very venv that flavor wants.
mods = ["PySide6", "numpy", "mutagen", "PIL"]
if os.environ.get("DANCESPORT_BUILD") != "player":
    mods.insert(1, "librosa")
missing = []
for mod in mods:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)
if missing:
    reqs = ("requirements-player.txt"
            if os.environ.get("DANCESPORT_BUILD") == "player" else "requirements.txt")
    sys.exit(f"❌ Build venv is missing: {', '.join(missing)}\n"
             f"   interpreter: {sys.executable}\n"
             f"   fix: .venv/bin/pip install -r {reqs} pyinstaller pillow")
EOF

"$PY" -m PyInstaller dancesport.spec --noconfirm

APP="dist/$APP_NAME.app"

# Ad-hoc signature. PyInstaller signs what it writes, but the bundle is assembled
# afterwards and an Apple-silicon Mac refuses to launch a binary whose signature
# no longer matches — it reports the app as "damaged", which sounds like a broken
# download and is really just an unsigned bundle.
if command -v codesign >/dev/null 2>&1; then
    codesign --force --deep --sign - "$APP"
fi

# ffmpeg is not bundled (the repo carries the Windows build only). It is needed
# for the library analysis, the loudness scan and the silence detection.
command -v ffmpeg >/dev/null 2>&1 || echo "NOTE: no ffmpeg on PATH — brew install ffmpeg"

if [ "$2" = "dmg" ] || [ "$1" = "dmg" ]; then
    rm -f "dist/$APP_NAME.dmg"
    hdiutil create -volname "$APP_NAME" -srcfolder "$APP" \
                   -ov -format UDZO "dist/$APP_NAME.dmg"
fi

echo "Built $APP"
echo "Data (database, settings, playlists) goes to ~/Library/Application Support/DanceSport-Planner-Player"
