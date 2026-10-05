#!/usr/bin/env python3
"""Tests for 🔕 keeping the operating system's own sounds off the PA.

Run:  py -m unittest tests.player.test_system_sounds -v

The music and the OS share the one sound card, so an error ding goes out over
the hall's speakers. Each platform has one switch for exactly those sounds; the
danger is leaving it off after the evening — the OS keeps the change after the
app is gone — or turning back on a switch the operator had turned off by hand.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_syssnd_"))

from player import system_sounds  # noqa: E402
from player.audio_device import AudioDevice  # noqa: E402
from player.system_sounds import (  # noqa: E402
    LinuxBackend,
    MacBackend,
    SystemSoundGuard,
    WindowsBackend,
)


class _FakeWin32:
    """Stands in for player.system_sounds_win32: one mute flag per device.
    Device n has the endpoint id "devn" and hands out the handle n."""

    def __init__(self, muted):
        self.muted = dict(enumerate(muted, start=1))   # handle → muted?
        self.live = set()

    def system_sound_volumes(self):
        self.live |= set(self.muted)
        return [(f"dev{h}", h) for h in self.muted]

    def get_mute(self, vol):
        return self.muted[vol]

    def set_mute(self, vol, on):
        self.muted[vol] = on

    def release(self, vol):
        self.live.discard(vol)


class WindowsTest(unittest.TestCase):

    def test_mutes_every_device_and_puts_them_back(self):
        w = _FakeWin32([False, False])
        guard = SystemSoundGuard(WindowsBackend(w))
        self.assertTrue(guard.hold(True))
        self.assertEqual(w.muted, {1: True, 2: True})
        self.assertTrue(guard.hold(False))
        self.assertEqual(w.muted, {1: False, 2: False})
        self.assertEqual(w.live, set(), "every COM pointer released")

    def test_a_hand_muted_device_stays_muted(self):
        w = _FakeWin32([True, False])
        guard = SystemSoundGuard(WindowsBackend(w))
        guard.hold(True)
        guard.hold(False)
        self.assertEqual(w.muted, {1: True, 2: False})

    def test_nothing_to_mute_leaves_no_record(self):
        guard = SystemSoundGuard(WindowsBackend(_FakeWin32([True])))
        guard.hold(True)
        self.assertTrue(guard.active)
        self.assertIsNone(guard.record, "nothing for a crash repair to undo")

    def test_holding_twice_sweeps_once(self):
        w = _FakeWin32([False])
        guard = SystemSoundGuard(WindowsBackend(w))
        guard.hold(True)
        w.muted[1] = False          # the operator lifts it mid-evening
        self.assertFalse(guard.hold(True))
        self.assertFalse(w.muted[1], "not fought over every tick")

    def test_a_device_plugged_in_mid_evening_is_muted_too(self):
        """The PA's USB interface goes in after Playing mode started — or is
        knocked loose and plugged back in."""
        w = _FakeWin32([False])
        guard = SystemSoundGuard(WindowsBackend(w))
        guard.hold(True)
        w.muted[2] = False
        self.assertTrue(guard.hold(True), "the record changed: persist it")
        self.assertEqual(w.muted, {1: True, 2: True})
        self.assertEqual(guard.record, ["dev1", "dev2"])
        guard.hold(False)
        self.assertEqual(w.muted, {1: False, 2: False})
        self.assertEqual(w.live, set(), "every COM pointer released")

    def test_a_hand_muted_device_plugged_in_later_stays_muted(self):
        w = _FakeWin32([False])
        guard = SystemSoundGuard(WindowsBackend(w))
        guard.hold(True)
        w.muted[2] = True
        self.assertFalse(guard.hold(True))
        guard.hold(False)
        self.assertEqual(w.muted, {1: False, 2: True})

    def test_crash_repair_unmutes_only_what_it_had_muted(self):
        """A device the operator had muted by hand stays muted after a crash."""
        w = _FakeWin32([True, True])
        SystemSoundGuard(WindowsBackend(w)).restore_leftover(["dev2"])
        self.assertEqual(w.muted, {1: True, 2: False})
        self.assertEqual(w.live, set())

    def test_crash_repair_of_an_old_count_record_unmutes_all(self):
        """Settings written before the ids were kept hold only a count."""
        w = _FakeWin32([True, True])
        SystemSoundGuard(WindowsBackend(w)).restore_leftover(2)
        self.assertEqual(w.muted, {1: False, 2: False})

    def test_unreachable_core_audio_is_harmless(self):
        w = _FakeWin32([False])
        w.system_sound_volumes = mock.Mock(side_effect=OSError("no audio"))
        guard = SystemSoundGuard(WindowsBackend(w))
        guard.hold(True)
        guard.hold(False)
        self.assertIsNone(guard.record)


class MacTest(unittest.TestCase):

    def _run(self, alert):
        calls = []

        def run(*cmd):
            calls.append(cmd[-1])
            return str(alert) if cmd[-1].startswith("alert volume") else ""
        return calls, mock.patch.object(system_sounds, "_run", side_effect=run)

    def test_alert_volume_goes_to_zero_and_back_to_its_level(self):
        calls, patch = self._run(65)
        with patch:
            guard = SystemSoundGuard(MacBackend())
            guard.hold(True)
            self.assertEqual(guard.record, 65)
            guard.hold(False)
        self.assertEqual(calls[1:], ["set volume alert volume 0",
                                     "set volume alert volume 65"])

    def test_an_already_silent_alert_is_not_raised_afterwards(self):
        calls, patch = self._run(0)
        with patch:
            guard = SystemSoundGuard(MacBackend())
            guard.hold(True)
            guard.hold(False)
        self.assertEqual(calls, ["alert volume of (get volume settings)"])

    def test_crash_repair_restores_the_stored_level(self):
        calls, patch = self._run(0)
        with patch:
            SystemSoundGuard(MacBackend()).restore_leftover(40)
        self.assertEqual(calls, ["set volume alert volume 40"])

    def test_no_osascript_changes_nothing(self):
        with mock.patch.object(system_sounds, "_run", return_value=None):
            guard = SystemSoundGuard(MacBackend())
            guard.hold(True)
        self.assertIsNone(guard.record)


class LinuxTest(unittest.TestCase):

    def test_event_sounds_off_and_back_on(self):
        calls = []

        def run(*cmd):
            calls.append(cmd)
            return "true" if cmd[1] == "get" else ""
        with mock.patch.object(system_sounds, "_run", side_effect=run):
            guard = SystemSoundGuard(LinuxBackend())
            guard.hold(True)
            guard.hold(False)
        key = ("org.gnome.desktop.sound", "event-sounds")
        self.assertEqual(calls, [("gsettings", "get", *key),
                                 ("gsettings", "set", *key, "false"),
                                 ("gsettings", "set", *key, "true")])

    def test_event_sounds_already_off_are_left_off(self):
        with mock.patch.object(system_sounds, "_run",
                               return_value="false") as run:
            guard = SystemSoundGuard(LinuxBackend())
            guard.hold(True)
            guard.hold(False)
        self.assertEqual(run.call_count, 1)

    def test_no_gnome_schema_changes_nothing(self):
        with mock.patch.object(system_sounds, "_run", return_value=None):
            guard = SystemSoundGuard(LinuxBackend())
            guard.hold(True)
        self.assertIsNone(guard.record)


class BackendChoiceTest(unittest.TestCase):

    def _choose(self, platform, which="/usr/bin/tool"):
        env = {k: v for k, v in os.environ.items()
               if k != "DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(system_sounds.sys, "platform", platform), \
                mock.patch.object(system_sounds.shutil, "which",
                                  return_value=which):
            return system_sounds.default_backend()

    def test_each_platform_gets_its_backend(self):
        self.assertIsInstance(self._choose("darwin"), MacBackend)
        self.assertIsInstance(self._choose("linux"), LinuxBackend)
        self.assertIsNone(self._choose("darwin", which=None))
        self.assertIsNone(self._choose("linux", which=None))
        self.assertIsNone(self._choose("freebsd"))

    def test_the_suite_never_touches_the_real_machine(self):
        self.assertTrue(os.environ.get("DANCEPLAYLIST_KEEP_SYSTEM_SOUNDS"))
        self.assertIsNone(system_sounds.default_backend())
        guard = SystemSoundGuard()
        self.assertFalse(guard.hold(True))


class _Desk:
    """The device's system-sound half and the two facts it asks about."""

    def __init__(self, w, playing=False, busy=False):
        self.settings = {}
        self.playing = playing
        self.busy = busy
        self.device = AudioDevice(
            None, None, None, None,
            mix=None,
            settings=lambda: self.settings,
            cart_voices=lambda: None,
            is_playing_mode=lambda: self.playing,
            apply_volume=lambda: None,
            system_sounds=SystemSoundGuard(WindowsBackend(w)))
        # Without a player the device counts itself busy; here that is a knob.
        self.device.busy = lambda: self.busy


