"""📱 Phone remote: the desk's transport on any phone on the same network.

No app to install. The app serves one web page itself; the phone's browser
opens it, asks for the PIN once, and from then on shows what is playing and
what comes next, and sends ⏯ ⏭ ⏮, the fade-outs and the 🎛 cartwall pads back.

Kept small on purpose, because it is a door into the desk:

- Off unless switched on in ⚙ Settings.
- Only answers addresses of the local network (private, link-local, loopback):
  a router that forwards the port by accident still exposes nothing.
- Everything but the page itself needs the PIN in a header. A page of another
  website cannot send that header without a CORS preflight, and nothing here
  answers one, so no website the operator browses can call the desk either.
- Guessing the PIN locks that address out, longer each time.
- Commands are a fixed list; a request body is at most 1 KB.

The server runs on plain daemon threads (http.server), not QThreads — see
player/waveform.py for why. Commands come back through `on_command` on the
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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shared.remote_page import page_html

log = logging.getLogger("dancesport.remote")

DEFAULT_PORT = 8765
PIN_HEADER = "X-Remote-Pin"
COMMANDS = frozenset({"toggle", "next", "prev", "fade", "hold", "pad", "stop_pads",
                      "announce", "seek"})
MAX_FAILS = 5
_LOCK_SECS = 60
_MAX_BODY = 1024


def _bar_point(value) -> bool:
    """A point on the phone's progress bar: a number from 0 to 1 (NaN fails)."""
    return type(value) in (int, float) and 0 <= value <= 1


def new_pin() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def lan_client(addr: str) -> bool:
    """Whether a request from `addr` comes from the local network."""
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_private or ip.is_loopback or ip.is_link_local


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


class _Handler(BaseHTTPRequestHandler):
    server_version = "DancePlaylistRemote"
    sys_version = ""

    def log_message(self, fmt, *args):     # the console is not the log
        log.debug("📱 %s %s", self.client_address[0], fmt % args)

    @property
    def app(self) -> "RemoteServer":
        return self.server.remote

    def _send(self, status: int, body: bytes = b"", ctype: str = "application/json"):
        self.send_response(status)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _gate(self, need_pin: bool) -> bool:
        """True when the request may go on; otherwise the refusal is sent."""
        ip = self.client_address[0]
        if not lan_client(ip):
            self.app.note("refused", ip)
            self._send(403)
            return False
        if not need_pin:
            return True
        verdict = self.app.check_pin(ip, self.headers.get(PIN_HEADER, ""))
        if verdict != 200:
            self._send(verdict)
            return False
        return True

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if self._gate(need_pin=False):
                self.app.note("page", self.client_address[0])
                self._send(200, self.app.page, "text/html; charset=utf-8")
        elif self.path == "/api/state":
            if self._gate(need_pin=True):
                self.app.logged_in(self.client_address[0])
                self._send(200, json.dumps(self.app.state(), ensure_ascii=False)
                           .encode("utf-8"))
        else:
            self._send(404)

    def do_POST(self):
        if self.path != "/api/cmd":
            self._send(404)
            return
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = -1
        if size < 0 or size > _MAX_BODY:
            # Read a modest one away first: closing on unread bytes resets the
            # connection, and the phone would see "no connection" instead.
            if 0 < size <= 64 * _MAX_BODY:
                self.rfile.read(size)
            self._send(413)
            self.close_connection = True
            return
        raw = self.rfile.read(size)
        if not self._gate(need_pin=True):
            return
        try:
            msg = json.loads(raw.decode("utf-8"))
            cmd = msg["cmd"]
            arg = msg.get("pad") if cmd == "pad" else msg.get("to") if cmd == "seek" else None
        except (ValueError, KeyError, TypeError, AttributeError):
            self._send(400)
            return
        if (cmd not in COMMANDS or (cmd == "pad" and (type(arg) is not int or arg < 0))
                or (cmd == "seek" and not _bar_point(arg))):
            self._send(400)
            return
        if cmd == "seek":
            arg = float(arg)
        self.app.note("cmd", self.client_address[0], cmd if arg is None else f"{cmd} {arg}")
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

    def __init__(self, pin: str, on_command, host: str = "0.0.0.0",
                 port: int = DEFAULT_PORT, labels: dict | None = None,
                 on_event=None):
        self._pin = str(pin)
        self.on_command = on_command
        self._on_event = on_event
        self._seen: set[str] = set()     # addresses logged in with this PIN
        self._host = host
        self._want_port = int(port)
        self.page = page_html(labels or {}).encode("utf-8")
        self._state: dict = {}
        self._lock = threading.Lock()
        self._fails: dict[str, tuple[int, float, int]] = {}
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
        httpd = ThreadingHTTPServer((self._host, self._want_port), _Handler)
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

    def check_pin(self, ip: str, given: str) -> int:
        """200 for the right PIN; 401 for a wrong one; 429 while `ip` is locked
        out — after MAX_FAILS wrong ones, for a minute, doubling every time."""
        now = time.monotonic()
        with self._lock:
            fails, until, rounds = self._fails.get(ip, (0, 0.0, 0))
            if now < until:
                return 429
            if hmac.compare_digest(given.encode("utf-8"), self._pin.encode("utf-8")):
                self._fails.pop(ip, None)
                return 200
            fails += 1
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
        if locked:
            self.note("locked", ip, str(int(until - now)))
        elif given:
            self.note("wrong_pin", ip)
        return 401
