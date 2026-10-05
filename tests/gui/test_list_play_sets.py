#!/usr/bin/env python3
"""Every list keeps its own play values.

Run:  py -m unittest tests.gui.test_list_play_sets -v

One player, several lists: the 🤸 party list runs full length and hands-free
while the tournament deck beside it cuts at 1:40 and is started title by title.
So the values a play set covers — play length, fade, ⏭, the pause switch,
loudness, 🔈, the double-click and the TSO pitch — belong to the LIST.

The play panel shows and edits the values of the list last clicked. Playback
runs on the values of the list that is playing, which need not be the same
one. And nothing is re-applied behind the operator's back: a list is given the
set of its kind once, the first time it is used, and from then on only a hand
changes it. Switching lists used to re-apply the set on every title, which
turned a play length nudged from 1:40 to 1:55 back into 1:40 after one party
song.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_listplay_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.running_order import Row  # noqa: E402
from planner.play_sets import play_set_of, tso_of  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _WindowCase(unittest.TestCase):
    """A real MainWindow — the binding runs through its focus, its play-panel
    wiring and its save, none of which a stand-in would exercise."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_listplay_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def window(self):
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        return win

    def setUp(self):
        self.win = self.window()
        self.panel = self.win._play_panel
        self.a = self.win._tableA
        self.b = self.win._tableB
        self.party = self.win._warmup_table

    def vals(self, table):
        return self.win._list_vals(table)

    def click(self, table):
        self.win._on_table_focused(table)

    def play(self, table, row=0):
        """A title of `table` starts: what `_on_deck_play` does, then the ▶
        mark the play callback sets right after it."""
        self.win._on_deck_play(table)
        # The play cursor names a placed track: give it a row to play from.
        while len(table._row_meta) <= row:
            table._row_meta.append(Row())
        table._current_play_row = row

    def set_of(self, which):
        return play_set_of(self.win._settings, which)


class BindingTest(_WindowCase):
    """The panel shows the list last clicked, and its edits go there."""

    def test_the_panel_starts_on_the_first_deck(self):
        self.assertIs(self.win._panel_list(), self.a)

    def test_the_first_deck_keeps_what_the_panel_showed(self):
        """Start-up restored the panel from the settings — that is deck A's,
        not something to overwrite with a set."""
        shown = self.panel.play_set()
        self.assertEqual({k: v for k, v in self.vals(self.a).items()
                          if k != "tso"}, shown)

    def test_a_list_seen_for_the_first_time_gets_the_set_of_its_kind(self):
        self.win._settings["tournament_set"] = dict(
            self.set_of("tournament"), secs=105)
        self.click(self.b)
        self.assertEqual(self.panel.play_set(), self.set_of("tournament"))
        self.assertEqual(self.panel.play_secs(), 105)
        self.click(self.party)
        self.assertEqual(self.panel.play_set(), self.set_of("party"))

    def test_a_wishlist_plays_full_titles_one_at_a_time(self):
        """⭐ Wishlists play requests and background music: each title to its
        own end, and nothing starts by itself. Neither play set is applied —
        not even one edited in ⚙ Settings."""
        self.win._settings["party_set"] = dict(
            self.set_of("party"), secs=200, advance=True)
        self.win._settings["tournament_set"] = dict(
            self.set_of("tournament"), secs=105, advance=True)
        for wish in self.win._wishlists:
            self.click(wish)
            self.assertEqual(self.panel.play_secs(), 0)
            self.assertIs(self.vals(wish)["secs"], 0)
            self.assertIs(self.vals(wish)["advance"], False)
            self.assertIs(self.vals(wish)["tso"], False)

    def test_the_tso_pitch_is_seeded_with_the_set_too(self):
        self.assertIs(self.vals(self.party)["tso"],
                      tso_of(self.win._settings, "party"))
        self.assertIs(self.vals(self.b)["tso"],
                      tso_of(self.win._settings, "tournament"))

    def test_a_click_shows_the_lists_own_values(self):
        self.vals(self.b)["secs"] = 115
        self.click(self.b)
        self.assertEqual(self.panel.play_secs(), 115)

    def test_a_click_writes_nothing_into_either_list(self):
        before_a = dict(self.vals(self.a))
        self.vals(self.b)["secs"] = 115
        before_b = dict(self.vals(self.b))
        self.click(self.b)
        self.click(self.a)
        self.assertEqual(self.vals(self.a), before_a)
        self.assertEqual(self.vals(self.b), before_b)

    def test_a_panel_edit_goes_into_the_clicked_list_only(self):
        self.click(self.b)
        before_a = dict(self.vals(self.a))
        was = self.vals(self.b)["secs"]
        self.panel._step_len(-1)           # as a hand on the length ladder
        self.assertEqual(self.vals(self.b)["secs"], self.panel.play_secs())
        self.assertNotEqual(self.vals(self.b)["secs"], was)
        self.assertEqual(self.vals(self.a), before_a)

    def test_the_lights_follow_the_clicked_list(self):
        self.click(self.party)
        self.assertTrue(self.panel.party_btn.isChecked())
        self.click(self.b)
        self.assertFalse(self.panel.party_btn.isChecked())
        self.assertTrue(self.panel.tournament_on())


