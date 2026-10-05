#!/usr/bin/env python3
"""Tests for the ref-counted music duck (`OutputMix.duck_reason`).

Run:  py -m unittest tests.player.test_cartwall_duck -v

Two things pull the music down: a spoken announcement and a 🎛 cartwall pad. The
target used to be assigned bare, so whichever of them ended first lifted the
music back up over the other — a fanfare firing mid-announcement and then ending
would leave the announcer competing with full-level music. The reasons are held
in a set, so the music only comes back when the last one is gone.

The duck is arithmetic, so this runs on the mix itself: no QApplication, no
offscreen platform, no desk stripped down to the handful of attributes the ramp
happened to read.
"""

import unittest

from player.mix import (
    OutputMix,
    _ANNOUNCE_DUCK,
    _CART_DUCK,
    _DUCK_DOWN_MS,
    _DUCK_UP_MS,
)


class DuckReasonTest(unittest.TestCase):
    def setUp(self):
        self.m = OutputMix()

    def test_the_announcer_alone_ducks_and_lifts(self):
        self.m.duck_reason("announce", True)
        self.assertEqual(self.m.duck_target, _ANNOUNCE_DUCK)
        self.m.duck_reason("announce", False)
        self.assertEqual(self.m.duck_target, 1.0)

    def test_a_pad_alone_ducks_and_lifts(self):
        self.m.duck_reason("cartwall", True)
        self.assertEqual(self.m.duck_target, _CART_DUCK)
        self.m.duck_reason("cartwall", False)
        self.assertEqual(self.m.duck_target, 1.0)

    def test_the_announcer_ending_first_leaves_the_pad_ducking(self):
        """The regression the ref-count exists for."""
        self.m.duck_reason("announce", True)
        self.m.duck_reason("cartwall", True)
        self.m.duck_reason("announce", False)
        self.assertEqual(self.m.duck_target, _CART_DUCK)
        self.m.duck_reason("cartwall", False)
        self.assertEqual(self.m.duck_target, 1.0)

    def test_the_pad_ending_first_leaves_the_announcer_ducking(self):
        self.m.duck_reason("cartwall", True)
        self.m.duck_reason("announce", True)
        self.m.duck_reason("cartwall", False)
        self.assertEqual(self.m.duck_target, _ANNOUNCE_DUCK)
        self.m.duck_reason("announce", False)
        self.assertEqual(self.m.duck_target, 1.0)

    def test_a_pad_pulls_deeper_than_the_announcer(self):
        """A fanfare over music that only sat back 10 dB was lost in it: the
        pad takes the music down about 20 dB, the voice keeps its softer duck."""
        self.assertLess(_CART_DUCK, _ANNOUNCE_DUCK)
        self.assertAlmostEqual(_CART_DUCK, 0.1)

    def test_both_on_take_the_deeper_duck(self):
        for first, second in (("announce", "cartwall"), ("cartwall", "announce")):
            m = OutputMix()
            m.duck_reason(first, True)
            m.duck_reason(second, True)
            self.assertEqual(m.duck_target, _CART_DUCK, (first, second))

    def test_an_unbalanced_off_cannot_strand_the_music(self):
        """The announcer's give-up watchdog can report `off` twice; a counter
        would go negative and leave the music pinned down."""
        self.m.duck_reason("announce", False)
        self.m.duck_reason("announce", False)
        self.m.duck_reason("announce", True)
        self.m.duck_reason("announce", False)
        self.assertEqual(self.m.duck_target, 1.0)
        self.assertEqual(self.m.duck_reasons, set())

    def test_the_same_reason_twice_is_still_one_reason(self):
        self.m.duck_reason("cartwall", True)
        self.m.duck_reason("cartwall", True)
        self.m.duck_reason("cartwall", False)
        self.assertEqual(self.m.duck_target, 1.0)

    def test_ducking_aims_rather_than_jumps(self):
        self.m.duck_reason("cartwall", True)
        self.assertEqual(self.m.duck, 1.0, "no hard jump — it ramps")
        self.assertFalse(self.m.settled, "…so the caller knows to run the ramp")

    def test_down_is_faster_than_up(self):
        """A pad must not bury its own first transient; the music comes back
        slowly so the return is not itself an event."""
        self.m.duck_reason("cartwall", True)
        self.m.step()
        down = 1.0 - self.m.duck
        self.m.duck = _ANNOUNCE_DUCK
        self.m.duck_reason("cartwall", False)
        self.m.step()
        up = self.m.duck - _ANNOUNCE_DUCK
        self.assertGreater(down, up)
        self.assertAlmostEqual(down / up, _DUCK_UP_MS / _DUCK_DOWN_MS, places=3)

    def test_the_ramp_arrives_and_settles(self):
        """A ramp that overshot or never quite landed would keep the 25 ms timer
        running for the rest of the session."""
        self.m.duck_reason("announce", True)
        for _ in range(1000):
            if self.m.settled:
                break
            self.m.step()
        self.assertTrue(self.m.settled)
        self.assertEqual(self.m.duck, _ANNOUNCE_DUCK)


