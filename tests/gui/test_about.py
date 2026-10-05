#!/usr/bin/env python3
"""ℹ About behind the ❔ button, and the version on the splash.

Run:  py -m unittest tests.gui.test_about -v

Marcel: "add also a about dialog where my github and the version and licency
typ is mentioned, try to integrate it in the qustion mark button. make sure
the version info is also shown in splash screen for loading."
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_about_"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from gui import about  # noqa: E402
from gui.common import LoadingDialog  # noqa: E402
from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class AboutTextTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_it_names_version_github_and_licence(self):
        text = about.about_html("DanceSport Player", "1.2.0")
        for part in ("DanceSport Player", "1.2.0", "MIT License",
                     "github.com/dancesport-dj/DanceSportPlayer",
                     "github.com/marcelkb"):
            self.assertIn(part, text)

    def test_the_licence_is_the_one_in_the_repo(self):
        first = (ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(about.LICENSE_NAME, first.strip())

    def test_the_labels_follow_the_language(self):
        i18n.set_active("de")
        text = about.about_html("DanceSport Player", "1.2.0")
        for label in ("Projekt", "Autor", "Lizenz"):
            self.assertIn(label, text)


class SplashTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_splash_shows_the_version(self):
        dlg = LoadingDialog("DanceSport Player", "Version 1.2.0")
        self.addCleanup(reap_widget, dlg)
        label = dlg.findChild(QLabel, "splashVersion")
        self.assertEqual(label.text(), "Version 1.2.0")


class HelpButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "player"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def german(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        self.addCleanup(i18n._restore_text_hook)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_the_question_mark_offers_shortcuts_and_about(self):
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Keyboard shortcuts  (F1)", "ℹ  About…"])

    def test_the_german_menu_says_just_tastenkuerzel(self):
        """Marcel: "Tastenkürzel_Maustricks should only be Tastenkürzel"."""
        self.german()
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Tastenkürzel  (F1)", "ℹ  Über…"])

    def test_the_about_title_has_no_icon(self):
        """Marcel: the ℹ belongs to the menu entry, not the window title."""
        self.german()
        dlg = about.about_dialog(self.win, "DanceSport Player")
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg.windowTitle(), "Über")

    def test_about_opens_with_the_app_name(self):
        about_action = self.win._help_menu().actions()[1]
        with mock.patch.object(self.gui, "show_about") as show:
            about_action.trigger()
        show.assert_called_once_with(self.win, "DanceSport Player")

    def test_the_button_is_there_on_the_player_side(self):
        self.assertFalse(self.win._help_btn.isHidden())

    def test_the_splash_carries_the_version(self):
        label = self.win._loading_dlg.findChild(QLabel, "splashVersion")
        self.assertEqual(label.text(), "Version dev")

    def test_the_splash_shows_a_build_version(self):
        with mock.patch.object(self.gui, "app_version", return_value="1.2.0"):
            win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        label = win._loading_dlg.findChild(QLabel, "splashVersion")
        self.assertEqual(label.text(), "Version 1.2.0")


if __name__ == "__main__":
    unittest.main()
