"""📱 Phone remote: the little web server the phone's browser talks to."""
import http.client
import json
import socket
import unittest
from unittest import mock

from shared import remote_server as rs
from shared.remote_page import page_html


class LanClientTest(unittest.TestCase):
    def test_home_networks_are_let_in(self):
        for addr in ("192.168.1.5", "10.0.0.2", "172.16.4.1", "127.0.0.1",
                     "fe80::1", "::1", "::ffff:192.168.0.3"):
            self.assertTrue(rs.lan_client(addr), addr)

    def test_the_internet_is_not(self):
        for addr in ("8.8.8.8", "2001:4860:4860::8888", "::ffff:8.8.8.8", "junk"):
            self.assertFalse(rs.lan_client(addr), addr)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.srv = rs.RemoteServer(pin="4711", on_command=lambda c, a: self.calls.append((c, a)),
                                   host="127.0.0.1", port=0,
                                   labels={"next": "Next"})
        self.srv.start()
        self.addCleanup(self.srv.stop)

    def _req(self, method, path, body=None, pin="4711", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=5)
        h = dict(headers or {})
        if pin is not None:
            h[rs.PIN_HEADER] = pin
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        if data is not None:
            h["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=h)
        resp = conn.getresponse()
        out = resp.status, dict(resp.getheaders()), resp.read()
        conn.close()
        return out

    def test_the_page_needs_no_pin_and_carries_the_labels(self):
        status, headers, body = self._req("GET", "/", pin=None)
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"<html", body)
        self.assertIn(b'"next": "Next"', body)
        self.assertNotIn(b"4711", body)

    def test_state_needs_the_pin(self):
        self.srv.publish({"title": "Moon", "dance": "Slow Waltz"})
        self.assertEqual(self._req("GET", "/api/state", pin=None)[0], 401)
        self.assertEqual(self._req("GET", "/api/state", pin="0000")[0], 401)
        status, _h, body = self._req("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"title": "Moon", "dance": "Slow Waltz"})

    def test_a_command_reaches_the_app(self):
        status, _h, _b = self._req("POST", "/api/cmd", {"cmd": "next"})
        self.assertEqual(status, 204)
        self.assertEqual(self.calls, [("next", None)])

    def test_a_pad_is_fired_by_its_number(self):
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "pad", "pad": 3})[0], 204)
        self.assertEqual(self.calls, [("pad", 3)])
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "pad", "pad": "x"})[0], 400)
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "pad", "pad": True})[0], 400)
        self.assertEqual(len(self.calls), 1)

    def test_a_seek_carries_a_point_on_the_bar(self):
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "seek", "to": 0.5})[0], 204)
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "seek", "to": 1})[0], 204)
        self.assertEqual(self.calls, [("seek", 0.5), ("seek", 1.0)])
        for bad in ("x", True, -0.1, 1.5, None):
            self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "seek", "to": bad})[0], 400)
        self.assertEqual(self._req("POST", "/api/cmd", b'{"cmd": "seek", "to": NaN}')[0], 400)
        self.assertEqual(len(self.calls), 2)

    def test_the_bar_can_be_dragged(self):
        html = page_html({})
        self.assertIn("pointerdown", html)
        self.assertIn('cmd: "seek"', html)

    def test_unknown_commands_and_bad_bodies_are_refused(self):
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "quit"})[0], 400)
        self.assertEqual(self._req("POST", "/api/cmd", b"not json")[0], 400)
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "next"}, pin="1")[0], 401)
        self.assertEqual(self.calls, [])

    def test_a_large_body_is_refused(self):
        big = json.dumps({"cmd": "next", "x": "y" * 5000}).encode()
        self.assertEqual(self._req("POST", "/api/cmd", big)[0], 413)
        self.assertEqual(self.calls, [])

    def test_guessing_the_pin_locks_the_phone_out(self):
        for _ in range(rs.MAX_FAILS):
            self._req("GET", "/api/state", pin="0000")
        self.assertEqual(self._req("GET", "/api/state")[0], 429)

    def test_no_other_website_may_read_or_call_it(self):
        status, headers, _b = self._req("OPTIONS", "/api/cmd",
                                        headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertNotEqual(status, 200)
        _s, headers, _b = self._req("GET", "/api/state")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_unknown_paths_are_404(self):
        self.assertEqual(self._req("GET", "/etc/passwd")[0], 404)

    def test_stop_frees_the_port(self):
        port = self.srv.port
        self.srv.stop()
        again = rs.RemoteServer(pin="1", on_command=lambda c, a: None,
                                host="127.0.0.1", port=port)
        again.start()
        again.stop()


class EventTest(unittest.TestCase):
    """What the desk's 📱 log hears — and what it does not."""

    def setUp(self):
        self.events = []
        self.srv = rs.RemoteServer(pin="4711", on_command=lambda c, a: None,
                                   host="127.0.0.1", port=0,
                                   on_event=lambda *e: self.events.append(e))
        self.srv.start()
        self.addCleanup(self.srv.stop)

    _req = ServerTest._req

    def test_start_page_login_once_command_wrong_pin_stop(self):
        port = self.srv.port
        self._req("GET", "/", pin=None)
        self._req("GET", "/api/state")
        self._req("GET", "/api/state")      # the second poll is no news
        self._req("POST", "/api/cmd", {"cmd": "pad", "pad": 2})
        self._req("GET", "/api/state", pin="0000")
        self._req("GET", "/api/state", pin="")   # no PIN yet: not a wrong one
        self.srv.stop()
        self.assertEqual(self.events, [
            ("start", "", str(port)), ("page", "127.0.0.1", ""),
            ("login", "127.0.0.1", ""), ("cmd", "127.0.0.1", "pad 2"),
            ("wrong_pin", "127.0.0.1", ""), ("stop", "", "")])

    def test_the_lockout_is_reported_with_its_length(self):
        for _ in range(rs.MAX_FAILS):
            self._req("GET", "/api/state", pin="0000")
        kinds = [e[0] for e in self.events]
        self.assertEqual(kinds.count("wrong_pin"), rs.MAX_FAILS - 1)
        self.assertEqual(self.events[-1], ("locked", "127.0.0.1", "60"))

    def test_a_new_pin_counts_at_once_and_phones_log_in_again(self):
        self._req("GET", "/api/state")
        self.srv.set_pin("1234")
        self.assertEqual(self._req("GET", "/api/state")[0], 401)
        self.assertEqual(self._req("GET", "/api/state", pin="1234")[0], 200)
        self.assertEqual([e[0] for e in self.events].count("login"), 2)

    def test_a_failing_listener_never_breaks_a_request(self):
        self.srv._on_event = mock.Mock(side_effect=RuntimeError("boom"))
        self.assertEqual(self._req("GET", "/", pin=None)[0], 200)


class FailureBudgetTest(unittest.TestCase):
    """The per-address lockout is beaten by changing addresses; a budget for
    the whole network is not. Phones already in keep working through it."""

    def setUp(self):
        self.events = []
        self.srv = rs.RemoteServer(pin="4711", on_command=lambda c, a: None,
                                   on_event=lambda *e: self.events.append(e))
        patcher = mock.patch.multiple(rs, MAX_FAILS=100, GLOBAL_MAX_FAILS=3)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _flood(self):
        for i in range(rs.GLOBAL_MAX_FAILS):
            self.srv.check_pin(f"10.0.0.{i + 1}", "0000")

    def test_wrong_pins_from_many_addresses_pause_new_logins(self):
        self._flood()
        self.assertEqual(self.srv.check_pin("10.0.0.99", "4711"), 429)

    def test_a_phone_already_in_keeps_working(self):
        self.assertEqual(self.srv.check_pin("10.0.0.50", "4711"), 200)
        self.srv.logged_in("10.0.0.50")
        self._flood()
        self.assertEqual(self.srv.check_pin("10.0.0.50", "4711"), 200)

    def test_the_pause_ends_with_the_window(self):
        with mock.patch.object(rs.time, "monotonic", return_value=1000.0):
            self._flood()
        later = 1000.0 + rs._GLOBAL_WINDOW_SECS + 1
        with mock.patch.object(rs.time, "monotonic", return_value=later):
            self.assertEqual(self.srv.check_pin("10.0.0.99", "4711"), 200)

    def test_the_pause_is_reported_once(self):
        self._flood()
        self.srv.check_pin("10.0.0.98", "0000")
        paused = [e for e in self.events if e[0] == "locked_all"]
        self.assertEqual(paused, [("locked_all", "", str(rs._GLOBAL_WINDOW_SECS))])


class IdleConnectionTest(unittest.TestCase):
    def test_the_default_idle_timeout_is_ten_minutes(self):
        self.assertEqual(rs._Handler.timeout, 600)

    def test_a_connection_that_never_speaks_is_dropped(self):
        srv = rs.RemoteServer(pin="4711", on_command=lambda c, a: None,
                              host="127.0.0.1", port=0)
        with mock.patch.object(rs._Handler, "timeout", 0.2):
            srv.start()
            self.addCleanup(srv.stop)
            with socket.create_connection(("127.0.0.1", srv.port), timeout=5) as sock:
                self.assertEqual(sock.recv(1), b"")    # closed by the server


class PageTest(unittest.TestCase):
    def test_the_qr_codes_pin_is_taken_from_the_address(self):
        # The QR code holds http://…/#pin=1234: the page keeps the PIN and
        # wipes it from the address bar.
        html = page_html({})
        self.assertIn("location.hash", html)
        self.assertIn("history.replaceState", html)

    def test_the_buttons_wear_the_big_players_icons(self):
        """The same artwork as the player card, not the system's emoji."""
        from shared.iconset import SVG
        html = page_html({})
        for name in ("prev", "play_circle", "pause_circle", "next",
                     "fade_out", "panic", "stop", "speak"):
            self.assertIn(SVG[name][1], html, name)
        for emoji in ("&#x23EE;", "&#x23EF;", "&#x23ED;", "1F509", "1F6D1", "25A0"):
            self.assertNotIn(emoji, html)


class AnnounceTest(unittest.TestCase):
    def test_the_phone_can_switch_the_announcement(self):
        self.assertIn("announce", rs.COMMANDS)
        html = page_html({"announce": "Ansage"})
        self.assertIn('data-cmd="announce"', html)
        self.assertIn('"announce": "Ansage"', html)
        self.assertIn("s.announce", html)        # lit while it is on


class PinTest(unittest.TestCase):
    def test_new_pin_is_four_digits(self):
        for _ in range(50):
            p = rs.new_pin()
            self.assertEqual(len(p), 4)
            self.assertTrue(p.isdigit())


if __name__ == "__main__":
    unittest.main()
