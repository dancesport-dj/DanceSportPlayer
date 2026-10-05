#!/usr/bin/env python3
"""Tests for the left config panel — the dance checkboxes it hands to a run.

Run:  py -m unittest tests.gui.test_config_panel -v

`get_config()` is what ⚡ Generate and 🤖 AI Playlist build from, so an empty
dance list there stops a run dead. The panel must never arrive at one on its
own, least of all in the modes that hide the checkboxes.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cfgpanel_"))

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from gui.config_panel import ConfigPanel, mark_index_gaps  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class DanceSelectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        panel = ConfigPanel()
        self.addCleanup(reap_widget, panel)
        return panel

    def _dances(self, panel):
        return panel.get_config()[3]

    def test_a_fresh_panel_offers_the_style_defaults(self):
        self.assertEqual(self._dances(self._panel()),
                         ["SA", "CC", "RB", "PD", "JI"])

    def test_a_decks_own_dance_set_is_applied(self):
        panel = self._panel()
        panel.apply_config(style="Latin", cls="S", dances=["SA", "JI"])
        self.assertEqual(self._dances(panel), ["SA", "JI"])

    def test_an_empty_dance_set_leaves_the_defaults_ticked(self):
        # A Theme / player deck never fills `_dances`, so focusing one used to
        # arrive here with [] and untick everything — invisibly, because those
        # modes hide the dance box. The next run then refused: "Please select
        # at least one dance."
        panel = self._panel()
        panel.apply_config(mode="Theme", style="Latin", cls="S", dances=[])
        self.assertEqual(self._dances(panel), ["SA", "CC", "RB", "PD", "JI"])

    def test_the_dance_box_is_hidden_in_theme_mode(self):
        # The reason an empty set may not be taken at face value: nobody could
        # see it, let alone fix it.
        panel = self._panel()
        panel.show()
        panel.apply_config(mode="Theme")
        self.assertFalse(panel._comp.isVisible())

    def test_no_dance_set_at_all_keeps_the_defaults(self):
        panel = self._panel()
        panel.apply_config(style="Standard", cls="S")
        self.assertEqual(self._dances(panel), ["LW", "TG", "WW", "SF", "QS"])

    def test_switching_style_ticks_that_styles_full_set(self):
        """A subset was picked for the style it was picked in; the style being
        switched to starts from its own defaults, never from an empty box."""
        panel = self._panel()
        panel.apply_config(style="Latin", cls="S", dances=["SA", "JI"])
        panel.style_combo.setCurrentText("Standard")
        self.assertEqual(self._dances(panel), ["LW", "TG", "WW", "SF", "QS"])
        panel.style_combo.setCurrentText("Latin")
        self.assertEqual(self._dances(panel), ["SA", "CC", "RB", "PD", "JI"])

    def test_from_c_upwards_all_five_dances_are_ticked(self):
        panel = self._panel()
        for cls in ("C", "B", "A", "S"):
            panel.apply_config(style="Standard", cls=cls)
            self.assertEqual(self._dances(panel),
                             ["LW", "TG", "WW", "SF", "QS"], cls)
            panel.apply_config(style="Latin", cls=cls)
            self.assertEqual(self._dances(panel),
                             ["SA", "CC", "RB", "PD", "JI"], cls)

    def test_the_d_class_dances_four(self):
        """D dances neither the Wiener Walzer nor the Paso Doble."""
        panel = self._panel()
        panel.apply_config(style="Standard", cls="D")
        self.assertEqual(self._dances(panel), ["LW", "TG", "SF", "QS"])
        panel.apply_config(style="Latin", cls="D")
        self.assertEqual(self._dances(panel), ["SA", "CC", "RB", "JI"])

    def test_switching_class_up_from_d_adds_the_fifth_dance(self):
        panel = self._panel()
        panel.apply_config(style="Standard", cls="D")
        panel.class_combo.setCurrentText("C")
        self.assertEqual(self._dances(panel), ["LW", "TG", "WW", "SF", "QS"])

    def test_a_dance_set_no_style_covers_falls_back_to_the_defaults(self):
        """An unusable stored set must not leave every box empty -- Generate
        would refuse to start and the panel would not say why."""
        panel = self._panel()
        panel.apply_config(style="Standard", cls="S", dances=["ZZ", "YY"])
        self.assertEqual(self._dances(panel), ["LW", "TG", "WW", "SF", "QS"])


class AiLogButtonTest(unittest.TestCase):
    """The 💬 button beside 🤖: the way back into the kept conversation."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        panel = ConfigPanel()
        self.addCleanup(reap_widget, panel)
        return panel

    def test_it_stays_out_of_the_way_until_there_is_a_conversation(self):
        panel = self._panel()
        panel.show()
        self.assertFalse(panel.ai_log_btn.isVisible())

    def test_a_click_asks_for_the_transcript(self):
        panel = self._panel()
        panel.ai_log_btn.setVisible(True)
        seen = []
        panel.ai_log_requested.connect(lambda: seen.append(True))
        panel.ai_log_btn.click()
        self.assertEqual(seen, [True])


