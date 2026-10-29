#!/usr/bin/env python3
"""🏆 A dance's play length per round — the final may run longer.

Run:  py -m unittest tests.gui.test_round_dance_secs -v

Within one round every heat of a dance is cut at the same length; between
rounds it may change — a final Waltz at 2:00 where the Vorrunde ran 1:30 —
but it does not have to. So the per-round length is an optional override in
⚙ Settings, kept per (round, dance): where none is set the dance's own 🏆
length applies as before. The round is read off the row's round name, which
is a German internal string ('Vorrunde', '2. Zwischenrunde', 'Semifinale',
'Finale'); a party round such as 'Standardrunde 1' is no tournament round.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rounddancesecs_"))

from pathlib import Path
from typing import Any, cast

from PySide6.QtWidgets import QApplication, QWidget

from gui.decks.running_order import Row
from planner.models import MusicEntry
from planner.playing.play_sets import (
    DANCE_SECS_KEY,
    ROUND_DANCE_SECS_KEY,
    ROUND_KINDS,
    ROUND_PD_KEY,
    round_dance_secs_of,
    round_kind,
    round_pd_n_of,
)
from planner.terms import dance_name, round_name
from tests.qt_test_support import reap_widget, stub_window_startup


class RoundKindTest(unittest.TestCase):
    """Which kind of round a round name is."""

    def test_the_planners_round_names(self):
        for name, kind in (("Vorrunde", "first"), ("Zwischenrunde", "inter"),
                           ("1. Zwischenrunde", "inter"),
                           ("3. Zwischenrunde", "inter"),
                           ("Semifinale", "semi"), ("Finale", "final")):
            with self.subTest(name=name):
                self.assertEqual(round_kind(name), kind)

    def test_case_and_other_spellings(self):
        self.assertEqual(round_kind("FINALE"), "final")
        self.assertEqual(round_kind("Final"), "final")
        self.assertEqual(round_kind("Semi-final"), "semi")
        self.assertEqual(round_kind("Halbfinale"), "semi")
        self.assertEqual(round_kind("Viertelfinale"), "inter")

    def test_a_stacked_day_decks_rounds(self):
        """A day plan names its rounds '<competition> — <round>'; the Finale
        and Vorrunde lost their kind there while the Semifinale kept it
        (BUG_REVIEW B7.1)."""
        for name, kind in (("Hgr D Std — Vorrunde", "first"),
                           ("Hgr D Std — 1. Zwischenrunde", "inter"),
                           ("Hgr D Std — Semifinale", "semi"),
                           ("Hgr D Std — Finale", "final")):
            with self.subTest(name=name):
                self.assertEqual(round_kind(name), kind)

    def test_a_competition_named_like_a_round_does_not_make_one(self):
        self.assertIsNone(round_kind("Semi-Pro Cup — Standardrunde 1"))

    def test_a_party_round_or_no_name_is_no_tournament_round(self):
        for name in ("", "Standardrunde 1", "Socialrunde 2", "LW"):
            with self.subTest(name=name):
                self.assertIsNone(round_kind(name))


class RoundDanceSecsOfTest(unittest.TestCase):
    """Reading the stored overrides: nothing guessed at."""

    def test_nothing_stored_is_no_override(self):
        self.assertEqual(round_dance_secs_of({}), {})
        self.assertEqual(round_dance_secs_of({ROUND_DANCE_SECS_KEY: "junk"}), {})

    def test_a_stored_length_is_read_as_seconds(self):
        self.assertEqual(
            round_dance_secs_of({ROUND_DANCE_SECS_KEY: {
                "final": {"WW": 120, "LW": "97"}}}),
            {"final": {"WW": 120, "LW": 97}})

    def test_zero_is_full_and_out_of_bounds_is_pulled_in(self):
        self.assertEqual(
            round_dance_secs_of({ROUND_DANCE_SECS_KEY: {
                "semi": {"PD": 0, "WW": 2, "LW": 99999}}}),
            {"semi": {"PD": 0, "WW": 5, "LW": 20 * 60}})

    def test_an_unknown_round_or_a_bad_entry_is_dropped(self):
        self.assertEqual(
            round_dance_secs_of({ROUND_DANCE_SECS_KEY: {
                "bogus": {"WW": 90}, "first": "junk",
                "inter": {"WW": "1:30x", "TG": None, "SF": 100}}}),
            {"inter": {"SF": 100}})


class RoundPdNOfTest(unittest.TestCase):
    """🐂 Reading the stored Paso Doble pick per round: 0 = full, 1 or 2 =
    after that highlight."""

    def test_nothing_stored_is_no_pick(self):
        self.assertEqual(round_pd_n_of({}), {})
        self.assertEqual(round_pd_n_of({ROUND_PD_KEY: "junk"}), {})

    def test_full_and_the_highlights_are_read(self):
        self.assertEqual(round_pd_n_of({ROUND_PD_KEY: {"final": 0, "first": "2"}}),
                         {"final": 0, "first": 2})

    def test_an_unknown_round_or_a_bad_pick_is_dropped(self):
        self.assertEqual(
            round_pd_n_of({ROUND_PD_KEY: {"bogus": 1, "semi": 3, "inter": None,
                                          "first": -1, "final": 1}}),
            {"final": 1})


class _WindowCase(unittest.TestCase):
    """A real MainWindow: the length runs through its panel wiring, its list
    values and its settings save."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_rounddancesecs_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.win._settings[DANCE_SECS_KEY] = {"WW": 90}
        self.win._settings[ROUND_DANCE_SECS_KEY] = {"final": {"WW": 120}}
        self.panel = self.win._play_panel
        self.b = self.win._deckset.tableB
        self.win._on_table_focused(self.b)   # first use: the 🏆 set

    def play(self, dance, round_name):
        """A `dance` title of the `round_name` round is on the deck."""
        self.win._on_deck_play(self.b)
        self.b._row_meta.append(Row(dance=dance, round_name=round_name))
        self.b._current_play_row = len(self.b._row_meta) - 1
        self.win._playback.path = Path("C:/music/title.mp3")
        self.win._playback.dance = dance
        self.win._sync_dance_len()


