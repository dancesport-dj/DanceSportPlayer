#!/usr/bin/env python3
"""⚙ Settings → 🔊 Sound & player: an output per source.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_audio_outputs_setting -v

A picker per source — music, pre-listen, cartwall, announcements — each offering every
output the operating system lists. A saved card that is not plugged in stays
chosen (marked ⚠) instead of silently turning into "default".
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_outputs_setting_"))

from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QTabWidget

import dancesport_gui as gui
from gui.dialogs import settings_dialog, settings_sound
from gui.window import main_global
from shared.audio.playback import OUTPUT_SOURCES, SYSTEM_DEFAULT
from tests.qt_test_support import reap_widget

_OUTPUTS = [("aa", "Out 1/2 (USB interface)"), ("bb", "Out 3/4 (USB interface)")]


class _PickerCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings, pairs=None):
        with mock.patch.object(settings_sound, "audio_output_choices",
                               return_value=list(_OUTPUTS)),                 mock.patch.object(settings_sound, "audio_output_pairs",
                                  return_value=dict(pairs or {})):
            dlg = settings_dialog.SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def _pick(self, dlg, source, data):
        combo = dlg._output_combos[source]
        combo.setCurrentIndex(combo.findData(data))


class PickerTest(_PickerCase):

    def test_one_picker_per_source_on_the_sound_tab(self):
        dlg = self._dialog({})
        # …and 🎧 pre-listen, which is no source of the evening.
        self.assertEqual(set(dlg._output_combos), set(OUTPUT_SOURCES) | {"cue"})
        tabs = dlg.findChild(QTabWidget)
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        page = tabs.widget(captions.index("🔊 Sound && player"))
        for combo in dlg._output_combos.values():
            self.assertTrue(page.isAncestorOf(combo))

    def test_pre_listen_comes_right_below_the_music(self):
        """Music and 🎧 first; announcements, which rarely need an
        output of their own, last, below a line."""
        self.assertEqual(list(self._dialog({})._output_combos),
                         ["music", "cue", "cartwall", "announcer"])

    def test_pre_listen_starts_on_same_as_the_music(self):
        combo = self._dialog({})._output_combos["cue"]
        self.assertEqual(combo.currentText(), "Same as the music")
        self.assertIsNone(combo.currentData())

    def test_nothing_chosen_saves_nothing(self):
        self.assertEqual(self._dialog({}).values()["audio_outputs"], {})

    def test_every_output_is_offered(self):
        combo = self._dialog({})._output_combos["cartwall"]
        texts = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn("Out 3/4 (USB interface)", texts)

    def test_a_choice_is_saved_with_its_name(self):
        dlg = self._dialog({})
        self._pick(dlg, "music", "aa")
        self._pick(dlg, "cartwall", "bb")
        self._pick(dlg, "announcer", SYSTEM_DEFAULT)
        self.assertEqual(dlg.values()["audio_outputs"], {
            "music": {"id": "aa", "name": "Out 1/2 (USB interface)"},
            "cartwall": {"id": "bb", "name": "Out 3/4 (USB interface)"},
            "announcer": {"id": SYSTEM_DEFAULT}})

    def test_the_music_has_no_follow_the_music_entry(self):
        combo = self._dialog({})._output_combos["music"]
        self.assertEqual(combo.findData(SYSTEM_DEFAULT), -1)
        self.assertEqual(combo.currentIndex(), 0)

    def test_a_saved_choice_is_shown(self):
        dlg = self._dialog({"audio_outputs": {"cartwall": {"id": "bb", "name": "x"}}})
        self.assertEqual(dlg._output_combos["cartwall"].currentData(), "bb")

    def test_a_card_not_plugged_in_stays_chosen(self):
        saved = {"music": {"id": "cc", "name": "Out 5/6 (USB interface)"}}
        dlg = self._dialog({"audio_outputs": saved})
        combo = dlg._output_combos["music"]
        self.assertEqual(combo.currentData(), "cc")
        self.assertIn("⚠", combo.currentText())
        self.assertIn("Out 5/6 (USB interface)", combo.currentText())
        self.assertEqual(dlg.values()["audio_outputs"], saved)

    def test_a_card_windows_numbered_anew_is_found_by_its_name(self):
        """🔊 "(2- ESI …)" saved, "(3- ESI …)" plugged in under a new id: it
        is that card, shown without a ⚠ and saved under its new id."""
        saved = {"music": {"id": "old", "name": "MAYA44USB Ch12 (2- ESI Audio Device)"}}
        outputs = [*_OUTPUTS, ("new", "MAYA44USB Ch12 (3- ESI Audio Device)")]
        with mock.patch.object(settings_sound, "audio_output_choices",
                               return_value=outputs):
            dlg = settings_dialog.SettingsDialog({"audio_outputs": saved})
        self.addCleanup(reap_widget, dlg)
        combo = dlg._output_combos["music"]
        self.assertEqual(combo.currentData(), "new")
        self.assertNotIn("⚠", "".join(combo.itemText(i) for i in range(combo.count())))
        self.assertEqual(dlg.values()["audio_outputs"]["music"],
                         {"id": "new", "name": "MAYA44USB Ch12 (3- ESI Audio Device)"})


class ChannelPairPickerTest(_PickerCase):
    """🔀 "aa" is ONE four-channel device: its Out 3/4 is an entry too."""

    def setUp(self):
        # The entries name Windows' audio layer; every test reads them as on Windows.
        platform = mock.patch.object(settings_sound.sys, "platform", "win32")
        platform.start()
        self.addCleanup(platform.stop)

    def _note(self, dlg):
        return [lbl for lbl in dlg.findChildren(QLabel)
                if lbl.text().startswith("🔀") and not lbl.isHidden()]

    def test_every_source_offers_the_pair(self):
        dlg = self._dialog({}, {"aa": 2, "bb": 1})
        for source, combo in dlg._output_combos.items():
            texts = [combo.itemText(i) for i in range(combo.count())]
            self.assertIn("Out 1/2 (USB interface) — Out 3/4 · WASAPI", texts, source)
            self.assertNotIn("Out 3/4 (USB interface) — Out 3/4 · WASAPI", texts, source)

    def test_only_a_routed_pair_says_wasapi(self):
        dlg = self._dialog({}, {"aa": 2})
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.itemText(combo.findData("aa")), "Out 1/2 (USB interface)")
        self.assertTrue(combo.itemText(combo.findData("aa#1")).endswith("· WASAPI"))

    def test_off_windows_a_pair_names_no_wasapi(self):
        with mock.patch.object(settings_sound.sys, "platform", "darwin"):
            dlg = self._dialog({}, {"aa": 2})
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.itemText(combo.findData("aa#1")),
                         "Out 1/2 (USB interface) — Out 3/4")

    def _pick_music_pair(self, dlg, answer):
        """The operator picks the music's Out 3/4 and answers the question."""
        combo = dlg._output_combos["music"]
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=answer) as ask:
            index = combo.findData("aa#1")
            combo.setCurrentIndex(index)
            combo.activated.emit(index)
        return combo, ask

    def test_the_music_on_a_pair_asks_about_the_pitch(self):
        dlg = self._dialog({}, {"aa": 2})
        combo, ask = self._pick_music_pair(dlg, QMessageBox.StandardButton.Yes)
        ask.assert_called_once()
        self.assertIn("pitch", ask.call_args.args[2])
        self.assertEqual(combo.currentData(), "aa#1")
        self.assertEqual(dlg.values()["audio_outputs"], {
            "music": {"id": "aa", "name": "Out 1/2 (USB interface)", "pair": 1}})

    def test_no_keeps_the_music_where_it_was(self):
        saved = {"music": {"id": "bb", "name": "Out 3/4 (USB interface)"}}
        dlg = self._dialog({"audio_outputs": saved}, {"aa": 2})
        combo, _ask = self._pick_music_pair(dlg, QMessageBox.StandardButton.No)
        self.assertEqual(combo.currentData(), "bb")
        self.assertEqual(dlg.values()["audio_outputs"], saved)

    def test_a_whole_device_or_another_source_asks_nothing(self):
        dlg = self._dialog({}, {"aa": 2})
        with mock.patch.object(settings_sound.QMessageBox, "question") as ask:
            music = dlg._output_combos["music"]
            music.activated.emit(music.findData("aa"))
            music.activated.emit(0)
            wall = dlg._output_combos["cartwall"]
            wall.activated.emit(wall.findData("aa#1"))
        ask.assert_not_called()

    def test_a_saved_music_pair_is_shown_without_asking(self):
        saved = {"music": {"id": "aa", "name": "x", "pair": 1}}
        with mock.patch.object(settings_sound.QMessageBox, "question") as ask:
            dlg = self._dialog({"audio_outputs": saved}, {"aa": 2})
        self.assertEqual(dlg._output_combos["music"].currentData(), "aa#1")
        ask.assert_not_called()

    def test_a_pair_is_saved_with_its_card(self):
        dlg = self._dialog({}, {"aa": 2})
        self._pick(dlg, "cartwall", "aa#1")
        self.assertEqual(dlg.values()["audio_outputs"], {
            "cartwall": {"id": "aa", "name": "Out 1/2 (USB interface)", "pair": 1}})

    def test_a_saved_pair_is_shown(self):
        saved = {"cue": {"id": "aa", "name": "x", "pair": 1}}
        dlg = self._dialog({"audio_outputs": saved}, {"aa": 2})
        self.assertEqual(dlg._output_combos["cue"].currentData(), "aa#1")

    def test_a_saved_pair_of_a_card_not_plugged_in_stays_chosen(self):
        saved = {"cartwall": {"id": "cc", "name": "UMC404HD", "pair": 1}}
        dlg = self._dialog({"audio_outputs": saved})
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.currentText(), "⚠  UMC404HD — Out 3/4 · WASAPI (not connected)")
        self.assertEqual(dlg.values()["audio_outputs"], saved)

    def test_the_note_only_with_such_a_card(self):
        self.assertEqual(self._note(self._dialog({})), [])
        note = self._note(self._dialog({}, {"aa": 2}))
        self.assertEqual(len(note), 1)
        self.assertIn("pitch", note[0].text())