@mock.patch("player.audio_device.save_settings")
class DeskTest(unittest.TestCase):

    def test_playing_mode_mutes_even_between_titles(self, _save):
        w = _FakeWin32([False])
        desk = _Desk(w, playing=True, busy=False)
        desk.device.watch_system_sounds()
        self.assertTrue(w.muted[1])
        self.assertEqual(desk.settings["system_sounds_muted"], ["dev1"])

    def test_a_device_arriving_is_saved_for_the_crash_repair(self, save):
        w = _FakeWin32([False])
        desk = _Desk(w, playing=True)
        desk.device.watch_system_sounds()
        w.muted[2] = False
        desk.device.watch_system_sounds()
        self.assertEqual(desk.settings["system_sounds_muted"], ["dev1", "dev2"])
        self.assertEqual(save.call_count, 2)

    def test_back_to_planning_and_silent_puts_them_back(self, _save):
        w = _FakeWin32([False])
        desk = _Desk(w, playing=True)
        desk.device.watch_system_sounds()
        desk.playing = False
        desk.device.watch_system_sounds()
        self.assertFalse(w.muted[1])
        self.assertNotIn("system_sounds_muted", desk.settings)

    def test_a_preview_in_planning_mutes_too(self, _save):
        w = _FakeWin32([False])
        desk = _Desk(w, busy=True)
        desk.device.watch_system_sounds()
        self.assertTrue(w.muted[1])

    def test_switched_off_in_settings(self, _save):
        w = _FakeWin32([False])
        desk = _Desk(w, playing=True)
        desk.settings["mute_system_sounds"] = False
        desk.device.watch_system_sounds()
        self.assertFalse(w.muted[1])

    def test_record_is_saved_only_on_a_change(self, save):
        desk = _Desk(_FakeWin32([False]), playing=True)
        desk.device.watch_system_sounds()
        desk.device.watch_system_sounds()
        self.assertEqual(save.call_count, 1)


if __name__ == "__main__":
    unittest.main()
