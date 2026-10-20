#!/usr/bin/env python3
"""Smoke tests for the MainWindow mixin assembly.

Run:  py -m unittest tests.gui.test_gui_smoke -v

MainWindow is `QMainWindow + 6 mixins`, and the mixins reach across each other
through bare `self.…` attributes that no single module declares. Nothing checks
that contract, so a renamed attribute only shows up as an AttributeError while
running a tournament. These tests close that gap two ways:

* statically — every `self.X` a mixin reads must be assigned (or defined as a
  method) somewhere in the assembly, and no two mixins may define the same
  method name (the second would silently win by MRO);
* at runtime — the window really is constructed offscreen and put through the
  deck-view cycle.

The runtime half needs Qt's offscreen platform, an isolated QSettings file and a
stubbed LibraryLoader so no music library is scanned.
"""

import ast
import os
import pathlib
import tempfile
import unittest
from collections import defaultdict
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_drop_check.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_smoke_"))

# Files holding MainWindow and its mixins — the assembly under test.
_ASSEMBLY = (
    "dancesport_gui.py",
    "gui/window/main_ai.py",
    "gui/window/main_allcache.py",
    "gui/window/main_analyze.py",
    "player/window/main_audio.py",
    "player/window/main_cartwall.py",
    "player/window/main_controller.py",
    "gui/window/main_deck_setup.py",
    "gui/window/main_decks.py",
    "gui/window/main_dupes.py",
    "gui/window/main_embed.py",
    "gui/window/main_event.py",
    "gui/window/main_export.py",
    "gui/window/main_fold.py",
    "gui/window/main_fullscreen.py",
    "gui/window/main_generate.py",
    "gui/window/main_global.py",
    "player/window/main_guest.py",
    "gui/window/main_import.py",
    "gui/window/main_libpane.py",
    "player/window/main_load.py",
    "gui/window/main_music.py",
    "gui/window/main_paths.py",
    "player/window/main_pause.py",
    "player/window/main_pd.py",
    "gui/window/main_persist.py",
    "player/window/main_play_values.py",
    "player/window/main_player.py",
    "player/window/main_presenter.py",
    "gui/window/main_print.py",
    "player/window/main_remote.py",
    "gui/window/main_restore.py",
    "gui/window/main_tags.py",
    "gui/window/main_undo.py",
    "gui/window/main_wish.py",
    "player/window/main_xfade.py",
)

_REPO = pathlib.Path(__file__).resolve().parents[2]


def _assembly_classes():
    """(file, ClassDef) for MainWindow and every *Mixin in the assembly."""
    for name in _ASSEMBLY:
        tree = ast.parse((_REPO / name).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and (
                    node.name == "MainWindow" or node.name.endswith("Mixin")):
                yield name, node


class MixinContractTest(unittest.TestCase):
    """Static checks — no Qt needed."""

    def test_no_method_is_defined_by_two_mixins(self):
        owners = defaultdict(list)
        for _, cls in _assembly_classes():
            if cls.name == "MainWindow":
                continue
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    owners[node.name].append(cls.name)
        clashes = {m: o for m, o in owners.items() if len(o) > 1}
        self.assertEqual(
            clashes, {},
            "same method defined by several mixins — MRO silently picks one")

    def test_every_self_attribute_has_an_owner(self):
        """A `self.X` read anywhere in the assembly must be assigned somewhere in
        it, be a method of it, or be inherited from QMainWindow."""
        from PySide6.QtWidgets import QMainWindow

        assigned, methods = set(), set()
        read = defaultdict(set)
        for fname, cls in _assembly_classes():
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(node.name)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)      # class-level annotation
                elif isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            assigned.add(tgt.id)      # class attribute
            for node in ast.walk(cls):
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"):
                    if isinstance(node.ctx, ast.Store):
                        assigned.add(node.attr)
                    elif isinstance(node.ctx, ast.Load):
                        read[node.attr].add(fname)

        orphans = {a: sorted(f) for a, f in read.items()
                   if a not in assigned and a not in methods
                   and not hasattr(QMainWindow, a)}
        self.assertEqual(
            orphans, {},
            "attribute read but never set in the assembly — renamed or typo'd")


