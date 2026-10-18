#!/usr/bin/env python3
"""A dynamic deck's grid edits: placing drops, growing and shrinking the grid.

Run:  py -m unittest tests.gui.table.test_table_dynamic -v

`DynamicModeMixin` lets a deck build its rounds and heats from what is dropped
on it: a track fills a free slot of its dance, extends a round, spills into the
next one or stacks as a backup under the final. The context menu takes heats,
rounds, dances and backups back out again, and every edit re-renders the grid
through `load()`. These tests drive a real PlaylistTable in dynamic mode; a
confirm dialog answers through a patched `_confirm_delete` or QMessageBox.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_table_dynamic_"))

from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication, QMessageBox

import gui.table.table_dynamic as dyn
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No


def _e(dance, n, folder="music"):
    return MusicEntry(path=Path(rf"C:\{folder}\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class _Ev:
    def __init__(self, source=None, mime=None):
        self._source = source
        self._mime = QMimeData() if mime is None else mime

    def source(self):
        return self._source

    def mimeData(self):
        return self._mime

    def modifiers(self):
        from PySide6.QtCore import Qt
        return Qt.KeyboardModifier.NoModifier


class _Base(unittest.TestCase):

    def table(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        return t

    def deck(self, playlist=None, capacity=(1, 1), backups=None, dances=("LW", "TG")):
        t = self.table()
        if playlist is None:
            playlist = {"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                        "Finale": [[_e("LW", 3), _e("TG", 4)]]}
        rounds = [RoundConfig(name=n, heats=len(h), tier="final") for n, h in playlist.items()]
        t.load(playlist, list(dances), rounds, "S", play_cb=None, suggester=None,
               use_timbre=False, style="Standard", dynamic=True,
               capacity=list(capacity), backups=backups)
        return t

    def patch(self, target, name, **kw):
        patcher = mock.patch.object(target, name, **kw)
        found = patcher.start()
        self.addCleanup(patcher.stop)
        return found

    def toasts(self):
        return self.patch(dyn, "_show_toast")

    def confirm(self, t, answer=True):
        return self.patch(t, "_confirm_delete", return_value=answer)

    @staticmethod
    def row_of(t, title, backup=False):
        return next(r for r, m in enumerate(t._row_meta)
                    if m and m.entry is not None and m.entry.title == title
                    and m.backup == backup)

    @staticmethod
    def titles(t, rname):
        return [[e.title if e else None for e in h] for h in t._playlist[rname]]


class GridBasicsTest(_Base):

    def test_a_dynamic_edit_without_a_playlist_is_a_bug(self):
        t = self.table()
        t._playlist = None
        with self.assertRaises(RuntimeError):
            t._dyn_playlist()

    def test_rows_dragged_from_another_table_are_placeable_and_resolve(self):
        t, src = self.table(), self.deck()
        src._drag_src_rows = [self.row_of(src, "TG 2"), 999, 0]
        ev = _Ev(source=src)
        self.assertTrue(t._can_dynamic_drop(ev))
        self.assertEqual([e.title for e in t._collect_drop_entries(ev)], ["TG 2"])

    def test_a_dropped_playlist_resolves_to_its_tracks(self):
        t = self.table()
        folder = Path(tempfile.mkdtemp(prefix="dp_table_dynamic_"))
        m3u = folder / "list.m3u"
        m3u.write_text("#EXTM3U\n", encoding="utf-8")
        mime = QMimeData()
        from PySide6.QtCore import QUrl
        mime.setUrls([QUrl.fromLocalFile(str(m3u))])
        self.patch(t, "_m3u_track_paths", return_value=[folder / "a.mp3"])
        resolve = self.patch(t, "_entries_for_paths", return_value=[_e("LW", 1), None])
        self.assertEqual([e.title for e in t._collect_drop_entries(_Ev(mime=mime))], ["LW 1"])
        resolve.assert_called_once_with([folder / "a.mp3"])

    def test_an_empty_deck_enters_dynamic_with_the_field_pattern(self):
        t = self.table()
        t._dynamic_backups = None
        t._capacity_provider = lambda: [3, 1]
        changed = []
        t.dynamicChanged.connect(changed.append)
        t._enter_dynamic_from_drop()
        self.assertEqual((t._dynamic, t._dynamic_capacity, t._dynamic_backups),
                         (True, [3, 1], {}))
        self.assertEqual(changed, [t])

    def test_the_field_pattern_falls_back_to_6_3_2_1(self):
        t = self.table()
        t._capacity_provider = None
        self.assertEqual(t._field_capacity(), [6, 3, 2, 1])
        t._capacity_provider = lambda: []
        self.assertEqual(t._field_capacity(), [6, 3, 2, 1])
        t._capacity_provider = mock.Mock(side_effect=ValueError("bad field"))
        self.assertEqual(t._field_capacity(), [6, 3, 2, 1])

    def test_a_new_dance_column_carries_the_backups_along(self):
        t = self.deck(playlist={"Finale": [[_e("TG", 1)]]}, capacity=(1,), dances=("TG",),
                      backups={("Finale", 0, 0): [_e("TG", 9)], ("Finale", 0, 5): []})
        t._ensure_dynamic_dance("LW")
        self.assertEqual(t._dynamic_dances, ["LW", "TG"])
        self.assertEqual(self.titles(t, "Finale"), [[None, "TG 1"]])
        self.assertIn(("Finale", 0, 1), t._dynamic_backups)
        self.assertEqual(t._new_heat(), [None, None])

    def test_rounds_not_created_yet_borrow_the_standard_names(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]]}, capacity=(2, 1))
        self.assertEqual(t._dynamic_specs(), [("Vorrunde", 2), ("Finale", 1)])
        self.assertEqual([c.name for c in t._dynamic_round_configs()], ["Vorrunde"])


class IdentityTest(_Base):

    def test_planned_entries_include_the_backups(self):
        t = self.deck(backups={("Finale", 0, 0): [_e("LW", 9)]})
        self.assertIn("LW 9", [e.title for e in t._iter_planned_entries()])

    def test_a_fingerprint_lookup_that_fails_is_unknown(self):
        t = self.table()
        t._cache = mock.Mock()
        t._cache.known_fingerprint.side_effect = OSError("locked")
        self.assertIsNone(t._entry_fingerprint(_e("LW", 1)))
        t._cache.fingerprint.side_effect = OSError("locked")
        self.assertEqual(t._audio_keys(_e("LW", 1)), {("p", r"c:\music\lw1.mp3")})

    def test_entries_without_a_path_have_no_identity(self):
        t = self.table()
        nameless = SimpleNamespace(path=None, title="x", dance="LW")
        self.assertFalse(t._same_path("", "C:/a.mp3"))
        self.assertEqual(t._dup_keys(nameless), (None, None))
        self.assertEqual(t._audio_keys(nameless), set())
        self.assertIsNone(t._title_key(nameless))
        self.assertIsNone(t._title_key(SimpleNamespace(path="C:/x/__.mp3", dance="LW")))
        self.assertIsNone(t._holds_same_audio(nameless, [_e("LW", 1)]))
        self.assertIsNone(t._find_duplicate(nameless))
        self.assertIsNone(t._find_duplicate(_e("PD", 1)))

    def test_the_reroll_exclusion_adds_library_copies_of_the_same_song(self):
        t = self.table()
        self.assertEqual(t._exclude_with_dupes([_e("LW", 1)]), {r"C:\music\LW1.mp3"})
        t._suggester = SimpleNamespace(lib=SimpleNamespace(entries=[
            SimpleNamespace(path=None), _e("LW", 1, folder="copy"), _e("TG", 5)]))
        self.assertEqual(t._exclude_with_dupes([_e("LW", 1)]),
                         {r"C:\music\LW1.mp3", r"C:\copy\LW1.mp3"})

    def test_a_planned_entry_is_replaced_in_a_heat_or_a_backup(self):
        backup = _e("LW", 9)
        t = self.deck(backups={("Finale", 0, 0): [backup]})
        old = t._playlist["Finale"][0][1]
        self.assertTrue(t._replace_planned_entry(old, _e("TG", 7)))
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", "TG 7"]])
        self.assertTrue(t._replace_planned_entry(backup, _e("LW", 8)))
        self.assertEqual(t._dynamic_backups[("Finale", 0, 0)][0].title, "LW 8")
        self.assertFalse(t._replace_planned_entry(_e("SF", 1), _e("SF", 2)))

    def test_a_list_without_a_grid_answers_from_its_rows(self):
        t = self.table()
        t.load_wishlist([_e("LW", 1)], play_cb=None, suggester=None)
        self.assertTrue(t._contains_path_or_fp(_e("LW", 1)))


class SoftDuplicateTest(_Base):

    def answer(self, label):
        class Box(QMessageBox):
            texts = []

            def exec(self):
                Box.texts.append(self.text())
                return 0

            def clickedButton(self):
                return next(b for b in self.buttons() if b.text() == label)

        self.patch(dyn, "QMessageBox", new=Box)
        return Box.texts

    def test_replace_or_keep(self):
        t = self.table()
        texts = self.answer("Replace")
        self.assertEqual(t._ask_soft_duplicate(_e("LW", 1, "a"), _e("LW", 1, "b")), "replace")
        self.assertIn("A track named", texts[0])
        texts = self.answer("Keep existing")
        cut = MusicEntry(path=Path(r"C:\a\LW1_cut.mp3"), title="LW 1", dance="LW", bpm=None)
        self.assertEqual(t._ask_soft_duplicate(cut, _e("LW", 1, "b")), "skip")
        self.assertIn("looks like the same title", texts[0])


class MoveFromSourceTest(_Base):

    def setUp(self):
        self.question = self.patch(QMessageBox, "question", return_value=_YES)

    def test_tracks_already_planned_are_only_taken_on_a_yes(self):
        t = self.deck()
        wish = self.table()
        wish.load_wishlist([_e("LW", 1), _e("SF", 5)], play_cb=None, suggester=None)
        wish._drag_src_rows = [0, 1, 99]
        remove = self.patch(wish, "_remove_rows", return_value=True)
        pre = t._planned_keys()
        self.assertEqual(t._move_from_drag_source(_Ev(source=wish), pre_planned=pre), 1)
        remove.assert_called_once_with([0], select_after=True)
        self.assertIn("from the wishlist", self.question.call_args.args[2])
        self.question.return_value = _NO
        self.assertEqual(t._move_from_drag_source(_Ev(source=wish), pre_planned=pre), 0)

    def test_several_from_a_deck_are_counted(self):
        t, src = self.deck(), self.deck()
        src._drag_src_rows = [self.row_of(src, "LW 1"), self.row_of(src, "TG 2")]
        clear = self.patch(src, "_clear_slots_at", return_value=True)
        self.assertEqual(t._move_from_drag_source(_Ev(source=src),
                                                  pre_planned=t._planned_keys()), 2)
        self.assertIn("2 dragged track(s)", self.question.call_args.args[2])
        self.assertIn("from the playlist", self.question.call_args.args[2])
        clear.assert_called_once()


class PlaceOneTest(_Base):

    def setUp(self):
        self.toast = self.toasts()

    def test_a_soft_duplicate_replaced_takes_its_place(self):
        t = self.deck()
        self.patch(t, "_ask_soft_duplicate", return_value="replace")
        self.assertEqual(t._dynamic_place_one(_e("LW", 1, "copy2"), -1), "")
        self.assertIn("Replaced", self.toast.call_args.args[1])

    def test_a_soft_duplicate_not_found_is_added_and_one_kept_is_a_dup(self):
        t = self.deck()
        ask = self.patch(t, "_ask_soft_duplicate", return_value="replace")
        self.patch(t, "_replace_planned_entry", return_value=False)
        self.assertEqual(t._dynamic_place_one(_e("LW", 1, "copy2"), -1), "")
        ask.return_value = "skip"
        self.assertEqual(t._dynamic_place_one(_e("LW", 1, "copy3"), -1), "dup")

    def test_an_extra_track_tops_up_a_free_slot_first(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), None]],
                                "Finale": [[_e("LW", 3), _e("TG", 4)]]})
        self.assertEqual(t._dynamic_place_one(_e("TG", 8), -1, prefer_existing=True), "")
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 8"]])

    def test_an_empty_slot_under_the_cursor_takes_the_track(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                                "Finale": [[None, _e("TG", 4)]]})
        empty = next(r for r, m in enumerate(t._row_meta)
                     if m and m.entry is None and m.dance == "LW")
        self.assertEqual(t._dynamic_place_one(_e("LW", 8), empty), "")
        self.assertEqual(self.titles(t, "Finale"), [["LW 8", "TG 4"]])

    def test_outside_any_round_the_track_autofills(self):
        t = self.deck()
        autofill = self.patch(t, "_dynamic_autofill")
        t._dynamic_place_one(_e("LW", 8), 999)
        autofill.assert_called_once()


class ReplaceSlotTest(_Base):

    def setUp(self):
        self.toast = self.toasts()
        self.question = self.patch(QMessageBox, "question", return_value=_NO)

    def test_rows_that_are_not_filled_main_slots(self):
        t = self.deck(backups={("Finale", 0, 0): [_e("LW", 9)]})
        self.assertFalse(t._dynamic_replace_slot(-1, _e("LW", 8)))
        self.assertFalse(t._dynamic_replace_slot(0, _e("LW", 8)))
        self.assertFalse(t._dynamic_replace_slot(self.row_of(t, "LW 9", backup=True),
                                                 _e("LW", 8)))
        row = self.row_of(t, "LW 1")
        self.assertFalse(t._dynamic_replace_slot(row, _e("LW", 1)))   # the same track
        t._dynamic_dances = ["TG"]
        self.assertFalse(t._dynamic_replace_slot(row, _e("LW", 8)))

    def test_another_dance_is_asked_about(self):
        t = self.deck()
        row = self.row_of(t, "LW 1")
        self.assertFalse(t._dynamic_replace_slot(row, _e("TG", 8)))
        self.question.return_value = _YES
        self.assertTrue(t._dynamic_replace_slot(row, _e("TG", 8)))
        self.assertEqual(self.titles(t, "Vorrunde"), [["TG 8", "TG 2"]])

    def test_a_track_planned_elsewhere_is_not_replaced(self):
        t = self.deck()
        self.assertFalse(t._dynamic_replace_slot(self.row_of(t, "LW 1"), _e("LW", 3)))
        self.assertIn("not replaced", self.toast.call_args.args[1])

    def test_a_stale_slot_index_is_refused(self):
        t = self.deck()
        row = self.row_of(t, "LW 1")
        t._row_meta[row].h_idx = 5
        self.assertFalse(t._dynamic_replace_slot(row, _e("LW", 8)))
        t._row_meta[row].h_idx = 0
        t._playlist["Vorrunde"][0] = []
        self.assertFalse(t._dynamic_replace_slot(row, _e("LW", 8)))


class FillAndGrowTest(_Base):

    def test_the_first_free_slot_of_a_dance_deck_wide(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                                "Finale": [[_e("LW", 3), None]]}, capacity=(1, 1, 1))
        self.assertFalse(t._fill_existing_empty_slot("SF", _e("SF", 1)))
        self.assertFalse(t._fill_existing_empty_slot("LW", _e("LW", 8)))
        t._round_skip_dances = {"Finale": {"TG"}}
        self.assertFalse(t._fill_existing_empty_slot("TG", _e("TG", 8)))
        t._round_skip_dances = {}
        self.assertTrue(t._fill_existing_empty_slot("TG", _e("TG", 8)))
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", "TG 8"]])
        t._playlist = {}
        self.assertFalse(t._fill_existing_empty_slot("TG", _e("TG", 8)))

    def test_a_round_not_created_yet_has_no_free_slot(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]]}, capacity=(1, 1))
        self.assertFalse(t._fill_existing_empty_slot("LW", _e("LW", 8)))

    def test_extending_a_round_unhides_the_dance_and_adds_heats(self):
        t = self.deck(capacity=(2, 1))
        t._round_skip_dances = {"Vorrunde": {"LW"}}
        t._dynamic_extend_round("Vorrunde", "LW", _e("LW", 8))
        self.assertEqual(t._round_skip_dances, {"Vorrunde": set()})
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 2"], ["LW 8", None]])
        t._dynamic_extend_round("Semifinale", "TG", _e("TG", 8))
        self.assertEqual(self.titles(t, "Semifinale"), [[None, "TG 8"]])

    def test_autofill_spills_over_full_rounds_into_the_final_backups(self):
        t = self.deck(capacity=(1, 1))
        t._dynamic_autofill("LW", _e("LW", 8))
        self.assertEqual(t._dynamic_backups[("Finale", 0, 0)][0].title, "LW 8")

    def test_autofill_adds_a_heat_where_capacity_is_left(self):
        t = self.deck(capacity=(2, 1))
        t._dynamic_autofill("LW", _e("LW", 8))
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 2"], ["LW 8", None]])

    def test_autofill_fills_a_free_slot_or_opens_a_missing_round(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), None]]}, capacity=(2, 1))
        t._dynamic_autofill("TG", _e("TG", 8))
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 8"]])
        t._dynamic_capacity = [1, 1]
        t._dynamic_autofill("LW", _e("LW", 9))
        self.assertEqual(self.titles(t, "Finale"), [["LW 9", None]])


class RemoveTest(_Base):

    def test_a_heat_removal_that_cannot_or_may_not_happen(self):
        t = self.deck(backups={("Finale", 0, 0): [_e("LW", 9)]})
        rebuild = self.patch(t, "_rebuild_dynamic")
        confirm = self.confirm(t, answer=False)
        t._remove_dynamic_heat(self.row_of(t, "LW 9", backup=True))
        row = self.row_of(t, "LW 1")
        t._row_meta[row].h_idx = 4
        t._remove_dynamic_heat(row)
        t._row_meta[row].h_idx = 0
        t._remove_dynamic_heat(row)
        confirm.assert_called_once()
        t._dynamic = False
        t._remove_dynamic_heat(row)
        rebuild.assert_not_called()

    def test_adding_a_heat_to_the_round_of_a_row(self):
        t = self.deck()
        t._add_dynamic_heat(self.row_of(t, "TG 4"))
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", "TG 4"], [None, None]])
        t._add_dynamic_heat(999)
        t._dynamic = False
        t._add_dynamic_heat(self.row_of(t, "TG 4"))
        self.assertEqual(len(t._playlist["Finale"]), 2)

    def test_removing_a_round_stops_its_playing_title(self):
        t = self.deck(capacity=(1, 1, 1),
                      playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                                "Zwischenrunde": [[_e("LW", 5), _e("TG", 6)]],
                                "Finale": [[_e("LW", 3), _e("TG", 4)]]},
                      backups={("Finale", 0, 0): [_e("LW", 9)]})
        played = []
        t._play_cb = played.append
        row = self.row_of(t, "LW 1")
        t._current_play_row = row
        self.confirm(t)
        t._remove_dynamic_round(row)
        self.assertEqual(played, [None])
        self.assertEqual(list(t._playlist), ["Vorrunde", "Finale"])
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 5", "TG 6"]])
        self.assertIn(("Finale", 0, 0), t._dynamic_backups)

    def test_a_round_removal_that_cannot_or_may_not_happen(self):
        t = self.deck()
        confirm = self.confirm(t, answer=False)
        t._remove_dynamic_round(self.row_of(t, "LW 1"))
        t._remove_dynamic_round(999)
        t._dynamic = False
        t._remove_dynamic_round(self.row_of(t, "LW 1"))
        confirm.assert_called_once()
        self.assertEqual(list(t._playlist), ["Vorrunde", "Finale"])

    def test_a_dance_leaves_one_round_and_hides_there(self):
        t = self.deck(backups={("Finale", 0, 0): [_e("LW", 9)]})
        played = []
        t._play_cb = played.append
        t._current_play_row = self.row_of(t, "LW 3")
        confirm = self.confirm(t)
        t._remove_dance_from_round("Finale", "LW")
        self.assertIn("1 song(s)", confirm.call_args.args[1])
        self.assertEqual(played, [None])
        self.assertEqual(self.titles(t, "Finale"), [[None, "TG 4"]])
        self.assertEqual(t._dynamic_backups, {})
        self.assertEqual(t._round_skip_dances["Finale"], {"LW"})
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 2"]])
        t._remove_dance_from_round("Finale", "LW")
        self.assertIn("Hide the empty", confirm.call_args.args[1])

    def test_a_dance_removal_from_a_round_that_cannot_or_may_not_happen(self):
        t = self.deck()
        confirm = self.confirm(t, answer=False)
        t._remove_dance_from_round("Finale", "SF")
        t._remove_dance_from_round("Nowhere", "LW")
        t._remove_dance_from_round("Finale", "LW")
        t._dynamic = False
        t._remove_dance_from_round("Finale", "LW")
        confirm.assert_called_once()
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", "TG 4"]])

    def test_a_dance_leaves_every_round(self):
        t = self.deck(backups={("Finale", 0, 1): [_e("TG", 9)]})
        played = []
        t._play_cb = played.append
        t._current_play_row = self.row_of(t, "TG 2")
        confirm = self.confirm(t)
        t._remove_dance_everywhere("TG")
        self.assertIn("2 song(s)", confirm.call_args.args[1])
        self.assertEqual(played, [None])
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", None]])
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", None]])
        self.assertEqual(t._dynamic_backups, {})
        t._remove_dance_everywhere("TG")
        self.assertIn("Hide the empty", confirm.call_args.args[1])

    def test_a_dance_removal_everywhere_that_cannot_or_may_not_happen(self):
        t = self.deck()
        confirm = self.confirm(t, answer=False)
        t._remove_dance_everywhere("SF")
        t._remove_dance_everywhere("LW")
        t._dynamic = False
        t._remove_dance_everywhere("LW")
        confirm.assert_called_once()
        self.assertEqual(self.titles(t, "Vorrunde"), [["LW 1", "TG 2"]])


class BackupTest(_Base):

    def test_backups_rekey_around_a_removed_heat(self):
        t = self.table()
        t._dynamic_backups = {("F", 0, 0): ["a"], ("F", 1, 0): ["b"], ("F", 2, 1): ["c"],
                              ("V", 1, 0): ["d"]}
        t._reindex_backups_for_heat("F", 1)
        self.assertEqual(t._dynamic_backups,
                         {("F", 0, 0): ["a"], ("F", 1, 1): ["c"], ("V", 1, 0): ["d"]})

    def test_an_emptied_final_is_rebuilt_from_its_backups(self):
        t = self.deck()
        t._dynamic_backups = {("Finale", 0, 0): [_e("LW", 8), _e("LW", 9)],
                              ("Finale", 0, 1): [_e("TG", 8)]}
        self.assertTrue(t._promote_backups_to_heats("Finale"))
        self.assertEqual(self.titles(t, "Finale"), [["LW 8", "TG 8"], ["LW 9", None]])
        self.assertEqual(t._dynamic_backups, {})
        self.assertFalse(t._promote_backups_to_heats("Finale"))

    def test_one_backup_is_removed_by_identity_or_path(self):
        t = self.deck()
        keep, gone = _e("LW", 8), _e("LW", 9)
        t._dynamic_backups = {("Finale", 0, 0): [keep, gone]}
        meta = SimpleNamespace(round_name="Finale", h_idx=0, d_idx=0, entry=_e("LW", 9))
        self.assertTrue(t._discard_backup_entry(meta))
        self.assertEqual(t._dynamic_backups, {("Finale", 0, 0): [keep]})
        self.assertFalse(t._discard_backup_entry(meta))
        meta.entry = keep
        self.assertTrue(t._discard_backup_entry(meta))
        self.assertEqual(t._dynamic_backups, {})
        self.assertFalse(t._discard_backup_entry(meta))

    def test_removing_a_backup_row(self):
        t = self.deck(backups={("Finale", 0, 0): [_e("LW", 9)]})
        played = []
        t._play_cb = played.append
        row = self.row_of(t, "LW 9", backup=True)
        t._current_play_row = row
        confirm = self.confirm(t, answer=False)
        t._remove_dynamic_backup(row)
        self.assertEqual(played, [])
        confirm.return_value = True
        t._remove_dynamic_backup(self.row_of(t, "LW 1"))     # not a backup row
        t._remove_dynamic_backup(999)
        t._remove_dynamic_backup(row)
        self.assertEqual(played, [None])
        self.assertEqual(t._dynamic_backups, {})
        self.assertFalse(any(m and m.backup for m in t._row_meta))

    def test_an_empty_slot_takes_its_backup_or_drops_its_dance(self):
        t = self.deck(playlist={"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                                "Finale": [[None, _e("TG", 4)]]},
                      backups={("Finale", 0, 0): [_e("LW", 9)]})
        toast = self.toasts()
        empty = next(r for r, m in enumerate(t._row_meta) if m and m.entry is None)
        t._remove_empty_dynamic_slot(self.row_of(t, "LW 1"))   # holds a song
        t._remove_empty_dynamic_slot(999)
        t._remove_empty_dynamic_slot(empty)
        self.assertEqual(self.titles(t, "Finale"), [["LW 9", "TG 4"]])
        self.assertEqual(t._dynamic_backups, {})
        toast.assert_called_once()
        t._playlist["Finale"][0][0] = None
        t._rebuild_dynamic()
        drop = self.patch(t, "_remove_dance_from_round")
        empty = next(r for r, m in enumerate(t._row_meta) if m and m.entry is None)
        t._remove_empty_dynamic_slot(empty)
        drop.assert_called_once_with("Finale", "LW")

    def test_an_empty_slot_outside_a_dynamic_grid_is_left(self):
        t = self.deck(playlist={"Vorrunde": [[None, _e("TG", 2)]]}, capacity=(1,))
        empty = next(r for r, m in enumerate(t._row_meta) if m and m.entry is None)
        drop = self.patch(t, "_remove_dance_from_round")
        t._row_meta[empty].round_name = None
        t._remove_empty_dynamic_slot(empty)
        t._dynamic = False
        t._remove_empty_dynamic_slot(empty)
        drop.assert_not_called()


class RoundStructureTest(_Base):

    def test_a_round_appended_becomes_the_final(self):
        t = self.deck()
        self.assertEqual(t._append_dynamic_round(), "Finale")
        self.assertEqual(list(t._playlist), ["Vorrunde", "Zwischenrunde", "Finale"])
        self.assertEqual(self.titles(t, "Zwischenrunde"), [["LW 3", "TG 4"]])
        self.assertEqual(self.titles(t, "Finale"), [[None, None]])
        self.assertEqual(t._dynamic_capacity, [1, 1, 1])
        self.assertEqual(t._row_round_name.get(t.currentRow()), "Finale")

    def test_a_round_inserted_after_the_first(self):
        t = self.deck()
        self.assertEqual(t._insert_dynamic_round(self.row_of(t, "LW 1")), "Zwischenrunde")
        self.assertEqual(self.titles(t, "Zwischenrunde"), [[None, None]])
        self.assertEqual(self.titles(t, "Finale"), [["LW 3", "TG 4"]])

    def test_no_round_is_added_to_a_static_deck_and_an_empty_one_starts(self):
        t = self.deck()
        t._dynamic = False
        self.assertEqual(t._insert_dynamic_round(None), "")
        empty = self.table()
        empty._enter_dynamic([1])
        empty._playlist = None
        self.assertEqual(empty._insert_dynamic_round(None), "Finale")

    def test_focus_without_headers_lands_on_the_first_song(self):
        t = self.deck()
        t._round_hdr_rows = []
        t._focus_round("Finale")
        self.assertEqual(t.currentRow(), self.row_of(t, "LW 3"))
        t._focus_round("Nowhere")
        self.assertEqual(t.currentRow(), self.row_of(t, "LW 3"))

    def test_a_resync_pads_the_pattern_and_renames_backups_and_hidden_dances(self):
        t = self.table()
        t._playlist = {"A": [[None]], "B": [[None]], "C": [[None]]}
        t._dynamic_capacity = [2]
        t._dynamic_backups = {("C", 0, 0): ["x"]}
        t._round_skip_dances = {"A": {"LW"}}
        t._resync_dynamic_rounds()
        self.assertEqual(t._dynamic_capacity, [2, 2, 2])
        self.assertEqual(list(t._playlist), ["Vorrunde", "Zwischenrunde", "Finale"])
        self.assertEqual(t._dynamic_backups, {("Finale", 0, 0): ["x"]})
        self.assertEqual(t._round_skip_dances, {"Vorrunde": {"LW"}})
        t._playlist = {}
        t._resync_dynamic_rounds()
        self.assertEqual(t._dynamic_capacity, [])


class CrossStyleTest(_Base):

    def setUp(self):
        self.question = self.patch(QMessageBox, "question", return_value=_NO)

    def test_the_style_of_a_dance(self):
        t = self.table()
        self.assertEqual(t._dance_style("SA"), "Latin")
        self.assertIsNone(t._dance_style(""))
        self.assertIsNone(t._dance_style("XX"))

    def test_foreign_dances_on_a_standard_deck_are_asked_about(self):
        t = self.deck()
        self.assertTrue(t._confirm_cross_style([_e("LW", 8)]))
        self.assertFalse(t._confirm_cross_style([_e("SA", 1), _e("CC", 2), _e("LW", 8)]))
        self.assertIn("2 dropped track(s) look like Latin", self.question.call_args.args[2])
        self.question.return_value = _YES
        self.assertTrue(t._confirm_cross_style([_e("SA", 1)]))
        t._style = "Others"
        self.assertTrue(t._confirm_cross_style([_e("SA", 1)]))


class DynamicDropTest(_Base):

    def setUp(self):
        self.toast = self.toasts()

    def test_nothing_readable_says_so(self):
        t = self.deck()
        t._suggester = mock.Mock(**{"similarity.return_value": None})
        self.patch(t, "_collect_drop_entries", return_value=[])
        t._dynamic_drop(_Ev(), -1)
        self.assertEqual(self.toast.call_args.args[1], "Couldn't read the dropped track(s).")

    def test_a_cancelled_style_question_drops_nothing(self):
        t = self.deck()
        t._suggester = mock.Mock(**{"similarity.return_value": None})
        self.patch(t, "_collect_drop_entries", return_value=[_e("SA", 1)])
        self.patch(QMessageBox, "question", return_value=_NO)
        rebuild = self.patch(t, "_rebuild_dynamic")
        t._dynamic_drop(_Ev(), -1)
        rebuild.assert_not_called()

    def test_an_empty_deck_goes_dynamic_and_takes_the_style_of_its_drop(self):
        t = self.table()
        t._suggester = mock.Mock(**{"similarity.return_value": None})
        t._style = None
        t._capacity_provider = lambda: [1]
        self.patch(t, "_collect_drop_entries",
                   return_value=[_e("SA", 1), _e("CC", 2), _e("LW", 3)])
        t._dynamic_drop(_Ev(), -1)
        self.assertTrue(t._dynamic)
        self.assertEqual(t._style, "Latin")
        self.assertIn("Added 3 track(s)", self.toast.call_args.args[1])

    def test_a_dynamic_deck_without_a_playlist_starts_one(self):
        t = self.deck()
        t._suggester = mock.Mock(**{"similarity.return_value": None})
        t._playlist = None
        self.patch(t, "_collect_drop_entries", return_value=[_e("LW", 8)])
        t._dynamic_drop(_Ev(), -1)
        self.assertIn("LW 8", [e.title for e in t._iter_planned_entries()])

    def test_ctrl_replaces_the_first_and_adds_the_rest(self):
        t = self.deck(capacity=(2, 1))
        t._suggester = mock.Mock(**{"similarity.return_value": None})
        self.patch(t, "_collect_drop_entries", return_value=[_e("LW", 8), _e("TG", 9)])
        t._dynamic_drop(_Ev(), self.row_of(t, "LW 1"), replace=True)
        self.assertIn("Replaced 1, ", self.toast.call_args.args[1])
        self.assertIn("added 1 track(s)", self.toast.call_args.args[1])

    def test_a_warmup_regrouped_keeps_the_selected_song(self):
        t = self.table()
        t.load_warmup([_e("LW", 1), _e("TG", 2)], "Eintanzen", style="", dance_class="S",
                      relax=True, play_cb=lambda *a: None, suggester=None)
        t.setCurrentCell(self.row_of(t, "TG 2"), 0)
        t.set_grouping(2)
        self.assertEqual(t._row_meta.at(t.currentRow()).entry.title, "TG 2")

    def test_a_song_no_longer_listed_is_not_reselected(self):
        t = self.deck()
        self.assertFalse(t._reselect_song(r"C:\music\gone.mp3"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
