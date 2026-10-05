#!/usr/bin/env python3
"""Tests for a deck's three drag modes: 🔒 static → 🔓 dynamic → ✋ free order.

Run:  py -m unittest tests.gui.test_deck_mode -v

A planned deck is a grid of rounds, dances and heats, and a title can only move
into another slot of its own dance — which is exactly what planning needs and
exactly what is in the way once the evening runs. The party list and a
player-only install's decks are one flat running order instead, where any row
can be dragged anywhere. Free order is that same list, on demand, for any deck.

Being a third STATE and not a one-way door is the part worth testing: free order
throws the grid away, so the way back has to build a new one out of the list as
it stands — same songs, same order, same rounds, including whatever was dragged
in while it was free.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_mode_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, duration=180)


def _lib_of(*entries) -> MusicLibrary:
    """A library that knows these tracks — a restore looks its paths up there."""
    lib = MusicLibrary()
    lib.entries.extend(entries)
    return lib


class _DeckModeBase(unittest.TestCase):
    """A real MainWindow with a two-round draw in deck A."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_mode_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.entries = [_e("LW", 1), _e("TG", 2), _e("LW", 3), _e("TG", 4)]
        self.win._lib = _lib_of(*self.entries)
        self.table = self.win._tableA
        self.draw()

    # ── fixtures ────────────────────────────────────────────────────────────
    def draw(self):
        """Load the deck with a two-round, two-dance draw."""
        a, b, c, d = self.entries
        self.table.load(
            {"Vorrunde": [[a, b]], "Finale": [[c, d]]},
            ["LW", "TG"],
            [RoundConfig(name="Vorrunde", heats=1, tier="early"),
             RoundConfig(name="Finale", heats=1, tier="final")],
            "S", play_cb=None, suggester=None, use_timbre=False)
        self.win._refresh_mode_btn(self.table)

    def songs(self):
        return [m.entry.title for m in self.table._row_meta
                if m and m.entry is not None]

    def strips(self):
        """What the ─── strips are called, without their summary."""
        out = []
        for r, m in enumerate(self.table._row_meta):
            if m is None:
                it = self.table.item(r, 0) or self.table.item(r, 3)
                text = (it.text() if it else "").strip(" ▼▶─")
                out.append(text.split("   (")[0].strip())
        return out

    def glyph(self):
        return self.win.deck(self.table).mode_btn.text()


