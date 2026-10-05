#!/usr/bin/env python3
"""The 🎉 party report's own chrome in German.

Run:  py -m unittest tests.gui.test_party_report_i18n -v

The sentences inside the report are the engine's and are checked in
tests.planner.test_party_check_i18n. What is left is what the dialog writes
itself, and it stayed English for two different reasons:

* the group headings go into a QLabel through an f-string, and the head line
  is built by `%` — neither is a catalog key, so the hook never sees them;
* the 🩺 tooltip that opens the whole thing simply had no entry.

The ✅ empty-state label and the two buttons DO go through patched
constructors, so for them this only asks whether the catalog carries the
entry.

The harness is the one the English UI test already uses — a harness that
restated `_PARTY_GROUPS` would keep passing after the production one changed.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pcheck_de_"))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from planner import i18n  # noqa: E402
from tests.gui.test_party_check_ui import _Win, _e  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class PartyReportGermanTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        i18n.set_active("de")
        i18n.install_text_hook()

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def report(self, codes, **kw):
        """The dialog the 🩺 button opens, over a list of `codes`."""
        from gui.playlist_table import PlaylistTable

        host = _Win()
        self.addCleanup(reap_widget, host)
        t = PlaylistTable()
        t.setParent(host)
        t.load_warmup([_e(d, i) for i, d in enumerate(codes)], "ETDS Party",
                      "", "S", True, lambda _p: None, None)
        host._warmup_table = t
        for attr, value in kw.items():
            setattr(t, attr, value)
        host._show_party_report(host._party_findings(),
                                len(t._row_meta.song_rows()))
        dlg = host._party_dlg
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def labels(dlg):
        return " ".join(w.text() for w in dlg.findChildren(QLabel))

    @staticmethod
    def buttons(dlg):
        return [w.text() for w in dlg.findChildren(QPushButton)]

    def test_the_window_is_named_in_german(self):
        dlg = self.report(('LW', 'TG', 'QS', 'CC', 'RB', 'JI'))
        self.assertEqual(dlg.windowTitle(), "🎉  Party-Check")

    def test_the_head_counts_titles_and_findings(self):
        dlg = self.report(('LW', 'SF', 'QS', 'CC', 'RB', 'JI'))
        self.assertIn("6 Titel", self.labels(dlg))
        self.assertIn("Befund", self.labels(dlg))

    def test_a_list_with_no_name_of_its_own(self):
        dlg = self.report(('LW', 'TG', 'QS', 'CC', 'RB', 'JI'),
                          _warmup_label="")
        self.assertIn("Partyliste", self.labels(dlg))

    def test_every_group_heading(self):
        dlg = self.report(('LW', 'SF', 'QS',
                           'CC', 'RB', 'JI',
                           'WW', 'TG', 'LW'))
        text = self.labels(dlg)
        self.assertIn("🔁 Runden", text)
        self.assertIn("⏳ Abstände", text)

    def test_a_clean_list_says_so_in_german(self):
        dlg = self.report(('LW', 'TG', 'QS', 'CC', 'RB', 'JI',
                           'TG', 'SF', 'LW', 'SA', 'RB', 'CC'))
        self.assertIn("Nichts zu melden", self.labels(dlg))

    def test_both_buttons(self):
        dlg = self.report(('LW', 'TG', 'QS', 'CC', 'RB', 'JI'))
        self.assertIn("↻  Nochmal prüfen", self.buttons(dlg))
        self.assertIn("Schließen", self.buttons(dlg))


class CheckButtonTooltipTest(unittest.TestCase):
    """The 🩺 in the 🤸 header — the way into the report."""

    def test_the_tooltip_is_in_the_catalog(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        english = ("Check the party list — rounds, the late WW / PD rules,\n"
                   "duplicates, takt and over-long titles.")
        self.assertNotEqual(i18n.t(english), english,
                            "the 🩺 button still explains itself in English")


if __name__ == "__main__":
    unittest.main()
