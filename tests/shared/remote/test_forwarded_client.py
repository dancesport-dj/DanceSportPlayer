#!/usr/bin/env python3
"""Who is asking, behind the tunnel: `CF-Connecting-IP`, parsed as an address.

Run:  py -m unittest tests.shared.remote.test_forwarded_client -v

The header is only believed from a loopback peer while a tunnel is up, but what
it said was handed on as text (cut at 64 characters). The per-address lockout
and the guest budgets key on it, so a value that is no address - or one address
written two ways - must not become a key of its own.
"""

import unittest

from shared.remote.remote_server import forwarded_client


def _who(forwarded, peer="127.0.0.1", tunnel="x.trycloudflare.com"):
    return forwarded_client(peer, {"CF-Connecting-IP": forwarded}, tunnel)


class ForwardedClientTest(unittest.TestCase):

    def test_a_phones_address_is_taken_from_the_header(self):
        self.assertEqual(_who("203.0.113.7"), "203.0.113.7")

    def test_a_value_that_is_no_address_is_not_a_key(self):
        self.assertEqual(_who("not an address"), "127.0.0.1")
        self.assertEqual(_who("a" * 200), "127.0.0.1")

    def test_one_address_written_two_ways_is_one_key(self):
        self.assertEqual(_who("2001:DB8::1"), _who("2001:0db8:0:0:0:0:0:1"))

    def test_the_header_is_not_believed_without_a_tunnel(self):
        self.assertEqual(_who("203.0.113.7", tunnel=""), "127.0.0.1")

    def test_the_header_is_not_believed_from_a_lan_peer(self):
        self.assertEqual(_who("203.0.113.7", peer="192.168.1.20"), "192.168.1.20")


if __name__ == "__main__":
    unittest.main()
