"""A title dropped on a list that already holds it: the list asks.

Run:  py -m unittest tests.gui.table.test_held_drop -v

Marcel's list, 6.1: "When dragging a title that already exists in the target
list, ask what to do: replace it, swap positions of both titles, or do nothing.
Example: ExportParty starts with "Used to Love", Party starts with "Stuck on
You". The user wants ExportParty to start with "Stuck on You", but that title is
at another position in ExportParty, so the user gets asked."

It used to be a toast or a box saying no, which left the title where it was.
"""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_held_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])
_DIR = Path(tempfile.mkdtemp(prefix="dp_held_m_"))


def _e(title, dance="LW"):
    path = _DIR / f"{title}.mp3"
    path.write_bytes(title.encode())
    return MusicEntry(path=path, title=title, dance=dance, duration=150)


class _Lib:
    """Knows nothing, so a dropped file comes back as a new object each time."""

    entries = ()

    def __init__(self):
        self.known = {}

    def entry_for(self, path, *_a, **_kw):
        return copy.copy(self.known.get(str(path)))


class _Suggester:

    def __init__(self):
        self.lib = _Lib()

    def similarity(self, *_a):
        return None

    def anchor_similarity(self, *_a, **_kw):
        return None

    def set_similarity(self, *_a):
        pass


class _Ev:

    def __init__(self, mods=Qt.KeyboardModifier.NoModifier, source=None):
        self.mods = mods
        self.src = source

    def modifiers(self):
        return self.mods

    def source(self):
        return self.src

    def setDropAction(self, *_a):
        pass

    def accept(self):
        pass

    def ignore(self):
        pass


class _Base(unittest.TestCase):

    def setUp(self):
        for name in ("information", "warning", "critical", "question"):
            p = mock.patch.object(QMessageBox, name)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def party(self, *titles, running_order=False):
        t = self.table()
        entries = [_e(x) for x in titles]
        suggester = _Suggester()
        t.load_warmup(entries, "Party", style="Standard", dance_class="S",
                      relax=True, play_cb=None, suggester=suggester,
                      running_order=running_order)
        suggester.lib.known = {str(e.path): e for e in entries}
        return t

    def deck(self, dynamic=False):
        t = self.table()
        playlist = {"Vorrunde": [[_e("LW 1"), _e("TG 1", "TG")]],
                    "Finale": [[_e("LW 2"), _e("TG 2", "TG")]]}
        rounds = [RoundConfig(name=n, heats=1, tier="final") for n in playlist]
        suggester = _Suggester()
        kw = {"dynamic": True, "capacity": [1, 1]} if dynamic else {}
        t.load(playlist, ["LW", "TG"], rounds, "S", style="Standard", play_cb=None,
               suggester=suggester, use_timbre=False, **kw)
        suggester.lib.known = {str(e.path): e for h in playlist.values()
                               for e in h[0]}
        return t

    @staticmethod
    def titles(t):
        return [e.title for e in t._row_meta.entries()]

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in t._row_meta.numbered() if m.entry.title == title)

    def answer(self, t, choice):
        """What the dialog will say, and a record of what it was offered."""
        t._ask_held_drop = mock.Mock(
            side_effect=lambda _title, _lines, _choices, done: done(choice))
        return t._ask_held_drop

    def drop(self, t, title, row=-1, gap=0, mods=Qt.KeyboardModifier.NoModifier,
             source=None):
        path = _DIR / f"{title}.mp3"
        t._wishlist_droppables = lambda _e: [path]
        t._drop_index = lambda _e: gap
        t._drop_static(_Ev(mods, source), row)
        _app.processEvents()

    def choices(self, ask):
        return ask.call_args.args[2]


