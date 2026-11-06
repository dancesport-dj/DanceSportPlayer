#!/usr/bin/env python3
"""🎧 When a loud music volume on a headset is stepped in on.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.audio.test_headset_guard -v
"""
import unittest

from player.audio.headset_guard import (
    ASK,
    LOUD,
    LOWER,
    LOWER_FULL,
    SAFE,
    SAFE_FULL,
    WARN,
    HeadsetGuard,
    is_headset,
    lower_volume,
    safe_volume,
)


class IsHeadsetTest(unittest.TestCase):
    def test_names_that_say_head(self):
        for name in ("Headphones (Realtek Audio)", "Kopfhörer (Realtek)",
                     "Headset Earphone (USB)", "AirPods Pro", "Galaxy Buds2",
                     "Hands-Free AG Audio"):
            self.assertTrue(is_headset(name), name)

    def test_speakers_and_cards_are_not(self):
        for name in ("Speakers (Realtek Audio)", "Lautsprecher (Realtek)",
                     "MAYA44 USB", "", None):
            self.assertFalse(is_headset(name), name)


class FormFactorTest(unittest.TestCase):
    def test_the_driver_says_headphones_or_headset(self):
        # "Lautsprecher (Senary Audio)" is not worn, "Kopfhoerer (Senary Audio)" is.
        self.assertTrue(is_headset("Anything", 3))
        self.assertTrue(is_headset("Anything", 5))

    def test_a_line_level_interface_is_never_a_headset(self):
        # An audio interface like a Maya, whatever its name says; also S/PDIF, HDMI.
        for form in (0, 2, 8, 9):
            self.assertFalse(is_headset("Maya44 USB Headphones out", form), form)

    def test_the_mac_headphone_jack_is_asked_about_only_at_100_percent(self):
        # A powered speaker on a cinch cable shows up as "External Headphones".
        for name in ("External Headphones", "Externe Kopfhörer"):
            self.assertFalse(is_headset(name), name)
            self.assertFalse(is_headset(name, None, 0.9), name)
            self.assertTrue(is_headset(name, None, 1.0), name)
        guard = HeadsetGuard()
        self.assertIsNone(guard.assess("External Headphones", 0.9, 1.0))
        self.assertEqual(guard.assess("External Headphones", 1.0, 1.0), ASK)
        guard.remember(1.0)
        self.assertIsNone(guard.assess("External Headphones", 0.5, 1.0))
        self.assertEqual(guard.assess("External Headphones", 1.0, 1.0), WARN)
        self.assertTrue(is_headset("AirPods Pro"))
        self.assertTrue(is_headset("USB Headset"))

    def test_a_usb_headset_reporting_speakers_is_still_found_by_its_name(self):
        self.assertTrue(is_headset("Lautsprecher (3- Logi USB Headset H340)", 1))
        self.assertFalse(is_headset("Lautsprecher (Senary Audio)", 1))
        self.assertFalse(is_headset("Speakers (Maya44 USB)", None))


class HeadsetGuardTest(unittest.TestCase):
    def test_a_loud_headset_asks_the_first_time(self):
        self.assertEqual(HeadsetGuard().assess("Headphones", 0.9), ASK)

    def test_above_70_percent_is_loud_70_itself_is_not(self):
        g = HeadsetGuard()
        self.assertIsNone(g.assess("Headphones", LOUD))
        self.assertEqual(g.assess("Headphones", LOUD + 0.05), ASK)

    def test_a_quiet_headset_or_a_loud_speaker_is_left_alone(self):
        g = HeadsetGuard()
        self.assertIsNone(g.assess("Headphones", LOUD - 0.01))
        self.assertIsNone(g.assess("Speakers", 1.0))

    def test_a_level_asked_about_gets_a_toast_not_a_question(self):
        g = HeadsetGuard()
        self.assertEqual(g.assess("Headphones", 1.0), ASK)
        g.remember(1.0)          # asked at 100/100, the user chose 70
        self.assertIsNone(g.assess("Headphones", SAFE))        # now at 70
        self.assertEqual(g.assess("Headphones", 1.0), WARN)    # raised again
        self.assertIsNone(g.assess("Headphones", 1.0))         # once per level

    def test_a_louder_level_than_any_asked_asks_again(self):
        g = HeadsetGuard()
        g.remember(0.9)
        self.assertEqual(g.assess("Headphones", 0.85), WARN)
        self.assertEqual(g.assess("Headphones", 1.0), ASK)   # 100 % on both

    def test_the_windows_slider_counts_with_the_app_fader(self):
        g = HeadsetGuard()
        self.assertIsNone(g.assess("Headphones", 1.0, 0.07))
        self.assertEqual(g.assess("Headphones", 1.0, 1.0), ASK)
        self.assertEqual(g.assess("Headphones", 1.0, 0.9), ASK)   # 90 % on the slider

    def test_safe_volume_is_the_safe_level_over_the_slider(self):
        self.assertEqual(safe_volume(1.0), SAFE)
        self.assertAlmostEqual(safe_volume(0.9) * 0.9, SAFE)
        self.assertEqual(safe_volume(0.3), 1.0)
        self.assertEqual(safe_volume(1.0, 1.0), SAFE_FULL)
        self.assertEqual(lower_volume(1.0, 1.0), LOWER_FULL)
        self.assertAlmostEqual(lower_volume(0.9, 0.9) * 0.9, LOWER)

    def test_the_safe_level_is_below_the_loud_one(self):
        self.assertLessEqual(SAFE, LOUD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
