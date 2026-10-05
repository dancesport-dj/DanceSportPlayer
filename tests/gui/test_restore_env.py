#!/usr/bin/env python3
"""Tests for putting a saved session back on the desk.

Run:  py -m unittest tests.gui.test_restore_env -v

An env has two readers — the startup restore and every undo/redo — and they
were two copies of the same forty lines. They are one method now, so what one
of them can do the other can too, and a piece of the session that comes back in
a fresh start comes back in an undo. Both are asked here, over the same env.
"""
import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_restore_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import dancesport_gui as gui  # noqa: E402
from gui import dialogs, main_restore  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402

# A session with no tracks in it: everything below is about the state AROUND the
# songs — titles, the two view shapes, the 📅 tab, the 🔒/🔓/✋ toggles — which
# is the half both readers used to restore in their own words.
ENV = {
    "deck_count": 4,
    "wish_state": 2,
    "day_tab": "Herbstpokal",
    "names": {"deck_a": "HGR B Latein", "day_c": "Nachmittag",
              "wishlist2": "⭐  Ideen"},
    "deck_modes": {"deck_b": "free", "day_a": "dynamic"},
}


class _WindowCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # No real scan: on CI's empty music folder it finished at once, and the
        # window being reaped ran the startup restore of the shared autosave.
        stub_window_startup(cls, {"app_mode": "both"})

    def _win(self):
        win = gui.MainWindow()
        win._loading_dlg.accept()      # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        return win


class RestoreEnvTest(_WindowCase):
    """What one env puts back, whichever reader ran it."""

    def setUp(self):
        self.win = self._win()
        self.win._restore_env(dict(ENV), deck_modes=True)

    def test_the_deck_view_comes_back(self):
        self.assertEqual(self.win._deck_count, 4)

    def test_the_wishlist_view_comes_back(self):
        self.assertEqual(self.win._wish_state, 2)

    def test_the_competition_name_on_the_day_tab_comes_back(self):
        self.assertEqual(self.win._day_tab_title, "Herbstpokal")

    def test_every_renamed_list_comes_back_named(self):
        """A deck, a 📅 day deck and a wishlist — three different lists reached
        through one walk, where a key that got left out of it means a list that
        silently loses its title."""
        self.assertEqual(self.win.deck(self.win._tableA).name, "HGR B Latein")
        self.assertEqual(self.win.deck(self.win._day_decks[2]).name,
                         "Nachmittag")
        self.assertEqual(self.win.deck(self.win._wishlist2).name, "⭐  Ideen")

    def test_the_toggle_of_a_deck_that_came_back_empty_is_replayed(self):
        """An empty deck carries no state of its own to hold its mode."""
        self.assertEqual(self.win._deck_own_mode(self.win._tableB), "free")
        self.assertEqual(self.win._deck_own_mode(self.win._day_decks[0]),
                         "dynamic")

    def test_deck_a_is_left_in_front(self):
        """Restoring the later decks leaves the window's globals theirs."""
        self.assertIs(self.win._table, self.win._tableA)


class ReaderParityTest(_WindowCase):
    """The two readers of an env, over the same env."""

    def _restored(self):
        """Through the startup path: the autosave file is all there is."""
        win = self._win()
        self.addCleanup(setattr, main_restore, "load_autosave",
                        main_restore.load_autosave)
        main_restore.load_autosave = lambda: dict(ENV)
        win._lib = win._lib or object()   # the restore is skipped without one
        win._restore_playlist()
        return win

    def _applied(self):
        """Through the undo path: the env is the whole truth about a moment."""
        win = self._win()
        win._apply_env(dict(ENV))
        return win

    def test_both_readers_bring_back_the_same_titles(self):
        for win in (self._restored(), self._applied()):
            self.assertEqual(win.deck(win._tableA).name, "HGR B Latein")
            self.assertEqual(win.deck(win._wishlist2).name, "⭐  Ideen")

    def test_both_readers_bring_back_the_same_views(self):
        for win in (self._restored(), self._applied()):
            self.assertEqual(win._deck_count, 4)
            self.assertEqual(win._wish_state, 2)
            self.assertEqual(win._day_tab_title, "Herbstpokal")

    def test_an_undo_to_a_session_without_wishlists_shows_one(self):
        """The undo reader has no "unsaid means unchanged": an env that says
        nothing about the wishlist view is a moment that had one wishlist."""
        win = self._win()
        win._set_wish_state(3)
        win._apply_env({"deck_count": 1})
        self.assertEqual(win._wish_state, 1)

    def test_a_startup_from_a_file_that_says_nothing_leaves_the_view_alone(self):
        """A pre-wish_state autosave must not blow the wishlists away."""
        win = self._win()
        win._set_wish_state(3)
        self.addCleanup(setattr, main_restore, "load_autosave",
                        main_restore.load_autosave)
        main_restore.load_autosave = lambda: {"deck_count": 1}
        win._lib = win._lib or object()
        win._restore_playlist()
        self.assertEqual(win._wish_state, 3)


