#!/usr/bin/env python3
"""📝 loguru is the log's sink; stdlib logging calls still reach it.

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_app_logging -v

Marcel: "use loguru for logs". The app's modules log through `logging`, and so do
the libraries it uses; one root handler hands those records to loguru, which
writes the console and session.log in one format.
"""
import io
import logging
import re
import tempfile
import unittest
from pathlib import Path

from loguru import logger

from shared import app_logging


class AppLoggingTest(unittest.TestCase):

    def setUp(self):
        root = logging.getLogger()
        saved = root.handlers[:], root.level
        self.addCleanup(lambda: (root.handlers.__setitem__(slice(None), saved[0]),
                                 root.setLevel(saved[1])))
        self.addCleanup(logger.remove)
        self.console = io.StringIO()
        logger.remove()
        logger.add(self.console, format=app_logging.LOG_FORMAT, level="INFO")
        logging.basicConfig(handlers=[app_logging.InterceptHandler()],
                            level=logging.INFO, force=True)
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "session.log"

    def lines(self, stream=None):
        text = self.path.read_text(encoding="utf-8") if stream is None else stream.getvalue()
        return text.splitlines()

    def test_a_stdlib_call_reaches_the_console_with_day_time_and_level(self):
        logging.getLogger("dancesport.test").warning("🚀 the %s", "line")
        self.assertRegex(self.lines(self.console)[-1],
                         r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d W 🚀 the line$")

    def test_the_file_sink_gets_the_same_line(self):
        sink = app_logging.addFileSink(self.path)
        logging.getLogger("dancesport.test").info("the line")
        self.assertRegex(self.lines()[-1], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d I the line$")
        logger.remove(sink)

    def test_a_multi_line_message_and_braces_stay_as_written(self):
        logging.getLogger("dancesport.test").info("started\nfile: {x}\nerror: <b>%s", "y")
        self.assertEqual(self.lines(self.console)[-3:],
                         [self.lines(self.console)[-3], "file: {x}", "error: <b>y"])
        self.assertTrue(self.lines(self.console)[-3].endswith(" I started"))

    def test_an_exception_puts_its_traceback_under_the_message(self):
        try:
            raise RuntimeError("worker died")
        except RuntimeError:
            logging.getLogger("dancesport.test").exception("boom")
        text = self.console.getvalue()
        self.assertRegex(text, r" E boom\n")
        self.assertIn("RuntimeError: worker died", text)

    def test_a_record_below_the_level_is_dropped(self):
        logging.getLogger("dancesport.test").debug("quiet")
        self.assertNotIn("quiet", self.console.getvalue())

    def test_the_caller_is_the_line_that_logged(self):
        seen = []
        logger.add(lambda m: seen.append(m.record["file"].name), level="INFO")
        logging.getLogger("dancesport.test").info("where")
        self.assertEqual(seen, ["test_app_logging.py"])

    def test_setup_leaves_one_console_sink_and_the_bridge(self):
        app_logging.setupLogging()
        handlers = logging.getLogger().handlers
        self.assertEqual([type(h) for h in handlers], [app_logging.InterceptHandler])
        self.assertTrue(re.search("level.name", app_logging.LOG_FORMAT))


if __name__ == "__main__":
    unittest.main(verbosity=2)