class PartyDropTest(_Base):

    def first_gap(self, t):
        return t._row_meta.song_rows()[0]

    def test_marcels_example_swaps_the_two_titles(self):
        t = self.party("Used to Love", "Other", "Stuck on You")
        ask = self.answer(t, "swap")
        self.drop(t, "Stuck on You", gap=self.first_gap(t))
        ask.assert_called_once()
        self.assertEqual(self.titles(t), ["Stuck on You", "Other", "Used to Love"])

    def test_replace_moves_it_to_the_drop_and_keeps_the_rest(self):
        """A plain drop on a party list inserts, nothing is overwritten by it,
        so the answer takes only the old copy out."""
        t = self.party("Used to Love", "Other", "Stuck on You")
        self.answer(t, "replace")
        self.drop(t, "Stuck on You", gap=self.first_gap(t))
        self.assertEqual(self.titles(t), ["Stuck on You", "Used to Love", "Other"])

    def test_replace_moves_down_as_well(self):
        t = self.party("Stuck on You", "Other", "Used to Love")
        self.answer(t, "replace")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertEqual(self.titles(t), ["Other", "Stuck on You", "Used to Love"])

    def test_do_nothing_does_nothing(self):
        t = self.party("Used to Love", "Other", "Stuck on You")
        self.answer(t, "")
        self.drop(t, "Stuck on You", gap=self.first_gap(t))
        self.assertEqual(self.titles(t), ["Used to Love", "Other", "Stuck on You"])

    def test_a_title_dropped_on_itself_is_not_worth_a_question(self):
        t = self.party("Stuck on You", "Other")
        ask = self.answer(t, "swap")
        self.drop(t, "Stuck on You", gap=self.first_gap(t))
        ask.assert_not_called()

    def test_below_the_last_row_there_is_nothing_to_swap_with(self):
        t = self.party("Stuck on You", "Other")
        ask = self.answer(t, "replace")
        self.drop(t, "Stuck on You", gap=t.rowCount())
        self.assertEqual(self.choices(ask), ["replace"])
        self.assertEqual(self.titles(t), ["Other", "Stuck on You"])

    def test_a_title_the_list_does_not_hold_is_still_just_added(self):
        t = self.party("Used to Love")
        new = _e("New")
        t._suggester.lib.known[str(new.path)] = new
        ask = self.answer(t, "swap")
        self.drop(t, "New", gap=self.first_gap(t))
        ask.assert_not_called()
        self.assertEqual(self.titles(t), ["New", "Used to Love"])

    def test_the_marker_follows_a_running_title_and_the_music_goes_on(self):
        t = self.party("Used to Love", "Other", "Stuck on You")
        t._play_cb = mock.Mock()
        t._current_play_row = self.row_of(t, "Stuck on You")
        self.answer(t, "swap")
        self.drop(t, "Stuck on You", gap=self.first_gap(t))
        t._play_cb.assert_not_called()
        self.assertEqual(t._current_play_row, self.row_of(t, "Stuck on You"))

    def test_the_source_list_keeps_the_title_and_asks_nothing_more(self):
        """The list that was dragged from took no part in this: the title only
        changed place in the list it was dropped on."""
        src = self.party("Stuck on You", running_order=True)
        src._drag_src_rows = [self.row_of(src, "Stuck on You")]
        t = self.party("Used to Love", "Other", "Stuck on You")
        t._confirm_remove_already_planned = mock.Mock(return_value=True)
        self.answer(t, "swap")
        self.drop(t, "Stuck on You", gap=self.first_gap(t), source=src)
        t._confirm_remove_already_planned.assert_not_called()
        self.assertEqual(self.titles(src), ["Stuck on You"])


class ShiftDropTest(_Base):
    """Shift+drop on a party list overwrites the title under the cursor."""

    SHIFT = Qt.KeyboardModifier.ShiftModifier

    def test_replace_overwrites_it_and_the_old_copy_goes(self):
        t = self.party("Used to Love", "Other", "Stuck on You", running_order=True)
        self.answer(t, "replace")
        self.drop(t, "Stuck on You", row=self.row_of(t, "Used to Love"),
                  mods=self.SHIFT)
        self.assertEqual(self.titles(t), ["Stuck on You", "Other"])

    def test_swap(self):
        t = self.party("Used to Love", "Other", "Stuck on You")
        self.answer(t, "swap")
        self.drop(t, "Stuck on You", row=self.row_of(t, "Used to Love"),
                  mods=self.SHIFT)
        self.assertEqual(self.titles(t), ["Stuck on You", "Other", "Used to Love"])

    def test_the_running_title_is_not_offered_for_overwriting(self):
        """Taking it out would stop the music, and a replace never cuts the
        floor (see test_playing_replace)."""
        t = self.party("Used to Love", "Stuck on You")
        t._current_play_row = self.row_of(t, "Used to Love")
        ask = self.answer(t, "")
        self.drop(t, "Stuck on You", row=t._current_play_row, mods=self.SHIFT)
        self.assertEqual(self.choices(ask), ["swap"])


