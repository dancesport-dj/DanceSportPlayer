#!/usr/bin/env python3
"""Closing a window whose worker still runs must not abort the process.

Run:  py -m unittest tests.app.test_orphan_workers -v

Qt aborts the process outright (0xC0000409, no traceback) when a running
QThread is destroyed. Two windows let that happen:

- A Similar-tracks window deletes itself on close, and its rank / index /
  drop workers are its children — closing it mid-rank took them down with it.
- The duplicate dialog's reference compare has no parent; only the dialog
  holds it. The dialog lives on as a child of the main window after `exec()`
  returns, and when the main window goes at quit, the compare goes with it —
  unseen by `_stop_workers`, which only finds children.

Run in a child process: the failure being tested kills whoever runs it.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

_PRELUDE = r"""
import gc, os, sys, threading, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QEvent, QThread, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget
import shiboken6
import dancesport_gui as dg

app = QApplication([])
release = threading.Event()

class Slow(QThread):
    progress = Signal(int, int)
    done = Signal(dict)
    failed = Signal(str)

    def run(self):
        release.wait(3)
"""

_SIMILAR = _PRELUDE + r"""
from gui.similar_dialog import SimilarTracksDialog
from planner.models import MusicEntry

def entry(title):
    return MusicEntry(path=Path(rf"C:\m\{title} (LW 29).mp3"), title=title,
                      dance="LW", bpm=29)

host = QWidget()
dlg = SimilarTracksDialog(entry("s"), [(0.9, entry("a"))], host)
dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
dlg.show()
dlg._rank_worker = Slow(dlg)     # a rank still running, parented like the real one
dlg._rank_worker.start()
dlg.close()                      # the user closes the window mid-rank
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print("window closed", flush=True)
release.set()
time.sleep(0.3)
dg.exit_app(0)
"""

_DUPLICATES = _PRELUDE + r"""
from gui.duplicate_dialog import DuplicateResolveDialog

win = QWidget()

def check_duplicates():
    # How main_dupes runs it: a local dialog, exec()'d, closed mid-compare.
    dlg = DuplicateResolveDialog({"within": [], "cross": []}, win, lambda e: None,
                                 ref_clean_factory=lambda ref, tour: Slow())
    dlg._ref_path = "ref.m3u"
    dlg._ref_tour_files.add_paths(["t.m3u"])
    dlg._on_ref_compare()
    dlg.reject()

check_duplicates()
dg.MainWindow._stop_workers(win)
shiboken6.delete(win)            # the main window going at quit, children and all
gc.collect()
print("window gone", flush=True)
dg.exit_app(0)
"""


class OrphanWorkerTest(unittest.TestCase):

    def _run(self, script: str):
        env = dict(os.environ, PYTHONPATH=str(_ROOT), PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, "-c", script], cwd=_ROOT, env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=60)

    def test_closing_a_similar_window_mid_rank(self):
        proc = self._run(_SIMILAR)
        self.assertIn("window closed", proc.stdout, proc.stderr[-2000:])
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])

    def test_quitting_after_a_duplicate_check_closed_mid_compare(self):
        proc = self._run(_DUPLICATES)
        self.assertIn("window gone", proc.stdout, proc.stderr[-2000:])
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
