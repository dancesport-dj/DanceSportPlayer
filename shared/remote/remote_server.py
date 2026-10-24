"""📱 Phone remote: the desk's transport on any phone on the same network.

No app to install. The app serves one web page itself; the phone's browser
opens it, asks for the PIN once, and from then on shows what is playing and
what comes next, and sends ⏯ ⏭ ⏮, the fade-outs and the 🎛 cartwall pads back.

Kept small on purpose, because it is a door into the desk:

- Off unless switched on in ⚙ Settings.
- Only answers addresses of the local network (private, link-local, loopback):
  a router that forwards the port by accident still exposes nothing. From
  outside, the only way in is a Cloudflare quick tunnel the desk starts
  (shared/remote/tunnel.py): it hands requests in from 127.0.0.1, with the
  phone's own address in `CF-Connecting-IP` — believed only from loopback
  and only while the tunnel is up, so the lockouts below still count per
  phone. The desk then wants a longer PIN (TUNNEL_PIN_DIGITS).
- Only answers to its own names: an address of the local network,
  localhost, or the tunnel's. A website whose name was re-pointed at this PC
  (DNS rebinding) sends its own name as the Host and is turned away.
- Everything but the page itself needs the PIN in a header. A page of another
  website cannot send that header without a CORS preflight, and nothing here
  answers one, so no website the operator browses can call the desk either.
- Guessing the PIN locks that address out, longer each time. Wrong PINs from
  the whole network share one budget too, so changing addresses does not
  buy more guesses: once it is spent, only phones already in get through.
- A connection that sends nothing is dropped after ten minutes.
- Commands are a fixed list; a request body is at most 1 KB.

The server runs on plain daemon threads (http.server), not QThreads — see
player/widgets/waveform.py for why. Commands come back through `on_command` on the
server's thread; the caller hands them to the GUI thread (a Qt signal does).
The state the page shows is pushed in by the app with `publish()`, so a request
never reaches into Qt.
"""
import hmac
import ipaddress
import json
import logging
import secrets
import socket
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import urlsplit

from shared.remote.remote_page import page_html

log = logging.getLogger("dancesport.remote")

DEFAULT_PORT = 8765
PIN_HEADER = "X-Remote-Pin"
COMMANDS = frozenset({"toggle", "next", "prev", "fade", "hold", "pad", "stop_pads",
                      "announce", "seek", "xfade", "advance", "jump"})
MAX_FAILS = 5
_LOCK_SECS = 60
GLOBAL_MAX_FAILS = 30          # wrong PINs from all addresses together…
_GLOBAL_WINDOW_SECS = 600      # …within this long pause new logins
_IDLE_SECS = 600
_MAX_BODY = 1024
_BODY_SECS = 5                 # the whole body, not each read of it
PIN_DIGITS = 4
TUNNEL_PIN_DIGITS = 8   # on a public address: 30 guesses in ten minutes find no 8-digit PIN
# Carrier-grade NAT: venue and hotel Wi-Fi (and Tailscale) use it; ipaddress
# calls it neither private nor global.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _bar_point(value) -> bool:
    """A point on the phone's progress bar: a number from 0 to 1 (NaN fails)."""
    return type(value) in (int, float) and 0 <= value <= 1


def _next_pick(value) -> bool:
    """A title tapped in the "next" list: its place there and its name."""
    to, title = value
    return type(to) is int and to >= 0 and type(title) is str and bool(title)


def new_pin(digits: int = PIN_DIGITS) -> str:
    return str(secrets.randbelow(10 ** digits)).zfill(digits)


def lan_client(addr: str) -> bool:
    """Whether a request from `addr` comes from the local network."""
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or (ip.version == 4 and ip in _CGNAT))


def desk_host(host: str | None, tunnel_host: str) -> bool:
    """Whether a request's Host names this desk: an address of the local
    network, localhost, or `tunnel_host` (the tunnel's name, "" when none)."""
    name = (host or "").strip().lower()
    if name.startswith("["):                    # [IPv6]:port
        name = name[1:].partition("]")[0]
    elif name.count(":") == 1:                  # name:port
        name = name.partition(":")[0]
    if name == "localhost" or (tunnel_host and name == tunnel_host.lower()):
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return lan_client(name)


def forwarded_client(peer: str, headers, tunnel_host: str) -> str:
    """Who is asking: the peer's address, or behind the tunnel (loopback, and
    only while one is up) the phone's own from `CF-Connecting-IP`."""
    forwarded = (headers.get("CF-Connecting-IP") or "").strip()
    if (tunnel_host and forwarded
            and ipaddress.ip_address(peer.split("%", 1)[0]).is_loopback):
        return forwarded[:64]
    return peer


def read_body(handler: BaseHTTPRequestHandler, size: int, secs: float) -> bytes | None:
    """The request's `size` body bytes, all within `secs` seconds together.
    None, and the connection closed, when they don't all come in time: the
    handler's own timeout is per read, so one byte a minute would keep it."""
    deadline = time.monotonic() + secs
    sock = handler.connection
    chunks = []
    try:
        while size > 0:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError
            sock.settimeout(left)
            chunk = handler.rfile.read1(size)
            if not chunk:
                raise ConnectionError
            chunks.append(chunk)
            size -= len(chunk)
    except OSError:
        handler.close_connection = True
        return None
    finally:
        sock.settimeout(handler.timeout)
    return b"".join(chunks)


