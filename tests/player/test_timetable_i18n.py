#!/usr/bin/env python3
"""The 🕒 Zeitplan dialog's four row buttons speak German.

Run:  py -m unittest tests.player.test_timetable_i18n -v

Every other string in that dialog — the window title, the long hint, the
rotate row — was in the catalog already. The four buttons under the table
were not, because they do not read like the rest of the file: they come out
of a loop over tuples,

    for text, tip, slot in (("➕  Add", "A new line at the end", …), …):

and a caption that sits in a data structure before it reaches QPushButton is
invisible to a scanner that looks at call arguments. The hook still
translates them — QPushButton's constructor is patched — so this was only
ever six missing catalog entries. This test is what notices the next time
one of those six strings is reworded and the German is left behind.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tt_i18n_"))

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from planner import i18n  # noqa: E402

ENGLISH = {
    "➕  Add": "A new line at the end",
    "✖  Remove": "Take the selected line out",
    "▲": "Move the selected line up",
    "▼": "Move the selected line down",
}


class TimetableButtonsI18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def buttons(self, language):
        """The four row buttons, as a caption -> tooltip map."""
        i18n.set_active(language)
        i18n.install_text_hook()
        from player.timetable_dialog import TimetableDialog
        dlg = TimetableDialog()
        self.addCleanup(dlg.deleteLater)
        # The dialog button box holds Save/Cancel; the row buttons are the
        # ones carrying a tooltip.
        return {b.text(): b.toolTip()
                for b in dlg.findChildren(QPushButton) if b.toolTip()}

    def test_english_is_unchanged(self):
        self.assertEqual(self.buttons("en"), ENGLISH)

    def test_every_caption_and_tooltip_is_german(self):
        found = self.buttons("de")
        # ▲ and ▼ are symbols and stay themselves; their tooltips must move.
        self.assertEqual(sorted(found), sorted(
            ["➕  Hinzufügen", "✖  Entfernen", "▲", "▼"]))
        for caption, tip in found.items():
            self.assertNotIn(tip, ENGLISH.values(),
                             f"{caption!r} kept its English tooltip")
            self.assertTrue(tip.strip())


if __name__ == "__main__":
    unittest.main()
