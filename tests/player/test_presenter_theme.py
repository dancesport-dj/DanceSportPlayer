"""🎨 The presenter screen's palettes: that every coloured widget really
follows a theme switch, and that an unknown theme name costs nothing.
"""
import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication, state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_prestheme_"))

from player.presenter_theme import (  # noqa: E402
    DEFAULT_KEY,
    THEMES,
    theme_choices,
    theme_for,
)
from tests.qt_test_support import reap_widget   # noqa: E402


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_STATE = ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
          [("TG", "Zweiter")], ("", ""))


def _presenter():
    from player.presenter import PresenterWindow
    return PresenterWindow(lambda: _STATE)


class ThemeDataTest(unittest.TestCase):
    """The theme table itself."""

    def test_default_is_the_black_hall_screen(self):
        t = theme_for(DEFAULT_KEY)
        self.assertEqual(t.bg, "#000000")
        self.assertEqual(t.hero, "#ffffff")

    def test_light_is_light(self):
        """A lit room, not a dark hall: SOFT ground, DARK text, GOLD accent —
        and no mark, the page stands under its heading alone."""
        t = theme_for("light")
        self.assertEqual(t.key, "light")
        self.assertEqual(t.label, "Light (gold)")
        self.assertEqual(t.logo, ())
        self.assertNotEqual(t.bg, THEMES[DEFAULT_KEY].bg)
        self.assertEqual(t.bg, "#f2f0e6")
        self.assertEqual(t.up, "#c9a84c")
        self.assertIn("Cantarell", t.hero_families)
        self.assertGreater(len(t.hero_families), 1,
                           "Cantarell is per-user — a theme needs a fallback")

    def test_unknown_name_falls_back(self):
        """A settings file naming a theme that no longer exists must not cost
        the screen its colours."""
        self.assertIs(theme_for("gibt-es-nicht"), THEMES[DEFAULT_KEY])
        self.assertIs(theme_for(None), THEMES[DEFAULT_KEY])

    def test_every_theme_is_offered(self):
        keys = [k for k, _label in theme_choices()]
        self.assertEqual(keys, list(THEMES))


class PresenterThemeTest(unittest.TestCase):
    """What a switch does to the built screen."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def test_starts_on_the_default_theme(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        self.assertEqual(w.theme_key(), DEFAULT_KEY)
        self.assertIn("#000000", w.styleSheet())

    def test_switch_repaints_every_registered_widget(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_theme("light")
        t = theme_for("light")
        self.assertEqual(w.theme_key(), "light")
        self.assertIn(t.bg, w.styleSheet())
        # The lines, the headers and the hairlines all moved with it.
        self.assertIn(t.hero, w.dance_lbl.styleSheet())
        self.assertIn(t.sub, w.title_lbl.styleSheet())
        self.assertIn(t.up, w.next_lbls[0].styleSheet())
        self.assertIn(t.past, w.last_sub_lbl.styleSheet())
        self.assertIn(t.sub, w.next_hdr.styleSheet())
        self.assertIn(t.div, w.hint_lbl.styleSheet())
        # …and the hero wears the theme's own face. Asserted on what was *set*,
        # not on what resolved: under QT_QPA_PLATFORM=offscreen Qt sees no
        # system fonts at all, so `family()` would answer for the substitute.
        self.assertEqual(w.dance_lbl.font().families(), list(t.hero_families))

    def test_switch_keeps_the_weight_css(self):
        """Re-styling must not drop the CSS the line was built with."""
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_theme("light")
        self.assertIn("font-weight:800", w.dance_lbl.styleSheet())
        self.assertIn("monospace", w.left_lbl.styleSheet())

    def test_blink_uses_the_theme_red(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_theme("light")
        t = theme_for("light")
        w._blink_on = False
        w._blink_left()          # → on, so the end colour
        self.assertIn(t.end, w.left_lbl.styleSheet())
        w._blink_left()          # → off again
        self.assertIn(t.left, w.left_lbl.styleSheet())

    def test_switching_back_restores_the_default(self):
        w = _presenter()
        self.addCleanup(reap_widget, w)
        w.set_theme("light")
        w.set_theme(DEFAULT_KEY)
        self.assertIn("#000000", w.styleSheet())
        self.assertEqual(w.dance_lbl.font().family(), w._base_family)


if __name__ == "__main__":
    unittest.main()
