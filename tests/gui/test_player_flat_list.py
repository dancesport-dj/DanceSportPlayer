#!/usr/bin/env python3
"""Tests for the flat running order of a player-only install.

Run:  py -m unittest tests.gui.test_player_flat_list -v

Someone who only runs the music never plans a draw, so a deck there is not a
round/dance/heat grid at all — it is the list the evening is played from. It
therefore behaves like the ETDS party list: one running order, a dropped title
stays exactly where it was dropped, and any row can be dragged anywhere. It
keeps ─── strips grouping the list by dance, because seeing where the Walzer end
and the Tango begin is worth having; being derived from the order, they simply
re-cut themselves around whatever was just dragged in.

Switching the app to player-only needs no restart, so a draw planned a moment
ago is still on screen — with slots that only take a title of their own dance.
Those decks are re-rendered: same songs, same order, free to drag.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_flat_"))

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDropEvent, QKeyEvent  # noqa: E402
from PySide6.QtWidgets import (QApplication,  # noqa: E402
                               QMessageBox as _QMessageBox, QWidget)
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.deck import Deck  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, bpm=None)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self, mode: str):
        super().__init__()
        self._settings = {"app_mode": mode}


class _FlatTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.file = Path(tempfile.mkdtemp(prefix="dp_flat_f_")) / "wish.mp3"
        cls.file.write_bytes(b"x")

    def table(self, mode: str = "player") -> PlaylistTable:
        """An EMPTY deck inside a window of app mode `mode`."""
        win = _Win(mode)
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        return t

    def deck(self, mode: str = "player") -> PlaylistTable:
        """A deck holding a two-round draw."""
        t = self.table(mode)
        t.load({"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                "Finale": [[_e("LW", 3), _e("TG", 4)]]},
               ["LW", "TG"],
               [RoundConfig(name="Vorrunde", heats=1, tier="early"),
                RoundConfig(name="Finale", heats=1, tier="final")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        return t

    def player_list(self, *entries) -> PlaylistTable:
        t = self.table("player")
        t.load_player_list(list(entries), "Abend", play_cb=None)
        return t

    def songs(self, table):
        return [m.entry.title for m in table._row_meta
                if m and m.entry is not None]

    def strips(self, table):
        """The ─── header rows, stripped down to their label."""
        return [table.item(r, 0).text().strip(" ▼▶─").split("   ")[0]
                for r, m in enumerate(table._row_meta) if m is None]

    def song_row(self, table, n: int) -> int:
        """Row of the n-th SONG — the ─── strips sit between them, so a song's
        index in the list is not its row in the table."""
        return [r for r, m in enumerate(table._row_meta)
                if m and m.entry is not None][n]

    def drop(self, table, at_row: int):
        """Drop the file into the gap above `at_row` (below the last row when the
        table is empty) and return what the deck holds afterwards."""
        table._move_from_drag_source = lambda *a, **kw: None
        table._planned_keys = lambda *a, **kw: set()
        # The temp file is a placeholder, not a real MP3 — resolving it would ask
        # the library (and pop a "couldn't read" box). The drop ROUTE is the
        # subject here, so hand the deck the entry it would have got.
        table._resolve_drop_entries = lambda files: [
            MusicEntry(path=self.file, title="wish", dance="WW", bpm=None)]
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.file))])
        y = (table.rowViewportPosition(at_row) + 2 if table.rowCount() else 2)
        table.dropEvent(QDropEvent(QPointF(20, y), Qt.DropAction.CopyAction, mime,
                                   Qt.MouseButton.LeftButton,
                                   Qt.KeyboardModifier.NoModifier))
        return table


class FirstDropTest(_FlatTest):
    """A drop onto a deck that is not the running order yet makes it one."""

    def test_an_empty_player_deck_becomes_the_running_order(self):
        t = self.table("player")
        self.drop(t, 0)
        self.assertTrue(t._player_list)
        self.assertEqual(self.songs(t), ["wish"])

    def test_an_empty_planner_deck_does_not(self):
        """While playlists are built, an empty deck still turns dynamic on its
        first drop and grows a round grid."""
        self.assertFalse(self.table("both")._deck_adds_on_drop())

    def test_a_planned_draw_is_re_rendered(self):
        """The case that started this: a grid left over from planning mode
        refuses every drag until it becomes the running order."""
        t = self.deck("player")
        before = self.songs(t)
        self.drop(t, 0)
        self.assertTrue(t._player_list)
        self.assertEqual(self.songs(t), ["wish"] + before,
                         "the planned order has to survive the re-render")

    def test_a_second_drop_does_not_reload_the_list(self):
        t = self.player_list(_e("LW", 1))
        self.assertFalse(t._deck_adds_on_drop())


class DropPositionTest(_FlatTest):
    """"Tracks stay where they were dropped" — the whole point of the flat list."""

    def test_a_drop_lands_where_it_was_dropped(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2), _e("WW", 3))
        self.drop(t, self.song_row(t, 1))
        self.assertEqual(self.songs(t), ["LW 1", "wish", "TG 2", "WW 3"])

    def test_a_drop_at_the_top_leads_the_list(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2))
        self.drop(t, self.song_row(t, 0))
        self.assertEqual(self.songs(t), ["wish", "LW 1", "TG 2"])

    def test_a_track_already_in_the_list_is_not_doubled(self):
        t = self.player_list(_e("LW", 1))
        self.drop(t, self.song_row(t, 0))
        self.drop(t, self.song_row(t, 0))
        self.assertEqual(self.songs(t), ["wish", "LW 1"])


class ShapeTest(_FlatTest):
    """One running order, grouped by the dance being played."""

    def test_a_strip_heads_every_run_of_a_dance(self):
        t = self.player_list(_e("LW", 1), _e("LW", 2), _e("TG", 3))
        self.assertEqual(self.strips(t), ["Langsamer Walzer", "Tango"])

    def test_a_dance_that_comes_round_again_gets_its_own_strip(self):
        """Derived from the ORDER, not from a set of dances — the party list's
        rule would open a whole new round here instead."""
        t = self.player_list(_e("LW", 1), _e("TG", 2), _e("LW", 3))
        self.assertEqual(self.strips(t), ["Langsamer Walzer", "Tango",
                                          "Langsamer Walzer"])

    def test_a_drop_re_cuts_the_strips(self):
        t = self.player_list(_e("LW", 1), _e("LW", 2))
        self.drop(t, self.song_row(t, 1))                 # a WW between the two
        self.assertEqual(self.strips(t), ["Langsamer Walzer", "Wiener Walzer",
                                          "Langsamer Walzer"])

    def test_the_strips_carry_no_heat_count(self):
        """A running order has no heats to count — that summary belongs to a
        competition round."""
        t = self.player_list(_e("LW", 1))
        self.assertNotIn("heat", t.item(0, 0).text())

    def test_the_dance_still_shows_per_row(self):
        t = self.player_list(_e("LW", 1), _e("SA", 2))
        self.assertEqual([m.dance for m in t._row_meta if m], ["LW", "SA"])


class RoundStripTest(_FlatTest):
    """Where the rounds can be worked out they head the strips — 'Vorrunde',
    'Zwischenrunde', 'Finale' is what the desk needs to see. The dance grouping
    is what is left when they can't."""

    def rounds(self, sections, *entries) -> PlaylistTable:
        t = self.table("player")
        t.load_player_list(list(entries), "Abend", play_cb=None, sections=sections)
        return t

    def test_the_rounds_head_the_strips(self):
        t = self.rounds({r"C:\music\LW1.mp3": "Vorrunde",
                         r"C:\music\TG2.mp3": "Vorrunde",
                         r"C:\music\LW3.mp3": "Finale"},
                        _e("LW", 1), _e("TG", 2), _e("LW", 3))
        self.assertEqual(self.strips(t), ["Vorrunde", "Finale"])

    def test_the_dance_groups_when_no_round_is_known(self):
        t = self.rounds({}, _e("LW", 1), _e("TG", 2))
        self.assertEqual(self.strips(t), ["Langsamer Walzer", "Tango"])

    def test_a_list_handed_no_rounds_works_them_out_of_its_own_order(self):
        """Nothing else ever derives them again: a draw converted without round
        names, or a running order restored from a file saved before the strips
        knew about rounds, would head its strips with dances for good."""
        t = self.rounds({},
                        _e("LW", 1), _e("TG", 2), _e("QS", 3),
                        _e("LW", 4), _e("TG", 5), _e("QS", 6),
                        _e("LW", 7), _e("TG", 8), _e("QS", 9))
        self.assertEqual(self.strips(t), ["Vorrunde", "Zwischenrunde", "Finale"])

    def test_a_party_list_is_cut_into_its_warm_up_rounds(self):
        """An evening that runs through the dances all night is no tournament,
        but it is not nameless either: it is a warm-up / party list, and the
        strips name the rounds it was built from — the same ones the 🤸 panel
        has always shown."""
        entries = [_e(d, i) for i in range(9) for d in ("LW", "TG")]
        t = self.rounds({}, *entries)
        self.assertEqual(self.strips(t),
                         [f"Standardrunde {n}" for n in range(1, 10)])

    def test_a_converted_draw_keeps_the_rounds_it_was_drawn_into(self):
        t = self.deck("player")
        t.become_player_list()
        self.assertEqual(self.strips(t), ["Vorrunde", "Finale"])

    def test_a_dropped_track_joins_the_round_it_landed_in(self):
        """It belongs to no round of its own, so the strips must not tear open
        around it."""
        t = self.rounds({r"C:\music\LW1.mp3": "Vorrunde",
                         r"C:\music\LW3.mp3": "Finale"},
                        _e("LW", 1), _e("LW", 3))
        self.drop(t, self.song_row(t, 1))
        self.assertEqual(self.songs(t), ["LW 1", "wish", "LW 3"])
        self.assertEqual(self.strips(t), ["Vorrunde", "Finale"])

    def test_a_track_dropped_ahead_of_them_all_joins_the_first_round(self):
        t = self.rounds({r"C:\music\LW1.mp3": "Vorrunde"}, _e("LW", 1))
        self.drop(t, self.song_row(t, 0))
        self.assertEqual(self.strips(t), ["Vorrunde"])


