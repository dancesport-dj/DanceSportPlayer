# DanceSport Player

A desktop music player for ballroom and Latin dance events: it runs the music of
a dancesport tournament or a dance party from the music desk.

**📖 [User manual](docs/manual/README.md)**:
setting up, the playlists, running the evening, every setting and shortcut,
with screenshots.

- Up to four playlist decks plus wishlists, with drag and drop to other apps
  (e.g. a DJ program or Explorer).
- Auto-advance or manual mode per list, a fixed play length per title with
  fade-out, and a countdown to the end of the music.
- Loudness levelling (EBU R128 through ffmpeg) and an optional pitch to the
  official TSO tempo of each dance.
- Spoken dance announcements before or over the music, in AI-generated voices.
- Cartwall with pads for jingles and fanfares.
- A USB MIDI or HID controller runs the desk with real buttons and faders,
  with built-in support for the Korg nanoKONTROL2: one preset maps its
  transport row, a fader, a knob and the cartwall pads. Any other controller
  is set up by Learn. See [A hardware controller](docs/manual/04-playing.md#-a-hardware-controller).
- Separate outputs for the music, a 🎧 pre-listen on headphones, the cartwall,
  the pause music and the announcements. Tested with the ESI MAYA44 USB: each
  of its output pairs (Ch12, Ch34) takes a source of its own, it is found again
  when Windows renumbers it after a replug, and a small 🔊 in the status bar
  shows it is plugged in. See [Settings › Outputs](docs/manual/06-settings.md#-outputs).
- Paso Doble highlight stops and pause music.
- Presenter window for a second screen: the current dance and the running order,
  with themes.
- Tournament and party play sets: one press puts every control on the values a
  heat or a party list is run with.
- Themes: the classic light and dark theme with a free accent colour, and 16
  looks to pick in ⚙ Settings: Windows 11, macOS and GNOME, four dark
  mixing-desk looks, and modern ones picked for readability, two of them
  high-contrast. A look of your own starts as a copy of one of them, in an
  editor with a live preview and a contrast check, and travels as a .json
  file. See [Settings › Look](docs/manual/06-settings.md#look).

The user interface is in English, German, Spanish, Dutch and Russian (⚙
Settings › Look › 🌐 Language). The manual is in English and German.
It runs on Windows, macOS and Linux. Windows is the main platform, the one the
player is used on at events; the macOS and Linux builds are newer and less
tested.

![The player](docs/manual/img/main-playing.png)

## Manual

The [user manual](docs/manual/README.md) walks through the player the way it
is used at a tournament or a dance evening, in English and
[German](docs/manual/de/README.md). Every download carries it as
`Manual.pdf` and `Handbuch.pdf`, and **❔ ▸ 📖 Manual** opens it from the app.

- [Getting started](docs/manual/01-getting-started.md): folders, the first scan, a tour of the window
- [Playing the evening](docs/manual/04-playing.md): the player card, play sets, announcements,
  the cartwall, the presenter screen, the phone remote and a hardware controller
- [Settings](docs/manual/06-settings.md) and [Keyboard and mouse](docs/manual/07-shortcuts.md)

## Download

Ready-to-run builds are on the [Releases](https://github.com/dancesport-dj/DanceSportPlayer/releases/latest) page, one
download per platform (two for Linux):

- **DanceSport-Player-…-windows-setup.exe**: installs the app in a folder of
  your choice, with a Start menu entry. Or **…-windows.zip**: unzip the folder
  and start `DanceSport-Player.exe`. ffmpeg is bundled in both.
- **DanceSport-Player-…-macos.dmg**: drag the app onto Applications. Signed ad
  hoc, not notarized. ffmpeg is not bundled there: `brew install ffmpeg`.
- **DanceSport-Player-…-linux-x86_64.tar.gz** (Intel/AMD PCs) or
  **…-linux-arm64.tar.gz** (ARM, e.g. Asahi Linux): unpack the folder and start
  `DanceSport-Player`. Built on Ubuntu 22.04 and 24.04. ffmpeg is not bundled:
  `sudo apt install ffmpeg` (Arch: `sudo pacman -S ffmpeg`).

How to install and open each one, including the first start past SmartScreen
and Gatekeeper: [Windows](docs/install/windows.md), [macOS](docs/install/macos.md),
[Linux](docs/install/linux.md). Every download carries its guide as `README.txt`.

## Running from source

- **Python 3.14 or newer.** The code relies on PEP 649 lazy annotations.
- **ffmpeg** for MP3 decoding, loudness and silence detection. Put it on `PATH`
  (`winget install Gyan.FFmpeg` on Windows, `brew install ffmpeg` on macOS,
  `sudo apt install ffmpeg` on Debian/Ubuntu, `sudo pacman -S ffmpeg` on Arch)
  or, on Windows, place the
  extracted build in an `ffmpeg*` folder next to the app.

```powershell
git clone <repo-url> dancesport-player
cd dancesport-player
py -3.14 -m venv .venv
.venv\Scripts\pip install -r requirements-player.txt
.venv\Scripts\python.exe dancesport_gui.py
```

On macOS and Linux:

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-player.txt
.venv/bin/python dancesport_gui.py
```

On first start the app asks how you want to use it; pick **Player only**.

The [user manual](docs/manual/README.md) describes the player, and
[Playing the evening](docs/manual/04-playing.md) covers running the music on
the floor.

## Building the app

See [BUILD.md](BUILD.md): `build_player.bat` builds the player as a PyInstaller
one-folder app on Windows, `./build_app.sh player` a `.app` bundle on macOS
and `./build_linux.sh player` a one-folder app on Linux (`./build_linux.sh
player tar` packs it as a tar.gz as well).

The [build-player](.github/workflows/build-player.yml) workflow builds all three
and publishes them as a release for every `v*` tag.

## Development

```powershell
.venv\Scripts\python.exe -m pytest                                   # whole suite as CI runs it, ~2 min
.venv\Scripts\python.exe -m tools.dev.parallel_suite                     # whole suite, ~2 min
.venv\Scripts\python.exe -m unittest discover -p "test_*.py"         # whole suite, serial, ~7 min
.venv\Scripts\python.exe -m unittest tests.player.test_cartwall -v   # one module
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\basedpyright --pythonpath .venv\Scripts\python.exe   # app types
```

The full test suite needs `requirements.txt`, and pytest needs
`requirements-dev.txt`. Tests are plain `unittest`, which pytest runs
unchanged on every core (`-n auto` in `pyproject.toml`); CI runs pytest too,
since the root `conftest.py` only applies under it. GUI tests drive Qt through
its offscreen platform, so no window opens.
`tools.dev.parallel_suite` runs the test modules in batches on 8 processes, each
with its own data folder; a batch that ends in a native crash is run once more
and reported as "native crash, retried". The pre-push hook uses it.
The type check covers the app code (not `tests/`) and reports only errors that are not in
`.basedpyright/baseline.json`; after fixing some, shrink the baseline with
`--writebaseline`.
The MainWindow and PlaylistTable mixins are checked against the host members
declared in `gui/window/hosts.pyi`; a mixin that uses a new member of its host needs
it declared there too.
Enable the git hooks once per clone with `git config core.hooksPath .githooks`.

| Path | Contents |
|---|---|
| `dancesport_gui.py` | launcher and main window, PyInstaller entry point |
| `player/` | the evening: `window/`, `audio/`, `widgets/`, `dialogs/`, `presenter/` |
| `gui/` | the planning desk: `window/`, `decks/`, `table/`, `dialogs/` |
| `shared/` | used by both: `audio/`, `controllers/`, `remote/`, `appearance/` |
| `planner/` | the logic, no Qt: `music/`, `generate/`, `playlist/`, `event/`, `playing/`, `i18n/` |
| `tools/` | one-off scripts, `py -m tools.<package>.<name>` |
| `speech/` | the spoken dance announcements |

## Privacy

The player keeps everything on your computer: the music, the playlists, the
settings and its database. It has no account and no telemetry. It goes online
for two things only, and for each only if you allow it:

**Error reports, only if you allow them.** On the first start the app asks
whether it may send error reports; "Don't send" is the default, and
⚙ Settings → ⚙ General changes the answer at any time. When the app
then hits an unexpected error, it sends a report to the developer's
[GlitchTip](https://glitchtip.com) project (app.glitchtip.com): the error and
where in the program it happened, the log lines before it (they can name the
title that was playing), the operating system, the build and the app version.
Not your music, not your playlists, not your computer's name, and your user
folder is cut out of every path. Like any server, GlitchTip sees the IP address
a report comes from.

**A check for new versions, only if you allow it.** The same first-start
question has a box for it, unticked by default; ⚙ Settings → ⚙ General
changes it at any time. When it is on, every start asks GitHub's API
(api.github.com) once for the latest release of this repository. The request
carries no version, no settings and nothing about your music; like any server,
GitHub sees the IP address it comes from. A newer version is announced once,
with a link to its release page. The app never downloads or installs anything
by itself.

**Who is responsible.** marcelkb, the developer of this app. Questions about
your data, or a request to delete the reports from your computer: open an
issue at <https://github.com/dancesport-dj/DanceSportPlayer/issues>.

Run from source with the planning side (`requirements.txt`), two more things
can go online: the optional AI suggestions send your request and the titles it
is about to the AI service whose key you enter (OpenRouter by default), and the
vocal tool downloads its Demucs model from its publisher on first use.

## Built with AI

The app was developed with the help of AI coding tools (Claude by Anthropic).
The spoken dance announcements are AI-generated voices (ElevenLabs), with
their own license: [speech/LICENSE-AUDIO.md](speech/LICENSE-AUDIO.md).

## License

[MIT](LICENSE) © marcelkb

The libraries the app is built on, and the ffmpeg bundled with the Windows
build, keep their own licenses; see
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

The app icon is the *Swing* icon by [Icons8](https://icons8.com). The icons
inside the app are Bootstrap Icons (MIT) and one Twemoji-derived icon
(CC-BY 4.0). None of them is under the MIT license; see
[ICONS-LICENSE.txt](ICONS-LICENSE.txt).

The dance announcement recordings were generated with
[elevenlabs.io](https://elevenlabs.io) and are **not** under the MIT license:
non-commercial use only, see [speech/LICENSE-AUDIO.md](speech/LICENSE-AUDIO.md).
