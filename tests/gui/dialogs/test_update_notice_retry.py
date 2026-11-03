"""🔔 The update notice's wait for the main window (#48)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_update_notice_"))

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget

from gui.dialogs import update_notice


class RetryTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.005)

    def test_the_retry_ends_with_the_window(self):
        window = QWidget()       # never shown, like a start that is closed during loading
        notice = update_notice.UpdateNotice(window)
        errors = []
        old_hook = sys.excepthook
        sys.excepthook = lambda *a: errors.append(a[1])
        self.addCleanup(setattr, sys, "excepthook", old_hook)
        with mock.patch.object(update_notice, "_WAIT_FOR_WINDOW_MS", 20):
            notice.show_notice("9.9", "https://example.invalid")
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.pump(0.2)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
