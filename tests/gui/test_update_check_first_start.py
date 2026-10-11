#!/usr/bin/env python3
"""🔔 The update check is opt-in, asked once, under the error reports question.

Run:  py -m unittest tests.gui.test_update_check_first_start -v

The privacy promise was "no update check"; a portable zip then never hears of
a fix. So the first start asks, in the same question as the error reports, and
the answer is kept either way. Where that question is not asked, a short one
of its own asks once. A source run has no release to compare and asks nothing.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_updq_"))

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from gui import dialogs, update_notice
from gui.dialogs import (ErrorReportsQuestion, UpdateCheckQuestion,
                         ensure_error_reports_choice, ensure_update_check_choice)
from shared import error_reports, update_check
from tests.qt_test_support import reap_widget

_LANGS = ("de", "es", "nl", "ru")


class _Patched(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        self.saved = []
        for name, repl in (("load_settings", lambda: dict(self.settings)),
                           ("save_settings", self.saved.append)):
            self.addCleanup(setattr, dialogs, name, getattr(dialogs, name))
            setattr(dialogs, name, repl)
        for target, name, value in ((update_check, "available", True),
                                    (error_reports, "available", True)):
            patcher = mock.patch.object(target, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)


class UnderTheErrorReportsQuestionTest(_Patched):
    def _question(self, updates_ticked):
        self.made = []

        def make(*_a, ask_updates=False, **_kw):
            self.made.append(ask_updates)
            return type("_Stub", (), {"ask": lambda s: False,
                                      "wants_updates": lambda s: updates_ticked})()
        self.addCleanup(setattr, dialogs, "ErrorReportsQuestion",
                        dialogs.ErrorReportsQuestion)
        dialogs.ErrorReportsQuestion = make

    def test_the_first_start_asks_both_in_one_question(self):
        self._question(updates_ticked=True)
        ensure_error_reports_choice()
        self.assertEqual(self.made, [True])
        self.assertIs(self.saved[0][update_check.SETTING], True)
        self.assertIs(self.saved[0]["error_reports"], False)

    def test_an_unticked_box_is_kept_as_a_no(self):
        self._question(updates_ticked=False)
        ensure_error_reports_choice()
        self.assertIs(self.saved[0][update_check.SETTING], False)

    def test_a_source_run_leaves_the_box_out(self):
        self._question(updates_ticked=True)
        with mock.patch.object(update_check, "available", return_value=False):
            ensure_error_reports_choice()
        self.assertEqual(self.made, [False])
        self.assertNotIn(update_check.SETTING, self.saved[0])


class OwnQuestionTest(_Patched):
    def setUp(self):
        super().setUp()
        self.asked = []
        self.answer = True

        def make(*_a, **_kw):
            self.asked.append(True)
            answer = self.answer
            return type("_Stub", (), {"ask": lambda s: answer})()
        self.addCleanup(setattr, dialogs, "UpdateCheckQuestion",
                        dialogs.UpdateCheckQuestion)
        dialogs.UpdateCheckQuestion = make

    def test_asked_once_where_nothing_asked_it(self):
        self.settings = {"error_reports": False}     # answered before the check came
        self.assertTrue(ensure_update_check_choice())
        self.assertEqual(self.asked, [True])
        self.assertIs(self.saved[0][update_check.SETTING], True)
        self.assertIs(self.saved[0]["error_reports"], False)

    def test_a_no_is_kept_too(self):
        self.answer = False
        self.assertFalse(ensure_update_check_choice())
        self.assertIs(self.saved[0][update_check.SETTING], False)

    def test_an_answer_given_before_is_not_asked_again(self):
        for value in (True, False):
            self.settings = {update_check.SETTING: value}
            self.assertIs(ensure_update_check_choice(), value)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved, [])

    def test_a_source_run_asks_nothing(self):
        with mock.patch.object(update_check, "available", return_value=False):
            self.assertFalse(ensure_update_check_choice())
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved, [])


class QuestionWidgetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _own(self, widget):
        self.addCleanup(reap_widget, widget)
        return widget

    def test_the_box_is_off_by_default_and_only_there_when_asked(self):
        box = self._own(ErrorReportsQuestion(ask_updates=True))
        self.assertIs(box.checkBox(), box.update_chk)
        self.assertFalse(box.wants_updates())
        box.update_chk.setChecked(True)
        self.assertTrue(box.wants_updates())
        plain = self._own(ErrorReportsQuestion())
        self.assertIsNone(plain.checkBox())
        self.assertFalse(plain.wants_updates())

    def test_not_checking_is_the_default_and_the_escape(self):
        box = self._own(UpdateCheckQuestion())
        self.assertIs(box.defaultButton(), box.keep_btn)
        self.assertIs(box.escapeButton(), box.keep_btn)
        self.assertIn("api.github.com", box.informativeText())
        self.assertIn("IP address", box.informativeText())
        with mock.patch.object(QMessageBox, "exec", lambda b: 0), \
                mock.patch.object(QMessageBox, "clickedButton",
                                  lambda b: box.check_btn):
            self.assertTrue(box.ask())

    def test_every_text_is_in_every_language(self):
        own = self._own(UpdateCheckQuestion())
        combined = self._own(ErrorReportsQuestion(ask_updates=True))
        texts = [own.windowTitle(), own.text(), own.informativeText(),
                 own.check_btn.text(), own.keep_btn.text(),
                 combined.update_chk.text(), combined.update_chk.toolTip(),
                 "New version", "Version %s is out.",
                 "You are running %s. The download page lists what changed.",
                 "Open download page", "Later"]
        dlg = self._own(dialogs.SettingsDialog(dict(dialogs.load_settings())))
        texts += [dlg._update_check_chk.text(), dlg._update_check_chk.toolTip()]
        for lang in _LANGS:
            catalog = __import__(f"planner.lang_{lang}", fromlist=["CATALOG"]).CATALOG
            for text in texts:
                if lang == "nl" and text == "Later":
                    continue        # Dutch says it the same way
                self.assertIn(text, catalog, f"{lang}: {text[:40]}")


class SettingsCheckboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_it_shows_and_saves_the_choice(self):
        for value in (False, True):
            settings = dict(dialogs.load_settings())
            settings[update_check.SETTING] = value
            dlg = dialogs.SettingsDialog(settings)
            self.addCleanup(reap_widget, dlg)
            self.assertIs(dlg._update_check_chk.isChecked(), value)
            dlg._update_check_chk.setChecked(not value)
            self.assertIs(dlg.values()[update_check.SETTING], not value)


class NoticeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = QWidget()
        self.window._settings = {"theme": "x"}
        self.addCleanup(reap_widget, self.window)
        self.saved = []
        patcher = mock.patch.object(update_notice, "save_settings", self.saved.append)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.opened = []
        patcher = mock.patch.object(QMessageBox, "open",
                                    lambda box: self.opened.append(box))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_notice_waits_for_the_window(self):
        notice = update_notice.UpdateNotice(self.window)
        with mock.patch.object(update_notice.QTimer, "singleShot") as later:
            notice.show_notice("1.3.0", "https://x")
        later.assert_called_once()
        self.assertEqual(self.opened, [])

    def test_it_is_remembered_in_the_windows_own_settings(self):
        """The window saves its settings whole; a marker written only to the
        file would be dropped by its next save and announce the same release
        again."""
        self.window.show()
        notice = update_notice.UpdateNotice(self.window)
        notice.show_notice("1.3.0", "https://x")
        self.assertEqual(self.window._settings[update_check.SEEN_SETTING], "1.3.0")
        self.assertIs(self.saved[0], self.window._settings)
        self.assertEqual(len(self.opened), 1)
        self.assertIn("1.3.0", self.opened[0].text())
        reap_widget(self.opened[0])

    def test_a_find_from_the_check_thread_reaches_the_notice(self):
        notice = update_notice.UpdateNotice(self.window)
        heard = []
        with mock.patch.object(update_notice.UpdateNotice, "show_notice",
                               lambda s, v, u: heard.append((v, u))):
            notice = update_notice.UpdateNotice(self.window)
            with mock.patch.object(update_check, "check_in_background",
                                   lambda settings, cb: cb("1.3.0", "https://x")):
                notice.start({update_check.SETTING: True})
        self.assertEqual(heard, [("1.3.0", "https://x")])


class PrivacyTextTest(unittest.TestCase):
    def test_the_readme_names_the_check_and_where_it_goes(self):
        readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
            encoding="utf-8")
        self.assertNotIn("no update check.", readme)
        self.assertIn("api.github.com", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
