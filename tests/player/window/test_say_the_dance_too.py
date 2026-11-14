"""🔢 → 🔈 Answering Yes to the heat-only question names the dance again.

Run:  py -m unittest tests.player.window.test_say_the_dance_too -v
"""
import unittest
from unittest import mock

from player.window.main_pause import PauseMusicMixin


class _Host(PauseMusicMixin):

    def __init__(self, settings):
        self._settings = settings
        self._play_panel = mock.Mock()


class SayTheDanceTooTest(unittest.TestCase):

    def run_it(self, settings, with_heat=False):
        host = _Host(settings)
        with mock.patch("player.window.main_pause.save_settings") as save:
            host._say_the_dance_too(with_heat)
        return host, save

    def test_the_setting_is_switched_off_and_saved(self):
        host, save = self.run_it({"announce_heat_only": True})
        self.assertIs(host._settings["announce_heat_only"], False)
        save.assert_called_once_with(host._settings)

    def test_only_the_dance_switches_the_heat_off_too(self):
        host, save = self.run_it({"announce_heat_only": True, "announce_heat": True})
        self.assertIs(host._settings["announce_heat"], False)
        save.assert_called_once_with(host._settings)

    def test_the_dance_with_heat_switches_the_heat_on(self):
        host, _ = self.run_it({"announce_heat_only": True, "announce_heat": False},
                              with_heat=True)
        self.assertIs(host._settings["announce_heat"], True)
        self.assertIs(host._settings["announce_heat_only"], False)

    def test_the_panel_names_the_other_choices_unchanged(self):
        host, _ = self.run_it({"announce_heat_only": True, "announce_voice": "male",
                               "announce_wait": False, "announce_lead": True},
                              with_heat=True)
        host._play_panel.set_announce_style.assert_called_once_with(
            "male", True, False, True, False)


if __name__ == "__main__":
    unittest.main()
