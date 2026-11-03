"""🎨 make_iconset checks its argument before it downloads anything (#69)."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class IconsetArgsTest(unittest.TestCase):

    def test_no_output_path_exits_with_a_usage_line_and_no_traceback(self):
        run = subprocess.run([sys.executable, "-m", "tools.assets.make_iconset"],
                             cwd=ROOT, capture_output=True, timeout=30)
        err = run.stderr.decode("utf-8", "replace")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("usage", err.lower())
        self.assertNotIn("IndexError", err)


if __name__ == "__main__":
    unittest.main()
