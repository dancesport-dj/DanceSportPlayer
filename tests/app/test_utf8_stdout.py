"""Every module that switches stdout to UTF-8 must leave it usable for the next one.

Four places do it: the GUI launcher, the planner facade, a test module and a tool.
Replacing `sys.stdout` with a fresh `TextIOWrapper` twice orphans the first
wrapper, and when it is collected it closes the buffer the second one writes to:
the next `print()` raises "I/O operation on closed file". Importing all four in
one process on a cp1252 console is exactly what a test discovery run does.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Utf8StdoutTest(unittest.TestCase):

    def test_stdout_survives_every_utf8_switch(self):
        code = ("import gc, dancesport_gui, dancesport_planner, "
                "tests.planner.test_senorita_similarity, tools.find_missing_metadata\n"
                "gc.collect()\n"
                "print('still writable ✓')\n")
        env = dict(os.environ, PYTHONIOENCODING="cp1252", QT_QPA_PLATFORM="offscreen")
        run = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                             capture_output=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stderr.decode("utf-8", "replace")[-2000:])
        self.assertIn("still writable ✓", run.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
