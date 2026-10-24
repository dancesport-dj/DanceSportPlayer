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

from PySide6.QtWidgets import QApplication, QTabWidget

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

    def test_a_fade_of_nothing_reads_cut(self):
        dlg, _ = self.open({"cart_fade_ms": 0})
        self.assertEqual(dlg._cart_fade_spin.text(), "cut")

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

    def test_its_text_is_translated(self):
        # "🎛 Cartwall" is the same in German, so it has no entry to look for.
        from planner.i18n.lang_de import CATALOG
        dlg, tabs = self.open()
        texts = [dlg._cart_intro.text(), dlg._cart_fade_lbl.text(),
                 dlg._cart_fade_spin.toolTip(), dlg._cart_colour_lbl.text(),
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
