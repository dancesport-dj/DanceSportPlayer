#!/usr/bin/env python3
"""The 🎨 looks: every one complete, readable, and wired into the theme.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_looks -v

A look is data (shared/looks.py), so most of what can go wrong is a look that
was added half-way: no preview picture, a stylesheet that does not build, a
caption without its German. The readability floors are the point of the modern
group and are held for every look where they are cheap to meet.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_looks_"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from planner import lang_de  # noqa: E402
from shared import looks, theme  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class LookDataTest(unittest.TestCase):

    def test_the_three_groups_are_all_there(self):
        groups = {look.group for look in looks.LOOKS.values()}
        self.assertEqual(groups, {g for g, _label in looks.GROUPS})
        self.assertGreaterEqual(
            sum(look.group == "modern" for look in looks.LOOKS.values()), 6)

    def test_every_theme_has_a_preview_picture(self):
        for key in theme._THEMES:
            with self.subTest(key=key):
                self.assertTrue(looks.preview_path(key).is_file(),
                                f"run: py -m tools.theme_previews {key}")

    def test_every_look_has_a_known_button_style(self):
        for look in looks.LOOKS.values():
            with self.subTest(look=look.key):
                self.assertIn(look.buttons, looks.BUTTON_STYLES)

    # Names that are the same word in German. The catalog may not carry an
    # entry translating to itself (test_i18n), so they are exempt here.
    _SAME_IN_GERMAN = {"Carbon", "Neon", "Studio", "Aurora"}

    def test_every_caption_and_blurb_has_its_german(self):
        texts = [label for _g, label in looks.GROUPS]
        for look in looks.LOOKS.values():
            texts += [look.caption, look.blurb]
        for text in texts:
            if text in self._SAME_IN_GERMAN:
                continue
            with self.subTest(text=text):
                self.assertIn(text, lang_de.CATALOG)

    def test_body_text_reads_at_aaa_on_every_look(self):
        for look in looks.LOOKS.values():
            t = look.tokens
            with self.subTest(look=look.key):
                self.assertGreaterEqual(theme.contrast_ratio(t.text, t.base), 7.0)
                self.assertGreaterEqual(theme.contrast_ratio(t.text, t.alt_base), 7.0)
                self.assertGreaterEqual(
                    theme.contrast_ratio(t.on_selection, t.selection), 4.5)
                self.assertGreaterEqual(
                    theme.contrast_ratio(t.on_accent, t.accent), 3.0)

    def test_the_modern_looks_keep_every_text_at_aa(self):
        """Dim text, text on the accent and the accent as text included."""
        for look in looks.LOOKS.values():
            if look.group != "modern":
                continue
            t = look.tokens
            with self.subTest(look=look.key):
                self.assertGreaterEqual(theme.contrast_ratio(t.text_dim, t.base), 4.5)
                self.assertGreaterEqual(theme.contrast_ratio(t.text_dim, t.window), 4.5)
                self.assertGreaterEqual(theme.contrast_ratio(t.on_accent, t.accent), 4.5)
                self.assertGreaterEqual(theme.contrast_ratio(t.accent_ink, t.base), 4.5)


class LookStyleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_stylesheet_builds_and_names_its_colours(self):
        for look in looks.LOOKS.values():
            with self.subTest(look=look.key):
                sheet = looks.stylesheet(look)
                self.assertIn("QPushButton", sheet)
                self.assertIn(look.tokens.window, sheet)
                self.assertNotIn("{t.", sheet)

    def test_every_look_has_its_parts_marked_final(self):
        for look in looks.LOOKS.values():
            parts = looks.parts(look)
            with self.subTest(look=look.key):
                self.assertEqual(set(parts), {"deck_idle", "deck_active", "mode_btn"})
                for sheet in parts.values():
                    self.assertTrue(sheet.startswith(looks.LOOK_MARK))


class ActiveLookTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)

    def test_every_look_is_a_theme(self):
        for key in looks.LOOKS:
            with self.subTest(key=key):
                self.assertEqual(theme.theme_of({"theme": key}), key)

    def test_a_look_sets_dark_and_brings_its_own_accent(self):
        for look in looks.LOOKS.values():
            with self.subTest(look=look.key):
                # A picked accent is for the classic pair; a look ignores it.
                theme.set_active(look.key, "#b8006e")
                self.assertIs(theme.active_look(), look)
                self.assertEqual(theme.is_dark(), look.dark)
                self.assertEqual(theme.active_accent(), look.tokens.accent.lower())

    def test_the_classic_themes_have_no_look_and_no_parts(self):
        for key in ("light", "dark"):
            theme.set_active(key, theme.ACCENT_DEFAULT)
            self.assertIsNone(theme.active_look())
            self.assertEqual(theme.look_parts(), {})

    def test_the_transform_leaves_a_looks_parts_alone(self):
        theme.set_active("midnight", theme.ACCENT_DEFAULT)
        for sheet in theme.look_parts().values():
            self.assertEqual(theme.qss(sheet), sheet)
        # ...while an ordinary inline sheet is still shaded for the dark look.
        self.assertNotEqual(theme.qss("background:#ffffff;"), "background:#ffffff;")

    def test_a_deck_strip_set_through_the_hook_compares_equal(self):
        """main_decks tells the focused deck by comparing the strip's sheet
        with _DECK_HDR_ACTIVE, so the hook must store a part unchanged."""
        theme.install_stylesheet_hook()
        theme.set_active("console", theme.ACCENT_DEFAULT)
        active = theme.look_parts()["deck_active"]
        label = QLabel()
        self.addCleanup(reap_widget, label)
        label.setStyleSheet(active)
        self.assertEqual(label.styleSheet(), active)

    def test_apply_app_sets_the_looks_stylesheet(self):
        theme.install_stylesheet_hook()
        app = QApplication.instance()
        before = app.styleSheet()
        self.addCleanup(theme._raw_app_set_stylesheet, app, before)
        self.addCleanup(app.setFont, app.font())
        self.addCleanup(app.setPalette, app.palette())
        theme.set_active("paper", theme.ACCENT_DEFAULT)
        theme.apply_app(app)
        self.assertIn(looks.LOOKS["paper"].tokens.window, app.styleSheet())

    def test_the_rounds_parse_button_is_never_clipped(self):
        """It sat at a fixed 55 px: enough for "Parse" in the classic sheet,
        not for "Einlesen" once a look pads its buttons."""
        from PySide6.QtWidgets import QPushButton

        from planner import i18n
        from gui.config_panel import ConfigPanel

        theme.install_stylesheet_hook()
        app = QApplication.instance()
        self.addCleanup(theme._raw_app_set_stylesheet, app, app.styleSheet())
        self.addCleanup(app.setFont, app.font())
        self.addCleanup(app.setPalette, app.palette())
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)
        i18n.set_active("de")
        i18n.install_text_hook()
        for key in ("light", "console", "win11_light"):
            with self.subTest(key=key):
                theme.set_active(key, theme.ACCENT_DEFAULT)
                theme.apply_app(app)
                panel = ConfigPanel()
                self.addCleanup(reap_widget, panel)
                btn = next(b for b in panel.findChildren(QPushButton)
                           if b.text() == "Einlesen")
                self.assertGreaterEqual(btn.width(), btn.sizeHint().width())


if __name__ == "__main__":
    unittest.main(verbosity=2)
