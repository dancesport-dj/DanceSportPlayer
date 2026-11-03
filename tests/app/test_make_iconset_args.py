"""🎨 make_iconset checks its argument before it downloads anything (#69)."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


class IconsetArgsTest(unittest.TestCase):

    def test_no_output_path_exits_with_a_usage_line_and_no_traceback(self):
        run = subprocess.run([sys.executable, "-m", "tools.assets.make_iconset"],
                             cwd=ROOT, capture_output=True, timeout=30)
        err = run.stderr.decode("utf-8", "replace")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("usage", err.lower())
        self.assertNotIn("IndexError", err)


class IconsetCertsTest(unittest.TestCase):

    def test_the_download_uses_the_os_certificate_store(self):
        """#88: behind a TLS-intercepting proxy every icon failed with
        CERTIFICATE_VERIFY_FAILED."""
        from tools.assets import make_iconset
        fake = mock.Mock()
        with mock.patch.dict(sys.modules, {"truststore": fake}):
            make_iconset.useOsCerts()
        fake.inject_into_ssl.assert_called_once_with()

    def test_without_truststore_it_carries_on(self):
        from tools.assets import make_iconset
        with mock.patch.dict(sys.modules, {"truststore": None}):
            make_iconset.useOsCerts()


if __name__ == "__main__":
    unittest.main()