class MainWindowSmokeTest(unittest.TestCase):
    """Runtime checks — the window is really built, offscreen."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        # Keep QSettings out of the real registry / user config.
        cls._settings_dir = tempfile.mkdtemp(prefix="dp_smoke_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)

        cls.app = QApplication.instance() or QApplication([])

        from tests.qt_test_support import stub_window_startup
        # No library scan, and settings that don't depend on this machine.
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        from tests.qt_test_support import reap_widget   # Qt stays out of module import
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_window_constructs_without_a_library(self):
        self.assertIsNone(self.win._library.lib)
        self.assertTrue(self.win._library.loader.started)
        self.assertEqual(self.win.windowTitle(), "DanceSport Planner & Player")

    def test_the_guest_window_opens_before_any_library(self):
        """📨 Closed, no titles yet — and the same window again on the next open."""
        dlg = self.win.open_guest_window()
        self.addCleanup(dlg.close)
        self.assertFalse(self.win.guest_desk().status()["running"])
        self.assertEqual(self.win.guest_desk()._catalog(), [])
        self.assertIs(self.win.open_guest_window(), dlg)

    def test_every_mixin_contributed_its_methods(self):
        """Each mixin's public entry points really landed on the instance."""
        for name, cls in _assembly_classes():
            if cls.name == "MainWindow":
                continue
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertTrue(
                        callable(getattr(self.win, node.name, None)),
                        f"{cls.name}.{node.name} ({name}) missing on MainWindow")

    def test_deck_view_cycles_through_every_count(self):
        """1 → 2 → 4 → 8 → 0 (no playlists) → 1, decks following along."""
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        for expected in (2, 4, 8, 0, 1):
            self.win._cycle_deck_view()
            self.assertEqual(self.win._deckset.deck_count, expected)
        self.assertTrue(self.win._grid.deck_tabs.isVisible() or self.win.isHidden())

    def test_a_right_click_walks_the_deck_cycle_backwards(self):
        """Right click = one step back, so overshooting the view you wanted
        costs one click instead of four more forward."""
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        for expected in (0, 8, 4, 2, 1):
            self.win._cycle_deck_view(back=True)
            self.assertEqual(self.win._deckset.deck_count, expected)

    def test_a_right_click_walks_the_wishlist_cycle_backwards(self):
        """Same ring as the ⭐ button's left click, the other way round —
        including the 4-stacked-2×2 step between 'off' and plain 4."""
        self.win._set_wish_state(1)
        for state, grid in ((0, False), (4, True), (4, False),
                            (3, False), (2, False), (1, False)):
            self.win._cycle_wish_view(back=True)
            self.assertEqual((self.win._wish_state, self.win._wish_grid),
                             (state, grid))

    def test_no_playlist_view_hides_the_decks(self):
        self.win._deckset.deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._grid.deck_tabs.isVisibleTo(self.win))

    def test_a_filled_deck_is_brought_back_into_view(self):
        """A playlist generated behind the 'No playlist' view looks exactly like
        a run that did nothing — whatever the view was, the deck comes back."""
        self.win._deckset.deck_count = 0
        self.win._apply_deck_view()
        self.win._reveal_deck(self.win._deckset.tableA)
        self.assertGreaterEqual(self.win._deckset.deck_count, 1)
        self.assertTrue(self.win._grid.deck_tabs.isVisibleTo(self.win))
        self.assertIs(self.win._deckset.table, self.win._deckset.tableA)

    def test_revealing_a_later_deck_widens_the_view_and_fronts_its_tab(self):
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        self.win._reveal_deck(self.win._deckset.tableF)
        self.assertEqual(self.win._deckset.deck_count, 8)
        self.assertEqual(self.win._grid.deck_tabs.currentIndex(), 1)
        self.assertTrue(self.win._box_shown(self.win._deckset.tableF))

    def test_revealing_unfolds_a_deck_folded_to_a_strip(self):
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        self.win._toggle_deck_fold(self.win._deckset.tableB, True)
        self.win._reveal_deck(self.win._deckset.tableB)
        self.assertFalse(self.win.deck(self.win._deckset.tableB).folded)

    def test_focusing_a_playlist_widens_the_view_and_makes_it_active(self):
        """🎯 The controller's focus button for playlist 2, from the one-deck view."""
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        self.win._focus_list("deck", 2)
        self.assertGreaterEqual(self.win._deckset.deck_count, 2)
        self.assertIs(self.win._deckset.table, self.win._deckset.tableB)

    def test_focusing_a_wishlist_opens_enough_wishlists(self):
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        self.win._set_wish_state(1)
        wl = self.win._deckset.wishlists[2]
        self.win._focus_list("wish", 3)
        self.assertGreaterEqual(self.win._wish_state, 3)
        self.assertTrue(self.win.deck(wl).active)
        self.assertTrue(self.win._grid.wish_box3.isVisibleTo(self.win))

    def test_focusing_the_one_wishlist_in_the_one_deck_view_shows_it(self):
        """State 1 hides the single wishlist in the one-deck view; a focus
        button pressed there must not light up a list nobody can see."""
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        self.win._set_wish_state(1)
        self.win._focus_list("wish", 1)
        self.assertTrue(self.win._grid.wish_box.isVisibleTo(self.win))
        self.assertTrue(self.win.deck(self.win._deckset.wishlists[0]).active)

    def test_a_focused_list_takes_the_keyboard(self):
        """Space plays the selection of the list with the keyboard focus: a
        focus button that only lit the list up left Space on the old one."""
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        self.win.show()
        self.win._deckset.tableA.setFocus()
        self.win._focus_list("deck", 2)
        self.assertIs(self.win.focusWidget(), self.win._deckset.tableB)
        self.win._focus_list("wish", 1)
        self.assertIs(self.win.focusWidget(), self.win._deckset.wishlists[0])

    def test_alt_s_still_swaps_in_the_warm_up_list(self):
        """The warm-up list's own Alt+S (⇅ swap) — a desk key on it would
        take the key before the list sees it."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        t = self.win._deckset.tableA
        self.win.show()
        self.win.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.win))
        t._warmup, t._player_list = True, False
        with mock.patch.object(t, "_swap_selected") as swap:
            t.setFocus()
            QTest.keyClick(t, Qt.Key.Key_S, Qt.KeyboardModifier.AltModifier)
        swap.assert_called_once_with()

    def _playing_desk(self, engine):
        """The window active and in Playing mode, `engine` the list playing,
        and the big player's card a mock. Space is the card's play / pause
        there; this is where it must still reach another list."""
        from PySide6.QtTest import QTest
        self.win.show()
        self.win.activateWindow()
        self.assertTrue(QTest.qWaitForWindowActive(self.win))
        card = mock.Mock()
        for name, value in (("_is_playing_mode", mock.Mock(return_value=True)),
                            ("_big_player", card),
                            ("_engine_list", mock.Mock(return_value=engine))):
            patcher = mock.patch.object(self.win, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        return card

    def test_space_in_another_playlist_plays_its_title_while_one_plays(self):
        """Marcel: "when i switch from playlist 1 to 2 i still cant use
        leertaste to start playing the focused item in this playlist"."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        a, b = self.win._deckset.tableA, self.win._deckset.tableB
        card = self._playing_desk(engine=a)
        path = pathlib.Path("C:/m/Waltz LW 29.mp3")
        with mock.patch.object(b, "_selected_song_row", return_value=(3, path)), \
                mock.patch.object(b, "_on_play_click") as play_b:
            self.win._focus_list("deck", 2)
            QTest.keyClick(self.win.focusWidget(), Qt.Key.Key_Space)
        play_b.assert_called_once_with(3, path)
        card.toggle_play.assert_not_called()

    def test_space_stays_play_pause_in_the_list_playing(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        a = self.win._deckset.tableA
        card = self._playing_desk(engine=a)
        path = pathlib.Path("C:/m/Waltz LW 29.mp3")
        with mock.patch.object(a, "_selected_song_row", return_value=(3, path)), \
                mock.patch.object(a, "_on_play_click") as play_a:
            self.win._focus_list("deck", 1)
            QTest.keyClick(self.win.focusWidget(), Qt.Key.Key_Space)
        card.toggle_play.assert_called_once_with()
        play_a.assert_not_called()

    def test_space_with_nothing_selected_stays_play_pause(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        card = self._playing_desk(engine=self.win._deckset.tableA)
        self.win._focus_list("deck", 2)      # an empty playlist
        QTest.keyClick(self.win.focusWidget(), Qt.Key.Key_Space)
        card.toggle_play.assert_called_once_with()

    def _library_of(self, n):
        """The 📚 pane and the window's library holding `n` titles."""
        from planner.models import MusicEntry
        from planner.music.library import MusicLibrary
        folder = pathlib.Path(tempfile.mkdtemp(prefix="dp_smoke_lib_"))
        entries = []
        for i in range(n):
            path = folder / f"Waltz {i} LW 29.mp3"
            path.write_bytes(b"")      # a drop takes only files that exist
            entries.append(MusicEntry(path=path, title=f"Waltz {i}", dance="LW"))
        self.win._library.lib = MusicLibrary()
        self.win._library.lib.entries = entries
        self.win._lib_browser.set_entries(entries)
        return entries

    def test_the_library_focus_takes_the_keyboard(self):
        self.win.show()
        self.win._lib_btn.setChecked(False)
        self.win._run_controller_action("lib", 1.0)
        self.assertTrue(self.win._lib_tabs.isVisible())
        self.assertIs(self.win.focusWidget(), self.win._lib_browser._table)

    def test_browsing_moves_the_selection_of_the_focused_list(self):
        """⬆ ⬇ and the endless knob are the arrow keys of the list in focus."""
        self._library_of(6)
        self.win.show()
        lib = self.win._lib_browser._table
        self.win._run_controller_action("lib", 1.0)
        lib.setCurrentCell(0, 2)
        self.win._run_controller_action("browse_down", 1.0)
        self.assertEqual(lib.currentRow(), 1)
        self.win._run_controller_action("browse", 3 / 127)      # 3 steps right
        self.assertEqual(lib.currentRow(), 4)
        self.win._run_controller_action("browse", 63 / 127)     # 1 step left
        self.assertEqual(lib.currentRow(), 3)
        self.win._run_controller_action("browse_up", 1.0)
        self.assertEqual(lib.currentRow(), 2)
        self.assertEqual({ix.row() for ix in lib.selectedIndexes()}, {2})

    def test_play_selected_is_space_in_the_focused_list(self):
        self._library_of(3)
        self.win.show()
        lib = self.win._lib_browser._table
        lib.space_cb = mock.Mock()
        self.win._run_controller_action("lib", 1.0)
        lib.setCurrentCell(1, 2)
        self.win._run_controller_action("pick_play", 1.0)
        lib.space_cb.assert_called_once_with(1)

    def test_play_selected_plays_the_library_title_while_one_plays(self):
        self._library_of(3)
        card = self._playing_desk(engine=self.win._deckset.tableA)
        lib = self.win._lib_browser._table
        lib.space_cb = mock.Mock()
        self.win._run_controller_action("lib", 1.0)
        lib.setCurrentCell(1, 2)
        self.win._run_controller_action("pick_play", 1.0)
        lib.space_cb.assert_called_once_with(1)
        card.toggle_play.assert_not_called()

    def test_play_selected_plays_the_selected_title_of_the_list_playing(self):
        """Marcel: "alt+p for play selected title playes not the selected but
        the one selected before" — Space there is the card's play / pause."""
        a = self.win._deckset.tableA
        card = self._playing_desk(engine=a)
        path = pathlib.Path("C:/m/Waltz LW 29.mp3")
        with mock.patch.object(a, "_selected_song_row", return_value=(3, path)), \
                mock.patch.object(a, "_on_play_click") as play_a:
            self.win._focus_list("deck", 1)
            self.win._run_controller_action("pick_play", 1.0)
        play_a.assert_called_once_with(3, path)
        card.toggle_play.assert_not_called()

    def test_enter_plays_the_selected_title_of_the_list_playing(self):
        """Enter starts the selection, Space stays the card's play / pause."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        a = self.win._deckset.tableA
        card = self._playing_desk(engine=a)
        path = pathlib.Path("C:/m/Waltz LW 29.mp3")
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            with mock.patch.object(a, "_selected_song_row", return_value=(3, path)), \
                    mock.patch.object(a, "_on_play_click") as play_a:
                self.win._focus_list("deck", 1)
                a._space_at = 0.0       # not a double tap of the last key
                QTest.keyClick(self.win.focusWidget(), key)
            play_a.assert_called_once_with(3, path)
        card.toggle_play.assert_not_called()

    def test_enter_plays_the_selected_library_row(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self._library_of(3)
        self._playing_desk(engine=self.win._deckset.tableA)
        lib = self.win._lib_browser._table
        lib.space_cb = mock.Mock()
        self.win._run_controller_action("lib", 1.0)
        lib.setCurrentCell(1, 2)
        QTest.keyClick(lib, Qt.Key.Key_Return)
        lib.space_cb.assert_called_once_with(1)

    def test_a_picked_title_goes_to_the_end_of_the_wishlist(self):
        entries = self._library_of(3)
        self.win.show()
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        self.win._set_wish_state(0)
        wl = self.win._deckset.wishlists[0]
        lib = self.win._lib_browser._table
        self.win._run_controller_action("lib", 1.0)
        for row in (2, 0):
            lib.setCurrentCell(row, 2)
            self.win._run_controller_action("pick_wish", 1.0)
        self.assertGreaterEqual(self.win._wish_state, 1)   # shown for it
        self.assertEqual([str(e.path) for e in wl._row_meta.entries()],
                         [str(self.win._lib_browser._row_path(r)) for r in (2, 0)])
        self.assertTrue({str(e.path) for e in entries}
                        >= {str(e.path) for e in wl._row_meta.entries()})
        self.assertIs(self.win.focusWidget(), lib)   # browsing goes on there

    def test_a_picked_title_goes_to_the_active_playlist(self):
        self._library_of(2)
        self.win.show()
        deck = self.win._deckset.table
        lib = self.win._lib_browser._table
        self.win._run_controller_action("lib", 1.0)
        lib.setCurrentCell(1, 2)
        seen = []

        def drop(event):     # the event dies with the call: read it in there
            seen.append(([u.toLocalFile() for u in event.mimeData().urls()],
                         deck.rowAt(int(event.position().y())), event.source()))

        with mock.patch.object(deck, "dropEvent", side_effect=drop):
            self.win._run_controller_action("pick_deck", 1.0)
        self.assertEqual(seen, [(
            [pathlib.Path(self.win._lib_browser._row_path(1)).as_posix()],
            -1,       # below the rows: the end of the list
            None)])   # no drag source: a copy, the library keeps it

    def test_a_player_build_ignores_playlists_past_four(self):
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        before = self.win._deckset.table
        with mock.patch("gui.window.main_decks.player_build", return_value=True):
            self.win._focus_list("deck", 6)
        self.assertEqual(self.win._deckset.deck_count, 1)
        self.assertIs(self.win._deckset.table, before)

    def test_the_cartwall_is_a_dock_beside_the_decks_not_a_tab(self):
        from PySide6.QtCore import Qt

        self.assertEqual(self.win._grid.deck_tabs.count(), 3)
        self.assertIs(self.win._cart_dock.widget(), self.win._cartwall)
        self.assertEqual(self.win.dockWidgetArea(self.win._cart_dock),
                         Qt.DockWidgetArea.RightDockWidgetArea)

    def test_the_wall_can_ask_the_desk_for_the_sound_device(self):
        """🔇 idle release: a pad fires straight from the wall, so the wall has
        to be able to tell the desk to take the card back — see
        player.audio.audio_device.AudioDevice.ensure."""
        if self.win._cart_voices is None:
            self.skipTest("no audio backend here")
        self.win._audio_device.released = True
        self.win._cart_voices.wantsDevice.emit()
        self.assertFalse(self.win._audio_device.released)

    def test_the_cartwall_dock_can_be_moved_and_floated(self):
        """The whole point of the dock: park it left, right, below or on a
        second screen, and drag the splitter to size it."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget

        feats = self.win._cart_dock.features()
        self.assertTrue(feats & QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.assertTrue(feats & QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.assertEqual(self.win._cart_dock.allowedAreas(),
                         Qt.DockWidgetArea.AllDockWidgetAreas)

    def test_the_cartwall_dock_can_be_narrowed(self):
        """'Snapped on the right … and resized' — the wall has to be draggable
        down to a slim strip, not only wider."""
        self.assertLess(self.win._cart_dock.minimumSizeHint().width(), 500)

    def test_a_first_run_opens_the_cartwall_at_a_quarter_of_the_window(self):
        """No saved layout yet: a third of the window was too much wall."""
        from gui.window.main_persist import layout_settings
        from tests.qt_test_support import reap_widget

        # Cleared before the window is built: setUp's window already restored
        # whatever an earlier test's window saved — fullscreen, say.
        layout_settings().clear()
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        win.resize(1600, 900)
        win._cartwall_shown = False
        win._restore_layout()
        win.show()
        # The wall comes up later, from the toolbar, as on a real first run.
        win._cart_btn.setChecked(True)
        self.app.processEvents()
        self.assertAlmostEqual(win._cart_dock.width(), 400, delta=30)
        win._cart_btn.setChecked(False)

    def test_the_toolbar_toggle_and_the_dock_stay_in_step(self):
        self.win.show()     # a dock closing before the window is up is not a click
        self.win._cart_btn.setChecked(True)
        self.assertTrue(self.win._cartwall_shown)
        self.assertFalse(self.win._cart_dock.isHidden())
        # Closing the dock itself has to un-press the toolbar button.
        self.win._cart_dock.close()
        self.assertFalse(self.win._cart_btn.isChecked())
        self.assertFalse(self.win._cartwall_shown)

    def test_the_cartwall_survives_the_no_playlist_view(self):
        """A dock is not inside _deck_tabs, so the view that hides the whole tab
        area no longer takes the wall down with it."""
        self.win._cart_btn.setChecked(True)
        self.win._deckset.deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._grid.deck_tabs.isVisibleTo(self.win))
        self.assertFalse(self.win._cart_dock.isHidden())
        self.win._cart_btn.setChecked(False)

    def test_one_wishlist_shows_in_the_no_playlist_view(self):
        """A single wishlist steps aside only for the ONE-deck view. With the decks
        hidden entirely (party list, no normal playlists) it must show — that view
        exists precisely so the wishlist / Eintanzen / library panes take over."""
        self.win._set_wish_state(1)
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        self.assertFalse(self.win._grid.wish_split.isVisibleTo(self.win))
        self.win._deckset.deck_count = 0
        self.win._apply_deck_view()
        self.assertTrue(self.win._grid.wish_split.isVisibleTo(self.win))
        self.assertTrue(self.win._grid.wish_box.isVisibleTo(self.win))

    def test_the_wishlist_off_state_survives_the_no_playlist_view(self):
        """⭐ off means off — even with every deck hidden."""
        self.win._set_wish_state(0)
        self.win._deckset.deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._grid.wish_split.isVisibleTo(self.win))

    def test_active_deck_can_be_switched(self):
        """Focusing a deck makes it the Generate / Save / ↺ target."""
        self.win._set_active_table(self.win._deckset.tableB)
        self.assertIs(self.win._deckset.table, self.win._deckset.tableB)
        self.win._set_active_table(self.win._deckset.tableA)
        self.assertIs(self.win._deckset.table, self.win._deckset.tableA)


if __name__ == "__main__":
    unittest.main()
