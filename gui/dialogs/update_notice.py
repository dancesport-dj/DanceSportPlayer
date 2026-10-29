"""🔔 The notice a newer release gets, once — see shared/update_check.py.

The check runs on a plain thread; the find crosses to the GUI thread by the
signal here, and waits until the main window is on screen (the library may
still be loading) so the notice is not the first thing a start shows.
"""
import logging

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from gui.dialogs import load_settings, save_settings
from planner import i18n
from planner.version import app_version
from shared import update_check

log = logging.getLogger("dancesport.update")

_WAIT_FOR_WINDOW_MS = 1000


class UpdateNotice(QObject):
    found = Signal(str, str)     # version, release page

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self.found.connect(self.show_notice)

    def start(self, settings: dict) -> None:
        update_check.check_in_background(settings, self.found.emit)

    def show_notice(self, version: str, url: str) -> None:
        if not self._window.isVisible():
            QTimer.singleShot(_WAIT_FOR_WINDOW_MS,
                              lambda: self.show_notice(version, url))
            return
        self._mark_seen(version)
        log.info("🔔 New version announced\n"
                 "version: %s", version)
        box = QMessageBox(self._window)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.setWindowTitle("New version")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(i18n.t("Version %s is out.") % version)
        box.setInformativeText(
            i18n.t("You are running %s. The download page lists what "
                   "changed.") % app_version())
        open_btn = box.addButton("Open download page",
                                 QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.buttonClicked.connect(
            lambda btn: QDesktopServices.openUrl(QUrl(url))
            if btn is open_btn else None)
        box.open()      # not exec(): the desk keeps running behind it

    def _mark_seen(self, version: str) -> None:
        """Announced once: kept in the window's own settings too, which it
        saves whole and would otherwise write back without it."""
        settings = getattr(self._window, "_settings", None)
        if settings is None:
            settings = load_settings()
        settings[update_check.SEEN_SETTING] = version
        save_settings(settings)