class PlaybackTest(_WindowCase):
    """The cut obeys the round's length for the dance — where it has one."""

    def test_the_final_cuts_at_its_own_length(self):
        self.play("WW", "Finale")
        self.assertEqual(self.win._play_limit_secs(), 120)

    def test_a_round_without_an_override_runs_the_dances_length(self):
        self.play("WW", "Vorrunde")
        self.assertEqual(self.win._play_limit_secs(), 90)

    def test_a_list_nudged_off_the_set_has_one_length_for_all(self):
        self.win._list_vals(self.b)["secs"] = 115
        self.play("WW", "Finale")
        self.assertEqual(self.win._play_limit_secs(), 115)

    def test_the_short_track_flag_measures_against_the_round(self):
        cb = self.b._short_secs_cb
        assert cb is not None
        self.assertEqual(cb("WW", "Finale"), 120)
        self.assertEqual(cb("WW", "Vorrunde"), 90)
        self.assertEqual(cb("WW", ""), 90)


class PasoDobleRoundTest(_WindowCase):
    """🐂 The round's Paso Doble pick decides where it stops — while the list
    plays the set's length, like every per-round length."""

    def setUp(self):
        super().setUp()
        self.win._settings[ROUND_PD_KEY] = {"first": 2, "final": 0}
        self.panel.set_pd_highlight_stop(False)
        self.panel.set_pd_highlight_n(1)

    def test_the_vorrunde_stops_after_its_second_highlight(self):
        self.play("PD", "Vorrunde")
        self.assertEqual(self.win._pd_highlight(), (True, 2))
        self.assertTrue(self.win._pd_runs_to_its_highlight())

    def test_the_final_runs_in_full(self):
        self.panel.set_pd_highlight_stop(True)
        self.play("PD", "Finale")
        self.assertFalse(self.win._pd_highlight()[0])
        self.assertFalse(self.win._pd_runs_to_its_highlight())

    def test_a_round_without_a_pick_follows_the_panel(self):
        self.panel.set_pd_highlight_stop(True)
        self.play("PD", "Semifinale")
        self.assertEqual(self.win._pd_highlight(), (True, 1))

    def test_a_list_nudged_off_the_set_follows_the_panel(self):
        self.win._list_vals(self.b)["secs"] = 115
        self.play("PD", "Vorrunde")
        self.assertEqual(self.win._pd_highlight(), (False, 1))

    def test_the_stop_is_armed_on_the_rounds_highlight(self):
        from unittest import mock
        self.play("PD", "Vorrunde")
        path = self.win._playback.path
        self.win._pd_highlights[str(path)] = [30.0, 60.0, 90.0]
        with mock.patch("player.window.main_pd.pd_stop_at",
                        return_value=60.0) as at:
            self.win._arm_pd_stop(path)
        self.assertEqual(at.call_args.args[1], 2)
        self.assertEqual(self.win._pd_stop_at, 60.0)