class LiveDevicesTest(_PickerCase):
    """🔌 A card plugged in or pulled out while the dialog is open shows up
    in the pickers at once, the way the OS reports it."""

    def setUp(self):
        platform = mock.patch.object(settings_sound.sys, "platform", "win32")
        platform.start()
        self.addCleanup(platform.stop)

    def _refill(self, dlg, outputs, pairs=None, signal=False):
        """The OS now lists `outputs`: the dialog hears of it."""
        with mock.patch.object(settings_sound, "audio_output_choices",
                               return_value=list(outputs)),                 mock.patch.object(settings_sound, "audio_output_pairs",
                                  return_value=dict(pairs or {})):
            if signal:
                dlg._sound_devices.audioOutputsChanged.emit()
            else:
                dlg._fill_outputs()

    @staticmethod
    def _texts(combo):
        return [combo.itemText(i) for i in range(combo.count())]

    def test_the_os_reporting_a_new_card_offers_it(self):
        dlg = self._dialog({})
        self._refill(dlg, [*_OUTPUTS, ("cc", "Speakers (UMC404HD)")], signal=True)
        for source, combo in dlg._output_combos.items():
            self.assertIn("Speakers (UMC404HD)", self._texts(combo), source)

    def test_the_choice_stays_chosen_across_a_refill(self):
        dlg = self._dialog({})
        self._pick(dlg, "cartwall", "bb")
        self._refill(dlg, [("cc", "Speakers (UMC404HD)"), *_OUTPUTS])
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.currentData(), "bb")
        self.assertEqual(combo.count(), len(set(self._texts(combo))))

    def test_a_chosen_card_pulled_out_stays_chosen_marked(self):
        dlg = self._dialog({})
        self._pick(dlg, "cartwall", "bb")
        self._refill(dlg, _OUTPUTS[:1])
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.currentText(), "⚠  Out 3/4 (USB interface) (not connected)")
        self.assertEqual(dlg.values()["audio_outputs"], {
            "cartwall": {"id": "bb", "name": "Out 3/4 (USB interface)"}})

    def test_a_card_plugged_back_in_loses_its_mark(self):
        dlg = self._dialog({})
        self._pick(dlg, "cartwall", "bb")
        self._refill(dlg, _OUTPUTS[:1])
        self._refill(dlg, _OUTPUTS)
        combo = dlg._output_combos["cartwall"]
        self.assertEqual(combo.currentText(), "Out 3/4 (USB interface)")
        self.assertNotIn("⚠", "".join(self._texts(combo)))

    def test_a_card_back_under_a_new_number_is_that_card(self):
        dlg = self._dialog({})
        self._refill(dlg, [*_OUTPUTS, ("old", "Ch12 (2- ESI Audio Device)")])
        self._pick(dlg, "music", "old")
        self._refill(dlg, [*_OUTPUTS, ("new", "Ch12 (3- ESI Audio Device)")])
        combo = dlg._output_combos["music"]
        self.assertEqual(combo.currentData(), "new")
        self.assertNotIn("⚠", "".join(self._texts(combo)))

    def test_a_chosen_pair_survives_a_refill(self):
        dlg = self._dialog({}, {"aa": 2})
        self._pick(dlg, "cue", "aa#1")
        self._refill(dlg, [("cc", "Speakers (UMC404HD)"), *_OUTPUTS], {"aa": 2})
        self.assertEqual(dlg._output_combos["cue"].currentData(), "aa#1")

    def test_the_note_appears_with_a_multichannel_card(self):
        dlg = self._dialog({})
        note = [lbl for lbl in dlg.findChildren(QLabel) if lbl.text().startswith("🔀")]
        self.assertEqual(len(note), 1)
        self.assertTrue(note[0].isHidden())
        self._refill(dlg, [*_OUTPUTS, ("cc", "Speakers (UMC404HD)")], {"cc": 2})
        self.assertFalse(note[0].isHidden())
        self.assertIn("Speakers (UMC404HD) — Out 3/4 · WASAPI",
                      self._texts(dlg._output_combos["cartwall"]))

    def test_no_after_a_refill_keeps_the_music_where_it_was(self):
        """The music's question reverts to the entry it was on, though a
        refill moved that entry to another row."""
        saved = {"music": {"id": "bb", "name": "Out 3/4 (USB interface)"}}
        dlg = self._dialog({"audio_outputs": saved}, {"aa": 2})
        with mock.patch.object(settings_sound.QMessageBox, "question") as ask:
            self._refill(dlg, [("cc", "Speakers (UMC404HD)"), *_OUTPUTS], {"aa": 2})
        ask.assert_not_called()
        combo = dlg._output_combos["music"]
        with mock.patch.object(settings_sound.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            index = combo.findData("aa#1")
            combo.setCurrentIndex(index)
            combo.activated.emit(index)
        self.assertEqual(combo.currentData(), "bb")


class _Dialog:

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**self._given, "audio_outputs": {"music": {"id": "aa", "name": "x"}}}

    def running_look_touched(self):
        return False

    def deleteLater(self):
        pass


class SaveAppliesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_saving_moves_the_outputs_at_once(self):
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: {"app_mode": "both"})
        patch.start()
        self.addCleanup(patch.stop)
        win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            p = mock.patch.object(main_global, name, value)
            p.start()
            self.addCleanup(p.stop)
        with mock.patch.object(win._audio_device, "sync") as sync:
            win._open_settings()
        sync.assert_called()

    def test_the_wall_is_put_on_its_output_when_it_is_built(self):
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: {"app_mode": "both"})
        patch.start()
        self.addCleanup(patch.stop)
        win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        if win._cart_voices is None:
            self.skipTest("no Qt Multimedia")
        from PySide6.QtMultimedia import QMediaDevices
        if QMediaDevices.defaultAudioOutput().isNull():
            self.skipTest("needs an audio output on this machine")
        self.assertIn("cartwall", win._audio_device._applied)


if __name__ == "__main__":
    unittest.main()
