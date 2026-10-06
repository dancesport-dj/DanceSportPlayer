#!/usr/bin/env python3
"""Under a 🎨 look the chrome's emoji become painted icons; classic keeps them.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_look_icons -v
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_look_icons_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QGroupBox, QLabel, QMenu, QPushButton, QTabWidget,
    QToolButton, QWidget)

from planner import i18n  # noqa: E402
from shared import icons, look_icons, looks, theme  # noqa: E402
from tests.qt_test_support import reap_widget, stub_window_startup  # noqa: E402

LOOK = "midnight" if "midnight" in looks.LOOKS else next(iter(looks.LOOKS))


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def use(self, key, language="en"):
        """Theme `key` (and `language`), hooks installed the way run_gui does."""
        theme.set_active(key, theme.ACCENT_DEFAULT)
        self.addCleanup(theme.set_active, "light", theme.ACCENT_DEFAULT)
        look_icons.install()
        self.addCleanup(look_icons._restore)
        i18n.set_active(language)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        i18n.install_text_hook()
        self.addCleanup(i18n._restore_text_hook)

    def keep(self, widget):
        self.addCleanup(reap_widget, widget)
        return widget


class ClassicKeepsTheEmoji(_Base):

    def test_light_and_dark_install_nothing(self):
        for key in ("light", "dark"):
            with self.subTest(theme=key):
                self.use(key)
                btn = self.keep(QPushButton("💾  Save"))
                self.assertEqual(btn.text(), "💾  Save")
                self.assertTrue(btn.icon().isNull())
                self.assertFalse(look_icons._installed)


class ALookWearsIcons(_Base):

    def setUp(self):
        self.use(LOOK)

    def test_a_button_loses_the_emoji_and_gains_the_icon(self):
        for cls in (QPushButton, QCheckBox):
            with self.subTest(cls=cls.__name__):
                btn = self.keep(cls("💾  Save"))
                self.assertEqual(btn.text(), "Save")
                self.assertFalse(btn.icon().isNull())
                self.assertEqual(btn.property("lookGlyph"), "💾")

    def test_set_text_and_a_glyph_only_caption(self):
        btn = self.keep(QToolButton())
        btn.setText("▾")
        self.assertEqual(btn.text(), "")
        self.assertFalse(btn.icon().isNull())
        btn.setText("▸")
        self.assertEqual(btn.property("lookGlyph"), "▸")

    def test_plain_text_keeps_the_icon(self):
        # The toolbar compacts a button by setText("") and grows it back with
        # its full caption; the icon must survive both.
        btn = self.keep(QPushButton("⚙  Settings"))
        btn.setText("")
        self.assertFalse(btn.icon().isNull())
        btn.setText("Settings")
        self.assertFalse(btn.icon().isNull())

    def test_variation_selector_and_unmapped_glyphs(self):
        btn = self.keep(QPushButton("⚠️ Careful"))
        self.assertEqual(btn.text(), "Careful")
        for text in ("• bullet", "🟧 legend", "Plain"):
            with self.subTest(text=text):
                self.assertEqual(self.keep(QPushButton(text)).text(), text)

    def test_menu_entries_and_submenus(self):
        menu = self.keep(QMenu())
        act = menu.addAction("🧹  Empty this playlist")
        self.assertEqual(act.text(), "Empty this playlist")
        self.assertFalse(act.icon().isNull())
        sub = menu.addMenu("📂  Open")
        self.assertEqual(sub.title(), "Open")
        self.assertFalse(sub.icon().isNull())
        own = QAction("🗑  Delete", menu)
        self.assertEqual(own.text(), "Delete")

    def test_tabs(self):
        tabs = self.keep(QTabWidget())
        i = tabs.addTab(QWidget(), "🎨  Look")
        self.assertEqual(tabs.tabText(i), "Look")
        self.assertFalse(tabs.tabIcon(i).isNull())
        tabs.setTabText(i, "📚  Library")
        self.assertEqual(tabs.tabText(i), "Library")

    def test_a_plain_label_gets_an_inline_image(self):
        label = self.keep(QLabel("⚠  Watch <out>\nnext line"))
        self.assertEqual(label.textFormat(), Qt.TextFormat.RichText)
        self.assertIn("<img", label.text())
        self.assertIn("Watch &lt;out&gt;<br>next line", label.text())
    def test_a_rich_label_swaps_its_leading_glyph(self):
        rich = self.keep(QLabel("<b>🎨 Theme</b> — pick one"))
        self.assertIn("<img", rich.text())
        self.assertNotIn("🎨", rich.text())
        self.assertTrue(rich.text().startswith("<b><img"))
        self.assertTrue(rich.text().endswith("Theme</b> — pick one"))
        other = self.keep(QLabel("<b>Plain</b> 🎨 later"))
        self.assertEqual(other.text(), "<b>Plain</b> 🎨 later")
        plain = QLabel()
        self.keep(plain).setTextFormat(Qt.TextFormat.PlainText)
        plain.setText("🎨 <literal>")
        self.assertEqual(plain.text(), "🎨 <literal>")

    def test_a_group_box_title_only_loses_the_glyph(self):
        self.assertEqual(self.keep(QGroupBox("🎛  Mixer")).title(), "Mixer")

    def test_the_counted_toolbar_icon_draws_the_svg(self):
        icons.counted_emoji.cache_clear()
        self.addCleanup(icons.counted_emoji.cache_clear)
        self.assertFalse(icons.counted_emoji("⧉", 2, 16).isNull())


class TheTableHolds(unittest.TestCase):

    def test_every_icon_exists(self):
        names = set(icons.names())
        for glyph, (name, tone) in look_icons.GLYPHS.items():
            with self.subTest(glyph=glyph):
                self.assertIn(name, names)

    def test_meaning_colours_read_on_every_look(self):
        for look in looks.LOOKS.values():
            for tone, pair in look_icons._SEMANTIC.items():
                colour = pair[1 if look.dark else 0]
                with self.subTest(look=look.key, tone=tone):
                    self.assertGreaterEqual(
                        theme.contrast_ratio(colour, look.tokens.base), 3.0)


class GermanIsTranslatedFirst(_Base):

    def test_the_catalog_key_with_its_emoji_still_matches(self):
        self.use(LOOK, "de")
        btn = self.keep(QPushButton("⚙  Settings"))
        self.assertEqual(btn.text(), "Einstellungen")
        self.assertFalse(btn.icon().isNull())
        act = self.keep(QMenu()).addAction("🧹  Empty this playlist")
        self.assertEqual(act.text(), "Diese Playlist leeren")


class TheWindowsBuild(_Base):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        super().setUpClass()
        cls._qs_dir = tempfile.mkdtemp(prefix="dp_look_icons_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def test_main_window_and_settings(self):
        from gui.dialogs import SettingsDialog

        theme.install_stylesheet_hook()
        self.use(LOOK, "de")
        win = self.gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        win._on_table_focused(win._tableA)
        # The fold entry in a deck's menu keeps its arrow, now an icon.
        self.assertIn(win.deck(win._tableA).fold_btn.property("lookGlyph"),
                      ("▾", "▴", "▸", "◂"))
        dlg = self.keep(SettingsDialog({}))
        self.assertGreater(dlg.findChildren(QTabWidget)[0].count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