def lan_addresses() -> list[str]:
    """This PC's IPv4 addresses on the local network — what the phone types in.
    The route-to-the-internet one first: that is the Wi-Fi the phone is on."""
    found = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))     # TEST-NET: picks a route, sends nothing
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
            found.append(addr)
    except OSError:
        pass
    out = []
    for a in found:
        if a not in out and lan_client(a) and not a.startswith("127."):
            out.append(a)
    return out


class _Server(ThreadingHTTPServer):
    """The HTTP server, holding the RemoteServer its handlers answer to."""
    remote: "RemoteServer"
    # On Windows SO_REUSEADDR lets a second socket share a port that is
    # still listening, splitting the phones between the two, instead of
    # the "port taken" error. Elsewhere it only skips TIME_WAIT.
    allow_reuse_address = sys.platform != "win32"


class _Handler(BaseHTTPRequestHandler):
    server_version = "DanceSportPlayerRemote"
    sys_version = ""
    timeout = _IDLE_SECS        # a client that never speaks frees its thread

    def log_message(self, format, *args):  # the console is not the log
        log.debug("📱 %s %s", self.client_address[0], format % args)

    @property
    def app(self) -> "RemoteServer":
        return cast(_Server, self.server).remote   # start() serves with a _Server

    def _send(self, status: int, body: bytes = b"", ctype: str = "application/json"):
        self.send_response(status)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")   # no other page may frame it
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; "
                             "frame-ancestors 'none'")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _phone(self) -> str:
        """Who is asking: the address, or behind the tunnel the phone's own."""
        return forwarded_client(self.client_address[0], self.headers,
                                self.app.tunnel_host)

    def _gate(self, need_pin: bool) -> bool:
        """True when the request may go on; otherwise the refusal is sent."""
        if (not lan_client(self.client_address[0])
                or not desk_host(self.headers.get("Host"), self.app.tunnel_host)):
            self.app.note("refused", self.client_address[0])
            self._send(403)
            return False
        if not need_pin:
            return True
        phone = self._phone()
        verdict = self.app.check_pin(phone, self.headers.get(PIN_HEADER, ""),
                                     via_tunnel=phone != self.client_address[0])
        if verdict != 200:
            self._send(verdict)
            return False
        return True

    def do_GET(self):
        path = self.path.split("?", 1)[0]   # a scanner may append "?utm_..."
        if path in ("/", "/index.html"):
            if self._gate(need_pin=False):
                self.app.note("page", self._phone())
                self._send(200, self.app.page, "text/html; charset=utf-8")
        elif path == "/api/state":
            if self._gate(need_pin=True):
                self.app.logged_in(self._phone())
                self._send(200, json.dumps(self.app.state(), ensure_ascii=False)
                           .encode("utf-8"))
        else:
            self._send(404)

    def do_POST(self):
        known = self.path.split("?", 1)[0] == "/api/cmd"
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = -1
        if not known or size < 0 or size > _MAX_BODY:
            # Read a modest one away first: closing on unread bytes resets the
            # connection, and the phone would see "no connection" instead.
            if 0 < size <= 64 * _MAX_BODY:
                read_body(self, size, _BODY_SECS)
            self._send(413 if known else 404)
            self.close_connection = True
            return
        # The gate before the body: a wrong PIN costs no wait for its bytes.
        # They are still read away after the answer, for the reason above.
        if not self._gate(need_pin=True):
            read_body(self, size, _BODY_SECS)
            self.close_connection = True
            return
        raw = read_body(self, size, _BODY_SECS)
        if raw is None:
            return
        try:
            msg = json.loads(raw.decode("utf-8"))
            cmd = msg["cmd"]
            arg = (msg.get("pad") if cmd == "pad" else msg.get("to") if cmd == "seek"
                   else (msg.get("to"), msg.get("title")) if cmd == "jump" else None)
        except (ValueError, KeyError, TypeError, AttributeError):
            self._send(400)
            return
        if (not isinstance(cmd, str) or cmd not in COMMANDS
                or (cmd == "pad" and (type(arg) is not int or arg < 0))
                or (cmd == "seek" and not _bar_point(arg))
                or (cmd == "jump" and not _next_pick(arg))):
            self._send(400)
            return
        if cmd == "seek" and isinstance(arg, (int, float)):   # _bar_point checked it
            arg = float(arg)
        self.app.note("cmd", self._phone(), cmd if arg is None else f"{cmd} {arg}")
        self.app.on_command(cmd, arg)
        self._send(204)

    def do_OPTIONS(self):
        # A CORS preflight. Never granted: only the page this server serves
        # itself may call it.
        self._send(405)


