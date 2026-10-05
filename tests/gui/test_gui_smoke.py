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

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_drop_check.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_smoke_"))

# Files holding MainWindow and its mixins — the assembly under test.
_ASSEMBLY = (
    "dancesport_gui.py",
    "gui/main_allcache.py",
    "gui/main_analyze.py",
    "player/main_audio.py",
    "player/main_cartwall.py",
    "gui/main_decks.py",
    "gui/main_dupes.py",
    "gui/main_embed.py",
    "gui/main_export.py",
    "gui/main_fold.py",
    "gui/main_generate.py",
    "gui/main_global.py",
    "gui/main_import.py",
    "gui/main_music.py",
    "gui/main_paths.py",
    "player/main_pause.py",
    "player/main_pd.py",
    "gui/main_persist.py",
    "player/main_player.py",
    "gui/main_print.py",
    "gui/main_restore.py",
    "gui/main_undo.py",
    "gui/main_wish.py",
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
        self.assertIsNone(self.win._lib)
        self.assertTrue(self.win._loader.started)
        self.assertEqual(self.win.windowTitle(), "DanceSport Planner & Player")

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
        self.win._deck_count = 1
        self.win._apply_deck_view()
        for expected in (2, 4, 8, 0, 1):
            self.win._cycle_deck_view()
            self.assertEqual(self.win._deck_count, expected)
        self.assertTrue(self.win._deck_tabs.isVisible() or self.win.isHidden())

    def test_a_right_click_walks_the_deck_cycle_backwards(self):
        """Right click = one step back, so overshooting the view you wanted
        costs one click instead of four more forward."""
        self.win._deck_count = 1
        self.win._apply_deck_view()
        for expected in (0, 8, 4, 2, 1):
            self.win._cycle_deck_view(back=True)
            self.assertEqual(self.win._deck_count, expected)

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
        self.win._deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._deck_tabs.isVisibleTo(self.win))

    def test_a_filled_deck_is_brought_back_into_view(self):
        """A playlist generated behind the 'No playlist' view looks exactly like
        a run that did nothing — whatever the view was, the deck comes back."""
        self.win._deck_count = 0
        self.win._apply_deck_view()
        self.win._reveal_deck(self.win._tableA)
        self.assertGreaterEqual(self.win._deck_count, 1)
        self.assertTrue(self.win._deck_tabs.isVisibleTo(self.win))
        self.assertIs(self.win._table, self.win._tableA)

    def test_revealing_a_later_deck_widens_the_view_and_fronts_its_tab(self):
        self.win._deck_count = 1
        self.win._apply_deck_view()
        self.win._reveal_deck(self.win._tableF)
        self.assertEqual(self.win._deck_count, 8)
        self.assertEqual(self.win._deck_tabs.currentIndex(), 1)
        self.assertTrue(self.win._box_shown(self.win._tableF))

    def test_revealing_unfolds_a_deck_folded_to_a_strip(self):
        self.win._deck_count = 2
        self.win._apply_deck_view()
        self.win._toggle_deck_fold(self.win._tableB, True)
        self.win._reveal_deck(self.win._tableB)
        self.assertFalse(self.win.deck(self.win._tableB).folded)

    def test_the_cartwall_is_a_dock_beside_the_decks_not_a_tab(self):
        from PySide6.QtCore import Qt

        self.assertEqual(self.win._deck_tabs.count(), 3)
        self.assertIs(self.win._cart_dock.widget(), self.win._cartwall)
        self.assertEqual(self.win.dockWidgetArea(self.win._cart_dock),
                         Qt.DockWidgetArea.RightDockWidgetArea)

    def test_the_wall_can_ask_the_desk_for_the_sound_device(self):
        """🔇 idle release: a pad fires straight from the wall, so the wall has
        to be able to tell the desk to take the card back — see
        player.audio_device.AudioDevice.ensure."""
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
        self.win._deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._deck_tabs.isVisibleTo(self.win))
        self.assertFalse(self.win._cart_dock.isHidden())
        self.win._cart_btn.setChecked(False)

    def test_one_wishlist_shows_in_the_no_playlist_view(self):
        """A single wishlist steps aside only for the ONE-deck view. With the decks
        hidden entirely (party list, no normal playlists) it must show — that view
        exists precisely so the wishlist / Eintanzen / library panes take over."""
        self.win._set_wish_state(1)
        self.win._deck_count = 1
        self.win._apply_deck_view()
        self.assertFalse(self.win._wish_split.isVisibleTo(self.win))
        self.win._deck_count = 0
        self.win._apply_deck_view()
        self.assertTrue(self.win._wish_split.isVisibleTo(self.win))
        self.assertTrue(self.win._wish_box.isVisibleTo(self.win))

    def test_the_wishlist_off_state_survives_the_no_playlist_view(self):
        """⭐ off means off — even with every deck hidden."""
        self.win._set_wish_state(0)
        self.win._deck_count = 0
        self.win._apply_deck_view()
        self.assertFalse(self.win._wish_split.isVisibleTo(self.win))

    def test_active_deck_can_be_switched(self):
        """Focusing a deck makes it the Generate / Save / ↺ target."""
        self.win._set_active_table(self.win._tableB)
        self.assertIs(self.win._table, self.win._tableB)
        self.win._set_active_table(self.win._tableA)
        self.assertIs(self.win._table, self.win._tableA)


if __name__ == "__main__":
    unittest.main()
