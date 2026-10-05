#!/usr/bin/env python3
"""An AI playlist run can be stopped.

Run:  py -m unittest tests.planner.test_ai_cancel -v

A run is two turns, each on up to two backends with three retries between
them, and nothing could end it early: the button stayed greyed out until the
thread gave up on its own. Stopping now kills a `claude -p` that is still
thinking, cuts a retry wait short and never starts the fallback.
"""
import os
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_cancel_"))

from planner import ai, llm  # noqa: E402


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
        with mock.patch.object(llm, "_ask", side_effect=llm.Cancelled()):
            with self.assertRaises(llm.Cancelled):
                llm.search_rows("rules", "task", [], cancel=cancel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
