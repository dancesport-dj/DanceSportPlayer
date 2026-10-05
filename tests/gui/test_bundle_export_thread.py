#!/usr/bin/env python3
"""The 🧳 USB export copies off the GUI thread.

Run:  py -m unittest tests.gui.test_bundle_export_thread -v

A venue bundle copies every track of every playlist to a USB stick. The copy
ran on the GUI thread with a `processEvents` per track, so the window froze
for as long as each single copy took — seconds per file on a slow stick.
Cancel must still stop it and remove the half-written bundle.
"""

import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from gui import main_export
from gui.main_export import ExportMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class _FakeBusy(QObject):
    cancel_requested = Signal()
    last = None

    def __init__(self, parent=None, message="", cancelable=False):
        super().__init__()
        _FakeBusy.last = self

    def show_after(self, ms=500):
        pass

    def set_message(self, msg):
        pass

    def set_progress(self, *args):
        pass

    def finish(self):
        pass


class BundleExportThreadTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_bundle_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.tracks = []
        for name in ("one", "two"):
            t = self.dir / f"{name} (LW 29).mp3"
            t.write_bytes(b"audio")
            self.tracks.append(t)
        self.bundle = self.dir / "Turnier"
        self.bundle.mkdir()
        self.host = QMainWindow()
        self.addCleanup(reap_widget, self.host)
        self.on_main = []
        self.gate = None
        no_box = mock.patch.object(QMessageBox, "exec", return_value=0)
        no_box.start()
        self.addCleanup(no_box.stop)

    def _write(self, out: Path) -> Path:
        self.on_main.append(threading.current_thread() is threading.main_thread())
        body = "".join(f"#EXTINF:1,{t.stem}\n{t}\n" for t in self.tracks)
        out.write_text("#EXTM3U\n" + body, encoding="utf-8")
        if self.gate is not None:
            self.gate.wait(2)
        return out

    def test_the_copy_runs_off_the_gui_thread(self):
        ExportMixin._write_bundle(self.host, self.bundle, [("Final", self._write)], [])
        self.assertEqual(self.on_main, [False])
        self.assertEqual(len(list((self.bundle / "Final").glob("*.mp3"))), 2)

    def test_cancel_removes_the_half_written_bundle(self):
        self.gate = threading.Event()

        def cancel():
            _FakeBusy.last.cancel_requested.emit()
            self.gate.set()

        QTimer.singleShot(50, cancel)
        with mock.patch.object(main_export, "BusyDialog", _FakeBusy):
            ExportMixin._write_bundle(self.host, self.bundle,
                                      [("Final", self._write), ("Rest", self._write)], [])
        self.assertFalse(self.bundle.exists())
        self.assertEqual(len(self.on_main), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
