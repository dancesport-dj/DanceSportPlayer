"""🎛 ⚙ Settings → 🎛 Cartwall: the wall's settings in one place.

Run:  py -m unittest tests.gui.test_settings_cartwall -v

Marcel: "in the settings make a own section for cartwall where the duck and
behavour settings globally live", "i would also see there the std fade out
instead of the item in context menu", "also the wall color defaults". The
pad duck and the 🎶 background pads moved over from 🔊 Sound & player; the
wall fade-out and the wall colour left the pad's right-click menu. Those two
are still the wall's own, kept in cartwall.json: the window hands them in
and takes them back out under CART_WALL_KEYS.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_cartwall_"))

from PySide6.QtWidgets import QApplication, QGroupBox, QTabWidget

from gui.dialogs.settings_cartwall import CART_WALL_KEYS
from gui.dialogs.settings_dialog import SettingsDialog
from planner.playing import cartwall as pc
from tests.qt_test_support import reap_widget, stub_window_startup


class CartwallTabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def open(self, settings=None):
        dlg = SettingsDialog(settings or {}, None)
        self.addCleanup(reap_widget, dlg)
        return dlg, dlg.findChild(QTabWidget)

    def assertReadsZero(self, spin):
        """Marcel: "why did you write cut instead if 0 sec?" — a fade of
        nothing reads as 0 s, in the machine's own decimal format."""
        self.assertEqual(spin.text(), spin.textFromValue(0.0) + " s")

    def page(self, tabs, caption):
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn(caption, captions)
        return tabs.widget(captions.index(caption))

    def test_the_wall_has_a_tab_of_its_own(self):
        dlg, tabs = self.open()
        page = self.page(tabs, "🎛 Cartwall")
        sound = self.page(tabs, "🔊 Sound && player")
        for w in (dlg._cart_duck_spin, dlg._cart_bg_combo,
                  dlg._cart_fade_spin, dlg._cart_colour_combo):
            with self.subTest(w=w):
                self.assertTrue(page.isAncestorOf(w))
                self.assertFalse(sound.isAncestorOf(w))

    def test_it_sits_after_sound_and_player(self):
        _, tabs = self.open()
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertEqual(captions.index("🎛 Cartwall"),
                         captions.index("🔊 Sound && player") + 1)

    def test_a_planner_only_install_has_no_wall_to_set(self):
        _, tabs = self.open({"app_mode": "planner"})
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertFalse(tabs.isTabVisible(captions.index("🎛 Cartwall")))

    def test_the_duck_and_background_settings_still_save(self):
        dlg, _ = self.open({"cart_duck_pct": 30, "cart_bg_mode": "mute"})
        self.assertEqual(dlg._cart_duck_spin.value(), 30)
        dlg._cart_duck_spin.setValue(20)
        self.assertEqual(dlg.values()["cart_duck_pct"], 20)
        self.assertEqual(dlg.values()["cart_bg_mode"], "mute")

    def test_the_background_fade_back_in_starts_at_the_standard(self):
        """'make the fade-in for cartwall also configurable … use current std
        value as default'."""
        dlg, tabs = self.open()
        self.assertTrue(self.page(tabs, "🎛 Cartwall").isAncestorOf(
            dlg._cart_bg_fade_spin))
        self.assertAlmostEqual(dlg._cart_bg_fade_spin.value(),
                               pc.DEFAULT_BG_FADE_IN_MS / 1000)
        self.assertEqual(dlg.values()["cart_bg_fade_in_ms"], pc.DEFAULT_BG_FADE_IN_MS)

    def test_the_background_fade_back_in_comes_in_and_goes_out(self):
        dlg, _ = self.open({"cart_bg_fade_in_ms": 3500})
        self.assertAlmostEqual(dlg._cart_bg_fade_spin.value(), 3.5)
        dlg._cart_bg_fade_spin.setValue(0.0)
        self.assertReadsZero(dlg._cart_bg_fade_spin)
        self.assertEqual(dlg.values()["cart_bg_fade_in_ms"], 0)

    def test_the_fire_fade_in_starts_at_the_standard_and_saves(self):
        """'fade in and fade out should be per default both 0.2'."""
        dlg, _ = self.open()
        self.assertAlmostEqual(dlg._cart_bg_fire_spin.value(), 0.2)
        self.assertEqual(dlg.values()["cart_bg_fire_fade_ms"], 200)
        dlg._cart_bg_fire_spin.setValue(0.0)
        self.assertReadsZero(dlg._cart_bg_fire_spin)
        self.assertEqual(dlg.values()["cart_bg_fire_fade_ms"], 0)
        dlg, _ = self.open({"cart_bg_fire_fade_ms": 1500})
        self.assertAlmostEqual(dlg._cart_bg_fire_spin.value(), 1.5)
        dlg._cart_bg_fire_spin.setValue(0.8)
        self.assertEqual(dlg.values()["cart_bg_fire_fade_ms"], 800)

    def test_the_wait_starts_at_the_standard_and_saves(self):
        dlg, _ = self.open()
        self.assertAlmostEqual(dlg._cart_bg_hold_spin.value(),
                               pc.DEFAULT_BG_HOLD_MS / 1000)
        self.assertEqual(dlg.values()["cart_bg_hold_ms"], pc.DEFAULT_BG_HOLD_MS)
        dlg._cart_bg_hold_spin.setValue(0.6)
        self.assertEqual(dlg.values()["cart_bg_hold_ms"], 600)

    def test_the_paso_doble_wait_keeps_the_bed_down_and_saves(self):
        """Marcel: no background music while waiting for Paso Doble."""
        dlg, tabs = self.open()
        self.assertTrue(self.page(tabs, "🎛 Cartwall").isAncestorOf(
            dlg._cart_bg_pd_check))
        self.assertTrue(dlg._cart_bg_pd_check.isChecked())
        self.assertIs(dlg.values()["cart_bg_pd_quiet"], True)
        dlg._cart_bg_pd_check.setChecked(False)
        self.assertIs(dlg.values()["cart_bg_pd_quiet"], False)
        dlg, _ = self.open({"cart_bg_pd_quiet": False})
        self.assertFalse(dlg._cart_bg_pd_check.isChecked())

    def test_the_title_waits_for_the_fade_out_unless_overlapping(self):
        """Marcel: "make it configurable whether it overlaps or not. Default:
        complete fade-out, then the main music starts"."""
        dlg, tabs = self.open()
        self.assertTrue(self.page(tabs, "🎛 Cartwall").isAncestorOf(
            dlg._cart_bg_overlap_check))
        self.assertFalse(dlg._cart_bg_overlap_check.isChecked())
        self.assertIs(dlg.values()["cart_bg_overlap"], False)
        dlg._cart_bg_overlap_check.setChecked(True)
        self.assertIs(dlg.values()["cart_bg_overlap"], True)
        dlg, _ = self.open({"cart_bg_overlap": True})
        self.assertTrue(dlg._cart_bg_overlap_check.isChecked())

    def test_the_overlap_says_which_title_and_over_what(self):
        """F19: "Start the title while it is still fading out" left open which
        title, and what is fading."""
        dlg, _ = self.open()
        text = dlg._cart_bg_overlap_check.text()
        self.assertIn("main player", text)
        self.assertIn("background", text)

    def test_the_background_dip_starts_at_the_standard(self):
        """'make also both fade in and fade out configurable', and 'set to
        0.2 instead of 0.18', and later 'for fading out over use 0.5s'."""
        dlg, tabs = self.open()
        self.assertTrue(self.page(tabs, "🎛 Cartwall").isAncestorOf(
            dlg._cart_bg_out_spin))
        self.assertAlmostEqual(dlg._cart_bg_out_spin.value(),
                               pc.DEFAULT_BG_FADE_OUT_MS / 1000)
        self.assertEqual(dlg.values()["cart_bg_fade_out_ms"], 500)

    def test_every_time_takes_one_decimal(self):
        """'i can only input one commata wich is fine, but then it should be
        the same on fading out' — and on every other time of the tab."""
        dlg, _ = self.open()
        for spin in (dlg._cart_fade_spin, dlg._cart_bg_fire_spin,
                     dlg._cart_bg_out_spin, dlg._cart_bg_hold_spin,
                     dlg._cart_bg_fade_spin):
            with self.subTest(spin=spin.toolTip()[:30]):
                self.assertEqual(spin.decimals(), 1)

    def test_the_background_dip_comes_in_and_goes_out(self):
        dlg, _ = self.open({"cart_bg_fade_out_ms": 1500})
        self.assertAlmostEqual(dlg._cart_bg_out_spin.value(), 1.5)
        dlg._cart_bg_out_spin.setValue(0.7)
        self.assertEqual(dlg.values()["cart_bg_fade_out_ms"], 700)
        dlg._cart_bg_out_spin.setValue(0.0)
        self.assertReadsZero(dlg._cart_bg_out_spin)

    def test_the_wall_fade_and_colour_come_in_and_go_out(self):
        dlg, _ = self.open({"cart_fade_ms": 2500, "cart_wall_colour": "#c8871a"})
        self.assertAlmostEqual(dlg._cart_fade_spin.value(), 2.5)
        self.assertEqual(dlg._cart_colour_combo.currentData(), "#c8871a")
        dlg._cart_fade_spin.setValue(0.4)
        combo = dlg._cart_colour_combo
        combo.setCurrentIndex(combo.findData("#2f8f4e"))
        vals = dlg.values()
        self.assertEqual(vals["cart_fade_ms"], 400)
        self.assertEqual(vals["cart_wall_colour"], "#2f8f4e")

    def test_without_a_wall_it_shows_the_standard(self):
        dlg, _ = self.open()
        self.assertAlmostEqual(dlg._cart_fade_spin.value(),
                               pc.DEFAULT_FADE_MS / 1000)
        self.assertEqual(dlg._cart_colour_combo.currentData(),
                         pc.DEFAULT_PAD_COLOUR)

    def test_a_fade_of_nothing_reads_0_s(self):
        dlg, _ = self.open({"cart_fade_ms": 0})
        self.assertReadsZero(dlg._cart_fade_spin)

    def test_the_colours_are_the_wall_menu_ones(self):
        """White stands for the standard, then every pad colour but "Wall
        default", which is what the wall colour itself is."""
        combo = self.open()[0]._cart_colour_combo
        self.assertEqual(
            [combo.itemData(i) for i in range(combo.count())],
            [pc.DEFAULT_PAD_COLOUR] + [v for v in pc.PAD_COLOURS.values() if v])

    def test_the_colour_row_says_it_is_the_walls_default(self):
        """Marcel: "label should be default wall color" — it is not a pad's
        colour, it is what every pad without its own one shows."""
        dlg, _ = self.open()
        self.assertEqual(dlg._cart_colour_lbl.text(), "🖌  Default wall colour:")
        self.assertTrue(dlg._cart_colour_combo.toolTip().startswith(
            "The wall's default colour"))

    @staticmethod
    def _box_of(widget):
        while widget is not None and not isinstance(widget, QGroupBox):
            widget = widget.parentWidget()
        return widget

    def test_the_rows_say_which_pads_they_touch(self):
        """Marcel: "make it in settings clear when what setting is used" —
        the rows every pad follows sit in one box, the 🎶 Background ones in
        another, and those in the order they happen to a background pad."""
        dlg, _ = self.open()
        every = self._box_of(dlg._cart_duck_spin)
        self.assertEqual(every.title(), "🎛  All pads")
        for widget in (dlg._cart_fade_spin, dlg._cart_colour_combo):
            self.assertIs(self._box_of(widget), every)
        bg = self._box_of(dlg._cart_bg_combo)
        self.assertEqual(bg.title(), "🎶  Pads set to 🎶 Background")
        lyt = bg.layout()
        rows = [lyt.itemAt(i) for i in range(lyt.count())]
        firsts = [row.widget() or row.layout().itemAt(0).widget() for row in rows]
        self.assertEqual(firsts, [
            dlg._cart_bg_hint, dlg._cart_bg_vol_lbl, dlg._cart_bg_fire_lbl,
            firsts[3], dlg._cart_bg_out_lbl, dlg._cart_bg_overlap_check,
            dlg._cart_bg_hold_lbl, dlg._cart_bg_fade_lbl, dlg._cart_bg_pd_check])
        self.assertEqual(firsts[3].text(), "🎵  When the main player starts a title:")
        self.assertEqual(dlg._cart_bg_fire_lbl.text(), "▶  When fired — fade the pad in over:")
        self.assertEqual(dlg._cart_bg_hold_lbl.text(), "⏳  When the main player stops — wait:")

    def test_each_fade_says_it_moves_the_pad(self):
        """Marcel: the fade settings have to make clear whether the pad or
        the main music is meant. Every fade here moves the pad; the music is
        only what sets them off."""
        dlg, _ = self.open()
        for lbl in (dlg._cart_fade_lbl, dlg._cart_bg_fire_lbl,
                    dlg._cart_bg_out_lbl, dlg._cart_bg_fade_lbl):
            self.assertIn("the pad", lbl.text())

    def test_the_paso_doble_wait_says_it_keeps_the_pad_down(self):
        """Marcel: rename 'keep it down while a paso doble waits to start'
        to also include pad."""
        dlg, _ = self.open()
        self.assertEqual(dlg._cart_bg_pd_check.text(),
                         "🐂  Keep the pad down while a Paso Doble waits to start")

    def test_its_text_is_translated(self):
        # "🎛 Cartwall" is the same in German, so it has no entry to look for.
        from planner.i18n.lang_de import CATALOG
        dlg, tabs = self.open()
        boxes = [self._box_of(dlg._cart_duck_spin), self._box_of(dlg._cart_bg_combo)]
        texts = [box.title() for box in boxes] + [
                 dlg._cart_bg_hint.text(), dlg._cart_intro.text(), dlg._cart_fade_lbl.text(),
                 dlg._cart_fade_spin.toolTip(), dlg._cart_colour_lbl.text(),
                 dlg._cart_bg_fade_lbl.text(), dlg._cart_bg_fade_spin.toolTip(),
                 dlg._cart_bg_out_lbl.text(), dlg._cart_bg_out_spin.toolTip(),
                 dlg._cart_bg_fire_lbl.text(), dlg._cart_bg_fire_spin.toolTip(),
                 dlg._cart_bg_hold_lbl.text(), dlg._cart_bg_hold_spin.toolTip(),
                 dlg._cart_bg_overlap_check.text(), dlg._cart_bg_overlap_check.toolTip(),
                 dlg._cart_colour_combo.toolTip()]
        for text in texts:
            with self.subTest(text=text):
                self.assertIn(text, CATALOG)


