"""📱 The phone remote's window: is the server up, how the phone gets in, and
what has reached it so far.

Start / Stop holds for this run of the app only: closing the app stops the
server, and the next launch starts without one. The QR code holds the address with the PIN after a
"#" (see shared/remote_page.py): scanned, the phone is in without typing.
The log shows every page opened, login, wrong PIN and command — so when the
phone shows nothing and the log stays empty too, the request never got here,
and the firewall hint below says where to look.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QVBoxLayout)

from planner import i18n
from player.main_remote import qr_url

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


class RemoteDialog(QDialog):
    """Non-modal; the main window keeps one and shows it again."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self._host = host
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

        self._hint = QLabel(
            i18n.t("Nothing turns up in the log when the phone tries? Then a firewall "
                   "on this PC drops it: allow the program below for private networks "
                   "(Windows Defender Firewall, or your security suite's own, e.g. "
                   "Norton → Firewall → Program Control). The phone must be on the "
                   "same Wi-Fi.%s")
            % ("\n" + server_program()))   # its own line: a path wraps badly
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

    def _on_toggle(self):
        self._host.set_remote_running(not self._host.remote_status()["running"])

    def refresh(self):
        """Running or not, the addresses and the PIN — from the host, afresh."""
        st = self._host.remote_status()
        running = st["running"]
        if running:
            self._status.setText(i18n.t("● Running — port %d") % st["port"])
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#2e7d32;")
            self._toggle_btn.setText("■  Stop")
        else:
            self._status.setText("○ Stopped")
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#666;")
            self._toggle_btn.setText("▶  Start")
        keep = self._addr.currentText()
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
        pix = qr_pixmap(qr_url(url, st["pin"]))
        if pix is None:
            self._qr.setPixmap(QPixmap())
            self._qr.setText("No QR code: the segno package is missing. "
                             "Type the address instead.")
            return
        self._qr.setText("")
        self._qr.setPixmap(pix)
