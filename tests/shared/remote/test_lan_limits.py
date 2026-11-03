"""🛡 The LAN servers' connection limits (review #19): a stranger who trickles
the request line, or opens many sockets from one address, must not be able to
hold every thread."""
import socket
import time
import unittest
from unittest import mock

from shared.remote import guest_server as gs
from shared.remote import remote_server as rs


def _servers():
    remote = rs.RemoteServer(on_command=lambda *a, **k: None, host="127.0.0.1",
                             port=0, pin="1234")
    guests = gs.GuestServer(on_request=lambda r: None, host="127.0.0.1", port=0,
                            labels={}, code="ABC234")
    return (("remote", remote), ("guests", guests))


class HeaderDeadlineTest(unittest.TestCase):

    def test_a_trickled_request_line_is_cut_off_at_a_total_deadline(self):
        for name, srv in _servers():
            with self.subTest(server=name):
                with mock.patch.object(rs, "HEADER_TOTAL_SECS", 0.4):
                    srv.start()
                    self.addCleanup(srv.stop)
                    s = socket.create_connection(("127.0.0.1", srv.port), timeout=3)
                    self.addCleanup(s.close)
                    started = time.monotonic()
                    try:
                        # A byte now and then keeps each single read alive.
                        for ch in b"GET / HT":
                            s.sendall(bytes([ch]))
                            time.sleep(0.15)
                    except OSError:
                        pass            # already cut off: the point
                    try:
                        closed = s.recv(10) == b""
                    except OSError:
                        closed = True
                    self.assertTrue(closed)
                    self.assertLess(time.monotonic() - started, 2.5)


class PerAddressCapTest(unittest.TestCase):

    def test_one_address_cannot_take_every_slot(self):
        for name, srv in _servers():
            with self.subTest(server=name):
                with mock.patch.object(rs, "MAX_PER_ADDRESS", 2):
                    srv.start()
                    self.addCleanup(srv.stop)
                    held = [socket.create_connection(("127.0.0.1", srv.port))
                            for _ in range(2)]
                    for s in held:
                        self.addCleanup(s.close)
                    time.sleep(0.2)
                    third = socket.create_connection(("127.0.0.1", srv.port),
                                                     timeout=2)
                    self.addCleanup(third.close)
                    third.sendall(b"GET / HTTP/1.0\r\n\r\n")
                    try:
                        data = third.recv(10)
                    except OSError:
                        data = b""
                    self.assertEqual(data, b"")     # refused: closed unanswered

    def test_the_tunnel_side_is_not_counted(self):
        """The tunnel's connections all come from the loopback address."""
        for name, srv in _servers():
            with self.subTest(server=name):
                with mock.patch.object(rs, "MAX_PER_ADDRESS", 1):
                    srv.start()
                    self.addCleanup(srv.stop)
                    srv.tunnel_host = "x.trycloudflare.com"
                    held = socket.create_connection(("127.0.0.1", srv.port))
                    self.addCleanup(held.close)
                    time.sleep(0.2)
                    second = socket.create_connection(("127.0.0.1", srv.port),
                                                      timeout=2)
                    self.addCleanup(second.close)
                    second.sendall(b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
                    self.assertTrue(second.recv(20).startswith(b"HTTP/1."))


class WrongCodeBucketTest(unittest.TestCase):
    """#22: wrong codes from many addresses must not use up the budget the
    guests' real requests draw on."""

    def test_wrong_codes_do_not_lock_out_the_guests(self):
        srv = gs.GuestServer(on_request=lambda r: None, host="127.0.0.1", port=0,
                             labels={}, code="ABC234")
        srv.set_catalog([("a1b2c3d4", "Moon River", "Andy", "Slow Waltz")])
        for i in range(gs.ALL_GUESTS * 2):
            srv.check_code(f"10.9.{i // 250}.{i % 250}", "WRONG1")
        self.assertEqual(srv.take("192.168.1.50", {"song": "a1b2c3d4"}), 204)


if __name__ == "__main__":
    unittest.main()