class SwitchToastTest(_WindowCase):
    """A click that puts other values on the panel says so, like 🎉 and 🏆 do
    — the operator should not have to read eight controls to notice."""

    def setUp(self):
        super().setUp()
        from unittest import mock
        self.win.show()
        self.toasts = []
        patcher = mock.patch("player.main_player._show_toast",
                             lambda _w, text, *_a: self.toasts.append(text))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_switching_to_the_party_list_names_the_set_and_what_changed(self):
        self.click(self.party)
        self.assertEqual(len(self.toasts), 1)
        head, *lines = self.toasts[0].split("\n")
        self.assertIn("🎉", head)
        self.assertIn("Party set", head)
        self.assertIn("play length → full", lines)

    def test_switching_back_names_the_tournament_set(self):
        self.click(self.party)
        self.click(self.a)
        self.assertIn("Tournament set", self.toasts[-1].split("\n")[0])

    def test_a_list_on_its_own_values_is_named(self):
        self.vals(self.b)["secs"] = 115
        self.click(self.b)
        head, *lines = self.toasts[0].split("\n")
        self.assertIn(self.win.deck(self.b).title, head)
        self.assertIn("play length → 1:55", lines)

    def test_a_list_on_the_same_values_says_nothing(self):
        self.vals(self.b).update(self.vals(self.a))
        self.click(self.b)
        self.assertEqual(self.toasts, [])

    def test_the_tso_pitch_is_listed_while_it_moves(self):
        self.click(self.party)
        self.assertIn("TSO tempo equalize → off",
                      self.toasts[0].split("\n"))

    def test_nothing_is_said_before_the_window_is_up(self):
        """Start-up binds the panel too (the restored lists, a first player
        start on the 🤸 list) — no toast for what nobody clicked."""
        self.win.hide()
        self.click(self.party)
        self.assertEqual(self.toasts, [])


class NoReapplyTest(_WindowCase):
    """His case: 1:40 nudged to 1:55, one party song, back — and 1:40 again."""

    def test_a_nudged_play_length_survives_a_party_and_back(self):
        self.click(self.b)                          # the tournament set: 1:40
        self.assertEqual(self.panel.play_secs(), 100)
        self.panel._step_len(1)                     # → 1:55
        self.assertEqual(self.panel.play_secs(), 115)
        self.play(self.b)
        self.click(self.party)
        self.play(self.party)
        self.click(self.b)
        self.play(self.b)
        self.assertEqual(self.panel.play_secs(), 115)
        self.assertEqual(self.vals(self.b)["secs"], 115)

    def test_starting_a_title_applies_nothing_to_the_panel(self):
        self.click(self.b)
        self.panel._step_len(1)
        shown = self.panel.play_set()
        self.play(self.party)                       # plays, is not clicked
        self.assertEqual(self.panel.play_set(), shown)

    def test_a_party_list_changed_by_hand_stays_changed(self):
        self.click(self.party)
        self.panel.announce_check.setChecked(True)
        self.click(self.a)
        self.click(self.party)
        self.assertTrue(self.panel.announce_check.isChecked())


class EngineTest(_WindowCase):
    """Playback obeys the list that is playing, not the one on the panel."""

    def test_the_playing_list_decides_the_play_length(self):
        self.vals(self.b)["secs"] = 115
        self.play(self.b)
        self.click(self.party)                      # panel: full length
        self.assertEqual(self.panel.play_secs(), 0)
        self.assertEqual(self.win._play_limit_secs(), 115)

    def test_with_nothing_playing_the_panel_list_decides(self):
        self.click(self.party)
        self.assertEqual(self.win._play_limit_secs(), 0)

    def test_the_playing_list_decides_auto_advance(self):
        self.vals(self.b)["advance"] = False
        self.play(self.b)
        self.click(self.party)                      # panel: ⏭ Auto
        self.assertTrue(self.panel.auto_advance())
        self.assertFalse(self.win._playing_advance())

    def test_the_playing_list_decides_the_pause(self):
        self.panel.pause_spin.setValue(20)
        self.vals(self.b)["pause_off"] = False
        self.play(self.b)
        self.click(self.party)                      # panel: no pause
        self.assertEqual(self.win._engine_pause_secs(), 20)

    def test_the_playing_list_decides_the_fade_and_the_announcement(self):
        self.vals(self.b).update(fade=1.5, announce=True)
        self.play(self.b)
        self.click(self.party)
        self.assertEqual(self.win._pv("fade"), 1.5)
        self.assertTrue(self.win._pv("announce"))

    def test_a_double_click_answers_for_its_own_list(self):
        self.vals(self.b)["dblclick"] = False
        self.vals(self.party)["dblclick"] = True
        self.assertFalse(self.b.dblclick_plays())
        self.assertTrue(self.party.dblclick_plays())

    def test_each_deck_flags_short_tracks_against_its_own_length(self):
        self.vals(self.b)["secs"] = 115
        self.vals(self.party)["secs"] = 0
        self.assertEqual(self.b._short_secs_cb(), 115)
        self.assertEqual(self.party._short_secs_cb(), 0)


