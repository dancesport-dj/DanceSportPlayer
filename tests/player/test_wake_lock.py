#!/usr/bin/env python3
"""☀ Keeping the screen awake while the desk is working.

Windows counts idle time from the mouse and the keyboard, never from what comes
out of the speakers — so a tournament that nobody touches for an hour blanks
the screen and starts the screensaver, on the presenter beamer as well. The
desk holds the timeout off while music plays or the presenter screen stands,
and hands it back the moment neither does — on Windows through
SetThreadExecutionState, on macOS through a caffeinate that dies with the app.

Run:  py -m unittest tests.player.test_wake_lock -v
"""

import unittest

from shared import playback
from player import main_player
from player.main_player import PlayerControlMixin


class _Panel:
    def __init__(self, awake=True):
        self._awake = awake

    def keep_awake(self):
        return self._awake


class WakeLockTest(unittest.TestCase):
    """`_refresh_wake_lock` against the two things that can want the screen."""

    def setUp(self):
        self.calls = []
        real = main_player.keep_display_awake

        def fake(on):
            self.calls.append(on)
            return self.answer

        self.answer = True
        main_player.keep_display_awake = fake
        self.addCleanup(setattr, main_player, "keep_display_awake", real)

        self.win = PlayerControlMixin.__new__(PlayerControlMixin)
        self.win._play_panel = _Panel()
        self.win._presenter = None
        self.win._awake_held = False
        self.playing = False
        self.win._is_player_running = lambda: self.playing

    def test_music_on_the_speakers_holds_the_screen(self):
        self.playing = True
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True])
        self.assertTrue(self.win._awake_held)

    def test_a_standing_presenter_screen_holds_it_without_music(self):
        """The beamer shows the running order between heats too — blanking it
        there is exactly as wrong as blanking it during one."""
        self.win._presenter = object()
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True])

    def test_with_neither_the_machine_gets_its_timeouts_back(self):
        self.playing = True
        self.win._refresh_wake_lock()
        self.playing = False
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True, False])
        self.assertFalse(self.win._awake_held)

    def test_the_switch_off_means_off(self):
        self.win._play_panel = _Panel(awake=False)
        self.playing = True
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [])

    def test_switching_it_off_mid_song_releases_the_hold(self):
        self.playing = True
        self.win._refresh_wake_lock()
        self.win._play_panel._awake = False
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True, False])

    def test_only_the_changes_reach_the_os(self):
        """Every playback edge calls in, and a track switch passes through
        Stopped — no reason to hand the timeout back and take it again."""
        self.playing = True
        for _ in range(4):
            self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True])

    def test_a_refused_hold_is_tried_again_next_time(self):
        """Nothing is held, so nothing may be remembered as held — otherwise a
        single refusal at startup would leave the screen unprotected all day."""
        self.answer = False
        self.playing = True
        self.win._refresh_wake_lock()
        self.assertFalse(self.win._awake_held)
        self.win._refresh_wake_lock()
        self.assertEqual(self.calls, [True, True])


class _Caffeinate:
    """Stand-in for the caffeinate child process."""

    def __init__(self, argv):
        self.argv = argv
        self.alive = True
        self.terminated = False

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.terminated = True
        self.alive = False


class MacWakeLockTest(unittest.TestCase):
    """macOS holds the screen with `caffeinate` — the assertion Apple ships."""

    def setUp(self):
        self.started = []

        def fake_popen(argv):
            self.started.append(_Caffeinate(argv))
            return self.started[-1]

        real_popen = playback.subprocess.Popen
        playback.subprocess.Popen = fake_popen
        self.addCleanup(setattr, playback.subprocess, "Popen", real_popen)
        self.addCleanup(setattr, playback, "_CAFFEINATE", None)
        playback._CAFFEINATE = None

    def test_it_holds_the_display_and_the_machine(self):
        self.assertTrue(playback._awake_macos(True))
        argv = self.started[0].argv
        self.assertEqual(argv[0], "caffeinate")
        self.assertIn("-d", argv)     # the display assertion
        self.assertIn("-i", argv)     # …and no idle sleep either

    def test_the_helper_dies_with_the_app(self):
        """-w <our pid>: a crash on our side must not leave the screen pinned
        on until somebody reboots the machine."""
        import os
        playback._awake_macos(True)
        argv = self.started[0].argv
        self.assertEqual(argv[argv.index("-w") + 1], str(os.getpid()))

    def test_releasing_it_ends_the_helper(self):
        playback._awake_macos(True)
        playback._awake_macos(False)
        self.assertTrue(self.started[0].terminated)
        self.assertIsNone(playback._CAFFEINATE)

    def test_a_second_arm_does_not_start_a_second_helper(self):
        playback._awake_macos(True)
        playback._awake_macos(True)
        self.assertEqual(len(self.started), 1)

    def test_a_helper_that_died_is_replaced(self):
        playback._awake_macos(True)
        self.started[0].alive = False
        playback._awake_macos(True)
        self.assertEqual(len(self.started), 2)

    def test_releasing_without_a_helper_is_no_error(self):
        self.assertTrue(playback._awake_macos(False))
        self.assertEqual(self.started, [])



if __name__ == "__main__":
    unittest.main(verbosity=2)