class DeckModeTest(_DeckModeBase):

    # ── the cycle ───────────────────────────────────────────────────────────
    def test_the_button_cycles_static_dynamic_free_and_back(self):
        seen = []
        for _ in range(4):
            seen.append((self.win._deck_mode(self.table), self.glyph()))
            self.win._cycle_deck_mode(self.table)
        self.assertEqual(seen, [("static", "🔒"), ("dynamic", "🔓"),
                                ("free", "✋"), ("static", "🔒")])

    def test_free_order_lets_any_row_be_dragged_anywhere(self):
        """The whole point of the third state — the party list's own rule."""
        self.assertFalse(self.table._supports_row_reorder())
        self.win._set_deck_mode(self.table, "free")
        self.assertTrue(self.table._supports_row_reorder())
        self.assertTrue(self.table._player_list)

    def test_free_order_keeps_the_songs_in_their_playing_order(self):
        self.win._set_deck_mode(self.table, "free")
        self.assertEqual(self.songs(), ["LW 1", "TG 2", "LW 3", "TG 4"])
        self.assertEqual(self.strips(), ["Vorrunde", "Finale"])

    def test_free_order_throws_the_grid_away(self):
        self.win._set_deck_mode(self.table, "free")
        self.assertIsNone(self.table._playlist)

    # ── and back again ──────────────────────────────────────────────────────
    def test_going_back_builds_the_same_grid_again(self):
        self.win._set_deck_mode(self.table, "free")
        self.win._set_deck_mode(self.table, "static")
        self.assertEqual(self.win._deck_mode(self.table), "static")
        self.assertEqual(list(self.table._playlist), ["Vorrunde", "Finale"])
        self.assertEqual(self.songs(), ["LW 1", "TG 2", "LW 3", "TG 4"])

    def test_going_back_to_dynamic_arrives_dynamic(self):
        self.win._set_deck_mode(self.table, "free")
        self.win._set_deck_mode(self.table, "dynamic")
        self.assertTrue(self.table._dynamic)
        self.assertEqual(list(self.table._playlist), ["Vorrunde", "Finale"])

    def test_what_was_dragged_in_while_free_comes_back_with_it(self):
        """Free order is for editing — an edit that the trip back drops would
        make the mode a trap."""
        self.win._set_deck_mode(self.table, "free")
        entries = [m.entry for m in self.table._row_meta
                   if m and m.entry is not None]
        self.table._reload_warmup(entries[:2] + [_e("WW", 9)] + entries[2:])
        self.win._set_deck_mode(self.table, "static")
        self.assertIn("WW 9", self.songs())
        self.assertIn("WW", self.table._loaded_dances)

    def test_a_track_dropped_into_a_round_stays_in_that_round(self):
        """It has no round of its own; the strip it was shown under is its round."""
        self.win._set_deck_mode(self.table, "free")
        entries = [m.entry for m in self.table._row_meta
                   if m and m.entry is not None]
        self.table._reload_warmup(entries[:2] + [_e("WW", 9)] + entries[2:])
        self.win._set_deck_mode(self.table, "static")
        self.assertEqual(list(self.table._playlist), ["Vorrunde", "Finale"])
        titles = [e.title for e in self.table._playlist["Vorrunde"][0] if e]
        self.assertIn("WW 9", titles)

    def test_a_list_of_no_known_dance_stays_free(self):
        """Nothing to build a grid from — going blank would be worse than staying."""
        from gui.main_decks import QMessageBox

        self.table.load_player_list(
            [MusicEntry(path=Path(r"C:\music\x.mp3"), title="x", duration=180)],
            "Abend", play_cb=None)
        self.win._refresh_mode_btn(self.table)
        asked = []
        real = QMessageBox.information
        QMessageBox.information = lambda *a, **kw: asked.append(a)
        try:
            self.win._set_deck_mode(self.table, "static")
        finally:
            QMessageBox.information = real
        self.assertTrue(asked)
        self.assertEqual(self.win._deck_mode(self.table), "free")

    def _free_with_a_nameless_track(self):
        """The deck free, with one track whose dance nothing can name."""
        self.win._set_deck_mode(self.table, "free")
        entries = [m.entry for m in self.table._row_meta
                   if m and m.entry is not None]
        stray = MusicEntry(path=Path(r"C:\music\mystery.mp3"),
                           title="mystery", duration=180)
        self.table._reload_warmup(entries + [stray])

    def _answer_question(self, button):
        """Make the next QMessageBox.question answer `button`; record the asking."""
        from gui.main_decks import QMessageBox

        asked = []
        real = QMessageBox.question

        def fake(*a, **kw):
            asked.append(a)
            return button

        QMessageBox.question = staticmethod(fake)
        self.addCleanup(lambda: setattr(QMessageBox, "question", real))
        return asked

    def test_the_way_back_asks_before_it_drops_a_track(self):
        """A grid has no column for a dance-less track, so building one deletes
        it — and a deletion is asked for, not reported after the fact."""
        from gui.main_decks import QMessageBox

        self._free_with_a_nameless_track()
        asked = self._answer_question(QMessageBox.StandardButton.No)
        self.win._set_deck_mode(self.table, "static")
        self.assertTrue(asked)
        self.assertEqual(self.win._deck_mode(self.table), "free")
        self.assertEqual(self.songs(),
                         ["LW 1", "TG 2", "LW 3", "TG 4", "mystery"])

    def test_saying_yes_builds_the_grid_without_it(self):
        from gui.main_decks import QMessageBox

        self._free_with_a_nameless_track()
        self._answer_question(QMessageBox.StandardButton.Yes)
        self.win._set_deck_mode(self.table, "static")
        self.assertEqual(self.win._deck_mode(self.table), "static")
        self.assertEqual(self.songs(), ["LW 1", "TG 2", "LW 3", "TG 4"])

    def test_a_list_it_can_place_whole_is_not_asked_about(self):
        from gui.main_decks import QMessageBox

        self.win._set_deck_mode(self.table, "free")
        asked = self._answer_question(QMessageBox.StandardButton.No)
        self.win._set_deck_mode(self.table, "static")
        self.assertFalse(asked)
        self.assertEqual(self.win._deck_mode(self.table), "static")

    def test_free_order_survives_a_save_and_restore(self):
        self.win._set_deck_mode(self.table, "free")
        state = self.win._serialize_playlist_state(self.table)
        self.draw()                       # deck back to a planned grid
        self.win._restore_into_deck(self.table, state)
        self.assertEqual(self.win._deck_mode(self.table), "free")
        self.assertEqual(self.songs(), ["LW 1", "TG 2", "LW 3", "TG 4"])

    def test_an_emptied_free_deck_does_not_go_back_to_a_grid_on_its_own(self):
        """Free is a chosen mode — the next drop must not silently undo it."""
        self.win._set_deck_mode(self.table, "free")
        self.table._reload_warmup([])
        self.assertTrue(self.table._player_list)
        self.assertFalse(self.table._dynamic)


