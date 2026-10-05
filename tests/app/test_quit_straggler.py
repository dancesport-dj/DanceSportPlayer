#!/usr/bin/env python3
"""Quitting while a worker won't stop must not abort the process.

Run:  py -m unittest tests.app.test_quit_straggler -v

`_stop_workers` cancels what can be cancelled and waits 5 s per worker. Most
worker classes have no cancel at all, and some steps can't be cut even with
one (an HTTP request on the wire, a VACUUM, one OpenL3 inference) — so a
worker can still be running when the window goes. Qt aborts the process
outright (0xC0000409, no traceback) when a running QThread is destroyed,
which is what the window takes its children down with.

Run in a child process: the failure being tested kills whoever runs it.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import os, sys, threading
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QWidget
import shiboken6
import dancesport_gui as dg

app = QApplication([])
release = threading.Event()

class Stubborn(QThread):
    # No cancel, and a wait that gives up at once: the 5 s the real wait
    # allows, used up without the worker stopping.
    def run(self):
        release.wait(3)

    def wait(self, ms=0):
        return super().wait(10)

win = QWidget()
worker = Stubborn(win)
worker.start()
dg.MainWindow._stop_workers(win)
shiboken6.delete(win)            # the window going, children and all
print("window gone", flush=True)
dg.exit_app(0)                   # how run_gui leaves once app.exec() returns
"""


class QuitStragglerTest(unittest.TestCase):

    def test_a_worker_that_will_not_stop_does_not_abort_the_quit(self):
        env = dict(os.environ, PYTHONPATH=str(_ROOT), PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=_ROOT, env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=60)
        self.assertIn("window gone", proc.stdout, proc.stderr[-2000:])
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
