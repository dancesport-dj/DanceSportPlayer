"""The key above Return removes a title, as Del does.

Run:  py -m unittest tests.gui.table.test_backspace_delete -v

Marcel's list, 6.4: "Mac keyboards have no Del key. Make the Backspace-style
delete key (above Return) remove a title from the playlist."
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_backspace_"))

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from gui import tournament_tree as gt
from gui.common import platform_keys
from gui.dialogs import shortcuts
from gui.table.playlist_table import PlaylistTable
from planner import i18n
from planner.models import MusicEntry, RoundConfig
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])
_YES = QMessageBox.StandardButton.Yes


def _e(title, dance="LW"):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance=dance,
                      duration=150)


class _Base(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(QMessageBox, "question", return_value=_YES)
        p.start()
        self.addCleanup(p.stop)

    def table(self):
        t = PlaylistTable()
        t.resize(700, 900)
        self.addCleanup(reap_widget, t)
        t.show()
        t.setFocus()
        return t

    def party(self, *titles):
        t = self.table()
        t.load_warmup([_e(x) for x in titles], "Party", "Standard", "S", False,
                      mock.Mock(), None, running_order=True)
        return t

    @staticmethod
    def titles(t):
        return [m.entry.title for _, m in t._row_meta.numbered()
                if m and m.entry is not None]

    def pick(self, t, title):
        row = next(r for r, m in t._row_meta.numbered()
                   if m and m.entry is not None and m.entry.title == title)
        t.clearSelection()
        t.setCurrentCell(row, 1)
        t.selectRow(row)


class BackspaceInTheListsTest(_Base):

    def test_it_takes_a_title_out_of_a_party_list(self):
        t = self.party("A", "B", "C")
        self.pick(t, "B")
        QTest.keyClick(t, Qt.Key.Key_Backspace)
        self.assertEqual(self.titles(t), ["A", "C"])

    def test_it_empties_the_slot_of_a_deck(self):
        t = self.table()
        playlist = {"Final": [[_e("A"), _e("B", "TG")]]}
        rounds = [RoundConfig(name="Final", heats=1, tier="final")]
        t.load(playlist, ["LW", "TG"], rounds, "S", mock.Mock(), suggester=None,
               use_timbre=False, style="Standard", dynamic=True, capacity=[1, 1])
        self.pick(t, "A")
        QTest.keyClick(t, Qt.Key.Key_Backspace)
        self.assertEqual(self.titles(t), ["B"])

    def test_it_takes_a_title_off_a_wishlist(self):
        t = self.table()
        t.load_wishlist([_e("A"), _e("B")], mock.Mock(), None)
        self.pick(t, "A")
        QTest.keyClick(t, Qt.Key.Key_Backspace)
        self.assertEqual(self.titles(t), ["B"])

    def test_a_key_of_the_number_block_counts_too(self):
        """Qt marks those with the keypad flag, and Del asked for no flag at
        all, so the Del of a number block did nothing."""
        t = self.party("A", "B")
        self.pick(t, "A")
        QTest.keyClick(t, Qt.Key.Key_Delete, Qt.KeyboardModifier.KeypadModifier)
        self.assertEqual(self.titles(t), ["B"])


class BackspaceInTheTournamentTreeTest(unittest.TestCase):

    def test_it_removes_a_playlist_like_del(self):
        d = tempfile.mkdtemp(prefix="dp_tree_backspace_")
        pane = gt.TournamentTree(JsonStore.at(os.path.join(d, "t.json")))
        self.addCleanup(reap_widget, pane)
        pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T1", "m3u": "t1.m3u"}, {"name": "T2", "m3u": "t2.m3u"}]})
        pane._rebuild()
        pane._tree.setCurrentItem(pane._tree.topLevelItem(0))
        pane._board._tiles["0/1"].picked.emit("0/1")
        with mock.patch.object(QMessageBox, "question", return_value=_YES):
            pane.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace,
                                         Qt.KeyboardModifier.NoModifier))
        self.assertEqual([n["name"] for n in pane._nodes[0]["children"]], ["T1"])


class TheKeyIsNamedAsTheKeyboardNamesItTest(unittest.TestCase):

    def test_a_mac_shows_its_own_key(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(platform_keys("Ctrl + Shift + Del"), "Cmd + Shift + ⌫")
            self.assertEqual(platform_keys("Strg + Entf"), "Cmd + ⌫")
            self.assertEqual(platform_keys("Ctrl + Supr"), "Cmd + ⌫")

    def test_words_that_only_start_alike_stay(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(platform_keys("Delete the look, Delta"),
                             "Delete the look, Delta")

    def test_other_systems_keep_del(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(platform_keys("Ctrl + Del"), "Ctrl + Del")

    def test_the_sheet_on_a_mac(self):
        i18n.set_active("en")
        with mock.patch.object(sys, "platform", "darwin"):
            sheet = shortcuts.shortcut_sheet_html()
        self.assertIn("⌫", sheet)
        self.assertNotIn("Del ", sheet)


if __name__ == "__main__":
    unittest.main()
