#!/usr/bin/env python3
"""Leaving after the event loop skips the interpreter's teardown.

Run:  py -m unittest tests.app.test_quit_fast -v

Every save runs in `closeEvent`. What a plain `sys.exit` adds after that is
Python and Qt taking every object apart one by one: measured at 1.0-1.2 s of
each quit, against ~0.2 s for leaving at once. The log must still reach its
file, and the exit code must still reach the caller.

Run in a child process: the exit being tested ends whoever runs it.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import atexit, logging, os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import dancesport_gui as dg

handler = logging.FileHandler(sys.argv[1], encoding="utf-8")
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("quit").info("last line before the exit")
atexit.register(lambda: print("teardown ran", flush=True))
dg.exit_app(3)
"""

# A windowed build (PyInstaller console=False) has no console: both streams are None.
_WINDOWED_SCRIPT = r"""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import dancesport_gui as dg

sys.stdout = sys.stderr = None
dg.exit_app(4)
"""


class QuitFastTest(unittest.TestCase):

    def test_exit_skips_teardown_but_keeps_log_and_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "session.log"
            env = dict(os.environ, PYTHONPATH=str(_ROOT), PYTHONIOENCODING="utf-8")
            proc = subprocess.run([sys.executable, "-c", _SCRIPT, str(log_path)],
                                  cwd=_ROOT, env=env, capture_output=True, text=True,
                                  encoding="utf-8", timeout=60)
            self.assertEqual(proc.returncode, 3, proc.stderr[-2000:])
            self.assertNotIn("teardown ran", proc.stdout)
            self.assertIn("last line before the exit",
                          log_path.read_text(encoding="utf-8"))

    def test_exit_without_a_console(self):
        env = dict(os.environ, PYTHONPATH=str(_ROOT), PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, "-c", _WINDOWED_SCRIPT],
                              cwd=_ROOT, env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        self.assertEqual(proc.returncode, 4, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
