"""📱 The phone remote's window: is the server up, how the phone gets in, and
what has reached it so far.

Start / Stop holds for this run of the app only: closing the app stops the
server, and the next launch starts without one. The QR code holds the address with the PIN after a
"#" (see shared/remote/remote_page.py): scanned, the phone is in without typing.
The log shows every page opened, login, wrong PIN and command — so when the
phone shows nothing and the log stays empty too, the request never got here,
and the firewall hint below says where to look. Away from the Wi-Fi, a
Cloudflare tunnel gives the remote a public address (player/window/main_remote.py).
"""
import html
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton,
                               QVBoxLayout)

from planner import config, i18n
from player.window.main_remote import qr_url
from shared.remote import tunnel as tn

CLOUDFLARED_PAGE = "https://github.com/cloudflare/cloudflared/releases"
_QR_SIZE = 220
_QR_BORDER = 4          # the quiet zone a scanner needs, in modules
_LOG_BLOCKS = 500


def qr_pixmap(text: str, size: int = _QR_SIZE) -> QPixmap | None:
    """`text` as a QR code, black on white, about `size` pixels square.
    None without segno — the window then shows the address only."""
    try:
        import segno
    except ImportError:
        return None
    matrix = segno.make(text, error="m").matrix
    cells = len(matrix) + 2 * _QR_BORDER
    img = QImage(cells, cells, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    black = QColor("black").rgb()
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                img.setPixel(x + _QR_BORDER, y + _QR_BORDER, black)
    # Whole pixels per module, or the scaled code blurs at its edges.
    side = cells * max(1, size // cells)
    return QPixmap.fromImage(img.scaled(side, side, Qt.AspectRatioMode.IgnoreAspectRatio,
                                        Qt.TransformationMode.FastTransformation))


def server_program() -> str:
    """The program a firewall has to let in: the one that listens."""
    if getattr(sys, "frozen", False):
        return sys.executable
    # A venv's python.exe only starts the real one, which then listens.
    return getattr(sys, "_base_executable", sys.executable)


def ask_cloudflared(parent, fetcher, then):
    """No cloudflared yet: fetch it now, or say where to put it. `fetcher`
    downloads it (the 📨 guest desk: fetch_cloudflared, fetch_progress,
    fetch_done); `then()` runs once it is there."""
    answer = QMessageBox.question(
        parent, "cloudflared",
        i18n.t("The tunnel needs Cloudflare's free cloudflared program (about "
               "55 MB). Download it now from Cloudflare's releases on GitHub?\n\n"
               "It goes to: %s") % config.APP_DIR)
    if answer == QMessageBox.StandardButton.Yes:
        _fetch_cloudflared(parent, fetcher, then)
        return
    QMessageBox.information(
        parent, "cloudflared",
        i18n.t("Then download cloudflared yourself from\n%s\nand put it next to "
               "the program, as %s in:\n%s\n\nUntil then choose Wi-Fi only.")
        % (CLOUDFLARED_PAGE, tn.binary_name(), config.INSTALL_DIR))


def _install_by_hand(error: str) -> str:
    """Rich text after a failed download: where to get cloudflared, which
    file to take, and where to put it so find_cloudflared sees it."""
    asset = tn.asset_name() or tn.binary_name()
    lines = [html.escape(i18n.t("The download failed: %s") % error), "",
             i18n.t("Download it yourself instead from "
                    "<a href=\"%s\">Cloudflare's releases on GitHub</a>:") % CLOUDFLARED_PAGE]
    if sys.platform == "darwin":
        lines.append(i18n.t("Take <b>%s</b>, double-click it to unpack it, and put "
                            "the <b>cloudflared</b> inside into:") % asset)
    else:
        lines.append(i18n.t("Take <b>%s</b> and save it as <b>%s</b> in:")
                     % (asset, tn.binary_name()))
    folder = Path(config.APP_DIR)
    lines.append(html.escape(str(folder)))
    if sys.platform.startswith("linux"):
        lines.append(i18n.t("Then make it runnable: <code>chmod +x %s</code>")
                     % html.escape(str(folder / tn.binary_name())))
    if sys.platform == "darwin":
        lines += ["", i18n.t("Or, with Homebrew: <code>brew install cloudflared</code>")]
    lines += ["", i18n.t("Then start again. Until then choose Wi-Fi only.")]
    return "<br>".join(lines)


def _fetch_cloudflared(parent, fetcher, then):
    busy = QProgressDialog(i18n.t("Downloading cloudflared…"), "", 0, 0, parent)
    busy.setCancelButton(None)        # a download cannot be called back halfway
    busy.setWindowTitle("cloudflared")
    busy.setMinimumDuration(0)

    def progress(done, total):
        if total:
            busy.setMaximum(total)
            busy.setValue(done)

    def finished(path, error):
        fetcher.fetch_progress.disconnect(progress)
        fetcher.fetch_done.disconnect(finished)
        busy.close()
        if path:
            then()
        else:
            box = QMessageBox(QMessageBox.Icon.Warning, "cloudflared",
                              _install_by_hand(error), parent=parent)
            box.setTextFormat(Qt.TextFormat.RichText)
            box.exec()
    fetcher.fetch_progress.connect(progress)
    fetcher.fetch_done.connect(finished)
    busy.show()
    fetcher.fetch_cloudflared()


class RemoteDialog(QDialog):
    """Non-modal; the main window keeps one and shows it again."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self._host = host
        self._public_seen = ""
        self.setWindowTitle("📱  Phone remote")
        self.setMinimumWidth(560)
        lyt = QVBoxLayout(self)

        top = QHBoxLayout()
        self._status = QLabel()
        self._status.setStyleSheet("font-weight:bold; font-size:14px;")
        top.addWidget(self._status, stretch=1)
        self._toggle_btn = QPushButton()
        self._toggle_btn.setMinimumWidth(110)
        self._toggle_btn.clicked.connect(self._on_toggle)
        top.addWidget(self._toggle_btn)
        lyt.addLayout(top)
        self._add_mode_row(lyt)

        mid = QHBoxLayout()
        self._qr = QLabel()
        self._qr.setFixedSize(_QR_SIZE + 12, _QR_SIZE + 12)
        self._qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr.setWordWrap(True)
        self._qr.setStyleSheet("background:white; color:#666; border:1px solid #ccc;")
        mid.addWidget(self._qr)
        side = QVBoxLayout()
        scan = QLabel("Scan the code with the phone's camera — it opens "
                      "the remote, logged in. Or type the address:")
        scan.setWordWrap(True)
        side.addWidget(scan)
        self._addr = QComboBox()
        self._addr.setToolTip(
            "This PC is on more than one network. The first one is the way to\n"
            "the internet, usually the Wi-Fi the phone is on as well.")
        self._addr.currentIndexChanged.connect(lambda _i: self._show_code())
        side.addWidget(self._addr)
        self._link = QLabel()
        self._link.setOpenExternalLinks(True)
        self._link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self._link.setToolTip("Opens the remote in this PC's browser — a quick test "
                              "that the server answers.")
        side.addWidget(self._link)
        pin_row = QHBoxLayout()
        self._pin = QLabel()
        self._pin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._pin.setStyleSheet("font-size:14px;")
        pin_row.addWidget(self._pin, stretch=1)
        self._new_pin_btn = QPushButton("New PIN")
        self._new_pin_btn.setToolTip(
            "Make up a new PIN — phones that know the old one have to enter it again.")
        self._new_pin_btn.clicked.connect(self._host.new_remote_pin)
        pin_row.addWidget(self._new_pin_btn)
        side.addLayout(pin_row)
        side.addStretch(1)
        mid.addLayout(side, stretch=1)
        lyt.addLayout(mid)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._hint.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(self._hint)

        lyt.addWidget(QLabel("Log"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(_LOG_BLOCKS)
        self._log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self._log.setMinimumHeight(160)
        lyt.addWidget(self._log, stretch=1)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.close)
        lyt.addWidget(box)

        for line in host.remote_log():
            self._log.appendPlainText(line)
        hub = host.remote_hub()
        hub.line.connect(self._log.appendPlainText)
        hub.changed.connect(self.refresh)
        self.refresh()

    def _add_mode_row(self, lyt):
        """How the phone reaches the desk: this PC's Wi-Fi, or from anywhere."""
        row = QHBoxLayout()
        row.addWidget(QLabel("The phone reaches the desk:"))
        self._mode = QComboBox()
        self._mode.addItem("Wi-Fi only", "wifi")
        self._mode.addItem("Wi-Fi and mobile data (Cloudflare tunnel)", "tunnel")
        self._mode.setToolTip(
            "Wi-Fi only: the phone must be on the same Wi-Fi as this PC, or on its hotspot.\n"
            "Cloudflare tunnel: a public https address leads to this PC as well —\n"
            "no account and no router setup; it changes with every start, and\n"
            "the PIN grows to 8 digits. Needs the free cloudflared program.")
        self._mode.setCurrentIndex(max(0, self._mode.findData(self._host.remote_mode())))
        self._mode.currentIndexChanged.connect(
            lambda _i: self._host.set_remote_mode(self._mode.currentData()))
        row.addWidget(self._mode, stretch=1)
        lyt.addLayout(row)

    def _on_toggle(self):
        running = self._host.remote_status()["running"]
        if (not running and self._host.remote_mode() == "tunnel"
                and tn.find_cloudflared() is None):
            ask_cloudflared(self, self._host.guest_desk(),
                            lambda: self._host.set_remote_running(True))
            return
        self._host.set_remote_running(not running)

    def _hint_text(self, mode: str) -> str:
        """The grey line under the code: who can reach the remote, and the firewall."""
        if mode == "tunnel":
            return i18n.t("The https address works on mobile data too, and on any "
                          "Wi-Fi. It is new on every start — scan the fresh QR code. "
                          "Whoever has the address still needs the PIN.")
        return (i18n.t("Nothing turns up in the log when the phone tries? Then a firewall "
                       "on this PC drops it: allow the program below for private networks "
                       "(Windows Defender Firewall, or your security suite's own, e.g. "
                       "Norton → Firewall → Program Control). The phone must be on the "
                       "same Wi-Fi.%s")
                % ("\n" + server_program()))   # its own line: a path wraps badly

    def refresh(self):
        """Running or not, the addresses and the PIN — from the host, afresh."""
        st = self._host.remote_status()
        running = st["running"]
        if running:
            self._status.setText(
                (i18n.t("● Running — port %d, waiting for Cloudflare…") if st["waiting"]
                 else i18n.t("● Running — port %d")) % st["port"])
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#2e7d32;")
            self._toggle_btn.setText("■  Stop")
        else:
            self._status.setText("○ Stopped")
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#666;")
            self._toggle_btn.setText("▶  Start")
        self._hint.setText(self._hint_text(st["mode"]))
        keep = self._addr.currentText()
        if st["public"] != self._public_seen:   # a new public address: show it first
            self._public_seen = st["public"]
            keep = st["public"] or keep
        self._addr.blockSignals(True)
        self._addr.clear()
        for url in st["urls"]:
            self._addr.addItem(url)  # i18n: data — an address
        self._addr.setCurrentIndex(max(0, self._addr.findText(keep)))
        self._addr.blockSignals(False)
        self._addr.setVisible(len(st["urls"]) > 1)
        # i18n: data — "PIN" reads the same in German
        self._pin.setText(f"PIN: {st['pin']}")
        self._new_pin_btn.setEnabled(running)
        self._show_code()

    def _show_code(self):
        st = self._host.remote_status()
        url = self._addr.currentText()
        if not url:
            self._link.setText("No network found — is this PC on the Wi-Fi?")
            self._qr.setPixmap(QPixmap())
            self._qr.setText("")
            return
        self._link.setText(f'<a href="{url}">{url}</a>')  # i18n: data — a link
        if not st["running"]:
            self._qr.setPixmap(QPixmap())
            self._qr.setText("Press Start — the code to scan shows up here.")
            return
        if st["waiting"]:   # the tunnel is connecting: no address to scan yet
            self._link.setText("")
            self._qr.setPixmap(QPixmap())
            self._qr.setText("Connecting… the code to scan shows up as soon as "
                             "the phone can reach the desk.")
            return
        pix = qr_pixmap(qr_url(url, st["pin"]))
        if pix is None:
            self._qr.setPixmap(QPixmap())
            self._qr.setText("No QR code: the segno package is missing. "
                             "Type the address instead.")
            return
        self._qr.setText("")
        self._qr.setPixmap(pix)
