#!/usr/bin/env python3
"""Tests of 🔋: what Windows says about the power, up to the 🚦 Ready? line.

Run:  py -m unittest tests.player.audio.test_power_status -v

A laptop on battery plays the whole evening well until it does not, and nothing
at the desk says so while the charger cable lies under the table.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_power_"))

from gui.window.main_music import MusicCheckMixin
from planner.event.readiness import OK, WARN
from shared.audio import playback


class PowerStatusTest(unittest.TestCase):

    def ask(self, line, percent, answer=1, platform="win32"):
        def fill(ref):
            ref._obj.ACLineStatus = line
            ref._obj.BatteryLifePercent = percent
            return answer
        kernel32 = mock.Mock(GetSystemPowerStatus=fill)
        with mock.patch.object(playback.sys, "platform", platform), \
                mock.patch("ctypes.windll", mock.Mock(kernel32=kernel32), create=True):
            return playback.power_status()

    def test_on_mains(self):
        self.assertEqual(self.ask(1, 80), (True, 80))

    def test_on_battery(self):
        self.assertEqual(self.ask(0, 43), (False, 43))

    def test_a_desktop_without_a_battery_is_on_mains(self):
        self.assertEqual(self.ask(1, 255), (True, None))

    def test_a_battery_of_unknown_charge(self):
        self.assertEqual(self.ask(0, 255), (False, None))

    def test_windows_does_not_know(self):
        self.assertIsNone(self.ask(255, 255))

    def test_the_call_failing_tells_nothing(self):
        self.assertIsNone(self.ask(1, 80, answer=0))

    def test_off_windows_nothing_is_told(self):
        self.assertIsNone(self.ask(1, 80, platform="darwin"))


class DeskFindingsTest(unittest.TestCase):

    def findings(self, status):
        win = SimpleNamespace(
            _audio_device=SimpleNamespace(unplugged=list, cue_on_music=lambda: False,
                                          cue_shares_music=lambda: False),
            controller_status=lambda: (False, ""),
            controller_config=lambda: {"device": ""},
            _play_panel=SimpleNamespace(keep_awake=lambda: True))
        with mock.patch("gui.window.main_music.power_status", return_value=status):
            return MusicCheckMixin._desk_findings(win)

    def test_the_power_line_stands_with_the_desk_lines(self):
        by_key = {f.key: f.level for f in self.findings((False, 43))}
        self.assertEqual(by_key, {"outputs": OK, "awake": OK, "power": WARN})

    def test_power_nobody_can_tell_adds_no_line(self):
        self.assertEqual([f.key for f in self.findings(None)], ["outputs", "awake"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
