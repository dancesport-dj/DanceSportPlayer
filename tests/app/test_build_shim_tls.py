#!/usr/bin/env python3
"""The build shim does not switch off certificate checks by being on the path.

Run:  py -m unittest tests.app.test_build_shim_tls -v

`_build_shims/sitecustomize.py` relaxes the stdlib HTTPS context for the one
openl3 install that downloads its weights through a TLS-intercepting proxy.
Python imports a sitecustomize from anywhere on sys.path, so a shell that kept
`PYTHONPATH=_build_shims` after that install ran every later Python from it —
the app's OpenRouter calls included — with no certificate check at all. It now
does that only when the build asks for it by name.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = "import ssl; print(ssl._create_default_https_context.__name__)"


def _context(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "DANCEPLAYLIST_INSECURE_BUILD_TLS")}
    env["PYTHONPATH"] = str(ROOT / "_build_shims")
    env.update(extra)
    out = subprocess.run([sys.executable, "-c", PROBE], env=env, cwd=ROOT,
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip(), out.stderr


class BuildShimTlsTest(unittest.TestCase):

    def test_on_the_path_alone_it_keeps_verification_on(self):
        name, _err = _context()
        self.assertEqual(name, "create_default_context")

    def test_the_build_can_still_ask_for_it(self):
        name, err = _context(DANCEPLAYLIST_INSECURE_BUILD_TLS="1")
        self.assertEqual(name, "_create_unverified_context")
        self.assertIn("certificate", err.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
