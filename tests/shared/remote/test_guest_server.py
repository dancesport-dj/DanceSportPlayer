"""📨 Guest requests: the small web server guests' phones ask for titles through."""
import http.client
import json
import time
import types
import unittest

from shared.remote import guest_server as gs
from shared.remote.guest_page import GUEST_CODE_HEADER, MAX_WISH, page_html

SONGS = [("a1b2c3d4", "Moon River", "Andy Williams", "Slow Waltz"),
         ("0f0f0f0f", "Senorita", "Shawn Mendes", "Samba")]


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.events = []
        self.srv = gs.GuestServer(on_request=self.requests.append, host="127.0.0.1", port=0,
                                  labels={"send": "Senden"}, code="ABC234",
                                  on_event=lambda k, g, d: self.events.append((k, g, d)))
        self.srv.set_catalog(SONGS)
        self.srv.start()
        self.addCleanup(self.srv.stop)

    def _req(self, method, path, body=None, code: str | None = "ABC234", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=5)
        h = dict(headers or {})
        if code is not None:
            h[GUEST_CODE_HEADER] = code
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        if data is not None:
            h["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=h)
        resp = conn.getresponse()
        out = resp.status, dict(resp.getheaders()), resp.read()
        conn.close()
        return out

    def test_the_page_needs_no_code_and_carries_the_labels(self):
        status, headers, body = self._req("GET", "/", code=None)
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])
        self.assertIn('"send": "Senden"'.encode(), body)
        self.assertNotIn(b"ABC234", body)

    def test_the_title_list_needs_the_code(self):
        self.assertEqual(self._req("GET", "/api/catalog", code=None)[0], 403)
        self.assertEqual(self._req("GET", "/api/catalog", code="ZZZZZZ")[0], 403)
        status, _h, body = self._req("GET", "/api/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["songs"][1],
                         ["0f0f0f0f", "Senorita", "Shawn Mendes", "Samba"])

    def test_now_playing_is_shared(self):
        self.srv.publish_now({"title": "Moon River", "dance": "Slow Waltz"})
        status, _h, body = self._req("GET", "/api/now")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"title": "Moon River", "dance": "Slow Waltz"})

    def test_a_library_title_reaches_the_desk(self):
        self.assertEqual(self._req("POST", "/api/request", {"song": "a1b2c3d4"})[0], 204)
        self.assertEqual(self.requests, [{"song": "a1b2c3d4"}])
        self.assertIn(("request", "127.0.0.1", "a1b2c3d4"), self.events)

    def test_a_wish_arrives_cleaned(self):
        wish = "  Dancing\x00 Queen\n\tplease " + "x" * 300
        self.assertEqual(self._req("POST", "/api/request", {"text": wish})[0], 204)
        self.assertEqual(len(self.requests), 1)
        text = self.requests[0]["text"]
        self.assertTrue(text.startswith("Dancing Queen please x"))
        self.assertEqual(len(text), MAX_WISH)

    def test_bad_requests_are_refused(self):
        for body in ({"song": "nothere"}, {"text": "  \n "}, {"song": 5},
                     {"song": "a1b2c3d4", "text": "both"}, {}, b"[1]", b"{nope"):
            self.assertEqual(self._req("POST", "/api/request", body)[0], 400, body)
        self.assertEqual(self.requests, [])

    def test_a_request_needs_the_code(self):
        self.assertEqual(self._req("POST", "/api/request", {"song": "a1b2c3d4"},
                                   code="ZZZZZZ")[0], 403)
        self.assertEqual(self.requests, [])

    def test_a_large_body_is_refused(self):
        big = json.dumps({"text": "x" * 2000}).encode()
        self.assertEqual(self._req("POST", "/api/request", big)[0], 413)
        self.assertEqual(self.requests, [])

    def test_a_guest_has_a_budget(self):
        for _ in range(gs.PER_GUEST):
            self.assertEqual(self._req("POST", "/api/request", {"text": "one more"})[0], 204)
        self.assertEqual(self._req("POST", "/api/request", {"text": "one more"})[0], 429)
        self.assertEqual(len(self.requests), gs.PER_GUEST)
        self.assertIn(("too_many", "127.0.0.1", ""), self.events)

    def test_guests_behind_the_tunnel_each_have_their_own(self):
        for guest in ("203.0.113.7", "198.51.100.9"):
            hdr = {"CF-Connecting-IP": guest}
            for _ in range(gs.PER_GUEST):
                self.assertEqual(self._req("POST", "/api/request", {"text": "hi"},
                                           headers=hdr)[0], 204)
            self.assertEqual(self._req("POST", "/api/request", {"text": "hi"},
                                       headers=hdr)[0], 429)

    def test_guessing_the_code_runs_out(self):
        for _ in range(gs.PER_GUEST):
            self.assertEqual(self._req("GET", "/api/catalog", code="WRONG1")[0], 403)
        self.assertEqual(self._req("GET", "/api/catalog", code="WRONG1")[0], 429)
        self.assertEqual(sum(1 for e in self.events if e[0] == "bad_code"), gs.PER_GUEST)

    def test_a_new_code_turns_the_old_link_away(self):
        self.srv.set_code("NEW567")
        self.assertEqual(self._req("GET", "/api/catalog")[0], 403)
        self.assertEqual(self._req("GET", "/api/catalog", code="NEW567")[0], 200)

    def test_no_code_means_closed(self):
        self.srv.set_code("")
        self.assertEqual(self._req("GET", "/api/catalog", code="")[0], 410)
        self.assertEqual(self._req("POST", "/api/request", {"text": "hi"}, code="")[0], 410)
        self.assertEqual(self.requests, [])

    def test_no_other_website_may_call_it(self):
        self.assertEqual(self._req("OPTIONS", "/api/request")[0], 405)
        _s, headers, _b = self._req("GET", "/api/catalog")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_unknown_paths_are_404(self):
        self.assertEqual(self._req("GET", "/api/state")[0], 404)
        self.assertEqual(self._req("POST", "/api/cmd", {"cmd": "next"})[0], 404)

    def test_a_post_to_an_unknown_path_is_answered_not_reset(self):
        # Closing on an unread body resets the connection on Windows, and a
        # client that reads a moment later sees that instead of the 404.
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=5)
        self.addCleanup(conn.close)
        conn.request("POST", "/api/cmd", body=b"x" * 60_000, headers={GUEST_CODE_HEADER: "ABC234"})
        time.sleep(0.3)
        self.assertEqual(conn.getresponse().status, 404)

    def test_a_failing_desk_never_breaks_a_request(self):
        def boom(_request):
            raise RuntimeError("desk gone")
        self.srv.on_request = boom
        self.assertEqual(self._req("POST", "/api/request", {"song": "a1b2c3d4"})[0], 204)

    def test_stop_frees_the_port(self):
        self.assertEqual(self._req("GET", "/api/now")[0], 200)   # a guest was here
        port = self.srv.port
        self.srv.stop()
        self.assertFalse(self.srv.running)
        again = gs.GuestServer(on_request=lambda r: None, host="127.0.0.1", port=port)
        again.start()
        again.stop()

    def test_a_taken_port_is_refused(self):
        other = gs.GuestServer(on_request=lambda r: None, host="127.0.0.1", port=self.srv.port)
        with self.assertRaises(OSError):
            other.start()
        other.stop()


