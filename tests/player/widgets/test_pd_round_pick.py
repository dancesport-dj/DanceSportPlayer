#!/usr/bin/env python3
"""🐂 The panel's "Stop after highlight" shows the round's own pick.

Run:  py -m unittest tests.player.widgets.test_pd_round_pick -v

⚙ Settings → 🎛 Play sets gives each kind of round its Paso Doble pick — a
final in full, a Vorrunde after the 2nd — and that pick, not the panel's spin,
decides the stop. The spin still read "2" over a final played in full. It now
shows what applies: the round's highlight, and a final in full as the 3rd
(the music's own end). The panel's own number is kept for every other title.

Marcel then: "it is disabled/greyed out, it should still be able to be
overwriten". A change on the spin while the round's pick shows is that list's
own pick for rounds of that kind; other lists and ⚙ Settings keep the round's.
Turning it back to the round's pick, or putting the 🏆 set on again, drops it.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_round_"))

from PySide6.QtWidgets import QApplication

from player.widgets.play_mode_panel import PlayModePanel

app = QApplication.instance() or QApplication([])


class PanelShowsTheRoundsPick(unittest.TestCase):

    def setUp(self):
        self.panel = PlayModePanel({"pd_highlight_stop": True, "pd_highlight_n": 2})

    def tearDown(self):
        self.panel.deleteLater()

    def test_a_final_in_full_reads_as_the_third_highlight(self):
        self.panel.set_round_pd_n(0, "Finale")
        self.assertEqual(self.panel.pd_spin.value(), 3)
        self.assertTrue(self.panel.pd_spin.isEnabled())
        self.assertIn("Finale", self.panel.pd_spin.toolTip())

    def test_a_change_over_the_rounds_pick_is_offered_as_the_lists_own(self):
        picked = []
        self.panel.roundPdPicked.connect(picked.append)
        self.panel.set_round_pd_n(0, "Finale")
        self.panel.pd_spin.setValue(2)
        self.assertEqual(picked, [2])
        self.assertEqual(self.panel.pd_highlight_n(), 2)   # own number untouched

    def test_a_change_without_a_round_pick_is_the_panels_own(self):
        picked = []
        self.panel.roundPdPicked.connect(picked.append)
        self.panel.pd_spin.setValue(1)
        self.assertEqual(picked, [])
        self.assertEqual(self.panel.pd_highlight_n(), 1)

    def test_the_panels_own_number_is_kept(self):
        self.panel.set_round_pd_n(0, "Finale")
        self.assertEqual(self.panel.pd_highlight_n(), 2)

    def test_a_vorrunde_shows_its_own_highlight(self):
        self.panel.set_pd_highlight_n(1)
        self.panel.set_round_pd_n(2, "Vorrunde")
        self.assertEqual(self.panel.pd_spin.value(), 2)

    def test_no_round_pick_gives_the_spin_back(self):
        self.panel.set_round_pd_n(0, "Finale")
        self.panel.set_round_pd_n(None)
        self.assertEqual(self.panel.pd_spin.value(), 2)
        self.assertTrue(self.panel.pd_spin.isEnabled())

    def test_the_round_does_not_save_itself_as_the_panels_number(self):
        seen = []
        self.panel.settingsChanged.connect(lambda: seen.append(1))
        self.panel.set_round_pd_n(0, "Finale")
        self.panel.set_round_pd_n(None)
        self.assertEqual(seen, [])

    def test_a_set_applied_meanwhile_lands_on_the_panels_number(self):
        self.panel.set_round_pd_n(0, "Finale")
        self.assertEqual(self.panel.set_pd_highlight_n(1),
                         ["🐂 Paso Doble stop after highlight → 1"])
        self.assertEqual(self.panel.pd_spin.value(), 3)   # the final still shows
        self.panel.set_round_pd_n(None)
        self.assertEqual(self.panel.pd_spin.value(), 1)


class _Panel:
    def __init__(self):
        self.round_pd = "untouched"

    def set_round_pd_n(self, n, label=""):
        self.round_pd = (n, label)

    def pd_highlight_stop(self):
        return True

    def pd_highlight_n(self):
        return 1

    def set_pd_highlight_stop(self, _on):
        return []

    def set_pd_highlight_n(self, _n):
        return []

    def set_pd_start_delay(self, _secs):
        return []


class _List:
    def __init__(self, rnd="Finale"):
        self.vals = {}
        self.rnd = rnd

    def round_at(self, _row):
        return self.rnd


def _win(on_set_length=True, picks=None):
    from player.window.main_play_values import PlayValuesMixin

    class Win(PlayValuesMixin):
        def _on_tournament_length(self, _table):
            return on_set_length

        def _list_vals(self, table):
            return table.vals

        def _panel_list(self):
            return self.panel_list

        def _playing_row(self):
            return self.panel_list, 0

        def _slot_in_focus(self, table):
            return "PD", table.rnd if table is not None else ""

        def _autosave_playlist(self):
            pass

    w = Win()
    w._play_panel = _Panel()
    w.panel_list = None
    w._settings = {"tournament_round_pd_n":
                   picks if picks is not None else {"first": 2, "final": 0}}
    return w


class WindowSyncsTheRoundsPick(unittest.TestCase):

    def test_a_final_pd_shows_its_pick(self):
        w = _win()
        w._sync_round_pd(None, "PD", "Finale")
        self.assertEqual(w._play_panel.round_pd[0], 0)

    def test_a_round_without_a_pick_shows_the_panels_own(self):
        w = _win(picks={"final": 0})
        w._sync_round_pd(None, "PD", "Vorrunde")
        self.assertEqual(w._play_panel.round_pd, (None, ""))

    def test_off_the_sets_length_the_panel_decides(self):
        w = _win(on_set_length=False)
        w._sync_round_pd(None, "PD", "Finale")
        self.assertEqual(w._play_panel.round_pd, (None, ""))

    def test_another_dance_leaves_the_spin_to_the_panel(self):
        w = _win()
        w._sync_round_pd(None, "SA", "Finale")
        self.assertEqual(w._play_panel.round_pd, (None, ""))


class ThePanelOverridesTheRoundForItsList(unittest.TestCase):

    def setUp(self):
        self.w = _win()
        self.final = self.w.panel_list = _List("Finale")

    def test_a_pick_on_the_panel_stops_this_lists_final(self):
        self.w._on_round_pd_picked(2)
        self.assertEqual(self.w._pd_highlight(), (True, 2))

    def test_the_spin_shows_the_lists_own_pick(self):
        self.w._on_round_pd_picked(1)
        self.w._sync_round_pd(self.final, "PD", "Finale")
        self.assertEqual(self.w._play_panel.round_pd, (1, "Finale"))

    def test_another_list_keeps_the_rounds_pick(self):
        self.w._on_round_pd_picked(2)
        self.w.panel_list = _List("Finale")
        self.assertEqual(self.w._pd_highlight(), (False, 1))

    def test_a_vorrunde_on_the_same_list_keeps_its_own(self):
        self.w._on_round_pd_picked(1)
        self.final.rnd = "Vorrunde"
        self.assertEqual(self.w._pd_highlight(), (True, 2))

    def test_back_on_the_rounds_pick_drops_the_lists_own(self):
        self.w._on_round_pd_picked(2)
        self.w._on_round_pd_picked(3)   # a final in full reads as 3
        self.assertEqual(self.final.vals["pd_round_n"], {})
        self.assertEqual(self.w._pd_highlight(), (False, 1))

    def test_the_tournament_set_drops_the_lists_own(self):
        self.w._on_round_pd_picked(2)
        self.w._set_set_pd("tournament")
        self.assertEqual(self.w._pd_highlight(), (False, 1))

    def test_off_the_sets_length_the_panel_decides(self):
        self.w._on_round_pd_picked(2)
        self.w._on_tournament_length = lambda _t: False
        self.assertEqual(self.w._pd_highlight(), (True, 1))


if __name__ == "__main__":
    unittest.main()
