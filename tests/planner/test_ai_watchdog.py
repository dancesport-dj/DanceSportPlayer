#!/usr/bin/env python3
"""9.2 A model that never finishes: output has to keep arriving.

Run:  py -m unittest tests.planner.test_ai_watchdog -v

The request sat in one blocking read. Its timeout only limits a single recv, so
a host that keeps the line alive without saying anything could hold a run for as
long as it liked, and nothing told a slow answer from no answer. The reply now
streams: a model that stops producing is noticed long before the deadline, asked
once more, and then the other backend takes over.
"""
import contextlib
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_watchdog_"))

from planner.generate import ai, llm

STALL = 0.4
KEEP_ALIVE = b": OPENROUTER PROCESSING\n\n"
DONE = b"data: [DONE]\n\n"
SSE = "text/event-stream"


def chunk(content=None, reasoning=None, finish=None):
    delta = {}
    if content is not None:
        delta["content"] = content
    if reasoning is not None:
        delta["reasoning"] = reasoning
    row = {"choices": [{"delta": delta, "finish_reason": finish}]}
    return b"data: " + json.dumps(row).encode("utf-8") + b"\n\n"


class _Host:
    """A local server playing a script: bytes go out, a float is a silence."""

    def __init__(self, test, script, kind=SSE):
        self.script = script
        self.kind = kind
        self.request = b""
        self.srv = socket.create_server(("127.0.0.1", 0))
        test.addCleanup(self.srv.close)
        self.base = f"http://127.0.0.1:{self.srv.getsockname()[1]}/v1"
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        try:
            conn, _addr = self.srv.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(10)
            # The client leaving is what several of these tests are about.
            with contextlib.suppress(OSError):
                self._answer(conn)

    def _answer(self, conn):
        while b"\r\n\r\n" not in self.request:
            self.request += conn.recv(65536)
        head, _, body = self.request.partition(b"\r\n\r\n")
        length = [ln for ln in head.split(b"\r\n")
                  if ln.lower().startswith(b"content-length")][0]
        while len(body) < int(length.split(b":")[1]):
            body += conn.recv(65536)
        self.request = body
        for step in self.script:
            if step == "head":
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: "
                             + self.kind.encode("ascii")
                             + b"\r\nConnection: close\r\n\r\n")
            elif isinstance(step, float):
                time.sleep(step)
            else:
                conn.sendall(step)

    def asked(self):
        return json.loads(self.request.decode("utf-8"))


