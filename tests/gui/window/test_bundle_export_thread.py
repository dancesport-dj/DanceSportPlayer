#!/usr/bin/env python3
"""The 🧳 USB export copies off the GUI thread.

Run:  py -m unittest tests.gui.window.test_bundle_export_thread -v

A venue bundle copies every track of every playlist to a USB stick. The copy
ran on the GUI thread with a `processEvents` per track, so the window froze
for as long as each single copy took — seconds per file on a slow stick.
Cancel must still stop it and remove the half-written bundle. The progress
runs over the whole bundle with the time left, the M3U Copy Tool's estimate:
elapsed / tracks done * tracks left.
"""

import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from gui.window import main_export
from gui.window.main_export import ExportMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class _FakeBusy(QObject):
    cancel_requested = Signal()
    last = None

    def __init__(self, parent=None, message="", cancelable=False):
        super().__init__()
        self.progress = []
        _FakeBusy.last = self

    def show_after(self, ms=500):
        pass

    def set_message(self, msg):
        pass

    def set_progress(self, *args):
        self.progress.append(args)

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
        self.writing = threading.Event()
        no_box = mock.patch.object(QMessageBox, "exec", return_value=0)
        no_box.start()
        self.addCleanup(no_box.stop)

    def _write(self, out: Path) -> Path:
        self.on_main.append(threading.current_thread() is threading.main_thread())
        self.writing.set()
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
            # Only once the first playlist is being written: on a loaded
            # machine the thread may not have started after a fixed delay.
            if not self.writing.is_set():
                QTimer.singleShot(10, cancel)
                return
            _FakeBusy.last.cancel_requested.emit()
            self.gate.set()

        QTimer.singleShot(50, cancel)
        with mock.patch.object(main_export, "BusyDialog", _FakeBusy):
            ExportMixin._write_bundle(self.host, self.bundle,
                                      [("Final", self._write), ("Rest", self._write)], [])
        self.assertFalse(self.bundle.exists())
        self.assertEqual(len(self.on_main), 1)

    def test_progress_spans_the_bundle_with_the_time_left(self):
        # Every copy takes 10 s on this clock: the first reading starts the
        # count, the one before each track is the time spent so far.
        ticks = iter([0, 0, 10, 20, 30])
        clock = SimpleNamespace(monotonic=lambda: next(ticks))
        with mock.patch.object(main_export, "BusyDialog", _FakeBusy),                 mock.patch.object(main_export, "time", clock):
            ExportMixin._write_bundle(self.host, self.bundle,
                                      [("Final", self._write), ("Rest", self._write)], [])
        got = [(done, total, eta) for done, total, _name, eta in _FakeBusy.last.progress]
        self.assertEqual(got, [(1, 4, -1.0), (2, 4, 30.0), (3, 4, 20.0), (4, 4, 10.0)])
        self.assertEqual(len(list((self.bundle / "Rest").glob("*.mp3"))), 2)

    def test_the_time_left_weighs_the_bytes_of_the_whole_transfer(self):
        # F15: one MB, then three. After the first, 10 s for 1 MB leaves
        # 30 s for the other 3 MB of the transfer, not 10 s for one track.
        self.tracks[0].write_bytes(b"a" * 1_000_000)
        self.tracks[1].write_bytes(b"a" * 3_000_000)
        ticks = iter([0, 0, 10])
        clock = SimpleNamespace(monotonic=lambda: next(ticks))
        with mock.patch.object(main_export, "BusyDialog", _FakeBusy), \
                mock.patch.object(main_export, "time", clock):
            ExportMixin._write_bundle(self.host, self.bundle, [("Final", self._write)], [])
        got = [(done, total, eta) for done, total, _name, eta in _FakeBusy.last.progress]
        self.assertEqual(got, [(1, 2, -1.0), (2, 2, 30.0)])
        detail = _FakeBusy.last.progress[1][2]
        self.assertTrue(detail.startswith("1 / 4 MB · "), detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