class GuestAddressTest(unittest.TestCase):
    """Behind the tunnel the header names the guest; elsewhere nobody can choose."""

    def _guest(self, peer, forwarded):
        fake = types.SimpleNamespace(client_address=(peer, 1234),
                                     headers={"CF-Connecting-IP": forwarded})
        return gs._Handler._guest(fake)  # type: ignore[arg-type]

    def test_the_tunnel_names_the_guest(self):
        self.assertEqual(self._guest("127.0.0.1", "203.0.113.7"), "203.0.113.7")
        self.assertEqual(self._guest("::1", "203.0.113.7"), "203.0.113.7")

    def test_a_phone_on_the_wifi_cannot_pick_one(self):
        self.assertEqual(self._guest("192.168.1.5", "203.0.113.7"), "192.168.1.5")


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.budget = gs.Budget(per_guest=2, all_guests=3, window=60, clock=lambda: self.now)

    def test_each_guest_and_all_together(self):
        self.assertTrue(self.budget.spend("a"))
        self.assertTrue(self.budget.spend("a"))
        self.assertFalse(self.budget.spend("a"))
        self.assertTrue(self.budget.spend("b"))
        self.assertFalse(self.budget.spend("c"))   # all three spent

    def test_the_budget_comes_back_with_the_window(self):
        self.budget.spend("a")
        self.budget.spend("a")
        self.now = 61.0
        self.assertTrue(self.budget.spend("a"))


class CodeTest(unittest.TestCase):
    def test_a_code_is_easy_to_read_off(self):
        codes = {gs.new_code() for _ in range(50)}
        self.assertGreater(len(codes), 40)
        for code in codes:
            self.assertEqual(len(code), gs.CODE_LENGTH)
            self.assertTrue(set(code) <= set(gs.CODE_ALPHABET))
        self.assertFalse(set("01IO") & set(gs.CODE_ALPHABET))

    def test_a_wish_is_cleaned(self):
        self.assertEqual(gs.clean_wish(" a​\x07b  \r\nc "), "a b c")
        self.assertEqual(gs.clean_wish(None), "")
        self.assertEqual(gs.clean_wish(5), "")


class PageTest(unittest.TestCase):
    def test_the_code_is_taken_from_the_address(self):
        html = page_html({})
        self.assertIn('hash.get("e")', html)
        self.assertIn(f'"{GUEST_CODE_HEADER}": code', html)
        self.assertIn(f'maxlength="{MAX_WISH}"', html)

    def test_every_address_is_relative(self):
        html = page_html({})
        for path in ("api/catalog", "api/now", "api/request"):
            self.assertIn(f'"{path}"', html)
        self.assertNotIn('"/api/', html)

    def test_a_translation_cannot_break_out(self):
        html = page_html({"title": "</script><b>", "send": "</script>x"})
        self.assertNotIn("</script><b>", html)
        self.assertIn("<title>&lt;/script&gt;&lt;b&gt;</title>", html)
        self.assertEqual(html.count("</script>"), 1)

    def test_server_text_goes_onto_the_page_as_text(self):
        self.assertNotIn("innerHTML", page_html({}))


if __name__ == "__main__":
    unittest.main()
