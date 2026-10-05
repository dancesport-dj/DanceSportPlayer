#!/usr/bin/env python3
"""The theme reaching the things a stylesheet cannot: icons and the ▶ player.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_theme_icons -v

Every other colour in the app is set through a stylesheet, and the hook in
shared/theme.py rewrites those. An icon is different: its colour ends up in the
pixels, so `color:` never applies to it and the hook never sees it. That is why
shared/icons.py shades inside the painter — and why these tests look at the
rendered pixels rather than at a string. A test that only checked `shade()`
would pass just as happily with the painting left unthemed.

The ▶ player panel is the other half: it is the one surface built out of the
accent rather than merely highlighted with it, so a picked accent has to carry
the whole panel, while the button colours that MEAN something keep their hue.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_themeico_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared import icons, theme  # noqa: E402

MAGENTA = "#b8006e"

# The ▶ player's icon colours, split by what they are. shared/theme.py recolours
# the accent's own family and spares anything whose colour is its meaning.
PLAYER_ACCENT = {
    "_OVERLAY_INK": "#1565c0",   # the overlay's ink, the accent itself
    "_CARD_INK": "#cfe0f5",      # ink on the dark card
    "_CARD_DIM": "#8fa3c4",      # the fader's own small marks
}
PLAYER_MEANING = {
    "_CARD_FADE": "#d8a0a0",     # fade this song out
    "_CARD_EXTEND": "#7fd4a0",   # give the pause more time
    "_CARD_CUE": "#f0c674",      # back to 0:00
    "_CARD_PANIC": "#e58080",    # fade to silence and hold
    "_CARD_GAIN": "#d8b35c",     # the R128 readout
}
# The panel's own surfaces, set through stylesheets in player/player.py.
PLAYER_SURFACES = ("#1d2330", "#10141d", "#2a3346", "#3a4a68")


def clear_icon_caches():
    """icons.* are cached per (name, size, colour), not per theme.

    The app picks its theme up before the first widget exists and never changes
    it while running, so the cache is right there. A test that switches themes
    inside one process is the only thing that can out-run it."""
    for fn in (icons.pixmap, icons.icon, icons.html,
               icons.letter_pixmap, icons.counted_emoji):
        fn.cache_clear()


def ink_of(pm):
    """The mean brightness of a pixmap's opaque pixels, 0–255.

    The icons are one flat colour on transparency, so this is that colour's
    brightness — and comparing it is how we know the painter, not just the
    colour table, followed the theme."""
    img = pm.toImage()
    total = n = 0
    for y in range(img.height()):
        for x in range(img.width()):
            px = img.pixelColor(x, y)
            if px.alpha() > 200:
                total += (px.red() + px.green() + px.blue()) / 3
                n += 1
    assert n, "the icon came out fully transparent"
    return total / n


class IconThemeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        clear_icon_caches()

    def tearDown(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        clear_icon_caches()

    # ── the painted pixels follow the theme ──────────────────────────────────

    def test_a_dark_icon_is_repainted_light_for_dark_mode(self):
        """The near-black default ink would be invisible on a dark ground."""
        theme.set_active("light", theme.ACCENT_DEFAULT)
        light = ink_of(icons.pixmap("play", 32))
        clear_icon_caches()
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        dark = ink_of(icons.pixmap("play", 32))
        self.assertGreater(dark, light + 40,
                           "the icon was not repainted for dark mode")

    def test_light_mode_paints_exactly_what_it_always_did(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        themed = icons.pixmap("play", 32).toImage()
        raw = icons.pixmap("play", 32, icons.INK).toImage()
        self.assertEqual(themed, raw)

    def test_the_default_colour_argument_is_shaded_too(self):
        """`color=INK` was bound when the function was defined.

        Rebinding icons.INK could never reach it, which is the whole reason the
        shading happens in the painter — so a call that passes no colour at all
        is the case worth pinning."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        defaulted = ink_of(icons.pixmap("play", 32))
        clear_icon_caches()
        explicit = ink_of(icons.pixmap("play", 32, icons.INK))
        self.assertEqual(defaulted, explicit)

    def test_an_accent_icon_follows_the_picked_accent(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        blue = icons.pixmap("play", 32, icons.ACCENT).toImage()
        clear_icon_caches()
        theme.set_active("light", MAGENTA)
        picked = icons.pixmap("play", 32, icons.ACCENT).toImage()
        self.assertNotEqual(blue, picked)

    def test_a_meaning_icon_keeps_its_colour_under_a_picked_accent(self):
        """A red erase stays red however the accent was set."""
        theme.set_active("light", theme.ACCENT_DEFAULT)
        before = icons.pixmap("trash", 32, icons.DANGER).toImage()
        clear_icon_caches()
        theme.set_active("light", MAGENTA)
        after = icons.pixmap("trash", 32, icons.DANGER).toImage()
        self.assertEqual(before, after)

    # ── the badge discs stay readable ────────────────────────────────────────

    def test_the_badge_letter_flips_when_the_disc_turns_light(self):
        """White on a pale accent is the bug this guards."""
        self.assertEqual(icons._disc_ink("#1565c0"), "#ffffff")
        self.assertEqual(icons._disc_ink("#60a5fd"), "#141414")

    def test_every_badge_letter_clears_aa_on_its_disc(self):
        for th, accent in (("light", theme.ACCENT_DEFAULT),
                           ("dark", theme.ACCENT_DEFAULT),
                           ("light", MAGENTA), ("dark", MAGENTA)):
            theme.set_active(th, accent)
            disc = theme.shade(icons.ACCENT, "ink")
            ratio = theme.contrast_ratio(icons._disc_ink(disc), disc)
            self.assertGreaterEqual(round(ratio, 2), 4.5,
                                    f"{th}/{accent}: letter on {disc} = {ratio:.2f}")

    def test_the_deck_badge_is_painted_in_the_accent(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        blue = icons.letter_pixmap("A", 32).toImage()
        clear_icon_caches()
        theme.set_active("light", MAGENTA)
        picked = icons.letter_pixmap("A", 32).toImage()
        self.assertNotEqual(blue, picked)

    # ── the ▶ player panel ───────────────────────────────────────────────────

    def test_the_player_accent_colours_follow_a_picked_accent(self):
        theme.set_active("light", MAGENTA)
        for name, color in PLAYER_ACCENT.items():
            self.assertNotEqual(theme.shade(color, "ink"), color,
                                f"{name} ignored the accent")

    def test_the_player_meaning_colours_do_not(self):
        theme.set_active("light", MAGENTA)
        for name, color in PLAYER_MEANING.items():
            self.assertEqual(theme.shade(color, "ink"), color,
                             f"{name} lost the hue that is its meaning")

    def test_the_panel_itself_follows_the_accent(self):
        """Not just the marks on it — the dark ground is accent-built too."""
        theme.set_active("light", MAGENTA)
        for surface in PLAYER_SURFACES:
            self.assertNotEqual(theme.shade(surface, "ground"), surface,
                                f"{surface} stayed blue under a magenta accent")

    def test_the_panel_is_left_alone_by_dark_mode(self):
        """It was already dark; dark mode must not flip it into mush."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        for surface in PLAYER_SURFACES:
            self.assertEqual(theme.shade(surface, "ground"), surface)

    def test_the_hovered_button_stays_visibly_lighter_than_the_one_under_it(self):
        """The regression that made `_ALREADY_DARK` a constant of its own.

        The hovered player button sits at Oklab L 0.41 — above the cap grounds
        are derived down to, but already perfectly dark. Squeezing it under
        that cap left it a fifth of a step from the button beneath it, so
        hovering did almost nothing. Measured in Oklab because relative
        luminance is compressed to uselessness this near black."""
        def lightness(color, role="ground"):
            return theme.to_oklab(theme.hex_to_rgb(theme.shade(color, role)))[0]

        theme.set_active("light", theme.ACCENT_DEFAULT)
        was = lightness("#3a4a68") - lightness("#2a3346")
        for th, accent in (("dark", theme.ACCENT_DEFAULT),
                           ("light", MAGENTA), ("dark", MAGENTA)):
            theme.set_active(th, accent)
            now = lightness("#3a4a68") - lightness("#2a3346")
            self.assertGreaterEqual(
                now, was * 0.9,
                f"{th}/{accent}: hover separation fell from {was:.4f} to {now:.4f}")

    # ── widgets that paint their own colours ─────────────────────────────────

    def test_the_painted_widgets_follow_the_theme(self):
        """A QPainter is the third thing a stylesheet cannot reach.

        `sync_shared_colors` re-shades these QColors in place at start-up. It
        had no test at all, which is how the Nb. gutter stayed a white stripe
        down a black table and the desk switches stayed a column of bright
        pills: both are painted, not styled.

        The colours are mutated IN PLACE and the transform does not invert, so
        every value is snapshotted and put back."""
        from gui import playlist_table
        from player import play_mode_panel

        painted = ((playlist_table._NumberHeader, "_BG", "ground"),
                   (playlist_table._NumberHeader, "_FG", "ink"),
                   (playlist_table._NumberHeader, "_LINE", "line"),
                   (play_mode_panel._Toggle, "_OFF_TRACK", "ground"),
                   (play_mode_panel._Toggle, "_DISABLED_TEXT", "ink"))
        saved = [(getattr(owner, name), getattr(owner, name).rgba())
                 for owner, name, _role in painted]
        try:
            theme.set_active("dark", theme.ACCENT_DEFAULT)
            theme.sync_shared_colors()
            gutter = playlist_table._NumberHeader._BG
            self.assertLess(gutter.lightness(), 90,
                            f"the Nb. gutter stayed light ({gutter.name()})")
            self.assertGreaterEqual(
                round(theme.contrast_ratio(
                    playlist_table._NumberHeader._FG.name(), gutter.name()), 2),
                4.5, "the row numbers are not readable on their own gutter")
            track = play_mode_panel._Toggle._OFF_TRACK
            self.assertLess(track.lightness(), 90,
                            f"the off switch stayed a bright pill ({track.name()})")
            self.assertGreaterEqual(
                round(theme.contrast_ratio(
                    play_mode_panel._Toggle._KNOB.name(), track.name()), 2),
                3.0, "the knob no longer stands out on its track")
        finally:
            for color, rgba in saved:
                color.setRgba(rgba)

    def test_the_gap_report_marks_darken_with_the_rest_of_the_dialog(self):
        """📊 Library gaps marks thin spots by painting the row's background.

        Those two QColors are CLASS attributes on the dialog rather than
        module-level constants, which is the only reason they were missed —
        `_SHARED_COLORS` resolves a dotted path perfectly well. Unregistered,
        a pastel red row stayed a bright stripe across a dark table."""
        from gui import dialogs

        marks = ((dialogs.LibraryGapsDialog, "_C_BAD"),
                 (dialogs.LibraryGapsDialog, "_C_WARN"))
        saved = [(getattr(owner, name), getattr(owner, name).rgba())
                 for owner, name in marks]
        try:
            theme.set_active("dark", theme.ACCENT_DEFAULT)
            theme.sync_shared_colors()
            for owner, name in marks:
                color = getattr(owner, name)
                self.assertLess(
                    color.lightness(), 128,
                    f"{name} stayed a bright stripe ({color.name()})")
                # It still has to read as a WARNING, not as an ordinary row.
                self.assertGreaterEqual(
                    round(theme.contrast_ratio("#e8e8e8", color.name()), 2),
                    4.5, f"{name} is no longer readable under the row text")
        finally:
            for color, rgba in saved:
                color.setRgba(rgba)

    def test_the_on_switch_keeps_the_green_that_means_on(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        from player import play_mode_panel
        green = play_mode_panel._Toggle._ON_TRACK.name()
        self.assertEqual(theme.shade(green, "ground"), green)

    def test_the_player_ink_still_reads_on_the_panel_it_was_recoloured_with(self):
        theme.set_active("dark", MAGENTA)
        ground = theme.shade("#1d2330", "ground")
        for name, color in PLAYER_ACCENT.items():
            if name == "_OVERLAY_INK":
                continue          # the overlay is its own light card
            ratio = theme.contrast_ratio(theme.shade(color, "ink"), ground)
            self.assertGreaterEqual(round(ratio, 2), 4.5,
                                    f"{name} on {ground} = {ratio:.2f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