class EmptyDayTabTest(_WindowCase):
    """Marcel: "can a new tournament tab saved to the json?" A 📅 tab opened
    by hand under a competition name holds no tracks yet — the name alone has
    to come back after a restart, and on an undo."""

    def _opened(self):
        win = self._win()
        win._deck_count = 4
        win._set_day_tab_title("Herbstpokal")
        win._day_tab_keep = True
        win._apply_deck_view()
        return win

    def test_the_snapshot_says_the_tab_is_open(self):
        self.assertTrue(self._opened()._build_env()["day_tab_keep"])

    def test_an_empty_session_with_the_tab_is_written(self):
        from gui import main_persist
        saved = []
        self.addCleanup(setattr, main_persist, "save_autosave",
                        main_persist.save_autosave)
        main_persist.save_autosave = saved.append
        self._opened()._autosave_playlist()
        self.assertTrue(saved and saved[-1]["day_tab_keep"])

    def test_both_readers_bring_the_empty_tab_back(self):
        env = dict(ENV, day_tab_keep=True)
        self.addCleanup(setattr, main_restore, "load_autosave",
                        main_restore.load_autosave)
        main_restore.load_autosave = lambda: dict(env)
        started = self._win()
        started._lib = started._lib or object()
        started._restore_playlist()
        undone = self._win()
        undone._apply_env(dict(env))
        for win in (started, undone):
            self.assertTrue(win._deck_tabs.isTabVisible(2))
            self.assertEqual(win._deck_tabs.tabText(2), "📅 Herbstpokal")

    def test_a_snapshot_without_it_closes_the_tab(self):
        """An undo to a moment before the tab was opened takes it away again."""
        win = self._opened()
        win._apply_env(dict(ENV))
        self.assertFalse(win._deck_tabs.isTabVisible(2))


HERE = r"F:\my music\tanzcds\WW\Mondschein.mp3"
GONE = r"F:\my music\tanzcds\LW\Weg.mp3"


def _found_unless_gone(path):
    if path == GONE:
        return None
    return MusicEntry(path=Path(path), title=Path(path).stem, dance="WW", bpm=None)


class IncompleteRestoreTest(_WindowCase):
    """F: unplugged at launch: its tracks cannot come back, and the first edit
    wrote the thinned-out desk over the one autosave that still had them."""

    def setUp(self):
        self.kept = dialogs.autosave_kept_path()
        for path in (dialogs.AUTOSAVE.path, self.kept):
            # The state dir is shared by the whole run: a copy another
            # module's window kept is no copy of this test's.
            path.unlink(missing_ok=True)
            self.addCleanup(path.unlink, missing_ok=True)

    def _launch(self, env, resolve=_found_unless_gone):
        dialogs.AUTOSAVE.write(env)
        self.before = dialogs.AUTOSAVE.path.read_bytes()
        win = self._win()
        win._lib = win._lib or object()
        win._resolve_entry = resolve
        win._restore_playlist()
        return win

    def test_a_restore_that_lost_tracks_keeps_the_saved_session(self):
        win = self._launch({"version": 4, "wishlist": [HERE, GONE]})
        win._autosave_playlist()          # the first edit after the launch
        self.assertEqual(self.kept.read_bytes(), self.before)

    def test_a_complete_restore_keeps_no_copy(self):
        win = self._launch({"version": 4, "wishlist": [HERE]})
        # Red on CI only (64d53d2), never here: the status bar says whether
        # the restore raised or lost a track.
        self.assertFalse(self.kept.exists(), win.statusBar().currentMessage())

    def test_a_restore_that_failed_keeps_the_saved_session(self):
        def fail(path):
            raise OSError("the drive went away")
        self._launch({"version": 4, "wishlist": [HERE]}, resolve=fail)
        self.assertEqual(self.kept.read_bytes(), self.before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
