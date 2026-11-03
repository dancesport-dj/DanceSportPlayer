"""Take a title out together with its slot.

Run:  py -m unittest tests.gui.table.test_remove_with_slot -v

Marcel's list, 6.3: "The context item "remove" keeps the title slot empty. Also
offer removing the title together with its slot."

A party list's slot is just its row. A grid keeps one row per heat and dance, so
there a slot can only go when the round holds that dance nowhere else: the dance
then leaves the round, which is what the menu already does for an empty slot.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_slot_"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

ONE = "🗑  Remove this title and its slot"
MANY = "🗑  Remove 2 selected titles and their slots"


def _e(title, dance="LW"):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance=dance,
                      duration=150)


class _Base(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(QMessageBox, "question",
                              return_value=QMessageBox.StandardButton.Yes)
        self.ask = p.start()
        self.addCleanup(p.stop)

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        return t

    def party(self, *titles, running_order=False):
        t = self.table()
        t.load_warmup([_e(x) for x in titles], "Party", "Standard", "S", False,
                      mock.Mock(), None, running_order=running_order)
        return t

    def deck(self, playlist):
        t = self.table()
        rounds = [RoundConfig(name=n, heats=len(h), tier="final")
                  for n, h in playlist.items()]
        t.load(playlist, ["LW", "TG"], rounds, "S", mock.Mock(), suggester=None,
               use_timbre=False, style="Standard", dynamic=True, capacity=[1, 1])
        return t

    @staticmethod
    def row_of(t, title):
        return next(r for r, m in t._row_meta.numbered() if m.entry.title == title)

    def menu(self, t, row, pick=None):
        """The menu's texts on `row`; `pick` is chosen from it."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen


class PartyListTest(_Base):

    def test_both_ways_are_offered(self):
        t = self.party("A", "B")
        texts = self.menu(t, self.row_of(t, "A"))
        self.assertIn("🗑  Remove this title (keep slot)	Del", texts)
        self.assertIn(ONE, texts)

    def test_the_row_goes(self):
        t = self.party("A", "B", "C")
        self.menu(t, self.row_of(t, "B"), pick=ONE)
        self.assertEqual([e.title for e in t._row_meta.entries()], ["A", "C"])
        self.assertEqual(len(t._row_meta.song_rows()), 2)
        self.assertFalse([r for r, m in enumerate(t._row_meta)
                          if m and not m.theme and m.entry is None])

    def test_keep_slot_still_keeps_it(self):
        t = self.party("A", "B", "C")
        rows = t.rowCount()
        self.menu(t, self.row_of(t, "B"), pick="🗑  Remove this title (keep slot)	Del")
        self.assertEqual(t.rowCount(), rows)

    def test_no_means_no(self):
        self.ask.return_value = QMessageBox.StandardButton.No
        t = self.party("A", "B")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertEqual(len(t._row_meta.song_rows()), 2)

    def test_the_prompt_says_the_slot_goes_too(self):
        t = self.party("A", "B")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        self.assertIn("slot", self.ask.call_args.args[2])
        self.assertNotIn("empty", self.ask.call_args.args[2])

    def test_a_selection_goes_as_a_whole(self):
        t = self.party("A", "B", "C")
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(self.row_of(t, "A"))
        t.selectRow(self.row_of(t, "B"))
        self.menu(t, self.row_of(t, "A"), pick=MANY)
        self.assertEqual([e.title for e in t._row_meta.entries()], ["C"])

    def test_the_title_on_air_stops_like_any_removal(self):
        t = self.party("A", "B")
        t._current_play_row = self.row_of(t, "A")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        t._play_cb.assert_called_once_with(None)

    def test_a_title_behind_it_keeps_its_marker(self):
        t = self.party("A", "B")
        t._current_play_row = self.row_of(t, "B")
        self.menu(t, self.row_of(t, "A"), pick=ONE)
        t._play_cb.assert_not_called()
        self.assertEqual(t._current_play_row, self.row_of(t, "B"))


