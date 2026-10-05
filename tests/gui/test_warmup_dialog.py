#!/usr/bin/env python3
"""Tests for the 🤸 Eintanzen / party dialog's answer, without a window.

Run:  py -m unittest tests.gui.test_warmup_dialog -v

The dialog is shown with its `exec` stubbed, so what is checked is what the
generator receives: the options a click on Generate hands back.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_warmup_dlg_"))

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from gui.dialogs import M3uDropDialog  # noqa: E402
from gui.warmup_dialog import ask_warmup_options  # noqa: E402

ACCEPTED = QDialog.DialogCode.Accepted
REJECTED = QDialog.DialogCode.Rejected


def answered(exec_result):
    # A plain function in the class's place, so it is called with the dialog.
    with mock.patch.object(M3uDropDialog, "exec", exec_result):
        return ask_warmup_options(None, [], "")


class WarmupDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_generate_with_the_defaults(self):
        opts = answered(lambda dlg: ACCEPTED)
        self.assertEqual(
            {k: opts[k] for k in ("mode", "source", "m3u_path", "unused_only",
                                  "style", "dance_class", "max_tracks",
                                  "fresh_ratio", "relax")},
            {"mode": "class", "source": "library", "m3u_path": None,
             "unused_only": True, "style": "Latin", "dance_class": "S",
             "max_tracks": 100, "fresh_ratio": 0.25, "relax": True})
        self.assertEqual(opts["etds"]["max_tracks"], 120)
        self.assertEqual(opts["etds"]["modetaenze"], ["DISCOFOX", "SALSA"])

    def test_cancel_answers_nothing(self):
        self.assertIsNone(answered(lambda dlg: REJECTED))

    def test_a_dropped_playlist_becomes_the_source(self):
        def drop_then_generate(dlg):
            dlg.m3uDropped.emit("C:/lists/party.m3u")
            return ACCEPTED
        opts = answered(drop_then_generate)
        self.assertEqual((opts["source"], opts["m3u_path"], opts["unused_only"]),
                         ("m3u", "C:/lists/party.m3u", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
