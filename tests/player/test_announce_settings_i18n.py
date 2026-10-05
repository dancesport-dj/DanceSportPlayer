#!/usr/bin/env python3
"""The 🔈 announcement settings on the ▶ Playing panel, in German.

Run:  py -m unittest tests.player.test_announce_settings_i18n -v

The "Stimme:" combo named its three recordings in English — Female, Male,
Mixed — beside a label that had long said Stimme. `QComboBox.addItem` IS
one of i18n's patched methods, and the combo is read back with
`currentData()`, never by text, so the captions were free to translate all
along; nobody had written the three catalog entries.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ann_i18n_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner import i18n  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _AnnouncePanel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def panel(self, language, **settings):
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        p.show()
        return p


class AnnounceWhenCaptionTest(_AnnouncePanel):
    """The pair that says where the call sits against the first bar.

    Both captions were written as whole sentences with the mechanism in
    brackets — "announce over the first bars (music ducks)" came to 528px,
    and its German 612px, in a panel that is laid out between 250 and 640.
    The German was cut on screen and the English only just was not.

    The reasons live in the tooltips, which have all the room they want.
    """

    # The panel's own minimum width is 250px; this leaves the pair readable
    # there without pinning either language to an exact string.
    BUDGET = 320

    def radios(self, language):
        p = self.panel(language, announce_next=True)
        return [p.announce_over_radio, p.announce_wait_radio]

    def test_both_fit_the_panel_in_english(self):
        for r in self.radios("en"):
            with self.subTest(caption=r.text()):
                self.assertLessEqual(r.sizeHint().width(), self.BUDGET)

    def test_both_fit_the_panel_in_german(self):
        for r in self.radios("de"):
            with self.subTest(caption=r.text()):
                self.assertLessEqual(r.sizeHint().width(), self.BUDGET)

    def test_the_german_pair_left_the_english_behind(self):
        """A caption missing from the catalog would still be English, and
        still fit — so measuring alone would not catch it."""
        for de, en in zip(self.radios("de"), self.radios("en")):
            with self.subTest(caption=en.text()):
                self.assertNotEqual(de.text(), en.text())

    def test_the_mechanism_is_still_explained_somewhere(self):
        """Shortening the caption must not lose what ducking means."""
        over, wait = self.radios("en")
        self.assertIn("ducked", over.toolTip())
        self.assertIn("silence", wait.toolTip())


class VoiceComboTest(_AnnouncePanel):
    """Which recorded voice reads the announcement."""

    def voices(self, language):
        combo = self.panel(language).announce_voice_combo
        return [combo.itemText(i) for i in range(combo.count())]

    def test_english_is_unchanged(self):
        self.assertEqual(self.voices("en"), ["Female", "Male", "Mixed"])

    def test_the_three_recordings_are_named_in_german(self):
        self.assertEqual(self.voices("de"), ["Weiblich", "Männlich", "Gemischt"])

    def test_the_setting_is_still_stored_in_english(self):
        """The combo is read by data, so a German screen writes the same
        settings file as an English one."""
        p = self.panel("de", announce_voice="male")
        self.assertEqual(p.announce_voice_combo.currentText(), "Männlich")
        self.assertEqual(p.announce_voice(), "male")


if __name__ == "__main__":
    unittest.main(verbosity=2)
