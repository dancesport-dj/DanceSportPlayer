"""📱 The phone remote's window: Start / Stop, the QR code that logs in, the log."""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from player.dialogs import remote_dialog
from player.dialogs.remote_dialog import RemoteDialog, qr_pixmap
from player.window.main_remote import RemoteHub
from tests.qt_test_support import reap_widget


class _Host:
    """What the window asks of the main window, and nothing more."""

    def __init__(self, running=False, urls=("http://192.168.1.20:8765",)):
        self.running = running
        self.urls = list(urls)
        self.pin = "4711"
        self.hub = RemoteHub()
        self.lines = ["12:00:00  ▶ Server started on port 8765"]
        self.switched = []
        self.mode = "wifi"
        self.public = ""
        self.waiting = False
        self.desk = mock.Mock()

    def remote_hub(self):
        return self.hub

    def remote_log(self):
        return list(self.lines)

    def remote_status(self):
        public = [self.public] if self.public else []
        return {"running": self.running, "port": 8765, "pin": self.pin,
                "mode": self.mode, "public": self.public, "waiting": self.waiting,
                "urls": public + self.urls}

    def remote_mode(self):
        return self.mode

    def set_remote_mode(self, mode):
        self.mode = mode
        self.hub.changed.emit()

    def guest_desk(self):
        return self.desk

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
        self.addCleanup(reap_widget, dlg)   # the test may delete it itself
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

    def test_the_window_picks_the_tunnel_and_the_public_address_comes_first(self):
        """Marcel: "for normal remote control also the option to use cloudflare,
        for cases where i have internet but not in same network as my pc"."""
        host = _Host(running=True)
        dlg = self._dlg(host)
        dlg._mode.setCurrentIndex(dlg._mode.findData("tunnel"))
        self.assertEqual(host.mode, "tunnel")
        self.assertIn("mobile data", dlg._hint.text())
        host.waiting = True
        host.hub.changed.emit()
        self.assertIn("Cloudflare", dlg._status.text())
        self.assertTrue(dlg._qr.pixmap().isNull())
        self.assertIn("Connecting", dlg._qr.text())
        host.waiting, host.public = False, "https://moon-river-tango-waltz.trycloudflare.com"
        with mock.patch.object(remote_dialog, "qr_pixmap",
                               wraps=remote_dialog.qr_pixmap) as qr:
            host.hub.changed.emit()
            qr.assert_called_with("https://moon-river-tango-waltz.trycloudflare.com/#pin=4711")
        self.assertEqual(dlg._addr.currentText(), "https://moon-river-tango-waltz.trycloudflare.com")

    def test_without_cloudflared_the_window_offers_the_download(self):
        host = _Host()
        host.mode = "tunnel"
        dlg = self._dlg(host)
        box = remote_dialog.QMessageBox
        with mock.patch.object(remote_dialog.tn, "find_cloudflared", return_value=None), \
                mock.patch.object(box, "question", return_value=box.StandardButton.Yes), \
                mock.patch.object(remote_dialog, "QProgressDialog"):
            dlg._toggle_btn.click()
        self.assertEqual(host.switched, [])
        host.desk.fetch_cloudflared.assert_called_once()
        done = host.desk.fetch_done.connect.call_args.args[0]
        done("C:/cloudflared.exe", "")
        self.assertEqual(host.switched, [True])

    def test_a_failed_download_says_how_to_install_it_by_hand(self):
        host = _Host()
        host.mode = "tunnel"
        dlg = self._dlg(host)
        box = remote_dialog.QMessageBox
        with mock.patch.object(remote_dialog.tn, "find_cloudflared", return_value=None), \
                mock.patch.object(box, "question", return_value=box.StandardButton.Yes), \
                mock.patch.object(remote_dialog, "QProgressDialog"):
            dlg._toggle_btn.click()
        done = host.desk.fetch_done.connect.call_args.args[0]
        for system, asset, step in (("darwin", "cloudflared-darwin-arm64.tgz", "brew install"),
                                    ("linux", "cloudflared-linux-amd64", "chmod +x"),
                                    ("win32", "cloudflared-windows-amd64.exe", "")):
            with self.subTest(system), mock.patch.object(remote_dialog.sys, "platform", system), \
                    mock.patch.object(remote_dialog.tn, "asset_name", return_value=asset), \
                    mock.patch.object(box, "exec") as shown:
                done("", "<urlopen error certificate verify failed>")
                shown.assert_called_once()
                msg = dlg.findChildren(box)[-1]
                text = msg.text()
                self.assertEqual(msg.textFormat(), remote_dialog.Qt.TextFormat.RichText)
                self.assertIn("&lt;urlopen error certificate verify failed&gt;", text)
                self.assertIn(f'href="{remote_dialog.CLOUDFLARED_PAGE}"', text)
                self.assertIn(asset, text)
                self.assertIn(str(remote_dialog.config.APP_DIR), text)
                self.assertIn(step, text)
                msg.deleteLater()
        self.assertEqual(host.switched, [])

    def test_a_download_that_lands_after_the_window_closed_does_not_raise(self):
        """BUG 172: the progress dialog is the window's child, so closing the
        window — ⚙ Settings' ✕, with the 📱 window opened on top of it — takes
        it along. The download runs on in its thread and, coming back, closed
        the dialog that is gone: "Internal C++ object (QProgressDialog) already
        deleted"."""
        import shiboken6

        host = _Host()
        host.mode = "tunnel"
        dlg = self._dlg(host)
        box = remote_dialog.QMessageBox
        with mock.patch.object(remote_dialog.tn, "find_cloudflared", return_value=None), \
                mock.patch.object(box, "question", return_value=box.StandardButton.Yes), \
                mock.patch.object(box, "exec"):
            dlg._toggle_btn.click()
        done = host.desk.fetch_done.connect.call_args.args[0]
        shiboken6.delete(dlg)           # the window goes while the bytes still come in
        done("", "connection reset")    # was: RuntimeError out of busy.close()
        done("C:/cloudflared.exe", "")
        self.assertEqual(host.switched, [True])   # the Start he asked for still lands

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
