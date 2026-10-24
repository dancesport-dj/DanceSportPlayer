"""🌐 A Cloudflare quick tunnel: the guest page on a public https address.

Guests on mobile data cannot reach this PC: it sits behind the venue's
router. `cloudflared tunnel --url` dials out to Cloudflare and gets a random
https://….trycloudflare.com address that leads back to the guest server on
127.0.0.1 — no account, no router setup, a new address each run. The guest
server sees every request come in from loopback, with the guest's own
address in `CF-Connecting-IP` (see guest_server).

cloudflared is not shipped. It is looked for next to the app, then in the
app's data folder (where a download goes), then on the PATH, then in the
places its installers use. Downloading it is the user's choice, asked in the
📨 window.

No Qt here: the callbacks run on the tunnel's reader thread.
"""
import hashlib
import io
import logging
import os
import platform
import re
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

from planner import config
from planner.tls import tls_context

log = logging.getLogger("dancesport.guests")

# A fixed release, and the SHA-256 of each of its files as GitHub lists them:
# "latest" would run whatever the release page holds that day, unchecked. A
# new version needs its hashes here too.
CLOUDFLARED_VERSION = "2026.10.1"
DOWNLOAD_BASE = ("https://github.com/cloudflare/cloudflared/releases/download/"
                 f"{CLOUDFLARED_VERSION}/")
_SHA256 = {
    "cloudflared-windows-amd64.exe": "4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6",
    "cloudflared-darwin-arm64.tgz": "647615df99d49cd179ea5e13ef760b9bbfb33630f6ae62f87e33dfadda60adcc",
    "cloudflared-darwin-amd64.tgz": "3b0dbaf378337e9d7fb6cd235a76d1d6a7dee434c2d8edf9281164fb6a3837ab",
    "cloudflared-linux-amd64": "3bfc539f45d2620c71debb7a86be0efa737ed5ccbad9eb85c787116900e5c586",
    "cloudflared-linux-arm64": "2c65dfabf616c40efc7545d107d7a57ad5e21377e2964b7e88af19a238074a46",
}
_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_CHUNK = 64 * 1024
_STOP_SECS = 3
# trycloudflare.com's own nameservers, and how long to wait for them to know
# a new tunnel's name before handing its address out anyway.
_NAMESERVERS = ("kevin.ns.cloudflare.com", "marjory.ns.cloudflare.com")
_DNS_ASK_SECS = 2
_DNS_POLL_SECS = 1.0
_DNS_WAIT_SECS = 30
_PROGRAM_FILES = (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                  os.environ.get("ProgramFiles", r"C:\Program Files"))
_LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
# Where an installed cloudflared lives when the PATH misses it: an app started
# from Finder or the Dock gets launchd's PATH without Homebrew, and one started
# before the installer ran still has the old PATH. A place that cannot exist
# on this system simply never matches.
_INSTALL_CANDIDATES = (
    *(Path(base) / "cloudflared" / "cloudflared.exe" for base in _PROGRAM_FILES),  # the .msi
    _LOCAL_APPDATA / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe",  # winget
    Path.home() / "scoop" / "shims" / "cloudflared.exe",  # Scoop
    Path(r"C:\ProgramData\chocolatey\bin\cloudflared.exe"),  # Chocolatey
    Path("/opt/homebrew/bin/cloudflared"),  # Homebrew, Apple silicon
    Path("/usr/local/bin/cloudflared"),  # Homebrew on Intel, Linux packages
    Path("/opt/local/bin/cloudflared"),  # MacPorts
    Path("/home/linuxbrew/.linuxbrew/bin/cloudflared"),  # Homebrew on Linux
    Path.home() / ".linuxbrew" / "bin" / "cloudflared",  # …its per-user install
)


def binary_name(plat: str = sys.platform) -> str:
    return "cloudflared.exe" if plat == "win32" else "cloudflared"


def asset_name(plat: str = sys.platform, machine: str | None = None) -> str | None:
    """The release file for this system; None where Cloudflare builds none.
    Windows on ARM runs the amd64 build emulated: there is no arm64 .exe."""
    arch = (machine if machine is not None else platform.machine()).lower()
    arm = arch in ("arm64", "aarch64")
    if plat == "win32":
        return "cloudflared-windows-amd64.exe"
    if plat == "darwin":
        return "cloudflared-darwin-arm64.tgz" if arm else "cloudflared-darwin-amd64.tgz"
    if plat.startswith("linux"):
        if arm:
            return "cloudflared-linux-arm64"
        return "cloudflared-linux-amd64" if arch in ("x86_64", "amd64") else None
    return None


def find_cloudflared(dirs: tuple[Path, ...] | None = None) -> Path | None:
    """cloudflared next to the app, in its data folder, on the PATH, or where
    an installer put it (Program Files, winget, Scoop, Homebrew…)."""
    name = binary_name()
    for folder in dirs if dirs is not None else (config.INSTALL_DIR, config.APP_DIR):
        candidate = Path(folder) / name
        if candidate.is_file():
            return candidate
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    return next((c for c in _INSTALL_CANDIDATES if c.is_file()), None)


def _open(url: str, timeout: float):
    return urllib.request.urlopen(url, timeout=timeout, context=tls_context())