class TsoTest(_WindowCase):
    """TSO sits on the player card, which serves the list that plays."""

    def setUp(self):
        super().setUp()
        self.card = self.win._big_player
        if self.card is None:
            self.skipTest("no media backend — no player card")
        self.vals(self.b)["tso"] = True
        self.vals(self.party)["tso"] = False

    def test_a_click_moves_it_while_nothing_plays(self):
        self.click(self.party)
        self.assertFalse(self.card.tso_mode())
        self.click(self.b)
        self.assertTrue(self.card.tso_mode())

    def test_a_click_leaves_it_to_the_playing_list(self):
        self.click(self.b)
        self.play(self.b)
        self.click(self.party)
        self.assertTrue(self.card.tso_mode())

    def test_a_list_starting_to_play_brings_its_own(self):
        self.click(self.b)
        self.play(self.b)
        self.b._current_play_row = -1
        self.play(self.party)
        self.assertFalse(self.card.tso_mode())
        self.assertTrue(self.vals(self.b)["tso"], "the switch wrote into B")

    def test_the_toggle_by_hand_writes_into_the_playing_list(self):
        self.click(self.party)
        self.play(self.b)
        self.card.set_tso_mode(False)
        self.win._on_tso_mode(False)
        self.assertFalse(self.vals(self.b)["tso"])
        self.assertFalse(self.vals(self.party)["tso"])


class SetButtonTest(_WindowCase):
    """🎉/🏆 are hands too — on the list the panel shows, and only there."""

    def test_the_party_button_sets_the_clicked_list_only(self):
        self.click(self.b)
        before_a = dict(self.vals(self.a))
        self.win._set_party_mode(True)
        got = {k: v for k, v in self.vals(self.b).items() if k != "tso"}
        self.assertEqual(got, self.set_of("party"))
        self.assertEqual(self.vals(self.a), before_a)

    def test_the_tournament_button_sets_the_clicked_list_only(self):
        self.click(self.party)
        before_b = dict(self.vals(self.b))
        self.win._apply_tournament_set()
        got = {k: v for k, v in self.vals(self.party).items() if k != "tso"}
        self.assertEqual(got, self.set_of("tournament"))
        self.assertEqual(self.vals(self.b), before_b)

    def test_the_sets_tso_goes_into_the_clicked_list(self):
        self.click(self.b)
        self.win._set_party_mode(True)
        self.assertIs(self.vals(self.b)["tso"],
                      tso_of(self.win._settings, "party"))


class CornerSwitchTest(_WindowCase):
    """⏭/✋ under a deck is that deck's own answer."""

    def test_it_writes_its_own_list(self):
        self.click(self.a)
        shown = self.panel.auto_advance()
        self.win._set_deck_advance(self.b, not self.vals(self.b)["advance"])
        self.assertEqual(self.panel.auto_advance(), shown,
                         "a corner under B moved the panel showing A")

    def test_the_panel_follows_when_it_shows_that_list(self):
        self.click(self.b)
        want = not self.panel.auto_advance()
        self.win._set_deck_advance(self.b, want)
        self.assertIs(self.panel.auto_advance(), want)
        self.assertIs(self.vals(self.b)["advance"], want)


class PersistTest(_WindowCase):
    """The values are part of the saved session."""

    def test_the_lists_with_values_are_written(self):
        self.vals(self.b)["secs"] = 115
        self.vals(self.party)["advance"] = False
        saved = self.win._build_env()["list_play"]
        self.assertEqual(saved["deck_b"]["secs"], 115)
        self.assertIs(saved["warmup"]["advance"], False)

    def test_they_come_back_on_the_next_start(self):
        self.vals(self.b)["secs"] = 115
        self.vals(self.party)["advance"] = False
        env = self.win._build_env()
        again = self.window()
        again._restore_list_play(env["list_play"], {})
        self.assertEqual(again._list_vals(again._tableB)["secs"], 115)
        self.assertIs(again._list_vals(again._warmup_table)["advance"], False)

    def test_the_panel_shows_what_its_list_brought_back(self):
        vals = dict(self.vals(self.a), secs=115)
        self.win._restore_list_play({"deck_a": vals}, {})
        self.assertEqual(self.panel.play_secs(), 115)

    def test_an_older_file_seeds_the_list_and_keeps_its_answer(self):
        """A session written before the lists had values of their own only
        knew a ⏭/✋ answer per list."""
        want = not self.set_of("tournament")["advance"]
        self.win._restore_list_play({}, {"deck_b": want})
        self.assertIs(self.vals(self.b)["advance"], want)
        self.assertEqual(self.vals(self.b)["secs"],
                         self.set_of("tournament")["secs"])

    def test_the_corner_reads_the_restored_answer(self):
        self.win._set_play_mode(True)               # the switch only shows there
        self.win._restore_list_play({}, {"deck_b": False, "deck_a": True})
        self.assertIn("Manual", self.b.advance_toggle().text())
        self.assertIn("Auto", self.a.advance_toggle().text())


if __name__ == "__main__":
    unittest.main()
