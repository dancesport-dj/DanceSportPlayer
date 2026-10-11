"""📱 Phone remote, desk side: start / stop the server, feed it, obey it.

The server itself (shared/remote_server.py) knows nothing of Qt. This mixin
pushes it a snapshot of the desk twice a second while it runs, and takes the
phone's commands on the GUI thread — the server's thread hands them over
through a signal — to the very methods the big player's, the presenter's and
the taskbar's buttons call. What the server reports goes into a short log the
📱 window shows, so "the phone can't reach it" has an answer on the desk.
"""
import logging
import time
from collections import deque

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QPushButton

from planner import cartwall as pc
from planner import i18n
from shared import remote_server as rs
from shared.remote_page import DEFAULT_LABELS
from shared.stores import save_settings

log = logging.getLogger("dancesport.gui.remote")

_PUBLISH_MS = 500
_LOG_LINES = 300

# What each server event reads like in the 📱 window's log.
_EVENT_TEXT = {
    "start": "▶ Server started on port %(detail)s",
    "stop": "■ Server stopped",
    "page": "%(ip)s opened the page",
    "login": "✔ %(ip)s logged in with the PIN",
    "wrong_pin": "✖ %(ip)s sent a wrong PIN",
    "locked": "⛔ %(ip)s locked out for %(detail)s s — too many wrong PINs",
    "refused": "⛔ %(ip)s refused — not on the local network",
    "cmd": "%(ip)s → %(detail)s",
    "failed": "⚠ Could not start: %(detail)s",
}


class _RemoteHub(QObject):
    """Lives as long as the window: carries the server's commands and events
    from its thread onto the GUI thread, and tells the 📱 window news."""

    command = Signal(str, object)
    event = Signal(str, str, str)       # kind, ip, detail (server thread → GUI)
    line = Signal(str)                  # a new log line, formatted
    changed = Signal()                  # started, stopped or a new PIN


