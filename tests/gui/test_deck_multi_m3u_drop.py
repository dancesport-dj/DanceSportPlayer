#!/usr/bin/env python3
"""Several .m3u dropped on a deck go into the free decks, one each.

Run:  py -m unittest tests.gui.test_deck_multi_m3u_drop -v

The 🏆 tab drags all its marked playlists at once (Ctrl+A). A deck imported a
drop only when it carried exactly ONE playlist; Marcel chose that several are
"Auf freie Decks verteilen", the way 📂 Import M3U fans out several picked
files. A deck of a player-only install takes its file as the flat running
order, there as everywhere else.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_multi_m3u_"))

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from gui import main_import  # noqa: E402
from gui.main_import import ImportMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _drop(table, *paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    table.dropEvent(event)
    return event


class _Win(QWidget):
    """The window as far as a deck's playlist drop reaches."""

    def __init__(self):
        super().__init__()
        self.multi, self.single = [], []
        self.deck = PlaylistTable()
        QVBoxLayout(self).addWidget(self.deck)

    def _import_m3u_multi(self, paths):
        self.multi.append(paths)

    def _import_dropped_playlist(self, table, path):
        self.single.append(path)


class DeckDropTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_multi_m3u_"))
        cls.t1, cls.t2 = cls.dir / "T1.m3u", cls.dir / "T2.m3u"
        for p in (cls.t1, cls.t2):
            p.write_text("#EXTM3U\n", encoding="utf-8")

    def setUp(self):
        self.win = _Win()
        self.addCleanup(reap_widget, self.win)

    def test_two_playlists_go_to_the_free_decks(self):
        event = _drop(self.win.deck, self.t1, self.t2)
        self.assertTrue(event.isAccepted())
        self.assertEqual(self.win.multi, [[str(self.t1), str(self.t2)]])
        self.assertEqual(self.win.single, [])

    def test_the_deck_takes_them_while_they_hover(self):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in (self.t1, self.t2)])
        for cls in (QDragEnterEvent, QDragMoveEvent):
            event = cls(QPoint(5, 5), Qt.DropAction.CopyAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            event.ignore()
            (self.win.deck.dragEnterEvent if cls is QDragEnterEvent
             else self.win.deck.dragMoveEvent)(event)
            self.assertTrue(event.isAccepted(), cls.__name__)

    def test_one_playlist_is_still_imported_into_this_deck(self):
        _drop(self.win.deck, self.t1)
        self.assertEqual(self.win.single, [self.t1])
        self.assertEqual(self.win.multi, [])


class _Deck:
    """A deck as `_import_m3u_multi` sees it: empty, flat or planned."""

    def __init__(self, flat):
        self._flat = flat

    def plays_flat(self):
        return self._flat


class _ImportWin(ImportMixin):

    def __init__(self, flat):
        self._decks = [_Deck(flat) for _ in range(4)]
        self._deck_count = 4
        self.loaded = []

    def _max_decks(self):
        return 4

    def _serialize_playlist_state(self, table):
        return None

    def _set_active_table(self, table):
        self._active = table

    def _import_playlist_path(self, path, report=True):
        self.loaded.append(("grid", self._decks.index(self._active), path))

    def _load_player_list_from_m3u(self, table, path):
        self.loaded.append(("flat", self._decks.index(table), path))

    def _autosave_playlist(self):
        pass


class MultiImportTest(unittest.TestCase):

    def setUp(self):
        self._toast = main_import._show_toast
        main_import._show_toast = lambda *a: None
        self.addCleanup(setattr, main_import, "_show_toast", self._toast)

    def test_a_planner_deck_gets_the_grid_import(self):
        win = _ImportWin(flat=False)
        win._import_m3u_multi(["a.m3u", "b.m3u"])
        self.assertEqual(win.loaded, [("grid", 0, "a.m3u"), ("grid", 1, "b.m3u")])

    def test_a_player_deck_gets_its_flat_running_order(self):
        win = _ImportWin(flat=True)
        win._import_m3u_multi(["a.m3u", "b.m3u"])
        self.assertEqual(win.loaded, [("flat", 0, "a.m3u"), ("flat", 1, "b.m3u")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
