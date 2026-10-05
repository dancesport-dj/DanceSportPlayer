#!/usr/bin/env python3
"""`claude -p` gets a question, not the machine.

Run:  py -m unittest tests.planner.test_claude_cli_sandbox -v

The prompt carries the library — titles, artists and the free ID3 comment
markers, all text someone else wrote. The CLI ran with every tool it has, every
MCP server of the login, and the app folder as its working directory, so a
comment that read like an instruction could have the model run commands with
the user's rights. The pick needs none of that: the model answers in plain
text and the app runs its queries itself.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_claude_sandbox_"))

from planner import llm  # noqa: E402
from planner.config import INSTALL_DIR  # noqa: E402


class ClaudeCliSandboxTest(unittest.TestCase):

    def setUp(self):
        self.seen = {}
        seen = self.seen

        class FakePopen:
            returncode = 0

            def __init__(self, cmd, **kw):
                seen["cmd"] = cmd
                seen["cwd"] = kw.get("cwd")
                seen["cwd_existed"] = bool(kw.get("cwd")) and os.path.isdir(kw["cwd"])
                if kw.get("cwd"):
                    seen["cwd_files"] = os.listdir(kw["cwd"])

            def communicate(self, input=None, timeout=None):
                return "OK", ""

        patches = (mock.patch.object(llm, "resolve_claude_bin",
                                     return_value="claude.exe"),
                   mock.patch.object(llm.subprocess, "Popen", FakePopen))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        llm.call_claude_cli("hi")
        self.cmd = self.seen["cmd"]

    def _value_of(self, flag):
        return self.cmd[self.cmd.index(flag) + 1]

    def test_no_built_in_tool_is_offered(self):
        self.assertEqual(self._value_of("--tools"), "")

    def test_no_mcp_server_of_the_login_is_loaded(self):
        self.assertIn("--strict-mcp-config", self.cmd)
        self.assertEqual(self._value_of("--mcp-config"), '{"mcpServers": {}}')

    def test_the_prompt_is_not_kept_as_a_session(self):
        self.assertIn("--no-session-persistence", self.cmd)

    def test_it_runs_in_an_empty_folder_away_from_the_app(self):
        cwd = self.seen["cwd"]
        self.assertTrue(self.seen["cwd_existed"])
        self.assertEqual(self.seen["cwd_files"], [])
        self.assertNotEqual(Path(cwd).resolve(), INSTALL_DIR.resolve())
        self.assertFalse(os.path.exists(cwd), "the folder is removed afterwards")


if __name__ == "__main__":
    unittest.main(verbosity=2)
