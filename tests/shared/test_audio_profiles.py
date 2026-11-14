#!/usr/bin/env python3
"""🎧 Audio output profiles: named sets of "audio_outputs".

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_audio_profiles -v

A tournament runs the music on the PA card and pre-listen on the headphones;
the evening's preparation runs everything on the headphones. A profile is one
of those sets by name. "audio_outputs" stays what the rest of the app reads: it
always mirrors the active profile, so nothing else has to know profiles exist.
A private profile (rehearsal: the hall hears nothing) is never kept across a
restart — a silent PA at the tournament is the mistake this guards against.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from planner.store import JsonStore
from shared.audio import profiles

HALL = {"music": {"id": "aa", "name": "PA"}, "cue": {"id": "bb", "name": "Phones"}}
HOME = {"music": {"id": "bb", "name": "Phones"}}


def _settings(**extra):
    s = {"audio_outputs": dict(HALL)}
    s.update(extra)
    return s


class SaveTest(unittest.TestCase):

    def test_saving_makes_the_profile_active_and_stores_a_copy(self):
        s = _settings()
        profiles.save_profile(s, "Tournament", s["audio_outputs"])
        self.assertEqual(profiles.profile_names(s), ["Tournament"])
        self.assertEqual(profiles.active_profile(s), "Tournament")
        s["audio_outputs"]["music"]["id"] = "zz"
        self.assertEqual(s["audio_profiles"]["Tournament"]["outputs"]["music"]["id"], "aa")

    def test_saving_over_a_name_replaces_it(self):
        s = _settings()
        profiles.save_profile(s, "A", HALL)
        profiles.save_profile(s, "A", HOME, private=True)
        self.assertEqual(profiles.profile_names(s), ["A"])
        self.assertTrue(profiles.is_private(s, "A"))
        self.assertEqual(s["audio_outputs"], HOME)

    def test_a_blank_name_is_refused(self):
        s = _settings()
        self.assertFalse(profiles.save_profile(s, "   ", HALL))
        self.assertEqual(profiles.profile_names(s), [])


class SwitchTest(unittest.TestCase):

    def _two(self):
        s = _settings()
        profiles.save_profile(s, "Tournament", HALL)
        profiles.save_profile(s, "Evening", HOME, private=True)
        return s

    def test_switching_puts_that_profiles_outputs_where_the_app_reads_them(self):
        s = self._two()
        self.assertTrue(profiles.switch_profile(s, "Tournament"))
        self.assertEqual(s["audio_outputs"], HALL)
        self.assertEqual(profiles.active_profile(s), "Tournament")

    def test_switching_does_not_alias_the_stored_profile(self):
        s = self._two()
        profiles.switch_profile(s, "Tournament")
        s["audio_outputs"]["music"]["id"] = "zz"
        self.assertEqual(s["audio_profiles"]["Tournament"]["outputs"]["music"]["id"], "aa")

    def test_an_unknown_profile_changes_nothing(self):
        s = self._two()
        before = dict(s["audio_outputs"])
        self.assertFalse(profiles.switch_profile(s, "Nope"))
        self.assertEqual(s["audio_outputs"], before)
        self.assertEqual(profiles.active_profile(s), "Evening")

    def test_deleting_the_active_profile_keeps_the_outputs_and_clears_active(self):
        s = self._two()
        profiles.delete_profile(s, "Evening")
        self.assertEqual(profiles.profile_names(s), ["Tournament"])
        self.assertIsNone(profiles.active_profile(s))
        self.assertEqual(s["audio_outputs"], HOME)


class ClearTest(unittest.TestCase):

    def test_clearing_unlinks_the_active_profile_and_keeps_everything_else(self):
        s = _settings()
        profiles.save_profile(s, "Tournament", HALL)
        profiles.clear_active(s)
        self.assertIsNone(profiles.active_profile(s))
        self.assertEqual(profiles.profile_names(s), ["Tournament"])
        self.assertEqual(s["audio_outputs"], HALL)

    def test_clearing_with_nothing_active_is_harmless(self):
        s = _settings()
        profiles.clear_active(s)
        self.assertIsNone(profiles.active_profile(s))


class PrivateTest(unittest.TestCase):

    def test_nothing_is_private_without_profiles(self):
        self.assertFalse(profiles.is_private(_settings()))

    def test_the_active_profile_decides_by_default(self):
        s = _settings()
        profiles.save_profile(s, "Rehearsal", HOME, private=True)
        self.assertTrue(profiles.is_private(s))
        profiles.save_profile(s, "Tournament", HALL)
        self.assertFalse(profiles.is_private(s))

    def test_garbage_in_the_settings_file_is_not_private(self):
        s = _settings(audio_profiles={"X": "not a dict", "Y": {"private": "yes"}},
                      audio_profile="X")
        self.assertFalse(profiles.is_private(s))
        self.assertEqual(profiles.profile_names(s), ["Y"])


class BuiltinTest(unittest.TestCase):
    """Main and Rehearsal always exist; Rehearsal is private by definition."""

    def test_a_settings_dict_gets_main_and_rehearsal(self):
        s = _settings()
        self.assertTrue(profiles.ensure_builtin(s))
        self.assertEqual(profiles.profile_names(s), ["Main", "Rehearsal"])

    def test_main_is_seeded_from_the_outputs_in_force_and_made_active(self):
        s = _settings()
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"], HALL)
        self.assertEqual(profiles.active_profile(s), "Main")
        self.assertEqual(s["audio_outputs"], HALL)

    def test_main_does_not_alias_the_outputs_in_force(self):
        s = {"audio_outputs": copy.deepcopy(HALL)}   # not _settings(): HALL stays whole
        profiles.ensure_builtin(s)
        s["audio_outputs"]["music"]["id"] = "zz"
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"]["music"]["id"], "aa")

    def test_main_is_not_seeded_from_a_private_profile_left_active(self):
        """An old file left on a rehearsal: its outputs in force are the
        headphones, and a Main made of them would be a hall that is silent."""
        s = {}
        profiles.save_profile(s, "Tournament", HALL)
        profiles.save_profile(s, "Practice", HOME, private=True)   # active, private
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"], HALL)
        self.assertEqual(profiles.active_profile(s), "Practice", "the active one is not moved")

    def test_main_is_empty_when_a_private_profile_is_all_there_is(self):
        s = {}
        profiles.save_profile(s, "Practice", HOME, private=True)
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"], {})

    def test_rehearsal_puts_everything_on_the_prelisten_output(self):
        s = _settings()
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Rehearsal"]["outputs"],
                         {"music": HALL["cue"]})

    def test_rehearsal_without_a_prelisten_output_starts_empty(self):
        s = {"audio_outputs": dict(HOME)}
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Rehearsal"]["outputs"], {})

    def test_it_is_idempotent(self):
        s = _settings()
        profiles.ensure_builtin(s)
        before = copy.deepcopy(s)
        self.assertFalse(profiles.ensure_builtin(s))
        self.assertEqual(s, before)

    def test_an_existing_main_is_not_overwritten(self):
        s = _settings()
        profiles.save_profile(s, "Main", HOME)
        profiles.ensure_builtin(s)
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"], HOME)

    def test_a_vanished_active_profile_falls_back_to_main(self):
        """A hand-edited file names a profile that is not in it: Settings opened
        on Main while the status bar said "(no profile)". Main takes over at the
        start, and its outputs with it: the profile shown is the one that plays."""
        s = _settings()
        profiles.ensure_builtin(s)
        profiles.save_profile(s, "Main", HOME)
        s["audio_outputs"] = dict(HALL)
        s["audio_profile"] = "Gone"
        self.assertTrue(profiles.ensure_builtin(s))
        self.assertEqual(profiles.active_profile(s), "Main")
        self.assertEqual(s["audio_outputs"], HOME)
        self.assertEqual(s["audio_profiles"]["Main"]["outputs"], HOME)

    def test_custom_profiles_and_the_active_one_survive(self):
        s = _settings()
        profiles.save_profile(s, "Tournament", HALL)
        profiles.ensure_builtin(s)
        self.assertEqual(profiles.profile_names(s), ["Main", "Rehearsal", "Tournament"])
        self.assertEqual(profiles.active_profile(s), "Tournament")

    def test_rehearsal_is_private_whatever_the_file_says(self):
        s = _settings()
        profiles.ensure_builtin(s)
        s["audio_profiles"]["Rehearsal"]["private"] = False
        self.assertTrue(profiles.is_private(s, "Rehearsal"))

    def test_main_is_never_private(self):
        s = _settings()
        profiles.ensure_builtin(s)
        s["audio_profiles"]["Main"]["private"] = True
        self.assertFalse(profiles.is_private(s, "Main"))

    def test_saving_over_rehearsal_keeps_it_private_and_over_main_public(self):
        s = _settings()
        profiles.ensure_builtin(s)
        profiles.save_profile(s, "Rehearsal", HOME)
        self.assertTrue(profiles.is_private(s, "Rehearsal"))
        profiles.save_profile(s, "Main", HALL, private=True)
        self.assertFalse(profiles.is_private(s, "Main"))

    def test_the_builtins_cannot_be_deleted(self):
        s = _settings()
        profiles.ensure_builtin(s)
        self.assertFalse(profiles.delete_profile(s, "Main"))
        self.assertFalse(profiles.delete_profile(s, "Rehearsal"))
        self.assertEqual(profiles.profile_names(s), ["Main", "Rehearsal"])

    def test_a_custom_profile_can_be_deleted(self):
        s = _settings()
        profiles.save_profile(s, "Tournament", HALL)
        profiles.ensure_builtin(s)
        self.assertTrue(profiles.delete_profile(s, "Tournament"))
        self.assertEqual(profiles.profile_names(s), ["Main", "Rehearsal"])

    def test_a_garbled_builtin_is_replaced(self):
        s = _settings(audio_profiles={"Rehearsal": "oops"})
        profiles.ensure_builtin(s)
        self.assertEqual(profiles.profile_names(s), ["Main", "Rehearsal"])
        self.assertIsInstance(s["audio_profiles"]["Rehearsal"], dict)

    def test_the_builtin_names_are_exposed(self):
        self.assertEqual(profiles.BUILTIN, ("Main", "Rehearsal"))
        self.assertTrue(profiles.is_builtin("Main"))
        self.assertFalse(profiles.is_builtin("Tournament"))


class PersistTest(unittest.TestCase):
    """The profiles are in gui_settings.json: a save and a load bring them back."""

    def setUp(self):
        self.store = JsonStore.at(Path(tempfile.mkdtemp(prefix="dp_prof_")) / "gui_settings.json")

    def test_the_builtins_survive_a_save_and_a_load(self):
        s = _settings()
        profiles.ensure_builtin(s)
        self.assertTrue(self.store.write(s))
        back = self.store.read()
        self.assertEqual(profiles.profile_names(back), ["Main", "Rehearsal"])
        self.assertEqual(back["audio_profiles"], s["audio_profiles"])
        self.assertEqual(profiles.active_profile(back), "Main")

    def test_a_custom_profile_and_a_switch_survive_too(self):
        s = _settings()
        profiles.ensure_builtin(s)
        profiles.save_profile(s, "Tournament", HALL)
        profiles.switch_profile(s, "Rehearsal")
        self.store.write(s)
        back = self.store.read()
        self.assertEqual(profiles.profile_names(back), ["Main", "Rehearsal", "Tournament"])
        self.assertEqual(profiles.active_profile(back), "Rehearsal")
        self.assertEqual(back["audio_outputs"], s["audio_outputs"])

    def test_an_old_settings_file_gets_the_builtins_through_load_settings(self):
        """The start-up path: load_settings, ensure_builtin, save, load again."""
        from unittest import mock

        from gui import dialogs
        self.store.write({"audio_outputs": copy.deepcopy(HALL)})
        with mock.patch.object(dialogs, "SETTINGS", self.store):
            s = dialogs.load_settings()
            self.assertTrue(profiles.ensure_builtin(s))
            self.store.write(s)
            again = dialogs.load_settings()
        self.assertEqual(profiles.profile_names(again), ["Main", "Rehearsal"])
        self.assertEqual(profiles.active_profile(again), "Main")
        self.assertEqual(again["audio_outputs"], HALL)
        self.assertFalse(profiles.ensure_builtin(again))

    def test_ensuring_a_loaded_file_changes_nothing(self):
        s = _settings()
        profiles.ensure_builtin(s)
        self.store.write(s)
        back = self.store.read()
        self.assertFalse(profiles.ensure_builtin(back))


if __name__ == "__main__":
    unittest.main()
