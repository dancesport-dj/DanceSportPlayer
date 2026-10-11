"""📱 The phone remote's window: Start / Stop, the QR code that logs in, the log."""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from player import remote_dialog
from player.main_remote import _RemoteHub
from player.remote_dialog import RemoteDialog, qr_pixmap


class _Host:
    """What the window asks of the main window, and nothing more."""

    def __init__(self, running=False, urls=("http://192.168.1.20:8765",)):
        self.running = running
        self.urls = list(urls)
        self.pin = "4711"
        self.hub = _RemoteHub()
        self.lines = ["12:00:00  ▶ Server started on port 8765"]
        self.switched = []

    def remote_hub(self):
        return self.hub

    def remote_log(self):
        return list(self.lines)

    def remote_status(self):
        return {"running": self.running, "port": 8765, "pin": self.pin, "urls": self.urls}

    def set_remote_running(self, on):
        self.switched.append(on)
        self.running = on
        self.hub.changed.emit()

    def new_remote_pin(self):
        self.pin = "0815"
        self.hub.changed.emit()


class RemoteDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, host):
        dlg = RemoteDialog(host)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_start_and_stop_go_to_the_host_and_the_code_follows(self):
        host = _Host()
        dlg = self._dlg(host)
        self.assertIn("Stopped", dlg._status.text())
        self.assertTrue(dlg._qr.pixmap().isNull())
        self.assertFalse(dlg._new_pin_btn.isEnabled())
        dlg._toggle_btn.click()
        self.assertEqual(host.switched, [True])
        self.assertIn("port 8765", dlg._status.text())
        self.assertFalse(dlg._qr.pixmap().isNull())
        self.assertIn("Stop", dlg._toggle_btn.text())
        dlg._toggle_btn.click()
        self.assertEqual(host.switched, [True, False])
        self.assertTrue(dlg._qr.pixmap().isNull())

    def test_the_code_holds_the_address_with_the_pin(self):
        host = _Host(running=True)
        with mock.patch.object(remote_dialog, "qr_pixmap",
                               wraps=remote_dialog.qr_pixmap) as qr:
            dlg = self._dlg(host)
            qr.assert_called_with("http://192.168.1.20:8765/#pin=4711")
            dlg._new_pin_btn.click()
            qr.assert_called_with("http://192.168.1.20:8765/#pin=0815")
        self.assertIn("0815", dlg._pin.text())

    def test_more_than_one_network_offers_a_choice(self):
        host = _Host(running=True, urls=["http://192.168.1.20:8765",
                                         "http://172.24.112.1:8765"])
        dlg = self._dlg(host)
        self.assertFalse(dlg._addr.isHidden())
        with mock.patch.object(remote_dialog, "qr_pixmap",
                               wraps=remote_dialog.qr_pixmap) as qr:
            dlg._addr.setCurrentIndex(1)
            qr.assert_called_with("http://172.24.112.1:8765/#pin=4711")
        self.assertTrue(self._dlg(_Host())._addr.isHidden())

    def test_the_log_shows_what_came_before_and_what_comes_now(self):
        host = _Host()
        dlg = self._dlg(host)
        host.hub.line.emit("12:00:05  192.168.1.33 opened the page")
        text = dlg._log.toPlainText()
        self.assertIn("Server started on port 8765", text)
        self.assertIn("192.168.1.33 opened the page", text)

    def test_without_segno_the_address_is_enough(self):
        host = _Host(running=True)
        with mock.patch.object(remote_dialog, "qr_pixmap", return_value=None):
            dlg = self._dlg(host)
        self.assertTrue(dlg._qr.pixmap().isNull())
        self.assertIn("segno", dlg._qr.text())
        self.assertIn("http://192.168.1.20:8765", dlg._link.text())

    def test_the_firewall_hint_names_the_program_that_listens(self):
        with mock.patch.object(remote_dialog, "server_program",
                               return_value=r"C:\Python\python.exe"):
            dlg = self._dlg(_Host())
        self.assertIn(r"C:\Python\python.exe", dlg._hint.text())

    def test_a_qr_code_is_square_whole_pixels_and_white_round_the_edge(self):
        pix = qr_pixmap("http://192.168.1.20:8765/#pin=4711", 220)
        self.assertIsNotNone(pix)
        self.assertEqual(pix.width(), pix.height())
        img = pix.toImage()
        self.assertEqual(img.pixelColor(0, 0).name(), "#ffffff")
        modules = 29 + 2 * 4                 # version 3 plus the quiet zone
        self.assertEqual(pix.width() % modules, 0)


if __name__ == "__main__":
    unittest.main()
