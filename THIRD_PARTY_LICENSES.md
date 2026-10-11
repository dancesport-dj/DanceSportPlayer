# Third-party licenses

The app's own code is under the [MIT license](LICENSE). It is built on the
open-source components below, each under its own license. The versions are
the ones in `requirements-player.txt` and `requirements.txt`. The full
GPL and LGPL texts, `GPL-2.0.txt`, `GPL-3.0.txt`, `LGPL-2.1.txt` and
`LGPL-3.0.txt`, sit next to this file in every build, and in
[`licenses/`](licenses/) here.

## In the player build

What the packaged player (`DanceSport-Player`, Windows folder or macOS `.app`)
contains.

| Component | Version | License |
|---|---|---|
| [Python](https://www.python.org/) and its standard library | 3.14 | PSF-2.0. It ships OpenSSL (Apache-2.0, only in builds that send error reports), libffi, expat and mimalloc (MIT), mpdecimal, bzip2 and Zstandard (BSD), and SQLite and liblzma (public domain) |
| [Qt](https://www.qt.io/) with [PySide6](https://pypi.org/project/PySide6/) and shiboken6 | 6.11.2 | LGPL-3.0 (also offered under GPL-2.0 / GPL-3.0). Qt Multimedia's FFmpeg libraries are LGPL-2.1-or-later |
| [numpy](https://numpy.org/) | 2.5.3 | BSD-3-Clause, with parts under 0BSD, MIT, Zlib and CC0-1.0. Its OpenBLAS is BSD-3-Clause |
| [mutagen](https://github.com/quodlibet/mutagen) | 1.48.1 | GPL-2.0-or-later |
| [sentry-sdk](https://github.com/getsentry/sentry-python) | 2.71.0 | MIT |
| [urllib3](https://github.com/urllib3/urllib3) | as required by sentry-sdk | MIT |
| [certifi](https://github.com/certifi/python-certifi) | as required by sentry-sdk | MPL-2.0 |
| [segno](https://github.com/heuer/segno) | 1.6.6 | BSD-3-Clause (notice below) |
| [hidapi](https://github.com/trezor/cython-hidapi) | 0.15.0 | Offered under GPL-3.0, a BSD-style license or the original cython-hidapi license; used here under the original one (notice below). It contains the [HIDAPI](https://github.com/libusb/hidapi) C library, offered on the same three terms and used under its original license |
| [PyInstaller](https://pyinstaller.org/) bootloader | 6.22.0 | GPL-2.0-or-later with the bootloader exception, which allows the bundled app to be distributed under its own license |
| Microsoft Visual C++ runtime (Windows) | | Microsoft Visual C++ Redistributable license |

The Windows folder also contains `ffmpeg.exe`: the essentials build
of [FFmpeg](https://ffmpeg.org/) 9.0.2 from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
It is configured with `--enable-gpl --enable-version3` and is therefore under
**GPL-3.0**. It runs as a separate program; the app only calls it. Its source code is at
<https://ffmpeg.org/download.html>, and its license text is `GPL-3.0.txt`.

mutagen is GPL-2.0-or-later, and the player build bundles and imports it, so the
distributed build as a whole falls under the GPL's terms. The app's own MIT
code is compatible with that, and its complete source is in this repository.

On Linux the hidapi wheel brings the system libraries it talks to the
devices through, as shared libraries in `hidapi.libs/`. They are unmodified
builds from the CentOS 7 (x86_64) and EL8 (aarch64) packages that
`auditwheel` copies in, loaded at run time and replaceable by other builds of
the same library.

| Library | x86_64 | aarch64 | License |
|---|---|---|---|
| libusb (libusbx) | 1.0.21 | 1.0.23 | LGPL-2.1-or-later |
| libudev (systemd) | 219 | 239 | LGPL-2.1-or-later |
| libelf, libdw (elfutils) | 0.176 | | GPL-2.0-or-later OR LGPL-3.0-or-later |
| liblzma (xz) | 5.2.2 | | public domain |
| libbz2 (bzip2) | 1.0.6 | | bzip2-1.0.6 (BSD-style) |
| libcap | 2.22 | | BSD-3-Clause OR GPL-2.0 |
| libattr | 2.4.46 | | LGPL-2.1-or-later |
| libblkid, libmount (util-linux) | | 2.32.1 | LGPL-2.1-or-later |
| libuuid (util-linux) | | 2.32.1 | BSD-3-Clause |
| libselinux | | 2.9 | public domain |
| pcre2 | | 10.32 | BSD-3-Clause |

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
[speech/LICENSE-AUDIO.md](speech/LICENSE-AUDIO.md). The app icon is the
*Swing* icon by [Icons8](https://icons8.com), the toolbar and panel icons are
Bootstrap Icons (MIT) and one Twemoji-derived icon (CC-BY 4.0).

## Notices

The BSD and MIT licenses ask for their notice in every binary copy; this file
ships in the `licenses/` folder of each build.

### segno

```
Copyright (c) 2016 - 2025, Lars Heuer
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### hidapi (cython-hidapi)

```
You are free to use cython-hidapi code for any purpose.

Copyright 2011, Gary Bishop
```

### HIDAPI

```
HIDAPI - Multi-Platform library for
communication with HID devices.

Copyright 2009, Alan Ott, Signal 11 Software.
All Rights Reserved.

This software may be used by anyone for any reason so
long as the copyright notice in the source files
remains intact.
```

### sentry-sdk

```
MIT License

Copyright (c) 2018 Functional Software, Inc. dba Sentry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### urllib3

```
MIT License

Copyright (c) 2008-2020 Andrey Petrov and contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### certifi

Its CA bundle is under the MPL-2.0; the source code is at
<https://github.com/certifi/python-certifi>.

```
This package contains a modified version of ca-bundle.crt:

ca-bundle.crt -- Bundle of CA Root Certificates

This is a bundle of X.509 certificates of public Certificate Authorities
(CA). These were automatically extracted from Mozilla's root certificates
file (certdata.txt).  This file can be found in the mozilla source tree:
https://hg.mozilla.org/mozilla-central/file/tip/security/nss/lib/ckfw/builtins/certdata.txt
It contains the certificates in PEM format and therefore
can be directly used with curl / libcurl / php_curl, or with
an Apache+mod_ssl webserver for SSL client authentication.
Just configure this file as the SSLCACertificateFile.#

***** BEGIN LICENSE BLOCK *****
This Source Code Form is subject to the terms of the Mozilla Public License,
v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain
one at http://mozilla.org/MPL/2.0/.

***** END LICENSE BLOCK *****
@(#) $RCSfile: certdata.txt,v $ $Revision: 1.80 $ $Date: 2011/11/03 15:11:58 $
```

### Python

The PSF license is in `PYTHON-LICENSE.txt` next to this file, with the
notices of the software Python carries (OpenSSL's Apache-2.0 text, expat,
libffi, mpdecimal, mimalloc, bzip2, Zstandard and the rest of CPython's own
list).
