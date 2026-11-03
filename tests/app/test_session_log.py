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


if __name__ == "__main__":
    unittest.main(verbosity=2)
