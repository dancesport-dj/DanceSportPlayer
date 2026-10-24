#!/usr/bin/env python3
"""🏆 The tournament set's own play length per dance.

Run:  py -m unittest tests.gui.test_dance_play_secs -v

A heat is timed per dance — a Viennese Waltz cut at 1:30, a Waltz at 1:37 —
so the 🏆 set can give a dance a length of its own, kept in ⚙ Settings. It only
counts while a list stands on the set: nudge that list's length by hand and
its one length is every dance's again. The ▶ Playing panel shows which length
is valid right now, with the dance named under the digits, and its −/+ and a
typed length change that dance's time rather than the list's.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dancesecs_"))

from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.decks.running_order import Row
from planner.playing.play_sets import (
    DANCE_SECS_KEY, dance_secs_of, play_set_of)
from planner.terms import dance_name
from tests.qt_test_support import reap_widget, stub_window_startup


class DanceSecsOfTest(unittest.TestCase):
    """Reading the stored lengths: nothing guessed at."""

    def test_nothing_stored_is_the_shipped_lengths(self):
        """A fresh install, or a hand-edit that is no list of lengths: the
        shipped per-dance lengths (see test_play_set_defaults)."""
        self.assertEqual(dance_secs_of({})["WW"], 90)
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: "junk"}),
                         dance_secs_of({}))

    def test_a_stored_length_is_read_as_seconds(self):
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: {"WW": 90, "LW": "97"}}),
                         {"WW": 90, "LW": 97})

    def test_zero_is_full(self):
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: {"PD": 0}}), {"PD": 0})

    def test_a_length_out_of_bounds_is_pulled_in(self):
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: {"WW": 2, "LW": 99999}}),
                         {"WW": 5, "LW": 20 * 60})

    def test_an_entry_that_is_no_length_is_dropped(self):
        self.assertEqual(dance_secs_of({DANCE_SECS_KEY: {"WW": "1:30x", "LW": None,
                                                         "TG": 100}}),
                         {"TG": 100})


class _WindowCase(unittest.TestCase):
    """A real MainWindow: the length runs through its panel wiring, its list
    values and its settings save."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_dancesecs_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win._settings[DANCE_SECS_KEY] = {"WW": 90}
        self.panel = self.win._play_panel
        self.b = self.win._deckset.tableB
        self.win._on_table_focused(self.b)   # first use: the 🏆 set

    def play(self, table, dance):
        """A `dance` title of `table` is on the deck."""
        self.win._on_deck_play(table)
        if not len(table._row_meta):
            table._row_meta.append(Row(dance=dance))
        table._current_play_row = 0
        self.win._playback.path = Path("C:/music/title.mp3")
        self.win._playback.dance = dance
        self.win._sync_dance_len()


class PlaybackTest(_WindowCase):
    """The cut obeys the dance's own length — on the set only."""

    def test_a_list_on_the_set_cuts_a_dance_at_its_own_length(self):
        self.play(self.b, "WW")
        self.assertEqual(self.win._play_limit_secs(), 90)

    def test_a_dance_without_its_own_runs_the_sets_length(self):
        self.play(self.b, "LW")
        self.assertEqual(self.win._play_limit_secs(),
                         play_set_of(self.win._settings, "tournament")["secs"])

    def test_a_list_nudged_off_the_set_has_one_length_for_all(self):
        self.win._list_vals(self.b)["secs"] = 115
        self.play(self.b, "WW")
        self.assertEqual(self.win._play_limit_secs(), 115)

    def test_auto_advance_and_the_pause_keep_the_dances_length(self):
        """⏭ and the pause are how a list walks on, not how long a title
        runs. Marcel's Vorrunde on ⏭ Auto cut every dance at the set's 1:45."""
        self.panel.advance_check.setChecked(True)
        self.panel.pause_check.setChecked(True)
        self.assertTrue(self.win._list_vals(self.b)["advance"])
        self.play(self.b, "WW")
        self.assertEqual(self.win._play_limit_secs(), 90)
        self.assertEqual(self.panel.len_lbl.text(), "1:30")

    def test_the_short_track_flag_measures_against_the_dance(self):
        self.assertEqual(self.b._short_secs_cb("WW"), 90)
        self.assertEqual(self.b._short_secs_cb("LW"), 105)


