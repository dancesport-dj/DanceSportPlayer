#!/usr/bin/env python3
"""📝 Every line of session.log says the day, not only the time.

Run:  py -m unittest tests.app.test_session_log -v

A log looked at weeks later, or a session that ran past midnight, could not be
placed: the same time of day came twice and nothing told them apart.
"""

import logging
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_session_log_"))

import dancesport_gui
import planner.config


class SessionLogTest(unittest.TestCase):

    def open_log(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = logging.getLogger()
        before = list(root.handlers)
        self.addCleanup(self.remove_handlers, root, before)
        self.path = Path(tmp.name) / "session.log"
        with mock.patch.object(planner.config, "APP_DIR", Path(tmp.name)):
            return dancesport_gui._open_session_log()

    @staticmethod
    def remove_handlers(root, before):
        for handler in [h for h in root.handlers if h not in before]:
            root.removeHandler(handler)
            handler.close()

    def test_a_line_starts_with_day_and_time(self):
        self.open_log()
        logging.getLogger("dancesport.test").warning("the line")
        line = self.path.read_text(encoding="utf-8").splitlines()[-1]
        self.assertRegex(line, r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d W the line$")
        self.assertTrue(re.match(r"20\d\d-", line), line)


class SecondInstanceTest(unittest.TestCase):
    """#25: a second launch must not overwrite the first one's diagnostics,
    and a worker thread's uncaught exception must reach the log."""

    def test_a_second_instance_leaves_the_first_ones_logs_alone(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = logging.getLogger()
            before = list(root.handlers)
            self.addCleanup(SessionLogTest.remove_handlers, root, before)
            (Path(tmp) / "session.log").write_text("first run\n", encoding="utf-8")
            with mock.patch.object(planner.config, "APP_DIR", Path(tmp)):
                dancesport_gui._open_session_log(suffix=".second")
            self.assertEqual((Path(tmp) / "session.log").read_text(encoding="utf-8"),
                             "first run\n")
            self.assertTrue((Path(tmp) / "session.second.log").exists())

    def test_the_lock_is_held_by_one_instance_at_a_time(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with mock.patch.object(planner.config, "APP_DIR", Path(tmp)):
                first = dancesport_gui._take_instance_lock()
                self.addCleanup(first.unlock)
                second = dancesport_gui._take_instance_lock()
                self.assertTrue(first.isLocked())
                self.assertFalse(second.isLocked())

    def test_an_exception_in_a_thread_is_logged(self):
        import faulthandler
        import sys
        import threading
        saved = sys.excepthook, threading.excepthook
        self.addCleanup(lambda: (setattr(sys, "excepthook", saved[0]),
                                 setattr(threading, "excepthook", saved[1])))
        self.addCleanup(faulthandler.disable)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp, \
                mock.patch.object(planner.config, "APP_DIR", Path(tmp)):
            dancesport_gui._install_crash_log(suffix=".t")
            faulthandler.disable()      # release the file before the folder goes

            def boom():
                raise RuntimeError("worker died")
            with self.assertLogs("dancesport", level="ERROR") as cm:
                t = threading.Thread(target=boom)
                t.start()
                t.join()
        self.assertIn("worker died", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
