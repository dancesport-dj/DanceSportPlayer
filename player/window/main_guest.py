"""📨 Guest requests, desk side: the guest server, its inbox and its window.

The server (shared/remote/guest_server.py) knows nothing of Qt. GuestDesk owns
it for the window — one object, one attribute on the window — hands it the
library's titles as it starts, tells it what is playing, and gathers what the
guests ask for into an inbox. A request moves nothing by itself: from the 📨
window the DJ puts a title on the ⭐ wishlist, or drops it.
"""
import hashlib
import logging
import threading
import time
from collections import deque
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QPushButton

from planner import config, i18n
from planner.terms import dance_name
from player.window.main_remote import remote_urls
from shared.remote import guest_server as gs
from shared.remote import tunnel as tn
from shared.remote.guest_page import DEFAULT_LABELS
from shared.stores import save_settings
from shared.widgets import show_toast

if TYPE_CHECKING:
    from gui.window.hosts import MainWindowHost
    from player.dialogs.guest_dialog import GuestDialog
else:
    MainWindowHost = object

log = logging.getLogger("dancesport.gui.guests")

_NOW_MS = 2000
_FLASH_MS = 500
_LOG_LINES = 300
_UP_NEXT = 5  # titles on the guest page's "Up next" tab

# The 📨 pill: calm blue, and the orange it flashes to while a request waits unseen.
_BADGE_STYLE = ("background:%s; color:white; font-weight:bold; "
                "border:none; border-radius:8px; padding:1px 8px; margin:2px 4px;")
_BADGE_CALM = "#1565c0"
_BADGE_LIT = "#ff9800"

# How guests reach the page: on this PC's networks only, or through a
# Cloudflare quick tunnel from anywhere (shared/remote/tunnel.py).
MODES = ("wifi", "tunnel")

# What each server event reads like in the 📨 window's log.
_EVENT_TEXT = {
    "start": "▶ Guest requests open on port %(detail)s",
    "stop": "■ Guest requests closed",
    "page": "%(ip)s opened the page",
    "request": "📨 %(ip)s asks for %(detail)s",
    "wish": "📨 %(ip)s wishes: %(detail)s",
    "bad_code": "✖ %(ip)s came with an old code",
    "too_many": "⛔ %(ip)s sent too many requests",
    "refused": "⛔ %(ip)s refused — not on the local network",
    "failed": "⚠ Could not start: %(detail)s",
    "tunnel_wait": "🌐 Connecting to Cloudflare…",
    "tunnel_up": "🌐 Public address: %(detail)s",
    "tunnel_down": "⚠ The tunnel ended (exit code %(detail)s) — guests on mobile data are cut off",
    "no_tunnel": "⚠ cloudflared not found — guests reach the page on the Wi-Fi only",
    "tunnel_failed": "⚠ The tunnel could not start: %(detail)s",
}


def guest_qr_url(url: str, code: str) -> str:
    """The address the QR code holds: the page, with the event code."""
    return f"{url}/#e={code}"


def song_id(entry) -> str:
    """A title's id on the guest page: the same file, the same id."""
    return hashlib.sha1(str(entry.path).encode("utf-8"), usedforsecurity=False).hexdigest()[:10]


def song_label(entry) -> str:
    """How a requested title reads in the inbox: the dance, then artist – title
    — the three things the guest picked it by."""
    dance = dance_name(entry.dance, entry.other_genre or entry.dance or "")
    artist = entry.tag_artist or ""
    song = f"{artist} – {entry.title}" if artist else entry.title
    return f"{dance} — {song}" if dance else song