class PanelTest(_WindowCase):
    """The panel says which length is valid, and edits that one."""

    def test_the_panel_shows_the_dances_own_length_and_names_it(self):
        self.play(self.b, "WW")
        self.assertEqual(self.panel.len_lbl.text(), "1:30")
        self.assertFalse(self.panel.len_dance_lbl.isHidden())
        self.assertIn(dance_name("WW", "WW"), self.panel.len_dance_lbl.text())
        # No 🏆: on a Mac the wide glyph ran over the −/+ above it.
        self.assertNotIn("🏆", self.panel.len_dance_lbl.text())

    def test_a_dance_without_its_own_shows_the_lists_length(self):
        self.play(self.b, "LW")
        self.assertEqual(self.panel.len_lbl.text(), "1:45")
        self.assertTrue(self.panel.len_dance_lbl.isHidden())

    def test_the_row_picked_in_the_list_decides_before_anything_plays(self):
        self.b.setRowCount(2)
        self.b._row_meta.append(Row(dance="LW"))
        self.b._row_meta.append(Row(dance="WW"))
        self.b.setCurrentCell(1, 0)
        self.assertEqual(self.panel.len_lbl.text(), "1:30")
        self.b.setCurrentCell(0, 0)
        self.assertEqual(self.panel.len_lbl.text(), "1:45")

    def test_plus_moves_the_dances_time_not_the_lists(self):
        self.play(self.b, "WW")
        self.panel._step_len(+1)
        self.assertEqual(self.win._settings[DANCE_SECS_KEY]["WW"], 105)
        self.assertEqual(self.win._list_vals(self.b)["secs"], 105)
        self.assertEqual(self.panel.play_secs(), 105)
        self.assertTrue(self.panel.tournament_btn.isChecked(),
                        "the list still stands on the 🏆 set")
        self.assertEqual(self.win._play_limit_secs(), 105)

    def test_a_fresh_install_nudges_one_dance_and_keeps_the_others(self):
        """Nothing stored yet: the nudged dance is written beside the shipped
        lengths, not instead of them."""
        del self.win._settings[DANCE_SECS_KEY]
        self.play(self.b, "WW")
        self.panel._step_len(+1)
        stored = self.win._settings[DANCE_SECS_KEY]
        self.assertEqual(stored["WW"], 105)
        self.assertEqual(stored["TG"], 97)
        self.assertEqual(stored["LW"], 90)

    def test_a_typed_length_lands_on_the_dance(self):
        self.play(self.b, "WW")
        self.panel._on_len_typed()
        self.panel._len_edit.setText("1:35")
        self.panel._commit_len_typed()
        self.assertEqual(self.win._settings[DANCE_SECS_KEY]["WW"], 95)
        self.assertEqual(self.panel.len_lbl.text(), "1:35")
        self.assertEqual(self.win._play_limit_secs(), 95)

    def test_off_the_set_the_panel_edits_the_lists_length_again(self):
        self.win._list_vals(self.b)["secs"] = 115
        self.win._on_table_focused(self.win._deckset.tableA)
        self.win._on_table_focused(self.b)
        self.play(self.b, "WW")
        self.assertTrue(self.panel.len_dance_lbl.isHidden())
        self.panel._step_len(+1)
        self.assertEqual(self.win._settings[DANCE_SECS_KEY]["WW"], 90)
        self.assertEqual(self.win._list_vals(self.b)["secs"], 130)