class RowMoveTest(_FlatTest):

    def test_any_row_may_be_dragged_anywhere(self):
        self.assertTrue(self.player_list(_e("LW", 1))._supports_row_reorder())

    def test_a_planned_draw_still_moves_within_its_dance(self):
        self.assertFalse(self.deck("both")._supports_row_reorder())

    def test_a_reorder_crosses_the_strips(self):
        """The point of the whole change: a Wiener Walzer can be pulled to the
        front of the Langsamer Walzer, which a slot grid refuses."""
        t = self.player_list(_e("LW", 1), _e("TG", 2), _e("WW", 3))
        t._drag_src_rows = [r for r, m in enumerate(t._row_meta)
                            if m and m.entry.title == "WW 3"]
        t._reorder_warmup(0)
        self.assertEqual(self.songs(t), ["WW 3", "LW 1", "TG 2"])


class DeleteTest(_FlatTest):
    """Del takes a track OUT of a running order — it does not empty a slot.

    A planned deck keeps the slot behind a deleted title: the grid says a Tango
    belongs there, and the next pick or drop fills it again. A free running order
    has no grid saying anything, so the slot left behind was a hole nothing could
    fill — a "⚠ No song found" row sitting in the evening's list for good.
    """

    def press_delete(self, table, song: int,
                     answer=_QMessageBox.StandardButton.Yes) -> list:
        """Select the n-th song, press Del, and return the messages asked."""
        from unittest import mock

        from gui import table_actions

        seen = []

        def _question(*args, **_kw):
            seen.append(args[2])
            return answer

        table.selectRow(self.song_row(table, song))
        ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete,
                       Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(table_actions.QMessageBox, "question",
                               _question):
            table.keyPressEvent(ev)
        return seen

    def empty_rows(self, table) -> int:
        """Song rows left holding no track — the slots a grid would keep."""
        return sum(1 for m in table._row_meta if m is not None and m.entry is None)

    def test_the_track_goes_and_leaves_no_slot(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2), _e("LW", 3))
        self.press_delete(t, 1)
        self.assertEqual(self.songs(t), ["LW 1", "LW 3"])
        self.assertEqual(self.empty_rows(t), 0)

    def test_the_strips_re_cut_around_it(self):
        """The two Walzer are one run again once the Tango between them is gone
        — same rule a drop goes by."""
        t = self.player_list(_e("LW", 1), _e("TG", 2), _e("LW", 3))
        self.press_delete(t, 1)
        self.assertEqual(self.strips(t), ["Langsamer Walzer"])

    def test_the_question_says_what_happens(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2))
        seen = self.press_delete(t, 0)
        self.assertEqual(len(seen), 1)
        self.assertIn("running order", seen[0])
        self.assertNotIn("slot", seen[0])

    def test_no_keeps_the_track(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2))
        self.press_delete(t, 0, answer=_QMessageBox.StandardButton.No)
        self.assertEqual(self.songs(t), ["LW 1", "TG 2"])

    def test_a_planned_deck_still_keeps_its_slot(self):
        """The other half of the rule: a grid slot is a plan, and emptying it is
        how a title is swapped out."""
        t = self.deck("both")
        self.press_delete(t, 1)
        self.assertEqual(self.songs(t), ["LW 1", "LW 3", "TG 4"])
        self.assertEqual(self.empty_rows(t), 1)

    def test_dragging_one_out_drops_the_row_too(self):
        """The MOVE out of a deck goes through the same clear — it must not leave
        the hole either."""
        t = self.player_list(_e("LW", 1), _e("TG", 2))
        self.assertTrue(t._clear_slots_at({self.song_row(t, 0)}))
        self.assertEqual(self.songs(t), ["TG 2"])
        self.assertEqual(self.empty_rows(t), 0)


