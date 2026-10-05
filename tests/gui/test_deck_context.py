#!/usr/bin/env python3
"""A4: every deck keeps its own generation context; focus only picks one.

Run:  py -m unittest tests.gui.test_deck_context -v

The fifteen fields a deck was generated with (mode, style, class, dances, the
grid, the replay and theme state…) used to live on the window and were copied
out to the deck and back in on every focus change. Anything that finished later
(an AI run, a restore) had to put the focus back on its deck before it could
write, or it wrote into whichever deck the user had clicked meanwhile.

Now they live on the deck (gui.deck.DeckContext). `self._style` and friends on
the window read and write the FOCUSED deck's context, and a deck that is not
focused can be written directly through `win.deck(table).ctx`.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_deckctx_"))

from gui.deck import DeckContext  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class DeckContextTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_deckctx_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.a, self.b, self.c = self.win._tableA, self.win._tableB, self.win._tableC

    def test_the_focused_deck_holds_its_context(self):
        self.win._set_active_table(self.a)
        self.win._style = "Standard"
        self.win._playlist = {"Runde 1": []}
        ctx = self.win.deck(self.a).ctx
        self.assertIsInstance(ctx, DeckContext)
        self.assertEqual(ctx.style, "Standard")
        self.assertEqual(ctx.playlist, {"Runde 1": []})

    def test_a_deck_written_while_unfocused_shows_it_on_focus(self):
        self.win._set_active_table(self.a)
        self.win._set_active_table(self.b)   # B gets a context of its own
        self.win._set_active_table(self.a)
        self.win.deck(self.b).ctx.dance_class = "A"
        self.win.deck(self.b).ctx.theme_label = "Late answer"
        self.assertEqual(self.win._deck_meta(self.b)["dance_class"], "A")
        self.assertNotEqual(self.win._dance_class, "A")   # A is untouched
        self.win._set_active_table(self.b)
        self.assertEqual(self.win._dance_class, "A")
        self.assertEqual(self.win._theme_label, "Late answer")

    def test_leaving_a_deck_copies_nothing(self):
        self.win._set_active_table(self.a)
        ctx_a = self.win.deck(self.a).ctx
        self.win._set_active_table(self.b)
        self.win._age = "Senioren I"
        self.assertIs(self.win.deck(self.a).ctx, ctx_a)
        self.assertNotEqual(ctx_a.age, "Senioren I")
        self.assertIsNot(self.win.deck(self.b).ctx, ctx_a)

    def test_a_fresh_deck_keeps_the_combo_selection(self):
        """Unchanged behaviour: focusing a never-generated deck leaves the
        mode/style/class/dances on screen and clears only the content."""
        self.win._set_active_table(self.a)
        self.win._style = "Standard"
        self.win._dance_class = "B"
        self.win._dances = ["LW", "TG"]
        self.win._playlist = {"Runde 1": []}
        self.win._theme_label = "Mine"
        self.win._set_active_table(self.c)
        self.assertEqual(self.win._style, "Standard")
        self.assertEqual(self.win._dance_class, "B")
        self.assertIsNone(self.win._playlist)
        self.assertEqual(self.win._theme_label, "")
        self.win._set_active_table(self.a)
        self.assertEqual(self.win._playlist, {"Runde 1": []})

    def test_a_blanked_unfocused_deck_forgets_its_context(self):
        self.win._set_active_table(self.b)
        self.win._dance_class = "A"
        self.win._set_active_table(self.a)
        self.win._blank_deck(self.b)
        self.assertEqual(self.win._deck_meta(self.b)["dance_class"], "S")

    def test_the_window_keeps_no_copy(self):
        for name in ("_CTX_FIELDS", "_save_deck_ctx"):
            self.assertFalse(hasattr(self.win, name), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