class _DragEvent:
    """Stands in for the drop event: a hand-built QDropEvent has no source()."""

    def __init__(self, src, ctrl: bool = False):
        self._src = src
        self._ctrl = ctrl

    def source(self):
        return self._src

    def modifiers(self):
        from PySide6.QtCore import Qt

        return (Qt.KeyboardModifier.ControlModifier if self._ctrl
                else Qt.KeyboardModifier.NoModifier)


class FreeDeckDragTest(_DeckModeBase):
    """Deck → deck in free order is a MOVE, the way it is everywhere else.

    A free deck is rendered with the warm-up machinery, and dragging out of the
    Eintanzen panel is a copy — so the title used to arrive in Playlist 2 and
    stay in Playlist 1 as well."""

    def setUp(self):
        super().setUp()
        self.win._set_deck_mode(self.table, "free")
        self.other = self.win._tableB
        self.other.load_player_list([_e("WW", 7)], "Playlist 2", play_cb=None)

    def _drag_first_row_over(self, ctrl: bool = False) -> int:
        """Hand deck B the first track of deck A, then let it vacate the source."""
        row = next(r for r, m in enumerate(self.table._row_meta)
                   if m and m.entry is not None)
        entry = self.table._row_meta[row].entry
        self.table._drag_src_rows = [row]
        held = [m.entry for m in self.other._row_meta if m and m.entry]
        self.other._reload_warmup(held + [entry])
        return self.other._move_from_drag_source(
            _DragEvent(self.table, ctrl), pre_planned=set())

    def _titles(self, table):
        return [m.entry.title for m in table._row_meta if m and m.entry]

    def test_a_title_dragged_to_the_other_deck_leaves_this_one(self):
        self.assertEqual(self._drag_first_row_over(), 1)
        self.assertNotIn("LW 1", self._titles(self.table))
        self.assertIn("LW 1", self._titles(self.other))

    def test_the_rest_of_the_list_is_untouched(self):
        self._drag_first_row_over()
        self.assertEqual(self._titles(self.table), ["TG 2", "LW 3", "TG 4"])

    def test_ctrl_still_copies(self):
        self.assertEqual(self._drag_first_row_over(ctrl=True), 0)
        self.assertIn("LW 1", self._titles(self.table))

    def test_dragging_out_of_the_eintanzen_panel_is_still_a_copy(self):
        """The panel is a source of music, not a list tracks are taken from."""
        self.win._warmup_table = self.table
        self.assertEqual(self._drag_first_row_over(), 0)
        self.assertIn("LW 1", self._titles(self.table))


class PlayerOnlyModeTest(_DeckModeBase):
    """A player-only install plans nothing, so its decks ARE free order —
    before anything has been loaded into them, not once a list arrives."""

    def setUp(self):
        super().setUp()
        self.win._settings["app_mode"] = "player"
        self.empty = self.win._tableB

    def test_an_empty_deck_is_free_from_the_start(self):
        self.assertEqual(self.win._deck_mode(self.empty), "free")

    def test_a_deck_still_showing_a_planned_grid_is_free_too(self):
        self.assertEqual(self.win._deck_mode(self.table), "free")

    def test_a_planning_install_still_starts_its_decks_static(self):
        self.win._settings["app_mode"] = "both"
        self.assertEqual(self.win._deck_mode(self.empty), "static")

    def test_what_gets_SAVED_is_the_decks_own_mode(self):
        """Free BECAUSE nobody plans here is not a choice the deck made — saving
        it would hand every deck free order to an install that does plan."""
        self.assertEqual(self.win._deck_own_mode(self.empty), "static")
        self.assertEqual(self.win._build_env()["deck_modes"]["deck_b"], "static")

    # ── a saved planning mode must not be replayed here ──────────────────────
    def test_a_saved_dynamic_mode_is_not_replayed(self):
        """It used to be, and the deck then said free on the button while being
        dynamic underneath — with no toggle on screen to get out of it."""
        self.win._restore_deck_modes({"deck_b": "dynamic"})
        self.assertEqual(self.win._deck_mode(self.empty), "free")
        self.assertFalse(self.empty._dynamic)

    def test_a_deck_that_declined_the_replay_is_free_all_the_way_down(self):
        """Whatever the file said, every reader of the deck has to agree."""
        self.win._restore_deck_modes({"deck_a": "dynamic", "deck_b": "dynamic"})
        for table in (self.table, self.empty):
            self.assertEqual(self.win._deck_mode(table), "free")
            self.assertFalse(table._dynamic)

    def test_the_mode_toggle_stays_hidden_across_a_fold(self):
        """Unfolding used to show the button by itself, which handed a
        player-only install the static/dynamic choice it does not have."""
        btn = self.win.deck(self.table).mode_btn
        self.win._refresh_mode_btn(self.table)
        self.assertTrue(btn.isHidden())
        self.win._toggle_deck_fold(self.table, True)
        self.win._toggle_deck_fold(self.table, False)
        self.assertTrue(btn.isHidden())

    def test_a_planning_install_gets_its_toggle_back_after_a_fold(self):
        self.win._settings["app_mode"] = "both"
        btn = self.win.deck(self.table).mode_btn
        self.win._toggle_deck_fold(self.table, True)
        self.assertTrue(btn.isHidden())
        self.win._toggle_deck_fold(self.table, False)
        self.assertFalse(btn.isHidden())


