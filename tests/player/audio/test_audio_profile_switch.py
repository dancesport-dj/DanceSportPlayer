#!/usr/bin/env python3
"""🎧 Switching the audio profile moves every source at once.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_audio_profile_switch -v

A tournament profile (music on the PA, pre-listen on the headphones) and a
rehearsal one (everything on the headphones) are one click apart. The switch
changes "audio_outputs" and puts every source where it now belongs — nothing
waits for a dialog or a restart.
"""
import unittest
from unittest import mock

from shared.audio import profiles
from tests.player.audio.test_audio_outputs import SPEAKERS, USB12, USB34, _Desk, _Test


def _desk_with_two_profiles():
    desk = _Desk()
    desk.choose("music", USB12)
    desk.choose("cue", USB34)
    profiles.save_profile(desk.settings, "Tournament", desk.settings["audio_outputs"])
    desk.settings["audio_outputs"] = {}
    desk.choose("music", USB34)
    profiles.save_profile(desk.settings, "Rehearsal", desk.settings["audio_outputs"], private=True)
    profiles.switch_profile(desk.settings, "Tournament")
    desk.device.sync()
    return desk


@mock.patch("player.audio.audio_device.save_settings", return_value=True)
class SwitchTest(_Test):

    def test_the_music_and_the_sources_following_it_move_to_the_new_output(self, _save):
        desk = _desk_with_two_profiles()
        self.assertEqual(desk.where(), {"music": USB12, "cartwall": USB12, "announcer": USB12})
        self.assertTrue(desk.device.switch_profile("Rehearsal"))
        self.assertEqual(desk.where(), {"music": USB34, "cartwall": USB34, "announcer": USB34})

    def test_the_pre_listen_choice_goes_with_the_profile(self, _save):
        desk = _desk_with_two_profiles()
        self.assertIs(desk.device.cue_device(), USB34)
        desk.device.switch_profile("Rehearsal")
        self.assertIsNone(desk.device.cue_device())   # "Same as the music"
        desk.device.switch_profile("Tournament")
        self.assertIs(desk.device.cue_device(), USB34)

    def test_the_switch_is_saved(self, save):
        desk = _desk_with_two_profiles()
        desk.device.switch_profile("Rehearsal")
        save.assert_called_once_with(desk.settings)
        self.assertEqual(profiles.active_profile(desk.settings), "Rehearsal")

    def test_an_unknown_profile_moves_and_saves_nothing(self, save):
        desk = _desk_with_two_profiles()
        before = desk.where()
        self.assertFalse(desk.device.switch_profile("Nope"))
        self.assertEqual(desk.where(), before)
        save.assert_not_called()

    def test_switching_to_the_active_profile_does_not_reopen_the_card(self, _save):
        desk = _desk_with_two_profiles()
        moves = desk.music.moves
        desk.device.switch_profile("Tournament")
        self.assertEqual(desk.music.moves, moves)

    def test_a_failed_save_still_switches_for_this_run(self, save):
        save.return_value = False
        desk = _desk_with_two_profiles()
        self.assertTrue(desk.device.switch_profile("Rehearsal"))
        self.assertEqual(desk.music.dev, USB34)

    def test_a_profile_pointing_at_an_unplugged_card_plays_on_the_default(self, _save):
        desk = _desk_with_two_profiles()
        desk.devices.outputs.remove(USB34)
        desk.device.switch_profile("Rehearsal")
        self.assertEqual(desk.music.dev, SPEAKERS)
        self.assertEqual(desk.device.unplugged(), [("music", "Out 3/4 (USB interface)")])

    def test_a_hall_profile_is_no_rehearsal(self, _save):
        desk = _desk_with_two_profiles()
        self.assertIsNone(desk.device.rehearsal_profile())

    def test_a_rehearsal_profile_names_itself(self, _save):
        desk = _desk_with_two_profiles()
        desk.device.switch_profile("Rehearsal")
        self.assertEqual(desk.device.rehearsal_profile(), "Rehearsal")
        desk.device.switch_profile("Tournament")
        self.assertIsNone(desk.device.rehearsal_profile())

    def test_without_profiles_there_is_no_rehearsal(self, _save):
        self.assertIsNone(_Desk().device.rehearsal_profile())


if __name__ == "__main__":
    unittest.main()
