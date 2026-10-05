# Third-party licenses

The app's own code is under the [MIT license](LICENSE). It is built on the
open-source components below, each under its own license. The versions are
the ones in `requirements-player.txt` and `requirements.txt`; the license
texts ship inside each package.

## In the player build

What the packaged player (`DanceSport-Player`, Windows folder or macOS `.app`)
contains.

| Component | Version | License |
|---|---|---|
| [Python](https://www.python.org/) and its standard library | 3.14 | PSF-2.0. It ships OpenSSL (Apache-2.0), SQLite (public domain), libffi (MIT) and expat (MIT) |
| [Qt](https://www.qt.io/) with [PySide6](https://pypi.org/project/PySide6/) and shiboken6 | 6.11.2 | LGPL-3.0 (also offered under GPL-2.0 / GPL-3.0). Qt Multimedia's FFmpeg libraries are LGPL-2.1-or-later |
| [numpy](https://numpy.org/) | 2.5.3 | BSD-3-Clause, with parts under 0BSD, MIT, Zlib and CC0-1.0. Its OpenBLAS is BSD-3-Clause |
| [mutagen](https://github.com/quodlibet/mutagen) | 1.48.1 | GPL-2.0-or-later |
| [sentry-sdk](https://github.com/getsentry/sentry-python) | 2.71.0 | MIT |
| [urllib3](https://github.com/urllib3/urllib3) | as required by sentry-sdk | MIT |
| [certifi](https://github.com/certifi/python-certifi) | as required by sentry-sdk | MPL-2.0 |
| [PyInstaller](https://pyinstaller.org/) bootloader | 6.22.0 | GPL-2.0-or-later with the bootloader exception, which allows the bundled app to be distributed under its own license |
| Microsoft Visual C++ runtime (Windows) | | Microsoft Visual C++ Redistributable license |

The Windows folder also contains `ffmpeg.exe`: the essentials build
of [FFmpeg](https://ffmpeg.org/) 9.0.2 from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
It is configured with `--enable-gpl --enable-version3` and is therefore under
**GPL-3.0**. It runs as a separate program; the app only calls it. Its source code is at
<https://ffmpeg.org/download.html>, and its license text is in the
`LICENSE` file of the downloaded build.

mutagen is GPL-2.0-or-later, and the player build bundles and imports it, so the
distributed build as a whole falls under the GPL's terms. The app's own MIT
code is compatible with that, and its complete source is in this repository.

## Only in the planner

`requirements.txt` adds the analysis stack for the planning half of the app
and the full test suite. None of it is in the player build.

| Component | Version | License |
|---|---|---|
| [librosa](https://librosa.org/) | 1.0.0 | ISC |
| [soxr](https://github.com/dofuuz/python-soxr) | as required by librosa | LGPL-2.1-or-later |
| [scipy](https://scipy.org/) | as required by librosa | BSD-3-Clause |
| [scikit-learn](https://scikit-learn.org/) | as required by librosa | BSD-3-Clause |
| [numba](https://numba.pydata.org/) | as required by librosa | BSD-2-Clause |
| [llvmlite](https://github.com/numba/llvmlite) | as required by numba | BSD-2-Clause and Apache-2.0 with LLVM exception |
| [soundfile](https://github.com/bastibe/python-soundfile) | as required by librosa | BSD-3-Clause |
| [audioread](https://github.com/beetbox/audioread) | as required by librosa | MIT |

## Icons and recordings

The icons and the dance announcement recordings have their own terms; see
[ICONS-LICENSE.txt](ICONS-LICENSE.txt) and
[speech/LICENSE-AUDIO.md](speech/LICENSE-AUDIO.md).