class PanelTest(_WindowCase):
    """The panel shows the round's length, and edits that one."""

    def test_the_panel_shows_the_rounds_length(self):
        self.play("WW", "Finale")
        self.assertEqual(self.panel.len_lbl.text(), "2:00")
        self.assertFalse(self.panel.len_dance_lbl.isHidden())

    def test_the_label_names_the_round_whose_length_it_shows(self):
        self.play("WW", "Finale")
        text = self.panel.len_dance_lbl.text()
        self.assertIn(dance_name("WW", "WW"), text)
        self.assertIn(round_name("Finale"), text)

    def test_a_round_on_the_dances_length_names_only_the_dance(self):
        self.play("WW", "Vorrunde")
        text = self.panel.len_dance_lbl.text()
        self.assertIn(dance_name("WW", "WW"), text)
        self.assertNotIn(round_name("Vorrunde"), text)

    def test_a_long_label_wraps_rather_than_widening_the_panel(self):
        """'Langsamer Walzer, 2. Zwischenrunde — eigene Länge' on a 250 px
        panel: the −/+ beside the digits must keep their place (Mac)."""
        self.assertTrue(self.panel.len_dance_lbl.wordWrap())

    def test_the_row_picked_in_the_list_decides_before_anything_plays(self):
        self.b.setRowCount(2)
        self.b._row_meta.append(Row(dance="WW", round_name="Vorrunde"))
        self.b._row_meta.append(Row(dance="WW", round_name="Finale"))
        self.b.setCurrentCell(1, 0)
        self.assertEqual(self.panel.len_lbl.text(), "2:00")
        self.b.setCurrentCell(0, 0)
        self.assertEqual(self.panel.len_lbl.text(), "1:30")

    def test_plus_moves_the_rounds_time_and_leaves_the_dances(self):
        self.play("WW", "Finale")
        self.panel._step_len(+1)
        self.assertEqual(self.win._settings[ROUND_DANCE_SECS_KEY],
                         {"final": {"WW": 135}})
        self.assertEqual(self.win._settings[DANCE_SECS_KEY]["WW"], 90)
        self.assertEqual(self.win._play_limit_secs(), 135)

    def test_without_an_override_plus_moves_the_dances_time(self):
        self.play("WW", "Vorrunde")
        self.panel._step_len(+1)
        self.assertEqual(self.win._settings[DANCE_SECS_KEY]["WW"], 105)
        self.assertEqual(self.win._settings[ROUND_DANCE_SECS_KEY],
                         {"final": {"WW": 120}})


