"""📱 Fuzz: what a phone may POST to the remote and the guest server.

Both answer anyone on the network (and, behind the tunnel, anyone at all)
who has the PIN or the event code, so the body is the least trusted input
the app has. The real handlers run here on a fake connection; only the PIN /
code gate is waved through, since that is not what is under test
(test_remote_server and test_guest_server have it).

What must hold, whatever the body and its Content-Length say: the handler
raises nothing, answers with one of its own statuses (or none, when the
body never came in full), and hands the desk only what the desk's handler
expects - main_remote._on_remote_command for the remote (a finite 0..1
float for seek and volume, a whole number for a pad, a place and a name for
jump), main_requests for the guests (a known song id, or a cleaned wish).
"""
import io
import json
import math
import unicodedata
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from hypothesis import event, example, given
from hypothesis import strategies as st

from shared.remote import guest_server as gs
from shared.remote import remote_server as rs
from shared.remote.guest_page import MAX_WISH
from tests.fuzz_support import fuzz, json_docs, json_values, mutated, texts

PHONE = ("192.168.1.20", 50123)

def mostly(usual, other) -> st.SearchStrategy:
    """`usual` three times in four: what a phone sends is mostly well formed,
    and the checks behind the first one only run on what gets past it."""
    # Not integers(0, 3): Hypothesis draws the ends of a range far more often.
    return st.sampled_from((usual, usual, usual, other)).flatmap(lambda strat: strat)


COMMAND_DOCS = st.one_of(
    st.fixed_dictionaries(
        {"cmd": mostly(st.sampled_from(sorted(rs.COMMANDS)), st.text(max_size=6) | json_values)},
        optional={"pad": mostly(st.integers(-2, 40), json_values),
                  "to": mostly(st.floats(-0.5, 1.5) | st.integers(-2, 40), json_values),
                  "level": mostly(st.floats(-0.5, 1.5) | st.integers(-1, 2), json_values),
                  "title": mostly(texts, json_values)}),
    json_docs(["cmd", "pad", "to", "level", "title"]))

GOOD_COMMANDS = [{"cmd": "pad", "pad": 3}, {"cmd": "seek", "to": 0.5},
                 {"cmd": "volume", "level": 1}, {"cmd": "jump", "to": 0, "title": "Song 01"},
                 {"cmd": "toggle"}]


