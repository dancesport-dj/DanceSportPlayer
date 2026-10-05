"""The fallback backend may live anywhere OpenAI-compatible.

OpenRouter is only the default: pointing `base_url` at another host — Mammouth,
say — has to move the chat call, the model list and the messages with it.
"""
import json
import os
import tempfile
import subprocess
import unittest
from unittest import mock

# Offscreen BEFORE any QApplication exists, state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_aibackend_"))

from planner import ai  # noqa: E402


class _Resp:
    """The bare minimum of what urlopen hands back."""

    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture(payload):
    """Patch urlopen, remember the request it was given."""
    seen = {}

    def fake(req, timeout=None):
        seen["req"] = req
        seen["timeout"] = timeout
        return _Resp(payload)

    return seen, fake


MAMMOUTH = "https://api.mammouth.ai/v1"


class EndpointTest(unittest.TestCase):

    def test_default_is_openrouter(self):
        self.assertEqual(ai._endpoint("", "/chat/completions"),
                         "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(ai.OPENROUTER_URL,
                         "https://openrouter.ai/api/v1/chat/completions")

    def test_other_host(self):
        self.assertEqual(ai._endpoint(MAMMOUTH, "/chat/completions"),
                         "https://api.mammouth.ai/v1/chat/completions")

    def test_trailing_slash_is_forgiven(self):
        self.assertEqual(ai._endpoint(MAMMOUTH + "/  ", "/models"),
                         "https://api.mammouth.ai/v1/models")

    def test_a_full_url_is_taken_as_it_stands(self):
        full = MAMMOUTH + "/chat/completions"
        self.assertEqual(ai._endpoint(full, "/chat/completions"), full)

    def test_host_and_flavour(self):
        self.assertEqual(ai.api_host(MAMMOUTH), "api.mammouth.ai")
        self.assertEqual(ai.api_host(""), "openrouter.ai")
        self.assertTrue(ai.is_openrouter(""))
        self.assertFalse(ai.is_openrouter(MAMMOUTH))


class ChatTest(unittest.TestCase):

    _REPLY = {"choices": [{"message": {"content": "hi"}}]}

    def test_posts_to_the_configured_host(self):
        seen, fake = _capture(self._REPLY)
        with mock.patch("urllib.request.urlopen", fake):
            out = ai.openrouter_chat("k", "gpt-5.5", "sys", "usr",
                                             base_url=MAMMOUTH)
        self.assertEqual(out, "hi")
        req = seen["req"]
        self.assertEqual(req.full_url, MAMMOUTH + "/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer k")
        # OpenRouter's ranking headers mean nothing to anyone else.
        self.assertIsNone(req.get_header("X-title"))
        self.assertEqual(json.loads(req.data)["model"], "gpt-5.5")

    def test_openrouter_still_gets_its_headers(self):
        seen, fake = _capture(self._REPLY)
        with mock.patch("urllib.request.urlopen", fake):
            ai.openrouter_chat("k", "m", "sys", "usr")
        self.assertEqual(seen["req"].full_url, ai.OPENROUTER_URL)
        self.assertEqual(seen["req"].get_header("X-title"),
                         "Dancesport Playlist Planner")

    def test_a_missing_key_names_the_host(self):
        with self.assertRaises(RuntimeError) as ctx:
            ai.openrouter_chat("", "m", "s", "u", base_url=MAMMOUTH)
        self.assertIn("api.mammouth.ai", str(ctx.exception))

    def test_an_answer_that_is_not_a_completion_is_reported(self):
        _seen, fake = _capture({"error": {"message": "no such model"}})
        with mock.patch("urllib.request.urlopen", fake):
            with self.assertRaises(RuntimeError) as ctx:
                ai.openrouter_chat("k", "openrouter/free", "s", "u")
        msg = str(ctx.exception)
        self.assertIn("openrouter.ai", msg)
        self.assertIn("no such model", msg)


