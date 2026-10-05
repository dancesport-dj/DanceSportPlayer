#!/usr/bin/env python3
"""The right-click menus, down to the captions that only appear sometimes.

Run:  py -m unittest tests.gui.test_menu_captions_i18n -v

Two shapes were still English, and both hide from a reader skimming the
source for quoted text:

  * a caption written as a ternary — `addAction("🔒  Back to a planned grid"
    if self._player_list else "🔒  Switch to static mode" if self._dynamic
    else "🔓  Switch to dynamic mode")`. Only one of the three is ever on
    screen at a time, so a missing entry shows up only in that one state;
  * a caption with a value in the middle, which makes it an f-string and so
    can never be a catalog key at all — `f"Columns in every {kind}"`,
    `f"➕  Insert new round after {round_name}"`, `f"🗑  Remove {dn} from
    this round (keep other dances)"`.

`test_every_menu_caption_is_in_the_catalog` is the guard: it walks the AST
of gui/, player/ and dancesport_gui.py, descends into ternaries, and fails
on any literal the catalog does not know. An earlier sweep that did not
descend reported "0 missing" while eleven were sitting there.

The dance name is already German in DANCE_NAMES ("Langsamer Walzer"), so
only the sentence around it needs the catalog — which is what `%s` gives.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_menucap_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QContextMenuEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QWidget  # noqa: E402

from gui import table_actions  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

SONGS = [MusicEntry(path=Path(rf"C:\music\tanzcds\LW{i}.mp3"),
                    title=f"LW {i}", dance="LW", duration=180)
         for i in (1, 2)]


class _Menus(unittest.TestCase):
    """A real deck, right-clicked, with nothing popping up."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    @staticmethod
    def speak(language):
        i18n.set_active(language)
        i18n.install_text_hook()    # a no-op until a language is picked

    def table(self, **kwargs):
        from gui.playlist_table import PlaylistTable
        win = QWidget()
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        t.load(**kwargs)
        return t


class ColumnMenuI18nTest(_Menus):
    """The tick list on the header says which kind of list it applies to."""

    def head(self, language, kind):
        self.speak(language)
        t = self.table(playlist={}, dances=["LW"], rounds=[], dance_class="S",
                       play_cb=lambda *a: None, suggester=None)
        t.list_kind = kind
        menu = t.build_column_menu()
        self.addCleanup(reap_widget, menu)
        return menu.actions()[0].text()

    def test_english_is_unchanged(self):
        self.assertEqual(self.head("en", "playlist"), "Columns in every playlist")
        self.assertEqual(self.head("en", "wishlist"), "Columns in every wishlist")
        self.assertEqual(self.head("en", "party"), "Columns in every party list")

    def test_every_kind_of_list_says_it_in_german(self):
        for kind in ("playlist", "wishlist", "party"):
            with self.subTest(kind=kind):
                self.assertNotIn("Columns in every", self.head("de", kind))


class RemoveDanceMenuI18nTest(_Menus):
    """"🗑 Remove Langsamer Walzer from this round" — the dance name is
    already German, the sentence around it was not."""

    def captions(self, language):
        self.speak(language)
        rounds = [RoundConfig(name="Vorrunde", heats=1, tier="early")]
        t = self.table(playlist={"Vorrunde": [[SONGS[0]]]},
                       dances=["LW"], rounds=rounds, dance_class="S",
                       play_cb=lambda *a: None, suggester=None,
                       dynamic=True, capacity=[1])
        row = next(iter(t._row_meta.song_rows()))

        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append([a.text() for a in self.actions()])
                return None

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0]

    def test_english_is_unchanged(self):
        joined = " ".join(self.captions("en"))
        self.assertIn("🗑  Remove Langsamer Walzer from this round "
                      "(keep other dances)", joined)
        self.assertIn("🗑  Remove Langsamer Walzer from all rounds and heats",
                      joined)

    def test_the_sentence_around_the_dance_speaks_german(self):
        joined = " ".join(self.captions("de"))
        self.assertNotIn("from this round", joined)
        self.assertNotIn("from all rounds and heats", joined)

    def test_the_dance_keeps_its_name(self):
        """DANCE_NAMES is German already — translating it again would be a
        second spelling of the same dance."""
        self.assertIn("Langsamer Walzer", " ".join(self.captions("de")))

    def test_the_round_the_new_one_goes_after_is_named(self):
        self.assertNotIn("Insert new round after", " ".join(self.captions("de")))


class EveryMenuCaptionTest(unittest.TestCase):
    """The sweep that finds the next one of these before the user does."""

    ROOT = Path(__file__).resolve().parents[2]

    def captions(self):
        """Every literal handed to `addAction` / `addMenu` as its text.

        A ternary is two captions, which is the part the first sweep of this
        missed — `addAction("a" if x else "b")` is not an `ast.Constant`.
        """
        import ast

        found = []

        def visit(arg, path):
            if isinstance(arg, ast.IfExp):
                visit(arg.body, path)
                visit(arg.orelse, path)
            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value:
                    found.append((f"{path.name}:{arg.lineno}", arg.value))

        files = (list((self.ROOT / "gui").rglob("*.py"))
                 + list((self.ROOT / "player").rglob("*.py"))
                 + [self.ROOT / "dancesport_gui.py"])
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("addAction", "addMenu")):
                    for arg in node.args[:2]:
                        visit(arg, path)
        return found

    def test_the_sweep_actually_sees_the_menus(self):
        """A scan that silently matches nothing would pass everything.

        71 captions are written as literals; the rest of the menus build
        their text from a table or a loop variable and are out of reach
        here — those are covered by the tests that open the real menu.
        """
        self.assertGreater(len(self.captions()), 50)

    def test_every_menu_caption_is_in_the_catalog(self):
        from planner.lang_de import CATALOG

        missing = [f"{where}  {text!r}"
                   for where, text in self.captions() if text not in CATALOG]
        self.assertEqual(missing, [], "menu captions with no German:\n"
                                      + "\n".join(missing))


if __name__ == "__main__":
    unittest.main(verbosity=2)
