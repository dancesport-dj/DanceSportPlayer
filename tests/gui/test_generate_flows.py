#!/usr/bin/env python3
"""🎲 Generate: the flows around ⚡ Generate, 📅, 🕑, 🤸 and the .m3u loaders.

Run:  py -m unittest tests.gui.test_generate_flows -v

Each test runs one `GenerateMixin` method against a MagicMock window: the
method under test is the real one, everything it calls on `self` is a recorder
unless the test binds the real sibling too. What is pinned here is the order
of the questions, the guards that stop a run, and the message each exit leaves
on the status bar — not the pixels.
"""

import os
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_genflows_"))

from PySide6.QtWidgets import QDialog

from gui.window import main_generate as gen
from planner import i18n
from planner.models import ALLOW_REPEAT, MusicEntry
from planner.playlist.playlist_text import PlaylistEncodingError

PD = next(iter(ALLOW_REPEAT))


def _e(name, dance="SA"):
    return MusicEntry(path=Path(f"C:/lib/{dance}/{name}.mp3"), title=name,
                      dance=dance, bpm=51)


def _host(*names, **attrs):
    """A MagicMock window whose named methods are the mixin's real ones."""
    h = mock.MagicMock(name="win")
    h._deckset.table._current_play_row = -1
    h._WARMUP_LOGO = "🤸"
    for name in names:
        setattr(h, name, types.MethodType(getattr(gen.GenerateMixin, name), h))
    for key, value in attrs.items():
        setattr(h, key, value)
    return h


def _status(h):
    return h.statusBar().showMessage.call_args.args[0]


class Sig:
    def __init__(self):
        self.slots = []

    def connect(self, fn):
        self.slots.append(fn)


class FakeBusy:
    made = []

    def __init__(self, parent=None, message="", **kw):
        self.message = message
        self.shown_after = None
        self.progress = []
        self.finished = False
        FakeBusy.made.append(self)

    def show_after(self, ms):
        self.shown_after = ms

    def set_progress(self, *args):
        self.progress.append(args)

    def finish(self):
        self.finished = True


class FakeWorker:
    made = []

    def __init__(self, src, mode, params, parent, cache=None):
        self.args = (src, mode, params)
        self.progress, self.done, self.error, self.finished = Sig(), Sig(), Sig(), Sig()
        self.started = False
        FakeWorker.made.append(self)

    def start(self):
        self.started = True