class OutputLevelTest(unittest.TestCase):
    """Which factor reaches which output — the three formulas that used to be
    spelled out at three call sites."""

    def setUp(self):
        self.m = OutputMix(0.8)

    def test_the_deck_hears_every_factor(self):
        self.m.gain, self.m.fade, self.m.duck, self.m.desk = 0.5, 0.5, 0.5, 0.5
        self.assertAlmostEqual(self.m.deck(), 0.8 * 0.0625)

    def test_the_pads_follow_the_fader_and_the_desk_duck(self):
        self.m.desk = 0.2
        self.assertAlmostEqual(self.m.cartwall(), 0.8 * 0.2)

    def test_the_pads_ignore_the_duck_they_cause(self):
        """A pad ducking the music must not duck itself — that was the point."""
        self.m.duck = _ANNOUNCE_DUCK
        self.assertAlmostEqual(self.m.cartwall(), 0.8)

    def test_the_pads_ignore_the_running_title_s_own_level(self):
        self.m.gain, self.m.fade = 0.3, 0.4
        self.assertAlmostEqual(self.m.cartwall(), 0.8)

    def test_the_filler_carries_the_announcement_duck(self):
        """The announcer speaks over the filler — that is what the break is for."""
        self.m.duck = 0.5
        self.assertAlmostEqual(self.m.filler(1.0), 0.8 * 0.5)

    def test_the_filler_ignores_the_deck_s_gain_and_fade(self):
        """No deck title is running: its loudness correction means nothing."""
        self.m.gain, self.m.fade = 0.25, 0.25
        self.assertAlmostEqual(self.m.filler(0.5), 0.4)

    def test_the_filler_takes_its_own_fade(self):
        self.m.filler_fade = 0.5
        self.assertAlmostEqual(self.m.filler(1.0), 0.4)

    def test_a_level_never_leaves_the_range(self):
        """A broken R128 measurement may push the gain over 1 — a blast at the
        desk is worse than a wrong level."""
        self.m.base, self.m.gain = 1.0, 2.8
        self.assertEqual(self.m.deck(), 1.0)

    def test_the_master_fader_is_clamped_where_it_is_set(self):
        self.m.set_base(1.7)
        self.assertEqual(self.m.base, 1.0)
        self.m.set_base(-0.2)
        self.assertEqual(self.m.base, 0.0)

    def test_the_desk_duck_pulls_and_releases(self):
        self.assertLess(self.m.set_desk_duck(True), 1.0)
        self.assertEqual(self.m.set_desk_duck(False), 1.0)


class GainRampTest(unittest.TestCase):
    """The 📊 loudness gain reaches the mix three ways, and they differ in
    whether the hall can hear the change happen."""

    def setUp(self):
        self.m = OutputMix()

    def test_a_load_takes_the_gain_outright(self):
        self.m.load_gain(0.4)
        self.assertEqual((self.m.gain, self.m.gain_target), (0.4, 0.4))
        self.assertTrue(self.m.settled, "nothing to ramp before the first sample")

    def test_a_load_cancels_a_ramp_aimed_at_the_previous_title(self):
        self.m.ramp_gain_to(0.5)
        self.m.load_gain(1.2)
        self.assertEqual(self.m.gain, 1.2)
        self.assertTrue(self.m.settled)

    def test_a_resume_snaps_and_says_so(self):
        """The music is silent at that moment, so the change is inaudible."""
        self.assertTrue(self.m.snap_gain(0.5))
        self.assertEqual(self.m.gain, 0.5)
        self.assertTrue(self.m.settled)

    def test_an_unchanged_resume_touches_nothing(self):
        self.assertFalse(self.m.snap_gain(1.002))
        self.assertEqual(self.m.gain, 1.0)

    def test_a_late_measurement_ramps_instead_of_stepping(self):
        self.assertTrue(self.m.ramp_gain_to(0.5))
        self.assertEqual(self.m.gain, 1.0, "a step under running music clicks")
        self.m.step()
        self.assertLess(self.m.gain, 1.0)
        self.assertGreater(self.m.gain, 0.5)

    def test_a_late_measurement_that_agrees_is_left_alone(self):
        self.assertFalse(self.m.ramp_gain_to(1.005))

    def test_the_gain_reports_the_step_it_lands_on(self):
        """The player card shows the gain as a dB readout and wants telling once,
        when the number stops moving."""
        self.m.ramp_gain_to(0.5)
        landings = [self.m.step() for _ in range(200)]
        self.assertEqual(landings.count(True), 1)
        self.assertEqual(self.m.gain, 0.5)

    def test_both_ramps_run_at_once(self):
        """An announcement over a title whose measurement just landed."""
        self.m.duck_reason("announce", True)
        self.m.ramp_gain_to(0.5)
        self.m.step()
        self.assertLess(self.m.duck, 1.0)
        self.assertLess(self.m.gain, 1.0)


if __name__ == "__main__":
    unittest.main()
