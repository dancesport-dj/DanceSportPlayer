#!/bin/sh
# Build the Linux one-folder app — the counterpart of build_exe.bat and build_app.sh.
#   ./build_linux.sh            -> lite (dist/DanceSport-Planner-Player)
#   ./build_linux.sh full       -> full (dist/DanceSport-Planner-Player-Full, + Demucs)
#   ./build_linux.sh player     -> player (dist/DanceSport-Player, no analysis stack)
#   ./build_linux.sh player tar -> also dist/DanceSport-Player-linux-x86_64.tar.gz to hand around
#                                  (-linux-arm64.tar.gz on an ARM machine)
#
# Run this ON Linux: PyInstaller does not cross-build. The result runs on every
# distribution whose glibc is at least as new as this machine's, so build on an
# old one (CI uses Ubuntu 22.04, and 24.04 for ARM). See BUILD.md for the system libraries Qt
# needs on the build machine.
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
# dependency still "builds" — it just yields an app that dies on launch with
# "PySide6 not found". Check first.
"$PY" - <<'EOF' || exit 1
import os
import sys

if sys.version_info < (3, 14):
    sys.exit(f"❌ Python {sys.version.split()[0]} is too old — the code needs 3.14+.\n"
             f"   interpreter: {sys.executable}\n"
             f"   fix: python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller")

# The player flavor is built without librosa on purpose (see BUILD.md), so
# demanding it here would refuse the very venv that flavor wants.
mods = ["PySide6", "numpy", "mutagen", "PyInstaller"]
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
             f"   fix: .venv/bin/pip install -r {reqs} pyinstaller")
EOF

# The manual as a PDF, which the spec bundles (tools/build_manual_pdf, printed
# by Chrome, Chromium or Edge). Without one the build goes on, only without a manual.
"$PY" -m tools.build_manual_pdf || echo "NOTE: no manual PDF printed, see above"

"$PY" -m PyInstaller dancesport.spec --noconfirm

# ffmpeg is not bundled (the repo carries the Windows build only). It is needed
# for the library analysis, the loudness scan and the silence detection.
command -v ffmpeg >/dev/null 2>&1 || echo "NOTE: no ffmpeg on PATH — install it with the package manager"

if [ "$2" = "tar" ] || [ "$1" = "tar" ]; then
    # A tar keeps the executable bit, which a zip drops. Packed straight from
    # the build: a start writes its settings and logs next to the executable.
    # The guide names the player, so the other flavors go without it.
    if [ "$DANCESPORT_BUILD" = "player" ]; then
        cp docs/install/linux.md "dist/$APP_NAME/README.txt"
        if [ -f docs/manual/manual.pdf ]; then cp docs/manual/manual.pdf "dist/$APP_NAME/Manual.pdf"; fi
        if [ -f docs/manual/de/manual.pdf ]; then cp docs/manual/de/manual.pdf "dist/$APP_NAME/Handbuch.pdf"; fi
        # And the licence texts in a folder of their own; the bundle has them too.
        mkdir -p "dist/$APP_NAME/Licenses"
        cp LICENSE "dist/$APP_NAME/Licenses/"
        cp ICONS-LICENSE.txt "dist/$APP_NAME/Licenses/"
        cp THIRD_PARTY_LICENSES.md "dist/$APP_NAME/Licenses/"
        cp speech/LICENSE-AUDIO.md "dist/$APP_NAME/Licenses/"
    fi
    # The name says which machines it runs on: a build runs only on its own
    # architecture, and box64 on an ARM machine does not get it to start.
    ARCH=$(uname -m)
    [ "$ARCH" = aarch64 ] && ARCH=arm64
    tar -czf "dist/$APP_NAME-linux-$ARCH.tar.gz" -C dist "$APP_NAME"
    echo "Packed dist/$APP_NAME-linux-$ARCH.tar.gz"
fi

echo "Built dist/$APP_NAME"
echo "Data (database, settings, playlists) goes next to the executable, or to ~/.local/share/DanceSport-Planner-Player where that folder is read-only"
