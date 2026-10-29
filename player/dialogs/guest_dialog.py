"""📨 The guest requests' window: open or closed, how guests get in, what they
asked for, and what has reached the server so far.

The QR code holds the page's address with the event code after a "#" (see
shared/remote/guest_page.py): scanned, the guest is in. "New code" turns every
older link and photo of the code away. The inbox holds what guests asked for
until the DJ puts a title on the ⭐ wishlist or dismisses it — nothing a guest
sends is played on its own.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from planner import i18n
from player.dialogs.remote_dialog import ask_cloudflared, qr_pixmap, server_program
from player.window.main_guest import guest_qr_url, song_label
from shared.remote import tunnel as tn

_QR_SIZE = 220
_LOG_BLOCKS = 500


def hint_text(mode: str) -> str:
    """The grey line under the code: who can reach the page, and the firewall."""
    firewall = i18n.t("Nothing turns up in the log when a phone on the Wi-Fi tries? Then "
                      "a firewall on this PC drops it: allow the program below for "
                      "private networks.%s") % ("\n" + server_program())  # a path wraps badly
    if mode == "tunnel":
        reach = i18n.t("The https address works on mobile data too, and on any Wi-Fi. "
                       "It is new on every start — show the fresh QR code.")
    else:
        reach = i18n.t("Guests must be on the same Wi-Fi as this PC — or on its hotspot.")
    return f"{reach} {firewall}"


def inbox_row(item: dict) -> str:
    """One inbox row: when, then the title (and how often asked) or the words."""
    count = f"  ×{item['count']}" if item["count"] > 1 else ""
    entry = item.get("entry")
    if entry is not None:
        return f"{item['at']}  {song_label(entry)}{count}"
    return f"{item['at']}  💬 {item['text']}{count}"


class GuestDialog(QDialog):
    """Non-modal; the main window keeps one and shows it again."""

    def __init__(self, desk, parent=None):
        super().__init__(parent)
        self._desk = desk
        self._public_seen = ""
        self.setWindowTitle("📨  Guest requests")
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
        scan = QLabel("Guests scan the code with their phone's camera — it opens "
                      "the request page. Or show them the address:")
        scan.setWordWrap(True)
        side.addWidget(scan)
        self._addr = QComboBox()
        self._addr.setToolTip(
            "This PC is on more than one network. The first one is the way to\n"
            "the internet, usually the Wi-Fi the guests are on as well.")
        self._addr.currentIndexChanged.connect(lambda _i: self._show_code())
        side.addWidget(self._addr)
        self._link = QLabel()
        self._link.setOpenExternalLinks(True)
        self._link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self._link.setToolTip("Opens the request page in this PC's browser — a quick "
                              "test that the server answers.")
        side.addWidget(self._link)
        code_row = QHBoxLayout()
        self._code = QLabel()
        self._code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._code.setStyleSheet("font-size:14px;")
        code_row.addWidget(self._code, stretch=1)
        self._new_code_btn = QPushButton("New code")
        self._new_code_btn.setToolTip(
            "Make up a new event code — older links and photos of the QR code stop working.")
        self._new_code_btn.clicked.connect(self._desk.new_code)
        code_row.addWidget(self._new_code_btn)
        side.addLayout(code_row)
        self._on_presenter = QCheckBox("🖥  Show the QR code on the presenter screen")
        self._on_presenter.setToolTip(
            "While guest requests are open, the presenter screen shows the code in\n"
            "its corner — guests scan it from the floor.")
        self._on_presenter.setChecked(self._desk.presenter_qr_on())
        self._on_presenter.toggled.connect(self._desk.set_presenter_qr)
        side.addWidget(self._on_presenter)
        side.addStretch(1)
        mid.addLayout(side, stretch=1)
        lyt.addLayout(mid)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._hint.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(self._hint)

        self._add_inbox(lyt)

        lyt.addWidget(QLabel("Log"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(_LOG_BLOCKS)
        self._log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self._log.setMinimumHeight(100)
        lyt.addWidget(self._log)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.close)
        lyt.addWidget(box)

        for line in desk.log:
            self._log.appendPlainText(line)
        desk.line.connect(self._log.appendPlainText)
        desk.changed.connect(self.refresh)
        self.refresh()

    def _add_mode_row(self, lyt):
        """How guests reach the page: this PC's Wi-Fi, or from anywhere."""
        row = QHBoxLayout()
        row.addWidget(QLabel("Guests reach the page:"))
        self._mode = QComboBox()
        self._mode.addItem("Wi-Fi only", "wifi")
        self._mode.addItem("Wi-Fi and mobile data (Cloudflare tunnel)", "tunnel")
        self._mode.setToolTip(
            "Wi-Fi only: guests must be on the same Wi-Fi as this PC, or on its hotspot.\n"
            "Cloudflare tunnel: a public https address leads to this PC as well —\n"
            "no account and no router setup; it changes with every start.\n"
            "Needs the free cloudflared program (asked for on the first start).")
        self._mode.setCurrentIndex(max(0, self._mode.findData(self._desk.mode())))
        self._mode.currentIndexChanged.connect(
            lambda _i: self._desk.set_mode(self._mode.currentData()))
        row.addWidget(self._mode, stretch=1)
        lyt.addLayout(row)

    def _add_inbox(self, lyt):
        """The requests waiting, and the two things the DJ can do with one."""
        lyt.addWidget(QLabel("Inbox"))
        self._inbox = QListWidget()
        self._inbox.setMinimumHeight(140)
        self._inbox.currentRowChanged.connect(lambda _r: self._sync_buttons())
        self._inbox.itemDoubleClicked.connect(lambda _i: self._on_take())
        lyt.addWidget(self._inbox, stretch=1)
        btns = QHBoxLayout()
        self._take_btn = QPushButton("⭐  To wishlist")
        self._take_btn.setToolTip("Put the requested title on the first ⭐ wishlist.")
        self._take_btn.clicked.connect(self._on_take)
        btns.addWidget(self._take_btn)
        self._drop_btn = QPushButton("✕  Dismiss")
        self._drop_btn.setToolTip("Take the request out of the inbox.")
        self._drop_btn.clicked.connect(self._on_drop)
        btns.addWidget(self._drop_btn)
        btns.addStretch(1)
        lyt.addLayout(btns)

    def _on_toggle(self):
        running = self._desk.status()["running"]
        if (not running and self._desk.mode() == "tunnel"
                and tn.find_cloudflared() is None):
            ask_cloudflared(self, self._desk, lambda: self._desk.set_running(True))
            return
        self._desk.set_running(not running)

    def _selected(self) -> dict | None:
        row = self._inbox.currentRow()
        items = self._desk.inbox
        return items[row] if 0 <= row < len(items) else None

    def _on_take(self):
        item = self._selected()
        if item is not None and item.get("entry") is not None:
            self._desk.take(item)

    def _on_drop(self):
        item = self._selected()
        if item is not None:
            self._desk.drop(item)

    def _sync_buttons(self):
        item = self._selected()
        self._take_btn.setEnabled(item is not None and item.get("entry") is not None)
        self._drop_btn.setEnabled(item is not None)

    def refresh(self):
        """Open or closed, the addresses, the code and the inbox — afresh."""
        st = self._desk.status()
        running = st["running"]
        if running:
            self._status.setText(
                (i18n.t("● Open — port %d, waiting for Cloudflare…") if st["waiting"]
                 else i18n.t("● Open — port %d")) % st["port"])
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#1565c0;")
            self._toggle_btn.setText("■  Stop")
        else:
            self._status.setText("○ Closed")
            self._status.setStyleSheet("font-weight:bold; font-size:14px; color:#666;")
            self._toggle_btn.setText("▶  Start")
        self._hint.setText(hint_text(st["mode"]))
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
        self._code.setText(i18n.t("Event code: %s") % (st["code"] or "—"))
        self._new_code_btn.setEnabled(running)
        row = self._inbox.currentRow()
        self._inbox.clear()
        for item in self._desk.inbox:
            self._inbox.addItem(QListWidgetItem(inbox_row(item)))  # i18n: data — a request
        self._inbox.setCurrentRow(min(row, self._inbox.count() - 1))
        self._sync_buttons()
        self._show_code()

    def _show_code(self):
        st = self._desk.status()
        url = self._addr.currentText()
        if not url:
            self._link.setText("No network found — is this PC on the Wi-Fi?")
            self._qr.setPixmap(QPixmap())
            self._qr.setText("")
            return
        if not st["running"]:
            self._link.setText(f'<a href="{url}">{url}</a>')  # i18n: data — a link
            self._qr.setPixmap(QPixmap())
            self._qr.setText("Press Start — the code to scan shows up here.")
            return
        if st["waiting"]:   # a new way is connecting: no old code to copy meanwhile
            self._link.setText("")
            self._qr.setPixmap(QPixmap())
            self._qr.setText("Connecting… the code to scan shows up as soon as "
                             "guests can reach the page.")
            return
        self._desk.pick_address(url)
        full = guest_qr_url(url, st["code"])
        self._link.setText(f'<a href="{full}">{url}</a>')  # i18n: data — a link
        pix = qr_pixmap(full)
        if pix is None:
            self._qr.setPixmap(QPixmap())
            self._qr.setText("No QR code: the segno package is missing. "
                             "Type the address instead.")
            return
        self._qr.setText("")
        self._qr.setPixmap(pix)
