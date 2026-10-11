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

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QLabel

from gui import about
from gui.common import LoadingDialog
from planner import i18n
from tests.qt_test_support import reap_widget, stub_window_startup

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
        for label in ("Projekt", "Autor", "Lizenz", "App-Icon", "Stimmen",
                      "Bibliotheken", "KI-generiert", "alle Lizenzen"):
            self.assertIn(label, text)

    def test_it_credits_the_icons(self):
        # Marcel: the app icon's credit, and the UI icons', belong in the
        # licence files. Icons8's free licence asks for a link in the About section.
        text = about.about_html("DanceSport Player", "1.2.0")
        for part in ("href='https://icons8.com'", "Icons8", "Bootstrap Icons",
                     "Twemoji"):
            self.assertIn(part, text)

    def test_it_credits_the_voices_and_the_libraries(self):
        # Marcel: "but then also the other licences and usage of eleven labs".
        # ElevenLabs' free plan wants "Voices: elevenlabs.io" (LICENSE-AUDIO.md),
        # Qt's LGPL and the GPL parts want naming; the full list is linked.
        text = about.about_html("DanceSport Player", "1.2.0")
        for part in ("Voices", "href='https://elevenlabs.io'", "non-commercial",
                     "Libraries", "Qt / PySide6 (LGPL-3.0)", "mutagen (GPL-2.0+)",
                     # Every build has Qt's FFmpeg libraries; only the Windows
                     # one adds ffmpeg.exe, the GPL-3.0 build.
                     "FFmpeg (LGPL-2.1+, ffmpeg.exe GPL-3.0)",
                     "href='https://github.com/dancesport-dj/DanceSportPlayer/blob/main/"
                     "THIRD_PARTY_LICENSES.md'"):
            self.assertIn(part, text)

    def test_the_libraries_take_two_lines(self):
        # Marcel: "to not make the about dialog wider break them in 2 lines".
        text = about.about_html("DanceSport Player", "1.2.0")
        self.assertIn("mutagen (GPL-2.0+)<br>FFmpeg (", text)

    def test_the_named_licences_are_the_ones_in_the_list(self):
        listed = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
        for part in ("LGPL-3.0", "GPL-2.0-or-later", "GPL-3.0", "LGPL-2.1-or-later"):
            self.assertIn(part, listed)
        self.assertIn("non-commercial", (ROOT / "speech" / "LICENSE-AUDIO.md").read_text(
            encoding="utf-8"))


def pdfs(root: Path, *langs: str) -> Path:
    """A docs/manual under root with a manual.pdf per language ("" is English)."""
    for lang in langs:
        folder = root / "docs" / "manual" / lang
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "manual.pdf").write_bytes(b"%PDF-1.7")
    return root / "docs" / "manual"


class ManualPdfTest(unittest.TestCase):
    """Marcel: "generate manuel and pdf in german and english, especially if
    we call it from the app". The bundle carries docs/manual[/de]/manual.pdf
    (dancesport.spec); a source run finds the ones tools.build_manual_pdf made."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.object(about, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_german_opens_the_german_manual(self):
        manual = pdfs(self.root, "", "de")
        self.assertEqual(about.manual_pdf("de"), manual / "de" / "manual.pdf")

    def test_english_opens_the_english_manual(self):
        manual = pdfs(self.root, "", "de")
        self.assertEqual(about.manual_pdf("en"), manual / "manual.pdf")

    def test_a_language_without_a_manual_gets_the_english_one(self):
        manual = pdfs(self.root, "")
        self.assertEqual(about.manual_pdf("de"), manual / "manual.pdf")
        self.assertEqual(about.manual_pdf("fr"), manual / "manual.pdf")

    def test_no_pdf_is_no_manual(self):
        self.assertIsNone(about.manual_pdf("de"))

    def test_the_app_language_picks_it(self):
        manual = pdfs(self.root, "", "de")
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.assertEqual(about.manual_pdf(), manual / "de" / "manual.pdf")


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
        # No PDF unless a test makes one: a checkout may hold a built manual.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.object(about, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def german(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        self.addCleanup(i18n._restore_text_hook)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_the_question_mark_offers_shortcuts_and_about(self):
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Keyboard shortcuts  (F1)", "📜  Played titles…", "ℹ  About…",
                                 "⛶  Fullscreen  (F11)"])

    def test_the_entries_start_without_an_empty_gutter(self):
        """Marcel: "why are there a empty spot before the title comes" — Fusion
        keeps a check/icon column even when no entry has either."""
        self.assertLess(self.text_indent(self.win._help_menu()), 16)

    def test_the_check_menu_has_no_gutter_either(self):
        """Marcel: "by ? it is now fine but by check button still wrong"."""
        self.assertLess(self.text_indent(self.win._check_menu()), 16)

    def text_indent(self, menu) -> int:
        """Pixels from an entry's left edge to its first ink."""
        self.addCleanup(reap_widget, menu)
        menu.adjustSize()
        menu.show()
        self.app.processEvents()
        img = menu.grab().toImage()
        r = menu.actionGeometry(menu.actions()[0])
        bg = img.pixelColor(r.left() + 3, r.center().y()).lightness()
        ink = next(x for x in range(r.left() + 3, r.right())
                   for y in range(r.top() + 2, r.bottom() - 2)
                   if abs(img.pixelColor(x, y).lightness() - bg) > 60)
        return ink - r.left()

    def test_with_a_pdf_the_menu_offers_the_manual(self):
        pdfs(self.root, "", "de")
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Keyboard shortcuts  (F1)", "📖  Manual", "📜  Played titles…",
                                 "ℹ  About…",
                                 "⛶  Fullscreen  (F11)"])

    def test_the_german_menu_offers_the_handbuch(self):
        pdfs(self.root, "", "de")
        self.german()
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Tastenkürzel  (F1)", "📖  Handbuch", "📜  Gespielte Titel…",
                                 "ℹ  Über…",
                                 "⛶  Vollbild  (F11)"])

    def test_the_manual_opens_in_the_pdf_viewer(self):
        manual = pdfs(self.root, "", "de")
        self.german()
        entry = self.win._help_menu().actions()[1]
        with mock.patch.object(about.QDesktopServices, "openUrl", return_value=True) as open_:
            entry.trigger()
        open_.assert_called_once_with(QUrl.fromLocalFile(str(manual / "de" / "manual.pdf")))

    def test_the_german_menu_says_just_tastenkuerzel(self):
        """Marcel: "Tastenkürzel_Maustricks should only be Tastenkürzel"."""
        self.german()
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertEqual(texts, ["⌨  Tastenkürzel  (F1)", "📜  Gespielte Titel…", "ℹ  Über…",
                                 "⛶  Vollbild  (F11)"])

    def test_the_about_title_has_no_icon(self):
        """Marcel: the ℹ belongs to the menu entry, not the window title."""
        self.german()
        dlg = about.about_dialog(self.win, "DanceSport Player")
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg.windowTitle(), "Über")

    def test_about_opens_with_the_app_name(self):
        about_action = next(a for a in self.win._help_menu().actions()
                            if a.text() == "ℹ  About…")
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