class ConversionTest(_FlatTest):
    """Switching the install to player-only re-renders a planned draw."""

    def test_the_order_survives(self):
        t = self.deck("player")
        before = self.songs(t)
        t.become_player_list()
        self.assertTrue(t._player_list)
        self.assertEqual(self.songs(t), before)

    def test_the_rows_can_then_be_dragged(self):
        t = self.deck("player")
        self.assertFalse(t._supports_row_reorder())
        t.become_player_list()
        self.assertTrue(t._supports_row_reorder())

    def test_the_mode_switch_converts_every_deck(self):
        from gui.main_decks import DeckLayoutMixin

        planned, running = self.deck("player"), self.player_list(_e("LW", 1))

        class _App(DeckLayoutMixin):
            _decks = [planned, running]
            _day_decks: list = []

            def _autosave_playlist(_self):
                pass

        self.assertEqual(_App()._decks_to_player_lists(), 1,
                         "only the deck still showing a grid needs re-rendering")
        self.assertTrue(planned._player_list)
        self.assertEqual(self.songs(running), ["LW 1"],
                         "a list already flat must not be reloaded")


class FlavourTest(_FlatTest):
    """`plays_flat()` decides where an imported .m3u goes."""

    def test_a_player_deck_plays_flat(self):
        self.assertTrue(self.table("player").plays_flat())
        self.assertTrue(self.player_list(_e("LW", 1)).plays_flat())

    def test_a_planner_deck_does_not(self):
        self.assertFalse(self.table("both").plays_flat())
        self.assertFalse(self.deck("both").plays_flat())

    def test_the_eintanzen_panel_keeps_its_own_route(self):
        t = self.table("player")
        t._warmup = True
        self.assertFalse(t.plays_flat())

    def test_a_wishlist_keeps_its_own_route(self):
        t = self.table("player")
        t.load_wishlist([_e("LW", 1)], play_cb=None, suggester=None)
        self.assertFalse(t.plays_flat())

    def test_loading_a_draw_clears_the_flag(self):
        """Switching the install back to planning, or importing a draw: the deck
        is a grid again and must not report itself as a running order."""
        t = self.player_list(_e("LW", 1))
        t.load({"Vorrunde": [[_e("LW", 1)]]}, ["LW"],
               [RoundConfig(name="Vorrunde", heats=1, tier="early")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        self.assertFalse(t._player_list)

    def test_loading_a_theme_clears_the_flag(self):
        t = self.player_list(_e("LW", 1))
        t.load_theme([_e("LW", 1)], "Theme", play_cb=None, suggester=None)
        self.assertFalse(t._player_list)


class PersistTest(_FlatTest):
    """The running order has to survive a restart — the grid serializer finds no
    rounds in it and would drop the whole deck."""

    def state(self, table):
        from gui.main_persist import PersistenceMixin

        class _Win(PersistenceMixin):
            _table = None

            def deck(self, table):
                return Deck(table)

        return _Win()._serialize_playlist_state(table)

    def test_the_tracks_and_their_order_are_saved(self):
        t = self.player_list(_e("LW", 1), _e("TG", 2))
        state = self.state(t)
        self.assertTrue(state["player_list"])
        self.assertEqual(state["theme_entries"],
                         [r"C:\music\LW1.mp3", r"C:\music\TG2.mp3"])

    def test_the_list_name_rides_along(self):
        self.assertEqual(self.state(self.player_list(_e("LW", 1)))["theme_label"],
                         "Abend")

    def test_the_rounds_ride_along(self):
        """Derived once, at load — a restart must not have to guess them again."""
        t = self.deck("player")
        t.become_player_list()
        self.assertEqual(self.state(t)["player_sections"],
                         {r"C:\music\LW1.mp3": "Vorrunde",
                          r"C:\music\TG2.mp3": "Vorrunde",
                          r"C:\music\LW3.mp3": "Finale",
                          r"C:\music\TG4.mp3": "Finale"})

    def test_an_empty_list_saves_nothing(self):
        self.assertIsNone(self.state(self.player_list()))

    def test_it_is_saved_as_a_flat_list(self):
        """"Theme" is what every reader already understands as "a flat list of
        tracks" — export, undo diffing and the row flash then need no change."""
        self.assertEqual(self.state(self.player_list(_e("LW", 1)))["mode"], "Theme")


class M3uProgressTest(_FlatTest):
    """Reading a long .m3u reports progress instead of freezing the window."""

    def read(self, lines):
        from gui.main_generate import GenerateMixin

        path = Path(tempfile.mkdtemp(prefix="dp_flat_m3u_")) / "list.m3u"
        path.write_text("\n".join(lines), encoding="utf-8")

        class _Lib:
            entries = [_e("LW", n) for n in range(1, 200)]

            def make_external_entry(_self, p, cache):
                return None

        class _Win(GenerateMixin):
            _lib = _Lib()
            _cache = None

        seen = []
        got = _Win()._entries_from_m3u_file(
            path, progress_cb=lambda d, t, detail="": seen.append((d, t, detail)))
        return got, seen

    def test_the_read_is_reported_while_it_runs(self):
        got, seen = self.read([rf"C:\music\LW{n}.mp3" for n in range(1, 100)])
        self.assertEqual(len(got), 99)
        self.assertGreater(len(seen), 1, "reported only once — nothing to watch")
        self.assertTrue(all(t == 99 for _, t, _ in seen), "the total must not move")
        self.assertEqual([d for d, _, _ in seen], sorted(d for d, _, _ in seen))

    def test_the_total_counts_tracks_not_lines(self):
        """A real .m3u heads every track with an #EXTINF comment, so counting
        lines counts each track twice: a 282-track party list ran the bar up
        past 500 and then loaded 282 — which reads as half of it being lost."""
        lines = ["#EXTM3U"]
        for n in range(1, 100):
            lines += [f"#EXTINF:120,LW {n}", rf"C:\music\LW{n}.mp3"]
        got, seen = self.read(lines)
        self.assertEqual(len(got), 99)
        totals = {t for _, t, _ in seen}
        self.assertEqual(totals, {99}, f"the bar counted lines: {sorted(totals)}")
        self.assertLessEqual(max(d for d, _, _ in seen), 99)

    def test_it_still_reads_without_a_callback(self):
        """The generator's own 'from an .m3u file' source passes none."""
        from gui.main_generate import GenerateMixin

        path = Path(tempfile.mkdtemp(prefix="dp_flat_m3u2_")) / "list.m3u"
        path.write_text(r"C:\music\LW1.mp3", encoding="utf-8")

        class _Lib:
            entries = [_e("LW", 1)]

        class _Win(GenerateMixin):
            _lib = _Lib()
            _cache = None

        self.assertEqual(len(_Win()._entries_from_m3u_file(path)), 1)


class M3uReplaceWarningTest(_FlatTest):
    """An .m3u dropped onto a list REPLACES it. Dragging one in from Explorer is
    an easy slip, and it must not cost the evening's list without a word."""

    def ask(self, table, answer):
        """Answer the confirmation with `answer`; returns (went ahead, messages)."""
        from unittest import mock

        from gui import table_dnd as gui_table_dnd

        seen = []

        def _question(*args, **_kw):
            seen.append(args[2])
            return answer

        with mock.patch.object(gui_table_dnd.QMessageBox, "question", _question):
            ok = table._confirm_m3u_replaces(Path("Turnier1.m3u"))
        return ok, seen

    def test_an_empty_list_is_not_worth_a_question(self):
        ok, seen = self.ask(self.table("player"),
                            _QMessageBox.StandardButton.No)
        self.assertTrue(ok)
        self.assertEqual(seen, [])

    def test_a_full_list_says_what_is_lost(self):
        _ok, seen = self.ask(self.player_list(_e("LW", 1), _e("TG", 2)),
                             _QMessageBox.StandardButton.Yes)
        self.assertEqual(len(seen), 1)
        self.assertIn("2 track(s)", seen[0])
        self.assertIn("Turnier1.m3u", seen[0])

    def test_no_keeps_the_list(self):
        ok, _seen = self.ask(self.player_list(_e("LW", 1)),
                             _QMessageBox.StandardButton.No)
        self.assertFalse(ok)

    def test_yes_imports(self):
        ok, _seen = self.ask(self.player_list(_e("LW", 1)),
                             _QMessageBox.StandardButton.Yes)
        self.assertTrue(ok)

    def test_a_declined_drop_never_reaches_the_importer(self):
        from unittest import mock

        from gui import table_dnd as gui_table_dnd

        t = self.player_list(_e("LW", 1))
        m3u = Path(tempfile.mkdtemp(prefix="dp_flat_drop_")) / "Turnier1.m3u"
        m3u.write_text("#EXTM3U\n", encoding="utf-8")
        loaded = []
        t.window()._load_player_list_from_m3u = lambda table, p: loaded.append(p)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(m3u))])
        def _drop(answer):
            with mock.patch.object(gui_table_dnd.QMessageBox, "question",
                                   lambda *a, **k: answer):
                t.dropEvent(QDropEvent(QPointF(20, 2), Qt.DropAction.CopyAction,
                                       mime, Qt.MouseButton.LeftButton,
                                       Qt.KeyboardModifier.NoModifier))

        _drop(_QMessageBox.StandardButton.No)
        self.assertEqual(loaded, [])
        self.assertEqual(self.songs(t), ["LW 1"])
        _drop(_QMessageBox.StandardButton.Yes)
        self.assertEqual(loaded, [m3u], "the drop no longer imports at all")