class SlotDropTest(_Base):

    def test_swap_exchanges_the_two_slots(self):
        t = self.deck()
        self.answer(t, "swap")
        self.drop(t, "LW 1", row=self.row_of(t, "LW 2"))
        self.assertEqual(self.titles(t), ["LW 2", "TG 1", "LW 1", "TG 2"])
        self.information.assert_not_called()

    def test_replace_overwrites_the_slot_and_empties_the_old_one(self):
        t = self.deck()
        self.answer(t, "replace")
        self.drop(t, "LW 1", row=self.row_of(t, "LW 2"))
        self.assertEqual(self.titles(t), ["TG 1", "LW 1", "TG 2"])
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")
        self.assertIsNone(t._playlist["Vorrunde"][0][0])

    def test_a_refused_move_loses_no_title(self):
        """A slot only holds its own dance: the swap says so and stays put, and
        the Replace behind it must not go on to empty the old slot."""
        t = self.deck()
        self.question.return_value = QMessageBox.StandardButton.Yes
        self.answer(t, "replace")
        self.drop(t, "LW 1", row=self.row_of(t, "TG 2"))
        self.assertEqual(self.titles(t), ["LW 1", "TG 1", "LW 2", "TG 2"])
        self.information.assert_called_once()

    def test_an_empty_slot_offers_the_move_alone(self):
        t = self.deck()
        target = self.row_of(t, "LW 2")
        t._clear_slots_at({target})
        ask = self.answer(t, "move")
        self.drop(t, "LW 1", row=target)
        self.assertEqual(self.choices(ask), ["move"])
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")
        self.assertIsNone(t._playlist["Vorrunde"][0][0])

    def test_do_nothing_leaves_the_grid(self):
        t = self.deck()
        self.answer(t, "")
        self.drop(t, "LW 1", row=self.row_of(t, "LW 2"))
        self.assertEqual(self.titles(t), ["LW 1", "TG 1", "LW 2", "TG 2"])

    def test_the_extra_titles_of_a_multi_drop_are_not_asked_about(self):
        """They were not aimed at any row, a title nobody pointed at."""
        t = self.deck()
        ask = self.answer(t, "swap")
        target = self.row_of(t, "LW 2")
        t._clear_slots_at({target})
        path = t._row_meta[self.row_of(t, "LW 1")].entry.path
        self.assertEqual(t._fill_empty_slots_with([path], 0), [])
        ask.assert_not_called()
        self.information.assert_called_once()


class DynamicDropTest(_Base):

    def dropped(self, t, title, row, replace=False):
        held = t._row_meta[self.row_of(t, title)].entry
        t._collect_drop_entries = lambda _e: [copy.copy(held)]
        settled = t._dynamic_drop(_Ev(), row, replace=replace)
        _app.processEvents()
        return settled

    def test_a_ctrl_drop_asks_instead_of_refusing(self):
        t = self.deck(dynamic=True)
        ask = self.answer(t, "swap")
        self.dropped(t, "LW 1", self.row_of(t, "LW 2"), replace=True)
        ask.assert_called_once()
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")
        self.assertEqual(t._playlist["Vorrunde"][0][0].title, "LW 2")

    def test_a_plain_drop_on_a_filled_slot_asks_too(self):
        t = self.deck(dynamic=True)
        ask = self.answer(t, "replace")
        self.dropped(t, "LW 1", self.row_of(t, "LW 2"))
        ask.assert_called_once()
        self.assertEqual(t._playlist["Finale"][0][0].title, "LW 1")
        self.assertIsNone(t._playlist["Vorrunde"][0][0])

    def test_the_source_stays_out_of_it(self):
        t = self.deck(dynamic=True)
        self.answer(t, "")
        self.assertTrue(self.dropped(t, "LW 1", self.row_of(t, "LW 2")))