class PlainHttpTest(unittest.TestCase):
    """The key rides in a header: over plain http anyone on the network reads
    it. An edited base URL with 'http://' must not take it there."""

    _REPLY = {"choices": [{"message": {"content": "hi"}}], "data": []}

    def _sent(self, call):
        seen, fake = _capture(self._REPLY)
        with mock.patch("urllib.request.urlopen", fake):
            try:
                call()
            except RuntimeError:
                pass
        return "req" in seen

    def test_the_chat_refuses_plain_http(self):
        with self.assertRaises(RuntimeError) as ctx:
            with mock.patch("urllib.request.urlopen",
                            _capture(self._REPLY)[1]):
                ai.openrouter_chat("k", "m", "s", "u",
                                   base_url="http://api.mammouth.ai/v1")
        self.assertIn("https", str(ctx.exception))
        self.assertFalse(self._sent(lambda: ai.openrouter_chat(
            "k", "m", "s", "u", base_url="http://api.mammouth.ai/v1")))

    def test_the_model_list_refuses_plain_http(self):
        self.assertFalse(self._sent(lambda: ai.openrouter_free_models(
            "k", base_url="http://api.mammouth.ai/v1")))

    def test_a_server_on_this_machine_may_use_http(self):
        for base in ("http://localhost:11434/v1", "http://127.0.0.1:1234/v1",
                     "http://[::1]:8080/v1"):
            with self.subTest(base=base):
                self.assertTrue(self._sent(lambda: ai.openrouter_chat(
                    "k", "m", "s", "u", base_url=base)))

    def test_https_still_goes_out(self):
        self.assertTrue(self._sent(lambda: ai.openrouter_chat(
            "k", "m", "s", "u", base_url=MAMMOUTH)))


