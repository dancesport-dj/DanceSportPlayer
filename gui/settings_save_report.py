"""💾 Tells the user when the settings could not be saved.

shared.stores.save_settings calls the hook installed here when its write
fails (a full disk, a read-only folder, a Dropbox lock). The window's status
bar says so every time, a box once a session: the settings are saved on
every slider move, and one box is enough to send the user to the disk.

The box is queued, never shown inside the click or slider that was saving,
and a save from a worker thread arrives on the window's thread too.
"""
import contextlib
import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from planner import i18n
from shared import stores

log = logging.getLogger(__name__)

_STATUS_MS = 15000


class _Reporter(QObject):
    failed = Signal()

    def __init__(self, window):
        super().__init__(window)
        self.setObjectName("settingsSaveReport")
        self._window = window
        self._told = False      # the box came this session
        self.failed.connect(self._tell, Qt.ConnectionType.QueuedConnection)

    def _tell(self):
        self._window.statusBar().showMessage(
            i18n.t("⚠️ The settings could not be saved — is the settings folder "
                   "writable and the disk not full?"), _STATUS_MS)
        if self._told:
            return
        self._told = True
        log.warning("💾 Settings not saved: the user is told\n"
                    "file: %s", stores.SETTINGS.path)
        QMessageBox.warning(
            QApplication.activeModalWidget() or self._window, i18n.t("⚙  Settings"),
            i18n.t("The settings could not be saved.\n\n"
                   "They apply until the app is closed. Is the settings "
                   "folder writable and the disk not full?")
            + f"\n\n{stores.SETTINGS.path}")   # i18n: data — the file's path


def install_report(window) -> None:
    """Hang the report on `window`, found by its name so the window keeps no
    attribute for it. A second call on the same window reuses it."""
    reporter = window.findChild(_Reporter, "settingsSaveReport")
    if reporter is None:
        reporter = _Reporter(window)

    def hook():
        with contextlib.suppress(RuntimeError):   # the window is gone: nobody left to tell
            reporter.failed.emit()

    stores.report_settings_failures(hook)
