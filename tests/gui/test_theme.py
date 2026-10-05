#!/usr/bin/env python3
"""Tests for the light/dark theme transform and the accent colour.

Run:  py -m unittest tests.gui.test_theme -v

The dark theme is derived from the light one rather than hand-authored, so what
needs testing is not "is this colour right" but the two promises the derivation
makes:

* **Light mode changes nothing.** The transform is the identity unless the theme
  is dark or the accent was changed, so a user who touches neither keeps exactly
  today's look.
* **Every ink clears WCAG AA on every ground.** Grounds are capped at the
  lightness inks were lifted against, which makes that an invariant and not a
  hope. The pairs below are real ones, pulled out of gui/ and player/.

The third promise is idempotence: the ▶ player panel is already dark and must
come through untouched instead of being flipped into mush.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_theme_"))

from shared import theme  # noqa: E402

# (ink, ground, what it is) — every pair really used by the app.
REAL_PAIRS = [
    ("#141414", "#ffffff", "body text on a white row"),
    ("#666666", "#ffffff", "dim hint text"),
    ("#777777", "#ffffff", "secondary hint"),
    ("#888888", "#ffffff", "tertiary hint"),
    ("#aaaaaa", "#ffffff", "album gray — faint, but text"),
    ("#b46e00", "#ffffff", "popularity amber"),
    ("#1e6ec8", "#ffffff", "new-track blue"),
    ("#c81e1e", "#ffffff", "warning red"),
    ("#147d32", "#ffffff", "similar green"),
    ("#d77800", "#ffffff", "length-warning orange"),
    ("#e07b00", "#ffffff", "path-warning orange"),
    ("#1e3278", "#c8d2f0", "round header: navy on blue-gray"),
    ("#1e5a1e", "#d2ebd2", "dance header: green on soft green"),
    ("#2c3e60", "#f3f6fc", "overlay title on the light card"),
    ("#1565c0", "#f3f6fc", "accent on the light card"),
    ("#555555", "#f0f2f5", "config-panel label on the window"),
    ("#7a5b00", "#fff8e6", "amber note on cream"),
    ("#b3261e", "#ffffff", "duplicate-dialog red"),
    ("#1b7f3b", "#ffffff", "duplicate-dialog green"),
    ("#2a7a45", "#ffffff", "path-ok green"),
    ("#6b727c", "#f2f4f7", "AI dialog muted text"),
]

# Colours used as a FILL — a figure sitting on the page, not a pane behind text:
# a filled slider, the selection band, a badge, an active header.
FILLS = [
    ("#1565c0", "the ▶ player's volume and tempo bars"),
    ("#2d6cdf", "the active deck header"),
    ("#4682d2", "the selection band (QPalette.Highlight)"),
    ("#c81e1e", "a warning banner"),
    ("#147d32", "a proven-track mark"),
    ("#5f9e72", "the desk toggle in its on position"),
]
# Deliberately NOT here: icons.GOLD #d99e0b and its siblings. They are inks —
# the colour of a drawn glyph — and never sit behind anything. A filled disc
# picks its own letter colour in icons._disc_ink rather than assuming white.

# Colours the ▶ player panel already uses — it is dark before the theme is.
ALREADY_DARK = [
    ("#cfe0f5", "#2a3346", "player ink on a player button"),
    ("#8fa3c4", "#1d2330", "player dim text on the player ground"),
    ("#eef3fb", "#1d2330", "player title"),
]


class ThemeTransformTest(unittest.TestCase):

    def tearDown(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)

    # ── light mode is the identity ────────────────────────────────────────────

    def test_light_mode_leaves_stylesheets_alone(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        for sheet in ("color:#666; background:#ffffff;",
                      "#BigPlayer { background:#1d2330; border:2px solid #10141d; }",
                      "QSlider::sub-page:horizontal { background:#4a82d2; }"):
            self.assertEqual(theme.qss(sheet), sheet)

    def test_light_mode_leaves_single_colours_alone(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        for color, _ground, _what in REAL_PAIRS:
            self.assertEqual(theme.shade(color, "ink"), color)

    # ── the AA invariant ─────────────────────────────────────────────────────

    def test_every_real_pair_clears_aa_in_dark_mode(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        bad = []
        for ink, ground, what in REAL_PAIRS:
            dark_ink = theme.shade(ink, "ink")
            dark_ground = theme.shade(ground, "ground")
            ratio = theme.contrast_ratio(dark_ink, dark_ground)
            if ratio < 4.5:
                bad.append(f"{what}: {dark_ink} on {dark_ground} = {ratio:.2f}")
        self.assertEqual(bad, [], "dark mode dropped below AA:\n  " + "\n  ".join(bad))

    def test_no_ground_is_lighter_than_the_ink_reference(self):
        """The invariant the AA promise rests on."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        cap = theme.ground_cap() + theme.ground_tolerance()
        for _ink, ground, what in REAL_PAIRS:
            L = theme.to_oklab(theme.hex_to_rgb(theme.shade(ground, "ground")))[0]
            self.assertLessEqual(round(L, 6), cap, f"{what}: ground too light ({L:.3f})")

    def test_inks_are_readable_on_the_lightest_possible_ground(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        reference = theme.ink_reference()
        for ink, _ground, what in REAL_PAIRS:
            ratio = theme.contrast_ratio(theme.shade(ink, "ink"), reference)
            self.assertGreaterEqual(round(ratio, 2), 4.5, f"{what} on {reference}")

    # ── it leaves what is already right alone ────────────────────────────────

    def test_already_dark_player_colours_survive(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        for ink, ground, what in ALREADY_DARK:
            self.assertEqual(theme.shade(ground, "ground"), ground,
                             f"{what}: dark ground was flipped")
            self.assertGreaterEqual(
                theme.contrast_ratio(theme.shade(ink, "ink"),
                                     theme.shade(ground, "ground")), 4.5, what)

    def test_a_saturated_colour_behind_something_is_a_fill_not_a_ground(self):
        """`background:#1565c0` is a filled slider, not a pale pane.

        The ground rule derives a light pane DOWN to the cap, which is right
        for a white card and wrong for a fill: the ▶ player's volume bar came
        out #003281 — 1.33:1 against the card it sits on, where the light theme
        had 2.74:1. A saturated colour behind something is a figure, and keeps
        the lightness it was designed with."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        for fill, what in FILLS:
            self.assertEqual(theme.shade(fill, "ground"), fill,
                             f"{what}: a fill was derived down like a pane")

    def test_a_fill_still_reads_against_the_page_and_carries_its_text(self):
        """Both halves, because brightening one costs the other.

        The text floor is 3.0, not AA's 4.5, and deliberately so: white on the
        selection band `#4682d2` is 3.9 in the LIGHT theme already. Leaving a
        fill alone inherits that number rather than introducing it, and
        asserting 4.5 here would be asserting something the app has never
        done."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        page = theme.shade("#ffffff", "ground")
        for fill, what in FILLS:
            shaded = theme.shade(fill, "ground")
            self.assertGreaterEqual(
                round(theme.contrast_ratio(shaded, page), 2), 2.5,
                f"{what}: {shaded} vanishes into the page {page}")
            self.assertGreaterEqual(
                round(theme.contrast_ratio("#ffffff", shaded), 2), 3.0,
                f"{what}: white on {shaded} is unreadable")

    def test_a_pale_pane_is_still_derived_down(self):
        """The rule must not let the round/dance header grounds through.

        They are the closest pale panes to the line — measured chroma 0.043,
        against 0.093 for the least saturated real fill."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        for pane, what in (("#c8d2f0", "round header"),
                           ("#d2ebd2", "dance header"),
                           ("#fff8e6", "amber note"),
                           ("#ffffff", "a white row")):
            self.assertNotEqual(theme.shade(pane, "ground"), pane,
                                f"{what}: a pale pane stayed light in dark mode")

    def test_transform_is_idempotent(self):
        """Shading an already-shaded colour must not drift further."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        for ink, ground, what in REAL_PAIRS:
            once = theme.shade(ink, "ink")
            self.assertEqual(theme.shade(once, "ink"), once, f"ink {what}")
            once_bg = theme.shade(ground, "ground")
            self.assertEqual(theme.shade(once_bg, "ground"), once_bg, f"ground {what}")

    # ── the rewriter ─────────────────────────────────────────────────────────

    def test_role_comes_from_the_property(self):
        """The same grey is light as text and dark as a border."""
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        as_text = theme.qss("color:#aaaaaa;")
        as_border = theme.qss("border:1px solid #aaaaaa;")
        self.assertNotEqual(as_text, as_border)
        text_L = theme.to_oklab(theme.hex_to_rgb(as_text.split(":")[1].strip(" ;")))[0]
        self.assertGreater(text_L, theme.ground_cap(), "faint text must go light")

    def test_id_selectors_are_not_mistaken_for_colours(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        out = theme.qss("#BigPlayer { background:#ffffff; }")
        self.assertIn("#BigPlayer", out)
        self.assertNotIn("#ffffff", out)

    def test_gradient_stops_are_rewritten_with_the_property_role(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        out = theme.qss(
            "background:qlineargradient(x1:0, y1:0, stop:0 #ffffff, stop:1 #f0f2f5);")
        self.assertNotIn("#ffffff", out)
        self.assertNotIn("#f0f2f5", out)
        self.assertIn("qlineargradient", out)

    def test_three_digit_hex_is_handled(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        self.assertNotIn("#666", theme.qss("color:#666;"))

    def test_non_colour_text_is_untouched(self):
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        sheet = "font-size:11px; font-family:Consolas,monospace; margin-left:2px;"
        self.assertEqual(theme.qss(sheet), sheet)

    # ── the accent ───────────────────────────────────────────────────────────

    def test_accent_recolours_the_family_and_spares_meaning(self):
        theme.set_active("light", "#b8006e")          # a magenta accent
        self.assertNotEqual(theme.shade(theme.ACCENT_DEFAULT, "ink"),
                            theme.ACCENT_DEFAULT)
        for keep in ("#c81e1e", "#147d32", "#b46e00"):
            self.assertEqual(theme.shade(keep, "ink"), keep,
                             "a warning/proven/popularity colour must keep its hue")

    def test_accent_family_keeps_its_light_dark_structure(self):
        """The hover tint must stay lighter than the accent it belongs to."""
        theme.set_active("light", "#b8006e")
        accent_L = theme.to_oklab(theme.hex_to_rgb(theme.shade("#1565c0", "ink")))[0]
        tint_L = theme.to_oklab(theme.hex_to_rgb(theme.shade("#d6e6fa", "ground")))[0]
        self.assertGreater(tint_L, accent_L)

    def test_the_accent_family_is_a_rule_and_not_only_a_list(self):
        """64 colours in gui/ and player/ sit at the accent's hue.

        Naming each one was tried and does not hold: the active deck header
        (#2d6cdf) and the selection band were both missed, and a picked accent
        that recolours half the blues looks broken rather than restrained. So
        anything at the accent's hue and blue enough to read as blue follows it,
        whether or not it was ever written down."""
        for color, what in (("#2d6cdf", "active deck header"),
                            ("#2456b8", "its border"),
                            ("#6a9de0", "the takt meter's scale"),
                            ("#3b6ea5", "the tournament tree"),
                            ("#7ba4e8", "the cartwall"),
                            ("#b6d0ee", "an AI dialog panel")):
            self.assertTrue(theme.in_accent_family(color),
                            f"{what} ({color}) would stay blue")

    def test_the_apps_greys_are_not_dragged_along_with_the_accent(self):
        """A grey with a hint of blue in it is still a grey.

        These all sit within a degree or two of the accent's hue — icons' own
        near-black among them — and tinting them would carry the picked colour
        into the body text and every panel border in the app."""
        for color, what in (("#33383f", "the icon ink"),
                            ("#6b7480", "a tree grey"),
                            ("#8a929c", "another tree grey"),
                            ("#a8aeb8", "a table grey"),
                            ("#141414", "body text"),
                            ("#ffffff", "white")):
            self.assertFalse(theme.in_accent_family(color),
                             f"{what} ({color}) would be tinted")

    def test_the_players_meaning_colours_are_outside_the_family(self):
        for color, what in (("#d8a0a0", "fade out"), ("#7fd4a0", "extend"),
                            ("#f0c674", "cue"), ("#e58080", "panic")):
            self.assertFalse(theme.in_accent_family(color), f"{what} ({color})")

    def test_default_accent_is_a_no_op(self):
        theme.set_active("light", theme.ACCENT_DEFAULT)
        self.assertEqual(theme.qss("color:#1565c0;"), "color:#1565c0;")

    # ── settings plumbing ────────────────────────────────────────────────────

    def test_theme_of_settings(self):
        self.assertEqual(theme.theme_of({"theme": "dark"}), "dark")
        self.assertEqual(theme.theme_of({"theme": "DARK"}), "dark")
        self.assertEqual(theme.theme_of({}), "light")
        self.assertEqual(theme.theme_of({"theme": "nonsense"}), "light")
        self.assertEqual(theme.theme_of(None), "light")

    def test_accent_of_settings(self):
        self.assertEqual(theme.accent_of({"accent_color": "#B8006E"}), "#b8006e")
        self.assertEqual(theme.accent_of({"accent_color": "#abc"}), "#aabbcc")
        self.assertEqual(theme.accent_of({}), theme.ACCENT_DEFAULT)
        self.assertEqual(theme.accent_of({"accent_color": "red"}), theme.ACCENT_DEFAULT)

    def test_light_palette_is_the_one_run_gui_used_to_set(self):
        """The exact 12 values that stood inline in run_gui before the theme.

        The promise "light mode is unchanged" rests on these, and they are the
        one part of it no other test covers: qss() and shade() are proven
        identities in light mode, so the palette is what is left."""
        from PySide6.QtGui import QPalette
        was = {
            "Window": (240, 242, 245), "WindowText": (20, 20, 20),
            "Base": (255, 255, 255), "AlternateBase": (245, 247, 252),
            "Text": (20, 20, 20), "ButtonText": (20, 20, 20),
            "Button": (225, 228, 235), "Link": (30, 100, 200),
            "Highlight": (70, 130, 210), "HighlightedText": (255, 255, 255),
            "ToolTipBase": (255, 255, 220), "ToolTipText": (20, 20, 20),
        }
        theme.set_active("light", theme.ACCENT_DEFAULT)
        pal = theme.app_palette()
        for name, rgb in was.items():
            got = pal.color(getattr(QPalette.ColorRole, name))
            self.assertEqual((got.red(), got.green(), got.blue()), rgb, name)

    def test_the_title_bar_is_only_asked_for_in_dark_mode(self):
        """Windows paints the caption bar, not Qt, and it follows the SYSTEM
        theme — which is what left a white bar over every window of a dark app.

        Offscreen there is no native handle for DWM to act on, so what a test
        can pin is the decision: light mode never asks, dark mode installs one
        watcher and not a second. That the call itself is accepted was checked
        against the real compositor by hand (HRESULT 0)."""
        from PySide6.QtWidgets import QApplication, QWidget
        QApplication.instance() or QApplication([])
        was = theme._frame_watcher
        try:
            theme._frame_watcher = None
            theme.set_active("light", theme.ACCENT_DEFAULT)
            theme.install_titlebar_hook()
            self.assertIsNone(theme._frame_watcher,
                              "light mode asked Windows for a dark title bar")
            self.assertFalse(theme.apply_window_frame(QWidget()))

            theme.set_active("dark", theme.ACCENT_DEFAULT)
            theme.install_titlebar_hook()
            first = theme._frame_watcher
            self.assertIsNotNone(first, "dark mode installed no title-bar hook")
            theme.install_titlebar_hook()
            self.assertIs(theme._frame_watcher, first, "hook installed twice")
        finally:
            theme._frame_watcher = was
            theme.set_active("light", theme.ACCENT_DEFAULT)

    def test_the_bevel_roles_follow_the_theme_too(self):
        """Fusion draws every frame edge, group-box outline, sunken panel and
        scrollbar groove from Light/Midlight/Mid/Dark/Shadow — and those five
        were never set, so a default (light) QPalette's values survived into
        dark mode. The visible symptom was the ⚙ Settings separators: pure
        white 855px rules across a dark dialog.

        Light mode must keep Qt's own derivation untouched, so the check is
        one-sided: dark gets its own, light is left exactly as it was."""
        from PySide6.QtGui import QPalette
        bevels = ("Light", "Midlight", "Mid", "Dark", "Shadow")

        theme.set_active("light", theme.ACCENT_DEFAULT)
        untouched = QPalette()
        for name in bevels:
            role = getattr(QPalette.ColorRole, name)
            self.assertEqual(
                theme.app_palette().color(role).name(),
                untouched.color(role).name(),
                f"light mode no longer leaves {name} to Qt")

        theme.set_active("dark", theme.ACCENT_DEFAULT)
        pal = theme.app_palette()
        window = pal.color(QPalette.ColorRole.Window)
        for name in bevels:
            got = pal.color(getattr(QPalette.ColorRole, name))
            self.assertLess(
                got.lightness(), 128,
                f"{name} stayed a light-theme value ({got.name()})")
        # The bevel still has to be a bevel: Light above the ground it edges,
        # Dark below it, or a sunken frame reads as a flat smear.
        self.assertGreater(pal.color(QPalette.ColorRole.Light).lightness(),
                           window.lightness(), "no highlight edge left")
        self.assertLess(pal.color(QPalette.ColorRole.Dark).lightness(),
                        window.lightness(), "no shadow edge left")

    def test_palette_follows_the_theme(self):
        from PySide6.QtGui import QPalette
        theme.set_active("light", theme.ACCENT_DEFAULT)
        light = theme.app_palette().color(QPalette.ColorRole.Window)
        theme.set_active("dark", theme.ACCENT_DEFAULT)
        dark = theme.app_palette().color(QPalette.ColorRole.Window)
        self.assertGreater(light.lightness(), dark.lightness())


if __name__ == "__main__":
    unittest.main(verbosity=2)