class ModelListTest(unittest.TestCase):

    _LIST = {"data": [
        {"id": "paid/one", "pricing": {"prompt": "0.5", "completion": "1"}},
        {"id": "free/one:free", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": ""},
    ]}

    def test_openrouter_keeps_only_the_free_ones(self):
        _seen, fake = _capture(self._LIST)
        with mock.patch("urllib.request.urlopen", fake):
            self.assertEqual(ai.openrouter_free_models(), ["free/one:free"])

    def test_another_host_prices_nothing_so_everything_is_offered(self):
        _seen, fake = _capture(self._LIST)
        with mock.patch("urllib.request.urlopen", fake):
            got = ai.openrouter_free_models(base_url=MAMMOUTH)
        self.assertEqual(got, ["free/one:free", "paid/one"])


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self._store = mock.patch.object(ai, "OPENROUTER").start()
        self.addCleanup(mock.patch.stopall)

    def test_an_old_config_gets_the_default_base(self):
        self._store.read.return_value = {"api_key": "k", "model": "m"}
        cfg = ai.load_openrouter_config()
        self.assertEqual(cfg["base_url"], ai.DEFAULT_API_BASE)

    def test_a_stored_base_wins(self):
        self._store.read.return_value = {"api_key": "k", "model": "m",
                                         "base_url": MAMMOUTH}
        self.assertEqual(ai.load_openrouter_config()["base_url"], MAMMOUTH)

    def test_the_environment_can_name_the_host(self):
        self._store.read.return_value = {"api_key": "k", "model": "m",
                                         "base_url": ""}
        with mock.patch.dict(os.environ, {"OPENROUTER_BASE_URL": MAMMOUTH}):
            self.assertEqual(ai.load_openrouter_config()["base_url"],
                             MAMMOUTH)

    def test_saving_keeps_the_base(self):
        ai.save_openrouter_config("k", "m", MAMMOUTH)
        self._store.write.assert_called_once_with(
            {"api_key": "k", "model": "m", "base_url": MAMMOUTH})

    def test_saving_without_one_falls_back(self):
        ai.save_openrouter_config("k", "m")
        self.assertEqual(self._store.write.call_args[0][0]["base_url"],
                         ai.DEFAULT_API_BASE)


class BackendLabelTest(unittest.TestCase):
    """`_ask` has to say which host answered — or which one failed."""

    def test_the_fallback_names_the_host(self):
        from planner import llm as planner_llm
        cfg = {"api_key": "k", "model": "gpt-5.5", "base_url": MAMMOUTH}
        with mock.patch.object(planner_llm, "call_claude_cli",
                               side_effect=RuntimeError("no cli")), \
             mock.patch.object(ai, "load_openrouter_config",
                               return_value=cfg), \
             mock.patch.object(ai, "openrouter_chat",
                               return_value="ok") as chat:
            text, backend = planner_llm._ask("s", "u", model="opus",
                                             config_dir="", timeout=5)
        self.assertEqual(text, "ok")
        self.assertEqual(backend, "api.mammouth.ai (gpt-5.5)")
        self.assertEqual(chat.call_args.kwargs["base_url"], MAMMOUTH)

    def test_both_failures_are_named(self):
        from planner import llm as planner_llm
        cfg = {"api_key": "k", "model": "m", "base_url": MAMMOUTH}
        with mock.patch.object(planner_llm, "call_claude_cli",
                               side_effect=RuntimeError("no cli")), \
             mock.patch.object(ai, "load_openrouter_config",
                               return_value=cfg), \
             mock.patch.object(ai, "openrouter_chat",
                               side_effect=RuntimeError("401")):
            with self.assertRaises(RuntimeError) as ctx:
                planner_llm._ask("s", "u", model="opus", config_dir="", timeout=5)
        msg = str(ctx.exception)
        self.assertIn("claude -p", msg)
        self.assertIn("api.mammouth.ai", msg)
        self.assertIn("401", msg)


class TransientErrorTest(unittest.TestCase):
    """Which failures are worth asking again about."""

    def setUp(self):
        from planner import llm as planner_llm
        self.L = planner_llm

    def test_a_server_side_wobble_is_transient(self):
        for msg in ("api.mammouth.ai HTTP 529: overloaded",
                    "api.x HTTP 500: internal server error",
                    "openrouter.ai HTTP 429: rate limit exceeded",
                    "api.x HTTP 504: gateway timeout",
                    "connection reset by peer"):
            self.assertTrue(self.L.is_transient(RuntimeError(msg)), msg)

    def test_a_broken_socket_is_transient(self):
        self.assertTrue(self.L.is_transient(ConnectionResetError("boom")))

    def test_a_timeout_is_not(self):
        """The host already had its whole timeout. Asking again three times
        over two backends and two turns kept a hung run going for hours."""
        import urllib.error
        for exc in (subprocess.TimeoutExpired("claude", 600),
                    TimeoutError("The read operation timed out"),
                    urllib.error.URLError(TimeoutError("timed out")),
                    RuntimeError("<urlopen error timed out>")):
            self.assertFalse(self.L.is_transient(exc), repr(exc))

    def test_our_own_mistakes_are_not(self):
        """These fail the same way in a minute — go to the fallback at once."""
        for msg in ("api.x HTTP 401: invalid api key",
                    "api.x HTTP 400: bad request",
                    "claude CLI not found — not on PATH",
                    "No API key set for api.x.",
                    "api.x sent no answer: {}"):
            self.assertFalse(self.L.is_transient(RuntimeError(msg)), msg)


class RetryTest(unittest.TestCase):
    """A 529 is the host having a moment. `_ask` waits 10s, 30s and 60s before
    it gives up on a backend — the fallback is for a backend that is broken,
    not for one that is busy."""

    def setUp(self):
        from planner import llm as planner_llm
        self.L = planner_llm
        self.cfg = {"api_key": "k", "model": "m", "base_url": MAMMOUTH}
        self.slept = []

    def _ask(self, cli, chat, **kw):
        with mock.patch.object(self.L, "call_claude_cli", cli), \
             mock.patch.object(ai, "load_openrouter_config",
                               return_value=self.cfg), \
             mock.patch.object(ai, "openrouter_chat", chat):
            return self.L._ask("s", "u", model="opus", config_dir="",
                               timeout=5, sleep=self.slept.append, **kw)

    def test_the_waits_are_ten_thirty_sixty(self):
        self.assertEqual(self.L._RETRY_WAITS, (10, 30, 60))

    def test_an_overloaded_host_is_asked_again(self):
        cli = mock.Mock(side_effect=[RuntimeError("HTTP 529: overloaded"),
                                     "answer"])
        text, backend = self._ask(cli, mock.Mock())
        self.assertEqual(text, "answer")
        self.assertEqual(backend, "claude -p (opus)")
        self.assertEqual(self.slept, [10])

    def test_three_retries_then_the_fallback(self):
        cli = mock.Mock(side_effect=RuntimeError("HTTP 503: service unavailable"))
        text, backend = self._ask(cli, mock.Mock(return_value="from the other"))
        self.assertEqual(cli.call_count, 4)          # first try + 10s + 30s + 60s
        self.assertEqual(self.slept, [10, 30, 60])
        self.assertEqual(text, "from the other")
        self.assertEqual(backend, "api.mammouth.ai (m)")

    def test_the_fallback_backend_gets_its_own_retries(self):
        cli = mock.Mock(side_effect=RuntimeError("no cli"))
        chat = mock.Mock(side_effect=[RuntimeError("HTTP 529: overloaded"),
                                      "late answer"])
        text, _ = self._ask(cli, chat)
        self.assertEqual(text, "late answer")
        self.assertEqual(self.slept, [10])

    def test_both_backends_wobbling_is_still_an_abort(self):
        cli = mock.Mock(side_effect=RuntimeError("HTTP 529: overloaded"))
        chat = mock.Mock(side_effect=RuntimeError("HTTP 502: bad gateway"))
        with self.assertRaises(RuntimeError) as ctx:
            self._ask(cli, chat)
        self.assertIn("Both backends failed", str(ctx.exception))
        self.assertEqual(self.slept, [10, 30, 60, 10, 30, 60])

    def test_a_bad_key_does_not_wait_around(self):
        cli = mock.Mock(side_effect=RuntimeError("no cli"))
        chat = mock.Mock(side_effect=RuntimeError("HTTP 401: invalid key"))
        with self.assertRaises(RuntimeError):
            self._ask(cli, chat)
        self.assertEqual(self.slept, [])
        self.assertEqual(chat.call_count, 1)

    def test_the_wait_shows_up_in_the_transcript(self):
        """A run quietly waiting out a 529 must not look like a hung one."""
        steps = []
        cli = mock.Mock(side_effect=[RuntimeError("HTTP 529: overloaded"),
                                     "answer"])
        self._ask(cli, mock.Mock(),
                  on_step=lambda role, title, text: steps.append(
                      (role, title, text)))
        self.assertEqual(len(steps), 1)
        role, title, text = steps[0]
        self.assertEqual(role, "note")
        self.assertIn("claude -p", title)
        self.assertIn("1 of 4", title)
        self.assertIn("529", text)
        self.assertIn("10s", text)

    def test_a_backend_that_answers_says_nothing(self):
        self._ask(mock.Mock(return_value="fine"), mock.Mock())
        self.assertEqual(self.slept, [])


class DialogTest(unittest.TestCase):
    """The base URL is a field, and what is typed there is what gets saved."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, cfg):
        from gui import ai_dialogs as gui_ai_dialogs
        from tests.qt_test_support import reap_widget
        with mock.patch.object(gui_ai_dialogs, "load_openrouter_config",
                               return_value=cfg):
            dlg = gui_ai_dialogs.AiSuggestDialog(None)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_stored_host_shows_up(self):
        dlg = self._dlg({"api_key": "k", "model": "gpt-5.5", "base_url": MAMMOUTH})
        self.assertEqual(dlg._base_edit.currentText(), MAMMOUTH)
        self.assertEqual(dlg._base_url(), MAMMOUTH)

    def test_an_empty_base_falls_back_to_openrouter(self):
        dlg = self._dlg({"api_key": "k", "model": "m", "base_url": ""})
        self.assertEqual(dlg._base_url(), ai.DEFAULT_API_BASE)

    def test_asking_saves_the_host_along_with_key_and_model(self):
        from gui import ai_dialogs as gui_ai_dialogs
        dlg = self._dlg({"api_key": "k", "model": "m", "base_url": ""})
        dlg._base_edit.setCurrentText(MAMMOUTH)
        with mock.patch.object(gui_ai_dialogs, "save_openrouter_config") as save, \
             mock.patch.object(gui_ai_dialogs, "OpenRouterChatWorker") as worker:
            dlg._get()
        save.assert_called_once_with("k", "m", MAMMOUTH)
        self.assertEqual(worker.call_args.kwargs["base_url"], MAMMOUTH)


if __name__ == "__main__":
    unittest.main()
