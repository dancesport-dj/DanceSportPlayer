"""📨 Guest requests: guests search the library on their phones and ask for a title.

A second, smaller door than the phone remote's, and a different kind: no PIN,
nothing that moves the desk. A guest can read the title list and what is
playing, and leave a request — a library title or a few words of free text —
that lands in the desk's 📨 inbox for the DJ to take or drop. Nothing a guest
sends is ever played on its own.

How a guest gets here:

- On the same Wi-Fi (or the DJ's phone hotspot): straight to this server.
- On mobile data: through a Cloudflare quick tunnel (shared/remote/tunnel.py),
  which runs on this PC and hands every request in from 127.0.0.1.

Kept small on purpose:

- Only answers addresses of the local network, as the remote does; the
  tunnel arrives from loopback. Behind the tunnel the guest's own address is
  the `CF-Connecting-IP` header — believed only from loopback, so a phone on
  the Wi-Fi cannot pick a new one per request.
- Every API call carries the event code from the QR code. A new code (each
  start, or "New code") turns every old link and photo of the QR away.
- Each guest has a request budget, and all guests together another one;
  wrong codes count against the guest's budget too.
- A request body is at most 1 KB, a wish at most MAX_WISH characters.

Runs on daemon threads like the remote (http.server, no Qt); requests come
back through `on_request` on the server's thread.
"""
import ipaddress
import json
import logging
import secrets
import sys
import threading
import time
import unicodedata
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

from shared.remote.guest_page import GUEST_CODE_HEADER, MAX_WISH, page_html
from shared.remote.remote_server import lan_client

log = logging.getLogger("dancesport.guests")

DEFAULT_PORT = 8766
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O, 1/I: read off a screen
CODE_LENGTH = 6
PER_GUEST = 10                # requests (and wrong codes) one guest may send…
ALL_GUESTS = 120              # …and all guests together…
_WINDOW_SECS = 600            # …within this long
_IDLE_SECS = 60
_MAX_BODY = 1024


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def clean_wish(text) -> str:
    """A guest's free text as the inbox may show it: no control characters,
    one space between words, at most MAX_WISH characters."""
    if not isinstance(text, str):
        return ""
    kept = "".join(" " if unicodedata.category(ch).startswith("C") else ch for ch in text)
    return " ".join(kept.split())[:MAX_WISH].strip()


class Budget:
    """How many requests each guest, and all of them together, have left."""

    def __init__(self, per_guest: int = PER_GUEST, all_guests: int = ALL_GUESTS,
                 window: float = _WINDOW_SECS, clock=time.monotonic):
        self._per_guest = per_guest
        self._all = all_guests
        self._window = window
        self._clock = clock
        self._lock = threading.Lock()
        self._guests: dict[str, deque[float]] = {}
        self._every: deque[float] = deque()

    def spend(self, guest: str) -> bool:
        """One request from `guest`: True while both budgets allow it."""
        now = self._clock()
        cut = now - self._window
        with self._lock:
            for old in [g for g, times in self._guests.items() if not times or times[-1] <= cut]:
                del self._guests[old]
            mine = self._guests.setdefault(guest, deque())
            for times in (mine, self._every):
                while times and times[0] <= cut:
                    times.popleft()
            if len(mine) >= self._per_guest or len(self._every) >= self._all:
                return False
            mine.append(now)
            self._every.append(now)
            return True


class _Server(ThreadingHTTPServer):
    """The HTTP server, holding the GuestServer its handlers answer to."""
    guests: "GuestServer"
    allow_reuse_address = sys.platform != "win32"   # as the remote: never share a port


class _Handler(BaseHTTPRequestHandler):
    server_version = "DanceSportPlayerGuests"
    sys_version = ""
    timeout = _IDLE_SECS

    def log_message(self, format, *args):  # the console is not the log
        log.debug("📨 %s %s", self.client_address[0], format % args)

    @property
    def app(self) -> "GuestServer":
        return cast(_Server, self.server).guests

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

    def _guest(self) -> str:
        """Who is asking: the address, or behind the tunnel the guest's own."""
        peer = self.client_address[0]
        forwarded = (self.headers.get("CF-Connecting-IP") or "").strip()
        if forwarded and ipaddress.ip_address(peer.split("%", 1)[0]).is_loopback:
            return forwarded[:64]
        return peer

    def _gate(self) -> str | None:
        """The guest, when the request may go on; otherwise None, refusal sent."""
        if not lan_client(self.client_address[0]):
            self.app.note("refused", self.client_address[0])
            self._send(403)
            return None
        return self._guest()

    def _api_gate(self) -> str | None:
        """As `_gate`, and the event code must be the current one."""
        guest = self._gate()
        if guest is None:
            return None
        verdict = self.app.check_code(guest, self.headers.get(GUEST_CODE_HEADER, ""))
        if verdict != 200:
            self._send(verdict)
            return None
        return guest

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            guest = self._gate()
            if guest is not None:
                self.app.note("page", guest)
                self._send(200, self.app.page, "text/html; charset=utf-8")
        elif path == "/api/catalog":
            if self._api_gate() is not None:
                self._send(200, self.app.catalog_json())
        elif path == "/api/now":
            if self._api_gate() is not None:
                self._send(200, json.dumps(self.app.now(), ensure_ascii=False).encode("utf-8"))
        else:
            self._send(404)

    def do_POST(self):
        known = self.path.split("?", 1)[0] == "/api/request"
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = -1
        if not known or size < 0 or size > _MAX_BODY:
            # As the remote: closing on unread bytes resets the connection.
            if 0 < size <= 64 * _MAX_BODY:
                self.rfile.read(size)
            self._send(413 if known else 404)
            self.close_connection = True
            return
        raw = self.rfile.read(size)
        guest = self._api_gate()
        if guest is None:
            return
        try:
            msg = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._send(400)
            return
        self._send(self.app.take(guest, msg))

    def do_OPTIONS(self):
        # A CORS preflight. Never granted: only the page served here may call in.
        self._send(405)


