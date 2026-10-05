#!/usr/bin/env python3
"""🎛 The right-click on a pad, in the language the rest of the app is in.

Run:  py -m unittest tests.player.test_cartwall_i18n -v

Two holes, both invisible from the source at a glance:

  * three captions carry the "how many pads this will hit" suffix and are
    therefore f-strings — `f"🎨  Colour{many}"` can never be a catalog key,
    so those three lines stayed English between German neighbours;
  * the colour names are handed to `addAction(icon, name, cb)` from
    PAD_COLOURS, and the hook does translate that position — they simply had
    no entries.

The name is display only: the signal carries the colour VALUE and the
checkmark compares values, so a German name changes nothing behind it. That
is what makes them safe to translate, and it is pinned below.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wall_i18n_"))

from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402

from planner import cartwall as pc  # noqa: E402
from planner import i18n  # noqa: E402
from player import cartwall as gc  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _OpenedMenu(QMenu):
    """A QMenu that records itself instead of entering a modal loop.

    `QMenu.exec` cannot be replaced on the Shiboken type — assigning to it is
    accepted and then ignored, and the test hangs on a real popup. Swapping
    the name the module looks up is what works.
    """

    built: list = []

    def __init__(self, parent=None):
        super().__init__(parent)
        _OpenedMenu.built.append(self)

    def exec(self, *_a, **_k):
        return None


class _PadMenu(unittest.TestCase):
    """A real pad, right-clicked, with nothing popping up."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._real_menu = gc.QMenu
        gc.QMenu = _OpenedMenu
        _OpenedMenu.built = []

    def tearDown(self):
        gc.QMenu = self._real_menu
        _OpenedMenu.built = []
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def menu(self, language, *, filled=True, selected=0):
        """The captions and submenu titles the right-click puts on screen."""
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked
        pad = gc._CartPadButton((0, 0, 0))
        self.addCleanup(reap_widget, pad)
        pad._editable = True
        pad._sel_count = selected
        if filled:
            pad.set_pad(pc.CartPad(path="fanfare.mp3"))

        _OpenedMenu.built = []
        pad._context_menu(pad.rect().center())
        self.assertTrue(_OpenedMenu.built, "the pad opened no menu")
        return _OpenedMenu.built[0]

    @staticmethod
    def captions(menu):
        return [a.text() for a in menu.actions() if a.text()]


class PadMenuI18nTest(_PadMenu):

    def test_english_is_unchanged(self):
        self.assertEqual(
            self.captions(self.menu("en"))[:3],
            ["⚙  Settings…", "🎨  Colour", "🗑  Clear pad"])

    def test_the_three_captions_speak_german(self):
        for caption in self.captions(self.menu("de"))[:3]:
            self.assertNotIn("Settings", caption)
            self.assertNotIn("Colour", caption)
            self.assertNotIn("Clear pad", caption)

    def test_the_empty_pad_was_already_german(self):
        """`"📂  Assign files…"` is a plain literal, so the hook always had
        it — which is why the three below it could sit English unnoticed."""
        caption = self.captions(self.menu("de", filled=False))[0]
        self.assertNotIn("Assign files", caption)

    def test_the_count_of_pads_comes_along(self):
        """"(3 pads)" is the whole point of the f-strings that broke this."""
        joined = " ".join(self.captions(self.menu("de", selected=3)))
        self.assertNotIn("pads)", joined)
        self.assertIn("3", joined)

    def test_one_pad_gets_no_count_at_all(self):
        for caption in self.captions(self.menu("de", selected=1)):
            self.assertNotIn("(", caption)


class PadColourI18nTest(_PadMenu):

    def test_every_colour_name_has_a_german_one(self):
        i18n.set_active("de")
        for name in gc.PAD_COLOURS:
            self.assertNotEqual(i18n.t(name), name,
                                f"the pad colour {name!r} stayed English")

    def test_white_comes_along_too(self):
        """Offered on the wall-wide submenu only — a pad already has
        "Wall default" for it."""
        i18n.set_active("de")
        self.assertNotEqual(i18n.t("White"), "White")

    def test_the_value_behind_a_name_is_untouched(self):
        """What the signal carries and what the checkmark compares."""
        i18n.set_active("de")
        self.assertEqual(gc.PAD_COLOURS["Green"], "#2f8f4e")
        self.assertEqual(gc.PAD_COLOURS["Wall default"], "")

    def test_the_settings_dialog_reads_its_combo_back_by_value(self):
        """The same names fill the pad-settings combo through
        `addItem(name, value)`; `findData` is what reads it back."""
        i18n.set_active("de")
        i18n.install_text_hook()    # `addItem` only translates through the hook
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", colour="#b23b3b"),
                               slot_key="1")
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._colour.currentData(), "#b23b3b")
        self.assertNotIn("Red", dlg._colour.currentText())


if __name__ == "__main__":
    unittest.main(verbosity=2)
