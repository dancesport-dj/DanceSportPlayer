#!/usr/bin/env python3
"""The model name that reaches `claude -p` is a model name, nothing else.

Run:  py -m unittest tests.planner.test_claude_cli_model_name -v

`ai_model` comes from the settings, and a venue pack can carry it. Behind a
Windows `claude.cmd` shim cmd.exe reads `&` and `>` in an argument without
spaces as shell syntax. Security audit run-2 #5.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_claude_model_"))

from planner.event import venue_pack
from planner.generate import llm


class ModelNameTest(unittest.TestCase):

    def _run(self, model):
        with mock.patch.object(llm, "resolve_claude_bin", return_value="claude.exe"), \
                mock.patch.object(llm.subprocess, "Popen") as popen:
            popen.return_value.returncode = 0
            popen.return_value.communicate.return_value = ("OK", "")
            return llm.call_claude_cli("hi", model=model), popen

    def test_real_model_names_pass(self):
        for name in ("opus", "sonnet", "claude-opus-5-5", "claude-sonnet-5-5",
                     "claude-3-5-haiku-20241022", "opus[1m]", "us.anthropic/x:1"):
            with self.subTest(name=name):
                out, popen = self._run(name)
                self.assertEqual(out, "OK")
                self.assertIn(name, popen.call_args.args[0])

    def test_shell_syntax_is_refused_before_anything_starts(self):
        for name in ("x&calc", "x>out.txt", "a|b", "a^b", "a%PATH%", 'a"b',
                     "a;b", "a b", "a\nb", "$(x)", "`x`", "", "-p", "x" * 200):
            with self.subTest(name=name):
                with mock.patch.object(llm.subprocess, "Popen") as popen:
                    with mock.patch.object(llm, "resolve_claude_bin",
                                           return_value="claude.exe"):
                        with self.assertRaises(ValueError):
                            llm.call_claude_cli("hi", model=name)
                popen.assert_not_called()

    def test_a_venue_pack_keeps_the_model_local(self):
        self.assertIn("ai_model", venue_pack.MACHINE_KEYS)
        out = venue_pack.merge_settings({"ai_model": "opus"},
                                        {"ai_model": "x&calc"})
        self.assertEqual(out["ai_model"], "opus")


if __name__ == "__main__":
    unittest.main(verbosity=2)