class GuestServer:
    """The guest server and what it shares with the desk: the code, the
    title list, what is playing.

    `on_request(request)` gets each accepted request as a dict, on the
    server's thread: {"song": id} for a library title, {"text": wish} for
    free text. `on_event(kind, guest, detail)` hears start, stop, page,
    request, wish, bad_code, too_many, refused — for the guest window's log."""

    def __init__(self, on_request, host: str = "0.0.0.0",  # nosec B104: guests on the LAN or via the tunnel
                 port: int = DEFAULT_PORT, labels: dict | None = None,
                 on_event=None, code: str = ""):
        self.on_request = on_request
        self._on_event = on_event
        self._host = host
        self._want_port = int(port)
        self.page = page_html(labels or {}).encode("utf-8")
        self._lock = threading.Lock()
        self._code = code or new_code()
        self._ids: frozenset[str] = frozenset()
        self._catalog = b'{"songs":[]}'
        self._now: dict = {}
        self._budget = Budget()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self._httpd.server_address[1] if self._httpd else self._want_port

    @property
    def running(self) -> bool:
        return self._httpd is not None

    @property
    def code(self) -> str:
        with self._lock:
            return self._code

    def set_code(self, code: str) -> None:
        """A new event code at once: every older link is turned away."""
        with self._lock:
            self._code = str(code)

    def start(self) -> None:
        """Bind and serve. Raises OSError when the port is taken."""
        httpd = _Server((self._host, self._want_port), _Handler)
        httpd.daemon_threads = True
        httpd.guests = self
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, args=(0.1,), daemon=True,
                                        name="guest-requests")
        self._thread.start()
        log.info("📨 Guest requests on\n"
                 "port: %d", self.port)
        self.note("start", "", str(self.port))

    def stop(self) -> None:
        httpd, self._httpd = self._httpd, None
        if httpd is None:
            return
        httpd.shutdown()
        httpd.server_close()
        log.info("📨 Guest requests off")
        self.note("stop", "")

    def note(self, kind: str, guest: str, detail: str = "") -> None:
        """Hand one event to `on_event`; a failing listener never stops a request."""
        if self._on_event is None:
            return
        try:
            self._on_event(kind, guest, detail)
        except Exception as exc:
            log.debug("📨 Event listener failed: %s", exc)

    def set_catalog(self, songs) -> None:
        """The titles guests can search: (id, title, artist, dance) each."""
        rows = [[str(i), str(t), str(a), str(d)] for i, t, a, d in songs]
        blob = json.dumps({"songs": rows}, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
        with self._lock:
            self._ids = frozenset(r[0] for r in rows)
            self._catalog = blob

    def catalog_json(self) -> bytes:
        with self._lock:
            return self._catalog

    def publish_now(self, now: dict) -> None:
        with self._lock:
            self._now = dict(now)

    def now(self) -> dict:
        with self._lock:
            return self._now

    def check_code(self, guest: str, given: str) -> int:
        """200 for the current code; 410 while requests are closed (no code);
        403 for another one (and it costs the guest one request); 429 once
        the guest's budget is spent."""
        with self._lock:
            code = self._code
        if not code:
            return 410
        if secrets.compare_digest(given.encode("utf-8"), code.encode("utf-8")):
            return 200
        if not self._budget.spend(guest):
            return 429
        self.note("bad_code", guest)
        return 403

    def take(self, guest: str, msg) -> int:
        """One request from `guest`: 204 taken, 400 malformed, 429 over budget."""
        if not isinstance(msg, dict):
            return 400
        song = msg.get("song")
        song = song if isinstance(song, str) else ""
        text = clean_wish(msg.get("text"))
        with self._lock:
            known = song in self._ids
        if known == bool(text):     # exactly one of the two, and a valid one
            return 400
        if not self._budget.spend(guest):
            self.note("too_many", guest)
            return 429
        request = {"song": song} if known else {"text": text}
        self.note("request" if known else "wish", guest, song if known else text)
        try:
            self.on_request(request)
        except Exception as exc:
            log.warning("📨 A guest request was lost\n"
                        "error: %s", exc)
        return 204
