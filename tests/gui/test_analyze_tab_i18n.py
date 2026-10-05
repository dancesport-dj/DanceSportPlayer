#!/usr/bin/env python3
"""⚗ The analysis tab of ⚙ Settings, in a German app.

Run:  py -m unittest tests.gui.test_analyze_tab_i18n -v

"Analyse Setting Screen is missing translations." The 🐘 Heavy group beside it
is German, which is what makes the gap so visible: everything on the ⚗ tab
that a number, a file count or an availability check goes into was built by an
f-string or glued with `+`, and a string in either shape reaches `t()` as a
sentence no catalog can hold.

  ⚡ Light — …            two whole captions, picked by the build flavour
  🔬  Analyze audio …     carries "— 7 files to do" or "✓ all cached"
  🎚️  librosa indexed: —  six captions, all glued to their coverage by
                          `_index_label`
  🧠  OpenL3 …            glued to "  – not installed" when it is missing
  🎙️  Analyze vocals …    the same glue

The two 🎛 Play-set blurbs and the 🔇 sound-card tooltip are the same bug on
the neighbouring tabs of the same dialog, so they are settled here with it.

`DEFAULT_LANGUAGE` is English and `t()` is then the identity, so only a test
that switches the language itself can see a missing entry.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_analyze_i18n_"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QGroupBox, QLabel)

from gui.dialogs import SettingsDialog  # noqa: E402
from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Analyze(unittest.TestCase):
    """A real ⚙ Settings dialog, built offscreen under one language.

    The heavy models are pinned absent and the flavour to "dev" so the group
    is built on every machine and both "– not installed" captions appear —
    otherwise the test would say something different on a box that happens to
    have OpenL3 installed."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def dlg(self, language, n_unanalyzed=0):
        i18n.set_active(language)
        i18n.install_text_hook()
        with mock.patch("planner.config.build_flavor", return_value="dev"), \
             mock.patch("planner.config.player_build", return_value=False), \
             mock.patch("planner.embeddings.openl3_available", return_value=False), \
             mock.patch("planner.vocals.demucs_available", return_value=False):
            dlg = SettingsDialog({}, n_unanalyzed=n_unanalyzed)
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def labels(dlg):
        return [w.text() for w in dlg.findChildren(QLabel)]

    @staticmethod
    def titles(dlg):
        return [w.title() for w in dlg.findChildren(QGroupBox)]


class LightGroupTest(_Analyze):
    """The ⚡ group heading — its 🐘 sibling has been German all along."""

    def test_the_lite_build_heading(self):
        said = self.titles(self.dlg("de"))
        self.assertIn("⚡ Leicht — librosa/ffmpeg, läuft in jeder "
                      "Installation (Lite-Build)", said, said)


class AnalyzeButtonTest(_Analyze):
    """Both captions of 🔬 Analyze audio — the count decides which."""

    def test_with_files_left_to_do(self):
        said = self.dlg("de", n_unanalyzed=7)._analyze_btn.text()
        self.assertEqual("🔬  Audio analysieren (Timbre) — 7 Dateien offen",
                         said)

    def test_with_everything_cached(self):
        said = self.dlg("de")._analyze_btn.text()
        self.assertEqual("🔬  Audio neu analysieren (Timbre)  "
                         "✓ alles im Cache", said)


class IndexLabelTest(_Analyze):
    """The six grey "… indexed:  —" captions under the buttons."""

    def test_every_coverage_caption(self):
        said = self.labels(self.dlg("de"))
        for want in ("🎚️  librosa indiziert:  —",
                     "🎼  Chroma indiziert:  —",
                     "📊  Lautheit gemessen:  —",
                     "🐂  PD-Höhepunkte erkannt:  —",
                     "🔇  Stillen geprüft:  —",
                     "🧠  OpenL3 indiziert:  —"):
            self.assertIn(want, said, "%r is still English" % want)


class NotInstalledTest(_Analyze):
    """A model that is not there says so — glued on, in both places."""

    def test_the_openl3_combo_entry(self):
        combo = self.dlg("de")._embed_combo
        said = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn("🧠  OpenL3-Index „klingt ähnlich“  – nicht installiert",
                      said, said)

    def test_the_demucs_button(self):
        self.assertEqual("🎙️  Gesang analysieren (Demucs)…  – nicht installiert",
                         self.dlg("de")._vocals_btn.text())


class PlaySetBlurbTest(_Analyze):
    """The two grey lines under 🏆 Tournament set and 🎉 Party set."""

    def test_both_blurbs(self):
        said = self.labels(self.dlg("de"))
        self.assertIn("Die Werte, mit denen eine Runde läuft — gedrückt, um "
                      "sie zurückzuholen, nachdem eine Partyliste das Panel "
                      "woandershin gezogen hat.", said, "the 🏆 blurb is still English")
        self.assertIn("Wird von selbst angewandt, sobald du aus der 🤸 "
                      "Eintanzen-/Partyliste abspielst, und zurückgeschaltet, "
                      "wenn ein Turnier-Deck übernimmt.", said, "the 🎉 blurb is still English")


class HissTooltipTest(_Analyze):
    """The 🔇 sound-card check box — its caption was translated, its tooltip
    carries the idle seconds through an f-string and was not."""

    def test_the_tooltip(self):
        dlg = self.dlg("de")
        tip = next(w.toolTip() for w in dlg.findChildren(QCheckBox)
                   if w is dlg._release_audio_chk)
        self.assertIn("Eine Onboard-Soundkarte hebt die Stummschaltung", tip,
                      tip)
        self.assertIn("nach 5 s Stille", tip, tip)


class EnglishIsUnchangedTest(_Analyze):
    """The catalog is a lookup on the English string, so English has to come
    back byte for byte — the f-strings that became templates most of all."""

    def test_the_captions_read_the_way_they_did(self):
        dlg = self.dlg("en", n_unanalyzed=7)
        self.assertEqual("🔬  Analyze audio (timbre) — 7 files to do",
                         dlg._analyze_btn.text())
        self.assertEqual("🎙️  Analyze vocals (Demucs)…  – not installed",
                         dlg._vocals_btn.text())
        self.assertIn("⚡ Light — librosa/ffmpeg, works in every install "
                      "(lite build)", self.titles(dlg))
        self.assertIn("🎚️  librosa indexed:  —", self.labels(dlg))


if __name__ == "__main__":
    unittest.main()