class AddItHereTooTest(_Base):
    """6.2: "Play mode: show a dialog asking whether the user really wants to
    add it here, and allow it." Planning keeps its block: no second copy."""

    def playing(self, *titles):
        t = self.party(*titles)
        t._play_hl_enabled = True
        return t

    def source(self, title):
        src = self.party(title, "Keeps")
        src._drag_src_rows = [self.row_of(src, title)]
        return src

    def test_playing_mode_offers_it(self):
        t = self.playing("Used to Love", "Stuck on You")
        ask = self.answer(t, "")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertIn("add", self.choices(ask))

    def test_planning_mode_does_not(self):
        t = self.party("Used to Love", "Stuck on You")
        ask = self.answer(t, "")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertNotIn("add", self.choices(ask))

    def test_the_title_plays_in_both_places(self):
        t = self.playing("Used to Love", "Other", "Stuck on You")
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertEqual(self.titles(t), ["Stuck on You", "Used to Love", "Other",
                                          "Stuck on You"])

    def test_the_two_are_their_own_rows(self):
        """One object twice would make one marker and one grey for both."""
        t = self.playing("Used to Love", "Stuck on You")
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        rows = t._row_meta.song_rows()
        self.assertIsNot(t._row_meta[rows[0]].entry, t._row_meta[rows[2]].entry)

    def test_the_new_one_is_selected(self):
        t = self.playing("Used to Love", "Stuck on You")
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertEqual([i.row() for i in t.selectionModel().selectedRows()],
                         [t._row_meta.song_rows()[0]])

    def test_the_running_title_stays_marked(self):
        t = self.playing("Used to Love", "Stuck on You")
        running = self.row_of(t, "Stuck on You")
        t._current_play_row = running
        held = t._row_meta[running].entry
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        self.assertIs(t._row_meta[t._current_play_row].entry, held)
        self.assertEqual(t._current_play_row, t._row_meta.song_rows()[2])

    def test_a_played_title_comes_back_grey(self):
        """Report it: grey only colours, the new row still plays when it's up."""
        t = self.playing("Used to Love", "Stuck on You")
        t._played_paths.add(str(_DIR / "Stuck on You.mp3"))
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"))
        new_row = t._row_meta.song_rows()[0]
        self.assertTrue(any(r == new_row for r, _c in t._played_saved))

    def test_a_wish_leaves_the_wishlist_without_a_second_question(self):
        t = self.playing("Used to Love", "Stuck on You")
        src = self.table()
        wish = _e("Stuck on You")
        src.load_wishlist([wish], play_cb=None, suggester=None)
        src._drag_src_rows = [src._row_meta.song_rows()[0]]
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"), source=src)
        self.question.assert_not_called()
        self.assertEqual(self.titles(src), [])

    def test_a_ctrl_drop_is_a_copy_as_ever(self):
        t = self.playing("Used to Love", "Stuck on You")
        src = self.table()
        src.load_wishlist([_e("Stuck on You")], play_cb=None, suggester=None)
        src._drag_src_rows = [src._row_meta.song_rows()[0]]
        self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Used to Love"), source=src,
                  mods=Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.titles(src), ["Stuck on You"])

    def test_shift_overwrites_so_it_has_no_add(self):
        t = self.playing("Used to Love", "Stuck on You")
        ask = self.answer(t, "")
        self.drop(t, "Stuck on You", row=self.row_of(t, "Used to Love"),
                  mods=Qt.KeyboardModifier.ShiftModifier)
        ask.assert_called_once()
        self.assertNotIn("add", self.choices(ask))

    def test_dropped_on_itself_it_stays_quiet(self):
        t = self.playing("Used to Love", "Stuck on You")
        ask = self.answer(t, "add")
        self.drop(t, "Stuck on You", gap=self.row_of(t, "Stuck on You"))
        ask.assert_not_called()
        self.assertEqual(self.titles(t), ["Used to Love", "Stuck on You"])