def dump(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def bodies(docs, good) -> st.SearchStrategy:
    """A body: any bytes, a good one changed, or any JSON shaped like a
    request; with a Content-Length that is usually its own."""
    body = st.one_of(st.binary(max_size=rs._MAX_BODY + 40), docs.map(dump), docs.map(dump),
                     st.sampled_from(good).map(dump).flatmap(mutated))
    length = st.text(max_size=6) | st.integers(-5, rs._MAX_BODY * 70).map(str)
    return st.tuples(body, mostly(st.none(), length))


def post(handler_cls, server, path: str, body: bytes, length) -> list[int]:
    """`do_POST` on a fake connection; the statuses it sent."""
    h = handler_cls.__new__(handler_cls)
    h.server = server
    h.path = path
    h.client_address = PHONE
    h.headers = {"Content-Length": str(len(body)) if length is None else length}
    h.rfile = io.BytesIO(body)
    h.connection = mock.Mock()
    h.close_connection = False
    sent: list[int] = []
    h._send = lambda status, *_a, **_kw: sent.append(status)
    h.do_POST()
    return sent


def declared(body: bytes, length) -> int | None:
    """The Content-Length the handler goes by, None when it is no number."""
    try:
        return len(body) if length is None else int(length or 0)
    except ValueError:
        return None


class RemoteCommandFuzzTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.app = rs.RemoteServer("4711", lambda cmd, arg: self.calls.append((cmd, arg)))
        gate = mock.patch.object(rs._Handler, "_gate", lambda _self, need_pin: True)
        gate.start()
        self.addCleanup(gate.stop)

    @fuzz(150)
    @given(bodies(COMMAND_DOCS, GOOD_COMMANDS),
           mostly(st.sampled_from(["/api/cmd", "/api/cmd?x=1"]),
                  st.sampled_from(["/api/state", "/", "/api/cmd/"])))
    @example((dump({"cmd": "seek", "to": float("nan")}), None), "/api/cmd")
    @example((dump({"cmd": "volume", "level": float("inf")}), None), "/api/cmd")
    @example((dump({"cmd": "pad", "pad": 10 ** 400}), None), "/api/cmd")
    @example((dump({"cmd": "pad", "pad": True}), None), "/api/cmd")
    @example((dump({"cmd": "jump", "to": -1, "title": "x"}), None), "/api/cmd")
    @example((dump(["cmd"]), None), "/api/cmd")
    @example((b"[" * 1000, None), "/api/cmd")
    def test_a_body_is_a_command_or_refused(self, sent_body, path):
        body, length = sent_body
        self.calls.clear()
        sent = post(rs._Handler, NS(remote=self.app), path, body, length)
        size = declared(body, length)
        event(f"answered {sent}")   # --hypothesis-show-statistics
        if sent == []:   # the body never came in full: the connection just closes
            self.assertTrue(size is not None and size > len(body), (body, length))
        else:
            self.assertEqual(len(sent), 1, sent)
            self.assertIn(sent[0], (204, 400, 404, 413))
        self.assertEqual(len(self.calls), 1 if sent == [204] else 0, self.calls)
        for cmd, arg in self.calls:
            self.assertIn(cmd, rs.COMMANDS)
            if cmd in ("seek", "volume"):
                self.assertIs(type(arg), float)
                self.assertTrue(math.isfinite(arg) and 0 <= arg <= 1, arg)
            elif cmd == "pad":
                self.assertIs(type(arg), int)
                self.assertGreaterEqual(arg, 0)
            elif cmd == "jump":
                to, title = arg
                self.assertIs(type(to), int)
                self.assertGreaterEqual(to, 0)
                self.assertIs(type(title), str)
                self.assertTrue(title)
            else:
                self.assertIsNone(arg)


class GuestRequestFuzzTest(unittest.TestCase):
    IDS = ("17", "4711", "0")

    def setUp(self):
        self.requests = []
        self.app = gs.GuestServer(self.requests.append, code="QUICKSTEP")
        self.app.set_catalog([(i, f"Song {i}", "Band", "LW") for i in self.IDS])
        gate = mock.patch.object(gs._Handler, "_api_gate", lambda _self: PHONE[0])
        gate.start()
        self.addCleanup(gate.stop)

    @fuzz(150)
    @given(bodies(st.one_of(
        st.fixed_dictionaries({"song": mostly(st.sampled_from(IDS), json_values)}),
        st.fixed_dictionaries({"text": mostly(texts, json_values)}),
        st.fixed_dictionaries({}, optional={
            "song": mostly(st.sampled_from(IDS), json_values),
            "text": mostly(texts, json_values)}),
        json_docs(["song", "text"])),
        [{"song": "17"}, {"text": "Cha Cha please"}]),
        mostly(st.sampled_from(["/api/request", "/api/request?a"]),
               st.sampled_from(["/api/now", "/"])))
    @example((dump({"song": "17", "text": "and this"}), None), "/api/request")
    @example((dump({"text": "‮\x00 \n"}), None), "/api/request")
    @example((dump({"text": "x" * 500}), None), "/api/request")
    @example((dump({"song": 17}), None), "/api/request")
    def test_a_body_is_a_request_or_refused(self, sent_body, path):
        body, length = sent_body
        self.requests.clear()
        self.app._budget = gs.Budget()     # every input from a fresh evening
        sent = post(gs._Handler, NS(guests=self.app), path, body, length)
        size = declared(body, length)
        event(f"answered {sent}")   # --hypothesis-show-statistics
        if sent == []:
            self.assertTrue(size is not None and size > len(body), (body, length))
        else:
            self.assertEqual(len(sent), 1, sent)
            self.assertIn(sent[0], (204, 400, 404, 413, 429))
        self.assertEqual(len(self.requests), 1 if sent == [204] else 0, self.requests)
        for request in self.requests:
            self.assertEqual(len(request), 1, request)
            if "song" in request:
                self.assertIn(request["song"], self.IDS)
            else:
                wish = request["text"]
                self.assertIs(type(wish), str)
                self.assertTrue(wish)
                self.assertLessEqual(len(wish), MAX_WISH)
                self.assertEqual(wish, wish.strip())
                self.assertFalse([ch for ch in wish
                                  if unicodedata.category(ch).startswith("C")], wish)


if __name__ == "__main__":
    unittest.main()
