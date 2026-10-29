#!/usr/bin/env python3
"""The ▶ panel's switches in German are no wider than in English (F10).

Run:  .venv/Scripts/python.exe -m unittest tests.player.widgets.test_panel_width_i18n -v

Marcel: "German strings must fit their widgets: e.g. 'Merken, wo ein Titel
stehen geblieben ist' → 'Titelposition merken'; 'innerhalb der Spieldauer'
shorter." A switch elides its caption rather than widen the panel, so a long
German one is cut off where the English fits.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_panel_width_"))

from PySide6.QtWidgets import QApplication, QComboBox

from planner import i18n
from player.widgets.panel_parts import Toggle
from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget

# Two characters of slack: German is longer, but not by a word.
SLACK_PX = 24


class PanelWidthTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def widths(self, language):
        """Each switch's and combo's width, in the order the panel builds them."""
        i18n.set_active(language)
        i18n.install_text_hook()
        panel = PlayModePanel({})
        self.addCleanup(reap_widget, panel)
        rows = [(p.text(), p.sizeHint().width()) for p in panel.findChildren(Toggle)]
        rows += [(c.currentText(), c.sizeHint().width())
                 for c in panel.findChildren(QComboBox)]
        i18n._restore_text_hook()
        return rows

    def test_no_german_switch_is_a_word_wider(self):
        english = self.widths("en")
        german = self.widths("de")
        for (en, en_w), (de, de_w) in zip(english, german, strict=True):
            self.assertLessEqual(de_w, en_w + SLACK_PX,
                                 "%r is %d px wider than %r" % (de, de_w - en_w, en))

    def test_the_two_marcel_named(self):
        i18n.set_active("de")
        self.assertEqual(i18n.t("↩  Remember where a title stopped"),
                         "↩  Titelposition merken")
        self.assertNotIn("innerhalb", i18n.t("within the length"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
