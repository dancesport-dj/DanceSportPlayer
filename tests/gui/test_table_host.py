#!/usr/bin/env python3
"""A2: the table asks the window around it through one interface.

Run:  py -m unittest tests.gui.test_table_host -v

PlaylistTable read player state and called MainWindow's private methods
through `self.window()` in 33 places, each behind its own hasattr. The table
now talks to `self.host` (gui.table_host.TableHost) only, and TableHost is the
one file that knows MainWindow's member names. A table in a window without
those members (a dialog, a test) gets the answer "nothing to do".
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_host_"))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.table_host import TableHost  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TABLE_MODULES = ("gui/playlist_table.py", "gui/table_actions.py",
                 "gui/table_dnd.py", "gui/table_dynamic.py")

app = QApplication.instance() or QApplication([])


def windowCalls(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "window" and not n.args]


class _Window(QWidget):
    """Just enough of MainWindow for the host to find."""

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "player"}
        self._warmup_table = None
        self.calls = []

    def _is_player_running(self):
        return True

    def _set_deck_mode(self, table, mode):
        self.calls.append(("mode", table, mode))

    def _clean_wishlist_against_playlists(self, table, announce=True):
        self.calls.append(("clean", table, announce))
        return 3


def _hosted(win: QWidget) -> PlaylistTable:
    table = PlaylistTable()
    QVBoxLayout(win).addWidget(table)
    return table


class TableHostTest(unittest.TestCase):

    def test_the_table_modules_never_call_window(self):
        found = {m: windowCalls(REPO / m) for m in TABLE_MODULES}
        self.assertEqual({m: v for m, v in found.items() if v}, {})

    def test_the_table_has_a_host(self):
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        self.assertIsInstance(table.host, TableHost)

    def test_a_bare_window_means_nothing_to_do(self):
        win = QWidget()
        self.addCleanup(reap_widget, win)
        host = _hosted(win).host
        self.assertEqual(host.settings(), {})
        self.assertFalse(host.player_only())
        self.assertIsNone(host.list_vals())
        self.assertFalse(host.has_big_player())
        self.assertFalse(host.is_player_running())
        self.assertFalse(host.is_player_stopped())
        self.assertFalse(host.can_stop_and_skip())
        self.assertFalse(host.music_running())
        self.assertFalse(host.can_check_tracks())
        self.assertEqual(host.deck_name(), "")
        self.assertEqual(host.planned_paths(), set())
        self.assertIsNone(host.warmup_table())
        self.assertIsNone(host.wishlist_paths())
        self.assertFalse(host.can_clean_decks())
        self.assertEqual(host.clean_wishlist_against_playlists(announce=False), 0)
        self.assertIsNone(host.warmup_m3u_loader())
        self.assertIsNone(host.import_m3u_loader())
        # The actions are silent no-ops, not AttributeErrors.
        host.set_deck_mode("static")
        host.ensure_deck_ready()
        host.reset_wishlist_name()
        host.cue("C:/x.mp3")
        host.show_library_filtered(dance="SA", cls="D")
        host.show_status("hello")

    def test_the_window_members_are_reached(self):
        win = _Window()
        self.addCleanup(reap_widget, win)
        table = _hosted(win)
        host = table.host
        self.assertTrue(host.player_only())
        self.assertTrue(table.player_only())
        self.assertTrue(host.is_player_running())
        host.set_deck_mode("dynamic")
        self.assertEqual(host.clean_wishlist_against_playlists(announce=False), 3)
        self.assertEqual(win.calls, [("mode", table, "dynamic"),
                                     ("clean", table, False)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
