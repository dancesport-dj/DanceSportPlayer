#!/usr/bin/env python3
"""The monkey's sandbox holds: a random click cannot reach the network or
open a port on the LAN, whichever client or server the app uses for it.

The walks never look at this (a request that got out leaves no trace in the
test), so it is checked here, with the sandbox of tests/gui/monkey_support.py
up and no window built.
"""

import socket
import unittest
import urllib.error
import urllib.request

from tests.gui.monkey_support import LoadedWindow


class SandboxTest(LoadedWindow):

    def setUp(self):
        pass                # the sandbox is up for the class; no window needed

    def test_the_guest_requests_server_cannot_bind(self):
        from shared.remote.guest_server import GuestServer
        server = GuestServer(lambda _request: None, port=0)
        with self.assertRaises(OSError):
            server.start()
        server.stop()

    def test_an_opener_of_its_own_finds_the_network_down(self):
        # planner/generate/ai.py builds one, past the patched urlopen.
        opener = urllib.request.build_opener()
        with self.assertRaises(urllib.error.URLError) as caught:
            opener.open("http://192.0.2.1/", timeout=1)
        self.assertIn("monkey test", str(caught.exception))

    def test_no_socket_reaches_past_this_machine(self):
        # httpx (the model downloads) and the tunnel's DNS probe come down
        # to these.
        with socket.socket() as s:
            s.settimeout(1)
            with self.assertRaisesRegex(OSError, "monkey test"):
                s.connect(("192.0.2.1", 80))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            with self.assertRaisesRegex(OSError, "monkey test"):
                s.sendto(b"x", ("192.0.2.1", 53))
        with socket.socket() as s:
            with self.assertRaisesRegex(OSError, "monkey test"):
                s.bind(("0.0.0.0", 0))

    def test_loopback_still_works(self):
        """Qt and asyncio talk to themselves over loopback sockets."""
        a, b = socket.socketpair()
        with a, b:
            a.sendall(b"x")
            self.assertEqual(b.recv(1), b"x")


if __name__ == "__main__":
    unittest.main()