class DeleteKeyTest(_Base):
    """Del in a party list asks which way, like the two menu entries."""

    def press_del(self, t, title, choice):
        t.selectRow(self.row_of(t, title))
        with mock.patch.object(PlaylistTable, "_ask_remove_party",
                               return_value=choice) as ask:
            QTest.keyClick(t, Qt.Key.Key_Delete)
        return ask

    def test_the_slot_can_go_with_the_title(self):
        t = self.party("A", "B", "C")
        ask = self.press_del(t, "B", "slots")
        ask.assert_called_once_with(1)
        self.assertEqual([e.title for e in t._row_meta.entries()], ["A", "C"])
        self.assertEqual(len(t._row_meta.song_rows()), 2)

    def test_or_stay_empty(self):
        t = self.party("A", "B", "C")
        rows = t.rowCount()
        self.press_del(t, "B", "keep")
        self.assertEqual(t.rowCount(), rows)
        self.assertEqual([e.title for e in t._row_meta.entries()], ["A", "C"])

    def test_cancel_removes_nothing(self):
        t = self.party("A", "B", "C")
        self.press_del(t, "B", None)
        self.assertEqual(len(t._row_meta.entries()), 3)

    def test_a_deck_still_just_asks_yes_or_no(self):
        t = self.deck({"R": [[_e("A"), _e("B", "TG")]]})
        t.selectRow(self.row_of(t, "A"))
        with mock.patch.object(PlaylistTable, "_ask_remove_party") as ask:
            QTest.keyClick(t, Qt.Key.Key_Delete)
        ask.assert_not_called()
        self.ask.assert_called()


class FocusStaysTest(_Base):
    """After a removal the cursor stays where the title was, on the one that
    moved up into its place."""

    def selected_titles(self, t):
        rows = {ix.row() for ix in t.selectedIndexes()}
        return [m.entry.title if m.entry else None
                for r, m in t._row_meta.numbered() if r in rows]

    def test_del_with_the_slot_lands_on_the_next_title(self):
        t = self.party("A", "B", "C")
        t.selectRow(self.row_of(t, "B"))
        with mock.patch.object(PlaylistTable, "_ask_remove_party", return_value="slots"):
            QTest.keyClick(t, Qt.Key.Key_Delete)
        self.assertEqual(self.selected_titles(t), ["C"])
        self.assertEqual(t.currentRow(), self.row_of(t, "C"))

    def test_del_of_the_last_title_lands_on_the_new_last(self):
        t = self.party("A", "B", "C")
        t.selectRow(self.row_of(t, "C"))
        with mock.patch.object(PlaylistTable, "_ask_remove_party", return_value="slots"):
            QTest.keyClick(t, Qt.Key.Key_Delete)
        self.assertEqual(self.selected_titles(t), ["B"])

    def test_keep_slot_stays_on_the_emptied_slot(self):
        t = self.party("A", "B", "C")
        row = self.row_of(t, "B")
        t.selectRow(row)
        with mock.patch.object(PlaylistTable, "_ask_remove_party", return_value="keep"):
            QTest.keyClick(t, Qt.Key.Key_Delete)
        self.assertEqual(t.currentRow(), row)
        self.assertIn(row, {ix.row() for ix in t.selectedIndexes()})

    def test_the_menu_removal_lands_on_the_next_title_too(self):
        t = self.party("A", "B", "C")
        self.menu(t, self.row_of(t, "B"), pick=ONE)
        self.assertEqual(self.selected_titles(t), ["C"])


class RunningOrderTest(_Base):

    def test_no_second_entry_where_the_row_goes_anyway(self):
        t = self.party("A", "B", running_order=True)
        self.assertNotIn(ONE, self.menu(t, self.row_of(t, "A")))


class GridTest(_Base):

    def test_the_only_title_of_its_dance_in_the_round_can_go(self):
        t = self.deck({"Finale": [[_e("LW 1"), _e("TG 1", "TG")]]})
        self.menu(t, self.row_of(t, "LW 1"), pick=ONE)
        self.assertIn("LW", t._round_skip_dances["Finale"])
        self.assertEqual([e.title for e in t._row_meta.entries()], ["TG 1"])

    def test_a_dance_with_more_titles_in_the_round_keeps_its_rows(self):
        t = self.deck({"Finale": [[_e("LW 1"), _e("TG 1", "TG")],
                                  [_e("LW 2"), _e("TG 2", "TG")]]})
        self.assertNotIn(ONE, self.menu(t, self.row_of(t, "LW 1")))

    def test_a_backup_under_it_is_not_thrown_away(self):
        t = self.deck({"Finale": [[_e("LW 1"), _e("TG 1", "TG")]]})
        t._dynamic_backups[("Finale", 0, 0)] = [_e("LW 9")]
        self.assertNotIn(ONE, self.menu(t, self.row_of(t, "LW 1")))

    def test_a_selection_is_not_offered(self):
        t = self.deck({"Finale": [[_e("LW 1"), _e("TG 1", "TG")]]})
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        t.selectRow(self.row_of(t, "LW 1"))
        t.selectRow(self.row_of(t, "TG 1"))
        self.assertNotIn(MANY, self.menu(t, self.row_of(t, "LW 1")))


if __name__ == "__main__":
    unittest.main()
