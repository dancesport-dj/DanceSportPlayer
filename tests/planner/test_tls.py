"""🔒 The one TLS setup every HTTPS request of the app goes through.

Run:  py -m unittest tests.planner.test_tls -v
"""
import ssl
import sys
import unittest
from unittest import mock

import certifi

from planner import tls


def has_certifi_roots(ctx) -> bool:
    """Whether `ctx` trusts every root certifi ships."""
    roots = {c["serialNumber"] for c in ctx.get_ca_certs()}
    bundled = ssl.create_default_context(cafile=certifi.where()).get_ca_certs()
    return bool(bundled) and {c["serialNumber"] for c in bundled} <= roots


class TlsContextTest(unittest.TestCase):
    def test_certifi_roots_come_along_with_the_systems(self):
        """A Mac's Python has no CA file of its own: without certifi every
        HTTPS request failed with "certificate verify failed"."""
        ctx = tls.tls_context()
        self.assertIsInstance(ctx, ssl.SSLContext)
        self.assertTrue(has_certifi_roots(ctx))

    def test_a_build_without_ssl_gets_none(self):
        """A player build without error reports drops the ssl module
        (dancesport.spec): no context then, and nothing raises."""
        with mock.patch.dict(sys.modules, {"ssl": None}):
            self.assertIsNone(tls.tls_context())


if __name__ == "__main__":
    unittest.main()