class DeckModePersistTest(_DeckModeBase):
    """The 🔒/🔓/✋ toggle survives a restart — an EMPTY deck's too, which has
    no saved tracks to carry it."""

    def setUp(self):
        super().setUp()
        self.empty = self.win._tableB

    def modes(self):
        return self.win._build_env()["deck_modes"]

    def test_an_empty_dynamic_deck_is_saved_as_dynamic(self):
        self.win._set_deck_mode(self.empty, "dynamic")
        self.assertEqual(self.modes()["deck_b"], "dynamic")

    def test_an_empty_dynamic_deck_comes_back_dynamic(self):
        self.win._restore_deck_modes({"deck_b": "dynamic"})
        self.assertEqual(self.win._deck_mode(self.empty), "dynamic")
        self.assertEqual(self.win.deck(self.empty).mode_btn.text(), "🔓")

    def test_an_empty_free_deck_comes_back_free(self):
        self.win._set_deck_mode(self.empty, "free")
        saved = self.modes()
        self.assertEqual(saved["deck_b"], "free")
        fresh = self.gui.MainWindow()
        self.addCleanup(reap_widget, fresh)
        fresh._loading_dlg.accept()
        fresh._restore_deck_modes(saved)
        self.assertEqual(fresh._deck_mode(fresh._tableB), "free")

    def test_a_deck_with_tracks_is_left_alone(self):
        """Its own saved state already restored its mode — re-applying one here
        would throw the grid that state just rebuilt away."""
        self.win._restore_deck_modes({"deck_a": "free"})
        self.assertEqual(self.win._deck_mode(self.table), "static")
        self.assertEqual(self.songs(), ["LW 1", "TG 2", "LW 3", "TG 4"])

    def test_a_day_deck_keeps_its_mode_too(self):
        day = self.win._day_decks[0]
        self.win._set_deck_mode(day, "dynamic")
        self.assertEqual(self.modes()["day_a"], "dynamic")

    def test_a_file_without_the_key_changes_nothing(self):
        self.win._restore_deck_modes({})
        self.assertEqual(self.win._deck_mode(self.empty), "static")


class StartupWindowsTest(_DeckModeBase):
    """Building the desk must not flash windows across the screen.

    A QToolButton made without a parent is a top-level window until something
    puts it in a layout, so a setVisible() in between shows it as one — sixteen
    44×19 windows appearing before the loading splash did."""

    def setUp(self):
        pass          # this one builds its own window, under the spy

    def test_building_the_desk_opens_no_stray_windows(self):
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QWidget

        shown = []

        class Spy(QObject):
            def eventFilter(self, obj, ev):
                if (ev.type() == QEvent.Type.Show
                        and isinstance(obj, QWidget) and obj.isWindow()):
                    shown.append(type(obj).__name__)
                return False

        spy = Spy()
        self.app.installEventFilter(spy)
        try:
            win = self.gui.MainWindow()
        finally:
            self.app.removeEventFilter(spy)
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        # The splash is the one window that is MEANT to show at this point.
        self.assertEqual([n for n in shown if n != "LoadingDialog"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