class SettingsGridTest(unittest.TestCase):
    """⚙ Settings → 🎛 Play sets: a length per dance in the 🏆 box."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def combo(self, dlg, dance):
        return dlg._dance_len_combos[dance][0]

    def test_untouched_the_shipped_lengths_are_written(self):
        self.assertEqual(self.dialog({}).values()[DANCE_SECS_KEY],
                         dance_secs_of({}))

    def test_a_list_emptied_before_stays_empty(self):
        # …but for the Paso Doble, which has no "set's length" to fall back on.
        self.assertEqual(
            self.dialog({DANCE_SECS_KEY: {}}).values()[DANCE_SECS_KEY],
            {"PD": 0})

    def test_stored_lengths_come_back_as_they_were(self):
        dlg = self.dialog({DANCE_SECS_KEY: {"WW": 90, "LW": 97, "PD": 0}})
        self.assertEqual(self.combo(dlg, "WW").currentText(), "1:30")
        self.assertEqual(self.combo(dlg, "LW").currentText(), "1:37")
        self.assertEqual(dlg.values()[DANCE_SECS_KEY],
                         {"WW": 90, "LW": 97, "PD": 0})

    def test_a_picked_rung_and_a_typed_length_are_saved(self):
        dlg = self.dialog({DANCE_SECS_KEY: {}})
        ww = self.combo(dlg, "WW")
        ww.setCurrentIndex(ww.findData(90))
        self.combo(dlg, "LW").setEditText("1:37")
        self.assertEqual(dlg.values()[DANCE_SECS_KEY],
                         {"WW": 90, "LW": 97, "PD": 0})

    def test_back_to_the_sets_length_drops_the_dance(self):
        dlg = self.dialog({DANCE_SECS_KEY: {"WW": 90}})
        self.combo(dlg, "WW").setCurrentIndex(0)
        self.assertEqual(dlg.values()[DANCE_SECS_KEY], {"PD": 0})

    def test_a_typed_slip_keeps_the_length_it_opened_on(self):
        dlg = self.dialog({DANCE_SECS_KEY: {"WW": 90}})
        self.combo(dlg, "WW").setEditText("1:")
        self.assertEqual(dlg.values()[DANCE_SECS_KEY], {"WW": 90, "PD": 0})


class PasoDobleLengthTest(unittest.TestCase):
    """🐂 Marcel: "paso doble has only full as option i would like to
    configure there the paso doble highlight stop 1,2,3 besides full, other
    values makes no sense. if selected it should fill or disable the pd stop
    after highlight checkbox"."""

    setUpClass = SettingsGridTest.setUpClass
    dialog = SettingsGridTest.dialog
    combo = SettingsGridTest.combo

    def pd(self, dlg):
        return dlg._set_widgets["tournament"]["pd"]

    def test_full_or_one_of_two_highlights(self):
        """Marcel: "full, after highlight 1 and 2, 3 = full"."""
        combo = self.combo(self.dialog({}), "PD")
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         ["full", "after highlight 1", "after highlight 2"])
        self.assertFalse(combo.isEditable())

    def test_a_third_highlight_in_the_set_reads_as_full(self):
        dlg = self.dialog({"tournament_set": {"pd_stop": True, "pd_n": 3}})
        self.assertEqual(self.combo(dlg, "PD").currentText(), "full")

    def test_a_highlight_ticks_the_stop_and_picks_it(self):
        dlg = self.dialog({})
        self.combo(dlg, "PD").setCurrentIndex(2)
        stop, n, _delay = self.pd(dlg)
        self.assertTrue(stop.isChecked())
        self.assertEqual(n.value(), 2)
        vals = dlg.values()
        self.assertEqual(vals["tournament_set"]["pd_stop"], True)
        self.assertEqual(vals["tournament_set"]["pd_n"], 2)
        # The highlight ends it, so the dance itself runs in full.
        self.assertEqual(vals[DANCE_SECS_KEY]["PD"], 0)

    def test_full_unticks_the_stop(self):
        dlg = self.dialog({"tournament_set": {"pd_stop": True, "pd_n": 2}})
        self.combo(dlg, "PD").setCurrentIndex(0)
        self.assertFalse(self.pd(dlg)[0].isChecked())
        self.assertEqual(dlg.values()["tournament_set"]["pd_stop"], False)

    def test_it_opens_on_the_sets_highlight_stop(self):
        self.assertEqual(self.combo(self.dialog({}), "PD").currentIndex(), 0)
        dlg = self.dialog({"tournament_set": {"pd_stop": True, "pd_n": 2}})
        self.assertEqual(self.combo(dlg, "PD").currentIndex(), 2)

    def test_it_follows_the_checkbox_and_the_number(self):
        dlg = self.dialog({})
        stop, n, _delay = self.pd(dlg)
        stop.setChecked(True)
        n.setValue(1)
        self.assertEqual(self.combo(dlg, "PD").currentIndex(), 1)
        stop.setChecked(False)
        self.assertEqual(self.combo(dlg, "PD").currentIndex(), 0)

    def test_the_party_sets_paso_doble_is_left_alone(self):
        dlg = self.dialog({})
        self.combo(dlg, "PD").setCurrentIndex(2)
        party = dlg.values()["party_set"]
        self.assertEqual((party["pd_stop"], party["pd_n"]), (True, 2))
        dlg._set_widgets["party"]["pd"][0].setChecked(False)
        self.assertEqual(self.combo(dlg, "PD").currentIndex(), 2)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        combo = self.combo(self.dialog({}), "PD")
        for text in ("after highlight %d", combo.toolTip()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