class RemoteMixin:
    """📱 The phone remote — off unless switched on."""

    def remote_hub(self) -> _RemoteHub:
        hub = getattr(self, "_remote_bridge", None)
        if hub is None:
            hub = _RemoteHub()
            hub.command.connect(lambda cmd, arg: self._on_remote_command(cmd, arg))
            hub.event.connect(self._on_remote_event)
            self._remote_bridge = hub
            self._remote_log = deque(maxlen=_LOG_LINES)
        return hub

    def remote_log(self) -> list[str]:
        self.remote_hub()
        return list(self._remote_log)

    def _on_remote_event(self, kind: str, ip: str, detail: str):
        text = i18n.t(_EVENT_TEXT.get(kind, "%(ip)s %(detail)s")) % {
            "ip": ip, "detail": detail}
        line = f"{time.strftime('%H:%M:%S')}  {text}"
        self._remote_log.append(line)
        self.remote_hub().line.emit(line)

    def remote_status(self) -> dict:
        """What the 📱 window shows: running or not, where, with which PIN."""
        srv = self._remote
        port = srv.port if srv is not None else int(
            self._settings.get("remote_port", rs.DEFAULT_PORT))
        return {"running": srv is not None, "port": port,
                "pin": str(self._settings.get("remote_pin") or ""),
                "urls": remote_urls(port)}

    def set_remote_running(self, on: bool):
        """The 📱 window's Start / Stop — for this run of the app only: closing
        it stops the server, and the next launch starts without one."""
        self._remote_wanted = bool(on)
        self._apply_remote()

    def new_remote_pin(self):
        """A new PIN at once — a running server takes it without a restart."""
        pin = rs.new_pin()
        self._settings["remote_pin"] = pin
        save_settings(self._settings)
        if self._remote is not None:
            self._remote.set_pin(pin)
        self.remote_hub().changed.emit()

    def _apply_remote(self, restart: bool = False):
        """Start or stop the server to match the 📱 window's Start / Stop."""
        want = bool(getattr(self, "_remote_wanted", False))
        if self._remote is not None and (restart or not want):
            self._stop_remote()
        if want and self._remote is None:
            self._start_remote()
        self._sync_remote_badge()
        self.remote_hub().changed.emit()

    def _sync_remote_badge(self):
        """📱 A green LIVE pill at the right of the status bar while the
        server runs — on either side of the desk, so it is never forgotten."""
        badge = getattr(self, "_remote_badge", None)
        if badge is None:
            # i18n: data — "LIVE" reads the same in German
            badge = QPushButton("📱 LIVE")
            badge.setToolTip("The phone remote's server is running — "
                             "click for its window.")
            badge.setStyleSheet("background:#2e7d32; color:white; font-weight:bold; "
                                "border:none; border-radius:8px; padding:1px 8px; "
                                "margin:2px 4px;")
            badge.setCursor(Qt.CursorShape.PointingHandCursor)
            badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            badge.clicked.connect(lambda: self.open_remote_window())
            # First of the permanent widgets: the ⛶ clock keeps the far right.
            self.statusBar().insertPermanentWidget(0, badge)
            self._remote_badge = badge
        badge.setVisible(self._remote is not None)

    def _start_remote(self):
        pin = str(self._settings.get("remote_pin") or "")
        if not pin:
            pin = rs.new_pin()
            self._settings["remote_pin"] = pin
            save_settings(self._settings)
        hub = self.remote_hub()
        srv = rs.RemoteServer(
            pin, hub.command.emit,
            port=int(self._settings.get("remote_port", rs.DEFAULT_PORT)),
            labels={k: i18n.t(v) for k, v in DEFAULT_LABELS.items()},
            on_event=hub.event.emit)
        try:
            srv.start()
        except OSError as exc:
            log.error("📱 Phone remote could not start\n"
                      "port: %s\n"
                      "error: %s", srv.port, exc)
            self._on_remote_event("failed", "", str(exc))
            self.statusBar().showMessage(
                i18n.t("📱 The phone remote could not start: %s") % exc)
            return
        self._remote = srv
        self._remote_timer = QTimer()
        self._remote_timer.setInterval(_PUBLISH_MS)
        self._remote_timer.timeout.connect(self._publish_remote)
        self._remote_timer.start()
        self._publish_remote()
        urls = remote_urls(srv.port)
        # i18n: data — the address and the PIN go in as they are
        self.statusBar().showMessage(
            i18n.t("📱 Phone remote on — open %s on the phone, PIN %s")
            % (urls[0] if urls else f"port {srv.port}", pin))

    def _stop_remote(self):
        if self._remote_timer is not None:
            self._remote_timer.stop()
            self._remote_timer = None
        srv, self._remote = self._remote, None
        if srv is not None:
            srv.stop()

    def start_remote_server(self, over=None):
        """⚙ Settings' 📱 Start Server: the server on, its window on top."""
        if self._remote is None:
            self.set_remote_running(True)
        return self.open_remote_window(over)

    def open_remote_window(self, over=None):
        """📱 The server's window: Start / Stop, the QR code, the log.

        `over` is a modal dialog it is opened from (⚙ Settings): the window is
        then that dialog's own, or the modal one would keep every click from
        it — and it goes when that dialog does."""
        from player.remote_dialog import RemoteDialog
        if over is not None:
            dlg = RemoteDialog(self, parent=over)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.show()
            return dlg
        dlg = getattr(self, "_remote_dlg", None)
        if dlg is None:
            dlg = RemoteDialog(self, parent=self)
            self._remote_dlg = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def _publish_remote(self):
        if self._remote is not None:
            self._remote.publish(self._remote_state())

    def _remote_state(self) -> dict:
        """What the phone shows: the presenter's view of the desk, plus the
        pads of the cartwall page that is up."""
        dance, title, times, upcoming, _last = self._presenter_state()
        played, left, ending, fraction = times
        pads, keys = [], []
        wall = self._cartwall
        if wall is not None:
            page = wall.current_page()
            pages = wall.pages()
            if 0 <= page < len(pages):
                for (row, col), pad in sorted(pages[page].pads.items()):
                    key = (page, row, col)
                    voices = self._cart_voices
                    pads.append({"label": pad.label or pc.default_label(pad.path),
                                 "colour": pad.colour,
                                 "live": bool(voices is not None
                                              and voices.is_playing(key))})
                    keys.append(key)
        self._remote_pad_keys = keys
        return {"dance": dance, "title": title, "played": played, "left": left,
                "ending": bool(ending), "fraction": float(fraction),
                "next": [list(x) for x in upcoming],
                "playing": not self._is_player_stopped(),
                "announce": bool(self._play_panel.announce_next()),
                "pads": pads}

    def _on_remote_command(self, cmd: str, arg):
        """A button on the phone — the same action as on the desk."""
        log.info("📱 Remote: %s%s", cmd, "" if arg is None else f" {arg}")
        if cmd == "toggle":
            self._presenter_play_pause()
        elif cmd == "next":
            self._on_player_next()
        elif cmd == "prev":
            self._preview_skip(-1)
        elif cmd == "fade":
            self._fade_out_now()
        elif cmd == "hold":
            self._fade_and_hold()
        elif cmd == "announce":
            # 🔈 The play panel's own switch: remembered, and its options
            # follow, exactly as when it is flipped on the desk.
            chk = self._play_panel.announce_check
            chk.setChecked(not chk.isChecked())
        elif cmd == "seek":
            self._seek_fraction(arg)
        elif cmd == "stop_pads":
            self._on_cart_stop_all()
        elif cmd == "pad":
            keys = self._remote_pad_keys
            if self._cartwall is not None and isinstance(arg, int) and 0 <= arg < len(keys):
                self._cartwall.play_pad(keys[arg])
        self._publish_remote()


def remote_urls(port: int) -> list[str]:
    """What to type on the phone, one per network this PC is on."""
    return [f"http://{a}:{port}" for a in rs.lan_addresses()]


def qr_url(url: str, pin: str) -> str:
    """The address the QR code holds: the page, logged in with the PIN.
    After the "#", so the browser keeps it to itself (see remote_page)."""
    return f"{url}/#pin={pin}"
