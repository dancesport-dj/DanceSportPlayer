#!/usr/bin/env python3
"""A test's wait lets the other threads run, as the app's event loop does.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_qwait_releases_gil -v

PySide's QTest.qWait pumps events while still holding the GIL; the app's
exec() lets go of it. A Qt media thread that has to touch a Python wrapper
(shiboken's override lookup when it destroys one) then waits for the GIL
while the main thread, inside qWait, waits for that media thread: the
click-through of Played titles hung there every time once ffmpeg was found.
"""

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


class QWaitReleasesGilTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_another_thread_runs_during_the_wait(self):
        woke = []
        t = threading.Thread(target=lambda: (time.sleep(0.02), woke.append(time.monotonic())))
        start = time.monotonic()
        t.start()
        QTest.qWait(400)
        t.join()
        self.assertLess(woke[0] - start, 0.3,
                        "the thread only got the GIL back once the wait was over")

    def test_the_wait_still_runs_timers_and_deferred_deletes(self):
        fired, gone = [], []
        QTimer.singleShot(10, lambda: fired.append(True))
        obj = QObject()
        obj.destroyed.connect(lambda: gone.append(True))
        obj.deleteLater()
        QTest.qWait(50)
        self.assertEqual(fired, [True])
        self.assertEqual(gone, [True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
