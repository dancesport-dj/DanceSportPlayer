#!/usr/bin/env python3
"""Every enabled entry of a deck's right-click menu does what it says.

Run:  py -m unittest tests.gui.table.test_context_menu_dispatch -v

The menu is built in sections and each entry is wired to its action where it
is added. An entry that is shown but never wired would do nothing at all when
picked, silently. So every enabled entry, on every kind of list, is picked
once here, and exactly the one call it names has to happen: no other, and
not none.
"""

import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ctxmenu_"))

from PySide6.QtCore import QItemSelectionModel, QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

# Caption → the call picking it must make. Table methods are patched on the
# table, host calls are recorded on a mock host, module functions in gui.table.table_menu.
TARGETS = [
    (r"🔎  Find similar tracks", "_show_similar"),
    (r"⭐  Find similar \(in my wishlist only\)", "_show_similar"),
    (r"🌱  Find similar \(never played\)", "_show_similar"),
    (r"📜  Find planned before", "_show_planned_before"),
    (r"📋  Copy file path", "module.show_toast"),
    (r"📂  Show in Explorer", "module.reveal_in_explorer"),
    (r"🎵  Check music speed", "host.check_track_speed"),
    (r"🏷  Re-read MP3 tags", "host.rescan_entry_tags"),
    (r"🏷  Edit tags", "host.edit_entry_tags"),
    (r"🔁  (Unmark|Mark for)", "_toggle_mark"),
    (r"🔁  Reset all replacement marks", "_reset_all_marks"),
    (r"📌  (Unpin|Pin)", "_toggle_pin"),
    (r"🗑  Remove from wishlist", "_remove_rows"),
    (r"⇅  Swap these two titles", "_swap_selected"),
    (r"➕  Add a heat", "_add_dynamic_heat"),
    (r"➕  (Insert new round|Create new round)", "_insert_dynamic_round"),
    (r"🗑  Remove (this title|\d+ selected titles)", "_confirm_delete"),
    (r"🗑  Remove this backup", "_remove_dynamic_backup"),
    (r"🗑  Remove this heat", "_remove_dynamic_heat"),
    (r"(⬆  Move backup up|🗑  Remove this empty slot)", "_remove_empty_dynamic_slot"),
    (r"🗑  Remove .+ from this round", "_remove_dance_from_round"),
    (r"🗑  Remove .+ from all rounds", "_remove_dance_everywhere"),
    (r"🗑  Remove this round", "_remove_dynamic_round"),
    (r"(🔒|🔓)  ", "host.set_deck_mode"),
    (r"💾  Save as M3U", "saveRequested"),
    (r"🏆  Save and add to Tournaments", "saveToTournamentsRequested"),
    (r"📂  Import M3U", "host.import_m3u_into"),
    (r"🧹  Remove tracks already in a playlist", "host.clean_wishlist_against_playlists"),
    (r"🧹  Remove titles the other", "host.clean_deck_against_others"),
    (r"♊  Remove duplicate titles", "_remove_duplicate_titles"),
    (r"🔍  Find a title or genre in this list", "_search_title"),
    (r"🧹  Empty this", "_clear_entire"),
]
TABLE_METHODS = sorted({t for _, t in TARGETS if "." not in t
                        and not t.endswith("Requested")})
MODULE_FUNCS = sorted({t.split(".", 1)[1] for _, t in TARGETS
                       if t.startswith("module.")})


def _song(dance, i, features=True):
    e = MusicEntry(path=Path(rf"C:\music\tanzcds\{dance}{i}.mp3"),
                   title=f"{dance} {i}", dance=dance, duration=180)
    if features:
        e.features = SimpleNamespace()
    return e


def _target_of(caption):
    for pattern, target in TARGETS:
        if re.match(pattern, caption):
            return target
    return None


class ContextMenuDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _host(self, table):
        """A window that has everything: a player, tournaments, a wishlist
        and a second deck with songs, so every entry can show up."""
        host = mock.MagicMock()
        host.player_only.return_value = False
        host.wishlist_paths.return_value = [r"C:\music\tanzcds\LW1.mp3"]
        host.has_tournaments.return_value = True
        host.can_clean_decks.return_value = True
        other = SimpleNamespace(_row_meta=SimpleNamespace(has_songs=lambda: True))
        host.visible_deck_tables.return_value = [table, other]
        return host

    def _table(self):
        win = QWidget()
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        return t

    def _open(self, t, row, pick=None):
        """Open the menu on `row`; pick the entry at index `pick` (None: close
        it). Returns the entries as (text, enabled) and the calls made."""
        seen = []

        class _Menu(QMenu):
            def exec(self, *_args):
                acts = [a for a in self.actions() if not a.isSeparator()]
                seen.extend((a.text(), a.isEnabled()) for a in acts)
                return None if pick is None else acts[pick]

        host = self._host(t)
        calls = []
        patches = [mock.patch.object(table_menu, "QMenu", _Menu),
                   mock.patch.object(PlaylistTable, "host", new_callable=mock.PropertyMock,
                                     return_value=host)]
        patches.extend(mock.patch.object(
            t, name, side_effect=lambda *a, _n=name, **k: calls.append(_n))
            for name in TABLE_METHODS)
        patches.extend(mock.patch.object(
            table_menu, name,
            side_effect=lambda *a, _n=name, **k: calls.append("module." + _n))
            for name in MODULE_FUNCS)
        # removeRow's caller goes on to drop the row meta and announce the change.
        patches.append(mock.patch.object(t, "_notify_changed"))
        for sig in ("saveRequested", "saveToTournamentsRequested"):
            getattr(t, sig).connect(lambda *_a, _s=sig: calls.append(_s))
        with mock.patch("PySide6.QtWidgets.QApplication.clipboard"):
            for p in patches:
                p.start()
            try:
                pos = QPoint(5, t.rowViewportPosition(row) + 2)
                t.contextMenuEvent(QContextMenuEvent(
                    QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
            finally:
                for p in reversed(patches):
                    p.stop()
        for sig in ("saveRequested", "saveToTournamentsRequested"):
            getattr(t, sig).disconnect()
        for call in host.method_calls:
            name = call[0]
            if _target_of_host(name):
                calls.append("host." + name)
        return seen, calls

    def _check_every_entry(self, make, row_of):
        """Pick each enabled entry on a fresh table; return the captions seen."""
        t = make()
        entries, _ = self._open(t, row_of(t))
        self.assertTrue(entries, "the menu never opened")
        picked = []
        for i, (text, enabled) in enumerate(entries):
            if not enabled:
                continue
            want = _target_of(text)
            self.assertIsNotNone(want, f"no expected call listed for {text!r}")
            t = make()
            again, calls = self._open(t, row_of(t), pick=i)
            self.assertEqual(again[i][0], text, "the menu changed between openings")
            with self.subTest(entry=text):
                self.assertEqual(calls, [want])
            picked.append(text)
        return picked

    # ── the four kinds of list ────────────────────────────────────────────────

    def _warmup(self):
        """Two titles selected, so ⇅ Swap shows up as well."""
        t = self._table()
        t.load_warmup([_song("LW", i) for i in (1, 2, 3)], "🤸 Party", "both", "S",
                      False, lambda *a: None, None)
        sm = t.selectionModel()
        for r in list(t._row_meta.song_rows())[:2]:
            sm.select(t.model().index(r, 0), QItemSelectionModel.SelectionFlag.Select
                      | QItemSelectionModel.SelectionFlag.Rows)
        return t

    def _running_order(self):
        """One title already marked, so Reset-all shows up as well."""
        t = self._table()
        t.load_player_list([_song("LW", i) for i in (1, 2, 3)], "🏁 Order",
                           lambda *a: None, None)
        t._marked_paths = {r"C:\music\tanzcds\LW1.mp3"}
        return t

    def _wishlist(self):
        t = self._table()
        t.load_wishlist([_song("LW", i) for i in (1, 2)], lambda *a: None, None)
        return t

    def _dynamic(self):
        t = self._table()
        t.load({"Vorrunde": [[_song("LW", 1), _song("TG", 2)],
                             [_song("LW", 3), None]]},
               ["LW", "TG"],
               [RoundConfig(name="Vorrunde", heats=2, tier="early")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        t._enter_dynamic([2])
        t._suggester = SimpleNamespace(lib=object())   # "Find planned before" needs one
        return t

    @staticmethod
    def _first_song(t):
        return list(t._row_meta.song_rows())[0]

    def test_warmup_deck(self):
        picked = self._check_every_entry(self._warmup, self._first_song)
        self.assertIn("📋  Copy file path", picked)
        self.assertTrue(any(p.startswith("⇅  Swap") for p in picked))

    def test_running_order(self):
        picked = self._check_every_entry(self._running_order, self._first_song)
        self.assertIn("🔁  Reset all replacement marks", picked)

    def test_wishlist(self):
        picked = self._check_every_entry(self._wishlist, self._first_song)
        self.assertIn("🗑  Remove from wishlist", picked)

    def test_dynamic_deck_song(self):
        picked = self._check_every_entry(self._dynamic, self._first_song)
        self.assertTrue(any(p.startswith("🗑  Remove this heat") for p in picked))

    def test_dynamic_deck_empty_slot(self):
        """An empty slot with a backup stacked beneath it."""
        def empty_slot(t):
            r = next(r for r in range(len(t._row_meta))
                     if t._row_meta[r] and t._row_meta[r].round_name
                     and t._row_meta[r].entry is None)
            m = t._row_meta[r]
            t._dynamic_backups[(m.round_name, m.h_idx, m.d_idx)] = [_song("TG", 9)]
            return r
        picked = self._check_every_entry(self._dynamic, empty_slot)
        self.assertIn("⬆  Move backup up into this empty slot", picked)
        self.assertIn("📜  Find planned before", picked)


def _target_of_host(name):
    return any(t == "host." + name for _, t in TARGETS)


if __name__ == "__main__":
    unittest.main()