class WatchdogCase(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.object(ai, "NO_OUTPUT_SECS", STALL)
        patcher.start()
        self.addCleanup(patcher.stop)

    def chat(self, script, timeout=5, cancel=None, kind=SSE):
        self.host = _Host(self, script, kind)
        return ai.openrouter_chat("k", "m", "s", "u", timeout=timeout,
                                  base_url=self.host.base, cancel=cancel)


class StreamTest(WatchdogCase):

    def test_the_pieces_add_up_to_the_answer(self):
        answer = self.chat(["head", chunk("Hello "), KEEP_ALIVE, chunk("there"),
                            chunk(finish="stop"), DONE])
        self.assertEqual(answer, "Hello there")

    def test_the_reply_is_asked_for_as_a_stream(self):
        self.chat(["head", chunk("x"), chunk(finish="stop"), DONE])
        self.assertTrue(self.host.asked()["stream"])

    def test_a_host_that_ignores_the_stream_still_answers(self):
        reply = {"choices": [{"message": {"content": "whole"},
                              "finish_reason": "stop"}]}
        answer = self.chat(["head", json.dumps(reply).encode("utf-8")],
                           kind="application/json")
        self.assertEqual(answer, "whole")

    def test_an_error_in_the_stream_reads_like_the_http_error(self):
        row = {"error": {"code": 502, "message": "upstream fell over"}}
        with self.assertRaisesRegex(RuntimeError, "HTTP 502: upstream fell over"):
            self.chat(["head", chunk("par"),
                       b"data: " + json.dumps(row).encode("utf-8") + b"\n\n"])

    def test_nothing_but_a_finish_is_an_empty_answer(self):
        with self.assertRaisesRegex(RuntimeError, "empty answer.*length"):
            self.chat(["head", chunk(finish="length"), DONE])

    def test_a_line_cut_mid_answer_can_be_retried(self):
        with self.assertRaises(ConnectionError) as caught:
            self.chat(["head", chunk("half an ans")])
        self.assertTrue(llm.is_transient(caught.exception))


class NoOutputTest(WatchdogCase):

    def assertGivesUp(self, script, within, **kw):
        started = time.monotonic()
        with self.assertRaises(ai.NoOutput):
            self.chat(script, **kw)
        self.assertLess(time.monotonic() - started, within)

    def test_a_host_that_only_keeps_the_line_alive(self):
        """The hang itself: bytes keep coming, none of them are an answer."""
        self.assertGivesUp(["head"] + [KEEP_ALIVE, 0.1] * 50, within=2)

    def test_a_host_that_stops_after_the_first_words(self):
        self.assertGivesUp(["head", chunk("So"), 5.0], within=2)

    def test_a_host_that_never_answers_at_all(self):
        self.assertGivesUp([5.0], within=2)

    def test_a_model_thinking_out_loud_is_not_stalled(self):
        script = ["head"] + [chunk(reasoning="hm"), 0.2] * 5
        answer = self.chat(script + [chunk("done"), chunk(finish="stop"), DONE])
        self.assertEqual(answer, "done")

    def test_the_whole_answer_has_a_deadline_too(self):
        """A dribble of words can outlast the watchdog, not the deadline."""
        self.assertGivesUp(["head"] + [chunk("."), 0.1] * 100, within=3, timeout=1)

    def test_a_short_timeout_is_not_stretched_by_the_watchdog(self):
        with mock.patch.object(ai, "NO_OUTPUT_SECS", 30):
            self.assertGivesUp([5.0], within=2, timeout=0.5)

    def test_it_is_not_a_wobble_to_wait_out(self):
        self.assertFalse(llm.is_transient(ai.NoOutput("silent")))


class CancelTest(WatchdogCase):

    def test_a_stop_cuts_a_stream_in_mid_answer(self):
        cancel = threading.Event()
        timer = threading.Timer(0.2, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        started = time.monotonic()
        with self.assertRaises(OSError):
            self.chat(["head"] + [chunk("."), 0.05] * 100, cancel=cancel)
        self.assertLess(time.monotonic() - started, 2)


class RetryTest(unittest.TestCase):

    def test_silence_is_asked_again_once_without_a_wait(self):
        sleep = mock.Mock()
        steps = []
        call = mock.Mock(side_effect=[ai.NoOutput("silent"), "answer"])
        got = llm._try_backend(call, "host", sleep=sleep,
                               on_step=lambda *a: steps.append(a))
        self.assertEqual(got, "answer")
        self.assertEqual(call.call_count, 2)
        sleep.assert_not_called()
        self.assertTrue(steps, "the transcript shows why the wait went on")

    def test_silence_twice_moves_on(self):
        call = mock.Mock(side_effect=ai.NoOutput("silent"))
        with self.assertRaises(ai.NoOutput):
            llm._try_backend(call, "host", sleep=mock.Mock())
        self.assertEqual(call.call_count, 2)

    def test_the_other_backend_takes_over(self):
        cfg = {"api_key": "k", "model": "m", "base_url": "https://example.test/v1",
               "ask_first": True}
        with mock.patch.object(ai, "load_openrouter_config", return_value=cfg), \
             mock.patch.object(ai, "openrouter_chat",
                               side_effect=ai.NoOutput("silent")) as chat, \
             mock.patch.object(llm, "call_claude_cli", return_value="cli") as cli:
            raw, backend = llm._ask("s", "u", model="opus", config_dir="",
                                    timeout=30, sleep=mock.Mock())
        self.assertEqual(raw, "cli")
        self.assertEqual(backend, "claude -p (opus)")
        self.assertEqual(chat.call_count, 2)
        cli.assert_called_once()


if __name__ == "__main__":
    unittest.main()
