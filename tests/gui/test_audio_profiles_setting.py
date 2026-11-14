#!/usr/bin/env python3
"""⚙ Settings → 🔊 Sound & player: audio profiles.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_audio_profiles_setting -v

A profile row above the output pickers: choose a profile and the pickers show
its outputs; "Save as…" stores the pickers under a name. Main and Rehearsal are
always there and cannot be deleted; Rehearsal is private by definition (the
hall hears nothing of it), so there is no tick for that. An edit, a "Save as…"
and a delete are kept at once (see KeptWithoutOkTest); the rest waits for OK.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_profiles_setting_"))

from PySide6.QtWidgets import QApplication, QMessageBox

from gui.dialogs import settings_dialog, settings_sound
from shared.audio import profiles
from tests.qt_test_support import reap_widget

_OUTPUTS = [("aa", "Out 1/2 (USB interface)"), ("bb", "Out 3/4 (USB interface)")]
HALL = {"music": {"id": "aa", "name": "Out 1/2 (USB interface)"},
        "cue": {"id": "bb", "name": "Out 3/4 (USB interface)"}}
HOME = {"music": {"id": "bb", "name": "Out 3/4 (USB interface)"}}
_NAME = "gui.dialogs.settings_sound.QInputDialog.getText"


def _two_profiles():
    """Main (the hall), Rehearsal (the pre-listen output) and one of your own."""
    s = {"audio_outputs": HALL}
    profiles.ensure_builtin(s)
    profiles.save_profile(s, "Tournament", HALL)
    return s


class _Case(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings, **kw):
        # Patched for the whole test: a refill after a profile pick lists them again.
        for name, value in (("audio_output_choices", list(_OUTPUTS)),
                            ("audio_output_pairs", {})):
            patcher = mock.patch.object(settings_sound, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        dlg = settings_dialog.SettingsDialog(settings, **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def _choose(self, dlg, name):
        combo = dlg._profile_combo
        combo.setCurrentIndex(combo.findData(name))
        combo.activated.emit(combo.currentIndex())

    def _pick(self, dlg, source, data):
        combo = dlg._output_combos[source]
        combo.setCurrentIndex(combo.findData(data))


class RowTest(_Case):

    def test_a_file_without_profiles_still_offers_main_and_rehearsal(self):
        dlg = self._dialog({"audio_outputs": HALL})
        combo = dlg._profile_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         ["Main", "Rehearsal"])
        self.assertEqual(combo.currentData(), "Main")
        values = dlg.values()
        self.assertEqual(list(values["audio_profiles"]), ["Main", "Rehearsal"])
        self.assertEqual(values["audio_profiles"]["Main"]["outputs"], HALL)
        self.assertEqual(values["audio_profile"], "Main")

    def test_a_fresh_install_has_them_too(self):
        values = self._dialog({}).values()
        self.assertEqual(list(values["audio_profiles"]), ["Main", "Rehearsal"])

    def test_the_saved_profiles_are_listed_and_the_active_one_shown(self):
        dlg = self._dialog(_two_profiles())
        combo = dlg._profile_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         ["Main", "Rehearsal", "Tournament"])
        self.assertEqual(combo.currentData(), "Tournament")

    def test_there_is_no_rehearsal_tick(self):
        self.assertFalse(hasattr(self._dialog({}), "_profile_private_chk"))

    def test_choosing_rehearsal_loads_its_outputs(self):
        dlg = self._dialog(_two_profiles())
        self._choose(dlg, "Rehearsal")
        self.assertEqual(dlg._output_combos["music"].currentData(), "bb")
        self.assertIsNone(dlg._output_combos["cue"].currentData())
        values = dlg.values()
        self.assertEqual(values["audio_profile"], "Rehearsal")
        self.assertTrue(values["audio_profiles"]["Rehearsal"]["private"])

    def test_there_is_no_no_profile_entry_and_main_is_the_default(self):
        """Marcel: remove the no-profile entry, Main is the default. A file whose
        active profile is gone (older ones, or none ever set) opens on Main with
        the pickers as they were."""
        s = _two_profiles()
        s.pop("audio_profile")
        dlg = self._dialog(s)
        combo = dlg._profile_combo
        self.assertNotIn(None, [combo.itemData(i) for i in range(combo.count())])
        self.assertEqual(combo.currentData(), "Main")
        self.assertEqual(dlg._output_combos["music"].currentData(), "aa")
        self.assertEqual(dlg.values()["audio_profile"], "Main")

    def test_a_vanished_profile_opens_on_main_with_mains_outputs(self):
        """Marcel: the profile shown must be the one that plays. Main's outputs
        are in the pickers, not the ones the vanished profile left behind."""
        s = _two_profiles()
        profiles.save_profile(s, "Main", HOME)
        s["audio_outputs"] = dict(HALL)
        s["audio_profile"] = "Gone"
        dlg = self._dialog(s)
        self.assertEqual(dlg._profile_combo.currentData(), "Main")
        self.assertEqual(dlg._output_combos["music"].currentData(), "bb")
        self.assertEqual(dlg.values()["audio_outputs"]["music"]["id"], "bb")


class AutoSaveTest(_Case):
    """Changing a picker while a profile is chosen edits that profile — leaving
    for another profile and back keeps it; "Save as…" is only for a new name."""

    def _edit(self, dlg, source, data):
        combo = dlg._output_combos[source]
        combo.setCurrentIndex(combo.findData(data))
        combo.activated.emit(combo.currentIndex())

    def test_an_edit_survives_leaving_the_profile_and_coming_back(self):
        dlg = self._dialog({"audio_outputs": HALL})
        self._edit(dlg, "cue", None)
        self._choose(dlg, "Rehearsal")
        self._choose(dlg, "Main")
        self.assertEqual(dlg._output_combos["music"].currentData(), "aa")
        self.assertIsNone(dlg._output_combos["cue"].currentData())
        self.assertNotIn("cue", dlg.values()["audio_profiles"]["Main"]["outputs"])

    def test_the_edit_goes_into_the_chosen_profile_only(self):
        dlg = self._dialog(_two_profiles())
        self._edit(dlg, "music", "bb")
        values = dlg.values()["audio_profiles"]
        self.assertEqual(values["Tournament"]["outputs"]["music"]["id"], "bb")
        self.assertEqual(values["Main"]["outputs"], HALL)

    def test_editing_rehearsal_keeps_it_private(self):
        dlg = self._dialog(_two_profiles())
        self._choose(dlg, "Rehearsal")
        self._edit(dlg, "cue", "aa")
        stored = dlg.values()["audio_profiles"]["Rehearsal"]
        self.assertEqual(stored["outputs"]["cue"]["id"], "aa")
        self.assertTrue(stored["private"])

    def test_switching_alone_changes_no_profile(self):
        dlg = self._dialog(_two_profiles())
        before = dlg.values()["audio_profiles"]
        self._choose(dlg, "Rehearsal")
        self._choose(dlg, "Tournament")
        self.assertEqual(dlg.values()["audio_profiles"], before)


class SaveTest(_Case):

    def test_save_as_stores_the_pickers_under_the_name_and_makes_it_active(self):
        dlg = self._dialog({})
        self._pick(dlg, "music", "aa")
        self._pick(dlg, "cue", "bb")
        with mock.patch(_NAME, return_value=("Tournament", True)):
            dlg._profile_save_btn.click()
        values = dlg.values()
        self.assertEqual(values["audio_profile"], "Tournament")
        self.assertEqual(values["audio_profiles"]["Tournament"]["outputs"], HALL)
        self.assertFalse(values["audio_profiles"]["Tournament"]["private"])
        self.assertEqual(dlg._profile_combo.currentData(), "Tournament")

    def test_saving_over_rehearsal_keeps_it_private(self):
        dlg = self._dialog({})
        self._pick(dlg, "music", "bb")
        with mock.patch(_NAME, return_value=("Rehearsal", True)), \
                mock.patch.object(settings_sound.QMessageBox, "question",
                                  return_value=QMessageBox.StandardButton.Yes):
            dlg._profile_save_btn.click()
        values = dlg.values()
        self.assertTrue(values["audio_profiles"]["Rehearsal"]["private"])
        self.assertEqual(values["audio_profiles"]["Rehearsal"]["outputs"]["music"]["id"], "bb")

    def test_saving_over_main_keeps_it_a_hall_profile(self):
        dlg = self._dialog({})
        with mock.patch(_NAME, return_value=("Main", True)):
            dlg._profile_save_btn.click()
        self.assertFalse(dlg.values()["audio_profiles"]["Main"]["private"])

    def test_cancelling_the_name_changes_nothing(self):
        dlg = self._dialog({})
        with mock.patch(_NAME, return_value=("Tournament", False)):
            dlg._profile_save_btn.click()
        self.assertEqual(list(dlg.values()["audio_profiles"]), ["Main", "Rehearsal"])

    def test_a_blank_name_changes_nothing(self):
        dlg = self._dialog({})
        with mock.patch(_NAME, return_value=("  ", True)):
            dlg._profile_save_btn.click()
        self.assertEqual(list(dlg.values()["audio_profiles"]), ["Main", "Rehearsal"])

    def test_replacing_another_profile_asks_first(self):
        dlg = self._dialog(_two_profiles())
        self._pick(dlg, "music", "aa")
        with mock.patch(_NAME, return_value=("Rehearsal", True)), \
                mock.patch.object(settings_sound.QMessageBox, "question",
                                  return_value=QMessageBox.StandardButton.No) as ask:
            dlg._profile_save_btn.click()
        ask.assert_called_once()
        self.assertEqual(dlg.values()["audio_profiles"]["Rehearsal"]["outputs"], HOME)
        self.assertEqual(dlg.values()["audio_profile"], "Tournament")

    def test_editing_the_pickers_of_the_active_profile_updates_it_on_ok(self):
        """The pickers always mirror the active profile, so an edit that was
        not saved under a new name is an edit of that profile."""
        dlg = self._dialog(_two_profiles())
        self._pick(dlg, "music", "bb")
        values = dlg.values()
        self.assertEqual(values["audio_profiles"]["Tournament"]["outputs"]["music"]["id"], "bb")
        self.assertEqual(values["audio_outputs"]["music"]["id"], "bb")
        self.assertEqual(values["audio_profiles"]["Rehearsal"]["outputs"], HOME)

    def test_editing_a_custom_profile_does_not_make_it_private(self):
        dlg = self._dialog(_two_profiles())
        self._pick(dlg, "music", "bb")
        self.assertFalse(dlg.values()["audio_profiles"]["Tournament"]["private"])


class DeleteTest(_Case):

    def test_delete_removes_your_own_profile_after_asking(self):
        dlg = self._dialog(_two_profiles())
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg._profile_delete_btn.click()
        values = dlg.values()
        self.assertEqual(list(values["audio_profiles"]), ["Main", "Rehearsal"])
        # Main takes over, with its own outputs showing: the pickers must not
        # stay on the deleted profile's, or the next edit would rewrite Main.
        self.assertEqual(values["audio_profile"], "Main")
        self.assertEqual(dlg._profile_combo.currentData(), "Main")
        self.assertEqual(values["audio_outputs"], HALL)

    def test_deleting_the_active_one_shows_main_s_outputs(self):
        s = _two_profiles()
        profiles.save_profile(s, "Home", HOME)
        dlg = self._dialog(s)
        self.assertEqual(dlg._output_combos["music"].currentData(), "bb")
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg._profile_delete_btn.click()
        self.assertEqual(dlg._output_combos["music"].currentData(), "aa")
        self.assertEqual(dlg.values()["audio_profiles"]["Main"]["outputs"], HALL)

    def test_declining_keeps_it(self):
        dlg = self._dialog(_two_profiles())
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            dlg._profile_delete_btn.click()
        self.assertEqual(list(dlg.values()["audio_profiles"]),
                         ["Main", "Rehearsal", "Tournament"])

    def test_main_and_rehearsal_cannot_be_deleted(self):
        dlg = self._dialog(_two_profiles())
        self.assertTrue(dlg._profile_delete_btn.isEnabled(), "Tournament is your own")
        for name in ("Main", "Rehearsal"):
            self._choose(dlg, name)
            self.assertFalse(dlg._profile_delete_btn.isEnabled(), name)

    def test_the_greyed_delete_button_looks_greyed(self):
        """Marcel: grey the delete button for Main and Rehearsal, so it is clear
        they cannot be deleted. Greyed text alone is too faint: the face itself
        has to differ from an enabled button's."""
        dlg = self._dialog(_two_profiles())
        btn = dlg._profile_delete_btn
        btn.resize(90, 30)

        def face():
            image = btn.grab().toImage()
            return image.pixelColor(6, image.height() // 2).name()

        enabled_face = face()
        self._choose(dlg, "Main")
        self.assertFalse(btn.isEnabled())
        self.assertNotEqual(face(), enabled_face)


class KeptWithoutOkTest(_Case):
    """Marcel: when I define a new output device for an audio profile it must be
    saved without pressing OK. An edit, a "Save as…" and a delete go to the
    window the moment they are made (`profiles_cb`); only picking another
    profile stays in the dialog until OK."""

    def _kept(self, settings):
        got = []
        dlg = self._dialog(settings, profiles_cb=got.append)
        return dlg, got

    def _edit(self, dlg, source, data):
        combo = dlg._output_combos[source]
        combo.setCurrentIndex(combo.findData(data))
        combo.activated.emit(combo.currentIndex())

    def test_an_edited_output_is_handed_over_at_once(self):
        dlg, got = self._kept(_two_profiles())
        self._edit(dlg, "music", "bb")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["audio_outputs"]["music"]["id"], "bb")
        self.assertEqual(
            got[0]["audio_profiles"]["Tournament"]["outputs"]["music"]["id"], "bb")
        self.assertEqual(got[0]["audio_profiles"]["Main"]["outputs"], HALL)
        self.assertEqual(got[0]["audio_profile"], "Tournament")

    def test_save_as_is_handed_over_at_once(self):
        dlg, got = self._kept({})
        self._pick(dlg, "music", "aa")
        self._pick(dlg, "cue", "bb")
        with mock.patch(_NAME, return_value=("Tournament", True)):
            dlg._profile_save_btn.click()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["audio_profile"], "Tournament")
        self.assertEqual(got[0]["audio_profiles"]["Tournament"]["outputs"], HALL)

    def test_a_delete_is_handed_over_at_once(self):
        dlg, got = self._kept(_two_profiles())
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg._profile_delete_btn.click()
        self.assertEqual(len(got), 1)
        self.assertEqual(list(got[0]["audio_profiles"]), ["Main", "Rehearsal"])
        self.assertEqual(got[0]["audio_profile"], "Main")
        self.assertEqual(got[0]["audio_outputs"], HALL)

    def test_a_declined_delete_hands_over_nothing(self):
        dlg, got = self._kept(_two_profiles())
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            dlg._profile_delete_btn.click()
        self.assertEqual(got, [])

    def test_picking_another_profile_stays_in_the_dialog(self):
        dlg, got = self._kept(_two_profiles())
        self._choose(dlg, "Rehearsal")
        self.assertEqual(got, [])

    def test_an_edit_after_a_pick_does_not_move_the_hall(self):
        # The window runs Tournament. Rehearsal is only picked (kept on OK), so
        # an edit of it is stored, but the hall output stays where it is.
        dlg, got = self._kept(_two_profiles())
        self._choose(dlg, "Rehearsal")
        self._edit(dlg, "music", "aa")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["audio_profile"], "Tournament")
        self.assertEqual(got[0]["audio_outputs"], HALL)
        self.assertEqual(
            got[0]["audio_profiles"]["Rehearsal"]["outputs"]["music"]["id"], "aa")
        self.assertEqual(dlg.values()["audio_profile"], "Rehearsal",
                         "the pick itself still waits for OK")

    def test_picking_back_the_running_profile_makes_its_edit_count(self):
        dlg, got = self._kept(_two_profiles())
        self._choose(dlg, "Rehearsal")
        self._choose(dlg, "Tournament")
        self._edit(dlg, "music", "bb")
        self.assertEqual(got[0]["audio_profile"], "Tournament")
        self.assertEqual(got[0]["audio_outputs"]["music"]["id"], "bb")

    def test_deleting_a_profile_that_is_not_running_keeps_the_running_one(self):
        s = _two_profiles()
        profiles.save_profile(s, "Other", HOME)
        profiles.switch_profile(s, "Tournament")
        dlg, got = self._kept(s)
        self._choose(dlg, "Other")
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg._profile_delete_btn.click()
        self.assertNotIn("Other", got[0]["audio_profiles"])
        self.assertEqual(got[0]["audio_profile"], "Tournament")
        self.assertEqual(got[0]["audio_outputs"], HALL)

    def test_without_a_callback_nothing_breaks(self):
        dlg = self._dialog(_two_profiles())
        self._edit(dlg, "music", "bb")
        self.assertEqual(dlg.values()["audio_outputs"]["music"]["id"], "bb")


