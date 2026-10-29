#!/usr/bin/env python3
"""An AI playlist run can be stopped.

Run:  py -m unittest tests.planner.test_ai_cancel -v

A run is two turns, each on up to two backends with three retries between
them, and nothing could end it early: the button stayed greyed out until the
thread gave up on its own. Stopping now kills a `claude -p` that is still
thinking, cuts a retry wait short and never starts the fallback.
"""
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_cancel_"))

from planner.generate import ai, llm
from tests.planner.test_tls import has_certifi_roots


class _Proc:
    """A `claude -p` that thinks forever — until it is killed."""

    def __init__(self, on_wait=None):
        self.killed = False
        self.waits = 0
        self._on_wait = on_wait
        self.returncode = None

    def communicate(self, input=None, timeout=None):
        if self.killed:
            return "", ""
        self.waits += 1
        if self._on_wait:
            self._on_wait()
        raise subprocess.TimeoutExpired("claude", timeout)

    def kill(self):
        self.killed = True
        self.returncode = 1


class CliCancelTest(unittest.TestCase):

    def _run(self, proc, **kw):
        with mock.patch.object(llm, "resolve_claude_bin", return_value="claude.exe"), \
             mock.patch.object(llm.subprocess, "Popen", return_value=proc):
            return llm.call_claude_cli("hi", **kw)

    def test_stopping_kills_the_cli_that_is_still_thinking(self):
        cancel = threading.Event()
        proc = _Proc(on_wait=cancel.set)      # stop is pressed while it runs
        with self.assertRaises(llm.Cancelled):
            self._run(proc, cancel=cancel, timeout=600)
        self.assertTrue(proc.killed)
        self.assertEqual(proc.waits, 1)

    def test_the_timeout_still_ends_it(self):
        proc = _Proc()
        with self.assertRaises(subprocess.TimeoutExpired):
            self._run(proc, timeout=0)
        self.assertTrue(proc.killed)


class AskCancelTest(unittest.TestCase):

    def setUp(self):
        self.cfg = {"api_key": "k", "model": "m",
                    "base_url": "https://api.mammouth.ai/v1"}

    def _ask(self, cli, chat, cancel):
        with mock.patch.object(llm, "call_claude_cli", cli), \
             mock.patch.object(ai, "load_openrouter_config",
                               return_value=self.cfg), \
             mock.patch.object(ai, "openrouter_chat", chat):
            return llm._ask("s", "u", model="opus", config_dir="", timeout=5,
                            cancel=cancel)

    def test_a_stop_during_the_retry_wait_ends_it_without_the_fallback(self):
        cancel = threading.Event()

        def overloaded(*_a, **_kw):
            cancel.set()
            raise RuntimeError("HTTP 529: overloaded")

        cli = mock.Mock(side_effect=overloaded)
        chat = mock.Mock(return_value="from the other")
        started = time.monotonic()
        with self.assertRaises(llm.Cancelled):
            self._ask(cli, chat, cancel)
        self.assertLess(time.monotonic() - started, 5, "the 10 s wait was cut short")
        self.assertEqual(cli.call_count, 1)
        chat.assert_not_called()

    def test_an_answer_that_lands_after_the_stop_is_thrown_away(self):
        cancel = threading.Event()

        def late(*_a, **_kw):
            cancel.set()
            return "too late"

        with self.assertRaises(llm.Cancelled):
            self._ask(mock.Mock(side_effect=late), mock.Mock(), cancel)

    def test_a_stopped_search_round_is_not_swept_over(self):
        cancel = threading.Event()
        cancel.set()
        with mock.patch.object(llm, "_ask", side_effect=llm.Cancelled()), self.assertRaises(llm.Cancelled):
            llm.search_rows("rules", "task", [], cancel=cancel)


class HttpsTrustTest(unittest.TestCase):
    """On a Mac, Python has no CA file of its own: an https host answered
    "certificate verify failed" until certifi's roots came along."""

    def _answer(self, payload):
        body = json.dumps(payload).encode()
        return mock.MagicMock(__enter__=lambda s: mock.Mock(read=lambda: body),
                              __exit__=lambda s, *a: False)

    def test_the_model_list_is_fetched_with_certifi_too(self):
        with mock.patch.object(ai.urllib.request, "urlopen",
                               return_value=self._answer({"data": []})) as urlopen:
            ai.openrouter_free_models(base_url="https://openrouter.ai/api/v1")
        self.assertTrue(has_certifi_roots(urlopen.call_args.kwargs["context"]))

    def test_the_chat_is_sent_with_certifi_too(self):
        reply = {"choices": [{"message": {"content": "ok"}}]}
        with mock.patch.object(ai.urllib.request, "urlopen",
                               return_value=self._answer(reply)) as urlopen:
            ai.openrouter_chat("k", "m", "s", "u", base_url="https://openrouter.ai/api/v1")
        self.assertTrue(has_certifi_roots(urlopen.call_args.kwargs["context"]))

    def test_a_stoppable_chat_is_sent_with_certifi_too(self):
        handler = ai._KeptHttps([])
        self.assertTrue(has_certifi_roots(handler.tls))


class HttpCancelTest(unittest.TestCase):
    """The fallback host's request was the one thing a stop could not end: it
    sat in urlopen for its whole timeout (600 s in a run). A stop now shuts
    its socket, so the run ends at once and the host sees the client leave."""

    def setUp(self):
        self.srv = socket.create_server(("127.0.0.1", 0))
        self.addCleanup(self.srv.close)
        self.hung_up = threading.Event()
        threading.Thread(target=self._never_answer, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.getsockname()[1]}/v1"

    def _never_answer(self):
        """Takes the request, says nothing, notes when the client hangs up."""
        try:
            conn, _addr = self.srv.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(30)
            try:
                while conn.recv(65536):
                    pass
                self.hung_up.set()
            except OSError:
                self.hung_up.set()

    def _stop_soon(self):
        cancel = threading.Event()
        timer = threading.Timer(0.3, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        return cancel

    def test_a_stop_cuts_the_chat_request_on_the_wire(self):
        cancel = self._stop_soon()
        started = time.monotonic()
        with self.assertRaises(OSError):
            ai.openrouter_chat("k", "m", "s", "u", timeout=30,
                               base_url=self.base, cancel=cancel)
        self.assertLess(time.monotonic() - started, 5, "not the 30 s timeout")
        self.assertTrue(self.hung_up.wait(5), "the host saw no hang-up")

    def test_a_stop_while_the_fallback_waits_ends_the_run(self):
        cancel = self._stop_soon()
        cfg = {"api_key": "k", "model": "m", "base_url": self.base}
        started = time.monotonic()
        with mock.patch.object(llm, "call_claude_cli",
                               side_effect=RuntimeError("no CLI")), \
             mock.patch.object(ai, "load_openrouter_config", return_value=cfg), \
             self.assertRaises(llm.Cancelled):
            llm._ask("s", "u", model="opus", config_dir="", timeout=30,
                     cancel=cancel)
        self.assertLess(time.monotonic() - started, 5, "not the 30 s timeout")


if __name__ == "__main__":
    unittest.main(verbosity=2)
