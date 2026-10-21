#!/usr/bin/env python3
"""🔊 One output device per source: music, filler, cartwall, announcements.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_audio_outputs -v

A tester runs the evening through an external sound card with more than one
output pair. Every output the operating system lists as a device of its own
(Windows, macOS and Linux alike) can be chosen per source in ⚙ Settings →
🔊 Sound & player. Nothing chosen keeps the old behaviour: the music follows
the system default, and the other sources follow the music.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_outputs_"))

from PySide6.QtWidgets import QApplication

from player.audio.audio_device import SYSTEM_DEFAULT, AudioDevice
from player.audio.mix import OutputMix
from player.audio.system_sounds import SystemSoundGuard


class _Dev:
    """Stands in for a QAudioDevice."""

    def __init__(self, key: str, name: str):
        self._id = key.encode()
        self._name = name

    def id(self):
        return self._id

    def description(self):
        return self._name

    def isNull(self):
        return False

    @property
    def hex(self):
        return self._id.hex()


class _Devices:
    """Stands in for QMediaDevices: the list and which one is the default."""

    def __init__(self, *devs):
        self.outputs = list(devs)
        self.default = devs[0]

    def defaultAudioOutput(self):
        return self.default

    def audioOutputs(self):
        return list(self.outputs)


class _Out:
    """A QAudioOutput: where it plays and how often it was moved."""

    def __init__(self, dev):
        self.dev = dev
        self.moves = 0

    def setDevice(self, dev):
        self.dev = dev
        self.moves += 1

    def device(self):
        return self.dev


class _Sink:
    """The cart voice pool / the announcer: anything with set_device."""

    def __init__(self):
        self.dev = None

    def set_device(self, dev):
        self.dev = dev


SPEAKERS = _Dev("spk", "Speakers (Realtek)")
USB12 = _Dev("usb12", "Out 1/2 (USB interface)")
USB34 = _Dev("usb34", "Out 3/4 (USB interface)")


class _Desk:

    def __init__(self, outputs=None, voices=True, announcer=True):
        self.devices = _Devices(SPEAKERS, USB12, USB34)
        self.settings = {"audio_outputs": dict(outputs or {})}
        self.music = _Out(SPEAKERS)
        self.filler = _Out(SPEAKERS)
        self.voices = _Sink() if voices else None
        self.announcer = _Sink() if announcer else None
        self.warnings = []
        self.device = AudioDevice(
            object(), self.music, None, self.filler,
            mix=OutputMix(0.9),
            settings=lambda: self.settings,
            cart_voices=lambda: self.voices,
            is_playing_mode=lambda: False,
            apply_volume=lambda: None,
            system_sounds=SystemSoundGuard(),
            announcer=lambda: self.announcer,
            devices=self.devices,
            warn=self.warnings.append)

    def choose(self, source, dev):
        self.settings["audio_outputs"][source] = (
            {"id": dev} if dev == SYSTEM_DEFAULT
            else {"id": dev.hex, "name": dev.description()})

    def where(self) -> dict:
        return {"music": self.music.dev, "filler": self.filler.dev,
                "cartwall": self.voices.dev, "announcer": self.announcer.dev}


class _Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class DefaultsTest(_Test):

    def test_nothing_chosen_plays_everything_on_the_system_default(self):
        desk = _Desk()
        self.assertEqual(set(desk.where().values()), {SPEAKERS})

    def test_nothing_chosen_does_not_reopen_the_music(self):
        """The outputs were built on the default — moving them there again
        would re-open the card for nothing."""
        desk = _Desk()
        desk.device.sync()
        self.assertEqual((desk.music.moves, desk.filler.moves), (0, 0))

    def test_a_default_switch_moves_everything_that_follows_it(self):
        desk = _Desk()
        desk.devices.default = USB12
        desk.device.watch_default()
        self.assertEqual(set(desk.where().values()), {USB12})


class ChoiceTest(_Test):

    def test_the_music_card_takes_the_other_sources_along(self):
        desk = _Desk({})
        desk.choose("music", USB12)
        desk.device.sync()
        self.assertEqual(set(desk.where().values()), {USB12})

    def test_the_music_is_applied_when_the_desk_starts(self):
        desk = _Desk({"music": {"id": USB12.hex, "name": "x"}})
        self.assertIs(desk.music.dev, USB12)

    def test_every_source_on_its_own_output(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.choose("filler", USB12)
        desk.choose("cartwall", USB34)
        desk.choose("announcer", SYSTEM_DEFAULT)
        desk.device.sync()
        self.assertEqual(desk.where(), {"music": USB12, "filler": USB12,
                                        "cartwall": USB34, "announcer": SPEAKERS})

    def test_a_pinned_source_stays_when_the_default_switches(self):
        desk = _Desk()
        desk.choose("cartwall", USB34)
        desk.device.sync()
        desk.devices.default = USB12
        desk.device.watch_default()
        self.assertEqual(desk.where(), {"music": USB12, "filler": USB12,
                                        "cartwall": USB34, "announcer": USB12})

    def test_the_tick_picks_up_a_changed_setting(self):
        desk = _Desk()
        desk.choose("music", USB34)
        desk.device.watch_default()
        self.assertIs(desk.music.dev, USB34)

    def test_an_unchanged_choice_is_not_applied_again(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.device.sync()
        desk.device.sync()
        desk.device.watch_default()
        self.assertEqual(desk.music.moves, 1)

    def test_a_wall_built_later_still_gets_its_output(self):
        desk = _Desk(voices=False)
        desk.choose("cartwall", USB34)
        desk.device.sync()
        desk.voices = _Sink()
        desk.device.sync()
        self.assertIs(desk.voices.dev, USB34)


class MissingDeviceTest(_Test):

    def setUp(self):
        self.desk = _Desk()
        self.desk.choose("music", USB12)
        self.desk.devices.outputs.remove(USB12)

    def test_it_plays_on_the_system_default_and_says_so_once(self):
        with self.assertLogs("dancesport.gui.audio", level="WARNING"):
            self.desk.device.sync()
            self.desk.device.sync()
        self.assertIs(self.desk.music.dev, SPEAKERS)
        self.assertEqual(len(self.desk.warnings), 1)
        self.assertIn("Out 1/2 (USB interface)", self.desk.warnings[0])

    def test_the_card_coming_back_takes_the_music_back(self):
        with self.assertLogs("dancesport.gui.audio", level="WARNING"):
            self.desk.device.sync()
        self.desk.devices.outputs.append(USB12)
        self.desk.device.on_outputs_changed()
        self.assertIs(self.desk.music.dev, USB12)

    def test_unplugged_again_it_says_so_again(self):
        with self.assertLogs("dancesport.gui.audio", level="WARNING"):
            self.desk.device.sync()
            self.desk.devices.outputs.append(USB12)
            self.desk.device.sync()
            self.desk.devices.outputs.remove(USB12)
            self.desk.device.sync()
        self.assertEqual(len(self.desk.warnings), 2)


class RenumberedCardTest(_Test):
    """🔊 Windows numbers a USB card's instance — "(2- ESI Audio Device …)" —
    and hands it a new endpoint id, and the next number, when it enumerates
    it afresh: another USB port, a driver reload. Marcel's MAYA44USB came back
    as "(3- …)" and played on the system default, marked not connected."""

    OLD = {"id": "old", "name": "MAYA44USB Ch12 (2- ESI Audio Device (WDM) - MAYA44USB)"}
    NEW = _Dev("new", "MAYA44USB Ch12 (3- ESI Audio Device (WDM) - MAYA44USB)")

    def _desk(self, *extra):
        desk = _Desk()
        desk.devices.outputs += [self.NEW, *extra]
        desk.settings["audio_outputs"]["music"] = dict(self.OLD)
        return desk

    def test_it_plays_on_the_card_under_its_new_number(self):
        desk = self._desk()
        desk.device.sync()
        self.assertIs(desk.music.dev, self.NEW)
        self.assertEqual(desk.warnings, [])

    def test_ready_does_not_call_it_unplugged(self):
        self.assertEqual(self._desk().device.unplugged(), [])

    def test_two_cards_of_that_name_are_no_answer(self):
        """Two MAYA44s plugged in: which one was chosen cannot be told from
        the name, so it is missing, as before."""
        twin = _Dev("twin", "MAYA44USB Ch12 (4- ESI Audio Device (WDM) - MAYA44USB)")
        desk = self._desk(twin)
        with self.assertLogs("dancesport.gui.audio", level="WARNING"):
            desk.device.sync()
        self.assertIs(desk.music.dev, SPEAKERS)

    def test_another_output_of_the_card_is_not_it(self):
        desk = _Desk()
        desk.devices.outputs.append(
            _Dev("ch34", "MAYA44USB Ch34 (3- ESI Audio Device (WDM) - MAYA44USB)"))
        desk.settings["audio_outputs"]["music"] = dict(self.OLD)
        self.assertEqual(desk.device.unplugged(),
                         [("music", self.OLD["name"])])


class MusicCardTest(_Test):
    """🔊 What the status bar's green badge names: the card chosen for the
    music, while it is plugged in."""

    def test_nothing_chosen_names_nothing(self):
        self.assertIsNone(_Desk().device.music_card())

    def test_the_system_default_is_no_card(self):
        desk = _Desk()
        desk.choose("music", SYSTEM_DEFAULT)
        self.assertIsNone(desk.device.music_card())

    def test_a_plugged_in_card_is_named(self):
        desk = _Desk()
        desk.choose("music", USB12)
        self.assertEqual(desk.device.music_card(), "Out 1/2 (USB interface)")

    def test_an_unplugged_card_is_not(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.devices.outputs.remove(USB12)
        self.assertIsNone(desk.device.music_card())
        self.assertEqual(desk.warnings, [], "a look, not a warning")


class ReadinessLookTest(_Test):
    """🚦 Ready? asks which chosen cards are missing and whether a preview
    would be refused — a look that warns nothing and moves nothing."""

    def test_nothing_chosen_has_nothing_unplugged(self):
        desk = _Desk()
        self.assertEqual(desk.device.unplugged(), [])
        self.assertFalse(desk.device.cue_on_music())

    def test_an_unplugged_choice_is_named_without_a_warning(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.choose("cue", USB34)
        desk.device.sync()
        desk.devices.outputs.remove(USB12)
        desk.devices.outputs.remove(USB34)
        self.assertEqual(desk.device.unplugged(),
                         [("music", "Out 1/2 (USB interface)"),
                          ("cue", "Out 3/4 (USB interface)")])
        self.assertEqual(desk.warnings, [])

    def test_the_system_default_is_never_unplugged(self):
        desk = _Desk()
        desk.choose("filler", SYSTEM_DEFAULT)
        self.assertEqual(desk.device.unplugged(), [])

    def test_pre_listen_on_the_music_card_would_be_refused(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.choose("cue", USB12)
        self.assertTrue(desk.device.cue_on_music())

    def test_pre_listen_on_its_own_card_is_fine(self):
        desk = _Desk()
        desk.choose("music", USB12)
        desk.choose("cue", USB34)
        self.assertFalse(desk.device.cue_on_music())

    def test_a_missing_pre_listen_card_falls_back_onto_the_music(self):
        """Its fallback is the system default — which is the music's card when
        nothing else is chosen for the music."""
        desk = _Desk()
        desk.choose("cue", USB34)
        desk.devices.outputs.remove(USB34)
        self.assertTrue(desk.device.cue_on_music())
        self.assertEqual(desk.warnings, [])

    def test_pre_listen_same_as_the_music_is_off_not_refused(self):
        desk = _Desk()
        self.assertFalse(desk.device.cue_on_music())

    def test_pre_listen_same_as_the_music_shares_its_output(self):
        """Marcel: "ready check should warn when pre player is same output
        as main". Nothing chosen: 📚 and 🏆 previews play on the music's
        output, the other panes on the deck's player."""
        desk = _Desk()
        self.assertTrue(desk.device.cue_shares_music())
        desk.choose("cue", USB34)
        self.assertFalse(desk.device.cue_shares_music())
        self.assertEqual(desk.warnings, [])

    def test_with_one_output_sharing_it_is_no_warning(self):
        desk = _Desk()
        desk.devices.outputs[:] = [SPEAKERS]
        self.assertFalse(desk.device.cue_shares_music())

    def test_with_one_output_there_is_nothing_to_refuse(self):
        """A laptop with only its speakers: there is no other card to
        choose, so pre-listen plays there and Ready? has nothing to say."""
        desk = _Desk()
        desk.devices.outputs[:] = [SPEAKERS]
        desk.choose("cue", SYSTEM_DEFAULT)
        self.assertTrue(desk.device.single_output())
        self.assertFalse(desk.device.cue_on_music())

    def test_several_outputs_are_not_one(self):
        self.assertFalse(_Desk().device.single_output())


class AnnouncerDeviceTest(_Test):
    """The recorded announcements' player is built on first use."""

    def setUp(self):
        from PySide6.QtMultimedia import QMediaDevices
        from player.audio.announce import DanceAnnouncer
        default = bytes(QMediaDevices.defaultAudioOutput().id())
        others = [d for d in QMediaDevices.audioOutputs()
                  if bytes(d.id()) != default]
        if not others:
            self.skipTest("needs a second audio output on this machine")
        self.dev = others[0]
        self.ann = DanceAnnouncer()

    def test_a_device_set_before_the_player_exists_is_used(self):
        self.ann.set_device(self.dev)
        self.ann._clip_engine()
        self.assertEqual(bytes(self.ann._clip_out.device().id()),
                         bytes(self.dev.id()))

    def test_a_device_set_afterwards_moves_it(self):
        self.ann._clip_engine()
        self.ann.set_device(self.dev)
        self.assertEqual(bytes(self.ann._clip_out.device().id()),
                         bytes(self.dev.id()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