class SwapFlashTest(_Base):

    def test_a_swap_flashes_both_rows_and_paints_them_back(self):
        t = self.party("Used to Love", "Stuck on You")
        a, c = t._row_meta.song_rows()[:2]
        base = t.item(a, 0).background().color()
        t._swap_song_rows(a, c)
        self.assertIsNotNone(t._pulse)
        self.assertEqual(sorted(t._pulse[1]), sorted([a, c]))
        t._pulse[0].setCurrentTime(300)
        _app.processEvents()
        self.assertNotEqual(t.item(a, 0).background().color(), base)
        t._end_pulse()
        self.assertIsNone(t._pulse)
        self.assertEqual(t.item(a, 0).background().color(), t._row_base_bg(a, t._row_meta.at(a)))


    def _flashed_titles(self, t):
        self.assertIsNotNone(t._pulse)
        return [getattr(t._row_meta.at(r).entry, "title", None) for r in sorted(t._pulse[1])]

    def test_a_replace_into_a_gap_flashes_landing_and_old_place(self):
        t = self.party("Used to Love", "Other", "Stuck on You")
        old = self.row_of(t, "Stuck on You")
        self.answer(t, "replace")
        self.drop(t, "Stuck on You", gap=t._row_meta.song_rows()[0])
        _app.processEvents()
        # the landing row AND the place it came from, so the eye sees both
        self.assertIn(old, t._pulse[1])
        self.assertIn("Stuck on You", self._flashed_titles(t))
        self.assertEqual(len(t._pulse[1]), 2)

    def test_a_replace_onto_a_slot_flashes_landing_and_old_place(self):
        t = self.deck()
        self.answer(t, "replace")
        old = self.row_of(t, "LW 1")
        self.drop(t, "LW 1", row=self.row_of(t, "LW 2"))
        _app.processEvents()
        self.assertIn(old, t._pulse[1])
        self.assertIn("LW 1", self._flashed_titles(t))
        t._end_pulse()


class RealDialogTest(_Base):

    def run_box(self, go, title, lines, choices):
        """Open the real box, let `go` act on it, and say what came back."""
        got, seen = [], {}
        t = self.party("Used to Love")
        t._ask_held_drop(title, lines, choices, got.append)
        box = t._held_box
        seen["buttons"] = [b.text() for b in box.buttons()]
        seen["text"] = box.text() + "\n" + box.informativeText()
        seen["default"] = box.defaultButton().text()
        seen["modal"] = box.isModal()
        seen["tips"] = {b.text(): b.toolTip() for b in box.buttons()}
        go(box)
        _app.processEvents()
        return (got[0] if got else None), seen

    @staticmethod
    def click(label):
        return lambda box: next(b for b in box.buttons() if b.text() == label).click()

    def test_the_answers_come_back(self):
        lines = ["why r", "why s"]
        for label, choice in (("Replace", "replace"), ("Swap", "swap"), ("Cancel", "")):
            got, _seen = self.run_box(self.click(label), "Song", lines,
                                      ["replace", "swap"])
            self.assertEqual(got, choice)

    def test_it_does_not_block_the_player(self):
        _got, seen = self.run_box(self.click("Cancel"), "Song", ["why"], ["swap"])
        self.assertFalse(seen["modal"])

    def test_it_is_short_and_says_why_in_the_hints(self):
        _got, seen = self.run_box(self.click("Cancel"), "Song", ["why r", "why s"],
                                  ["replace", "swap"])
        self.assertEqual(seen["buttons"], ["Replace", "Swap", "Cancel"])
        self.assertEqual(seen["tips"]["Swap"], "why s")

    def test_add_is_offered_as_add(self):
        _got, seen = self.run_box(self.click("Add"), "Song", ["a", "r", "s"],
                                  ["add", "replace", "swap"])
        self.assertEqual(seen["buttons"], ["Add", "Replace", "Swap", "Cancel"])

    def test_it_names_the_title_and_defaults_to_cancel(self):
        _got, seen = self.run_box(self.click("Cancel"), "Song", ["why"], ["swap"])
        self.assertIn("“Song” is already in this list.", seen["text"])
        self.assertEqual(seen["default"], "Cancel")
        self.assertNotIn("Replace", seen["buttons"])

    def test_escape_cancels(self):
        got, _seen = self.run_box(lambda box: box.reject(), "Song", ["why"], ["swap"])
        self.assertEqual(got, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
