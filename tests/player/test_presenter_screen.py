#!/usr/bin/env python3
"""Tests for which monitor the presenter screen goes to, and what happens to
it when that monitor goes away.

Run:  py -m unittest tests.player.test_presenter_screen -v

A beamer is plugged in after the app starts, knocked loose mid-evening, and
plugged back. The pick used to be a bare list index: an unplug clamped it onto
the laptop screen and it stayed there, and the full-screen presenter was left
for Windows to drop onto the desk — over the controls, mid-heat.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_prescreen_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player import play_mode_panel as pmp  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402

_LAPTOP = ("1 · 1920×1080  (primary)", "LAPTOP")
_BEAMER = ("2 · 1280×720", "BEAMER")


class _Screens:
    """Stands in for the connected monitors; the test plugs and unplugs."""

    def __init__(self, *choices):
        self.now = list(choices)

    def __call__(self):
        return list(self.now)


class PanelPickTest(unittest.TestCase):
    """The combo keeps the monitor, not its place in the list."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self, settings, *choices):
        self.screens = _Screens(*choices)
        real = pmp.screen_choices
        pmp.screen_choices = self.screens
        self.addCleanup(setattr, pmp, "screen_choices", real)
        p = pmp.PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        return p

    def test_the_saved_monitor_is_found_where_the_list_now_has_it(self):
        p = self._panel({"presenter_screen": 0, "presenter_screen_name": "BEAMER"},
                        _LAPTOP, _BEAMER)
        self.assertEqual(p.presenter_screen(), 1)

    def test_an_unplugged_beamer_is_picked_again_when_it_is_back(self):
        p = self._panel({"presenter_screen_name": "BEAMER"}, _LAPTOP, _BEAMER)
        self.screens.now = [_LAPTOP]
        p._fill_screens()
        self.assertEqual(p.presenter_screen(), 0)
        self.assertEqual(p.presenter_screen_name(), "BEAMER")   # still wanted
        self.screens.now = [_LAPTOP, _BEAMER]
        p._fill_screens()
        self.assertEqual(p.presenter_screen(), 1)

    def test_picking_another_monitor_is_what_is_kept(self):
        p = self._panel({"presenter_screen_name": "BEAMER"}, _LAPTOP, _BEAMER)
        p.presenter_screen_combo.setCurrentIndex(0)
        self.assertEqual(p.presenter_screen_name(), "LAPTOP")

    def test_a_setting_from_before_names_still_opens_its_index(self):
        p = self._panel({"presenter_screen": 1}, _LAPTOP, _BEAMER)
        self.assertEqual(p.presenter_screen(), 1)
        self.assertEqual(p.presenter_screen_name(), "BEAMER")


class _Screen:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class _Presenter:
    def __init__(self, screen):
        self._screen = screen

    def screen(self):
        return self._screen


class _Panel:
    def __init__(self):
        self.on = []

    def set_presenter_on(self, on):
        self.on.append(on)

    def _fill_screens(self):
        pass


class _Desk(PlayerControlMixin):
    def __init__(self, presenter=None):
        self._presenter = presenter
        self._presenter_lost = None
        self._play_panel = _Panel()

    def statusBar(self):
        return self

    def showMessage(self, *_a):
        pass


class UnplugTest(unittest.TestCase):
    """The desk: a presenter whose monitor goes away is closed, and comes back
    with it."""

    def setUp(self):
        self.beamer = _Screen("BEAMER")
        self.desk = _Desk(_Presenter(self.beamer))

    def test_its_monitor_going_away_closes_the_presenter(self):
        self.desk._on_screen_removed(self.beamer)
        self.assertEqual(self.desk._play_panel.on, [False])

    def test_another_monitor_going_away_leaves_it_standing(self):
        self.desk._on_screen_removed(_Screen("OTHER"))
        self.assertEqual(self.desk._play_panel.on, [])

    def test_it_comes_back_with_its_monitor(self):
        self.desk._on_screen_removed(self.beamer)
        self.desk._presenter = None             # closed, as the toggle does
        self.desk._on_screen_added(_Screen("BEAMER"))
        self.assertEqual(self.desk._play_panel.on, [False, True])

    def test_some_other_monitor_arriving_does_not_open_it(self):
        self.desk._on_screen_removed(self.beamer)
        self.desk._presenter = None
        self.desk._on_screen_added(_Screen("OTHER"))
        self.assertEqual(self.desk._play_panel.on, [False])

    def test_a_presenter_closed_by_hand_stays_closed(self):
        self.desk._presenter = None
        self.desk._on_screen_added(_Screen("BEAMER"))
        self.assertEqual(self.desk._play_panel.on, [])


if __name__ == "__main__":
    unittest.main()