def download(dest_dir: Path, progress=None, opener=_open) -> Path:
    """Fetch cloudflared from Cloudflare's GitHub releases into `dest_dir`.

    `progress(done, total)` hears each chunk (total 0 when unknown). Written
    to a .part file first, so a broken download never looks like a binary,
    and thrown away unless its SHA-256 is the release's.
    Raises OSError (urllib's errors are OSErrors) or ValueError."""
    asset = asset_name()
    if asset is None:
        raise ValueError(f"no cloudflared build for {sys.platform} {platform.machine()}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest_dir / (binary_name() + ".part")
    digest = hashlib.sha256()
    with opener(DOWNLOAD_BASE + asset, timeout=60) as resp, open(part, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while chunk := resp.read(_CHUNK):
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    if digest.hexdigest() != _SHA256.get(asset):
        part.unlink()
        raise ValueError(f"{asset} is not the {CLOUDFLARED_VERSION} release: its SHA-256 differs")
    if asset.endswith(".tgz"):
        _unpack(part)
    target = dest_dir / binary_name()
    if sys.platform != "win32":
        os.chmod(part, 0o755)
    os.replace(part, target)
    log.info("🌐 cloudflared downloaded\n"
             "file: %s", target)
    return target


def _unpack(part: Path) -> None:
    """The macOS release is a .tgz holding the one binary: keep only that."""
    with tarfile.open(part, "r:gz") as tgz:
        member = next((m for m in tgz.getmembers()
                       if m.isfile() and Path(m.name).name == "cloudflared"), None)
        stream = tgz.extractfile(member) if member is not None else None
        if stream is None:
            raise ValueError("no cloudflared in the download")
        data = stream.read()
    part.write_bytes(data)


def tunnel_command(binary: Path, port: int) -> list[str]:
    return [str(binary), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"]


def dns_query(host: str, qid: int) -> bytes:
    """A DNS question for the A record of `host`, no recursion asked for."""
    name = b"".join(bytes([len(label)]) + label.encode("ascii") for label in host.split("."))
    return struct.pack(">6H", qid, 0, 1, 0, 0, 0) + name + b"\0" + struct.pack(">2H", 1, 1)


def dns_answered(reply: bytes, qid: int) -> bool:
    """Whether `reply` answers question `qid` with a record: no error, not empty."""
    if len(reply) < 12:
        return False
    rid, flags, _, answers = struct.unpack(">4H", reply[:8])
    return rid == qid and bool(flags & 0x8000) and flags & 0xF == 0 and answers > 0


def name_published(host: str) -> bool | None:
    """Whether trycloudflare.com's own nameservers know `host` yet; None when
    neither could be asked. Asked there, not through this PC's resolver: a
    resolver told "no such name" keeps that for a minute (the zone's negative
    TTL), and the venue router's would pass it on to every guest on its Wi-Fi."""
    qid = secrets.randbelow(1 << 16)
    for server in _NAMESERVERS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(_DNS_ASK_SECS)
                sock.sendto(dns_query(host, qid), (server, 53))
                reply = sock.recv(512)
        except OSError:
            continue
        return dns_answered(reply, qid)
    return None


class Tunnel:
    """One cloudflared quick tunnel to `port` on this PC.

    `on_url(url)` hears the public address once its name resolves,
    `on_line(text)` each line cloudflared prints, `on_exit(code)` its end —
    also after `stop()`. All on the tunnel's own threads. `resolves(host)` is
    `name_published` but in tests."""

    def __init__(self, binary: Path, port: int, on_url, on_line=None, on_exit=None,
                 resolves=name_published):
        self.argv = tunnel_command(binary, port)
        self.url = ""
        self._on_url = on_url
        self._on_line = on_line
        self._on_exit = on_exit
        self._resolves = resolves
        self._proc: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        """Start cloudflared. Raises OSError when it cannot be run."""
        self._proc = subprocess.Popen(
            self.argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self._read, args=(self._proc,), daemon=True,
                         name="guest-tunnel").start()

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(_STOP_SECS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def _read(self, proc: subprocess.Popen) -> None:
        if proc.stdout is None:
            return
        for line in io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace"):
            text = line.rstrip()
            self._call(self._on_line, text)
            found = _URL_RE.search(text)
            if found and not self.url:
                self.url = found.group(0)
                threading.Thread(target=self._announce, args=(proc, self.url),
                                 daemon=True, name="guest-tunnel-dns").start()
        code = proc.wait()
        log.info("🌐 Guest tunnel ended\n"
                 "exit code: %s", code)
        self._call(self._on_exit, code)

    def _announce(self, proc: subprocess.Popen, url: str) -> None:
        """Hand the address out once its name resolves. cloudflared prints it
        before Cloudflare's DNS has the name: a phone asking then hears "name
        not resolved", and its resolver keeps that answer for a minute."""
        host = url.split("//", 1)[1]
        started = time.monotonic()
        while (published := self._resolves(host)) is False:
            if time.monotonic() - started >= _DNS_WAIT_SECS:
                break
            time.sleep(_DNS_POLL_SECS)
        if self._proc is not proc or proc.poll() is not None:
            return   # stopped or ended while waiting: on_exit tells
        log.info("🌐 Guest tunnel up\n"
                 "url: %s\n"
                 "name published: %s after %.1f s",
                 url, {True: "yes", False: "not yet", None: "unknown"}[published],
                 time.monotonic() - started)
        self._call(self._on_url, url)

    @staticmethod
    def _call(listener, arg) -> None:
        if listener is None:
            return
        try:
            listener(arg)
        except Exception as exc:
            log.debug("🌐 Tunnel listener failed: %s", exc)
