#!/usr/bin/env python3
"""⏱ The play-length readout on the ▶ Playing panel, in German.

Run:  py -m unittest tests.player.test_play_length_i18n -v

In the off position the big readout said "full" on an otherwise German panel:
the label is set to the bare word, and the catalog had no entry for it. The
German is "komplett". The readout is also where a length is typed (double-
click), and the editor opens on the readout's own text — so "komplett" has to
parse back to 0, like "full" does.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_len_i18n_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner import i18n  # noqa: E402
from player.play_mode_panel import PlayModePanel, parse_play_length  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class PlayLengthReadoutTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def panel(self, language, secs):
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked
        p = PlayModePanel({"play_secs": secs})
        self.addCleanup(reap_widget, p)
        p.show()
        return p

    def test_english_still_says_full(self):
        self.assertEqual(self.panel("en", 0).len_lbl.text(), "full")

    def test_german_says_komplett(self):
        self.assertEqual(self.panel("de", 0).len_lbl.text(), "komplett")

    def test_komplett_types_back_to_no_cut(self):
        self.assertEqual(parse_play_length("komplett"), 0)
        self.assertEqual(parse_play_length("Komplett"), 0)

    def test_typing_komplett_into_the_readout_stops_the_cut(self):
        p = self.panel("de", 90)
        p._on_len_typed()
        p._len_edit.setText("komplett")
        p._commit_len_typed()
        self.assertEqual(p.play_secs(), 0)
        self.assertEqual(p.len_lbl.text(), "komplett")

    def test_the_readout_explains_itself_in_german(self):
        de = self.panel("de", 0).len_lbl.toolTip()
        self.assertNotEqual(de, self.panel("en", 0).len_lbl.toolTip())
        self.assertIn("'komplett'", de)

    def test_the_hints_name_the_word_german_shows(self):
        """Every German hint on this control says what the readout says."""
        i18n.set_active("de")
        for key in ("Pick a length or type one: m:ss, seconds, or 'full'",
                    "m:ss, seconds, or 'full' — Enter to keep, Esc to abandon",
                    "full — to each title's own end"):
            with self.subTest(key=key):
                self.assertIn("komplett", i18n.t(key))
                self.assertNotIn("full", i18n.t(key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
