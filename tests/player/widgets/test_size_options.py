#!/usr/bin/env python3
"""🔠 Text size and 🔘 player button size from ⚙ Settings → Look (item 28).

Run:  .venv/Scripts/python.exe -m unittest tests.player.widgets.test_size_options -v

Marcel: "Increase font size and button size. Button size for primary buttons
only (Play/Stop, config switches) in the Player and Mini Player." The text is
read at start-up like the theme; the buttons follow at once.

F9: "Text size: drop the separate player-button option; above 115 % all
buttons scale with the text (width too, not only height); offer 105/110/115 %."
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sizes_"))

from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from gui.dialogs.settings_dialog import SettingsDialog
from player.widgets.panel_parts import Toggle
from player.widgets.play_mode_panel import PlayModePanel
from player.widgets.player import BigPlayerWidget, PreviewOverlay
from player.window.main_player import PlayerControlMixin
from shared.appearance import theme
from tests.qt_test_support import reap_widget


class _QtCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class ScaleOfTest(unittest.TestCase):

    def test_only_the_offered_sizes_count(self):
        self.assertEqual(theme.font_scale_of({"font_scale": 130}), 130)
        for pct in (105, 110, 115):
            self.assertEqual(theme.font_scale_of({"font_scale": pct}), pct)
        for junk in (None, "big", 99, 1000, [1]):
            self.assertEqual(theme.font_scale_of({"font_scale": junk}), 100, junk)
        self.assertEqual(theme.font_scale_of({}), 100)

    def test_no_separate_button_size_any_more(self):
        self.assertFalse(hasattr(theme, "button_scale_of"))
        self.assertFalse(hasattr(theme, "BUTTON_SCALES"))


class ButtonScaleTest(unittest.TestCase):

    def tearDown(self):
        theme.set_font_scale(100)

    def test_up_to_115_the_buttons_keep_their_size(self):
        for pct in (100, 105, 110, 115):
            theme.set_font_scale(pct)
            self.assertEqual(theme.button_scale(), 100, pct)

    def test_above_115_they_follow_the_text(self):
        for pct in (130, 150):
            theme.set_font_scale(pct)
            self.assertEqual(theme.button_scale(), pct)


class FontScaleTest(unittest.TestCase):

    def tearDown(self):
        theme.set_font_scale(100)

    def test_every_font_size_in_a_sheet_grows(self):
        sheet = "QLabel { font-size:10px; } QToolButton { font-size: 9pt; }"
        self.assertEqual(theme.scale_fonts(sheet, 150),
                         "QLabel { font-size:15px; } QToolButton { font-size: 13.5pt; }")

    def test_at_100_the_sheet_is_untouched(self):
        sheet = "QLabel { font-size:11px; color:#333; }"
        self.assertIs(theme.qss(sheet), sheet)

    def test_the_stylesheet_hook_scales_even_the_light_default(self):
        theme.set_font_scale(130)
        self.assertEqual(theme.qss("font-size:10px; color:#333;"),
                         "font-size:13px; color:#333;")

    def test_a_size_that_is_not_offered_falls_back(self):
        theme.set_font_scale(123)
        self.assertEqual(theme.font_scale(), 100)


class AppFontTest(_QtCase):

    def setUp(self):
        # apply_app dresses the whole app: put font AND palette back.
        self.addCleanup(self.app.setPalette, self.app.palette())
        self.addCleanup(self.app.setFont, self.app.font())
        self.addCleanup(theme.apply_settings, {})

    def test_the_app_font_grows_with_the_text_size(self):
        base = QFont(self.app.font())
        theme.apply_settings({"font_scale": 150})
        theme.apply_app(self.app)
        if base.pointSizeF() > 0:
            self.assertAlmostEqual(self.app.font().pointSizeF(),
                                   base.pointSizeF() * 1.5, places=1)
        else:
            self.assertEqual(self.app.font().pixelSize(),
                             round(base.pixelSize() * 1.5))


class FixedButtonTest(_QtCase):
    """A button with a fixed width cut its grown caption off: it widens too."""

    def button(self):
        b = QPushButton("⚡  Erzeugen")
        self.addCleanup(reap_widget, b)
        return b

    def test_a_fixed_width_and_height_grow(self):
        b = self.button()
        b.setFixedSize(40, 20)
        theme.scale_fixed_size(b, 130)
        self.assertEqual((b.width(), b.height()), (52, 26))
        self.assertEqual(b.minimumWidth(), b.maximumWidth())

    def test_twice_is_not_twice_as_wide(self):
        b = self.button()
        b.setFixedWidth(40)
        theme.scale_fixed_size(b, 130)
        theme.scale_fixed_size(b, 130)
        self.assertEqual(b.maximumWidth(), 52)

    def test_a_width_set_again_grows_again(self):
        b = self.button()
        b.setFixedWidth(40)
        theme.scale_fixed_size(b, 130)
        b.setFixedWidth(60)       # a caption that changed sets it anew
        theme.scale_fixed_size(b, 130)
        self.assertEqual(b.maximumWidth(), 78)

    def test_a_capped_width_grows_its_cap(self):
        b = self.button()
        b.setMaximumWidth(100)
        theme.scale_fixed_size(b, 150)
        self.assertEqual(b.maximumWidth(), 150)
        self.assertEqual(b.minimumWidth(), 0)

    def test_a_free_button_is_left_to_its_size_hint(self):
        b = self.button()
        theme.scale_fixed_size(b, 150)
        self.assertEqual((b.minimumWidth(), b.maximumWidth()), (0, 16777215))
        self.assertEqual(b.maximumHeight(), 16777215)

    def test_the_hook_widens_a_button_as_it_shows(self):
        theme.set_font_scale(130)
        self.addCleanup(theme.set_font_scale, 100)
        self.addCleanup(theme.remove_button_scale_hook)
        theme.install_button_scale_hook()
        host = QWidget()
        self.addCleanup(reap_widget, host)
        b = QPushButton("⚡", host)
        b.setFixedWidth(40)
        host.show()
        self.app.processEvents()
        self.assertEqual(b.width(), 52)

    def test_no_hook_up_to_115(self):
        theme.set_font_scale(115)
        self.addCleanup(theme.set_font_scale, 100)
        self.addCleanup(theme.remove_button_scale_hook)
        theme.install_button_scale_hook()
        self.assertIsNone(theme._button_scaler)


class PlayerCardTest(_QtCase):

    def test_play_and_its_neighbours_grow_the_rest_does_not(self):
        w = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, w)
        self.assertEqual(len(w._primary_btns), 3)
        self.assertIn(w._pause_btn, w._primary_btns)
        cue = w._cue_btn.iconSize()
        w.set_button_scale(150)
        for b in w._primary_btns:
            self.assertEqual(b.iconSize().width(), 36)
        self.assertEqual(w._cue_btn.iconSize(), cue)
        w.set_button_scale(100)
        self.assertEqual(w._pause_btn.iconSize().width(), 24)


class MiniPlayerTest(_QtCase):

    def test_stop_and_skip_grow(self):
        out = QAudioOutput()
        view = PreviewOverlay(QMediaPlayer(), out)
        self.addCleanup(reap_widget, view)
        self.assertEqual(len(view._primary_btns), 3)
        view.set_button_scale(175)
        self.assertEqual([b.iconSize().width() for b, _px in view._primary_btns],
                         [19, 21, 21])


class SwitchTest(_QtCase):

    def test_the_pill_grows_and_the_class_does_not(self):
        pill = Toggle("⏭  Auto-advance")
        self.addCleanup(reap_widget, pill)
        small = pill.sizeHint()
        pill.set_scale(150)
        self.assertEqual((pill._TRACK_W, pill._TRACK_H), (54, 30))
        self.assertGreater(pill.sizeHint().height(), small.height())
        self.assertEqual((Toggle._TRACK_W, Toggle._TRACK_H), (36, 20))
        pill.set_scale(100)
        self.assertEqual(pill.sizeHint(), small)

    def test_the_panel_reaches_every_switch(self):
        panel = PlayModePanel({})
        self.addCleanup(reap_widget, panel)
        panel.set_button_scale(125)
        pills = panel.findChildren(Toggle)
        self.assertTrue(pills)
        self.assertTrue(all(p._TRACK_H == 25 for p in pills))


class WindowTest(unittest.TestCase):

    def test_every_player_view_is_told(self):
        seen = []
        tell = lambda name: SimpleNamespace(
            set_button_scale=lambda pct: seen.append((name, pct)))
        win = SimpleNamespace(
            _big_player=tell("card"), _play_panel=tell("panel"),
            _preview=tell("mini"),
            _cue_player=lambda: SimpleNamespace(view=tell("cue")))
        PlayerControlMixin._set_button_scale(win, 150)
        self.assertEqual(seen, [("card", 150), ("panel", 150), ("mini", 150),
                                ("cue", 150)])

    def test_no_player_no_harm(self):
        seen = []
        win = SimpleNamespace(
            _big_player=None, _preview=None, _cue_player=lambda: None,
            _play_panel=SimpleNamespace(set_button_scale=seen.append))
        PlayerControlMixin._set_button_scale(win, 125)
        self.assertEqual(seen, [125])


class SettingsRoundTripTest(_QtCase):

    def test_the_stored_size_comes_back_out(self):
        dlg = SettingsDialog({"font_scale": 110})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg.values()["font_scale"], 110)

    def test_defaults_are_the_built_size(self):
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg.values()["font_scale"], 100)

    def test_the_small_steps_are_offered_and_no_button_size(self):
        dlg = SettingsDialog({})
        self.addCleanup(reap_widget, dlg)
        combo = dlg._font_scale_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         [100, 105, 110, 115, 130, 150])
        self.assertFalse(hasattr(dlg, "_button_scale_combo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
