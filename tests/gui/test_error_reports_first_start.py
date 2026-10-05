#!/usr/bin/env python3
"""🐞 The error reports are asked about once, on the first start.

Run:  py -m unittest tests.gui.test_error_reports_first_start -v

Off by default and tucked away in ⚙ Settings, nobody would ever switch them
on. Marcel: "frage beim start einmal sonst in settings". So the first start
that can send them asks, the answer is kept either way, and from then on only
⚙ Settings changes it. A build without the address asks nothing.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_errq_"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from gui import dialogs  # noqa: E402
from gui.dialogs import ErrorReportsQuestion, ensure_error_reports_choice  # noqa: E402
from shared import error_reports  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class EnsureChoiceTest(unittest.TestCase):

    def setUp(self):
        self.settings = {}
        self.saved = []
        self.asked = []
        self.answer = True
        for name, repl in (("load_settings", lambda: dict(self.settings)),
                           ("save_settings", self.saved.append),
                           ("ErrorReportsQuestion", self._make_question)):
            self.addCleanup(setattr, dialogs, name, getattr(dialogs, name))
            setattr(dialogs, name, repl)
        available = mock.patch.object(error_reports, "available",
                                      return_value=True)
        self.available = available.start()
        self.addCleanup(available.stop)

    def _make_question(self, *_a, **_kw):
        """A question that never enters an event loop — a real exec()
        offscreen would hang the run."""
        self.asked.append(True)
        answer = self.answer
        return type("_Stub", (), {"ask": lambda s: answer})()

    def test_the_first_start_asks_and_keeps_a_yes(self):
        self.assertTrue(ensure_error_reports_choice())
        self.assertEqual(self.asked, [True])
        self.assertIs(self.saved[0]["error_reports"], True)

    def test_a_no_is_kept_too(self):
        """Otherwise the question comes back on every start."""
        self.answer = False
        self.assertFalse(ensure_error_reports_choice())
        self.assertIs(self.saved[0]["error_reports"], False)

    def test_an_answer_given_before_is_not_asked_again(self):
        for value in (True, False):
            with self.subTest(value=value):
                self.settings = {"error_reports": value}
                self.assertIs(ensure_error_reports_choice(), value)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved, [])

    def test_a_build_that_cannot_send_asks_nothing(self):
        self.available.return_value = False
        self.assertFalse(ensure_error_reports_choice())
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved, [])

    def test_the_rest_of_the_settings_survive(self):
        self.settings = {"app_mode": "player"}
        ensure_error_reports_choice()
        self.assertEqual(self.saved[0]["app_mode"], "player")


class QuestionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def question(self):
        box = ErrorReportsQuestion()
        self.addCleanup(reap_widget, box)
        return box

    def test_it_says_what_goes_and_where_to_change_it(self):
        text = self.question().informativeText()
        self.assertIn("Not sent", text)
        self.assertIn("⚙ Settings", text)

    def test_every_text_of_it_is_in_german_too(self):
        from planner.lang_de import CATALOG
        box = self.question()
        for text in (box.windowTitle(), box.text(), box.informativeText(),
                     box.send_btn.text(), box.keep_btn.text()):
            self.assertIn(text, CATALOG)

    def test_not_sending_is_the_default_and_the_escape(self):
        box = self.question()
        self.assertIs(box.defaultButton(), box.keep_btn)
        self.assertIs(box.escapeButton(), box.keep_btn)

    def test_the_answer_is_the_button_pressed(self):
        box = self.question()
        with mock.patch.object(QMessageBox, "exec", lambda b: 0), \
                mock.patch.object(QMessageBox, "clickedButton",
                                  lambda b: box.send_btn):
            self.assertTrue(box.ask())
        with mock.patch.object(QMessageBox, "exec", lambda b: 0), \
                mock.patch.object(QMessageBox, "clickedButton",
                                  lambda b: box.keep_btn):
            self.assertFalse(box.ask())


if __name__ == "__main__":
    unittest.main(verbosity=2)
