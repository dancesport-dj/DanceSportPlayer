#!/usr/bin/env python3
"""📂 The first start asks where the music is instead of guessing.

Run:  py -m unittest tests.gui.test_library_dir_first_start -v

The guess (F:\\my music\\tanzcds, then the Windows Music folder) landed a
tester's 1.3.1 on an external drive: the startup scan read 34,000 files before
the window opened. So the very first start asks, with the guess preselected,
and every later start - and every install that already has a folder - keeps
the one it has.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libq_"))

from PySide6.QtWidgets import QApplication, QFileDialog

from gui import dialogs
from gui.dialogs import (
    ASK_LIBRARY_DIR,
    LibraryDirQuestion,
    ensure_app_mode,
    ensure_library_dir,
)
from planner import config
from tests.qt_test_support import reap_widget


class _Stubbed(unittest.TestCase):
    """load/save and both questions replaced: a real exec() offscreen would
    hang the run."""

    def setUp(self):
        self.settings = {}
        self.saved = []
        self.asked = []
        self.answer = r"D:\Musik\Tanz"
        for name, repl in (("load_settings", lambda: dict(self.settings)),
                           ("save_settings", self.saved.append),
                           ("LibraryDirQuestion", self._make_question),
                           ("AppModeDialog", lambda *a, **kw: type(
                               "_Stub", (), {"exec": lambda s: 0,
                                             "mode": lambda s: "both"})()),
                           ("warn_if_ffmpeg_missing", lambda *a: None)):
            self.addCleanup(setattr, dialogs, name, getattr(dialogs, name))
            setattr(dialogs, name, repl)

    def _make_question(self, guess, *_a, **_kw):
        self.asked.append(guess)
        answer = self.answer
        return type("_Stub", (), {"ask": lambda s: answer})()


class FirstStartArmsTheQuestionTest(_Stubbed):
    def test_the_app_mode_question_arms_it(self):
        ensure_app_mode()
        self.assertIs(self.saved[0][ASK_LIBRARY_DIR], True)

    def test_a_player_build_arms_it_too(self):
        real = config.build_flavor
        config.build_flavor = lambda: "player"
        self.addCleanup(setattr, config, "build_flavor", real)
        ensure_app_mode()
        self.assertIs(self.saved[0][ASK_LIBRARY_DIR], True)

    def test_a_later_start_arms_nothing(self):
        self.settings = {"app_mode": "planner"}
        ensure_app_mode()
        self.assertEqual(self.saved, [])


class EnsureLibraryDirTest(_Stubbed):
    def test_the_first_start_asks_with_the_guess(self):
        self.settings = {ASK_LIBRARY_DIR: True, "library_dir": r"F:\my music\tanzcds"}
        self.assertEqual(ensure_library_dir(), r"D:\Musik\Tanz")
        self.assertEqual(self.asked, [r"F:\my music\tanzcds"])
        self.assertEqual(self.saved[0]["library_dir"], r"D:\Musik\Tanz")

    def test_it_is_asked_once(self):
        self.settings = {ASK_LIBRARY_DIR: True, "library_dir": "x"}
        ensure_library_dir()
        self.assertNotIn(ASK_LIBRARY_DIR, self.saved[0])

    def test_an_existing_install_keeps_its_folder(self):
        self.settings = {"app_mode": "both", "library_dir": r"C:\Lib"}
        self.assertEqual(ensure_library_dir(), r"C:\Lib")
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved, [])

    def test_the_rest_of_the_settings_survive(self):
        self.settings = {ASK_LIBRARY_DIR: True, "library_dir": "x",
                         "app_mode": "player"}
        ensure_library_dir()
        self.assertEqual(self.saved[0]["app_mode"], "player")


class QuestionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def question(self):
        q = LibraryDirQuestion(r"F:\my music\tanzcds")
        self.addCleanup(reap_widget, q)
        q.exec = lambda: 0
        return q

    def test_it_names_the_guess(self):
        self.assertIn(r"F:\my music\tanzcds", self.question().informativeText())

    def test_closing_it_keeps_the_guess(self):
        self.assertEqual(self.question().ask(), r"F:\my music\tanzcds")

    def test_another_folder_is_picked_in_a_folder_dialog(self):
        q = self.question()
        q.clickedButton = lambda: q.pick_btn
        real = QFileDialog.getExistingDirectory
        QFileDialog.getExistingDirectory = staticmethod(lambda *a, **kw: "D:/Musik/Tanz")
        self.addCleanup(setattr, QFileDialog, "getExistingDirectory", real)
        self.assertEqual(q.ask(), os.path.normpath("D:/Musik/Tanz"))

    def test_a_cancelled_folder_dialog_keeps_the_guess(self):
        q = self.question()
        q.clickedButton = lambda: q.pick_btn
        real = QFileDialog.getExistingDirectory
        QFileDialog.getExistingDirectory = staticmethod(lambda *a, **kw: "")
        self.addCleanup(setattr, QFileDialog, "getExistingDirectory", real)
        self.assertEqual(q.ask(), r"F:\my music\tanzcds")


if __name__ == "__main__":
    unittest.main()