class PlayerRoundSectionsTest(_FlatTest):
    """Which round each track of an imported .m3u is played in: the markers this
    app writes, else the order itself, else nothing (the dance then groups)."""

    def sections(self, lines, entries):
        from gui.main_generate import GenerateMixin

        path = Path(tempfile.mkdtemp(prefix="dp_flat_sec_")) / "list.m3u"
        path.write_text("\n".join(lines), encoding="utf-8")
        return GenerateMixin()._player_round_sections(path, entries)

    def test_the_markers_win(self):
        """Their names are the real ones — 'Endrunde' is not guessable from an
        order that reads like any other two-pass list."""
        entries = [_e("LW", 1), _e("TG", 2)]
        got = self.sections(["#EXTM3U",
                             "# ═══  Vorrunde  (1 Heat)  ═══",
                             r"C:\music\LW1.mp3",
                             "# ═══  Endrunde  (1 Heat)  ═══",
                             r"C:\music\TG2.mp3"], entries)
        self.assertEqual(got, {r"C:\music\LW1.mp3": "Vorrunde",
                               r"C:\music\TG2.mp3": "Endrunde"})

    def test_a_marker_less_file_is_read_from_its_order(self):
        entries = [_e("LW", 1), _e("TG", 2), _e("LW", 3), _e("TG", 4)]
        got = self.sections([str(e.path) for e in entries], entries)
        self.assertEqual(list(got.values()),
                         ["Vorrunde", "Vorrunde", "Finale", "Finale"])

    def test_one_pass_leaves_the_dances_to_group(self):
        entries = [_e("LW", 1), _e("TG", 2)]
        self.assertEqual(self.sections([str(e.path) for e in entries], entries), {})


if __name__ == "__main__":
    unittest.main()