class RemoteServer:
    """The HTTP server and what it shares with the app: the PIN, the state.

    `on_event(kind, ip, detail)` hears what happens, on the server's thread,
    for the desk's log: start, stop, page (opened), login (the first right
    PIN from an address), wrong_pin, locked, refused (not the local network)
    and cmd. The state polls a phone sends every second are not events."""

    def __init__(self, pin: str, on_command, host: str = "0.0.0.0",  # nosec B104: phones on the LAN, PIN-gated
                 port: int = DEFAULT_PORT, labels: dict | None = None,
                 on_event=None):
        self._pin = str(pin)
        self.on_command = on_command
        self._on_event = on_event
        self._seen: set[str] = set()     # addresses logged in with this PIN
        self._host = host
        self._want_port = int(port)
        self.tunnel_host = ""            # the tunnel's name while it is up
        self.page = page_html(labels or {}).encode("utf-8")
        self._state: dict = {}
        self._lock = threading.Lock()
        self._fails: dict[str, tuple[int, float, int]] = {}
        # Every wrong PIN, any address; the tunnel's apart, so the internet
        # cannot pause logins on the venue's own network.
        self._recent_fails: dict[bool, deque[float]] = {False: deque(), True: deque()}
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self._httpd.server_address[1] if self._httpd else self._want_port

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self) -> None:
        """Bind and serve. Raises OSError when the port is taken."""
        httpd = _Server((self._host, self._want_port), _Handler)
        httpd.daemon_threads = True
        httpd.remote = self
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, args=(0.1,), daemon=True,
                                        name="phone-remote")
        self._thread.start()
        log.info("📱 Phone remote on\n"
                 "port: %d", self.port)
        self.note("start", "", str(self.port))

    def stop(self) -> None:
        httpd, self._httpd = self._httpd, None
        if httpd is None:
            return
        httpd.shutdown()
        httpd.server_close()
        with self._lock:
            self._seen.clear()
        log.info("📱 Phone remote off")
        self.note("stop", "")

    def note(self, kind: str, ip: str, detail: str = "") -> None:
        """Hand one event to `on_event`; a failing listener never stops a request."""
        if self._on_event is None:
            return
        try:
            self._on_event(kind, ip, detail)
        except Exception as exc:
            log.debug("📱 Event listener failed: %s", exc)

    def logged_in(self, ip: str) -> None:
        """A right PIN from `ip`: an event the first time only."""
        with self._lock:
            first = ip not in self._seen
            self._seen.add(ip)
        if first:
            self.note("login", ip)

    def set_tunnel(self, url: str) -> None:
        """The tunnel's public address once it is up; "" when it is gone."""
        self.tunnel_host = urlsplit(url).hostname or ""

    def set_pin(self, pin: str) -> None:
        """A new PIN at once; phones that knew the old one must log in again."""
        with self._lock:
            self._pin = str(pin)
            self._seen.clear()

    def publish(self, state: dict) -> None:
        with self._lock:
            self._state = state

    def state(self) -> dict:
        with self._lock:
            return self._state

    def check_pin(self, ip: str, given: str, via_tunnel: bool = False) -> int:
        """200 for the right PIN; 401 for a wrong one; 429 while `ip` is locked
        out — after MAX_FAILS wrong ones, for a minute, doubling every time —
        and, for an address not logged in yet, while the network has sent
        GLOBAL_MAX_FAILS wrong PINs within _GLOBAL_WINDOW_SECS. The tunnel and
        the local network each count their own. No PIN at all is a 401 that
        counts as no guess: the page never asks without one."""
        now = time.monotonic()
        paused_all = False
        with self._lock:
            fails, until, rounds = self._fails.get(ip, (0, 0.0, 0))
            if now < until:
                return 429
            recent = self._recent_fails[via_tunnel]
            while recent and recent[0] <= now - _GLOBAL_WINDOW_SECS:
                recent.popleft()
            if len(recent) >= GLOBAL_MAX_FAILS and ip not in self._seen:
                return 429
            if not given:
                return 401
            if hmac.compare_digest(given.encode("utf-8"), self._pin.encode("utf-8")):
                self._fails.pop(ip, None)
                return 200
            fails += 1
            recent.append(now)
            paused_all = len(recent) == GLOBAL_MAX_FAILS
            if paused_all:
                log.warning("📱 Phone remote: %d wrong PINs from the network\n"
                            "new logins paused for: %ds", GLOBAL_MAX_FAILS,
                            _GLOBAL_WINDOW_SECS)
            locked = fails >= MAX_FAILS
            if locked:
                rounds += 1
                until = now + _LOCK_SECS * 2 ** (rounds - 1)
                fails = 0
                log.warning("📱 Phone remote: wrong PIN %d times\n"
                            "from: %s\n"
                            "locked for: %ds", MAX_FAILS, ip, int(until - now))
            self._fails[ip] = (fails, until, rounds)
        # Outside the lock: the listener may take its time.
        if paused_all:
            self.note("locked_all", "", str(_GLOBAL_WINDOW_SECS))
        if locked:
            self.note("locked", ip, str(int(until - now)))
        else:
            self.note("wrong_pin", ip)
        return 401