class SourceSelectorTest(unittest.TestCase):
    """"Draw tracks from": which pool the next ⚡ Generate is allowed to use."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        panel = ConfigPanel()
        self.addCleanup(reap_widget, panel)
        return panel

    def test_a_fresh_panel_draws_from_the_favorites_library(self):
        self.assertEqual(self._panel().get_source(), ("library", ""))

    def test_the_m3u_path_row_only_shows_for_the_m3u_source(self):
        panel = self._panel()
        panel.show()
        self.assertFalse(panel._source_m3u_row.isVisible())
        panel.source_combo.setCurrentIndex(panel.source_combo.findData("m3u"))
        self.assertTrue(panel._source_m3u_row.isVisible())
        panel.source_combo.setCurrentIndex(panel.source_combo.findData("wishlists"))
        self.assertFalse(panel._source_m3u_row.isVisible())

    def test_a_browsed_file_selects_the_m3u_source(self):
        panel = self._panel()
        panel.set_source_m3u("C:/lists/party.m3u")
        self.assertEqual(panel.get_source(), ("m3u", "C:/lists/party.m3u"))

    def test_a_stale_path_never_leaks_into_another_source(self):
        panel = self._panel()
        panel.set_source_m3u("C:/lists/party.m3u")
        panel.source_combo.setCurrentIndex(panel.source_combo.findData("wishlists"))
        self.assertEqual(panel.get_source(), ("wishlists", ""))

    def test_browse_asks_the_window_for_a_file(self):
        panel = self._panel()
        seen = []
        panel.m3u_source_requested.connect(lambda: seen.append(True))
        panel._source_m3u_row.findChild(QPushButton).click()
        self.assertEqual(seen, [True])

    def test_clearing_a_deck_puts_the_source_back_to_the_library(self):
        """reset_to_defaults runs on a cleared deck — a pool picked for the last
        playlist must not quietly plan the next one."""
        panel = self._panel()
        panel.set_source_m3u("C:/lists/party.m3u")
        panel.reset_to_defaults()
        self.assertEqual(panel.get_source(), ("library", ""))


class IndexGapMarkingTest(unittest.TestCase):
    """The status block's 'analyzed/total' pairs, and the 🧱 shortcut beside it.

    Six index lines of flat grey counts hid the one thing worth acting on, so
    an index that is still short is marked — and only that number, never the
    total and never a finished index. While anything is unanalyzed, the build
    that fixes it sits right there.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        panel = ConfigPanel()
        self.addCleanup(reap_widget, panel)
        return panel

    def test_only_the_short_count_is_marked_not_the_total(self):
        got = mark_index_gaps("librosa: Favorites 1,200/3,638")
        self.assertIn('<span style="color:#c77700">1,200</span>/3,638', got)

    def test_a_complete_index_keeps_its_grey(self):
        got = mark_index_gaps("librosa: Favorites 3,638/3,638")
        self.assertNotIn("<span", got)

    def test_every_pair_on_a_line_is_judged_on_its_own(self):
        got = mark_index_gaps("librosa: Favorites 3/3 · Repository 1/9")
        self.assertIn("Favorites 3/3", got)
        self.assertIn('<span style="color:#c77700">1</span>/9', got)

    def test_the_lines_survive_as_rich_text(self):
        got = mark_index_gaps("Library: 10 files\nFavorites: 10")
        self.assertIn("<br>", got)
        self.assertNotIn("\n", got)

    def test_library_text_can_never_smuggle_in_markup(self):
        """The block quotes folder names — a stray < would eat the rest."""
        self.assertIn("&lt;none&gt;", mark_index_gaps("Search mode: <none>"))

    def test_the_build_button_hides_while_everything_is_analyzed(self):
        panel = self._panel()
        panel.show()
        panel.set_library_status("Library: 10 files", n_unanalyzed=0)
        self.assertFalse(panel.build_all_btn.isVisible())

    def test_the_build_button_appears_for_any_short_favorites_index(self):
        """Every file has a librosa vector, but e.g. loudness is behind."""
        panel = self._panel()
        panel.show()
        panel.set_library_status("Loudness: Favorites 3/9", n_unanalyzed=0,
                                 needs_build=True)
        self.assertTrue(panel.build_all_btn.isVisible())
        self.assertIn("not complete", panel.build_all_btn.toolTip())

    def test_the_build_button_appears_with_unanalyzed_files(self):
        panel = self._panel()
        panel.show()
        panel.set_library_status("Library: 10 files", n_unanalyzed=4)
        self.assertTrue(panel.build_all_btn.isVisible())
        self.assertIn("4", panel.build_all_btn.toolTip())

    def test_a_click_asks_the_window_to_build(self):
        panel = self._panel()
        seen = []
        panel.build_all_requested.connect(lambda: seen.append(True))
        panel.build_all_btn.click()
        self.assertEqual(seen, [True])

    def test_the_status_text_reaches_the_label_coloured(self):
        panel = self._panel()
        panel.set_library_status("librosa: Favorites 1/9", n_unanalyzed=8)
        self.assertIn("#c77700", panel.status_lbl.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