class WindowKeepsThemTest(unittest.TestCase):
    """The window end: the real `_open_settings` hands the dialog a callback
    that stores, saves and applies what the dialog sends, with no OK."""

    NEW = {"audio_outputs": HOME,
           "audio_profiles": {"Main": {"outputs": HOME}},
           "audio_profile": "Main"}

    def _open(self, settings):
        from functools import partial

        from PySide6.QtWidgets import QDialog

        from gui.window import main_global
        host = mock.MagicMock()
        host._settings = dict(settings)
        host.cart_wall_settings = dict
        host._keep_audio_profiles = partial(
            main_global.GlobalIndexMixin._keep_audio_profiles, host)
        dlg = mock.MagicMock()
        dlg.exec.return_value = QDialog.DialogCode.Rejected     # ✕: no OK
        with mock.patch.object(main_global, "SettingsDialog",
                               return_value=dlg) as dialog_cls:
            main_global.GlobalIndexMixin._open_settings(host)
        return host, dialog_cls.call_args.kwargs["profiles_cb"]

    def test_what_the_dialog_sends_is_saved_and_applied_without_ok(self):
        from gui.window import main_global
        host, cb = self._open({"audio_outputs": HALL, "language": "de"})
        with mock.patch.object(main_global, "save_settings",
                               return_value=True) as save:
            cb(self.NEW)
        self.assertEqual(host._settings["audio_outputs"], HOME)
        self.assertEqual(host._settings["audio_profile"], "Main")
        self.assertEqual(host._settings["language"], "de", "the rest is untouched")
        save.assert_called_once_with(host._settings, report=False)
        host._audio_device.sync.assert_called()
        host._guard_headset_volume.assert_called()
        host._audio_device.on_activity.assert_called()
        host._sync_sound_badge.assert_called()

    def test_a_save_that_does_not_land_is_told(self):
        from gui.window import main_global
        host, cb = self._open({})
        with mock.patch.object(main_global, "save_settings", return_value=False), \
                mock.patch.object(main_global.QMessageBox, "warning") as warn:
            cb(self.NEW)
        warn.assert_called_once()
        self.assertEqual(host._settings["audio_outputs"], HOME, "applies anyway")

    def test_the_warning_stands_on_the_open_settings_dialog(self):
        # Settings is modal over the window: a box parented to the window sits
        # behind it. While the dialog is open it is the parent.
        from gui.window import main_global
        host, cb = self._open({})
        host._settings_dlg = open_dialog = mock.sentinel.settings_dialog
        with mock.patch.object(main_global, "save_settings", return_value=False), \
                mock.patch.object(main_global.QMessageBox, "warning") as warn:
            cb(self.NEW)
        self.assertIs(warn.call_args.args[0], open_dialog)


if __name__ == "__main__":
    unittest.main()