class Case(unittest.TestCase):
    def setUp(self):
        FakeBusy.made, FakeWorker.made = [], []
        self.box = mock.MagicMock(name="QMessageBox")
        for name, value in (("QMessageBox", self.box),
                            ("QApplication", mock.MagicMock()),
                            ("show_toast", mock.MagicMock()),
                            ("BusyDialog", FakeBusy)):
            patcher = mock.patch.object(gen, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        i18n.set_active("en")


class ReplayTabsTest(Case):
    def test_a_fresh_schedule_drops_the_stashed_work(self):
        h = _host("_on_schedule_parsed", _replay_work={1: "x"}, _active_replay_idx=3)
        h._on_schedule_parsed()
        self.assertEqual((h._replay_work, h._active_replay_idx), ({}, None))

    def test_outside_past_competitions_the_combo_does_nothing(self):
        h = _host("_on_replay_competition_changed")
        h._cfg.get_mode.return_value = "Favorites"
        h._on_replay_competition_changed(1)
        h._stash_replay_work.assert_not_called()

    def test_picking_the_same_competition_again_does_nothing(self):
        h = _host("_on_replay_competition_changed", _active_replay_idx=2)
        h._cfg.get_mode.return_value = "Past Competitions"
        h._on_replay_competition_changed(2)
        h._stash_replay_work.assert_not_called()

    def test_the_one_left_is_stashed_and_a_worked_one_restored(self):
        h = _host("_on_replay_competition_changed", _active_replay_idx=0,
                  _replay_work={1: "saved"})
        h._cfg.get_mode.return_value = "Past Competitions"
        h._on_replay_competition_changed(1)
        h._stash_replay_work.assert_called_once_with(0)
        h._restore_replay_work.assert_called_once_with(1)
        self.assertEqual(h._active_replay_idx, 1)

    def test_a_new_competition_shows_an_empty_grid_and_says_how_to_seed_it(self):
        h = _host("_on_replay_competition_changed", _active_replay_idx=None,
                  _replay_work={})
        h._cfg.get_mode.return_value = "Past Competitions"
        h._on_replay_competition_changed(4)
        h._clear_replay_grid.assert_called_once()
        self.assertIn("Generate from History", _status(h))

    def test_clearing_the_grid_stops_the_title_playing_from_it(self):
        h = _host("_clear_replay_grid")
        h._deckset.table._current_play_row = 3
        h._clear_replay_grid()
        h._play_or_stop.assert_called_once_with(None)
        h._deckset.table.setRowCount.assert_called_once_with(0)
        h._cfg.save_btn.setEnabled.assert_called_once_with(False)
        h._show_hints.assert_called_once_with([])
        self.assertIsNone(h._playlist)

    def test_clearing_an_idle_grid_stops_nothing(self):
        h = _host("_clear_replay_grid")
        h._clear_replay_grid()
        h._play_or_stop.assert_not_called()

    def test_stale_tooltip_sources_are_dropped_from_every_entry(self):
        entries = [SimpleNamespace(replay_sources=["a"]), SimpleNamespace(replay_sources=["b"])]
        h = _host("_clear_replay_sources")
        h._library.lib.entries = entries
        h._clear_replay_sources()
        self.assertEqual([e.replay_sources for e in entries], [None, None])
        h._library.lib = None
        h._clear_replay_sources()


class BlankDeckTest(Case):
    def test_the_focused_deck_goes_back_to_the_defaults(self):
        h = _host("_blank_deck")
        table = h._deckset.table
        table._current_play_row = 2
        h.deck.return_value.default_name = "Playlist 1"
        h._blank_deck(table)
        h._play_or_stop.assert_called_once_with(None)
        table.setRowCount.assert_called_once_with(0)
        self.assertEqual((table._dynamic, table._style, table._m3u_path), (False, "", None))
        h._set_deck_name.assert_called_once_with(table, "Playlist 1")
        self.assertEqual((h._mode, h._age, h._replay_active), ("Favorites", "", False))
        h._cfg.reset_to_defaults.assert_called_once()

    def test_keep_playing_leaves_the_title_running(self):
        h = _host("_blank_deck")
        h._deckset.table._current_play_row = 2
        h._blank_deck(h._deckset.table, keep_playing=True)
        h._play_or_stop.assert_not_called()

    def test_another_deck_loses_its_context_but_not_the_panel(self):
        h = _host("_blank_deck")
        other = mock.MagicMock()
        other._current_play_row = -1
        h.deck.return_value.default_name = ""
        h._blank_deck(other)
        self.assertIsNone(h.deck.return_value.ctx)
        h._set_deck_name.assert_not_called()
        h._cfg.reset_to_defaults.assert_not_called()

    def test_a_header_del_focuses_a_background_deck_before_wiping_it(self):
        h = _host("_on_table_cleared")
        other = mock.MagicMock()
        h._is_deck.return_value = True
        h._on_table_cleared(other)
        h._set_active_table.assert_called_once_with(other)
        h._blank_deck.assert_called_once_with(other)
        h._autosave_playlist.assert_called_once()

    def test_the_focused_deck_needs_no_refocus(self):
        h = _host("_on_table_cleared")
        h._is_deck.return_value = True
        h._on_table_cleared(h._deckset.table)
        h._set_active_table.assert_not_called()


class SourcePickersTest(Case):
    def test_choosing_folders_needs_a_library(self):
        h = _host("_choose_source_folders")
        h._library.lib = None
        with mock.patch.object(gen, "ask_library_folders") as ask:
            h._choose_source_folders()
        ask.assert_not_called()

    def test_the_picked_folders_are_kept_and_a_cancel_changes_nothing(self):
        h = _host("_choose_source_folders", _settings={"library_dir": "C:/lib"})
        with mock.patch.object(gen, "ask_library_folders", return_value=["SA"]):
            h._choose_source_folders()
        h._cfg.set_source_folders.assert_called_once_with(["SA"])
        h._cfg.set_source_folders.reset_mock()
        with mock.patch.object(gen, "ask_library_folders", return_value=None):
            h._choose_source_folders()
        h._cfg.set_source_folders.assert_not_called()

    def test_browsing_for_an_m3u_remembers_the_file(self):
        h = _host("_browse_source_m3u", _settings={"playlist_dir": None})
        with mock.patch.object(gen.QFileDialog, "getOpenFileName",
                               return_value=("C:/p/party.m3u", "")):
            h._browse_source_m3u()
        h._cfg.set_source_m3u.assert_called_once_with("C:/p/party.m3u")
        h._cfg.set_source_m3u.reset_mock()
        with mock.patch.object(gen.QFileDialog, "getOpenFileName", return_value=("", "")):
            h._browse_source_m3u()
        h._cfg.set_source_m3u.assert_not_called()

    def test_a_library_not_loaded_yet_is_named_as_the_problem(self):
        h = _host("_source_library")
        h._library.lib = None
        self.assertEqual(h._source_library(),
                         (None, "", "The music library is not loaded yet."))

    def test_without_the_tick_the_pool_is_returned_untouched(self):
        h = _host("_skip_planned")
        h._cfg.skip_planned.return_value = False
        lib = mock.MagicMock()
        self.assertIs(h._skip_planned(lib), lib)

    def test_with_the_tick_titles_in_other_decks_are_left_out(self):
        planned = _e("Planned")
        free = _e("Free")
        lib = mock.MagicMock()
        lib.entries = [planned, free]
        h = _host("_skip_planned")
        h._cfg.skip_planned.return_value = True
        h._deck_dedup_index.return_value = (set(), set())
        h._library.cache = None
        with mock.patch.object(gen, "is_planned",
                               side_effect=lambda path, *_a: path == planned.path):
            h._skip_planned(lib)
        lib.restricted_to.assert_called_once_with([free])

    def test_the_cache_supplies_the_fingerprint_lookup(self):
        lib = mock.MagicMock()
        lib.entries = [_e("A")]
        h = _host("_skip_planned")
        h._cfg.skip_planned.return_value = True
        h._deck_dedup_index.return_value = (set(), set())
        with mock.patch.object(gen, "is_planned", return_value=False) as planned:
            h._skip_planned(lib)
        self.assertIs(planned.call_args.args[3], h._library.cache.known_fingerprint)


class GenerateTest(Case):
    def setUp(self):
        super().setUp()
        self.pool = mock.MagicMock()
        self.rounds = [SimpleNamespace(heats=2)]
        self.h = _host("_generate", _iteration=1, _style="")
        self.h._cfg.get_mode.return_value = "Favorites"
        self.h._cfg.get_config.return_value = ("Latin", "Hauptgruppe", "S",
                                               ["SA", "CH"], self.rounds, False)
        self.h._cfg.rounds_valid = True
        self.h._source_library.return_value = (self.pool, "", "")
        self.h._skip_planned.return_value = self.pool

    def run_generate(self, suggester=None, gap=""):
        fake = suggester or mock.MagicMock()
        with mock.patch.object(gen, "PlaylistSuggester", return_value=fake), \
                mock.patch.object(gen, "generate_hints", return_value=["hint"]), \
                mock.patch.object(gen, "source_gap_hint", return_value=gap):
            self.h._generate()
        return fake

    def test_no_library_means_nothing_happens(self):
        self.h._library.lib = None
        self.run_generate()
        self.h._cfg.get_mode.assert_not_called()

    def test_the_mode_routes_to_its_own_generator(self):
        for mode, name in (("Theme", "_generate_theme"), ("Past Competitions", "_generate_replay")):
            with self.subTest(mode=mode):
                self.h._cfg.get_mode.return_value = mode
                self.run_generate()
                getattr(self.h, name).assert_called_once()

    def test_no_dances_is_a_warning(self):
        self.h._cfg.get_config.return_value = ("Latin", "H", "S", [], self.rounds, False)
        self.run_generate()
        self.assertEqual(self.box.warning.call_args.args[1], "No Dances")

    def test_no_valid_round_pattern_is_a_warning(self):
        self.h._cfg.rounds_valid = False
        self.run_generate()
        self.assertEqual(self.box.warning.call_args.args[1], "No Rounds")

    def test_a_source_with_nothing_to_give_says_why(self):
        self.h._source_library.return_value = (None, "", "Choose an .m3u file first.")
        self.run_generate()
        self.box.information.assert_called_once()
        self.assertEqual(self.box.information.call_args.args[2], "Choose an .m3u file first.")

    def test_a_failing_suggester_is_reported_and_the_button_comes_back(self):
        bad = mock.MagicMock()
        bad.suggest.side_effect = RuntimeError("boom")
        self.run_generate(bad)
        self.assertEqual(self.box.critical.call_args.args[2], "boom")
        self.h._cfg.generate_btn.setEnabled.assert_called_with(True)
        self.assertIn("Error generating playlist: boom", _status(self.h))

    def test_a_grid_that_fails_to_load_does_not_leave_the_button_grey(self):
        """Only the suggester was inside the try: an error in the load, the
        naming or the reveal left Generate disabled until the next start."""
        self.h._deckset.table.load.side_effect = RuntimeError("no room")
        with self.assertRaises(RuntimeError):
            self.run_generate()
        self.h._cfg.generate_btn.setEnabled.assert_called_with(True)

    def test_a_good_run_loads_the_grid_and_reports_the_song_count(self):
        self.run_generate(gap="gap")
        self.h._deckset.table.load.assert_called_once()
        self.h._show_hints.assert_called_once_with(["gap", "hint"])
        self.h._cfg.save_btn.setEnabled.assert_called_with(True)
        self.assertEqual(_status(self.h), "Generated 4 songs — Latin, Hauptgruppe, S  (iteration 2)")

    def test_a_restricted_source_is_named_in_the_report(self):
        self.h._source_library.return_value = (self.pool, "📂 party.m3u", "")
        self.run_generate()
        self.assertTrue(_status(self.h).endswith(" — from 📂 party.m3u"))


class TournamentDayTest(Case):
    def setUp(self):
        super().setUp()
        self.free = SimpleNamespace(state=None)
        self.full = SimpleNamespace(state="old")
        self.h = _host("_plan_tournament_day", "_mark_day_played")
        self.h._serialize_playlist_state = lambda t: t.state
        self.h._favorites_deck_name = lambda age, cls, style: f"{style} {age} {cls}"
        self.h._cfg.get_config.return_value = ("Latin", "H", "S", [], [], False)
        self.h._deckset.day_decks = [self.free]
        self.good = dict(style="Latin", age="Hauptgruppe", cls="S", pattern="2-1")
        self.bad = dict(style="Nope", age="x", cls="S", pattern="2-1")

    def dialog(self, comps, result=QDialog.DialogCode.Accepted):
        dlg = mock.MagicMock()
        dlg.exec.return_value = result
        dlg.competitions.return_value = comps
        return mock.patch.object(gen, "TournamentDayDialog", return_value=dlg)

    def suggester(self, fail_on=()):
        calls = []

        def make(_lib):
            sug = mock.MagicMock()

            def suggest(*_a, **_kw):
                calls.append(1)
                if len(calls) in fail_on:
                    raise RuntimeError("no songs")
                return {"Final": [[_e(f"T{len(calls)}")]]}
            sug.suggest.side_effect = suggest
            return sug
        return mock.patch.object(gen, "PlaylistSuggester", side_effect=make)

    def plan(self, comps, fail_on=()):
        with self.dialog(comps), self.suggester(fail_on), \
                mock.patch.object(gen, "spread_over_decks",
                                  side_effect=lambda free, cs: [(free[0], cs)]):
            self.h._plan_tournament_day()

    def test_no_library_no_dialog(self):
        self.h._library.lib = None
        with self.dialog([]) as dlg:
            self.h._plan_tournament_day()
        dlg.assert_not_called()

    def test_a_cancelled_or_empty_dialog_plans_nothing(self):
        with self.dialog([self.good], QDialog.DialogCode.Rejected):
            self.h._plan_tournament_day()
        with self.dialog([]):
            self.h._plan_tournament_day()
        self.h._load_day_deck.assert_not_called()

    def test_an_earlier_plan_asks_before_it_is_replaced(self):
        self.h._deckset.day_decks = [self.full, self.free]
        self.box.question.return_value = self.box.StandardButton.Yes
        self.plan([self.good])
        self.box.question.assert_called_once()
        self.h._blank_deck.assert_called_once_with(self.full)

    def test_a_no_with_a_free_deck_plans_beside_the_old_one(self):
        self.h._deckset.day_decks = [self.full, self.free]
        self.box.question.return_value = self.box.StandardButton.No
        self.plan([self.good])
        self.h._blank_deck.assert_not_called()
        self.h._load_day_deck.assert_called_once()

    def test_a_no_with_every_deck_taken_stops_there(self):
        self.h._deckset.day_decks = [self.full]
        self.box.question.return_value = self.box.StandardButton.No
        self.plan([self.good])
        self.h._load_day_deck.assert_not_called()

    def test_competitions_that_cannot_be_planned_are_listed_as_skipped(self):
        self.plan([self.good, self.bad, dict(self.good)], fail_on=(2,))
        parts = self.h._load_day_deck.call_args.args[1]
        self.assertEqual(len(parts), 1)
        targets, built, used_today, decks_used, skipped = self.h._report_day_plan.call_args.args
        self.assertEqual((targets, built, decks_used), ([self.free], 1, 1))
        self.assertEqual(len(skipped), 2)
        self.assertTrue(skipped[1].endswith("— no songs"))
        self.assertEqual(len(used_today), 1)

    def test_a_day_of_nothing_loads_no_deck(self):
        self.plan([self.bad])
        self.h._load_day_deck.assert_not_called()
        self.assertEqual(self.h._report_day_plan.call_args.args[1], 0)

    def test_paso_doble_may_repeat_so_it_is_not_spent(self):
        playlist = {"R": [[_e("A"), None, _e("P", PD)]]}
        used = set()
        self.h._mark_day_played(playlist, used)
        self.assertEqual(used, {str(_e("A").path)})


class DayReportTest(Case):
    def setUp(self):
        super().setUp()
        self.h = _host("_report_day_plan")

    def test_a_built_day_is_revealed_and_announced(self):
        targets = [mock.MagicMock()]
        self.h._report_day_plan(targets, 2, {"a", "b", "c"}, 1, [])
        self.h._set_active_table.assert_called_once_with(targets[0])
        self.h._autosave_playlist.assert_called_once()
        self.assertIn("2 competition(s) generated", self.h._show_hints.call_args.args[0][0])
        gen.show_toast.assert_called_once()
        self.box.warning.assert_not_called()
        self.assertEqual(_status(self.h), "📅 Day plan: 2 competition(s) generated")

    def test_skipped_ones_get_a_warning_and_a_count(self):
        self.h._report_day_plan([None], 0, set(), 0, ["Latin S", "Std A — boom"])
        self.assertIn("• Std A — boom", self.box.warning.call_args.args[2])
        self.h._apply_deck_view.assert_not_called()
        self.assertEqual(_status(self.h), "📅 Day plan: 0 generated, 2 skipped")


class DayDeckTest(Case):
    def part(self, label, dance="SA"):
        return {"label": label, "playlist": {"R": []}, "dances": [dance],
                "rounds": [SimpleNamespace(name="R")], "cls": "S", "style": "Latin",
                "age": "Hauptgruppe", "suggester": mock.MagicMock()}

    def test_one_competition_fills_the_deck_under_its_own_name(self):
        h = _host("_load_day_deck")
        first = self.part("Latin S")
        h._load_day_deck(h._deckset.table, [first], False)
        self.assertIs(h._playlist, first["playlist"])
        h._deckset.table.load.assert_called_once()
        h._set_deck_name.assert_called_once_with(h._deckset.table, "📅  Latin S")

    def test_several_share_the_deck_and_the_name_joins_them(self):
        h = _host("_load_day_deck")
        merged = ({"R": []}, ["SA", "CH"], ["rounds"], {"R": []}, {"R": {}})
        with mock.patch.object(gen.planner.models, "merge_day_playlists",
                               return_value=merged):
            h._load_day_deck(h._deckset.table, [self.part("A"), self.part("B")], True)
        kwargs = h._deckset.table.load.call_args.kwargs
        self.assertEqual((kwargs["round_skip_dances"], kwargs["round_ctx"]),
                         ({"R": []}, {"R": {}}))
        self.assertEqual(h._dances, ["SA", "CH"])
        h._set_deck_name.assert_called_once_with(h._deckset.table, "📅  A  +  B")


class ReplayGenerateTest(Case):
    def setUp(self):
        super().setUp()
        self.spec = SimpleNamespace(label="Latin S", dances=["SA", "CH"],
                                    dance_class="S", style="Latin")
        self.rounds = [SimpleNamespace(name="Final", heats=1)]
        self.e1 = SimpleNamespace(replay_sources=None)
        self.h = _host("_generate_replay", _iteration=0)
        self.h._cfg.get_replay_config.return_value = (self.spec, self.rounds, True)
        self.h._library.lib.past_competition_round_pools.return_value = (
            [self.e1], [[1, 2, 3]], 2, [{id(self.e1): ("List A",)}])

    def run_replay(self, suggester=None):
        fake = suggester or mock.MagicMock()
        with mock.patch.object(gen, "PlaylistSuggester", return_value=fake):
            self.h._generate_replay()
        return fake

    def test_no_library_no_run(self):
        self.h._library.lib = None
        self.run_replay()
        self.h._cfg.get_replay_config.assert_not_called()

    def test_no_picked_competition_is_a_warning(self):
        self.h._cfg.get_replay_config.return_value = None
        self.run_replay()
        self.assertEqual(self.box.warning.call_args.args[1], "No Competition")

    def test_a_competition_without_heat_counts_is_a_warning(self):
        self.h._cfg.get_replay_config.return_value = (self.spec, [], True)
        self.run_replay()
        self.assertEqual(self.box.warning.call_args.args[1], "No Rounds")

    def test_unreadable_history_is_reported(self):
        self.h._library.lib.past_competition_round_pools.side_effect = OSError("gone")
        self.run_replay()
        self.assertEqual(self.box.critical.call_args.args[1], "History Error")
        self.assertIn("Error reading past playlists", _status(self.h))

    def test_a_failing_suggester_is_reported(self):
        bad = mock.MagicMock()
        bad.suggest.side_effect = RuntimeError("boom")
        self.run_replay(bad)
        self.assertEqual(self.box.critical.call_args.args[1], "Generate Error")
        self.h._adopt_replay_spec.assert_not_called()

    def test_a_seeded_run_tags_each_track_with_the_lists_it_came_from(self):
        self.run_replay()
        self.assertEqual(self.e1.replay_sources, ["List A"])
        self.h._adopt_replay_spec.assert_called_once_with(self.spec)
        args = self.h._show_replay_hints.call_args.args
        self.assertEqual(args[2:], (self.rounds, [[1, 2, 3]], True, 2))
        self.assertEqual(_status(self.h), "Generated 2 songs — Latin S")

    def test_without_history_the_whole_library_is_used_and_a_rerun_says_so(self):
        self.h._library.lib.past_competition_round_pools.return_value = ([], [[]], 0, [{}])
        self.h._iteration = 1
        self.run_replay()
        self.assertIsNone(self.h._show_replay_hints.call_args.args[3])
        self.assertIs(self.h._show_replay_hints.call_args.args[4], False)
        self.assertEqual(_status(self.h), "Generated 2 songs — Latin S  (iteration 2)")

    def test_the_hints_lead_with_where_the_pools_came_from(self):
        h = _host("_show_replay_hints", _playlist={})
        rounds = [SimpleNamespace(name="Final")]
        with mock.patch.object(gen, "generate_hints", return_value=["x"]):
            h._show_replay_hints(mock.MagicMock(), self.spec, rounds, [[1, 2, 3]], True, 2)
            self.assertIn("round pool sizes: Final:3", h._show_hints.call_args.args[0][0])
            self.assertEqual(h._show_hints.call_args.args[0][1], "x")
            h._show_replay_hints(mock.MagicMock(), self.spec, rounds, None, False, 0)
            self.assertIn("No past", h._show_hints.call_args.args[0][0])

    def test_adopting_the_spec_makes_it_the_active_tab(self):
        h = _host("_adopt_replay_spec", _replay_work={0: "old"})
        h._cfg.replay_combo.currentIndex.return_value = 0
        h._adopt_replay_spec(self.spec)
        self.assertEqual((h._style, h._age, h._ui_mode), ("Latin", "Latin S", "Past Competitions"))
        self.assertEqual(h._replay_work, {})
        self.assertEqual(h._active_replay_idx, 0)

    def test_the_scope_toggle_decides_which_rounds_keep_their_history(self):
        h = _host("_effective_replay_pools", _replay_pools=None)
        self.assertIsNone(h._effective_replay_pools())
        h._replay_pools = [["p1"]]
        h._replay_rounds = [SimpleNamespace(name="A"), SimpleNamespace(name="B")]
        h._cfg.round_scope.side_effect = lambda name: name == "A"
        self.assertEqual(h._effective_replay_pools(), [["p1"], None])
        h._cfg.round_scope.side_effect = lambda name: False
        self.assertEqual(h._effective_replay_pools(), [None, None])


class StrategyTest(Case):
    def favorites(self, **attrs):
        self.rc = SimpleNamespace(name="R1", strategy=None, prefer_fresh=False)
        playlist = {"R1": [[_e("Mine")]],
                    "R2": [[_e("Other"), None, _e("Pd", PD)]]}
        h = _host("_on_favorites_strategy_changed", _mode="Favorites",
                  _playlist=playlist, _suggester=mock.MagicMock(), _dances=["SA"],
                  _dance_class="S", _style="Latin", **attrs)
        h._cfg._round_cfgs = [self.rc]
        h._cfg.auto_reroll_check.isChecked.return_value = True
        h._cfg.timbre_check.isChecked.return_value = False
        return h

    def test_the_change_goes_to_the_handler_of_the_active_mode(self):
        h = _host("_on_strategy_changed", _replay_active=True)
        h._on_strategy_changed("R1", "fresh")
        h._on_replay_strategy_changed.assert_called_once_with("R1", "fresh")
        h._replay_active = False
        h._on_strategy_changed("R1", "fresh")
        h._on_favorites_strategy_changed.assert_called_once_with("R1", "fresh")

    def test_the_timbre_toggle_reaches_the_table_and_the_status_bar(self):
        h = _host("_on_timbre_toggled")
        h._on_timbre_toggled(True)
        h._deckset.table.set_use_timbre.assert_called_once_with(True)
        self.assertIn("on for", _status(h))
        h._on_timbre_toggled(False)
        self.assertIn("off for", _status(h))

    def test_favorites_guards(self):
        for attr, value in (("_mode", "Theme"), ("_playlist", None), ("_suggester", None)):
            with self.subTest(attr=attr):
                h = self.favorites()
                setattr(h, attr, value)
                h._on_favorites_strategy_changed("R1", "fresh")
                h._deckset.table.load.assert_not_called()
        h = self.favorites()
        h._on_favorites_strategy_changed("Nope", "fresh")
        h._cfg._round_cfgs = []
        h._on_favorites_strategy_changed("R1", "fresh")
        h._deckset.table.load.assert_not_called()

    def test_with_auto_reroll_off_only_the_strategy_is_remembered(self):
        h = self.favorites()
        h._cfg.auto_reroll_check.isChecked.return_value = False
        h._on_favorites_strategy_changed("R1", "fresh")
        h._deckset.table.update_strategy.assert_called_once_with("R1", "fresh", True)
        self.assertTrue(self.rc.prefer_fresh)
        self.assertIn("strategy set to", _status(h))
        h._suggester.regenerate_round.assert_not_called()

    def test_with_auto_reroll_on_the_other_rounds_are_held_out(self):
        h = self.favorites()
        h._deckset.table._current_play_row = 1
        h._on_favorites_strategy_changed("R1", "proven")
        used, pd_used = h._suggester.regenerate_round.call_args.args[3:5]
        self.assertEqual(pd_used, {str(_e("Pd", PD).path)})
        self.assertTrue(used)
        h._play_or_stop.assert_called_once_with(None)
        h._deckset.table.load.assert_called_once()
        self.assertIn("re-rolled", _status(h))

    def test_the_reroll_hands_the_decks_pins_marks_and_context_back(self):
        """load() resets whatever it is not handed, and then autosaves that."""
        h = self.favorites()
        kept = {"marked": {"m"}, "pinned": {"p"},
                "round_skip_dances": {"R1": {"CC"}}, "round_ctx": {"R1": {"x": 1}}}
        h._deckset.table._reloadKwargs.return_value = dict(kept)
        h._on_favorites_strategy_changed("R1", "proven")
        got = h._deckset.table.load.call_args.kwargs
        for key, value in kept.items():
            self.assertEqual(got[key], value, key)
        h._deckset.table._reloadKwargs.assert_called_once_with(h._cfg._round_cfgs)

    def test_a_failed_reroll_keeps_the_grid(self):
        h = self.favorites()
        h._suggester.regenerate_round.side_effect = RuntimeError("x")
        h._on_favorites_strategy_changed("R1", "proven")
        h._deckset.table.load.assert_not_called()
        self.assertIn("Re-roll failed", _status(h))

    def replay(self, pools=("P1", "P2")):
        self.rc = SimpleNamespace(name="R1", strategy=None, prefer_fresh=False)
        playlist = {"R1": [[_e("Mine")]], "R2": [[_e("Other"), None, _e("Pd", PD)]]}
        h = _host("_on_replay_strategy_changed", _replay_active=True,
                  _playlist=playlist, _suggester=mock.MagicMock(), _dances=["SA"],
                  _dance_class="S", _style="Latin", _replay_use_timbre=False,
                  _replay_rounds=[self.rc], _replay_pools=list(pools) if pools else None)
        h._cfg.auto_reroll_check.isChecked.return_value = True
        h._cfg.round_scope.return_value = True
        return h

    def test_replay_guards(self):
        for attr, value in (("_replay_active", False), ("_playlist", None), ("_suggester", None)):
            with self.subTest(attr=attr):
                h = self.replay()
                setattr(h, attr, value)
                h._on_replay_strategy_changed("R1", "fresh")
                h._deckset.table.load.assert_not_called()
        h = self.replay()
        h._on_replay_strategy_changed("Nope", "fresh")
        h._replay_rounds = []
        h._on_replay_strategy_changed("R1", "fresh")
        h._deckset.table.load.assert_not_called()

    def test_replay_with_auto_reroll_off_hands_the_buttons_the_scope(self):
        h = self.replay()
        h._cfg.auto_reroll_check.isChecked.return_value = False
        h._on_replay_strategy_changed("R1", "fresh")
        h._deckset.table.set_round_pool.assert_called_once_with("R1", "P1")
        self.assertIn("this comp", _status(h))
        h._cfg.round_scope.return_value = False
        h._on_replay_strategy_changed("R1", "fresh")
        h._deckset.table.set_round_pool.assert_called_with("R1", None)
        self.assertIn("all playlists", _status(h))

    def test_replay_with_auto_reroll_draws_from_the_rounds_own_history(self):
        h = self.replay()
        h._deckset.table._current_play_row = 0
        h._on_replay_strategy_changed("R1", "proven")
        self.assertEqual(h._suggester.regenerate_round.call_args.kwargs["candidates"], "P1")
        h._play_or_stop.assert_called_once_with(None)
        h._deckset.table.load.assert_called_once()
        self.assertIn("this comp", _status(h))

    def test_the_replay_reroll_hands_the_decks_pins_marks_and_context_back(self):
        h = self.replay()
        h._effective_replay_pools = mock.Mock(return_value=["fresh pools"])
        kept = {"marked": {"m"}, "pinned": {"p"},
                "round_skip_dances": {"R1": {"CC"}}, "round_ctx": {"R1": {"x": 1}},
                "round_pools": ["stale pools"]}
        h._deckset.table._reloadKwargs.return_value = dict(kept)
        h._on_replay_strategy_changed("R1", "proven")
        got = h._deckset.table.load.call_args.kwargs
        for key in ("marked", "pinned", "round_skip_dances", "round_ctx"):
            self.assertEqual(got[key], kept[key], key)
        self.assertEqual(got["round_pools"], ["fresh pools"])

    def test_replay_without_history_pools_falls_back_to_the_library(self):
        h = self.replay(pools=None)
        h._on_replay_strategy_changed("R1", "proven")
        self.assertIsNone(h._suggester.regenerate_round.call_args.kwargs["candidates"])

    def test_a_failed_replay_reroll_keeps_the_grid(self):
        h = self.replay()
        h._suggester.regenerate_round.side_effect = RuntimeError("x")
        h._on_replay_strategy_changed("R1", "proven")
        h._deckset.table.load.assert_not_called()
        self.assertIn("Re-roll failed", _status(h))


class ThemeTest(Case):
    def setUp(self):
        super().setUp()
        self.h = _host("_generate_theme")
        self.h._cfg.get_theme_config.return_value = ("xmas", "Christmas", 20)

    def run_theme(self, entries=None, error=None):
        sug = mock.MagicMock()
        if error:
            sug.suggest_theme.side_effect = error
        else:
            sug.suggest_theme.return_value = entries or []
        with mock.patch.object(gen, "PlaylistSuggester", return_value=sug):
            self.h._generate_theme()

    def test_no_theme_picked_is_a_warning(self):
        self.h._cfg.get_theme_config.return_value = ("", "", 0)
        self.run_theme()
        self.assertEqual(self.box.warning.call_args.args[1], "No Theme")

    def test_a_failing_suggester_is_reported_and_the_button_comes_back(self):
        self.run_theme(error=RuntimeError("x"))
        self.assertEqual(self.box.critical.call_args.args[1], "Theme Error")
        self.h._cfg.generate_btn.setEnabled.assert_called_with(True)

    def test_no_matches_empties_the_deck_and_says_what_to_tag(self):
        self.h._deckset.table._current_play_row = 0
        self.run_theme([])
        self.h._play_or_stop.assert_called_once_with(None)
        self.h._deckset.table.setRowCount.assert_called_once_with(0)
        self.h._cfg.save_btn.setEnabled.assert_called_with(False)
        self.assertIn("No tracks matched theme 'Christmas'", self.box.information.call_args.args[2])
        self.assertEqual(_status(self.h), "No tracks matched 'Christmas'.")

    def test_matches_are_loaded_with_a_dance_mix_hint(self):
        self.run_theme([_e("A"), _e("B"), _e("C", "CH")])
        self.h._deckset.table.load_theme.assert_called_once()
        self.assertEqual(self.h._ui_mode, "Theme")
        self.assertIn("3 tracks", self.h._show_hints.call_args.args[0][0])
        self.assertIn("×2", self.h._show_hints.call_args.args[0][0])
        self.assertEqual(_status(self.h), "Theme 'Christmas' — 3 tracks")


class M3uLoadTest(Case):
    def test_the_dialog_gets_the_wishlist_names_and_counts(self):
        wl = mock.MagicMock()
        wl.wishlist_entries.return_value = [1, 2]
        h = _host("_ask_warmup_options", _settings={"library_dir": ""})
        h._wishlists_with_titles.return_value = [wl]
        h.deck.return_value.name = ""
        h._library.lib = None
        with mock.patch.object(gen, "ask_warmup_options", return_value="opts") as ask:
            self.assertEqual(h._ask_warmup_options(), "opts")
        self.assertEqual(ask.call_args.args[1:4], ([], "", [("⭐  Wishlist", 2)]))

    def test_only_wishlists_with_titles_count(self):
        full, empty = mock.MagicMock(), mock.MagicMock()
        full.wishlist_entries.return_value = [1]
        empty.wishlist_entries.return_value = []
        h = _host("_wishlists_with_titles")
        h._deckset.wishlists = [empty, full]
        self.assertEqual(h._wishlists_with_titles(), [full])

    def test_an_m3u_resolves_through_the_library(self):
        h = _host("_entries_from_m3u_file")
        with mock.patch.object(gen, "read_playlist_text", return_value=("a\nb", "utf-8")), \
                mock.patch.object(gen, "playlist_paths", return_value=["a", "b"]), \
                mock.patch.object(gen, "resolve_playlist_entries",
                                  return_value=["E"]) as resolve:
            self.assertEqual(h._entries_from_m3u_file("C:/p/x.m3u", keep_repeats=True), ["E"])
        self.assertTrue(resolve.call_args.kwargs["keep_repeats"])

    def test_no_library_or_an_unreadable_file_gives_nothing(self):
        h = _host("_entries_from_m3u_file")
        with mock.patch.object(gen, "read_playlist_text", side_effect=OSError("gone")):
            self.assertEqual(h._entries_from_m3u_file("C:/p/x.m3u"), [])
        h._library.lib = None
        self.assertEqual(h._entries_from_m3u_file("C:/p/x.m3u"), [])

    def test_a_file_in_no_known_encoding_is_shown_not_swallowed(self):
        h = _host("_entries_from_m3u_file")
        with mock.patch.object(gen, "read_playlist_text",
                               side_effect=PlaylistEncodingError("not text")):
            self.assertEqual(h._entries_from_m3u_file("C:/p/x.m3u"), [])
        self.assertEqual(self.box.warning.call_args.args[2], "not text")

    def test_the_progress_dialog_follows_the_tick(self):
        h = _host("_m3u_progress")
        dlg, tick = h._m3u_progress("C:/p/party.m3u")
        self.assertEqual(dlg.shown_after, 250)
        self.assertIn("party.m3u", dlg.message)
        tick(1, 2, "x")
        self.assertEqual(dlg.progress, [(1, 2, "x")])
        gen.QApplication.processEvents.assert_called_once()

    def test_marked_rounds_win_over_the_derived_ones(self):
        a, b = _e("A"), _e("B")
        marked = {gen.path_key(a.path): "Vorrunde", gen.path_key(b.path): "Finale"}
        h = _host("_player_round_sections")
        with mock.patch.object(gen.planner.playlist.m3u, "m3u_marker_rounds",
                               return_value=marked):
            self.assertEqual(h._player_round_sections("x.m3u", [a, b]),
                             {str(a.path): "Vorrunde", str(b.path): "Finale"})

    def test_without_markers_the_rounds_come_from_the_order(self):
        a, b = _e("A"), _e("B")
        h = _host("_player_round_sections")
        with mock.patch.object(gen.planner.playlist.m3u, "m3u_marker_rounds",
                               return_value={}), \
                mock.patch.object(gen.planner.playlist.m3u, "running_order_rounds",
                                  return_value=[("Runde 1", [a, b])]) as order:
            got = h._player_round_sections("x.m3u", [a, b], warmup=False)
        self.assertEqual(got, {str(a.path): "Runde 1", str(b.path): "Runde 1"})
        self.assertIs(order.call_args.kwargs["warmup"], False)

    def player_list(self, entries, sections=None):
        h = _host("_load_player_list_from_m3u")
        h._entries_from_m3u_file.return_value = entries
        h._m3u_progress.return_value = (FakeBusy(), lambda *a, **k: None)
        h._player_round_sections.return_value = sections or {}
        table = mock.MagicMock()
        with mock.patch.object(gen, "PlaylistSuggester"):
            h._load_player_list_from_m3u(table, "C:/p/evening.m3u")
        return h, table

    def test_a_player_list_that_loads_nothing_says_so(self):
        h, table = self.player_list([])
        table.load_player_list.assert_not_called()
        self.assertIn("Nothing loadable from evening.m3u", _status(h))

    def test_a_player_list_becomes_the_decks_running_order(self):
        h, table = self.player_list([_e("A")], {"p": "Finale"})
        table.load_player_list.assert_called_once()
        self.assertEqual(table._m3u_path, Path("C:/p/evening.m3u"))
        h._set_deck_name.assert_called_once_with(table, "evening")
        self.assertEqual(_status(h), "evening — 1 tracks")
        self.assertTrue(FakeBusy.made[0].finished)


class WarmupPanelM3uTest(Case):
    def load(self, entries, heat_plan=(), sections=None):
        h = _host("_load_warmup_from_m3u")
        h._entries_from_m3u_file.return_value = entries
        busy = FakeBusy()
        h._m3u_progress.return_value = (busy, lambda *a, **k: None)
        h._warmup_title = lambda s: "🤸 " + s
        h._player_round_sections.return_value = sections or {}
        table = mock.MagicMock()
        with mock.patch.object(gen, "PlaylistSuggester"), \
                mock.patch.object(gen.planner.playlist.m3u, "m3u_marker_heats",
                                  return_value=list(heat_plan)):
            h._load_warmup_from_m3u(table, "C:/p/party.m3u")
        return h, table, busy

    def test_nothing_loadable_leaves_the_panel_alone(self):
        h, table, busy = self.load([])
        table.load_warmup.assert_not_called()
        self.assertTrue(busy.finished)
        self.assertIn("nothing loadable from party.m3u", _status(h))

    def test_a_training_list_with_every_title_keeps_its_heats(self):
        h, table, _busy = self.load([_e("A"), _e("B")], [("Final", 2, 2)])
        self.assertEqual(table.load_warmup.call_args.kwargs["heat_plan"], [("Final", 2, 2)])
        table._remove_duplicate_titles.assert_called_once_with(on_load=True)
        h._party_list_alone.assert_called_once()

    def test_a_training_list_missing_titles_loses_its_heats(self):
        _h, table, _busy = self.load([_e("A")], [("Final", 2, 2)], sections={})
        self.assertEqual(table.load_warmup.call_args.kwargs["heat_plan"], [])

    def test_a_running_order_is_cut_into_the_rounds_it_is_played_in(self):
        _h, table, _busy = self.load([_e("A")], sections={"p": "Finale"})
        table.load_player_list.assert_called_once()
        table.load_warmup.assert_not_called()


class WarmupBuildTest(Case):
    def options(self, **kw):
        base = dict(source="library", unused_only=False, mode="class", style="Latin",
                    dance_class="S", max_tracks=10, fresh_ratio=0.5, relax=True)
        base.update(kw)
        return base

    def start(self, opts, entries=None, planned=()):
        h = _host("_generate_warmup", _settings={"library_dir": "C:/lib"})
        h._library.lib.entries = entries if entries is not None else [_e("A"), _e("B", "CH")]
        h._library.cache = None
        h._ask_warmup_options.return_value = opts
        h._deck_dedup_index.return_value = (set(), set())
        with mock.patch.object(gen, "WarmupBuilder", FakeWorker), \
                mock.patch.object(gen, "is_non_turnier", return_value=False), \
                mock.patch.object(gen, "is_planned",
                                  side_effect=lambda path, *_a: path in planned), \
                mock.patch.object(gen.planner.generate.warmup, "warmup_code",
                                  side_effect=lambda e: e.dance):
            h._generate_warmup()
        return h

    def told(self):
        return self.box.information.call_args.args[2]

    def test_a_library_still_loading_asks_to_try_again(self):
        h = _host("_generate_warmup")
        h._library.lib.entries = []
        h._generate_warmup()
        self.assertIn("still loading", self.told())

    def test_a_cancelled_dialog_builds_nothing(self):
        self.start(None)
        self.assertEqual(FakeWorker.made, [])

    def test_a_class_warmup_starts_its_worker_behind_a_bar(self):
        h = self.start(self.options())
        worker, busy = FakeWorker.made[0], FakeBusy.made[0]
        self.assertTrue(worker.started)
        self.assertEqual(worker.args[1], "class")
        self.assertEqual(worker.args[2]["max_tracks"], 10)
        self.assertEqual(busy.shown_after, 0)
        self.assertIn("Latin S", h._warmup_label)
        self.assertEqual(h._warmup_opts["dances"], {"SA", "CH"})
        self.assertEqual(worker.done.slots, [h._on_warmup_done])
        self.assertEqual(worker.error.slots, [h._on_warmup_error])
        worker.progress.slots[0](3, 9)
        self.assertEqual(busy.progress, [(3, 9)])

    def test_a_competition_training_is_relaxed_and_named_for_the_class(self):
        opts = self.options(mode="competition",
                            competition={"style": "Latin", "dance_class": "A"})
        h = self.start(opts)
        self.assertTrue(FakeWorker.made[0].args[2]["relax"])
        self.assertIn("Latin A", h._warmup_label)

    def test_a_party_list_is_just_called_party(self):
        h = self.start(self.options(mode="party", etds={"late_ww": True}))
        self.assertEqual(h._warmup_label, "Party")
        self.assertEqual(FakeWorker.made[0].args[2], {"late_ww": True})

    def test_an_m3u_source_with_nothing_resolvable_stops(self):
        h = _host("_generate_warmup")
        h._library.lib.entries = [_e("A")]
        h._ask_warmup_options.return_value = self.options(source="m3u", m3u_path="x.m3u")
        h._entries_from_m3u_file.return_value = []
        h._generate_warmup()
        self.assertIn("No resolvable tracks", self.told())

    def test_an_m3u_source_with_tracks_builds_from_them(self):
        h = _host("_generate_warmup", _settings={})
        h._library.lib.entries = [_e("A")]
        h._library.cache = None
        h._ask_warmup_options.return_value = self.options(source="m3u", m3u_path="x.m3u")
        h._entries_from_m3u_file.return_value = [_e("M")]
        with mock.patch.object(gen, "WarmupBuilder", FakeWorker):
            h._generate_warmup()
        self.assertEqual([e.title for e in FakeWorker.made[0].args[0]], ["M"])

    def test_wishlist_sources(self):
        wl = mock.MagicMock()
        wl.wishlist_entries.return_value = [_e("W"), _e("W")]
        for opts, has_titles in ((self.options(source="wishlists"), True),
                                 (self.options(source="wishlists", wishlist_picks=[0]), True),
                                 (self.options(source="wishlists"), False)):
            with self.subTest(picks=opts.get("wishlist_picks"), has_titles=has_titles):
                FakeWorker.made = []
                self.box.reset_mock()
                h = _host("_generate_warmup", _settings={})
                h._library.lib.entries = [_e("A")]
                h._library.cache = None
                h._ask_warmup_options.return_value = opts
                wl.wishlist_entries.return_value = [_e("W"), _e("W")] if has_titles else []
                h._wishlists_with_titles.return_value = [wl]
                with mock.patch.object(gen, "WarmupBuilder", FakeWorker):
                    h._generate_warmup()
                if has_titles:
                    self.assertEqual(len(FakeWorker.made[0].args[0]), 1)
                else:
                    self.assertIn("wishlists are empty", self.told())

    def test_folder_sources(self):
        with mock.patch.object(gen, "entries_in_folders", return_value=[]):
            self.start(self.options(source="folders", folders=["SA"]))
            self.assertIn("hold no titles", self.told())
            self.start(self.options(source="folders", folders=[]))
            self.assertIn("Choose at least one", self.told())
        with mock.patch.object(gen, "entries_in_folders", return_value=[_e("F")]):
            self.start(self.options(source="folders", folders=["SA"]))
        self.assertEqual([e.title for e in FakeWorker.made[0].args[0]], ["F"])

    def test_only_titles_not_yet_in_a_deck_are_used_when_asked(self):
        a, b = _e("A"), _e("B")
        self.start(self.options(unused_only=True), [a, b], planned={a.path})
        self.assertEqual([e.title for e in FakeWorker.made[0].args[0]], ["B"])
        FakeWorker.made = []
        self.start(self.options(unused_only=True), [a, b], planned={a.path, b.path})
        self.assertEqual(FakeWorker.made, [])
        self.assertIn("already in a deck", self.told())

    def test_a_worker_error_is_shown(self):
        h = _host("_on_warmup_error")
        h._on_warmup_error("no memory")
        self.assertEqual(self.box.critical.call_args.args[2], "no memory")
        self.assertEqual(_status(h), "Practice failed.")


class WarmupDoneTest(Case):
    def done(self, entries, opts):
        h = _host("_on_warmup_done", _warmup_opts=opts)
        h._warmup_title = lambda s: "🤸 " + s
        table = h._deckset.warmup_table
        with mock.patch.object(gen, "PlaylistSuggester"), \
                mock.patch.object(gen.planner.generate.warmup, "warmup_code",
                                  side_effect=lambda e: e.dance), \
                mock.patch.object(gen.planner.generate.warmup, "competition_plan",
                                  return_value=["plan"]):
            h._on_warmup_done(entries)
        return h, table

    def test_no_tracks_is_explained_and_nothing_is_loaded(self):
        h, table = self.done([], {})
        table.load_warmup.assert_not_called()
        self.assertIn("No matching tracks", self.box.information.call_args.args[2])
        self.assertEqual(_status(h), "Practice: no matching tracks.")

    def test_a_class_list_loads_with_its_style_and_class(self):
        h, table = self.done([_e("A"), _e("B")], {"mode": "class", "style": "Latin",
                                                  "dance_class": "A", "relax": False})
        args = table.load_warmup.call_args
        self.assertEqual(args.args[2:5], ("Latin", "A", False))
        self.assertEqual(args.kwargs["heat_plan"], [])
        self.assertIn("by timbre", h._show_hints.call_args.args[0][0])
        h._party_list_alone.assert_called_once()
        self.assertIn("2 tracks", _status(h))

    def test_a_competition_training_gets_its_heat_plan(self):
        comp = {"style": "Standard", "dance_class": "B", "dances": ["LW"], "heats": 2,
                "rounds": 2, "final_heats": 1}
        _h, table = self.done([_e("A")], {"mode": "competition", "competition": comp})
        self.assertEqual(table.load_warmup.call_args.kwargs["heat_plan"], ["plan"])
        self.assertEqual(table.load_warmup.call_args.args[2:4], ("Standard", "B"))

    def test_a_party_list_has_no_style_and_swaps_from_the_end(self):
        h, table = self.done([_e("A")], {"mode": "party"})
        self.assertEqual(table.load_warmup.call_args.args[2], "")
        self.assertIn("from the end", h._show_hints.call_args.args[0][0])


class WarmupPanelTest(Case):
    def test_the_panel_takes_the_column_the_playlists_held(self):
        h = _host("_party_list_alone")
        split = h._grid.right_split
        split.sizes.return_value = [100, 50, 30, 20]
        h._grid.warmup_box, h._grid.wish_split = "box", "wish"
        split.indexOf.side_effect = lambda w: {"box": 2, "wish": 1}[w]
        h._party_list_alone()
        split.setSizes.assert_called_once_with([0, 40, 140, 20])
        self.assertEqual(h._deckset.deck_count, 0)
        h._set_wish_state.assert_called_once_with(1)
        h._on_table_focused.assert_called_once_with(h._deckset.warmup_table)

    def test_the_manual_button_mirrors_the_list(self):
        for manual, glyph in ((True, "✋"), (False, "🔒")):
            with self.subTest(manual=manual):
                h = _host("_sync_warmup_manual_btn")
                t = h._deckset.warmup_table
                t._player_list, t._warmup = manual, True
                t._row_meta.song_rows.return_value = [1]
                btn = mock.MagicMock()
                h._sync_warmup_manual_btn(btn)
                btn.setVisible.assert_called_once_with(True)
                btn.setChecked.assert_called_once_with(manual)
                btn.setText.assert_called_once_with(glyph)

    def test_the_toggle_goes_the_other_way_round(self):
        h = _host("_warmup_toggle_manual")
        h._deckset.warmup_table._player_list = True
        h._warmup_toggle_manual("btn")
        h._warmup_to_auto.assert_called_once_with("btn")
        h._deckset.warmup_table._player_list = False
        h._warmup_toggle_manual("btn")
        h._warmup_to_manual.assert_called_once_with("btn")

    def test_going_manual_keeps_what_the_list_was_built_with(self):
        h = _host("_warmup_to_manual")
        t = h._deckset.warmup_table
        t._warmup_style, t._warmup_class, t._warmup_relax, t._heat_plan = "Latin", "A", False, [1]
        h._warmup_to_manual("btn")
        self.assertEqual(t._auto_params, ("Latin", "A", False, [1]))
        t.become_player_list.assert_called_once()
        h._autosave_playlist.assert_called_once()
        self.assertIn("Manual", _status(h))

    def test_going_automatic_restores_those_or_the_plain_defaults(self):
        for params, expected in ((("Std", "B", False, [2]), ("Std", "B", False, [2])),
                                 (None, ("", "S", True, []))):
            with self.subTest(params=params):
                h = _host("_warmup_to_auto")
                t = SimpleNamespace(_player_list=True, _reload_warmup=mock.MagicMock())
                if params:
                    t._auto_params = params
                h._deckset.warmup_table = t
                h._warmup_to_auto("btn")
                self.assertEqual((t._warmup_style, t._warmup_class, t._warmup_relax, t._heat_plan),
                                 expected)
                self.assertFalse(t._player_list)
                t._reload_warmup.assert_called_once_with(rebuild=True)
                self.assertIn("Automatic", _status(h))

    def test_shuffle_and_check_show_only_on_a_party_list_with_titles(self):
        h = _host("_sync_warmup_shuffle_btn")
        t = h._deckset.warmup_table
        t._party_swap.return_value = True
        t._row_meta.song_rows.return_value = [1]
        h._sync_warmup_shuffle_btn()
        h._warmup_shuffle_btn.setVisible.assert_called_with(True)
        t._row_meta.song_rows.return_value = []
        h._sync_warmup_shuffle_btn()
        h._warmup_check_btn.setVisible.assert_called_with(False)

    def test_shuffling_reorders_with_the_last_builds_late_rules(self):
        h = _host("_shuffle_warmup", _warmup_opts={"etds": {"late_ww": False}})
        t = h._deckset.warmup_table
        t._party_swap.return_value = True
        t._row_meta.entries.return_value = [_e("A"), _e("B")]
        t._warmup_label = ""
        with mock.patch.object(gen, "reshuffle_warmup", return_value=["B", "A"]) as shuffle:
            h._shuffle_warmup()
        self.assertEqual((shuffle.call_args.kwargs["late_ww"], shuffle.call_args.kwargs["late_pd"]),
                         (False, True))
        t._reload_warmup.assert_called_once_with(["B", "A"])
        t._notify_changed.assert_called_once()
        self.assertIn("2 tracks", _status(h))

    def test_shuffling_a_list_that_cannot_be_shuffled_does_nothing(self):
        h = _host("_shuffle_warmup")
        t = h._deckset.warmup_table
        t._party_swap.return_value = False
        t._row_meta.entries.return_value = [_e("A")]
        with mock.patch.object(gen, "reshuffle_warmup") as shuffle:
            h._shuffle_warmup()
        shuffle.assert_not_called()


class HintsAndGapsTest(Case):
    def test_hints_show_joined_and_hide_when_empty(self):
        h = _host("_show_hints")
        h._show_hints(["a", "b"])
        h._hints_lbl.setText.assert_called_once_with("a   b")
        h._hints_lbl.setVisible.assert_called_with(True)
        h._show_hints([])
        h._hints_lbl.clear.assert_called_once()
        h._hints_lbl.setVisible.assert_called_with(False)

    def test_a_library_still_loading_opens_no_dialog(self):
        h = _host("_show_library_gaps")
        h._library_still_loading.return_value = True
        with mock.patch.object(gen, "LibraryGapsDialog") as dlg:
            h._show_library_gaps()
        dlg.assert_not_called()

    def test_an_empty_library_asks_to_try_again(self):
        h = _host("_show_library_gaps")
        h._library_still_loading.return_value = False
        h._library.lib.entries = []
        h._show_library_gaps()
        self.assertIn("still loading", self.box.information.call_args.args[2])

    def gaps(self, jump_to, settings_dlg):
        h = _host("_show_library_gaps", _settings_dlg=settings_dlg)
        h._library_still_loading.return_value = False
        h._library.lib.entries = [_e("A")]
        dlg = mock.MagicMock()
        dlg.jump_to = jump_to
        with mock.patch.object(gen, "LibraryGapsDialog", return_value=dlg), \
                mock.patch.object(gen.QTimer, "singleShot",
                                  side_effect=lambda _ms, fn: fn()):
            h._show_library_gaps()
        return h

    def test_closing_the_dialog_without_a_jump_changes_nothing(self):
        h = self.gaps(None, mock.MagicMock())
        h.show_library_filtered.assert_not_called()

    def test_a_jump_closes_settings_and_filters_the_pane(self):
        settings_dlg = mock.MagicMock()
        h = self.gaps(("SA", "S"), settings_dlg)
        settings_dlg.accept.assert_called_once()
        h.show_library_filtered.assert_called_once_with(dance="SA", cls="S", plays="never")

    def test_a_jump_without_an_open_settings_dialog_still_filters(self):
        h = self.gaps(("SA", "S"), None)
        h.show_library_filtered.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