class RunningOrderRoundTest(unittest.TestCase):
    """A player-only running order knows its rounds by its strips, not by
    its rows — `round_at` answers for both kinds of list."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_running_order_row_is_in_the_round_its_strip_names(self):
        from gui.table.playlist_table import PlaylistTable
        win = cast(Any, QWidget())
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        songs = [MusicEntry(path=Path(rf"C:\music\WW{i}.mp3"), title=f"WW {i}",
                            dance="WW", duration=180) for i in (1, 2, 3)]
        t = PlaylistTable()
        t.setParent(win)
        t.load_player_list(songs, "🏁 Order", lambda *a: None, None,
                           sections={str(songs[0].path): "Vorrunde",
                                     str(songs[2].path): "Finale"})
        rounds = [t.round_at(row) for row, _m in t._row_meta.numbered()]
        self.assertEqual(rounds, ["Vorrunde", "Vorrunde", "Finale"])

    def order(self, n: int, short_cb=None):
        from gui.table.playlist_table import PlaylistTable
        win = cast(Any, QWidget())
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        songs = [MusicEntry(path=Path(rf"C:\music\WW{i}.mp3"), title=f"WW {i}",
                            dance="WW", duration=180) for i in range(n)]
        t = PlaylistTable()
        t.setParent(win)
        t._short_secs_cb = short_cb
        sections = {str(songs[0].path): "Vorrunde", str(songs[n - 1].path): "Finale"}
        return t, songs, sections

    def label_passes(self, n: int) -> int:
        """How often a load of `n` rows works the strips out from the order."""
        t, songs, sections = self.order(n, short_cb=lambda dance, rnd: 0)
        calls = [0]
        real = t._player_section_labels

        def counted(entries):
            calls[0] += 1
            return real(entries)

        t._player_section_labels = counted
        t.load_player_list(songs, "🏁 Order", lambda *a: None, None,
                           sections=sections)
        return calls[0]

    def test_the_length_column_works_the_rounds_out_once_not_per_row(self):
        """The ⏱ cell asks `round_at` on every row; each answer used to work
        out the whole order again — 0.7 s on a 1200-row running order."""
        self.assertEqual(self.label_passes(60), self.label_passes(6))

    def test_a_row_changed_in_place_is_in_its_new_round(self):
        """The rounds a load hands over end with the load: rows change their
        entry in place later (a swap, a regen), and the order answers then."""
        t, songs, sections = self.order(3)
        t.load_player_list(songs, "🏁 Order", lambda *a: None, None,
                           sections=sections)
        rows = t._row_meta.numbered()
        self.assertEqual([t.round_at(r) for r, _m in rows],
                         ["Vorrunde", "Vorrunde", "Finale"])
        (_r1, m1), (_r2, m2) = rows[1], rows[2]
        m1.entry, m2.entry = m2.entry, m1.entry
        self.assertEqual([t.round_at(r) for r, _m in rows],
                         ["Vorrunde", "Finale", "Finale"])

    def test_a_grid_row_carries_its_round(self):
        from gui.table.playlist_table import PlaylistTable
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t._row_meta.append(None)
        t._row_meta.append(Row(dance="WW", round_name="Semifinale"))
        self.assertEqual(t.round_at(1), "Semifinale")
        self.assertEqual(t.round_at(0), "")
        self.assertEqual(t.round_at(9), "")


class SettingsGridTest(unittest.TestCase):
    """⚙ Settings → 🎛 Play sets: a length per round and dance in the 🏆 box."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def combo(self, dlg, kind, dance):
        return dlg._round_len_combos[(kind, dance)][0]

    def test_untouched_nothing_is_overridden(self):
        self.assertEqual(self.dialog({}).values()[ROUND_DANCE_SECS_KEY], {})

    def test_stored_lengths_come_back_as_they_were(self):
        dlg = self.dialog({ROUND_DANCE_SECS_KEY: {"final": {"WW": 120, "LW": 97},
                                                  "first": {"SA": 0}}})
        self.assertEqual(self.combo(dlg, "final", "WW").currentText(), "2:00")
        self.assertEqual(self.combo(dlg, "final", "LW").currentText(), "1:37")
        self.assertEqual(dlg.values()[ROUND_DANCE_SECS_KEY],
                         {"final": {"WW": 120, "LW": 97}, "first": {"SA": 0}})

    def test_the_paso_doble_picks_full_or_a_highlight_per_round(self):
        """🐂 Marcel: "paso doble per dance setting and per round should
        show full, after highlight 1 and 2, 3 = full … so i can configure
        highlight3 = full for finals and 2 vor vorrunde". Never a time."""
        dlg = self.dialog({ROUND_DANCE_SECS_KEY: {"final": {"PD": 90}}})
        combo = dlg._round_pd_combos["final"]
        self.assertTrue(combo.isEnabled())
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         ["— the dance's length", "full",
                          "after highlight 1", "after highlight 2"])
        self.assertEqual(combo.currentIndex(), 0)
        vals = dlg.values()
        self.assertEqual(vals[ROUND_DANCE_SECS_KEY], {})
        self.assertEqual(vals[ROUND_PD_KEY], {})

    def test_a_rounds_paso_doble_pick_is_saved_and_comes_back(self):
        dlg = self.dialog({ROUND_PD_KEY: {"final": 0}})
        self.assertEqual(dlg._round_pd_combos["final"].currentText(), "full")
        first = dlg._round_pd_combos["first"]
        first.setCurrentIndex(first.findText("after highlight 2"))
        self.assertEqual(dlg.values()[ROUND_PD_KEY], {"final": 0, "first": 2})

    def test_a_rounds_paso_doble_pick_leaves_the_sets_stop_alone(self):
        dlg = self.dialog({})
        first = dlg._round_pd_combos["first"]
        first.setCurrentIndex(first.findText("after highlight 2"))
        self.assertFalse(dlg.values()["tournament_set"]["pd_stop"])

    def test_a_picked_rung_and_a_typed_length_are_saved(self):
        dlg = self.dialog({})
        ww = self.combo(dlg, "semi", "WW")
        ww.setCurrentIndex(ww.findData(120))
        self.combo(dlg, "final", "LW").setEditText("1:37")
        self.assertEqual(dlg.values()[ROUND_DANCE_SECS_KEY],
                         {"semi": {"WW": 120}, "final": {"LW": 97}})

    def test_back_to_the_dances_length_drops_the_override(self):
        dlg = self.dialog({ROUND_DANCE_SECS_KEY: {"final": {"WW": 120}}})
        self.combo(dlg, "final", "WW").setCurrentIndex(0)
        self.assertEqual(dlg.values()[ROUND_DANCE_SECS_KEY], {})

    def test_the_selector_shows_one_list_at_a_time(self):
        """Marcel: per dance is the standard, per round an optional override,
        so "a selector on top saying if per dance or per round and for per
        round in which round" and one list below it like the per-dance one.
        The round picker shows only for per round: "show the selctor with
        vorrunde only wehen per round is selected"."""
        dlg = self.dialog({})
        scope, which = dlg._len_scope_combo, dlg._len_round_combo
        self.assertEqual(scope.currentData(), "dance")
        self.assertTrue(which.isHidden())
        self.assertTrue(dlg._round_len_lbl.isHidden())
        page = dlg._len_stack.currentWidget()
        self.assertTrue(page.isAncestorOf(dlg._dance_len_combos["WW"][0]))

        scope.setCurrentIndex(scope.findData("round"))
        which.setCurrentIndex(which.findData("final"))
        self.assertFalse(which.isHidden())
        self.assertFalse(dlg._round_len_lbl.isHidden())
        self.assertTrue(dlg._dance_len_lbl.isHidden())
        page = dlg._len_stack.currentWidget()
        self.assertTrue(page.isAncestorOf(self.combo(dlg, "final", "WW")))
        self.assertFalse(page.isAncestorOf(self.combo(dlg, "semi", "WW")))
        self.assertFalse(page.isAncestorOf(dlg._dance_len_combos["WW"][0]))
        scope.setCurrentIndex(scope.findData("dance"))
        self.assertTrue(which.isHidden())

    def test_every_round_lists_the_dances_of_the_per_dance_list(self):
        dlg = self.dialog({})
        which = dlg._len_round_combo
        self.assertEqual([which.itemData(i) for i in range(which.count())],
                         list(ROUND_KINDS))
        for kind in ROUND_KINDS:
            with self.subTest(kind=kind):
                # The Paso Doble's is a highlight pick, kept apart.
                self.assertIn(kind, dlg._round_pd_combos)
                self.assertEqual({d for k, d in dlg._round_len_combos if k == kind}
                                 | {"PD"}, set(dlg._dance_len_combos))

    def test_a_length_set_in_a_hidden_round_is_still_saved(self):
        """The selector only shows a list: a round not on screen keeps its
        lengths, and the per-dance ones stay the standard."""
        dlg = self.dialog({ROUND_DANCE_SECS_KEY: {"final": {"WW": 120}}})
        scope = dlg._len_scope_combo
        scope.setCurrentIndex(scope.findData("round"))
        dlg._len_round_combo.setCurrentIndex(dlg._len_round_combo.findData("first"))
        scope.setCurrentIndex(scope.findData("dance"))
        self.assertEqual(dlg.values()[ROUND_DANCE_SECS_KEY], {"final": {"WW": 120}})

    def test_its_text_is_translated(self):
        # Widget text reaches the catalog through the text hook, not a t()
        # call, so test_i18n_catalog_keys never sees it.
        from planner.i18n.lang_de import CATALOG
        dlg = self.dialog({})
        combo = self.combo(dlg, "final", "WW")
        scope = dlg._len_scope_combo
        for text in (dlg._round_len_lbl.text(), combo.itemText(0),
                     combo.toolTip(), dlg._len_scope_lbl.text(),
                     scope.itemText(0), scope.itemText(1), scope.toolTip(),
                     dlg._len_round_combo.toolTip()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
