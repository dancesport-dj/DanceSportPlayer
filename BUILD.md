# Building the app

The GUI can be packaged into a standalone application with PyInstaller — a
Windows `.exe` folder, or a macOS `.app` bundle from the same spec.

## Build (Windows)

```powershell
.venv\Scripts\pyinstaller.exe dancesport.spec --noconfirm
```

Output is a **one-folder** build at `dist\DanceSport-Planner-Player\` with `DanceSport-Planner-Player.exe`
inside. Ship the whole `DanceSport-Planner-Player` folder (the `_internal\` subfolder holds
the Python runtime, PySide6, librosa, etc.).

Or drive it through `build_exe.bat`, which picks the flavor, checks the venv and
copies `ffmpeg.exe` into the result:

```powershell
build_exe.bat            rem lite   -> dist\DanceSport-Planner-Player          (~483 MB)
build_exe.bat full       rem full   -> dist\DanceSport-Planner-Player-Full     (+ Demucs)
build_exe.bat player     rem player -> dist\DanceSport-Player   (~220 MB, see below)
```

## Build (macOS)

**Must run on a Mac.** PyInstaller does not cross-build: it bundles the
interpreter and the compiled wheels of the machine it runs on, so there is no
way to produce a `.app` from Windows.

Needs **Python 3.14 or newer**. The code writes forward references unquoted and
leans on PEP 649 lazy annotations for them, so anything older raises `NameError`
on import — and `numpy>=2.4` has no wheels below 3.11 anyway. Apple's bundled
`/usr/bin/python3` is 3.9 — do not build against it, or you get an `.app` that
launches and immediately quits with "PySide6 not found". Install a current
Python from <https://www.python.org/downloads/macos/> and use it by name:

```sh
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller pillow
./build_app.sh            # dist/DanceSport-Planner-Player.app
./build_app.sh full       # dist/DanceSport-Planner-Player-Full.app  (+ Demucs)
./build_app.sh lite dmg   # plus dist/DanceSport-Planner-Player.dmg
```

The script builds, ad-hoc signs the bundle (`codesign --sign -`; without a
signature Apple silicon refuses to launch it and reports the app as "damaged")
and optionally wraps it in a .dmg. It is built for the architecture of the Mac
that builds it — no `universal2`, because llvmlite/numba/soundfile have no
universal wheels.

For a crisp Dock icon, make an `icon.icns` once:
`sips -s format icns icon.png --out icon.icns`. Without it PyInstaller converts
`icon.png` when Pillow is installed.

☀ *Keep the screen awake* runs `caffeinate -d -i -w <pid>` on macOS — part of
the system, nothing to install, and the helper dies with the app instead of
pinning the screen on after a crash. Windows uses `SetThreadExecutionState`.

Untested, and it is where trouble would show first: the media backend. Qt picks
AVFoundation on macOS, while every timing decision in the player — the 250 ms
load coalescing, the fade ramps, the `EndOfMedia` loop — was measured against
Windows Media Foundation.

## Player build

The flavor for the venue: the same code, packaged without the analysis stack and
locked to player mode.

```powershell
build_player.bat            rem or: build_exe.bat player
./build_app.sh player       # macOS
```

GitHub builds both as well: `.github/workflows/build-player.yml`, started by
hand (*Run workflow*) or by pushing a `v*` tag. It runs the same two scripts,
fetches ffmpeg 9.0.2 for the Windows folder and passes the
`DANCEPLAYLIST_ERROR_DSN` secret. The Windows folder and the macOS `.dmg` are
the run's artifacts. A `v*` tag also publishes them as that tag's GitHub
release (`DanceSport-Player-1.2.0-windows.zip` and `…-macos.dmg` for the tag
`v1.2.0`, so the names carry no v either), with the
tagged commit's message as the release text.

The version number is `VERSION` in `planner/version.py` (`1.0.0`), and a build
without a tag gets it. A `v*` tag overrides it, so name the tag
`vMAJOR.MINOR.PATCH` (`v1.2.0`); the app in the release then says `1.2.0`, the
tag without its v. Keep `VERSION` in step after a release, so desk builds carry
the newest number. Every build bakes it in: the splash and the title bar show
it, every 🐞 error report carries it as its `release`, the `.exe` has it as its file version and the `.app` as
its bundle version. A source run is `dev`.

Output is `dist\DanceSport-Player\`, around **220 MB** against the lite
build's 483 MB — the bulk of the difference is librosa and the numba / llvmlite /
scipy / soundfile stack it pulls in. numpy stays.

**Kept**, because it is what a tournament actually runs on:

- playback, the ±16 % tempo fader (pitch held, Qt's ffmpeg media backend)
- 🔊 Equalize volume — loudness measurement is ffmpeg `ebur128`, not librosa
- Paso Doble highlight detection — the decoder is ffmpeg
  (`shared.audio_probes.decode_pcm_mono`), the envelope and the thresholds are unchanged
- silence detection, 🎛 Cartwall, 📚 Library browser, 🗣 dance announcements

**Dropped**: timbre similarity, the BPM/MFCC analysis, the chroma
indexes, the AI suggestions, and the printed running order (Qt6Pdf goes with it).
Qt Quick/QML and OpenSSL go too — this build is QtWidgets throughout and talks to
nothing over the network.

Two consequences of the locked flavor, both driven by the `build_flavor.txt`
marker PyInstaller ships inside the app:

- the startup mode chooser never appears — `app_mode_of()` returns `"player"`
  whatever a carried-over `gui_settings.json` says, and ⚙ Settings hides the
  mode combo;
- the 🎵 Analysis tab keeps only its ffmpeg entries (loudness, PD highlights,
  silences); the librosa ones are hidden rather than shown disabled;
- ⧉ stops at four playlist decks instead of eight — a venue runs one
  competition at a time, and a layout carried over from a planner install is
  clamped down on open.

**Analyse at home, play at the venue.** Copy a pre-analysed `audio_features.db`
next to `DanceSport-Player.exe` and this build reads the stored PD highlights
and LUFS values verbatim — no analysis run on tournament day. It can also produce
them itself, since all three of those scans are ffmpeg-only.

The build venv needs less as well: `requirements-player.txt` (PySide6, numpy,
mutagen) instead of `requirements.txt`. `build_exe.bat` knows this and does not
demand librosa for this flavor.

## Data files live NEXT TO the .exe

When frozen, the app resolves its data directory to the folder the `.exe` sits in
(`planner.config._app_dir()` switches from `__file__` to `sys.executable` under
PyInstaller). So these all read/write in `dist\DanceSport-Planner-Player\`:

- `audio_features.db` — the analysed-features / caches database
- `gui_settings.json`, `autosave_playlist.json`, `themes.json`
- `planner_config.json`, `openrouter_config.json`
- `scan_cache.json`, `global_scan_cache.json`
- `playlists\` — generated M3U output
- `crash.log`

To reuse an already-analysed library, **copy your existing `audio_features.db`**
(and optionally `gui_settings.json`) next to `DanceSport-Planner-Player.exe`.

The build used to be called `DancePlaylist` (and `DancePlaylist-Full`). A new
build goes to a new folder and leaves `dist\DancePlaylist\` in place, so the
files listed above have to be copied from there once.

Two exceptions, both handled by `planner.config._data_dir()`: a folder that
refuses writes (`C:\Program Files`) and a macOS `.app` — a bundle is a
replaceable artefact and writing inside it breaks its signature. There the same
files go to the per-user folder instead:

| | |
|---|---|
| macOS | `~/Library/Application Support/DanceSport-Planner-Player` |
| Windows | `%LOCALAPPDATA%\DanceSport-Planner-Player` |
| Linux | `$XDG_DATA_HOME/DanceSport-Planner-Player`, else `~/.local/share/DanceSport-Planner-Player` |

That folder used to be called `DancePlaylist`. The first start under the new
name renames an existing `DancePlaylist` folder in place, as long as no
`DanceSport-Planner-Player` folder exists yet. If the rename fails, the app
keeps using the old folder.

Files shipped *with* the app (`ffmpeg.exe`, `build_flavor.txt`) are looked up
under `INSTALL_DIR` and stay next to the executable either way.

## ffmpeg (analysis / loudness / silence)

ffmpeg is **not** in the repository — it's a 300 MB third-party build, so it is
gitignored and has to be fetched once per machine. Grab the *essentials* build
from <https://www.gyan.dev/ffmpeg/builds/> and either

- put it on `PATH`, or
- unpack it into the project root as it comes, e.g. `ffmpeg-9.0.2-essentials_build\`
  (any version; with several, the newest is used), or
- drop a bare `ffmpeg.exe` into the project root.

`find_ffmpeg()` (shared/audio_probes.py) checks `PATH` first, then next to the app /
.exe, then that unpacked folder, then the macOS package-manager prefixes.
Without it the library analysis, the loudness EQ and the silence detection stay
disabled; everything else runs.

For the packaged build `ffmpeg.exe` belongs next to `DanceSport-Planner-Player.exe`;
`build_exe.bat` copies it there after every build (from the project root, or
out of the unpacked essentials folder). PyInstaller deletes `dist\DanceSport-Planner-Player`
each time, so a build driven by `pyinstaller` directly needs that copy by hand.
On macOS
nothing is bundled — `brew install ffmpeg`. Note that `PATH` alone is **not**
enough there: a `.app` started from Finder or the Dock inherits launchd's
`/usr/bin:/bin:/usr/sbin:/sbin` and never sees `/opt/homebrew/bin`, so
`find_ffmpeg()` also probes `/opt/homebrew/bin`, `/usr/local/bin` and
`/opt/local/bin` directly.

## Error reports (GlitchTip)

The opt-in error reports (⚙ Settings → 🐞, `shared/error_reports.py`) need the
project's address, the DSN. It is not in the repository. It comes from
`DANCEPLAYLIST_ERROR_DSN`: in CI from the GitHub secret of that name, locally
from the environment or from a line in the git-ignored `.env` in the project root:

```
DANCEPLAYLIST_ERROR_DSN=https://<key>@app.glitchtip.com/<project>
```

A source run reads it from there. `dancesport.spec` bundles it into the build
as `error_report_dsn.txt`. A build without it offers no reports at all.
`tests.app.test_error_reports.LiveServerTest` sends one real event (tagged
`test: unittest`). It runs only with `DANCEPLAYLIST_LIVE_TESTS=1` and an
address, and skips otherwise. In CI, tick *live_tests* when starting the
tests workflow by hand.

## What's excluded

The optional OpenL3 deep-embedding backend (`tensorflow`, `torch`,
`openl3`) are **not** bundled. Everything else — the
librosa MFCC similarity, BPM detection, and the full GUI — works. To include the
deep-embedding feature, remove those names from `excludes` in `dancesport.spec`
and rebuild (expect a multi-GB result).