class WindowTest(unittest.TestCase):
    """The window side: what it hands the dialog and what it does with the
    answer. The wall stays where its fade and colour are kept."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from player.widgets.cartwall import CartwallWidget
        self.wall = CartwallWidget()
        self.addCleanup(reap_widget, self.wall)
        self.wall.set_wall(pc.DEFAULT_GRID, [pc.blank_page()], 0, "#7a3fbf", 3000)
        self.host = SimpleNamespace(_cartwall=self.wall)

    def test_it_hands_the_wall_in(self):
        from player.window.main_cartwall import CartwallMixin
        self.assertEqual(CartwallMixin.cart_wall_settings(self.host),
                         {"cart_fade_ms": 3000, "cart_wall_colour": "#7a3fbf"})
        self.assertEqual(set(CartwallMixin.cart_wall_settings(self.host)),
                         set(CART_WALL_KEYS))

    def test_the_answer_reaches_the_wall(self):
        from player.window.main_cartwall import CartwallMixin
        saved = []
        self.wall.changed.connect(lambda: saved.append(1))
        CartwallMixin.apply_cart_wall(
            self.host, {"cart_fade_ms": 500, "cart_wall_colour": "#c8871a"})
        self.assertEqual(self.wall.fade_ms(), 500)
        self.assertEqual(self.wall.default_colour(), "#c8871a")
        self.assertTrue(saved)

    def test_no_wall_no_harm(self):
        from player.window.main_cartwall import CartwallMixin
        host = SimpleNamespace()
        self.assertEqual(CartwallMixin.cart_wall_settings(host), {})
        CartwallMixin.apply_cart_wall(host, {"cart_fade_ms": 500})



class OpenSettingsTest(unittest.TestCase):
    """The real _open_settings, with the dialog stubbed."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_settings_cartwall_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_the_wall_values_go_to_the_wall_not_the_settings_file(self):
        from PySide6.QtWidgets import QDialog
        win, seen = self.win, {}
        win._cartwall.set_fade_ms(3000)

        class Dlg:
            def __init__(self, settings, *_a, **_k):
                seen["in"] = dict(settings)

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return {**seen["in"], "cart_fade_ms": 4200,
                        "cart_wall_colour": "#c8871a"}

            def running_look_touched(self):
                return False

            def deleteLater(self):
                pass

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings") as save:
            win._open_settings()
        self.assertEqual(seen["in"]["cart_fade_ms"], 3000)
        self.assertEqual(win._cartwall.fade_ms(), 4200)
        self.assertEqual(win._cartwall.default_colour(), "#c8871a")
        saved = save.call_args[0][0]
        for key in CART_WALL_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(key, saved)
                self.assertNotIn(key, win._settings)


class PadMenuTest(unittest.TestCase):
    """The pad's right-click lost ⏱ Wall fade-out… and 🖌 Wall colour."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_pad_no_longer_asks_for_them(self):
        from player.widgets.cartwall import CartwallWidget
        w = CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.blank_page()])
        button = next(iter(w._buttons.values()))
        self.assertFalse(hasattr(button, "wall_fade_requested"))
        self.assertFalse(hasattr(button, "wall_colour_requested"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