class GuestDesk(QObject):
    """📨 The guest server and its inbox, for as long as the window lives.

    The inbox holds one row per requested title (asked again: its count goes
    up) and one per wish (the same words again: likewise). Start / Stop holds
    for this run of the app only, as the phone remote's does."""

    arrived = Signal(object)            # a guest's request (server thread → GUI)
    guest_event = Signal(str, str, str)  # kind, guest, detail (server thread → GUI)
    line = Signal(str)                  # a new log line, formatted
    changed = Signal()                  # started, stopped, a new code, the inbox
    tunnel_url = Signal(object, str)    # tunnel, its address (reader thread → GUI)
    tunnel_ended = Signal(object, int)  # tunnel, exit code (reader thread → GUI)
    fetch_progress = Signal(int, int)   # cloudflared download: done, total bytes
    fetch_done = Signal(str, str)       # its path, or "" and the error

    def __init__(self, window: MainWindowHost):
        super().__init__()
        self._win = window
        self.server: gs.GuestServer | None = None
        self.tunnel: tn.Tunnel | None = None
        self.public_url = ""
        self.picked = ""   # the address the 📨 window shows, for the presenter too
        self.inbox: list[dict] = []
        self.log: deque[str] = deque(maxlen=_LOG_LINES)
        self.dialog: GuestDialog | None = None
        self._songs: dict = {}
        self._badge: QPushButton | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(_NOW_MS)
        self._timer.timeout.connect(self._publish_now)
        self._flash = QTimer(self)
        self._flash.setInterval(_FLASH_MS)
        self._flash.timeout.connect(self._on_flash)
        self._lit = False
        self.arrived.connect(self._on_arrived)
        self.guest_event.connect(self._on_event)
        self.tunnel_url.connect(self._on_tunnel_url)
        self.tunnel_ended.connect(self._on_tunnel_ended)
        self.changed.connect(self.sync_presenter)

    def status(self) -> dict:
        """What the 📨 window shows: running or not, where, with which code."""
        srv = self.server
        port = srv.port if srv is not None else int(
            self._win._settings.get("guest_port", gs.DEFAULT_PORT))
        public = [self.public_url] if self.public_url else []
        return {"running": srv is not None, "port": port,
                "code": srv.code if srv is not None else "",
                "mode": self.mode(), "public": self.public_url,
                # Connecting: no code to show yet, the address may not work.
                "waiting": self.tunnel is not None and not self.public_url,
                "urls": public + remote_urls(port)}

    def mode(self) -> str:
        mode = self._win._settings.get("guest_mode")
        return mode if mode in MODES else MODES[0]

    def set_mode(self, mode: str):
        """Remembered across runs; a running server restarts the new way."""
        if mode not in MODES or mode == self.mode():
            return
        self._win._settings["guest_mode"] = mode
        save_settings(self._win._settings)
        if self.server is not None:
            self.stop()
            self._start()
        self._sync_badge()
        self.changed.emit()

    def presenter_qr_on(self) -> bool:
        return bool(self._win._settings.get("guest_qr_presenter", True))

    def set_presenter_qr(self, on: bool):
        """🖥 The code on the presenter screen, or not: remembered across runs."""
        self._win._settings["guest_qr_presenter"] = bool(on)
        save_settings(self._win._settings)
        self.sync_presenter()

    def pick_address(self, url: str):
        """The 📨 window shows `url`: the presenter screen shows the same one."""
        if url != self.picked:
            self.picked = url
            self.sync_presenter()

    def presenter_link(self) -> str:
        """What the presenter screen's QR code holds; "" for no code."""
        srv = self.server
        if srv is None or not self.presenter_qr_on():
            return ""
        st = self.status()
        urls = st["urls"]
        if not urls or st["waiting"]:
            return ""
        url = self.picked if self.picked in urls else urls[0]
        return guest_qr_url(url, srv.code)

    def sync_presenter(self):
        """Hand an open presenter screen the code it should show."""
        screen = getattr(self._win, "_presenter", None)
        if screen is None:
            return
        from player.dialogs.remote_dialog import qr_pixmap
        link = self.presenter_link()
        screen.set_guest_qr(qr_pixmap(link, 1) if link else None)  # one pixel per module

    def set_running(self, on: bool):
        if on and self.server is None:
            self._start()
        elif not on:
            self.stop()
        self._sync_badge()
        self.changed.emit()

    def new_code(self):
        """A new event code at once: every older link and QR photo is turned away."""
        if self.server is not None:
            self.server.set_code(gs.new_code())
        self.changed.emit()

    def _start(self):
        srv = gs.GuestServer(
            self.arrived.emit,
            port=int(self._win._settings.get("guest_port", gs.DEFAULT_PORT)),
            labels={k: i18n.t(v) for k, v in DEFAULT_LABELS.items()},
            on_event=self.guest_event.emit)
        srv.set_catalog(self._catalog())
        try:
            srv.start()
        except OSError as exc:
            log.error("📨 Guest requests could not start\n"
                      "port: %s\n"
                      "error: %s", srv.port, exc)
            self._on_event("failed", "", str(exc))
            self._win.statusBar().showMessage(
                i18n.t("📨 Guest requests could not start: %s") % exc)
            return
        self.server = srv
        self._publish_now()
        self._timer.start()
        if self.mode() == "tunnel":
            self._start_tunnel(srv.port)

    def _start_tunnel(self, port: int):
        binary = tn.find_cloudflared()
        if binary is None:
            self._on_event("no_tunnel", "", "")
            return
        t = tn.Tunnel(binary, port,
                      on_url=lambda url: self.tunnel_url.emit(t, url),
                      on_line=lambda text: log.debug("🌐 %s", text),
                      on_exit=lambda code: self.tunnel_ended.emit(t, code))
        try:
            t.start()
        except OSError as exc:
            self._on_event("tunnel_failed", "", str(exc))
            return
        self.tunnel = t
        self._on_event("tunnel_wait", "", "")

    def _on_tunnel_url(self, t, url: str):
        if t is self.tunnel:
            self.public_url = url
            if self.server is not None:
                self.server.set_tunnel(url)
            self.picked = ""   # the public address goes first, as in the window
            self._on_event("tunnel_up", "", url)
            self.changed.emit()

    def _on_tunnel_ended(self, t, code: int):
        """cloudflared gave up on its own — after stop() the tunnel is gone already."""
        if t is self.tunnel:
            self.tunnel = None
            self.public_url = ""
            if self.server is not None:
                self.server.set_tunnel("")
            self._on_event("tunnel_down", "", str(code))
            self.changed.emit()

    def stop(self):
        self._timer.stop()
        t, self.tunnel = self.tunnel, None
        self.public_url = ""
        if t is not None:
            t.stop()
        srv, self.server = self.server, None
        if srv is not None:
            srv.stop()

    def fetch_cloudflared(self):
        """Download cloudflared into the data folder, off the GUI thread;
        `fetch_done` tells how it went."""
        def run():
            try:
                path = tn.download(config.APP_DIR, progress=self.fetch_progress.emit)
            except (OSError, ValueError) as exc:
                log.warning("🌐 cloudflared download failed\n"
                            "error: %s", exc)
                self.fetch_done.emit("", str(exc))
                return
            self.fetch_done.emit(str(path), "")
        threading.Thread(target=run, daemon=True, name="cloudflared-download").start()

    def _catalog(self) -> list[tuple[str, str, str, str]]:
        """The library's titles for the guest page, each under its id."""
        lib = self._win._library.lib
        self._songs = {song_id(e): e for e in (lib.entries if lib is not None else [])}
        return [(i, e.title, e.tag_artist or "",
                 dance_name(e.dance, e.other_genre or e.dance or ""))
                for i, e in self._songs.items()]

    def _publish_now(self):
        if self.server is not None:
            dance, title, *_rest = self._win._presenter_state()
            self.server.publish_now({
                "dance": dance, "title": title,
                "next": [list(n) for n in self._win._presenter_upcoming(_UP_NEXT)]})

    def _on_event(self, kind: str, guest: str, detail: str):
        if kind == "request" and detail in self._songs:
            detail = song_label(self._songs[detail])
        text = i18n.t(_EVENT_TEXT.get(kind, "%(ip)s %(detail)s")) % {
            "ip": guest, "detail": detail}
        line = f"{time.strftime('%H:%M:%S')}  {text}"
        self.log.append(line)
        self.line.emit(line)

    def _on_arrived(self, request: dict):
        """One request into the inbox: a title or words asked before count up."""
        entry = self._songs.get(request.get("song", ""))
        text = request.get("text", "")
        if entry is None and not text:
            return
        same = next((item for item in self.inbox
                     if (entry is not None and item.get("entry") is entry)
                     or (text and item.get("text", "").casefold() == text.casefold())),
                    None)
        if same is None:
            same = {"entry": entry} if entry is not None else {"text": text}
            same["count"] = 0
            self.inbox.append(same)
        same["count"] += 1
        same["at"] = time.strftime("%H:%M")
        self._sync_badge()
        self.changed.emit()
        if self.dialog is None or not self.dialog.isVisible():
            # Out of sight: the pill flashes until the 📨 window is opened.
            self._flash.start()
            show_toast(self._win, (i18n.t("📨 Guest request: %s") % song_label(entry)
                                    if entry is not None
                                    else i18n.t("📨 Guest wish: %s") % text), 4000)

    def seen(self):
        """The 📨 window is up: the pill stops flashing."""
        self._flash.stop()
        self._lit = False
        if self._badge is not None:
            self._badge.setStyleSheet(_BADGE_STYLE % _BADGE_CALM)

    def _on_flash(self):
        self._lit = not self._lit
        if self._badge is not None:
            self._badge.setStyleSheet(_BADGE_STYLE % (_BADGE_LIT if self._lit else _BADGE_CALM))

    def take(self, item: dict) -> bool:
        """⭐ A requested title onto the first wishlist, and out of the inbox.
        False when it was on the wishlist already."""
        entry = item.get("entry")
        if entry is None:
            return False
        table = self._win._deckset.wishlists[0]
        before = table.rowCount()
        table._append_entry(entry)
        self.drop(item)
        added = table.rowCount() > before
        self._win.statusBar().showMessage(
            (i18n.t("⭐ On the wishlist: %s") if added
             else i18n.t("⭐ Already on the wishlist: %s")) % song_label(entry), 4000)
        return added

    def drop(self, item: dict):
        self.inbox = [i for i in self.inbox if i is not item]
        self._sync_badge()
        self.changed.emit()

    def _sync_badge(self):
        """📨 A pill at the right of the status bar while guests can ask, or
        while requests wait: how many, and a click opens the window."""
        badge = self._badge
        if badge is None:
            badge = QPushButton()
            badge.setToolTip("Guest requests — click for the inbox.")
            badge.setStyleSheet(_BADGE_STYLE % _BADGE_CALM)
            badge.setCursor(Qt.CursorShape.PointingHandCursor)
            badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            badge.clicked.connect(lambda: self._win.open_guest_window())
            self._win.statusBar().insertPermanentWidget(0, badge)
            self._badge = badge
        waiting = sum(item["count"] for item in self.inbox)
        badge.setText(f"📨 {waiting}" if waiting else "📨")  # i18n: data — a count
        badge.setVisible(self.server is not None or waiting > 0)
        if not waiting:
            self.seen()


class GuestMixin(MainWindowHost):
    """📨 Guest requests — off unless switched on in their window."""

    def guest_desk(self) -> GuestDesk:
        desk = getattr(self, "_guests", None)
        if desk is None:
            desk = GuestDesk(self)
            self._guests = desk
        return desk

    def open_guest_window(self, over=None):
        """📨 The window: Start / Stop, the QR code, the inbox, the log.

        `over` is a modal dialog it is opened from (⚙ Settings), as for the
        phone remote's window: then it is that dialog's own, and goes with it."""
        from player.dialogs.guest_dialog import GuestDialog
        desk = self.guest_desk()
        desk.seen()
        if over is not None:
            dlg = GuestDialog(desk, parent=over)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.show()
            return dlg
        dlg = desk.dialog
        if dlg is None:
            dlg = GuestDialog(desk, parent=self)
            desk.dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def _guest_shutdown(self):
        desk = getattr(self, "_guests", None)
        if desk is not None:
            desk.stop()
